# Contrato de API — Agenda/Eventos leitura (145, US1)

Herda as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md`
(sucesso = recurso no corpo; erro = `{"error":{"message","fields"}}`; 401/403/404). Todos os
endpoints exigem sessão (guard `api_login_required`).

## `GET /api/agenda?ym=YYYY-MM`

- Sem `ym`: usa o mês atual.
- 200: `{ "ym": "YYYY-MM", "events": EventoResumo[], "by_day": {"YYYY-MM-DD": [int]} }`
- Lê do banco (`_build_events_from_db`); NÃO dispara sync (sync manual é US5).

## `GET /api/agenda/day/<date>` (date = `YYYY-MM-DD`)

- 200: `{ "day": "YYYY-MM-DD", "events": EventoResumo[] }`
- date inválida: 400 `{"error":{"message":"Data inválida"}}`.

## `GET /api/events/<id>`

- 200: `EventoDetalhe` (ver data-model.md) — blocos financeiros presentes conforme o papel do
  usuário autenticado (RBAC na serialização).
- 404: evento inexistente.
- Evento ENSAIO: retorna o `EventoDetalhe` reduzido (event + logs + material).

## Fora de escopo desta fatia (US2–US5)

Toda ação de escrita: escalar/gerir casting, dados de venda, pagamentos, reembolsos, contrato,
logística, confirmação, convites, agrupamento, criar evento, gerir ensaio, sincronizar, excluir.
Cada uma vira endpoint(s) REST dedicado(s) no `/speckit-plan` da sua fatia.
