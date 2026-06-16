# Contrato de Rotas: Agrupamento de Eventos por Contrato

**Feature**: 053-agrupar-eventos | **Date**: 2026-06-16

Aplicação monolítica Flask — as rotas abaixo são endpoints HTML
(form POST + redirect), seguindo o padrão já usado em todo o módulo
`calendar` (não é uma API JSON separada).

## `POST /eventos/<int:event_id>/agrupar`

**Blueprint**: `calendar_bp` (`app/calendar/routes.py`)

**Acesso**: COMERCIAL, FINANCEIRO, SUPERADMIN (FR-001)

**Body (form)**:
| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `target_event_id` | int | sim | Id do outro evento a vincular |
| `leader_event_id` | int | sim | Qual dos dois (event_id ou target_event_id) será o principal |
| `confirm_clear_financials` | bool | condicional | Obrigatório `true` se o evento que vai se tornar satélite já tiver `sale_value` preenchido (FR-005) |

**Validações** (ver data-model.md):
- 400/flash de erro se `target_event_id == event_id` (FR-004)
- 400/flash de erro se qualquer um dos dois já for satélite (FR-002)
- 400/flash de erro se qualquer um dos dois já for principal de outro grupo (estrutura plana)
- 400/flash de erro se qualquer um dos dois for `event_type == "ENSAIO"` (FR-003)
- 400/flash de erro se o satélite resultante tiver campos comerciais preenchidos e `confirm_clear_financials != true`

**Sucesso**: define `satellite.group_leader_id = leader.id`, zera campos
comerciais do satélite (data-model.md), grava log de auditoria (FR-015),
`flash("Eventos agrupados com sucesso")`, redirect para
`event_detail(leader_event_id)`.

---

## `POST /eventos/<int:event_id>/desagrupar`

**Blueprint**: `calendar_bp`

**Acesso**: COMERCIAL, FINANCEIRO, SUPERADMIN (mesma regra do agrupar)

**Body**: nenhum campo extra — `event_id` na URL é sempre o satélite a
desvincular.

**Validações**:
- 400/flash de erro se `event.group_leader_id is None` (não é satélite)

**Sucesso**: `event.group_leader_id = None`, campos comerciais permanecem
zerados/editáveis (FR-008, SC-005 — elenco/figurino do evento não são
tocados), grava log de auditoria (FR-015), `flash("Agrupamento desfeito")`,
redirect para `event_detail(event_id)`.

---

## Alterações em rota existente: exclusão de evento

**Rota existente**: presumivelmente `POST /eventos/<int:event_id>/excluir` ou
equivalente em `app/calendar/routes.py` (confirmar nome exato na
implementação).

**Nova validação** (FR-009): se `event.is_group_leader` (tem satélites),
bloquear exclusão com mensagem orientando a desagrupar os satélites primeiro.

---

## Alterações em `event_detail.html` (sem rota nova, apenas UI)

- Se `event.is_satellite`: banner "Este evento faz parte do grupo de
  **{{ event.group_leader.title }}**" com link; campos comerciais renderizados
  como somente leitura (valores herdados do principal); botão "Desfazer
  agrupamento" (com confirmação — Princípio V).
- Se `event.is_group_leader`: seção "Eventos agrupados a este contrato"
  listando `event.satellites` (título + data, link para cada); botão
  "Agrupar outro evento" abre seletor de evento existente.
- Se nenhum dos dois: botão "Agrupar a outro evento" disponível (visível só
  para COMERCIAL/FINANCEIRO/SUPERADMIN).

## Alterações em `app/financeiro/routes.py` (sem rota nova, apenas cálculo)

Sem novos endpoints — `research.md` (itens 3 e 4) já descreve as mudanças de
agregação (`_group_cost`) e filtro (`group_leader_id is None`) aplicadas às
rotas GET já existentes (`/financeiro/`, `/vendas/`).
