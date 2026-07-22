# Data Model: Catálogo Público em React (Leitura)

Nenhum modelo novo, nenhum campo novo, nenhuma migration. Esta fatia só lê 3 tabelas já
existentes (`app/models.py`). Os shapes abaixo são a forma de resposta JSON dos 4 endpoints —
não alteram o schema do banco.

## Entidades existentes (leitura)

### CatalogItem → `CatalogItemSummary` (usado nas listas) / `CatalogItemDetail` (usado no detalhe)

| Campo Python (`CatalogItem`) | Campo JSON (summary) | Campo JSON (detail) | Observação |
|---|---|---|---|
| `id` | `id` | `id` | — |
| `name` | `name` | `name` | — |
| `slug` | `slug` | `slug` | chave de rota (`/:slug`) |
| `short_description_html` | — | `description_html` | só no detalhe; renderizado com `dangerouslySetInnerHTML` (mesmo HTML confiável — vem de conteúdo interno importado, não de usuário externo) |
| `tags_list` (property) | — (usado só no `search_text` server-side hoje; nesta fatia a busca é client-side sobre `name`+`tags`+categorias já enviados) | — | ver FR-002 na spec 156-like: busca client-side |
| `categories` | `categories: string[]` (nomes) | `categories: {name, slug}[]` | detalhe inclui slug p/ link "ver mais em X" |
| `cover_image` (property) | `cover_image_url: string \| null` | — | capa para card |
| `images` (ordenado por `position`) | — | `images: {url, position}[]` | galeria completa, já ordenada |
| `is_active` | (filtro — só itens `True` aparecem) | (idem) | nunca exposto como campo (implícito: se apareceu, está ativo) |

### CatalogCategory → `CatalogCategorySummary`

| Campo Python | Campo JSON | Observação |
|---|---|---|
| `id` | `id` | — |
| `name` | `name` | — |
| `slug` | `slug` | chave de rota (`/categoria/:slug`) |
| (calculado) | `item_count: number` | quantidade de itens ativos nessa categoria |
| (calculado) | `cover_image_url: string \| null` | foto de capa do primeiro item da categoria |

### CatalogItemImage → `{url: string, position: number}`

Leitura direta, sem transformação.

## Sem estado local persistido no servidor

A lista de desejos (favoritos) não é uma entidade de banco — é só `localStorage` no navegador
(`lib/wishlist.ts`, ver `research.md` §5). Nenhum endpoint de escrita nesta fatia.
