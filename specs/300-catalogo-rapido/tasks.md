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
- [X] T012 [US2] *(37 de 37 imagens em `/t/128/`, nenhuma no original, nenhuma carregada num
      documento 16× mais alto que a janela)* Rodar o verify (cenários 2 e 6) e abrir os três modos do gerenciador: conferir no
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
- [X] T016 [US3] *(grade de categorias com `srcset` e o navegador escolhendo 320 sozinho; lista de
      desejos em `/t/128/`; palco no original; 375 sem rolagem horizontal)* Rodar o verify (cenário 3) e abrir em 375×812: grade geral, grade de categorias,
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
- [X] T022 [US5] *(conferido em 18/09 no componente real `CatalogItemSearch`, sem sessão: pedidos
      ao servidor `""`, `"co"`, `"coe"` — uma consulta por palavra, não por tecla; ver T040)*
      **Estava PENDENTE — não conferido na tela.** O campo vive dentro do painel de
      personagens, que exige sessão de SUPERADMIN; o andaime desta feature renderiza só as duas
      grades, que recebem dados por prop. A pausa foi conferida por leitura de código (`setTimeout`
      de 300 ms alimentando a chave da query), **não na tela** — e não registro como conferido o
      que não conferi. Fica para quem tiver sessão. Original: abrir o painel e digitar uma palavra de 6 letras sem pausa: uma requisição, não
      seis; os resultados anteriores permanecem enquanto os novos não chegam.

**Checkpoint**: as cinco histórias entregues.

---

## Phase 8: Polimento e transversais

- [X] T023 `cd frontend && npm run typecheck` limpo (três SPAs — `npx tsc` app a app não satisfaz o
      portão) e `ruff check` nos três arquivos Python tocados. `ruff format` em nenhum: todos são
      legado.
- [ ] T024 **PARCIAL — mesma trava da T022/T035.** Conferidos: Cards e Árvore (37 de 37 imagens em
      `/t/128/`, nenhuma no original, 1 requisição e 300 bytes antes de rolar) e a vitrine inteira
      em 375×812. **Faltam** o modo Personagens e a tela de edição: os dois exigem sessão de
      SUPERADMIN, que eu não crio (não digito senha em formulário). Original: conferência de tela final pelo `quickstart.md` §3: gerenciador nos três modos e tela de
      edição no computador; vitrine inteira em 375×812.
- [X] T025 *(a rota entrou no §3.10; o §4.3 já cobria — `_require_superadmin()` para
      `admin_catalogo_*`, e a view nova usa esse mesmo gate nesse mesmo módulo)* `docs/01` §4.3: linha do gate de `GET /api/admin/catalogo/categorias` (SUPERADMIN).
- [X] T026 *(dívidas 56, 57 e 58; `docs/04` ganhou a linha de Catálogo, que não existia)* Docs por fonte única: `docs/02` (entradas de `/admin/catalogo` e das telas da vitrine
      tocadas), `docs/03` (entrada nova no topo, append-only, registrando a reversão consciente da
      decisão 7 da 270 e os números antes/depois), `docs/04` (invariante: listagem de catálogo
      carrega o acompanhamento de uma vez, nunca por item) e `docs/05` (as três dívidas novas: as
      demais telas internas sem miniatura, as capas de campanha virtual que não casam com o regex de
      variante, e o pacote JavaScript sem divisão por página).
- [X] T027 *(§1 verify 8/8, §2 portões verdes, §3 telas — salvo o que depende de sessão, §4 números
      do "depois" anotados; §5 só faz sentido depois do deploy)* `quickstart.md` executado de ponta a ponta, com os números do "depois" anotados ao lado
      dos do "antes".

**Checkpoint**: portões da constituição verdes e documentação viva atualizada.

---

## Phase 9: Depois do deploy (não antes)

- [X] T028 *(feito ANTES do deploy, e de outro jeito: a galeria já estava quente; as 44 fotos de
      personagem que existem no disco foram aquecidas uma por vez pela rota pública — ver T050)*
      Com a **fila de push vazia**, rodar `flask warm-thumbnails` por SSH no `manto-backend`
      (`MANTO_SEM_THREADS=1`, `PYTHONPATH=$PWD`). Sem isto, a primeira pessoa a abrir a tela paga a
      geração de centenas de miniaturas dentro de uma thread do gunicorn — a assinatura exata do
      incidente da feature 263. Um deploy troca o contêiner e mataria a rodada.
