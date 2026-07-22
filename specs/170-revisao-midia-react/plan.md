# Implementation Plan: Revisão de Mídia em React (170)

**Branch**: `170-revisao-midia-react` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/170-revisao-midia-react/spec.md`

## Summary

Fatia final da US6 e da migração 144. Migra as 14 rotas de `app/revisao/routes.py` para
React + API JSON. Extrai o núcleo (upload/validação de arquivo, snapshot de versão, limpeza de
armazenamento) para `app/revisao/review_ops.py`; os 4 endpoints de comentário (já JSON hoje)
migram de contrato/local sem mudar de forma. Ao final desta fatia, 100% das rotas do sistema
têm endpoint JSON equivalente (SC-002 da spec 144) — a migração fica completa.

## Technical Context

Igual às fatias 145–169. Sem dependência nova. Verificação com test client Flask contra
`manto_local`, requests fora de `app_context`, multipart para upload/substituição.

## Constitution Check

- **I**: `_save_assets`/`_snapshot_current_version`/`_delete_version_files`/`_detect_media_type`/
  `_file_size` migram para `review_ops.py`, reusadas por Jinja e API; `_comment_json` também
  migra (serializador único). `_can_view`/`_can_manage`/`_can_resolve`/`_can_delete_comment`
  reimplementadas como funções puras no módulo novo, chamadas pelos dois lados.
- **II**: `review_ops.py` novo com type hints/docstrings; endpoints em
  `app/api/revisao_read.py`/`revisao_write.py`.
- **III**: endpoints novos 100% JSON; views Jinja continuam em paralelo (FR-006). Os 4
  comentários (já JSON) passam a viver em `/api/revisao/*` — a versão antiga em `/revisao/*`
  continua funcionando via alias fino que chama o mesmo `review_ops`.
- **IV**: paridade verificada contra `manto_local`.
- **V**: loading/erro/sucesso via TanStack Query; confirmação antes de excluir espaço/material/
  comentário.
- **VIII**: revisão é usada por Marketing (não é superfície pública/mobile-first
  obrigatório pela constituição, mas segue mobile-first por princípio geral de UI).

Sem violação nova.

## Project Structure

```text
app/revisao/review_ops.py               # NOVO — núcleo: espaços, materiais, versões,
                                         #   comentários, permissões
app/api/revisao_read.py                 # NOVO — GET espaços/detalhe/material/comentários
app/api/revisao_write.py                # NOVO — POST/DELETE espaço/material/comentário
app/api/__init__.py                     # + import dos 2 módulos
frontend/apps/internal/src/
├── lib/revisao.ts                      # NOVO — hooks
├── pages/RevisaoListPage.tsx           # NOVO
├── pages/RevisaoSpaceCreatePage.tsx    # NOVO
├── pages/RevisaoSpacePage.tsx          # NOVO — detalhe do espaço (materiais, revisores)
└── pages/RevisaoAssetPage.tsx          # NOVO — visualizador + comentários
App.tsx                                 # + rotas /revisao, /revisao/novo, /revisao/:id,
                                         #   /revisao/:spaceId/asset/:assetId
scripts/db/verify_170_revisao_midia_react.py  # NOVO
```

**Structure Decision**: núcleo extraído para `app/revisao/review_ops.py` — mesmo padrão das
fatias 154/162/165/167/169. Visualizador React usa players HTML5 nativos + lista de
comentários (ver Assumptions do spec) — sem timeline de anotação visual.

## Design Decisions

1. **`app/revisao/review_ops.py`**: `can_create()`, `can_view(space, user)`,
   `can_manage(space, user)`, `can_resolve(comment, user)`, `can_delete_comment(comment, user)`,
   `detect_media_type(filename)`, `save_assets(space, files, uploader_id)`,
   `snapshot_current_version(asset)`, `delete_version_files(asset)`, `create_space(title,
   description, creator_id, reviewer_ids, files)`, `update_reviewers(space, reviewer_ids)`,
   `delete_space(space)`, `delete_asset(asset)`, `replace_asset(asset, file, uploader_id)`,
   `finalize_asset(asset)`, `comment_to_dict(comment, user)`, `add_comment(asset, user, body,
   timecode, page, pos_x, pos_y)`, `resolve_comment(comment, user)`,
   `delete_comment_row(comment)`. Erros de validação levantam `ReviewValidationError(field,
   message)`.
2. **Endpoints de espaço**: `GET /api/revisao`, `POST /api/revisao` (multipart), `GET
   /api/revisao/<id>`, `POST /api/revisao/<id>/upload` (multipart), `PATCH
   /api/revisao/<id>/reviewers`, `DELETE /api/revisao/<id>`.
3. **Endpoints de material**: `GET /api/revisao/<space_id>/asset/<asset_id>?v=`, `DELETE
   /api/revisao/asset/<asset_id>`, `POST /api/revisao/asset/<asset_id>/replace` (multipart),
   `POST /api/revisao/asset/<asset_id>/finalize`.
4. **Endpoints de comentário**: `GET /api/revisao/asset/<asset_id>/comments?v=`, `POST
   /api/revisao/asset/<asset_id>/comment`, `POST /api/revisao/comment/<id>/resolve`, `DELETE
   /api/revisao/comment/<id>`.
5. **Frontend — visualizador (`RevisaoAssetPage`)**: player nativo por tipo de mídia; barra de
   ancoragem simplificada — para vídeo/áudio, captura o `currentTime` do player no momento do
   envio do comentário; para PDF, campo numérico de página; para imagem, clique na própria
   `<img>` calcula `pos_x`/`pos_y` relativos ao tamanho renderizado. Lista de comentários com
   botão "ir para o ponto" (seek do player / abrir página) por item.

## Complexity Tracking

Nenhuma violação nova — simplificação da timeline de anotação registrada como Assumption
explícita no spec (170), não uma omissão silenciosa.
