# Implementation Plan: convite / dispensar / restaurar / figurino (148)

**Branch**: `148-agenda-casting-convite-dispensar` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

## Summary

Fecha a paridade de casting em React aplicando o padrão de 146/147 às quatro ações menores.
Núcleo extraído para `casting_ops`; handlers/rotas Jinja viram wrappers finos; quatro endpoints
REST; verificação por paridade contra `manto_local`. Sem mudança de schema.

## Technical Context

Igual à 146/147: Python/Flask + React (Vite/TS/TanStack Query); sem dependência nova;
verificação com test client contra `manto_local` (Postgres), e-mail mockado; requests fora de
`app_context`.

## Constitution Check

- **I**: núcleo único em `casting_ops` (`send_invite`, `set_figurino_done`, `dismiss_role`,
  `restore_role`), reusado por Jinja e API.
- **IV**: adaptadores Jinja com efeito idêntico; paridade verificada campo a campo.
- **V**: botões com feedback (mutations do TanStack); as quatro ações são idempotentes do ponto
  de vista do usuário (UPDATE de coluna, não INSERT) — clique-duplo não gera segundo registro
  relevante. `send_invite` reenvia sempre (comportamento atual preservado), mas o front bloqueia
  o clique enquanto pendente.
- **VII**: sem cachê nesta fatia (nenhuma máscara monetária nova).

## Project Structure

```text
app/calendar/casting_ops.py   # + send_invite, set_figurino_done, dismiss_role, restore_role
app/calendar/routes.py        # _handle_send_invite / _handle_figurino_done / dismiss_role /
                              #   restore_role viram wrappers finos sobre o núcleo
app/api/agenda_write.py       # + POST /api/roles/<id>/{invite,dismiss,restore,figurino-done}
app/api/agenda_read.py        # _serialize_role expõe `dismissed`
frontend/apps/internal/src/
├── lib/casting.ts            # + useSendInvite, useSetFigurinoDone, useDismissRole, useRestoreRole
└── pages/EventDetailPage.tsx # botões por cargo conforme RBAC (convite/figurino/dispensar-restaurar)
```

## Design Decisions

1. **RBAC por ação (paridade exata)**, aplicada no endpoint antes de chamar o núcleo:
   - `invite` **e** `figurino-done` → `_can_edit_event()` (`_CAN_EDIT_EVENT`). No Jinja ambos são
     despachados pelo POST de `/events/<id>`, gateado por quem pode editar o evento — sem gate
     próprio de Figurino. A auditoria do código confirmou isso (a suposição inicial de "figurino =
     Figurino/superadmin" estava errada); paridade exige o mesmo gate do POST.
   - `dismiss`/`restore` → só superadmin; `dismiss` exige cargo sem talento (retorno do núcleo
     sinaliza bloqueio, vira 400 — igual ao `flash` de erro do Jinja).
2. **Assinaturas do núcleo** (todas recebem o `role` já buscado com `int` e `actor_name`/`tz`):
   - `send_invite(event, role, *, actor_name, tz) -> bool` — retorna se o e-mail saiu (só p/ o
     `flash` do adaptador Jinja; a API ignora). Mantém o envio **síncrono** de hoje
     (`send_invite_email`, não `send_async`) para não mudar o comportamento observável do Jinja.
   - `set_figurino_done(event, role, *, actor_name, tz) -> None`.
   - `dismiss_role(role, *, actor_name) -> bool` — False se o cargo tem talento (bloqueio). Usa
     `datetime.utcnow()` e `dismissed_by` como hoje; o adaptador passa `dismissed_by`.
   - `restore_role(role, *, actor_name) -> None`.
   Obs.: dispensar/restaurar operam sobre o cargo (não recebem `event`); o log usa `role.event_id`
   e `actor_role="Casting"`, como o Jinja atual.
3. **`dismissed_by`**: o núcleo precisa do id de quem dispensa. Passa-se `dismissed_by` explícito
   (o adaptador Jinja usa `current_user.id`; a API idem) — mantém o núcleo sem `current_user`.
4. **Serializer**: `_serialize_role` ganha `"dismissed": role.dismissed_at is not None` para a
   tela React escolher entre botão "dispensar" e "restaurar" (paridade com o Jinja, que mostra um
   ou outro). Campo novo é aditivo — não quebra os consumidores da 145/146/147.
5. **Verificação** (`verify_148_casting.py`): para cada ação, roda via API e via Jinja em cargos
   equivalentes e compara o estado resultante campo a campo; cobre os 403 (figurino sem papel;
   dispensar/restaurar sem superadmin), o bloqueio de dispensar cargo com talento, e o reenvio de
   convite sem talento (no-op). E-mail mockado; Jinja segue 302; API 200. ruff/tsc/build limpos.

## Complexity Tracking
*Sem violações.*
