# Implementation Plan: Catálogo — tags/categorias criáveis, navegação por categoria, produtos relacionados e lista de desejos

**Branch**: `140-catalogo-descoberta-lista-desejos` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/140-catalogo-descoberta-lista-desejos/spec.md`

## Summary

Cinco melhorias sobre o módulo de catálogo (admin em `/admin/catalogo/...`, feature 139;
público em `/catalogo/...`, feature 133), cada uma independentemente entregável:

1. **Tags com autocomplete + criação inline** no formulário de produto — mesmo padrão de
   busca/seleção já usado para talentos (`.ts-wrap`/`initSearch()`, feature 138), adaptado
   para múltiplos valores (chips) em vez de um só.
2. **Categorias criáveis** — hoje só existem via importação do CSV; ganham um endpoint
   pequeno de criação (get-or-create, insensível a maiúsculas/acentos), usado tanto no
   formulário de produto quanto na tela de gestão do catálogo.
3. **Navegação pública por categoria** — nova página `/catalogo/categorias` (grade de
   categorias) e `/catalogo/categoria/<slug>` (produtos daquela categoria, fotos maiores).
4. **Produtos relacionados** — seção nova na página do produto (`/catalogo/<slug>`),
   mesma categoria, excluindo o próprio.
5. **Lista de desejos** — widget flutuante 100% client-side (localStorage, sem tabela nova
   nem login) presente em todas as páginas públicas do catálogo, mais uma página
   `/catalogo/lista-desejos` que monta a mensagem e abre o WhatsApp comercial já
   configurado no sistema (`SiteSetting.whatsapp_form_number`, mesmo usado pelos
   formulários de pré-contrato — feature 118).

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy + Jinja2; JavaScript vanilla
(sem framework) nos templates públicos e no admin

**Primary Dependencies**: nenhuma nova. Reaproveita `_slugify` (`app/catalogo/importer.py`),
o padrão `.ts-wrap`/`initSearch` de busca+seleção (`event_detail.html`, feature 138,
adaptado para múltipla seleção), e `_whatsapp_target`/`DEFAULT_WHATSAPP_NUMBER`
(`app/formularios/routes.py`, feature 118) para o número de WhatsApp da lista de desejos

**Storage**: PostgreSQL — nenhuma migration nova. `CatalogCategory`/`CatalogItem.tags` já
existem; lista de desejos não é persistida no servidor (localStorage do navegador)

**Testing**: script de verificação funcional com Flask test client contra `manto_local`
(padrão do projeto) para as partes server-side (criação de categoria/tag, páginas novas,
produtos relacionados); a lista de desejos (100% client-side) é verificada por
`node --check` no JS extraído + simulação dos cenários com um stub de `localStorage`,
já que não há navegador automatizado no projeto

**Target Platform**: aplicação web server-side (Flask + Jinja2) — parte admin autenticada,
parte pública sem login

**Project Type**: web application (monolito Flask existente)

**Performance Goals**: N/A — catálogo já opera com centenas de itens; consultas novas
(produtos relacionados, contagem por categoria) são do mesmo porte das já existentes no
index público

**Constraints**: a página pública deve continuar sem login, `noindex`, mobile-first
(mesmos requisitos não-negociáveis das features 133/139); nenhuma migration de schema

**Scale/Scope**: 2 blueprints existentes (`admin_bp`, `catalogo_bp`) ganham rotas novas;
templates públicos novos (`categorias.html`, `categoria_detail.html`, `lista_desejos.html`,
`_wishlist_widget.html` parcial) e um endpoint pequeno de criação de categoria

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: núcleo da decisão de design em todas as 5 histórias —
  ver "Primary Dependencies" acima. O padrão `.ts-wrap` (feature 138) é estendido, não
  reescrito, para virar um seletor de múltiplos valores (tags/categorias). Nenhuma tabela
  nova, nenhum sistema de sessão/carrinho novo no servidor.
- **II. Padrões de código Python**: funções novas com type hints/docstring; endpoint de
  criação de categoria pequeno e único (não duplicado entre as duas telas que o usam).
- **III. Arquitetura em camadas**: rotas orquestram; nenhuma regra de negócio nova além de
  normalização de texto (slug/case-insensitive), que já é o mesmo padrão usado em
  `_slugify`/`_unique_catalog_slug` (feature 139).
- **IV. Não quebrar o que funciona**: a página inicial do catálogo (`/catalogo/`) e a de
  produto (`/catalogo/<slug>`) continuam funcionando como hoje — as mudanças são aditivas
  (nova seção de relacionados, novo widget flutuante), não uma reescrita; verificação
  funcional cobre explicitamente que o comportamento de hoje não regride.
- **V. UI/UX consistente e com feedback**: novas páginas públicas seguem a paleta/tipografia
  já estabelecida (`--cat-*`, `.cat-btn`, `.cat-chip`, fontes Fraunces/Manrope) de
  `_head_shared.html` — nenhum estilo novo desalinhado; formulário admin segue o padrão de
  erro/preservação de campos já usado (feature 134/139).
- **VIII. Superfícies públicas são mobile-first**: as páginas novas (categorias, categoria,
  lista de desejos) seguem o mesmo grid responsivo já usado em `index.html`/`detail.html`.

Nenhuma violação. Gate passa sem exceções.

## Project Structure

### Documentation (this feature)

```text
specs/140-catalogo-descoberta-lista-desejos/
├── plan.md              # This file
├── spec.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

