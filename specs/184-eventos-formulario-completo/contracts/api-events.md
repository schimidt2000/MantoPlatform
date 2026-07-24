# Contrato de API — Eventos (feature 184)

Todas as rotas herdam `@api_login_required`. Auth por cookie de sessão HttpOnly (Flask-Login).
Erros seguem `json_error(msg, status, fields=...)` já padrão do repo. RBAC é checado por função
(não decorator), mesmo padrão de `agenda_write.py`.

## `PATCH /api/events/<int:event_id>` (novo)

Atualiza em bloco os campos centrais de um evento existente: dados do evento, valores, forma de
pagamento, elenco (reconciliado por `role_id`), clientes (substituição completa), coordenador e
pré-contrato vinculado.

**RBAC**: `_can_create_event()` — COMERCIAL ou SUPERADMIN (mesmo nível exigido para criar um
evento, por escrever os mesmos campos financeiros sensíveis).

Request body: ver `data-model.md` (forma completa).

Response `200`: `serialize_event_detail(event, current_user, impersonate)` — mesmo formato usado
por todo o resto da API de eventos.

Response `400` — mesma validação de `_validate_event_core` reaproveitada da criação (envelope
padrão de erro, `app/api_utils.py::json_error`):
```json
{ "error": { "message": "Corrija os campos destacados", "fields": { "sale_value": "Informe o valor de venda." } } }
```

Response `409` — remoção de personagem com convite aceito por ator não-SUPERADMIN:
```json
{ "error": { "message": "Não é possível remover \"Mickey\": o talento já aceitou o convite." } }
```

Response `403` — ator sem papel COMERCIAL/SUPERADMIN. Response `404` — evento não encontrado.

## `POST /api/events/<int:event_id>/contracts` (alterado)

Multipart, campo novo opcional `is_signed` (`"true"`/`"false"`, default `"false"`), além do já
existente `file` (obrigatório). RBAC inalterado (`_can_edit_event()`).

```
Content-Type: multipart/form-data
file: <binário>
is_signed: "true"
```

Response `201`: mesmo formato de sempre (full event detail). Nenhum outro campo de resposta novo.

## Endpoints já existentes, reaproveitados sem alteração (fase 2 de anexos)

Usados tanto pela criação (depois que `POST /api/events` devolve o `event.id`) quanto pela edição:

- `POST /events/<id>/payments` (multipart: `amount`, `file`) — comprovante de pagamento.
- `POST /events/<id>/reimbursements` (multipart: `description`, `amount`, `file?`) — reembolso
  (inclui a nota fiscal do gasto opcional).
- `POST /events/<id>/observations` (multipart: `obs_type=image`, `file`, `label?`) — observação
  com foto; `text`/`link` continuam JSON simples, já suportados.
- `DELETE /observations/<id>`, `DELETE /payments/<id>`, `DELETE /contracts/<id>`,
  `DELETE /reimbursements/<id>` — remoção de anexos já salvos (só usados na edição, um evento
  recém-criado ainda não tem anexos salvos para remover).

Nenhum desses contratos muda nesta feature.

## `POST /api/events` (criação — contrato inalterado)

O corpo deixa de incluir, na prática, `has_reembolso`/`reembolso_description`/`reembolso_amount`
(o frontend simplesmente para de enviá-los — o endpoint continua aceitando esses campos se
alguém os enviar, por compatibilidade, apenas não é mais o caminho usado pela tela nova). Nenhuma
mudança de schema no backend.
