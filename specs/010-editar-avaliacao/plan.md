# Implementation Plan: Editar avaliação de eventos (até 30 dias)

**Branch**: `010-editar-avaliacao` | **Date**: 2026-05-30 | **Spec**: [spec.md](./spec.md)

## Summary

A tela de avaliação já reabre e atualiza uma avaliação existente (`rate_event` GET pré-preenche;
`submit_rating` POST faz update; `rate.html` mostra estrelas/comentário atuais). Falta apenas o
ponto de entrada: no histórico, eventos **já avaliados** realizados nos **últimos 30 dias**
mostram "Editar avaliação", apontando para a mesma tela `/portal/events/<id>/rate`.

## Technical Context

**Language/Version**: Python 3.11+ (Flask, Jinja2)
**Storage**: sem mudança de schema, sem migration.
**Constraints**: janela de edição = 30 dias pelo término (coalesce end_at/start_at); reutilizar
a tela de avaliação; não criar duplicata (já garantido por submit_rating).
**Scale/Scope**: 1 helper + 2 rotas (home, historico) + 2 templates.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reusa a tela de avaliação e o update já existentes;
  espelha o padrão de `_rateable_event_ids`/`_rated_event_ids`.
- **II. Padrões Python** ✅ — helper pequeno e tipado.
- **III. Camadas** ✅ — cálculo nas rotas; templates só apresentação.
- **IV. Não quebrar** ✅ — sem schema; "Avaliar" (7d) e "✓ Avaliado" preservados; só adiciona "Editar".
- **V. UI/UX (pt-BR)** ✅ — link "Editar avaliação" discreto ao lado do "✓ Avaliado".
- **VI. Planejar antes de codar** ✅ — este plano.

**Sem violações. Sem migration.**

## Project Structure

```text
app/
├── talent_portal/routes.py          # helper _editable_rating_event_ids(talent); home() + historico()
└── templates/portal/
    ├── home.html                    # "Editar avaliação" no histórico recente
    └── historico.html               # idem na lista completa
```

## Design Detalhado

### 1. Helper `_editable_rating_event_ids(talent) -> set[int]`
Eventos **já avaliados** e terminados nos últimos 30 dias:
```python
def _editable_rating_event_ids(talent) -> set[int]:
    window = datetime.utcnow() - timedelta(days=30)
    event_end = func.coalesce(CalendarEvent.end_at, CalendarEvent.start_at)
    rated = _rated_event_ids(talent)
    if not rated:
        return set()
    rows = (EventRole.query.filter_by(talent_id=talent.id, invite_status="accepted")
            .join(CalendarEvent)
            .filter(CalendarEvent.id.in_(rated),
                    event_end < datetime.utcnow(), event_end >= window).all())
    return {r.event_id for r in rows}
```
- `home()` e `historico()` passam `editable_rating_event_ids` ao template.

### 2. Templates (ordem de decisão por item do histórico)
```jinja
{% if ev.id in rateable_event_ids %}
  <a ...>⭐ Avaliar</a>
{% elif ev.id in rated_event_ids %}
  <span class="pay-badge pay-pago">✓ Avaliado</span>
  {% if ev.id in editable_rating_event_ids %}
    <a href="/portal/events/{{ ev.id }}/rate" ...>Editar avaliação</a>
  {% endif %}
{% endif %}
```
- O link de edição aponta para a tela existente (que pré-preenche e atualiza).

### Verificação
- Avaliado há 10 dias → "✓ Avaliado" + "Editar avaliação".
- Avaliado há 40 dias → só "✓ Avaliado".
- Não avaliado dentro de 7 dias → "⭐ Avaliar".
- Editar e salvar → atualiza, não duplica.

### Fora de escopo
- Mudar a tela de avaliação; alterar a janela de primeira avaliação (7 dias); histórico de
  versões da avaliação.
