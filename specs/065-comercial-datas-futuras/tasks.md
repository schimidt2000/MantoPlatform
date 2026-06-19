# Tasks: NF futura e parcelas com datas + recebimentos no painel

**Feature**: `065-comercial-datas-futuras` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Migration manual (head `s5b6c7d8e9f0`). Receita reconhecida NÃO muda. Verificação contra
**`manto_local` (Postgres)**.

---

## Fase 1 — Modelo + migration

- [X] T001 `app/models.py`: adicionar `class EventInstallment` (id, event_id FK, due_date Date, amount Numeric(12,2), received Bool default False, created_at) e a relação `CalendarEvent.installments` (cascade delete-orphan, order_by due_date). Adicionar coluna `CalendarEvent.invoice_due_date` (Date, nullable).
- [X] T002 Migration manual `migrations/versions/t6c7d8e9f0a1_event_installments_invoice_due_date.py` (down_revision `s5b6c7d8e9f0`): `op.create_table("event_installments", ...)` + `batch_alter_table("calendar_events").add_column(invoice_due_date)`. Downgrade reverte. Aplicar `flask db upgrade` no `manto_local`.

## Fase 2 — Backend

- [X] T003 [US1/US2] `app/calendar/routes.py::_handle_update_comercial`: ler `invoice_due_date` (quando `with_invoice`); aceitar método `parcelado_datas` e, nesse caso, apagar `EventInstallment` do evento e recriar a partir de `parcela_date[]`/`parcela_amount[]` (parse_brl; só linhas com data+valor).
- [X] T004 [US3] `app/financeiro/routes.py::dashboard`: montar `recebimentos_previstos` (EventInstallment com due_date no período e received False → data/evento/valor + total) e `nf_a_emitir` (eventos com invoice_due_date no período → data/evento/valor + total); passar ao template. **Não** alterar `_compute_drg`/DRE.

## Fase 3 — UI

- [X] T005 [US1/US2] `app/templates/event_detail.html`: botão de método **"Parcelado (datas)"**; bloco com lista dinâmica de parcelas (data + valor, add/remove via JS) e soma com aviso de divergência; campo **data de emissão da NF** (aparece quando "emitir nota").
- [X] T006 [US3] `app/templates/financeiro/dashboard.html`: seções **"Recebimentos previstos"** e **"NF a emitir"** (listas com data/evento/valor + total).

## Fase 4 — Verificação

- [X] T007 Verificar contra **`manto_local`**: aplicar migration; salvar evento com 2 parcelas + data NF (persiste/reexibe); painel lista recebimentos previstos e NF a emitir com totais; **receita do período inalterada**; métodos/comprovantes atuais ok. `ruff check` sem erros novos (comparar `git stash`).

---

## Dependências

- T001→T002→(T003,T004). T003 com T005; T004 com T006. T007 ao final.

## MVP

T001–T005 entregam o registro (parcelas+NF); T004/T006 entregam a visão no painel.
