# Tasks — Melhorias na criação de produtos do catálogo (141)

- [X] T001 [US2] `app/admin/routes.py`: `_ALLOWED_CATALOG_PHOTO_EXTENSIONS` +
      `_validate_catalog_photo_extensions` — recusa arquivos fora de
      `.jpg/.jpeg/.png/.webp` antes de qualquer processamento, levantando
      `InvalidCatalogPhotoError`
- [X] T002 [US2] `app/admin/routes.py` (`catalogo_admin_new`/`catalogo_admin_edit`):
      capturam `InvalidCatalogPhotoError`, mostram mensagem clara e re-renderizam
      preservando os campos — validado ANTES de criar/commitar qualquer coisa
- [X] T003 [US1] `app/admin/routes.py` (`_apply_catalog_photos`): lê
      `new_photo_cover_index`; usa `new_images[índice]` como capa quando não há foto
      existente marcada; mantém FR-002 (1ª foto nova = padrão)
- [X] T004 [US1] `app/templates/admin_catalogo_form.html`: prévia client-side
      (`URL.createObjectURL`) das fotos recém-selecionadas, com rádio "Capa" por card;
      escolher uma foto nova como capa desmarca a seleção de foto existente (e
      vice-versa, já que os rádios existentes continuam funcionando como antes)
- [X] T005 [US3] `app/templates/admin_catalogo_list.html`: removido o link "Importar do
      WordPress" de `page_actions`
- [X] T006 [US3] `app/templates/admin_importar_catalogo.html`: removido o link recíproco
      "Gerenciar catálogo" — página e rota continuam existindo, só sem porta de entrada
- [X] T007 Verificação funcional vs `manto_local`: capa escolhida explicitamente
      (identificada por cor do pixel, já que `save_file` sempre renomeia pra UUID) fica
      em `position=0`; sem escolha, 1ª foto continua sendo a capa (sem regressão);
      arquivo `.pdf` é recusado com mensagem clara, nada é criado; foto grande
      (4032×3024, ~190KB sintético) enviada via `save_file` resulta em arquivo ~6.7KB e
      redimensionado para 1200×900 (compressão confirmada); `/admin/catalogo` não tem
      mais link para `/admin/importar-catalogo`. Todos os cenários passaram
      (`scripts/db/verify_141_catalogo_form.py`). Smoke test adicional confirmou que
      `/admin/catalogo/novo`, `/admin/catalogo`, `/admin/catalogo/<id>/editar` e
      `/admin/importar-catalogo` (ainda acessível por URL direta) renderizam sem erro.
- [X] T008 `ruff check` nos arquivos tocados (mesma contagem do baseline, 7
      pré-existentes em `admin/routes.py`, nenhum novo); changelog
      (`docs/changelog.html`, republicado no link já existente); pointer do plano em
      `CLAUDE.md`; commit, merge em `main`, push
