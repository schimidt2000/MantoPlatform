# Implementation Plan: Galeria de fotos do produto e reordenação na gestão

**Branch**: `142-galeria-produto-catalogo` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/142-galeria-produto-catalogo/spec.md`

## Summary

Quatro ajustes sobre a galeria de fotos do catálogo, dois na página pública do produto
(`app/templates/catalogo/detail.html`) e dois na gestão (`admin_catalogo_form.html`,
`app/admin/routes.py`):

1. **Proporção dinâmica por foto**: a moldura da foto principal (`.cat-gallery-main`) hoje
   tem `aspect-ratio: 4/5` fixo — passa a se ajustar à proporção real de cada foto
   (lida via `naturalWidth`/`naturalHeight` no `load` da imagem) conforme a navegação
   acontece, com um teto de altura pra não quebrar o layout em fotos muito altas/largas.
   A barra de miniaturas passa de grade que quebra linha para uma faixa horizontal que
   rola sozinha até manter a miniatura ativa visível.
2. **Swipe**: Pointer Events (unificado touch+mouse) na foto principal, um único ponto de
   navegação (`goToPhoto(index)`) reaproveitado tanto pelo clique na miniatura quanto pelo
   arrasto.
3. **Botão "Ver mais em <categoria>"**: substitui o link redundante "Ver mais
   personagens" — leva à página da primeira categoria do produto (feature 140); some
   quando o produto não tem categoria.
4. **Reordenar fotos na gestão**: arrastar-e-soltar (HTML5 Drag and Drop API) nos cards de
   fotos já salvas do formulário de produto (feature 139/141); a ordem final vira um campo
   oculto lido no salvar, aplicado ANTES da regra de capa (que sempre garante a foto
   marcada em primeiro, como já funciona hoje).

## Technical Context

**Language/Version**: Python 3.11, Flask + Jinja2; JavaScript vanilla (sem framework,
sem biblioteca de swipe/drag externa — usa Pointer Events e a Drag and Drop API nativas
do navegador)

**Primary Dependencies**: nenhuma nova. Reaproveita a infraestrutura de galeria já
existente (`detail.html`), o padrão de cards de foto já usado no formulário admin
(feature 139/141), e a página de categoria já entregue na feature 140

**Storage**: PostgreSQL — nenhuma migration nova; reordenação usa o campo `position` que
`CatalogItemImage` já tem

**Testing**: script de verificação funcional com Flask test client contra `manto_local`
para a parte server-side (categoria do produto no botão, persistência da nova ordem ao
salvar); `node --check` + simulação para a lógica de navegação/swipe/drag extraída do
JS, já que não há navegador automatizado no projeto

**Target Platform**: página pública do catálogo (sem login, mobile-first) + área
administrativa autenticada

**Project Type**: web application (monolito Flask existente)

**Performance Goals**: N/A — mudanças são CSS/JS client-side e uma leitura de lista já
existente (`item.categories`); sem impacto de performance perceptível

**Constraints**: a página pública continua sem dependências externas (mesma regra das
features 133/139/140 — nada de bibliotecas JS de terceiros); swipe não pode interferir
com o scroll vertical normal da página (só reage a arrasto predominantemente horizontal)

**Scale/Scope**: `app/templates/catalogo/detail.html`, `app/catalogo/routes.py`
(`detail()`), `app/templates/admin_catalogo_form.html`, `app/admin/routes.py`
(`_apply_catalog_photos`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: nenhuma biblioteca nova — Pointer Events e a Drag and
  Drop API já são nativas do navegador; a página de categoria já existe (feature 140), só
  é linkada de um lugar novo; o card de foto do formulário admin (feature 139/141) só
  ganha `draggable`, não é reescrito.
- **II. Padrões de código Python**: mudança pequena e localizada em `detail()` e
  `_apply_catalog_photos` (já documentadas, type hints mantidos).
- **III. Arquitetura em camadas**: nenhuma regra de negócio nova — "primeira categoria" e
  "ordem definida pelo admin" são leituras/gravações diretas de campos que já existem.
- **IV. Não quebrar o que funciona**: navegação por clique na miniatura continua
  funcionando (agora unificada com o swipe pela mesma função); a regra de capa (feature
  141) continua tendo prioridade sobre a ordem manual — verificação funcional cobre os
  dois usados juntos (FR-007).
- **V. UI/UX consistente**: usa os mesmos tokens visuais (`--cat-*`, `.cat-btn`) já
  estabelecidos; nenhuma cor/fonte nova.
- **VIII. Superfícies públicas são mobile-first**: swipe e a barra de miniaturas rolável
  são melhorias pensadas primeiro pro uso em celular, coerente com o princípio já adotado
  nas features 133/139/140.

Nenhuma violação. Gate passa sem exceções.

## Project Structure

### Documentation (this feature)

```text
specs/142-galeria-produto-catalogo/
├── plan.md              # This file
├── spec.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

Sem `research.md`/`data-model.md`/`contracts/`: sem incógnita técnica (Pointer Events e
Drag and Drop API são padrões web bem estabelecidos, já usados em outros projetos do
próprio autor do sistema pela convenção "sem biblioteca externa"), sem entidade nova.

