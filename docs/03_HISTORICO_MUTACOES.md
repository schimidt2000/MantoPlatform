# 03 — Histórico de Mutações (índice)

> **Documento vivo — APPEND ONLY.** Cada feature concluída adiciona uma entrada **no topo** da
> seção "Registro", e uma linha **no topo** da tabela do índice. Nunca reescrever entradas antigas
> (elas são o histórico); correções entram como nova entrada referenciando a anterior.
>
> Última atualização: **2026-08-07** · Estado do repositório: pós-feature **222 (paridade do
> "Exportar elenco")** · Head de migration: `c5d92fa16e34`
> (confira com `flask db heads` — não versione o head em prosa fora deste cabeçalho).

## Como ler isto sem gastar a janela de contexto

Este arquivo tinha 202 KB (~61k tokens, ~30% de uma janela de 200k) e nenhum índice: era preciso
ler tudo para descobrir onde estava a resposta. Agora ele é **índice + as 12 entradas mais
recentes**; o restante foi movido, **sem perder uma linha sequer**, para `docs/historico/`.

1. Ache a feature na tabela abaixo (arquivo + linha).
2. Leia **só** aquela entrada: `Read(file_path=..., offset=<linha>, limit=~70)`.
3. Nunca leia um arquivo de histórico inteiro — nenhuma pergunta real precisa disso.

Se a sua pergunta é "como o sistema funciona hoje" e não "por que ficou assim", **este documento é
o lugar errado**: comece por `docs/00_MAPA_DO_SISTEMA.md`.

| Preciso de… | Vá para |
|---|---|
| Onde mexer / o que ler primeiro | `docs/00_MAPA_DO_SISTEMA.md` |
| Schema, endpoints, RBAC, deploy | `docs/01_SISTEMA_E_BANCO.md` |
| Fluxo e UX de uma tela | `docs/02_MAPA_DE_PAGINAS_E_UX.md` |
| Fluxos, invariantes e armadilhas por domínio | `docs/04_GUIA_DE_DOMINIOS.md` |
| Dívida técnica priorizada | `docs/05_DIVIDA_TECNICA.md` |
| **Por que** uma decisão foi tomada / o que foi descartado | **este documento** |

## Índice de features

Legenda de arquivo: **(aqui)** = neste documento · **H2** = `docs/historico/200-207.md` ·
**H1** = `docs/historico/184-199.md`.

| Feature | Título | Data | Migration | Arquivo | Linha |
|---|---|---|---|---|---|
| **222** | Exportar elenco perdeu quatro campos (nascimento/CPF/RG/documento) na migração para o React | 2026-08-07 | `—` | (aqui) | 134 |
| **221** | Agente auditor financeiro semanal (endpoints + fix de sobrescrita de upload) | 2026-08-06 | `—` | (aqui) | 161 |
| **220b** | Hotfix: menu "Ferramentas" do evento embaçado no meio | 2026-08-06 | `—` | (aqui) | 133 |
| **220** | Formulários×clientes×eventos: vínculo endurecido, fila de revisão e histórico da cliente | 2026-08-06 | `—` | (aqui) | 156 |
| **219** | Email errado do talento: confirmação no cadastro e fila de devoluções | 2026-08-06 | `b4c81ef07d29`, `c5d92fa16e34` | (aqui) | 217 |
| **218** | Superadmin corrige/exclui faixa de salário; Usuários com filtros; telas desempilhadas | 2026-08-06 | `—` | (aqui) | 292 |
| **217** | Tema escuro com switch na sidebar, e reestruturação da documentação | 2026-08-06 | `—` | (aqui) | 367 |
| **216** | Cachê no portal, prévia de link no WhatsApp, contraste e endurecimento de segurança | 2026-08-05 | `—` | (aqui) | 436 |
| **215** | Tela de evento em abas, com edição inline e buscas visuais | 2026-08-05 | `—` | (aqui) | 494 |
| **214** | Hotfix: Revendedor EducaManto sem acesso a nada (calculadora incluída) | 2026-08-05 | `—` | (aqui) | 571 |
| **213** | Acervo 3D: superadmin exclui peça já usada, desvinculando de todos os eventos | 2026-08-05 | `—` | (aqui) | 606 |
| **212** | Hotfix: diálogos abrindo pela metade, fora da tela | 2026-08-05 | `—` | (aqui) | 638 |
| **211** | Vitrine: quadro da foto com teto e piso | 2026-08-05 | `—` | (aqui) | 671 |
| **210d** | Hotfix: navegador preso no bundle antigo (e vínculo de ficha mais óbvio) | 2026-08-05 | `—` | (aqui) | 706 |
| **210c** | Hotfix: Comercial voltou a enxergar o pagamento do evento | 2026-08-05 | `—` | (aqui) | 738 |
| **210b** | Hotfix: buscador de pré-contrato mudo | 2026-08-05 | `—` | (aqui) | 767 |
| **210** | Hotfix: horário deslocado, anexo do evento e orçamento sem saída | 2026-08-05 | `—` | (aqui) | 802 |
| **209** | Catálogo como espinha organizacional (página própria + fichas + busca) | 2026-08-05 | `e7a1c94f20b3` | (aqui) | 875 |
| **208** | Restauração do papel ENSAIO (dashboard + agendamento + presença) | 2026-08-05 | `—` | (aqui) | 924 |
| **206b** | Hotfix: superfícies públicas por link voltaram a abrir sem login | 2026-08-05 | `—` | H2 | 11 |
| **207** | Pacote de melhorias operacionais (5 frentes) | 2026-08-04 | `d9f2b3a41c07` | H2 | 36 |
| **206** | React como interface primária e proxy reverso em produção | 2026-08-04 | `—` | H2 | 101 |
| **205f** | Loja de Interações Virtuais (resiliência a falha de serviço externo) | 2026-08-04 | `c17b3ea94f52` | H2 | 187 |
| **205e** | Loja de Interações Virtuais (registro financeiro segregado e fechamento) | 2026-08-04 | `—` | H2 | 259 |
| **205d** | Loja de Interações Virtuais (presente 3D, fila de produção e entrega do vídeo) | 2026-07-31 | `—` | H2 | 311 |
| **205c** | Loja de Interações Virtuais (efetivação automática da venda) | 2026-07-31 | `—` | H2 | 357 |
| **205b** | Loja de Interações Virtuais (checkout público e soft lock) | 2026-07-31 | `a5c81e0cd247` | H2 | 406 |
| **205** | Loja de Interações Virtuais (fundação + gestão de campanhas) | 2026-07-31 | `f3a9c72e5d18` | H2 | 458 |
| **204b** | Múltiplos Temas por postagem de marketing | 2026-07-29 | `b7d4f81a6e0c` | H2 | 534 |
| **204** | Módulo de Gestão de Marketing e Frequência | 2026-07-29 | `a3c7e1d59f42` | H2 | 589 |
| **203** | Melhorias na Comunicação e Alertas de E-mail | 2026-07-29 | `—` | H2 | 715 |
| **202** | Fila de Impressão dirigida pelo evento | 2026-07-29 | `e4f7b2c9a350` | H2 | 779 |
| **201** | Acervo 3D: uma peça, vários arquivos | 2026-07-29 | `d9e3a5b7c124` | H2 | 837 |
| **200** | Módulo Core de Impressões 3D | 2026-07-29 | `c8d2f4a6b013` | H2 | 906 |
| **199** | Liberação do status 'No banco' para Comissões e Recorrentes | 2026-07-29 | `—` | H1 | 11 |
| **197** | Refatoração do Dashboard de Avaliações de Clientes | 2026-07-28 | `—` | H1 | 68 |
| **196** | Pivot do Pipeline de Vendas para Dashboard Comercial | 2026-07-28 | `—` | H1 | 146 |
| **195** | Autocomplete de Endereços com Google Places e Comboboxes com Busca Visual | 2026-07-28 | `—` | H1 | 216 |
| **194** | Planilha de Pagamentos: cards-filtro, colorização por faixa e soma da seleção | 2026-07-28 | `—` | H1 | 302 |
| **193** | Importação Histórica do WhatsForm (One-time Migration) | 2026-07-28 | `—` | H1 | 387 |
| **191** | Migração do Portal do Artista (React) e Auditoria de Segurança — **portal** | 2026-07-28 | `—` | H1 | 512 |
| **192** | Detalhe do Evento: layout de duas colunas com paridade total da tela clássica | 2026-07-27 | `—` | H1 | 641 |
| **191** | Calculadora de Orçamento: paridade de layout clássico + cálculo reativo — **orçamento** | 2026-07-27 | `—` | H1 | 717 |
| **190** | Paridade e Unificação do Módulo de Orçamentos e EducaManto (React) | 2026-07-27 | `—` | H1 | 775 |
| **189** | Módulo Financeiro de Alta Fidelidade e Consistência (React) | 2026-07-27 | `—` | H1 | 864 |
| **188** | Refatoração e Paridade do Módulo de Formulários | 2026-07-27 | `—` | H1 | 957 |
| **187** | Reestruturação do Módulo de Comissões | 2026-07-24 | `—` | H1 | 1034 |
| **186** | Gerenciador de Catálogo: UX e fluxo Ficha ↔ Catálogo ↔ Venda | 2026-07-24 | `—` | H1 | 1086 |
| **185** | Catálogo Vitrine Completo: Temas, Personagens e Vídeo | 2026-07-24 | `9f1c3a7b5e2d` | H1 | 1135 |
| **184** | Reconstrução do Formulário de Cadastro/Edição de Eventos | 2026-07-24 | `—` | H1 | 1181 |

> **Colisões e buracos de numeração** (a numeração é a chave primária de fato do histórico e não é
> contínua): existem **duas** entradas `191` — a do Portal do Artista em React e a da Calculadora
> de Orçamento, ambas em H1, desambiguadas na coluna Título. A feature **198 não existe** (número
> pulado, não perdido). `206b` foi mergeada depois de `207`/`208`, por isso aparece fora de ordem
> numérica na ordem cronológica do arquivo.

