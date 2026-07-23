# Contrato de API — Portal do Artista (fatia 1)

Herda as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md`
(envelope de sucesso/erro, códigos HTTP), com uma exceção: a sessão usa a chave `talent_id`
(não Flask-Login), então "autenticado" aqui significa `session.get("talent_id")` presente.
Upload segue a convenção multipart introduzida na feature 153. RBAC = "é o dono do recurso":
toda consulta já filtra por `talent_id` da sessão, nunca aceita um id de talento vindo do
cliente.

## Auth (`app/api/portal_auth.py`)

### `POST /api/portal/auth/login`

- Body: `{"login": string, "password": string}` (`login` = CPF ou e-mail, mesma resolução de
  `_talent_by_login` do legado)
- 200: `{"id", "full_name", "artistic_name", "must_redirect_to_classic": bool}` + `Set-Cookie`
  da sessão (`session["talent_id"]`). `must_redirect_to_classic=true` quando
  `must_change_password` ou `terms_accepted_at is None` — o app React deve fazer um redirect de
  página inteira para `/portal/login` nesse caso (ver research.md).
- 401: `{"error": {"message": "CPF/e-mail ou senha incorretos."}}`

### `POST /api/portal/auth/logout`

- 204, `session.pop("talent_id")`

### `GET /api/portal/auth/me`

- 200: `{"id", "full_name", "artistic_name", "photo_face_url", "photo_full_url"}`
- 401: sem sessão válida

## Agenda e Convites (`app/api/portal_agenda.py`)

### `GET /api/portal/agenda`

- 200: `{"pending_invites": [...], "upcoming": [...], "history": [...]}` — cada item:
  `{"role_id", "event_id", "title", "start_at", "end_at", "location", "character_name",
  "has_unacknowledged_change": bool}`; itens de `history` incluem também `"cache_total",
  "payment_status"`.
- 401: sem sessão válida

### `POST /api/portal/invites/<int:role_id>/accept`

- 200: `{"role_id", "invite_status": "accepted"}` — idempotente (repetir não gera erro)
- 404: convite não pertence ao talento da sessão (mesma regra do `first_or_404` legado)

### `POST /api/portal/invites/<int:role_id>/reject`

- 200: `{"role_id", "invite_status": "rejected"}` — idempotente
- 404: convite não pertence ao talento da sessão

### `POST /api/portal/roles/<int:role_id>/ack-change`

- 200: `{"role_id"}` — limpa `event_changed_at`/`change_description` (paridade com
  `ack_event_change` legado)
- 404: role não pertence ao talento

## Figurino (`app/api/portal_figurino.py`)

### `GET /api/portal/events/<int:event_id>/figurino`

- 200: `{"event": {"id","title","start_at"}, "sheets": [{"character_name","photo_url","notes","pieces"}]}`
- 403: talento não está escalado no evento (nem pendente nem aceito)
- 200 com `"sheets": []`: talento escalado mas sem ficha cadastrada ainda (estado vazio, não erro)

## Fotos/Documentos (`app/api/portal_profile.py`)

### `POST /api/portal/profile/photo` (multipart/form-data)

- Campos: `kind` (`"face"` ou `"full"`), `file`
- 200: `{"photo_face_url", "photo_full_url"}` (estado atualizado)
- 400: `{"error": {"message": "..."}}` — formato não aceito ou acima do limite (reusa
  `cadastro_ops.validate_upload`, `PHOTO_EXTS`/`PHOTO_MAX`)

### `POST /api/portal/profile/document` (multipart/form-data)

- Campos: `file` (CNH)
- 200: `{"cnh_file_url"}`
- 400: formato/tamanho inválido (reusa `cadastro_ops.validate_upload`, `DOC_EXTS`/`DOC_MAX`)

## Fora de escopo desta fatia

Primeiro acesso, troca de senha, aceite de termos, esqueci a senha, avaliação de eventos, edição
de dados de perfil além de fotos/CNH — endpoints Jinja legados (`app/talent_portal/routes.py`)
continuam servindo essas telas sem equivalente em `/api/portal/*` por enquanto.
