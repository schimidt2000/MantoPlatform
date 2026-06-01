# Implementation Plan: Gastos — acesso restrito + lista de pagamentos

**Branch**: `005-gastos-pagamento` | **Date**: 2026-05-30 | **Spec**: [spec.md](./spec.md)

## Summary

Dois ajustes sobre a feature 004:
1. **Restringir** a página `/gastos` e o item de menu a super admin.
2. **Desembolso**: o gasto ganha tipo (reembolso a funcionário | fornecedor) + dados de
   pagamento + status de pagamento próprio; quando **aprovado**, vira um item `type="expense"`
   na lista de pagamentos do financeiro (`/financeiro/pagamentos`), no mês da data do gasto.

Reaproveita o sistema de itens de pagamento já existente (`_build_payment_items`,
`set_payment_status`) — que é genérico por `type`/`item_id` — e o template `pagamentos.html`,
que renderiza por campos (`person_name`, `amount`, `pix_key`, `status`).

## Technical Context

**Language/Version**: Python 3.11+ (Flask + SQLAlchemy)
**Storage**: novas colunas em `special_expenses` (migration à mão — autogenerate quebrado).
**Constraints**: acesso a super admin; desembolso só de gasto aprovado; status de pagamento
independente da aprovação; sem regressão na lista de pagamentos atual.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — usa o pipeline de pagamentos existente (terceiro `type`),
  o template genérico e o PIX do User; não duplica tela nem lógica de status.
- **II. Padrões Python** ✅ — colunas tipadas, helper pequeno para montar o item de gasto.
- **III. Camadas** ✅ — o financeiro (consumidor) lê `SpecialExpense`; o módulo gastos não conhece o financeiro.
- **IV. Não quebrar** ✅ — migration aditiva (novas colunas nullable); branch isolado; verificação no app.
- **V. UI/UX (pt-BR)** ✅ — seletor de tipo de desembolso com campos condicionais; R$; reusa estilos.
- **VI. Planejar antes de codar** ✅ — este plano.
- **Migration à mão** ✅ — conforme memória do projeto (autogenerate captura drift pré-existente).

## Project Structure

```text
app/
├── models.py                       # SpecialExpense: + disbursement_type, reimburse_user_id,
│                                   #   supplier_name, supplier_pix, payment_status
├── gastos/routes.py                # index/aprovar restritos a superadmin; novo() grava desembolso
├── financeiro/routes.py            # _build_payment_items: + itens de gastos aprovados;
│                                   #   set_payment_status: trata item_type 'expense'
├── templates/
│   ├── gastos/index.html           # seletor reembolso/fornecedor + campos condicionais; col status pgto
│   └── base.html                   # item de menu 'Gastos Extras' -> só superadmin
migrations/versions/
└── xxxx_special_expense_disbursement.py   # novas colunas (à mão)
```

## Design Detalhado

### 1. Acesso restrito (US1)
- `base.html`: trocar `{% if current_user.is_authenticated %}` do item Gastos por
  `{% if current_user.is_authenticated and eff_has_role('SUPERADMIN') %}`.
- `gastos/routes.py`: `index()` e `novo()` passam a exigir super admin (hoje `index/novo` são
  abertos; `aprovar/rejeitar` já exigem). Adiciono checagem `_is_superadmin()` → `abort(403)`.

### 2. Model `SpecialExpense` (novas colunas, nullable)
- `disbursement_type` (String 20): "reembolso" | "fornecedor" | None.
- `reimburse_user_id` (FK users, null) — funcionário a reembolsar.
- `supplier_name` (String 200, null), `supplier_pix` (String 120, null).
- `payment_status` (String 20, default "nao_pago") — estado do desembolso.
- Relationship `reimburse_user`. Propriedades auxiliares: `payee_name`, `payee_pix`
  (resolvem reembolso→user.pix / fornecedor→supplier_pix).

### 3. Migration à mão
- `down_revision` = head atual (`f1a2b3c4d5e6`). `op.add_column` × 5 + índice opcional.

### 4. Formulário (gastos/index.html)
- Radio "Tipo de desembolso": Reembolso / Fornecedor.
- Reembolso → `<select>` de funcionários (lista de users ativos).
- Fornecedor → inputs nome + PIX.
- JS simples mostra/esconde os campos conforme o radio.
- `novo()` valida conforme o tipo e grava os campos.

### 5. Lista de pagamentos (financeiro)
- `pagamentos()`: buscar `SpecialExpense` aprovados do mês (por `expense_date`) e passar a
  `_build_payment_items`.
- `_build_payment_items`: novo bloco que cria item `type="expense"`, `id=expense.id`,
  `person_name=payee_name`, `amount`, `pix_key=payee_pix`, `status=payment_status`,
  `event_title="Gasto: <categoria>"`, `sublabel=description`, `date=expense_date`.
- `set_payment_status`: tratar `item_type == "expense"` → atualizar `SpecialExpense.payment_status`
  (+ audit). Status válidos reusam `_VALID_PAYMENT_STATUS`.
- `bulk_payment_action`: fora de escopo inicial (manter cache/salary); o gasto usa o seletor por linha.

### 6. Página de gastos — refletir status de pagamento
- Mostrar uma coluna/badge de status do desembolso (não pago/pago/no banco) para gasto aprovado.

### Fora de escopo
- Cadastro de fornecedores; bulk-action para gastos; edição de desembolso após pago.
