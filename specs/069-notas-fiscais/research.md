# Research: Notas fiscais (069)

Decisões técnicas. **Migration manual** (autogenerate quebrado).

## 1. Estado atual

- `CalendarEvent.with_invoice` (bool), `invoice_file` (1 arquivo), `invoice_due_date` (1 data) —
  feature 065.
- `financeiro/routes.py::_compute_drg`: já calcula `impostos` = `tax_rate`% de `sale_value` para
  eventos `with_invoice` (competência = data do evento). **Não muda** nesta feature.
- Dashboard já tem bloco "NF a emitir" (eventos com `invoice_due_date` no período) — meramente
  informativo, 1 por evento.
- `_handle_update_comercial` grava `with_invoice`/`invoice_file`/`invoice_due_date`.
- `tax_rate` default 16% em `SiteSetting` (`_get_tax_rate`).

## 2. Novo modelo `EventInvoice`

- **Decisão**: tabela `event_invoices` com `event_id`, `amount` (Numeric 12,2), `issue_date`
  (Date, data de emissão prevista/real), `status` ("a_emitir" | "emitida"), `file` (String,
  nullable), `issued_at` (DateTime, nullable), `created_at`.
- **Rationale**: cada nota com valor + data próprios (clarificação do cliente). Custo = 16% por nota.
- Mantém `with_invoice` no evento ("venda exige nota"). Colunas antigas `invoice_file`/
  `invoice_due_date` ficam (não dropar) p/ segurança; lógica passa a usar `EventInvoice`.

## 3. Migração de dados (065 → 069)

- Para cada evento com `invoice_file` OU `invoice_due_date` preenchidos e **sem** `EventInvoice`,
  criar 1 nota: `amount = sale_value`, `issue_date = invoice_due_date`, `file = invoice_file`,
  `status = "emitida"` se tinha arquivo senão `"a_emitir"`, `issued_at = now` se emitida.
- Feito **dentro da migration** (op.execute / inserts via SQL), idempotente.

## 4. Tarefa de emissão (super admin)

- **Decisão**: notas `status == "a_emitir"` = tarefas. Evoluir o bloco "NF a emitir" do dashboard
  para listar **por nota** (não por evento), com ação **subir arquivo + marcar emitida**. Badge de
  contagem no home para SUPERADMIN/FINANCEIRO.
- Rota nova: `POST /financeiro/nf/<invoice_id>/emitir` (sobe arquivo opcional, status→emitida,
  `issued_at=now`). `require_financeiro`.

## 5. Custo de nota por mês de emissão

- **Decisão**: novo cálculo no dashboard — notas com `issue_date` no período → custo = `tax_rate`%
  de `amount`. Total + lista detalhada (evento, valor da nota, data, custo). Separado da DRE.
- **Rationale**: visão de caixa pedida ("quanto gastamos com pagamento de nota por mês").

## 6. Comercial (CRUD de notas)

- **Decisão**: na seção "Dados de Venda" do `event_detail`, quando `with_invoice`, lista dinâmica de
  notas (valor + data + arquivo opcional), estilo das parcelas (065). Backend em
  `_handle_update_comercial`: recria/atualiza as `EventInvoice` do evento a partir das linhas; se a
  linha tem arquivo → emitida; sinaliza quando soma ≠ total (flash informativo).
- Máscara `brl-input` nos valores (FR-010).

## 7. Verificação

- Contra **`manto_local`** (Postgres): criar evento com nota, 2 notas datas diferentes; conferir
  tarefa a emitir, emitir 1, custo por mês de emissão + detalhe; DRE inalterada. `ruff` sem erros
  novos. Migração de evento legado preserva a nota.

## 8. Sem libs novas

- Reusa `parse_brl`, `money-mask.js`, `UPLOAD_INVOICES`, `_get_tax_rate`, padrões de upload.
