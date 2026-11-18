---
description: "Tasks da feature 352 — fornecedores cadastrados nos gastos extras"
---
# Tasks: Fornecedores cadastrados nos gastos extras

**Input**: artefatos em `/specs/352-fornecedores-gastos-extras/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Verificação (constituição, Princípio VIII)**: `verify_352.py` contra `manto_352` (exceção registrada
no `plan.md`), escrito na fase Foundational, antes do núcleo.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [x] T001 Banco de verificação `manto_352` restaurado de `backups/manto_2026-11-17_0200.dump` (head `d334b2c4e6f8`, 83 gastos a fornecedor) e URL guardada fora do repositório (scratchpad da sessão)

---

## Phase 2: Foundational (bloqueia as histórias)

- [x] T002 Model `Fornecedor` (tabela `fornecedores`) e `SpecialExpense.fornecedor_id` + relação `fornecedor` em `app/models.py`, conforme `data-model.md` (docstring com o porquê: o gasto guarda o PIX do lançamento)
- [x] T003 Migration manual `migrations/versions/f352a1b2c3d4_fornecedores.py` (`down_revision = "d334b2c4e6f8"`): tabela, `UNIQUE(nome_normalizado)`, coluna + FK `ON DELETE SET NULL` + índice; `downgrade` completo. Só o esquema nesta tarefa (a importação entra na T015); aplicar no `manto_352`
- [x] T004 Núcleo `app/gastos/fornecedor_ops.py` (arquivo novo): `normalizar_nome`, `CATEGORIAS_DO_FORNECEDOR`, `FornecedorValidationError(field, message)`, `fornecedor_por_nome_normalizado`
- [x] T005 **`specs/352-fornecedores-gastos-extras/verify_352.py`** — os 11 cenários da seção "Verificação" da spec (login por `POST /api/auth/login` com um FINANCEIRO e um FIGURINO descartáveis; conferência por conexão `psycopg` separada; cenário 9 que DEVE falhar; limpeza no `finally`), rodando contra `DATABASE_URL` do `manto_352` — escrito AGORA e falhando nos cenários ainda não construídos

**Checkpoint**: esquema no `manto_352`, primitivas prontas, verify falhando pelos motivos certos.

---

## Phase 3: História 1 — Escolher o fornecedor preenche o gasto (P1) 🎯 MVP

**Objetivo**: sugestões no campo do fornecedor; escolher preenche nome, PIX e categoria; o gasto salva ligado.

**Verificação**: cenários 4, 5 e 10 em PASS; formulário aberto no Browser pane.

- [x] T006 [US1] `app/gastos/fornecedor_ops.py`: `listar(apenas_ativos: bool, com_totais: bool)` — ordem alfabética sem acento; totais (`gastos`, `total_aprovado`, `ultimo_gasto`) numa consulta agregada só
- [x] T007 [US1] `app/gastos/fornecedor_ops.py`: `resolver_para_gasto(fornecedor_id, nome, pix, categoria, ator)` — ramo do id válido e do nome normalizado existente; completa `pix`/`categoria_padrao` vazios; devolve o fornecedor (o ramo "cadastrar" é a T013)
- [x] T008 [US1] `app/gastos/gastos_ops.py`: `_validate_expense_data` lê `fornecedor_id`; `create_expense` e `edit_expense` chamam `resolver_para_gasto` só com desembolso `fornecedor`, gravam `fornecedor_id` e `supplier_name = fornecedor.nome`; outro desembolso zera o vínculo; `changed` da edição considera `fornecedor_id`
- [x] T009 [US1] `app/api/gastos_read.py`: `fornecedor_id` no `_expense_dict`; `GET /api/gastos/fornecedores` (comentário `RBAC:`; não gestor = só ativos, sem totais) — e `app/api/gastos_write.py`: `fornecedor_id` lido no `POST /api/gastos` (multipart) e no `PATCH /api/gastos/<id>` (JSON)
- [x] T010 [P] [US1] `frontend/apps/internal/src/lib/fornecedores.ts` (novo): tipos `Fornecedor`/`FornecedoresResponse` e `useFornecedores()` (`staleTime` 5 min) — e `frontend/apps/internal/src/lib/gastos.ts`: `fornecedor_id?: number | null` no `GastoExtra`, nos inputs de criar/editar, e invalidação de `["gastos-fornecedores"]` no sucesso
- [x] T011 [US1] `frontend/apps/internal/src/components/Gastos/FornecedorCampo.tsx` (novo): `Combobox freeSolo` com os ativos (segunda linha PIX · categoria); escolher → `onEscolher(fornecedor)`; digitar → `onDigitar(texto)` (zera a escolha)
- [x] T012 [US1] `frontend/apps/internal/src/pages/GastosExtrasPage.tsx`: `fornecedorId` no `GastoFormValues` (vazio, do gasto na edição), `FornecedorCampo` no lugar do `<input>` do nome em "Pagamento a fornecedor", escolher preenche nome/PIX/categoria, `fornecedor_id` no `buildPayload`

**Checkpoint**: escolher um fornecedor da importação preenche e salva ligado.

---

## Phase 4: História 2 — Fornecedor novo se cadastra ao salvar o gasto (P1)

**Objetivo**: nome que não existe vira fornecedor ao salvar; grafia diferente liga ao existente.

**Verificação**: cenários 2 e 3 em PASS; aviso de "fornecedor novo" visto na tela.

- [x] T013 [US2] `app/gastos/fornecedor_ops.py`: ramo "cadastrar" de `resolver_para_gasto` — nome com espaços colapsados, PIX, categoria só se escolhível, `criado_por`; `SAVEPOINT` (`db.session.begin_nested()`) e, no `IntegrityError`, desfaz e relê pelo nome
- [x] T014 [US2] `frontend/apps/internal/src/components/Gastos/FornecedorCampo.tsx`: texto sem nome normalizado igual na lista mostra "Fornecedor novo: ficará salvo para os próximos gastos."

**Checkpoint**: histórias 1 e 2 funcionam juntas e sozinhas.

---

## Phase 5: História 3 — O cadastro nasce com o histórico, juntado e arrumado (P1)

**Objetivo**: 41 fornecedores a partir das 65 grafias; todo gasto a fornecedor ligado; nomes arrumados.

**Verificação**: cenário 1 em PASS sobre o `manto_352` restaurado de novo; números do `quickstart.md` §1.

- [x] T015 [US3] `migrations/versions/f352a1b2c3d4_fornecedores.py`: importação no `upgrade` — cópia local de `normalizar_nome` e da normalização de PIX (migration não importa `app/`), união de grupos, tabela de grafias do `plan.md` §7, nome/PIX/categoria por grupo, sufixo defensivo, `UPDATE` dos gastos (`fornecedor_id` e `supplier_name`), contagem no log da migration
- [x] T016 [US3] Ensaio: recriar `manto_352` do dump de 17/11, rodar `flask db upgrade && python seed.py` (sequência real do start) e conferir por SQL: 41 fornecedores, 0 gastos `fornecedor` sem vínculo, 0 gastos `cliente` com vínculo, "Adão Lima da Silva" com 5 gastos, PIX dos gastos idêntico ao do dump

**Checkpoint**: importação ensaiada no dump fresco.

---

## Phase 6: História 4 — Financeiro arruma o cadastro (P2)

**Objetivo**: tela "Fornecedores" com cadastrar, alterar, arquivar/reativar e juntar.

**Verificação**: cenários 6, 7, 8 e 9 em PASS; tela aberta em 390px e desktop.

- [x] T017 [US4] `app/gastos/fornecedor_ops.py`: `cadastrar`, `alterar` (nome único → `FornecedorValidationError("nome")`; renomear reescreve `supplier_name` dos ligados; `ativo`), `juntar(origem, destino)` (trava `ORDER BY id`, move os gastos com o nome do destino, completa PIX/categoria, apaga a origem) — auditoria por `gastos_ops._log` (import tardio)
- [x] T018 [US4] `app/api/gastos_write.py`: `POST /api/gastos/fornecedores`, `PATCH /api/gastos/fornecedores/<id>`, `POST /api/gastos/fornecedores/<id>/juntar` — gate `_require_financeiro()` no início; 400 com `fields`, 404, contrato de `contracts/api.md`
- [x] T019 [P] [US4] `frontend/apps/internal/src/lib/fornecedores.ts`: `useCadastrarFornecedor`, `useAlterarFornecedor`, `useJuntarFornecedores` (invalidam fornecedores e `["gastos-extras"]`)
- [x] T020 [US4] `frontend/apps/internal/src/pages/FornecedoresPage.tsx` (novo): busca e "Mostrar arquivados" no endereço, `useRestaurarRolagem`, cartões com totais, `KebabMenu` (Alterar, Juntar com outro fornecedor, Arquivar/Reativar), `Modal` de cadastro/alteração com erro no campo, `Modal` de juntar com `Combobox` do destino e frase do efeito
- [x] T021 [US4] `frontend/apps/internal/src/App.tsx` (rota `/gastos/fornecedores`), `frontend/apps/internal/src/lib/navigation.tsx` (item "Fornecedores", Financeiro/Superadmin, depois de "Gastos Recorrentes") e botão "Fornecedores" no cabeçalho de `GastosExtrasPage.tsx` quando `can_manage`

**Checkpoint**: as quatro histórias funcionam.

---

## Phase 7: Polimento e transversais

- [x] T022 `cd frontend && npm run typecheck` limpo (três SPAs); `ruff check` nos `.py` tocados; `ruff format` só em `fornecedor_ops.py`, na migration e no verify
- [x] T023 `verify_352.py` verde ponta a ponta contra o `manto_352` (com a importação aplicada)
- [x] T024 Tela aberta (skill `manto-conferir-tela`): formulário de gasto (criar e editar) e "Fornecedores", em 390px e desktop, claro e escuro; textos revisados pelo Princípio XV junto dos vizinhos
- [x] T025 Docs por fonte única: `docs/01` (schema `fornecedores`, coluna, endpoints, linhas em §4.3), `docs/02` (tela "Fornecedores" e o campo em Gastos Extras), `docs/03` (entrada no topo + linha no índice, com o reencadeamento da migration da 348 e a perda das grafias no downgrade), `docs/04` (o gasto guarda nome e PIX do lançamento; o cadastro completa, não substitui)
- [x] T026 `quickstart.md` executado de ponta a ponta

---

## Dependências e ordem

- Setup → Foundational (T002–T005) → US1 (T006–T012) → US2 (T013–T014) → US3 (T015–T016) → US4 (T017–T021) → Polimento
- US2 estende a função da US1 (`resolver_para_gasto`); US3 só depende da Foundational; US4 depende da Foundational
- Paralelos: T010 com T006–T009; T019 com T017–T018; a US3 pode correr ao lado da US1/US2 (arquivos diferentes)

## Estratégia

- MVP: Foundational + US1 + US3 (as sugestões já nascem com os 41 fornecedores)
- Commit por grupo lógico (`feat(352):`), sempre por caminho; merge e push só quando o dono pedir

---

## Phase 8: Convergence

- [x] T027 Cobrir no `verify_352.py` o gasto digitado com o nome de um fornecedor arquivado (liga a ele, que continua arquivado) e, em `frontend/apps/internal/src/components/Gastos/FornecedorCampo.tsx`, comparar o nome digitado com a lista inteira do payload (o Financeiro recebe os arquivados) para não anunciar "Fornecedor novo" a um arquivado per spec §Casos de borda (partial)
- [x] T028 Tirar da `spec.md` o caso de borda da "tela antiga (Jinja) de gastos": `app/gastos/routes.py` não existe mais; os únicos que gravam gasto são `gastos_ops` e `cancel_ops` per spec §Casos de borda (contradicts)
