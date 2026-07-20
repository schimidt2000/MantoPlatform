# Tasks — Animação suave na galeria de fotos do produto (143)

- [X] T001 [US1] `app/templates/catalogo/detail.html` (CSS): `.cat-gallery-main` ganha
      `transition: height .32s ease`; `.cat-gallery-main img` ganha
      `transition: opacity .18s ease, transform .22s ease`; media query
      `@media (prefers-reduced-motion: reduce)` zera essas transições
- [X] T002 [US1] `app/templates/catalogo/detail.html` (JS): `applySize(img, animate)`
      substitui `applyRatio` — calcula `height` em px (`wrap.clientWidth ×
      naturalHeight/naturalWidth`, limitado a `innerHeight * 0.7`) e aplica em
      `wrap.style.height`; primeira aplicação (carregamento inicial) sem transição
- [X] T003 [US1] `app/templates/catalogo/detail.html` (JS): `goToPhoto()` reescrito com
      cross-fade (`opacity` para 0, troca `src` após ~180ms — ou instantâneo se
      `prefers-reduced-motion` — aplica nova altura, volta `opacity` para 1); token
      `pending` garante que só a chamada mais recente aplica o resultado (FR-005)
- [X] T004 [US1] `app/templates/catalogo/detail.html` (JS): swipe ganha feedback ao vivo
      — `pointermove` translada a imagem (`transform: translateX`) acompanhando o
      ponteiro com leve queda de opacidade proporcional à distância; `pointerup` conclui
      a troca (cruzou o limiar de 40px, mesma regra da feature 142) ou volta suavemente
      ao lugar (não cruzou)
- [X] T005 Verificação: `node --check` no JS extraído (sintaxe OK) + simulação isolada —
      cálculo de altura a partir de largura×proporção com teto de `innerHeight*0.7`
      (incluindo o caso de foto muito alta sendo limitada), decisão de limiar/direção do
      swipe (mesmos casos da feature 142, sem regressão), token de "chamada mais recente
      vence" com resolução fora de ordem — todos os 8 cenários passaram. Smoke test HTTP
      confirmou `/catalogo/<slug>` respondendo 200 com todos os elementos da galeria
      presentes (`galleryWrap`, `galleryMain`, miniaturas, media query de reduced-motion).
- [X] T006 Nenhum arquivo Python tocado (mudança 100% em `detail.html`) — `ruff check`
      não se aplica; changelog (`docs/changelog.html`, republicado no link já existente,
      mencionando a atualização da constituição); pointer do plano em `CLAUDE.md`;
      commit (incluindo `.specify/memory/constitution.md` v1.6.0), merge em `main`, push
