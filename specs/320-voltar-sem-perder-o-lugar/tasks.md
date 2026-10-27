---
description: "Tasks da feature 320 — voltar sem perder o lugar"
---
# Tasks: 320 — Voltar sem perder o lugar

**Input**: artefatos em `specs/320-voltar-sem-perder-o-lugar/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/ui.md, quickstart.md

**Verificação (Princípio VIII)**: `verify_320.py` (orquestrador: usuário descartável, login pela
API, limpeza) + `verify_320_navegador.mjs` (Chromium/Playwright). Escritos na Phase 2, ANTES do
núcleo, e rodados contra a `main` para falhar pelos motivos certos.

**Organização**: por história da spec. US1, US2 e US3 são P1; US4 é P2.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 Adicionar `pdfjs-dist` na versão exata `4.10.38` às `dependencies` de `frontend/packages/ui/package.json` e rodar `npm install` em `frontend/` (atualiza `frontend/package-lock.json`); conferir que o `npm run build` do interno ainda passa
- [X] T002 [P] Subir o backend local sem Google (porta 5000) e os Vite do worktree em segundo plano (interno 5320, público 5321) conforme `quickstart.md`; o `.claude/launch.json` versionado não muda

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase.

- [X] T003 Escrever `specs/320-voltar-sem-perder-o-lugar/verify_320.py`: cria usuário descartável SUPERADMIN no `manto_local` (`FLASK_ENV=development`, `MANTO_SEM_THREADS=1`), confere login por `POST /api/auth/login` contra o Flask local, escolhe dados reais (2 gastos com comprovante JPG e PDF cujo arquivo existe em `instance/uploads`, ≥ 40 talentos ativos, ≥ 1 pendente, catálogo público com ≥ 20 temas), chama `node verify_320_navegador.mjs` com esses dados por variável de ambiente e apaga o usuário no `finally` (`roles.clear()` antes)
- [X] T004 Escrever `specs/320-voltar-sem-perder-o-lugar/verify_320_navegador.mjs` (Playwright de `frontend/node_modules`): cenários 1–11 da tabela da spec, cada um com PASS/FAIL e motivo; viewport 390×844 com toque nos cenários 7–10; `navigator.standalone = true` por `addInitScript` no 10; modo contraprova (`--contraprova`) que roda 1, 5 e 7 e exige falha
- [X] T005 Rodar o verify contra o Vite da `main` (checkout principal) e guardar a saída em `specs/320-voltar-sem-perder-o-lugar/verify_320_primeira_falha.txt` — tem de falhar em 1, 2, 4, 5, 6, 7, 8 e 10 pelos motivos certos
- [X] T006 [P] Criar `useRestaurarRolagem` em `frontend/packages/ui/src/lib/rolagem.ts` conforme `contracts/ui.md` (sessionStorage `manto:rolagem`, 50 entradas, tentativa por até 1,5 s, desiste se a pessoa rolar) e exportar em `frontend/packages/ui/src/index.ts`
- [X] T007 [P] Criar `estaComoAppInstalado` em `frontend/packages/ui/src/lib/app-instalado.ts` e exportar em `frontend/packages/ui/src/index.ts`
- [X] T008 [P] Criar `frontend/apps/internal/src/lib/navegacao.tsx`: `DA_LISTA` (estado `{ daLista: true }`), `useVoltarParaLista(fallback)` e `RolarAoTopoEmNovaPagina`; montar `RolarAoTopoEmNovaPagina` dentro do `BrowserRouter` em `frontend/apps/internal/src/App.tsx`
- [X] T009 [P] Criar `frontend/apps/public/src/lib/navegacao.tsx` com o mesmo trio e montar `RolarAoTopoEmNovaPagina` em `frontend/apps/public/src/App.tsx`

**Checkpoint**: verify escrito e falhando na `main`; peças compartilhadas prontas.

---

## Phase 3: História 1 — Voltar ao catálogo no mesmo ponto (P1) 🎯 MVP

**Objetivo**: catálogo público e gerenciador voltam com busca, filtros e rolagem.

**Teste independente**: cenários 1–4 e 11 do verify.

- [X] T010 [P] [US1] `frontend/apps/public/src/pages/CatalogGridPage.tsx`: `search` → `?q`, `activeCategory` → `?categoria` (`useSearchParams`, `replace: true`); `useRestaurarRolagem(location.key, { restaurar: navigationType === "POP", pronto: Boolean(data) })`
- [X] T011 [P] [US1] `frontend/apps/public/src/components/ProductCard.tsx`: `state={DA_LISTA}` no link do tema
- [X] T012 [US1] `frontend/apps/public/src/pages/ProductDetailPage.tsx`: os dois "← Voltar ao catálogo" usam `useVoltarParaLista("/")` (botão/link com `onClick` que preserva o `href` para abrir em outra aba)
- [X] T013 [P] [US1] `frontend/apps/public/src/pages/CategoryDetailPage.tsx`: "←" usa `useVoltarParaLista("/categorias")`; `useRestaurarRolagem` com `pronto` = dados da categoria; links de categoria em `frontend/apps/public/src/pages/CategoriesPage.tsx` levam `DA_LISTA`
- [X] T014 [US1] `frontend/apps/internal/src/pages/AdminCatalogoListPage.tsx`: `q`, `categoria`, `situacao`, `visao` no endereço (`data-model.md` §1; `visao` ausente = `localStorage`, escolher também grava no `localStorage`); busca digitada fica local e vai ao endereço junto com a pausa de 300 ms; `useRestaurarRolagem` com `pronto` = `query.data` presente e não atualizando
- [X] T015 [P] [US1] `frontend/apps/internal/src/components/CatalogCardGrid.tsx` e `CatalogTreeView.tsx`: links de edição com `state={DA_LISTA}`; "Editar" do menu troca `window.location.assign` por `navigate(..., { state: DA_LISTA })`
- [X] T016 [US1] `frontend/apps/internal/src/pages/AdminCatalogoFormPage.tsx`: atalho "‹ Catálogo" e o pós-salvar da edição usam `useVoltarParaLista("/admin/catalogo")`
- [X] T017 [US1] Rodar cenários 1–4 e 11 do verify até passarem

---

## Phase 4: História 2 — Voltar ao banco de talentos no mesmo ponto (P1)

**Teste independente**: cenários 5, 6 e 11.

- [X] T018 [US2] `frontend/apps/internal/src/pages/TalentsListPage.tsx`: `status`, `aba`, `q`, `pagina` e filtros avançados no endereço (`data-model.md` §1, `replace: true`); busca local com pausa para o endereço (padrão `AgendaPage.tsx:33-63`); painel de filtros começa aberto se houver filtro no endereço; `useRestaurarRolagem` com `pronto` = `query.data`; página acima do total → última página existente
- [X] T019 [P] [US2] `frontend/apps/internal/src/components/TalentMosaic.tsx`: link da ficha com `state={DA_LISTA}`
- [X] T020 [US2] `frontend/apps/internal/src/pages/TalentDetailPage.tsx`: atalho do topo e o pós-rejeitar usam `useVoltarParaLista` com fallback `/talents` ou `/talents?status=pending`
- [X] T021 [US2] Rodar cenários 5, 6 e 11 até passarem

---

## Phase 5: História 3 — Arquivo abre dentro do sistema, com "Voltar" (P1)

**Teste independente**: cenários 7–9.

- [X] T022 [P] [US3] `frontend/packages/ui/src/components/pdf-paginas.tsx`: importa `pdfjs-dist` (worker via `?url`), desenha cada página num `<canvas>` (densidade ≤ 2) quando chega perto da tela, `Skeleton` no lugar, `onErro` para o pai; exportado só como `default` para `React.lazy`
- [X] T023 [US3] `frontend/packages/ui/src/components/visualizador-de-arquivo.tsx`: tela cheia sobre Radix Dialog (z-[60], `AnimatePresence` + `useReducedMotion`), barra fixa "Voltar" / nome / "Baixar", foto, PDF por `lazy(() => import("./pdf-paginas"))`, sem prévia, erro com "Tentar novamente"; "Baixar" com folha de compartilhar em tela de toque e `<a download>` no resto; exportar em `frontend/packages/ui/src/index.ts`
- [X] T024 [US3] `frontend/apps/internal/src/components/ArquivoViewer.tsx`: `ArquivoViewerProvider` (marca `arquivoAberto` no histórico, fecha no POP, limpa marca órfã ao recarregar), `useAbrirArquivo`, `LinkDeArquivo` (`forwardRef`, `assetUrl`, externo segue em outra aba, Ctrl/⌘/Shift/meio deixam o navegador agir); montar o provedor em `frontend/apps/internal/src/App.tsx`
- [X] T025 [US3] `frontend/apps/internal/src/pages/GastosExtrasPage.tsx`: "Ver" → `LinkDeArquivo caminho={expense.receipt_url}`
- [X] T026 [P] [US3] `frontend/apps/internal/src/components/EventDetail/GastosVinculados.tsx` e `FinanceiroSection.tsx` (contrato, comprovante, nota, nota do gasto, comprovante de recebimento) → `LinkDeArquivo`
- [X] T027 [P] [US3] `frontend/apps/internal/src/components/EventDetail/LogisticaSection.tsx` (só material arquivo), `frontend/apps/internal/src/components/Pagamentos/SalaryAdvancesDialog.tsx`, `frontend/apps/internal/src/pages/VirtuaisDevolucoesPage.tsx` → `LinkDeArquivo`
- [X] T028 [P] [US3] `frontend/apps/internal/src/pages/FigurinoProducaoDetailPage.tsx` (3 pontos), `RevisaoAssetPage.tsx` ("Ver PDF"), `TalentDetailPage.tsx` (2 pontos, "Ver PDF") → `LinkDeArquivo`
- [X] T029 [US3] Rodar cenários 7–9 até passarem

---

## Phase 6: História 4 — Catálogo pelo menu no app instalado (P2)

**Teste independente**: cenário 10.

- [X] T030 [P] [US4] `frontend/packages/ui/src/components/app-layout.tsx`: item `external` sem `target` quando `estaComoAppInstalado()`; ajustar o `hint` do item em `frontend/apps/internal/src/lib/navigation.tsx` só se o texto ficar falso
- [X] T031 [P] [US4] `frontend/apps/public/src/components/VoltarAoSistema.tsx` (só no app instalado; "← Voltar ao sistema"; `history.back()` ou `/`), montado em `frontend/apps/public/src/App.tsx` só nas rotas do catálogo
- [X] T032 [US4] Rodar o cenário 10 até passar

---

## Phase 7: Polish e portões

- [X] T033 Verify completo `12/12` (com contraprova contra a `main`); saída em `specs/320-voltar-sem-perder-o-lugar/verify_320_resultado.txt`
- [X] T034 [P] `cd frontend && npm run typecheck` e `npm run build` (o chunk do pdf.js e o worker saem à parte; os três apps os emitem, só baixados quando um PDF abre — dívida 168)
- [X] T035 Conferência de tela no Browser pane (skill `manto-conferir-tela`), viewport de iPhone: os 6 passos do `quickstart.md`
- [X] T036 [P] Docs: `docs/02` (catálogo público, gerenciador, banco de talentos, visualizador), `docs/00` §5 (convenção: estado de lista no endereço; arquivo sempre por `LinkDeArquivo`), `docs/03` (entrada no topo + índice), `docs/05` (dívidas: e2e da 180 parado; outras listas sem restauração)
- [X] T037 Commits por caminho (`feat(320): …`, `docs(320): …`), nunca `git add -A`

---

## Dependências

- Phase 1 → Phase 2 → histórias. US1, US2 e US3 são independentes entre si depois da Phase 2
  (US3 só depende de T001). US4 depende de T007.
- Dentro de US3: T022 → T023 → T024 → T025–T028.
- `TalentDetailPage.tsx` é tocada por T020 (US2) e T028 (US3): fazer em sequência.

## Paralelismo

- Phase 2: T006, T007, T008, T009 em arquivos diferentes.
- US1: T010, T011, T013, T015 juntos; depois T012, T014, T016.
- US3: T026, T027, T028 juntos depois de T024.

## Estratégia

MVP = US1 (o pedido mais repetido: catálogo). Entrega única, porém: as quatro histórias vão juntas
num deploy só, fora do horário, quando o dono pedir.

---

## Phase 8: Convergence

Leitura independente do código contra spec/plano/contrato (27/10). Os achados viraram as tarefas
abaixo, já feitas nesta mesma rodada; o verify foi rodado de novo no fim.

- [X] T038 Prefixar `/uploads/` no comprovante de gasto vinculado em `frontend/apps/internal/src/components/EventDetail/GastosVinculados.tsx` (a API manda `receipt_path` relativo, "expenses/…"; o link abria `/events/<id>/expenses/…`) per FR-015 (partial)
- [X] T039 Não restaurar rolagem na primeira tela de um carregamento (o React Router a marca como POP) e prefixar a chave com o caminho em `frontend/packages/ui/src/lib/rolagem.ts` e nos dois `lib/navegacao.tsx` per FR-005 (contradicts)
- [X] T040 "Baixar" no celular: buscar o arquivo ao abrir e chamar `share` direto do toque, sem cair no `<a download>` em erro, em `frontend/packages/ui/src/components/visualizador-de-arquivo.tsx` per FR-012 (partial)
- [X] T041 Usar o build legacy do pdf.js (iOS < 17.4 sem `Promise.withResolvers`) em `frontend/packages/ui/src/components/pdf-paginas.tsx` per FR-010 (partial)
- [X] T042 Devolver o foco ao "Ver" ao fechar o visualizador (`onCloseAutoFocus`) em `visualizador-de-arquivo.tsx` per Casos de borda/Teclado (missing)
- [X] T043 Marcar `DA_LISTA` nos links da visão Personagens (`CatalogPersonagensView.tsx`) e da fila de e-mails (`BounceQueue.tsx`) per FR-006 (partial)
- [X] T044 Raiz do `IntersectionObserver` = área que rola do visualizador (antecipação das páginas do PDF) em `pdf-paginas.tsx` per Casos de borda/PDF longo (partial)
- [X] T045 Toque duplo no "Ver" não empilha dois passos de "voltar" em `frontend/apps/internal/src/components/ArquivoViewer.tsx` per FR-011 (partial)
- [X] T046 "← Voltar ao sistema" só quando há entrada antes do catálogo (cliente que salvou o catálogo na Tela de Início não vê) em `frontend/apps/public/src/components/VoltarAoSistema.tsx`; contrato atualizado para `history.go(-(idx+1))` per FR-017 (partial)
- [X] T047 Foto inteira na tela (`max-h-full object-contain`) em `visualizador-de-arquivo.tsx` per História 3 (partial)

Ficaram fora, de propósito: largura do PDF ao girar o aparelho e liberar páginas já desenhadas em
PDF muito longo (o comprovante típico tem 1–3 páginas); downloads `<a download>` de arquivo 3D
(`Acervo3DPage`, `Fila3DPage`) — são download, não "abrir", e não prendem a janela.
