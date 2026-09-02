# Tarefas — Feature 270

- [x] T01 `og_ops.py`: `Receita`, `RECEITA_OG` (chave "1"), `receita_variante`, `LARGURAS_PERMITIDAS`, `_redimensionar` por largura, `pastas_da_variante`, `resolve_variante`, `variante_em_cache`; API antiga (`resolve_thumbnail`) intacta
- [x] T02 `catalogo/routes.py`: `GET /catalogo/midia/t/<int:largura>/<filename>` antes de `midia`, 404 sem gravar, `immutable`
- [x] T03 `app/__init__.py`: `GET /uploads/t/<int:largura>/<path:filename>` (login, só `talent_photos`), `Cache-Control: private … immutable` só para `talent_photos` em `uploaded_file`, `_subpasta_do_upload`
- [x] T04 `app/cli.py`: `flask warm-thumbnails` idempotente com relatório
- [x] T05 `@manto/api-client`: `assetUrl(path, { largura })`, `assetSrcSet`, tipos exportados
- [x] T06 `ProductGallery` (tira 128), `ProductCard` (srcset 320/480/640 + sizes por uso, coluna real no mobile), `CharacterCard`, `TalentMosaic`
- [x] T07 `verify_270.py` 10/10 contra `manto_local` (o cenário 6 achou e provou o `.tmp` por PID do motor — corrigido com `mkstemp`)
- [x] T08 `npm run typecheck` limpo nos três apps; `ruff` no baseline
- [x] T09 Conferência na tela da vitrine (fotos públicas baixadas de produção para o disco local): tira pede 128 (9 miniaturas, ~9 KB cada vs ~173 KB do original); grade a 375px/DPR 2 pede 320 nos 457 cards (com `50vw` pedia 640 — daí o `calc(50vw - 32px)` e o 480); desktop 1280px/DPR 1.5 pede 480 (39–75 KB). **Grade do Banco de Talentos não conferida em tela**: o disco local não tem nenhuma das 258 fotos de rosto e `/uploads` exige login em produção — coberta pelos cenários 7 e 8 do verify (rota, largura, `private`, documento sem variante); conferir em produção depois do deploy.
- [x] T10 `docs/01`, `docs/02`, `docs/03` (entrada 270 no topo)
- [ ] T11 Pós-deploy: `flask warm-thumbnails` no backend do Render, e abrir `/talents` em produção com a aba de rede para fechar o T09
