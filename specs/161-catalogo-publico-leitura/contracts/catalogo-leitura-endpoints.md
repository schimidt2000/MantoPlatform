# Contrato de API — Catálogo Público (Leitura)

Segue as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md`
(envelope de sucesso/erro, códigos HTTP). Todos os endpoints abaixo são **públicos** — sem
`@login_required`, sem RBAC — mesma acessibilidade do blueprint `catalogo_bp` hoje. Herdam o
`X-Robots-Tag: noindex, nofollow, noarchive` já aplicado globalmente pelo `after_request` do
app (`app/__init__.py:264`), sem configuração adicional.

## `GET /api/catalogo`

Grade geral — itens ativos, ordenados por nome, mais grade de categorias com contagem
(reaproveita exatamente `catalogo_bp.index`).

- 200:
  ```json
  {
    "items": [
      {
        "id": 1, "name": "Elsa", "slug": "elsa",
        "cover_image_url": "/catalogo/midia/elsa-1.jpg",
        "categories": ["Princesas", "Natal"]
      }
    ],
    "total": 1,
    "categories": [
      {"id": 2, "name": "Princesas", "slug": "princesas", "item_count": 1, "cover_image_url": "..."}
    ],
    "whatsapp_number": "5511970570577"
  }
  ```
- `categories` só inclui categorias com pelo menos 1 item ativo, ordenadas por `item_count`
  desc (mesma regra de `index()` hoje).
- `whatsapp_number` é o mesmo valor de `_whatsapp_target()` (`app/formularios/routes.py`) —
  incluído aqui (em vez de endpoint dedicado) porque a tela de lista de desejos reaproveita este
  mesmo endpoint só para obter o número (evita endpoint novo para 1 campo).
- Sem erro possível (lista vazia → `items: [], total: 0`, não 404).

## `GET /api/catalogo/categorias`

Grade de categorias (reaproveita `catalogo_bp.categorias`).

- 200: `{"categories": [{"id", "name", "slug", "item_count", "cover_image_url"}, ...]}` — só
  categorias com item ativo, ordenadas por nome (mesma ordem de hoje).

## `GET /api/catalogo/categoria/<slug>`

Itens ativos de uma categoria (reaproveita `catalogo_bp.categoria_detail`).

- 200: `{"category": {"id", "name", "slug"}, "items": [CatalogItemSummary, ...]}`
- 404: `{"error": {"message": "Categoria não encontrada"}}` quando o slug não existe ou não tem
  nenhum item ativo (paridade com o 404 da tela Jinja).

## `GET /api/catalogo/<slug>`

Detalhe do item (reaproveita `catalogo_bp.detail`).

- 200:
  ```json
  {
    "id": 1, "name": "Elsa", "slug": "elsa",
    "description_html": "<p>...</p>",
    "categories": [{"name": "Princesas", "slug": "princesas"}],
    "images": [{"url": "/catalogo/midia/elsa-1.jpg", "position": 0}],
    "related": [
      {"id": 2, "name": "Anna", "slug": "anna", "cover_image_url": "...", "categories": ["Princesas"]}
    ]
  }
  ```
- `related`: até 6 itens ativos de mesma categoria, excluindo o próprio item (mesma regra de
  `detail()` hoje).
- 404: `{"error": {"message": "Personagem não encontrado"}}` quando o slug não existe ou o item
  está inativo.
- **Não inclui** campos de Open Graph (`og_title`/`og_image`/etc.) — esses só existem na rota
  Jinja, que segue sendo a fonte da prévia de link (ver `research.md` §4). O frontend React
  ainda define `document.title` via `useEffect`/lib de rota, só por UX da aba, sem pretensão de
  gerar prévia de compartilhamento.

## Fora de escopo desta fatia

Qualquer endpoint de escrita (favoritar é 100% client-side, sem chamada ao servidor — ver
`data-model.md`), endpoint de `/cadastro`, `/f/*` e feedback público — fatias futuras da US5.
