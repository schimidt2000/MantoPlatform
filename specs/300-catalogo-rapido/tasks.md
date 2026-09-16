---
description: "Tasks — Feature 300, catálogo rápido"
---
# Tasks: Catálogo rápido

**Input**: artefatos em `/specs/300-catalogo-rapido/`

**Pré-requisitos**: `plan.md`, `spec.md` (5 histórias + seção Verificação), `research.md`,
`data-model.md`, `contracts/catalogo-listagens.md`

**Verificação (OBRIGATÓRIA — constituição, Princípio VIII)**: `specs/300-catalogo-rapido/verify_300.py`
contra `manto_local`. A tarefa que ESCREVE o verify está na fase Foundational, ANTES de qualquer
alteração de comportamento — ele nasce **falhando** e passa história a história.

**Sem migration**: `app/models.py` não muda. As tarefas de modelo e migration do template saem.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1…US5, na numeração das histórias da spec

---

## Phase 1: Setup

**⚠️ A T001 precede QUALQUER alteração de código.** O contrato desta feature é "a resposta não
muda" (FR-003), e a referência do "antes" é impossível de obter depois que o código mudar.

- [X] T001 Capturar a impressão digital das respostas de hoje em
      `specs/300-catalogo-rapido/referencia_300.json`: para cada um dos 5 endpoints do
      `contracts/catalogo-listagens.md`, o SHA-256 do JSON canônico (chaves ordenadas), a contagem
      de itens e a contagem de consultas medida. Guardar o hash e os totais, **não** os payloads —
      são ~600 KB que não pertencem ao repositório. Script de apoio pode viver no scratchpad.

**Checkpoint**: referência gravada e commitada antes de tocar em qualquer arquivo de produção.

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T002 `specs/300-catalogo-rapido/verify_300.py` — os 7 cenários da seção "Verificação" da spec,
      com ouvinte `before_cursor_execute` contando consultas e `db.session.expire_all()` antes de
      cada medida; login só por `POST /api/auth/login` com usuário descartável; cenário 5 **DEVE
      falhar** (papel sem permissão no gerenciador e no endpoint novo); limpeza no `finally` com
      `rollback()` e `user.roles.clear()` antes de apagar o usuário. Compara contra
      `referencia_300.json` da T001.
- [X] T003 Rodar o verify e **confirmar que ele falha pelos motivos certos**: teto de consultas
      estourado nos cenários 1, 3 e 4; o cenário 4 falha por rota inexistente. Um verify que passa
      com o código de hoje é defeito do verify, não do código.

**Checkpoint**: verify escrito e falhando pelos motivos certos.

---

## Phase 3: História 1 — O gerenciador abre sem esperar pelo servidor (P1) 🎯 MVP

**Objetivo**: os três modos do gerenciador deixam de fazer uma consulta por produto — 1.846 e 474
(2.320 na aba Personagens) caem para um punhado, com a resposta idêntica.

**Verificação da história**: cenário 1 do `verify_300.py` em PASS.

- [X] T004 [US1] `app/api/admin_catalogo_read.py:81-98`: `.options(selectinload(...))` na consulta
      da listagem, cobrindo os relationships que `_item_summary` (`:29`) toca — `images`,
      `characters`, `categories`, `figurino_sheet` e `as_character` (+ `tema` deste). Comentário
      explicando o PORQUÊ: `cover_image` é property sobre `images[0]`, então pedir a capa carrega a
      coleção inteira.
- [X] T005 [US1] `app/admin/catalog_character_ops.py:363`: carregamento antecipado de `characters` e
      `images` no `CatalogItem.query.all()`. As 474 consultas vêm do laço dos avulsos (`:405-438`),
      onde `item.characters` é tocado uma vez por produto só para um teste de verdade/falso — o laço
      **não** precisa ser reescrito.
- [X] T006 [US1] Rodar o verify: cenário 1 em PASS, com a resposta batendo hash a hash com a
      referência.

**Checkpoint**: história 1 funcional e verificada sozinha. Já entrega a maior parte do ganho.

---

## Phase 4: História 2 — A tela para de baixar foto grande para caixa pequena (P1)

**Objetivo**: as miniaturas do gerenciador passam a pedir a variante de 128 px, e o que está fora da
tela só é pedido ao rolar.

**Verificação da história**: cenários 2 e 6 do `verify_300.py` em PASS; tela aberta nos três modos.

