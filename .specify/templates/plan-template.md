<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: [FEATURE]

**Branch**: `[NNN-nome]` | **Data**: [AAAA-MM-DD] | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/[NNN-nome]/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3+) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

[requisito principal da spec + abordagem técnica escolhida na pesquisa]

## Contexto técnico

<!--
  Stack real da Manto, já preenchida. Troque só o que a feature muda; marque NEEDS CLARIFICATION
  onde não souber.
-->

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack
Query, Tailwind CSS, shadcn/ui (`@manto/ui`), Framer Motion, `@manto/api-client`
(`apiFetch`/`assetUrl`), `@manto/money`

**Armazenamento**: PostgreSQL — produção no Render (`manto-postgres`, `render.yaml`); verificação
contra a cópia `manto_local`. Arquivos no disco persistente do `manto-backend` (`app/storage.py`)

**Verificação**: `specs/NNN-nome/verify_NNN.py` contra `manto_local` (login só pela API; escrita
por conexão separada); `cd frontend && npm run typecheck` (três SPAs); tela aberta no Browser
pane; superfície pública em viewport mobile

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs servidas por `frontend/server.js`);
staff em desktop, público e portal em smartphone

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: [específicas da feature, ou N/A]

**Restrições**: [ex.: URL imutável; sem login; 320–430px sem rolagem; `useReducedMotion`; rota
pública nova precisa entrar em `BACKEND_PREFIXES` de `frontend/server.js`]

**Escala/escopo**: [tabelas, colunas, endpoints, telas]

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | [o que já existe e é reusado: `_ops`, hooks, componentes, gates] |
| II. Padrões de código | type hints/docstrings; TS estrito; constantes; `ruff check` nos tocados |
| III. Camadas / API First | `_ops.py` puro; `_read`/`_write` só RBAC + serialização; import em `app/api/__init__.py`; `BACKEND_PREFIXES` se rota pública |
| IV. Não quebrar o que funciona | mudança aditiva? pontos compartilhados conferidos? |
| V. UI/UX com feedback | TanStack Query; loading nos botões; erro no campo; toasts pt-BR |
| VI. Esteira (Nível 1) | esteira completa; artefatos mínimos em `specs/NNN-nome/` |
| VII. Living Spec | spec atualizada antes do código |
| VIII. Verify antes do núcleo | `verify_NNN.py` na fase Foundational, falhando pelos motivos certos |
| IX. Dinheiro BRL | `@manto/money`; `Numeric/Decimal` |
| X. Mobile-first público | [se toca superfície pública] |
| XI. Framer Motion | [se toca UI] |
| XII. Combobox / Maps | [se lista > 10 itens ou endereço] |
| XIII. RBAC declarado | papéis por endpoint; linha em `docs/01` §4.3 |
| XIV. Config / efeito externo | env nova com default real; trava `_suppress_*` se escreve fora |
| Stack | migration à mão (`down_revision` = head); sem Jinja novo; sem segredo |
| Operação e Deploy | [toca `startCommand`? migração destrutiva → ensaio em banco descartável] |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/[NNN-nome]/
├── spec.md              # /speckit-specify
├── plan.md              # este arquivo (/speckit-plan)
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
├── checklists/          # /speckit-checklist
├── tasks.md             # /speckit-tasks
└── verify_NNN.py        # Princípio VIII — escrito antes do núcleo
```

### Código (caminhos reais — apague o que não usar)

```text
app/models.py                               # models; migration à mão em migrations/versions/
app/<dominio>/<nome>_ops.py                 # núcleo de negócio puro (sem flask.request)
app/api/<dominio>_read.py | _write.py       # endpoints; registrar em app/api/__init__.py
app/constants.py, app/config.py             # constantes; config com default real
frontend/apps/<internal|public|portal>/src/{pages,components,lib}/
frontend/packages/{ui,api-client,money}/    # componente novo: exportar em packages/ui/src/index.ts
frontend/server.js                          # BACKEND_PREFIXES / mounts, só se houver rota pública nova
```

**Decisão de estrutura**: [onde cada parte da feature mora e por quê]

## Rastreamento de complexidade

> Preencher SÓ se o Constitution Check tiver violação a justificar.

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| [ex.: import tardio de `calendar/routes.py`] | [necessidade] | [por que o `_ops` não basta hoje] |
