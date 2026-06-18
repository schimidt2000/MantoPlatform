# Data Model: Máscara padrão para campos de valor em reais (059)

## Mudança no modelo

**Nenhuma.** Sem nova coluna, sem nova entidade, sem migration. As colunas que guardam valores
(`Float`/`Numeric` em `CalendarEvent`, `EducamantoPackage`, `EducamantoItem`, `SalaryHistory`,
`SiteSetting`, etc.) continuam iguais. A feature é de **apresentação (máscara no input) +
parsing (leitura do valor enviado)**.

## Regra de classificação (derivada — qual campo recebe a máscara)

```
recebe_mascara_R$  ⇔  o campo representa um valor monetário em reais que o usuário digita
NÃO recebe         ⇔  percentual/taxa, multiplicador/markup, contagem/quantidade,
                       dimensão (cm) ou tempo (min)
```

| Campo (exemplos) | Tipo | Recebe máscara R$? |
|---|---|---|
| cachê, viagem, venda, pagamento, parcela (valor), salário, gasto | R$ | ✅ |
| preços orçamento (`ator_*`, `cantor_base_*`), `acrescimo_valor`, `cust_valor_*` | R$ | ✅ |
| custos/valores educamanto (`ensemble_*`, `item_cost_*`) | R$ | ✅ |
| desconto em valor (`desc-val`), filtros `min_val`/`max_val` | R$ | ✅ |
| comissão %, desconto %, `tax_rate`, `fator_r_threshold` | % | ❌ |
| `markup_*`, `margin_*` | multiplicador | ❌ |
| `payment_installments`, `item_qty`, `item_ensemble_add`, `piece_qtys` | contagem | ❌ |
| `height_cm`/`height_value`, `departure_margin_minutes`, `duracao_custom` | dimensão/tempo | ❌ |

## Contrato de valor (sem mudança de tipo persistido)

- O **input** exibe e captura no padrão BR (`1.500,00`).
- A **borda** (rota/JS) converte para número via `parse_brl`/`parse_brl_int` (Python) ou
  `MoneyMask.parseNumber` (JS).
- O **persistido** continua sendo o mesmo número de antes (ex.: `Float` 1500.0). Reabrir e salvar
  sem alterar não muda o valor (FR-008).

## Migração

Nenhuma.
