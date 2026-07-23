# Tasks: EducaManto — Pacotes e Conteúdos em React

**Input**: Design documents from `specs/175-educamanto-pacotes-react/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/educamanto-endpoints.md, quickstart.md

**Tests**: não solicitados no spec — a verificação funcional (script contra `manto_local`) cobre
o papel de teste de integração, seguindo o padrão já usado em todas as fatias 145-174.

## Phase 1: Setup

- [ ] T001 Ler `app/educamanto/routes.py`, `pricing_ops.py`, `pdf.py` e `app/models.py`
  (linhas 1093-1187) para confirmar shape exato de `to_dict()` antes de escrever a API (nenhuma
  mudança de schema esperada).

## Phase 2: Foundational

- [ ] T002 Extrair `app/educamanto/package_ops.py`: funções puras
  `create_package(data: dict) -> EducaMantoPackage`, `update_package(pkg, data: dict) -> EducaMantoPackage`,
  `duplicate_package(pkg) -> EducaMantoPackage`, `delete_package(pkg) -> None`, e um helper
  `_parse_items(data: dict) -> list[dict]` — mesma lógica hoje só em
  `create_package`/`edit_package`/`duplicate_package`/`delete_package`/`_parse_items_from_form`
  de `app/educamanto/routes.py`. Sem `flask.request`/`render_template` dentro do módulo (recebe
  `dict` já parseado, não o form).
- [ ] T003 Atualizar `app/educamanto/routes.py` para chamar `package_ops.py` em vez de conter a
  lógica inline (views continuam parseando `request.form` e chamando as funções puras) —
  zero mudança de comportamento, só remoção da duplicação.
- [ ] T004 Rodar a verificação funcional existente (ou manual rápida) das rotas Jinja de
  `app/educamanto` para confirmar paridade após a extração, antes de prosseguir.

**Checkpoint**: núcleo de negócio extraído e testado — pronto para expor via API.

---

## Phase 3: User Story 1 — Montar e gerar orçamento por pacote (P1) 🎯 MVP

**Goal**: usuário gera e baixa o PDF do orçamento a partir de pacotes reais, e o registro entra
no histórico.

**Independent Test**: selecionar pacote(s) na calculadora já existente, preencher dias, clicar
"Gerar orçamento", confirmar download do PDF e o novo registro no histórico (via API).

- [ ] T005 [US1] `POST /api/educamanto/orcamento/gerar` em `app/api/educamanto_write.py` — RBAC
  `_CAN_USE`, valida pacotes/dias (mesmas mensagens do `gerar_orcamento` legado), monta o
  snapshot (reusar/mover `_build_snapshot()` de `app/educamanto/routes.py` para
  `package_ops.py` ou um novo `quote_ops.py`, sem duplicar), persiste `EducaMantoQuote`, retorna
  o PDF binário via `_pdf_response` (reusado de `app/educamanto/pdf.py`).
- [ ] T006 [US1] `GET /api/educamanto/orcamento/<quote_id>/pdf` em `app/api/educamanto_write.py`
  (ou `educamanto_read.py`) — RBAC `_CAN_USE`, 404 se não encontrado, reconstrói o PDF a partir
  do `snapshot` congelado (nunca recalcula do pacote atual).
- [ ] T007 [P] [US1] `useGerarOrcamento()`/`useOrcamentoPdf()` em
  `frontend/apps/internal/src/lib/educamanto.ts` usando `apiFetchBlob` (`@manto/api-client`).
- [ ] T008 [US1] Adicionar botão "Gerar orçamento" em
  `frontend/apps/internal/src/pages/EducaMantoCalculadoraPage.tsx`: chama `useGerarOrcamento()`,
  trata loading/erro (toast amigável), dispara o download do PDF ao concluir.
- [ ] T009 [US1] Verificação funcional (script contra `manto_local`): gerar orçamento com
  sucesso (200 + PDF + registro criado), erro sem pacote/dias (400), RBAC por papel.

**Checkpoint**: US1 completa e testável isoladamente — já é um incremento útil por si só.

---

## Phase 4: User Story 2 — Gerenciar pacotes educacionais (P2)

**Goal**: SuperAdmin cria/edita/duplica/exclui pacotes pela tela React.

**Independent Test**: como SuperAdmin, criar pacote com itens, editar, duplicar e excluir,
conferindo reflexo imediato na lista e na calculadora (US1).

- [ ] T010 [US2] `POST /api/educamanto/packages` e `PATCH /api/educamanto/packages/<id>` em
  `app/api/educamanto_write.py` — RBAC `_CAN_MANAGE`, chama `package_ops.create_package`/
  `update_package`, erros de validação retornam `json_error(msg, 400, fields=...)`.
- [ ] T011 [US2] `POST /api/educamanto/packages/<id>/duplicate` e
  `DELETE /api/educamanto/packages/<id>` em `app/api/educamanto_write.py` — RBAC `_CAN_MANAGE`,
  chama `package_ops.duplicate_package`/`delete_package`, 404 se não encontrado.
- [ ] T012 [P] [US2] Hooks `usePackages()` (lista), `useCreatePackage()`, `useUpdatePackage()`,
  `useDuplicatePackage()`, `useDeletePackage()` em
  `frontend/apps/internal/src/lib/educamanto.ts`, invalidando a query `["educamanto-packages"]`
  já usada pela calculadora (US1) em toda mutação.
- [ ] T013 [US2] `frontend/apps/internal/src/pages/EducaMantoPackagesPage.tsx` — lista de
  pacotes (`PageHeader` + `DenseCard`), ações de editar/duplicar/excluir (excluir com
  `window.confirm`), visível só a SuperAdmin/Comercial (Comercial só vê a lista, sem
  criar/editar — mesma regra de `_CAN_PACKAGES` vs `_CAN_MANAGE`); acesso negado tratado com
  mensagem amigável para quem não tem `_CAN_PACKAGES`.
- [ ] T014 [US2] `frontend/apps/internal/src/pages/EducaMantoPackageFormPage.tsx` — formulário
  react-hook-form + zod (nome, margens, dias de desconto, comissão, ensemble, lista de itens
  com adicionar/remover linha), campos monetários via `@manto/money`; usado para criar e editar
  (rota compartilhada, `pkg_id` opcional).
- [ ] T015 [US2] Registrar as duas rotas novas (`/educamanto/pacotes`, `/educamanto/pacotes/novo`,
  `/educamanto/pacotes/:id/editar`) no router do `frontend/apps/internal` e no menu de
  navegação do EducaManto (link a partir da calculadora, visível conforme RBAC).
- [ ] T016 [US2] Verificação funcional: criar/editar/duplicar/excluir pacote via API (200/201/
  204), 403 para papéis sem `_CAN_MANAGE`, itens substituídos corretamente na edição.

**Checkpoint**: US1 + US2 completas — catálogo de pacotes totalmente gerenciável em React.

---

## Phase 5: User Story 3 — Consultar histórico de orçamentos gerados (P3)

**Goal**: qualquer usuário do EducaManto consulta e filtra o histórico; SuperAdmin também
filtra por quem gerou.

**Independent Test**: gerar dois orçamentos (US1), abrir o histórico, filtrar por texto/período,
reabrir o PDF de um deles e confirmar que os valores batem com os do momento da geração.

- [ ] T017 [US3] `GET /api/educamanto/historico` em `app/api/educamanto_read.py` — RBAC
  `_CAN_USE`, filtros `q`/`date_from`/`date_to`/`user_id` (mesma lógica de `historico()` em
  `app/educamanto/routes.py`), `users`/`user_name` só para SuperAdmin.
- [ ] T018 [P] [US3] Hook `useEducaMantoHistorico(filtros)` em
  `frontend/apps/internal/src/lib/educamanto.ts`.
- [ ] T019 [US3] `frontend/apps/internal/src/pages/EducaMantoHistoricoPage.tsx` — tabela/lista
  com busca textual, filtro de período, coluna "Gerado por" condicional a SuperAdmin, botão
  para reabrir o PDF (usa `useOrcamentoPdf()` da US1).
- [ ] T020 [US3] Registrar rota `/educamanto/historico` e link de navegação.
- [ ] T021 [US3] Verificação funcional: busca/filtros retornando o subconjunto certo, coluna
  "Gerado por" ausente para não-SuperAdmin, PDF reaberto batendo com o snapshot congelado mesmo
  após editar/excluir o pacote original (US2).

**Checkpoint**: as 3 user stories completas — spec 175 encerrada.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T022 [P] `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal` sem erros.
- [ ] T023 [P] `ruff check` nos arquivos Python novos/tocados
  (`app/educamanto/package_ops.py`, `app/educamanto/routes.py`, `app/api/educamanto_read.py`,
  `app/api/educamanto_write.py`); `ruff format` só nos arquivos novos.
- [ ] T024 Conferir as 4 telas (calculadora, pacotes, form de pacote, histórico) em viewport
  mobile (375px) e desktop antes de "pronto"; confirmar transições Framer Motion e
  `useReducedMotion()`.
- [ ] T025 Confirmar zero regressão nas rotas Jinja legadas de `app/educamanto` (paridade final).
- [ ] T026 Atualizar `docs/changelog.html` com a entrega (linguagem simples) e republicar no
  mesmo link já existente.

## Dependencies & Execution Order

- **Setup (T001) → Foundational (T002-T004)**: bloqueiam todo o resto — `package_ops.py`
  precisa existir e estar validado antes de qualquer endpoint de escrita.
- **US1 (T005-T009)** depende só do Foundational — é o MVP, entregável isoladamente.
- **US2 (T010-T016)** depende do Foundational (T002); independente de US1 no código, mas faz
  mais sentido testar depois de US1 estar de pé (mesma tela de calculadora consome os pacotes).
- **US3 (T017-T021)** depende de US1 (reabrir PDF usa `useOrcamentoPdf` da T007) e se beneficia
  de US2 já existir para testar o cenário "pacote editado depois" (edge case do spec).
- **Polish (T022-T026)** só depois das 3 user stories.

## Parallel Execution Examples

- Dentro da US1: T007 (hook frontend) é `[P]` em relação a T005/T006 (backend) — pode ser
  escrito em paralelo, integrado ao final.
- Dentro da US2: T012 (hooks) é `[P]` em relação a T010/T011 (backend).
- Dentro da US3: T018 (hook) é `[P]` em relação a T017 (backend).
- T022/T023 (tsc/build e ruff) são paralelizáveis entre si na fase de polish.

## Implementation Strategy

**MVP = User Story 1** (T001-T009): gerar orçamento real a partir de pacotes persistidos já
entrega valor (fecha o gap mais visível hoje — a calculadora React de 171 ainda não persistia
nada). US2 e US3 podem seguir como incrementos subsequentes no mesmo branch/PR ou em commits
atômicos separados, cada um verificado e commitado antes do próximo.
