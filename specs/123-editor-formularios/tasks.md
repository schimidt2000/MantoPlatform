# Tasks — Editor de Formulários (123)

- [X] T001 Migration `form_field_definitions` (`down_revision = "d5e6f7a8b9c0"`) + seed via
      `op.bulk_insert` reproduzindo exatamente os campos hoje hardcoded dos dois formulários
      (mesmos rótulos/tipos/obrigatoriedade/ordem), marcando `is_system=True` nos campos usados
      por extração de contato, feature 119 (CPF/CNPJ/endereço) e autopreenchimento por CEP;
      checar colisão de revision-id antes de finalizar
- [X] T002 `app/models.py`: modelo `FormFieldDefinition`; atualizar docstring de
      `FormResponse.data` para o novo formato `[chave, rótulo, valor]`
- [X] T003 `app/formularios/routes.py`: `_validate_dynamic(form_type, f)` e
      `_build_sections_dynamic(form_type, f)` substituindo `_validate_comum`/
      `_validate_corporativo`/`_sections_comum`/`_sections_corporativo`; `form_comum`/
      `submit_comum`/`form_corporativo`/`submit_corporativo` passam a usar as versões
      dinâmicas (mesmo comportamento de hoje, dirigido pela tabela)
- [X] T004 `_field_from_sections`/`_fill_client_from_response`: busca por `field_key` (com
      fallback para entradas antigas de 2 posições sem chave) em vez de seção+rótulo em texto —
      sobrevive a renomeações (FR-009)
- [X] T005 Templates públicos: unificar `pre_contrato.html`/`corporativo.html` num
      `public_form.html` genérico iterando seções/campos vindos das rotas; macro única `field()`
      em `_field_macros.html` despachando por `field_type` (inclui `cep` com máscara +
      autopreenchimento ViaCEP genérico por `field_key`, e `sim_nao`); remove `radio_field`
      (espaço do evento vira `selecao`)
- [X] T006 Editor SUPERADMIN em `app/formularios/routes.py`: decorator `require_superadmin`;
      rotas `GET /formularios/editor/<form_type>`, `POST .../campo/novo`,
      `POST .../campo/<id>/editar`, `POST .../campo/<id>/mover`, `POST .../campo/<id>/excluir`
      (bloqueia exclusão de `is_system`, bloqueia troca de `field_type`/`field_key`)
- [X] T007 Template `formularios/editor.html` (lista por seção com ações de editar/adicionar/
      mover/excluir, confirmação antes de excluir) + link a partir de `formularios/index.html`
      para o editor de cada formulário
- [X] T008 Verificação funcional vs manto_local: os dois formulários públicos continuam
      idênticos ao comportamento atual pós-migration (todos os campos, mesma validação);
      SUPERADMIN edita rótulo/obrigatoriedade de campo existente e reflete no público; adiciona
      campo personalizado (obrigatório e opcional) e ele aparece/valida/salva/entra na mensagem
      de WhatsApp; tenta remover campo de sistema (bloqueado); remove campo personalizado e
      confere resposta antiga preservada; reordena campos; renomeia rótulo de CPF/CNPJ/endereço
      e confirma que a automação da feature 119 continua funcionando; busca de
      `/formularios/respostas/search` (usada em `/events/new`) não quebra; acesso não-SUPERADMIN
      ao editor bloqueado (403); ruff nos arquivos tocados — 38/38 cenários passaram
- [ ] T009 Commit, merge em main, push