## Índice por assunto

| Assunto | Features |
|---|---|
| Agenda / evento / formulário de evento | 215, 210, 208, 192, 184 |
| Loja de Interações Virtuais | 205, 205b, 205c, 205d, 205e, 205f |
| Impressões e Acervo 3D | 213, 202, 201, 200 |
| Marketing e frequência | 204, 204b |
| Catálogo e vitrine | 211, 209, 186, 185 |
| Financeiro, comissões e pagamentos | 210c, 199, 194, 189, 187 |
| Orçamento e EducaManto | 214, 191 (orçamento), 190 |
| Portal do Artista | 216, 191 (portal) |
| Design system, tema e acessibilidade | 217, 216, 212 |
| Documentação e economia de token | 217 |
| Formulários e pré-contrato | 210b, 188, 193 |
| Avaliações e dashboards | 197, 196 |
| Infra, deploy, proxy e cache de bundle | 210d, 206, 206b, 212 |
| Segurança / RBAC / endurecimento | 216, 214, 206b |

**Runbooks reexecutáveis embutidos no histórico** (procedimento, não registro): carga histórica do
WhatsForm com backup e import — `docs/historico/184-199.md`, entrada **193**. Não há
`docs/04_RUNBOOKS.md`: os demais procedimentos operacionais (refresh do `manto_local`, backup)
vivem em `scripts/db/README.md`, que **não é versionado** (`.gitignore` cobre `/scripts/db/`).

Formato de cada entrada:

```
### <NNN> — <título>            (branch · data do merge · migration)
Motivação · O que mudou (Backend / Banco / Frontend) · Impacto em RBAC e regras de negócio ·
Rotas e endpoints novos/alterados · Riscos e pegadinhas
```

---

## Registro

*(As 12 entradas mais recentes. As anteriores estão em `docs/historico/` — ver índice acima.)*

### 222 — Exportar elenco perdeu quatro campos na migração para o React
`main` · **2026-08-07** · sem migration

**Motivação.** Reclamação direta: "no antigo sistema Flask essa telinha de exportar elenco tinha
mais informações". O modal Jinja (`app/templates/event_detail.html`) oferecia **dez** campos —
Personagem, Nome completo, Data de nascimento, CPF, RG, Link documento, Top, Bottom, Calçado e
Altura. O React ficou com **seis**: a porta esqueceu os quatro de documento/nascimento, porque
`_serialize_talent` (`app/api/agenda_read.py`) nunca chegou a serializá-los.

**O que mudou.** *Backend*: `_serialize_talent` ganhou `birth_date` (ISO), `cpf`, `rg` e
`doc_photo_path`, atrás de um novo parâmetro `show_pii`. *Frontend*: `RoleTalent` (`lib/agenda.ts`)
declara os quatro como **opcionais** — para os outros papéis a chave nem existe no JSON — e o
`ExportElencoDialog` voltou a ter as dez caixas de seleção, na ordem da tela antiga.

**Impacto em RBAC.** `show_pii = show_casting or can_confirm` — exatamente o público que via o
botão na tela antiga (`CASTING`, `COMERCIAL`, `SUPERADMIN`). Sem esse gate a mudança seria um
vazamento: Figurino, Ensaio e Artista 3D leem o **mesmo** `/api/events/<id>` e passariam a receber
CPF e RG de todo mundo escalado. Verificado em `scripts/db/verify_export_elenco_documentos.py`
(21/21 contra `manto_local`), que testa os dois lados — quem recebe e quem não recebe.

**Pegadinhas.** (1) `birth_date` é data pura: `new Date("1998-03-12")` vira meia-noite **UTC** e
em São Paulo volta um dia — o modal formata quebrando a string, sem `Date` (a mesma armadilha da
210, agora em data sem hora). `TalentDetailPage.formatDate` ainda tem esse bug, não tocado aqui.
(2) O link do documento tem que sair **absoluto**: `assetUrl()` devolve path puro em dev, e o
texto exportado é colado no WhatsApp. (3) `doc_photo_path` pode já ser uma URL do Drive (legado da
154) — daí o teste de `^https?://` antes de prefixar a origem.

### 221 — Agente auditor financeiro semanal
`221-agente-auditor-financeiro` · **2026-08-06** · sem migration

**Motivação.** O dono não revisa todas as movimentações; comprovante falso, duplicado ou
divergente passava sem verificação nenhuma. Pedido direto: rotina de segunda ~06h que lê os
comprovantes e cruza com o registrado, usando a assinatura do Claude (zero API paga).

**O que entrou.** (1) **Fix crítico**: `_save_bounded_upload` salvava com `secure_filename`
puro — uploads homônimos ("Comprovante.pdf") sobrescreviam o binário anterior em silêncio;
a base de produção tem **11 casos reais** de `file_path` repetido em `event_payments` por
causa disso. Agora prefixo timestamp+uuid. (2) Endpoints `audit_agent.py` (ver
`docs/01_SISTEMA_E_BANCO.md` §3.6). (3) Pipeline `scripts/auditor/` (coleta read-only →
leitura dos comprovantes por visão → batimento → relatório por e-mail), com memória SQLite
idempotente por (entidade, SHA-256). (4) Skills locais `financeiro-auditor` (rodada) e
`financeiro` (analista sob demanda) — `.claude/` é gitignored, vivem na máquina do auditor.

**Decisões.** Cachê/comissão/recorrente/BV não têm campo de anexo — ficam listados como
"não auditáveis" (decisão de produto; reavaliar depois). Job roda na máquina local via
scheduled task do Claude Code, não como cron do Railway (visão pela API teria custo). Store
local em vez de tabela nova: ERP intocado.

**Pegadinhas.** `recurring_expense_entries.paid_at` é **DATE**, não timestamp.
"Recebido > venda" precisa comparar contra venda + `transport_value` + `acrescimo_value`
(cobrados nos mesmos comprovantes, fora de `sale_value`) e tolerar ~1% (juros de
parcelamento) — sem isso, 3 falsos positivos e casos reais escondidos no meio (ex.: evento
186 com R$ 160.550,00 digitado no lugar de R$ 1.605,50). Anomalias de varredura all-time
precisam de supressão por `entity_uid` no store, senão repetem todo relatório.

### 220b — Hotfix: menu "Ferramentas" do evento embaçado no meio
`main` · **2026-08-06** · sem migration

**Sintoma.** No detalhe do evento, o menu "⋯ Ferramentas" abria com uma faixa horizontal no meio
embaçada/apagada, como se o menu estivesse partido em dois pedaços.

**Causa.** Empate de `z-index`. O painel do `KebabMenu` era `z-20` — o mesmo degrau da régua de
abas (`sticky top-14 z-20` em `EventDetailPage`). Empate de z-index se decide por **ordem no
DOM**, e a régua vem depois do cabeçalho, então ela ganhava. Como a régua tem
`backdrop-blur(8px)` + `bg-surface/95`, os 62px do menu que caíam atrás dela apareciam
embaçados — não era um menu quebrado, era um menu **coberto**.

**Medição (antes/depois).** `elementFromPoint` no centro da faixa devolvia a régua; depois do
ajuste devolve o próprio item de menu, e nenhum dos 10 itens fica coberto por outro elemento.

**Correção.** Painel do `KebabMenu` sobe para `z-30` — a camada de popover que o `Combobox` de
`@manto/ui` já usava. Vocabulário de camadas do app, para não regredir: conteúdo `auto` <
cromo fixo de página `z-20` < **popover `z-30`** < topbar/sidebar do app `z-30/z-40` < diálogo
`z-40` (véu) / `z-50` (conteúdo).

**Pegadinha.** Comentário `//` solto entre atributos de JSX é erro de sintaxe; por isso a classe
virou constante nomeada com o comentário acima dela — que é onde a regra de camada é procurada.

### 220 — Formulários×clientes×eventos: vínculo endurecido, fila de revisão e histórico da cliente
`main` · **2026-08-06** · sem migration (correção de dados direto na produção, com dump prévio)

**Motivação.** Um formulário apareceu vinculado ao evento errado, e a auditoria completa da base
(1.495 respostas) explicou o porquê. A heurística nível 3 da feature 126 — "sem evento na data
informada, mas o telefone tem exatamente 1 evento futuro → vincula" — ignorava a data que a
cliente escreveu: **25 formulários históricos de 2023–2025 (importados na 193) foram grudados em
eventos de 2026 das mesmas clientes recorrentes**. Além disso, 88% das respostas não tinham evento
(a agenda só existe desde 02/01/2026), e mesmo respostas com cliente E evento não apareciam na
ficha da cliente, porque **nenhum caminho de vínculo criava a linha em `event_clients`**.

**Correção de dados (produção, 06/08 ~15h).** Script SQL transacional, ensaiado na cópia local:
(A) desfez os 25 vínculos `auto_client`/`auto_date` com divergência resposta×evento > 30 dias,
marcando `event_link_locked` (a automação nunca religa) e `event_link_ambiguous` (aparece na fila
de revisão); datas com ano < 2000 ficaram de fora do critério (lixo de digitação, ex. `0006-08-22`
com vínculo correto). (B) criou 20 associações `event_clients` em 18 eventos que tinham resposta
com cliente mas nenhum cliente associado — mais recente vira `Contratante`, demais `Outros`.
(C) restaurou o denormalizado `calendar_events.client_id` nesses 18. Rollback disponível:
`backups/manto_2026-08-06_1449.dump`.

