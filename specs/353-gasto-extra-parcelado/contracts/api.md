# Contratos — 353

## Gasto (`_expense_dict`, todas as respostas de gasto)

Novo: `parcelas: [{"id": int, "numero": int, "data": "AAAA-MM-DD", "valor": float, "payment_status": "nao_pago" |
"no_banco" | "pago"}]` — `[]` no gasto não parcelado. `amount` = soma no parcelado.

## `POST /api/gastos` (multipart)

Novo campo opcional `parcelas`: texto JSON `[{"data": "2026-11-20", "valor": 500.0}, …]`. Presente e não vazio → o
gasto nasce parcelado e o `amount` enviado é ignorado (vale a soma).

## `PATCH /api/gastos/<id>` (JSON)

Novo campo opcional `parcelas`: `[{"id"?: int, "data": str, "valor": number}]`.

| Valor | Efeito |
|---|---|
| ausente | parcelas gravadas intocadas; se o gasto é parcelado, `amount` tem de ser a soma (senão 400 `fields.amount`) |
| `[]` | deixa de ser parcelado; 400 `fields.parcelas` se alguma está paga/no banco |
| lista | substitui o conjunto (regras abaixo) |

## Erros (400, envelope `json_error`)

| `fields` | Mensagem |
|---|---|
| `parcelas` | "Parcelado precisa de pelo menos duas parcelas." · "Até 24 parcelas." · "Este gasto não pode ser parcelado." (sem desembolso, devolução, multa, já pago no cadastro, gasto do auditor de marketing) · "Parcela paga não muda: desmarque o pagamento na Planilha de Pagamentos primeiro." (paga removida ou desligar parcelas com paga) |
| `parcelas.N.data` | "Informe a data da parcela." |
| `parcelas.N.valor` | "Informe o valor da parcela." · "Parcela paga não muda: …" (paga alterada) |

`N` é o índice (0..) da parcela na lista enviada.

## `GET /api/financeiro/pagamentos`

Itens novos `type: "expense_parcela"`: `id` (id da parcela), `date` (data da parcela), `event_title` "Gasto:
{categoria}", `sublabel` "{descrição} · Parcela N de M", `person_name`, `pix_key`, `amount` (valor da parcela),
`status`, `is_future`; nos atrasados, com `de_mes_anterior`, `mes_origem`, `dias_em_atraso`. O gasto parcelado não vem
mais como `type: "expense"`.

## `POST /api/financeiro/pagamentos/set-status`

`item_type: "expense_parcela"`, `item_id`: id da parcela. Grava a parcela e rederiva o `payment_status` do gasto. 404 se
a parcela não existe. Gate inalterado (Financeiro/Superadmin).

## `POST /api/financeiro/pagamentos/bulk-action`

Novo array `parcela_ids: number[]`. "excluir" ignora parcelas (como ignora gastos).
