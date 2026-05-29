# Tasks: Calendário não trava mais ao abrir

**Input**: `specs/001-calendario-sem-travar/` (spec.md, plan.md)

**Tests**: não há suíte automatizada no projeto — cada história tem uma tarefa de
**verificação manual no app real** (constituição: "conferir no app real que funciona").

## Format: `[ID] [P?] [Story] Descrição`
- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)

---

## Phase 1: User Story 1 — Abrir o calendário é instantâneo (P1) 🎯 MVP

**Goal**: a abertura do calendário nunca mais bloqueia esperando sincronização externa.

**Independent Test**: abrir a agenda em um mês passado/desatualizado e confirmar que os
eventos aparecem em < 1s, mesmo com o Google lento/indisponível.

- [ ] T001 [US1] Em `agenda()` ([app/calendar/routes.py:290](../../app/calendar/routes.py#L290)),
      inverter o control flow: **sempre** servir do banco via `_build_events_from_db()`;
      só executar o caminho de sincronização ao vivo quando `force_sync=1`.
- [ ] T002 [US1] No ramo `force_sync`, após `sync_events()` + `_mark_month_synced()`,
      fazer **redirect** para `/agenda?ym=...&view=...` (sem `force_sync`) — evita
      re-sincronizar em F5 e renderiza já fresco pelo caminho rápido. Em falha do Google,
      manter o `flash` de aviso e seguir para o caminho rápido (FR-008).
- [ ] T003 [US1] **Verificação manual**: abrir vários meses (atual, passado, futuro);
      confirmar carregamento instantâneo e que nenhuma chamada externa bloqueia a página.

**Checkpoint**: calendário abre rápido sempre. MVP entregável.

---

## Phase 2: User Story 2 — Indicador de frescor (P2)

**Goal**: o usuário vê há quanto tempo o mês foi atualizado.

**Independent Test**: abrir a agenda e ver um badge "atualizado há X" / "nunca atualizado".

- [ ] T004 [US2] Criar helper `_month_sync_age_minutes(ym: str) -> int | None` em
      [app/calendar/routes.py](../../app/calendar/routes.py) lendo `SiteSetting.calendar_sync_cache`
      (mesma fonte de `_is_month_fresh`); retorna minutos desde a última sync, ou `None`.
- [ ] T005 [US2] Em `agenda()`, calcular `sync_age_min` e passá-lo ao `render_template`.
- [ ] T006 [US2] Em [app/templates/calendar_list.html](../../app/templates/calendar_list.html),
      exibir badge de frescor (verde = recente, âmbar = desatualizado, cinza = nunca),
      usando variáveis CSS.

**Checkpoint**: frescor visível em 1 olhada.

---

## Phase 3: User Story 3 — Atualizar agora (P2)

**Goal**: forçar atualização do mês em 1 clique.

**Independent Test**: alterar um evento no Google, clicar "Atualizar agora", ver o reflexo.

- [ ] T007 [US3] Em `calendar_list.html`, adicionar botão "Atualizar agora" apontando para
      a URL atual + `&force_sync=1`, com estado visual "Atualizando…" ao clicar.
- [ ] T008 [US3] Em `agenda()`, após sync manual bem-sucedido, `flash("Agenda atualizada.", "success")`
      (exibido após o redirect do T002).
- [ ] T009 [US3] **Verificação manual**: criar/alterar evento na origem, usar o botão,
      confirmar reflexo e que o badge de frescor zera.

**Checkpoint**: válvula de escape funcionando.

---

## Phase 4: Polish

- [ ] T010 [P] Rodar `ruff check app/calendar/routes.py` e formatar os arquivos tocados.
- [ ] T011 Verificação final end-to-end + confirmar que o cron (`sync_worker.py`) não
      regrediu (continua marcando meses como sincronizados).

---

## Dependencies & Execution Order

- **T001 → T002** (mesmo ramo de control flow).
- **T004 → T005 → T006** (helper antes de usar; rota antes do template).
- **US3 (T007/T008)** depende do redirect do T002 existir.
- US1 é o MVP e pode ser entregue sozinho. US2 e US3 agregam transparência e controle.
- T003/T009/T011 são verificações manuais ao fim de cada bloco.

## Notes
- Fora de escopo (features próprias): extrair `sync_service.py`; unificar páginas
  Log/Sync + remover template órfão; sync assíncrono real via fila.
