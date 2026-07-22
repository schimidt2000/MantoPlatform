# Data Model: Gestão de Catálogo (169)

Nenhuma tabela/campo novo.

| Entidade           | Uso                                                                  |
|--------------------|-------------------------------------------------------------------------|
| `CatalogItem`      | produto — nome, slug, descrição, tags (JSON), status, categorias, fotos |
| `CatalogItemImage` | foto do produto — url, posição (0 = capa)                            |
| `CatalogCategory`  | categoria — nome, slug                                                |

## Valores computados (movidos para `catalog_ops.py`, sem duplicar regra)

- `create_or_reuse_category(name)` — slug via `_slugify`; reaproveita categoria existente.
- `all_tags()` — todas as tags distintas já usadas (dedupe por slug, mantém primeira grafia).
- `validate_photo_extensions(files)` — recusa extensão fora de JPG/PNG/WebP antes de processar
  qualquer coisa.
- `apply_photos(item, form, files)` — ordem de aplicação: (1) remove fotos marcadas, (2) aplica
  `photo_order` manual nas restantes, (3) adiciona fotos novas (posição sequencial), (4) resolve
  capa (explícita → primeira nova → primeira restante) e recoloca em posição 0.
- `_normalize_tags(raw_tags, known_tags)` — reaproveita grafia já existente (case/acento-
  insensitive).
- `CatalogValidationError(field, message)` — exceção nova; Jinja vira `flash`, API vira 400.
