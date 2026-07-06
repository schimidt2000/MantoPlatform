# Research — Gastos Recorrentes (110)

## R1. Onde a feature mora

"Extensão da seção de gastos extras" (pedido do usuário) — mas com RBAC diferente
(FINANCEIRO+SUPERADMIN vs. todos) e sem fluxo de aprovação.

**Decision**: mesmas rotas/módulo `app/gastos/routes.py` (blueprint `gastos_bp`), sob
`/gastos/recorrentes`, com guard próprio `_require_financeiro_recorrentes` (FINANCEIRO ou
SUPERADMIN). Tela própria (`gastos/recorrentes.html`) + link no menu na seção Financeiro
(guard FINANCEIRO/SUPERADMIN já existente em `base.html`). `SpecialExpense` NÃO é tocado
(FR-011) — modelo distinto, sem aprovação, sem NF obrigatória.

**Alternatives considered**: reusar `SpecialExpense` com flag `is_recurring` — rejeitado:
semânticas incompatíveis (aprovação, NF obrigatória, RBAC aberto, sem mês de referência).

## R2. Modelo de dados

Dois conceitos: o **cadastro** (Conta de Luz, faixa 400–600, dia 10) e o **lançamento
mensal** (Conta de Luz 07/2026, R$ 512,30, pago). Um lançamento por conta/mês (unique).

**Decision**: `RecurringExpense` (cadastro; `expense_type` em {"variavel",
"debito_automatico", "assinatura"}) + `RecurringExpenseEntry` (lançamento;
`month_ref = "YYYY-MM"`, unique com `recurring_id`). Estados do lançamento: `a_pagar`,
`pago`, `registrado` (fixos, criados automaticamente), `pulado` (conta variável que não veio
no mês). "Aguardando valor" NÃO é linha no banco — é a ausência de lançamento no mês para
conta variável ativa (não há o que registrar antes de a conta chegar).

## R3. Geração automática dos lançamentos fixos

FR-005 pede lançamento mensal sem ação manual e sem tarefa agendada externa.

**Decision**: geração preguiçosa idempotente `ensure_recurring_entries(year, month)` —
mesmo padrão de `_ensure_salary_payments` (feature financeiro): chamada ao carregar as telas
que consomem os dados (recorrentes, home/alertas, planilha de pagamentos, painel
financeiro). Cria `registrado` para cada conta fixa ativa sem lançamento no mês; unique
constraint garante idempotência mesmo em corrida.

## R4. Alertas na home

Home (`/`, `app/__init__.py`) já monta blocos por papel (`is_superadmin` etc.).

**Decision**: helper `recurring_alerts(today)` retorna, para contas variáveis ativas com
`min(due_day, último dia do mês) <= today.day`: sem lançamento no mês → alerta
"aguardando valor"; lançamento `a_pagar` → alerta "a pagar" (com valor). `pago`/`pulado`
→ sem alerta. Home passa `recurring_alerts` ao template só quando o usuário tem
FINANCEIRO/SUPERADMIN; bloco novo em `home.html` com link para `/gastos/recorrentes` e
botão de preencher direto. Sempre mês corrente (edge case: meses antigos ficam no
histórico, não na home).

## R5. Planilha de pagamentos

Itens da planilha são dicts tipados (`type`: cache/salary/expense/bv/commission) montados
em `pagamentos()`; marcação via `set_payment_status` (branch por `item_type`).

**Decision**: `_build_recurring_items(year, month, today)` — lançamentos `a_pagar`/`pago`
do `month_ref` visto, `type: "recurring"`, data = `due_date` do lançamento (fallback: dia
esperado clampado no mês), PIX copiável. `set_payment_status` ganha branch `"recurring"`
(`pago` ↔ `a_pagar`; sem estado "no banco"). Sem seleção em massa para recorrentes na
primeira versão (mesma abordagem das comissões, que também ficam de fora do bulk "banco").
Lançamentos `registrado` (fixos) NUNCA viram item de pagamento (FR-005/SC-004).

## R6. Painel financeiro (balanço)

Dashboard (`/financeiro/`, ~linha 414) soma `gastos_extras` (SpecialExpense aprovado no
período) e passa ao DRE (`_compute_drg`).

**Decision**: somar também os lançamentos recorrentes do período (status `a_pagar`, `pago`,
`registrado` — competência pelo `month_ref`; `pulado` fica fora) como variável própria
`gastos_recorrentes`, exibida como linha própria no dashboard e incluída no custo do DRE
junto de `gastos_extras`. Meses do período = todos os `month_ref` entre o mês de
`start_date` e o de `end_date`.

## R7. Fora da faixa / pular mês

**Decision**: faixa (min–max) é referência: valor fora é aceito e o lançamento/alerta ganha
destaque visual "fora da faixa" (comparação no template — sem coluna extra). "Pular mês"
cria lançamento `pulado` sem valor (encerra o alerta e documenta o buraco no histórico).
Exclusão de conta: bloqueada se houver qualquer lançamento (desativar é o caminho);
liberada se zero lançamentos.
