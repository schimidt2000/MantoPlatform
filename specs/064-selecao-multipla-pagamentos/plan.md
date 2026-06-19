# Implementation Plan: Seleção múltipla estilo planilha nos pagamentos

**Branch**: `064-selecao-multipla-pagamentos` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/064-selecao-multipla-pagamentos/spec.md`

## Summary

Na tela de pagamentos, mostrar a **soma em R$** dos selecionados (junto da quantidade já
existente) e permitir seleção por **Shift** (intervalo) além do clique individual. Tudo
**client-side**, reusando a seleção em lote e o `data-amount` por linha já existentes. **Sem
backend, sem migration.**

## Technical Context

**Language/Version**: HTML/CSS/JS vanilla em Jinja2 (Flask). Sem Python novo.

**Primary Dependencies**: Nenhuma. Reusa `.row-check`, `#bulk-count`, `updateBulkBar`,
`isRowVisible` e `tr.pay-row[data-amount]`.

**Storage**: N/A (sem mudança de dados).

**Testing**: GET da página contra **`manto_local`** (render 200 + presença dos hooks). Shift/soma
são client-side → verificação funcional manual no navegador.

**Target Platform**: App web (Railway), mobile-first.

**Project Type**: Web application (monolito Flask).

**Constraints**: Não quebrar as ações em lote nem o filtro/busca; soma em formato BR; pt-BR.

**Scale/Scope**: 1 arquivo — `app/templates/financeiro/pagamentos.html` (JS + o span do contador).

## Constitution Check

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa toda a infra de seleção existente;
  só soma valores e adiciona o handler de Shift.
- **II. Padrões Python**: N/A (sem Python).
- **III. Arquitetura em camadas**: ✅ Mudança só de apresentação/UX.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ Aditivo; clique simples e ações em
  lote inalterados. Render verificado em `manto_local`.
- **V. UI/UX consistente (pt-BR)**: ✅ Soma clara na barra; Shift no padrão de explorador.
- **VI. Planejar antes de codar**: ✅ Este plano + research.
- **VII. Valores monetários BR (NÃO-NEGOCIÁVEL)**: ✅ Soma formatada em R$ (milhar/centavos BR).

**Resultado**: PASS — sem violações, sem migration.

## Project Structure

### Documentation (this feature)

```text
specs/064-selecao-multipla-pagamentos/
├── plan.md  spec.md  research.md  quickstart.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/templates/financeiro/pagamentos.html
  # #bulk-count passa a mostrar "N selecionados · R$ soma"
  # updateBulkBar(): soma data-amount dos marcados; fmtBRL(v) local
  # handler de click nas .row-check: Shift seleciona intervalo (linhas visíveis)
```

**Structure Decision**: Monolito Flask; mudança isolada em um template. Sem migration.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
