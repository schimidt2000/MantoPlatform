# Implementation Plan: Reconstrução do Formulário de Cadastro/Edição de Eventos

**Branch**: `184-eventos-formulario-completo` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/184-eventos-formulario-completo/spec.md`

## Summary

Reescrever `frontend/apps/internal/src/pages/EventCreatePage.tsx` em 7 blocos de alta densidade
com paridade total de campos frente ao Jinja legado (`event_create.html`), acrescentar uma nova
tela `EventEditPage.tsx` (`/events/:id/edit`) reaproveitando os mesmos blocos, e um sistema de
validação com destaque em tempo real + auto-scroll ao primeiro erro. O trabalho de UI fica 100%
em `frontend/apps/internal`. O backend ganha apenas duas extensões mínimas: (1) um novo endpoint
`PATCH /api/events/<id>` para atualização em bloco dos campos centrais (não existe hoje — só há
ações pontuais), e (2) um parâmetro opcional `is_signed` no upload de contrato já existente
(`POST /events/<id>/contracts`). Todos os anexos (comprovantes, contrato, reembolso, observação
com foto) reaproveitam os endpoints já existentes da feature 153 — nenhum novo endpoint de anexo é
criado. Nenhuma view/template Jinja legado é tocada.

## Technical Context

**Language/Version**: Python 3.14 (Flask/SQLAlchemy) + TypeScript 5 / React 18 (Vite)

**Primary Dependencies**: Flask, SQLAlchemy · React, TanStack Query, `react-hook-form` + `zod`
(já usados em `EventCreatePage.tsx`), Tailwind CSS, `@manto/ui` (Button, Card, PageHeader,
Skeleton, FileUpload), `@manto/money` (MoneyInput/formatBRL), `@manto/api-client` (apiFetch,
ApiRequestError), Framer Motion

**Storage**: PostgreSQL (produção Railway; verificação sempre contra `manto_local`)

**Testing**: Playwright (`frontend/apps/internal/e2e/`) contra `manto_local`; script de
verificação funcional Flask test client (`scripts/db/verify_184_*.py`, local, não versionado —
ver memória de gotchas de tooling do projeto)

**Target Platform**: Web (staff autenticado, papel COMERCIAL/SUPERADMIN — desktop-first, tela
interna de vendas)

**Project Type**: Web app (frontend React desacoplado + backend Flask API JSON)

**Performance Goals**: Auto-scroll ao primeiro erro em &lt;1s (SC-003); cálculo de % desconto e
geração de título sem chamada de rede (client-side puro)

**Constraints**: Zero alteração em `app/calendar/routes.py`, `app/templates/event_create.html`,
`app/templates/event_detail.html` (FR-028); RBAC do endpoint novo de edição igual ao de criação
(COMERCIAL/SUPERADMIN); nenhuma mudança na semântica dos endpoints de anexo já existentes além da
extensão aditiva `is_signed`

**Scale/Scope**: 1 tela reescrita (`EventCreatePage.tsx`) + 1 tela nova (`EventEditPage.tsx`,
grande parte de UI compartilhada via componentes extraídos) + 1 endpoint novo (`PATCH
/api/events/<id>`) + 1 extensão pontual (`POST /events/<id>/contracts` + `is_signed`) + orquestração
de upload em duas fases na criação

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: `FileUpload` (`@manto/ui`) reaproveitado para o contrato; os
  hooks de anexo já existentes (`lib/eventAttachments.ts` — `useAddPayment`, `useAddContract`,
  `useAddReimbursement`, `useAddObservation`, já usados em `EventDetailPage.tsx`) são reaproveitados
  tanto na criação (fase 2) quanto na edição, em vez de duplicar lógica de upload;
  `useQuickCreateClient()` (já existe, `lib/clientes.ts`) reaproveitado para o cadastro rápido de
  cliente — nenhum endpoint novo para isso. **PASS**.
- **II. Padrões de código**: type hints + docstrings no Python novo (ops de edição); TypeScript
  estrito nos componentes/hooks novos. **PASS** (verificado na implementação).
- **III. Arquitetura em camadas**: novo endpoint fica em `app/api/agenda_write.py` (mesmo módulo
  dos demais endpoints de evento), núcleo de negócio em `app/calendar/event_ops.py` (já existe,
  hoje só cobre logística/confirmação — ganha as funções de atualização em bloco) — nenhuma regra
  de negócio direto na rota. **PASS**.
- **IV. Não quebrar o que funciona**: `POST /api/events` (criação) **não muda de contrato** — o
  único ajuste é o frontend parar de enviar `has_reembolso`/`reembolso_description`/
  `reembolso_amount` no corpo (o reembolso passa a ser criado na fase 2, via o endpoint de
  reembolso já existente, que já aceita descrição+valor+arquivo). Isso é uma mudança de como o
  frontend usa a API, não da API em si. Confirmado por busca no repo: o único chamador desses três
  campos no corpo de `POST /api/events` é `EventCreatePage.tsx`, reescrito nesta mesma feature.
  **PASS, com nota**.
- **V. UI/UX**: todo campo de arquivo usa loading/erro via mutation; ações destrutivas (remover
  comprovante/contrato já salvos, remover personagem com convite aceito) mantêm a mesma
  confirmação/trava já usada hoje; erros de validação nunca apagam o que o vendedor digitou.
  **PASS**.
- **VI. Planejar antes de codar**: esta é a execução do fluxo spec-kit completo. **PASS**.
- **VII. Valores monetários**: todo campo de dinheiro usa `MoneyInput`/`formatBRL` (já usados no
  form atual) — nenhuma máscara nova é inventada. **PASS**.
- **VIII. Mobile-first**: não aplicável — tela interna de staff comercial, não é superfície
  pública. **N/A**.
- **IX. Movimento com propósito**: expansão do mini-form de cliente, transição entre blocos
  condicionais (cortesia, forma de pagamento) e o scroll suave até o erro usam Framer Motion /
  `scrollIntoView({behavior:"smooth"})`, respeitando `prefers-reduced-motion`. **PASS**.

Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/184-eventos-formulario-completo/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api-events.md    # Phase 1 output — contrato do endpoint novo + extensão
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
# Backend — extensão mínima, sem tocar Jinja legado
app/
├── calendar/
│   └── event_ops.py                # + update_event_core() (título/datas/valores/pagamento/
│                                    #   elenco reconciliado/clientes/coordenador/pré-contrato);
│                                    #   reaproveita _validate_event_core / helpers de
│                                    #   app/calendar/routes.py (import local, mesmo padrão já
│                                    #   usado por save_logistics/toggle_confirmed)
└── api/
    └── agenda_write.py             # + PATCH /api/events/<id> (RBAC: COMERCIAL/SUPERADMIN,
                                     #   igual à criação)
                                     # + parâmetro opcional `is_signed` em
                                     #   POST /events/<id>/contracts

# Frontend — 100% do trabalho de UI
frontend/apps/internal/src/
├── lib/
│   ├── eventCreate.ts              # tipos atualizados (characters com role_id opcional,
│                                    #   remove has_reembolso/reembolso_* do payload de criação);
│                                    #   useUpdateEvent() (PATCH)
│   └── eventAttachments.ts         # useAddContract aceita is_signed; reaproveitado sem mudança
│                                    #   estrutural nos demais hooks
├── components/
│   ├── ClientPicker.tsx            # + cadastro rápido inline (useQuickCreateClient)
│   ├── EventFormBlocks/            # NOVO — blocos extraídos e compartilhados entre criação/edição
│   │   ├── ClienteBlock.tsx        # Bloco 1
│   │   ├── DadosEventoBlock.tsx    # Bloco 2
│   │   ├── ElencoBlock.tsx         # Bloco 3 (+ geração automática de título)
│   │   ├── ValoresBlock.tsx        # Bloco 4 (+ calculadora de desconto)
│   │   ├── PagamentoBlock.tsx      # Bloco 5 (+ comprovantes, estado local até salvar)
│   │   ├── ContratoBlock.tsx       # Bloco 6
│   │   └── ObservacoesBlock.tsx    # Bloco 7 (+ tipo foto)
│   └── PendingAttachmentsPanel.tsx # NOVO — status da fase 2 de upload (sucesso/falha/retry)
├── pages/
│   ├── EventCreatePage.tsx         # Reescrito: monta os 7 blocos, fase 1 (POST /api/events) +
│                                   #   fase 2 (loop de anexos)
│   ├── EventEditPage.tsx           # NOVO (/events/:id/edit): mesmos blocos, pré-preenchidos,
│                                   #   PATCH /api/events/:id + anexos via hooks já existentes
│   └── EventDetailPage.tsx         # + botão "Editar" (gated por flags.can_edit_core) no
│                                   #   PageHeader, linkando para /events/:id/edit
├── App.tsx                        # + rota /events/:id/edit
└── e2e/
    └── event-form.spec.ts          # Playwright: criação completa, edição, validação+auto-scroll
```

**Structure Decision**: Web app já existente. Os 7 blocos viram componentes compartilhados
(`EventFormBlocks/`) para reaproveitar 100% da UI entre `EventCreatePage` e `EventEditPage` sem
duplicar JSX — cada bloco recebe valores/handlers via props (padrão controlado), independente de
ser alimentado por `useForm` de criação ou pelos dados carregados de um evento existente.

## Complexity Tracking

*Sem violações da constituição a justificar.*
