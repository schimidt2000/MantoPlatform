---
description: "Tasks da feature 351 — painel atribuído"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Feature 351 — Painel atribuído

**Input**: artefatos em `/specs/351-painel-atribuido/`

**Pré-requisitos**: plan.md, spec.md (histórias e "Verificação"), research.md, data-model.md, contracts/api-351.md

**Verificação (OBRIGATÓRIA — constituição, Princípio VIII)**: `specs/351-painel-atribuido/verify_351.py`, contra o
espelho `manto_351` (exceção do plano). Escrito na fase Foundational, antes do núcleo, falhando pelos motivos certos.

**Organização**: por história da spec (US1…US8).

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 Constantes em `app/constants.py`: `ATRIBUICAO_JANELA_DIAS = 45`, `ATRIBUICAO_DESDE = date(2026, 6, 1)`,
      `INCREMENTALIDADE_PREMISSA = Decimal("0.50")`, `ANUNCIO_NO_AR_DIAS = 3`, `DIAS_NO_MES_DO_IMPACTO = 30`,
      `METRICAS_DO_TESTE` (rótulos), `JANELA_TESTE_PADRAO = 7`/`_MIN = 3`/`_MAX = 28`, `TEMAS_POR_PAGINA = 50`,
      `MARKETING_STATUS_FILA_ANUNCIO = ("pronto", "agendado", "publicado")`, `CONCEITO_MAX = 120`
- [X] T002 Backend próprio da rodada: copiar `scripts/db/run-local-sem-google.py` (checkout principal) para o
      scratchpad com a porta 5351; Vite na 6351 com config temporária (nada disso entra no commit)

---

## Phase 2: Foundational (bloqueia as histórias)

- [X] T003 Models em `app/models.py` conforme `data-model.md`: colunas novas em `MarketingFrente`, `MarketingPost`,
      `MarketingProposta`, `MarketingDiario`; classe nova `MarketingCalendario` (docstring com o porquê)
- [X] T004 Migration manual `migrations/versions/a351b0c1d2e3_painel_atribuido.py` (`down_revision = "d334b2c4e6f8"`):
      colunas, tabela `marketing_calendario` com UNIQUE e CHECK, 60 linhas com o foco da pesquisa §4.6; downgrade
      completo; aplicar no `manto_351` (`flask db upgrade`) e conferir `alembic_version`
- [X] T005 Esqueleto de `app/marketing/atribuicao_ops.py` (`Toque`, `VendaAtribuida`, assinaturas de
      `toques_pagos`, `atribuir_vendas`, `vendas_por_anuncio`, `clientes_novos`, `funil_com_custo`)
- [X] T006 **`specs/351-painel-atribuido/verify_351.py`** — os 28 cenários da spec (login por `POST /api/auth/login`
      com usuários descartáveis Superadmin, Marketing e Comercial; semeadura própria com prefixo `V351`; escrita
      conferida por conexão separada; cenários 15 e 26 DEVEM falhar com 403; limpeza no `finally`) — rodar e ver
      falhar nos cenários ainda não construídos

**Checkpoint**: migration no `manto_351`, verify falhando pelos motivos certos.

---

## Phase 3: História 1 — Custo por venda atribuída, por frente (P1) 🎯 MVP

**Verificação**: cenários 1–6 (e 26, 27) em PASS; Desempenho aberto.

- [X] T007 [US1] `app/marketing/atribuicao_ops.py`: `toques_pagos(client_ids)` (conversa, ficha, utm — relógios do
      research R3; frente da campanha por R5) e `_toque_da_venda` + `atribuir_vendas(inicio, fim, *, client_ids=None)`
      (regra R4; vendas com `frente_venda_sql()`; clientes por `event_clients` ∪ `client_id`)
- [X] T008 [US1] `app/marketing/comando_ops.py`: `gasto_por_frente(..., plataforma=None)`; `resumo_frentes` com
      `vendas_atribuidas`, `faturamento_atribuido`, `custo_venda_atribuida`, `custo_venda_atribuida_desconto`,
      `estado_atribuido`; `painel_frentes` com o bloco `atribuicao` (regra, `parcial`, `sem_frente`)
