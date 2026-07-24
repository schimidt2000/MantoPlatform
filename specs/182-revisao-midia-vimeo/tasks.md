---
description: "Task list for Revisão de Mídia estilo Vimeo (182)"
---

# Tasks: Revisão de Mídia estilo Vimeo

**Input**: Design documents from `specs/182-revisao-midia-vimeo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/revisao-status.md, quickstart.md

**Tests**: incluídos — o usuário pediu validação explícita via `tsc`, `vite build` e Playwright contra `manto_local`.

**Organization**: tarefas agrupadas por user story (US1–US4), cada uma independentemente
implementável e testável, conforme `spec.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: US1 (player) / US2 (comentários por timestamp) / US3 (layout 2 colunas) / US4 (versões + status)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: preparar o banco e os fixtures de teste antes de qualquer implementação.

- [X] T001 Adicionar coluna `status` (`db.Column(db.String(20), nullable=False, default="em_revisao", server_default="em_revisao")`) ao model `ReviewAsset` em `app/models.py` (perto de `finalized_at`/`file_removed`, linha ~1407)
- [X] T002 Escrever migration manual Alembic em `migrations/versions/<novo>_add_review_asset_status.py` (`down_revision` = head atual; `upgrade()` adiciona a coluna com `server_default`; `downgrade()` remove a coluna) — depende de T001
- [X] T003 Aplicar a migration em `manto_local`: `$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); python -m flask db upgrade` — depende de T002
- [X] T004 [P] Adicionar vídeo de fixture pequeno (poucos segundos) em `frontend/apps/internal/e2e/fixtures/sample-review.webm` para os testes e2e (`.webm`/VP8, não `.mp4` — Chromium do Playwright não decodifica H.264 sem codecs proprietários)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: estrutura mínima compartilhada pelos componentes novos das 4 stories.

**⚠️ CRITICAL**: completar antes de iniciar qualquer user story.

- [X] T005 [P] Criar diretório `frontend/apps/internal/src/components/revisao/` com barrel export vazio em `frontend/apps/internal/src/components/revisao/index.ts`

**Checkpoint**: estrutura pronta — as 4 user stories podem começar (em paralelo, se houver mais de um desenvolvedor).

---

## Phase 3: User Story 1 - Assistir e navegar o vídeo com precisão (Priority: P1) 🎯 MVP

**Goal**: player de vídeo custom com scrubber clicável, controles de velocidade, atalhos de teclado e tempo formatado.

**Independent Test**: abrir um material de vídeo existente; pausar/retomar com espaço, saltar 5s com as setas, trocar velocidade e ver `MM:SS / MM:SS` — sem depender de comentários, layout ou versões.

### Tests for User Story 1

- [X] T006 [P] [US1] Criar `frontend/apps/internal/e2e/revisao-asset.spec.ts` com o primeiro bloco de testes: play/pause via Espaço, seek de 5s via setas (ignorado com foco em textarea), troca de velocidade, tempo `MM:SS / MM:SS` visível

### Implementation for User Story 1

- [X] T007 [P] [US1] Criar hook `useVideoPlayer` (estado de `currentTime`/`duration`/`playbackRate`/`paused`, métodos `togglePlay`/`seek(delta)`/`seekTo(time)`/`setSpeed`, listener de teclado no `window` que ignora `INPUT`/`TEXTAREA` focados) em `frontend/apps/internal/src/components/revisao/useVideoPlayer.ts`
- [X] T008 [US1] Criar `VideoScrubber.tsx` (barra de progresso clicável/arrastável, sem marcadores ainda — adicionados na US2) em `frontend/apps/internal/src/components/revisao/VideoScrubber.tsx` — depende de T007
- [X] T009 [US1] Criar `VideoPlayer.tsx` (envolve `<video>` nativo com `controls={false}`, botão play/pause, seletor de velocidade 0.5x/1x/1.5x/2x, tempo formatado, embute `VideoScrubber`) em `frontend/apps/internal/src/components/revisao/VideoPlayer.tsx` — depende de T007, T008
- [X] T010 [US1] Substituir o `<video controls>` nativo por `VideoPlayer` em `frontend/apps/internal/src/pages/RevisaoAssetPage.tsx` para `media_type === "video"` (áudio/imagem/PDF sem mudança) — depende de T009

**Checkpoint**: US1 completa e testável de forma independente.

