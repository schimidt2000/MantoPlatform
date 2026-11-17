---
description: "Tasks da feature 349 — o comercial mede e fecha pela conversa"
---
# Tasks: 349 — O comercial mede e fecha pela conversa

**Input**: artefatos em `/specs/349-comercial-mede-e-fecha/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Verificação (Princípio VIII)**: `specs/349-comercial-mede-e-fecha/verify_349.py`, contra o espelho **`manto_349`**
(exceção registrada no `plan.md`), escrito na fase Foundational ANTES do núcleo e falhando pelos motivos certos.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 Constantes da feature em `app/conversas/constantes.py` (motivos de perda e rótulos, qualificação, pontos e corte, rótulos dos sinais, recortes, degraus da régua, hora do lembrete, limite de 15 min, textos dos avisos e das recusas) — `data-model.md` §Constantes
- [X] T002 [P] Dois `kind` no catálogo de `app/notificacoes/notificacoes_ops.py` (`KIND_CONVERSA_LEMBRETE` com destinatário explícito, `KIND_CONVERSA_ORCAMENTO_PARADO` com COMERCIAL e SUPERADMIN)

---

## Phase 2: Foundational (bloqueia as histórias)

- [X] T003 13 colunas e 4 relações em `Conversa` (`app/models.py`), com o porquê em comentário — `data-model.md`
- [X] T004 Migration manual `migrations/versions/a349c0e1f2a3_comercial_mede_e_fecha.py` (`down_revision = "d334b2c4e6f8"`; colunas, FKs SET NULL, índice de `lembrar_em`, preenchimento da primeira mensagem e da primeira resposta; downgrade completo) e `flask db upgrade` no `manto_349`
- [X] T005 **`specs/349-comercial-mede-e-fecha/verify_349.py`** com os 18 cenários da spec (login pela API; escrita conferida por conexão separada; Meta, Google e push com dublê; cenários 5, 13 e 17 de recusa; limpeza no `finally`) — escrito agora e falhando nos cenários ainda não construídos

**Checkpoint**: `manto_349` em `a349c0e1f2a3`; verify roda e falha só no que falta.

---

## Phase 3: História 1 — Primeira resposta (P1) 🎯 MVP

**Verificação**: cenários 1, 2, 3 e (parte) 6 em PASS.

- [X] T006 [US1] `app/conversas/primeira_resposta_ops.py`: `registrar_contato`, `registrar_resposta` (UPDATEs condicionais) e `recalcular` (derivação pela régua de resposta válida)
- [X] T007 [US1] Ganchos: `aviso_ops._gravar_recebida` e `_gravar_eco`, `_aplicar_status` (falha), `instagram_ops._chegou_da_cliente` e `_gravar_eco`, `equipe_ops.resposta_da_equipe` (`app/conversas/`)
- [X] T008 [US1] Funil: colunas da coorte e métricas de primeira resposta no total, por grupo e nos parados em `app/conversas/funil_ops.py`

**Checkpoint**: a conversa guarda a primeira resposta; o funil devolve as métricas.

---

## Phase 4: História 2 — Perdida (P1)

**Verificação**: cenários 4, 5 e 6 em PASS.

- [X] T009 [US2] `app/conversas/venda_ops.py`: `marcar_perdida`, `reabrir` (validação no molde da 298; marcar apaga o lembrete), `motivos_de_perda()`
- [X] T010 [US2] `app/api/conversas_venda.py` (RBAC `pode_conversas` no topo do módulo e de cada view): `POST`/`DELETE …/perdida`; registrar em `app/api/__init__.py`
- [X] T011 [US2] Funil: perdidas da coorte, motivos e grupos; perdida nos parados (`app/conversas/funil_ops.py`)

---

## Phase 5: História 4 — Lista com selos e recortes (P1)

**Verificação**: cenários 9, 10 e 11 em PASS; tela em 390 px.

- [X] T012 [US4] `app/conversas/parado_ops.py`: predicado SQL único do orçamento parado (lista e régua)
- [X] T013 [US4] `app/conversas/pontuacao_ops.py`: `contexto(linhas)` com etapa (`funil_ops._etapas`), sinais e pontos em lote
- [X] T014 [US4] `app/conversas/venda_ops.py`: `resumos_da_lista(conversas)` (anúncio, etapa, qualificada, perdida, lembrete)
- [X] T015 [US4] `app/conversas/leitura_ops.py` (`recorte`, `dias`) e `app/api/conversas_read.py` (validação 422 e `venda` por item)
- [X] T016 [P] [US4] `frontend/apps/internal/src/lib/conversas.ts`: tipos `VendaResumo`, `Venda`, `Recorte`; parâmetros da lista; hooks da venda
- [X] T017 [US4] `components/conversas/SelosDaVenda.tsx` (novo), `ListaDeConversas.tsx`, `FiltroDaLista.tsx` (recortes + dias) e `pages/ConversasPage.tsx` (endereço)

---

## Phase 6: História 3 — Qualificada (P2)

**Verificação**: cenários 7 e 8 em PASS.

- [X] T018 [US3] `app/conversas/venda_ops.py`: `decidir_qualificacao` e `painel(conversa)` (o objeto `Venda` do contrato); `GET …/venda` e `POST …/qualificacao` em `app/api/conversas_venda.py`
- [X] T019 [US3] Funil: qualificadas no total, por grupo e nos parados (`app/conversas/funil_ops.py`)
- [X] T020 [US3] `components/conversas/PainelDaVenda.tsx` (novo) e `PerdidaDialog.tsx` (novo) montados em `ConversaAberta.tsx`: etapa, 1ª resposta (com o caso sem autor), qualificação com sinais, perda, reabrir, erro e carregando

---

## Phase 7: História 5 — Cotar sem sair (P2)

**Verificação**: tela (fluxo completo em 390 px).

- [X] T021 [US5] `pages/OrcamentoCalculadoraPage.tsx`: `conversa` e `cliente` no estado inicial, faixa de volta, "Gerar orçamento" volta para `/conversas?c=…&orcamento=…`
- [X] T022 [US5] `components/conversas/EnvioDoOrcamento.tsx` ("Fazer orçamento" e escolha automática do orçamento inicial), `CaixaDeEnvio.tsx`, `ConversaAberta.tsx` e `pages/ConversasPage.tsx` (parâmetro `orcamento` consumido)

---

## Phase 8: História 6 — Criar evento pela conversa (P2)

**Verificação**: cenários 12 e 13 em PASS; tela.

- [X] T023 [US6] `app/conversas/fechamento_ops.py`: `o_que_levar(conversa)` e o ponto único `ligar_evento_a_conversa(evento, conversa)`
- [X] T024 [US6] `app/api/agenda_write.py`: `conversa_id` em `POST /api/events` (422 antes do Google; vínculo depois do núcleo)
- [X] T025 [US6] "Criar evento" no `PainelDaVenda.tsx` (sem ficha → "Ligar à ficha"); `pages/EventCreatePage.tsx` + `lib/eventCreate.ts` leem `conversa`, põem a ficha e o vendedor e mandam `conversa_id`

---

## Phase 9: História 7 — Lembrete e régua (P2)

**Verificação**: cenários 14, 15 e 16 em PASS.

- [X] T026 [US7] `app/conversas/venda_ops.py`: `lembrar_amanha` e `cancelar_lembrete`; `POST`/`DELETE …/lembrete` em `app/api/conversas_venda.py`
- [X] T027 [US7] `app/conversas/parado_ops.py`: `avisar_lembretes(agora_sp)` (vencidos + régua, 9h–21h, push depois do commit) e a rotina em `app/conversas/varredura.py`
- [X] T028 [US7] "Lembrar amanhã"/"Cancelar lembrete" no `PainelDaVenda.tsx` e na lista "Pararam em" de `pages/FunilPage.tsx`; cartões e colunas novas do funil em `FunilPage.tsx` + `lib/funil.ts`

---

## Phase 10: Polimento e transversais

- [X] T029 `verify_349.py` todo verde contra `manto_349`
- [X] T030 `ruff check` nos Python tocados (`ruff format` só nos novos) e `cd frontend && npm run typecheck`
- [X] T031 Telas no Browser pane (backend 5349, Vite 6349) em 390 px e no computador: Conversas, conversa aberta, calculadora, criar evento, funil; texto revisado pelo Princípio XV
- [ ] T032 Docs: `docs/01` (inventário, §4.3 RBAC, schema), `docs/02` (telas), `docs/03` (entrada no topo + índice), `docs/04` §Conversas, `docs/05` (dívidas)

---

## Dependências e ordem

- Setup → Foundational → US1 → US2 → US4 → US3 → US5 → US6 → US7 → Polimento.
- US4 depende de `venda_ops` (US2) para o resumo da perdida; US3 usa `pontuacao_ops` (US4); US6 e US7 usam o
  `PainelDaVenda` (US3). US5 é independente do backend.
- Paralelos: T002 com T001; T016 com T012–T015 (arquivos diferentes); T021 com qualquer tarefa de backend.

## Estratégia

- MVP: Foundational + US1 + US2 + US4 (o que a vendedora usa o dia todo e o que o dono mede).
- Commits por grupo lógico (`feat(349):`), sempre por caminho; sem merge e sem push.