Sem `research.md`/`data-model.md`/`contracts/`: sem incógnita técnica (precedentes diretos
já existem no código para cada peça), sem entidade de banco nova.

### Source Code (repository root)

```text
app/
├── admin/
│   └── routes.py            # + POST /admin/catalogo/categorias (get-or-create);
│                             #   catalogo_admin_new/edit passam all_tags ao template;
│                             #   normalização de tags (case/accent-insensitive) ao salvar
├── catalogo/
│   └── routes.py            # + GET /categorias, GET /categoria/<slug>;
│                             #   detail() ganha `related` (produtos da mesma categoria);
│                             #   + GET /lista-desejos (só injeta o nº de WhatsApp)
└── templates/
    ├── admin_catalogo_form.html    # campo de tags vira seletor múltiplo (chips);
    │                                #   categorias ganham "+ nova categoria" inline
    ├── admin_catalogo_list.html    # "+ nova categoria" inline no filtro
    └── catalogo/
        ├── index.html               # inclui _wishlist_widget.html
        ├── detail.html              # + seção "Você também pode gostar"; inclui o widget
        ├── categorias.html          # nova — grade de categorias
        ├── categoria_detail.html    # nova — produtos de uma categoria, fotos maiores
        ├── lista_desejos.html       # nova — vê/remove itens e envia pro WhatsApp
        └── _wishlist_widget.html    # novo parcial — botão flutuante + JS localStorage,
                                      #   incluído em index/detail/categorias/categoria_detail
```

## Design Decisions

### 1. Tags — seletor múltiplo com autocomplete + criação inline

- Backend (`catalogo_admin_new`/`catalogo_admin_edit`): calcula `all_tags` (lista de tags
  distintas em todos os `CatalogItem.tags`, deduplicada por `_slugify`, mantendo a
  primeira grafia vista) e passa ao template.
- Template: campo de tags deixa de ser `<input name="tags">` de texto livre e vira um
  componente de chips: input de busca + dropdown (filtra `all_tags` client-side, mesmo
  padrão de `filter()`/`render()` de `initSearch` — feature 138) + opção "criar '<texto>'"
  quando não há correspondência exata; cada tag escolhida vira um chip removível; um
  `<input type="hidden" name="tags">` é preenchido (join por vírgula) antes do submit —
  **contrato do backend não muda** (`request.form.get("tags").split(",")` continua igual).
- Servidor, ao salvar: normaliza cada tag recebida contra `all_tags` (case/accent-
  insensitive via `_slugify`) — se uma tag enviada bate com uma já existente, usa a grafia
  já existente (evita "Natal" e "natal" coexistirem por digitação inconsistente, FR-003).

### 2. Categorias criáveis

- `POST /admin/catalogo/categorias` (`@require_superadmin`, JSON): recebe `name`; get-or-
  create por `slug=_slugify(name)` (FR-006); retorna `{"id": ..., "name": ...}`.
- No formulário de produto: ao lado da lista de checkboxes de categoria, um campo "+ nova
  categoria" (texto + botão) que chama esse endpoint via `fetch`, e ao receber a resposta
  adiciona um novo checkbox (já marcado) na lista, sem reload de página (FR-004).
- Na tela de gestão (`admin_catalogo_list.html`): mesmo campo, reaproveitando o mesmo
  endpoint, adiciona a categoria à `<select>` de filtro (FR-005) — não precisa de reload.

