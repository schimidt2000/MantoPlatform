# Tasks: Ensaios órfãos contam só a partir da data de início do sistema

**Feature**: `060-ensaios-orfaos-data-inicio` | **Spec**: [spec.md](spec.md)

Mudança cirúrgica que reaproveita o `task_cutoff` (derivado de `release_date`) já calculado na
rota home. Sem migration. Verificação contra **`manto_local` (Postgres)**.

---

## Fase 1 — Implementação (US1)

- [X] T001 [US1] Em `app/__init__.py` (rota `home`), aplicar o corte `CalendarEvent.start_at >= task_cutoff` ao filtro de `orphan_ensaios` (que hoje inclui todas as datas). Atualizar o comentário que diz "Inclui datas passadas".

## Fase 2 — Verificação

- [X] T002 Verificar contra **`manto_local`**: com `release_date` definido, órfãos anteriores não aparecem e órfãos a partir da data aparecem; com `release_date` nulo, corte = hoje. Conferir que a feature 057 (cancelar órfão) segue intacta. `ruff check` sem erros novos.

---

## Dependências

- T002 após T001.

## MVP

T001 já entrega o pedido (remover órfãos do passado da home).
