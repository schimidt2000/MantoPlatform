# Contrato para a 349 e a 351

O que a 348 entrega para as features que rodam em paralelo. A versão normativa vai para `docs/01` (§ do CRM e da
Agenda); este arquivo é o rascunho de trabalho.

## Para a 349 ("Criar evento" na conversa)

- **Criar o evento ligado à conversa**: `POST /api/events` com `conversa_id` (e, se quiser, `frente`). O servidor grava
  `calendar_events.conversa_id` e congela `origem_contato_id` pela regra R7. Não grave as colunas à mão.
- **Núcleo, para quem cria por outro caminho**: `app.conversas.origem_ops.ligar_evento(evento, conversa_id)` — valida
  a conversa (levanta `ConversaNaoEncontrada`) e congela o contato. Não comita.
- **Orçamento aberto da conversa**: `orcamento_history.conversa_id` é gravado no primeiro envio pela conversa
  (`costura_ops.enviar_orcamento`). Para a calculadora que já nasce com a conversa, use
  `origem_ops.ligar_orcamento(entry, conversa)` (condicional: não troca a conversa de um orçamento já ligado).
- **Nunca** ligue venda à conversa pela ficha (`Client`): é o que mistura as vendas da cliente recorrente.

## Para a 351 (venda atribuída)

- **Frente do evento**: `app.calendar.frente_ops.frente_do_evento(evento) -> dict` (`frente`, `rotulo`, `definida`,
  `sugestao`, `sugestao_certa`) e `frente_ops.frente_sql()` (expressão SQLAlchemy, mesmo resultado). Satélite lê o
  principal (no SQL, filtre `group_leader_id IS NULL`, como o `_filtro_venda` da 345). `definida = False` quer dizer
  "regra do título" — dá para mostrar "N vendas com frente sugerida".
- **Origem da venda**: `calendar_events.origem_contato_id` → `conversa_anuncios` (tipo `anuncio` | `publicacao` |
  `site`; `anuncio_id`, `ctwa_clid`, `codigo_id`) → `anuncios_meta` (`campanha_id`, `conjunto_id`) ou
  `origem_codigos` (`gclid`, `campanha_id`, `utm_*`). Em Python: `origem_ops.origem_da_venda(evento)`.
- **Venda orgânica**: `conversa_id` preenchido e `origem_contato_id` nulo. **Sem conversa**: os dois nulos (venda
  que não passou pelo CRM, ou anterior a ele).
- **Lead × campanha**: `clients.utm_campaign_id` (id da campanha de origem) — case por ele; o nome
  (`utm_campaign`) só para ficha sem id.

## O que não muda

- `comando_ops.frente_venda_sql()` continua existindo e agora devolve `frente_ops.frente_sql()`: os números de 16/11
  ficam iguais para todo evento sem frente gravada.
- `ConversaAnuncio` continua com a chave UNIQUE da 334; o tipo `site` é novo e não entra em `aplicar_na_ficha` como
  anúncio da Meta (não mexe em `anuncio_origem_id`).
