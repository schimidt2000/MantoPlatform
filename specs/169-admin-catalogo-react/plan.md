# Implementation Plan: Gestão de Catálogo (CRUD de produtos) em React (169)

**Branch**: `169-admin-catalogo-react` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/169-admin-catalogo-react/spec.md`

## Summary

Quinta fatia da US6. Migra as 6 rotas de gestão de produtos do catálogo (`/admin/catalogo*`,
`app/admin/routes.py`) para React + API JSON. Extrai o núcleo (fotos, tags, categorias,
validação) para `app/admin/catalog_ops.py`, reusado pela view Jinja e pelos endpoints novos.

## Technical Context

Igual às fatias 145–168. Sem dependência nova. Verificação com test client Flask contra
`manto_local`, requests fora de `app_context`, multipart para as rotas de foto.

## Constitution Check

- **I**: `_apply_catalog_photos`/`_validate_catalog_photo_extensions`/`_all_catalog_tags`/
  `_normalize_tags`/`_unique_catalog_slug` migram para `catalog_ops.py`, reusadas por Jinja e
  API sem duplicação; `app.catalogo.importer._slugify`/`_rewrite_public_url` continuam sendo a
  fonte única de slug/URL, só chamados a partir do módulo novo.
- **II**: `catalog_ops.py` novo com type hints/docstrings; endpoints em
  `app/api/admin_catalogo_read.py`/`admin_catalogo_write.py`.
- **III**: endpoints novos 100% JSON (multipart para criar/editar); views Jinja continuam em
  paralelo (FR-006).
- **IV**: paridade verificada contra `manto_local` — mesmo conjunto/ordem final de fotos para a
  mesma sequência de ações.
- **V**: loading/erro/sucesso via TanStack Query; confirmação antes de excluir produto; erro de
  validação mantém os dados preenchidos.
- **VII**: não há valor monetário nesta fatia.
- **VIII/IX**: mobile-first e transições padrão.

Sem violação nova.

## Project Structure

```text
app/admin/catalog_ops.py                 # NOVO — núcleo: categoria, criar/editar produto,
                                          #   fotos (validar/aplicar), tags, toggle, excluir
app/api/admin_catalogo_read.py           # NOVO — GET lista/detalhe
app/api/admin_catalogo_write.py          # NOVO — POST categoria/criar/toggle/excluir,
                                          #   PATCH editar (multipart)
app/api/__init__.py                      # + import dos 2 módulos
frontend/apps/internal/src/
├── lib/adminCatalogo.ts                 # NOVO — hooks
├── pages/AdminCatalogoListPage.tsx      # NOVO
└── pages/AdminCatalogoFormPage.tsx      # NOVO — criar/editar (fotos com mover-esquerda/
                                          #   direita, capa, tags, categorias)
App.tsx                                  # + rotas /admin/catalogo, /admin/catalogo/novo,
                                          #   /admin/catalogo/:id/editar
scripts/db/verify_169_admin_catalogo_react.py  # NOVO
```

**Structure Decision**: núcleo extraído para `app/admin/catalog_ops.py` — mesmo padrão das
fatias 154/162/165/167. Reordenação de fotos no React usa botões mover-esquerda/direita (ver
Assumptions do spec), não drag-and-drop.

## Design Decisions

1. **`app/admin/catalog_ops.py`**: `create_or_reuse_category(name)`, `create_product(name,
   description, tags_raw, category_ids, files, form)`, `update_product(item, name, description,
   tags_raw, category_ids, files, form)`, `toggle_active(item)`, `delete_product(item)`,
   `all_tags()`. Fotos: `validate_photo_extensions(files)` levanta `CatalogValidationError`;
   `apply_photos(item, form, files)` aplica remoção/reordenação/upload/capa (mesma lógica de
   `_apply_catalog_photos` hoje).
2. **`GET /api/admin/catalogo`**: querystring `q`/`categoria`/`status` → `{"items": [...],
   "categories": [...]}`.
3. **`GET /api/admin/catalogo/<id>`**: produto completo (fotos, tags, categorias) para o form de
   edição.
4. **`POST /api/admin/catalogo/categorias`**: `{"name"}` → `{"id","name"}` (multipart não
   necessário, é JSON puro).
5. **`POST /api/admin/catalogo`** (multipart): cria produto. 400 com `fields` em validação.
6. **`PATCH /api/admin/catalogo/<id>`** (multipart): edita produto — mesmo corpo de campos de
   criação + `remove_photo_ids[]`/`photo_order`/`cover_photo_id`/`new_photo_cover_index`.
7. **`POST /api/admin/catalogo/<id>/toggle-ativo`**: sem corpo → produto atualizado.
8. **`DELETE /api/admin/catalogo/<id>`**: 204, remove arquivos de foto do armazenamento.
9. **Frontend**: `AdminCatalogoFormPage` reusa o mesmo componente para criar/editar (item
   opcional); grade de fotos com miniatura, botão remover, botões mover-esquerda/direita, rádio
   de capa; upload múltiplo de fotos novas.

## Complexity Tracking

Nenhuma violação nova.
