---
description: "Tasks da feature 350 — base autorizada"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 350 — base autorizada

**Input**: artefatos em `/specs/350-base-autorizada/`

**Pré-requisitos**: plan.md, spec.md (histórias e "Verificação"), research.md, data-model.md,
contracts/api.md

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `specs/350-base-autorizada/verify_350.py` contra o
espelho próprio `manto_350`, escrito na fase Foundational, antes do núcleo.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [ ] T001 Constantes em `app/constants.py`: `CONSENTIMENTO_TIPO_*`, `CONSENTIMENTO_ACAO_*`, textos e versões (`CONSENTIMENTO_NOVIDADES_TEXTO/_VERSAO`, `CONSENTIMENTO_ANIVERSARIO_TEXTO/_VERSAO`), `VIRTUAL_ACEITE_TEXTO` (o rótulo da loja, junto de `VIRTUAL_ACEITE_VERSAO`), origens (`CONSENTIMENTO_ORIGENS_EQUIPE` e as automáticas), `PALAVRAS_DE_SAIDA`, `ERRO_WHATSAPP_PEDIU_PARA_NAO_RECEBER = 131050`, `PARCEIRO_TIPOS`, `POS_EVENTO_CANAL_*`, `POS_EVENTO_DIAS = 7`, `ANIVERSARIOS_DIAS_PADRAO = 60`, `CRIANCA_IDADE_MAXIMA = 17`

---

## Phase 2: Foundational (bloqueia as histórias)

- [ ] T002 Models em `app/models.py`: `Parceiro`, `ClienteConsentimento`, `ClienteCrianca`, `PosEvento`; colunas novas em `Client` (`marketing_opt_in_version`, `marketing_opt_out_at`, `marketing_opt_out_source`, `indicado_por_id`, `parceiro_id`) — sem backref nas filhas (data-model §clients)
- [ ] T003 Migration manual `migrations/versions/a350b1c2d3e4_base_autorizada.py` (`down_revision = "d334b2c4e6f8"`; upgrade e downgrade completos); aplicar no `manto_350` e ensaiar downgrade → upgrade
- [ ] T004 Núcleo base `app/clientes/consentimento_ops.py`: `ConsentimentoErro(campo, mensagem, status)`, `registrar_aceite_novidades`, `retirar_aceite_novidades`, `pode_prospectar`, `serializar(client, com_criancas)` (sem commit)
- [ ] T005 **`specs/350-base-autorizada/verify_350.py`** — os 19 cenários da spec (dublê da Meta + disjuntor de rede, molde `verify_325`; login pela API; conexão separada; cenário 4 DEVE falhar; limpeza `v350-` no `finally`) — escrito agora, falhando nos cenários não construídos

**Checkpoint**: `manto_350` em `a350b1c2d3e4`; verify roda e falha pelos motivos certos.

---

## Phase 3: História 1 — Aceites na ficha e na conversa (P1) 🎯 MVP

**Verificação**: cenários 1–6 do `verify_350.py`; ficha e conversa abertas em 390 px.

- [ ] T006 [US1] `app/clientes/consentimento_ops.py`: `inserir_crianca` (validação de nome, data, aceite, origem) e `remover_crianca` (apaga + retirada sem dado da criança)
- [ ] T007 [US1] `app/api/clientes_base_write.py` (novo, docstring `RBAC:`): `POST|DELETE /clientes/<id>/consentimentos/novidades`, `POST /clientes/<id>/criancas`, `DELETE /clientes/<id>/criancas/<cid>` — gate Comercial/Superadmin; registrar em `app/api/__init__.py`
- [ ] T008 [US1] `app/api/clientes_read.py`: detalhe ganha `consentimentos` (crianças só Comercial/Superadmin), `pode_prospectar`, `flags.pode_editar_base`; lista ganha `flags`
- [ ] T009 [US1] `app/conversas/leitura_ops.py`: `_cliente` ganha `aceite_novidades`
- [ ] T010 [P] [US1] `frontend/apps/internal/src/lib/baseAutorizada.ts`: tipos + hooks de consentimento e criança; `lib/clientes.ts` e `lib/conversas.ts` com os campos novos opcionais
- [ ] T011 [US1] `frontend/apps/internal/src/components/clientes/AceiteDeNovidadesDialog.tsx` (texto exato, origem na lista fechada, registrar/retirar) e `CriancaDialog.tsx`
- [ ] T012 [US1] `frontend/apps/internal/src/components/clientes/ConsentimentosCard.tsx` + encaixe em `pages/ClientDetailPage.tsx` (substitui a linha só-leitura do aceite)
- [ ] T013 [US1] `frontend/apps/internal/src/components/conversas/AceiteNaConversa.tsx` + encaixe no cabeçalho de `ConversaAberta.tsx`

