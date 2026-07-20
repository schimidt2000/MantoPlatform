# Tasks: Migração para arquitetura desacoplada — Fundação (144, User Story 1)

**Input**: Design documents em `/specs/144-migracao-react-spa/` (spec.md, plan.md, research.md,
data-model.md, contracts/api-conventions.md, quickstart.md)

**Prerequisites**: plan.md (lido), spec.md (lido)

**Tests**: sem suíte automatizada de contrato/integração (não solicitada) — verificação é o
script funcional Python já padrão do projeto (T026) + portão de qualidade `tsc`/`build`
(T027), igual ao resto do sistema.

**Escopo**: esta lista cobre **só a User Story 1 (Fundação)** — a única que `plan.md`
detalha. US2–US6 (Agenda/Eventos, Talentos/Figurino, Financeiro/Vendas, Superfícies
Públicas, Cauda Administrativa) recebem seu próprio `tasks.md` quando cada uma tiver seu
`/speckit-plan`, per a estratégia strangler-fig (Q1) já decidida.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência entre si)
- **[US1]**: tarefa da User Story 1 (única story desta lista)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: criar o monorepo `frontend/` e preparar o backend para servir JSON

- [X] T001 Criar `frontend/package.json` como raiz de npm workspaces (`apps/*`, `packages/*`)
- [X] T002 [P] Scaffold `frontend/apps/internal/` via template Vite + React + TypeScript
- [X] T003 [P] Scaffold `frontend/apps/portal/` como workspace mínimo/vazio (conteúdo real é
      escopo de US3 — só o necessário para o workspace resolver)
- [X] T004 [P] Scaffold `frontend/apps/public/` como workspace mínimo/vazio (conteúdo real é
      escopo de US5)
- [X] T005 [P] Scaffold `frontend/packages/ui/` (init shadcn/ui + config base do Tailwind)
- [X] T006 [P] Scaffold `frontend/packages/api-client/` (workspace vazio, preenchido na Phase 2)
- [X] T007 [P] Scaffold `frontend/packages/money/` (workspace vazio, preenchido na Phase 2)
- [X] T008 Configurar `frontend/apps/internal/tailwind.config.ts` mapeando as variáveis CSS
      hoje em `app/static/style.css` (`--accent`, `--line` etc.) para `theme.extend` — mesma
      paleta, zero mudança visual como efeito colateral (depende de T002, T005)
- [X] T009 [P] Adicionar `flask-cors` a `requirements.txt` e instalar no ambiente

**Checkpoint**: monorepo existe, builda vazio, backend tem a dependência de CORS disponível

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestrutura que a User Story 1 (e todas as futuras) vai reaproveitar — API
error envelope, cliente HTTP tipado, TanStack Query, componente monetário único, proxy de dev

**⚠️ CRITICAL**: nenhuma tarefa da Phase 3 começa antes desta fase completa

- [X] T010 Configurar `flask-cors` em `app/__init__.py`: `supports_credentials=True`, lista de
      origens permitidas vinda de variável de ambiente (`CORS_ALLOWED_ORIGINS`, uma entrada
      por app/ambiente — interno/portal/público × dev/produção) — ver `research.md` §2
      (depende de T009)
- [X] T011 [P] Criar `app/api_utils.py`: helper `json_error(message: str, status: int,
      fields: dict | None = None)` retornando o envelope de erro de
      `contracts/api-conventions.md`, e um decorator `api_login_required` que responde
      401 JSON (não redirect) quando não autenticado
- [X] T012 [P] Criar `frontend/packages/api-client/src/client.ts`: wrapper `fetch` tipado
      (`credentials: "include"`, base URL configurável por app, parse do envelope de erro em
      um tipo `ApiError`) (depende de T006)
- [X] T013 [P] Criar `frontend/packages/api-client/src/queryClient.ts`: instância do
      `QueryClient` (TanStack Query) + `QueryClientProvider` exportado, reutilizável pelos 3
      apps (depende de T006)
- [X] T014 [P] Criar `frontend/packages/money/src/formatBRL.ts` e `parseBRL.ts`: portar a
      lógica de `app/static/js/money-mask.js` para TypeScript (fonte única, FR-012) (depende
      de T007)
- [X] T015 [US1-dep] Criar `frontend/packages/money/src/MoneyInput.tsx`: componente de input
      monetário usando `formatBRL`/`parseBRL` (T014) com estilo de `packages/ui` (depende de
      T005, T014) — não usado nesta fatia (Fundação não tem tela de dinheiro), mas
      construído agora para não ser reinventado por US2/US4
