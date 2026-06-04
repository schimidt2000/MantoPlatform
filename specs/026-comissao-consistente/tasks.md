# Tasks: Comissão consistente entre as telas

**Input**: `specs/026-comissao-consistente/`
**Tests**: boot + ruff + verificação no app real.

## Phase 1: Reconciliação
- [ ] T001 financeiro/routes.py: `_resync_pending_commissions()` — para cada evento com comissão
      a_pagar (positiva), chama `_sync_commission_payment(ev)` e commita.
- [ ] T002 financeiro/routes.py: chamar `_resync_pending_commissions()` no início de `comissoes()` e
      de `pagamentos()`.

## Phase 2: Verificação
- [ ] T003 boot + ruff; cenário: comissão gravada a 2% → após abrir Comissões/Pagamentos vira 2,5%
      (= aba comercial); paga não muda; estorno não muda.

## Dependencies
- T001 → T002 → T003.

## Notes
- Reusa _sync_commission_payment (só a_pagar; preserva pago). Sem migration.
