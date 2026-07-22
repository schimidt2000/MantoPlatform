# Data Model: Feedback Público por Token em React

Nenhum campo ou tabela novos. Os endpoints só leem `CalendarEvent` (por `feedback_token`) e
criam `ClientFeedback` (`app/models.py`) exatamente como o handler Jinja hoje.

## `GET /api/avaliar/<token>` — resposta

| Campo | Origem |
|---|---|
| `event_title` | `CalendarEvent.title` |
| `event_date` | `CalendarEvent.start_at` formatada `DD/MM/AAAA`, ou `null` se ausente |
| `positive_tags` | `POSITIVE_TAGS` (constante) |
| `attention_tags` | `ATTENTION_TAGS` (constante) |

404 se o token não corresponder a nenhum evento.

## `ClientFeedback` — criado pelo POST (sem mudança de shape)

| Campo | Origem | Observação |
|---|---|---|
| `event_id` | evento resolvido pelo token | — |
| `score` | `score` (1–5) | obrigatório |
| `tags` | `tags[]` filtradas por `_tags_for_score(score)` | opcional, JSON |
| `comment` | `comment`, até 2000 caracteres | opcional |
| `client_name` | `client_name`, até 200 caracteres | obrigatório |
