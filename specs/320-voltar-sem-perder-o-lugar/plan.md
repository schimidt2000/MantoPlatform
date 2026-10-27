# Plano de implementação: 320 — Voltar sem perder o lugar

**Branch**: `320-voltar-sem-perder-o-lugar` | **Data**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/320-voltar-sem-perder-o-lugar/spec.md`

## Resumo

Três sintomas, uma raiz: "voltar" não devolve a pessoa para onde ela estava. As listas (catálogo
público, gerenciador de catálogo, banco de talentos) passam a guardar busca e filtros no endereço e
a restaurar a rolagem na volta; os atalhos "Voltar" das páginas de detalhe passam a voltar de
verdade quando a pessoa veio da lista. Todo arquivo do app interno passa a abrir num visualizador
dentro do sistema (foto, PDF pelo pdf.js, "Baixar"), ligado ao histórico, com "Voltar" sempre à
vista — o que resolve o iPhone com o sistema na Tela de Início. No app instalado, o "Catálogo" do
menu abre na mesma janela e o catálogo mostra "← Voltar ao sistema". Só frontend; nada no Flask.

## Contexto técnico

**Linguagem/Versão**: TypeScript + React 18 (Vite), react-router-dom 6.30, TanStack Query 5

**Dependências principais**: `@manto/ui` (Radix Dialog, Framer Motion), `@manto/api-client`
(`assetUrl`). **Nova**: `pdfjs-dist@4.10.38` em `@manto/ui`, importada sob demanda
(`research.md` R4).

**Armazenamento**: nenhum novo — endereço, `sessionStorage` e `history.state` (`data-model.md`)

**Verificação**: `verify_320.py` + `verify_320_navegador.mjs` (Playwright, Chromium, viewport de
iPhone) contra Vite do worktree + Flask sobre `manto_local`; `npm run typecheck` (três SPAs);
`npm run build` (o chunk do pdf.js e o worker saem no build); tela aberta no Browser pane

**Plataforma-alvo**: app interno no iPhone (Tela de Início, sem barra do Safari) e no computador;
catálogo público no celular da cliente e da comercial

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: zero peso novo nas telas que não abrem PDF (pdf.js só no chunk sob
demanda); restauração de rolagem perceptível como imediata (< 1 quadro com a lista em cache)

**Restrições**: sem migration, sem endpoint; não migrar para `createBrowserRouter`; Node 20 no build
do Render (`render.yaml:116`); `/uploads` continua com login (mesma origem)

**Escala/escopo**: 3 listas, 4 páginas de detalhe, 13 pontos de arquivo (`contracts/ui.md`),
2 componentes + 3 hooks + 1 utilitário novos, 1 dependência

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Estado no endereço segue o padrão de `AgendaPage`/`PagamentosPage` (`useSearchParams` + `replace`). Visualizador e restauração de rolagem não existem em lugar nenhum (`research.md`); nascem UMA vez em `@manto/ui` e os 13 links passam a usar um só `LinkDeArquivo`. `Dialog` do Radix já é dependência do pacote |
| II. Padrões de código | TS estrito; comentários do porquê em pt-BR; constantes nomeadas (`CHAVE_ROLAGEM`, `MAX_ENTRADAS`) |
| III. Camadas / API First | Não toca backend. `assetUrl()` passa a valer também no comprovante de gasto extra (hoje cru) |
| IV. Não quebrar o que funciona | `?status=pending` já usado pela ficha passa a funcionar; `localStorage` do modo de visão mantido; Ctrl/⌘-clique em arquivo segue abrindo outra aba; links externos (WhatsApp, Drive, InfinitePay) intocados; `AppLayout` só muda no modo app instalado; diálogos abertos sobrevivem ao visualizador (z-[60], camada própria do Radix) |
| V. UI/UX com feedback | Visualizador com `Skeleton` por página, erro "Não foi possível abrir o arquivo. Tente novamente." + "Tentar novamente"; "Baixar" desabilita enquanto busca o arquivo para compartilhar |
| VI. Esteira (Nível 1) | Três superfícies (interno, público, design system) e dependência nova → Nível 1 completo |
| VII. Living Spec | Spec com Clarifications de 27/10 antes do código |
| VIII. Verify antes do núcleo | **Desvio justificado** (tabela abaixo): o comportamento é só de navegador; `verify_320.py` mantém o esqueleto (usuário descartável, login pela API, limpeza no `finally`) e delega a navegação a um `.mjs` com Playwright. Escrito na fase Foundational, falhando na `main` (cenário 12) |
| IX. Dinheiro BRL | Não se aplica |
| X. Mobile-first público | Catálogo público conferido em 390×844; "← Voltar ao sistema" com área de toque ≥ 44px |
| XI. Framer Motion | Entrada/saída do visualizador com `AnimatePresence` + `useReducedMotion`, como o `Dialog` |
| XII. Combobox / Maps | Não se aplica |
| XIII. RBAC declarado | Nenhum endpoint novo ou alterado; `/uploads` segue com login |
| XIV. Config / efeito externo | Nenhuma env; nada escreve fora |
| XV. Texto por superfície | Interno: "Voltar", "Baixar", "Ver PDF" (era "Abrir PDF"/"Abrir PDF em nova aba" — "Ver" é o verbo do glossário para abrir arquivo), "Este tipo de arquivo não tem prévia.", "Não foi possível abrir o arquivo. Tente novamente.", "Tentar novamente". Público: "← Voltar ao sistema". Nenhum texto comparado pelo código |
| Stack | Sem migration, sem Jinja, sem segredo. `pdfjs-dist` fixada em versão exata |
| Operação e Deploy | Não toca `startCommand`. O build do frontend ganha um worker (~1 MB) servido como arquivo estático do bundle interno |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/320-voltar-sem-perder-o-lugar/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/ui.md
├── checklists/
├── tasks.md
├── verify_320.py              # orquestrador (usuário descartável, login pela API, limpeza)
└── verify_320_navegador.mjs   # cenários no Chromium (Playwright)
```