**Backend.**
- `_attempt_auto_link` (formularios/routes.py) reescrito: vincula **só com data+telefone
  confirmados** — evento real na data informada cujo cliente associado tem o telefone da resposta.
  Evento na data sem confirmação → `ambiguous` (fila de revisão). Sem evento na data → nada.
  A heurística de "evento futuro" morreu; `auto_client` não é mais gerado (linhas antigas seguem
  válidas para leitura).
- `formularios_ops.ensure_event_client` (novo): todo vínculo com cliente conhecido garante a linha
  em `event_clients` (primeiro = Contratante + denormalizado; demais = Outros). Chamado por
  `link_event`, `associate_client` (quando a resposta já tem evento) e implícito no fluxo de criar
  evento a partir da resposta (que agora também marca `manual` + `locked` — antes deixava o
  vínculo "anônimo" e religável).
- `formularios_ops.count_status`/`STATUS_FILTERS` + `list_responses(filtro=)`: contadores e filtro
  server-side (`sem_evento`, `sem_cliente`, `ambiguos`, `futuros_sem_evento` — este ordenado por
  urgência).
- `client_ops.list_client_form_history` (novo): festas registradas em formulário por cliente —
  decisão de produto: **histórico pré-2026 vem dos formulários; eventos passados NÃO são
  materializados na agenda**.
- `client_ops.client_metrics` (novo): novos clientes por mês (12m, origem agregada; Kommo usa
  `kommo_created_at`, senão a carga viraria pico falso) + recorrentes (2+ eventos).

**Endpoints.** `GET /api/formularios/respostas` ganhou `?filtro=` e devolve `counts` junto (uma
chamada só); `GET /api/clientes/<id>` ganhou `form_history`; novo `GET /api/clientes/metricas`.

**Frontend (apps/internal).** FormulariosAdminPage: 5 cartões-filtro clicáveis no topo, linha
vermelha (`bg-red-50`) e badge `⚠ Sem evento — festa dd/mm/aaaa` para festa futura sem evento,
badge de origem `auto`/`manual`, badge `Revisar vínculo` nos ambíguos. ClientDetailPage: card
"Festas anteriores (formulários)" com marcação "na agenda"/"só formulário". ClientsListPage: KPIs
(novos este mês, com evento, recorrentes) + barras de novos por mês.

**Riscos e pegadinhas.**
- O primeiro ciclo do `retry_auto_link_pending` pós-deploy vai reprocessar ~1.300 respostas sem
  evento e marcar `event_link_ambiguous` nas ~130 que têm evento na data sem telefone confirmado —
  é o comportamento desejado (fila de revisão), não um bug.
- `formatDate` do ClientDetailPage formatava com `new Date(iso)`: data-só (`event_date`) desloca
  um dia no fuso de São Paulo. Agora fatia a string. Mesma armadilha da 210/`relatorio_horarios`.
- Kommo trouxe milhares de clientes de nome genérico ("Fernanda" ×34, "." ×41) — duplicata de
  verdade se detecta por CPF/e-mail (8 pares por CPF, 18 por e-mail na auditoria), não por nome.
  Ferramenta de mesclagem ficou para uma próxima feature.
- Verificação: `scripts/db/verify_220_vinculos_formularios.py` (15 checagens, roda contra
  `manto_local`).

### 219 — Email errado do talento: confirmação no cadastro e fila de devoluções
`main` · **2026-08-06** · migrations `b4c81ef07d29` (email_bounces) e `c5d92fa16e34` (confirmação)

**Motivação.** Gente se cadastra com o email errado (ou com a caixa lotada) e **o sistema nunca
fica sabendo**: a falha existe apenas como um aviso do Mail Delivery Subsystem na caixa de quem
enviou. O talento some do radar sem ninguém perceber, e a descoberta só acontece quando um convite
volta — se alguém reparar.

**Achado que desenhou a solução.** Uma varredura das devoluções reais da conta encontrou 48
mensagens e 13 endereços distintos. Os códigos estendidos (RFC 3463) separam dois problemas que
pedem ações opostas: **`4.2.2`/`5.2.2` caixa cheia** (23) — "avisa no WhatsApp para liberar
espaço" — contra **`5.1.1` usuário inexistente** (8) e **`5.1.2` domínio inexistente** (5) — "o
cadastro está furado, pega o email certo". Um dos endereços é `gabriella.baleeiro@hotmail.con`:
`.con`, não `.com`. Nenhum validador de formato pega isso, porque é um email sintaticamente
perfeito.

**Parte 1 — fila de devoluções (`EmailBounce`).**

`app/integracoes/imap_client.py` lê a caixa por IMAP com a **mesma App Password que o envio já
usa** — sem credencial nova e sem escopo OAuth novo, o que foi decisivo para a viabilidade. A
leitura é estritamente passiva: `EXAMINE` (não `SELECT`) e `BODY.PEEK[]`, então nada é marcado como
lido, movido ou apagado.

`app/talents/bounce_ops.py` interpreta o bloco `message/delivery-status`, classifica pelo código e
casa o destinatário com `Talent`/`User`. **Devolução de endereço desconhecido é descartada de
propósito**: a caixa é a pessoal de quem opera a conta, e guardar contato alheio seria coleta que
ninguém pediu. O total ignorado volta no resultado da varredura para a decisão não ficar invisível
(17 na primeira execução).

Idempotência pelo `Message-Id` único — reler a caixa não duplica (confirmado: 2ª varredura,
`novas=0`). Uma mensagem que reporta N destinatários vira N linhas com sufixo `#índice`, sem perder
a trava. A fila é **agrupada por endereço** na leitura: caixa cheia gera um aviso por tentativa, e
o casting precisa de uma linha por pessoa com o contador de falhas.

A varredura roda em thread (30 min) com **claim atômico** em `import_state` — obrigatório, não
opcional: o Railway roda vários workers gunicorn e cada um abriria a própria conexão IMAP.
Desligada por padrão em ambiente local (`EMAIL_BOUNCE_SWEEP_ENABLED` segue `_suppress_mail`), senão
um processo de desenvolvimento apontado para o espelho leria a caixa real.

**Parte 2 — confirmação do email no cadastro público.**

A confirmação acontece **depois do envio**, com o `Talent` já gravado. Isso não é detalhe: o
formulário tem dados, medidas, PIX, duas fotos e um documento — condicionar a gravação a uma caixa
que talvez nem exista trocaria um problema por outro pior. Na tela de sucesso a pessoa relê o
endereço, corrige **só ele** e reenvia; nada mais é reenviado nem revalidado.

O `email_verify_token` faz dois papéis de propósito: é o link que confirma **e** a credencial da
tela de sucesso para corrigir/reenviar. Confirmar zera o token, o que fecha os dois caminhos de uma
vez — verificado: depois de confirmado, a correção pelo token devolve 404.

As duas partes se reforçam: antes, o primeiro email para um talento novo só saía no convite de um
evento, semanas depois. Agora todo cadastro dispara um email na hora, e quando ele volta a fila
avisa em minutos.

Corrigir o email na ficha (ou pela tela de sucesso) **tira o endereço antigo da fila sozinho** —
`bounce_ops.clear_for_email` roda dentro de `update_talent_fields`, sem commit próprio, para não
gravar estado parcial no meio da edição.

**Riscos e pegadinhas.**
- `useMutation` disparada por `useEffect` no carregamento da página **trava em "pending"** com o
  double-mount do StrictMode: a chamada da primeira montagem resolve contra um observer já
  descartado, e o `useRef` de trava não salva. A confirmação virou `useQuery` (`enabled`, `retry:
  false`, `staleTime: Infinity`), que desduplica pela chave e sobrevive ao remonte. O verbo segue
  POST — confirmar consome o token, não é leitura idempotente. **Regra geral: efeito no load é
  query, não mutation.**
- `_salary_for_month` do 218 tem um irmão aqui: `pending_queue` ordena por definitivo-primeiro e
  recente-primeiro, direções opostas que **não cabem numa chave composta**. São dois `sorted`
  encadeados, apoiados na estabilidade do sort do Python.
- O palpite de domínio (`Você quis dizer gmail.com?`) existe nos **dois lados** — `verify_ops` e
  `lib/cadastro.ts`. É duplicação consciente: o backend precisa dela para o log/diagnóstico e o
  frontend para avisar antes do envio, e um import cruzado entre Python e TS não existe.
- Nunca bloquear envio por formato de email: `hotmail.con` passa em qualquer regex, e regex
  apertada rejeita endereço válido de gente real. Quem separa certo de errado é a confirmação — e,
  quando ela falha, a fila.

### 218 — Superadmin corrige/exclui faixa de salário; Usuários com filtros; telas desempilhadas
`main` · **2026-08-06** · sem migration

**Motivação.** Um salário foi digitado errado e registrado. O caminho existente — registrar um
salário novo por cima — corrige dali para a frente, mas **deixa a faixa errada no histórico e o
valor errado na planilha de pagamentos**: `_ensure_salary_payments` só recria os lançamentos
`nao_pago` **sem adiantamento**, então qualquer lançamento já pago ou com adiantamento fica
congelado no valor errado, para sempre, sem tela que o conserte. Junto vieram dois pedidos de UX:
a tela de Usuários "bagunçada, sem organização nem filtro", e várias telas empilhando tudo numa
coluna estreita num monitor largo.

**O que mudou — salário.**

`user_ops` ganhou três funções e uma passou a ser fonte única: **`_rechain_salary_history`**
recalcula os `end_date` de toda a cadeia (cada faixa termina onde a seguinte começa; a última fica
vigente), desempatando por `id` quando duas faixas compartilham a mesma `start_date` — que é
exatamente o caso de "errei e regravei no mesmo dia". `add_salary`, `update_salary` e
`delete_salary` chamam a mesma função, então nenhuma delas pode deixar duas faixas vigentes.

