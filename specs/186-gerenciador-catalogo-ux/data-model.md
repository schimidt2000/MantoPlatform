# Data Model: Gerenciador de Catálogo — UX e Fluxo Ficha↔Catálogo↔Venda

**Nenhuma migration nesta feature.** Todo o trabalho é de leitura/apresentação (respostas de API
estendidas com campos já existentes no banco) e de reatribuição de uma FK já existente
(`CatalogCharacter.catalog_item_id`, `CatalogCharacter.figurino_sheet_id`) — ambas já nullable/
mutáveis desde a feature 185, sem coluna nova.

## Extensões de forma de resposta (sem mudança de schema)

- `GET /api/catalogo/elenco-busca`: cada Personagem em `temas[].characters[]` ganha `photo_url`.
- `GET /api/admin/catalogo`: cada item ganha `characters: [{id, name, photo_url,
  figurino_sheet_id, is_active}]` (resumo, para a árvore não precisar do detalhe completo).

## Operação nova (sem entidade nova)

- **Mover em massa**: reatribuição transacional de `CatalogCharacter.catalog_item_id` para um
  `target_item_id` comum, para uma lista de `character_ids`. Não cria nem remove nenhuma linha —
  só realoca o vínculo pai↔filho já existente.

## Estado client-side (não persiste no banco)

- Preferência de visualização (Cards/Árvore): `localStorage`, chave
  `manto_admin_catalogo_view`, valores `"cards" | "tree"`.
- Conjunto de itens selecionados para ações em massa: estado React local, não persiste entre
  reloads (intencional — seleção é uma sessão de trabalho pontual).
