# Tasks: Avaliar evento só depois que ele ACABOU

**Input**: `specs/039-avaliar-so-apos-fim/`
**Tests**: boot + ruff + test client (portal). Sem migration.

## Phase 1: Correção de fuso
- [x] T001 `app/talent_portal/routes.py`: helpers `_now_sp()` e `_event_ended(event)`.
- [x] T002 Trocar `utcnow()` por `_now_sp()` nas comparações com horários de evento:
      `_rateable_event_ids`, `_editable_rating_event_ids`, `home()` (today/upcoming/history/
      all_past), `historico()`. Carimbos internos permanecem UTC.

## Phase 2: Trava no servidor
- [x] T003 `rate_event` (GET), `submit_rating` (POST), `rate_event_detail` (GET/POST): recusar
      evento não terminado com flash + redirect ao home do portal.

## Phase 3: Verificação
- [x] T004 ruff + boot + test client: evento em +2h não listado/recusado (GET redirect, POST não
      grava); terminado há 1h listado e grava; começando em +2h segue em próximos; janelas 7/30 dias
      preservadas.

## Dependencies
- T001 → T002 → T003 → T004.

## Notes
- Eventos são naïve-Brasília no banco; bug era comparação com UTC (+3h).
