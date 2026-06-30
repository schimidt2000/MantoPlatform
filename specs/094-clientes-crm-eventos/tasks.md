# Tasks: Clientes (CRM) — base Kommo, associação a eventos e ecossistema de marketing

**Feature**: 094-clientes-crm-eventos | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> Testes/verificações SEMPRE contra `manto_local` (Postgres). Migration **manual** (autogenerate
> quebrado). `[P]` = pode ser feito em paralelo (arquivos distintos).

## Phase 1 — Modelo de dados e migration (base de US1/US2)

- [ ] **T001** Em [models.py](../../app/models.py): adicionar `class Client` (tabela `clients`) com os
  campos do plano (PK, `name`, `phone` unique+index, `phone_display`, `email`, `company`, `source`,
  `kommo_lead_id`, `responsible`, `tags`, `lead_stage`, `funnel`, `lead_value`, `kommo_created_at`,
  `notes`, `created_at`, `updated_at`) + relationship `events`. Type hints/docstring.

- [ ] **T002** Em [models.py](../../app/models.py) `CalendarEvent`: adicionar `client_id =
  db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True)`, índice em `client_id` e
  relationship `client` (backref `events`).

- [ ] **T003** Criar migration manual `migrations/versions/<hash>_clientes_e_event_client_fk.py` com
  `down_revision = "a3d4e5f6a7b8"`: `create_table('clients', ...)` com unique em `phone`, e
  `add_column('calendar_events', client_id)` + FK + índice. Implementar `downgrade()`.

- [ ] **T004** Aplicar e validar: `.\scripts\db\run-local.ps1` + `python -m flask db upgrade` contra
  `manto_local`; conferir tabela `clients` e coluna `calendar_events.client_id` criadas.

## Phase 2 — Serviço de importação + comando CLI (US2, P1)

- [ ] **T005** [P] Criar [app/clientes/__init__.py](../../app/clientes/__init__.py) (pacote) e
  [app/clientes/importer.py](../../app/clientes/importer.py) com `normalize_phone(raw: str) -> str |
  None` (remove não-dígitos, valida tamanho mínimo de número discável). Cobre Assumptions de telefone.

- [ ] **T006** Em [importer.py](../../app/clientes/importer.py): `import_kommo_csv(path: str) ->
  ImportReport` — lê CSV (`utf-8-sig`), para cada linha com nome+telefone normaliza o telefone,
  deduplica por telefone (cria ou mescla metadados: tags/etapa/funil/responsável/lead_value/datas),
  idempotente em re-run. Ignora linha sem telefone utilizável. Retorna contagens
  (criados/mesclados/ignorados). Cobre FR-001..FR-004, SC-001, SC-005.

- [ ] **T007** Em [cli.py](../../app/cli.py) `register_commands`: comando
  `@app.cli.command("import-kommo-clients")` com argumento `path` (default
  `kommo_export_leads_2026-06-29.csv`), chama `import_kommo_csv` e imprime o relatório.

- [ ] **T008** Verificar importação: rodar `flask import-kommo-clients` contra `manto_local`; conferir
  contagens e que re-run não duplica (idempotência por telefone). Cobre AC US2.

## Phase 3 — Associar/criar cliente no evento (US1, P1) 🎯 MVP

- [ ] **T009** [P] Criar [app/clientes/routes.py](../../app/clientes/routes.py) com `clientes_bp` e rota
  de **busca JSON** (`GET /clientes/search?q=`) por nome/telefone (limit ~10), restrita a
  COMERCIAL/FINANCEIRO/SUPERADMIN. Registrar `clientes_bp` em
  [app/__init__.py](../../app/__init__.py). Cobre FR-006, FR-016.

- [ ] **T010** Em [clientes/routes.py](../../app/clientes/routes.py): rota `POST /clientes/quick-create`
  (nome + telefone obrigatórios; reaproveita cliente existente se telefone já existe → FR-008) usada
  pela criação inline. Cobre FR-007.

- [ ] **T011** Em [event_detail.html](../../app/templates/event_detail.html), seção "Dados de Venda":
  adicionar campo de **cliente** (busca com autocomplete via `/clientes/search`, exibe cliente
  vinculado, permite trocar/remover, e "criar novo" inline chamando `/clientes/quick-create`). Envia
  `client_id` no form comercial. Cobre FR-005, FR-006, FR-009.

- [ ] **T012** Em `_handle_update_comercial` ([app/calendar/routes.py](../../app/calendar/routes.py)):
  ler `client_id` do form e setar `event.client_id` (validando que o cliente existe). Registrar no
  `EventLog` quando o cliente mudar. Cobre FR-005.

## Phase 4 — Obrigatoriedade a partir da ativação (US3, P2)

- [ ] **T013** Definir a **data de ativação** (constante em [constants.py](../../app/constants.py) ou
  config) e, em `_handle_update_comercial`, se `event.start_at >= ativação` e sem `client_id` →
  `flash(erro)` claro e **abortar** o salvamento comercial sem descartar o resto do form (retornar antes
  do commit das mudanças comerciais). Cobre FR-010, FR-011.

- [ ] **T014** Garantir que o **sync do Google Calendar** não passa por essa validação (confirmar que o
  caminho de sync não chama `_handle_update_comercial`). Cobre FR-012.

## Phase 5 — Ecossistema: lista + ficha (US4, P2)

- [ ] **T015** [P] Em [clientes/routes.py](../../app/clientes/routes.py): `GET /clientes/` — lista
  pesquisável (nome/telefone) com nº de eventos por cliente; template
  [clientes/list.html](../../app/templates/clientes/list.html). Cobre FR-013.

- [ ] **T016** Em [clientes/routes.py](../../app/clientes/routes.py): `GET /clientes/<id>` — ficha com
  contato, metadados de marketing e eventos associados (data, título, valor, status) + totais (nº de
  eventos, soma de vendas); template [clientes/detail.html](../../app/templates/clientes/detail.html)
  com estado vazio. Cobre FR-014, SC-004.

- [ ] **T017** Tratamento de exclusão segura de cliente com eventos (bloquear ou desvincular) — FR-015.
  Adicionar link de "Clientes" no menu/área comercial existente.

## Phase 6 — Testes e verificação

- [ ] **T018** [P] Testes em `tests/` contra `manto_local`: `normalize_phone` (casos `'+5511...`,
  inválidos), dedup/idempotência de `import_kommo_csv`, validação de obrigatoriedade no save comercial,
  totais da ficha do cliente. Cobre SC-001, SC-003, SC-004.

- [ ] **T019** Qualidade (CLAUDE.md "Pronto"): `ruff format app/`, `ruff check app/`, `mypy app/` nos
  arquivos novos/alterados; rodar `pytest` contra `manto_local`.

- [ ] **T020** Verificação manual: importar CSV; em um evento novo, associar/criar cliente e salvar;
  tentar salvar venda sem cliente (bloqueio); abrir lista e ficha conferindo contagem/totais (SC-002).

## Dependências

- T001→T002→T003→T004 (modelo antes da migration; migration antes de usar).
- Phase 2 depende de T004. Phase 3 depende de T004 (+ T009/T010 antes de T011).
- T013/T014 dependem de T011/T012. Phase 5 depende de T004 (+ dados de T008 para ver valor real).
- Phase 6 ao final.

## Critério de pronto

- Importação idempotente por telefone funcionando e reportando contagens.
- Evento permite associar/criar cliente; venda nova exige cliente; passados/sync intactos.
- Lista e ficha de cliente com contagem/datas/totais corretos.
- Checklist "Pronto" do CLAUDE.md atendido (ruff/mypy/pytest contra `manto_local`).
