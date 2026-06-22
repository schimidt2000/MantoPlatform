# Data Model — Notas fiscais (069)

## Nova tabela: `event_invoices`

| Campo        | Tipo           | Notas                                                        |
|--------------|----------------|-------------------------------------------------------------|
| id           | Integer PK     |                                                             |
| event_id     | Integer FK     | → `calendar_events.id`, NOT NULL, indexado                  |
| amount       | Numeric(12,2)  | valor da nota (nullable enquanto rascunho)                  |
| issue_date   | Date           | data de emissão (prevista ou real); nullable               |
| status       | String(12)     | "a_emitir" \| "emitida"; default "a_emitir"                 |
| file         | String(300)    | caminho do arquivo da nota; nullable                        |
| issued_at    | DateTime       | quando marcada emitida; nullable                            |
| created_at   | DateTime       | default utcnow                                              |

Relationship: `CalendarEvent.invoices` (lazy, cascade all/delete-orphan, order_by issue_date).

## Campos existentes (mantidos)

- `CalendarEvent.with_invoice` (bool) — "venda exige nota".
- `CalendarEvent.invoice_file`, `CalendarEvent.invoice_due_date` — **mantidos** (não dropar);
  migrados para uma `EventInvoice`. Lógica nova ignora-os.
- `SiteSetting.tax_rate` (float, 16% default) — percentual do custo de nota.

## Estados da nota

```
a_emitir  ──(super admin sobe arquivo + marca emitida)──▶  emitida
   ▲                                                          │
   └──────────── (vendedor já anexa arquivo na venda) ────────┘  (nasce emitida)
```

## Regras derivadas

- **Tarefa de emissão** = `EventInvoice.status == "a_emitir"` (de eventos com nota, não permuta).
- **Custo de nota (mês M)** = Σ `amount * tax_rate/100` das notas com `issue_date` em M.
- **Divergência** = `with_invoice` e `Σ amount(notas) != sale_value` → sinalizar.

## Migração (manual, idempotente)

Para cada evento com `invoice_file` ou `invoice_due_date` e sem linha em `event_invoices`:
inserir 1 nota (`amount=sale_value`, `issue_date=invoice_due_date`, `file=invoice_file`,
`status= emitida se file senão a_emitir`, `issued_at=now se emitida`).
