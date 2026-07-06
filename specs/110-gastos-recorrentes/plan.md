# Implementation Plan: Gastos Recorrentes

**Branch**: `110-gastos-recorrentes` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/110-gastos-recorrentes/spec.md`

## Summary

Novo cadastro de gastos recorrentes em `/gastos/recorrentes` (FINANCEIRO+SUPERADMIN), com
dois modelos novos: `RecurringExpense` (conta: variável | débito automático | assinatura) e
`RecurringExpenseEntry` (lançamento mensal, um por conta/mês). Contas variáveis geram alerta
na home a partir do dia esperado ("aguardando valor" → "a pagar" → some quando pago); o
preenchimento (valor + PIX + vencimento) cria o lançamento que entra na planilha de
Pagamentos (`type: "recurring"`). Débitos automáticos e assinaturas ganham lançamento
`registrado` gerado preguiçosamente todo mês (padrão `_ensure_salary_payments`) e compõem as
despesas do painel financeiro — nunca aparecem como pendência. Gastos extras existentes não
mudam.

## Technical Context

**Language/Version**: Python 3.12 + Flask + SQLAlchemy (stack existente)

**Primary Dependencies**: nenhuma nova — reusa padrões: geração preguiçosa mensal
(`_ensure_salary_payments`), itens tipados da planilha (`_build_*_items` +
`set_payment_status`), guards por papel, `parse_brl`/`format_brl`

**Storage**: PostgreSQL; 1 migration manual (2 tabelas novas:
`recurring_expenses`, `recurring_expense_entries`)

**Testing**: test client vs `manto_local` (requests fora de app_context): alerta na home por
papel/dia, preencher → item na planilha → pagar, geração automática dos fixos (idempotente),
soma no painel, pular mês, RBAC (403), regressão de `/gastos/` (FR-011)

**Target Platform**: sistema interno (desktop-first); telas: home, gastos/recorrentes,
pagamentos, painel financeiro

**Project Type**: web app Flask monolítico

**Performance Goals**: irrelevante — dezenas de contas, 1 lançamento/conta/mês

**Constraints**: `SpecialExpense`/rotas de gastos extras intocados; lançamentos `registrado`
nunca viram pendência; home só mostra alertas a FINANCEIRO/SUPERADMIN

**Scale/Scope**: 1 migration; `app/models.py` (2 modelos); `app/gastos/routes.py` (seção
recorrentes: ~9 rotas + helpers `ensure_recurring_entries`/`recurring_alerts`);
`app/financeiro/routes.py` (`_build_recurring_items`, branch `recurring` no set-status,
soma no dashboard); `app/__init__.py` (home: alertas); templates: `gastos/recorrentes.html`
(novo), `home.html` (bloco de alertas), `base.html` (link), `financeiro/dashboard.html`
(linha recorrentes), `financeiro/pagamentos.html` (se necessário p/ o tipo novo)

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar antes de criar | ✅ Geração mensal preguiçosa = padrão dos salários; planilha = padrão de itens tipados existente; moeda via `parse_brl`/`format_brl`; guards no padrão do módulo. |
| II. Padrões Python | ✅ Modelos com docstring/constantes de estado; helpers com type hints; nomes completos (`recurring_expense_entries`). |
| III. Camadas | ✅ Regra de alerta/geração centralizada em helpers únicos importáveis; rotas orquestram. |
| IV. Não quebrar o que funciona | ✅ Zero mudança em `SpecialExpense`/rotas de gastos extras (verificação cobre regressão); planilha só GANHA um tipo de item; dashboard ganha uma parcela somada com teste explícito. |
| V. UI/UX + feedback | ✅ Alertas com estado claro e ação a 1 clique; confirmação em desativar/excluir/pular; flash de sucesso; destaque "fora da faixa"; proteção global de duplo envio (107). |
| VI. Planejar antes de codar | ✅ Este plano; 4 decisões de produto perguntadas ao usuário antes do spec. |
| VII. Moeda BR | ✅ Todos os valores via filtro/format BR existente; inputs com máscara BRL padrão do sistema. |
| VIII. Mobile-first público | N/A — telas internas. |

**Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/110-gastos-recorrentes/
├── plan.md
├── research.md          # R1–R7
├── data-model.md
├── quickstart.md
├── contracts/
│   └── routes.md
└── tasks.md
```

### Source Code (repository root)

```text
migrations/versions/
└── f6a7b8c9d0e1_recurring_expenses.py    # manual; down_revision = e5f6a7b8c9d0

app/
├── models.py                    # RecurringExpense + RecurringExpenseEntry
├── gastos/routes.py             # seção "recorrentes": guard financeiro, CRUD, preencher,
│                                #   pular, pagar, ensure_recurring_entries(), recurring_alerts()
├── financeiro/routes.py         # _build_recurring_items(); set_payment_status branch "recurring";
│                                #   dashboard soma gastos_recorrentes no período
├── __init__.py                  # home: recurring_alerts p/ FINANCEIRO/SUPERADMIN
└── templates/
    ├── gastos/recorrentes.html  # NOVO — lista agrupada por tipo + mês corrente + histórico
    ├── home.html                # bloco "Contas recorrentes" (financeiro)
    ├── base.html                # link "Gastos Recorrentes" (seção Financeiro)
    └── financeiro/dashboard.html # linha "Gastos recorrentes" no resumo/DRE
```

**Structure Decision**: extensão do módulo `gastos` (pedido do usuário) com RBAC próprio;
integrações pontuais nos módulos donos (financeiro, home).

## Decisões de design (detalhe em research.md)

1. **Cadastro × lançamento** (R2): `RecurringExpense` + `RecurringExpenseEntry`
   (unique conta+mês). "Aguardando valor" = ausência de lançamento (variável).
2. **Fixos sem cron** (R3): `ensure_recurring_entries()` preguiçoso e idempotente, chamado
   pelas telas consumidoras — padrão `_ensure_salary_payments`.
3. **Alertas do mês corrente** (R4): `recurring_alerts(today)`; dia esperado clampado no
   último dia do mês; visível só a FINANCEIRO/SUPERADMIN.
4. **Planilha** (R5): tipo novo `"recurring"` (a_pagar/pago); `registrado` nunca vira item.
5. **Balanço** (R6): soma dos lançamentos com valor do período (competência por month_ref)
   como linha própria no dashboard, dentro do custo do DRE.
6. **Faixa é referência** (R7): fora da faixa aceito com destaque; "pular mês" documenta
   conta que não veio; excluir só sem lançamentos.

## Complexity Tracking

Sem violações — tabela não aplicável.