- [X] T016 Configurar proxy de dev em `frontend/apps/internal/vite.config.ts`:
      `/api/* → http://localhost:5000` (depende de T002)
- [X] T017 [P] Adicionar componentes base do shadcn/ui (`Button`, `Input`, `Card`,
      `Skeleton`, `Toast`/`Sonner`) em `frontend/packages/ui/src/components/` (depende de T005)

**Checkpoint**: fundação de API/HTTP/monetário pronta — User Story 1 pode começar

---

## Phase 3: User Story 1 - Fundação: login + dashboard (Priority: P1) 🎯 MVP

**Goal**: provar o padrão arquitetural inteiro ponta-a-ponta numa fatia pequena e de baixo
risco (login + dashboard inicial), antes de qualquer uma das outras ~190 rotas ser tocada.

**Independent Test**: um usuário SUPERADMIN loga via `/api/auth/login` (React, sem
`render_template`), vê o dashboard em React com dados reais de `/api/dashboard`, com
feedback de loading/erro/sucesso e transição Framer Motion — rodando lado a lado com o app
Flask+Jinja antigo intacto, sem nenhuma outra rota migrada ainda.

### Backend

- [X] T018 [P] [US1] Implementar `POST /api/auth/login`, `POST /api/auth/logout`,
      `GET /api/auth/me` em `app/auth/routes.py` — JSON puro, usando `json_error` (T011) e o
      shape de `data-model.md` (depende de T011)
- [X] T019 [US1] Extrair a agregação hoje em `home()` (`app/__init__.py:399+` — pendências de
      casting/figurino/ensaio/financeiro/dispensados) para uma função pura em
      `app/dashboard/service.py`, reaproveitada tanto pela rota Jinja antiga (`home()` passa
      a chamá-la) quanto pela nova rota JSON — nenhuma lógica duplicada (Princípio I)
- [X] T020 [US1] Implementar `GET /api/dashboard` em `app/dashboard/routes.py`, chamando o
      serviço de T019 e serializando conforme `data-model.md` §"Resumo do dashboard",
      condicionado por papel/impersonation (depende de T019, T011)

### Frontend

- [X] T021 [P] [US1] Criar `frontend/apps/internal/src/pages/LoginPage.tsx`:
      `react-hook-form` + `zod`, mutation TanStack Query chamando `POST /api/auth/login`,
      estados de loading/erro (preserva valores digitados em erro, foca campo inválido),
      transição Framer Motion no botão (depende de T012, T013, T017)
- [X] T022 [P] [US1] Criar `frontend/apps/internal/src/lib/useAuth.ts`: hook envolvendo
      `GET /api/auth/me` + mutations de login/logout, expondo usuário atual e papéis
      (depende de T012, T013)
- [X] T023 [US1] Criar `frontend/apps/internal/src/components/RequireAuth.tsx`: guarda de
      rota que redireciona para `/login` quando `useAuth()` não retorna usuário (depende de
      T022)
- [X] T024 [US1] Criar `frontend/apps/internal/src/pages/DashboardPage.tsx`: TanStack Query
      buscando `GET /api/dashboard`, seções condicionadas por papel (casting/figurino/
      ensaio/financeiro/dispensados), skeleton de loading, estado de erro amigável, transição
      Framer Motion de entrada (depende de T022, T017)
- [X] T025 [US1] Conectar `frontend/apps/internal/src/main.tsx`/`App.tsx`: rotas
      (`/login`, `/`), `QueryClientProvider` (T013), `RequireAuth` (T023) envolvendo a rota
      do dashboard (depende de T021, T023, T024)

### Verificação

- [X] T026 [US1] Escrever `scripts/db/verify_144_auth_dashboard.py` (gitignored): test client
      do Flask contra `manto_local`, requests fora de `app.app_context()`, cobrindo login
      sucesso/falha, `/api/auth/me` autenticado/401, `/api/dashboard` com campos variando por
      papel, logout (depende de T018, T020)
