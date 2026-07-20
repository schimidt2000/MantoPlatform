# Implementation Plan: Gestão de produtos do catálogo (criar e editar)

**Branch**: `139-gestao-catalogo-admin` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/139-gestao-catalogo-admin/spec.md`

## Summary

Nova área de gestão do catálogo (`/admin/catalogo/...`, restrita a SUPERADMIN via
`require_superadmin`, já usado por `/admin/importar-catalogo`), separada da página pública
`/catalogo`. Segue o padrão já estabelecido duas vezes no projeto para "converter um
catálogo importado em nativamente editável": Figurino (`app/figurino/routes.py::new_sheet`/
`edit_sheet`) e o editor de campos de formulário (feature 123). A tela escreve nas mesmas
tabelas (`CatalogItem`, `CatalogItemImage`, `CatalogCategory`) que a página pública já lê —
sem sincronização adicional, sem migration nova (`is_active` já existia prevendo esta
feature).

Diferença em relação ao precedente do Figurino: catálogo tem MÚLTIPLAS fotos por item
(reordenáveis, uma marcada como capa), não uma só — a única peça de UI genuinamente nova é
o gerenciador de fotos múltiplas do formulário.

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy + Jinja2 (stack existente, sem
dependência nova)

**Primary Dependencies**: `app/storage.py::save_file`/`delete_file` (upload com compressão
automática + abstração local/S3, já usado por Figurino/Talentos/importação do catálogo);
`app/utils.py::audit` (trilha de auditoria, já usado por Figurino); helpers já existentes
de `app/catalogo/importer.py` (`_rewrite_public_url`, `_slugify`) reaproveitados, não
duplicados

**Storage**: PostgreSQL — nenhuma migration nova; fotos na mesma pasta/serviço já usado
pela importação (`catalog_photos`, local ou S3/R2 conforme `USE_S3`)

**Testing**: script de verificação funcional com Flask test client contra `manto_local`
(padrão do projeto): criar produto, editar produto, inativar/reativar, upload/remoção de
fotos, bloqueio de acesso para não-SUPERADMIN, e confirmação de que a página pública reflete
tudo imediatamente

**Target Platform**: aplicação web server-side (Flask + Jinja2)

**Project Type**: web application (monolito Flask existente)

**Performance Goals**: N/A — CRUD simples, catálogo já opera com centenas de itens sem
problema na leitura pública hoje

**Constraints**: a página pública (`/catalogo`, `/catalogo/<slug>`) MUST permanecer
byte-a-byte igual ao comportamento atual (FR-007) — nenhuma rota ou template público é
tocado nesta feature, só o backend de dados que ambos compartilham

**Scale/Scope**: um blueprint existente (`admin_bp`) ganha ~5 rotas novas; dois templates
novos (listagem + formulário de criar/editar, compartilhado)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: núcleo da decisão de design — reaproveita
  `save_file`/`delete_file` (upload), `audit` (trilha), `_rewrite_public_url`/`_slugify`
  (já existem em `importer.py`, só importados, não reescritos), o padrão de rota
  create/edit do Figurino, e `require_superadmin` já usado pelo import do catálogo. Nenhum
  padrão de UI ou upload novo é inventado.
- **II. Padrões de código Python**: rotas novas com type hints/docstring, seguindo o
  tamanho e nomenclatura já usados em `app/figurino/routes.py`.
- **III. Arquitetura em camadas**: rotas orquestram; toda a lógica de slug/upload/imagem já
  vive em módulos existentes (`storage.py`, `catalogo/importer.py`) — reaproveitados, sem
  regra de negócio nova na camada de view além de validação de formulário.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: página pública não é tocada (FR-007);
  verificação funcional cobre explicitamente "o público continua igual" além do fluxo novo
  de gestão.
- **V. UI/UX consistente e com feedback**: formulário segue o padrão visual de
  `figurino_form.html` (mesmo `base.html`, mesmos componentes); validação com mensagem
  clara e sem apagar campos preenchidos (FR-005, mesmo padrão da feature 134); ação
  destrutiva (excluir de vez, FR-008) exige confirmação, igual ao resto do sistema.
- **VII. Valores monetários**: N/A — catálogo não tem campo monetário.

Nenhuma violação. Gate passa sem exceções.

## Project Structure

### Documentation (this feature)

```text
specs/139-gestao-catalogo-admin/
├── plan.md              # This file
├── spec.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

Sem `research.md`/`data-model.md`/`contracts/`/`quickstart.md`: sem incógnita técnica
(precedente direto já existe no código), sem entidade nova, sem interface externa nova.

### Source Code (repository root)

