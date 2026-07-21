# Implementation Plan: confirmar evento / logística (149)

**Branch**: `149-agenda-confirmar-logistica` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

## Summary

Migra as duas ações de **nível-evento** hoje no POST único de `/events/<id>` — confirmar/
desconfirmar (`toggle_confirmado`) e salvar logística (`save_logistics`) — para React + API JSON,
aplicando o padrão de 146/147/148. Núcleo extraído para um novo `app/calendar/event_ops.py`;
handlers Jinja viram wrappers finos; dois endpoints REST; serializer de leitura passa a expor
logística + `confirmed_by` + flags de permissão; React ganha um toggle de confirmação e uma seção
de Logística editável. Verificação por paridade contra `manto_local`, e-mails mockados. Sem mudança
de schema.

## Technical Context

Igual à 146/148: Python/Flask + React (Vite/TS/TanStack Query); sem dependência nova; verificação
com test client contra `manto_local` (Postgres), e-mail mockado; requests fora de `app_context`.
Campos já existentes em `CalendarEvent`: `confirmed_at`/`confirmed_by_id` (+ relação `confirmer`),
`makeup_time`/`makeup_location`, `departure_time`/`departure_location`, `needs_rehearsal`.

## Constitution Check

- **I (reutilizar)**: núcleo único em `event_ops` (`toggle_confirmed`, `save_logistics`), reusado por
  Jinja e API. Os dois notificadores de logística (`notify_accepted_roles`, `notify_ensaio_team`)
  **movem** de `routes.py` para `event_ops` (são helpers de notificação, pertencem à camada de
  operações); `routes.py` os reimporta com alias `_notify_*` — os 4 call sites existentes (sync
  inclusive) seguem inalterados. Dependência unidirecional `routes → event_ops` (event_ops só
  importa `models`/`email_service`, nunca `routes` — sem ciclo).
- **IV (não quebrar)**: adaptadores Jinja com efeito idêntico; paridade verificada campo a campo. As
  notificações disparam nos mesmos gatilhos (mudança de logística → cargos aceitos; "precisa ensaio"
  desligado→ligado → equipe ENSAIO).
- **V (feedback)**: botões com feedback (mutations do TanStack); confirmar é toggle idempotente
  (UPDATE de coluna), o front bloqueia o clique enquanto pendente — clique-duplo não gera log espúrio.
- **VII (monetário)**: sem valor monetário nesta fatia (nenhuma máscara nova).
- **VIII (mobile-first)**: a seção de Logística e o toggle são conferidos em viewport 320–430px.
- **IX (movimento)**: reusa os utilitários de transição já presentes na `EventDetailPage` (sem
  animação nova exigida; a seção surge/atualiza com o mesmo padrão das demais).

## Project Structure

```text
app/calendar/event_ops.py     # NOVO: toggle_confirmed, save_logistics + notify_accepted_roles,
                              #   notify_ensaio_team (movidos de routes.py)
app/calendar/routes.py        # _handle_toggle_confirmado / _handle_save_logistics viram wrappers
                              #   finos; import-alias dos dois notificadores movidos
app/api/agenda_write.py       # + POST /api/events/<id>/confirm, PATCH /api/events/<id>/logistics
app/api/agenda_read.py        # event block: + confirmed_by + logística; _role_flags: + can_confirm,
                              #   can_edit_event
frontend/apps/internal/src/
├── lib/agenda.ts             # EventoDetalhe.event: + confirmed_by + campos de logística
├── lib/eventOps.ts           # NOVO: useToggleConfirm, useSaveLogistics
└── pages/EventDetailPage.tsx # badge "Confirmado" → toggle; nova seção Logística (leitura + edição)
scripts/db/verify_149_logistica.py  # NOVO: paridade API×Jinja
```

## Design Decisions

1. **Núcleo em `event_ops.py`** (parâmetros explícitos, sem `request`/`flash`/`current_user`):
   - `toggle_confirmed(event, *, actor_name, actor_id, tz) -> bool` — alterna `confirmed_at`/
     `confirmed_by_id`, registra `EventLog` ("Marcou…"/"Desfez…") como hoje; devolve o novo estado.
     A RBAC (Comercial/Superadmin) fica nos adaptadores.
   - `save_logistics(event, *, makeup_time, makeup_location, departure_time, departure_location,
     needs_rehearsal, actor_name, tz) -> None` — recebe valores **já resolvidos** (o "outro" de
     maquiagem é resolvido no adaptador via helper compartilhado `resolve_makeup_location`); aplica
     os campos, detecta as 4 mudanças e dispara `notify_accepted_roles` (mudou logística) e
     `notify_ensaio_team` (só na transição de `needs_rehearsal` desligado→ligado) — comportamento
     idêntico ao handler atual (que inlinha o mesmo corpo do `_notify_ensaio_team`).
2. **RBAC por ação (paridade exata)**, aplicada no endpoint antes de chamar o núcleo:
   - `confirm` → **Comercial ou Superadmin** (gate interno do handler Jinja de hoje). Um Financeiro
     que pode editar o evento mas não é Comercial recebe 403 (paridade com o flash de erro do Jinja,
     que não altera estado). No React o botão só aparece com `flags.can_confirm`.
   - `logistics` → `_can_edit_event()` (`_CAN_EDIT_EVENT` = casting/figurino/comercial/financeiro/
     superadmin), o mesmo gate do POST Jinja que despacha `save_logistics`. No React a seção de
     edição só aparece com `flags.can_edit_event`.
3. **Serializer** (`agenda_read.py`): o bloco `event` (não-financeiro, sempre presente) ganha
   `confirmed_by` (`event.confirmer.name`), `makeup_time`, `makeup_location`, `departure_time`,
   `departure_location`, `needs_rehearsal`. `_role_flags` ganha `can_confirm` (Comercial|SA) e
   `can_edit_event` (qualquer papel de `_CAN_EDIT_EVENT`), via o helper `has()` que respeita
   impersonação. Campos aditivos — não quebram consumidores da 145/146/147/148.
4. **Endpoints**: `POST /api/events/<id>/confirm` (toggle, sem corpo) e `PATCH /api/events/<id>/
   logistics` (corpo JSON com os campos de logística). Ambos devolvem `serialize_event_detail`
   (RBAC de serialização preservado), para a tela re-renderizar sem reload.
5. **Frontend**: `lib/eventOps.ts` com `useToggleConfirm` (segue o `useRoleAction` — POST sem corpo,
   atualiza `["event", id]`) e `useSaveLogistics` (PATCH com corpo). Na `EventDetailPage`, o badge
   "Confirmado" vira botão (Confirmar/Desfazer) quando `can_confirm`; nova seção **Logística** mostra
   maquiagem/saída/precisa-ensaio e, quando `can_edit_event`, um form de edição (inputs de hora/
   texto, select de local com "outro"→custom, checkbox de ensaio) com feedback de clique.
6. **Verificação** (`verify_149_logistica.py`): para cada ação, roda via API e via Jinja em eventos
   equivalentes e compara o estado resultante campo a campo; cobre confirmar/desconfirmar (toggle
   ida e volta), o 403 de confirmar sem Comercial/SA e de logística fora de `_CAN_EDIT_EVENT`, o
   local "outro", e o disparo do alerta de ENSAIO **só** na transição desligado→ligado (mock dos
   senders, contagem de chamadas). E-mail mockado; Jinja segue 302; API 200. ruff/tsc/build limpos.

## Complexity Tracking
*Sem violações.*
