# Contrato de API — Talentos e Figurino (154)

Segue as convenções gerais já em vigor: `specs/144-migracao-react-spa/contracts/
api-conventions.md` (envelope de sucesso/erro, JSON puro — nenhum endpoint desta fatia recebe
arquivo).

## `GET /api/talents/directory`

- Gate: `@api_login_required` (leitura aberta a qualquer autenticado, paridade com
  `list_talents`).
- Query: `status` (`active`\|`pending`, default `active`), `q`, `ja_trabalhou` (`0`\|`1`),
  `language[]`, `race[]`, `top[]`, `bottom[]`, `shoe[]`, `height_op` (`gte`\|`lte`),
  `height_value`, `passport[]`, `tag[]`, `character`, `page` (default 1).
- 200:
  ```json
  {
    "items": [{"id", "full_name", "artistic_name", "status", "warning_level",
               "photo_face_path", "height_cm", "clothing_size_top", "clothing_size_bottom",
               "shoe_size", "character_matches": {"<nome>": <contagem>}}],
    "total": int, "page": int, "pages": int, "pending_count": int,
    "filter_options": {"languages": [...], "races": [...], "tags": [...],
                        "sizes": [...], "shoes": [...],
                        "passport": [["visa","..."],["passport","..."],["none","..."]]}
  }
  ```
  `filter_options` só presente quando `status=active` (mesma condição de hoje).

## `GET /api/talents/<id>`

- Gate: leitura aberta.
- 200: `{"talent": {...campos de data-model.md...}, "history": {...}, "can_edit": bool}`
- 404 se não existir.

## `PATCH /api/talents/<id>`

- Gate: CASTING/SUPERADMIN. 403 caso contrário.
- Body: JSON com os campos editáveis (ver data-model.md, exceto `status`/`notes`/
  `warning_level`, que têm endpoints próprios). `cpf` só é aplicado se o requisitante for
  SUPERADMIN — se enviado por não-superadmin, é ignorado silenciosamente (paridade: o campo
  nem aparece no form para quem não é superadmin).
- 400 `{"fields": {"cpf": "..."}}` se CPF com menos/mais de 11 dígitos ou já usado por outro
  talento.
- 200: talento atualizado.

## `POST /api/talents/<id>/approve`

- Gate: CASTING/SUPERADMIN.
- Sem corpo. 200 sempre (idempotente — paridade com `approve_talent`, que não valida o status
  atual).

## `POST /api/talents/<id>/reject`

- Gate: CASTING/SUPERADMIN.
- Sem corpo. 400 `{"message": "Só é possível rejeitar cadastros pendentes."}` se
  `status != "pending"`. 200 `{"ok": true}` se removido (recurso deixa de existir).

## `POST /api/talents/<id>/notes`

- Gate: CASTING/SUPERADMIN.
- Body: `{"notes": str, "warning_level": ""|"leve"|"moderado"|"grave"}`.
- 200: talento atualizado.

## `GET /api/figurino`

- Gate: leitura aberta.
- 200: `{"items": [{"id", "character_name", "pieces", "notes", "photo_url", "updated_at"}],
  "chars_without_sheet": [str]}`.

## `POST /api/figurino`

- Gate: FIGURINO/SUPERADMIN.
- Body: `{"character_name": str, "pieces": [{"name", "qty"}], "notes": str}`.
- 400 `{"fields": {"character_name": "Obrigatório"}}` se nome vazio.
- 201: ficha criada.

## `PATCH /api/figurino/<id>`

- Gate: FIGURINO/SUPERADMIN. Mesmo body/validação de criar.
- 200: ficha atualizada.

## `DELETE /api/figurino/<id>`

- Gate: FIGURINO/SUPERADMIN.
- 200 `{"ok": true}` — desvincula `EventRole.figurino_sheet_id` de qualquer cargo antes de
  excluir (sem erro se nenhum cargo usava a ficha).
