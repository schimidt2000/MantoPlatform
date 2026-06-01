# Tasks: Gastos — acesso restrito + lista de pagamentos

**Input**: `specs/005-gastos-pagamento/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: US1 — Acesso restrito a super admin (P1)

- [ ] T001 [US1] `base.html`: item de menu "Gastos Extras" só para `eff_has_role('SUPERADMIN')`.
- [ ] T002 [US1] `gastos/routes.py`: `index()` e `novo()` exigem super admin (`abort(403)` senão).

## Phase 2: Fundação do desembolso (model + migration)

- [ ] T003 Model `SpecialExpense` ([app/models.py](../../app/models.py)): + `disbursement_type`,
      `reimburse_user_id` (FK users), `supplier_name`, `supplier_pix`, `payment_status`
      (default "nao_pago"); relationship `reimburse_user`; propriedades `payee_name`/`payee_pix`.
- [ ] T004 Migration à mão `special_expense_disbursement` (down_revision = `f1a2b3c4d5e6`):
      add_column × 5; `flask db upgrade`.

## Phase 3: US2 — Definir destino do desembolso (P1)

- [ ] T005 [US2] `gastos/index.html`: radio Reembolso/Fornecedor; select de funcionários
      (reembolso) e inputs nome+PIX (fornecedor), com JS de mostrar/esconder.
- [ ] T006 [US2] `index()` passa a lista de funcionários ao template; `novo()` valida por tipo e
      grava `disbursement_type` + destino.

## Phase 4: US3 — Gasto aprovado na lista de pagamentos (P1)

- [ ] T007 [US3] `_build_payment_items` ([financeiro/routes.py](../../app/financeiro/routes.py)):
      novo item `type="expense"` (person_name=payee, amount, pix_key=payee_pix, status=payment_status,
      event_title="Gasto: <categoria>", sublabel=description, date=expense_date).
- [ ] T008 [US3] `pagamentos()`: buscar `SpecialExpense` aprovados do mês (por `expense_date`) e
      incluir no `_build_payment_items`; somar nos totais.
- [ ] T009 [US3] `set_payment_status`: tratar `item_type == "expense"` → atualiza
      `SpecialExpense.payment_status` + audit.
- [ ] T010 [US3] `gastos/index.html`: badge de status do desembolso para gastos aprovados.

## Phase 5: Polish

- [ ] T011 `ruff check` nos .py tocados.
- [ ] T012 Verificação E2E no app real:
      (a) não-superadmin: menu sem "Gastos Extras" + `/gastos` → 403;
      (b) criar gasto reembolso + fornecedor; aprovar;
      (c) `/financeiro/pagamentos` do mês mostra os 2 itens com destinatário/valor/PIX;
      (d) marcar "pago" reflete no gasto; pendente/rejeitado não aparecem.

## Dependencies
- T003 → T004 (model antes da migration). T003 → T007/T008/T009 (campos consumidos).
- T001/T002 independentes (podem ir primeiro). T010 depende de T003.

## Notes
- Reusa pipeline genérico de pagamentos (type/item_id) e PIX do User.
- Migration à mão (autogenerate quebrado — ver memória do projeto).
- Status de pagamento do desembolso é independente do status de aprovação.
