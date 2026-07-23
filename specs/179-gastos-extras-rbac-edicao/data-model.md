# Data Model: Gastos Extras — RBAC, edição, "Aprovado com edições"

## `SpecialExpense` (tabela `special_expenses`) — mudança

Coluna nova (todas as demais colunas e `STATUSES` permanecem exatamente como estão hoje):

| Coluna                 | Tipo      | Default | Nullable | Descrição |
|-------------------------|-----------|---------|----------|-----------|
| `approved_with_edits`   | `Boolean` | `False` | Não      | `True` quando o gasto está `status == "aprovado"` e os dados foram alterados na mesma operação (ou em uma edição posterior) que resultou/manteve o gasto aprovado. Nunca `True` para `status` `"pendente"` ou `"rejeitado"`. |

Nenhuma mudança em `STATUSES = ["pendente", "aprovado", "rejeitado"]` — ver `research.md` §1
para o porquê.

### Regra de transição de `approved_with_edits`

- `create_expense`: sempre `False` (gasto novo, nunca editado).
- `approve_expense` (aprovação rápida, 1 clique, sem edição — usada pela Jinja e pela API): não
  altera `approved_with_edits` (permanece `False`, pois não há função nova envolvida).
- `edit_expense` (nova, só API): calcula `changed` comparando os campos editáveis
  (descrição/categoria/valor/data/desembolso+payee/evento) ANTES de sobrescrever.
  - Se `aprovar=True`: seta `status="aprovado"`, `approved_by_id`, `approved_at`.
  - Se o `status` final é `"aprovado"` (já era, ou acabou de virar) **e** `changed`: seta
    `approved_with_edits=True`.
  - Editar um gasto `"pendente"` sem `aprovar=True`: `status` não muda, `approved_with_edits`
    não muda (fica `False`).
  - Editar um gasto `"rejeitado"` só é permitido com `aprovar=True` (reconsiderar).

## Estados de exibição (frontend, derivado — não persistido)

| `status`     | `approved_with_edits` | Rótulo exibido        |
|--------------|------------------------|------------------------|
| `pendente`   | —                       | Pendente               |
| `aprovado`   | `false`                 | Aprovado               |
| `aprovado`   | `true`                  | Aprovado c/ edições    |
| `rejeitado`  | —                       | Rejeitado              |

## RBAC (não é uma entidade de dado nova — é lógica de leitura sobre `User.roles` já existente)

- **Colaborador comum** (nenhum papel `SUPERADMIN` nem `FINANCEIRO`): só os gastos com
  `created_by_id == user.id`.
- **`FINANCEIRO` ou `SUPERADMIN`**: todos os gastos, mais os totais agregados por status.

Esta é a mesma tabela `roles`/`user_roles` já existente (`app/models.py`) — nenhum papel novo é
criado.
