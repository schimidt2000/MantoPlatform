# Contrato de API: Gerenciador de Catálogo UX (feature 186)

Convenções herdadas de `specs/144-migracao-react-spa/contracts/api-conventions.md` e
`specs/185-catalogo-vitrine-completo/contracts/api-catalogo.md`.

## Estendido — `GET /api/catalogo/elenco-busca` (`app/api/catalogo_read.py`)

Gate ampliado: `COMERCIAL` **ou** `FIGURINO` **ou** `SUPERADMIN` (era só `COMERCIAL`/`SUPERADMIN`).

```jsonc
{
  "temas": [
    {
      "id": 1, "name": "...", "slug": "...",
      "characters": [
        { "id": 10, "name": "Gatuno", "figurino_sheet_id": 42, "photo_url": "/catalogo/midia/..." } // novo campo
      ]
    }
  ]
}
```

## Estendido — `GET /api/admin/catalogo` (`app/api/admin_catalogo_read.py`)

```jsonc
{
  "items": [
    {
      "id": 1, "name": "...", "slug": "...", "is_active": true, "cover_url": "...",
      "category_names": [...],
      "characters": [                                            // novo
        { "id": 10, "name": "Gatuno", "photo_url": "...", "figurino_sheet_id": 42, "is_active": true }
      ]
    }
  ],
  "categories": [...]
}
```

## Novo — `POST /api/admin/catalogo/personagens/mover-em-massa`

Gate: `require_superadmin` (mesmo padrão do resto do CRUD de catálogo).

Body:

```jsonc
{ "character_ids": [10, 11, 23], "target_item_id": 5 }
```

- 200 → `{ "moved": 3 }`.
- 400 → `character_ids` vazio, ou algum id não existe → `CatalogValidationError`.
- 404 → `target_item_id` não encontrado ou inativo.

## Sem endpoint novo (reaproveitados)

- **Vincular a partir da Ficha**: `PATCH /api/admin/catalogo/personagens/<id>` já existente
  (feature 185), só com `figurino_sheet_id` no body.
- **Inativar/excluir em massa**: `POST .../toggle-ativo` e `DELETE /api/admin/catalogo/<id>` /
  `DELETE /api/admin/catalogo/personagens/<id>` já existentes, chamados em sequência pelo
  frontend.
