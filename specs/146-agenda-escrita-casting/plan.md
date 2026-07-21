# Implementation Plan: Agenda/Eventos — escrita de casting (146, US1 escalar)

**Branch**: `146-agenda-escrita-casting` (criado no implement) | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/146-agenda-escrita-casting/spec.md`

## Summary

Primeira migração de ESCRITA. Cobre a fatia **P1 — escalar/atualizar talento num cargo**
(`assign_casting`), a ação mais rica e o pattern-setter das escritas. As demais (adicionar/
remover cargo, convite, dispensar/restaurar, figurino) são US2/US3, com seu próprio ciclo.

A lógica de `_handle_assign_casting` é densa (teto de cachê, transições de convite, reset de
figurino, **e-mails**, EventLog). Reimplementá-la na API divergiria com o tempo (Princípio I).
Estratégia: **extrair o núcleo** para uma operação com parâmetros explícitos, chamada por dois
caminhos finos — o handler Jinja atual (lê `request.form`, dá `flash`) e o endpoint JSON novo
(lê JSON, devolve o evento serializado). UMA implementação da regra; dois adaptadores de I/O.

## Technical Context

**Language/Version**: Python 3.11 (backend) + TypeScript/React (frontend).

**Primary Dependencies**: nenhuma nova — reusa `parse_brl`/`format_brl` (backend), `@manto/money`,
`@manto/ui`, `@manto/api-client`, TanStack Query, react-hook-form/zod, Framer Motion (já instalados).

**Storage**: PostgreSQL (`manto_local` p/ verificação). Sem mudança de schema.

**Testing**: script contra `manto_local` — **paridade de estado**: executar a ação pela API e
pelo caminho Jinja (test client, form) e afirmar que produzem o MESMO estado em `event_roles`
+ `EventLog`, e que o estado bate com o esperado (cap aplicado, invite=pending, assigned_at,
figurino resetado). **E-mail é isolado/mockado** (monkeypatch de `send_async`) — nada de e-mail
real. Frontend: `tsc`/`vite build`.

**Target Platform**: `apps/internal` (staff), consumido em `beta`.

**Project Type**: web app desacoplado (monorepo existente).

**Constraints**: coexistência — o handler Jinja `_handle_assign_casting` deve continuar
produzindo exatamente o mesmo efeito de hoje após virar um wrapper fino; RBAC no servidor;
`prefers-reduced-motion`; cachê pt-BR via `@manto/money`.

**Scale/Scope**: 1 endpoint (`POST /api/roles/<id>/assign`), 1 extração de handler, 1 form
React no detalhe do evento.

## Constitution Check

- **I. Reutilizar antes de criar**: núcleo de casting extraído para UMA função reusada por
  Jinja e API; conflito via `_talent_time_conflict` existente; serialização de retorno via
  `serialize_event_detail` (feature 145). Zero duplicação de regra.
- **III. API First**: `POST /api/roles/<id>/assign` retorna JSON (o evento atualizado).
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL aqui)**: o handler Jinja vira wrapper que
  chama o mesmo núcleo — a verificação prova que o caminho Jinja segue idêntico (paridade
  Jinja×API + estado esperado). É o maior risco desta fatia; a verificação é desenhada em
  torno dele.
- **V. Feedback + sem duplicado**: o botão de escalar dá feedback imediato (mutation pending);
  reenvio não duplica (a operação é idempotente — atualiza a mesma linha do cargo, não cria).
- **VII. Monetário pt-BR**: cachê via `@manto/money` no front; `parse_brl` no back.
- **IX. Movimento**: atualização da tela após escalar com transição suave.

Nenhuma violação; a atenção máxima é o Princípio IV (coexistência).

## Project Structure

### Documentation
```text
specs/146-agenda-escrita-casting/
├── plan.md, spec.md, research.md, data-model.md, quickstart.md
├── contracts/api-conventions.md
└── checklists/requirements.md
```

### Source Code
```text
app/
├── calendar/
│   ├── casting_ops.py    # NOVO: assign_role(event, role, *, talent_id, cache_value, travel_cache,
│   │                     #   actor_name, is_superadmin, tz) -> ResultadoOperacao (msg + evento).
│   │                     #   Faz DB + EventLog + e-mails. SEM request.form, SEM flash, SEM current_user.
│   └── routes.py         # _handle_assign_casting vira wrapper fino: lê form + current_user,
│                         #   chama assign_role, dá flash(result.message). Comportamento idêntico.
└── api/
    └── agenda_write.py   # NOVO: POST /api/roles/<id>/assign — lê JSON + current_user, chama
                          #   assign_role, retorna serialize_event_detail(event) (RBAC).

frontend/apps/internal/src/
├── lib/casting.ts        # useAssignRole(eventId) — mutation TanStack Query; invalida ["event", id]
└── pages/EventDetailPage.tsx  # bloco de elenco ganha ação de escalar (só se flags.show_casting):
                               #   seletor de talento + MoneyInput de cachê; botão com feedback.
```

## Design Decisions

1. **Núcleo em `casting_ops.assign_role(...)`** recebendo tudo explícito (talento, cachê já
   parseado ou cru?, actor, is_superadmin, tz). Decisão: recebe os **valores crus** (string de
   cachê) e faz `parse_brl` internamente, para o parsing (e o teto de cap) ficarem numa fonte
   só — Jinja e API mandam o cru. Retorna um objeto simples `{message, ok}` para o wrapper Jinja
   dar `flash` e a API ignorar. E-mails são disparados dentro do núcleo (é o comportamento a
   preservar), via `send_async` — que a verificação monkeypatcha.

2. **Handler Jinja vira wrapper**: `_handle_assign_casting(event, tz)` passa a: ler
   `request.form`, montar os args, chamar `assign_role(...)`, e `flash(result.message)`. Nada
   da regra fica no wrapper. Risco controlado pela verificação de paridade.

3. **Endpoint**: `POST /api/roles/<id>/assign` (a role pertence a um evento; valida
   `role.event_id`). Body `{talent_id, cache_value, travel_cache}`. RBAC: mesmo gate de edição
   de casting (CASTING/SUPERADMIN; cap só superadmin). 403 JSON se não pode; 404 se role não
   existe. Sucesso: `serialize_event_detail(event, current_user, impersonate)` — a tela
   re-renderiza com o mesmo formato de leitura da 145.

4. **Conflito**: exposto na LEITURA como aviso (o `availability` da view era do seletor). Nesta
   fatia, o endpoint NÃO bloqueia por conflito (o Jinja também não bloqueia — só sinaliza na
   UI); a checagem de conflito visual pode vir junto ao seletor depois. Mantém paridade com o
   Jinja (que grava mesmo com conflito, só avisa). Documentar isso explicitamente.

5. **Verificação (o núcleo)**: `scripts/db/verify_146_casting_write.py` — monkeypatcha
   `send_async` (captura e-mails sem enviar); num cargo de teto conhecido, escala via API e
   afirma o estado (talent_id, cache respeitando cap p/ não-superadmin, assigned_at,
   invite_status=pending, figurino_done_at=None, EventLog criado, 1 convite "enviado"); repete
   a MESMA entrada pelo caminho Jinja (test client, form) num cargo gêmeo e afirma estado
   idêntico; cobre 403 (papel sem permissão), 404 (role inexistente), e idempotência (reenviar
   não cria 2º convite/linha). Limpa os dados de teste.
```

## Complexity Tracking

*Sem violações — tabela não aplicável.*
