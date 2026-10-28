---
description: "Tasks da feature 323 — nota pedida ao Superadmin"
---

# Tasks: 323 — a nota pedida chega ao Superadmin

**Input**: `specs/323-nota-pedida-ao-superadmin/` (spec, plan, research, data-model, contracts/api.md)

**Verificação (Princípio VIII)**: `verify_323.py` é escrito na Foundational, antes do núcleo, e
nasce falhando nos cenários 1–3, 5–7, 9–12.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 `NOTA_DADOS_BANCARIOS` em `app/config.py` com o bloco do Inter como default real e env só sobrepondo (research R6, Princípio XIV)

---

## Phase 2: Foundational (bloqueia as histórias)

- [X] T002 Colunas `nota_tomador_doc`, `nota_iss_retido`, `nota_municipio`, `nota_referencia`, `nota_observacoes` em `CalendarEvent` e `pedida_por_id`, `pedida_em`, `aviso_enviado_em` em `EventInvoice` (`app/models.py`, data-model.md)
- [X] T003 Migration manual `migrations/versions/d323b5a1c0e7_nota_pedida.py` (`down_revision = "c322a7e1b9d4"`, aditiva, downgrade derruba as colunas e a FK); aplicar no `manto_local`
- [X] T004 Esqueleto de `app/calendar/pedido_de_nota_ops.py`: `DadosDaNota`, `NotaInvalida(fields)`, `ler_dados_da_nota`, `dados_mudariam`, constantes de mensagem e limites (contracts §1)
- [X] T005 **`specs/323-nota-pedida-ao-superadmin/verify_323.py`** — os 13 cenários da spec: eventos/usuários descartáveis sobre o `manto_local`, login só por `POST /api/auth/login`, Google (`_insert_event`, sync de evento) trocado por dublê, `_send` trocado por coletor e `send_async` síncrono, escrita conferida por conexão separada, cenário 8 de RBAC que deve falhar se vazar, limpeza no `finally` — rodar e confirmar que falha pelos motivos certos

**Checkpoint**: banco migrado, verify falhando nos cenários do núcleo.

---

## Phase 3: História 1 — ligar o chip pede a nota em qualquer porta (P1) 🎯 MVP

**Verificação**: cenários 1–4, 11, 12 em PASS.

- [X] T006 [US1] `acompanhar_pedido(event, *, pedida_por_id)` e `carimbar_pedido_da_criacao` em `app/calendar/pedido_de_nota_ops.py` (cria a emitir se ligado e sem nota; exclui a emitir se desligado; nota única a emitir acompanha `sale_value` — FR-016; nada no cancelado/satélite)
- [X] T007 [US1] `update_event_core`/`_gravar_venda_da_edicao` e `update_event_comercial` em `app/calendar/event_ops.py`: parâmetros `dados_nota` e `pedida_por_id`; gravar dados e chamar `acompanhar_pedido` depois de `with_invoice` (evento já travado por `estado_da_venda`)
- [X] T008 [US1] `_create_event_core` em `app/calendar/routes.py`: carimbar o pedido da nota criada por `_create_event_row`, com `actor_id`
- [X] T009 [US1] `app/api/agenda_write.py`: passar `pedida_por_id=current_user.id` aos três núcleos

**Checkpoint**: o furo da edição fechado; desligar exclui só a emitir.

---

## Phase 4: História 2 — a vendedora informa os dados da nota (P1)

**Verificação**: cenários 5, 6, 12 em PASS.

- [X] T010 [US2] `gravar_dados_da_nota` (com o documento completando o cliente contratante se vazio) e `serializar_dados` em `app/calendar/pedido_de_nota_ops.py`
- [X] T011 [US2] `app/api/agenda_write.py`: ler `body["nota"]` por `ler_dados_da_nota` nas três portas (criação antes do Google; `NotaInvalida` → 400 `Corrija os campos destacados` com `fields`); `dados_mudariam` no 409 do cancelado do PATCH em bloco; `_create_event_row` (`app/calendar/routes.py`) grava os dados vindos do `data`
- [X] T012 [US2] `app/api/agenda_read.py`: `venda.nota` (com `doc_do_cliente`) e `pedida_por`/`pedida_em` em `notas_fiscais`
- [X] T013 [P] [US2] `frontend/apps/internal/src/lib/eventFormSchema.ts`: campos `nota_*`, refine do município, defaults, `SERVER_FIELD_MAP`/`FIELD_ORDER`; `lib/agenda.ts`: `venda.nota?` e `pedida_por?`/`pedida_em?`
- [X] T014 [US2] `frontend/apps/internal/src/components/EventFormBlocks/DadosDaNotaCampos.tsx` (novo) e uso em `ValoresBlock.tsx` sob o chip, com `AnimatePresence` + `useReducedMotion`
- [X] T015 [US2] `lib/eventCreate.ts` + `pages/EventCreatePage.tsx` + `pages/EventEditPage.tsx`: `nota` no corpo; hidratação do edit a partir de `venda.nota`
- [X] T016 [US2] `lib/eventInline.ts` + `components/EventDetail/ComercialSection.tsx`: `nota` no `EventComercialInput`, campos sob o checkbox com erros dos `fields`, leitura no `VendaPanel`

