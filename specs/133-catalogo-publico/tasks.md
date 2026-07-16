# Tasks — Catálogo Público de Personagens (133)

- [X] T001 `app/models.py`: `CatalogCategory`, `CatalogItem`, `CatalogItemImage` +
      tabela de associação `catalog_item_categories` (padrão de `user_roles`)
- [X] T002 Migration manual (`down_revision` = head atual) — cria as 4 tabelas; checar
      colisão de revision-id antes de finalizar
- [X] T003 `requirements.txt`: adicionar `requests` como dependência direta
- [X] T004 `app/catalogo/importer.py`: `run_import(csv_path, limit=0, echo=None) -> dict`
      — parse do CSV (filtro `Publicado`, dedup por `wp_product_id`, slug com
      desambiguação, categorias `get_or_create`, limpeza de descrição), download +
      `save_file()` por imagem (tolerante a falha individual), reescrita de URL local
      pra rota pública, medição de tamanho + relatório de imagens pesadas (>300KB), item
      sem nenhuma imagem baixada é descartado
- [X] T005 `app/cli.py`: comando `import-wordpress-catalog <path> [--limit N]`
- [X] T006 `app/catalogo/routes.py`: blueprint `catalogo_bp` sem login —
      `GET /catalogo/` (lista + categorias/capa pré-carregadas),
      `GET /catalogo/<slug>` (detalhe + metatags Open Graph com URL absoluta de imagem),
      `GET /catalogo/midia/<filename>` (serve só `catalog_photos`, sem login)
- [X] T007 `app/templates/catalogo/_head_shared.html` + `index.html` + `detail.html` +
      `invalid.html`: página própria (não estende `base.html`), busca client-side por
      nome/tag/categoria, abas "Todos"/seções, galeria no detalhe, botão copiar link,
      estado vazio, design editorial (tipografia própria, não reaproveita `style.css`)
- [X] T008 `app/__init__.py`: registrar `catalogo_bp`
- [X] T009 `app/templates/base.html`: link "📖 Catálogo" no grupo Comercial da sidebar
      (`target="_blank"`)
- [X] T010 Rodar a importação real contra `manto_local` com o CSV fornecido
      (`Produtos Catalogo/wc-product-export-16-7-2026-1784216390934.csv`) e conferir o
      relatório final (importados, descartados, imagens pesadas)
- [X] T011 Verificação funcional vs `manto_local`: reimportação não duplica; nomes
      repetidos viram itens distintos; rascunho descartado; página pública acessível
      sem sessão; busca por tag encontra item; alternância seção/tudo; estado vazio;
      metatags Open Graph com imagem absoluta; rota de mídia não vaza arquivo fora de
      `catalog_photos`; `X-Robots-Tag: noindex` presente
- [X] T012 `ruff check` nos arquivos tocados; changelog (`docs/changelog.html`,
      republicar no link já existente); commit, merge em `main`, push
