# Contrato de API — 7 ferramentas migradas

Herda as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md`
(envelope de sucesso/erro, códigos HTTP, `json_error(msg, status, fields=...)`). RBAC replicado
por função no início de cada view (nunca decorator Flask-Login), paridade com os checks já
existentes nas views Jinja de origem (ver `research.md`).

## Gastos Extras (`app/api/gastos_read.py` / `gastos_write.py`) — US1

### `GET /api/gastos`

- RBAC: qualquer autenticado — SUPERADMIN vê todos os gastos, demais usuários só os próprios
  (`created_by_id == current_user.id`), mesma regra da view Jinja `index()`.
- Query params: `status`, `category`, `date_from`, `date_to` (opcionais).
- 200: `{"expenses": [SpecialExpense.to_dict(), ...]}`

### `GET /api/gastos/eventos`

- RBAC: idem — busca de eventos para o seletor "vincular a evento" (equivalente a
  `gastos/api/eventos` hoje sob o blueprint Jinja).
- 200: `{"events": [{"id","label","date"}, ...]}`

### `POST /api/gastos`

- RBAC: qualquer autenticado.
- Body: `{"description","category","amount","expense_date","disbursement_type","reimburse_user_id"?,"supplier_name"?,"supplier_pix"?,"paid_at_creation"?,"notes"?}` + comprovante via multipart (mesma regra de `_save_receipt`).
- 201: `SpecialExpense.to_dict()`
- 400: `fields` aponta o campo inválido (ex. `amount` ≤ 0).

### `POST /api/gastos/<id>/aprovar` / `/rejeitar`

- RBAC: SUPERADMIN.
- 200: `SpecialExpense.to_dict()` atualizado.
- 409: gasto já não está `pendente` (dupla aprovação/rejeição).

### `DELETE /api/gastos/<id>`

- RBAC: SUPERADMIN.
- 204 · 404: gasto não encontrado.

### `POST /api/gastos/<id>/vincular-evento`

- RBAC: SUPERADMIN.
- Body: `{"event_id"}` (`null` desvincula).
- 200: `SpecialExpense.to_dict()`.

## Gastos Recorrentes (mesmo par `gastos_read.py`/`gastos_write.py`) — US3

### `GET /api/gastos/recorrentes`

- RBAC: FINANCEIRO ou SUPERADMIN.
- 200: `{"recurring": [RecurringExpense.to_dict() + "entries": [...]], "alerts": [...]}` (chama
  `ensure_recurring_entries()`/`recurring_alerts()` movidos para `gastos_ops.py`).

### `POST /api/gastos/recorrentes`

- RBAC: FINANCEIRO ou SUPERADMIN.
- Body: shape conforme `expense_type` (`variavel`/`debito_automatico`/`assinatura`/`programado`) — mesmos campos aceitos hoje por `_parse_conta_form`/`_parse_programado_form`.
- 201: `RecurringExpense.to_dict()`

### `PATCH /api/gastos/recorrentes/<id>` · `POST /api/gastos/recorrentes/<id>/toggle` · `DELETE /api/gastos/recorrentes/<id>`

- RBAC: FINANCEIRO ou SUPERADMIN.
- 200/204 conforme ação; `toggle` retorna o registro atualizado (`is_active` invertido).

### `POST /api/gastos/recorrentes/entry/<id>/preencher|pular|pagar|reabrir` · `DELETE /api/gastos/recorrentes/entry/<id>`

- RBAC: FINANCEIRO ou SUPERADMIN.
- 200/204; 409 se a transição de status não é permitida no estado atual (ex. pagar parcela já `pulado` sem valor).

## Calculadora de Orçamento / Transporte (`app/api/orcamento_read.py` / `orcamento_write.py`) — US2

### `GET /api/orcamento/personagens-no-dia`

- RBAC: COMERCIAL ou SUPERADMIN (`_require_vendas`).
- Query: `date`. 200: `{"characters": [...]}` (mesmo shape do endpoint Jinja hoje).

### `GET /api/orcamento/distancia`

- RBAC: idem. Query: `endereco`. 200: `{"km_ida": float}` · erro: `{"error": {...}}` com status propagado de `distance_km_ida`.

### `POST /api/orcamento/calcular`

- RBAC: idem.
- Body: shape do formulário de orçamento (elenco, horas, show, transporte) — mesmo aceito hoje por
  `_process_quote()`, agora `quote_ops.calculate_quote(payload)`.
- 200: `{"result": {...}}` — mesmo shape hoje renderizado em `resultado.html`.
- 400: `fields` aponta a seção inválida (ex. elenco vazio).

### `POST /api/orcamento/salvar`

- RBAC: idem.
- Body: `{"form_snapshot", "result_snapshot", "client_name"?, "event_location"?, "event_date"?}`.
- 201: `OrcamentoHistory.to_dict()` (id do registro criado).

## Configuração de Preços (mesmo par `orcamento_read.py`/`orcamento_write.py`) — US5

### `GET /api/orcamento/settings`

- RBAC: SUPERADMIN (`_require_superadmin`).
- 200: shape de `settings.load()` (valores de ator/cantor/técnico/coordenador/maquiador,
  especiais, tipos de acréscimo).

### `POST /api/orcamento/settings`

- RBAC: SUPERADMIN.
- Body: mesmo shape do GET, parcial ou completo — chama `settings.save()`.
- 200: shape atualizado.

### `POST /api/orcamento/settings/especiais` · `DELETE /api/orcamento/settings/especiais/<nome>`

- RBAC: SUPERADMIN.
- 200/204 — adiciona/remove item especial (`especiais_list()`).

## Orçamentos — histórico + PDF (mesmo par `orcamento_read.py`/`orcamento_write.py`) — US4

### `GET /api/orcamento/historico`

- RBAC: COMERCIAL ou SUPERADMIN — SUPERADMIN vê de todos os usuários, demais só o próprio
  (mesma regra de `is_sa` em `routes.py:714`).
- Query: `q`, `date_from`, `date_to` (opcionais).
- 200: `{"entries": [{"id","created_at","client_name","event_date","total_1h"..."total_4h"}, ...]}`

### `GET /api/orcamento/historico/<id>`

- RBAC: idem, mais checagem de dono (não-SUPERADMIN só vê o próprio registro).
- 200: `{"quote": {...}}` — se registro legado (sem `result_snapshot` completo), passa por
  `quote_ops.legacy_quote(entry)` antes de responder (FR-007).
- 404: não encontrado ou de outro usuário (não-SUPERADMIN).

### `GET /api/orcamento/historico/<id>/pdf`

- RBAC: idem.
- 200: PDF binário (`Content-Type: application/pdf`), via `apiFetchBlob` — reusa
  `app/orcamento/pdf.py:gerar_orcamento_pdf(quote)` sem alteração.

### `POST /api/orcamento/historico/<id>/enviar-email`

- RBAC: idem.
- Body: `{"to"?}` (default: e-mail do cliente do orçamento, se houver).
- 200: `{"sent": true}` · 400/502: falha no envio (mensagem amigável, nunca stack trace).

### `DELETE /api/orcamento/historico/<id>`

- RBAC: idem (dono ou SUPERADMIN).
- 204 · 404.

## Avaliação de Casting (`app/api/ratings_read.py` / `ratings_write.py`) — US6

### `GET /api/ratings`

- RBAC: qualquer autenticado.
- Query: `event_id`, `category`, `date_from`, `date_to` (opcionais).
- 200: `{"ratings": [...], "distribution": {"som": {...}, "figurino": {...}, ...}, "anonymous_mode": bool}`
  — autor/talent avaliado omitido quando `anonymous_mode=true` e requisitante não é SUPERADMIN
  (mesma regra da view Jinja `avaliacoes()`).

### `POST /api/ratings/modo-anonimo`

- RBAC: SUPERADMIN.
- Body: `{"enabled": bool}`.
- 200: `{"anonymous_mode": bool}` — grava em `SiteSetting.ratings_fully_anonymous`.

## Formulários — lado staff (`app/api/formularios_admin_read.py` / `formularios_admin_write.py`) — US7

Não confundir com `app/api/formularios_write.py` (fluxo público `/f/*`, intocado nesta feature).

### `GET /api/formularios/respostas`

- RBAC: COMERCIAL, FINANCEIRO ou SUPERADMIN.
- Query: `q` (busca), `form_type`, `client_id`, `event_id` (opcionais).
- 200: `{"responses": [FormResponse resumida, ...]}`

### `GET /api/formularios/respostas/<id>`

- RBAC: idem. 200: `{"response": {...}, "can_edit_structure": bool}` (`can_edit_structure` só `true` para SUPERADMIN, controla se o editor de campos aparece).

### `POST /api/formularios/respostas/<id>/associar` · `/desassociar` (cliente) · `/vincular-evento` · `/desvincular-evento`

- RBAC: idem. 200: `FormResponse` atualizado — `desvincular-evento`/`desassociar` setam
  `event_link_locked=true` (regra existente, nunca deixar a automação sobrescrever depois).

### `DELETE /api/formularios/respostas/<id>`

- RBAC: SUPERADMIN. 204 · 404.

### `GET /api/formularios/editor/<form_type>`

- RBAC: SUPERADMIN. 200: `{"fields": [FormFieldDefinition.to_dict(), ...]}` agrupados por
  `section_name` na ordem de `order`.

### `POST /api/formularios/editor/<form_type>/campo` · `PATCH /api/formularios/editor/campo/<id>` · `POST /api/formularios/editor/campo/<id>/mover` · `DELETE /api/formularios/editor/campo/<id>`

- RBAC: SUPERADMIN.
- 400/403: tentativa de excluir ou renomear `field_key`/`field_type` de um campo `is_system=true`
  (bloqueado, mesma regra do editor Jinja).

## Fora de escopo desta feature

Qualquer endpoint do fluxo público `/f/*` (schema/submit) — já coberto por
`app/api/formularios_write.py` desde a feature 163. Decommissioning das rotas Jinja legadas das 7
áreas — fora de escopo (strangler-fig, ver spec.md Assumptions).
