# Programa de integração do funil — plano das ondas 2, 3 e 4

**Data**: 2026-09-01 · **Origem**: análise de integração de 31/08
(`specs/266-costuras-funil/analise-integracao.md`, §4 "O plano de ondas").

**Onde o programa está:**

| Onda | Feature | Estado em 01/09 |
|---|---|---|
| 1a — o lead aparece + tudo leva a tudo | **266** | em produção (31/08, migration `a1c7d3e59b02` — head) |
| 1b — integridade de vínculo + comissão que bate | **267** | em produção (01/09, sem migration) |
| — | **271** | hotfix em produção (01/09): a Home degrada por painel (`_bloco()`), corrida dos lançamentos recorrentes |
| fundação transversal | **272** — notificações internas | spec escrita em 01/09 (`specs/272-notificacoes-internas/spec.md`), em desenvolvimento; migration provisória `b7d2e4f1a9c3` com `down_revision = a1c7d3e59b02` |
| 2, 3, 4 | **273 a 291** (números provisórios) | **este documento** |

**Regra de leitura.** Este é o plano; a spec de cada feature nasce daqui e pode divergir — quando
divergir, **a spec vence** e este arquivo ganha uma nota na seção da feature dizendo o que mudou e
por quê. Os números 273+ são provisórios: o número definitivo se confere em `docs/03` na hora de
abrir a branch, nunca em `specs/`.

**Números medidos no `manto_local` em 01/09**, usados como corte e como pré-condição dos verifies
(quem abrir a spec re-mede no dump do dia):

| Fato | Medida |
|---|---|
| Orçamentos no histórico | 1.809 · 109 referenciados por evento (107 deles com `client_id` no evento) · **nenhum** referenciado por dois eventos · 0 com `event_date` fora do padrão ISO · ~1.700 de 2026 sem evento |
| Orçamentos EducaManto | 39 |
| Parcelas (`event_installments`) | **5**, em 2 eventos, **nenhuma recebida**, todas vencidas (R$ 157.940) |
| Comprovantes (`event_payments`) | 238 · **24 sem `amount`** |
| Eventos `pix_parcelado` sem nenhuma parcela datada | 76 |
| Eventos futuros vindos do Google com venda e sem orçamento | 9 |
| Clientes | 6.215 · 312 nomes repetidos em 1.257 fichas · 1.038 com e-mail |
| Respostas de formulário | 1.508 · 63 com nome/idade do aniversariante no JSON |
| Eventos vendidos e realizados em 2026 | 123 · 30 com token de avaliação gerado · **13** com avaliação respondida |

A leitura que decide a onda 3: **o cronograma de parcelas quase não existe e o dinheiro real está
nos comprovantes.** Uma onda 3 centrada só em parcela mostraria quase nada no primeiro dia.

---

## 1. Princípios do programa

1. **Uma verdade por fato.** Status derivado da FK que já existe — orçamento "ganho" =
   `CalendarEvent.orcamento_history_id` (`app/models.py:324`) de evento não cancelado; resposta
   "ganha" = `FormResponse.event_id`; parcela "recebida" = `payment_id` apontando para o
   comprovante. Só a decisão humana que o banco não consegue deduzir ganha coluna (`lost_at`,
   `archived_at`, `feedback_requested_at`).
2. **Um número, uma função.** Saldo, vencimento e recebido saem de `entradas_ops` (284); status do
   orçamento de `quote_ops.status_do_orcamento` (275); contadores de resposta de `count_status`
   (`formularios_ops.py:154`, desde a 266). Telas consomem, nunca recalculam. Se duas telas
   discordam, o defeito é de fonte, não de tela.
3. **Nenhum e-mail novo para a equipe.** Tudo que "avisa" passa pela 272 (`notificacoes_ops.emitir`,
   `dedupe_key` UNIQUE) e leva a mensagem de WhatsApp pronta quando o destinatário final é a
   cliente — a cliente continua sendo cobrada e convidada por uma pessoa. Nenhuma feature deste
   programa cria thread de e-mail.
4. **Migration só aditiva ou afrouxando `NOT NULL`, uma por feature, ensaiada no dump do dia**
   (`flask db upgrade && python seed.py` num banco descartável — receita da 235/266; nunca
   autogenerate, memória `manto_alembic_drift_autogenerate`). Oito no programa inteiro (274, 275,
   276, 279, 281, 283, 286, 287 — ver tabela). Nada de `ALTER TYPE`, nada de `DROP COLUMN`.
   **Migration nunca falha de propósito**: o `startCommand` é `flask db upgrade && … gunicorn`
   (`render.yaml:22`) — um `raise` dentro do `upgrade` é loop de 502 até alguém corrigir dado à
   mão (memória `manto_startcommand_derruba_producao`). Checagem de dado roda como oneoff **antes**
   do merge, contra a produção (SSH no Render), e a migration, se encontrar o que a checagem não
   previu, **pula o passo e loga** em vez de estourar. Só uma branch com migration aberta por vez;
   `flask db heads` **no dia do merge**, com o `down_revision` ajustado no rebase — dois heads
   derrubam o `upgrade` do mesmo jeito.
5. **Toda FK nova para `clients` ou `form_responses` entra junto com o `delete_*` que a anula**
   (`client_ops.delete_client`, `client_ops.py:238`; `formularios_ops.delete_response`, `:323`). A
   266 pagou `IntegrityError` numa relação sem backref; não repetir.
6. **Relógio canônico `now_sp()`** (`app/constants.py:257`) em toda regra nova, e cada feature
   conserta o `date.today()` que encontrar no seu caminho: `agenda_read.py:405` (283),
   `dashboard_service.py:22` e `:552` (284), `ClientsListPage.tsx:72` (280). **Dois relógios no
   banco** (docs/04 §1 inv. 3): `created_at` de `OrcamentoHistory` (`models.py:1481`) e de
   `EventPayment` (`:673`) são `utcnow` naive; toda comparação deles com `now_sp()` ou com uma
   constante `ATIVACAO` em SP passa por `utc_para_sp(dt)` (nasce em `app/constants.py` na 275, ao
   lado de `now_sp`) — sem isso, 3 h de deslocamento nas bordas de dia (275 `dias_em_aberto`, 285
   comprovantes avulsos, 288 corte de ativação). Coluna nova é sempre naive SP.
7. **Escrita de evento devolve o `EventoDetalhe` inteiro** e passa por `useEventMutation`
   (`lib/eventDetail.ts:14-21`); mutação que toca recebimento chama `invalidarFinanceiro()`
   (`lib/financeiro.ts:300` — hoje **não exportada**; a 283 exporta) e invalida `["dashboard"]`.
