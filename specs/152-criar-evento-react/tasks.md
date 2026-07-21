# Tasks: criar evento em React (152)

**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)
Padrão de 146-151: núcleo compartilhado → adaptadores finos (Jinja + API) → React → verificação por
paridade contra `manto_local`. Google mockado (`insert_event`). Sem mudança de schema. Upload de
arquivo fora de escopo (fica só no Jinja). **Núcleo em `app/calendar/routes.py`** (não em módulo
`ops` novo — ver Complexity Tracking do plano: helpers reusados por outras rotas).

## Backend — núcleo (funções de módulo em `routes.py`)

- [X] T001 [US1][US2] `app/calendar/routes.py`: `_validate_event_core(data: dict) -> dict[str, str]`
      (título, data, horários início/fim distintos e ambos presentes via `_build_start_end`,
      financeiro quando não-cortesia, vendedor, parcelamento PIX 2–12 — mapa campo→mensagem) e
      `_create_event_row(data: dict, *, google_event_id: str, gc_title: str) -> CalendarEvent`
      (grava `CalendarEvent`, `EventInvoice` quando `with_invoice` sem arquivo, `EventAcrescimo`
      tipados, detecção fora-de-SP via `_lookup_sp_status`/`_fetch_travel_data`). Funções puras (sem
      `request`/`flash`/`current_user`). Docstrings + type hints.
- [X] T002 [US3] `routes.py`: `_create_roles_from_input(event, characters: list[dict], *, orc_caches,
      dur_idx, figurino_by_name, valid_talent_ids) -> list[tuple[int, str]]` (EventRole por
      personagem, auto-match de figurino por nome, pré-escala sem duplicar talento no mesmo
      formulário) e `_apply_default_roles(event, *, event_type, came_from_orcamento,
      coordinator_talent_id, valid_talent_ids)` (chama `_ensure_coordinator`/
      `_ensure_sound_technician` para SHOW, mesma regra condicional de hoje).
- [X] T003 [P] [US3] `routes.py`: `_check_talent_conflicts(assigned_now, start, end, event_id,
      talents) -> list[str]` (aviso não-bloqueante pós-commit, usa `_talent_time_conflict` já
      existente).
- [X] T004 [P] [US4] `routes.py`: `_build_event_create_options() -> dict` (fichas de figurino,
      vendedores, talentos atribuíveis, `CLIENT_RELATION_TIPOS`) e `_build_orcamento_prefill(
      orcamento_id: int | None) -> dict` (mesmo cálculo de transporte/acréscimo legado/cachês por
      duração de hoje, via `_lookup_sp_status`/`_compute_performer_caches`; `{}` se id
      ausente/inválido).
- [X] T005 [P] [US5] `routes.py`: `_create_client_links(event, client_pairs: list[tuple[int,
      str]])` (usa `_primary_client_id`), `_link_form_response(form_response_id: int | None,
      event_id: int)`, `_create_reembolso_entry(event, *, description, amount,
      invoice_file_path=None, created_by_id)`, `_create_observations_from_input(event,
      observations: list[dict])` (grava texto/link; ignora `obs_type == "image"` — paridade com o
      padrão da 150).
- [X] T006 [US1][US2][US3][US5] `routes.py`: `_create_event_core(data: dict, *, google_event_id,
      gc_title, actor_name, actor_id) -> tuple[CalendarEvent, list[str]]` — orquestrador único
      (T001-T005 em sequência: evento → clientes/pré-contrato → acréscimos/nota fiscal/fora-SP →
      elenco/pré-escala → coordenador/som → reembolso → observações → `EventLog` +
      `_sync_commission_payment` + commit → `_notify_ensaio_team` se `needs_rehearsal` →
      `_check_talent_conflicts`). Único ponto chamado pelo wrapper Jinja e pela API (mesmo padrão de
      `_delete_event_flow`/`_sync_single_event_flow`, 151).

## Backend — wrapper Jinja e endpoints API

- [X] T007 `app/calendar/routes.py`: `create_event` (GET e POST) vira wrapper fino sobre o núcleo —
      GET monta contexto com `_build_event_create_options`/`_build_orcamento_prefill`; POST faz
      parsing de `request.form`/`request.files` (incl. os campos de arquivo que ficam só aqui: nota
      fiscal, contrato, comprovantes de pagamento, comprovante de reembolso, imagem de observação),
      chama `insert_event` (Google) antes de qualquer gravação, e então `_create_event_core`. Mesmos
      flashes/redirects/re-render de erro (a lista de erros do Jinja é a lista de valores do dict
      que `_validate_event_core` devolve). Bloco de contrato/comprovantes de pagamento (dependem de
      arquivo, sempre `if fpath:`) continua só aqui, após o núcleo retornar o evento.