- [X] T007 [P] [US2] `frontend/apps/internal/src/components/CatalogCardGrid.tsx:43` — capa de 64 px:
      `assetUrl(item.cover_url, { largura: 128 })`, via `AvatarThumb`/`Foto` do `@manto/ui`, que já
      trazem `loading="lazy"` e o espaço reservado para foto ausente.
- [X] T008 [P] [US2] `frontend/apps/internal/src/components/CatalogTreeView.tsx:128` (capa, 40 px) e
      `:47` (rosto, 32 px).
- [X] T009 [P] [US2] `frontend/apps/internal/src/components/CatalogPersonagensView.tsx:103` (rosto,
      48 px) e `:289` (chip de tema, 28 px).
- [X] T010 [P] [US2] `frontend/apps/internal/src/components/AdminCatalogCharacterPanel.tsx:109` e
      `:387`.
- [X] T011 [P] [US2] `frontend/apps/internal/src/components/CatalogPhotoManager.tsx:347` e `:465`.
- [ ] T012 [US2] Rodar o verify (cenários 2 e 6) e abrir os três modos do gerenciador: conferir no
      inspetor que o endereço pedido é `/catalogo/midia/t/128/...`; que as imagens fora da tela só
      chegam ao rolar; que a animação de `layout` do modo Personagens não salta quando a imagem
      chega; e que um produto com arquivo ausente cai no espaço reservado.

**Checkpoint**: histórias 1 e 2 entregam juntas a espera que o dono relatou.

---

## Phase 5: História 3 — A vitrine pública carrega com o mesmo alívio (P2)

**Objetivo**: a vitrine cai de 916 para poucas consultas, e as duas telas que a feature 270 deixou
de fora passam a pedir miniatura.

**Verificação da história**: cenário 3 em PASS; telas em viewport mobile 375×812 (Princípio X).

- [X] T013 [US3] `app/api/catalogo_read.py`: carregamento antecipado de `categories` e `images` nas
      três listagens — `:96` (grade geral), `:121` (grade de categorias) e `:149` (categoria por
      slug). A `:149` é o pior caso: `_item_summary` (`:63`) toca os dois por item.
- [X] T014 [P] [US3] `frontend/apps/public/src/pages/CategoriesPage.tsx:51` — card de ~270 px:
      `assetUrl(url, { largura: 640 })` + `assetSrcSet(url, [320, 480, 640])` + `sizes` espelhando a
      grade real, no mesmo padrão que o `ProductCard` já usa. Preservar o `loading="lazy"` de `:53`.
- [X] T015 [P] [US3] `frontend/apps/public/src/pages/WishlistPage.tsx:69` — quadrado de 64 px:
      `{ largura: 128 }`. É o caso de ~380× que motivou a 270.
- [ ] T016 [US3] Rodar o verify (cenário 3) e abrir em 375×812: grade geral, grade de categorias,
      página de produto (a **foto grande continua no original** — decisão 9 da 270) e lista de
      desejos. Sem rolagem horizontal.

**Checkpoint**: as três histórias principais entregues; o deploy já faria sentido aqui.

---

## Phase 6: História 4 — Editar um produto não baixa o catálogo inteiro (P2)

**Objetivo**: o formulário de edição para de baixar 199 KB para desenhar 39 opções.

**Verificação da história**: cenários 4 e 5 do `verify_300.py` em PASS.

- [X] T017 [US4] `app/api/admin_catalogo_read.py`: view `GET /api/admin/catalogo/categorias` —
      mesmo `_require_superadmin()` do vizinho, type hints, docstring, e a forma do
      `contracts/catalogo-listagens.md` (`{"categories": [{"id", "name"}]}`, ordenado por nome,
      **todas** as categorias, inclusive sem produto ativo). O módulo já é importado por
      `app/api/__init__.py` — nenhum registro novo a esquecer.
- [X] T018 [P] [US4] `frontend/apps/internal/src/lib/adminCatalogo.ts`: hook das categorias
      reusando o tipo `CatalogCategoryOption` que já existe (`:37`), com chave de cache sob o
      prefixo `["admin-catalogo", …]` para as mutações existentes já o invalidarem.
- [X] T019 [US4] `frontend/apps/internal/src/pages/AdminCatalogoFormPage.tsx:41`: trocar
      `useAdminCatalogo({})` pelo hook novo. Conferir que criar categoria durante a edição continua
      aparecendo no seletor.
- [X] T020 [US4] Rodar o verify: cenário 4 em PASS e **cenário 5 falhando como deve** (papel sem
      permissão recebendo recusa no endpoint novo).

