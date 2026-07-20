# Tasks — Catálogo: tags/categorias criáveis, navegação por categoria, relacionados e lista de desejos (140)

- [X] T001 [US2] `app/admin/routes.py`: `POST /admin/catalogo/categorias`
      (`@require_superadmin`, JSON) — get-or-create por `slug=_slugify(name)`, retorna
      `{"id", "name"}`
- [X] T002 [US1] `app/admin/routes.py`: helper `_all_catalog_tags() -> list[str]` (tags
      distintas de todos os `CatalogItem.tags`, dedupe por `_slugify`, mantém primeira
      grafia); `catalogo_admin_new`/`catalogo_admin_edit` passam `all_tags` ao template
- [X] T003 [US1] `app/admin/routes.py`: normalização de tags ao salvar (`_normalize_tags`)
      — cada tag enviada é comparada contra `all_tags` via `_slugify`; se bater, usa a
      grafia já existente (FR-003). Achado na verificação: o catálogo real (importado do
      WordPress) já tem ~2100 tags distintas, muitas em minúsculo (ex.: "natal", "show")
      — normalização funciona corretamente reaproveitando essas grafias já existentes.
- [X] T004 [US1] `app/templates/admin_catalogo_form.html`: campo de tags vira seletor de
      chips com autocomplete + criação inline ("Criar tag '...'" quando não há
      correspondência) — hidden `tags` (join por vírgula) preenchido antes do submit,
      contrato do backend inalterado
- [X] T005 [US2] `app/templates/admin_catalogo_form.html`: "+ nova categoria" inline
      (texto + botão) ao lado dos checkboxes, chama T001 via `fetch`, adiciona checkbox
      novo já marcado sem reload
- [X] T006 [US2] `app/templates/admin_catalogo_list.html`: "+ nova categoria" inline no
      filtro, mesmo endpoint de T001, adiciona opção ao `<select>` sem reload
- [X] T007 [US3] `app/catalogo/routes.py`: `GET /categorias` — categorias com produto
      ativo (contagem > 0), cada uma com foto representativa
- [X] T008 [US3] `app/catalogo/routes.py`: `GET /categoria/<slug>` — 404 se categoria
      inexistente ou sem produto ativo; senão, produtos ativos daquela categoria
- [X] T009 [US3] `app/templates/catalogo/categorias.html` e `categoria_detail.html`
      (novos) — mesma paleta/tipografia de `_head_shared.html`; grid de fotos maiores em
      `categoria_detail.html` (`.cat-grid-lg`)
- [X] T010 [US3] Link para `/catalogo/categorias` em `index.html`
- [X] T011 [US4] `app/catalogo/routes.py` (`detail()`): `related` — até 6 produtos ativos
      compartilhando categoria com o item, excluindo o próprio
- [X] T012 [US4] `app/templates/catalogo/detail.html`: seção "Você também pode gostar"
      abaixo de `.cat-detail-grid`; só renderiza se `related` não vazio
- [X] T013 [US5] `app/static/js/catalogo-wishlist.js` (novo): API sobre `localStorage`
      (chave `manto_catalogo_wishlist`) — add/remove/toggle sem duplicar, contagem,
      mensagem e URL de WhatsApp
- [X] T014 [US5] `app/templates/catalogo/_wishlist_widget.html` (novo parcial): botão
      flutuante com contador + botão "♡ Adicionar" em cada card, incluído em
      `index.html`, `detail.html`, `categorias.html`, `categoria_detail.html`
- [X] T015 [US5] `app/catalogo/routes.py`: `GET /lista-desejos` — injeta o número de
      WhatsApp (`_whatsapp_target()`/`DEFAULT_WHATSAPP_NUMBER`, importado de
      `app.formularios.routes`)
- [X] T016 [US5] `app/templates/catalogo/lista_desejos.html` (novo): renderiza a lista via
      JS a partir do `localStorage`; botão "Enviar para o vendedor" desabilitado com lista
      vazia; abre `https://api.whatsapp.com/send?phone=...&text=...`
- [X] T017 Verificação funcional vs `manto_local`: bloqueio 403 para não-superadmin ao
      criar categoria; get-or-create de categoria (nome equivalente não duplica); tag nova
      preservada como digitada; tag equivalente (case) reaproveita grafia já usada;
      `/catalogo/categorias` e `/catalogo/categoria/<slug>` (incl. 404); relacionados
      aparecem com categoria compartilhada; `/catalogo/lista-desejos` injeta o número
      certo; `/catalogo/` e `/catalogo/<slug>` sem regressão. Todos os cenários passaram
      (`scripts/db/verify_140_catalogo_descoberta.py`). GET de smoke test adicional
      confirmou `/admin/catalogo/novo`, `/admin/catalogo`, `/admin/catalogo/<id>/editar` e
      `/catalogo/categorias` renderizando sem erro.
- [X] T018 Verificação do `catalogo-wishlist.js`: `node --check` (sintaxe OK, incluindo os
      trechos inline de `admin_catalogo_form.html`, `admin_catalogo_list.html`,
      `_wishlist_widget.html`, `lista_desejos.html`, `index.html`, `detail.html`) +
      simulação com stub de `localStorage` cobrindo os 10 cenários do plano (add sem
      duplicar, toggle, remove, contagem, mensagem e URL de WhatsApp, lista vazia) — todos
      passaram.
- [X] T019 `ruff check` nos arquivos tocados (mesma contagem do baseline, 7 pré-existentes
      em `admin/routes.py`, nenhum novo); changelog (`docs/changelog.html`, republicado no
      link já existente); pointer do plano em `CLAUDE.md`; commit, merge em `main`, push