---

## Phase 4: User Story 2 - Comentar e resolver feedback ancorado no tempo exato (Priority: P2)

**Goal**: comentários vinculados a timestamp, com captura automática, seek ao clicar e filtro pendentes/todos.

**Independent Test**: com US1 funcionando, escrever um comentário, confirmar timestamp salvo, clicar nele no feed e ver o player saltar; alternar resolvido e o filtro Todos/Pendentes.

### Tests for User Story 2

- [X] T011 [P] [US2] Estender `e2e/revisao-asset.spec.ts`: foco no campo de comentário pausa o vídeo e mostra `@ MM:SS`; envio cria comentário vinculado; clique no comentário faz seek; toggle resolvido; filtro Todos/Pendentes

### Implementation for User Story 2

- [X] T012 [US2] Adicionar marcadores de comentário ao `VideoScrubber.tsx` (um ponto por `comment.timecode`, posição `timecode/duration * 100%`) — depende de T008
- [X] T013 [US2] Criar `NewCommentForm.tsx` (pausa o player e captura `currentTime` ao focar o textarea via callback recebido do `VideoPlayer`/`useVideoPlayer`, exibe `@ MM:SS`, envia via `useAddRevisaoComment`) em `frontend/apps/internal/src/components/revisao/NewCommentForm.tsx`
- [X] T014 [P] [US2] Criar `CommentFeed.tsx` (lista ordenada por `timecode`, clique faz seek via callback `onSeek`, botões resolver/reabrir/excluir reaproveitando `useToggleResolveComment`/`useDeleteComment`, filtro Todos/Pendentes) em `frontend/apps/internal/src/components/revisao/CommentFeed.tsx`
- [X] T015 [US2] Integrar `NewCommentForm` e `CommentFeed` em `RevisaoAssetPage.tsx`, conectando `onSeek` ao `VideoPlayer` da US1 — depende de T010, T012, T013, T014

**Checkpoint**: US1 e US2 funcionam juntas e de forma independente.

---

## Phase 5: User Story 3 - Revisar em layout imersivo widescreen (Priority: P3)

**Goal**: layout de 2 colunas (player 70% / painel 30%) em widescreen, empilhado em mobile.

**Independent Test**: abrir a tela em viewport ≥1280px e confirmar as 2 colunas; redimensionar para mobile e confirmar o empilhamento com o player no topo.

### Tests for User Story 3

- [X] T016 [P] [US3] Estender `e2e/revisao-asset.spec.ts`: asserção de layout em viewport widescreen (grid 2 colunas) e em viewport mobile (1 coluna, player no topo)

### Implementation for User Story 3

- [X] T017 [US3] Reescrever o container raiz de `RevisaoAssetPage.tsx` para um grid responsivo Tailwind (`grid grid-cols-1 xl:grid-cols-[7fr_3fr] gap-4`, sem `max-w-3xl` centralizado): coluna esquerda com `VideoPlayer`/mídia não-vídeo, coluna direita com o painel de versões/status/comentários — depende de T010, T015
- [X] T018 [US3] Ajustar transições Framer Motion (150–350ms, `useReducedMotion()`) na troca de versão/status e no empilhamento responsivo em `RevisaoAssetPage.tsx` — depende de T017

**Checkpoint**: US1, US2 e US3 funcionam juntas; layout imersivo completo.

---

## Phase 6: User Story 4 - Gerenciar versões e aprovar com um clique (Priority: P4)

**Goal**: seletor de versões no cabeçalho + status de aprovação persistente com ações de um clique.

**Independent Test**: com duas versões existentes, alternar pelo seletor e ver os comentários mudarem; como usuário `can_manage`, trocar o status e confirmar persistência após reload; como usuário sem permissão, confirmar que os controles de status não aparecem.

### Tests for User Story 4

- [X] T019 [P] [US4] Script de verificação funcional Python (Flask test client contra `manto_local`, requests fora de `app_context`) em `specs/182-revisao-midia-vimeo/verify_182.py` (caminho corrigido — segue o padrão real do repo, ver `verify_173.py`/`verify_174.py`, não `scripts/`): GET retorna `status: "em_revisao"` por padrão; `PATCH .../status` com usuário `can_manage` → 200 e persiste; sem permissão → 403; valor inválido → 400; `replace_asset` reseta o status. 9/9 passaram contra `manto_local`.
- [X] T020 [P] [US4] Estender `e2e/revisao-asset.spec.ts`: seletor de versão troca os comentários exibidos; botões de status trocam o badge e o valor sobrevive a um reload; usuário sem permissão não vê os botões

