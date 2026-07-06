# Contracts — Gastos Recorrentes (110)

Guard de todas as rotas novas: FINANCEIRO ou SUPERADMIN (403 caso contrário; 401 anônimo).

## GET /gastos/recorrentes

Lista contas agrupadas por tipo com status do mês corrente (chama
`ensure_recurring_entries` antes). Query params: `month` (YYYY-MM, default corrente) e
`conta` (id — expande histórico da conta).

## POST /gastos/recorrentes/nova

Campos: `name`*, `expense_type`* (variavel|debito_automatico|assinatura), `due_day`* (1–31),
`amount` (obrigatório p/ fixos), `amount_min`/`amount_max` (opcionais, variável),
`default_pix`, `card_name` (assinatura), `notes`. Valor BRL mascarado (`parse_brl`).
Erros: flash + redirect (padrão do módulo).

## POST /gastos/recorrentes/<id>/editar

Mesmos campos. Afeta apenas lançamentos futuros (linhas existentes não mudam).

## POST /gastos/recorrentes/<id>/toggle

Ativa/desativa. Desativada: sem alertas e sem lançamentos novos.

## POST /gastos/recorrentes/<id>/excluir

403 de negócio (flash de erro) se a conta tiver qualquer lançamento; senão exclui.

## POST /gastos/recorrentes/<id>/preencher

Só conta variável. Campos: `amount`* (BRL), `pix`, `due_date` (opcional), `month_ref`
(default mês corrente). Cria/atualiza lançamento `a_pagar` do mês (idempotente por unique;
re-preencher enquanto `a_pagar` atualiza valores). Lançamento `pago` não é editável.

## POST /gastos/recorrentes/<id>/pular

Só conta variável, mês sem lançamento ou `a_pagar` não pago. Cria/atualiza lançamento
`pulado` (sem valor).

## POST /gastos/recorrentes/entry/<entry_id>/pagar  e  /reabrir

`pagar`: `a_pagar` → `pago` (paid_at = hoje). `reabrir`: `pago` → `a_pagar` (correção).

## Planilha de pagamentos (integração)

`_build_recurring_items(year, month, today)`: lançamentos `a_pagar`/`pago` com
`month_ref == mês visto` viram itens `{type: "recurring", id: entry_id, date: due_date ou
dia esperado clampado, person_name: nome da conta, sublabel: "Conta recorrente", amount,
pix_key, status}`. `set_payment_status` com `item_type == "recurring"`: `pago` → pago
(paid_at hoje); qualquer outro status válido → `a_pagar`. Sem estado "no banco"; fora da
seleção em massa (como comissões).

## Home (integração)

`recurring_alerts(today)` (importado de `app.gastos.routes`): lista de alertas do mês
corrente para contas variáveis ativas com dia atingido — `{conta, faixa, estado
("aguardando" | "a_pagar"), valor?}`. Renderizada em `home.html` apenas quando o usuário tem
FINANCEIRO/SUPERADMIN.

## Painel financeiro (integração)

Soma dos lançamentos do período (`status != 'pulado'`, `amount` não nulo) exibida como
"Gastos recorrentes" e incluída no custo do DRE junto de gastos extras.
