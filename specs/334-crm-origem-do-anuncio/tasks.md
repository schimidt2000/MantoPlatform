---
description: "Tasks da feature 334 — De qual anúncio veio cada cliente"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 334 — De qual anúncio veio cada cliente

**Input**: `specs/334-crm-origem-do-anuncio/` (spec, plan, research R1–R8, data-model, contracts).

**Verificação (Princípio VIII)**: `verify_334.py` (molde do `verify_333`), escrito na Foundational, antes do núcleo. Os
verifies 325, 328, 330, 332 e 333 são regressão.

**Base**: worktree `C:\tmp\mp334`, branch `334-crm-origem-do-anuncio` sobre a 333. Sem merge e sem push.

---

## Phase 1: Setup

- [X] T001 [P] `app/conversas/constantes.py`: origens ("Anúncio do WhatsApp", "Anúncio do Instagram", "WhatsApp",
  "Instagram"), `utm_source`/`utm_medium`, tipos do contato, prazo da reconsulta (24 h) e lote (10).
- [X] T002 [P] `app/config.py`: `META_ANUNCIOS_TOKEN` (vazio); `render.yaml` com `sync: false`; o log `[anuncios]` em
  `app/__init__.py`.

## Phase 2: Foundational

- [X] T003 `app/models.py`: `ConversaAnuncio`, `AnuncioMeta` e as 4 colunas de `Client`. Migration à mão
  `migrations/versions/d334b2c4e6f8_origem_do_anuncio.py` (`down_revision="c333e1a5b7d9"`). Aplicar no `manto_local` e
  ensaiar o downgrade.
- [X] T004 **`specs/334-crm-origem-do-anuncio/verify_334.py`** com os 11 cenários da spec. Falha agora.

## Phase 3: Histórias 1 e 2 — Captura e campanha (P1)

- [X] T005 [US2] `app/integracoes/meta_anuncios_client.py`: `consultar_anuncio(conexao, anuncio_id)`.
- [X] T006 [US1] `app/conversas/anuncio_ops.py`: `registrar_contato`, `consultar_pendentes`, `reconsultar` (com a
  propagação da campanha) e as leituras (`anuncio_da_conversa`, `origem_da_ficha`).
- [X] T007 [US1] Captura em `aviso_ops._gravar_recebida` (WhatsApp) e `instagram_ops._processar_item` (Instagram, com a
  abertura sem mensagem); `processar_aviso` chama `consultar_pendentes` depois do commit; `varredura` chama
  `reconsultar`.

## Phase 4: História 3 — A ficha (P1)

- [X] T008 [US3] `anuncio_ops.aplicar_na_ficha` e `origem_organica`; chamados na captura, em `ficha_ops.ligar`,
  `ficha_ops.ficha_para_envio` e `aviso_ops._vincular_cliente`.
- [X] T009 [US3] `app/api/conversas_read.py` (`anuncio` no detalhe) e `app/api/clientes_read.py` (`origem`).
- [X] T010 [US3] Front:
  - `lib/conversas.ts` e `lib/clientes.ts`: os tipos;
  - `ConversaAberta.tsx`: "Veio do anúncio…";
  - `ClientDetailPage.tsx`: Origem, Primeiro anúncio, Anúncio mais recente.

## Phase 5: História 4 — O Desempenho (P2)

- [X] T011 [US4] `app/marketing/desempenho_ops.py`: `attributed_clients` pela data de entrada (`coalesce`);
  `retornos_por_campanha`; `returns`/`return_events` na tabela de campanhas.
- [X] T012 [US4] `lib/marketing.ts` e `MarketingDesempenhoPage.tsx`: a coluna "Retornos" e o texto de ajuda.

## Phase 6: Polimento

- [X] T013 `ruff`, `npm run typecheck`; verifies 334, 333, 332, 330, 328 e 325 verdes.
- [X] T014 Tela pela worktree em desktop e 375×812 (quickstart §2).
- [X] T015 Docs: `docs/01`, `docs/02`, `docs/03` (**NÃO PUBLICADO**), `docs/04`, `docs/05` e o plano. Gates
  CHK001–CHK011.

## Phase 7: Convergence

Revisor independente, só de leitura: 9 achados (0 críticos, 0 altos, 2 médios, 7 baixos).

- [X] T016 Desempenho no horário de São Paulo: `created_at` e o `momento` do contato (UTC) convertidos antes da janela e
  do dia; o `kommo_created_at` já é de São Paulo per FR-010 (contradicts)
- [X] T017 `verify_334` cenário 11: ficha do Kommo com origem chega por anúncio, ficha existente ligada à mão, ficha que
  nasce depois e liga pelo telefone per FR-005/FR-007 (partial)
- [X] T018 `_propagar_pendentes` na varredura: a campanha que a corrida de dois workers deixou para trás per FR-005
  (partial)
- [X] T019 `verify_334`: consulta que quebra (aviso processado), eventos do retorno, ficha das 22 h e do Kommo sem data,
  token próprio per FR-002/FR-010/FR-011 (partial)
- [X] T020 Ficha: a campanha própria (do Kommo) aparece na Origem quando difere da do primeiro anúncio per FR-009
  (partial)
- [X] T021 Tipo de retorno em `_entrada_na_base` per Constitution II (partial)
- [X] T022 Abertura do Instagram sem mensagem fora das páginas 2+ da lista: aceito e registrado (`docs/05` 196); N+1 em
  `retornos_por_campanha` aceito (o mesmo padrão de `attributed_clients`) per FR-001 (partial)
- [X] T023 `verify_328` cenário 11 independente da hora do dia (só passava depois das 14 h) per Constitution VIII
  (unrequested)

## Dependências

Setup → Foundational → US1/US2 → US3 → US4 → Polimento. O T007 mexe no `processar_aviso` e nos processadores: os
verifies 325, 330 e 332 rodam logo depois.
