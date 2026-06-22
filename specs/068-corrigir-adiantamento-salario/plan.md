# Implementation Plan: Corrigir adiantamento de salário + máscara BR

**Branch**: `068-corrigir-adiantamento-salario` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

## Summary

Corrigir o bug que fazia o adiantamento de salário (067) sumir após salvar: a rotina de
regeneração mensal (`_ensure_salary_payments`) apagava o lançamento não pago recém-editado.
A correção exclui da regeneração os lançamentos que têm adiantamento. Também restaura a máscara
padrão de R$ no campo de valor. **Sem migration.**

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + JS vanilla.

**Primary Dependencies**: Nenhuma nova. Reusa `parse_brl`, `money-mask.js` (brl-input), colunas
da 067.

**Storage**: PostgreSQL/SQLite. **Sem migration** (colunas já existem).

**Testing**: Contra **`manto_local`**: salvar adiantamento → **GET da tela** (dispara
regeneração) → conferir persistência + líquido. Reproduz o ciclo real que faltou na 067.

**Constraints**: Preservar regeneração p/ salários sem adiantamento; regras da 067 mantidas;
máscara BR; pt-BR.

**Scale/Scope**: `financeiro/routes.py` (1 filtro no delete) + `financeiro/pagamentos.html`
(restaurar brl-input + applyMask).

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Reusa tudo; só ajusta um filtro e restaura a máscara.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Regeneração intacta para salários sem adiantamento;
  pagos/"no banco" já preservados. Verificação do ciclo completo em `manto_local`.
- **VII. Valores BR (NÃO-NEGOCIÁVEL)**: ✅ Restaura a máscara padrão e mantém `parse_brl`.
- Demais princípios: ✅ (mudança mínima, planejada).

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/
├── financeiro/routes.py      # _ensure_salary_payments: delete dos nao_pago exclui advance_amount IS NOT NULL
└── templates/financeiro/pagamentos.html  # campo de adiantamento volta a usar brl-input + applyMask no open
```

**Structure Decision**: Correção cirúrgica + restauração da máscara. Sem migration.

## Complexity Tracking

> Sem violações.