### Implementation for User Story 4

- [X] T021 [US4] Adicionar `set_asset_status(asset, status)` a `app/revisao/review_ops.py` (valida contra os 4 valores, `ReviewValidationError` se inválido) e resetar `asset.status = "em_revisao"` dentro de `replace_asset()` — depende de T001–T003
- [X] T022 [US4] Incluir `"status": asset.status` no dict de `_asset_summary()` em `app/api/revisao_read.py` — depende de T001–T003
- [X] T023 [US4] Adicionar endpoint `PATCH /api/revisao/asset/<int:asset_id>/status` em `app/api/revisao_write.py` (RBAC via `review_ops.can_manage`, delega a `set_asset_status`, erros via `json_error`) — depende de T021
- [X] T024 [P] [US4] Adicionar campo `status` a `RevisaoAssetSummary` e criar `useUpdateAssetStatus(assetId)` (mutation + invalidação de `["revisao-asset", ...]`) em `frontend/apps/internal/src/lib/revisao.ts` — depende de T022, T023
- [X] T025 [US4] Criar `VersionSelector.tsx` (pills/dropdown no cabeçalho, substitui a lista simples de "Histórico de versões") em `frontend/apps/internal/src/components/revisao/VersionSelector.tsx`
- [X] T026 [US4] Criar `StatusBadge.tsx` (badge com cor por status + 4 botões de ação, visíveis só quando `can_manage`, `loading` do `Button` durante a mutation) em `frontend/apps/internal/src/components/revisao/StatusBadge.tsx` — depende de T024
- [X] T027 [US4] Integrar `VersionSelector` e `StatusBadge` no cabeçalho de `RevisaoAssetPage.tsx` — depende de T017, T025, T026

**Checkpoint**: todas as 4 user stories funcionam juntas — feature completa.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T028 [P] Rodar `npx tsc --noEmit` em `frontend/apps/internal` — zero erros
- [X] T029 [P] Rodar `npm run build` em `frontend/apps/internal` — zero erros
- [X] T030 [P] Rodar `ruff check app/revisao app/api/revisao_read.py app/api/revisao_write.py app/models.py` — zero avisos
- [X] T031 Rodar `quickstart.md` de ponta a ponta (migration, `scripts/verify_revisao_status.py`, `npx playwright test e2e/revisao-asset.spec.ts`) contra `manto_local`
- [ ] T032 Atualizar `docs/changelog.html` com a entrega (linguagem simples) e republicar no artifact existente
- [X] T033 Conferir manualmente em viewport mobile (resize/preview) antes de declarar pronto (Princípio VIII) — coberto pelo teste e2e US3 (viewport 390×844) + inspeção manual via Browser preview

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende de Setup — bloqueia as 4 user stories
- **US1 (Phase 3)**: depende só de Foundational
- **US2 (Phase 4)**: depende de Foundational; integra com componentes da US1 (`VideoScrubber`, `VideoPlayer`) mas é testável de forma independente assim que US1 existir
- **US3 (Phase 5)**: depende de Foundational; reorganiza visualmente o que US1+US2 já produziram
- **US4 (Phase 6)**: depende de Foundational + Setup (coluna de status); a parte de backend (T021–T023) é independente de US1–US3, só a integração visual (T025–T027) depende do layout da US3
- **Polish (Phase 7)**: depende de todas as stories desejadas estarem completas

### Parallel Opportunities

- T004 (fixture de vídeo) roda em paralelo com T001–T003 (migration)
- T019–T020 (testes de US4) e T021–T023 (backend de US4) podem ser feitos em paralelo por pessoas diferentes; T024–T027 (frontend de US4) dependem do backend
- T028–T030 (tsc/build/lint) rodam em paralelo entre si na Polish

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1)
2. **Parar e validar**: player funcional de forma independente
3. Seguir incrementalmente para US2 → US3 → US4, validando cada checkpoint antes de avançar

### Incremental Delivery

Cada story fecha um checkpoint testável (ver "Independent Test" de cada fase) antes de a próxima
começar a integrar visualmente — evita que uma regressão de uma story esconda a de outra.