### 3. Navegação pública por categoria

- `GET /catalogo/categorias`: mesma lógica de contagem já usada em `index()` (`category_
  counts`), mas retornando todas as categorias com contagem > 0, cada uma com uma foto
  representativa (capa do primeiro produto ativo daquela categoria, por nome).
- `GET /catalogo/categoria/<slug>`: 404 (`catalogo/invalid.html`, mesmo padrão de produto
  inexistente) se a categoria não existe ou não tem produto ativo; senão, lista os
  produtos ativos daquela categoria com uma variante de grid de foto maior (classe CSS
  nova `.cat-grid-lg`, mesma família de `.cat-card`, só com `aspect-ratio`/`grid-template-
  columns` diferentes — sem duplicar o componente).
- Link para `/catalogo/categorias` adicionado no cabeçalho/rodapé de `index.html` e
  `detail.html` (mesma `.cat-shell`/`.cat-eyebrow`).

### 4. Produtos relacionados

- Em `detail()`: se `item.categories`, busca até 6 outros `CatalogItem` ativos que
  compartilhem ao menos uma categoria, ordenados por nome; passa como `related`.
- Template: nova seção abaixo de `.cat-detail-grid`, reaproveitando `.cat-card`/`.cat-grid`
  (mesmo componente do index) — sem CSS novo além do já existente; só renderiza se
  `related` não é vazio (FR-009).

### 5. Lista de desejos (100% client-side)

- Novo parcial `catalogo/_wishlist_widget.html`: botão flutuante fixo (canto inferior
  direito, `.cat-btn`) mostrando a contagem, incluído em `index.html`, `detail.html`,
  `categorias.html`, `categoria_detail.html`. Cada card/produto ganha um botão "♡
  Adicionar à lista" com `data-slug`/`data-name`/`data-cover` — ao clicar, um script
  compartilhado (`/static/js/catalogo-wishlist.js`, novo arquivo, carregado nas páginas
  públicas do catálogo) lê/escreve um array em `localStorage` (chave
  `manto_catalogo_wishlist`), atualiza o contador do botão flutuante em todas as páginas
  (recalculado a cada carregamento) e o estado visual do botão do produto (já
  adicionado/não).
- `GET /catalogo/lista-desejos`: página server-rendered só para injetar o número de
  WhatsApp (`data-wa-number` no `<body>`, resolvido do lado do servidor com o mesmo
  helper `_whatsapp_target()`/`DEFAULT_WHATSAPP_NUMBER` de `app/formularios/routes.py`,
  reaproveitado via import — sem duplicar a lógica de fallback). Todo o conteúdo da
  lista (itens, remoção, contagem) é montado no carregamento via JS lendo o
  `localStorage` — nenhum dado de produto precisa vir do servidor nessa página, porque o
  widget já guarda nome/foto/slug no momento em que o item foi adicionado.
  - Botão "Enviar para o vendedor" desabilitado quando a lista está vazia (FR-014); ao
    clicar, monta a mensagem (nome de cada produto + link `/catalogo/<slug>`) e abre
    `https://api.whatsapp.com/send?phone=<numero>&text=<mensagem>` numa nova aba — mesmo
    formato de URL já usado por `_whatsapp_link()` (feature 118), só montado em JS em vez
    de Python, porque aqui não há round-trip ao servidor.

### 6. Verificação funcional (T00x)

- Script novo (`scripts/db/verify_140_*.py`, gitignored) cobrindo as partes server-side:
  criar tag nova + reaproveitar tag existente (case-insensitive) num produto; criar
  categoria via endpoint (e reaproveitar em criação duplicada); `/catalogo/categorias`
  lista categorias com produto ativo; `/catalogo/categoria/<slug>` mostra só produtos
  daquela categoria e dá 404 para categoria sem produto ativo; produto com categoria
  compartilhada mostra relacionados na página de detalhe; `/catalogo/lista-desejos`
  carrega e injeta o número de WhatsApp corretamente; index/detail de hoje continuam
  funcionando sem regressão.
- `node --check` no `catalogo-wishlist.js` extraído + simulação com um stub simples de
  `localStorage` em Node, cobrindo: adicionar item, não duplicar o mesmo slug duas vezes,
  remover item, contagem correta, mensagem de WhatsApp montada citando os produtos certos,
  botão de enviar desabilitado com lista vazia.
