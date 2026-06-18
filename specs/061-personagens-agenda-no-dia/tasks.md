# Tasks: Personagens já na agenda no dia (calculadora de orçamento)

**Feature**: `061-personagens-agenda-no-dia` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Recurso aditivo: endpoint JSON + bloco na UI da calculadora. Reusa `EventRole`/`CalendarEvent` e
`_require_vendas`. Sem migration. Verificação contra **`manto_local` (Postgres)**.

Convenção: `[P]` = paralelizável; `[US#]` = história relacionada.

---

## Fase 1 — Backend (US1)

- [X] T001 [US1] Em `app/orcamento/routes.py`, adicionar `GET /orcamento/personagens-no-dia` (`@login_required` + `@_require_vendas`): lê `date` (ISO), consulta `EventRole` (`role_type="character"`) join `CalendarEvent` com `func.date(start_at)==data` e `event_type != "ENSAIO"`, agrupa distinto por `character_name` com os títulos dos eventos, retorna JSON `{date, personagens:[{nome, eventos[]}]}`. Data ausente/inválida → `{date:null, personagens:[]}` (sem 500).

## Fase 2 — UI (US1 + US2)

- [X] T002 [US1] Em `app/templates/orcamento/index.html`: dar `id="event_date"` ao input de data e adicionar o container `#agenda-no-dia` logo abaixo do bloco data/horário.
- [X] T003 [US1] JS (em `orcamento.js` ou script da página): ao `change` de `#event_date`, buscar o endpoint e renderizar — bloco de atenção com a lista (nome + evento(s), US2/FR-008), estado vazio ("Nenhum personagem agendado neste dia"), e falha silenciosa (não exibir). Limpar data → esconder.

## Fase 3 — Verificação

- [X] T004 Verificar contra **`manto_local`**: GET do endpoint para uma data com agenda (personagens distintos; apoio/ensaio ausentes; vaga sem talento presente) e uma data vazia (lista vazia); 403 sem permissão. `ruff check` sem erros novos (comparar com `git stash`).

---

## Dependências

- T001 antes de T003 (consumo do endpoint). T002 e T003 no mesmo template/JS.
- T004 ao final.

## MVP

T001 + T002 + T003 entregam o pedido central (lista de personagens do dia abaixo da data).
