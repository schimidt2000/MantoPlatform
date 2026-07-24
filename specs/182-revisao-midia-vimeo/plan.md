# Implementation Plan: Revisão de Mídia estilo Vimeo

**Branch**: `182-revisao-midia-vimeo` | **Date**: 2026-07-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/182-revisao-midia-vimeo/spec.md`

## Summary

Redesenhar a tela `frontend/apps/internal/src/pages/RevisaoAssetPage.tsx` (rota `/revisao/:spaceId/asset/:assetId`)
como um layout imersivo de 2 colunas (player 70% + painel de revisão 30% em widescreen, empilhado em
mobile), com um player de vídeo customizado (scrubber com marcadores de comentário, controles de
velocidade, atalhos de teclado, tempo formatado), comentários indexados por timestamp com captura
automática e seek ao clicar, seletor de versões no cabeçalho, e um novo status de aprovação
persistente por material (`em_revisao` | `aprovado` | `precisa_ajustes` | `rejeitado`). O backend
ganha só o mínimo aditivo: uma coluna nova em `ReviewAsset`, uma migration manual, duas funções em
`review_ops.py` e um endpoint de API — sem tocar `app/revisao/routes.py` (Jinja legado) nem
`frontend/apps/public`/`frontend/apps/portal`.

## Technical Context

**Language/Version**: Python 3.x (Flask) + TypeScript 5.x (React 18, Vite)

**Primary Dependencies**: Flask-SQLAlchemy, Flask-Migrate (Alembic) no backend; React, TanStack Query,
Tailwind CSS, Framer Motion, `@manto/ui` (design system interno, papel equivalente ao shadcn/ui do
projeto — ver Constitution Check), `@manto/api-client` no frontend. Nenhuma biblioteca nova de player
de vídeo — o elemento `<video>` HTML5 nativo, controlado via `ref` + eventos (`timeupdate`,
`loadedmetadata`, `play`, `pause`), cobre 100% dos requisitos (scrubber custom, velocidade,
atalhos). Ver `research.md`.

**Storage**: PostgreSQL (produção via Railway; verificação sempre contra `manto_local`, cópia local).

**Testing**: Script Python com Flask test client (padrão do projeto, requests fora de `app_context`)
contra `manto_local` para os endpoints novos/alterados; Playwright para o fluxo e2e da tela
(`frontend/apps/internal/e2e/revisao-asset.spec.ts`, novo — não existe spec de revisão hoje).

**Target Platform**: Web (SPA), staff autenticado — desktop widescreen e mobile (Princípio VIII).

**Project Type**: Web application (monorepo já existente: `app/` Flask + `frontend/apps/internal` React).

**Performance Goals**: Interações do player (play/pause, seek, troca de velocidade) devem refletir na
UI em menos de um frame perceptível (sem chamada de rede); troca de versão/status usa TanStack Query
com invalidação direcionada (não recarrega a página).

**Constraints**: Zero regressão nos fluxos de áudio/imagem/PDF já existentes; zero alteração em
`app/revisao/routes.py`, `frontend/apps/public`, `frontend/apps/portal`; RBAC de status reaproveita
`review_ops.can_manage` (sem papel novo).

**Scale/Scope**: Uma tela (`RevisaoAssetPage.tsx`) decomposta em ~5 componentes novos + 1 hook de
player + 1 coluna nova no banco + 1 endpoint de API novo. Sem migração de dados existentes além do
`server_default` da coluna nova.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: PASS. Reusa `review_ops.can_manage`/`can_view`, hooks existentes em
  `lib/revisao.ts` (estendidos, não duplicados), `@manto/ui` (`Button`, `Card`, `Skeleton`) e
  `@manto/api-client` (`apiFetch`, `assetUrl`). Componentes novos (badge de status, scrubber, seletor
  de versão) não existem ainda no design system — criados uma vez em `apps/internal`, não duplicados
  por tela.
- **II. Padrões de tipagem**: PASS. Novo endpoint com type hints + docstring Google style; hooks/
  componentes novos com interfaces TS explícitas, zero `any`.
- **III. Arquitetura em camadas**: PASS. Endpoint novo em `app/api/revisao_write.py` só valida RBAC e
  serializa; regra de negócio (mudar status, resetar no replace) vive em `review_ops.py`. Jinja legado
  não ganha a feature (fora de escopo, conforme spec) e continua funcionando sem o campo de status
  sendo obrigatório na leitura (default cobre o Jinja também, já que lê o mesmo `ReviewAsset`).
- **IV. Não quebrar o que funciona**: PASS. `tsc --noEmit` + `npm run build` antes de qualquer commit;
  verificação funcional Python contra `manto_local`; fluxos de áudio/imagem/PDF cobertos pelos mesmos
  testes para garantir zero regressão.
- **V. UI/UX com feedback**: PASS. Botões de status usam `loading` do `Button` (`@manto/ui`) durante a
  mutation; toggle de resolvido e troca de versão já seguem o padrão; erros via mensagem amigável
  (reaproveita `ApiRequestError`).
- **VI. Planejar antes de codar**: em andamento — este é o próprio plano.
- **VII. Valores monetários**: N/A (feature não lida com dinheiro).
- **VIII. Mobile-first**: PASS. FR-011 exige empilhamento em 1 coluna; verificação em viewport mobile
  é portão de qualidade explícito antes de "pronto".
- **IX. Movimento com propósito**: PASS. Transição de layout entre versões/status e abertura do
  seletor de versão usam Framer Motion (150–350ms, respeitando `useReducedMotion()`).

Nenhuma violação — não há necessidade de preencher "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/182-revisao-midia-vimeo/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── revisao-status.md # Contrato do endpoint novo (PATCH status)
└── tasks.md              # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── models.py                     # ReviewAsset ganha coluna `status` (Enum/String)
├── revisao/
│   ├── routes.py                 # INTOCADO (Jinja legado)
│   └── review_ops.py             # + set_asset_status(), + reset no replace_asset()
└── api/
    ├── revisao_read.py           # _asset_summary() passa a incluir "status"
    └── revisao_write.py          # + endpoint PATCH /revisao/asset/<id>/status

migrations/
└── <novo arquivo>_add_review_asset_status.py   # upgrade/downgrade manuais

frontend/apps/internal/src/
├── lib/
│   └── revisao.ts                # + campo `status` nos types, + useUpdateAssetStatus()
├── components/
│   └── revisao/                  # NOVO subdiretório de componentes só desta tela
│       ├── VideoPlayer.tsx       # player custom (controles, velocidade, atalhos, tempo)
│       ├── VideoScrubber.tsx     # barra de progresso + marcadores de comentário
│       ├── CommentFeed.tsx       # feed ordenado por timestamp + filtro Todos/Pendentes
│       ├── VersionSelector.tsx   # pills/dropdown de versão no cabeçalho
│       └── StatusBadge.tsx       # badge + botões de ação de status
└── pages/
    └── RevisaoAssetPage.tsx      # reescrita: layout 2 colunas, orquestra os componentes acima

frontend/apps/internal/e2e/
└── revisao-asset.spec.ts         # NOVO — cobre player, comentário por timestamp, versão, status
```

**Structure Decision**: Monorepo existente reaproveitado como está. Nenhum diretório novo em nível de
app — só um subdiretório `components/revisao/` dentro de `frontend/apps/internal` (primeira tela do
app a extrair componentes de página em subpasta própria; padrão local, não altera a convenção global
do design system compartilhado `@manto/ui`, que continua reservado a componentes reusados por
múltiplas telas).

## Complexity Tracking

*Sem violações da constituição — seção não aplicável.*