**`_resync_salary_payments`** realinha a planilha. Regra: lançamento `nao_pago` tem `amount` e
`salary_history_id` recalculados; lançamento **já pago / "no banco" só tem a FK reatada** — o valor
é registro do que saiu do caixa e não se reescreve. Os registros são atualizados **no lugar**,
nunca recriados, e é isso que preserva os adiantamentos (`SalaryAdvance`) — a regeneração do
`_ensure_salary_payments` os preservava se abstendo de tocar no registro, o que era justamente a
causa do valor congelado.

**Decisão não óbvia:** `_salary_for_month` resolve a faixa **por mês** (a de maior `start_date`
ativa no mês), espelhando `app/financeiro/routes.py::_ensure_salary_payments` em vez de resolver
por data de vencimento — que seria mais preciso. Se as duas regras divergissem, o próximo
carregamento da tela de Pagamentos desfaria o realinhamento.

Antes de excluir uma faixa, as referências em `salary_payments.salary_history_id` são zeradas: os
lançamentos já pagos apontam para ela e a FK barraria o `DELETE`. O `_resync` reata cada uma logo
em seguida.

**Endpoints novos (SUPERADMIN, não FINANCEIRO).** `PATCH` e `DELETE` em
`/api/admin/users/<uid>/salary/<sid>`, ambos devolvendo `payments_resynced` — a UI usa esse número
para dizer quantos lançamentos em aberto mudaram. Registrar salário continua SUPERADMIN **ou**
FINANCEIRO; **corrigir o passado** é só SUPERADMIN.

**O que mudou — telas.**

`/admin/usuarios` foi reescrita: busca por nome/email, três filtros combináveis (papel, situação,
frequência de pagamento) via `FilterDropdown`/`CheckboxList`, ordenação, quatro contadores e uma
**tabela** em vez de cards empilhados, com colunas caindo por breakpoint (papéis em `md`,
frequência em `lg`, PIX em `xl`). Os filtros de situação se somam como **E** ("ativo + sem PIX"
funciona como se lê); os de papel e frequência somam como **OU** dentro da própria categoria.

A "Folha do mês" replica a cadência do gerador de pagamentos (semanal × segundas-feiras do mês,
quinzenal × 2) e diz isso na própria legenda — não é uma média inventada.

Onze telas saíram de `max-w-lg/xl/2xl/3xl` em coluna única para largura de desktop com blocos lado
a lado (ficha e criação de usuário, configurações, logs — que viraram tabela —, desempenho,
clientes e ficha do cliente, revisão e espaço de revisão, catálogo admin e seu formulário, ficha de
figurino, configuração de preços). Formulário de evento **não** foi mexido: os blocos já usam
`sm:grid-cols-2` internamente e 3xl é largura correta para formulário longo.

**Riscos e pegadinhas.**
- Item de grid nasce com `min-width: auto`. Ao colocar as tabelas de preço dentro de um grid, o
  `overflow-x-auto` do `Table` parou de agir e a página estourou 14px no celular. Todo grid novo
  leva `[&>*]:min-w-0` — se aparecer rolagem horizontal numa tela nova, é esse o suspeito.
- `add_salary` agora também roda o `_resync`: registrar um salário novo passa a **corrigir** os
  lançamentos em aberto do mês, inclusive os que têm adiantamento. É mudança de comportamento
  silenciosa em relação ao que existia, e é a metade da correção que o usuário percebe primeiro.

**Achado de brinde — a planilha mostrava toda data um dia antes.** Investigando "o valor está
errado" apareceu que o vencimento também estava: a tela exibia **04/08** para um quinzenal que vence
em **05/08**, e segunda-feira de salário semanal caía num domingo. Causa: `new Date("2026-08-05")`
— data **pura**, sem hora — é interpretada como **UTC** pela especificação, e em São Paulo (UTC−3)
volta 21h do dia anterior. O comentário de `packages/ui/src/lib/date.ts` afirmava o contrário, o que
é verdade só para `"2026-08-05T20:00:00"`. `parse` passou a montar a data pura campo a campo em
horário local, e `PagamentosPage` (que tinha cópia própria de `formatDate`) passou a usar
`formatShortDate` da fonte única. **Qualquer tela que formate campo `date` puro estava errada pelo
mesmo motivo** — corrigir na fonte única conserta todas de uma vez. Ver também feature 210.

### 217 — Tema escuro com switch na sidebar, e reestruturação da documentação
`main` · **2026-08-06** · sem migration

**Motivação.** Duas frentes pedidas juntas. (1) Tema escuro "com as cores bem vivas" — fundo quase
preto com os acentos **saturados** por cima, não um cinza lavado. (2) Uma varredura de documentação
e clean code com objetivo declarado de **economia de token**: que a próxima pessoa (ou agente) leia
pouco e entenda rápido.

**O que mudou — tema.**

Os 35 tokens eram **hex fixo** em `tailwind-preset.ts`. Viraram **variável CSS** em
`frontend/packages/ui/src/theme.css`, com dois conjuntos de valores e `darkMode: "class"`. Os nomes
dos tokens não mudaram, então **nenhuma tela precisou trocar de classe** — é isso que tornou a
conversão viável em 189 arquivos.

Princípio que guia a paleta escura: sobre fundo escuro a mesma matiz precisa ficar **mais clara e
mais saturada** para continuar legível e parecer viva, e os fundos `soft` deixam de ser pastel claro
e viram **tinta escura da própria matiz**. Daí `accent` sair de `#544596` (claro) para `#a78bfa`
(escuro), e `green-soft` sair de `#d4edda` para `#10331f`.

Dois tokens novos nasceram da conversão: **`on-color`** (tinta sobre preenchimento saturado — no
escuro o acento clareia e o branco reprovaria AA) e **`gold-ink`**. Eles precisam existir também em
`apps/public/tailwind.config.ts`, que **não consome o preset**: o `content` do Tailwind inclui
`packages/ui/src`, então o `Button` do design system referencia o token mesmo no catálogo.

**Decisão da sidebar (não óbvia).** A sidebar é escura nos dois temas. No tema escuro ela
**clareia** (`#1f1a30` → `#2a2438`) em vez de escurecer: o fundo da página é `#121016`, e manter a
sidebar mais escura que a página a faria desaparecer. É o inverso da intuição.

**Animação.** `document.startViewTransition` com revelar **circular a partir do próprio botão** — a
origem sai do retângulo do botão, não do ponteiro, para que a troca por teclado nasça do mesmo
lugar. Sol e lua se cruzam girando, sobrepostos, para não empurrar o rótulo ao lado. 240ms, dentro
da faixa de 150–350ms do Princípio IX. Fallback de crossfade onde não há suporte, e troca
instantânea com `useReducedMotion()`.

**Preferência.** `localStorage` (chave `manto-tema`), com padrão vindo de `prefers-color-scheme` na
primeira visita. Um script **inline no `index.html`** carimba a classe no `<html>` antes do primeiro
paint — sem ele há flash do tema errado a cada carregamento. Escolhido em vez de gravar no `User`
justamente por isso: preferência vinda do servidor implica flash ou fetch bloqueante.

**Riscos e pegadinhas.**
- O Portal do Artista adotou o tema junto (compartilha o preset), e na primeira passada ganhou o
  tema escuro **sem interruptor** — quem tem o sistema no escuro ficaria preso nele. `ThemeSwitch`
  ganhou `tom="claro"` e `compacto` para caber no header claro do portal.
- `MemoriaDeCalculo.tsx` já usava `dark:` sem nenhum config declarar `darkMode`: com o padrão
  `media` do Tailwind essas linhas **já reagiam sozinhas** ao tema do sistema enquanto o resto da
  tela ficava claro. Adotar `darkMode: "class"` neutralizou o bug de brinde.
- `text-white` sobre preenchimento saturado **não** vira token automaticamente: sobre a sidebar,
  sobre foto e sobre o player continua correto nos dois temas. Só vira `on-color` onde o
  preenchimento clareia no escuro.

**O que mudou — documentação.**

`03_HISTORICO_MUTACOES.md` tinha **202 KB (~61k tokens, ~30% de uma janela de 200k)** e nenhum
índice: era preciso ler tudo para achar qualquer coisa. Virou **índice + as 12 entradas mais
recentes** (47 KB); o restante foi para `docs/historico/184-199.md` e `200-207.md`. **Nenhuma
entrada foi perdida** — 43 antes, 43 depois, conjuntos idênticos (o documento é append-only por
contrato).

Três documentos novos: **`00_MAPA_DO_SISTEMA.md`** (a porta de entrada que não existia — onde cada
domínio mora, tabela de papéis, e "qual arquivo ler para cada tipo de tarefa"),
**`04_GUIA_DE_DOMINIOS.md`** (fluxos, invariantes e armadilhas) e **`05_DIVIDA_TECNICA.md`**
(achados priorizados com arquivo:linha).

O achado estrutural mais grave da auditoria está no 05: **o núcleo do domínio de agenda não está em
nenhum `*_ops.py`** — 39 símbolos privados de `app/calendar/routes.py` (3.910 linhas) são importados
por 10 módulos, inclusive pelo próprio `event_ops.py`. Isso inverte a regra do CLAUDE.md e obriga a
carregar ~49k tokens para qualquer tarefa que toque evento.

### 216 — Cachê no portal, prévia de link no WhatsApp, contraste e endurecimento de segurança
`main` · **2026-08-05** · sem migration

**Motivação.** Cinco frentes pedidas de uma vez: (1) um artista relatou que o **valor do cachê não
aparecia** no portal; (2) link de catálogo compartilhado no WhatsApp saía **sem miniatura**; (3) ao
abrir uma avaliação já enviada, não dava para **ver o que tinha sido escrito**; (4) contraste da
agenda difícil de ler; (5) auditoria de segurança (vazamento, ataque, RBAC).

**O que mudou.**

