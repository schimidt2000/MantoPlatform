---
description: "Tasks da feature 314 — Gastos Extras na tela inteira, com filtros e as pagas recolhidas"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Gastos Extras na tela inteira, com filtros e as pagas recolhidas

**Input**: artefatos em `/specs/314-gastos-extras-filtros/`

**Pré-requisitos**: plan.md, spec.md (histórias e seção "Verificação"), research.md (D1–D9), data-model.md,
contracts/gastos-list.md, quickstart.md

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `specs/314-gastos-extras-filtros/verify_314.py` contra `manto_local`,
escrito na fase Foundational ANTES de `situacao_do_gasto`, falhando no cenário 1 ("gasto sem `situacao`").

**Organização**: por história da spec. A US1 (layout) e a US2 (situação + grupos) são P1. A US3 (filtros) depende da
página das duas. A US4 (não gestor) é conferência com pouca mudança.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: história a que a tarefa pertence (US1…US4)

---

## Phase 1: Setup

- [X] T001 Dependências do frontend no worktree: `npm ci` em `C:\tmp\mp314\frontend` (o worktree nasceu sem
      `node_modules`); conferir que `npm run typecheck` roda limpo ANTES de qualquer mudança (linha de base)

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T002 **`specs/314-gastos-extras-filtros/verify_314.py`** — os 8 cenários da tabela "Verificação" da spec,
      pelo esqueleto da skill `manto-verify`: usuários descartáveis (Financeiro e Casting) criados por conexão
      própria, login só por `POST /api/auth/login`, requisições fora de `app.app_context()`; 9 gastos semeados por
      ORM com descrição marcada `[verify314]` (os casos de `research.md` D2 + 2 do Casting); oráculo do cenário 3 =
      a regra D2 escrita em SQL (`CASE`) rodada por `sqlalchemy.create_engine` separado sobre `special_expenses`
      inteira, comparada à soma por `situacao` do payload; cenário 4 aprova pela API (`POST
      /api/gastos/<id>/aprovar`); cenário 7 troca `gastos_ops.situacao_do_gasto` por uma versão quebrada (pago no
      cadastro → `a_pagar`) e exige que o cenário 2 caia; limpeza no `finally` (`rollback`, `roles.clear()`, apaga
      gastos `[verify314]`, as linhas de `AuditLog` `entity_type="gasto"` deles — a aprovação do cenário 4 grava — e
      os usuários) conferida por conexão separada. Rodar AGORA: deve falhar no cenário 1 por
      falta de `situacao` — salvar a saída em `specs/314-gastos-extras-filtros/verify_314_primeira_falha.txt`
- [X] T002b Base dos verifies vizinhos ANTES de qualquer mudança de backend: rodar `verify_306.py` e `verify_312.py`
      neste worktree e anotar o placar em `specs/314-gastos-extras-filtros/base_verifies_vizinhos.txt`
- [X] T003 [P] `frontend/apps/internal/src/lib/gastos.ts`: `GastoSituacao` (`"aguardando_aprovacao" | "a_pagar" |
      "no_banco" | "pago" | "rejeitado"`); `situacao?: GastoSituacao` em `GastoExtra` (opcional — armadilha 21);
      `situacaoDe(e)` com a ponte de deploy de `research.md` D1 (sem a chave: pendente → aguardando, rejeitado →
      rejeitado, resto → `a_pagar`, nunca recolhido); `SITUACAO_LABELS`, `SITUACAO_ORDEM`, `SITUACAO_TONE`
      (`BucketTone` de `lib/pagamentos.ts`; aguardando `gold`, a pagar `red`, no banco `blue`, pago `green`,
      rejeitado neutro); `SITUACOES_A_VISTA` (aguardando, a pagar, no banco)

**Checkpoint**: verify falhando pelo motivo certo; tipos prontos; typecheck limpo.

---

## Phase 3: História 1 — A lista cabe na tela, sem rolagem lateral (P1) 🎯 MVP

**Objetivo**: raiz sem teto; tabela de 7 colunas a partir de `xl` sem rolagem lateral; cartões abaixo.

