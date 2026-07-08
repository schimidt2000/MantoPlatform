# Tasks — Cadastro de Cliente Mais Completo (119)

- [X] T001 Migration (`clients` += `cpf`, `cnpj`, `address`), `down_revision =
      "e1f2a3b4c5d6"`, conferir unicidade do revision, upgrade no manto_local
- [X] T002 `app/models.py`: colunas `cpf`, `cnpj`, `address` em `Client`
- [X] T003 `app/formularios/routes.py`: `_fill_client_from_response()` (extrai CPF/endereço
      do comum ou CNPJ/endereço do corporativo; só preenche campo vazio) chamada em
      `associar()` nos dois caminhos (criar novo / vincular existente)
- [X] T004 `app/clientes/routes.py`: rota `POST /clientes/<id>/update` (CPF/CNPJ/endereço),
      RBAC `require_vendas`
- [X] T005 `app/templates/clientes/detail.html`: exibir CPF/CNPJ/endereço + formulário de
      edição inline
- [X] T006 Verificação funcional vs manto_local (cenários do plano) + ruff
- [X] T007 Commit, merge em main, push
