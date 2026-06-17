# Contrato: nome do grupo (definir ao agrupar + ação `rename_group`)

## A) Definir nome ao agrupar — estende `group_events` (053/054)

`POST /events/<int:event_id>` com `action=group_events`.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `action` | string | sim | `group_events`. |
| `target_event_ids` | lista int | sim (≥1) | Eventos a agrupar (feature 054). |
| `leader_event_id` | int | sim | Evento principal. |
| `confirm_clear_financials` | "1"/ausente | condicional | Confirmação (054). |
| `group_name` | string | **não** (opcional) | Nome do grupo; salvo no evento principal. Vazio → fallback para o título. |

Efeito adicional: ao concluir o agrupamento, `leader.group_name = group_name.strip() or None`.

## B) Renomear/limpar nome de um grupo existente — ação `rename_group`

`POST /events/<int:event_id>` com `action=rename_group`.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `action` | string | sim | `rename_group`. |
| `group_name` | string | não | Novo nome; vazio limpa (volta ao fallback). |

### Pré-condições

- RBAC: COMERCIAL/FINANCEIRO/SUPERADMIN (`_can_group_events`). Senão: flash de erro, sem
  efeito.
- `event` deve ser **principal** de um grupo (`is_group_leader`). Se não for: flash de erro
  ("Apenas o evento principal de um grupo pode ser renomeado.").

### Efeito

- `event.group_name = request.form.get("group_name", "").strip() or None`.
- `EventLog` no principal registrando a alteração (auditoria, padrão 053).
- `db.session.commit()`; flash de sucesso.

## Exibição (consumidores do rótulo)

`group_display_name = group_name or title`, usado em:

| Tela | Antes | Depois |
|---|---|---|
| Home comercial — cobranças pendentes | `ev.title` | `ev.group_display_name` |
| Home comercial — eventos sem valor | lista inclui satélites | satélites **ocultos** (`group_leader_id is None`) |
| Painel financeiro — tabela de eventos | `ev.title`, satélites listados | `ev.group_display_name`; satélites **ocultos** |
| Pipeline de vendas — coluna evento (líder) | `ev.title` | `ev.group_display_name` |
| Detalhe do evento — banner satélite / seção principal | só indicação | indicação + **nome do grupo** |

## Não-regressão

- Eventos **não agrupados**: `group_display_name == title` (sem nome) — inalterados.
- Cálculos financeiros consolidados (053): inalterados — apenas a apresentação muda.