**Verificação da história (obrigatória)**: tela aberta em 1920, 1366, 1280 e 375 px
(`document.documentElement.scrollWidth <= innerWidth` e nenhum `overflow-x` na lista); ações e "Devolução de
cancelado: travada." inteiras.

- [X] T004 [US1] `frontend/apps/internal/src/components/Gastos/GastoItemViews.tsx` (novo): `useAcoesDoGasto(expense)`
      (aprovar/rejeitar/excluir/vincular com as mesmas regras de hoje — `travado`, `canDelete`, `window.prompt` no
      motivo da rejeição, erro da ação); "Excluir" abre o `ConfirmDialog` do `@manto/ui` ("Excluir este gasto?",
      descrição e valor no corpo, botão `loading` e erro dentro do diálogo — FR-013, Princípio V; achado C1),
      `SituacaoBadge` (rótulo + tom de `lib/gastos.ts`; "com edições" quando
      `approved_with_edits`), `GastoRow` (7 colunas do plano: Data · Gasto [descrição, categoria · observação, "por
      <autor>" só gestão, `MarketingBatchDetail`] · Valor · Situação · Desembolso · Evento [`line-clamp-2` +
      `title`, `SeloSituacao` cancelado] · Ações [Aprovar/Rejeitar com texto; Ver nota fiscal, Editar, Vincular
      evento, Excluir em ícone de 32 px com `aria-label` + `title`; aviso de trava e erro embaixo]) e `GastoCard`
      (celular: descrição + valor, selo, data · categoria, desembolso, evento, autor, ações com texto). Linha de
      vínculo (`EventoVincular`) abre embaixo da linha/cartão como hoje. Mover `MarketingBatchDetail`,
      `EventoVincular`, `formatDate` e o rótulo do desembolso de `GastosExtrasPage.tsx` para cá
- [X] T005 [US1] `frontend/apps/internal/src/components/Gastos/GastoItemViews.tsx`: `ListaDeGastos({ expenses,
      canManage, onEdit })` = cartões `p-3 xl:hidden grid gap-2 md:grid-cols-2 [&>*]:min-w-0` + tabela `hidden
      xl:block` com `w-full table-fixed`, `colgroup` (`w-24`, flex, `w-28`, `w-28`, `w-36`, `w-40`, `w-44`), células
      `px-2`, `[overflow-wrap:anywhere]` em Gasto/Desembolso/Evento, cabeçalho "Situação" — **sem** `min-w-*` e sem
      `overflow-x-auto`
- [X] T006 [US1] `frontend/apps/internal/src/pages/GastosExtrasPage.tsx`: raiz `space-y-4 p-4 sm:p-6` (sem `mx-auto
      max-w-*`) também nos ramos de carregamento e erro (FR-017); trocar `GastosTable`/`GastoRow`/`StatusBadge` pela
      `ListaDeGastos`; apagar o que migrou para `GastoItemViews.tsx`; `GastoFormModal` fica
- [X] T007 [US1] Tela aberta (skill `manto-conferir-tela`) em 1920/1366/1280/375 como Superadmin — medir a rolagem
      lateral pelo JS e tirar print de 1366 e 375

**Checkpoint**: a queixa nº 1 resolvida sozinha (sem grupos nem filtros ainda).

---

## Phase 4: História 2 — Só o que pede ação à vista; pagos e rejeitados recolhidos (P1)

**Objetivo**: situação calculada no núcleo e servida; lista principal = aguardando + a pagar + no banco; "Pagos" e
"Rejeitados" em `AccordionRow` fechados.

**Verificação da história (obrigatória)**: cenários 1–4 e 7 do `verify_314.py` em PASS; tela: abertura só com os
três que pedem ação, abrir/fechar os grupos, aprovar e ver o gasto mudar de grupo sem recarregar.

- [X] T008 [US2] `app/gastos/gastos_ops.py`: constantes `SITUACAO_AGUARDANDO_APROVACAO`, `SITUACAO_A_PAGAR`,
      `SITUACAO_NO_BANCO`, `SITUACAO_PAGO`, `SITUACAO_REJEITADO` (+ tupla `SITUACOES`) no topo; `situacao_do_gasto(
      expense: SpecialExpense) -> str` com a ordem de `research.md` D2, docstring Google com o porquê (o que nunca vai
      à Planilha de Pagamentos conta como resolvido — ponteiro para `api_financeiro_pagamentos`)
