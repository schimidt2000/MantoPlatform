# Contrato de API — Revisão de Mídia (170)

Convenção de upload: `contracts/upload-endpoints.md` (feature 153) — multipart, resposta JSON.

## `GET /api/revisao/reviewer-options`

Gate: `can_create`. 200: `{"items": [{"id","name"}, ...]}` (usuários ativos com acesso,
elegíveis como revisores).

## `GET /api/revisao`

Gate: autenticado. 200: `{"items": [{"id","title","created_at","asset_count"}, ...],
"can_create": bool}`.

## `POST /api/revisao` (multipart)

Gate: `can_create` (MARKETING/SUPERADMIN). Campos: `title`, `description`?,
`reviewer_ids[]`?, `files` (arquivo(s))?. 201: `{"id", ...}`. 400 título vazio.

## `GET /api/revisao/<id>`

Gate: `can_view`. 200: espaço completo (materiais, revisores, `can_manage`, `invite_text`).
403/404.

## `POST /api/revisao/<id>/upload` (multipart)

Gate: `can_manage`. Campo `files`. 200: `{"saved", "errors": [...]}`.

## `PATCH /api/revisao/<id>/reviewers`

Gate: `can_manage`. Body: `{"reviewer_ids": [...]}`. 200.

## `DELETE /api/revisao/<id>`

Gate: `can_manage`. 204. Remove arquivos (atual + versões) de todos os materiais.

## `GET /api/revisao/<space_id>/asset/<asset_id>?v=`

Gate: `can_view`. 200: material + (se `v` informado e ≠ atual) snapshot da versão + histórico.
404 se versão não existir.

## `DELETE /api/revisao/asset/<asset_id>`

Gate: `can_manage`. 204.

## `POST /api/revisao/asset/<asset_id>/replace` (multipart)

Gate: `can_manage`. Campo `file`. 200: material atualizado. 400 tipo incompatível/tamanho.

## `POST /api/revisao/asset/<asset_id>/finalize`

Gate: `can_manage`. 200.

## `GET /api/revisao/asset/<asset_id>/comments?v=`

Gate: `can_view`. 200: `[{comentário...}, ...]` da versão informada (default: atual).

## `POST /api/revisao/asset/<asset_id>/comment`

Gate: `can_view`. Body: `{"body", "timecode"?, "page"?, "pos_x"?, "pos_y"?, "version"?}`. 201.
400 corpo vazio. 409 versão diferente da atual.

## `POST /api/revisao/comment/<id>/resolve`

Gate: `can_resolve`. 200: alterna resolved/reaberto.

## `DELETE /api/revisao/comment/<id>`

Gate: `can_delete_comment`. 204.
