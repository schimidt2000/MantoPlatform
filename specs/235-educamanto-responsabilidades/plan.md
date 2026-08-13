# Implementation Plan: EducaManto por responsabilidades — fim dos pacotes por nível

**Branch**: `235-educamanto-responsabilidades` | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/235-educamanto-responsabilidades/spec.md`

## Summary

Substituir o modelo "pacote por nível" (Master/Intermediário/Econômica) por **musical + responsabilidades**: a tabela de pacotes é renomeada para musicais (preservando ids), cada musical carrega elenco, produção, ensaios (≥2) e custos únicos de som completo, iluminação completa, cenário e alimentação; a calculadora ganha quatro alternadores Manto × contratante que ligam/desligam blocos de custo e derivam a equipe técnica pela matriz dos 4 casos (sonoplasta fixo). A geração passa a **recalcular tudo no servidor** e congela um snapshot v2 multi-configuração (várias páginas, inclusive musicais diferentes). O PDF é reescrito por responsabilidade (o que levamos / mínimo exigido), com avisos fixos, quantidades da equipe, 5% à vista calculado e trecho da contratação Manto embutida — que reusa `app.orcamento.quote_ops.calculate_quote` como fonte única, somando por duração com NF sobre o total. Transporte: caminhão R$ 800 dentro de SP; fora de SP, 2 vans (1 c/ carretinha) × dias + adicional por pessoa único. Breakdown/custos só para superadmin (corte no servidor). Telas Jinja do EducaManto desligadas com redirect para o React.

## Technical Context

**Language/Version**: Python 3.12 (Flask + SQLAlchemy + Alembic) · TypeScript 5 (React 18 + Vite)

**Primary Dependencies**: Flask API JSON estrita (`/api/*`), reportlab (PDF), TanStack Query, Tailwind + shadcn/ui (`@manto/ui`), `@manto/money`, Framer Motion

**Storage**: PostgreSQL (produção Railway; espelho local `manto_local` para todo teste/verificação)

**Testing**: scripts de verificação por feature (`verify_*.py`) contra `manto_local` via `scripts/db/run-local.ps1`; `npx tsc --noEmit` em `frontend/apps/internal`

**Target Platform**: Web interna (SPA `apps/internal` + API Flask), desktop-first (tela interna)

**Project Type**: Web application (frontend React + backend Flask já existentes — monorepo)

**Performance Goals**: recálculo da calculadora percebido como imediato (debounce 300 ms + resposta < 1 s no uso interno)

**Constraints**: valores congelados = calculados no servidor (fim da confiança no payload do cliente); snapshots antigos continuam renderizando idênticos; nenhum breakdown vaza para papéis não-superadmin (nem em API); valores provisórios (técnicos, áreas X/Y) isolados em um único módulo de constantes

**Scale/Scope**: 7 musicais, ~5 papéis de acesso, dezenas de orçamentos/mês; ~6 arquivos backend + 5 telas/módulos frontend tocados; 1 migração de dados

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio | Avaliação |
|---|---|
| I. Reutilizar antes de criar | **PASS** — contratação Manto reusa `calculate_quote` (função pura já existente) sem cópia; tarifas de transporte seguem em `orcamento/settings`; componentes de equipe/acréscimos extraídos da OrcamentoCalculadoraPage para módulos compartilhados (uma fonte, duas telas); `@manto/money`, `GoogleAddressInput` e hooks existentes reaproveitados. |
| II. Padrões Python/TS | **PASS** — novos `*_ops.py` puros com type hints/docstrings; TS estrito sem `any`; constantes provisórias em UPPER_CASE num módulo único. |
| III. API-first / camadas | **PASS (melhora o sistema)** — remove as últimas views Jinja do EducaManto; rotas novas só JSON; regra de negócio em `pricing_ops`/`quote_ops`; o servidor passa a recalcular na geração (hoje confia no cliente — dívida corrigida). |
| IV. Não quebrar o que funciona | **PASS** — migração renomeia tabela preservando ids; snapshots antigos têm renderização própria (v1) intocada; verificação numérica dos musicais migrados contra os pacotes Master atuais; testes contra `manto_local`. |
| V. UX consistente com feedback | **PASS** — tooltips nos blocos de responsabilidade; estados loading/erro TanStack; nenhum botão morto; valores preservados em erro. |
| VI. Full path SDD | **PASS** — specify → clarify → plan → checklist → tasks → analyze → implement. |

Nenhuma violação a justificar (Complexity Tracking vazio).

## Project Structure

### Documentation (this feature)

```text
specs/235-educamanto-responsabilidades/
├── plan.md              # Este arquivo
├── research.md          # Phase 0 — decisões técnicas
├── data-model.md        # Phase 1 — entidades, snapshot v2, migração
├── quickstart.md        # Phase 1 — roteiro de validação
├── contracts/
│   └── educamanto-endpoints.md   # Phase 1 — contrato da API
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── educamanto/
│   ├── musical_ops.py        # NOVO — CRUD de musicais (substitui package_ops.py)
│   ├── pricing_ops.py        # REESCRITO — responsabilidades, matriz técnica, transporte novo
│   ├── quote_ops.py          # REESCRITO — snapshot v2 multi-config, recálculo no servidor
│   ├── pdf.py                # REESCRITO — página por configuração, seções por responsabilidade
│   ├── pdf_textos.py         # NOVO — textos por responsabilidade + avisos + PROVISORIOS
│   └── routes.py             # ENXUGADO — só redirects 302 → React (views Jinja removidas)
├── api/
│   ├── educamanto_read.py    # ATUALIZADO — musicais, calcular (corte RBAC no servidor)
│   └── educamanto_write.py   # ATUALIZADO — gerar (recalcula), CRUD musicais
├── models.py                 # EducaMantoMusical/Item (rename + campos novos)
└── orcamento/                # INTOCADO (fonte única reusada: quote_ops, transport, settings)

migrations/versions/
└── xxxx_educamanto_musicais.py   # rename tabelas + campos novos + poda de níveis

frontend/apps/internal/src/
├── pages/
│   ├── EducaMantoCalculadoraPage.tsx   # REESCRITA — responsabilidades, páginas, contratação
│   ├── EducaMantoMusicaisPage.tsx      # NOVA — lista de musicais (substitui PackagesPage)
│   ├── EducaMantoMusicalFormPage.tsx   # NOVA — form do musical (substitui PackageFormPage)
│   └── EducaMantoHistoricoPage.tsx     # AJUSTADA — snapshot v2 no dialog "Ver"
├── components/orcamento/
│   ├── PerformersEditor.tsx            # NOVO — extraído da OrcamentoCalculadoraPage
│   └── AcrescimosEditor.tsx            # NOVO — extraído da OrcamentoCalculadoraPage
└── lib/educamanto.ts                   # ATUALIZADO — tipos/hooks do contrato novo

templates/educamanto/                   # REMOVIDO (views Jinja desligadas)
```

**Structure Decision**: monorepo existente (Flask `app/` + React `frontend/apps/internal`). O módulo `app/orcamento` não é alterado — o EducaManto o consome como biblioteca (imports diretos de funções puras), e a parte de UI compartilhada é extraída para `components/orcamento/` consumida pelas duas páginas.