- [X] T009 [US2] `app/api/gastos_read.py`: `_expense_dict` ganha `"situacao": gastos_ops.situacao_do_gasto(e)`;
      `ruff check app/gastos/gastos_ops.py app/api/gastos_read.py`
- [X] T010 [US2] Rodar `verify_314.py`: cenários 1–4 e 7 em PASS (5 e 6 também, já que o gate não muda)
- [X] T011 [US2] `frontend/apps/internal/src/pages/GastosExtrasPage.tsx`: separar `aVista` (`SITUACOES_A_VISTA`) de
      `pagos` e `rejeitados` por `situacaoDe`; lista principal = `ListaDeGastos(aVista)`; embaixo, um `AccordionRow`
      (`@manto/ui`, fechado, chave estável) por grupo não vazio com resumo "Pagos — N gastos · R$ X" /
      "Rejeitados — N gastos · R$ X" (contagem concorda com o número) e a `ListaDeGastos` do grupo dentro; lista
      principal vazia com grupos cheios → "Nenhum gasto aguardando ação." acima dos grupos
- [X] T012 [US2] Tela aberta: abertura, abrir/fechar "Pagos" (com e sem "reduzir movimento"), aprovar um gasto
      descartável do `manto_local` e vê-lo mudar de grupo com o grupo aberto continuando aberto

**Checkpoint**: o pedido do dono ("as pagas colapsam num card") entregue sobre a US1.

---

## Phase 5: História 3 — Filtros como na página de Pagamentos (P2)

**Objetivo**: cartões-filtro por situação, busca, categoria, desembolso e mês, tudo na URL.

**Verificação da história (obrigatória)**: tela — cartões ligam/desligam; busca sem acento e com vários termos;
combinação de filtros; "Limpar filtros"; recarregar mantém; valor inválido na URL é ignorado; filtro sem resultado
diz "Nenhum gasto encontrado.". Pagamentos com os cartões iguais aos de antes.

- [X] T013 [P] [US3] `frontend/apps/internal/src/components/CartaoFiltro.tsx` (novo): o `TotalCard` de
      `PagamentosPage.tsx` extraído — props `label`, `value`, `count`, `tone: BucketTone | null` (null = cartão
      neutro), `active`, `dimmed`, `unidade: [singular, plural]`, `className`, `onClick`; mesmas classes,
      `aria-pressed` e o "· filtro ativo" só quando `active && tone` (D5)
- [X] T014 [US3] `frontend/apps/internal/src/pages/PagamentosPage.tsx`: trocar o `TotalCard` local pelo
      `CartaoFiltro` (`tone={bucket ? BUCKET_TONE[bucket] : null}`, `unidade={["item", "itens"]}`); apagar o local
- [X] T015 [P] [US3] `frontend/apps/internal/src/lib/gastos.ts`: `searchIndexOfGasto(e)` (data dd/mm/aaaa e ISO,
      descrição, observação, categoria, quem recebe, PIX, evento, autor, rótulo da situação, `formatBRL` e
      `rawAmount` do valor) sobre `normalizeSearch`; `DESEMBOLSO_FILTRO` (`reembolso`, `fornecedor`, `cliente`,
      `nenhum` + rótulos); `lerFiltrosDaUrl(params, categories)` que descarta valor desconhecido (FR-011) e
      `filtrarGastos(expenses, filtros, terms, index)` (sem a situação — FR-009)
- [X] T016 [US3] `frontend/apps/internal/src/components/Gastos/GastosFiltros.tsx` (novo): busca (ícone + limpar,
      como Pagamentos, placeholder "Buscar por descrição, quem recebe, evento, autor, valor…"); `<select>`
      "Todas as categorias"; `<select>` "Todos os desembolsos"; mês (‹ › `aria-label` "Mês anterior"/"Mês
      seguinte", `Input type="month"` `aria-label` "Mês do gasto", botão "Todos os meses" quando há mês; setas sem
      mês partem de `currentMonth()`); "N de M gastos · R$ X" quando há filtro; "Limpar filtros"