- [X] T009 [US1] `app/marketing/atribuicao_ops.py`: `lista_vendas(inicio, fim, *, com_valor)` (até 100, com contato,
      campanha e anúncio) e período por `weeks`/`start&end` (`periodo_do_painel`) no relógio de SP
- [X] T010 [US1] `app/api/marketing_comando_read.py`: `GET /api/marketing/atribuicao` (gate `require_marketing_access`;
      `com_valor = eh_superadmin`; 400 em datas; 422 do funil no envelope) — comentário RBAC no topo
- [X] T011 [P] [US1] `frontend/apps/internal/src/lib/marketing.ts`: tipos novos (opcionais) de `DesempenhoFrente`,
      `DesempenhoAtribuicao`, `AtribuicaoResponse` e `useAtribuicao(params, dividir)`
- [X] T012 [US1] `frontend/apps/internal/src/components/marketing/PainelFrentes.tsx`: card com misto × atribuído ×
      com desconto, estado atribuído, premissa e regra escritas (FR-007), bloco "sem frente" das vendas atribuídas,
      aviso de período parcial
- [X] T013 [US1] `frontend/apps/internal/src/components/marketing/AtribuicaoPainel.tsx` (novo): lista "Vendas
      atribuídas" (valor só quando vier) com carregando/erro/vazio; montado em `MarketingDesempenhoPage.tsx` (fora
      das linhas 65-83)

**Checkpoint**: custo atribuído por frente verificado e visível.

---

## Phase 4: História 2 — Funil por frente, anúncio, peça e conceito, com custo (P1)

**Verificação**: cenários 7–9 em PASS; Desempenho e `/funil` abertos.

- [X] T014 [US2] `app/conversas/constantes.py`: `DIVISOES_DO_FUNIL` + `frente`, `anuncio`, `peca`, `conceito`; chaves e
      textos dos grupos "Sem frente", "Sem peça", "Sem conceito"; texto de divisão inválida
- [X] T015 [US2] `app/conversas/funil_ops.py`: coorte com `anuncio_id`/`campanha_id`; `Linha` com os campos novos;
      `_grupos` com as quatro divisões (import tardio de `comando_ops` para a frente; rótulo do anúncio por
      `anuncios_meta.nome`; peça e conceito por `marketing_post_anuncios`/`marketing_posts`); sem dinheiro
- [X] T016 [US2] `app/marketing/atribuicao_ops.py`: `funil_com_custo(inicio, fim, dividir)` — gasto por grupo (R6) e
      `custo_conversa`/`custo_orcamento`/`custo_evento`; ligado ao `GET /api/marketing/atribuicao`
- [X] T017 [P] [US2] `frontend/apps/internal/src/lib/funil.ts` e `pages/FunilPage.tsx`: opções novas de divisão
- [X] T018 [US2] `AtribuicaoPainel.tsx`: bloco "Funil com custo" com seletor de divisão (no endereço), cartões em
      390 px, carregando/erro/vazio

**Checkpoint**: funil por frente/anúncio/peça/conceito com custo (Marketing) e sem dinheiro (Comercial).

---

## Phase 5: História 3 — Resultado real da peça e conceito (P2)

**Verificação**: cenários 10–13 e 23 em PASS; diálogo do card aberto.

- [X] T019 [US3] `app/conversas/funil_ops.py`: `etapas_por_anuncio(anuncio_ids)` (conversa pelo primeiro anúncio,
      `_etapas`)
- [X] T020 [US3] `app/marketing/atribuicao_ops.py`: `vendas_por_anuncio(anuncio_ids)`
- [X] T021 [US3] `app/marketing/marketing_ops.py`: `conceito` em `create_post`/`update_post`/`serialize_post`;
      `resultados_por_post` com conversas reais, orçamentos, eventos, vendas, faturamento, `no_ar`/`ultimo_gasto_em`
      por anúncio, `anuncios_no_ar`, `ultima_leitura`
- [X] T022 [US3] `app/marketing/comando_ops.py`: `cards_prontos_sem_anuncio` com `MARKETING_STATUS_FILA_ANUNCIO`;
      `criar_pedidos` aceita `conceito`
- [X] T023 [US3] `app/api/marketing_write.py`: `conceito` no POST/PATCH do card (erro no campo)
- [X] T024 [P] [US3] `lib/marketing.ts` + `components/MarketingPostDialog.tsx`: campo Conceito; texto "no ar" ×
      "sem gasto desde dd/mm" × "sem leitura"; resultado real (conversas, orçamentos, vendas, faturamento)

