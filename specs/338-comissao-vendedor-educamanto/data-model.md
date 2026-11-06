# Modelo de dados — Feature 338

Migration `d338c5a9e2b1_comissao_vendedor_educamanto` (à mão, `down_revision = 'd323b5a1c0e7'`), aditiva:
quatro colunas anuláveis, sem default, sem backfill. `downgrade` remove as quatro.

| Tabela | Coluna | Tipo | Regra |
|---|---|---|---|
| `calendar_events` | `educamanto_seller_commission` | `NUMERIC(12,2) NULL` | A comissão do vendedor posta no preço pela calculadora. Só conta em evento EducaManto com responsável, no principal. Campo de venda (`SATELLITE_FIELDS_CLEARED`). |
| `commission_payments` | `source` | `VARCHAR(30) NULL` | `NULL` = comissão do evento; `'vendedor_educamanto'` = comissão do vendedor. Imutável depois de criada. |
| `event_cancellations` | `educamanto_seller_id` | `INTEGER NULL` FK `users.id` (sem `ondelete`, como `commission_seller_id`) | Quem recebia a comissão do vendedor no ato. |
| `event_cancellations` | `educamanto_seller_commission` | `NUMERIC(12,2) NULL` | O valor no ato (a "cheia" do vendedor). |

Constante: `ORIGEM_VENDEDOR_EDUCAMANTO = "vendedor_educamanto"` (`app/constants.py`).

## As duas trilhas de `commission_payments`

- **Principal** (`source IS NULL`): tudo o que existe hoje — a comissão do evento, os ajustes da 306, os
  estornos. Beneficiário: o vendedor (comum) ou o responsável (EducaManto).
- **Vendedor** (`source = 'vendedor_educamanto'`): no máximo uma linha viva sem `original_id` por evento;
  ajustes da 306 da trilha nascem com o mesmo `source`; o estorno da exclusão copia o `source`.

Ciclo da linha do vendedor: `payable_from` = dia do evento (o principal), `sale_date` = data da venda.

## Estados da linha do vendedor (evento vivo)

| Situação do evento | Linha a pagar | Linha paga/no banco |
|---|---|---|
| valor > 0, EducaManto com responsável, vendedor com comissão, venda > 0, sem cortesia | nasce ou acompanha (valor, vendedor, datas, título) | intacta |
| qualquer condição acima falha (valor apagado, cortesia, sem vendedor, vendedor sem comissão, deixou de ser EducaManto, virou satélite) | vira `cancelado` (nota "Cancelado: sem comissão do vendedor") | intacta |
| evento cancelado | só a reconciliação mexe (R5) | só a reconciliação mexe |

## Base do responsável

```
custo   = Σ dias vivos ( cachês [_event_cost] + gastos extras aprovados, fora a devolução )
          + comissão do vendedor (quando há quem receba)
imposto = venda × alíquota ÷ 100, só com nota (alíquota de Configurações, padrão 16%)
base    = max(0, venda − BV − custo − imposto)
comissão do responsável = base × taxa (5%, Configurações ou a do evento), ROUND_HALF_UP
```

No ato do cancelamento, `commission_cost` congela o `custo` acima (cachês + gastos + vendedor); o imposto
é refeito pela venda congelada e por `event_cancellations.with_invoice`.

## Cancelado

- alvo do responsável: o de hoje (`comissao_do_retido(cheia, retido, venda)`).
- alvo do vendedor: `comissao_do_retido(educamanto_seller_commission, retido, venda)` para
  `educamanto_seller_id`; todo outro beneficiário com linha viva da trilha do vendedor → 0.
- `ResumoCancelado.comissao_vendedor_retido` entra no `efeito_resultado` e no total `comissao_retido` da DRE.
