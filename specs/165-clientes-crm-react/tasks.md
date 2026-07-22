# Tasks: Clientes (CRM) em React (165)

**Input**: Design documents from `specs/165-clientes-crm-react/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/clientes-endpoints.md,
quickstart.md

**Tests**: verificação é o script de paridade `scripts/db/verify_165_clientes_react.py` contra
`manto_local`, gerado na Phase de Polish.

**Organização**: 4 user stories, todas nesta mesma fatia (165) — US1 busca/criação rápida (P1,
integra com a tela de evento já migrada), US2 lista/ficha (P2), US3 editar/excluir (P3), US4
avaliações (P4).

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` (Postgres) atualizado (`python -m flask db heads`) — sem
      migration nova nesta fatia.

## Phase 2: Foundational

- [X] T002 Criar `app/clientes/client_ops.py` (NOVO): mover para lá o núcleo hoje embutido em
      `app/clientes/routes.py` — `search_clients`, `quick_create_client`, `list_clients`,
      `get_client_detail`, `update_client_fields`, `delete_client`, `summarize_feedback`, e a
      exceção `ClientValidationError(field, message)`. Funções puras, type hints, docstrings
      Google-style, ≤30 linhas cada. `routes.py` passa a chamar essas funções (sem duplicar
      lógica) — a view Jinja continua funcionando sem mudança de comportamento (FR-010).
- [X] T003 [P] Criar `app/api/clientes_read.py` (NOVO, esqueleto): blueprint
      `clientes_api_bp`/`clientes_api_read_bp` com gate `require_vendas` reimplementado como
      função (COMERCIAL/FINANCEIRO/SUPERADMIN, paridade com `app/clientes/routes.py::_has_role`).
- [X] T004 [P] Criar `app/api/clientes_write.py` (NOVO, esqueleto): blueprint próprio, mesmo gate
      base + gate extra SUPERADMIN/FINANCEIRO para exclusão.
- [X] T005 Registrar os 2 blueprints novos em `app/__init__.py` (prefixo `/api/clientes`).
- [X] T006 [P] Criar `frontend/apps/internal/src/lib/clientes.ts` (NOVO, esqueleto): tipos
      TypeScript compartilhados (`Client`, `ClientDetail`, `ClientListItem`, `FeedbackSummary`)
      usados pelos hooks de todas as user stories.

**Checkpoint**: infraestrutura pronta — cada user story abaixo só adiciona endpoint/hook/tela.

## Phase 3: User Story 1 — Buscar e criar cliente rapidamente (P1)

**Goal**: usuário Comercial/Financeiro/Superadmin busca cliente (sem acentos) e cria rapidamente
via React, com o `ClientPicker` da tela de evento (US2 da migração, já em produção) consumindo o
endpoint novo sem quebrar.

**Independent Test**: no seletor de cliente de uma tela React, buscar com/sem acento e criar um
cliente novo ou reaproveitar um existente por telefone, com paridade de resultado com
`/clientes/search`/`/clientes/quick-create` (Jinja) para o mesmo termo/dados.

- [X] T007 [US1] Implementar `GET /api/clientes/search` em `app/api/clientes_read.py`: chama
      `client_ops.search_clients`, serializa conforme `contracts/clientes-endpoints.md`.
- [X] T008 [US1] Implementar `POST /api/clientes/quick-create` em `app/api/clientes_write.py`:
      chama `client_ops.quick_create_client`, captura `ClientValidationError` → 400 com `fields`.
- [X] T009 [P] [US1] Adicionar `useClientSearch`/`useQuickCreateClient` em
      `frontend/apps/internal/src/lib/clientes.ts`.
- [X] T010 [US1] Atualizar `frontend/apps/internal/src/components/ClientPicker.tsx`: trocar
      `fetch(`${API_BASE}/clientes/search?q=...`)` por `${API_BASE}/api/clientes/search?q=...`
      (ou pelo hook novo `useClientSearch`) — conferir que a tela de evento continua funcionando.

**Checkpoint**: US1 completa e testável isoladamente; `ClientPicker` não quebrou.

---

## Phase 4: User Story 2 — Consultar a lista e a ficha de clientes (P2)

**Goal**: usuário autorizado vê a lista de clientes (busca, contagem de eventos) e a ficha
completa de um cliente (contato, CPF/CNPJ, endereço, eventos, total vendido) em React.

**Independent Test**: abrir lista e ficha em React, comparar com `/clientes` e `/clientes/<id>`
(Jinja) para o mesmo termo/cliente.

- [X] T011 [US2] Implementar `GET /api/clientes/` em `app/api/clientes_read.py`: chama
      `client_ops.list_clients`, serializa envelope `{"items", "total_clients"}`.
- [X] T012 [US2] Implementar `GET /api/clientes/<id>` em `app/api/clientes_read.py`: chama
      `client_ops.get_client_detail`, serializa `{cliente..., "events", "total_sales"}`; 404 se
      não existir.
- [X] T013 [P] [US2] Adicionar `useClients(query)`/`useClientDetail(id)` em
      `frontend/apps/internal/src/lib/clientes.ts`.
