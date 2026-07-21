# Tasks: Migração da Agenda/Eventos — fatia de leitura (145, US1)

**Input**: Design docs em `/specs/145-migracao-agenda-eventos/` (spec, plan, research,
data-model, contracts, quickstart)

**Escopo**: só a User Story 1 (leitura). US2–US5 (escrita) têm seu próprio `tasks.md` depois.

**Sugestão de execução em 2 incrementos** (cada um verificável e commitável isolado):
**Incremento A = Agenda** (mais simples), **Incremento B = Detalhe do evento** (a serialização
com RBAC — a parte sensível). Recomendado parar e validar A antes de B.

## Format: `[ID] [P?] [Story] Description`

---

## Incremento A — Agenda (lista/calendário + dia)

### Backend
- [X] T001 [US1] Criar `app/api/agenda_read.py` com `serialize_event_summary(event)` conforme
      `data-model.md` (EventoResumo), reusando `parse_event_type`/`parse_characters`.
- [X] T002 [US1] Criar `app/api/agenda.py`: `GET /api/agenda?ym=YYYY-MM` (usa
      `_build_events_from_db`, retorna `{ym, events, by_day}`) e `GET /api/agenda/day/<date>`
      (400 em data inválida). Registrar o módulo em `app/api/__init__.py`.

### Frontend
- [X] T003 [P] [US1] `frontend/apps/internal/src/lib/agenda.ts`: tipos EventoResumo + hooks
      TanStack Query (`useAgenda(ym)`, `useAgendaDay(date)`).
- [X] T004 [US1] `frontend/apps/internal/src/pages/AgendaPage.tsx`: lista/calendário por mês,
      navegação prev/next mês, abrir dia; skeleton/erro; transição Framer Motion na troca de
      mês (respeita `prefers-reduced-motion`).
- [X] T005 [US1] Ligar rota `/agenda` no `App.tsx` (sob `RequireAuth`) + link no
      DashboardPage; conferir mobile.

### Verificação A
- [X] T006 [US1] `scripts/db/verify_145_agenda_read.py`: `GET /api/agenda?ym=...` retorna os
      mesmos ids que `_build_events_from_db`; 401 sem sessão. `tsc`/`build` limpos.

**Checkpoint A**: agenda em React lê e exibe igual ao Jinja — parar e validar antes de B.

---

## Incremento B — Detalhe do evento (leitura, com RBAC)

### Backend
- [ ] T007 [US1] Ler `event_detail.html` para inventariar as seções/campos exibidos por bloco
      (evitar regressão silenciosa — Edge Case).
- [ ] T008 [US1] `serialize_event_detail(event, user, impersonate)` em `agenda_read.py`: blocos
      sempre presentes (event, elenco, logs, observations, ratings, feedbacks) + blocos
      financeiros SÓ conforme papel (`show_comercial`: venda/kpi/cobranca/contratos/expenses;
      `show_financeiro`: pagamentos/reembolsos), reusando `_group_events` e replicando as
      fórmulas de KPI/cobrança da view. ENSAIO → shape reduzido.
- [ ] T009 [US1] `GET /api/events/<id>` em `app/api/agenda.py` (404 inexistente); serializa via
      T008 com o papel do usuário atual.

### Frontend
- [ ] T010 [P] [US1] Estender `lib/agenda.ts`: tipo EventoDetalhe (blocos opcionais) +
      `useEvent(id)`.
- [ ] T011 [US1] `frontend/apps/internal/src/pages/EventDetailPage.tsx`: renderiza cada bloco
      presente (elenco, financeiro gated, contrato, logs, observações, avaliações); valores
      monetários via `@manto/money`; skeleton/erro; Framer Motion; mobile.
- [ ] T012 [US1] Rota `/events/:id` no `App.tsx`; abrir a partir da AgendaPage.

### Verificação B (o coração — paridade por papel)
- [ ] T013 [US1] Estender `verify_145_agenda_read.py`: usuários efêmeros (superadmin;
      comercial; casting-sem-financeiro). Superadmin recebe blocos financeiros com totais
      (custo/comissão/recebido/reembolso pendente) == cálculo da view; casting-sem-financeiro
      NÃO recebe nenhum campo financeiro; 404/401 cobertos. `tsc`/`build` limpos; ruff nos
      arquivos novos.

**Checkpoint B**: página do evento em React exibe todas as seções com paridade e RBAC corretos.

---

## Fase final (após A+B)
- [ ] T014 Atualizar `CLAUDE.md` (estado híbrido: agenda/evento agora têm leitura em React) e
      registrar memória. Changelog do time: só quando a leitura de fato substituir algo em
      produção (a equipe ainda opera no Jinja) — decidir com o usuário, como na Fundação.
- [ ] T015 Conferência manual no browser com o usuário (não executável pelo agente): paridade
      Jinja × React no mesmo evento/papel, e viewport mobile.

## Dependências
- A antes de B (B reusa tipos/infra de A, mas é independentemente testável).
- Backend antes do frontend em cada incremento; verificação por último.
- Nenhuma tarefa toca as views Jinja (coexistência, FR-009).
