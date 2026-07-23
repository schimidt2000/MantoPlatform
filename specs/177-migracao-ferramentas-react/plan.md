# Implementation Plan: Migração das últimas ferramentas Jinja para React

**Branch**: `177-migracao-ferramentas-react` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/177-migracao-ferramentas-react/spec.md`

## Summary

Migrar as 7 últimas telas/ferramentas de staff que ainda rodam em Jinja legado (Gastos Extras,
Calculadora de Orçamento/Transporte, Gastos Recorrentes, Orçamentos/histórico+PDF, Configuração
de Preços, Avaliação de Casting, Formulários/Comercial) para o painel interno em React, e remover
os 7 itens `external: true` de `navigation.tsx` que hoje abrem essas telas em outra aba. Nenhuma
das 7 áreas tem hoje endpoint `/api/*` — cada uma ganha um núcleo `*_ops.py` puro (extraído da
lógica hoje inline em `routes.py`) reusado pela view Jinja (que continua existindo, estratégia
strangler-fig) e por um par novo de módulos `app/api/<dominio>_read.py`/`_write.py`. No frontend,
cada tela segue o padrão já estabelecido (`AppLayout`, `PageHeader`, `DenseCard`, hooks
TanStack Query em `lib/<dominio>.ts`, página em `pages/<Nome>Page.tsx`). Dado o volume (7 telas
independentes), a implementação é dividida em 7 fatias, uma por User Story do spec, entregues e
verificadas uma de cada vez mas dentro da mesma feature/branch.

## Technical Context

**Language/Version**: TypeScript 5.x / React 18 (frontend); Python 3.12 / Flask (backend)

**Primary Dependencies**: `@manto/ui` (`PageHeader`, `DenseCard`, `Button`, `Input`, `Skeleton`),
`@manto/money`, `@manto/api-client` (`apiFetch` + `apiFetchBlob` para o PDF de orçamento, mesmo
padrão da feature 160), TanStack Query, `react-hook-form` + `zod` para os formulários (padrão já
usado em CRUDs do painel, ex. feature 169/175). Backend reaproveita módulos puros já existentes:
`app/orcamento/pricing.py`, `app/orcamento/transport.py`, `app/orcamento/settings.py`,
`app/orcamento/pdf.py` (`reportlab`). Nenhuma dependência nova em nenhum dos dois lados.

**Storage**: sem mudança de schema — todos os models já existem (`SpecialExpense`,
`RecurringExpense`/`RecurringExpenseEntry`, `EventRating`/`EventSubRating`/`EventRatingVersion`,
`FormResponse`/`FormFieldDefinition`, `OrcamentoHistory`). Nenhuma migration nesta feature.

**Testing**: um script de verificação funcional por fatia (test client Flask contra
`manto_local`/Postgres, requests fora de `app.app_context()`), cobrindo sucesso/erro/RBAC de cada
par read/write novo; `npx tsc --noEmit` + `npm run build` em `frontend/apps/internal` após cada
fatia; conferência visual via `npm run dev:internal` (desktop, já que é painel interno).

**Target Platform**: web — painel interno (`frontend/apps/internal`), staff autenticado.

**Project Type**: web (SPA React + API Flask)

**Performance Goals**: nenhum requisito novo — volumes são baixos (dezenas a poucas centenas de
registros por tela; histórico de orçamento e respostas de formulário já paginam no Jinja legado,
paginação replicada na API).

**Constraints**: zero regressão nas 7 rotas Jinja legadas (paridade obrigatória, strangler-fig —
não decommissionar nesta feature); RBAC replicado como função no início de cada view de API
(nunca decorator Flask-Login); nenhum link/redirecionamento externo pode sobrar em
`navigation.tsx` para as 7 áreas ao final; nomes de módulo novos não podem colidir com módulos
existentes (ex. `app/api/formularios_write.py` já existe para o fluxo público — o par
admin usa `formularios_admin_read.py`/`formularios_admin_write.py`); `ensure_recurring_entries()`
e `recurring_alerts()` (`app/gastos/routes.py:357,395`) têm outros callers — mover com cuidado
para `gastos_ops.py` sem quebrar quem já importa essas funções.

**Scale/Scope**: 4 módulos `*_ops.py` novos (`app/gastos/gastos_ops.py`,
`app/talents/rating_ops.py`, `app/formularios/formularios_ops.py`,
`app/orcamento/quote_ops.py`), 7 pares de módulo de API novos (`gastos_read/write`,
`ratings_read/write`, `formularios_admin_read/write`, `orcamento_read/write` — este último cobre
calculadora + config de preços + histórico/PDF, mesmo blueprint de origem), 7 telas React novas +
1 hook por domínio (`lib/gastos.ts`, `lib/ratings.ts`, `lib/formulariosAdmin.ts`,
`lib/orcamento.ts`), atualização de `navigation.tsx` (remove os 7 `external: true`).

## Constitution Check

*GATE: aprovado. Re-checar após Phase 1.*

- **I. Reutilizar antes de criar** ✅ — `pricing.py`/`transport.py`/`settings.py`/`pdf.py` do
  `app/orcamento` são reusados sem alteração; cada `*_ops.py` novo é extraído da lógica que já
  existe em `routes.py` (não é lógica nova), viram fonte única chamada por Jinja e API.
- **II. Padrões de código** ✅ — todo `*_ops.py` novo com type hints + docstring Google style,
  funções ≤30 linhas (a orquestração de `_process_quote()`, hoje ~420 linhas inline, é quebrada em
  funções menores dentro de `quote_ops.py`); TS estrito sem `any`; formulários tipados com zod.
- **III. API First** ✅ — todos os módulos `app/api/*` novos são JSON puro (`jsonify`/
  `json_error`), RBAC como função chamada no início da view.
- **IV. Não quebrar o que funciona** ✅ — as 7 rotas Jinja continuam funcionando (delegando aos
  `*_ops.py` novos); verificação funcional cobre API nova + paridade de comportamento.
- **V. UI/UX com feedback** ✅ — Skeleton/loading em toda tela nova; `window.confirm()` antes de
  ações destrutivas (excluir gasto/parcela/resposta/campo/item especial); toasts de erro/sucesso
  em pt-BR; nenhum botão sem feedback ao clique.
- **VII. BRL** ✅ — todo valor monetário (gasto, parcela, preço de referência, resultado de
  orçamento) via componente de Input Monetário existente (`@manto/money`), nunca reinventado.
- **VIII. Mobile-first** — n/a diretamente (painel interno, não superfície pública), mas
  conferido em viewport mobile por consistência com o resto do painel antes de "pronto".
- **IX. Movimento com propósito** ✅ — transições de lista/formulário/filtros via Framer Motion,
  respeitando `useReducedMotion()`.

## Project Structure

### Documentation (this feature)

```text
specs/177-migracao-ferramentas-react/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── gastos/
│   ├── routes.py              # Jinja legado — passa a chamar gastos_ops.py
│   └── gastos_ops.py          # NOVO — CRUD de SpecialExpense + RecurringExpense/Entry
├── talents/
│   ├── routes.py              # Jinja legado — passa a chamar rating_ops.py p/ avaliacoes()
│   ├── talent_ops.py          # existente, intocado (outro domínio)
│   └── rating_ops.py          # NOVO — filtros/distribuição/modo anônimo de EventRating
├── formularios/
│   ├── routes.py              # Jinja legado — passa a chamar formularios_ops.py (lado staff)
│   └── formularios_ops.py     # NOVO — associar/vincular/buscar resposta + editor de campos
├── orcamento/
│   ├── routes.py              # Jinja legado — passa a chamar quote_ops.py
│   ├── pricing.py             # existente, reusado sem mudança
│   ├── transport.py           # existente, reusado sem mudança
│   ├── settings.py            # existente, reusado sem mudança (config de preços)
│   ├── pdf.py                 # existente, reusado sem mudança
│   └── quote_ops.py           # NOVO — orquestração de _process_quote() extraída
└── api/
    ├── gastos_read.py         # NOVO
    ├── gastos_write.py        # NOVO
    ├── ratings_read.py        # NOVO
    ├── ratings_write.py       # NOVO
    ├── formularios_admin_read.py   # NOVO (não colide com formularios_write.py público)
    ├── formularios_admin_write.py  # NOVO
    ├── orcamento_read.py      # NOVO — calculadora, config de preços (GET), histórico
    └── orcamento_write.py     # NOVO — calcular/salvar orçamento, config de preços (POST), PDF/e-mail

frontend/apps/internal/src/
├── lib/
│   ├── gastos.ts               # NOVO — hooks Gastos Extras + Gastos Recorrentes
│   ├── ratings.ts               # NOVO — hooks Avaliação de Casting
│   ├── formulariosAdmin.ts      # NOVO — hooks Formulários (lado staff)
│   ├── orcamento.ts             # NOVO — hooks Calculadora + Config de Preços + Histórico/PDF
│   └── navigation.tsx           # editado — remove os 7 `external: true`, liga rotas reais
└── pages/
    ├── GastosExtrasPage.tsx           # NOVO (US1)
    ├── OrcamentoCalculadoraPage.tsx   # NOVO (US2)
    ├── GastosRecorrentesPage.tsx      # NOVO (US3)
    ├── OrcamentoHistoricoPage.tsx     # NOVO (US4)
    ├── OrcamentoConfigPrecosPage.tsx  # NOVO (US5)
    ├── AvaliacaoCastingPage.tsx       # NOVO (US6)
    └── FormulariosAdminPage.tsx       # NOVO (US7)
```

**Structure Decision**: segue exatamente o padrão de todas as fatias 145-176 (rota API fina →
`*_ops.py` → models; página React em `pages/`, hooks em `lib/<dominio>.ts`). Nenhuma estrutura
nova é introduzida — a única particularidade é agrupar 2 telas por domínio de `*_ops.py`
(Gastos Extras + Gastos Recorrentes em `gastos_ops.py`; Calculadora + Config de Preços +
Histórico/PDF em `quote_ops.py`/`orcamento_read/write.py`) porque compartilham o mesmo blueprint
Jinja de origem e não há núcleo de negócio a duplicar entre eles.

## Complexity Tracking

*Nenhuma violação da constituição — seção não se aplica.*
