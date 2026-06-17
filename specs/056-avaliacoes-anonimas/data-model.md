# Data Model: Avaliações anônimas + função no evento

## Mudança no modelo

Uma adição em `SiteSetting`. Sem nova entidade.

### Novo campo

| Campo | Tipo | Nulo | Default | Uso |
|---|---|---|---|---|
| `SiteSetting.ratings_fully_anonymous` | Boolean | não | `False` (`server_default="0"`) | Modo anônimo total: quando `True`, a autoria fica oculta até para o super admin. |

## Entidades reutilizadas (sem mudança de schema)

| Entidade | Uso nesta feature |
|---|---|
| `EventRating` | Comentário/avaliação; `talent` é o **autor** a ser anonimizado. |
| `EventSubRating` | Comentários por categoria; mesmo tratamento de autoria (autor = rating.talent). |
| `EventRole` | Função/personagem do autor no evento: `character_name` para `(event_id, talent_id)`. |
| `Talent` | Nome do autor (`full_name`) — exibido só quando `show_authors`. |
| `AuditLog` | Registro da alteração do modo total (FR-010). |

## Regra de exibição da autoria (derivada)

```
show_authors = current_user.is_superadmin AND NOT settings.ratings_fully_anonymous
```

| Situação | `author` exibido | função exibida |
|---|---|---|
| Não super admin | "Anônimo" | não |
| Super admin, modo total **off** | nome real | sim (se houver) |
| Super admin, modo total **on** | "Anônimo" | não |

Quando `author == "Anônimo"`, **nenhum** dado identificável (nome, função, link de perfil)
é renderizado (FR-006) — decisão tomada no servidor (`_comment_item`).

## Mapa de funções (derivado, em batch)

`funcs = { (event_id, talent_id): "Personagem A, Personagem B" }` construído com uma única
query a `EventRole` para os pares `(event_id, talent_id)` dos comentários exibidos com
autoria; valor = `character_name` com `strip_role_prefix`, múltiplos unidos por vírgula.

## Regras de validação / comportamento

| Regra | Requisito | Comportamento |
|---|---|---|
| Toggle só super admin | FR-003 | Rota recusa quem não é super admin; botão só renderiza p/ super admin. |
| Persistência global | FR-005 | Flag em `SiteSetting` (id=1), vale para todos os acessos. |
| Anonimato real | FR-006 | Nome/função ausentes do HTML quando anônimo. |
| Função ausente | FR-009 | Sem `EventRole` para o par → exibe só o nome. |
| Auditoria | FR-010 | `AuditLog` ao alternar o modo. |

## Migração

- Manual: `..._ratings_fully_anonymous.py`, `down_revision = r4a5b6c7d8e9`.
- `upgrade`: `add_column(Column("ratings_fully_anonymous", Boolean, nullable=False, server_default="0"))`.
- `downgrade`: `drop_column("ratings_fully_anonymous")`.
- **Sem migração de dados**: nasce desligado → comportamento atual preservado (super admin
  vê autor).
