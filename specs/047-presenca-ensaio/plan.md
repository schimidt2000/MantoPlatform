# Implementation Plan: Presença é tarefa do ensaio (não do casting)

**Branch**: `047-presenca-ensaio` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)

## Summary

Sem migration. A vaga "Técnico de Som (Presença)" é uma `EventRole` sem `talent_id`, então cai em
`pending_casting`. Mudanças:

1. Constante `PRESENCE_CHARACTER` em `app/calendar/routes.py` (reusar nos 3 literais existentes).
2. `app/__init__.py` (home): excluir a presença do `pending_casting` e das contagens
   `total_casting`/`done_casting`; adicionar `pending_presence` (shows futuros sem presença) ao
   bloco do ensaio.
3. `app/templates/home.html`: subseção "Falta definir presença" no painel Ensaio + badge no header.

## Constitution Check
- **I. Reutilizar** ✅ — constante única; mesmo padrão de tarefas/sector-panel.
- **IV. Não quebrar** ✅ — ação de definir presença (já restrita ao ensaio) inalterada; PIX Nivaldo
  intacto; Coordenador e demais extras seguem como hoje.
- **V. UI/UX** ✅ — tarefa no setor certo, com link e contagem.

## Design Detalhado

### 1. `app/calendar/routes.py`
- `PRESENCE_CHARACTER = "Técnico de Som (Presença)"` perto de `SOUND_TECH_TALENT_ID`.
- Substituir os literais em `_handle_assign_tech_presence` e `_ensure_sound_technician`.

### 2. `app/__init__.py` — home
- `from app.calendar.routes import PRESENCE_CHARACTER` (import local na rota).
- `pending_casting`: `+ filter(EventRole.character_name != PRESENCE_CHARACTER)`.
- `total_casting`/`done_casting`: idem exclusão.
- Bloco ensaio (`if show_ensaio`): `pending_presence` =
  ```
  EventRole.talent_id.is_(None),
  EventRole.character_name == PRESENCE_CHARACTER
  + join CalendarEvent + exclude_ensaios + start_at >= agora(SP)
  ```
  passar `pending_presence` ao template.

### 3. `app/templates/home.html`
- Header do Ensaio: badge "{{ pending_presence|length }} sem presença" quando houver.
- Corpo: subseção "Falta definir presença" listando evento + data + link "Definir".

## Verificação
- ruff (sem novos) + boot.
- Test client: criar SHOW futuro com role de presença vazia →
  - casting (impersonate) NÃO vê presença em pending_casting; estatística não conta;
  - ensaio (impersonate) vê "Falta definir presença"; ao atribuir talento, some;
  - show passado com presença vazia não aparece. Seeds limpos no finally.

## Project Structure
```text
app/calendar/routes.py        # PRESENCE_CHARACTER + uso
app/__init__.py               # exclui do casting; pending_presence para ensaio
app/templates/home.html       # subseção presença no painel Ensaio
```

## Fora de escopo
- Mudar quem pode preencher a presença (já é ensaio/superadmin).
- Outros extras (Coordenador etc.) seguem como hoje.
