# Implementation Plan: Migração da Agenda/Eventos — fatia de leitura (145, US1)

**Branch**: `145-migracao-agenda-eventos` (criado no implement) | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/145-migracao-agenda-eventos/spec.md`

## Summary

Cobre **apenas a User Story 1 (leitura)**: expor em JSON o que as views Jinja `agenda`,
`agenda_day` e a metade GET de `event_detail` já mostram, e recriar essas telas em
`frontend/apps/internal` só para exibição — sem nenhuma ação de escrita. As fatias de escrita
(US2–US5) recebem seu próprio ciclo depois.

A parte difícil e arriscada não é a UI — é a **serialização fiel do evento com o RBAC
financeiro correto**. A view `event_detail` (GET) monta ~15 blocos, vários gated por papel
(`show_comercial`, `show_financeiro`, superadmin) e com KPIs agregados por **grupo comercial**
(principal + satélites), não pelo evento isolado. A API não pode serializar campos financeiros
para papéis que não os veriam. Estratégia (Princípio I): montar esses dados num **serviço de
leitura único** (`app/api/agenda_read.py`); onde a lógica já existe e é estável
(`_group_events`, `_build_events_from_db`), o serviço a **chama**, não a reescreve.

## Technical Context

**Language/Version**: Python 3.11 (backend) + TypeScript/React (frontend), como na Fundação.

**Primary Dependencies**: nenhuma nova — reusa `@manto/ui`, `@manto/api-client`, `@manto/money`,
TanStack Query, Framer Motion, react-router (já instalados na feature 144).

**Storage**: PostgreSQL (`manto_local` para verificação). Nenhuma mudança de schema.

**Testing**: script Python com test client contra `manto_local`, comparando a resposta JSON da
API com os dados que a view Jinja produz, **por papel** (superadmin, comercial, casting sem
financeiro) — o coração da verificação desta fatia. Frontend: `tsc --noEmit` + `vite build`.

**Target Platform**: `apps/internal` (staff autenticado), consumido em `beta`.

**Project Type**: web app desacoplado (monorepo já existente).

**Performance Goals**: a agenda hoje serve do banco (sem chamada de rede); manter isso — a API
lê do banco, sem disparar sync. Sem meta numérica nova.

**Constraints**: não tocar as views Jinja (coexistência, FR-009); RBAC idêntico ao atual;
valores pt-BR via `@manto/money`; `prefers-reduced-motion` respeitado.

**Scale/Scope**: 3 telas de leitura (agenda lista/calendário, dia, detalhe do evento) + 2–3
endpoints JSON. Sem escrita.

## Constitution Check

- **I. Reutilizar antes de criar**: o serviço de leitura chama `_group_events`,
  `_build_events_from_db` e a lógica de KPI existentes; não duplica. Onde extrair ajudar, o
  helper puro é reusado TAMBÉM pela view Jinja (como o dashboard na 144).
- **III. API First**: endpoints `/api/agenda*` e `/api/events/<id>` retornam só JSON.
- **IV. Não quebrar o que funciona**: nenhuma view Jinja muda de comportamento; a verificação
  compara a API com o Jinja para garantir paridade.
- **V. UI/UX + feedback**: skeleton/erro/sucesso via TanStack Query (a leitura não tem botões
  de ação nesta fatia, então "botão morto" ainda não se aplica).
- **VII. Monetário pt-BR**: todo valor via `@manto/money`.
- **VIII. Mobile-first**: agenda/evento são muito usados no celular pela equipe — conferir
  viewport mobile.
- **IX. Movimento**: transições de troca de dia/evento e entrada de listas via Framer Motion.

Nenhuma violação.

## Project Structure

### Documentation (this feature)

```text
specs/145-migracao-agenda-eventos/
├── plan.md, spec.md
├── research.md          # reuso vs. extração, shape de serialização, RBAC, recorte por mês
├── data-model.md        # shape JSON de EventoResumo (agenda) e EventoDetalhe (leitura, por papel)
├── contracts/
│   └── api-conventions.md   # endpoints desta fatia
└── checklists/requirements.md
```

### Source Code

```text
app/
├── api/
│   ├── agenda_read.py    # NOVO: serialize_event_summary / serialize_event_detail (com RBAC),
│   │                     #   reaproveitando _group_events / _build_events_from_db / KPIs
│   ├── agenda.py         # NOVO: GET /api/agenda, /api/agenda/day/<date>, /api/events/<id>
│   └── __init__.py       # registra o módulo de rotas
└── calendar/routes.py    # inalterado em comportamento (no máximo, extrair helper puro reusado)

frontend/apps/internal/src/
├── pages/AgendaPage.tsx        # lista/calendário + navegação de mês; abrir dia
├── pages/EventDetailPage.tsx   # exibição das seções (elenco, financeiro gated, contrato, logs...)
├── lib/agenda.ts               # hooks TanStack Query + tipos
└── (rota /agenda e /events/:id no App.tsx, sob RequireAuth)
```

## Design Decisions

1. **Serviço de leitura único (`app/api/agenda_read.py`)**: `serialize_event_summary(event)`
   (agenda) e `serialize_event_detail(event, user, impersonate)` (página do evento, aplicando
   RBAC). KPIs por grupo comercial e cobrança são montados a partir das MESMAS fontes
   (`_group_events`, `SpecialExpense`, acréscimos/BV) usadas pela view.

2. **RBAC na serialização, não só na UI (FR-003)**: calcula
   `show_comercial`/`show_financeiro`/`show_ensaio`/superadmin com a MESMA lógica da view
   (incluindo impersonação) e só inclui os blocos que o papel veria. Bloco financeiro (venda,
   KPIs, cobrança, contrato) sob `show_comercial`; pagamentos e reembolsos sob
   `show_financeiro`. Nunca serializa valor financeiro para papel sem permissão.

3. **Agenda lê do banco, nunca dispara sync**: `GET /api/agenda?ym=YYYY-MM` usa
   `_build_events_from_db`. O `force_sync` NÃO é exposto nesta fatia (sync manual é escrita →
   US5). Mantém a abertura instantânea de hoje.

4. **Disponibilidade de talento fica fora da leitura**: `availability` existe para o seletor de
   casting (escrita) — não é dado exibido. Entra na US2.

5. **Verificação = paridade com o Jinja, por papel (SC-001/SC-003)**: o script cria usuários
   efêmeros (superadmin; comercial; casting-sem-financeiro), chama `/api/events/<id>` e afirma:
   (a) superadmin recebe os blocos financeiros com os mesmos totais que a view calcula;
   (b) casting-sem-financeiro NÃO recebe nenhum campo de venda/pagamento/reembolso; (c) os
   totais (custo, comissão, recebido, reembolso pendente) batem com o cálculo da view. Também
   `GET /api/agenda` retorna os mesmos ids de evento que `_build_events_from_db`.

## Complexity Tracking

*Sem violações — tabela não aplicável.*