**Checkpoint**: a edição abre leve, e o gate novo está provado.

---

## Phase 7: História 5 — Digitar na busca do elenco não varre o catálogo (P3)

**Objetivo**: uma consulta por palavra, não uma por tecla.

**Verificação da história**: conferência de tela (comportamento de navegador, sem cenário de verify).

- [X] T021 [US5] `frontend/apps/internal/src/components/AdminCatalogCharacterPanel.tsx:69-70`: pausa
      de 300 ms antes de consultar (mesmo intervalo do `AgruparEventosDialog`), mantendo o mínimo de
      2 caracteres de hoje, com `placeholderData: keepPreviousData` para a lista não piscar
      (padrão de `agenda.ts` e `formulariosAdmin.ts`).
- [ ] T022 [US5] Abrir o painel e digitar uma palavra de 6 letras sem pausa: uma requisição, não
      seis; os resultados anteriores permanecem enquanto os novos não chegam.

**Checkpoint**: as cinco histórias entregues.

---

## Phase 8: Polimento e transversais

- [ ] T023 `cd frontend && npm run typecheck` limpo (três SPAs — `npx tsc` app a app não satisfaz o
      portão) e `ruff check` nos três arquivos Python tocados. `ruff format` em nenhum: todos são
      legado.
- [ ] T024 Conferência de tela final pelo `quickstart.md` §3: gerenciador nos três modos e tela de
      edição no computador; vitrine inteira em 375×812.
- [ ] T025 `docs/01` §4.3: linha do gate de `GET /api/admin/catalogo/categorias` (SUPERADMIN).
- [ ] T026 Docs por fonte única: `docs/02` (entradas de `/admin/catalogo` e das telas da vitrine
      tocadas), `docs/03` (entrada nova no topo, append-only, registrando a reversão consciente da
      decisão 7 da 270 e os números antes/depois), `docs/04` (invariante: listagem de catálogo
      carrega o acompanhamento de uma vez, nunca por item) e `docs/05` (as três dívidas novas: as
      demais telas internas sem miniatura, as capas de campanha virtual que não casam com o regex de
      variante, e o pacote JavaScript sem divisão por página).
- [ ] T027 `quickstart.md` executado de ponta a ponta, com os números do "depois" anotados ao lado
      dos do "antes".

**Checkpoint**: portões da constituição verdes e documentação viva atualizada.

---

## Phase 9: Depois do deploy (não antes)

- [ ] T028 Com a **fila de push vazia**, rodar `flask warm-thumbnails` por SSH no `manto-backend`
      (`MANTO_SEM_THREADS=1`, `PYTHONPATH=$PWD`). Sem isto, a primeira pessoa a abrir a tela paga a
      geração de centenas de miniaturas dentro de uma thread do gunicorn — a assinatura exata do
      incidente da feature 263. Um deploy troca o contêiner e mataria a rodada.
- [ ] T029 Sondar o backend por um endpoint `/api/` devolvendo JSON (nunca `/health` na URL pública,
      que cai no fallback da SPA e responde 200 com o Flask morto) e abrir o gerenciador em produção.

---

## Dependências e ordem

- **T001 antes de tudo** — depois de qualquer alteração, a referência do "antes" não existe mais.
- Setup → Foundational (bloqueia tudo) → histórias por prioridade (P1 → P2 → P3) → Polimento →
  pós-deploy.
- O verify é escrito ANTES e falha antes de implementar (Princípio VIII).
- Dentro de cada história: backend antes da tela; verify em PASS ao fim.
- **Backend e frontend desta feature são independentes**: como nenhum contrato muda
  (`contracts/catalogo-listagens.md`), não há a janela de incompatibilidade entre servidor e bundle
  — as tarefas `[P]` de frontend podem ir em qualquer ordem em relação às de backend.

## Estratégia

- **MVP**: T001 → T003 → História 1. Sozinha, ela já derruba 2.320 consultas para um punhado — é a
  maior parte da espera que o dono relatou.
- **Incremental**: cada história entrega valor sem quebrar a anterior; a Phase 5 é o ponto natural
  de parada se for preciso publicar antes do fim.
- Commit por tarefa ou grupo lógico (`feat(300):`), sempre **por caminho** — nunca `git add -A`: a
  raiz tem arquivos não versionados e tokens.
- Publicar só quando o dono pedir, em lote e fora do horário da equipe.