```text
app/
├── admin/
│   └── routes.py        # + rotas: listagem, novo, editar, toggle-ativo, excluir
│                         #   (mesmo blueprint/prefixo de /admin/importar-catalogo)
├── catalogo/
│   └── importer.py       # _rewrite_public_url/_slugify passam a ser importados
│                          #   também pelas rotas novas (sem duplicar)
└── templates/
    ├── admin_catalogo_list.html   # listagem + busca/filtro (US3)
    └── admin_catalogo_form.html   # criar/editar (mesmo template, sheet/item=None → criar)
```

## Design Decisions

1. **Rotas** (em `app/admin/routes.py`, todas `@require_superadmin`):
   - `GET /admin/catalogo` — listagem com busca (`?q=`), filtro de categoria (`?categoria=`)
     e status (`?status=ativo|inativo|todos`, default ativo+inativo juntos com badge).
   - `GET/POST /admin/catalogo/novo` — formulário de criação.
   - `GET/POST /admin/catalogo/<int:item_id>/editar` — formulário de edição (mesmo
     template do de criação, com `item` preenchido).
   - `POST /admin/catalogo/<int:item_id>/toggle-ativo` — inverte `is_active` (FR-003), um
     clique, sem formulário — mesmo padrão de outros toggles do sistema (ex.: contrato
     assinado/pendente em `event_detail.html`).
   - `POST /admin/catalogo/<int:item_id>/excluir` — exclusão definitiva, só permitida se
     não houver nenhuma FK apontando pro item além das próprias fotos (que são
     cascade-deletadas junto, `CatalogItemImage` já tem `cascade="all, delete-orphan"`);
     FR-008 fala em "orçamento" como vínculo futuro hipotético — hoje não existe nenhuma FK
     desse tipo, então a checagem por ora é só "sempre permitido, com confirmação forte no
     JS" (mesmo padrão de exclusão do resto do sistema) — não inventa uma trava para uma
     relação que não existe ainda.
   - Link "🖼️ Gerenciar catálogo" adicionado em `admin_importar_catalogo.html` e/ou no menu
     admin, apontando pra `/admin/catalogo` (mesma descoberta de fluxo do botão que já leva
     pra reimportação).

2. **Slug**: novo helper simples reaproveitando `_slugify` de `importer.py`: gera o slug
   base do nome, e se colidir com um item existente (`CatalogItem.query.filter_by(slug=...)`),
   sufixa com `-2`, `-3`, etc. até ficar único — mais simples que `_unique_slug` do
   importer (que resolve unicidade em lote contra um CSV inteiro); não reaproveita essa
   função porque seu contrato é para bulk-import, não para uma única criação via formulário.

3. **Fotos múltiplas** (a única peça de UI genuinamente nova): no formulário, cada foto
   já salva aparece como card com miniatura + botão "Remover" + rádio/estrela "Definir como
   capa"; um campo de upload permite adicionar novas fotos (múltiplo, `<input type="file"
   multiple>`). No POST:
   - Fotos novas enviadas → `save_file(f, "catalog_photos")` + `_rewrite_public_url(...)` →
     novo `CatalogItemImage` na próxima posição livre.
   - Fotos marcadas para remoção (checkbox oculto por card) → `delete_file(...)` +
     `db.session.delete(...)`.
   - Nova capa escolhida → reordena `position` (capa sempre vira `position=0`; demais
     mantêm ordem relativa).
   - Reaproveita exatamente `save_file`/`delete_file` do Figurino — só estende para N
     arquivos em vez de 1.

4. **Validação (FR-005)**: nome obrigatório e ao menos uma foto (nas já salvas OU nas
   recém-enviadas) — mesmo padrão de banner de erro + preservação dos campos já usado em
   `event_create.html` (feature 134): erros voltam pro mesmo template com os valores
   digitados, nunca perdem o que foi preenchido.

5. **Categorias**: `<select multiple>` ou checkboxes a partir de `CatalogCategory.query.all()`
   (lista já existente) — criar/editar categoria fica fora de escopo (spec Assumptions);
   produto pode ficar sem nenhuma marcada.

6. **Verificação funcional (T00x)**: script novo (`scripts/db/verify_139_*.py`, gitignored)
   contra `manto_local`: criar produto com foto+categoria e conferir que aparece em
   `/catalogo` e `/catalogo/<slug>`; editar nome/descrição/categoria de um existente e
   conferir reflexo imediato; inativar e conferir que some do público mas continua na
   listagem de gestão; adicionar/remover foto e trocar capa; tentar acessar `/admin/catalogo`
   como usuário não-SUPERADMIN e confirmar bloqueio (403); confirmar que `/catalogo` e
   `/catalogo/<slug>` de um item NÃO tocado continuam idênticos antes/depois (FR-007).
