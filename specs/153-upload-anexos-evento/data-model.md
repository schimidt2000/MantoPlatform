# Data Model — Upload e Gestão de Anexos do Evento (153)

Nenhum modelo novo. Os cinco modelos já existem em `app/models.py`; esta fatia só adiciona
formas de gravar/ler campos que já existem. Nenhuma migration é necessária.

## EventInvoice (`event_invoices`)

| Campo | Tipo | Observação |
|---|---|---|
| `amount` | Numeric(12,2) nullable | valor da nota |
| `issue_date` | Date nullable | data de emissão |
| `status` | String(12) | `"a_emitir"` \| `"emitida"` — `"emitida"` sempre que há `file` |
| `file` | String(300) nullable | `/uploads/invoices/<nome>` |
| `issued_at` | DateTime nullable | setado junto com `status="emitida"` |

**Ação desta fatia**: criar (`POST /api/events/<id>/invoices`). Sem editar/excluir (ver plan.md
Design Decision 3 — reconciliação completa continua no formulário de venda, Jinja-only).

## EventContract (`event_contracts`)

| Campo | Tipo | Observação |
|---|---|---|
| `file_path` | String(300) not null | `/uploads/contracts/<nome>` |
| `amount` | Integer nullable | não coletado pela ação "adicionar" (só na criação do evento, fora de escopo) |
| `is_signed` | Boolean default False | alternável por SUPERADMIN |

**Ações desta fatia**: criar, excluir, alternar `is_signed` (as duas últimas SUPERADMIN).

## EventPayment (`event_payments`)

| Campo | Tipo | Observação |
|---|---|---|
| `file_path` | String(300) not null | `/uploads/payments/<nome>` |
| `amount` | Numeric(12,2) nullable | editável por SUPERADMIN |

**Ações desta fatia**: criar, editar valor (SUPERADMIN), excluir (SUPERADMIN).

## EventReimbursement (`event_reimbursements`)

| Campo | Tipo | Observação |
|---|---|---|
| `description` | String(200) not null | |
| `amount` | Numeric(12,2) not null | valor a cobrar da cliente |
| `invoice_file_path` | String(300) nullable | comprovante do gasto original — **novo nesta fatia** |
| `is_collected` | (property/coluna) | `True` quando `collected_at is not None` |
| `collected_at` | DateTime nullable | setado ao marcar cobrado |
| `collected_amount` | Numeric(12,2) nullable | valor recebido |
| `receipt_file_path` | String(300) nullable | comprovante de recebimento — **novo nesta fatia** |
| `collected_by_id` | FK users nullable | |

**Ações desta fatia**: criar (com `invoice_file_path` opcional — hoje sempre `None` vindo da
API, feature 152), marcar como cobrado (`collected_amount` + `receipt_file_path`
obrigatórios), excluir (SUPERADMIN).

## EventObservation (`event_observations`, `obs_type="image"`)

| Campo | Tipo | Observação |
|---|---|---|
| `obs_type` | String(10) | `"image"` para esta fatia |
| `file_path` | String(500) nullable | `/uploads/event_obs/<nome>` — **gravável nesta fatia** |
| `label` | String(200) nullable | legenda opcional |

**Ação desta fatia**: criar via `POST /api/events/<id>/observations` (multipart quando
`obs_type == "image"`). Já existe o modelo de exclusão via `DELETE /api/observations/<id>`
(feature 150) — reaproveitado sem mudança, cobre imagem também.

## Limites de tamanho (herdados, sem mudança)

| Anexo | Limite | Origem |
|---|---|---|
| Nota fiscal | 10 MB | `_save_nf_file` |
| Contrato (ação "adicionar") | 10 MB | `_handle_add_contract` → `_save_bounded_upload` |
| Comprovante de pagamento | 10 MB | `_handle_add_payment`/`_handle_collect_reembolso` → `_save_bounded_upload` |
| Comprovante de reembolso (gasto original) | 10 MB | `_save_nf_file` |
| Observação — imagem | 20 MB | `_save_file_upload` (inalterado) |