**Checkpoint**: card mostra o resultado real; fila da rotina não perde card arrastado.

---

## Phase 6: História 4 — Meta, verba e calendário do ano (P2)

**Verificação**: cenários 14–16 em PASS; diálogos abertos.

- [X] T025 [US4] `app/marketing/comando_ops.py`: `salvar_frentes` com `metas`/`verbas`; `frentes_config` com meta e
      verba; `calendario()`, `salvar_calendario(frente, meses, user_id)`, `metas_do_mes(mes)`; `resumo_frentes` com
      `mes_corrente`; `contexto_comando` com `calendario` e `metas_do_mes`
- [X] T026 [US4] `app/api/marketing_comando_read.py` / `_write.py`: `GET|PATCH /api/marketing/calendario` (escrita só
      Superadmin real, 403); `PATCH /api/marketing/frentes` com `metas`/`verbas`
- [X] T027 [P] [US4] `lib/marketing.ts` + `components/marketing/FrentesConfigDialog.tsx`: meta e verba por frente
      (`MoneyInput`), erro no campo
- [X] T028 [US4] `components/marketing/CalendarioDialog.tsx` (novo): frente (5 opções) × 12 meses (meta, verba,
      foco), mês corrente destacado, salvar com "Salvando…", carregando/erro/vazio (FR-032); aberto do
      `PainelFrentes`; mês corrente no card

**Checkpoint**: meta/verba/calendário salvos e lidos pela rotina.

---

## Phase 7: História 5 — Proposta com número, frente, teto, impacto e sino (P2)

**Verificação**: cenários 17–19 em PASS; Decisões aberta.

- [X] T029 [US5] `app/notificacoes/notificacoes_ops.py`: `KIND_MARKETING_PROPOSTA` → `(SUPERADMIN,)` e
      `notificar_proposta_marketing(proposta)`
- [X] T030 [US5] `app/marketing/comando_ops.py`: `_reais_do_texto`, frente da proposta (R9), números,
      `criar_proposta` com aviso na mesma transação; `serialize_proposta` com `frente`, `frente_nome`,
      `valor_*_num`, `impacto_mensal`, `teto`, `verba_mes`; `impacto_aprovado_mes()`
- [X] T031 [US5] `app/api/marketing_comando_read.py`: `GET /api/marketing/propostas` com `impacto_aprovado_mes`
- [X] T032 [P] [US5] `components/notificacoes/NotificacaoItem.tsx`: ícone do `marketing.proposta`
- [X] T033 [US5] `lib/marketing.ts` + `pages/MarketingDecisoesPage.tsx`: frente, teto, verba da frente, impacto no mês
      no card; soma do mês no topo

**Checkpoint**: proposta com números e aviso no sino.

---

## Phase 8: História 6 — Diário com teste estruturado (P3)

**Verificação**: cenários 20–22 em PASS; aba Diário aberta.

- [X] T034 [US6] `app/marketing/comando_ops.py`: `_medir(platform, tipo, id, metrica, de, ate)` (R10),
      `_teste_da_entrada(e)`, `criar_entrada` com os campos do teste e linha de base congelada, `serialize_diario` com
      `teste`; `marcar_execucao` herdando alvo e métrica
- [X] T035 [US6] `lib/marketing.ts` + `pages/MarketingDecisoesPage.tsx`: formulário com alvo, métrica, dia, janela e
      controle (opcionais, erro no campo); card com antes, depois, variação, controle, efeito líquido, "em andamento",
      "sem leitura" (FR-032)

**Checkpoint**: diário com teste calculado no servidor.

---

## Phase 9: História 7 — Marketing no celular (P3)

**Verificação**: cenário 24 em PASS; telas em 390 × 844 sem rolagem lateral.

- [X] T036 [US7] `app/marketing/comando_ops.py` + `app/api/marketing_comando_read.py`: `listar_temas_licenca` paginado
      (`pagina`, `total`, `paginas`, `por_pagina`)
- [X] T037 [P] [US7] `lib/marketing.ts` + `pages/MarketingTemasPage.tsx`: página no endereço, filtro zera a página,
      linha que empilha em 390 px, "Confirmar as sugestões desta página"