*Cachê (backend + portal).* `_role_summary` (`app/talent_portal/portal_ops.py`) passou a serializar
`cache_value`, `travel_cache`, `cache_total`, `cache_defined` e `payment_status`. Antes o cachê era
enxertado **só** no laço de `history`, então `pending_invites` e `upcoming` saíam da API sem o campo
e a tela os omitia em silêncio — regressão em relação ao portal Jinja, que exibia o valor no convite
(`app/templates/portal/home.html:170`). Novo componente `CacheLine` é a fonte única das três telas;
`PortalConvitesPage`, que não tinha **nenhuma** referência a cachê, ganhou o valor em destaque.

*Prévia de link.* `frontend/server.js` injeta Open Graph no `index.html` da vitrine para página de
produto **e de tema** (`/catalogo/categoria/<slug>`), com miniatura reencodada por
`app/catalogo/og_ops.py` (teto de bytes — arquivo grande faz o WhatsApp entregar o link sem imagem).
A injeção só roda para **crawler de prévia**: visitante humano não ganha nada com meta tag e pagaria
a latência de uma ida ao Flask em cache frio.

*Avaliação.* O Histórico só linkava a avaliação enquanto a janela de edição de 30 dias estivesse
aberta. Depois disso a avaliação continuava existindo, o backend continuava servindo e a tela sabia
se apresentar em modo leitura — mas **nada apontava para lá**. Passou a usar `rated_event_ids` e
mostrar "Ver minha avaliação".

*Contraste e UX mobile.* Correções de razão WCAG nos chips de categoria da agenda e em textos
pequenos (`tailwind-preset.ts` e `apps/portal/tailwind.config.ts`); `text-xs` virou `text-sm` onde
carregava dado operacional. `/fotos-documentos` e `/termos` **não tinham link em lugar nenhum** —
o artista não conseguia enviar foto nem CNH pelo celular; agora saem do Perfil.

**Impacto em RBAC e segurança.**
- `/uploads/<path>` servia a árvore inteira só com `@login_required`: contrato, comprovante, nota
  fiscal e RG/CNH eram baixáveis por qualquer papel. Passou a despachar por subpasta com papel
  próprio; `expenses` é checado por **dono**, porque qualquer colaborador registra gasto.
- `/portal/photo/<path>` dava a qualquer talento logado alcance a todo o `UPLOAD_FOLDER`. Restrito
  às subpastas que o portal realmente usa.
- `GET /api/talents/<id>` devolvia CPF, RG, PIX e CNH a qualquer autenticado. Campos sensíveis
  passaram a ser redigidos por padrão (`include_sensitive=False`), preservando o shape do payload.
- Upload sem allowlist de extensão (XSS armazenado no mesmo origin): allowlists por finalidade em
  `app/storage.py`; o que não é seguro inline sai como anexo com `nosniff`.
- **Trava de e-mail por ambiente** (`MAIL_SUPPRESS_SEND`): a única trava era uma `SiteSetting`, que
  mora no banco — o espelho local herda ela ligada da produção e um processo de desenvolvimento
  conseguia escrever para o endereço real dos artistas. Confirmado na prática nesta rodada.

**Riscos e pegadinhas.**
- `.xml` de nota fiscal quase foi recusado: a allowlist inicial era imagem + PDF, mas quatro telas
  oferecem `.xml`. Existe `ALLOWED_INVOICE_EXTENSIONS` separada — e `.xml` **nunca** é inline.
- `.svg` saiu do logo: com `nosniff` + `Content-Disposition: attachment` o navegador se recusa a
  desenhá-lo; aceitá-lo produziria um logo invisível.
- A `og:image` **não pôde ser verificada localmente**: nenhuma das 458 capas ativas existe em
  `instance/uploads/catalog_photos` (o espelho do banco referencia arquivos que não foram baixados).
  O encoder foi verificado isolado (JPEG de 193 KB, dentro do teto). **Conferir em produção.**
- Ao criar fixture de teste local, não invente `character_name`: o sync do Google Calendar reconcilia
  o casting e **apaga** escalação com personagem inexistente — disparando e-mail de cancelamento.

### 215 — Tela de evento em abas, com edição inline e buscas visuais
`main` · **2026-08-05** · sem migration

**Motivação.** A tela `/events/:id` da feature 190 entrega **todos** os blocos de uma vez. Para o
`SUPERADMIN`, que recebe o payload inteiro, isso são **16 painéis** empilhados em duas colunas sem
hierarquia — e no mobile uma coluna só, interminável. Três defeitos concretos: (1) o mesmo
personagem aparece **duas vezes** (uma no *Casting*, outra no *Figurino*), dobrando a altura;
(2) nada na tela responde "o que falta neste evento?"; (3) para mudar título, data ou valor era
preciso **sair** para `/events/:id/edit` — uma tela que nem existia antes da migração React e que
edita exatamente o que a tela de detalhe já mostra.

**O que mudou.**

*Frontend.* `EventDetailPage` virou um **shell de abas** — Resumo · Produção · Comercial ·
Histórico — com a aba ativa na querystring (`?aba=`), régua sticky e rolagem horizontal no mobile.
A aba só é montada se o payload trouxe algum bloco dela, então o RBAC continua sendo do servidor.
Novos: `ResumoSection` (painel *Dados do evento* editável + `PendenciasStrip`), `TalentPicker` e
`FigurinoPicker`. `ComercialSection` ganhou os painéis *Clientes* e *Pré-contrato* e edição inline
dos valores. `CastingSection` trocou o `<select>` de talentos pelo `TalentPicker`;
`FigurinoSection` trocou o `<datalist>` pelo `FigurinoPicker`. O botão "Editar" saiu da barra do
cabeçalho e virou o item **"Editar tudo (formulário completo)"** no menu Ferramentas.
`ComboboxOption` (design system) ganhou o campo opcional `badge`, renderizado à direita da opção.

*Backend.* Cinco endpoints novos em `agenda.py`/`agenda_write.py`, com núcleo em `event_ops.py`
(`update_event_basics`, `update_event_comercial`, `set_event_clients`, `set_event_form_response`,
`assignable_talents_for_event`). `_serialize_talent` passou a incluir `photo_url`.

**Regras de negócio e RBAC.** Os quatro endpoints de escrita usam `_can_create_event()` — o mesmo
gate do `PATCH /api/events/<id>` (`COMERCIAL`/`SUPERADMIN`), porque cobrem os mesmos campos
sensíveis; mudar a data de um evento tem o peso de criá-lo. Nenhum gate foi afrouxado: quem já não
podia editar em bloco continua sem editar inline, com os painéis em leitura. `casting-options` é
leitura para qualquer autenticado, igual a `/api/talents`. `update_event_basics` mantém a
sincronização best-effort com o Google Agenda de `update_event_core` (falha vira aviso, não
bloqueio). Cortesia/permuta continua zerando a venda no servidor.

**Rotas e endpoints novos.**
- `GET /api/events/<id>/casting-options` — talentos ativos com `photo_url` e `availability`
  calculada contra a janela **deste** evento (uma consulta para todos, via `talent_availability`).
- `PATCH /api/events/<id>/basico` — título, tipo, data/horário, local, descrição.
- `PATCH /api/events/<id>/comercial` — valores, pagamento, vendedor, comissão.
- `PUT /api/events/<id>/clients` — substitui a lista (corpo é a lista inteira; `[]` desvincula).
- `PATCH /api/events/<id>/form-response` — vincula/desvincula o pré-contrato (409 se preso a
  outro evento — nunca roubamos o pré-contrato de outra venda).

**Riscos e pegadinhas.**
1. **Isolamento é a razão de existirem endpoints estreitos.** O `PATCH /api/events/<id>` da 184
   reescreve elenco e clientes junto: usá-lo para salvar só o horário destruiria escalas. Por isso
   cada função nova toca apenas o seu recorte — e o `verify_215` testa exatamente isso (elenco e
   clientes intactos depois de salvar cabeçalho e valores).
2. **Descrição é HTML do Google Agenda.** O textarea do Resumo mostra a versão em texto puro
   (`descriptionToText`), mas enviar essa conversão de volta achataria `<br>` e âncoras — e o
   achatamento iria para o Google no próximo sync. O formulário só manda o texto digitado se o
   usuário **realmente tocou** no campo; e `PATCH /basico` trata `description` **ausente** como
   "não mexa". Mesma armadilha que o hotfix 210 já tinha documentado para `/events/:id/edit`.
3. **Data/hora continuam sendo horário de parede.** O formulário inline usa `dataDeIsoLocal` /
   `horaDeIsoLocal` (recorte de string), nunca `Date` — o caminho que na 210 gravava +3h.
4. `?aba=` inexistente (link antigo, ou papel sem aquele bloco) cai no Resumo em vez de renderizar
   tela vazia. A troca de aba usa `replace` e **preserva os demais parâmetros** da URL.
5. `casting-options` tem chave por evento e sem `staleTime`: escalar alguém muda a agenda dos
   outros, e salvar data/hora invalida a lista (a disponibilidade é relativa à janela).

**Aviso de teto de cachê (mesma feature).** `EventRole.cache_cap` é gravado na criação quando o
evento vem da calculadora (`routes.py::_create_roles_from_input`, `cache_cap=cache_val if
from_orc`), e `assign_casting_role` **rebaixa** ao teto qualquer cachê maior salvo por não-
superadmin. O campo era serializado desde a 190 mas **nenhuma tela React o usava**: quem digitava
acima via "✓ Salvo" e o número voltava sozinho, sem explicação (a tela Jinja avisava; a migração
perdeu isso). Agora o card mostra o aviso — **sem nunca exibir o valor do teto**, por decisão de
produto — e reespelha o `cache_value` da resposta, para a tela não continuar exibindo o número
recusado. Só ~20% dos cargos têm cap (266/1353 no banco local): evento criado à mão não tem teto,
e aí nada muda.

