---
description: "Tasks da feature 360 — Conferência de personagens do catálogo"
---
# Tasks: Conferência de personagens do catálogo (360)

**Input**: artefatos em `/specs/360-conferencia-de-personagens/`

**Pré-requisitos**: plan.md, spec.md (histórias e seção "Verificação"), research.md, data-model.md,
contracts/conferencia-api.md

**Verificação (Princípio VIII)**: `specs/360-conferencia-de-personagens/verify_360.py`, contra o
espelho `manto_360` (exceção ao `manto_local` registrada no plano). Escrito na fase Foundational,
antes do núcleo; nasce falhando por rota inexistente.

**Organização**: por história da spec.

## Formato: `[ID] [P?] [Story] Descrição`

## Phase 1: Setup

- [x] T001 Worktree `C:\tmp\mp360` na branch `360-conferencia-de-personagens` (da `main`), junções de
      `.venv` e `frontend/node_modules`, espelho `manto_360` do dump de 24/11 02h e
      `.specify/feature.json` apontando para `specs/360-conferencia-de-personagens`
- [x] T002 Leitura dos 13 itens novos (`C:\tmp\catalogo_personagens\propostas\saida_27.json`), com a
      lista de fichas soltas de 24/11
- [ ] T003 `specs/360-conferencia-de-personagens/montar_leitura.py`: junta o piloto (bloco `TEMAS` de
      `scripts/oneoff/piloto_personagens/conferencia.html`) e as saídas `saida_01..27.json` no formato
      do `data-model.md` e grava `app/admin/dados/leitura_personagens.json`; imprime totais por tipo,
      personagens, com ficha, sem foto e problemas

---

## Phase 2: Foundational (bloqueia as histórias)

- [ ] T004 Models `CatalogConferencia` e `CatalogConferenciaPersonagem` em `app/models.py` conforme
      `data-model.md` (relacionamentos só deste lado; property tolerante `recorte_list`)
- [ ] T005 Migration manual `migrations/versions/f360a1b2c3d4_conferencia_de_personagens.py`
      (`down_revision = "f353a1b2c3d4"`; CHECKs, UNIQUE, índice, FKs com `ondelete`); aplicar no
      `manto_360`
- [ ] T006 **`specs/360-conferencia-de-personagens/verify_360.py`** — os 18 cenários da spec (login só
      pela API; escrita conferida por conexão separada; cenários 4b, 9, 11b, 13 e 16 DEVEM falhar;
      limpeza no `finally`; `--manter` deixa a leitura carregada) — escrito AGORA e falhando por 404
- [ ] T007 Núcleo `app/admin/catalog_conferencia_ops.py`: constantes, `ConferenciaValidationError`,
      `ConferenciaConflito`, a regra da fila num lugar só (`filtro_da_fila`) e os serializers de item,
      conferência e personagem
- [ ] T008 Esqueleto de `app/api/admin_catalogo_conferencia_read.py` e
      `app/api/admin_catalogo_conferencia_write.py` (comentário `RBAC:`, `_require_superadmin`) e os
      dois imports em `app/api/__init__.py`

**Checkpoint**: verify roda e falha pelos motivos certos (rotas existem, comportamento ainda não).

---

## Phase 3: História 3 — Carregar a leitura sem estragar o que já foi conferido (P1)

Vem primeiro porque as outras histórias precisam de dado.

**Teste independente**: cenários 1, 2, 8 e 14 do verify.

- [ ] T009 [US3] `carregar_leitura(dados)` e `ler_arquivo_da_leitura()` em
      `app/admin/catalog_conferencia_ops.py`: `pg_advisory_xact_lock`, pula item que já tem
      conferência, tolera item, foto e ficha inexistentes, devolve o resumo
- [ ] T010 [US3] `POST /api/admin/catalogo/conferencia/carregar` em
      `app/api/admin_catalogo_conferencia_write.py`

---

## Phase 4: História 2 — A fila é a verdade da produção (P1)

**Teste independente**: cenários 5, 6, 7 e 15 do verify.

- [ ] T011 [US2] `listar_fila(tipo, situacao, q)` e `contadores()` em
      `app/admin/catalog_conferencia_ops.py`: uma consulta, sem N+1; "sem leitura" por `OUTER JOIN`;
      `leitura.a_carregar`
- [ ] T012 [US2] `GET /api/admin/catalogo/conferencia` em
      `app/api/admin_catalogo_conferencia_read.py`
- [ ] T013 [US2] `detalhe_do_item(item_id, tipo, q)` (com `na_fila`, `anterior_id`, `proximo_id`) e
      `GET /api/admin/catalogo/conferencia/<item_id>`

---

## Phase 5: História 1 — Conferir um item e não perder o que foi feito (P1)

**Teste independente**: cenários 3, 4 e 9 do verify; tela aberta.

- [ ] T014 [US1] `alterar_personagem` (só `decisao` nesta fase), `conferir` (com FR-017) e `reabrir`
      em `app/admin/catalog_conferencia_ops.py`, com trava e releitura da conferência (research R7)
