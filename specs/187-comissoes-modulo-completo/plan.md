# Implementation Plan: Reestruturação do Módulo de Comissões

**Branch**: `187-comissoes-modulo-completo` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/187-comissoes-modulo-completo/spec.md`

## Summary

Reestruturar `/financeiro/comissoes` no app React (`frontend/apps/internal`): RBAC real
aplicado no servidor (vendedor comum só vê/opera sobre si mesmo), 3 KPIs somados no banco, duas
visões (resumo por vendedor com liquidação em lote / detalhamento analítico), liquidação em
lote atômica por vendedor+mês (corrige o `_bulk_set_commission_period` hoje duplicado e não
transacional em `app/api/financeiro_write.py` e `app/financeiro/routes.py`), e exportação CSV.
Abordagem técnica: extrair um módulo `app/financeiro/comissoes_ops.py` com a agregação e a
liquidação (fonte única, sem tocar na view Jinja legada), evoluir os dois endpoints JSON
existentes e adicionar um endpoint de liquidação dedicado, e reescrever `ComissoesPage.tsx` +
`lib/financeiro.ts` com dois pequenos componentes novos no design system compartilhado
(`Dialog`, `Tabs`) que faltavam para atender ao Princípio V da constituição (confirmação de
ação destrutiva via modal shadcn/ui, não `window.confirm()`).

## Technical Context

**Language/Version**: Python 3.11 (backend, Flask), TypeScript 5 (frontend, React 18)

**Primary Dependencies**: Flask + SQLAlchemy + Flask-Login (backend); Vite + React + TanStack
Query + Tailwind + `@manto/ui` (shadcn/ui-style) + Framer Motion (frontend)

**Storage**: PostgreSQL (produção Railway / cópia local `manto_local`) — tabela
`commission_payments` (única tocada por esta feature)

**Testing**: script de verificação funcional com `app.test_client()` do Flask contra
`manto_local`, cobrindo os 3 papéis e a atomicidade; `tsc --noEmit` + `npm run build` no
frontend

**Target Platform**: Web (SPA servida pelo Flask via build estático em produção; Vite dev
server com proxy `/api` em desenvolvimento)

**Project Type**: Web application (backend Flask `app/` + frontend monorepo `frontend/`)

**Performance Goals**: consulta de um mês com centenas de comissões deve responder em menos de
500ms (uma única query agregada por visão, sem N+1)

**Constraints**: não alterar `app/financeiro/routes.py` (Jinja legado) nem templates; não
tocar tabela além de `commission_payments`; sem migração de schema nova (ver Research §3)

**Scale/Scope**: dezenas de vendedores, algumas centenas de comissões por mês — volume baixo,
sem necessidade de paginação

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Aplicação nesta feature | Status |
|---|---|---|
| I — Reutilizar antes de criar | `comissoes_ops.py` é extraído para não duplicar a 3ª cópia da lógica de liquidação (hoje já duplicada 2x); `_resync_pending_commissions`/`_COMMISSION_STATUS_LABELS` continuam sendo a única fonte, reusados por leitura | ✅ Pass |
| II — Padrões Python/TS | type hints + docstrings Google style em `comissoes_ops.py`; zero `any` no TS novo | ✅ Pass (a verificar na implementação) |
| III — API First, camadas | rotas em `app/api/financeiro_{read,write}.py` só validam RBAC e serializam; regra de negócio 100% em `comissoes_ops.py`, sem `request`/Flask | ✅ Pass |
| IV — Não quebrar o que funciona | Jinja legado intocado; `tsc`/build rodados antes do commit; verificação funcional contra `manto_local` | ✅ Pass (a verificar) |
| V — UI/UX consistente e com feedback | Ação de liquidação é financeira e irreversível → exige modal `shadcn/ui`, não `window.confirm()` (ver Research §1); todo botão de ação usa estado de loading | ⚠️ Requer novo componente `Dialog` — justificado abaixo |
| VI — Planejar antes de codar | Fluxo spec-kit completo sendo seguido | ✅ Pass |
| VII — Dinheiro no padrão BR | Todos os valores exibidos via `formatBRL`/`@manto/money`, já usado hoje na tela | ✅ Pass |
| VIII — Mobile-first | Não é superfície pública (staff autenticado) — mobile-first não é obrigatório, mas a tela deve permanecer utilizável em viewport estreito (verificação manual) | ✅ Pass |
| IX — Movimento com propósito | Abertura do modal, troca de aba e expansão do accordion usam Framer Motion, respeitando `useReducedMotion()` | ✅ Pass |

**Violação a justificar (Complexity Tracking)**: criar `Dialog` (e um `Tabs`/`Accordion`
mínimos) em `@manto/ui` em vez de usar `window.confirm()` como o restante do app faz hoje.

## Project Structure

### Documentation (this feature)

```text
specs/187-comissoes-modulo-completo/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/
│   └── comissoes-api.md  # Fase 1
└── tasks.md              # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── financeiro/
│   ├── routes.py                # INTOCADO (Jinja legado)
│   └── comissoes_ops.py         # NOVO — agregação + liquidação em lote atômica (puro)
├── api/
│   ├── financeiro_read.py       # AJUSTADO — GET /financeiro/comissoes evolui payload
│   └── financeiro_write.py      # AJUSTADO — novo POST /financeiro/comissoes/pagar-mes
└── models.py                    # INTOCADO (CommissionPayment já tem os campos necessários)

