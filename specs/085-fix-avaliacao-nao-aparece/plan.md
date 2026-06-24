# Implementation Plan: Avaliação não aparece para talento incluído (085)

**Branch**: `085-fix-avaliacao-nao-aparece` | **Date**: 2026-06-24 | **Spec**: [spec.md](spec.md)

## Summary

Corrigir a regra de elegibilidade de avaliação em `app/talent_portal/routes.py`:

1. **Status do convite**: trocar a exigência de `invite_status == "accepted"` por "**não recusado**"
   (`accepted`, `pending` ou `NULL`), excluindo apenas `rejected`. Cuidado com NULL em SQL.
2. **Janela**: contar os 7 dias (avaliar) e 30 dias (editar) a partir do **mais recente** entre
   `coalesce(end_at, start_at)` (fim do evento) e `EventRole.assigned_at` (inclusão do talento).

Aplicar em **4 pontos**: `_rateable_event_ids`, `_editable_rating_event_ids`, `rate_event` (GET) e
`submit_rating` (POST). **Sem model novo, sem migration.**

## Technical Context

**Arquivo**: `app/talent_portal/routes.py`

- Novo helper `_not_rejected()` → cláusula SQL `or_(invite_status IS NULL, invite_status != 'rejected')`
  (evita o gotcha de `NULL != 'rejected'` retornar NULL).
- `_rateable_event_ids`: filtro `_not_rejected()`; término `event_end < now`; recência
  `or_(event_end >= window7, assigned_at >= window7)`.
- `_editable_rating_event_ids`: `_not_rejected()` + `or_(event_end >= window30, assigned_at >= window30)`.
- `rate_event` / `submit_rating`: trocar `invite_status == "accepted"` por `_not_rejected()` no
  `first_or_404()`; manter guarda `_event_ended`.
- Import: adicionar `or_` em `from sqlalchemy import func, or_`.

`assigned_at` é gravado em horário de Brasília (naïve no banco), comparável com `_now_sp()` (mesma
convenção dos demais horários).

## Constitution Check

- **I. Qualidade**: helper único reutilizado nos 4 pontos; sem duplicar a cláusula.
- **IV. Não quebrar**: continua exigindo término do evento; continua excluindo recusados; quem já
  enviou avaliação não duplica (filtro `rated`). Só amplia para incluídos/pendentes e janela por
  inclusão.

**Resultado**: PASS — sem migration.

## Testing

Contra **`manto_local`**:
- Simular (sem commit) uma `EventRole` para a Erika no evento #198 com `assigned_at = agora` e
  `invite_status = 'pending'`; confirmar que `#198 ∈ _rateable_event_ids(erika)` e que o guard de
  `rate_event` encontra a função.
- Confirmar que `invite_status='rejected'` **não** entra; que evento não terminado **não** entra; que
  `assigned_at` antigo + evento antigo (fora da janela) não entra.
- `ruff` sem erros novos.

## Project Structure

```text
app/talent_portal/routes.py — _not_rejected(); _rateable_event_ids; _editable_rating_event_ids;
                              rate_event; submit_rating
```

## Complexity Tracking

> Sem violações.