- [X] T017 [US3] `frontend/apps/internal/src/pages/GastosExtrasPage.tsx`: estado na URL (`useSearchParams`,
      `replace: true`, helper `atualizarUrl` como em Pagamentos) para `busca`, `categoria`, `desembolso`, `mes`,
      `situacao`; índice de busca em `useMemo` por resposta; grade de `CartaoFiltro` (`grid-cols-2 sm:grid-cols-3
      xl:grid-cols-6`: Todos + as 5 situações, com contagem e soma do recorte sem a situação); com situação escolhida,
      só ela, aberta, sem grupos (FR-006); linha `sr-only` `aria-live` "N de M gastos em exibição." (FR-010);
      estado vazio do recorte "Nenhum gasto encontrado." + "Limpar filtros" (FR-012); sem gasto nenhum →
      "Nenhum gasto registrado ainda." sem filtros nem grupos; o `KpiGrid` antigo sai
- [X] T018 [US3] Tela aberta: o roteiro do `quickstart.md` §3 passos 3–6 e 8 + Pagamentos (cartões, filtro ativo,
      "Limpar filtro") em 1366 e 375

**Checkpoint**: histórias 1–3 entregues; Pagamentos sem regressão.

---

## Phase 6: História 4 — Quem só lança gastos ganha a mesma tela (P3)

**Objetivo**: o não gestor vê só os seus, com grupos, filtros e cartões dos próprios números.

**Verificação da história (obrigatória)**: cenários 5 e 6 do `verify_314.py` em PASS (o 6 é o que deve falhar);
tela em 1366 com um usuário de Casting do `manto_local` (ou o descartável do verify mantido de propósito durante a
conferência e apagado depois).

- [X] T019 [US4] `frontend/apps/internal/src/pages/GastosExtrasPage.tsx` + `GastoItemViews.tsx`: sem `canManage`,
      nada de autor nem Aprovar/Rejeitar/Editar/Vincular; os cartões-filtro valem para o não gestor (somam a lista
      dele); subtítulo de hoje mantido
- [X] T020 [US4] Tela aberta como não gestor em 1366 e 375

**Checkpoint**: as quatro histórias funcionam juntas e sozinhas.

---

## Phase 7: Polimento e transversais

- [X] T021 `cd frontend && npm run typecheck` limpo (três SPAs) e `ruff check app/gastos/gastos_ops.py
      app/api/gastos_read.py`; `ruff format` só no `verify_314.py`
- [X] T022 Texto pelo Princípio XV lido na tela aberta: "Situação", rótulos das situações, "Ver nota fiscal",
      "Excluir", "Nenhum gasto encontrado.", "Limpar filtros", concordância "1 gasto"/"N gastos"; nenhuma chave
      ou enum renomeado
- [X] T023 `verify_314.py` verde de ponta a ponta + rodar os verifies vizinhos que leem `GET /api/gastos` ou
      `_expense_dict`: `specs/306-dinheiro-do-cancelamento/verify_306.py` e
      `specs/312-cancelado-fora-das-listas/verify_312.py`, comparando com a base medida em T002b (não com números de
      outra data — a `main` andou 86 commits desde 21/10)
- [X] T024 Docs por fonte única: `docs/01` (shape do `GET /api/gastos` com `situacao`); `docs/02` (`/gastos`: layout,
      grupos, filtros, URL; §Espaçamento ganha a exceção de largura da 314); `docs/03` (entrada no topo + linha no
      índice); `docs/05` (candidatos: `totals` sem consumidor; `window.prompt`/`window.confirm` da tela)
- [X] T025 `quickstart.md` executado de ponta a ponta

**Nota do implement (27/10).** As quatro histórias mexem em `GastosExtrasPage.tsx` em sequência, por isso a página
foi escrita uma vez com as quatro (T006+T011+T017+T019). As conferências de tela T007, T012, T018 e T020 rodaram
juntas sobre a página inteira, em 1920/1366/1280/375 e com Superadmin e Casting descartáveis. Os dois achados
(selo invadindo a coluna; grupo com 20 px de altura) foram corrigidos em `881ef41a`. Os números da `docs/05`
ficaram 165 e 166 (ver T024).