frontend/
├── packages/ui/src/
│   ├── components/
│   │   ├── dialog.tsx            # NOVO — Dialog shadcn/ui-style (Radix-like, local)
│   │   ├── tabs.tsx              # NOVO — Tabs shadcn/ui-style
│   │   └── accordion-row.tsx     # NOVO — linha expansível simples (usa Framer Motion)
│   └── index.ts                  # AJUSTADO — exporta os 3 novos componentes
└── apps/internal/src/
    ├── lib/financeiro.ts         # AJUSTADO — hooks: useComissoes (evoluído), usePagarMesComissao
    └── pages/ComissoesPage.tsx   # REESCRITO
```

**Structure Decision**: Web application já existente (backend Flask + frontend monorepo). Esta
feature só adiciona/ajusta arquivos dentro dos diretórios já estabelecidos pelo padrão do
projeto (`app/<blueprint>/<dominio>_ops.py`, `app/api/<dominio>_{read,write}.py`,
`frontend/apps/internal/src/{lib,pages}`, `frontend/packages/ui`) — nenhum diretório novo de
alto nível é criado.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| Novo `Dialog` em `@manto/ui` (em vez de `window.confirm()`, hoje o padrão do app) | A ação "Pagar Mês" é financeira/irreversível e a spec exige mostrar nome do vendedor + valor formatado + mês no aviso de confirmação — `window.confirm()` só produz uma caixa de texto puro do navegador, sem estilo, sem `formatBRL` renderizado com destaque, e a Constituição (Princípio V, "ações destrutivas exigem confirmação via modal/dialog do shadcn/ui") já supersede a nota antiga do CLAUDE.md sobre `window.confirm()` | `window.confirm()` foi rejeitado por violar o Princípio V diretamente e por não conseguir formatar o valor em destaque; construir o `Dialog` como componente pequeno e genérico em `@manto/ui` (não só nesta página) para já ficar disponível para a próxima tela que precisar de confirmação rica, evitando uma 2ª implementação futura |
| Novo `Tabs`/accordion mínimo em `@manto/ui` | A spec pede explicitamente duas visões alternáveis e linhas expansíveis; não existe hoje nenhum componente de abas ou expansão no design system compartilhado | Implementar só localmente em `ComissoesPage.tsx` foi considerado, mas violaria o Princípio I na primeira tela futura que precisar do mesmo padrão — o componente é pequeno o suficiente (states + Framer Motion) para não ser overengineering |
