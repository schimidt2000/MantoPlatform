# Contrato de API — Gestão de Catálogo (169)

Gate: SUPERADMIN em todos.

## `GET /api/admin/catalogo`

Querystring: `q`?, `categoria`? (id), `status`? (`ativo`|`inativo`|`todos`, default `todos`).
200: `{"items": [{"id","name","slug","is_active","cover_url","category_names":[...]}, ...],
"categories": [{"id","name"}, ...]}`.

## `GET /api/admin/catalogo/<id>`

200: `{"id","name","description","tags":[...],"is_active","category_ids":[...],
"images":[{"id","url","position"}, ...]}`. 404 se não existir.

## `POST /api/admin/catalogo/categorias`

Body: `{"name"}`. 200: `{"id","name"}`. 400 nome vazio.

## `POST /api/admin/catalogo` (multipart)

Campos: `name`, `description`?, `tags` (string separada por vírgula)?, `category_ids[]`?,
`new_photos` (arquivo(s)), `cover_photo_id`|`new_photo_cover_index`?. 201: produto criado (mesmo
shape do detalhe). 400 com `fields` (`name`, `photos`).

## `PATCH /api/admin/catalogo/<id>` (multipart)

Mesmos campos da criação + `remove_photo_ids[]`?, `photo_order`? (ids separados por vírgula, na
ordem final desejada das fotos restantes). 200: produto atualizado. 400 se ficar sem foto.

## `POST /api/admin/catalogo/<id>/toggle-ativo`

200: produto atualizado.

## `DELETE /api/admin/catalogo/<id>`

204. Remove os arquivos de foto do armazenamento.
