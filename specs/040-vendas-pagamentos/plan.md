# Implementation Plan: Controle de vendas, descontos e pagamentos recebidos

**Branch**: `040-vendas-pagamentos` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)

## Summary

Tudo que o banco precisa já existe: `CalendarEvent.sale_value_gross` (migration j6d7e8f9a0b1),
`payment_due_date`, `payment_method` (String 30), `EventContract.amount`, `EventPayment.amount`.
**Sem migration.** O trabalho é em rotas + templates:

1. Seção Comercial do evento: campo "Valor antes do desconto" (grava `sale_value_gross`), relabel
   "Valor de venda final", chip de desconto, resumo recebido/saldo, forma "Pagamento futuro"
   (`payment_method='futuro'` + `payment_due_date` obrigatória).
2. Contrato sem campo de valor; comprovante com valor obrigatório (cliente + servidor, com flash).
3. Ações novas (só SUPERADMIN): editar valor de comprovante, excluir comprovante, excluir contrato
   — com log no evento e `confirm()` antes de excluir.
4. Home: painel "Comercial" com eventos de saldo em aberto (régua 50/50 + data combinada para
   futuro/faturado).
5. Dashboard financeiro: KPIs "Descontos concedidos" (+ % médio) e "A receber (clientes)".

## Constitution Check
- **I. Reutilizar** ✅ — `parse_brl`/`parse_brl_int` (app/money.py), padrão de handlers
  `_EVENT_ACTIONS`, sector-panel da home, KPI cards do financeiro.
- **IV. Não quebrar** ✅ — `EventContract.amount` permanece no banco; `update_comercial` mantém
  todos os campos atuais; 'faturado' continua funcionando (só muda a régua de aviso).
- **V. UI/UX** ✅ — flash de erro/sucesso, `confirm()` antes de excluir, estado quitado visível.

## Design Detalhado

### 1. `app/calendar/routes.py`

- `_handle_update_comercial`:
  - `event.sale_value_gross = parse_brl(request.form.get("sale_value_gross", ""))`.
  - `_VALID_METHODS` += `"futuro"`; para `futuro` ler `payment_due_date` (igual faturado); se
    `futuro` sem data → mantém método mas flash de aviso pedindo a data (não bloqueia o resto do
    save).
- `_handle_add_contract`: para de ler `contract_amount` (amount=None); flash de erro quando sem
  arquivo ou >10 MB; flash de sucesso.
- `_handle_add_payment`: `amount = parse_brl_int(...)`; se `not amount or amount <= 0` → flash
  erro + return (nada gravado); arquivo continua obrigatório (flash erro); flash sucesso.
- Novos handlers (todos checam SUPERADMIN internamente, senão flash erro + return):
  - `_handle_edit_payment` (`payment_id`, `payment_amount`): valida > 0; atualiza; EventLog.
  - `_handle_delete_payment` (`payment_id`): deleta registro (arquivo fica no disco); EventLog.
  - `_handle_delete_contract` (`contract_id`): idem.
  - "Editar contrato" = marcar assinado/pendente: `_handle_toggle_contract_signed` (`contract_id`)
    — SUPERADMIN; alterna `is_signed`; EventLog. (Hoje `is_signed` não tem UI de escrita.)
- `_EVENT_ACTIONS` += `edit_payment`, `delete_payment`, `delete_contract`,
  `toggle_contract_signed`.
- `event_detail` GET: `received_total = sum(p.amount or 0 for p in payments)`;
  `saldo_cliente = float(event.sale_value or 0) - received_total`; passa ambos ao template.

### 2. `app/templates/event_detail.html`

- Dados da venda: input "Valor antes do desconto (R$)" (`sale_value_gross`), label do atual vira
  "Valor de venda final (R$)"; quando `gross > final`, chip "Desconto: R$ X (Y%)".
- Forma de pagamento: botão "Pagamento futuro" (`futuro`); bloco de data `detail-extra-futuro`
  (reusa `payment_due_date`, label "Data combinada de pagamento", `required` via JS quando ativo);
  `setDetailPayMethod` atualizado.
- Contrato: remove campo de valor do form e o "R$" da lista; botões SUPERADMIN por item:
  "✓ Assinado/Pendente" (toggle) e "Excluir" com `confirm()`.
- Comprovante: input de valor com `required`; resumo "Recebido R$ X de R$ Y — Falta R$ Z" (badge
  verde "Quitado ✓" quando saldo ≤ 0); por item (SUPERADMIN): "Editar" (mini-form inline com valor)
  e "Excluir" com `confirm()`.

### 3. Home — `app/__init__.py` + `app/templates/home.html`

- Rota `/`: `show_comercial = has_role(COMERCIAL) or has_role(FINANCEIRO) or is_superadmin`.
- Query: eventos com `sale_value > 0`, `start_at >= task_cutoff`, excluindo ensaios; soma de
  `EventPayment.amount` por evento (uma query agregada). Para cada evento com saldo > 0:
  - `futuro`/`faturado` com `payment_due_date`: vencida (≤ hoje) → `urgent`; senão `info` com data.
  - Demais: faltam ≤ 2 dias para o início (ou já passou) → `urgent`; recebido < 50% → `warn`;
    senão não lista (dentro da política).
- `home.html`: sector-panel "Comercial" (badge própria) com linhas: título/data do evento, recebido
  × venda, falta R$ X, badge URGENTE (vermelho) / SINAL PENDENTE (amarelo) / data combinada (info),
  link "Abrir evento".

### 4. Financeiro — `app/financeiro/routes.py` + `templates/financeiro/dashboard.html`

- `dashboard()`: `descontos = sum(gross - sale)` para eventos do período com `gross > sale`;
  `pct_desconto_medio = descontos / sum(gross desses eventos) * 100`;
  `a_receber_clientes = sum(max(sale - recebido, 0))` dos eventos do período.
- Template: 2 KPI cards na área de indicadores comerciais/caixa.

### 5. Verificação

- Boot + `ruff check` (sem erros NOVOS vs. baseline).
- Test client (seeds com `google_event_id` fake, deletados no finally):
  - add_payment sem valor → nada gravado; com valor → gravado.
  - edit/delete payment e delete contract como não-superadmin → recusado; como superadmin → ok +
    EventLog.
  - update_comercial grava `sale_value_gross` e `futuro` + data.
  - Home: cenários U4/U5 (sinal pendente, urgente ≤2 dias, quitado some, futuro com data,
    futuro vencido).
  - Dashboard financeiro: descontos e a receber corretos.

## Project Structure
```text
app/calendar/routes.py                      # handlers comercial/contrato/pagamento + novos
app/templates/event_detail.html             # seção Comercial
app/__init__.py                             # avisos comercial na home
app/templates/home.html                     # painel Comercial
app/financeiro/routes.py                    # KPIs descontos / a receber
app/templates/financeiro/dashboard.html     # cards novos
```

## Fora de escopo
- Migration / mudanças de schema (nada necessário).
- Trocar arquivo de comprovante (editar = valor; trocar arquivo = excluir + re-adicionar).
- Relatório detalhado de descontos por vendedora (futuro).