---

## Dependências e ordem

- Setup (T001) → Foundational (T002 verify falhando; T003 tipos) → US1 (T004→T005→T006→T007) → US2 (T008→T009→T010;
  T011 depois de T006; T012) → US3 (T013 ∥ T015; T014 depois de T013; T016 depois de T015; T017 depois de T011,
  T013, T016; T018) → US4 (T019, T020) → Polimento (T021–T025)
- O verify (T002) é escrito e roda falhando ANTES de `situacao_do_gasto` (T008)
- `GastosExtrasPage.tsx` é tocado em T006, T011, T017 e T019: em sequência, nunca em paralelo

## Paralelo

- T002 (Python) ∥ T003 (TS) — arquivos diferentes
- T013 (CartaoFiltro) ∥ T015 (lib de filtros) — arquivos diferentes; T014 só depois de T013

## Estratégia

- **MVP**: US1 + US2 (as duas P1 — a queixa do layout e o "card de pagas"), verify verde, tela aberta
- **Incremental**: US3 (filtros) sobre a página nova; US4 é conferência
- Commits `feat(314):` por história, sempre por caminho; merge e push só quando o dono pedir (fora do horário)

---

## Phase 8: Convergence

- [X] T026 Deixar o grupo do mês quebrar linha em `frontend/apps/internal/src/components/Gastos/GastosFiltros.tsx` para não haver rolagem lateral a 375 px com mês escolhido; medir `scrollWidth <= innerWidth` em `/gastos?mes=2026-09` a 375 px per FR-002, US1/AC3 (contradicts)
- [X] T027 Aceitar em `lerFiltrosDaUrl` (`frontend/apps/internal/src/lib/gastos.ts`) só valores próprios do desembolso (lista fechada, não o operador `in`, que aceita `constructor`) per FR-011 (partial)
- [X] T028 Incluir o total em R$ na linha `aria-live` e fazer a contagem concordar com o número ("0 de 1 gasto") em `frontend/apps/internal/src/pages/GastosExtrasPage.tsx` per FR-010, Constitution XV (partial)
- [X] T029 Completar o erro de exclusão com "Tente novamente." em `frontend/apps/internal/src/components/Gastos/GastoItemViews.tsx` per Constitution XV (contradicts)
- [X] T030 Trocar "Nenhum gasto aguardando ação." por "Nenhum gasto aguardando aprovação ou pagamento." em `GastosExtrasPage.tsx` e no caso de borda da `spec.md` per Constitution XV (contradicts)
- [X] T031 Mostrar o título do evento inteiro no cartão do celular (o `line-clamp-2` + `title` fica só na tabela) em `GastoItemViews.tsx` per US1 "nada fica cortado" (partial)
- [X] T032 Rodar também a comparação do cenário 3 (SQL) sob a mutação do cenário 7 em `specs/314-gastos-extras-filtros/verify_314.py` per spec §Verificação cenário 7 (partial)
- [X] T033 Registrar na `spec.md` o que o código já faz e a spec não diz — "Cancelar" no motivo da rejeição não rejeita (FR-013), índice de busca com categoria, PIX, data, situação e valor (FR-007, US3/AC1), a recusa de aprovar no cenário 6 — e corrigir `contracts/gastos-list.md` (rejeitado sem `situacao` vai a Rejeitados) per Constitution VII (unrequested)
- [X] T034 Registrar no `docs/05` (167): rótulos em CSS `uppercase` nos cartões-filtro e cabeçalhos de tabela (padrão de Pagamentos, junto da 146) e falta de transição na linha de vínculo de evento e na troca de grupo (XI; só o `AccordionRow` anima) per Constitution XV caixa, XI (contradicts)
- [X] T035 Marcar os portões CHK001–CHK011 de `checklists/ux.md` que a rodada cumpriu e apagar `frontend/apps/internal/vite.config.mp314.ts` ao fim da conferência de tela per tasks T023/T025 (partial)
