# Contrato: dados comerciais com datas futuras + visões do painel (065)

## Entrada (form de dados comerciais do evento)

- `invoice_due_date` (date, opcional) — data prevista de emissão da NF (quando `with_invoice`).
- Método `parcelado_datas`: listas paralelas
  - `parcela_date[]` (date) e `parcela_amount[]` (texto BR, ex. "1.500,00").
  - Linhas com data **e** valor preenchidos viram parcelas; demais são ignoradas.
  - Ao salvar com esse método, as parcelas do evento são **recriadas** a partir das linhas.

## Saída (painel financeiro, por período já filtrado)

- **Recebimentos previstos**: lista de parcelas com `due_date` no período e `received == False` —
  `{ data, evento, valor }` + **total**.
- **NF a emitir**: lista de eventos com `invoice_due_date` no período — `{ data, evento, valor }`
  + **total**.
- **Receita reconhecida**: inalterada (Σ `sale_value` por `start_at`).

## Critérios de aceite

- [ ] Salvar 2 parcelas (datas/valores) persiste e reexibe; editar/remover funciona.
- [ ] `invoice_due_date` salva e exibe (quando com NF).
- [ ] Painel lista recebimentos previstos e NF a emitir do período, com totais.
- [ ] Receita do período não muda vs. comportamento anterior.
- [ ] Métodos de pagamento e comprovantes atuais sem regressão.
