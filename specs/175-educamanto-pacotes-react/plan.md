# Implementation Plan: EducaManto — Pacotes e Conteúdos em React

**Branch**: `175-educamanto-pacotes-react` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/175-educamanto-pacotes-react/spec.md`

## Summary

Migrar as 3 telas restantes do EducaManto (gestão de pacotes, gerar orçamento a partir de
pacotes reais persistidos, histórico de orçamentos) do Jinja legado (`app/educamanto/routes.py`)
para o painel interno em React, reaproveitando 100% do núcleo já existente
(`pricing_ops.py`, `pdf.py`, models). A calculadora em si (feature 171) já está em React e
**não muda de UI** — ganha apenas dois novos poderes: persistir/baixar o orçamento (hoje só
calcula) e navegar para o histórico. As telas novas seguem o Design System das features 173/174
(`AppLayout`, `PageHeader`, `DenseCard`, `@manto/ui`). Backend: dois módulos de API novos
(`educamanto_write.py`, extensão de `educamanto_read.py`) chamando um `*_ops.py` novo
(`package_ops.py`) extraído das views Jinja de CRUD de pacote — a view Jinja passa a chamar o
mesmo `package_ops.py`, eliminando a duplicação atual (regra de negócio hoje só existe dentro da
própria view).

## Technical Context

**Language/Version**: TypeScript 5.x / React 18 (frontend); Python 3.12 / Flask (backend)

**Primary Dependencies**: `@manto/ui` (`PageHeader`, `DenseCard`, `Button`, `Input`, `Skeleton`,
`FileUpload` não se aplica aqui), `@manto/money`, `@manto/api-client` (`apiFetch` +
`apiFetchBlob` para o download de PDF, mesmo padrão da feature 160), TanStack Query,
react-hook-form + zod para o formulário de pacote (já usado em outras telas de CRUD do painel,
ex. feature 169). Nenhuma dependência nova.

**Storage**: sem mudança de schema — `EducaMantoPackage`/`EducaMantoItem`/`EducaMantoQuote` já
existem com todos os campos necessários (ver `app/models.py:1090-1200`).

**Testing**: script de verificação funcional com test client Flask contra `manto_local`
(Postgres) cobrindo os 2 módulos de API novos (CRUD de pacote, gerar/baixar orçamento,
histórico) com sucesso/erro/RBAC (`ENSAIO`/`REVENDEDOR_EDUCAMANTO` vs `COMERCIAL` vs
`SUPERADMIN`); `npx tsc --noEmit` + `npm run build` em `frontend/apps/internal`; conferência
visual em viewport desktop e mobile via `npm run dev:internal`.

**Target Platform**: web (desktop + mobile) — painel interno, não é superfície pública, mas
segue o mesmo grid responsivo das demais telas do internal.

**Project Type**: web (SPA React + API Flask)

**Performance Goals**: nenhum requisito novo de performance — volume de pacotes é baixo
(dezenas), histórico já pagina em 300 registros (mesma regra do Jinja legado).

**Constraints**: zero regressão nas rotas Jinja de `app/educamanto` (paridade obrigatória);
RBAC replicado por função (`_require_use`/`_require_packages`/`_require_manage`), nunca
decorator Flask-Login; PDF servido via `apiFetchBlob` (binário), nunca `window.location` cru;
snapshot do orçamento no histórico permanece congelado (não recalculado a partir do pacote
atual).

**Scale/Scope**: 1 módulo de negócio novo (`app/educamanto/package_ops.py`), 1 endpoint de
leitura estendido + 1 novo módulo de escrita (`app/api/educamanto_write.py`), 3 telas React
novas (`EducaMantoPackagesPage`, `EducaMantoPackageFormPage`, `EducaMantoHistoricoPage`) + 1
tela existente ganhando ações (`EducaMantoCalculadoraPage`).

## Constitution Check

*GATE: aprovado. Re-checado após Phase 1 — sem violações.*

- **I. Reutilizar antes de criar** ✅ — `pricing_ops.py`/`pdf.py` reusados sem alteração;
  `package_ops.py` é extraído da view Jinja (`create_package`/`edit_package`/`duplicate_package`/
  `delete_package`) para virar a fonte única, chamada pela view Jinja e pela API.
- **II. Padrões de código** ✅ — `package_ops.py` com type hints/docstring Google style; TS
  estrito sem `any`, formulário tipado com zod.
- **III. API First** ✅ — `app/api/educamanto_write.py` é JSON puro; RBAC como função.
- **IV. Não quebrar o que funciona** ✅ — rotas Jinja de `app/educamanto/routes.py` continuam
  funcionando (agora delegando a `package_ops.py`); verificação funcional cobre os dois lados.
- **V. UI/UX com feedback** ✅ — Skeleton nas 3 telas novas; confirmação (`window.confirm`,
  padrão já usado no projeto) antes de excluir pacote; toasts de erro/sucesso amigáveis.
- **VII. BRL** ✅ — todo campo monetário do formulário de pacote usa o componente de Input
  Monetário existente (`@manto/money`), nunca reinventado.
- **VIII. Mobile-first** — n/a diretamente (superfície interna, não pública), mas telas
  conferidas em viewport mobile antes de "pronto" por consistência com o resto do painel.
- **IX. Movimento com propósito** ✅ — transições de lista/formulário via Framer Motion,
  respeitando `useReducedMotion()`.

## Project Structure

### Documentation (this feature)

```text
specs/175-educamanto-pacotes-react/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── educamanto/
│   ├── routes.py          # Jinja legado — passa a chamar package_ops.py (sem duplicar lógica)
│   ├── package_ops.py      # NOVO — núcleo de negócio de CRUD de pacote (extraído de routes.py)
│   ├── pricing_ops.py      # existente, reusado sem mudança
│   └── pdf.py              # existente, reusado sem mudança
└── api/
    ├── educamanto_read.py   # existente — ganha GET /packages/<id>, GET /historico
    └── educamanto_write.py  # NOVO — POST/PATCH/DELETE pacote, POST duplicar, POST orçamento/gerar

frontend/apps/internal/src/
├── lib/
│   └── educamanto.ts        # existente — ganha hooks de CRUD de pacote + histórico + gerar orçamento
└── pages/
    ├── EducaMantoCalculadoraPage.tsx   # existente — ganha ação "Gerar orçamento" (download PDF)
    ├── EducaMantoPackagesPage.tsx       # NOVO — lista + ações (editar/duplicar/excluir)
    ├── EducaMantoPackageFormPage.tsx    # NOVO — criar/editar pacote + itens
    └── EducaMantoHistoricoPage.tsx      # NOVO — histórico com filtros
```

**Structure Decision**: segue exatamente o padrão de todas as fatias 145-174 (rota API fina →
`*_ops.py` → models; página React em `pages/`, hooks em `lib/<dominio>.ts`). Nenhuma estrutura
nova é introduzida.

## Complexity Tracking

*Nenhuma violação da constituição — seção não se aplica.*
