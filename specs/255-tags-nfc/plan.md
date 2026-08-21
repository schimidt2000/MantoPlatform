# Implementation Plan: Tags NFC nas peças 3D com página pública por código

**Branch**: `255-tags-nfc` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/255-tags-nfc/spec.md`

## Summary

Cada luminária 3D entregue num show carrega uma tag NFC com URL imutável (`app.mantoproducoes.com.br/nfc/<código>`). O servidor decide o conteúdo a cada acesso: v1 é uma página pública mobile-first com animação de portal e link do Instagram; o payload já traz o gancho `campaign: null` para campanhas futuras. Códigos nascem automaticamente quando um show ganha um presente 3D de item habilitado (prefixo NFC no acervo), um por unidade, cada um com número sequencial humano por produto (rótulo físico de logística); o ERP ganha uma tela de gestão (lote, associação a evento, ativar/desativar — sem exclusão).

## Technical Context

**Language/Version**: Python 3.11 (Flask + SQLAlchemy) backend; TypeScript + React 18 (Vite) frontend

**Primary Dependencies**: Flask, SQLAlchemy, Alembic (migrations manuais); React, TanStack Query, Tailwind CSS, shadcn/ui (`@manto/ui`), Framer Motion, `@manto/api-client` (`apiFetch`/`assetUrl`)

**Storage**: PostgreSQL (produção Railway; verificação contra cópia `manto_local`)

**Testing**: script `scripts/verify_255_nfc.py` contra `manto_local` (padrão verify_* do projeto — login só pela API); `npx tsc --noEmit` em `apps/public` e `apps/internal`; conferência mobile no browser

**Target Platform**: Web — página pública consumida em smartphones (iPhone/Android via NFC); admin no ERP desktop

**Project Type**: Web app (SPA desacoplada — Flask API JSON + 3 SPAs React servidas por `frontend/server.js`)

**Performance Goals**: página pública < 3s em 4G (SC-001) — payload público é 1 lookup indexado + bundle já otimizado da vitrine

**Constraints**: URL gravada é imutável/eterna; página pública sem login; 320–430px sem rolagem horizontal; `useReducedMotion` obrigatório; nenhum dado pessoal no payload público v1

**Scale/Scope**: dezenas de tags/mês (1–2 shows/semana × unidades); 1 tabela nova, 1 coluna nova, ~4 endpoints, 1 página pública, 1 tela admin

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após Phase 1 — sem violações.*

| Princípio | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | RBAC reusa `require_3d_access`/`has_3d_access` de `app/api/impressoes3d_read.py`; cliente do evento reusa `client_of_event` de `app/api/agenda_read.py`; serving público reusa o mecanismo `CADASTRO_PREFIX` de `frontend/server.js`; mídia via `assetUrl()`; UI com `@manto/ui` |
| II. Padrões de código | Type hints + docstrings Google style; TS estrito sem `any`; constantes UPPER_CASE (`NFC_SUFFIX_ALPHABET`, `MANTO_INSTAGRAM_URL`) |
| III. API First / camadas | Lógica em `app/impressoes3d/nfc_ops.py` (puro, sem `flask.request`); rotas só RBAC + serialização; zero Jinja |
| IV. Não quebrar o que funciona | Gancho em `add_event_gift`/`update_event_gift` é aditivo (item sem prefixo = comportamento idêntico ao atual); migration só adiciona; `tsc` + verify antes de cada commit |
| V. UI/UX com feedback | TanStack Query em tudo; botões com estado de loading; toasts pt-BR |
| VI–VIII. SDD / Living Spec / Test-First | Esteira completa; `verify_255_nfc.py` especificado antes do núcleo em tasks.md |
| X. Mobile-first público | Página `/nfc` desenhada para 320–430px, toque ≥ 44px, conferida em viewport mobile |
| XI. Framer Motion | Animação de portal com `useReducedMotion()` |
| XII. Combobox | Associação de evento usa combobox pesquisável existente do ERP |
| Stack | Migration Alembic manual (`down_revision = "f3a9c15d8b42"`); sem segredos novos |

## Project Structure

### Documentation (this feature)

```text
specs/255-tags-nfc/
├── plan.md              # Este arquivo
├── research.md          # Phase 0 — decisões técnicas e alternativas
├── data-model.md        # Phase 1 — entidades e regras
├── quickstart.md        # Phase 1 — roteiro de validação
├── contracts/
│   └── nfc-api.md       # Phase 1 — contrato dos endpoints
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── models.py                      # + NfcTag; + Acervo3DItem.nfc_prefix
├── constants.py                   # + MANTO_INSTAGRAM_URL, alfabeto/tamanho do sufixo
├── impressoes3d/
│   ├── impressoes3d_ops.py        # add_event_gift/update_event_gift chamam o sync de tags
│   └── nfc_ops.py                 # NOVO — núcleo puro: geração, sync, resolução, serialização
└── api/
    ├── __init__.py                # importa os módulos novos
    ├── nfc_read.py                # NOVO — GET /api/nfc/<code> (público) + GET /api/3d/nfc (RBAC)
    └── nfc_write.py               # NOVO — POST /api/3d/nfc/lote, PATCH /api/3d/nfc/<id>

migrations/versions/
└── <nova>_nfc_tags.py             # nfc_tags + acervo_3d_items.nfc_prefix (down_revision f3a9c15d8b42)

frontend/
├── server.js                      # + NFC_PREFIX "/nfc" (mesmo mecanismo de CADASTRO_PREFIX)
├── apps/public/src/
│   ├── App.tsx                    # isCadastroSurface → superfícies de raiz incluem /nfc
│   ├── lib/nfc.ts                 # NOVO — tipos + useQuery do payload público
│   └── pages/NfcPage.tsx          # NOVO — portal animado, mobile-first
└── apps/internal/src/
    ├── App.tsx                    # + rota /3d/tags
    ├── lib/navigation.tsx         # + entrada "Tags NFC" na seção 3D
    ├── lib/nfc.ts                 # NOVO — tipos + queries/mutations admin
    ├── lib/impressoes3d.ts        # tipo do acervo ganha nfc_prefix
    └── pages/Tags3DPage.tsx       # NOVO — lista, lote, associar evento, ativar/desativar

scripts/
└── verify_255_nfc.py              # NOVO — verificação funcional contra manto_local

docs/                              # 01, 02, 03 atualizados ao final (regra de documentação viva)
```

**Structure Decision**: web app existente (monorepo Flask + 3 SPAs). A feature só adiciona módulos nas camadas já estabelecidas — nenhum serviço, app ou pacote novo.

## Complexity Tracking

Sem violações da constituição — tabela vazia.
