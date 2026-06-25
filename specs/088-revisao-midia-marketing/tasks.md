# Tasks: Espaço de Revisão de Mídia (088)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local`.

## Phase 1: Setup / Dados

- [X] T001 Adicionar 4 modelos (`ReviewSpace`, `ReviewAsset`, `ReviewReviewer`, `ReviewComment`) em
  `app/models.py` com relacionamentos + cascade.
- [X] T002 Migração manual `down_revision='w9f0a1b2c3d4'` criando as 4 tabelas (índices em space_id/asset_id).
- [X] T003 Papel `MARKETING` em `app/constants.py` e `seed.py`.
- [X] T004 `MAX_CONTENT_LENGTH = 512MB` em `app/config.py`; subpasta `review` para uploads.

## Phase 2: US1 — Criar espaço + multi-upload + revisores (P1) 🎯 MVP

- [X] T005 [US1] Blueprint `app/revisao/__init__.py` + `routes.py` (`revisao_bp`) com helpers de acesso e
  `_detect_media_type`; registrar em `app/__init__.py`.
- [X] T006 [US1] Rotas `GET /` (lista), `GET/POST /novo` (criar com arquivos[] + revisores[]),
  `GET /<sid>` (detalhe), `POST /<sid>/upload`, `POST /<sid>/reviewers`, `POST /<sid>/delete`.
- [X] T007 [US1] Templates `revisao/list.html`, `revisao/new.html`, `revisao/space.html` + item de menu
  "Revisão" em `base.html`.

## Phase 3: US2 — Comentário com time code em vídeo/áudio (P1) 🎯 MVP

- [X] T008 [US2] Rotas de comentário: `GET /asset/<aid>/comments` (JSON), `POST /asset/<aid>/comment`,
  `POST /comment/<cid>/resolve`, `POST /comment/<cid>/delete`, `GET /<sid>/asset/<aid>` (visualizador),
  `POST /asset/<aid>/delete`.
- [X] T009 [US2] `revisao/asset.html`: player de vídeo/áudio + painel de comentários; JS captura/seek de
  time code, barra de marcadores, add/list/resolve/delete via fetch.

## Phase 4: US3 — Imagem (pin) e PDF (página) (P2)

- [X] T010 [US3] No `asset.html`: imagem com pin x/y(%) ao clicar; PDF em iframe + campo de página no
  comentário; renderização de pins e página nos comentários.

## Phase 5: Verificação

- [X] T011 Verificar contra `manto_local`: migração aplica; criar espaço + upload; acesso (revisor entra,
  outro bloqueado); comentar com time code/página/pin; resolver/excluir; cascade ao excluir asset/espaço.
  `ruff` sem erros novos. Limpar dados de teste.

## Dependencies

- T001→T002→(resto). T005→T006→T007 (US1). T008→T009 (US2). T010 depende de T009. T011 por último.

## MVP

US1 + US2 (criar/subir/revisores + comentário com time code em vídeo/áudio). US3 (imagem/PDF) na sequência.