**Verificação.** `scripts/db/verify_215_evento_abas_edicao_inline.py` contra `manto_local` —
49/49, incluindo o isolamento dos recortes, o 403 do casting no cabeçalho, o 409 do pré-contrato
alheio, a hora de parede preservada, o `conflict` aparecendo na busca de talento e o contrato do
teto (casting salvando 500 sobre cap 200 recebe 200 de volta na resposta e no banco; superadmin
ultrapassa).

### 214 — Hotfix: Revendedor EducaManto sem acesso a nada (calculadora incluída)
`main` · **2026-08-05** · sem migration

**Motivação.** Os dois usuários com o papel `REVENDEDOR_EDUCAMANTO` não conseguiam usar a
calculadora para vender. Na verdade **nada** funcionava para eles: até `/api/auth/me` falhava.

**Causa.** O `_revendedor_guard` (feature 078) roda em `before_request` e redireciona para
`/agenda` tudo que não estiver na allowlist de páginas — e `/api` nunca esteve nela, porque na
época o perfil só usava telas Jinja. Com a 206 tornando o React a interface primária, **toda**
chamada da SPA passou a levar 302. E o sintoma é mudo: o navegador segue o redirect, o servidor do
frontend responde `/agenda` com o `index.html` (status 200), e o `apiFetch` morre no `JSON.parse`
sem mensagem. Reproduzido com usuário real: 302 → `/agenda` em `auth/me`, `educamanto/packages`,
`educamanto/historico`, `agenda` e `educamanto/calcular`.

**O que mudou.** O guard passou a tratar `/api/*` separado: libera `/api/auth`, `/api/agenda`,
`/api/events` e `/api/educamanto` — o **espelho exato** das páginas que o perfil já podia abrir,
sem ampliar nada — e devolve **403 JSON** no resto, em vez de redirect. A allowlist de páginas
continua igual para as superfícies Jinja restantes.

No React, o revendedor passou a **entrar direto na Agenda**: a Home não é do perfil dele e o
servidor recusa os dados dela. Vale no login e em quem chega a `/` por favorito (`rotaInicial()` e
o componente de rota `HomeOuAgenda`, ambos apoiados em `isRevendedorOnly` no `useAuth`).

**Pegadinha.** Guard de navegação que responde **redirect** não serve para API: o cliente JSON
recebe HTML com 200 e falha em silêncio. Sempre que um `before_request` puder alcançar `/api/*`,
a resposta tem de ser status de erro com corpo JSON. Mesma família dos gaps de proxy da 206 —
o denominador comum é "HTML com 200 chegando onde se esperava JSON".

**Verificação.** `verify_214` 14/14 contra `manto_local`: as quatro rotas do perfil respondem 200
em JSON; a calculadora calcula de verdade (pacote real, 2 dias, transporte de 120 km); quatro
rotas fora do perfil devolvem 403 JSON (não 302); multi-perfil (revendedor + comercial) segue sem
restrição; e página Jinja fora do perfil continua redirecionando. Na tela, login do revendedor
cai em `/agenda`, o menu mostra só Agenda/EducaManto/Histórico e a calculadora devolve os valores
com a comissão.

### 213 — Acervo 3D: superadmin exclui peça já usada, desvinculando de todos os eventos
`main` · **2026-08-05** · sem migration

**Motivação.** Peça do Acervo já usada em evento não podia ser excluída de jeito nenhum — a
única saída era inativar. O dono do sistema precisa poder apagar de vez (peça duplicada,
cadastrada errada, arquivo trocado), assumindo que o presente some dos eventos.

**O que mudou.** `DELETE /api/3d/acervo/<id>` aceita `?force=true`: apaga os `Event3DGift`
daquela peça antes de removê-la. O padrão **não mudou** — sem `force`, peça em uso continua
recusada com a orientação de inativar, para o Artista 3D não apagar histórico sem querer. O
`force` exige **SUPERADMIN** (o gate normal do módulo, `require_3d_access`, também aceita
`ARTISTA_3D`, então há uma checagem extra no endpoint).

`delete_acervo_item(item, *, force=False)` faz a cascata explicitamente: nada no banco apagaria
os presentes sozinho (`Event3DGift.item_id` não tem `ondelete`), e é justamente por isso que a
exclusão era barrada. O `AuditLog` grava **de quantos eventos a peça foi desvinculada** — depois
não há como reconstruir.