- [X] T008 [US1][US2] `app/api/agenda_write.py`: `POST /api/events` (`@api_login_required`, gate
      `_CAN_CREATE`, importado de `routes.py` — mesma direção `api → routes`). Corpo JSON sem campos
      de arquivo. `_validate_event_core` não-vazio → `json_error("Corrija os campos destacados",
      400, fields=...)`. Válido → `insert_event`; falha → `json_error("Não foi possível criar o
      evento na Agenda do Google agora...", 502)`. Sucesso → `_create_event_core(...)`, `201` com
      `serialize_event_detail` do evento novo + `warnings` (conflitos de talento) no corpo.
- [X] T009 [P] [US4] `app/api/agenda.py` (correção: rotas de leitura ficam aqui, não em
      `agenda_read.py` — esse é só o módulo de serialização): `GET /api/events/new/options` e `GET
      /api/events/new/prefill?orcamento_id=<id>` (mesmo gate `_CAN_CREATE`), chamando
      `_build_event_create_options`/`_build_orcamento_prefill` (importados de `routes.py`).

## Frontend

- [X] T010 [P] `frontend/apps/internal/src/lib/eventCreate.ts` (NOVO): `useEventCreateOptions()`
      (GET `/api/events/new/options`, `staleTime` longo), `useOrcamentoPrefill(orcamentoId)` (GET
      `/api/events/new/prefill`, `enabled: !!orcamentoId`), `useCreateEvent()` (POST `/api/events`,
      `onSuccess` invalida `["agenda"]`/`["agenda-dia"]`).
- [X] T011 [P] [US5] `frontend/apps/internal/src/components/ClientPicker.tsx` e
      `FormResponsePicker.tsx` (NOVOS): busca com debounce consumindo `/clientes/search` e
      `/formularios/respostas/search` (já JSON, sem endpoint `/api/*` novo). Seleção múltipla de
      clientes com tipo de relação (`ClientPicker`); seleção única de pré-contrato
      (`FormResponsePicker`).
- [X] T012 [US1][US2][US3][US4][US5] `frontend/apps/internal/src/pages/EventCreatePage.tsx` (NOVO):
      formulário com `react-hook-form` + `zod` — campos essenciais (US1) sempre visíveis; bloco
      financeiro (US2) com `<MoneyInput/>`, colapsa quando cortesia/permuta ligado (Framer Motion);
      lista dinâmica de personagens com pré-escala de talento (US3); seleção de duração quando
      `orcamento_id` vem na URL, recalculando totais/cachês via `useOrcamentoPrefill` (US4); seções
      de clientes/pré-contrato/reembolso/observações texto-ou-link, sem campo de imagem (US5). Erros
      de campo do 400 (`fields`) mapeados via `setError`. Botão "Criar evento" desabilita + mostra
      estado pendente; sucesso navega para `/events/:id`. Conferir 320–430px (Princípio VIII).
- [X] T013 [P] `App.tsx`: rota `/events/new` → `EventCreatePage`. `AgendaPage.tsx`: link/botão "Novo
      evento".

## Verificação

- [X] T014 `scripts/db/verify_152_criar_evento.py`: mock de `insert_event` (Google). Paridade API×
      Jinja criando o mesmo evento com o mesmo input (exceto arquivos) e comparando linha a linha
      `CalendarEvent`/`EventRole`/`EventClient`/`EventAcrescimo`/`EventInvoice`/`EventReimbursement`/
      `EventObservation`. Cobre: cada erro de validação (título/data/horário/financeiro/vendedor/
      parcelamento) preservando os dados enviados; falha do Google (nada grava, 502); talento
      pré-escalado duplicado e conflito de agenda (aviso não-bloqueante); `orcamento_id` inválido
      (formulário/endpoint vazio, sem erro); observação de imagem descartada na API mas aceita no
      Jinja; 403 sem `_CAN_CREATE`. Jinja 302; API 200/201/400/403/502. `ruff` nos arquivos tocados;
      `tsc`/`build` limpos.

## Fase final

- [X] T015 Marcar tasks; commit no branch `152-...`; merge+push. `CLAUDE.md`/memória pointer.
      Changelog só quando substituir algo em produção — equipe segue no Jinja, não republicar agora.

## Dependências

- T001 → T002 → T003 (roles dependem do evento existir). T004/T005 independem de T001-T003 (podem
  rodar em paralelo). T006 depende de T001-T005 (orquestra tudo). T007/T008 dependem de T006. T009
  depende só de T004. Frontend (T010-T013) depende do backend (T007-T009). T014 por último. Nenhuma
  mudança de schema.
