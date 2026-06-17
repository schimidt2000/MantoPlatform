# Contrato: ação `group_events` (multi-seleção)

Esta feature **estende** a ação existente `group_events` da feature 053 (mesma rota,
mesmo action-dispatch), trocando a seleção de um único evento por **múltiplos**.

## Endpoint

`POST /events/<int:event_id>` (rota `calendar.event_detail` / dispatch em `_EVENT_ACTIONS`)

- `event_id`: o evento a partir do qual a ação é disparada (sempre participante do grupo).

## Campos do formulário

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `action` | string | sim | Valor fixo `group_events`. |
| `target_event_ids` | lista de int (`getlist`) | sim (≥1) | IDs dos eventos marcados na lista para agrupar. **Mudança vs. 053** (antes: `target_event_id` único). |
| `leader_event_id` | int | sim | ID do evento principal escolhido. Deve ser `event_id` ou um dos `target_event_ids`. Padrão no cliente: `event_id`. |
| `confirm_clear_financials` | "1" / ausente | condicional | Obrigatório se algum satélite resultante já tiver `sale_value` preenchido. |

## Pré-condições (RBAC)

- Usuário autenticado com papel `COMERCIAL`, `FINANCEIRO` ou `SUPERADMIN`
  (`_can_group_events()`). Caso contrário: flash de erro, sem efeito.

## Validações (todas devem passar; senão recusa atômica)

1. `target_event_ids` não vazio → senão "Selecione ao menos um evento para agrupar."
2. Cada `target_event_id` existe e não é o próprio `event_id`.
3. `leader_event_id` ∈ {`event_id`} ∪ `target_event_ids`.
4. Participantes do grupo = {evento atual} ∪ {eventos alvo}. O principal é
   `leader_event_id`; os demais participantes viram satélites.
5. Nenhum satélite resultante pode já ser satélite de outro grupo (`is_satellite`).
6. Nenhum participante pode já ser principal de outro grupo (`is_group_leader`).
7. Nenhum participante pode ser `event_type == "ENSAIO"`.
8. Se algum satélite resultante tem `sale_value` preenchido e
   `confirm_clear_financials != "1"` → recusa pedindo confirmação.

Em qualquer falha: `flash(..., "error")` indicando o evento problemático; **nenhuma**
alteração no banco (a seleção do usuário é preservada na tela — FR-010).

## Efeito (sucesso)

Para cada participante que **não** é o principal:
1. `_apply_satellite(satellite)` (zera 14 campos comerciais).
2. `satellite.group_leader_id = leader.id`.
3. `EventLog` no satélite + `EventLog` no principal.

`db.session.commit()` único ao final. Flash de sucesso:
`'Eventos agrupados: "<principal>" é o evento principal (N satélite(s)).'`

Redireciona/renderiza o evento (mesmo comportamento da 053).

## Resposta

- **Sucesso**: redirect para a página do evento, flash de sucesso, grupo persistido.
- **Erro de validação**: flash de erro com o motivo/evento; estado do banco inalterado.

## Compatibilidade

- A ação `ungroup_event` (desagrupar) **não muda** — continua por satélite individual.
- Caso `target_event_ids` traga um único id, o comportamento é equivalente ao da 053
  (N=1), garantindo não-regressão.
