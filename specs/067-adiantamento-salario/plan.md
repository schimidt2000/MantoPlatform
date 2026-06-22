# Implementation Plan: Adiantamento de salário com comprovante

**Branch**: `067-adiantamento-salario` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/067-adiantamento-salario/spec.md`

## Summary

Na tela de pagamentos, permitir editar um salário para registrar um **valor adiantado** com
**comprovante obrigatório**; o item passa a mostrar o **líquido** (salário − adiantamento). O
adiantamento afeta só o valor a pagar (caixa), **não** o custo de salário do balanço. Requer 2
colunas em `salary_payments` → **migration manual** (head `t6c7d8e9f0a1`).

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + HTML/CSS/JS vanilla.

**Primary Dependencies**: Nenhuma nova. Reusa `parse_brl`, `UPLOAD_PAYMENTS`, `audit` e a tela
de pagamentos.

**Storage**: PostgreSQL (prod) / SQLite (dev). **Migration manual**: `salary_payments.advance_amount`
+ `salary_payments.advance_proof`.

**Testing**: Verificação contra **`manto_local` (Postgres)**: aplicar migration; registrar
adiantamento (com/sem comprovante; > salário); conferir líquido e custo de salário inalterado.

**Target Platform**: App web (Railway), mobile-first.

**Constraints**: Comprovante obrigatório quando adiantamento > 0; adiantamento ≤ salário; custo de
salário do período inalterado; pt-BR; restrito a financeiro/admin; auditado.

**Scale/Scope**: `models.py` (2 colunas), 1 migration, `financeiro/routes.py` (rota nova +
`_build_payment_items`), `financeiro/pagamentos.html` (botão editar + modal).

## Constitution Check

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa `parse_brl`, `UPLOAD_PAYMENTS`,
  `audit`, a tela e o item de salário. Sem entidade nova (só 2 colunas).
- **II. Padrões Python**: ✅ Rota pequena e validada.
- **III. Arquitetura em camadas**: ✅ Validação/persistência na rota; UI no template.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ `_salary_cost`/DRE intactos; ações de
  pagamento e demais itens inalterados. Verificação em `manto_local`.
- **V. UI/UX consistente (pt-BR)**: ✅ Modal claro; líquido e adiantamento exibidos; erros
  amigáveis.
- **VI. Planejar antes de codar**: ✅ Este plano + research + data-model + contract.
- **VII. Valores monetários BR (NÃO-NEGOCIÁVEL)**: ✅ Adiantamento via `parse_brl`/`brl`.

**Resultado**: PASS — migration aditiva, sem violações.

## Project Structure

```text
app/
├── models.py                 # SalaryPayment: + advance_amount, + advance_proof
├── financeiro/routes.py      # rota /pagamentos/salary/<id>/advance; _build_payment_items: líquido + campos de adiantamento
└── templates/financeiro/pagamentos.html  # botão "Editar" no salário + modal (valor + comprovante)
migrations/versions/
└── u7d8e9f0a1b2_salary_advance.py  # manual; down_revision t6c7d8e9f0a1
```

**Structure Decision**: Monolito Flask. 2 colunas + migration manual; reuso de upload/parse/audit
e da tela de pagamentos. DRE inalterado.

## Complexity Tracking

> Sem violações de constituição. Migration manual é a norma do projeto.
