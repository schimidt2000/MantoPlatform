# Pesquisa — 348 Origem completa

Fonte externa: relatório "Máquina de vendas Manto" (17/11/2026), seções 6.1–6.4 e 8.2, com as referências [72],
[120], [121], [124]–[131] dele. Fonte interna: código da `main` em `20bf93c0`.

## R1 — Onde guardar o `ctwa_clid`

- **Decisão**: coluna `ctwa_clid` em `conversa_anuncios`, preenchida em `anuncio_ops.contato_do_whatsapp` a partir de
  `referral.ctwa_clid`.
- **Por quê**: o contato pelo anúncio (334) já é um registro por clique (chave = wamid); o `ctwa_clid` é do clique, não
  da conversa nem do anúncio. A Conversions API pede o `ctwa_clid` por evento (pesquisa 6.2).
- **Alternativas**: coluna na conversa (perderia o segundo clique da mesma cliente); tabela própria (duplicaria a 334).

## R2 — Preenchimento retroativo

- **Decisão**: na própria migration, em Python, linha a linha: `conversa_anuncios` (canal WhatsApp, `ctwa_clid` nulo)
  junto de `conversa_mensagens` pela chave = `externo_id`; `json.loads` tolerante; só grava se `referral.ctwa_clid`
  for texto.
- **Por quê**: roda uma vez, no deploy; não depende do código do app (a migration não importa `app`). Em produção as
  tabelas estão vazias (CRM desligado), então é garantia, não carga. O SQL puro (`dados::json`) derrubaria a
  migration na primeira mensagem corrompida.
- **Alternativas**: varredura periódica (refaria para sempre as linhas sem `ctwa_clid`); comando de CLI (alguém teria
  de lembrar de rodar).

## R3 — Conjunto de anúncios

- **Decisão**: `fields=name,campaign{id,name},adset{id,name}` na consulta que já existe; colunas `conjunto_id` e
  `conjunto_nome` em `anuncios_meta`. A migration devolve à fila (`consultado_em = NULL`) os anúncios consultados com
  sucesso, para ganharem o conjunto uma vez.
- **Por quê**: o anúncio pertence a um conjunto; é a mesma chamada, sem custo novo de cota.

## R4 — O código do site

- **Decisão**: cinco caracteres do alfabeto `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (31 símbolos, sem 0/O/1/I/L);
  `UNIQUE` no banco e nova tentativa na colisão; formato na mensagem `#XXXXX`; leitura por regex
  `#([A-Z0-9]{5})\b`, sem diferenciar maiúscula, e validação no banco (existe, sem conversa, criado há ≤ 90 dias).
- **Por quê**: 31⁵ ≈ 28,6 milhões de códigos; com dezenas de cliques por dia a colisão é rara e o casamento por acaso
  com texto da cliente exige acertar um código vivo e livre. Curto para não parecer "coisa de sistema" na mensagem.
- **Alternativas**: código gerado no navegador (colisão sem árbitro; o servidor não teria os marcadores);
  UUID/hash longo (a pessoa estranha e apaga — a falha conhecida da técnica, pesquisa 6.3).

## R5 — Quando o código nasce

- **Decisão**: no carregamento da página com marcador na URL, sem bloquear: o app guarda os marcadores no
  `localStorage` (90 dias) e chama `POST /api/origem/codigo`; a resposta grava o código junto. O botão de WhatsApp lê
  o código guardado de forma síncrona (a lista de desejos abre com `window.open`, que o Safari bloqueia depois de um
  `await`). Sem código na hora do clique, a mensagem sai sem ele.
- **Por quê**: o clique vem antes da navegação; esperar o clique no botão para criar o código perderia o
  `window.open` no iPhone.
- **Alternativas**: criar no envio do formulário (resolve só o formulário); criar para toda visita (linhas inúteis).

## R6 — `gad_campaignid` e `utm_id`

- **Decisão**: o id da campanha do clique vem de `gad_campaignid` (o Google Ads acrescenta à URL final) e, na falta
  dele, de `utm_id`. Vai para `origem_codigos.campanha_id` e daí para `clients.utm_campaign_id`.
- **Por quê**: o `gclid` não diz a campanha sem consultar a API do Google; o parâmetro da URL diz.

## R7 — Escolha do contato de origem da venda

- **Decisão**: o `ConversaAnuncio` mais recente da conversa, com tipo `anuncio`, `publicacao` ou `site`, de `momento`
  entre (referência − 90 dias) e a referência; empate pelo maior id. Referência = o momento em que a venda é ligada
  (primeiro envio do orçamento; criação do evento com conversa). Congelado em `origem_contato_id`.
- **Por quê**: a conversa é uma por telefone; sem congelar, a segunda venda de uma cliente recorrente herdaria o
  primeiro anúncio (o defeito da pesquisa 8.2). 90 dias acompanha o Google e cobre o ciclo do corporativo.
- **Alternativas**: janela de 7 dias da Meta (perde o corporativo); "o primeiro contato da conversa" (é o que mistura
  as vendas); calcular na leitura (a 351 teria de repetir a regra e o resultado mudaria com contatos novos).

## R8 — Evento herda do orçamento

- **Decisão**: `origem_ops.acompanhar_orcamento(evento, antigo, novo)` — se o evento não tem conversa, ou a conversa
  e o contato do evento são exatamente os do orçamento antigo, eles passam a ser os do novo (ou nada, no desvínculo).
  Chamado na criação a partir do orçamento e em `set_event_orcamento`.
- **Por quê**: troca e desvínculo de orçamento levam junto o que veio dele, sem apagar a ligação feita pela conversa
  (349).

## R9 — A frente

- **Decisão**: `calendar_events.frente` com FK para `marketing_frentes.slug`; `frente_ops.sugestao(titulo, tipo)`
  devolve `(slug, certa)` com a regra de 16/11 (o "resto" é `festas` com `certa=False`); `frente_do_evento` devolve a
  gravada (`definida=True`) ou a sugestão; `frente_sql()` = `COALESCE(frente, <regra>)`. `comando_ops.frente_venda_sql`
  passa a devolver `frente_ops.frente_sql()`.
- **Por quê**: a FK impede valor fora da lista no banco; o `COALESCE` mantém os números de 16/11 para todo evento
  antigo e passa a respeitar a escolha nos novos.
- **Obrigatoriedade**: só na aba Comercial com o bundle novo (que manda a chave `frente`) e venda > 0 sem cortesia.
  A criação grava sozinha só a sugestão certa. Assim o PATCH em bloco, o Jinja e o bundle antigo seguem como estão.

## R10 — Lead × campanha pelo id

- **Decisão**: `_campaign_table` agrupa por `(platform, campaign_id)` com o nome da linha de `period_end` mais
  recente; a ficha com `utm_campaign_id` casa pelos grupos daquele id (a plataforma decide pelo `utm_source`, como
  hoje); sem id, pelo nome normalizado. `retornos_por_campanha` passa a agrupar por `campanha_id` e leva o id.
- **Por quê**: renomear campanha é comum (a nomenclatura da 7.8 da pesquisa vai renomear todas); o id não muda.