### Source Code (repository root)

```text
app/
├── catalogo/
│   └── routes.py            # detail(): + `primary_category` (1ª categoria do item)
├── admin/
│   └── routes.py            # _apply_catalog_photos: lê `photo_order` (ids na ordem
│                             #   definida pelo admin) antes de aplicar a regra de capa
└── templates/
    ├── admin_catalogo_form.html  # cards de fotos existentes ganham `draggable`;
    │                              #   hidden `photo_order` preenchido antes do submit
    └── catalogo/
        └── detail.html            # moldura com aspect-ratio dinâmico; miniaturas em
                                    #   faixa rolável; swipe via Pointer Events; botão
                                    #   "Ver mais em <categoria>"
```

## Design Decisions

### 1. Proporção dinâmica + miniaturas sincronizadas (`detail.html`)

- `.cat-gallery-main` perde o `aspect-ratio: 4/5` fixo do CSS; ganha um `max-height`
  (ex.: `70vh`) pra não deixar fotos muito altas quebrarem o layout (edge case do spec).
  `object-fit` muda de `cover` para `contain` — como a proporção da moldura passa a
  acompanhar a da foto, `contain` garante que nenhuma foto fica cortada mesmo no instante
  entre trocar de foto e o `aspect-ratio` ser recalculado.
- Função única `goToPhoto(index)`: atualiza `main.src`; no evento `load` da imagem
  (ou imediatamente se já em cache — `img.complete`), lê `naturalWidth`/`naturalHeight` e
  aplica `mainWrap.style.aspectRatio = w + '/' + h`; atualiza a classe `active` nas
  miniaturas; chama `thumb.scrollIntoView({inline:'center', behavior:'smooth',
  block:'nearest'})` na miniatura ativa (satisfaz "a barra acompanha o movimento").
- `.cat-gallery-thumbs` muda de `display:grid` (que quebra linha) para
  `display:flex; overflow-x:auto; scroll-snap-type:x proximity` — vira uma faixa
  horizontal rolável, mais parecida com o comportamento descrito do WordPress.

### 2. Swipe (`detail.html`)

- Listener de `pointerdown`/`pointermove`/`pointerup` em `.cat-gallery-main`: guarda a
  posição X inicial; no `pointerup`, calcula o delta; se `|delta| > 40px` E o movimento
  foi predominantemente horizontal (evita capturar um scroll vertical por engano), chama
  `goToPhoto(current ± 1)`, sempre travado entre `0` e `images.length - 1` (edge case:
  não avança além da última foto).
- Reaproveita o mesmo `goToPhoto` do clique na miniatura — não duplica lógica de
  navegação.

### 3. Botão "Ver mais em categoria" (`app/catalogo/routes.py`, `detail.html`)

- `detail()`: `primary_category = item.categories[0] if item.categories else None`,
  passado ao template.
- Template: `{% if primary_category %}<a href="/catalogo/categoria/{{
  primary_category.slug }}" class="cat-btn cat-btn-ghost">Ver mais em {{
  primary_category.name }}</a>{% endif %}` no lugar do link antigo.

### 4. Reordenar fotos na gestão (`admin_catalogo_form.html`, `app/admin/routes.py`)

- Cada card em `#existing-photos` ganha `draggable="true"` e um `data-photo-id`. Listeners
  de `dragstart` (guarda o id arrastado), `dragover` (`preventDefault` pra permitir soltar)
  e `drop` (reordena os nós DOM, inserindo o card arrastado antes/depois do card alvo
  conforme a posição do cursor) — reordenação puramente visual até o submit.
- Um `<input type="hidden" name="photo_order">` é preenchido, no `submit` do formulário,
  com os `data-photo-id` de todos os cards em `#existing-photos`, na ordem visual atual
  (separados por vírgula).
- `_apply_catalog_photos`: se `photo_order` vier preenchido, usa essa sequência de ids
  (filtrando os que ainda existem após eventual remoção) como a ordem-base de `remaining`,
  em vez do `.order_by(CatalogItemImage.position.asc())` atual — a lógica de capa (que já
  existe, incluindo `new_photo_cover_index` da feature 141) continua rodando por cima
  dessa base, garantindo FR-007 (capa sempre primeiro, ordem manual pro resto).

### 5. Verificação funcional (T00x)

- Script novo (`scripts/db/verify_142_*.py`, gitignored): produto com categoria mostra o
  botão "Ver mais em <categoria>" apontando pro slug certo; produto sem categoria não
  mostra o botão; reordenar fotos existentes ao editar (via `photo_order`) e confirmar que
  a nova ordem é salva; reordenar E marcar uma foto diferente como capa ao mesmo tempo,
  confirmar que a capa fica em `position=0` e o resto segue a ordem manual (FR-007).
- `node --check` no JS de `detail.html` extraído (sintaxe) + simulação da lógica de
  `goToPhoto`/detecção de swipe com um DOM mínimo simulado (ou verificação da lógica pura
  de cálculo de delta/direção, isolada de manipulação de DOM real) — cobrindo: swipe pra
  esquerda avança, pra direita volta, não passa dos limites, arrasto pequeno (abaixo do
  limiar) não troca de foto.