8. **RBAC por função no início da view, no gate do vizinho.** `_can_manage_sale`
   (`agenda_write.py:53`) para dinheiro do evento; `_require_vendas` do módulo para
   clientes/orçamento/formulários. Nenhum gate novo. Regra para quem junta as duas metades
   (docs/05 §3.5): **o que entra no payload do dashboard segue o gate do dashboard (respeita "Ver
   como"); o que entra em tela de módulo segue o gate do módulo (ignora)** — e o verify de cada
   feature que cruza módulos testa SUPERADMIN em "Ver como CASTING" nos dois lados e registra.
9. **Blocos da Home são só leitura.** A geração preguiçosa da 271 mostrou que "criar se não
   existir" dentro do `GET /api/dashboard` é corrida entre workers. Nenhum bloco novo escreve;
   quem cria (notificação, pedido, reativação) é a rotina com claim (286).
10. **Idempotência é restrição de banco** (docs/00 §6 item 10): `UNIQUE(user_id, dedupe_key)` da
    272 para avisos, `UNIQUE` em `payment_id` para baixa, claim por `UPDATE` condicional em coluna
    de `site_settings` para rotina (molde `invite_reminders._claim_rodada`,
    `app/calendar/invite_reminders.py:130`).
11. **Toda rotina e toda fila nascem com corte por data de ativação documentado** (constante
    `ATIVACAO` no módulo) e com um script oneoff dry-run que lista o passivo herdado — 1.700
    orçamentos abertos, 5 parcelas vencidas de 2025, ~93 eventos sem pedido de avaliação. O passivo
    é tratado por filtro de tela e por passada humana, nunca por robô. Foi o ruído que matou o
    e-mail; o sino não pode nascer com o mesmo defeito.
12. **`verify_<nnn>.py` antes do código**, contra o `manto_local`, com escrita conferida por conexão
    separada (lição do 257), limpeza total ao fim e `FLASK_ENV=development` (memória
    `manto_create_app_threads_scripts` — o espelho traz credenciais reais). **Verify que cria,
    edita ou cancela evento dubla o Google** antes da primeira requisição: troca
    `insert_event`/`update_event`/`delete_event` em **`app.calendar.service` e em
    `app.calendar.routes`** (o `api_create_event` faz `from app.calendar.routes import
    insert_event` tardio, `agenda_write.py:729` — é a lacuna do `run-local-sem-google.py` que a
    baixa da 236 registrou em docs/05) e falha se algum evento criado ficar com `google_event_id`
    que não comece com `fake-local-`. Vale para 273, 278, 279 e 287; a memória
    `manto_local_escreve_em_servicos_reais` é o motivo.
13. **Deploy = ~45-60 s de 502.** Publicar fora do horário; features prontas juntas sobem no mesmo
    deploy (como 265+266), mas cada uma com branch, spec e verify próprios.
14. **Documentação ao fim de cada onda**: além de `docs/01/02/03`, aplicar o que a análise §6
    ainda deixou pendente — o item 3 inteiro, que são três armadilhas de `docs/04` §1 já
    resolvidas e ainda listadas: `docs/04:142-146` ("`update_event_core` não chama a
    sincronização" — a 267 injetou `sincronizar_comissao`, `event_ops.py:624,703`), `:147-148`
    ("agrupar/desagrupar só no Jinja" — a 246 pôs `api_desagrupar_evento`, `agenda_write.py:1980`)
    e `:149-151` (parcelas, acréscimos e notas "só escrita no Jinja" — a 253 pôs na API e a 282
    fecha o assunto). Corrigir também a contagem de threads em `docs/00:32` e `docs/04:426` quando
    a 286 acrescentar a oitava. Os itens 1 e 2 do §6 já foram aplicados na 266.

---

## 2. Tabela-resumo

| Onda | Código | Título | Tamanho | Migration | Depende de |
|---|---|---|---|---|---|
| 2 | 273 | Vincular orçamento a evento já criado (inclusive do Google), com opção de aplicar valores | P | não | — |
| 2 | 274 | Orçamento com cliente e origem: FKs `client_id`/`form_response_id`, card na ficha, cliente na calculadora | M | **sim** (#1) | — |
| 2 | 275 | Desfecho do orçamento: ganho derivado, perdido explícito, follow-up por negociação | P | **sim** (#2) | 273, 274 |
| 2 | 276 | Resposta arquivada: o lead que morreu sem orçamento sai da fila sem ser apagado | P | **sim** (#3) | — |
| 2 | 277 | Da resposta ao orçamento: "Fazer orçamento" e prefill da calculadora | P | não | 274 |
| 2 | 278 | Prefills completos do evento: do orçamento (fim, vendedor, cliente, resposta) e da resposta (local, hora, cliente a criar) | M | não | 274, 277 |
| 2 | 279 | EducaManto → evento: cliente no orçamento e "Criar evento" | M | **sim** (#4) | — |
| 2 | 280 | Ficha da cliente que diz a verdade: nome/telefone/e-mail/notas editáveis, avaliações por vínculo, KPI no relógio certo | P | não | — |
| 2→3 | 281 | Preferências de notificação por `kind` (silenciar) — pré-requisito da 272 para a onda 3 | P | **sim** (#5) | 272 |
| 3 | 282 | Cronograma de parcelas editável: reconciliação por id, "Gerar N parcelas" | P | não | — |
| 3 | 283 | Baixa de parcela ligada ao comprovante; comprovante sem arquivo; gate e `amount` corrigidos de carona | M | **sim** (#6) | 282 |
| 3 | 284 | `entradas_ops`: um saldo só para Home, evento e Financeiro; faixas D-3/D0/D+3 sem robô | M | não | 283 |
| 3 | 285 | Aba "Entradas" na Planilha de Pagamentos (parcelas, saldos, comprovantes avulsos, reembolsos a cobrar) | M | não | 284 |
| 3 | 286 | Rotina diária do funil (uma thread, claim) + produtor `parcela.vence` na 272 | M | **sim** (#7) | 272, 281, 284 |
| 4 | 287 | Pedido de avaliação com rastro + fila na Home + produtor `avaliacao.pedido_pendente` | P | **sim** (#8) | 286 |
| 4 | 288 | Follow-up de orçamento aberto por negociação: produtor `orcamento.followup` | P | não | 275, 286 |
| 4 | 289 | Reativação por aniversário da criança: lista em `/clientes` + produtor `aniversario.crianca` | M | não | 286 |
| 4 | 290 | Mesclar clientes duplicadas, com detector e verify por catálogo do Postgres | M | não | 274, 279, 280 |
| 4 | 291 | Busca global ⌘K federando as buscas que já existem | M | não | — |

Oito migrations, todas aditivas ou afrouxando `NOT NULL`. A cadeia de `down_revision` começa em
`b7d2e4f1a9c3` (272) — **a 272 precisa estar mergeada antes da primeira migration deste programa
(274)**, ou as duas disputam o head.

---

## 3. Onda 2 — fundação do funil

**Objetivo.** O orçamento deixa de ser um PDF por usuário e vira o registro do funil: sabe de quem
é (cliente), de onde veio (resposta) e como terminou (ganho derivado do evento, perdido
explícito). A resposta ganha desfecho — derivado quando virou orçamento ou evento, arquivado quando
morreu antes disso. O evento importado do Google aceita vínculo (e valores) depois de nascer. Os
três prefills param de fazer a comercial redigitar. E a ficha da cliente para de mentir. Nada aqui
emite notificação nova: esta onda cria as colunas que as ondas 3 e 4 vão ler.

### 273 — Vincular orçamento a evento já criado (inclusive importado do Google)

> **Implementada em 02/09/2026 com escopo maior** — vale `specs/273-orcamento-para-evento/spec.md`.
> Além do vínculo e dos valores, aplica a **equipe vendida** (coordenadores × quantidade, Técnico de
> Som, Maquiador, maquiagem/teto por personagem casado pelo nome) e o **"fora de SP"** do orçamento,
> porque foi isso que o dono pediu ("se vendeu maquiagem, tem que aparecer quem tem maquiagem"). O
> corpo usa `aplicar_valores_duracao` (não `aplicar_duracao`) e `aplicar_equipe`; a `relationship`
> reversa não entrou (o histórico faz um `SELECT` por página) e o `ensure_event_client` espera o
> `client_id` da 274. O `DELETE` responde 409 como a D14 previa. O texto abaixo é o plano original.


**Problema.** `CalendarEvent.orcamento_history_id` (`app/models.py:324`) só é gravado na criação
(`agenda_write.py:686`); o `PATCH` em bloco exclui o campo explicitamente (`agenda_write.py:767`) e
não há endpoint estreito. A aba Comercial só mostra "Ver orçamento" quando o vínculo existe
(`ComercialSection.tsx:574-576`). O evento que nasce no Google Calendar — o caminho comum de quem
marca a data no celular e orça depois (`source='google_calendar'`, `models.py:300`) — entra mudo:
sem venda, sem cliente e sem como apontar o orçamento que fechou. Hoje são **9 eventos futuros com
venda e sem orçamento**. Sem esse vínculo, nenhum orçamento pode ser considerado "ganho" (275).

**Escopo.**
- `PATCH /api/events/<id>/orcamento` com corpo
  `{orcamento_history_id: int|null, aplicar_duracao?: 1|2|3|4|"custom"}` em `agenda_write.py`,
  espelhando `PATCH /events/<id>/form-response` (`agenda_write.py:1009`): gate `_can_manage_sale`
  (`:53`), 409 + `leader_id` para satélite (paridade com `api_set_parcelas`, `:1199`), 409 com o
  `event_id` vencedor quando o orçamento já está preso a outro evento **não cancelado**, `null`
  desvincula. Devolve o `EventoDetalhe` inteiro.
- Núcleo `event_ops.set_event_orcamento(event, entry, *, duracao=None)` sem commit. Com
  `aplicar_duracao`, aplica `sale_value`/`sale_value_gross`/`transport_value`/`with_invoice` a
  partir dos totais de `_build_orcamento_prefill` (`app/calendar/routes.py:3101`), preenche
  `sale_date` com o `sale_date?` opcional do corpo ou com `now_sp().date()` se estava vazio (D1b:
  o evento do Google vendido meses atrás cai no ciclo de comissão do mês certo, docs/04 §2 ramo
  7, e não no mês corrente) e **sincroniza comissão por injeção** — o
  mesmo mecanismo que a 267 pôs em `update_event_core` (`event_ops.py:617`). Sem `aplicar_duracao`,
  o vínculo é só rastro. Se o orçamento tem `client_id` (274) e o evento não tem cliente, chama
  `ensure_event_client` (`formularios_ops.py:185`) — decisão 13 da 266.
- `OrcamentoHistory.events = db.relationship("CalendarEvent", backref="orcamento",
  foreign_keys="CalendarEvent.orcamento_history_id")` para a leitura reversa sem N+1 (sem migration).
  **Efeito colateral que a relationship traz**: hoje `DELETE /api/orcamento/historico/<id>`
  (`orcamento_write.py:108-122`) é `db.session.delete(entry)` cru, e a FK não tem `ondelete`
  (`models.py:324`) — apagar um dos 109 orçamentos referenciados estoura `IntegrityError`. Com a
  relationship, o SQLAlchemy passa a **anular o FK do evento em silêncio** e o "ganho" da 275
  evapora sem rastro. Decisão (D14): o `DELETE` recusa com **409 + `event_id`** quando há evento
  não cancelado apontando; com só eventos cancelados, desvincula com `audit()` e apaga. Sem
  `passive_deletes`, sem cascata.
- `_entry_summary` (`orcamento_read.py:112`) devolve `event_id`/`event_title` do evento vivo, e a
  linha do histórico ganha "Ver evento" — o selo de convertido mais barato possível.
- Aba Comercial: onde há só o link, um `OrcamentoPicker` (busca em
  `GET /api/orcamento/historico?q=`, que já filtra por nome/local — `orcamento_read.py:154-155`)
  com "Vincular" / "Trocar" / "Desvincular", no padrão visual do `FormResponsePicker`
  (`ComercialSection.tsx:21,501`). Ao vincular, escolha opcional da duração com prévia dos valores
  que vão ser aplicados; badge "Importado do Google, sem venda" quando `source='google_calendar'`
  e `sale_value` nulo.
- Resultado e histórico do orçamento: "Vincular a evento existente" → seletor por data reusando o
  seletor de evento do dia de `/formularios` (`useGastosEventos`, `FormulariosAdminPage.tsx:26,421`).

**Fora de escopo.** Status ganho/perdido (275) · recalcular cachês do elenco a partir do orçamento
(o evento já tem elenco pelo título) · EducaManto (279) · mudar título/tipo do evento.

**Modelo de dados / migration.** Nenhuma. A garantia de banco do 1:1 (índice único parcial) entra
na migration da 274 — ver lá.

**Endpoints.** `PATCH /api/events/<id>/orcamento` (novo; corpo ganha `sale_date?`) ·
`GET /api/orcamento/historico` — `_entry_summary` ganha `event_id`, `event_title` ·
`DELETE /api/orcamento/historico/<id>` — 409 `{event_id}` quando vinculado a evento vivo (D14) ·
`GET /api/events/<id>` — bloco `venda` ganha `orcamento_titulo` (cliente + data) e `source`.

**UI.** `components/EventDetail/ComercialSection.tsx` (picker, prévia de duração, estados
vazio/carregando/erro/409 "já vinculado ao evento X") · `pages/OrcamentoHistoricoPage.tsx` e
`OrcamentoResultadoPage.tsx` ("Ver evento" / "Vincular a evento existente") · mobile: o picker
cabe no card (`[&>*]:min-w-0`).

**Reusa.** `agenda_write.py:1009` (molde de endpoint estreito + 409) · `lib/eventDetail.ts:14`
(`useEventMutation`) · `components/FormResponsePicker.tsx` · `routes.py:3101`
(`_build_orcamento_prefill`, totais por duração) · sincronização de comissão por injeção (267) ·
`agenda_read.py:892-907` (quem pode abrir o orçamento vinculado — superadmin qualquer; comercial só
o próprio).

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- Histórico é por dono (`_get_entry_or_none`, `orcamento_read.py:204`): o picker lista o que o
  endpoint devolve — uma comercial não acha orçamento de outra; superadmin acha tudo. Registrado
  na spec como comportamento do módulo. *Verify:* COMERCIAL não-dono → 404 no vínculo.
- Aplicar valores dispara comissão e muda o Dashboard Comercial do mês de `sale_date`. *Verify:*
  evento do Google sem venda + `aplicar_duracao: 2` → `sale_value` = `total_2h`, `with_invoice` do
  snapshot, `CommissionPayment` nasce pela regra canônica, `sale_date` = hoje SP sem `sale_date`
  no corpo e = o informado com ele (conexão separada).
- Apagar o orçamento vinculado. *Verify:* `DELETE` do histórico com evento vivo → 409 + `event_id`,
  FK intacta; com o evento cancelado → 204, `orcamento_history_id` nulo e `AuditLog` (o teste que
  hoje estoura `IntegrityError`).
- Um orçamento, N eventos? Decisão: 1:1 com eventos não cancelados; cancelado (224) libera.
  *Verify:* segundo evento ativo → 409 com `event_id`; cancelar o primeiro → o segundo vincula.
- *Verify também:* `null` desvincula e o histórico deixa de listar `event_id` sem apagar a venda ·
  sem `aplicar_duracao` só o FK muda · cliente do orçamento entra em `event_clients` como
  Contratante quando o evento não tinha cliente, e não duplica quando tinha · satélite → 409 +
  `leader_id` · CASTING → 403 · excluir o evento deixa o orçamento sem `event_id` · na tela: evento
  do Google → vincular com duração → valores aparecem sem refetch manual.

**Dependências.** Nenhuma (o `client_id` da 274 é opcional aqui).

### 274 — Orçamento com cliente e origem (FK para `clients` e `form_responses`) + card "Orçamentos" na ficha

**Problema.** `OrcamentoHistory.client_name` é texto livre (`app/models.py:1481`); a calculadora
oferece um `<Input>` solto (`OrcamentoCalculadoraPage.tsx:362-363`), o histórico exibe "Sem
cliente" (`OrcamentoHistoricoPage.tsx:243`), `save_quote_history` grava o que veio
(`quote_ops.py:568`). Nada liga o orçamento à ficha nem à resposta que o motivou; a ficha
(`clientes_read.py:66-106`) mostra eventos e formulários, não orçamentos; a resposta
(`formularios_admin_read.py:100`) não sabe se virou orçamento. A busca do histórico é `ilike` em
nome: a mesma cliente com grafia diferente vira duas pessoas.

**Escopo.**
- Migration #1: `orcamento_history.client_id` (FK `clients`, nullable, índice, `ondelete SET
  NULL`) e `orcamento_history.form_response_id` (FK `form_responses`, nullable, índice, `SET
  NULL`). **Backfill só por FK**: `client_id` = `calendar_events.client_id` do evento que referencia
  o orçamento (107 linhas medidas) — nunca por nome (nome não é identidade neste CRM, telefone é).
  O `UPDATE` usa **subquery correlacionada** (`SET client_id = (SELECT client_id FROM
  calendar_events WHERE orcamento_history_id = orcamento_history.id AND cancelled_at IS NULL
  ORDER BY id LIMIT 1)`), não `UPDATE … FROM` — portável para o SQLite do ensaio e determinístico
  se a produção tiver o que o espelho não tem: um orçamento apontado por dois eventos com clientes
  diferentes.
- Na mesma migration, a garantia de banco do 1:1 da 273: índice único parcial
  `uq_calendar_events_orcamento_vivo ON calendar_events (orcamento_history_id) WHERE
  orcamento_history_id IS NOT NULL AND cancelled_at IS NULL`. Só Postgres (`postgresql_where`);
  em SQLite `sqlite_where` — a constituição já manda rodar no `manto_local`. **Falha-segura**
  (princípio 4): `scripts/oneoff/checar_orcamento_duplicado_274.py` lista os pares (orçamento em
  dois eventos vivos; orçamento em dois eventos com `client_id` diferente) e roda contra a
  produção por SSH **antes** do merge; na migration, se ainda houver duplicata, o `CREATE INDEX`
  é **pulado com log** (`conn.execute` + `print`, molde das 5 migrations que já consultam) e entra
  numa migration seguinte depois da limpeza humana — nunca `raise` dentro do `upgrade`.
- `save_quote_history` aceita `client_id` e `form_response_id`; `client_name` continua como
  snapshot de exibição (PDF e mensagem não mudam — `quote_ops.py:414-418,517`) e passa a ser
  preenchido a partir da ficha quando há FK.
- Calculadora: o campo "Cliente" vira `Combobox` do `@manto/ui` (`combobox.tsx:92`) sobre
  `useClientSearch`/`useQuickCreateClient` (`lib/clientes.ts:75,121`); escolher preenche
  `client_id` + `client_name`; digitar livre continua permitido (lead sem ficha) e deixa
  `client_id` nulo, visível como "sem ficha". O combobox **não** dispara recálculo (a calculadora é
  "request por tecla", memória `manto_deploys_janela_502`).
- Histórico: `?client_id=` e badge do cliente com link para a ficha.
- Ficha: card "Orçamentos" (data, total 4h, vendedor, status quando a 275 existir); o link "Ver"
  só renderiza quando o payload diz que pode (`_require_vendas` do orçamento é `{COMERCIAL,
  SUPERADMIN}`, `orcamento_read.py:30`, e o de clientes inclui FINANCEIRO, `clientes_read.py:24` —
  docs/05 §3.4).
- Detalhe da resposta: seção "Orçamentos desta resposta".
- `delete_client` (`client_ops.py:238`) e `delete_response` (`formularios_ops.py:323`) anulam as
  duas FKs explicitamente, mesmo com `SET NULL` no banco (princípio 5). Não é para a exclusão não
  falhar — com `SET NULL` o Postgres anula sozinho, como já faz com `nfc_tags.client_id`
  (`models.py:2329`) — é para o inventário de FKs viver **num lugar só** (`_FKS_PARA_CLIENTE`, que
  a 290 lê) e para o SQLite do ensaio, que sem `PRAGMA foreign_keys` deixa órfão silencioso, se
  comportar como a produção.

**Fora de escopo.** Backfill por nome · botão "Fazer orçamento" na resposta (277) · EducaManto
(279) · mudar `orcamento_history.event_date` de tipo — ver decisão em aberto D3.

**Modelo de dados.** `orcamento_history.client_id INTEGER NULL FK` + `ix_orcamento_history_client_id`
· `orcamento_history.form_response_id INTEGER NULL FK` + índice · índice único parcial em
`calendar_events` · `down_revision` = `b7d2e4f1a9c3` (272) — **confirmar com `flask db heads`**.

**Endpoints.** `POST /api/orcamento/salvar` — aceita `client_id`, `form_response_id` ·
`GET /api/orcamento/historico` — `?client_id=`; `_entry_summary` ganha os dois ids ·
`GET /api/clientes/<id>` — `orcamentos: [...]` (id, data, total 4h, vendedor, `pode_abrir`) ·
`GET /api/formularios/respostas/<id>` — `orcamentos: [...]`.

**UI.** `pages/OrcamentoCalculadoraPage.tsx` (combobox no lugar do input; erro da API preserva o
digitado) · `pages/ClientDetailPage.tsx` (card abaixo de "Festas anteriores", `:214`) ·
`pages/FormulariosAdminPage.tsx` (seção no diálogo) · `pages/OrcamentoHistoricoPage.tsx` (badge).

**Reusa.** `@manto/ui` `Combobox` · `lib/clientes.ts` · `client_ops.py:238` (inventário das FKs a
anular) · decisão 10 da 266 (coluna nullable sem backfill por nome) · `agenda_read.py:892-907`.

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- Migration em tabela pequena, mas é migration: ensaio no dump do dia. *Verify:* `flask db heads`
  único antes e depois; `upgrade → downgrade → upgrade`; contagem de `client_id` preenchidos ==
  107 (ou o que o dump do dia medir); o oneoff de checagem devolve vazio no espelho **e** na
  produção; ensaio com uma duplicata plantada → a migration termina, o índice não existe e o log
  diz por quê (o caminho falha-seguro é testado, não presumido).
- Dois heads se a 272 não for mergeada antes: `Multiple head revisions` derruba o `upgrade`. A
  regra do princípio 4 (uma branch com migration por vez, `flask db heads` no dia) é a defesa.
- FINANCEIRO vê o card e cairia em 403 no "Ver". *Verify:* payload da ficha para FINANCEIRO traz
  `pode_abrir=false`; para SUPERADMIN `true`.
- *Verify também:* salvar com `client_id` → FK gravada e `client_name` = nome da ficha (conexão
  separada); salvar com nome livre → `client_id` nulo, PDF sai com o nome (paridade) · excluir a
  cliente → orçamento fica com `client_id` nulo e `client_name` intacto (o teste que hoje estouraria
  FK) · excluir a resposta → `form_response_id` nulo · `?client_id=` devolve só os dela; comercial
  não-dono não vê alheio · na tela: escolher no combobox, salvar, abrir a ficha e ver o card.

**Dependências.** 272 mergeada (head da cadeia).

### 275 — Desfecho do orçamento: ganho derivado, perdido explícito, follow-up por negociação

**Problema.** Não existe status de orçamento; o histórico (`orcamento_read.py:130`) lista sem dizer
quais viraram evento nem quais morreram. Dos 1.809, ~1.700 de 2026 não têm evento e o sistema não
distingue negociação viva de negociação morta. O follow-up ("quem ainda não respondeu?") vive na
memória da comercial.

**Escopo.**
- Migration #2: `orcamento_history.lost_at` (DateTime naive SP) e `lost_reason` (String(40), lista
  fechada `LOST_REASONS` em `quote_ops`: `preco`, `data_indisponivel`, `fechou_concorrente`,
  `sem_resposta`, `desistiu`, `teste`, `outro`) e `lost_note` (Text, opcional). `teste` existe
  porque a comercial simula preços e salva — sem ele a fila de follow-up (288) nasce poluída.
- `quote_ops.status_do_orcamento(entry) -> "ganho"|"perdido"|"aberto"`: `ganho` se existe evento
  **não cancelado** com `orcamento_history_id = entry.id` (relationship da 273; na listagem, `EXISTS`
  em subquery, não uma query por linha); `perdido` se `lost_at`; senão `aberto`. **A única função
  que responde isso** — usada pelo histórico, pela ficha (274), pela resposta (274) e pela rotina
  (288). Nenhuma coluna `status`: "ganho" escrito divergiria do FK no cancelamento (267 decisão 5)
  e exigiria backfill; derivado não exige nada.
- `PATCH /api/orcamento/historico/<id>/desfecho {perdido: bool, motivo?, nota?}` — marcar/reabrir;
  409 para marcar perdido quem está ganho ("desvincule o evento primeiro"). Gate `_require_vendas`
  do orçamento + dono-ou-superadmin (`_get_entry_or_none`, `:204`).
- Histórico: `?status=aberto|ganho|perdido`, badge por linha, "Marcar como perdido" (diálogo com
  motivo — `ConfirmDialog` do `@manto/ui`, não `window.confirm`), "Reabrir".
- KPI "negociações abertas há mais de 7 dias" no topo do histórico, **agrupado por negociação**
  (`client_id` ou `client_name` normalizado + `event_date`): a calculadora salva várias versões da
  mesma cotação; contar por linha multiplicaria o mesmo lead por 4. `quote_ops.negociacoes_abertas(
  hoje, dias)` é a função — a 288 a reusa para notificar.
- Detalhe da resposta (274) exibe o status dos orçamentos dela — é o "lead com desfecho" derivado:
  com evento = ganha; todos os orçamentos perdidos = perdida; algum aberto = em orçamento; nenhum
  orçamento = nova (ou arquivada, 276). `formularios_ops.status_do_lead(response)` é a função, e
  a listagem de `/formularios` ganha selo e filtro por ela.

**Fora de escopo.** Coluna de status/motivo em `FormResponse` (a 276 cobre o único caso que a
derivação não alcança) · relatório de motivos de perda · card na Home · notificação (288).

**Modelo de dados.** `orcamento_history.lost_at TIMESTAMP NULL` · `lost_reason VARCHAR(40) NULL` ·
`lost_note TEXT NULL` · `down_revision` = migration da 274.

**Endpoints.** `PATCH /api/orcamento/historico/<id>/desfecho` (novo) · `GET /api/orcamento/historico`
— `?status=`; `_entry_summary` ganha `status`, `lost_at`, `lost_reason`, `dias_em_aberto`
(`created_at` é UTC — `utc_para_sp` antes de subtrair de `now_sp()`, princípio 6) ·
`GET /api/formularios/respostas` — cada item ganha `lead_status` derivado.

**UI.** `pages/OrcamentoHistoricoPage.tsx` (chips de filtro — padrão cards-filtro da 194; badge;
ação no kebab com motivo; KPI) · `pages/OrcamentoResultadoPage.tsx` (badge no cabeçalho) ·
`pages/FormulariosAdminPage.tsx` (selo por linha) · Framer: troca de badge com transição curta e
`useReducedMotion`.

**Reusa.** relationship da 273 · `orcamento_read.py:204` · `ConfirmDialog` (228) · estado-na-URL
das telas financeiras (267) para `?status=`.

**Notificação (272).** Nenhuma nesta feature (o produtor `orcamento.followup` é a 288 e lê
`negociacoes_abertas`).

**Riscos e como o verify cobre.**
- Orçamentos antigos convertidos por evento criado à mão ficam "aberto" até alguém vincular (273).
  O estado vazio diz "vincule o evento na aba Comercial"; o passivo (~1.700) é filtro de tela, não
  fila — a 288 corta por `created_at ≥ ATIVACAO`.
- *Verify:* sem evento → `aberto`; vincular (273) → `ganho`; cancelar o evento (224) → volta a
  `aberto` (derivado, não gravado) · marcar perdido grava `lost_at` com `now_sp()` (não UTC — comparar
  com `utcnow()` dá ~3 h) e motivo da lista; motivo fora da lista → 400 `fields.lost_reason` ·
  perdido em orçamento ganho → 409 · `?status=perdido` filtra; comercial não-dono → 404 no PATCH ·
  KPI: 4 salvamentos da mesma cliente/data contam 1 negociação · `lead_status` percorre nova → em
  orçamento → perdida → ganha · na tela: filtrar, marcar perdido, badge muda sem recarregar, reabrir.

**Dependências.** 273, 274.

### 276 — Resposta arquivada: o lead que morreu sem orçamento sai da fila sem ser apagado

**Problema.** O card da Home e os cartões de `/formularios` contam `sem_evento`/`futuros_sem_evento`
(`formularios_ops.py:130-154`), e a 266 registrou de propósito (decisão 2) que não existe "tratado"
no modelo. A 275 deriva o desfecho quando a resposta virou orçamento — mas a resposta que morreu
**antes** de qualquer orçamento (cliente desistiu no WhatsApp, duplicata, teste) fica na fila para
sempre. Hoje a única saída é excluir, e excluir destrói o registro da festa, que é a fonte do
histórico pré-2026 (`client_ops.list_client_form_history`, `client_ops.py:162`).

**Escopo.**
- Migration #3: `form_responses.archived_at` (DateTime naive SP), `archived_reason` (String(30),
  lista fechada `desistiu`, `sem_retorno`, `duplicada`, `teste`, `outro`), `archived_by_id` (FK
  `users`, nullable, `SET NULL`). Sem backfill.
- `formularios_ops.arquivar(response, reason, user, agora)` / `desarquivar(response)`: **recusa
  arquivar resposta com evento (409)** — a festa existe. `event_link_locked` **não é tocado**: o
  flag significa "um humano decidiu o vínculo" (docs/04 §6, `unlink_event` `:317`), e reaproveitá-lo
  para "arquivada" faria o `desarquivar` apagar uma trava que a comercial pôs antes de arquivar.
  Em vez disso, `retry_auto_link_pending` (`:689`) ganha `archived_at IS NULL` no filtro — a
  arquivada não é religada, e a trava humana sobrevive ao arquivar/desarquivar.
- `_status_condition` (`:133`) exclui `archived_at IS NOT NULL` de `sem_evento`, `sem_cliente`,
  `ambiguos` e `futuros_sem_evento`; `STATUS_FILTERS` ganha `arquivadas`; `count_status` (`:154`)
  acompanha sozinho — a Home (266) e os cartões leem a mesma função.
- `/formularios`: ação "Arquivar" com motivo em diálogo, cartão "Arquivadas", ação "Desarquivar";
  arquivada nunca some — fica num filtro próprio. Mutações invalidam `["dashboard"]` (266 decisão 4).
- `status_do_lead` (275) devolve `arquivada` quando `archived_at`.

**Fora de escopo.** Arquivar automaticamente por tempo (sempre humano) · "lida/não lida" (é a 272,
decisão 12) · propagar "orçamento perdido → resposta arquivada" (escrita cruzada; a derivação da
275 já mostra "perdida" quando todos os orçamentos morreram).

**Modelo de dados.** `form_responses.archived_at TIMESTAMP NULL` · `archived_reason VARCHAR(30) NULL`
· `archived_by_id INTEGER NULL FK users ON DELETE SET NULL`.

**Endpoints.** `POST /api/formularios/respostas/<id>/arquivar {reason}` · `DELETE …/arquivar`
(desarquivar) — gate `_require_vendas` de formulários (`formularios_admin_read.py:24`) ·
`GET /api/formularios/respostas?filtro=arquivadas` · `GET /api/dashboard` — bloco `formularios`
ganha `arquivadas`.

**UI.** `pages/FormulariosAdminPage.tsx` (cartão, ação com motivo, badge; diálogo de detalhe mostra
"arquivada em dd/mm por X: motivo") · Home: o card da 266 só para de contar as arquivadas.

**Reusa.** `count_status`/`_status_condition` (266) · `retry_auto_link_pending` (só ganha um
filtro) · `ConfirmDialog` · `now_sp()`.

**Notificação (272).** Nenhuma. A 272 v1 já marca lida a notificação da resposta ao abrir o
detalhe; arquivar não precisa avisar ninguém.

**Riscos e como o verify cobre.**
- Mudar `count_status` muda o número do card da Home. *Verify:* compara os contadores antes/depois
  no mesmo banco e a diferença é exatamente a resposta arquivada no teste.
- *Verify também:* arquivar → `archived_at` em SP, `event_link_locked` **inalterado**, `sem_evento`
  cai em 1; `retry_auto_link_pending` não a religa mesmo com evento real na data · resposta
  travada pela comercial, arquivada e desarquivada → continua travada · arquivar resposta com
  evento → 409 · desarquivar → volta a `nova`, contador sobe · CASTING não recebe o bloco do
  dashboard (RBAC por ausência).

**Dependências.** Nenhuma (fica melhor depois da 275, para o selo de status já existir).

### 277 — Da resposta ao orçamento: "Fazer orçamento" e prefill da calculadora

**Problema.** A transição resposta → orçamento não existe (análise §2: "redigitação total"). A
resposta traz nome, telefone, data, hora, endereço e quantidade de personagens em chaves estáveis
desde a feature 123 (`data_evento`, `hora_evento`, `periodo_contratacao`, `logradouro`…`estado`,
`qtd_personagens`, `forma_pagamento`, `nome_aniversariante`, `idade_aniversariante` — migration
`a51ce3dc4f3c:38-55`); a calculadora recebe nada. Sem `form_response_id` gravado, o desfecho do lead
(275) não tem como ser derivado.

**Escopo.**
- `formularios_ops.extrair_para_orcamento(response) -> dict` (puro): nome, telefone, `client_id`,
  data, hora, endereço composto (para o cálculo de km), cidade/estado, `qtd_personagens`,
  `form_response_id`. Lê as duas eras do JSON promovendo `_normalize_field`
  (`impressoes3d_ops.py:592`) para `formularios_ops` como utilitário único — a Fila 3D passa a
  importar de lá, não uma terceira cópia. Chave ausente (resposta anterior à 123, só rótulo) → campo
  fora do dicionário, nunca erro.
- `GET /api/formularios/respostas/<id>/prefill-orcamento` (gate `_require_vendas` de formulários).
- Botão "Fazer orçamento com esta resposta" no diálogo de `/formularios`, ao lado de "Criar evento
  com os dados desta resposta" (`FormulariosAdminPage.tsx:491-492`) → `/orcamento?resposta=<id>`;
  o mesmo botão na linha da resposta na ficha da cliente.
- Calculadora lê `?resposta=` (mesmo padrão de `recalcular_id`, `OrcamentoCalculadoraPage.tsx:113`)
  e preenche **em lote, num render** (para não disparar N `POST /calcular`): cliente (`client_id`
  + nome se a resposta já tem ficha — a 266 auto-associa; senão `client_name` = `contact_name`),
  `event_date`, `event_location`, N linhas de personagem vazias conforme `qtd_personagens`,
  deslocamento **sugerido** "fora de SP" quando a cidade normalizada ≠ São Paulo (sugestão marcada
  como tal, não decidida). Guarda `form_response_id` para o `salvar` (274). Faixa "Preenchido a
  partir da resposta de <nome> — confira" com link de volta `/formularios?resposta=<id>` (266).
- Guarda de id inválido: `?resposta=abc` → nenhuma chamada a `/respostas/NaN` (pegadinha da 266).

**Fora de escopo.** Prefill de elenco por nome de personagem (texto livre da cliente raramente bate
com o catálogo) · criar a cliente automaticamente (decisão 12 da 266) · calcular km sem clique
(Google Maps custa por chamada) · resposta corporativa → EducaManto.

**Modelo de dados.** Nenhuma migration (usa `form_response_id` da 274).

**Endpoints.** `GET /api/formularios/respostas/<id>/prefill-orcamento` (novo) ·
`POST /api/orcamento/salvar` já aceita `form_response_id` (274) · listagem de
`/formularios` devolve `orcamento_id`/`lead_status` (275).

**UI.** `pages/FormulariosAdminPage.tsx` (segundo botão) · `pages/ClientDetailPage.tsx` (ação na
linha da festa) · `pages/OrcamentoCalculadoraPage.tsx` (leitura do parâmetro, preenchimento em
lote, faixa de origem).

**Reusa.** `_field_value_by_key` (`formularios_ops.py:49`) · `useFormResponseDetail`
(`lib/formulariosAdmin.ts:63`) · deep-link `?resposta=` (266) · combobox de cliente (274).

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- Endereço da festa × endereço da contratante (`endereco_contratante` é chave de sistema,
  `formularios_ops.py:36`): escolher errado manda o transporte para a casa da mãe. A spec fixa
  `logradouro…estado` da seção "Endereço do Evento" e o verify usa uma resposta real do espelho.
- *Verify:* resposta com cliente → calculadora nasce com `client_id`, data, local; salvar grava
  `form_response_id` e `client_id` (conexão separada) · resposta sem cliente → `client_name` =
  `contact_name`, `client_id` nulo · cidade "Sao Paulo" sem acento → sugestão SP; "Campinas" →
  `fora_sp` sugerido · resposta pré-123 → 200 com poucos campos · `?resposta=abc` → sem requisição
  NaN · detalhe da resposta lista o orçamento com `aberto` (275) · CASTING → 403 no prefill · na
  tela: fluxo completo e volta pelo link.

**Dependências.** 274.

### 278 — Prefills completos para o evento

**Problema.** Orçamento → evento herda valor/cachê/transporte mas perde fim, vendedor, cliente e
resposta (`_build_orcamento_prefill`, `routes.py:3101-3178`, devolve `client_name` como texto;
consumo em `EventCreatePage.tsx:101-127`). Resposta → evento preenche só data e cliente-se-existir
(`EventCreatePage.tsx:131-152`), embora a resposta tenha endereço, hora, telefone e forma de
pagamento. A análise §2 também aponta "perde pagamento": **o snapshot do orçamento não tem forma de
pagamento nem parcelamento** — a calculadora não coleta; fica registrado (decisão em aberto D6).

**Escopo.**
- `_build_orcamento_prefill` ganha `seller_id` (`entry.user_id` se estiver em `options.sellers`),
  `client {id, name}` (274) e `form_response_id` (274). `end_time` é derivado no cliente
  (`start + duração escolhida`) — o servidor já manda `start_time`.
- `GET /api/events/new/prefill` (`agenda.py:155-167`) aceita também `?resposta_id=` e combina os
  dois: orçamento manda no que é preço, resposta manda no que é festa; o payload declara a origem
  de cada bloco. Fonte da parte "festa": `extrair_para_orcamento` (277) estendida com hora fim
  (parse só do formato "das XXh às YYh"; fora disso, vazio) e `payment_method` mapeado por constante
  (`forma_pagamento` do formulário → um dos seis de `_VALID_METHODS`, `routes.py:910`:
  `avista|pix_parcelado|faturado|cartao|futuro|parcelado_datas`; `futuro` exige `payment_due_date`,
  que o formulário não tem — mapeia e deixa a data para a humana; desconhecido → nulo).
- `EventCreatePage`: com `client` do orçamento, a lista de clientes recebe a Contratante; com
  `form_response_id`, o pré-contrato entra vinculado (`setFormResponse`) — uma criação a partir do
  orçamento fecha resposta → orçamento → evento sem redigitar. Do prefill por resposta: `location`,
  hora início/fim, `payment_method`, `event_type='CORP'` quando `form_type='corporativo'`,
  observação com aniversariante/tema/personagens pedidos. Resposta **sem** cliente abre o
  `QuickCreateClientForm` (`ClientPicker.tsx:16`) já preenchido com `contact_name`/`contact_phone`
  — a humana confirma, o sistema não cria sozinho. Campos vindos de prefill ganham indicação
  discreta da origem; nada fica travado.
- Ordem dos efeitos: o `seller_id` do orçamento vence o default "o próprio usuário se for vendedor"
  (`EventCreatePage.tsx:154-159`) sem sobrescrever escolha manual posterior.

**Fora de escopo.** Forma de pagamento/parcelas a partir do orçamento (o dado não existe — D6) ·
prefill de elenco por resposta · refatorar `calendar/routes.py` (docs/05 §9.1) · geocodificar no
prefill.

**Modelo de dados.** Nenhuma migration.

**Endpoints.** `GET /api/events/new/prefill?orcamento_id=&resposta_id=` — estendido; `{}` quando
nada bate (paridade); gate `_CAN_CREATE` (`routes.py:58`) como hoje.

**UI.** `pages/EventCreatePage.tsx` (dois efeitos preenchem mais campos; quick-create aberto quando
a resposta não tem cliente; aviso "Preenchido a partir de …") ·
`components/EventFormBlocks/ClienteBlock.tsx` (aceita `initialQuickCreate`).

**Reusa.** `routes.py:3101` · `ClientPicker.tsx:16,94` (`QuickCreateClientForm`,
`useQuickCreateClient` — telefone único, reaproveita ficha existente com `reused=true`) · 274 (FKs)
· 277 (extração das chaves) · `GoogleAddressInput` do `@manto/ui`.

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- Prefill demais vira "evento criado sem ler": a indicação de origem e nada travado são a defesa;
  o verify de tela sobrescreve um campo preenchido e confere que a escolha manual persiste.
- Hora fim mal parseada empurra `end_at` para o dia seguinte: só preencher quando o parse é
  inequívoco. *Verify:* "das 15h às 19h" → fim 19:00; "tarde" → fim vazio.
- Quick-create com telefone já existente devolve `reused=true` e a ficha existente; se a 266 não
  associou (formatação), pode nascer duplicata — a 290 é a rede. *Verify:* caso `reused`.
- *Verify também:* prefill de orçamento com cliente e resposta → `client`, `seller_id`,
  `form_response_id`; criar o evento grava `client_id`, `event_clients` (Contratante), `seller_id`,
  `orcamento_history_id`, `form_response_id` (conexão separada) e a resposta fica `manual` +
  travada (núcleo da 267); o orçamento vira `ganho` (275) · prefill sem cliente → sem `client`, sem
  erro · resposta corporativa → CORP pré-selecionado · `payment_method` mapeado; opção desconhecida
  → nulo · duração 3h → fim = início + 3h.

**Dependências.** 274, 277.

### 279 — EducaManto → evento: cliente no orçamento e "Criar evento"

**Problema.** `EducaMantoQuote` (`models.py:1439-1457`) guarda `client_name` texto e um `snapshot`;
não tem FK de cliente nem ligação com o evento que a venda gerou. O histórico
(`EducaMantoHistoricoPage.tsx:263-276`) oferece Ver/Recalcular/PDF — não "Criar evento". O prefill
só entende `orcamento_id` (`agenda.py:162-167`). O evento EducaManto nasce redigitado, e o prefixo
`(EDU` do título — que define a regra de comissão sobre lucro (`models.py:373-380`, docs/04 §2) — é
digitado à mão.

**Escopo.**
- Migration #4: `educamanto_quotes.client_id` (FK `clients`, nullable, `SET NULL`) e
  `calendar_events.educamanto_quote_id` (FK `educamanto_quotes`, nullable, índice, `SET NULL`).
  Sem backfill.
- `educamanto/quote_ops.build_event_prefill(quote) -> dict` (puro): título sugerido
  `(EDU) <musicais>`, data do snapshot se houver, `client {id, name}`, lista de configurações do
  snapshot v2 (`quote_ops.py:219-266`) com valor com/sem nota, `transport_value` do breakdown,
  `seller_id` = dono se for vendedor, `educamanto_quote_id`. Mesmas chaves do prefill comum onde
  couber, para o `useEffect` do `EventCreatePage` reusar.
- `GET /api/events/new/prefill?educamanto_id=` (gate `_CAN_CREATE`; `{}` se inválido ou se o usuário
  não pode ver o orçamento — dono ou superadmin, regra de `educamanto_read.py:28`).
- `POST /api/events` aceita `educamanto_quote_id` (gravado só na criação, como o irmão;
  `PATCH` em bloco não toca).
- Calculadora EducaManto: `Combobox` de cliente (274) grava `client_id`; histórico ganha "Criar
  evento" só quando o payload diz `can_create_event` (REVENDEDOR_EDUCAMANTO vê o histórico, mas
  `_CAN_CREATE` é `{COMERCIAL, SUPERADMIN}`, `routes.py:58`) e cliente clicável.
- `EventCreatePage`: bloco "Configuração vendida" — o seletor exige escolha explícita (sem
  default), mostra os dois valores (com/sem nota) e define `sale_value`/`sale_value_gross`/
  `with_invoice`; título pré-preenchido e editável com dica de que `(EDU` é o gatilho da comissão.
- `ComercialSection`: DataRow "Orçamento EducaManto de origem" → `/educamanto/historico?ver=<id>`.
- `delete_client` anula `educamanto_quotes.client_id` (princípio 5).

**Fora de escopo.** Status ganho/perdido do EducaManto (39 orçamentos; repete-se a 275 se a 288
mostrar demanda) · vincular EducaManto a evento existente · pré-escalar elenco pelos musicais.

**Modelo de dados.** `educamanto_quotes.client_id INTEGER NULL FK` · `calendar_events.educamanto_quote_id
INTEGER NULL FK` + índice · `down_revision` = migration da 276.

**Endpoints.** `GET /api/events/new/prefill?educamanto_id=` · `POST /api/events` (+
`educamanto_quote_id`) · `POST /api/educamanto/orcamento/gerar` (+ `client_id`) ·
`GET /api/educamanto/historico` (+ `client_id`, `client_name` da ficha, `can_create_event`) ·
`GET /api/events/<id>` — bloco `venda` ganha `educamanto_quote_id` sob a mesma regra de dono.

**UI.** `pages/EducaMantoCalculadoraPage.tsx` · `pages/EducaMantoHistoricoPage.tsx` ·
`pages/EventCreatePage.tsx` · `components/EventDetail/ComercialSection.tsx`.

**Reusa.** `_build_orcamento_prefill` como molde de forma · `lib/eventCreate.ts:70`
(`useOrcamentoPrefill`) · regra de comissão EducaManto canônica (267) · combobox da 274.

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- Configuração errada vende pelo preço errado: escolha explícita, sem default.
- Título sem `(EDU` perde a comissão sobre lucro. *Verify:* título sugerido casa
  `EDUCAMANTO_TITLE_PREFIX`; criar o evento → `is_educamanto` True e `CommissionPayment` nasce pela
  regra EducaManto (5% sobre lucro, `payable_from` = data do evento), não 2,5% da venda.
- *Verify também:* gerar orçamento com `client_id` → FK e `client_name` da ficha · prefill válido →
  título, configurações e valores iguais ao snapshot; inválido / de outro revendedor para comercial
  comum → `{}` · criar evento → `educamanto_quote_id` gravado, cliente em `event_clients` · `PATCH`
  em bloco não apaga o FK · `can_create_event` falso para REVENDEDOR · excluir a cliente → FK nula ·
  ensaio da migration.

**Dependências.** 274 (combobox); migration encadeia na 276.

### 280 — Ficha da cliente que diz a verdade

**Problema.** Três mentiras baratas. (1) `PATCH /api/clientes/<id>` só aceita `cpf`/`cnpj`/`address`
(`clientes_write.py:68-92`; `client_ops.update_client_fields`, `:228`): nome com grafia errada e
telefone trocado — a identidade única do CRM (`Client.phone` UNIQUE, `models.py:1859`) — não se
corrigem pela tela; `notes` (`:1890`), `lead_origin`/`lead_stage`/`utm_*` (`:1880-1887`) e as tags
NFC da cliente (`nfc_tags.client_id`, `:2329`) nunca aparecem. (2) `ClientsListPage.tsx:72` calcula
"novos este mês" com `new Date().toISOString()` — relógio do navegador em UTC: dia 31 às 22h de
Brasília já mostra o mês seguinte com zero. (3) `summarize_feedback` (`client_ops.py:330`) filtra
por `CalendarEvent.client_id` (contratante) enquanto o card "Eventos" da mesma ficha lista por
`EventClient` — a assessora vê "nenhuma avaliação" com eventos listados acima (266, decisão 19,
adiada para esta onda). E a exclusão ainda usa `window.confirm` (`ClientDetailPage.tsx:87`).

**Escopo.**
- `update_client_fields` aceita `name`, `phone`, `email`, `company`, `notes` além dos atuais;
  telefone normalizado pela função de `quick_create_client` (`client_ops.py:64`), `phone_display`
  regravado; colisão de UNIQUE → 409 com `{existing_client_id, existing_name}` (a porta de entrada
  do merge da 290); nome vazio → 400 `fields.name`. `audit()` (`app/utils.py:46`) na troca de
  nome/telefone — é identidade, precisa de rastro.
- `summarize_feedback` filtra por `EXISTS event_clients OR client_id` — a mesma composição de
  `search_events` (`event_ops.py:1242-1245`). A tela `/clientes/avaliacoes` (KPIs, distribuição,
  atenção) muda junto **só no filtro por cliente**; o agregado sem filtro não muda. O card da ficha
  troca o estado vazio.
- `client_metrics` (`client_ops.py:183`) devolve `current_month` calculado com `now_sp()`; a tela
  usa o valor do payload (`hojeYmd()` de `lib/horaLocal.ts:29` é a alternativa no cliente).
- Ficha: seção "Contato" editável inline (Editar/Salvar/Cancelar, erro por campo preservando o
  digitado, 409 vira aviso com "Ver a outra ficha" — e, depois da 290, "Mesclar"); card "Notas"
  editável; card "Origem e campanha" (leitura); card "Tags NFC" com link para `/3d/tags`; exclusão
  vira `ConfirmDialog`.

**Fora de escopo.** Mesclar (290) · editar campos do Kommo (importados; edição manual criaria
divergência com a origem) · histórico de alterações além do `AuditLog`.

**Modelo de dados.** Nenhuma migration.

**Endpoints.** `PATCH /api/clientes/<id>` — corpo amplia; 409 estruturado · `GET /api/clientes/<id>`
— ganha `notes`, bloco `campaign`, `nfc_tags` · `GET /api/clientes/avaliacoes?client_id=` — semântica
muda para vínculo por `EventClient` · `GET /api/clientes/metricas` — `current_month`.

**UI.** `pages/ClientDetailPage.tsx` · `pages/ClientsListPage.tsx` (só o relógio) ·
`pages/ClientFeedbackPage.tsx` (sem mudança visual; números por cliente podem subir).

**Reusa.** `client_ops.py:64` (normalização) · `event_ops.py:1242` (EXISTS) · `useUpdateClient`
(`lib/clientes.ts:145`) · `ConfirmDialog` · `ApiRequestError.fields` do `@manto/api-client`.

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- Trocar telefone muda a chave da auto-associação da 266 (respostas futuras casam pelo novo
  número — desejado; antigas não são reprocessadas — decisão 11 da 266). Registrado na docstring.
- Unificar o filtro de avaliações muda KPIs por cliente. *Verify:* total de `/clientes/avaliacoes`
  sem filtro **inalterado**; cliente só assessora em 1 evento com feedback passa a mostrar 1.
- *Verify também:* PATCH grava e normaliza (`phone` só dígitos, `phone_display` formatado) com
  `AuditLog` antigo→novo (conexão separada) · telefone de outra ficha → 409 + `existing_client_id`,
  nada gravado · nome vazio → 400 · PATCH só com cpf/cnpj/address continua funcionando · detalhe traz
  `notes`, `campaign`, `nfc_tags` (lista vazia, não ausente) · `current_month` às 23h de Brasília do
  dia 31 (monkeypatch) é o mês certo · FINANCEIRO passa, CASTING → 403 · na tela: editar e ver lista
  e ficha atualizarem sem F5; excluir passa pelo `ConfirmDialog`.

**Dependências.** Nenhuma.

---

## 4. Entre a onda 2 e a onda 3 — o que a 272 pede antes de qualquer rotina

### 281 — Preferências de notificação por `kind` (silenciar)

**Problema.** A spec da 272 ("Fora de escopo") é explícita: preferências por `kind` por usuário
precisam entrar **antes** da onda 3, porque o SUPERADMIN recebe todos os `kind` e, com lembretes
diários de parcela, o sino vira o e-mail de novo. Sem isso, a 286 não pode ligar.

**Escopo.**
- Migration #5: tabela `notification_mutes (id, user_id FK users CASCADE, kind VARCHAR(40),
  created_at)` + `UNIQUE(user_id, kind)`. Uma linha = "este usuário silenciou este `kind`". Tabela
  em vez de JSON em `users`: a UNIQUE é a regra, e `emitir` filtra por `NOT EXISTS` sem parsear nada.
- `notificacoes_ops.emitir` exclui dos destinatários quem tem mute para o `kind` (tanto os
  resolvidos por papel quanto a lista explícita) — no mesmo `SELECT` de dedupe que já existe.
  Severidade `urgent` **não** fura o mute na v1 (regra simples; ver D7).
- `GET/PUT /api/notificacoes/preferencias` — só `@api_login_required`, escopo `current_user.id`
  (terceiro padrão de RBAC da 272). Devolve o catálogo de `kind` com rótulo pt-BR e o estado.
- Página `/notificacoes` (272) ganha aba "Preferências" com um switch por `kind` (rótulos vêm do
  servidor; `kind` novo aparece sozinho).

**Fora de escopo.** Preferência por severidade, por horário, ou "digest" (decisão 16 da 272) ·
mute por objeto ("não me avise mais deste evento").

**Modelo de dados.** `notification_mutes` + `UNIQUE(user_id, kind)` + índice em `user_id`.

**Endpoints.** `GET /api/notificacoes/preferencias` → `{kinds: [{kind, label, muted}]}` ·
`PUT /api/notificacoes/preferencias {kind, muted}`.

**UI.** `pages/NotificacoesPage.tsx` (aba nova) — `Tabs` do `@manto/ui`.

**Reusa.** `notificacoes_ops` (272) · padrão de leitura por dono (272 decisão 10).

**Notificação (272).** É infraestrutura da própria 272.

**Riscos e como o verify cobre.**
- *Verify:* usuário COMERCIAL com mute em `form_response.nova` não recebe a linha no POST público;
  outro COMERCIAL sem mute recebe (conexão separada) · mute em `kind` de lista explícita
  (`destinatarios=[vendedor]`) também vale · `PUT` para `kind` fora do catálogo → 400 · SUPERADMIN em
  "Ver como" altera as **próprias** preferências (a caixa é da pessoa) · `upgrade → downgrade →
  upgrade`.

**Dependências.** 272 em produção.

---

## 5. Onda 3 — o financeiro que avisa

**Objetivo.** O recebimento do evento passa a existir como dado com uma verdade só: o comprovante
prova, a parcela agenda, e o saldo é uma função. Depois disso, Home, evento e Planilha mostram o
mesmo número, a Planilha ganha o lado das entradas, e o vencimento avisa antes, no dia e depois —
pelo sino, com a mensagem de WhatsApp pronta, nunca por e-mail.

### 282 — Cronograma de parcelas editável na aba Comercial

**Problema.** `PUT /api/events/<id>/parcelas` (`agenda_write.py:1199`) e `useSetParcelas`
(`lib/eventOps.ts:267`) existem desde a 253, mas o `ParcelasPanel` é só leitura e some quando não
há parcela (`ColecoesComerciaisPanel.tsx:221-223`), e nenhuma tela chama o hook: o cronograma é
inescrevível pelo produto. `substituir_parcelas` apaga e recria (`comercial_ops.py:237-243`), o
que destruiria qualquer baixa (283) na primeira edição e troca o `id` da parcela a cada
salvamento. Duas docstrings mentem que "a planilha marca `received`" (`agenda_read.py:519-522`,
`ColecoesComerciaisPanel.tsx:219`, `lib/agenda.ts:371-375`). E **76 eventos** declaram
`pix_parcelado` com `payment_installments` (`models.py:320`) sem uma parcela datada — o que é
**desenho, não defeito**: "Dividido no PIX" (`PagamentoBlock.tsx:11`) sempre foi só quantidade;
quem cria cronograma datado é `parcelado_datas` (`routes.py:926`, Jinja). A spec fixa a semântica:
`pix_parcelado` = N sem datas; `parcelado_datas` = N com datas; os 76 são candidatos a ganhar
datas, não erros a corrigir.

**Escopo.**
- `substituir_parcelas` vira `sincronizar_parcelas` (reconciliação por `id`): item com `id`
  atualiza `due_date`/`amount`; sem `id` cria; ausente do corpo apaga. `received`/`received_at`/
  `payment_id` nunca são tocados aqui. Todo `id` recebido tem de pertencer a `event.id` (400 —
  senão um corpo malformado edita parcela alheia). Compat: corpo sem ids apaga e recria (bundle
  antigo em cache continua funcionando; a 283 acrescenta a recusa de apagar recebida).
- `comercial_ops.gerar_cronograma(event, n, primeira_data)`: "Gerar N parcelas" a partir de
  `payment_installments` e da primeira data, mensal, dividindo `sale_value` com ajuste de centavos
  na última; 409 se já há parcelas. Resolve os 76 sem redigitar.
- `ParcelasPanel` vira editor (linhas com data + `MoneyInput` do `@manto/money`,
  adicionar/remover, salvar/cancelar) reusando o padrão do editor de acréscimos do mesmo arquivo;
  aparece mesmo sem parcela, com "Gerar N parcelas" quando `payment_method` é `pix_parcelado` ou
  `parcelado_datas` e não há parcela (gerar **não** troca o método: o cronograma datado é
  opcional em `pix_parcelado`). Soma ≠ venda é aviso, não bloqueio (sinal + saldo é legítimo).
- Docstrings e tipo (`lib/agenda.ts:375`) corrigidos.

**Fora de escopo.** Baixa (283) · parcelas em satélite (venda vive no líder; o painel só aparece no
líder, como o bloco venda).

**Modelo de dados.** Nenhuma migration.

**Endpoints.** `PUT /api/events/<id>/parcelas` — itens aceitam `id` (compatível) ·
`POST /api/events/<id>/parcelas/gerar {quantidade, primeira_data}` (novo; gate `_can_manage_sale`).

**UI.** `components/EventDetail/ColecoesComerciaisPanel.tsx` (editor, erro por campo via
`ApiRequestError.fields`, aviso de soma, gerar) · mobile: linhas empilhadas abaixo de `sm`.

**Reusa.** `comercial_ops.py:225` · `lib/eventOps.ts:267` · editor de acréscimos ·
`@manto/money` `MoneyInput`.

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- *Verify:* PUT com ids existentes preserva `received=True` da parcela mantida e altera só
  data/valor (conexão separada) · PUT sem ids apaga e recria (paridade) · `id` de parcela de outro
  evento → 400, nada gravado · gerar 3 de R$ 1.000,00 → 333,33 / 333,33 / 333,34 com vencimentos
  mensais; repetir → 409 · FIGURINO → 403 · contagem de eventos `pix_parcelado` sem parcela no
  espelho antes/depois do cenário · na tela: criar cronograma num evento sem parcelas, editar,
  remover, ver o KPI de cobrança mudar.

**Dependências.** Nenhuma.

### 283 — Baixa de parcela ligada ao comprovante

**Problema.** `EventInstallment.received` (`models.py:725`) é lido em cinco lugares
(`agenda_read.py:407`, `financeiro_read.py:431`, `financeiro/routes.py:470` e
`calendar/routes.py:1821` no Jinja inalcançável, mais o tipo do front) e escrito em nenhum — toda
parcela é "em aberto" para sempre. Pior: o dinheiro real está em `event_payments` (238 comprovantes)
e nada liga um comprovante à parcela que ele quita — `_compute_cobranca` (`agenda_read.py:401-421`)
**ignora os comprovantes quando há parcelas**, então o saldo de evento com cronograma nunca zera
mesmo com dinheiro na conta (análise §3.3). Uma baixa por booleano criaria duas verdades sobre o
mesmo real; e `EventPayment.file_path` é `NOT NULL` (`models.py:671`) — não dá para registrar um PIX
recebido sem anexo. De carona, dois defeitos conhecidos: `POST /events/<id>/payments`
(`agenda_write.py:1304`), `POST /events/<id>/reimbursements` (`:1380`) e
`POST /reimbursements/<id>/collect` (`:1416-1422`, registro do dinheiro recebido da cliente) usam
`_can_edit_event` (docs/05 §3.3 — Figurino registra dinheiro); `PATCH` e `DELETE /payments/<id>`
(`:1341`, `:1366`) são **só SUPERADMIN** — a financeira não corrige `amount` nem anexa nada; e 24
comprovantes têm `amount` NULL (o saldo os trata como zero e cobra de novo).

**Escopo.**
- Migration #6: `event_installments.payment_id` (FK `event_payments`, **UNIQUE**, nullable,
  `ondelete SET NULL`), `event_installments.received_at` (Date), `event_installments.received_by_id`
  (FK `users`, nullable); `event_payments.file_path` passa a **nullable**. `received` continua
  existindo e passa a ser escrito — invariante em docstring: `received == (payment_id IS NOT NULL)`,
  mantida por `dar_baixa`/`estornar_baixa`/`DELETE payments`. Sem `DROP COLUMN`: cinco leitores,
  um deles Jinja vivo pelo host.
- **Regra única de saldo, decidida aqui:** `outstanding = sale_value − Σ EventPayment.amount`,
  sempre, com ou sem cronograma. A parcela define `due` (menor vencimento sem `payment_id`) e as
  linhas da lista; o comprovante define o recebido. É o que faz `received_map`
  (`vendas_ops.py:118`), DRE, Dashboard Comercial e Home convergirem sem coluna nova, e é a regra
  que `entradas_ops` (284) cristaliza. `_compute_cobranca` passa a chamá-la e troca `date.today()`
  (`:405`) por `now_sp().date()`.
- `comercial_ops.dar_baixa(parcela, *, amount, received_at, file_storage=None, user)` (sem
  commit): cria o `EventPayment` (valor default = valor da parcela, arquivo opcional via
  `_add_payment_record`, `routes.py:1082`) e liga `payment_id`, `received=True`, `received_at`,
  `received_by_id`. `estornar_baixa(parcela)`: apaga o payment se não tem arquivo; se tem, mantém o
  comprovante e só desliga (prova não se apaga por engano). `DELETE /api/payments/<id>`
  (`agenda_write.py:1360`) desliga a parcela vinculada pela mesma função.
- `sincronizar_parcelas` (282) recusa apagar ou alterar valor/data de parcela com `payment_id`
  (409 listando quais) — corpo de bundle antigo sem ids cai em 409, nunca em perda.
- `POST /api/events/<id>/parcelas/<pid>/baixa` (multipart: `amount`, `received_at`, `file`
  opcional) e `DELETE …/baixa`; gate `_can_manage_sale` (paridade com `PUT /parcelas`). Resposta =
  `EventoDetalhe`.
- De carona, os gates de dinheiro do evento ficam **um só por risco** (docs/05 §3.3, D5b):
  `POST /events/<id>/payments`, `POST /events/<id>/reimbursements`, `POST /reimbursements/<id>/collect`
  e `PATCH /api/payments/<id>` (`:1335`) passam a `_can_manage_sale` (COMERCIAL/FINANCEIRO/
  SUPERADMIN) — registrar e corrigir dinheiro é do comercial e da financeira; `DELETE
  /api/payments/<id>` (`:1360`) **continua SUPERADMIN**: apagar prova é outro risco. A assimetria
  com `DELETE …/baixa` sob `_can_manage_sale` é deliberada e fica na docstring: o estorno só
  apaga o `EventPayment` **sem arquivo que a própria baixa criou**; comprovante com arquivo nunca
  é apagado por estorno. `amount` obrigatório em `POST payments` (400 `fields.amount`); `PATCH`
  aceita `file` multipart para anexar comprovante depois; script
  `scripts/oneoff/listar_comprovantes_sem_valor_283.py` lista os 24 para a financeira preencher
  pela tela (agora ela pode) antes de a 284 ligar o saldo unificado.
- UI: `ParcelasPanel` (282) ganha "Dar baixa" (`DarBaixaDialog` em `components/Pagamentos/` —
  data, valor, comprovante opcional; a 285 reusa), badge "Recebida em dd/mm" + "Estornar" +
  link do comprovante; `FinanceiroSection` marca comprovantes sem arquivo com "Anexar" e mostra a
  parcela quitada; aviso "há R$ X recebido sem parcela baixada" quando existe comprovante avulso em
  evento com cronograma. `invalidarFinanceiro()` exportada e chamada + `["dashboard"]`.

**Fora de escopo.** Casar comprovante avulso com parcela automaticamente (a baixa é humana; o aviso
sugere) · baixa parcial · um comprovante quitando várias parcelas (1:1 cobre o caso real) · mexer
no gêmeo Jinja (`calendar/routes.py:1821`, inalcançável) · `event_payments.amount NOT NULL` por
migration (só depois dos 24 corrigidos — registrado como pré-requisito de uma migration futura).

**Modelo de dados.** `event_installments.payment_id INTEGER NULL UNIQUE FK event_payments ON DELETE
SET NULL` · `received_at DATE NULL` · `received_by_id INTEGER NULL FK users ON DELETE SET NULL` ·
`event_payments.file_path` → `NULL` permitido (`ALTER COLUMN … DROP NOT NULL`, dentro de
`batch_alter_table` pelo SQLite do ensaio — 61 migrations já usam) · `down_revision` = migration
da 281. O `downgrade` reimpõe `NOT NULL` e **só é válido enquanto não existir baixa sem arquivo**
— documentado no cabeçalho da migration; depois da primeira baixa sem comprovante, voltar é
apagar dado, e a migration não faz isso sozinha.

**Endpoints.** `POST/DELETE /api/events/<id>/parcelas/<pid>/baixa` (novos) · `PUT …/parcelas` —
409 `{parcelas_recebidas: [ids]}` · `POST …/payments` — gate + `amount` obrigatório · `POST
…/reimbursements` e `POST /reimbursements/<id>/collect` — gate · `PATCH /api/payments/<id>` — gate
`_can_manage_sale` + aceita `file` · `DELETE /api/payments/<id>` — SUPERADMIN, desliga parcela ·
`GET /api/events/<id>` — `parcelas[].received_at/payment_id`, `cobranca` pela regra única,
`comprovantes_sem_parcela`.

**UI.** `ColecoesComerciaisPanel.tsx` · `components/Pagamentos/DarBaixaDialog.tsx` ·
`components/EventDetail/FinanceiroSection.tsx`.

**Reusa.** `_add_payment_record` (`routes.py:1082`) e `_log_anexo` (`agenda_write.py:1039`) ·
`vendas_ops.received_map`/`event_payment_status` (`:118`, `:44`) — passam a enxergar a baixa sem
mudar · `lib/eventDetail.ts` · `ConfirmDialog` para o estorno · barra de progresso XHR da Revisão
(254) como referência de upload.

**Notificação (272).** Nenhuma nesta feature. (Um `evento.quitado` ao vendedor quando o saldo zera
foi considerado e descartado — ver apêndice.)

**Riscos e como o verify cobre.**
- `file_path` nullable atinge o auditor financeiro 221 (`app/api/audit_agent.py:130` lê
  `event_payments.file_path`): o auditor passa a classificar "recebimento sem comprovante" como
  **achado**, não como erro. *Verify:* endpoints do agente respondem 200 com payment sem arquivo e a
  linha aparece como achado.
- Mudar a regra de saldo muda o KPI de cobrança dos eventos com cronograma (hoje 2). *Verify:*
  ensaio no dump lista os eventos cujo `outstanding` muda e cada um tem comprovante — é a única
  regra nova.
- Baixa por COMERCIAL é escrita financeira por papel comercial; é paridade com `PUT /parcelas` e a
  casa recebe PIX pelo comercial. Se o dono discordar, o gate estreita para FINANCEIRO/SUPERADMIN
  numa linha (D5).
- *Verify também:* baixa sem arquivo → `EventPayment` com `file_path NULL`, `installment.payment_id`
  certo, `received=True`, `received_at` = hoje SP (monkeypatch às 23h de Brasília: a data não avança);
  `received_map` e o Dashboard Comercial sobem o recebido (conexão separada) · baixa com arquivo →
  arquivo salvo por `save_file` · segunda baixa na mesma parcela → 409 (UNIQUE) sem comprovante
  órfão · estornar sem arquivo apaga o payment; com arquivo mantém e desliga · `DELETE payments` de
  um payment de baixa → parcela volta a pendente · PUT tentando apagar a recebida → 409 · parcelas +
  comprovante avulso → `outstanding` = venda − Σ comprovantes e `comprovantes_sem_parcela` aponta o
  avulso · FIGURINO em `POST payments`/`reimbursements`/`collect` → 403 (era 200) · FINANCEIRO em
  `PATCH payments` → 200 (era 403) e em `DELETE payments` → 403 (continua) · `POST payments` sem
  `amount` → 400 · script lista exatamente os 24 do espelho · `_compute_cobranca.enabled` às 22h de
  Brasília considera "hoje" o dia certo · `grep received` continua batendo nos cinco leitores, todos
  lendo o booleano mantido · ensaio: `ALTER … DROP NOT NULL` no dump; verify_266/267 continuam
  verdes.

**Dependências.** 282; migration encadeia na 281.

### 284 — `entradas_ops`: um saldo só para Home, evento e Financeiro (D-3/D0/D+3 sem robô)

**Problema.** Quatro lugares calculam "quanto falta / quando vence" com regras diferentes:
`_compute_cobranca` no evento (`agenda_read.py:401`, corrigido na 283); `compute_comercial_pending`
na Home (`dashboard_service.py:270-345`) só olha `EventPayment` e `payment_due_date` para
`futuro/faturado` (`:319`) — parcela não existe para ele; `financeiro_read` lista recebimentos
previstos só com `due_date` dentro do mês (`:426-433`) — parcela vencida em agosto some do painel em
setembro, exatamente quando mais precisa aparecer; `received_map` (`vendas_ops.py:118`) idem.
`dashboard_cutoff` (`dashboard_service.py:22`) e o painel de recorrentes (`:552`) usam
`date.today()`. E nenhuma das 7 threads toca cobrança de cliente.

**Escopo.**
- Novo `app/financeiro/entradas_ops.py` (puro): `listar_entradas(hoje, *, ate=None) ->
  list[Entrada]` — parcelas não recebidas (com `dias`, `faixa` `a_vencer`≤3 / `vence_hoje` /
  `vencida`, vencidas de qualquer mês incluídas) **e** eventos com venda, sem cronograma e saldo > 0
  como item `kind='saldo'` (vencimento pela política de hoje: `payment_due_date` para
  `futuro/faturado`, senão D-2 do evento — extraída de `compute_comercial_pending`); cada item traz
  evento, cliente (nome + `whatsapp_number`, `models.py:1906`), vencimento, valor, `installment_id`,
  severidade e os campos da mensagem de cobrança (`_serialize_mensagens`, `agenda_read.py:635-661`).
  Uma query com `joinedload`; `hoje` sempre por argumento. `saldo_do_evento` usa a regra única da
  283. `parcelas_em_aberto(hoje)` é a fatia que a 286 consome.
- **Três exclusões explícitas**, que `compute_comercial_pending` hoje não faz e que docs/04 §2
  exige: `not is_loja_virtual(event)` (`vendas_ops.py:197` — a Loja grava `sale_value` no evento,
  `virtuais_ops.py:1266`, e **nunca cria `EventPayment`**: sem o filtro, venda já paga pela
  InfinitePay vira "saldo em aberto" na Home e "parcela vence" na 286; registro segregado, §4),
  `not is_satellite` (inv. 1 — hoje escapa só porque `group_ops` zera a venda do satélite, `:181`;
  a regra não pode depender do acidente) e `not is_cortesia_permuta` (inv. 2 — permuta com
  `sale_value` > 0 não gera receita nem cobrança). Os três moram numa função `evento_cobravel(ev)`
  em `entradas_ops`, usada por `listar_entradas`, `itens_do_mes` (285) e pelo passo da 286.
- `compute_comercial_pending` (Home) e `recebimentos_previstos` (painel financeiro) passam a
  chamar `entradas_ops` — um número só. O painel financeiro separa `vencidas` (com `dias_atraso`,
  qualquer mês) de `a_vencer` (o campo antigo continua como união para a tela atual não quebrar).
- Home: linha por item com faixa colorida, "Copiar cobrança" (mensagem montada no cliente com os
  campos do item, como a cobrança da aba e a mensagem de convite, `DashboardPage.tsx:96`) e link
  `/events/<id>?aba=comercial`. Bloco continua sob `show_comercial` e dentro de `_bloco()`
  (`dashboard_service.py:466`).
- `dashboard_cutoff` e `:552` → `now_sp()`.
- **Corte:** itens de eventos com `start_at ≥ dashboard_cutoff()` ou vencimento ≥ `ATIVACAO`
  (constante no módulo, documentada). As 5 parcelas de 2025 (R$ 157.940) ficam para a aba
  Entradas (285) com filtro "antigas", não para o painel da Home.

**Fora de escopo.** Thread/notificação (286) · e-mail/WhatsApp automático à cliente · mudar a
política comercial (50% + 50% até D-2) — só passa a viver num lugar · alinhar o recorte de mês do
módulo de Comissões (267 decisão 10).

**Modelo de dados.** Nenhuma migration.

**Endpoints.** `GET /api/dashboard` — `comercial.pending_payments[]` vem de `entradas_ops` (mesma
forma; ganha `kind`, `installment_id`, `faixa`, `dias`) · `GET /api/financeiro/dashboard` —
`recebimentos_previstos` ganha `vencidas[]`/`a_vencer[]` · `GET /api/events/<id>` — `cobranca` já
vem da regra única (283).

**UI.** `pages/DashboardPage.tsx` (painel "Cobranças", `:520,863-872`: faixas, badge "parcela
2/3", "Copiar cobrança", link) · `pages/FinanceiroDashboardPage.tsx` (bloco "Vencidas de meses
anteriores" acima dos previstos) · motion: stagger curto com `useReducedMotion`.

**Reusa.** `dashboard_service.py:270-357` · `:466` (`_bloco`) · `:26` (`_base_filters`) ·
`agenda_read.py:635` · `financeiro_read.py:426-433` · `invite_reminders.py` só como desenho da janela.

**Notificação (272).** Nenhuma nesta feature — `parcelas_em_aberto(hoje)` é o produtor natural, e
a 286 a chama uma vez por dia.

**Riscos e como o verify cobre.**
- Unificar a Home com parcelas muda o card que o dono olha. *Verify:* ensaio no dump com diff das
  duas listas antes/depois; cada diferença é uma parcela datada ou um comprovante — a única regra
  nova; diferença sem explicação bloqueia o merge.
- Home é a página de entrada e foi o incidente de 01/09. *Verify:* mede o tempo do
  `GET /api/dashboard` no espelho antes/depois (portão: não piorar mais de 10%); a query nova é uma.
- *Verify também:* parcela vencendo em 3 dias → `a_vencer`; hoje → `vence_hoje`; ontem → `vencida`
  (relógio mockado às 22h de Brasília) · parcela baixada não aparece · evento VIRTUAL com
  `sale_value` e sem `EventPayment` → **fora**; satélite com venda plantada → fora; permuta com
  venda → fora (o diff antes/depois do ensaio explica cada VIRTUAL que some da Home por esta
  regra) · evento sem cronograma com
  saldo → `kind='saldo'` com `due` igual ao do detalhe do evento · Home e evento devolvem o mesmo
  `outstanding` e a mesma severidade para 20 eventos amostrados (o teste que hoje falha) · parcela
  vencida em julho continua em `vencidas` no dashboard de agosto · SUPERADMIN em "Ver como CASTING"
  não recebe o bloco · na tela: as três faixas, "Copiar cobrança" com valor/vencimento certos.

**Dependências.** 283.

### 285 — Aba "Entradas" na Planilha de Pagamentos

**Problema.** `api_financeiro_pagamentos` (`financeiro_read.py:646`) une seis fontes de **saída** e
nenhuma de entrada (análise §3.3). Quem opera o caixa vê o que sai num lugar e o que entra em
nenhum — e os **reembolsos a cobrar da cliente** (`EventReimbursement`, `models.py:678`, com
`collected_at`/`collected_amount` já existentes) são entrada e não aparecem em lista alguma.

**Escopo.**
- `entradas_ops.itens_do_mes(mes, hoje)`: parcelas com `due_date` no mês (prevista/recebida) +
  vencidas de meses anteriores ainda pendentes + itens `kind='saldo'` com vencimento no mês +
  comprovantes avulsos (sem `installment`) por `created_at` convertido para data de São Paulo +
  reembolsos a cobrar (`kind='reembolso'`, previstos por `created_at`, realizados por
  `collected_at`) — no formato comum da planilha (`type`, `id`, `date`, `amount`, `status`,
  `event_id`, `event_title`, `client_name`). Totais previsto/vencido/recebido.
- `GET /api/financeiro/entradas?month=YYYY-MM` — gate da planilha (FINANCEIRO/SUPERADMIN). Endpoint
  próprio, não `items[]` da planilha: o `set-status` poliforme ganharia um 7º tipo e os KPIs de "a
  pagar" somariam entrada com saída.
- `PagamentosPage`: aba "Entradas" via `?aba=entradas` (padrão 225f/265) compatível com `?mes=`
  (`PagamentosPage.tsx:232-234`), cards-filtro Vencidas / Hoje / A vencer / Recebidas (194), linha
  com "Dar baixa" (`DarBaixaDialog` da 283), "Cobrar no WhatsApp" (`wa.me` com a mensagem, como a
  Home) e link do evento; filtro "antigas" para o passivo de 2025; cartões abaixo de `xl` (226).
- Deep-link `?aba=entradas&status=vencida` — destino das notificações da 286.

**Fora de escopo.** Loja Virtual (registro segregado com fechamento próprio) · fluxo de caixa
consolidado (entradas − saídas por dia) · exportação · BV (é repasse, não entrada — docs/04 §2).

**Modelo de dados.** Nenhuma migration.

**Endpoints.** `GET /api/financeiro/entradas?month=` (novo).

**UI.** `pages/PagamentosPage.tsx` (aba, KPIs, tabela/cartões, baixa inline com loading por linha).

**Reusa.** 284 (`entradas_ops`) · 283 (`DarBaixaDialog`, `invalidarFinanceiro`) · `PagamentosPage`
(194/226/267) · `components/Pagamentos/`.

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- Dupla contagem: evento com cronograma **e** comprovante da baixa — o comprovante ligado a
  parcela não vira linha própria (a parcela representa); o avulso vira. *Verify:* mês com 2 parcelas
  (1 baixada) + 1 comprovante avulso + 1 reembolso a cobrar → 4 linhas, totais batem com a soma.
- *Verify também:* baixar pela aba atualiza linha, KPI e Home sem recarregar · COMERCIAL → 403 (gate
  da planilha) · `?aba=entradas&month=2026-08` abre direto · mobile 375px em cartões, sem scroll
  horizontal. É a feature mais "tela" da onda: **se a onda apertar, é a primeira a cair** — 283+284
  já entregam baixa e aviso.

**Dependências.** 284.

### 286 — Rotina diária do funil (uma thread, claim) + produtor `parcela.vence`

**Problema.** Nenhuma das 7 threads (`app/__init__.py:169-473`) toca cobrança de cliente. O único
aviso por data que existe é o lembrete de convite (`invite_reminders.py`: janela 9-20h `:47-48`,
claim atômico `:130`, `rodar_lembretes(forcar)` `:148`) — e ele manda e-mail. A 272 já desenhou o
`kind`: `parcela.vence:<installment_id>:<D-3|D0|D+3>`, destinatários FINANCEIRO + vendedor do
evento, "rotina diária nova com claim". As ondas 4 trazem mais três produtores diários — não pode
ser uma thread por rotina (cada worker já carrega 7, e a 272 recusou a oitava para a poda).

**Escopo.**
- Migration #7: `site_settings.funil_rotina_run_at` (DateTime nullable) — claim único da rotina
  diária, no padrão das três colunas que existem (`models.py:844,863,867`). Sem tabela
  `rotinas_fundo`: o padrão vigente é coluna no singleton.
- `app/rotinas/funil_diario.py`: `rodar(agora, forcar=False)` — janela 9-20h SP, `_claim_rodada`
  (molde `invite_reminders.py:130`), e uma lista ordenada de **passos** (`PASSOS = [cobranca,
  avaliacao, followup, aniversario, poda]`), cada um uma função pura `(agora) -> dict` em seu
  domínio que chama `notificacoes_ops.emitir(...)`; quem comita é a rodada ("em rotina de fundo,
  quem comita é a rodada", 272). Um passo que estoura faz `rollback`, loga com o nome e **não
  derruba os outros** (o `_bloco()` da 271 aplicado à rotina). `flask funil-rotina [--forcar]` para
  teste manual e para o verify (molde `compress-images`, `app/cli.py:61`).
- Thread `funil-rotinas` em `app/__init__.py` no esqueleto de `_start_invite_reminders` (`:427-473`),
  `FUNIL_ROTINA_ENABLED` no ambiente; acorda de hora em hora, a decisão fica na função (sobrevive a
  reinício de container).
- Produtor desta feature — `financeiro/cobranca_avisos.passo(agora)`: lê
  `entradas_ops.parcelas_em_aberto(hoje)` (284) e, para cada item cujo vencimento cai num marco
  (D-3, D0, D+3), chama `notificar_parcela_vence(item, marco)` com `dedupe_key =
  parcela.vence:<installment_id>:<marco>` (parcela) ou `parcela.vence:evento-<event_id>:<marco>`
  (item `kind='saldo'` — mesmo `kind`, mesma preferência do usuário), `destinatarios` = FINANCEIRO
  ativos + `seller_id` do evento, `severity='urgent'` em D+3, `link_path=
  /financeiro/pagamentos?aba=entradas&status=vencida` (285) e `body` com a mensagem de WhatsApp
  pronta. D0 aceita `due_date in (hoje, ontem)` se ainda não emitido — um deploy que derrube a
  rodada do dia não perde o marco.
- **Corte e passivo:** só vencimentos ≥ `ATIVACAO`; `scripts/oneoff/listar_passivo_cobranca_286.py`
  (dry-run) lista o que a rotina **não** vai avisar (as 5 de 2025) para a financeira baixar ou
  apagar pela aba Entradas antes de ligar a env.
- A poda de notificações da 272 (`limpar_antigas`) pode migrar para o último passo desta rotina
  (a 272 previu isso); decisão da spec da 286.

**Fora de escopo.** Mandar algo à cliente · e-mail para a equipe · juros/multa · agrupar N avisos do
mesmo marco numa notificação só (D8).

**Modelo de dados.** `site_settings.funil_rotina_run_at TIMESTAMP NULL` · `down_revision` = 283.

**Endpoints.** Nenhum HTTP novo (`flask funil-rotina --forcar` para o verify; `GET /api/dashboard`
e o detalhe do evento não mudam).

**UI.** Nenhuma tela nova: as notificações caem no sino da 272 com deep link; o `kind` ganha ícone
e rótulo em `NotificacaoItem` e nas preferências (281).

**Reusa.** `invite_reminders.py` inteiro como molde · `_start_invite_reminders` (`__init__.py:427`) ·
`notificacoes_ops.emitir` (272) · `entradas_ops` (284) · `_serialize_mensagens` · `_bloco()` (271)
como desenho do isolamento por passo.

**Notificação (272).** `KIND_PARCELA_VENCE = "parcela.vence"` + entrada em `DESTINATARIOS_POR_KIND`
(FINANCEIRO, SUPERADMIN) + `notificar_parcela_vence()` com `destinatarios` explícito acrescentando
o vendedor.

**Riscos e como o verify cobre.**
- 36 threads no gunicorn: o claim é obrigatório. *Verify:* duas chamadas concorrentes de `rodar`,
  uma ganha; fora da janela sem `forcar` → `pulados.fora_do_horario`.
- Ruído no primeiro dia: corte por `ATIVACAO` + passada da financeira + preferências (281).
  *Verify:* parcela vencida antes de `ATIVACAO` não gera nada.
- Rotina roda em thread do gunicorn (incidente 263): poucas consultas com `in_()`, sem I/O externo.
  *Verify:* tempo da rodada no dump < 2 s.
- *Verify também:* parcela vencendo em 3 dias → 1 linha `parcela.vence:<id>:D-3` por FINANCEIRO
  ativo + 1 para o vendedor (conexão separada); rodar de novo → 0 (UNIQUE da 272); baixar a parcela
  (283) e rodar → nada · vencida há 3 dias → `D+3` `urgent` · evento sem cronograma com saldo → chave
  `evento-<id>` · usuário com mute em `parcela.vence` (281) não recebe · passo `cobranca` levantando
  exceção (monkeypatch) → os outros passos rodam e o log tem o nome · `--forcar` só em
  `FLASK_ENV=development`.

**Dependências.** 272 e 281 em produção, 284. **Não sobe antes da 281.**

---

## 6. Onda 4 — o ciclo se fecha

**Objetivo.** Pós-evento e recompra deixam de ser memória: o pedido de avaliação ganha rastro e
fila, o orçamento parado cobra follow-up de quem vendeu, o aniversário da criança vira lista de
reativação, duplicatas se fundem sem perder festa nenhuma, e tudo se acha por uma busca só. Todos
os produtores entram como passo da rotina da 286.

### 287 — Pedido de avaliação com rastro + fila na Home + `avaliacao.pedido_pendente`

**Problema.** `feedback_link_pendente = not client_feedbacks` (`agenda_read.py:966`): o sistema só
sabe que o pedido foi feito quando a resposta chega; `POST /events/<id>/feedback-link`
(`agenda_write.py:1812-1838`) gera o token e devolve a URL sem rastro de quem copiou. No espelho:
123 eventos vendidos e realizados em 2026, 30 com token, 13 com resposta — 93 nunca tiveram o link
gerado e a tela diz "pendente" igual para "pedimos" e "ninguém pediu". `FeedbackSection.tsx:94`
pede para "copiar o link e enviar à cliente" à mão, sem lembrar de qual evento. A 272 já desenhou
`avaliacao.pedido_pendente:<event_id>` (D+1 sem link enviado) e `avaliacao.recebida` já é v1 —
nada a duplicar aqui.

**Escopo.**
- Migration #8: `calendar_events.feedback_requested_at` (DateTime, relógio de `confirmed_at`,
  `models.py:276`) e `feedback_requested_by_id` (FK `users`, nullable). Backfill: eventos com
  `feedback_token` não nulo (30) ganham `feedback_requested_at = NULL` **e** ficam fora da fila por
  já terem token — "pedido em data desconhecida" na tela, nunca data inventada.
- `POST /events/<id>/feedback-link` carimba na primeira vez (`event_ops.registrar_pedido_de_avaliacao`,
  na mesma transação de `ensure_feedback_token`, `event_ops.py:1125-1135`) — nesta casa copiar **é**
  pedir (WhatsApp manual). `DELETE /events/<id>/feedback-request` desfaz (toast "marcado como
  pedido — desfazer").
- Payload: `feedback_status: 'sem_pedido'|'pedido'|'respondido'`, `feedback_requested_at`,
  `feedback_requested_by_name`; `feedback_link_pendente` mantido uma versão como derivado.
- `feedback_ops.eventos_para_pedir_avaliacao(hoje)` (puro, `app/feedback/feedback_ops.py` já
  existe): eventos com venda, não cancelados, não ENSAIO/VIRTUAL, com cliente, terminados entre D+1
  e D+7, sem `ClientFeedback`, sem `feedback_requested_at` e sem token. Fonte única da Home e da
  rotina.
- Home: bloco `avaliacoes` (sob `show_comercial`, via `_bloco`) com "Copiar pedido" (chama o POST,
  que carimba, e copia `buildFeedbackMsg`) e link `/events/<id>?aba=historico`. **Só leitura**: o
  bloco não carimba nada por conta própria.
- Passo `avaliacao` da rotina (286): para cada evento de `eventos_para_pedir_avaliacao(hoje)`
  realizado em D+1 → `notificar_avaliacao_pendente(event)` com `dedupe_key =
  avaliacao.pedido_pendente:<event_id>`, destinatários COMERCIAL (+ vendedor explícito), corpo com a
  mensagem pronta e o link público já gerado (`ensure_feedback_token` na rotina; `PUBLIC_BASE_URL`,
  nunca `request.url_root`).
- `EventHeader.tsx:276-284`: rótulo "Pedido em dd/mm por X", desabilitar só quando respondido;
  `FeedbackSection`: três estados.

**Fora de escopo.** Envio automático à cliente (descartado — apêndice) · segundo pedido D+7 (só
depois de medir taxa de resposta com o rastro) · avaliação do artista (`EventRating`).

**Modelo de dados.** `calendar_events.feedback_requested_at TIMESTAMP NULL` ·
`feedback_requested_by_id INTEGER NULL FK users ON DELETE SET NULL` · `down_revision` = 286.

**Endpoints.** `POST /api/events/<id>/feedback-link` — carimba · `DELETE
/api/events/<id>/feedback-request` (novo; gate `_can_confirm`, `agenda_write.py:63`) ·
`GET /api/events/<id>` — `feedback_status`… · `GET /api/dashboard` — bloco `avaliacoes[]`.

**UI.** `components/EventDetail/EventHeader.tsx` · `FeedbackSection.tsx` · `pages/DashboardPage.tsx`
(painel "Avaliações a pedir", loading por item, invalida `["dashboard"]` ao copiar).

**Reusa.** `agenda_write.py:1812` · `event_ops.py:1125` · `EventHeader.tsx:19-20`
(`buildFeedbackMsg`, `useFeedbackLink`) · `_bloco()` · `_base_filters` · rotina da 286.

**Notificação (272).** `KIND_AVALIACAO_PENDENTE = "avaliacao.pedido_pendente"` → COMERCIAL,
SUPERADMIN (+ vendedor). `avaliacao.recebida` já existe (v1) — não se toca.

**Riscos e como o verify cobre.**
- Copiar = pedir é inferência; o desfazer e o registro de quem copiou são a defesa (D9).
- Passivo: D+1..D+7 limita a fila a uma semana e a rotina só considera eventos terminados ≥
  `ATIVACAO`. *Verify:* evento de 2025 sem feedback não entra.
- *Verify também:* POST carimba uma vez (segunda chamada não altera; conexão separada) · evento de
  ontem com venda e sem feedback → na fila; após POST → sai; com `ClientFeedback` → sai;
  cancelado/ensaio/virtual → nunca entra · rotina: evento D+1 → 1 notificação ao vendedor e aos
  COMERCIAL com URL pública que responde 200 em `GET /api/avaliar/<token>`; rodar de novo → 0 ·
  `feedback_status` percorre os três estados · backfill: os 30 com token ficam fora da fila e sem
  data inventada · CASTING não recebe o bloco · na tela: copiar pelo painel, item some, header
  mostra "Pedido em …", desfazer volta.

**Dependências.** 286 (thread) — pode nascer só com a fila na Home se a 286 atrasar.

### 288 — Follow-up de orçamento aberto por negociação: `orcamento.followup`

**Problema.** Depois da 275 o banco sabe quais negociações estão abertas e o histórico tem o KPI;
ninguém é avisado. Sem rotina, o desfecho fica opcional e "aberto" volta a mentir. A 272 reservou
`orcamento.followup:<orcamento_id>:<dia>` para o vendedor.

**Escopo.**
- Passo `followup` da rotina (286): `quote_ops.negociacoes_abertas(hoje, dias=7)` (275) filtrada por
  `utc_para_sp(created_at) ≥ ATIVACAO` (princípio 6 — `created_at` do orçamento é UTC) e
  `lost_reason` ausente; uma notificação **por negociação**, com
  `dedupe_key = orcamento.followup:<id do orçamento mais recente da negociação>:d7`, destinatário =
  `user_id` do orçamento (vendedor), `link_path=/orcamento/<id>`, corpo com cliente, data da festa,
  total 4h e "marque perdido ou vincule ao evento". Um marco só (d7) na v1.
- Histórico: filtro "aguardando follow-up" (`?followup=pendente`) e coluna "dias em aberto" (275
  já entrega `dias_em_aberto`).

**Fora de escopo.** d3/d14 · follow-up de EducaManto (39 no total, ciclo escolar) · arquivar em
massa os ~1.700 antigos (o filtro do histórico é a ferramenta; a decisão é humana) · funil no
Dashboard Comercial com medianas e motivos de perda (descartado — apêndice).

**Modelo de dados.** Nenhuma migration.

**Endpoints.** `GET /api/orcamento/historico?followup=pendente`.

**UI.** `pages/OrcamentoHistoricoPage.tsx` (filtro e coluna).

**Reusa.** 275 (`negociacoes_abertas`, `status_do_orcamento`) · 286 (rotina) · 272.

**Notificação (272).** `KIND_ORCAMENTO_FOLLOWUP = "orcamento.followup"` → vendedor (lista
explícita); SUPERADMIN só se for o vendedor.

**Riscos e como o verify cobre.**
- Sem o corte por `ATIVACAO` a primeira rodada geraria ~1.700 avisos — o corte é regra, não
  otimização. *Verify:* orçamento anterior à ativação nunca entra.
- *Verify também:* negociação com 4 salvamentos, aberta há 8 dias → **1** notificação ao vendedor
  (chave do mais recente); rodar de novo → 0; ganha/perdida → 0; `lost_reason='teste'` → 0 · filtro
  `followup=pendente` bate com o que a rotina avisou.

**Dependências.** 275, 286.

### 289 — Reativação por aniversário da criança: lista em `/clientes` + `aniversario.crianca`

**Problema.** O aniversário da criança não gera nada (análise §3.4), embora a data da última festa
— evento ou resposta de formulário, inclusive o histórico pré-2026 importado do WhatsForm — seja o
melhor indicador de quando a próxima acontece. A idade existe só como texto na resposta
(`idade_aniversariante`, 63 respostas) e o formulário pede "idade a completar", não nascimento. A
272 reservou `aniversario.crianca:<client_id>:<ano>` para COMERCIAL.

**Escopo.**
- `client_ops.proximos_aniversarios(hoje, dias=60)` (puro, agregação em SQL, não laço): última
  festa infantil por cliente = max(`start_at` dos eventos via `EventClient`/`client_id` com tipo
  não CORP/ENSAIO/VIRTUAL; `FormResponse.event_date` com `form_type='comum'`); próxima data = mesma
  data no primeiro ano ≥ hoje; entra se cai na janela, a cliente não tem evento futuro nem resposta
  futura; traz nome/idade do aniversariante quando a resposta tem (`extrair_para_orcamento`, 277).
  **Derivado, sem tabela de crianças**: o dado é estimado ("por volta de dd/mm"), e uma tabela
  congelaria uma estimativa.
- `GET /api/clientes/reativacao?dias=60` (gate `_require_vendas` de clientes).
- `/clientes`: aba "Reativação" (`?aba=`) com nome, festa anterior (link ao evento ou
  `/formularios?resposta=`), data prevista "aproximada", WhatsApp e "Copiar mensagem" (constante no
  cliente); sem telefone válido → sem botão; estado vazio honesto.
- Ficha: card "Aniversariantes" derivado do histórico (nome, idade na última festa, próxima data
  estimada).
- Passo `aniversario` da rotina (286): itens que entram na janela de 60 dias →
  `notificar_aniversario(client, ano)` com `dedupe_key = aniversario.crianca:<client_id>:<ano>`,
  COMERCIAL, link para a ficha. Um por cliente por ano — a chave garante, sem coluna de rastro.

**Fora de escopo.** Tabela de crianças com backfill (descartado — apêndice) · rastro
"contatada/descartada" (a janela rotaciona sozinha; se virar rotina, entra coluna) · data de
nascimento real (mudança de formulário) · envio automático.

**Modelo de dados.** Nenhuma migration.

**Endpoints.** `GET /api/clientes/reativacao?dias=` (novo) · `GET /api/clientes/<id>` —
`aniversariantes[]` derivado.

**UI.** `pages/ClientsListPage.tsx` (aba) · `pages/ClientDetailPage.tsx` (card) · mobile-first em
cartões.

**Reusa.** `client_ops.py:132,162` · `models.py:1906` (`whatsapp_number`) · `_base_filters` ·
deep-link `?resposta=` (266) · 277 (chaves do aniversariante) · 286.

**Notificação (272).** `KIND_ANIVERSARIO = "aniversario.crianca"` → COMERCIAL, SUPERADMIN.

**Riscos e como o verify cobre.**
- Festa não é sempre no aniversário; a janela de 60 dias absorve e a tela diz "aproximada".
- Duplicata de cliente recebe reativação indevida — a 290 reduz; se a lista de duplicatas for
  grande, 290 antes de 289.
- *Verify:* festa em 15/10/2025, hoje 01/09/2026 → 15/10/2026 na lista; evento futuro marcado → fora;
  só CORP → fora · cliente só com resposta de 2024 → projetado para 2026 · `dias=30` exclui quem cai
  no dia 45 · rotina: 1 notificação `aniversario.crianca:<client>:2026`; rodar de novo → 0; ano
  seguinte (relógio) → nova · CASTING → 403.

**Dependências.** 286.

### 290 — Mesclar clientes duplicadas

**Problema.** Não existe mesclagem (análise §3.2). 312 nomes repetidos em 1.257 fichas (DDI, 9º
dígito, número da mãe e do pai). `delete_client` (`client_ops.py:238-253`) desvincula
`event_clients`, `calendar_events.client_id` e `form_responses.client_id`, e não conhece
`nfc_tags.client_id` (`models.py:2329`, `ondelete="SET NULL"` — a exclusão **não falha**, o Postgres
anula sozinho; o que se perde é o vínculo da luminária com a cliente, em silêncio). As
ondas 2 acrescentaram `orcamento_history.client_id` (274) e `educamanto_quotes.client_id` (279):
repontar na mão é convite a órfão. A 280 devolve 409 ao corrigir telefone para um que já existe,
sem oferecer saída.

**Escopo.**
- `client_ops.merge_clients(manter, absorver, *, actor) -> dict` (puro, sem commit, transação
  única): repontar **todas** as FKs de uma lista declarada `_FKS_PARA_CLIENTE` no módulo
  (`calendar_events.client_id`, `event_clients.client_id`, `form_responses.client_id` preservando
  `client_link_source`, `nfc_tags.client_id`, `orcamento_history.client_id`,
  `educamanto_quotes.client_id`); `event_clients` faz `UPDATE` e apaga a linha da absorvida quando
  a mantida já está no evento (mantém a relação da mantida; registra a perdida no `audit()`);
  campos vazios da mantida herdam da absorvida (email, company, cpf, cnpj, address, utm_*, lead_*,
  kommo_*); `notes` concatena com data; `created_at` mais antigo vence; `audit()` (`utils.py:46`)
  com snapshot JSON completo da absorvida e as contagens movidas; depois `db.session.delete` —
  **não** reusar `delete_client` (ela anula em vez de mover). Mesma ficha → 400.
- Detector `client_ops.candidatos_duplicata(client)`: mesmo nome sem acento
  (`unaccent_lower_sql`, `utils.py:21`; `_name_search_conditions`, `client_ops.py:41`), mesmo
  e-mail, ou telefone igual sem DDI/9º dígito. `GET /api/clientes/duplicatas` lista pares com
  contagens por lado.
- `POST /api/clientes/<manter_id>/mesclar {absorver_id}` — gate do `DELETE`
  (SUPERADMIN/FINANCEIRO, `clientes_write.py:95-99`); devolve a ficha mantida + contagens.
- UI: ficha → "Mesclar com…" (`ClientPicker`) → `ConfirmDialog` com prévia (o que migra, campos
  herdados, qual telefone fica — e que a auto-associação da 266 passa a casar só o telefone
  mantido); `/clientes` → card "Possíveis duplicatas (N)"; o 409 da 280 vira "Já existe a ficha X —
  mesclar?".

**Fora de escopo.** Mesclagem automática · desfazer pela tela (o snapshot no `AuditLog` permite
reconstruir por script) · deduplicar talentos (`Talent.cpf` UNIQUE já resolve) · `UNIQUE(event_id,
client_id)` em `event_clients` por migration (D10).

**Modelo de dados.** Nenhuma migration.

**Endpoints.** `POST /api/clientes/<id>/mesclar` (novo) · `GET /api/clientes/duplicatas` e
`GET /api/clientes/<id>/duplicatas` (gate `_require_vendas`).

**UI.** `pages/ClientDetailPage.tsx` (ação, prévia, bloco "Possíveis duplicatas") ·
`pages/ClientsListPage.tsx` (contador) · diálogo Editar (280) oferece mesclar no 409 · invalida
`["clientes"]`, `["cliente", id]`, `["dashboard"]`, `["formularios"]`.

**Reusa.** `client_ops.py:238` (inventário inicial) · `utils.py:21,46` · `ClientPicker` ·
`ConfirmDialog` · 409 estruturado da 280.

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- Uma FK esquecida = `IntegrityError` no delete quando a FK não tem `ondelete` (foi o bug da 266,
  em `form_responses`) ou **perda silenciosa** quando tem `SET NULL` (`nfc_tags`, e as FKs da 274/279
  nascem assim) — a segunda é pior porque não avisa. **O verify enumera as FKs para `clients.id`
  em `information_schema.table_constraints` / `key_column_usage` e falha se o conjunto diferir de
  `_FKS_PARA_CLIENTE`** — é o teste que protege toda feature futura que criar FK para cliente, e
  é o único que pega a perda silenciosa.
- Mesclar a ficha errada é irreversível na tela; por isso o gate da exclusão e a prévia.
- *Verify também:* duas fichas com evento, `EventClient`, resposta, tag NFC, orçamento e EducaManto
  na absorvida → tudo aponta para a mantida, absorvida não existe, `AuditLog` com snapshot (conexão
  separada) · mesmo evento nas duas → uma linha em `event_clients` · campos vazios herdados,
  preenchidos preservados · `duplicatas` acha nome sem acento e e-mail; não acha telefone idêntico
  (UNIQUE já impede) · consigo mesma → 400; inexistente → 404; COMERCIAL → 403 no mesclar, 200 no
  detector · na tela: pelo kebab e pelo 409 da 280.

**Dependências.** 274, 279, 280.

### 291 — Busca global ⌘K (federando as buscas que já existem)

**Problema.** Cada domínio tem a sua busca no servidor — `search_events` (`event_ops.py:1234`, via
`GET /api/agenda/search`, `agenda.py:45`), `search_clients` (`client_ops.py:51`, `clientes_read.py:43`),
`search_responses` (`formularios_ops.py:100`, `formularios_admin_read.py:89`), diretório de talentos
(`talents_read.py:30-36` → `talent_ops.search_talents`, `:67`), histórico de orçamentos `?q=` — e
cada uma só é alcançável de dentro da própria tela. Não há nenhum atalho global: os `keydown` em
`document` são todos "Esc fecha" — `KebabMenu.tsx:100`, `Modal.tsx:27`,
`notificacoes/NotificacoesBell.tsx:53` (272) e `FilterDropdown` do `@manto/ui`
(`filter-dropdown.tsx:38`) — e o único em `window` é o player da Revisão
(`revisao/useVideoPlayer.ts:118`: espaço e setas, sem checar foco). Quem atende um WhatsApp com um
telefone na mão precisa saber em qual tela procurar.

**Escopo.**
- `components/CommandPalette.tsx` no `AppShell`: ⌘K/Ctrl+K (ignorado com foco em
  input/textarea/contenteditable; o handler do player da Revisão continua vendo espaço/setas e
  não vê ⌘K — nenhum dos dois faz `stopPropagation`, e a paleta aberta pausa o player por foco no
  input) e botão "Buscar ⌘K" com `<kbd>`; `Dialog` do `@manto/ui`
  (centralização por flex — armadilha registrada); um input com debounce 250 ms e mínimo 2
  caracteres (`SEARCH_MIN_CHARS`, `event_ops.py:1230`); grupos Eventos, Clientes, Pré-contratos,
  Talentos, Orçamentos; ↑↓ Enter Esc; `useReducedMotion`; recentes em `localStorage` (5).
- **Federação no cliente**, cinco requisições em paralelo com `Promise.allSettled` e
  `AbortController`; grupo cujo endpoint devolve 403 simplesmente não renderiza — o RBAC é o de
  cada endpoint, nenhum `if` de papel no cliente, nenhum endpoint agregado (que exigiria um gate
  composto novo). Destinos: `/events/:id`, `/clientes/:id`, `/formularios?resposta=:id` (266),
  `/talents/:id`, `/orcamento/:id`. Linha secundária útil por tipo (data + cliente; telefone;
  data da festa + `lead_status`; personagens; status 275 + total 4h).

**Fora de escopo.** Endpoint agregado · busca em financeiro/gastos/catálogo · ações no palette ·
full-text.

**Modelo de dados.** Nenhuma migration.

**Endpoints.** Nenhum novo.

**UI.** `components/AppShell.tsx` (atalho + botão) · `components/CommandPalette.tsx`.

**Reusa.** as cinco buscas existentes · `@manto/ui` `Dialog` · deep-link da 266.

**Notificação (272).** Nenhuma.

**Riscos e como o verify cobre.**
- Impersonação: os endpoints de clientes/formulários/orçamento ignoram "Ver como" (docs/05 §3.5) e
  o da agenda respeita — SUPERADMIN em "Ver como CASTING" veria Clientes e não veria nome de
  cliente nos Eventos. Registrado como comportamento dos módulos (princípio 8); o verify de tela
  documenta o resultado. Consertar é a dívida #9, não esta feature.
- Cinco requisições por tecla: debounce, mínimo de 2, `LIMIT` no servidor. *Verify:* 1 caractere →
  nenhuma requisição; digitação rápida → só a última resposta renderiza.
- *Verify também:* telefone parcial → Eventos e Clientes preenchidos; CASTING → grupos de
  clientes/pré-contratos/orçamentos ausentes sem erro · Enter navega e fecha; Esc fecha; voltar não
  reabre · mobile 375px: paleta ocupa a tela, teclado não cobre o input · Ctrl+K com foco num input
  não abre.

**Dependências.** Nenhuma — puxável para qualquer ponto se a equipe pedir o atalho antes.

---

## 7. Ordem de execução recomendada

```
272 ──► 273 ─► 274 ─► 275 ─► 276 ─► 277 ─► 278 ─► 279 ─► 280        (onda 2)
                 │
                 └──────────────────────────────────────► 281       (pré-onda 3)
282 ─► 283 ─► 284 ─► 285 ──────────────────────────────► 286        (onda 3)
                                                          ├─► 287 ─► 288 ─► 289
                                                          └─► 290 · 291 (a qualquer hora)
```

**Por quê nesta ordem.**

- **272 antes de tudo que tem migration** (274 é a primeira): a cadeia de `down_revision` começa
  em `b7d2e4f1a9c3`. Enquanto a 272 não mergeia, a onda 2 avança pelas features sem migration —
  273, 280, 282 e 291 não dependem de nada e podem subir hoje.
- **273 antes de 274/275**: o vínculo destrava o "ganho" derivado, resolve os 9 eventos do Google
  com venda já na primeira semana, e não tem migration — é o melhor primeiro deploy do programa.
- **274 → 275 → 276**: FK antes do status, status antes do arquivamento. Três migrations pequenas
  em sequência; podem subir num deploy só se ficarem prontas juntas (ensaio conjunto no dump).
- **277 → 278**: a extração das chaves do formulário (277) alimenta o prefill do evento (278).
- **279 e 280 fecham a onda 2** — 279 tem migration (última da onda, encadeia na 276); 280 não tem
  e pode subir a qualquer momento antes ou depois.
- **281 antes da 286, sem exceção**: é a condição da própria 272 para a onda 3.
- **282 → 283 → 284 → 285**: editor antes da baixa (senão a primeira edição apaga a baixa), baixa
  antes do saldo único (a regra depende de `payment_id`), saldo único antes da aba (que só lê).
  **A 285 cai primeiro se a onda apertar.**
- **286 depois de 284 e 281**: a rotina só existe para chamar `parcelas_em_aberto`, e só pode
  ligar com preferências.
- **Onda 4 na ordem 287 → 288 → 289**: cada uma é um passo a mais na mesma rotina; 287 ainda
  entrega a fila na Home se a 286 atrasar. **290 depois de 274/279/280** (todas as FKs para cliente
  já existem) e **antes de 289** se o detector mostrar muitas duplicatas. **291 a qualquer hora.**

**O que anda em paralelo.** 273 ‖ 280 ‖ 282 ‖ 291 (nenhuma depende de nada) · 276 ‖ 277 (depois
da 275/274) · 285 ‖ 286 (as duas leem a 284) · 290 ‖ 287. Regra para o deploy: features prontas
juntas sobem juntas, mas **nunca duas migrations no mesmo dia sem ensaio conjunto** no dump.

---

## 8. Riscos globais e decisões em aberto para o dono

### Riscos globais

1. **Oito migrations em três ondas.** Cada uma passa pelo ensaio no dump do dia do merge (não de
   semanas antes), `flask db heads` único antes e depois, `upgrade → downgrade → upgrade`. Nunca
   autogenerate; nunca `raise` dentro do `upgrade` (princípio 4). A única que toca coluna
   existente é o `DROP NOT NULL` de `file_path` (283). Duas (279, 287) acrescentam coluna e índice
   em `calendar_events`, a tabela mais quente: `ADD COLUMN NULL` é instantâneo e o `CREATE INDEX`
   sem `CONCURRENTLY` toma um lock breve — cabe na janela de 502, mas **nunca as duas no mesmo
   deploy sem ensaio conjunto**.
2. **Números que a equipe já confere vão mudar** — painel de cobranças da Home (284), KPI de
   cobrança do evento (283), avaliações por cliente (280), contadores de resposta (276). Regra:
   cada verify compara antes/depois no mesmo banco e explica cada diferença por uma regra nova
   nomeada; diferença sem explicação bloqueia o merge, e a entrada em `docs/03` diz o que mudou.
3. **Impersonação** (docs/05 §3.5): ficha mostrando orçamentos, Home mostrando parcelas e ⌘K
   federando módulos cruzam gates que tratam "Ver como" de forma diferente. Princípio 8: dashboard
   respeita, módulo ignora, verify testa os dois lados e registra. Consertar a dívida #9 continua
   sendo trabalho próprio — este programa multiplica consumidores, então **o conserto fica mais
   urgente, não menos**.
4. **Passivo herdado vira ruído** — 1.700 orçamentos abertos, 5 parcelas vencidas de 2025 (R$
   157.940), ~93 eventos sem pedido de avaliação. Toda rotina tem `ATIVACAO`; toda fila da Home
   tem janela; cada onda entrega um oneoff dry-run que lista o passivo para a passada humana. Se o
   primeiro dia de notificações for um dilúvio, a equipe aprende a ignorar o sino — o mesmo motivo
   que matou o e-mail.
5. **Home é a página de entrada** e foi o incidente de 01/09: cada bloco novo passa por `_bloco()`,
   é uma query com `joinedload`, e o verify mede o tempo do payload. Nenhum bloco escreve.
6. **Cache do bundle** (memória `manto_deploy_cache_bundle`): 282/283 mudam o contrato de
   `PUT /parcelas` e 285 acrescenta `?aba=`. O servidor degrada para o comportamento antigo ou para
   409, nunca para perda — e o verify manda o corpo antigo de propósito.
7. **Threads no gunicorn** (36 slots): a 286 é a **oitava** thread por worker e hospeda quatro
   passos; qualquer passo sem claim duplica avisos ×3. Um claim para a rodada inteira; verify
   simula concorrência; tempo medido.
8. **`file_path` nullable** (283) muda a semântica de "comprovante" para o auditor 221 e para
   qualquer leitor que faça `open(file_path)` — inventário por grep antes do merge.
9. **Gêmeos Jinja vivos pelo host** (`calendar/routes.py:1821`, `financeiro/routes.py:470`) leem
   `received`: por isso a coluna fica e é mantida coerente, em vez de cair.
10. **Documentação que mente** enquanto o programa anda: `docs/04:142-151` (comissão que a 267
    já sincroniza, agrupar que a 246 já expôs, parcelas "só Jinja"), `docs/00:32`/`docs/04:426`
    (7 threads → 8 com a 286). Princípio 14.

### Decisões em aberto (cada uma com a recomendação padrão)

| # | Pergunta | Recomendação |
|---|---|---|
| **D1** | Aplicar valores do orçamento a um evento já existente (273 `aplicar_duracao`) pode sobrescrever venda digitada à mão? | **Não sobrescreve venda existente**: `aplicar_duracao` só é oferecido quando `sale_value` é nulo; com venda, o vínculo é rastro. Sobrescrever é uma linha na spec se o dono quiser. |
| **D1b** | Ao aplicar valores num evento do Google vendido meses atrás, `sale_date` é hoje ou a data real da venda? | **A comercial informa** (`sale_date?` opcional no corpo, default hoje SP). A comissão entra pelo mês de `sale_date` (docs/04 §2 ramo 7): "hoje" jogaria venda de maio no Dashboard Comercial de setembro. |
| **D2** | Comercial pode marcar orçamento como perdido de outro comercial? | **Não** — mesma regra do histórico (dono ou superadmin). O superadmin arquiva o passivo. |
| **D3** | `orcamento_history.event_date` é `String(20)`: mudar para `DATE`? | **Não agora.** 0 linhas fora do ISO no espelho; comparação lexicográfica de ISO já serve para filtros; onde precisa de aritmética (dias até a festa) usa `CAST` guardado por `~ '^\d{4}-\d{2}-\d{2}$'` numa expressão única em `quote_ops`. `ALTER TYPE` em produção sem necessidade é risco puro. |
| **D4** | Baixa exige comprovante? | **Não** — arquivo opcional (PIX chega sem papel); o auditor 221 aponta "sem comprovante" como achado. Exigir obrigaria upload de captura de tela e a financeira deixaria de dar baixa. |
| **D5** | COMERCIAL pode dar baixa em parcela? | **Sim** — paridade com `PUT /parcelas`, e a casa recebe PIX pelo comercial. Estreitar para FINANCEIRO/SUPERADMIN é uma linha. |
| **D5b** | `PATCH /api/payments/<id>` (corrigir valor, anexar comprovante) sai de SUPERADMIN para `_can_manage_sale`? | **Sim** — hoje a financeira não consegue preencher os 24 `amount` nulos nem anexar nada; corrigir dinheiro é do mesmo risco que registrar. `DELETE /payments/<id>` **fica SUPERADMIN**: apagar prova é outro risco. Se o dono preferir manter o `PATCH` fechado, os 24 são corrigidos por script do superadmin. |
| **D6** | A calculadora passa a coletar forma de pagamento/parcelamento para o evento herdar? | **Sim, mas fora deste programa**: é campo novo na calculadora e no snapshot (feature própria, sem migration). Até lá, o prefill do evento herda `payment_method` da **resposta** (278), não do orçamento. |
| **D7** | Severidade `urgent` fura o mute por `kind` (281)? | **Não na v1** — regra simples; nota ≤ 2 chega pelo `avaliacao.recebida`, que ninguém tem motivo para silenciar. |
| **D8** | Agrupar N avisos do mesmo marco numa notificação só (286)? | **Não na v1** — há 5 parcelas no banco inteiro; a preferência por `kind` (281) resolve o ruído. Reavaliar com volume medido após 30 dias. |
| **D9** | Copiar o link de avaliação = pedido feito (287)? | **Sim**, com "desfazer" e registro de quem copiou. Botão explícito "Marcar como pedido" fica como alternativa na spec, a confirmar com a comercial. |
| **D10** | `UNIQUE(event_id, client_id)` em `event_clients` por migration (290)? | **Não** — 0 duplicatas no espelho por disciplina do código; `merge_clients` trata o caso; uma UNIQUE em tabela existente pode derrubar o `startCommand` se a produção divergir do dump. Registrar como candidata futura. |
| **D11** | Quem recebe `parcela.vence` (286)? | FINANCEIRO + vendedor do evento (como a 272 desenhou); SUPERADMIN pelo papel, silenciável pela 281. |
| **D12** | Passivo de parcelas de 2025 (R$ 157.940): baixar, apagar ou deixar? | **Passada humana pela aba Entradas (285) antes de ligar a 286**: o que foi recebido ganha baixa retroativa com comprovante quando houver; o que é lixo é apagado pelo editor (282). A rotina nunca avisa sobre isso. |
| **D13** | Os outros e-mails internos (ensaio, gasto novo, produção de figurino — tabela da 272) viram `kind`? | Fora deste programa; cada um é uma decisão do dono. A 286 já tem onde encaixar. |
| **D14** | Apagar um orçamento que está vinculado a evento vivo (273)? | **409 com o `event_id`** ("desvincule na aba Comercial antes"). Hoje estoura `IntegrityError`; com a relationship da 273 passaria a anular o FK em silêncio e o "ganho" da 275 sumiria sem rastro. Com só eventos cancelados apontando, desvincula com `audit()` e apaga. |

---

## Apêndice — o que foi considerado e descartado

Ideias que apareceram no desenho das ondas e não entraram, com o porquê — para não serem
reinventadas.

- **Coluna `status` escrita no orçamento (`aberto|ganho|perdido`) com backfill.** "Ganho" escrito
  divergiria do FK no cancelamento do evento (267 decisão 5) e exigiria backfill; derivado do FK
  não exige nada e nunca diverge. Só "perdido" é escrito (275).
- **`ALTER TYPE` de `orcamento_history.event_date` para `DATE`** com `USING CASE`. Única migration
  não-aditiva que se cogitou; 0 linhas fora do ISO tornam desnecessária; `legacy_quote`
  (`quote_ops.py:588-597`) e `_build_orcamento_prefill` leem o texto. Ver D3.
- **`DROP COLUMN received`** com "recebida = `payment_id IS NOT NULL`". Cinco leitores, dois em
  Jinja vivo pelo host; esquecer um derruba o boot sem aparecer em tela nenhuma. A coluna fica e é
  mantida coerente com `payment_id` (283).
- **Comprovante obrigatório para dar baixa** e **`amount NOT NULL` por migration**. Mudam a rotina
  da financeira sem o dono decidir; `amount` passa a ser obrigatório só na API (283) e a coluna
  espera os 24 serem corrigidos.
- **Tabela `rotinas_fundo` para claims.** O padrão vigente é coluna no singleton `site_settings`
  (três já existem); uma tabela nova para o mesmo `UPDATE` condicional é infraestrutura que a
  análise §5 disse não precisar.
- **Tabelas próprias de idempotência por aviso** (`event_cobranca_avisos`, `client_feedback_requests`,
  `orcamento_followups`, `client_reactivations`). Duplicam o `dedupe_key` UNIQUE da 272, que
  existe exatamente para isso ("um por parcela por marco", "um por criança por ano").
- **Uma thread por rotina.** Cada worker já carrega 7; a 272 recusou a oitava para a poda. Uma
  thread hospeda quatro passos isolados (286).
- **E-mail D+1 de pedido de avaliação para a cliente** (opt-in, toggle em `SiteSetting`). Criaria
  a única thread de e-mail nova do programa no momento em que a casa abandona e-mail; 1.038 de
  6.215 clientes têm e-mail; o canal da cliente é WhatsApp. Substituído pelo produtor
  `avaliacao.pedido_pendente` (287). Envio automático à cliente é decisão de negócio própria.
- **Notificação `evento.quitado` ao vendedor quando o saldo zera.** Boa notícia em volume vira
  ruído — mesma razão que descartou `convite.aceito` na 272; o KPI do evento já mostra.
- **Notificação de avaliação recebida / nota baixa.** Já é v1 da 272 (`avaliacao.recebida`, `urgent`
  com nota ≤ 2) — não se duplica.
- **`outcome='perdida'` propagado do orçamento perdido para a resposta.** Escrita cruzada a partir
  da tela de orçamento; a derivação da 275 já mostra "perdida" quando todos os orçamentos
  morreram, e a 276 cobre a resposta que morreu antes de qualquer orçamento.
- **Tabela `client_children` com backfill em Python dentro da migration + `client_reactivations`
  com status.** A data é estimada pela festa; uma tabela congela uma estimativa e o backfill na
  migration é o tipo de código que derruba `flask db upgrade` numa linha de JSON estranha. Derivado
  (289), sem rastro na v1.
- **`UNIQUE(event_id, client_id)` em `event_clients`** e **índice único parcial em
  `educamanto_quote_id`**. UNIQUE em tabela existente pode derrubar o `startCommand`; o merge trata
  o caso; EducaManto não tem status para exigir 1:1. Só o índice parcial de `orcamento_history_id`
  entrou (274), com checagem prévia.
- **Endpoint agregado `GET /api/busca` com `effective_roles`** e um `app/api/rbac.py` novo
  escondido dentro da busca. Um gate composto novo é exatamente o que a dívida #8/#9 pede que seja
  feito como feature própria, não de carona; a federação no cliente usa os gates que já existem
  (291).
- **Funil no Dashboard Comercial (respostas → orçamentos → ganhos, medianas, motivos de perda).**
  A análise não pede; depende de a comercial marcar perdido com disciplina por meses antes de o
  número valer algo. Quando os dados existirem, é feature própria.
- **Follow-up em três marcos (d3/d7/d-14).** Um marco (d7) por negociação prova o laço; mais marcos
  sem medir é ruído.
- **Backfill de `client_id` do orçamento por nome.** 534 nomes batem com exatamente uma ficha, mas
  nome não é identidade neste CRM — telefone é. Só por FK (274).
- **Reembolsos a cobrar fora da aba Entradas.** Cogitado excluir; `EventReimbursement` já tem
  `collected_at`/`collected_amount` e é a única entrada com baixa própria — entrou na 285.
- **Card de follow-up na Home.** O filtro do histórico (275) e a notificação ao vendedor (288)
  entregam o valor; a Home é a página de entrada e cada bloco custa.