**Checkpoint**: dados gravados pelas três telas; erro no campo sem apagar o formulário.

---

## Phase 5: História 3 — painel urgente do Superadmin (P1)

**Verificação**: cenários 7–9 em PASS; Home aberta em desktop e 375×812.

- [X] T017 [US3] `tomador`, `vencimento`, `discriminacao` e `painel()` em `app/calendar/pedido_de_nota_ops.py` (consulta única com evento, clientes e parcelas)
- [X] T018 [US3] `app/api/dashboard_service.py`: bloco `notas_a_emitir` só com `is_superadmin`, dentro de `_bloco`
- [X] T019 [P] [US3] `frontend/apps/internal/src/lib/types.ts`: `NotaAEmitir`, `NotasAEmitirSummary`, `DashboardSummary.notas_a_emitir?`
- [X] T020 [US3] `frontend/apps/internal/src/components/home/PainelNotasAEmitir.tsx` (novo): linha com valor, tomador, evento, quem pediu, ISS, discriminação + `CopyButton`, "Inserir nota" (input oculto + `Button loading`, `PATCH …/invoices/<id>` com `amount` e `issue_date`), "Ver evento"
- [X] T021 [US3] `frontend/apps/internal/src/pages/DashboardPage.tsx`: `SectionKey "notas"`, card no resumo (`urgent = total`), painel, "Tudo em dia" conhecendo o bloco

**Checkpoint**: Superadmin emite pela Home; outros papéis não veem.

---

## Phase 6: História 4 — e-mail com o que fazer no assunto (P2)

**Verificação**: cenários 4, 10, 12 em PASS.

- [X] T022 [US4] `send_nota_pedida_email(nota, users)` em `app/email_service.py` (contracts §5, tom da 319)
- [X] T023 [US4] `avisar_notas_pedidas(event_id)` em `app/calendar/pedido_de_nota_ops.py` (reivindicação atômica, commit, `send_async` para os Superadmins ativos; nunca levanta)
- [X] T024 [US4] Chamar `avisar_notas_pedidas` depois do commit em `_create_event_core` (`app/calendar/routes.py`), `update_event_core` e `update_event_comercial` (`app/calendar/event_ops.py`)

**Checkpoint**: um e-mail por nota; venda gravada mesmo com falha de envio.

---

## Phase 7: Polimento e transversais

- [X] T025 `cd frontend && npm run typecheck` e `ruff check` nos arquivos tocados (`ruff format` só em `pedido_de_nota_ops.py`, migration e verify)
- [X] T026 Tela aberta (skill `manto-conferir-tela`): criação, "Editar tudo", card Comercial, Home do Superadmin em desktop e 375×812, "Ver como" Comercial
- [X] T027 Texto revisado pelo Princípio XV na tela aberta e no HTML do e-mail (`VERIFY_323_HTML`)
- [X] T028 `docs/01` (colunas, `venda.nota`, bloco `notas_a_emitir`, chave `nota` nas portas, §4.3), `docs/02` (Home e formulário da venda), `docs/04` (invariante da nota pedida), `docs/03` (entrada no topo + linha no índice)
- [X] T029 `quickstart.md` de ponta a ponta

---

## Dependências e ordem

- T001–T005 antes de tudo. US1 (T006–T009) antes de US2 (as mesmas assinaturas dos núcleos) e de
  US4 (o aviso parte da nota pedida). US3 depende só da Foundational e de T010 (`tomador`).
- Paralelo: T013 e T019 (tipos TS) com o backend da história; T014–T016 entre si não (mesmo schema).

## Estratégia

- MVP: Foundational + US1 (o furo fechado e a nota pedida em toda porta).
- Depois US2 → US3 → US4, um commit `feat(323):` por história, sempre por caminho.

---

## Phase 8: Convergence

- [X] T030 Completar o documento do cliente DEPOIS de refazer os vínculos de cliente no "Editar tudo" (hoje roda antes e acerta o contratante antigo) em `app/calendar/event_ops.py` e `app/calendar/pedido_de_nota_ops.py`, com cenário no verify per FR-005 (contradicts)
- [X] T031 Excluir as notas a emitir só na transição ligado → desligado (hoje toda gravação com o chip desligado apaga a nota lançada à mão pelo Financeiro) em `pedido_de_nota_ops.acompanhar_pedido` e nos dois núcleos, com cenário no verify per FR-013 (unrequested)
- [X] T032 Mostrar o documento do cliente contratante escolhido como sugestão no formulário de criação em `frontend/apps/internal/src/pages/EventCreatePage.tsx` per FR-005 / História 2 cenário 1 (partial)
- [X] T033 Destacar "Não informado" do CNPJ/CPF no e-mail em `app/email_service.py` per caso de borda "Cliente sem CNPJ" (partial)
- [X] T034 Ajustar a spec: com várias notas a discriminação é a da venda (mesmo texto), não por nota, em `specs/323-nota-pedida-ao-superadmin/spec.md` per caso de borda "Várias notas" (partial)
