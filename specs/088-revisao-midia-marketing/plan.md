# Implementation Plan: Espaço de Revisão de Mídia (088)

**Branch**: `088-revisao-midia-marketing` | **Date**: 2026-06-25 | **Spec**: [spec.md](spec.md)

## Summary

Novo módulo `revisao` (blueprint `/revisao`): espaços de revisão com multi-upload de mídia (vídeo/áudio/
imagem/PDF) no volume, seleção de revisores, e **comentários ancorados** (time code em vídeo/áudio, pin
x/y em imagem, página em PDF) com resolver/excluir. Novo papel **MARKETING**. Migração manual (4 tabelas).

## Technical Context

**Models** (`app/models.py`):
- `ReviewSpace`: id, title, description, created_by(FK users), created_at; rel. assets/reviewers (cascade).
- `ReviewAsset`: id, space_id(FK), file_path, original_name, media_type('video'|'audio'|'image'|'pdf'),
  position, created_at; rel. comments (cascade).
- `ReviewReviewer`: id, space_id(FK), user_id(FK), unique(space_id,user_id).
- `ReviewComment`: id, asset_id(FK), user_id(FK), body(Text), timecode(Float, s), page(Int), pos_x(Float),
  pos_y(Float), resolved(Bool), created_at.

**Migration**: manual, `down_revision='w9f0a1b2c3d4'` → cria as 4 tabelas (índices em space_id/asset_id).

**Papel MARKETING**: `app/constants.py` (RoleName.MARKETING) + `seed.py` (get_or_create_role).

**Blueprint** `app/revisao/routes.py` (`revisao_bp`, url_prefix `/revisao`):
- `GET /` lista espaços visíveis (criados por mim, ou onde sou revisor, ou superadmin).
- `GET/POST /novo` criar (MARKETING/SUPERADMIN): título, descrição, arquivos[], revisores[].
- `GET /<sid>` detalhe (grade de materiais + gestão de revisores/exclusão).
- `POST /<sid>/upload` adicionar arquivos; `POST /<sid>/reviewers`; `POST /<sid>/delete`.
- `GET /<sid>/asset/<aid>` visualizador.
- `POST /asset/<aid>/delete`; `POST /asset/<aid>/comment` (form/JSON); `GET /asset/<aid>/comments` (JSON).
- `POST /comment/<cid>/resolve` (toggle); `POST /comment/<cid>/delete`.
- Helpers: `_can_view(space,user)`, `_can_manage(space,user)`, `_detect_media_type(ext)`.

**Storage**: `save_file(file, "review")` (volume). `MAX_CONTENT_LENGTH` elevado para 512 MB em
`app/config.py`. Cap por arquivo 512 MB + extensões permitidas por tipo. Servir via rota `/uploads/...`
existente (`send_from_directory` suporta Range → seek de vídeo).

**Templates** (`app/templates/revisao/`): `list.html`, `new.html`, `space.html`, `asset.html`.
`asset.html` traz o player + painel de comentários e o JS:
- vídeo/áudio: captura `currentTime` ao comentar; clicar comentário faz `seek`; barra de marcadores.
- imagem: clique → pin x/y(%); comentários mostram pins.
- pdf: `<iframe>` + campo de página no comentário.
- comentários via `fetch` (add/list/resolve/delete) re-renderizando a lista.

**Nav**: item "Revisão" na sidebar (`base.html`) para autenticados.

## Constitution Check

- **I. Qualidade**: helpers com type hints; rotas finas; lógica de acesso isolada.
- **II. Migration manual** (autogenerate quebrado): nova revisão escrita à mão.
- **IV. Não quebrar**: módulo isolado; só adiciona blueprint, role, nav, e eleva MAX_CONTENT_LENGTH.

**Resultado**: PASS (com migração manual de 4 tabelas).

## Testing

Contra **`manto_local`**: aplicar migração; criar espaço com upload (imagem/áudio/pdf de teste), definir
revisor; controle de acesso (não-revisor bloqueado, revisor entra); adicionar comentário com time code/
página/pin; resolver e excluir; excluir asset/espaço cascateia. `ruff` sem erros novos. Limpar dados.

## Project Structure

```text
app/models.py                       — 4 modelos novos
migrations/versions/xxxx_review.py   — cria as tabelas
app/constants.py, seed.py            — papel MARKETING
app/revisao/__init__.py, routes.py   — blueprint
app/templates/revisao/*.html         — 4 templates
app/__init__.py                      — registra blueprint
app/config.py                        — MAX_CONTENT_LENGTH 512MB
app/templates/base.html              — item de menu
```

## Complexity Tracking

> Maior risco: tamanho de vídeo vs. volume (5 GB) e teto de requisição — mitigado por cap por arquivo +
> volume redimensionável. JS do visualizador é a parte mais densa; mantido pragmático.
