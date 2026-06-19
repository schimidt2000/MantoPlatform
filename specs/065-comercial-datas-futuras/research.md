# Research: NF futura e parcelas com datas + recebimentos no painel (065)

Decisões técnicas. Decisões de produto confirmadas com o cliente (ver spec). Migration manual.

## 1. Estado atual

- `CalendarEvent` comercial: `sale_value`, `sale_value_gross`, `sale_date`, `with_invoice`
  (bool) + `invoice_file`, `payment_method` ('avista'|'pix_parcelado'|'faturado'|'cartao'|
  'futuro'), `payment_installments` (qtd), `payment_due_date` (uma data).
- `EventPayment` = comprovante (arquivo + valor) — recebimento já realizado, não cronograma.
- Painel (`financeiro/routes.py::dashboard`) reconhece receita por **`CalendarEvent.start_at`**
  (mês do evento); separa realizados/projetados; impostos sobre `with_invoice`.
- Salvamento comercial: `_handle_update_comercial` em `calendar/routes.py`.
- Migration head: **`s5b6c7d8e9f0`**.

## 2. Modelo novo (cronograma de parcelas)

- **Decisão**: nova tabela **`event_installments`** (id, event_id FK, due_date Date, amount
  Numeric(12,2), received Bool default False, created_at). Relação `event.installments`
  (cascade delete-orphan), ordenada por `due_date`.
- **Rationale**: parcela = recebimento planejado com data+valor (decisão Q2). Não mistura com
  `EventPayment` (comprovante de prova). Migration manual `op.create_table` (autogenerate
  quebrado).

## 3. NF em data futura

- **Decisão**: nova coluna **`calendar_events.invoice_due_date`** (Date, nullable) = data prevista
  de emissão da NF. Migration manual `batch_alter_table.add_column`.
- Mantém `with_invoice`/`invoice_file`. Reconhecimento de imposto **não muda** (segue por evento
  com NF no mês do evento — decisão Q1).

## 4. Salvamento comercial

- **Decisão**: novo método `parcelado_datas` na UI; em `_handle_update_comercial`, quando esse
  método, ler listas `parcela_date[]`/`parcela_amount[]` (máscara BR via `parse_brl`), apagar as
  `EventInstallment` do evento e recriar a partir das linhas válidas (data+valor presentes). Ler
  `invoice_due_date` quando `with_invoice`. Demais métodos inalterados.
- **Rationale**: reaproveita o handler único; `parse_brl` já trata máscara (feature 059).

## 5. Painel financeiro — visões (sem mudar DRE)

- **Decisão**: no `dashboard()`, montar:
  - `recebimentos_previstos` = `EventInstallment` com `due_date` no período e `received == False`,
    com evento + valor; total.
  - `nf_a_emitir` = eventos com `invoice_due_date` no período, com valor; total.
  - Passar ao template; render numa seção nova em `financeiro/dashboard.html`.
- **Rationale**: Q1 — receita segue por `start_at`; estas visões são informativas (fluxo de
  caixa), filtradas pelo período já existente. Não tocam no `_compute_drg`.

## 6. Permissões

- Edição comercial: `_handle_update_comercial` já restringe a COMERCIAL/FINANCEIRO/SUPERADMIN.
  Painel: `require_financeiro`. Sem mudança.

## 7. Migration

- Nova revisão `t6c7d8e9f0a1` (down_revision `s5b6c7d8e9f0`): cria `event_installments` e
  adiciona `invoice_due_date`. Escrita à mão; aplicada com `flask db upgrade` no `manto_local`
  para verificação.
