# Implementation Plan: Transporte explícito por dias no EducaManto + calculadora em React

**Branch**: `171-educamanto-transporte-react` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/171-educamanto-transporte-react/spec.md`

## Summary

Hoje o transporte calculado no EducaManto (endereço → distância → tarifa van/carro + adicional por
pessoa) é somado ao valor final como **uma única viagem**, mesmo quando o pacote tem vários dias de
apresentação fora de São Paulo. A correção multiplica o valor da viagem pelo total de dias
(`d1 + d2`) e deixa isso explícito na linha de resultado (tela Jinja atual). Além disso, cria-se a
primeira tela React do EducaManto — só a calculadora (pacotes, dias, ensemble, transporte já com a
multiplicação por dias, totais sem/com nota, detalhamento) — que precisa de um endpoint de API novo
porque a Constituição (Princípio III) proíbe lógica de negócio no frontend: a fórmula completa de
precificação do pacote e de transporte (hoje só existe replicada em JS na tela Jinja) é extraída para
um módulo Python novo (`app/educamanto/pricing_ops.py`), fonte única usada pela nova API. Geração de
PDF, histórico e CRUD de pacotes continuam só na tela Jinja (fora de escopo, conforme confirmado com
o usuário).

## Technical Context

**Language/Version**: Python 3.11 (Flask) + TypeScript 5.x (React 18 / Vite)

**Primary Dependencies**: Backend: Flask, SQLAlchemy, Flask-Login. Frontend: React, TanStack Query,
Tailwind CSS, shadcn/ui, Framer Motion, `@manto/api-client` (`apiFetch`), `@manto/money`
(`formatBRL`), `@manto/ui`.

**Storage**: PostgreSQL (produção/Railway; cópia local `manto_local` para verificação). Sem mudança
de schema — reusa `EducaMantoPackage`/`EducaMantoItem` e a configuração de transporte existente
(`SiteSetting`, lida via `app.orcamento.settings.load()`).

**Testing**: Script com Flask test client contra `manto_local` (Postgres) cobrindo os novos endpoints
JSON (sucesso, RBAC 401/403, edge cases de dias/km); `npx tsc --noEmit` + `npm run build` em
`frontend/apps/internal`; verificação manual da tela Jinja (multiplicação por dias) e da tela React
no navegador (paridade de valores).

**Target Platform**: Web interno (staff autenticado) — não é superfície pública, Princípio VIII
(mobile-first) não se aplica, mas a tela deve continuar usável em telas menores por consistência com
o resto do `frontend/apps/internal`.

**Project Type**: Web (monorepo existente) — Backend Flask (`app/`) + Frontend React
(`frontend/apps/internal`).

**Performance Goals**: Recalcular o resultado (pacote + transporte) em até ~300ms após o usuário
parar de digitar (debounce), igual ao padrão já usado em outras telas de cálculo já migradas
(ex.: Financeiro/Comissões). Sem requisito de alto throughput — ferramenta interna de uso ocasional.

**Constraints**: Não alterar a calculadora de orçamento (`app/orcamento`) nem sua fórmula de
transporte (`app/orcamento/transport.py`) — só reusar as funções existentes. Não alterar/mover
geração de PDF, histórico (`/educamanto/historico`) nem CRUD de pacotes (`/educamanto/packages/*`) —
permanecem 100% Jinja. Sem migração de banco (nenhum campo novo necessário).

**Scale/Scope**: Ferramenta interna, poucos usuários simultâneos (perfis Comercial/Superadmin/
Ensaio/Revendedor EducaManto). Uma tela nova em React; três endpoints de API novos (leitura +
cálculo); um módulo de regra de negócio novo (`pricing_ops.py`); ajuste pontual na tela Jinja
existente (função `calcTransporte()` e linha de resultado em `educamanto/index.html`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: PASS. `pricing_ops.py` reusa `calcular_van`/`calcular_carro` de
  `app/orcamento/transport.py` (apenas adiciona o multiplicador de dias, específico do EducaManto,
  sem duplicar a fórmula de tarifa/adicional por pessoa) e reusa `EducaMantoPackage.to_dict()`,
  `app.maps.distance_km_ida`, `app.money.parse_brl`, `@manto/api-client`, `@manto/money`, `@manto/ui`
  já existentes.
- **II. Padrões de código**: PASS (a aplicar na implementação) — type hints/docstrings em
  `pricing_ops.py`; TypeScript estrito (sem `any`) na página/hook React novos.
- **III. Arquitetura desacoplada (API first)**: PASS para o código NOVO — a nova tela React só
  consome JSON de `app/api/educamanto_read.py`, que só orquestra/serializa e chama
  `pricing_ops.py` (regra de negócio pura, sem `flask.request`). A tela Jinja legada
  (`app/educamanto/routes.py`, `templates/educamanto/index.html`) continua existindo e replicando o
  cálculo em JS no cliente — isso é o padrão já estabelecido pela feature 076 para essa tela
  específica (carve-out explícito do CLAUDE.md para código Jinja legado das áreas ainda não
  migradas); não estamos introduzindo lógica de negócio nova em Jinja, só ajustando a fórmula já
  replicada lá (multiplicador de dias) da mesma forma que a feature 076 fez.
- **IV. Não quebrar o que funciona**: PASS — verificação funcional dos novos endpoints contra
  `manto_local`; `tsc`/build da tela nova; teste manual da tela Jinja ajustada (cenários de 1 dia e
  múltiplos dias, com e sem transporte) antes de declarar pronto.
- **V. UI/UX com feedback**: PASS (a aplicar) — tela React usa TanStack Query
  (loading/erro/sucesso), `Skeleton` no carregamento de pacotes, mensagens de erro amigáveis em
  pt-BR, sem duplicar submissão.
- **VI. Planejar antes de codar**: PASS — este plano.
- **VII. Valores monetários BRL**: PASS — toda exibição de valor na tela React usa `formatBRL` de
  `@manto/money`; backend mantém float/decimal.
- **VIII. Mobile-first em superfícies públicas**: N/A — EducaManto é ferramenta interna
  (`frontend/apps/internal`), não é superfície pública.
- **IX. Movimento com propósito**: PASS (a aplicar) — transições Framer Motion ao trocar de pacote/
  expandir detalhamento, respeitando `useReducedMotion()`.

Nenhuma violação a justificar — Complexity Tracking fica vazio.

## Project Structure

### Documentation (this feature)

```text
specs/171-educamanto-transporte-react/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── educamanto-calculadora-endpoints.md
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
app/
├── educamanto/
│   ├── routes.py            # AJUSTE pontual: nenhuma mudança de rota; só contexto p/ template
│   │                           (sem mudança — a lógica ajustada mora no JS do template)
│   └── pricing_ops.py        # NOVO — núcleo de negócio puro: calcular_pacote() e
│                                calcular_transporte() (reusa app.orcamento.transport, aplica
│                                multiplicador de dias), sem `flask.request`/`render_template`
├── api/
│   └── educamanto_read.py    # NOVO — GET /api/educamanto/packages, GET /api/educamanto/distancia,
│                                POST /api/educamanto/calcular (RBAC como função, chama pricing_ops)
├── orcamento/
│   └── transport.py          # SEM MUDANÇA — reusado por pricing_ops.py (fonte única da fórmula)
└── templates/educamanto/
    └── index.html             # AJUSTE — calcTransporte() ganha multiplicador de dias + linha de
                                  resultado mais explícita (mesma tela Jinja, sem novo endpoint)

frontend/apps/internal/src/
├── pages/
│   └── EducaMantoCalculadoraPage.tsx   # NOVO — tela da calculadora em React
├── lib/
│   └── educamanto.ts                    # NOVO — hooks TanStack Query (packages, distância,
│                                           calcular) chamando apiFetch
└── App.tsx / router                     # AJUSTE — nova rota (ex.: /educamanto) + item de menu
```

**Structure Decision**: Segue o padrão já usado pelas fatias 165–170 (Cauda Administrativa): núcleo
de negócio puro em `app/<blueprint>/<dominio>_ops.py` (aqui, `app/educamanto/pricing_ops.py`),
endpoint novo em `app/api/<dominio>_read.py`, e tela nova em `frontend/apps/internal/src/pages/`
com hook próprio em `lib/`. Diferença desta fatia: o Jinja legado do EducaManto nunca teve seu
cálculo em Python (estava só em JS no template) — por isso `pricing_ops.py` nasce agora, mas é
consumido **apenas** pela API/React; o Jinja continua com sua réplica em JS (ajustada só no
multiplicador de dias), sem migrar para chamar a API nova.

## Complexity Tracking

*Sem violações à Constituição nesta feature — tabela não se aplica.*
