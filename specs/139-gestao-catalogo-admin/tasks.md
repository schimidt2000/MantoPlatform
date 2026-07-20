# Tasks — Gestão de produtos do catálogo (139)

- [X] T001 `app/catalogo/importer.py`: `_rewrite_public_url` e `_slugify` reaproveitados
      via import direto pelas rotas novas (sem duplicar)
- [X] T002 [US1][US2] `app/admin/routes.py`: `_unique_catalog_slug` (slug único para
      criação avulsa, via `_slugify` + checagem contra o banco)
- [X] T003 [US1] `app/admin/routes.py`: `GET/POST /admin/catalogo/novo`
      (`@require_superadmin`) — cria `CatalogItem`, salva fotos via `save_file` +
      `_rewrite_public_url`, valida nome+foto obrigatórios preservando campos no erro,
      `audit()` + `flash()`
- [X] T004 [US2] `app/admin/routes.py`: `GET/POST /admin/catalogo/<id>/editar` — mesmo
      formulário pré-preenchido; adiciona/remove fotos, troca capa (helper compartilhado
      `_apply_catalog_photos`, usado por criação e edição)
- [X] T005 [US2] `app/admin/routes.py`: `POST /admin/catalogo/<id>/toggle-ativo` e
      `POST /admin/catalogo/<id>/excluir` (exclusão definitiva com confirmação forte no JS)
- [X] T006 [US3] `app/admin/routes.py`: `GET /admin/catalogo` — busca por nome, filtro por
      categoria e status
- [X] T007 [US1][US2][US3] `app/templates/admin_catalogo_list.html` e
      `admin_catalogo_form.html` — mesmo padrão visual de `figurinos.html`/
      `figurino_form.html`; gerenciador de fotos múltiplas (capa via rádio, remover via
      checkbox, adicionar via input múltiplo)
- [X] T008 Link de descoberta: "🖼️ Gerenciar catálogo" em `admin_importar_catalogo.html`;
      link recíproco "Importar do WordPress" na nova listagem.
      Correção pós-entrega (mesmo dia): usuário não achou o link — ambas as páginas só
      eram alcançáveis por URL direta ou uma a partir da outra, nenhuma linkada do menu
      lateral. Adicionado item "Gerenciar catálogo" no `sidebar` (`base.html`, seção
      Comercial, ao lado do link "Catálogo" já existente que abre a página pública),
      visível só para SUPERADMIN.
- [X] T009 Verificação funcional vs `manto_local`: 403 para não-SUPERADMIN; validação
      bloqueia produto sem nome/foto; criar produto aparece no público (index+detalhe);
      editar reflete imediato; adicionar/remover foto e trocar capa; inativar tira do
      público (404 no detalhe) mas mantém na gestão; reativar; excluir definitivo remove
      produto e fotos. Todos os cenários passaram
      (`scripts/db/verify_139_catalogo_admin.py`).
- [X] T010 `ruff check` nos arquivos tocados (mesma contagem do baseline, 7 pré-existentes
      em `admin/routes.py`, nenhum novo); changelog (`docs/changelog.html`, republicado no
      link já existente); pointer do plano em `CLAUDE.md` atualizado; commit, merge em
      `main`, push
