# Contract: Upload Endpoints (155)

Convenção geral: `specs/144-migracao-react-spa/contracts/api-conventions.md` (seção "Upload de
arquivo"). Envelope de sucesso/erro igual a qualquer outro endpoint — só a requisição de upload
muda de `application/json` para `multipart/form-data`.

## `POST /api/talents/<id>/photo`

- **Auth**: sessão válida + CASTING/SUPERADMIN (`_can_edit_talent()`), senão 403.
- **Requisição**: `multipart/form-data`
  - `photo_type` (form field, obrigatório): `face` | `full` | `doc` | `cnh`
  - `photo` (file, obrigatório)
- **200 desconhecido → 400**: `photo_type` fora da lista → `{"error": {"message": "..."}}`
- **400**: extensão não aceita para o `photo_type` (face/full: jpg/png/webp; doc/cnh: +pdf)
- **404**: talento não encontrado
- **200**: talento atualizado — mesmo shape de `talent` em `GET /api/talents/<id>` (sem
  `history`)

## `DELETE /api/talents/<id>/photo?photo_type=...`

- **Auth**: idem acima.
- **Requisição**: querystring `photo_type` (obrigatório, mesmos 4 valores)
- **200**: talento atualizado (mesmo shape acima); no-op seguro se campo já vazio
- **400**: `photo_type` inválido
- **404**: talento não encontrado

## `POST /api/figurino/<id>/photo`

- **Auth**: sessão válida + FIGURINO/SUPERADMIN (`_can_edit_figurino()`), senão 403.
- **Requisição**: `multipart/form-data`, `photo` (file, obrigatório)
- **400**: extensão não aceita (jpg/png/webp) ou arquivo ausente
- **404**: ficha não encontrada
- **200**: ficha atualizada — mesmo shape de `POST /api/figurino`

## `DELETE /api/figurino/<id>/photo`

- **Auth**: idem acima.
- **200**: ficha atualizada; no-op seguro se `photo_filename` já vazio
- **404**: ficha não encontrada

## `POST /api/figurino/<id>/photo/rotate`

- **Auth**: idem acima.
- **Requisição**: `application/json`, `{"direction": "cw" | "ccw"}` (default `"cw"` se omitido)
- **400**: sem foto, foto em URL não-local (legado Drive), ou falha ao processar a imagem
- **404**: ficha não encontrada
- **200**: ficha atualizada com nova `photo_url`
