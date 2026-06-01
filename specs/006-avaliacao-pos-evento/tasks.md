# Tasks: Avaliação só após o evento + feedback do show no geral

**Input**: `specs/006-avaliacao-pos-evento/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: US1 — Avaliação só após término (P1) 🎯

- [ ] T001 [US1] Em `home()` ([app/talent_portal/routes.py](../../app/talent_portal/routes.py)),
      trocar o filtro de `events_to_rate`: usar `func.coalesce(CalendarEvent.end_at,
      CalendarEvent.start_at)` no lugar de `start_at` para as duas comparações (término < now;
      término >= janela). Importar `func` se necessário.

## Phase 2: US2 — Show no geral (P2)

- [ ] T002 [US2] Em [templates/portal/rate_detail.html](../../app/templates/portal/rate_detail.html),
      trocar o título "📝 Texto do Show" por "🎭 Show no geral" e adicionar a dica
      "Falar sobre coreografia, posicionamento, texto e interações". Manter os `name="sub_texto_*"`.

## Phase 3: Polish

- [ ] T003 `ruff check` no arquivo .py tocado.
- [ ] T004 Verificação no app real:
      (a) evento que termina no futuro NÃO aparece para avaliar; evento já terminado aparece;
      (b) avaliação detalhada de show mostra "Show no geral" + dica; envio salva normalmente.

## Dependencies
- T001 e T002 independentes (arquivos diferentes). T003/T004 ao final.

## Notes
- Sem migration: categoria interna `texto` preservada (histórico intacto).
- Fallback `coalesce(end_at, start_at)` cobre eventos sem término definido.
