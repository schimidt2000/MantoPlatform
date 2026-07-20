# Tasks — Galeria de fotos do produto e reordenação na gestão (142)

- [X] T001 [US1] `app/templates/catalogo/detail.html`: remove `aspect-ratio: 4/5` fixo de
      `.cat-gallery-main`; adiciona `max-height: 70vh`; `object-fit` de `cover` para
      `contain`
- [X] T002 [US1] `app/templates/catalogo/detail.html`: `.cat-gallery-thumbs` de
      `display:grid` (quebra linha) para faixa horizontal rolável (`display:flex;
      overflow-x:auto; scroll-snap-type:x proximity`)
- [X] T003 [US1][US2] `app/templates/catalogo/detail.html`: função única `goToPhoto(index)`
      — troca `main.src`, ajusta `aspect-ratio` da moldura via `naturalWidth`/
      `naturalHeight` no `load`, atualiza classe `active`, rola a miniatura ativa
      (`scrollIntoView`); clique na miniatura passa a chamar essa função
- [X] T004 [US2] `app/templates/catalogo/detail.html`: Pointer Events em
      `.cat-gallery-main` detectando arrasto horizontal (limiar 40px, direção
      predominante) chamando `goToPhoto(atual ± 1)`, travado nos limites
- [X] T005 [US3] `app/catalogo/routes.py` (`detail()`): `primary_category` (1ª categoria
      do item)
- [X] T006 [US3] `app/templates/catalogo/detail.html`: substitui "Ver mais personagens"
      por "Ver mais em {{ primary_category.name }}"; some sem categoria
- [X] T007 [US4] `app/templates/admin_catalogo_form.html`: cards de `#existing-photos`
      ganham `draggable="true"` + `data-photo-id`; drag-and-drop reordena os nós DOM;
      hidden `photo_order` preenchido no `submit`
- [X] T008 [US4] `app/admin/routes.py` (`_apply_catalog_photos`): lê `photo_order` e
      reordena `remaining` antes da regra de capa (que continua garantindo `position=0`
      pra foto marcada, por cima da ordem manual — FR-007)
- [X] T009 Verificação funcional vs `manto_local`: produto com categoria mostra "Ver mais
      em <categoria>" com link correto e sem o texto antigo; produto sem categoria não
      mostra o botão; reordenar fotos existentes (cores distintas por posição) persiste a
      nova ordem; reordenar + capa explícita ao mesmo tempo — capa fica em `position=0`,
      resto segue a ordem manual invertida. Todos os cenários passaram
      (`scripts/db/verify_142_galeria_produto.py`). Smoke test confirmou
      `/catalogo/<slug>`, `/admin/catalogo/<id>/editar` e `/admin/catalogo/novo`
      renderizando sem erro.
- [X] T010 Verificação do JS: `node --check` em `detail.html` e `admin_catalogo_form.html`
      (sintaxe OK) + simulação isolada da lógica de decisão do swipe (mesma regra do
      código real: limiar 40px + direção predominante + clamp nos limites) — 6 cenários,
      todos passaram (swipe esquerda/direita, limites, arrasto pequeno ignorado, arrasto
      vertical não interfere no scroll).
- [X] T011 `ruff check` nos arquivos tocados (mesma contagem do baseline, 7 pré-existentes
      em `admin/routes.py`, nenhum novo); changelog (`docs/changelog.html`, republicado
      no link já existente); pointer do plano em `CLAUDE.md`; commit, merge em `main`,
      push
