# Data Model: Seleção de eventos no agrupamento (busca + multi-seleção)

## Resumo

**Esta feature não altera o modelo de dados.** Ela reutiliza integralmente o vínculo de
agrupamento introduzido na feature 053. Não há nova coluna, nova tabela nem migration.

## Entidade reutilizada: `CalendarEvent` (tabela `calendar_events`)

Campos e relacionamentos relevantes, **já existentes** (feature 053):

| Campo / Relação | Tipo | Origem | Uso nesta feature |
|---|---|---|---|
| `group_leader_id` | Integer, FK → `calendar_events.id`, nullable | 053 | Satélite aponta para o principal. Setado em massa ao agrupar N eventos. |
| `group_leader` | relationship (remote_side) | 053 | Acesso ao principal a partir do satélite. |
| `satellites` | backref (lista) | 053 | Lista de satélites de um principal. |
| `is_satellite` (property) | bool | 053 | `True` se `group_leader_id is not None`. Marca o evento como não-selecionável na lista. |
| `is_group_leader` (property) | bool | 053 | `True` se tem satélites. Marca o evento como não-selecionável na lista. |
| `event_type` | String | base | Filtro: eventos `"ENSAIO"` são excluídos dos candidatos. |
| `start_at` | DateTime | base | Exibição (data/hora) e ordenação da lista de candidatos. |
| `title` | String | base | Exibição e alvo da busca textual. |
| Campos comerciais (`sale_value`, etc.) | vários | base/052 | Zerados no satélite via `_apply_satellite` (053) ao agrupar. |

## Regras de validação (na confirmação do agrupamento)

Aplicadas a **cada** evento da multi-seleção, no handler `_handle_group_events`
(reaproveitadas da 053, agora em laço sobre N eventos):

| Regra | Requisito | Comportamento |
|---|---|---|
| Pelo menos 1 evento selecionado | FR-003 | Recusa com aviso se a lista vier vazia. |
| Principal ∈ {evento atual} ∪ {selecionados} | FR-004 | Recusa se o `leader_event_id` não for um dos participantes. |
| Nenhum participante é o mesmo que outro (sem auto-grupo) | 053 FR-004 | O evento atual nunca aparece como candidato; principal ≠ duplicado. |
| Nenhum selecionado já é satélite | 053 FR-002 | Recusa apontando o evento; nada é alterado. |
| Nenhum selecionado (nem o principal) já é principal de outro grupo | 053 | Recusa apontando o evento. |
| Nenhum participante é ENSAIO | 053 FR-003 | Recusa; ENSAIO nem aparece na lista. |
| Confirmação se algum selecionado tem venda preenchida | 053 FR-005 / FR-008 | Exige `confirm_clear_financials=1`; senão recusa pedindo confirmação. |

**Atomicidade**: se qualquer regra falhar para qualquer evento da seleção, a operação
inteira é recusada e **nenhum** vínculo é criado (ver `contracts/group-events.md`).

## Efeito do agrupamento (idêntico à 053 — FR-012)

Para cada evento satélite confirmado:
1. `_apply_satellite(satellite)` zera os 14 campos comerciais.
2. `satellite.group_leader_id = leader.id`.
3. Um `EventLog` é gravado no satélite e um no principal (auditoria — FR-009).

Resultado final indistinguível, no banco e no painel financeiro, de um agrupamento feito
pelo fluxo antigo um-a-um.

## Sem migração de dados

Nenhuma. A feature é puramente de interface + handler. Grupos criados antes (pela 053)
continuam válidos e editáveis pela nova tela.
