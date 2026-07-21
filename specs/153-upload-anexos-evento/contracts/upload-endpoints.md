# Contrato de API — Upload e Gestão de Anexos do Evento (153)

Estende `specs/144-migracao-react-spa/contracts/api-conventions.md` com a convenção
**multipart/form-data**, usada pela primeira vez nesta fatia.

## Convenção multipart (nova, normativa para toda rota futura de upload)

- Requisição: `Content-Type: multipart/form-data`. Campos não-arquivo vão como campos de
  formulário comuns (mesmo nome, sem colchetes — cada endpoint aqui recebe um único arquivo).
- Resposta: **inalterada** em relação ao padrão JSON já em vigor — sucesso é o objeto/lista
  de sempre, erro é `{"error": {"message", "fields"?}}`, mesmos códigos HTTP.
- Endpoint que só edita/apaga (sem arquivo na requisição) continua `Content-Type:
  application/json` normal — só quem recebe arquivo muda de content-type.
- Toda resposta de sucesso desta fatia é `_event_detail_json(event)` — o mesmo shape de
  `GET /api/events/<id>` (`EventoDetalhe` no frontend) — para o cliente substituir o cache
  inteiro do evento em um único `setQueryData`, mesmo padrão já usado por
  confirm/logistics/sync/observations.

## `GET /api/events/<id>` (agenda_read.py) — campos novos na resposta existente

Sem endpoint novo — `serialize_event_detail` ganha/completa estes campos (bloco
`show_comercial`/`show_financeiro`, mesma visibilidade de hoje):

- `data["notas_fiscais"]` (novo): `[{"id", "amount", "issue_date", "status", "file"}]`
- `data["contratos"][*]`: sem mudança de shape (`file_path`/`is_signed` já existiam)
- `data["pagamentos"]["items"][*]`: `+ "file_path"`
- `data["reembolsos"]["items"][*]`: `+ "invoice_file_path"`, `+ "collected_amount"`,
  `+ "receipt_file_path"`

## `POST /api/events/<id>/invoices`

- Gate: `_CAN_EDIT_EVENT`. Multipart: `amount` (número puro, opcional), `issue_date`
  (`YYYY-MM-DD`, opcional), `file` (opcional).
- 400 se os três vierem vazios: `{"error": {"message": "Informe ao menos o valor, a data ou o
  arquivo da nota."}}`
- 201: evento atualizado.

## `POST /api/events/<id>/contracts`

- Gate: `_CAN_EDIT_EVENT`. Multipart: `file` (obrigatório).
- 400: `{"error": {"message": "Selecione o arquivo do contrato.", "fields": {"file": "Obrigatório"}}}`
- 400 se arquivo > 10 MB: `{"error": {"message": "Arquivo do contrato acima de 10 MB — envie um arquivo menor."}}`
- 201: evento atualizado.

## `DELETE /api/contracts/<id>`

- Gate: SUPERADMIN. 403 para qualquer outro papel. 404 se não existir.
- 200: evento atualizado.

## `POST /api/contracts/<id>/toggle-signed`

- Gate: SUPERADMIN. Sem corpo. Inverte `is_signed`.
- 200: evento atualizado.

## `POST /api/events/<id>/payments`

- Gate: `_CAN_EDIT_EVENT` (CASTING/FIGURINO/COMERCIAL/FINANCEIRO/SUPERADMIN) — gate efetivo
  herdado do dispatcher `event_detail` no Jinja, que gateia todo POST daquela rota antes de
  despachar para qualquer `_handle_*` (`_handle_add_payment` não checa papel por dentro, mas
  nunca é chamado sem passar por esse gate primeiro). Multipart: `amount` (número puro,
  obrigatório), `file` (obrigatório).
- 400 se faltar valor: `{"error": {"message": "Informe o valor recebido para adicionar o pagamento.", "fields": {"amount": "Obrigatório"}}}`
- 400 se faltar arquivo: `{"error": {"message": "Anexe o comprovante para adicionar o pagamento.", "fields": {"file": "Obrigatório"}}}`
- 201: evento atualizado.

## `PATCH /api/payments/<id>`

- Gate: SUPERADMIN. JSON: `{"amount": number}`.
- 400 se valor inválido/≤0. 200: evento atualizado.

## `DELETE /api/payments/<id>`

- Gate: SUPERADMIN. 200: evento atualizado.

## `POST /api/events/<id>/reimbursements`

- Gate: `_CAN_EDIT_EVENT` (herdado do dispatcher `event_detail`, mesma observação do endpoint
  de pagamento acima). Multipart: `description` (obrigatório), `amount` (número puro,
  obrigatório), `file` (opcional — comprovante do gasto original).
- 400 se faltar descrição ou valor. 201: evento atualizado.

## `POST /api/reimbursements/<id>/collect`

- Gate: `_CAN_EDIT_EVENT` (checado antes da validação de `is_collected`, mesma ordem do
  dispatcher Jinja: permissão sempre antes de regra de negócio). Multipart:
  `collected_amount` (número puro, obrigatório), `file` (obrigatório — comprovante de
  recebimento).
- 400 se já `is_collected`: `{"error": {"message": "Esse reembolso já foi marcado como cobrado."}}`
- 400 se faltar valor ou arquivo. 200: evento atualizado.

## `DELETE /api/reimbursements/<id>`

- Gate: SUPERADMIN. 200: evento atualizado.

## `POST /api/events/<id>/observations` (existente, feature 150 — estendido)

- Gate inalterado: `@login_required`, sem papel.
- **JSON** (`Content-Type: application/json`, inalterado): `{"obs_type": "text"|"link",
  "content", "label"?}`.
- **Multipart** (novo): `obs_type=image`, `label` (opcional), `file` (obrigatório).
- 400 se `obs_type` inválido ou faltar conteúdo/arquivo conforme o tipo.
- 200: evento atualizado (endpoint já retornava isso).
