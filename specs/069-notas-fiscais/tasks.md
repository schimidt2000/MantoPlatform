# Tasks: Notas fiscais (069)

**Feature**: `069-notas-fiscais` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Migration **manual**. Verificação do **ciclo completo** contra **`manto_local`** (Postgres).

---

## Fase 1 — Modelo + migration

- [X] T001 `app/models.py`: criar `class EventInvoice` (`event_invoices`: event_id, amount, issue_date, status, file, issued_at, created_at) + relationship `CalendarEvent.invoices` (cascade all/delete-orphan, order_by issue_date).
- [X] T002 `migrations/versions/v8e9f0a1b2c3_event_invoices.py` (down_revision = head u7d8e9f0a1b2): `op.create_table` de `event_invoices` + índice em `event_id`; depois migrar a nota única (065) — inserir 1 `event_invoice` por evento com `invoice_file`/`invoice_due_date` e sem nota (amount=sale_value, issue_date=invoice_due_date, file=invoice_file, status emitida/a_emitir, issued_at). Idempotente.

## Fase 2 — Comercial: CRUD das notas (US1/US2)

- [X] T003 [US2] `app/calendar/routes.py::_handle_update_comercial`: ler linhas `nf_amount[]`/`nf_date[]`/`nf_file[]` (+ ids existentes), recriar/atualizar `EventInvoice` do evento; linha com arquivo → `emitida` (issued_at=now); sem arquivo → `a_emitir`. Flash informativo quando Σ amount ≠ sale_value. Só quando `with_invoice`.
- [X] T004 [US1] `app/templates/event_detail.html` (seção Dados de Venda): lista dinâmica de notas (valor `brl-input` + data + arquivo opcional + estado + link do arquivo), JS add/remove (padrão das parcelas/065), exibida quando "com nota".

## Fase 3 — Emissão pelo super admin (US1)

- [X] T005 [US1] `app/financeiro/routes.py`: rota `POST /financeiro/nf/<int:invoice_id>/emitir` (`require_financeiro`): sobe arquivo opcional p/ `UPLOAD_INVOICES`, `status="emitida"`, `issued_at=now`; valida pertencer a evento com nota.
- [X] T006 [US1] `app/financeiro/routes.py` dashboard: "NF a emitir" passa a listar **por nota** (`EventInvoice.status=="a_emitir"`), com form de emitir (arquivo + botão). Contagem p/ badge.
- [X] T007 [US1] `app/templates/home.html`: badge/atalho "Notas a emitir" para SUPERADMIN/FINANCEIRO (contagem de notas a emitir).

## Fase 4 — Custo de nota por mês de emissão (US3)

- [X] T008 [US3] `app/financeiro/routes.py` dashboard: calcular `custo_nota` do período = Σ `amount*tax_rate/100` das notas com `issue_date` no período (mês de emissão) + lista detalhada (evento, valor da nota, data, custo). Passar ao template. **DRE inalterada.**
- [X] T009 [US3] `app/templates/financeiro/dashboard.html`: card "Custo de Notas Fiscais" do período + tabela detalhada (evento/valor/data/custo). Manter a DRE como está.

## Fase 5 — Verificação (ciclo completo)

- [X] T010 Contra **`manto_local`**: criar evento com nota; nota a emitir → tarefa do super admin → emitir; 2 notas em datas diferentes (custo por mês de emissão + detalhe); divergência sinalizada; DRE inalterada; migração de evento legado preserva a nota. `ruff check` sem erros novos.

---

## Dependências

- T001 → T002 → T003 → (T005, T008). T004 depende de T003; T006/T007 de T005; T009 de T008. T010 ao final.

## MVP

US1 (tarefa de emissão) + modelo/migration. US2 (múltiplas) e US3 (custo por mês) completam o pedido.
