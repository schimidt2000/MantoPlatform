# Implementation Plan: Data Customizável no Adiantamento de Salário (120)

**Branch**: `120-data-adiantamento-salario` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

## Summary

`SalaryAdvance` ganha `advance_date` (Date). O modal "Adiantamentos de salário" em
`financeiro/pagamentos.html` ganha um `<input type="date">` pré-preenchido com hoje
(mesmo padrão de `gastos/index.html`). A rota `salary_advance()` lê `advance_date` do
form; se vazio/inválido, usa `datetime.now(TZ_SP).date()` (mesmo fallback que já existe
implicitamente hoje via `created_at`). A serialização de `sp.advances` passa a exibir
`a.advance_date` em vez de `a.created_at`.

## Technical Context

**Stack**: o existente. **Storage**: 1 migration manual — coluna `advance_date` em
`salary_advances`, backfill a partir de `created_at::date` para as linhas já existentes,
depois `NOT NULL` (mesmo padrão de backfill+not-null já usado em `a7b8c9d0e1f3` e
`b8c9d0e1f2a4`). `down_revision = "a2b3c4d5e6f7"` (head atual, feature 119), conferir
unicidade do revision novo.

**Arquivos**: `app/models.py` (coluna nova em `SalaryAdvance`), migration nova,
`app/financeiro/routes.py` (`salary_advance()` lê e valida `advance_date`; serialização de
`_advances` usa a nova coluna), `app/templates/financeiro/pagamentos.html` (campo de data
no form do modal + JS reseta pra hoje a cada abertura, junto com `ADV_MONTH` existente).

**Testing**: lançar adiantamento sem tocar na data → salvo com hoje; lançar com data
escolhida (passada/futura) → salvo com a data escolhida e exibida na lista; reabrir o
modal → data persistida corretamente; data vazia/malformada no POST → cai para hoje sem
erro.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Mesmo padrão de `<input type="date" value="{{ today }}">` já usado em `gastos/index.html` e `gastos/recorrentes.html`; mesmo padrão de migração backfill+not-null das features 112/113. |
| II. Padrões Python | ✅ Parsing de data com fallback explícito, sem exceção não tratada. |
| III. Camadas | ✅ Mudança contida na rota que já processa o lançamento; nenhuma camada nova. |
| IV. Não quebrar | ✅ Coluna nova com backfill cobre os adiantamentos já lançados; nenhuma mudança em outros campos/fluxos do pagamento. |
| V. UI/UX | ✅ Campo já vem preenchido (sem exigir ação extra do usuário); mesma tela e modal de hoje. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | N/A (campo é data, não valor). |

**Gate: PASS.**

## Decisões

1. **Fallback silencioso pra hoje, não erro**: se o campo vier vazio ou mal formatado, o
   lançamento não deve travar por causa da data — mesma tolerância que o comportamento
   atual (implícito) já tinha.
2. **Backfill com a própria `created_at`** para os adiantamentos já lançados: é a única
   data disponível para o histórico; documentado como Assumption na spec.
3. **`created_at` continua existindo sem mudança** (timestamp de auditoria de quando o
   registro foi de fato gravado) — `advance_date` é um campo novo e independente, não uma
   renomeação.
