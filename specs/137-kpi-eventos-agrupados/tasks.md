# Tasks — KPIs financeiros de evento agrupado (137)

- [X] T001 `app/calendar/routes.py`: função `_group_events(event) -> list[CalendarEvent]`
      (perto das outras helpers de evento) — resolve principal+satélites a partir de
      qualquer membro do grupo; retorna `[event]` quando não agrupado
- [X] T002 [US1] `app/calendar/routes.py` (`event_detail()`): `event_cost`,
      `event_expenses`, `event_bv_total` passam a agregar todos os eventos de
      `_group_events(event)` (hoje: só `event`); `event_expenses_total` continua derivado
      da lista agregada
- [X] T003 [US1] `app/calendar/routes.py` (`event_detail()`): resolver `kpi_event` (=
      `_group_events(event)[0]`, o principal) e usar `kpi_event.sale_value` /
      `kpi_event.sale_value_gross` / `kpi_event.commission_rate` / `kpi_event.seller` no
      cálculo de `event_commission` e no que é passado ao template para o KPI grid — sem
      alterar o formulário "Dados de Venda" (continua editável só via `event`); passar
      `event_group_size = len(_group_events(event))` ao template
- [X] T004 [US1] `app/templates/event_detail.html`: KPI grid passa a usar `kpi_event` no
      lugar de `event` para Venda/Comissão/vendedor; aviso "Valores do contrato inteiro
      (N eventos agrupados)" acima do grid quando `event_group_size > 1`.
      Achado durante a implementação: o KPI grid (e a lista de gastos extras) estava
      dentro do MESMO `{% if not event.is_satellite %}` que o formulário "Dados da
      venda" — ou seja, satélites hoje não mostram NENHUM painel financeiro, nem o
      próprio. Reestruturado: o formulário de edição continua satellite-hidden (só o
      principal edita), mas o KPI grid + lista de gastos extras (`{% if show_financeiro
      %}`) foi movido para FORA desse gate — visível também em satélites, gated só por
      `show_financeiro`. A seção "Contratos e Comprovantes"/pagamentos permanece
      satellite-hidden (fora de escopo desta feature, não foi apontada como problema).
- [X] T005 [US2] `app/templates/event_detail.html`: tabela "Gastos extras vinculados"
      ganha coluna "Evento" (via `g.event.title`, link para `/events/{{ g.event_id }}`)
      quando `event_group_size > 1`; sem mudança quando o evento não está agrupado
- [X] T006 Verificação funcional vs `manto_local`: grupo sintético (principal + 2
      satélites, cada um com talento escalado e gasto extra aprovado próprio) — abrir
      principal e satélite mostram os mesmos totais agregados de custo/gastos/lucro/
      venda/comissão; evento avulso continua idêntico ao comportamento de hoje; gasto
      "pendente" continua fora do total; tabela de gastos extras rotula o evento de
      origem corretamente quando há mais de um evento no grupo. Todos os cenários
      passaram (`scripts/db/verify_137_kpi_grupo.py`).
- [X] T007 `ruff check` nos arquivos tocados (mesma contagem do baseline, 12
      pré-existentes em `routes.py`, nenhum novo); changelog (`docs/changelog.html`,
      republicado no link já existente); pointer do plano em `CLAUDE.md` atualizado;
      commit, merge em `main`, push
