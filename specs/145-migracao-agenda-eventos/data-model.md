# Data Model — Agenda/Eventos leitura (145, US1)

Nenhum modelo SQLAlchemy novo. Define o **shape JSON de leitura** derivado das views atuais.
Campos exatos a confirmar lendo os templates (`calendar_list.html`, `calendar_day.html`,
`event_detail.html`) na implementação — abaixo, a estrutura de alto nível já confirmada nas
views.

## EventoResumo (agenda e dia) — `GET /api/agenda`, `/api/agenda/day/<date>`

Espelha o que a agenda lista hoje. Sem dado financeiro (a lista não expõe valores).

| Campo | Tipo | Origem |
|---|---|---|
| `id` | int | `CalendarEvent.id` |
| `title` | string | `CalendarEvent.title` |
| `event_type` | string | `parse_event_type(title)` (SHOW/ENSAIO/...) |
| `start_at` | string ISO \| null | `start_at` |
| `end_at` | string ISO \| null | `end_at` |
| `location` | string \| null | `location` |
| `characters` | string[] | `parse_characters(title)` |
| `is_satellite` | bool | `is_satellite` |
| `group_name` | string \| null | `group_name` |
| `confirmed` | bool | estado de confirmação exibido hoje |

Resposta da agenda: `{ "ym": "YYYY-MM", "events": EventoResumo[], "by_day": {"YYYY-MM-DD": [ids]} }`
(o `by_day` alimenta a visão calendário; a lista usa `events`).

## EventoDetalhe (página do evento) — `GET /api/events/<id>`

Blocos nomeados; **blocos financeiros presentes só conforme o papel** (RBAC na API).

### Sempre presentes
- `event`: id, title, event_type, start_at, end_at, location, confirmed, is_satellite,
  group_name, event_group_size.
- `elenco`: lista de cargos — `{ role_id, character_name, role_type, talent: {id, name}|null,
  figurino_done, invite_status }`. (Sem `availability` — isso é do seletor de casting, US2.)
- `logs`: histórico — `{ ts, actor_name, actor_role, message }` (já formatado em SP).
- `observations`: lista de observações do evento.
- `ratings` / `client_feedbacks`: avaliações do artista e feedback da cliente (só leitura).

### Sob `show_comercial` (COMERCIAL/FINANCEIRO/SUPERADMIN)
- `venda`: sale_value, seller, commission_rate, payment_method, payment_due_date, client(s).
- `kpi`: `{ cost, expenses_total, bv_total, commission, sale_value, group_size, rate }` —
  agregados por grupo comercial (`_group_events`), não pelo evento isolado.
- `cobranca`: `{ enabled, amount_formatado, due_line }`.
- `contratos`: lista `{ id, filename, signed, created_at }`.
- `expenses`: gastos extras aprovados do grupo `{ description, amount, date }`.

### Sob `show_financeiro` (FINANCEIRO/SUPERADMIN)
- `pagamentos`: lista `{ id, amount, method, created_at }` + `received_total`.
- `reembolsos`: lista `{ id, description, amount, is_collected, created_at }` +
  `pendentes_total`.

### Flags de papel (para o front decidir o que exibir, espelhando a view)
`show_casting`, `show_figurino`, `show_comercial`, `show_financeiro`, `show_ensaio`,
`is_superadmin` — calculados no servidor com a mesma lógica de impersonação da view.

> **Regra de ouro (FR-003)**: se um bloco financeiro não é permitido para o papel, ele **não
> aparece no JSON** — não é serializado e depois escondido. Ausência = sem permissão.

## Evento tipo ENSAIO

A view desvia para `ensaio_detail.html` (painel simplificado). Nesta fatia, `GET
/api/events/<id>` para um ENSAIO retorna um `EventoDetalhe` reduzido (event + logs + material
de ensaio, sem painéis de show). A UI de ensaio completa (upload de material etc.) é escrita e
fica para US5; aqui é só exibição.
