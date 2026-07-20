# Implementation Plan: Animação suave na galeria de fotos do produto

**Branch**: `143-animacao-galeria-produto` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/143-animacao-galeria-produto/spec.md`

## Summary

A galeria da página do produto (feature 142) troca de foto e redimensiona a moldura
instantaneamente — sem transição — o que o usuário descreveu como "dar um tranco".
Correção é inteiramente client-side em `app/templates/catalogo/detail.html`:

1. A moldura passa a ter sua altura controlada via JS (`height` em pixels, calculado a
   partir da largura fixa do container × proporção da foto atual) em vez de depender só
   de `aspect-ratio`, porque `height` anima de forma confiável entre navegadores via CSS
   `transition` — `aspect-ratio` não tem suporte de animação consistente.
2. A troca de imagem passa por um cross-fade curto (opacity) sincronizado com a mudança
   de altura, em vez de um `src` trocado na hora.
3. O swipe ganha feedback ao vivo: a foto acompanha o dedo/mouse durante o arrasto
   (`transform: translateX`), com uma leve perda de opacidade proporcional à distância;
   solta com distância suficiente conclui a troca (cross-fade), solta sem distância
   suficiente volta suavemente pro lugar (rejeição, como um carrossel nativo).
4. `prefers-reduced-motion: reduce` remove as transições declaradas em CSS
   automaticamente (media query) e faz o JS pular o atraso do cross-fade — a navegação
   continua funcionando, só sem o efeito de movimento.
5. Trocas rápidas/repetidas usam um token de "chamada mais recente" para nunca deixar a
   galeria num estado inconsistente (FR-005).

Adicionalmente (decisão de governança à parte, já aplicada antes desta spec): a
constituição do projeto (`.specify/memory/constitution.md`) ganhou o **Princípio IX —
Movimento com propósito**, formalizando que mudanças de estado visual em superfícies
públicas precisam de transição suave, respeitando `prefers-reduced-motion` — versão
1.6.0.

## Technical Context

**Language/Version**: JavaScript vanilla (sem framework/biblioteca de animação); CSS
transitions nativas

**Primary Dependencies**: nenhuma nova — usa CSS `transition` e a `matchMedia` API
(padrão web), já dentro da mesma convenção "sem dependência externa" das features
133/139/140/141/142

**Storage**: N/A — nenhuma mudança de dado/backend

**Testing**: `node --check` no JS extraído (sintaxe) + simulação da lógica pura de
decisão (limiar de swipe, cálculo de altura a partir de largura×proporção, guarda do
token contra corrida de trocas rápidas) isolada de manipulação de DOM real — mesmo
padrão já usado nas features 138/140/142 pra esse tipo de lógica client-side

**Target Platform**: página pública do catálogo (sem login, mobile-first)

**Project Type**: web application (monolito Flask existente) — mudança restrita a um
template

**Performance Goals**: transições de 150–350ms (mesma faixa definida no novo Princípio
IX da constituição); nenhum impacto de performance de servidor (mudança 100% client-side)

**Constraints**: sem biblioteca de animação/gesture externa; deve respeitar
`prefers-reduced-motion`; não pode regredir nenhum comportamento funcional já entregue na
feature 142 (ordem de fotos, limiar de swipe, sincronização de miniaturas)

**Scale/Scope**: um único arquivo (`app/templates/catalogo/detail.html`) — CSS e JS da
galeria

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: reaproveita a estrutura/IDs da galeria já existentes
  (feature 142) — `goToPhoto`, `applyRatio` viram versões estendidas das mesmas funções,
  não uma reescrita paralela.
- **IV. Não quebrar o que funciona**: nenhuma regra funcional da feature 142 muda (ordem
  das fotos, limiar de 40px, sincronização de miniaturas, botão de categoria) — só a
  qualidade visual da transição. Verificação funcional cobre que a navegação continua
  chegando na foto certa.
- **V. UI/UX consistente**: usa os mesmos tokens de cor/tempo já estabelecidos; nenhuma
  cor nova.
- **VIII. Mobile-first**: o swipe com feedback ao vivo é a melhoria mais relevante
  justamente no celular, onde a maior parte do tráfego do catálogo acontece.
- **IX. Movimento com propósito (novo, nesta mesma sessão)**: esta feature é a aplicação
  direta do princípio recém-criado — transições de 150–350ms, `prefers-reduced-motion`
  respeitado, movimento com propósito (comunicar a troca de foto), não decoração solta.

Nenhuma violação. Gate passa sem exceções.

## Project Structure

### Documentation (this feature)

```text
specs/143-animacao-galeria-produto/
├── plan.md              # This file
├── spec.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

