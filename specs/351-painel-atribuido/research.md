# Pesquisa — Feature 351 (painel atribuído)

Tudo lido na `main` (`20bf93c0`, 17/11/2026) e nas notas da pesquisa "Máquina de vendas Manto" (pasta compartilhada
das sessões, `research_notes/…/erp_marketing_345.md` e `erp_crm_funil.md`). Nenhuma `NEEDS CLARIFICATION` ficou aberta.

## R1. Onde mora a atribuição

- **Decisão**: módulo novo `app/marketing/atribuicao_ops.py` com uma função de regra (`_toque_da_venda`) e uma de
  entrada (`atribuir_vendas(inicio, fim, *, client_ids=None)`). Todo número atribuído (frente, lista, card, cliente
  novo) passa por ela. A leitura dos contatos pagos é `toques_pagos(client_ids)`.
- **Por quê**: a 348 vai gravar `conversa_id` no evento e no orçamento. Com uma porta só, a troca é: "se o evento tem
  conversa ligada, o contato pago dessa conversa vence a busca pela ficha" — dentro de `atribuir_vendas`, sem mexer em
  quem consome.
- **Alternativas**: estender `comando_ops.vendas_por_frente` com JOINs (espalharia a regra em SQL de painel);
  calcular no `desempenho_ops` (já casa lead por nome de campanha, regra diferente).

## R2. A frente do evento continua numa função só

- **Decisão**: `comando_ops.frente_venda_sql()` segue sendo o único lugar que diz a frente de um evento; a 351 só a
  importa. A 348 troca o corpo por `coalesce(CalendarEvent.frente, <regra de hoje>)`.
- **Por quê**: pedido explícito da sessão principal ("leia a frente por uma função única, que a 348 troca pela coluna").

## R3. Contatos pagos e relógios

| Fonte | Tabela/coluna | Momento | Relógio |
|---|---|---|---|
| conversa | `conversa_anuncios` (tipo `anuncio`) via `conversas.client_id` | `momento` | UTC naive |
| ficha | `clients.anuncio_origem_id/_em`, `anuncio_recente_id/_em` | `*_em` | UTC naive |
| utm | `clients.utm_source` reconhecido por `desempenho_ops.platform_from_utm_source` | entrada na base (`kommo_created_at` ou `created_at`) | SP naive → convertido para UTC |

- A venda: `CalendarEvent.created_at` (UTC) e `sale_date` (data de SP). Cliente do evento: `event_clients` ∪
  `calendar_events.client_id` (o denormalizado ainda é o único em evento antigo).
- `utm_source` orgânico (bio, site) nunca é mapeado para plataforma: só valores de `_SOURCE_PLATFORM` contam. Os 462
  "Tintim: botão do site" não têm `utm_source` (conferido no log de 17/11) e ficam de fora.

## R4. A regra

Contato T vale para a venda V quando `T.momento ≤ V.created_at` **e** `dia_sp(T) ≤ V.sale_date ≤ dia_sp(T) + 45` **e**
`V.sale_date ≥ 2026-06-01`. Entre os válidos, o de maior momento; empate → conversa > ficha > utm. Constantes em
`app/constants.py`: `ATRIBUICAO_JANELA_DIAS = 45`, `ATRIBUICAO_DESDE = date(2026, 6, 1)`,
`INCREMENTALIDADE_PREMISSA = Decimal("0.50")`.

- **Alternativas rejeitadas**: primeiro contato (premia a campanha de entrada, não a que fechou); divisão linear (sem
  volume para valer a pena); usar só `sale_date` sem `created_at` (o evento criado antes do contato — cliente que já
  tinha reservado — seria creditado ao anúncio).

## R5. Frente da campanha do contato

- Meta (conversa e ficha): `anuncios_meta.campanha_id/campanha_nome` → `comando_ops.frente_da_campanha('Meta Ads', …)`
  (correção manual > prefixo).
- utm: `utm_campaign` normalizado (`desempenho_ops.normalize_campaign_name`) contra os nomes de
  `marketing_campaign_metrics` → `(platform, campaign_id)` → `frente_da_campanha`; sem casamento →
  `frente_por_prefixo(utm_campaign)`; sem prefixo → `None` ("sem frente").

## R6. Funil por frente, anúncio, peça e conceito — sem dinheiro no domínio das conversas

- **Decisão**: `app/conversas/funil_ops.py` ganha as divisões `frente`, `anuncio`, `peca`, `conceito` (contagens). A
  coorte passa a trazer `anuncio_id` e `campanha_id` do primeiro anúncio. O dinheiro fica no marketing:
  `atribuicao_ops.funil_com_custo(...)` chama `funil_ops.funil(...)` e põe gasto e custos em cada grupo pela chave.
- **Por quê**: a invariante 39 do `docs/04` ("o funil não tem dinheiro") continua valendo para o Comercial; o custo só
  sai pelo gate de Marketing.
