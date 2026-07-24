# Contrato de API: Catálogo (feature 185)

Segue o envelope de erro e as convenções já definidas em
`specs/144-migracao-react-spa/contracts/api-conventions.md` (`json_error(msg, status, fields=...)`).
Todas as rotas novas nascem em `app/api/*`, delegando a `*_ops.py` (Princípio III).

## Público (sem autenticação) — `app/api/catalogo_read.py`

### `GET /api/catalogo/<slug>` (estende a rota existente)

Resposta 200 — campos **novos** em relação ao contrato atual:

```jsonc
{
  "id": 1, "name": "...", "slug": "...", "description_html": "...",
  "video_url": "https://drive.google.com/uc?export=download&id=...",   // novo, nullable
  "video_kind": "drive",                                                // novo: "mp4"|"drive"|"vimeo"|null
  "categories": [...], "images": [...], "related": [...],
  "characters": [                                                       // novo
    {
      "id": 10, "name": "Gatuno", "slug": "a-casa-magica-da-gabby-gatuno",
      "photo_url": "/uploads/catalog_characters/....jpg",
      "video_url": "https://vimeo.com/...", "video_kind": "vimeo"
    }
  ]
}
```

`characters` só inclui Personagens com `is_active = true`, ordenados por `position`.

## Interno — leitura (`app/api/admin_catalogo_read.py`)

### `GET /api/admin/catalogo/<item_id>` (estende a rota existente)

Resposta 200 — adiciona `video_url` (raw, sem `video_kind` — validação é client-side também, mas
fonte de verdade é o backend) e `characters`, incluindo os **inativos** e com `figurino_sheet_id`:

```jsonc
{
  "id": 1, "name": "...", "description": "...", "tags": [...], "is_active": true,
  "category_ids": [...], "images": [...],
  "video_url": "https://...",                          // novo, nullable
  "characters": [                                       // novo
    {
      "id": 10, "name": "Gatuno", "slug": "...",
      "photo_url": "...", "video_url": "...",
      "figurino_sheet_id": 42, "position": 0, "is_active": true
    }
  ]
}
```

## Interno — escrita (`app/api/admin_catalogo_write.py`)

Gate: `require_superadmin` (mesmo padrão das rotas existentes).

### `POST /api/admin/catalogo` e `PATCH /api/admin/catalogo/<item_id>` (estendem as rotas existentes)

Multipart form — campo novo: `video_url` (string, opcional). Erro de validação:
`400 { "error": "...", "fields": { "video_url": "..." } }`.

### `POST /api/admin/catalogo/<item_id>/personagens` — cria um Personagem

Multipart form: `name` (obrigatório), `video_url` (opcional), `photo` (file, opcional),
`figurino_sheet_id` (opcional, int).

- 201 → objeto do Personagem (forma de `characters[]` acima, com `figurino_sheet_id`).
- 400 → `CatalogValidationError` (`name` ou `video_url` inválidos), `fields`.
- 404 → Tema (`item_id`) não encontrado.

### `PATCH /api/admin/catalogo/personagens/<character_id>` — edita um Personagem

Mesmos campos do create, todos opcionais (envia só o que muda); aceita também `position`
(int, para reordenação) e `remove_photo` (bool, remove a foto sem enviar uma nova).

- 200 → objeto atualizado.
- 400 → validação.
- 404 → Personagem não encontrado.

### `DELETE /api/admin/catalogo/personagens/<character_id>` — exclui um Personagem

- 204 → sucesso (remove foto do storage via `delete_file`, mesmo padrão de `CatalogItemImage`).
- 404 → não encontrado.

## Integração com Eventos — leitura para a `ElencoBlock`

A grade pública (`GET /api/catalogo`) não expõe `figurino_sheet_id` (dado interno). O time
comercial cria eventos com o papel `COMERCIAL` (não necessariamente `SUPERADMIN`), então os
endpoints de `admin_catalogo_write.py`/`admin_catalogo_read.py` (gate `SUPERADMIN`) não servem
para essa busca. Endpoint novo, autenticado mas **não** restrito a superadmin:

### `GET /api/catalogo/elenco-busca` — `app/api/catalogo_read.py`

Gate: usuário autenticado com papel `COMERCIAL` ou `SUPERADMIN` (mesmo padrão de
`_has_role`/`json_error(..., 403)` já usado em `agenda_write.py`).

Resposta 200 — Temas ativos com seus Personagens ativos, achatados para facilitar a busca no
formulário (sem paginação — volume do catálogo é pequeno o bastante para lista única, mesmo
padrão de `GET /api/catalogo`):

```jsonc
{
  "temas": [
    {
      "id": 1, "name": "A Casa Mágica da Gabby", "slug": "a-casa-magica-da-gabby",
      "characters": [
        { "id": 10, "name": "Gatuno", "figurino_sheet_id": 42 },
        { "id": 11, "name": "Gabby", "figurino_sheet_id": null }
      ]
    }
  ]
}
```

Ao escolher um Personagem (ou o próprio Tema) nessa busca, a `ElencoBlock` faz o *prefill*
client-side de `name`/`figurino_sheet_id` na linha do elenco — sem chamada de rede adicional,
sem mudança em `app/api/agenda_write.py` ou no schema de `EventRole` (research.md §6).