**Checkpoint**: aceite registrado e retirado pela ficha e pela conversa; verify 1–6 verdes.

---

## Phase 4: História 2 — Saída automática e guarda do modelo de marketing (P1)

**Verificação**: cenários 7–9.

- [ ] T014 [US2] `app/clientes/consentimento_ops.py`: `e_pedido_de_saida(texto)`, `retirar_se_pediu_para_parar(conversa, texto, referencia)`, `retirar_por_erro_do_whatsapp(conversa, codigo, referencia)`, `conversa_pode_receber_marketing(conversa)`
- [ ] T015 [US2] `app/conversas/aviso_ops.py`: gancho em `_gravar_recebida` (texto e interativa) e em `_aplicar_status` (131050)
- [ ] T016 [US2] `app/conversas/envio_ops.py`: gancho em `_registrar_falha` (131050) e recusa `sem_aceite` em `enviar_modelo` para categoria MARKETING; texto em `app/conversas/constantes.py`
- [ ] T017 [US2] `app/conversas/instagram_ops.py`: gancho da palavra de saída em `_gravar_recebida`

**Checkpoint**: saída por palavra e por 131050; modelo de marketing recusado sem aceite.

---

## Phase 5: História 3 — Pós-evento único (P1)

**Verificação**: cenários 10–13; diálogo do evento, lista e página pública (375×812).

- [ ] T018 [US3] `app/clientes/pos_evento_ops.py`: `mensagem(event, fotos_url)`, `estado(event)`, `registrar(event, canal, fotos_url, user_id)`, `enviar_pela_conversa(...)` (import tardio de `envio_ops`, chave `pos-evento-<id>`), `listar_recentes(agora)`
- [ ] T019 [US3] `app/api/clientes_base_read.py` (novo): `GET /pos-evento`, `GET /events/<id>/pos-evento`; `clientes_base_write.py`: `POST /events/<id>/pos-evento` — gate Comercial/Superadmin, 409 `cancelado`
- [ ] T020 [US3] `app/api/feedback_write.py`: bloco `consentimento` no `GET /avaliar/<token>`; `POST /avaliar/<token>/consentimento` (10/h, versão do texto, 409 `sem_ficha`/`texto_mudou`) usando `consentimento_ops`
- [ ] T021 [P] [US3] `frontend/apps/internal/src/components/EventDetail/PosEventoDialog.tsx` + `EventHeader.tsx` ("Pós-evento" no lugar de "Pedir feedback da cliente"; `buildFeedbackMsg` sai de `lib/eventDetail.ts`)
- [ ] T022 [US3] `frontend/apps/internal/src/pages/PosEventoPage.tsx` (rota `/clientes/pos-evento` em `App.tsx`; link no cabeçalho de `ClientsListPage.tsx`)
- [ ] T023 [P] [US3] `frontend/apps/public/src/lib/feedback.ts` (tipos opcionais + hook do POST), `components/feedback/ConsentimentoCard.tsx`, `components/feedback/IndicarAmiga.tsx`, encaixe na tela de agradecimento de `pages/AvaliarPage.tsx` (Google intocado)