Sem `research.md`/`data-model.md`/`contracts/`: mudança puramente client-side sobre uma
galeria já existente, sem entidade ou interface externa nova.

### Source Code (repository root)

```text
app/
└── templates/
    └── catalogo/
        └── detail.html   # CSS: .cat-gallery-main ganha transition de height+opacity
                          #   (+ media query prefers-reduced-motion); JS: goToPhoto()
                          #   reescrito com cross-fade + altura calculada, guarda de
                          #   corrida (token); swipe ganha feedback ao vivo
                          #   (pointermove) + snap-back quando não cruza o limiar
```

## Design Decisions

1. **Altura via JS em vez de `aspect-ratio` puro**: `applySize(img)` calcula
   `height = min(wrap.clientWidth * naturalHeight/naturalWidth, innerHeight * 0.7)` e
   define `wrap.style.height` (px) — `.cat-gallery-main` ganha `transition: height .32s
   ease` no CSS. Primeira definição de altura (carregamento inicial da página) é aplicada
   sem transição (Edge Case do spec: sem efeito de entrada), reabilitada logo em seguida
   para as trocas subsequentes.

2. **Cross-fade da imagem**: ao trocar de foto, `main` recebe `opacity: 0`
   (`transition: opacity .18s ease`); depois de ~180ms (ou instantâneo se
   `prefers-reduced-motion`), o `src` é trocado, a nova altura aplicada, e a opacity volta
   pra 1. Um contador (`pending`/token) garante que, se uma nova troca começar antes da
   anterior terminar, só a mais recente aplica o resultado final (FR-005) — sem isso,
   trocar de foto rápido demais poderia deixar `src`/altura de uma troca antiga
   "vencendo" por último.

3. **Swipe com feedback ao vivo**: durante `pointermove` com o ponteiro pressionado, a
   imagem principal segue o dedo/mouse via `transform: translateX(deltaX)` (sem
   transição — acompanha 1:1), com a opacidade caindo levemente proporcional à distância
   arrastada (feedback de "puxando"). No `pointerup`: se o deslocamento cruzou o limiar
   (mesmo valor já usado, 40px, predominantemente horizontal), o transform volta a 0
   instantaneamente enquanto `goToPhoto()` já assume a transição via cross-fade (a queda
   de opacidade em andamento disfarça o reset); se não cruzou o limiar, o transform volta
   a 0 e a opacidade volta a 1 COM transição suave (`transition: transform .22s ease,
   opacity .22s ease`) — sensação de "recusa" igual a um carrossel nativo. O
   acompanhamento 1:1 do dedo em si não é desabilitado por `prefers-reduced-motion` (é
   manipulação direta, não uma animação decorativa/automática — mesmo critério do WCAG
   2.3.3), mas a animação de snap-back/conclusão respeita a preferência.

4. **`prefers-reduced-motion`**: uma media query em CSS zera as `transition` declaradas
   (`height`, `opacity`, `transform` de snap-back) quando o sistema operacional da pessoa
   pede menos movimento; o JS consulta `window.matchMedia('(prefers-reduced-motion:
   reduce)').matches` uma vez para pular o atraso de 180ms do cross-fade (troca
   instantânea do `src`, já que a transição de opacidade não vai rodar mesmo).

5. **Verificação (T00x)**: sem mudança de backend, então sem script Python novo contra
   `manto_local` — a verificação desta feature é: `node --check` no JS extraído +
   simulação da lógica pura (cálculo de altura a partir de largura×proporção, decisão de
   limiar do swipe idêntica à já usada na feature 142, e o comportamento do token de
   "chamada mais recente vence" simulado com uma sequência de chamadas fora de ordem)
   + smoke test HTTP simples (a página `/catalogo/<slug>` continua respondendo 200 e
   contendo os elementos da galeria) pra garantir que o template não quebrou.