- [ ] T015 [US1] Rotas `PATCH …/personagens/<id>`, `POST …/<item_id>/conferir` e `…/reabrir` em
      `app/api/admin_catalogo_conferencia_write.py` (409 `conferido` / `nao_conferido`)
- [ ] T016 [P] [US1] `frontend/apps/internal/src/lib/catalogoConferencia.ts`: tipos do contrato (campos
      opcionais onde o payload é novo) e hooks de fila, item e mutações
- [ ] T017 [US1] `frontend/apps/internal/src/components/conferencia/RecortePersonagem.tsx` (recorte
      por geometria, `loading="lazy"`, estado "Sem foto") e `PersonagemPropostoCard.tsx` (recorte,
      nome, ficha, aviso, "Criar"/"Não criar"; cada controle com rótulo acessível que cita o personagem,
      FR-016)
- [ ] T018 [US1] `frontend/apps/internal/src/pages/CatalogoConferenciaItemPage.tsx`: fotos do item no
      visualizador, tipo, nota, ação proposta, elenco, rodapé fixo "Conferir e ir para o próximo" /
      "Reabrir", estados "sem leitura" e "saiu da fila"; transição curta na troca de item e na
      mudança de estado do cartão, sob `useReducedMotion` (Princípio XI)
- [ ] T019 [US1] `frontend/apps/internal/src/pages/CatalogoConferenciaPage.tsx` (fila mínima:
      progresso, lista, "Continuar conferência", "Carregar leitura"), rotas em
      `frontend/apps/internal/src/App.tsx` e botão "Conferir personagens" em
      `frontend/apps/internal/src/pages/AdminCatalogoListPage.tsx`

**Checkpoint**: MVP — carregar, abrir a fila, conferir item por item, fechar e voltar.

---

## Phase 6: História 4 — Corrigir o que a leitura errou (P2)

**Teste independente**: cenários 10 a 13 do verify; tela aberta.

- [ ] T020 [US4] Núcleo: `alterar_personagem` completo (`nome`, `ficha_id`, `sem_foto`, `observacao`),
      `acrescentar_personagem`, `excluir_personagem` (só `manual`), `alterar_item` (`tipo`,
      `ficha_id`, `observacao`) em `app/admin/catalog_conferencia_ops.py`
- [ ] T021 [US4] Rotas `PATCH …/<item_id>`, `POST …/<item_id>/personagens` e
      `DELETE …/personagens/<id>` em `app/api/admin_catalogo_conferencia_write.py`
- [ ] T022 [US4] Tela: nome editável com o proposto visível, `FigurinoPicker` com a sugerida visível,
      "Criar sem foto", observação, "Acrescentar personagem", excluir com `ConfirmDialog`, tipo do item
      e ficha do avulso em `PersonagemPropostoCard.tsx` e `CatalogoConferenciaItemPage.tsx`; erro no
      campo sem perder o digitado

---

## Phase 7: História 5 — Encontrar um item e saber quanto falta (P2)

**Teste independente**: cenário 15 do verify; tela aberta.

- [ ] T023 [US5] Filtros por tipo e situação, busca e contadores por tipo em
      `CatalogoConferenciaPage.tsx`, com estado no endereço (`useSearchParams`, `replace`),
      `useRestaurarRolagem` e o filtro repassado ao detalhe para o "próximo"

---

## Phase 8: Portões e fechamento

- [ ] T024 `verify_360.py` verde nos 18 cenários contra `manto_360`
- [ ] T025 [P] `cd frontend && npm run typecheck`; `ruff check` nos Python tocados e `ruff format` nos
      arquivos novos
- [ ] T026 Tela aberta de verdade (skill `manto-conferir-tela`): `/admin/catalogo/conferencia` e um
      item de cada tipo, a 390×844 e em tela larga; textos lidos pelo Princípio XV
- [ ] T027 Docs: `docs/01` (§3 endpoints, §4.3 gates, schema), `docs/02` (telas), `docs/03` (entrada
      no topo + índice), `docs/04` (fluxo leitura → conferência → gravação e a regra da fila),
      `docs/05` (dívidas: gravar o conferido; leitura no repositório); decisão de arquitetura (carga
      explícita em vez de migration; a conferência não toca o catálogo) na entrada do `docs/03`, e em
      nota de `docs/decisoes/` se a 359 já estiver na `main`
- [ ] T028 `/speckit-converge` sem gaps; spec marcada com o resultado do verify

## Dependências

- Phase 2 bloqueia tudo. US3 (carga) antes de US2 e US1, que precisam de dado. US1 depende de T013
  (detalhe). US4 e US5 dependem de US1 (telas existem). T016 pode correr em paralelo com T014–T015.

## Estratégia

MVP = Phases 1 a 5 (carregar, fila viva, conferir com progresso salvo). US4 e US5 entram na mesma
entrega: sem US4 a conferência só aprova ou recusa, que é o defeito da página antiga.