**UX.** A confirmação virou uma caixa de seleção própria ("Excluir mesmo assim, removendo o
presente de todos os N evento(s) e da Fila de Impressão. Não dá para desfazer"), e o botão fica
**desabilitado** até ela ser marcada; o rótulo muda para "Excluir e desvincular". Não é um segundo
clique no mesmo botão de propósito — exclusão em cascata não pode acontecer por engano. Quem não
é superadmin continua vendo só a orientação de inativar.

**Riscos e pegadinhas.** O presente some da tela do evento **e** da Fila de Impressão, então o
hook invalida as duas caches. Nada mais no banco referencia `Event3DGift`, então não sobra órfão.
Verificação: `verify_213` 17/17 contra `manto_local` (peça sem uso segue simples; peça em uso
recusada sem `force` para os dois papéis; `force` do Artista 3D → 403 sem apagar nada; `force` do
superadmin → 204 com presentes removidos e auditoria contando os vínculos) e o fluxo completo
exercitado no navegador (checkbox habilita o botão, requisição sai com `?force=true`, peça some da
lista e o presente some do evento).

### 212 — Hotfix: diálogos abrindo pela metade, fora da tela
`main` · **2026-08-05** · sem migration

**Motivação.** "Em diversas páginas o pop-up fica pela metade e não consigo mexer": o diálogo
abria com o topo no meio da tela e a metade de baixo para fora, sem rolagem que alcançasse o
resto. Atingia **11 telas** — todas as que usam o `Dialog` do design system (Novo post de
marketing, detalhe de resposta de formulário, memória de cálculo do orçamento, gastos
recorrentes, fila e acervo 3D, comissões, histórico EducaManto, cabeçalho do evento…).

**Causa.** O painel do `DialogContent` era centralizado por `left-1/2 top-1/2` +
`-translate-x-1/2 -translate-y-1/2` (Tailwind) **e** era um `motion.div` animando `scale`/`y`. O
Framer Motion escreve `transform` no **estilo inline**, que vence as classes utilitárias — a
centralização evaporava e sobrava só `left: 50%; top: 50%`, ou seja, o **canto superior esquerdo**
do diálogo no centro da tela. Confirmado no DOM: `transform: translateY(8px) scale(0.96)`.

**O que mudou.** Centralização por **flex**, não por transform: o `Content` do Radix passou a
viver dentro de `fixed inset-0 overflow-y-auto` > `flex min-h-full items-center justify-center
p-4`. Diálogo curto centraliza; diálogo mais alto que a janela faz o **container rolar** em vez de
vazar pelo rodapé. O Framer Motion continua animando `opacity`/`scale`/`y` — agora o `transform`
serve só à animação, não ao layout. Fechar clicando fora segue funcionando: quem cuida disso é o
`onPointerDownOutside` do `Content` do Radix, não o overlay.

**Pegadinha (vale para todo componente animado).** Não centralize com `translate` de utilitário um
elemento cujo `transform` é animado — a biblioteca de animação sobrescreve. Use flex/grid no
container. O `Modal` de `apps/internal/src/components/Modal.tsx` já fazia certo (flex + `max-h`),
o que explica por que só os `Dialog` quebravam.

**Verificação.** No navegador, contra a cópia de produção: "Nova postagem" (1280×720) topo 57 /
base 679, dentro da tela e centralizado; detalhe de resposta do formulário topo 74 / base 662;
mobile 375×812 dentro das margens; e o caso estrutural — painel de 1099px numa janela de 420px:
o container rola (1177px) com topo **e** rodapé alcançáveis. Typecheck e build limpos nos três
apps.

### 211 — Vitrine: quadro da foto com teto e piso
`main` · **2026-08-05** · sem migration

**Motivação.** Na página do produto, o tamanho da foto mandava no layout inteiro. "Às de Copas"
(retrato alto e de arquivo grande) tomava a tela e **espremia a coluna do texto até virar uma
tira**: título quebrado em duas linhas, tags empilhadas uma por linha e botões virando bolinhas.
"80's Neon", com foto menor, ficava correto. Cada produto abria de um jeito.

**Duas causas, não uma.**

1. **Coluna espremida** — a culpa não era da altura, era da largura. O `grid-cols-[1.1fr_1fr]`
   parece garantir a proporção, mas item de grid nasce com `min-width: auto`: a coluna **não
   encolhe abaixo da largura natural do conteúdo**. Uma foto de arquivo grande empurrava a
   coluna da direita para fora da sua fração. `min-w-0` nas duas colunas devolve o controle ao
   `1.1fr/1fr` (medido depois: 568px / 516px, como esperado).
2. **Quadro sem limites** — a galeria só tinha teto (70vh) e nenhum piso, então retrato alto
   virava parede e paisagem larga virava tira. O palco agora vive numa faixa: piso de 380px,
   teto de `min(62vh, 620px)`. A foto continua inteira (`object-contain`), o que sobra é o fundo
   do quadro.

**Onde a garantia mora.** Teto e piso são **CSS** (`min-height`/`max-height`) no elemento do
palco, não só conta em JavaScript. Assim valem antes de a foto carregar, quando ela falha, e
depois de o usuário redimensionar a janela — a altura calculada no `onLoad` é um pixel fixo que
envelhece, e não havia listener de resize. O cálculo em JS continua, para o quadro já nascer no
tamanho certo em vez de crescer na frente do cliente.

**Pegadinha.** A altura do palco saiu do `animate` do Framer Motion e virou `style` + transição
CSS. Tamanho de quadro precisa valer no primeiro quadro renderizado; entregá-lo à biblioteca de
animação deixava o palco com 24px quando a imagem falhava.

**Verificação.** Typecheck e build limpos nos três apps; proporção das colunas e a faixa aplicada
(`min-height: 380px`, `max-height: 446.4px` numa janela de 720px) conferidas no DOM. A cópia
local não tem os arquivos de mídia (só o banco vem de produção), então a conferência visual com
fotos reais foi feita na página publicada.

### 210d — Hotfix: navegador preso no bundle antigo (e vínculo de ficha mais óbvio)
`main` · **2026-08-05** · sem migration

**Motivação.** Chegou o relato "não dá para vincular ficha depois de criado o personagem", com
print do painel de Personagens sem o botão. O botão **já estava em produção desde a 209** — o
print mostrava a versão da 207 (dava para saber pelo rótulo "sem vídeo", que a 209 removeu).

**Causa raiz — deploy que não chega no usuário.** O `serve-handler` não manda `Cache-Control`
nenhum. Sem esse cabeçalho, o navegador aplica **cache heurístico** em cima do `Last-Modified` e
guarda o `index.html` — que é justamente quem aponta para o bundle com hash. Resultado: o deploy
sobe, a sondagem em produção passa (o servidor entrega o arquivo novo para quem pede), e mesmo
assim o usuário continua rodando o JavaScript velho até dar refresh forçado. Isso vale para
**todo** deploy do frontend, não só este caso.

`frontend/server.js` passou a declarar o contrato padrão de SPA com assets versionados:
`Cache-Control: no-cache` para HTML (pode guardar, mas **revalida sempre**; o arquivo tem menos
de 1 KB e vira 304 quando nada mudou) e `public, max-age=31536000, immutable` para `assets/*`
(o hash está no nome, então conteúdo novo = URL nova). A regra de `assets` vem depois de
propósito: o `serve-handler` percorre a lista inteira e a última que casar vence.

**UX.** O selo "⚠ Sem ficha vinculada" virou botão — "⚠ Sem ficha vinculada — vincular" — e abre
o mesmo painel do botão "Ficha & página". É onde o olho bate ao procurar o que falta; deixar a
ação só atrás do outro botão dava a impressão de que não dava para vincular depois de criar.

**Riscos e pegadinhas.** "Verifiquei em produção" ≠ "o usuário está com isso": a sondagem busca o
bundle direto, o navegador dele não. Quando um relato descrever uma tela que não bate com o
código, procure um texto que só existe na versão antiga antes de sair caçando bug — foi o "sem
vídeo" que resolveu este. Verificação: `frontend/scripts/verify-proxy.mjs` ganhou a seção "Cache
do navegador" (HTML das 3 SPAs com `no-cache`, asset com `immutable`) — todos os checks OK; e o
vínculo de ficha foi exercitado de ponta a ponta no navegador (vincular pelo selo, gravar,
desvincular pelo ✕).

### 210c — Hotfix: Comercial voltou a enxergar o pagamento do evento
`main` · **2026-08-05** · sem migration

**Motivação.** O Comercial criava o evento e subia o comprovante, mas não via se a cliente já
havia pagado — sumiram o painel "Comprovantes de pagamento" (com o "Recebido X de Y" e o selo
"Quitado ✓") e o de "Reembolsos".

**Causa.** Na API, `data["pagamentos"]` e `data["reembolsos"]` foram colocados no bloco
`show_financeiro` (FINANCEIRO/SUPERADMIN). No Jinja os dois painéis ficavam dentro de
`{% if show_comercial %}` (`event_detail.html` 1982-2196) — quem vende sempre viu. Incoerência
visível: `reembolsos_pendentes_total` já ia para o Comercial, então ele lia "há R$ X pendente"
sem poder ver do que se tratava.

**O que mudou.** As duas chaves passaram para o bloco `show_comercial`. Nada mudou no React: os
painéis já apareciam por presença de chave (o servidor decide), e o `PagamentosPanel` já trazia o
"Recebido/Quitado", a lista e o formulário de novo comprovante.

**RBAC — o que NÃO mudou.** Subir comprovante e registrar/cobrar reembolso sempre foram
`_CAN_EDIT_EVENT` (inclui Comercial) nos endpoints; editar valor e excluir comprovante/reembolso
seguem restritos a SUPERADMIN, checados no endpoint e escondidos no React por
`flags.is_superadmin`. `kpi` e `gastos` (lucro, cachês, despesas) continuam só no bloco
financeiro — foi só isso que sobrou lá.

**Pegadinha.** Ao migrar um bloco do Jinja para a API, o gate tem de ser o do **template**, não o
do "parece financeiro". Verificação: seção 6 do verify_210 (43/43) com usuários de papel puro
(Comercial vê pagamentos e não vê KPI; Comercial sobe comprovante → 201, mas edita/exclui → 403;
Financeiro segue com tudo; Casting segue sem ver venda nem pagamentos) e conferência na tela com
"Ver o sistema como COMERCIAL".

### 210b — Hotfix: buscador de pré-contrato mudo
`main` · **2026-08-05** · sem migration

**Motivação.** O campo "Pré-contrato (formulário recebido)" de `/events/new` e
`/events/:id/edit` não devolvia nada para nenhum termo.

**Causa.** `FormResponsePicker` chamava `${API_BASE}/formularios/respostas/search` — a rota
**Jinja**, fora de `/api`. `frontend/server.js` só repassa ao Flask os prefixos de
`BACKEND_PREFIXES`, e `/formularios` não pode entrar lá: é rota do React Router (a tela de
Formulários). Resultado: a chamada caía no fallback da SPA e recebia o `index.html` **com status
200** — `r.ok` era verdadeiro, o `JSON.parse` estourava e o `.catch(() => setResults([]))`
transformava a falha em lista vazia. Ninguém via erro nenhum.

Antes da 206 isso funcionava porque `VITE_API_BASE_URL` apontava para o domínio do Flask e a
chamada não passava por proxy nenhum. Mesma família dos gaps de proxy da migração — e o único
caso restante: `/figurinos/<id>/print` e `/figurinos/print-event/<id>` já estavam cobertos por
`BACKEND_PATTERNS`, e uma varredura em `apps/*/src` não achou outra chamada fora de `/api`.

**O que mudou.** O componente passou a usar `apiFetch("/api/formularios/respostas/search")` — o
endpoint equivalente já existia em `app/api/formularios_admin_read.py`, sem tela que o usasse. A
lista agora mostra tipo · telefone · data do evento. Estados de **buscando**, **nenhuma resposta
encontrada** e **erro** substituíram o silêncio: a lição do bug é que "lista vazia" e "a chamada
falhou" não podem se parecer.

`formularios_ops.search_responses` ganhou **busca por data do evento** (`dd/mm/aaaa`, `dd/mm/aa`,
`dd-mm-aaaa`, ISO) — o campo prometia "nome, telefone ou data" e só fazia nome e telefone. O
casamento por telefone passou a exigir 4+ dígitos: com data no jogo, um "12" digitado no meio de
`12/08/2026` casava com meio banco de telefones.

**Riscos e pegadinhas.** Ao consumir rota do Flask a partir do React, use **sempre** `/api/*`.
Fora de `/api`, só com entrada explícita no proxy (`server.js` **e** os `vite.config.ts`), e por
regex restrito quando o prefixo colide com rota do React Router. Verificação: seção 5 do
verify_210 (30/30) e os quatro caminhos conferidos no navegador (nome, telefone, data e termo sem
resultado).

### 210 — Hotfix: horário deslocado, anexo do evento e orçamento sem saída
`main` · **2026-08-05** · sem migration

**Motivação.** Três regressões críticas apareceram junto quando a 206 tornou o React a interface
primária — todas em código que já existia, mas que só virou o caminho real dos usuários agora:
horários de eventos "mudando sozinhos", comprovante falhando sempre depois de criar o evento, e a
calculadora de orçamento sem a memória de cálculo nem a tela de apresentação da proposta.

**1. Horário deslocado +3h a cada edição (o mais grave).**
`start_at`/`end_at` são **horário de parede de São Paulo** — o banco guarda naive (ver
`service.py::parse_event_datetime`) e a API serializa com `.isoformat()`, sem fuso. O
`EventEditPage` hidratava o formulário com `new Date(iso).toISOString().slice(...)`: o `Date`
interpretava a string como horário local do navegador e o `toISOString` convertia para UTC,
abrindo todo evento com **+3h**. Salvar gravava o horário deslocado no banco **e empurrava para o
Google Agenda** — por isso os dois "concordavam" no valor errado e não havia divergência para
comparar. Em evento noturno (≥ 21h) a **data** também pulava um dia, e o fim virava madrugada do
dia seguinte pela regra da meia-noite do `_build_start_end`.

Correção em `lib/horaLocal.ts` (`dataDeIsoLocal`, `horaDeIsoLocal`, `hojeYmd`): para preencher
formulário e comparar datas, **recorta a string, nunca passa por `Date`**. `GastosExtrasPage` e
`GastosRecorrentesPage` usavam `new Date().toISOString().slice(0,10)` como "hoje" — depois das 21h
isso já dava o dia seguinte; passaram a usar `hojeYmd()`.

No mesmo `reset()`, `description` era hidratada com `""` enquanto o PATCH manda a descrição
inteira: **toda edição apagava a descrição do evento** (e a do Google Agenda), inclusive os blocos
com dados da contratante. Passou a hidratar `data.event.description`.

**2. Comprovante "sempre falhou" ao criar evento.** A fase 2 do `EventCreatePage` (anexos) usava
`useAddPayment(createdEventId ?? 0)`. `setCreatedEventId` só tem efeito no render seguinte e a fase
2 dispara ainda dentro do `onSuccess` da criação — o hook continuava preso em `0` e o upload ia
para `POST /api/events/0/payments` → 404. Determinístico: o evento nascia certo e **todo** anexo
falhava. "Tentar novamente" funcionava, porque aí o estado já tinha atualizado — o que fazia
parecer instabilidade de rede. Os uploads viraram funções soltas
(`enviarComprovante`/`enviarContrato`/`enviarReembolso`/`enviarObservacaoComFoto`), que recebem o
`eventId` por argumento; os hooks passaram a ser casca fina em volta delas.

**3. Memória de cálculo virou a mensagem de WhatsApp.** O diálogo "Ver memória de cálculo" mostrava
`quote.message`. O painel do Jinja (`orcamento/index.html` + `static/js/orcamento.js`) montava a
memória **no cliente**, duplicando a conta — motivo de ela ter se perdido na migração.
`quote_ops.calculate_quote` agora emite a memória junto com o cálculo (chave `memoria`), linha a
linha e na ordem em que cada parcela entra: cachê por profissional, coordenador, subtotal, markup,
brinde, adicional noturno, técnico, maquiador, transportes, acréscimos, NF e total. A verify prova
que a soma das parcelas fecha com os totais — a memória não pode "explicar" um número diferente do
cobrado. No orçamento personalizado a memória mostra só cachê-base × multiplicador (ou o valor
digitado), porque transporte/NF/acréscimo realmente não entram ali.

**4. "Gerar Orçamento" não levava a lugar nenhum.** Só salvava e o botão virava "Orçamento salvo".
Nova rota `/orcamento/:id` (`OrcamentoResultadoPage`), sucessora de
`app/templates/orcamento/resultado.html`: mensagem de WhatsApp copiável, resumo por duração,
detalhamento do transporte, memória de cálculo, baixar PDF e enviar por e-mail. O histórico ganhou
"Abrir orçamento" apontando para ela. Nenhum endpoint novo — `historico/<id>`, `/pdf` e
`/enviar-email` já existiam sem tela que os usasse.

**Rotas.** React: `/orcamento/:id` (declarada **depois** de `/orcamento/historico` e
`/orcamento/configuracoes`, senão `:id` casaria com elas). Backend: nenhuma nova; `quote.memoria`
é chave nova em `POST /api/orcamento/calcular` e no detalhe do histórico (orçamentos salvos antes
disso não têm a chave — o React trata como "memória não registrada").

**Riscos e pegadinhas.**
- Nenhum `Date` deve tocar em `start_at`/`end_at` para produzir valor de formulário. O bug
  sobreviveu meses porque `new Date(iso)` **exibe** certo para quem está em São Paulo — só quebra
  ao voltar para string via `toISOString()`.
- Os eventos editados enquanto o bug existiu ficaram com o horário deslocado nos dois lados (banco
  e Google), então não há como detectá-los por divergência. `scripts/db/relatorio_horarios_
  deslocados.py` lista os candidatos pelo log "Editou os dados do evento" e sugere o horário
  original, para conferência humana — não corrige nada sozinho.
- Ferramenta nova de desenvolvimento: `scripts/db/run-local-sem-google.py` sobe o Flask contra
  `manto_local` com `insert/update/delete_event` do Google dublados. Sem isso, reproduzir criação
  de evento no navegador cria lixo no calendário de produção.
- Verificação: `verify_210_horario_anexo_orcamento.py` 23/23 contra `manto_local` (round-trip do
  PATCH sem deslocar em evento noturno, descrição preservada, anexo com id real ✕ id 0, memória
  fechando com os totais, PDF e e-mail). Typecheck e build limpos nos três apps.

### 209 — Catálogo como espinha organizacional (página própria + fichas + busca)
`main` · **2026-08-05** · migration `e7a1c94f20b3` (*own_item_id em catalog_characters*)

**Motivação.** O catálogo deixa de ser só vitrine e vira o início da organização: tema com
elenco embaixo (Abba), personagem com ficha de figurino vinculada (métrica de cobertura),
personagem que TAMBÉM tem página própria e buscável (Coelho Branco dentro do tema Alice), e
variação de figurino como personagem separado (Gabby Boneco ✕ Humanizada — decisão do dono:
a Humanizada mantém página vendável na busca).

**Modelo.** `catalog_characters.own_item_id` (FK catalog_items, UNIQUE, SET NULL): o
personagem aponta para o item que É a página dele. Hierarquia de UM nível, de propósito —
tema com elenco não pode virar personagem de outro tema (validação em `set_own_item`/
`adopt_item_as_character`). O relacionamento `CatalogItem.characters` precisou de
`foreign_keys` explícito (dois FKs para a mesma tabela = AmbiguousForeignKeysError no boot).

**O que mudou.**

*Ops/API* — `catalog_character_ops`: `set_own_item`, `toggle_own_page` (checkbox "Página
única" = `is_active` do item vinculado; reversível, nunca apaga), `adopt_item_as_character`
(foto COPIADA da capa via `storage.copy_file`). Endpoints SUPERADMIN:
`POST /api/admin/catalogo/personagens/<id>/pagina-propria`, `.../pagina-unica`,
`POST /api/admin/catalogo/<tema_id>/adotar-item`.

*Vitrine* — `_character_summary` público ganhou `own_item_slug` (só quando a página está
ATIVA): o tile do elenco vira link para a página própria. Detalhe do item ganhou
`parte_de_tema` → selo "✦ Parte do tema Alice" com volta ao elenco. `_item_summary` da
grade ganhou `tags` e a busca client-side passou a incluí-las — "alice" acha o Coelho pela
tag, sem personagens poluindo os resultados.

*Admin* — `FigurinoSheetPicker` novo (busca realtime sem acento + thumb da ficha; fichas
com nome batendo com o personagem sobem ao topo) substitui os DOIS `<select>` cegos (painel
de personagens e vínculo rápido da árvore). Cada personagem ganhou o bloco "Ficha & página"
(picker + controles de página própria). Painel ganhou "Adotar item existente como
personagem". Listagem ganhou o termômetro `characters_com_ficha/characters_total` por tema
+ soma no topo, e o rótulo "página única — elenco de X" nos itens adotados.

**Riscos e pegadinhas.**

1. **Adoção COPIA a foto da capa** — nunca referencia (`delete_file` é chamado em 5 pontos
   sem saber de compartilhamento; mesmo racional do drag de foto da 207).
2. **Desligar a "página única" usa `is_active` do item** — o mesmo flag do gerenciador.
   Reativar o item pelo gerenciador religa a página do personagem (comportamento desejado:
   um flag só, sem estado paralelo).
3. **manto_local está atrás da produção** (o Abba da assistente não existe na cópia local).
   Rodar `refresh-local-db.ps1` antes do mutirão de organização.
4. Regra de modelagem registrada: versão de TEMA inteiro = temas separados (Alice Desenho ✕
   Live Action); variação de FIGURINO = personagens separados no mesmo tema (Gabby Boneco ✕
   Humanizada), cada um com sua ficha — a métrica de cobertura conta certo sozinha.

### 208 — Restauração do papel ENSAIO (dashboard + agendamento + presença)
`main` · **2026-08-05** · sem migration

**Motivação.** Incidente relatado pela equipe: a home do papel ENSAIO ficou vazia
("Tudo em dia!") após a 206. A auditoria mostrou que o papel perdeu TRÊS capacidades — o
dashboard inteiro (ensaios a agendar/agendados/órfãos + presença pendente), o
**agendamento de ensaios** (create/edit/delete/link eram rotas Jinja sem equivalente
`/api`) e a **atribuição do Técnico de Som (Presença)** (no React a vaga só era editável
por casting; no Jinja era tarefa do ensaio).

**O que mudou.**

*Backend* — `event_ops.py` ganhou o núcleo extraído das rotas Jinja: `create_ensaio`,
`update_ensaio`, `delete_ensaio`, `link_ensaio_to_show`, `assign_tech_presence`,
`build_ensaio_times` (regra da meia-noite preservada) e `resolve_ensaio_location`
(dependências de `routes` importadas só em runtime — sem ciclo de boot). Endpoints novos:
`POST /api/events/<id>/ensaios`, `PATCH/DELETE /api/ensaios/<id>`,
`POST /api/ensaios/<id>/vincular`, `POST /api/events/<id>/presenca` — todos gated por
`_CAN_ENSAIO` (Ensaio/Casting/Superadmin). `dashboard_service.compute_ensaio_tasks` +
seção `ensaio` no `/api/dashboard` (gate: ENSAIO ou superadmin, paridade com a home
Jinja). `serialize_event_detail` expõe `ensaios`, `presenca` e (em eventos ENSAIO)
`ensaio_pai`.

*Frontend* — `EnsaioSection` no detalhe do evento: no SHOW lista/agenda/cancela ensaios e
define a presença (select de talentos); no próprio ENSAIO mostra o pai (ou o estado órfão
com busca de show para vincular — reusa `useAgendaSearch`), edita horário e cancela.
Dashboard ganhou o painel "🎭 Ensaio" com as quatro listas.

**Riscos e pegadinhas.**

1. **A resposta do PATCH/DELETE de ensaio é o detalhe do SHOW pai** (a tela que o painel
   refaz). Na página do próprio ensaio isso corromperia o cache se fosse para
   `setQueryData(["event", ensaioId])` — os hooks da página do ensaio usam
   `invalidateQueries` em vez do write-through padrão.
2. **`verify_208` contra manto_local toca o Google Calendar REAL** (o token vive no banco
   copiado): o ensaio de teste é criado e excluído de verdade. Transitório, mas visível
   por segundos na agenda.
3. **Excluir um show cascateia para os ensaios filhos** — a limpeza de teste precisa
   limpar as tabelas satélite de TODOS os eventos antes de deletar qualquer um.
4. O gate do dashboard é ENSAIO/superadmin (como a home antiga); o gate de ESCRITA é
   `_CAN_ENSAIO` (inclui CASTING). São padrões diferentes de propósito — casting agenda
   ensaio pelo evento, mas não carrega o painel de pendências.