### Código

```text
frontend/packages/ui/package.json                        # + pdfjs-dist@4.10.38
frontend/packages/ui/src/lib/rolagem.ts                  # novo (useRestaurarRolagem; hooks moram em lib/, como useTheme)
frontend/packages/ui/src/lib/app-instalado.ts            # novo (estaComoAppInstalado)
frontend/packages/ui/src/components/visualizador-de-arquivo.tsx  # novo
frontend/packages/ui/src/components/pdf-paginas.tsx      # novo (chunk sob demanda)
frontend/packages/ui/src/components/app-layout.tsx       # item external no app instalado
frontend/packages/ui/src/index.ts                        # exportar os novos

frontend/apps/internal/src/App.tsx                       # ArquivoViewerProvider + RolarAoTopoEmNovaPagina
frontend/apps/internal/src/lib/navegacao.tsx             # novo: useVoltarParaLista, RolarAoTopoEmNovaPagina, DA_LISTA
frontend/apps/internal/src/components/ArquivoViewer.tsx  # novo: provider, useAbrirArquivo, LinkDeArquivo
frontend/apps/internal/src/pages/{TalentsListPage,TalentDetailPage,AdminCatalogoListPage,AdminCatalogoFormPage}.tsx
frontend/apps/internal/src/components/{TalentMosaic,CatalogCardGrid,CatalogTreeView}.tsx
frontend/apps/internal/src/… 13 pontos de arquivo (contracts/ui.md)

frontend/apps/public/src/App.tsx                         # RolarAoTopoEmNovaPagina + VoltarAoSistema
frontend/apps/public/src/lib/navegacao.tsx               # novo: useVoltarParaLista, RolarAoTopoEmNovaPagina
frontend/apps/public/src/components/VoltarAoSistema.tsx  # novo
frontend/apps/public/src/pages/{CatalogGridPage,CategoryDetailPage,ProductDetailPage}.tsx
frontend/apps/public/src/components/ProductCard.tsx
```

**Decisão de estrutura**: o que não depende do roteador (rolagem, visualizador, detecção do app
instalado) mora em `@manto/ui`, que não depende do `react-router-dom`; o que depende
(`useVoltarParaLista`, `RolarAoTopoEmNovaPagina`, provedor do visualizador) mora em cada app. Os dois
`lib/navegacao.tsx` têm ~25 linhas parecidas — aceitável: pôr o roteador como dependência do design
system só por isso acoplaria o pacote a uma versão de roteador.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify em navegador (`.py` orquestra um `.mjs`) em vez de só `verify_320.py` com `test_client` | O que muda é histórico, rolagem e sobreposição — só existem no navegador | `test_client` não renderiza React; conferir só no Browser pane não deixa prova repetível nem contraprova na `main` |
| Dependência nova `pdfjs-dist` | O iPhone não mostra PDF de forma confiável dentro de `<iframe>`; o dono usa iPhone | `<iframe>` (não verificável daqui e falho no iOS); converter no servidor (backend novo sem necessidade) |