- [X] T038 [P] [US7] `pages/MarketingDesempenhoPage.tsx`: tabela de campanhas vira cartões abaixo de `md`
- [X] T039 [P] [US7] `pages/MarketingPainelPage.tsx` + `components/MarketingKanban.tsx`: filtros frente, tipo, "Minhas
      peças" no endereço (filtro na tela), frente no card

**Checkpoint**: três telas sem rolagem lateral.

---

## Phase 10: História 8 — Custo por cliente novo vindo de anúncio (P3)

**Verificação**: cenário 25 em PASS.

- [X] T040 [US8] `app/marketing/atribuicao_ops.py`: `clientes_novos(inicio, fim)` → `(total, de_anuncio)`
- [X] T041 [US8] `app/marketing/desempenho_ops.py`: `_cac` com `new_clients_ads` e `value = spend ÷ new_clients_ads`
- [X] T042 [US8] `pages/MarketingDesempenhoPage.tsx`: tile "Custo por cliente novo de anúncio" com "N de M clientes
      novos vieram de anúncio"

---

## Phase 11: Polimento e transversais

- [X] T043 `verify_351.py` inteiro verde contra `manto_351` (28 cenários; 15 e 26 recusados)
- [X] T044 `cd frontend && npm run typecheck` limpo e `ruff check` nos arquivos Python tocados (`ruff format` só em
      `atribuicao_ops.py` e na migration)
- [X] T045 Telas abertas (Browser pane, 5351/6351, `manto_351`): Desempenho, Decisões, Temas, Painel + diálogo do card,
      diálogos de frentes e calendário, Funil — em 390 × 844 e tela larga
- [X] T046 Texto novo revisado pelo Princípio XV na tela aberta
- [X] T047 Docs: `docs/01` (endpoints, campos, §4.3, schema), `docs/02` (telas), `docs/03` (entrada no topo + índice),
      `docs/04` (regra da atribuição; funil por frente), `docs/05` (214 em parte; dívidas novas)
- [X] T048 `/speckit-converge` e commits por caminho (`feat(351):`, `docs(351):`); temporários da rodada apagados

---

## Dependências e ordem

- Setup → Foundational (T003–T006) → US1 (T007 é base de US2, US3 e US8) → US2 → US3 → US4 → US5 → US6 → US7 → US8 →
  Polimento.
- US4, US5, US6 e US7 não dependem da atribuição: podem andar em paralelo à US2/US3 quando os arquivos não colidem
  (`comando_ops.py` é compartilhado — uma história por vez nele).
- Dentro da história: `_ops` → endpoint → `lib/marketing.ts` → tela; verify da história em PASS no fim.

## Paralelismo

- T011 (tipos) junto de T007–T010; T017 (Funil do Comercial) junto de T016; T032 (ícone) junto de T030; T037, T038 e
  T039 entre si (arquivos diferentes).

## Estratégia

- **MVP**: Setup + Foundational + US1 → custo atribuído por frente verificado e na tela.
- **Incremental**: US2 (funil com custo) → US3 (card) → US4/US5 (metas e propostas) → US6/US7/US8.
- Commit por grupo lógico, sempre por caminho; nunca `git add -A`.

---

## Phase 12: Convergence

- [X] T049 Devolver a lista de vendas atribuídas mesmo quando o funil recusa o período (mais de um ano): `funil` vazio com o motivo e aviso na tela, em `app/api/marketing_comando_read.py` e `AtribuicaoPainel.tsx`, per spec §Casos de borda (partial)
- [X] T050 Extrair a validação do teste (`_campos_do_teste`) e a linha de cada frente (`resumo_frentes`) em funções de até ~30 linhas em `app/marketing/comando_ops.py`, per Constitution II (contradicts)
- [X] T051 Subir o teto da lista de vendas atribuídas (`VENDAS_NA_LISTA`) em `app/marketing/atribuicao_ops.py`, per SC-002 (partial)
- [X] T052 Corrigir a redação da FR-001 em `specs/351-painel-atribuido/spec.md`: a função única cobre a venda atribuída (frente, lista, card); funil e cliente novo leem a origem do contato, per FR-001 (partial)
