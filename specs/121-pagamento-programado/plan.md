# Implementation Plan: Pagamento Programado (Gastos Recorrentes) (121)

**Branch**: `121-pagamento-programado` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

## Summary

Novo `expense_type = "programado"` em `RecurringExpense` (4º tipo, ao lado de
variavel/débito automático/assinatura). Ao contrário dos outros três — gerados mês a mês
por `ensure_recurring_entries`/`occurrences_in_month` — o pagamento programado tem suas
parcelas criadas de uma vez no cadastro: uma `RecurringExpenseEntry` por data informada,
com `due_date`/`amount`/`month_ref` próprios, status `a_pagar` (já nasce visível na
planilha de pagamentos, sem geração preguiçosa). Único ajuste de schema: remover a
constraint `uq_recurring_entry_month` (recurring_id, month_ref), que hoje assume no máximo
1 lançamento por conta/mês — um pagamento programado pode ter 2 parcelas no mesmo mês (ex.:
05/08 e 20/08). Painel de gastos recorrentes ganha uma seção própria "Pagamentos
programados" listando cada compromisso com TODAS as parcelas (não só as do mês em
exibição).

## Technical Context

**Stack**: o existente. **Storage**: 1 migration manual — apenas `DROP CONSTRAINT
uq_recurring_entry_month` em `recurring_expense_entries` (nenhuma coluna nova; `due_date`,
`amount`, `month_ref`, `pix`, `status` já existem e cobrem o caso). `down_revision =
"c4d5e6f7a8b9"` (head atual, feature 120), conferir unicidade do revision novo.

**Arquivos**: `app/models.py` (`RecurringExpense.TYPES`/`TYPE_LABELS` += "programado";
propriedade `parcelas_summary` para exibição), migration nova, `app/gastos/routes.py`
(`_parse_programado_form()` + rota `POST /gastos/recorrentes/programado/nova`; rota `POST
/gastos/recorrentes/entry/<id>/excluir-parcela`; `recorrentes()` passa `grupos['programado']`
já calculado; `_estimate()` retorna 0 para "programado" — não entra na soma "R$/mês"),
`app/templates/gastos/recorrentes.html` (seção nova "Pagamentos programados": formulário de
cadastro com linhas dinâmicas de data+valor — mesmo padrão de `parcela_date[]` já usado em
`event_detail.html` — e listagem de cada compromisso com todas as parcelas; loops
existentes de KPI/tabela genérica passam a excluir `t == 'programado'`).

**Testing**: cadastrar com "mesmo valor" (N datas, 1 valor) → N parcelas idênticas;
cadastrar com "valor individual" → cada parcela com seu valor; duas datas no mesmo mês →
duas parcelas distintas, nenhuma sobrescrita; parcela aparece na planilha de pagamentos na
data certa (`_build_recurring_items`); marcar parcela como paga (rota já existente
`recorrente_pagar`) reflete no painel e na planilha; excluir parcela não paga não afeta as
demais; cadastro sem nome/sem data válida é rejeitado sem criar nada; painel mostra
parcelas de todos os meses, não só o mês em exibição.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Reaproveita `RecurringExpenseEntry` (mesmo modelo, sem coluna nova) e as rotas já existentes de pagar/reabrir lançamento; UI de linhas dinâmicas segue o padrão já usado em `event_detail.html`. |
| II. Padrões Python | ✅ `_parse_programado_form()` isolado, type hints, docstring; validação por função pequena. |
| III. Camadas | ✅ Parsing/validação na rota; nenhuma lógica de negócio nova fora do módulo `gastos`. |
| IV. Não quebrar | ✅ Único change de schema é remover uma constraint (relaxamento, não quebra dado existente); `ensure_recurring_entries`/`recurring_alerts`/`_build_recurring_items` já filtram por tipo ou usam `.all()` sem assumir unicidade — confirmado por leitura, zero mudança nelas. |
| V. UI/UX | ✅ Cadastro em um formulário só (nome, datas, mesmo/individual, valor); painel mostra o compromisso inteiro, não fatiado por mês. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | ✅ Valores em `brl-input`/`parse_brl`, mesmo padrão do resto do módulo. |

**Gate: PASS.**

## Decisões

1. **Parcelas criadas de uma vez, não geradas por mês**: diferente dos outros tipos
   (geração preguiçosa via `ensure_recurring_entries`), aqui as datas já são conhecidas no
   cadastro — gerar tudo de uma vez é mais simples e é exatamente o que a planilha de
   pagamentos e o painel precisam consumir sem lógica nova.
2. **Remover a constraint em vez de reestruturar o modelo**: a constraint
   `(recurring_id, month_ref)` existe para os tipos com geração automática (que já se
   protegem via checagem em código antes de inserir, não dependem da constraint do banco);
   removê-la é seguro e evita duplicar o conceito de "lançamento" em duas tabelas.
3. **Seção própria no painel, fora do loop genérico de tipos**: as colunas do loop genérico
   (Dia/Frequência/Referência) não fazem sentido para um cronograma de datas soltas; uma
   seção dedicada, com a lista completa de parcelas, atende melhor o pedido de "conseguir
   visualizar" o compromisso inteiro.
4. **Sem edição em massa do cronograma**: reduz superfície da primeira versão; corrigir um
   erro é excluir a parcela (se não paga) e recadastrar — documentado como Assumption.
5. **`_estimate()` retorna 0 para "programado"**: a soma "R$/mês" das outras contas não faz
   sentido para um cronograma finito e não regular; evita número enganoso no card de
   resumo.
