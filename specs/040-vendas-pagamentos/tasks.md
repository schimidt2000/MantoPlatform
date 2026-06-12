# Tasks: Controle de vendas, descontos e pagamentos recebidos

**Input**: `specs/040-vendas-pagamentos/`
**Tests**: boot + ruff + test client. Sem migration.

## Phase 1: Rotas do evento (calendar)
- [x] T001 `_handle_update_comercial`: salvar `sale_value_gross`; aceitar `futuro` com
      `payment_due_date`.
- [x] T002 `_handle_add_contract`: remover leitura de valor; flash erro/sucesso.
- [x] T003 `_handle_add_payment`: valor obrigatório (> 0) no servidor; flash erro/sucesso.
- [x] T004 Handlers SUPERADMIN: `edit_payment`, `delete_payment`, `delete_contract`,
      `toggle_contract_signed` + registro em `_EVENT_ACTIONS` + EventLog.
- [x] T005 `event_detail` GET: `received_total` e `saldo_cliente` no contexto.

## Phase 2: Template do evento
- [x] T006 Dados da venda: campo "Valor antes do desconto", relabel "Valor de venda final", chip de
      desconto.
- [x] T007 Forma de pagamento: botão "Pagamento futuro" + data combinada (required quando ativo).
- [x] T008 Contrato: form sem valor; lista sem R$; ações superadmin (assinado/excluir+confirm).
- [x] T009 Comprovante: valor `required`; resumo recebido/saldo/quitado; ações superadmin
      (editar valor inline / excluir+confirm).

## Phase 3: Home do comercial
- [x] T010 Rota `/`: `show_comercial` + cálculo dos avisos (régua 50/50 e data combinada).
- [x] T011 `home.html`: sector-panel "Comercial" com severidades.

## Phase 4: Dashboard financeiro
- [x] T012 KPIs "Descontos concedidos" (+% médio) e "A receber (clientes)" — rota + template.

## Phase 5: Verificação
- [x] T013 ruff (sem erros novos) + boot + test client cobrindo US1–US5; commit.

## Dependencies
- T001–T005 → T006–T009; T010 → T011; T012 independente; T013 por último.