**Checkpoint**: pós-evento copiado/enviado e registrado; aceite colhido na página pública.

---

## Phase 6: História 4 — Indicado por e parceiro (P2)

**Verificação**: cenários 14–15.

- [ ] T024 [US4] `app/clientes/parceiro_ops.py` (criar, editar, listar com contagem, validação) e `app/clientes/indicacao_ops.py` (`definir`, `serializar`)
- [ ] T025 [US4] Endpoints: `GET /parceiros` em `clientes_base_read.py` (Comercial/Financeiro/Superadmin); `POST|PATCH /parceiros…` e `PATCH /clientes/<id>/indicacao` em `clientes_base_write.py`; detalhe da ficha com `indicado_por`, `indicacoes`, `parceiro`
- [ ] T026 [P] [US4] `frontend/apps/internal/src/components/clientes/IndicacaoCard.tsx` (Combobox de ficha e de parceiro) + encaixe na ficha
- [ ] T027 [US4] `frontend/apps/internal/src/pages/ParceirosPage.tsx` (lista, criar, editar, desativar; rota `/clientes/parceiros`; link na lista de clientes)

---

## Phase 7: História 5 — Aniversários dos próximos 60 dias (P2)

**Verificação**: cenário 16.

- [ ] T028 [US5] `app/clientes/aniversario_ops.py`: `proximo_aniversario(nascimento, hoje)` (29/02) e `listar(hoje, dias)` (dois aceites)
- [ ] T029 [US5] `GET /clientes/aniversarios` em `clientes_base_read.py` (Comercial/Superadmin)
- [ ] T030 [US5] `frontend/apps/internal/src/pages/AniversariosPage.tsx` (rota `/clientes/aniversarios`; link na lista de clientes)

---

## Phase 8: História 6 — O orçamento pede o aceite (P3)

**Verificação**: cenário 17.

- [ ] T031 [US6] `app/orcamento/quote_ops.py`: linha do convite ("responda QUERO") no fim da mensagem de WhatsApp, deslocamento intacto

---

## Phase 9: Loja (344) e polimento

- [ ] T032 `app/marketing/virtuais_ops.py`: a venda grava o aceite no histórico (texto e versão da loja, referência `pedido:<id>`) e não reaplica aceite anterior à última retirada (cenário 18)
- [ ] T033 `verify_350.py` verde de ponta a ponta contra `manto_350`
- [ ] T034 `ruff check` nos arquivos Python tocados; `ruff format` só nos novos; `cd frontend && npm run typecheck`
- [ ] T035 Telas abertas no Browser pane (backend 5350, Vite 6350): ficha, conversa, Pós-evento, Aniversários, Parceiros, diálogo do evento em 390 px; página pública em 375×812; textos pelo Princípio XV
- [ ] T036 Docs: `docs/01` (endpoints, gates §4.3, schema), `docs/02` (telas), `docs/03` (entrada no topo + índice), `docs/04` (Clientes: consentimento; Conversas: saída automática), `docs/05` (dívida do opt-out manual riscada; o que fica), `docs/00` §6 item 2 (relógio)
- [ ] T037 Commits por caminho (`feat(350):` / `docs(350):`), sem merge e sem push

---

## Dependências e ordem

- Setup → Foundational (T002–T005) → US1 → US2 → US3 → US4 → US5 → US6 → T032 → polimento.
- US2 e US3 usam `consentimento_ops` de T004/T006; US4 e US5 são independentes entre si.
- Em cada história: `_ops` → endpoint → `lib` → componente → página.

## Paralelismo

- T010 (lib) com T007–T009 (backend) da US1; T021 e T023 (dois apps) com T019–T020; T026 com T024–T025.

## Estratégia

- **MVP**: Setup + Foundational + US1 + US2 (a base passa a ser autorizável e a saída é automática).
- **Incremental**: US3 (pós-evento) entrega o pedido de aceite; US4–US6 completam a base.
