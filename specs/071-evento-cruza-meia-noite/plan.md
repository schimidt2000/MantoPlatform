# Implementation Plan: Evento que cruza a meia-noite (071)

**Branch**: `071-evento-cruza-meia-noite` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

## Summary

Quando o horário de fim for **menor** que o de início, interpretar o fim como **dia seguinte**
(evento cruza a meia-noite) em vez de rejeitar. Aplica-se a criar evento, criar e editar ensaio.
Aviso visual na tela de criação. Início == fim continua bloqueado. **Sem modelo, sem migration.**

## Technical Context

**Language/Version**: Python 3.11, Flask; Jinja2 + JS vanilla.

**Primary Dependencies**: nenhuma nova (`datetime`/`timedelta` já importados).

**Storage**: N/A (sem mudança de schema).

**Testing**: contra **`manto_local`**: criar evento 20:00→00:30 e conferir `end_at` no dia seguinte
(duração 4h30); mesmo-dia inalterado; início==fim rejeitado; ensaio overnight ok. `ruff` sem erros
novos.

**Constraints**: não quebrar criação normal; manter validação de início==fim; pt-BR; integração com
a agenda (insert_event recebe `st`/`et` em dias diferentes — já suportado, pois a agenda aceita).

**Scale/Scope**: `app/calendar/routes.py` (helper `_build_start_end` + 3 call sites) e
`app/templates/event_create.html` (validação JS + hint).

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Um helper único reaproveitado nos 3 fluxos.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Mesmo-dia e início==fim preservados; verificação em
  `manto_local`.
- Demais princípios: ✅ (mudança mínima).

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/
├── calendar/routes.py
│   ├── _build_start_end(d, start_str, end_str)  # fim < início ⇒ +1 dia
│   ├── create_event           # usa o helper; erro só se fim == início
│   ├── create_ensaio          # idem
│   └── edit_ensaio            # idem
└── templates/event_create.html
    ├── validação JS: bloquear só quando fim == início (permitir virar a noite)
    └── hint "termina no dia seguinte" quando fim < início
```

**Structure Decision**: Helper compartilhado + ajuste de UI. Sem migration.

## Complexity Tracking

> Sem violações.