- [X] T014 [US2] Criar `frontend/apps/internal/src/pages/ClientsListPage.tsx` (NOVO): busca,
      tabela/lista de clientes com contagem de eventos, link para a ficha; loading/erro/vazio;
      mobile-first.
- [X] T015 [US2] Criar `frontend/apps/internal/src/pages/ClientDetailPage.tsx` (NOVO): contato,
      CPF/CNPJ, endereço, lista de eventos associados (com relação), total vendido
      (`formatBRL`/`@manto/money`); loading/erro/vazio; mobile-first.
- [X] T016 [US2] Adicionar rotas `/clientes` e `/clientes/:id` em `App.tsx` (+ navegação).

**Checkpoint**: US2 completa e testável isoladamente (não depende de US3/US4).

---

## Phase 5: User Story 3 — Editar e excluir cliente (P3)

**Goal**: usuário autorizado edita CPF/CNPJ/endereço na ficha; Superadmin/Financeiro exclui
cliente sem deixar evento órfão.

**Independent Test**: editar dados na ficha React e ver refletido; tentar excluir como Comercial
(403); excluir como Financeiro/Superadmin e confirmar que eventos associados permanecem sem
cliente vinculado.

- [X] T017 [US3] Implementar `PATCH /api/clientes/<id>` em `app/api/clientes_write.py`: chama
      `client_ops.update_client_fields`.
- [X] T018 [US3] Implementar `DELETE /api/clientes/<id>` em `app/api/clientes_write.py`: gate
      extra SUPERADMIN/FINANCEIRO, chama `client_ops.delete_client`, 204.
- [X] T019 [P] [US3] Adicionar `useUpdateClient`/`useDeleteClient` (mutations) em
      `frontend/apps/internal/src/lib/clientes.ts`.
- [X] T020 [US3] Adicionar formulário de edição (CPF/CNPJ/endereço, `react-hook-form`+`zod`,
      preserva valores em erro) e botão de exclusão com dialog de confirmação (`shadcn/ui`,
      escondido para quem não é Superadmin/Financeiro) em `ClientDetailPage.tsx`.

**Checkpoint**: US3 completa e testável isoladamente.

---

## Phase 6: User Story 4 — Ver avaliações recebidas das clientes (P4)

**Goal**: usuário autorizado vê o resumo de avaliações das clientes com filtros de período, nota,
tag e cliente.

**Independent Test**: aplicar cada filtro isoladamente e em conjunto em React, comparar com
`/clientes/avaliacoes` (Jinja) para os mesmos filtros.

- [X] T021 [US4] Implementar `GET /api/clientes/avaliacoes` em `app/api/clientes_read.py`: chama
      `client_ops.summarize_feedback`, serializa conforme `contracts/clientes-endpoints.md`.
- [X] T022 [P] [US4] Adicionar `useClientFeedback(filters)` em
      `frontend/apps/internal/src/lib/clientes.ts`.
- [X] T023 [US4] Criar `frontend/apps/internal/src/pages/ClientFeedbackPage.tsx` (NOVO): filtros
      (período/nota/tag/cliente), totais, distribuição por nota, lista de atenção; loading/erro/
      vazio; mobile-first.
- [X] T024 [US4] Adicionar rota `/clientes/avaliacoes` em `App.tsx` (+ navegação).

**Checkpoint**: US4 completa e testável isoladamente.

---

## Phase 7: Polish & Verificação

- [X] T025 Criar `scripts/db/verify_165_clientes_react.py` (gitignored): test client Flask contra
      `manto_local`, requests fora de `app_context` — cobre paridade de busca/lista/ficha/
      avaliações, criação rápida (novo/reaproveitado/erros), edição, exclusão (sucesso +403
      Comercial), e gate 403 para papel fora de Comercial/Financeiro/Superadmin.
- [X] T026 Rodar `ruff check app/` nos arquivos tocados (`client_ops.py`, `routes.py`,
      `clientes_read.py`, `clientes_write.py`).
- [X] T027 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [ ] T028 Conferência mobile (320–430px) das 3 telas novas (lista, ficha, avaliações) — **não
      verificado nesta sessão**: sem Playwright/chromium-cli disponível no ambiente (mesma
      limitação da 157/158). Classes mobile-first seguem o mesmo padrão já usado; recomenda-se
      conferência visual manual antes do merge, se possível.
- [X] T029 Atualizar `docs/changelog.html` com entrada em linguagem simples e republicar no link
      existente.

## Dependencies

Setup (Phase 1) → Foundational (Phase 2) → US1 (P1) → US2 (P2) → US3 (P3) → US4 (P4) → Polish
(Phase 7). US2/US3/US4 dependem só da Foundational (client_ops.py, blueprints registrados), não
umas das outras — podem ser feitas em qualquer ordem entre si, mas seguimos a ordem de
prioridade do spec. Dentro de cada story: endpoint(s) API → hook(s) frontend → página → rota.

## Implementation Strategy

MVP = US1 (busca/criação rápida) — é o único ponto de integração com a Agenda já migrada; as
demais user stories desta fatia (US2–US4) entregam valor incremental sobre a mesma
`client_ops.py`, sem depender umas das outras.
