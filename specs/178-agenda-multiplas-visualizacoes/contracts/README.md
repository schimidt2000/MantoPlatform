# Contratos — Agenda com múltiplas visualizações

Nenhum contrato de API novo ou alterado nesta feature. As 3 visões consomem exclusivamente os
dois endpoints já existentes e documentados em `specs/145-migracao-agenda-eventos-feature145`:

- `GET /api/agenda?ym=YYYY-MM` — usado pelas visões **Mês** e **Lista**.
- `GET /api/agenda/day/YYYY-MM-DD` — usado pela visão **Dia** (endpoint já implementado no
  backend; esta feature é o primeiro consumidor React dele).

Formato de resposta de ambos: inalterado (ver `data-model.md` desta feature para os campos de
`EventoResumo` reutilizados). Nenhum campo novo é exigido do backend — se a implementação
revelar necessidade de algum ajuste pontual (ex.: um campo faltante), o ajuste deve ser
registrado aqui antes de ser codado, mantendo o princípio "planejar antes de codar".
