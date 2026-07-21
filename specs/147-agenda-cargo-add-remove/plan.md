# Implementation Plan: adicionar/remover cargo (147)

**Branch**: `147-agenda-cargo-add-remove` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

## Summary

Aplica o padrão da feature 146 às ações **add_role** e **delete_role**. Núcleo extraído para
`casting_ops`; handlers Jinja viram wrappers; endpoints REST; verificação por paridade.

## Technical Context

Igual à 146: Python/Flask + React; sem dependência nova; `manto_local` para verificação; sem
mudança de schema.

## Constitution Check

- **I**: núcleo único em `casting_ops` (add_role/delete_role), reusado por Jinja e API.
- **IV**: handlers Jinja viram wrappers com efeito idêntico; **corrige** o bug latente de
  `filter_by(id=string)` no delete (int explícito). Paridade verificada.
- **V**: botões com feedback; adicionar é a única ação que cria linha — o front previne
  clique-duplo (pending); no backend, um clique-duplo criaria 2 cargos (é INSERT), então o
  front é a barreira — documentar.
- **VII**: cachê via `parse_brl` (harmoniza o add, que usava `int()`).

## Project Structure

```text
app/calendar/casting_ops.py   # + add_role(...), delete_role(...)
app/calendar/routes.py        # _handle_add_role / _handle_delete_role viram wrappers (delete corrige int)
app/api/agenda_write.py       # + POST /api/events/<id>/roles, DELETE /api/roles/<id>
frontend/apps/internal/src/
├── lib/casting.ts            # + useAddRole, useDeleteRole
└── pages/EventDetailPage.tsx # form de adicionar cargo + botão remover por cargo (se show_casting)
```

## Design Decisions

1. **RBAC por ação (paridade exata)**: adicionar usa `_CAN_EDIT_EVENT` (o handler add não tem
   gate próprio — herda o do POST); remover exige CASTING/SUPERADMIN (gate do handler delete);
   cargo `accepted` só superadmin remove (regra no núcleo `delete_role`, retorna "não removido").
2. **`delete_role(event, role, *, is_superadmin, actor_name, tz)`** recebe o `role` já buscado
   (adaptadores fazem o fetch com `int` — corrige o bug psycopg3). Retorna bool (removeu?).
3. **`add_role(event, *, character_name, talent_id, cache_value, role_type, actor_name, tz)`**
   cria o cargo, log, convite se tem talento; cachê via `parse_brl`. Retorna o cargo.
4. **Verificação** (`verify_147_cargo.py`): add via API vs Jinja (form) → mesma linha; delete
   via API vs Jinja → mesmo efeito; delete de cargo `accepted` bloqueado p/ não-superadmin em
   ambos; 403 (sem casting no delete), 404, 400 (nome vazio). E-mail mockado. Jinja segue 302.

## Complexity Tracking
*Sem violações.*
