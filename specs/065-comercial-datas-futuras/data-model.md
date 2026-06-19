# Data Model: NF futura e parcelas com datas + recebimentos no painel (065)

## Mudanças no modelo (migration manual `t6c7d8e9f0a1`, down_revision `s5b6c7d8e9f0`)

### Nova tabela: `event_installments`

| Campo | Tipo | Notas |
|---|---|---|
| id | Integer PK | |
| event_id | Integer FK → calendar_events.id | NOT NULL; índice |
| due_date | Date | data de vencimento da parcela |
| amount | Numeric(12,2) | valor da parcela (R$) |
| received | Boolean | default False — marcada quando recebida |
| created_at | DateTime | default utcnow |

Relação: `CalendarEvent.installments` (lazy, `cascade="all, delete-orphan"`, `order_by due_date`).

### Coluna nova em `calendar_events`

| Campo | Tipo | Notas |
|---|---|---|
| invoice_due_date | Date (nullable) | data prevista de emissão da NF |

## Regras (derivadas)

```
parcelas(evento)        = EventInstallment do evento (ordenadas por due_date)
soma_parcelas           = Σ amount  (alerta informativo se ≠ sale_value)
recebimentos_previstos  = parcelas com due_date no período E received == False
nf_a_emitir             = eventos com invoice_due_date no período
receita reconhecida     = INALTERADA (Σ sale_value por start_at no período)
```

## Não altera

- `_compute_drg` / DRE / impostos: nada muda (receita por data do evento).
- `EventPayment` (comprovante), `payment_method`/`payment_installments`/`payment_due_date`:
  permanecem; o cronograma de parcelas é um método adicional (`parcelado_datas`).

## Migração

Manual: `op.create_table("event_installments", ...)` + `batch_alter_table("calendar_events").add_column(invoice_due_date)`.
Downgrade: drop coluna + drop tabela.
