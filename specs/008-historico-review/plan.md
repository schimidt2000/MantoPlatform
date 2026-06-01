# Implementation Plan: Avaliar qualquer evento elegível pelo histórico

**Branch**: `008-historico-review` | **Date**: 2026-05-30 | **Spec**: [spec.md](./spec.md)

## Summary

O backend já lista todos os eventos avaliáveis dos últimos 7 dias (`events_to_rate`) e o banner
já cria um link por evento — mas (a) o texto diz "último evento" e (b) o **histórico** não tem
botão de avaliar. Solução: calcular um conjunto de **event_ids elegíveis** (terminados ≤7 dias,
não avaliados) e expô-lo ao template; o histórico (na home e na página `/portal/historico`)
mostra "Avaliar" para esses; e ajustar o texto do destaque para plural/singular.

## Technical Context

**Language/Version**: Python 3.11+ (Flask, SQLAlchemy, Jinja2)
**Storage**: sem mudança de schema, sem migration.
**Constraints**: mesma janela de 7 dias e regra de término (coalesce end_at/start_at) já usadas
em `events_to_rate`; não permitir reavaliar; reutilizar a tela de avaliação existente.
**Scale/Scope**: 2 rotas (home, historico) + 2 templates (home.html, historico.html).

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reusa a tela `/portal/events/<id>/rate`, a janela e a
  regra de término já existentes; só calcula um conjunto de IDs elegíveis e ajusta a exibição.
- **II. Padrões Python** ✅ — um helper pequeno para o conjunto elegível, evitando duplicar a query.
- **III. Camadas** ✅ — cálculo nas rotas; templates só apresentação.
- **IV. Não quebrar** ✅ — sem schema; banner atual continua; só adiciona pontos de entrada.
- **V. UI/UX (pt-BR)** ✅ — botão "Avaliar" consistente; texto plural/singular correto.
- **VI. Planejar antes de codar** ✅ — este plano.

**Sem violações. Sem migration.**

## Project Structure

```text
app/
├── talent_portal/routes.py          # helper _rateable_event_ids(talent); usar em home() e historico()
└── templates/portal/
    ├── home.html                    # texto do destaque (plural) + botão "Avaliar" no histórico
    └── historico.html               # botão "Avaliar" nos itens elegíveis
```

## Design Detalhado

### 1. Helper `_rateable_event_ids(talent) -> set[int]`
Extrai a lógica que já existe em `home()` para uma função reutilizável:
```python
def _rateable_event_ids(talent) -> set[int]:
    window = datetime.utcnow() - timedelta(days=7)
    event_end = func.coalesce(CalendarEvent.end_at, CalendarEvent.start_at)
    rated = {r.event_id for r in EventRating.query.filter_by(talent_id=talent.id).all()}
    rows = (EventRole.query.filter_by(talent_id=talent.id, invite_status="accepted")
            .join(CalendarEvent)
            .filter(event_end < datetime.utcnow(), event_end >= window).all())
    return {r.event_id for r in rows if r.event_id not in rated}
```
- `home()` usa esse conjunto para montar `events_to_rate` (mantém comportamento) e passa
  `rateable_event_ids` ao template.
- `historico()` passa `rateable_event_ids` ao template também.

### 2. home.html
- Destaque: trocar "Avalie seu último evento" por "Avalie seus eventos" (título neutro) e o
  subtítulo já usa plural condicional ("evento(s)") — manter.
- Histórico recente: para cada item, se `ev.id in rateable_event_ids`, exibir botão "⭐ Avaliar"
  apontando para `/portal/events/{{ ev.id }}/rate`.

### 3. historico.html
- Para cada item da lista, mesmo botão "⭐ Avaliar" quando `ev.id in rateable_event_ids`.

### Verificação
- Dois eventos terminados ≤7 dias não avaliados → ambos com "Avaliar" no histórico.
- Evento avaliado / fora da janela → sem "Avaliar".

### Fora de escopo
- Mudar a tela de avaliação em si; permitir reavaliação; alterar a janela de 7 dias.
