# Implementation Plan: Migração para arquitetura desacoplada (React SPA + Flask API)

**Branch**: `main` (constituição alterada direto na main; branch de feature dedicado a ser
criado quando a implementação da Fundação começar) | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/144-migracao-react-spa/spec.md`

## Summary

Este plano cobre **apenas a User Story 1 (Fundação)** da spec — a fatia vertical que prova o
padrão arquitetural inteiro (monorepo frontend, ponte de autenticação por cookie entre 3
SPAs e o Flask, convenção de contrato JSON, migração de design tokens, verificação
funcional) antes de qualquer uma das outras 193 rotas ser tocada. É a decisão correta dado o
Q1 (strangler-fig): cada User Story subsequente (Agenda/Eventos, Talentos/Figurino,
Financeiro/Vendas, Superfícies Públicas, Cauda Administrativa) recebe seu próprio ciclo
`/speckit-plan` → `/speckit-tasks` → `/speckit-implement` quando chegar sua vez, reaproveitando
as decisões estabelecidas aqui (não faz sentido planejar 194 endpoints em detalhe antes do
primeiro sequer existir).

Escopo concreto desta fatia: `POST /api/auth/login`, `POST /api/auth/logout`,
`GET /api/auth/me`, `GET /api/dashboard` no backend Flask; e no frontend, o app
`frontend/apps/internal` (Vite+React+TS+Tailwind+shadcn/ui+Framer Motion+TanStack
Query+react-hook-form+zod) com a tela de login e o dashboard inicial, mais os pacotes
compartilhados `ui`, `api-client` e `money` que todas as User Stories seguintes vão
reaproveitar.

## Technical Context

**Language/Version**: Python 3.11 (backend, inalterado) + TypeScript 5.x / Node 20+ (frontend, novo)

**Primary Dependencies**:
- Backend (novo nesta fatia): `flask-cors` (CORS com `supports_credentials`)
- Frontend (novo, definido pela constituição 2.0.0): React 18, Vite, TypeScript, Tailwind
  CSS, shadcn/ui, Framer Motion, TanStack Query, react-hook-form, zod

**Storage**: PostgreSQL (Railway em produção, `manto_local` para dev/verificação) — inalterado

**Testing**: Backend — script Python com test client do Flask contra `manto_local`
(mesmo padrão do projeto, adaptado para JSON). Frontend — `tsc --noEmit` + `npm run build`
como portão de qualidade (constituição 2.0.0); sem framework de teste JS além disso nesta
fatia.

**Target Platform**: web — 3 bundles SPA (interno/portal/público) servidos separadamente +
API Flask existente

**Project Type**: web application, monorepo (backend em `app/` na raiz, novo `frontend/`
com npm workspaces — 3 apps + 3 pacotes compartilhados)

**Performance Goals**: sem meta numérica nova nesta fatia — a única superfície tocada
(`apps/internal`) é interna/autenticada, sem a mesma pressão de peso de bundle que
`apps/public` terá em US5 (mobile-first, tráfego anônimo)

**Constraints**: cookie de sessão HttpOnly deve funcionar entre os 3 futuros bundles e a API
sob origens diferentes (CORS + `credentials: "include"`, proxy de dev — ver `research.md`
§2); componente de máscara monetária deve ter fonte única compartilhada entre os 3 apps
desde já (mesmo que só `apps/internal` a use nesta fatia) para não repetir o erro de
"formatação por tela" que a constituição proíbe (FR-012).

**Scale/Scope**: 4 endpoints JSON, 1 app React com 2 telas (login, dashboard), 3 pacotes
compartilhados — escopo deliberadamente pequeno (é a fatia de fundação, não a migração
inteira).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: a lógica de negócio do dashboard (queries de
  casting/figurino/ensaio/financeiro) é reaproveitada tal como está em `app/__init__.py`,
  só muda a camada de saída (JSON em vez de `render_template`) — nenhuma regra duplicada.
  RBAC (`has_role`, `is_superadmin`, impersonation) também é reaproveitado do backend
  existente, não reescrito.
- **II. Padrões de código**: Python mantém type hints/docstrings; TypeScript estrito
  (proibido `any`) nos novos pacotes/app — alinhado ao novo Princípio II.
- **III. Arquitetura Desacoplada (API First)**: os 4 endpoints desta fatia não usam
  `render_template` em nenhum momento — cumprem a regra "Backend é 100% API RESTful JSON"
  desde a primeira rota migrada.
- **IV. Não quebrar o que funciona**: o Flask atual continua servindo todas as outras ~190
  rotas via Jinja normalmente durante esta fatia (strangler-fig) — só `/api/auth/*` e
  `/api/dashboard` são novos, sem tocar nenhuma rota/template existente. Verificação
  funcional roda contra `manto_local` antes de considerar pronto.
- **V. UI/UX consistente e com feedback**: login/dashboard em React cobrem loading/erro/
  sucesso via TanStack Query, formulário com `react-hook-form`+`zod` preservando valores em
  erro, botão de login nunca "morto" ao clique.
- **VI. Planejar antes de codar**: este plano + a spec + as 3 perguntas de clarificação já
  respondidas cumprem o fluxo ENTENDER→ESPECIFICAR→PLANEJAR antes de qualquer código.
- **VII. Valores monetários pt-BR**: o pacote `money` é criado nesta fatia como fonte única,
  mesmo sem uma tela de valor monetário real ainda em `apps/internal` — antecipa a exigência
  de "fonte única" (FR-012) para quando US2/US4 precisarem dele, em vez de cada User Story
  futura reinventar o componente.
- **VIII. Mobile-first em superfícies públicas**: não se aplica a esta fatia — `apps/internal`
  é uma tela interna, autenticada, sem o mesmo tráfego de smartphone anônimo do catálogo/
  cadastro (esses ficam para US5). Fica registrado como não-aplicável, não como ignorado.
- **IX. Movimento com propósito**: transição Framer Motion no botão de login (loading state)
  e na navegação login→dashboard, respeitando `useReducedMotion()`.

Nenhuma violação. Gate passa sem exceções — não há entrada na Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/144-migracao-react-spa/
├── plan.md              # This file — cobre só US1 (Fundação)
├── research.md           # Phase 0: monorepo, auth/CORS, contrato JSON, design tokens, verificação
├── data-model.md         # Phase 1: shape de usuário autenticado e resumo do dashboard
├── contracts/
│   └── api-conventions.md  # Phase 1: convenção geral de sucesso/erro + os 4 endpoints desta fatia
├── quickstart.md         # Phase 1: estrutura de diretórios, dev setup, verificação
└── tasks.md               # Phase 2 output (/speckit-tasks — ainda não gerado)
```

US2–US6 recebem suas próprias pastas `specs/14X-...` quando começarem (cada uma com seu
próprio spec/plan/tasks), reaproveitando a Fundação estabelecida aqui — não serão
subpastas desta.

### Source Code (repository root)

```text
Manto_Platform/
├── app/                          # Flask — backend existente
│   ├── __init__.py               # + registro de flask-cors; home() ganha irmã /api/dashboard
│   ├── auth/
│   │   └── routes.py             # + POST /api/auth/login, /logout, GET /api/auth/me (JSON)
│   └── ...                       # demais blueprints inalterados nesta fatia
├── frontend/                     # NOVO — monorepo npm workspaces
│   ├── package.json
│   ├── apps/
│   │   ├── internal/             # SPA staff — login + dashboard nesta fatia
│   │   │   ├── src/
│   │   │   │   ├── pages/LoginPage.tsx
│   │   │   │   ├── pages/DashboardPage.tsx
│   │   │   │   └── main.tsx
│   │   │   ├── vite.config.ts    # proxy /api → Flask local
│   │   │   └── tailwind.config.ts
│   │   ├── portal/               # scaffolding vazio (US3+)
│   │   └── public/               # scaffolding vazio (US5+)
│   └── packages/
│       ├── ui/                   # shadcn/ui + tema Tailwind base
│       ├── api-client/           # fetch wrapper tipado + hooks TanStack Query
│       └── money/                # <MoneyInput/> + hook de formatação BRL (FR-012)
```

**Structure Decision**: monorepo com o backend Flask permanecendo na raiz do repositório
(`app/`, inalterado em localização — Princípio IV, não mexer no que funciona sem motivo) e
um novo diretório `frontend/` com npm workspaces contendo 3 apps (um por população de
usuário, conforme Q2) e 3 pacotes compartilhados. `apps/internal` é o único com conteúdo
real nesta fatia; `apps/portal` e `apps/public` existem só como scaffolding do workspace,
vazios, para as User Stories que os preenchem (US3 e US5 respectivamente).

## Complexity Tracking

*Sem violações — tabela não aplicável nesta fatia.*