- **Gasto do grupo**: frente → `gasto_por_frente(..., plataforma="Meta Ads")` (as conversas com origem só vêm da Meta);
  anúncio → soma de `marketing_ad_metrics.spend` do anúncio; peça → anúncios do card; conceito → cards do conceito.
- O import de `comando_ops` dentro de `funil_ops` é tardio (dentro da função) para não criar ciclo de carga.

## R7. Resultado do card

- `funil_ops.etapas_por_anuncio(ids)` — conversas cujo **primeiro** anúncio está no conjunto, etapa pela mesma
  `_etapas`; `atribuicao_ops.vendas_por_anuncio(ids)` — vendas cujo contato atribuído é de um anúncio do conjunto.
- "No ar": por anúncio, o último dia com `spend > 0`; por plataforma, o último dia com leitura em
  `marketing_ad_metrics`. No ar = gastou num dos 3 últimos dias com leitura (`ANUNCIO_NO_AR_DIAS = 3`).
- `marketing_ops` importa `atribuicao_ops` dentro da função (`atribuicao_ops → comando_ops → marketing_ops`).

## R8. Fila da rotina

`cards_prontos_sem_anuncio` passa a aceitar `pronto`, `agendado` e `publicado` (`MARKETING_STATUS_FILA_ANUNCIO`). O
card de anúncio sem anúncio montado em Agendado/Publicado é um card que alguém arrastou antes da hora — continua na fila.

## R9. Proposta

- Números: `valor_antes_num`/`valor_depois_num` aceitos da rotina; se vierem vazios, lidos do texto quando o tipo é
  `verba` ou o texto traz "R$" (`"R$ 1.234,56/dia"` → 1234.56). "Público: mães 25–40" não vira número.
- Frente: a enviada > a da campanha do alvo (campanha: o próprio alvo; conjunto/anúncio: a campanha da última linha
  de `marketing_ad_metrics`) > a do card.
- Impacto mensal (`DIAS_NO_MES_DO_IMPACTO = 30`): verba `(depois − antes) × 30`; ativar `(depois ou custo/dia) × 30`;
  pausar `−(antes ou custo/dia) × 30`; público `None`.
- Sino: `notificacoes_ops.KIND_MARKETING_PROPOSTA = "marketing.proposta"` → `(SUPERADMIN,)`, regime A (proposta e
  aviso na mesma transação), `dedupe_key = marketing.proposta:<id>`, link `/marketing/decisoes`.

## R10. Diário estruturado

- Medição: campanha → `marketing_campaign_metrics` diário (`is_daily`) da campanha (cai para `marketing_ad_metrics`
  por `campaign_id` quando não há); conjunto → `marketing_ad_metrics.adset_id`; anúncio → `marketing_ad_metrics.ad_id`.
- Métricas (`METRICAS_DO_TESTE`): `conversas`, `custo_conversa`, `gasto`, `cliques`, `cadastros`.
- Antes = `[mudou_em − janela, mudou_em − 1]`; depois = `[mudou_em, mudou_em + janela − 1]`. "Completo" quando a
  última leitura da plataforma alcança o fim do depois. Efeito líquido = variação do alvo − variação do controle, em
  pontos percentuais (diferença em diferenças, a forma simples que cabe no volume).
- Linha de base: congelada na criação (a informada, ou o "antes" calculado na hora).

## R11. Telas no celular

- Campanhas: cartões abaixo de `md` (768 px), tabela de `md` para cima.
- Temas: paginação no servidor (`TEMAS_POR_PAGINA = 50`), `pagina` no endereço; filtro novo zera a página; página além
  da última volta a última. "Confirmar todas as sugestões" passa a ser "desta página".
- Kanban: filtro **na tela**, sobre a lista que já vem inteira — a mutação otimista de mover card escreve na chave
  `POSTS_KEY` exata, e uma chave por filtro quebraria isso. Filtros no endereço (`frente`, `tipo`, `minhas=1`).

## R12. Custo por cliente novo

`atribuicao_ops.clientes_novos(inicio, fim)` devolve `(total, de_anuncio)` com a mesma régua de entrada na base do
Desempenho (`desempenho_ops._entrada_na_base`). "De anúncio" = `anuncio_origem_id` preenchido ou `utm_source` de
plataforma de anúncio. O payload `cac` ganha `new_clients_ads` e `value` passa a ser `spend ÷ new_clients_ads`.

## R13. Banco e telas desta rodada

- Espelho próprio `manto_351` restaurado de `backups/manto_2026-11-17_0200.dump` (o `manto_local` é das sessões
  348–350 também). URL em `.local-db-url` do worktree (ignorado pelo git).
- Telas: backend na porta 5351 (cópia de `scripts/db/run-local-sem-google.py` com a porta trocada) e Vite na 6351
  (config temporária com o proxy na 5351); temporários apagados antes do commit.
