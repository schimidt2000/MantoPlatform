# Implementation Plan: Badge "✓ Avaliado" no histórico

**Branch**: `009-badge-avaliado` | **Date**: 2026-05-30 | **Spec**: [spec.md](./spec.md)

## Summary

Expor ao template o conjunto de eventos já avaliados pelo talento (`rated_event_ids`) e, no
histórico (home + página completa), mostrar "✓ Avaliado" quando o evento estiver nesse conjunto
— senão, cair na regra atual ("⭐ Avaliar" se elegível, ou nada).

## Technical Context

**Language/Version**: Python 3.11+ (Flask, Jinja2)
**Storage**: sem mudança de schema, sem migration.
**Constraints**: badge independe da janela de 7 dias; não regredir o botão "Avaliar".
**Scale/Scope**: 1 helper + 2 rotas (home, historico) + 2 templates.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — espelha o padrão de `_rateable_event_ids`; reusa `EventRating`.
- **II. Padrões Python** ✅ — helper pequeno e tipado, evita duplicar a query de avaliações.
- **III. Camadas** ✅ — cálculo nas rotas; templates só apresentação.
- **IV. Não quebrar** ✅ — sem schema; botão "Avaliar" preservado; só adiciona o badge.
- **V. UI/UX (pt-BR)** ✅ — badge "✓ Avaliado" consistente com os badges existentes.
- **VI. Planejar antes de codar** ✅ — este plano.

**Sem violações. Sem migration.**

## Project Structure

```text
app/
├── talent_portal/routes.py          # helper _rated_event_ids(talent); usar em home() e historico()
└── templates/portal/
    ├── home.html                    # "✓ Avaliado" no histórico recente
    └── historico.html               # "✓ Avaliado" na lista completa
```

## Design Detalhado

### 1. Helper `_rated_event_ids(talent) -> set[int]`
```python
def _rated_event_ids(talent) -> set[int]:
    return {r.event_id for r in EventRating.query.filter_by(talent_id=talent.id).all()}
```
- Refatorar `_rateable_event_ids` para reusar esse conjunto (DRY): `rated = _rated_event_ids(talent)`.
- `home()` e `historico()` passam `rated_event_ids` ao template.

### 2. Templates (home.html histórico recente + historico.html)
Ordem de decisão por item:
```jinja
{% if ev.id in rateable_event_ids %}
  <a ... >⭐ Avaliar</a>
{% elif ev.id in rated_event_ids %}
  <span class="pay-badge pay-pago">✓ Avaliado</span>
{% endif %}
```
- Reusa o estilo de badge verde já existente (`pay-pago`).
- Independe da janela (FR-005): `rated_event_ids` não filtra por data.

### Verificação
- Evento avaliado → "✓ Avaliado", sem botão.
- Evento elegível não avaliado → "⭐ Avaliar".
- Evento passado não avaliado fora da janela → nada.

### Fora de escopo
- Tornar o badge clicável / reabrir avaliação; mudar a janela de elegibilidade.
