# Tasks: "Futuro" pelo horário de término do evento (Pagamentos)

**Input**: `specs/034-pagamentos-futuro-horario/`
**Tests**: boot + ruff + verificação no app. Sem migration.

## Phase 1: Implementação
- [x] T001 `app/financeiro/routes.py`: importar `ZoneInfo` e definir `TZ_SP =
      ZoneInfo("America/Sao_Paulo")`.
- [x] T002 `pagamentos()`: `now_sp = datetime.now(TZ_SP).replace(tzinfo=None)`; `today = now_sp.date()`
      (Brasília); passar `now_sp` para `_build_payment_items`.
- [x] T003 `_build_payment_items(..., now_dt)`: cachê de evento usa
      `ev_end = event.end_at or event.start_at` e `is_future = bool(ev_end and ev_end > now_dt)`.
      Salário/gasto continuam por data de vencimento.

## Phase 2: Verificação
- [x] T004 boot + `ruff check`. Cenários: (a) evento que termina no futuro (hoje) → Futuro;
      (b) evento terminado hoje, não pago → Pendentes; (c) salário/gasto/comissão inalterados;
      (d) "agora" calculado em Brasília (não no fuso do servidor).

## Dependencies
- T001 → T002 → T003 → T004.

## Notes
- Usa end_at (reserva start_at). Eventos são naïve em SP; comparar com now_sp naïve. Sem migration.
