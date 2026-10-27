# Contrato — `GET /api/gastos` (mudança aditiva da 314)

**Gate (inalterado)**: `api_login_required`. Financeiro/Superadmin (`gastos_ops.is_financeiro`) recebem todos os
gastos + `totals`; os demais recebem só os próprios (`list_expenses(user)`) e **nenhum** `totals`.

**Parâmetros**: nenhum (inalterado). O recorte é na tela.

## O que muda

Cada item de `expenses[]` ganha uma chave:

```json
{
  "id": 412,
  "status": "aprovado",
  "payment_status": "no_banco",
  "paid_at_creation": false,
  "disbursement_type": "reembolso",
  "situacao": "no_banco"
}
```

| Chave | Tipo | Valores | Observação |
|---|---|---|---|
| `situacao` | string | `aguardando_aprovacao` · `a_pagar` · `no_banco` · `pago` · `rejeitado` | derivada por `gastos_ops.situacao_do_gasto`; nunca nula vinda do backend novo |

No React: `situacao?: GastoSituacao` (opcional, armadilha 21). Sem a chave, o gasto fica na lista principal.

As respostas de escrita que devolvem `_expense_dict` (`POST /api/gastos/<id>/aprovar`, `/rejeitar`, `PATCH
/api/gastos/<id>`, `/vincular-evento`) passam a trazer `situacao` também, porque usam o mesmo serializer. A tela não
depende disso: ela invalida `["gastos-extras"]` e relê a lista.

## O que não muda

`can_manage`, `categories`, `totals` (chaves `todos`/`pendente`/`aprovado`/`rejeitado`) e todos os outros campos do
item. Nenhum endpoint novo, nenhum gate novo, nenhuma escrita nova.