- [X] T027 [US1] Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal` —
      zero erros (portão de qualidade da constituição 2.0.0) (depende de T025)
- [ ] T028 [US1] **(PENDENTE — com o usuário)** Conferência manual no browser: fluxo
      login→dashboard completo, estados de loading/erro/sucesso, transição Framer Motion,
      comportamento com `prefers-reduced-motion` ativado. Não pode ser feita pelo agente
      (sem browser); `tsc --noEmit` e `vite build` passam, mas isso não substitui o olho no
      app rodando (`npm run dev:internal` + Flask local).

**Checkpoint**: Fundação funcional e testável de forma independente — próxima User Story
(Agenda/Eventos, US2) pode começar seu próprio ciclo spec-kit reaproveitando tudo daqui.

---

## Phase 4: Polish & Cross-Cutting

**Purpose**: fechar a fatia com a documentação do projeto refletindo o estado híbrido real
(não o estado final da migração — isso só quando US6 terminar)

- [ ] T029 [P] **(ADIADA de propósito)** Entrada no `docs/changelog.html` + republicação no
      Artifact. O changelog é "o que vai ao ar em produção"; a Fundação está em branch, não
      mergeada/deployada, e a equipe segue usando o login/home Jinja atual. Adicionar a
      entrada quando a primeira tela React de fato servir usuários em produção — publicar
      agora afirmaria como no ar algo que não está.
- [X] T030 [P] Atualizar `CLAUDE.md` para descrever o **estado híbrido em transição**: backend
      Flask agora serve tanto HTML (rotas ainda não migradas) quanto JSON (`/api/*`, Fundação
      migrada); frontend é Jinja+vanilla para tudo exceto login/dashboard, que agora vivem em
      `frontend/apps/internal` (React) — reescrita completa de `CLAUDE.md` para o estado
      final fica para quando US6 terminar (FR-015 da spec), não antes

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende do Setup — bloqueia toda a Phase 3
- **User Story 1 (Phase 3)**: depende da Phase 2 completa
- **Polish (Phase 4)**: depende da Phase 3 completa

### Dentro da Phase 3

- Backend: T018 é independente de T019/T020 (arquivos diferentes) — pode rodar em paralelo;
  T020 depende de T019 (usa o serviço extraído)
- Frontend: T021 e T022 podem rodar em paralelo; T023 depende de T022; T024 depende de T022;
  T025 depende de T021, T023, T024 (integra tudo)
- Verificação (T026–T028) só depois do backend (T018, T020) e frontend (T025) completos

### Parallel Opportunities

- Phase 1: T002–T007 em paralelo (workspaces diferentes)
- Phase 2: T011–T014, T017 em paralelo (arquivos/pacotes diferentes); T015 depende de T014
- Phase 3: T018 ⟂ (T019→T020); T021 ⟂ T022 (depois T023, T024 em paralelo entre si, ambos
  dependendo só de T022)

---

## Parallel Example: Phase 2 (Foundational)

```bash
Task: "Criar app/api_utils.py com json_error + api_login_required"
Task: "Criar frontend/packages/api-client/src/client.ts"
Task: "Criar frontend/packages/api-client/src/queryClient.ts"
Task: "Criar frontend/packages/money/src/formatBRL.ts e parseBRL.ts"
Task: "Adicionar componentes base do shadcn/ui em frontend/packages/ui/src/components/"
```

---

## Implementation Strategy

### MVP (única fatia desta lista)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (User Story 1)
2. **PARAR e VALIDAR**: rodar T026–T028, confirmar independentemente que login+dashboard
   funcionam via React+API sem tocar em nenhuma outra rota
3. Deploy/demo da Fundação isolada antes de abrir o `/speckit-specify`/`/speckit-plan` de
   US2 (Agenda/Eventos)

### Entrega incremental (visão do projeto inteiro, além desta lista)

Esta lista entrega só a Fundação. Depois dela validada em produção: US2 (Agenda/Eventos) →
US3 (Talentos/Figurino) → US4 (Financeiro/Vendas) → US5 (Superfícies Públicas) → US6 (Cauda
Administrativa) — cada uma com seu próprio spec→plan→tasks→implement, reaproveitando
`packages/ui`, `packages/api-client`, `packages/money` e as convenções de
`contracts/api-conventions.md` estabelecidas aqui.

## Notes

- [P] = arquivos diferentes, sem dependência entre si
- Nenhuma tarefa desta lista toca as ~190 rotas/91 templates ainda não migradas — Princípio
  IV (não quebrar o que funciona) cumprido por escopo, não por cuidado extra
- Commit por tarefa ou por grupo lógico coerente (Setup, Foundational, Backend US1, Frontend
  US1, Verificação) — não um único commit gigante no final
