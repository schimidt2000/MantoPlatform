# Implementation Plan: Avaliação só após o evento + feedback do show no geral

**Branch**: `006-avaliacao-pos-evento` | **Date**: 2026-05-30 | **Spec**: [spec.md](./spec.md)

## Summary

Dois ajustes pequenos e localizados no portal do talento:
1. **Bug**: a query de "eventos para avaliar" usa `CalendarEvent.start_at < now` — passa a usar
   o **término** do evento (`end_at`, com fallback para `start_at`).
2. **Rótulo**: o campo "Texto do Show" na avaliação detalhada passa a "Show no geral" + dica;
   mantém-se o identificador interno `texto` (sem migration, sem perda de histórico).

## Technical Context

**Language/Version**: Python 3.11+ (Flask), Jinja2
**Storage**: sem mudança de schema, sem migration (categoria interna `texto` preservada).
**Constraints**: não perder avaliações históricas; manter a janela de 7 dias atual.
**Scale/Scope**: 1 query na rota do portal + 1 bloco no template de avaliação.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — só ajusta a query e o rótulo existentes; nada novo.
- **II. Padrões Python** ✅ — mudança mínima e legível.
- **III. Camadas** ✅ — query no portal; template só apresentação.
- **IV. Não quebrar o que funciona** ✅ — categoria interna preservada (histórico intacto);
  fallback para eventos sem `end_at`; branch isolado; verificação no app.
- **V. UI/UX (pt-BR)** ✅ — novo título + dica em português.
- **VI. Planejar antes de codar** ✅ — este plano.

**Sem violações. Sem migration.**

## Project Structure

```text
app/
├── talent_portal/routes.py          # query events_to_rate: start_at -> término (end_at/coalesce)
└── templates/portal/rate_detail.html # "Texto do Show" -> "Show no geral" + dica
```

## Design Detalhado

### 1. Query "eventos para avaliar" (talent_portal/routes.py ~239-252)
Hoje:
```python
.filter(CalendarEvent.start_at < datetime.utcnow(),
        CalendarEvent.start_at >= _rating_window)
```
Passa a usar o término efetivo. Como `end_at` é nullable, usa-se coalesce(end_at, start_at):
```python
from sqlalchemy import func
_event_end = func.coalesce(CalendarEvent.end_at, CalendarEvent.start_at)
.filter(_event_end < datetime.utcnow(),
        _event_end >= _rating_window)
```
- "Terminado" = `end_at` no passado; se não houver `end_at`, usa `start_at`.
- A janela de 7 dias (`_rating_window`) passa a contar a partir do término — mantém o conceito
  de "eventos recentes" (FR-004).

### 2. Rótulo do campo de show (templates/portal/rate_detail.html ~114-124)
- Trocar o título "📝 Texto do Show" por "🎭 Show no geral".
- Adicionar a dica abaixo do título: "Falar sobre coreografia, posicionamento, texto e interações".
- Mantém `name="sub_texto_score"` / `sub_texto_comment` — o backend (`categories=["som","texto"]`)
  e o histórico permanecem intactos (FR-006, sem perda de dados).

### Fora de escopo
- Renomear a categoria interna `texto` no banco (manteria histórico mas exigiria migration + ajuste
  de relatórios) — desnecessário para o pedido.
- Mudar a avaliação de "Som" ou as demais categorias.