- [ ] T029 **PARCIAL.** Feito: sonda `/api/` com JSON; backend novo provado pela virada de 405 para
      401 em `GET /api/admin/catalogo/categorias`; bundle novo com os textos da 300; vitrine com as
      três respostas **idênticas** às de antes do deploy e tempo caindo 50–61%. **Falta** abrir o
      gerenciador em produção — exige sessão de SUPERADMIN, e fica com o dono. Original: sondar o backend por um endpoint `/api/` devolvendo JSON (nunca `/health` na URL pública,
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

---

## Phase 10: Convergence

Achados da avaliação do código contra `spec.md`, `plan.md` e `tasks.md` (16/09/2026), em ordem de
severidade. Nenhuma violação da constituição.

- [X] T030 Acrescentar `placeholderData: keepPreviousData` em `useAdminCatalogo`
      (`frontend/apps/internal/src/lib/adminCatalogo.ts:52`) para a lista não piscar esqueleto a
      cada refinamento da busca — a pausa da T021 entrou, esta metade não — per FR-010 (partial)
- [X] T031 *(a pausa vale só para o que vai ao servidor; o filtro client-side da visão
      Personagens segue instantâneo)* Dar a mesma pausa de 300 ms à busca da própria tela de listagem
      (`frontend/apps/internal/src/pages/AdminCatalogoListPage.tsx:41`, `q` vai direto para a chave
      da query): hoje cada tecla ainda dispara uma varredura do catálogo inteiro **na tela que
      originou o chamado** — a História 5 nomeou só o painel de personagens — per US1/FR-001 (missing)
- [X] T032 **Medido: 1 requisição e 300 bytes antes de rolar** (37 imagens no documento, 16× mais
      alto que a janela; zero no original) contra 458 pedidos e 95,4 MB de antes. Medir os bytes de imagem baixados na primeira tela do gerenciador, antes de qualquer
      rolagem, e registrar o número ao lado dos 95,4 MB de hoje: a conferência atual provou o
      endereço pedido e o adiamento, não o total — per SC-003 (missing)
- [X] T033 Estender o cenário 6 do `verify_300.py` para o arquivo **corrompido** (origem ilegível),
      não só o ausente: hoje o caso de borda "a geração da miniatura falha" não é exercitado por
      nada — per Spec §Casos de borda (missing)
- [X] T034 *(cenário 7: aquece a variante e então dispara 6 pedidos simultâneos, conferindo que
      todos recebem os MESMOS bytes. A geração simultânea **a frio** ficou de fora de propósito —
      no Windows ela esbarra num limite da plataforma, `os.replace` × `open()`, que faria o verify
      falhar pelo sistema de arquivos do desenvolvedor e não pelo produto: dívida 59, e a 270 já a
      cobre no cenário 6 dela)* Cobrir a corrida de geração da mesma miniatura por dois pedidos simultâneos — a spec diz
      que esta feature "não pode reintroduzir" o defeito que a 270 corrigiu, e não há guarda
      nenhuma provando isso — per Spec §Casos de borda (missing)
- [X] T035 *(conferido em 18/09 — ver T040)* Conferir na tela a pausa da busca do painel de personagens (uma requisição por palavra,
      não uma por tecla), com sessão de SUPERADMIN — o andaime desta feature só renderiza as
      grades — per T022 (partial)
- [X] T036 Remover de `spec.md` §Docs a atualizar a condicional "`docs/01` §5 — só se o contrato de
      cache mudar": o contrato não mudou, então o item nunca se cumpre nem se descarta — per
      Spec §Docs a atualizar (contradicts)

---

## Phase 11: Convergence

Segunda passada (16/09/2026). Os sete achados da Phase 10 estão fechados; o que sobra é coerência
entre artefatos — a exceção de ordenação foi registrada na spec e não alcançou os dois documentos
que um implementador futuro lê primeiro. Nenhuma violação da constituição.

- [X] T037 Registrar a exceção de ordenação em
      `specs/300-catalogo-rapido/contracts/catalogo-listagens.md`: o documento afirma resposta
      "byte a byte idêntica" sem ressalva, e **115 produtos mudaram a ordem dos nomes de
      categoria** (mais um par de personagens empatados) — quem ler só o contrato conclui o
      contrário do que aconteceu — per FR-003a (contradicts)
- [X] T038 Corrigir a invariante 1 de `specs/300-catalogo-rapido/data-model.md`, que ainda diz
      "mesmas chaves, mesmos valores, **mesma ordem**" — a mesma contradição do T037, no documento
      que descreve a estratégia de carga — per FR-003a (contradicts)
- [X] T039 *(o `quickstart.md` §3 descrevia a pausa como sendo só do painel — terceiro lugar com o
      mesmo recorte antigo, que eu tinha subdimensionado ao escrever esta tarefa; corrigido junto)*
      Fazer a spec e o `docs/02` alcançarem o código: a pausa de 300 ms entrou **também** na
      busca da tela de listagem (T031), e o FR-010 nomeia só a busca do painel de personagens; o
      `docs/02` repete o recorte antigo. Ampliar o FR-010 e a linha do `docs/02` — per FR-010
      (unrequested)

---

## Phase 12: Revisão pré-deploy (18/09/2026)

Revisão adversarial antes de publicar — cinco revisores, um por dimensão de risco; três céticos
por achado, com lentes distintas; um crítico de completude. **9 achados, os 9 confirmados, nenhum
derrubado.** Tratamento de cada um:

- [X] T040 Busca Adotar/Vincular mostrava linhas de OUTRA busca, ou do catálogo sem filtro, com o
      botão ativo — e trocava as linhas no lugar, então o clique mirado num item caía em outro.
      Estado `buscando` (pausa não disparada, lista anterior ou carregando): botão só quando a
      linha corresponde ao texto digitado agora; mais estado de erro. **Provado na tela com o
      componente real**, sem sessão (`fetch` falso, atraso realista): 72 amostras, **0
      violações**; pedidos ao servidor `""`, `"co"`, `"coe"` — per revisão #1 (high)
- [X] T041 Nomes de categoria ordenados por `id`, não alfabético: medido no código da `main`, por
      `id` reproduz a produção em **458 de 458** — a alfabética mudaria 123 produtos, e o card da
      vitrine mostra só as 3 primeiras etiquetas. FR-003a revisto; `referencia_300.json`
      recapturada **no código da `main`** (a anterior já tinha a ordem nova); verify 8/8 contra
      ela — per revisão #2 e #4
- [X] T042 Grade de fotos da edição volta a pedir o original: o cache de produção só tem 320 das
      capas, e a primeira abertura geraria de 9 a 17 variantes simultâneas no gunicorn — per
      revisão #3 e crítico
- [X] T043 Listagem esmaecida, sem clique e com "Atualizando…" enquanto mostra o filtro anterior;
      sem "Nenhum produto encontrado" nem termômetro de fichas falsos na janela — per revisão #6
- [X] T044 Modo Personagens sem "manter a lista anterior" (`useAdminCatalogo` ganhou a opção
      `manterAnterior`): ali a lista é FONTE das opções do "usar em outro tema" — per revisão #7
- [X] T045 Formulário de edição com erro visível e "Tentar de novo" nas categorias (Princípio V).
      A janela de 405 do deploy fica documentada: sem perda de dado, porque as categorias marcadas
      vêm do detalhe do produto — per revisão #5, #8 e #9
- [X] T046 *(varredura por "alfabétic", "frio", "9 arquivos", "nada quebra" e "não existe a janela"
      na spec e nos `docs/`: toda ocorrência restante está em contexto de correção ou é de outra
      feature)* Corrigir a documentação que ficou falsa: a premissa "cache frio" era do espelho local
      (em produção, 97% quente — aquecimento opcional), e a ordem alfabética e "a janela de deploy
      não quebra nada" precisam sair de spec, contrato, data-model, research, quickstart,
      `docs/02`, `docs/03` e `docs/04`; dívida 60 registrada — per crítico

---

## Phase 13: Segunda revisão, só das correções (18/09/2026)

Revisão adversarial apenas do diff das correções (`e11a813..18f51bd`): três revisores (estado,
ordem no backend e fechamento dos 9 achados originais), três céticos por achado. **4 achados,
todos baixos, todos confirmados** — nenhum bloqueante: as correções não introduziram defeito sério.

- [X] T047 "Tentar de novo" das categorias: ao refazer uma consulta que nunca teve dado, o TanStack
      v5 volta o estado para `pending`, e o aviso desmontava junto com o próprio botão — o cartão
      ficava mudo justamente durante a tentativa. Estado local segura o aviso e mostra o
      carregamento no botão — per revisão 2 (A)
- [X] T048 Modo Personagens: "usar em outro tema" afirmava "Nenhum tema disponível" enquanto a
      lista ainda carregava; agora diz "Carregando temas…" (`temasCarregando={query.isPending}`) —
      per revisão 2 (B)
- [X] T049 Desempate `(position, id)` só na listagem, não nos outros três serializadores do
      elenco: registrado como dívida 61 — não ocorre hoje (0 de 458), e corrigir agora ampliaria o
      raio para endpoints que o verify não cobre — per revisão 2 (C)
- [X] T050 *(243 fotos de personagem na produção, só 44 existem no disco — 199 perdidas na
      migração do Railway, 404 sem gerar nada, confirmado por `test -f` no disco; as 44 aquecidas
      antes do deploy, uma por vez, pela rota pública)* As fotos de PERSONAGEM nunca foram aquecidas a 128 — o laço do comando só faz 320/480/640,
      e nenhuma tela da `main` as pedia a 128. O "97% quente" era contagem agregada de arquivos, que
      não diz QUAIS fotos têm variante. Aquecer as 243 da produção antes do deploy, uma por vez, pela
      rota pública, e corrigir o que a documentação afirmava — per revisão 2 (D)
