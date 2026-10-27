# Pesquisa — Feature 320 (voltar sem perder o lugar)

Levantamento do código em 27/10/2026 (HEAD `e60aae53`). Citações `arquivo:linha` contra esse HEAD.

## Diagnóstico

| Sintoma | Causa no código |
|---|---|
| Busca/filtros somem ao voltar (catálogo público) | `apps/public/src/pages/CatalogGridPage.tsx:16-17` — `search` e `activeCategory` em `useState`; somem ao desmontar |
| Idem (gerenciador) | `apps/internal/src/pages/AdminCatalogoListPage.tsx:31-33` — `q`, `categoria`, `status` em `useState` |
| Idem (talentos) | `apps/internal/src/pages/TalentsListPage.tsx:17-24` — tudo em `useState`; o `?status=pending` que a ficha manda (`TalentDetailPage.tsx:347,401`) nunca é lido |
| Rolagem cai no topo | nenhum app tem restauração de rolagem: `BrowserRouter` (`apps/internal/src/App.tsx:86`, `apps/public/src/App.tsx:45`) não aceita `<ScrollRestoration>`; quem rola é a janela (`packages/ui/src/components/app-layout.tsx:183,245`). O navegador tenta restaurar no `popstate`, mas a página ainda é a do detalhe (curta) e a posição é cortada |
| "Voltar" leva ao início | os atalhos fazem PUSH de uma entrada nova em vez de voltar: `ProductDetailPage.tsx:50-55,64`, `CategoryDetailPage.tsx:32`, `AdminCatalogoFormPage.tsx:150,178`, `TalentDetailPage.tsx:347,401` |
| "Editar" do menu do card recarrega o app | `CatalogCardGrid.tsx:63` — `window.location.assign(...)` |
| Comprovante prende o app no iPhone | todo arquivo abre com `<a target="_blank">` (13 telas; lista no `contracts/ui.md`). No app da Tela de Início não há barra nem botão de voltar |
| Catálogo pelo menu prende o app | `app-layout.tsx:105-115` — item `external` sempre `target="_blank"` |
| Comprovante de gasto usa caminho cru | `GastosExtrasPage.tsx:719-729` usa `expense.receipt_url` direto, sem `assetUrl()` |

## R1 — Onde guardar busca e filtros

- **Decisão**: no endereço (`useSearchParams`), sempre com `{ replace: true }`.
- **Por quê**: voltar, recarregar e copiar o link reproduzem a lista; é o padrão já usado em
  `AgendaPage.tsx:33-63`, `PagamentosPage.tsx:232-245`, `FigurinoProducaoListPage.tsx:560-603`.
  `replace` evita um passo de "voltar" por letra digitada (FR-008).
- **Alternativas**: `sessionStorage` por tela (não sobrevive a link copiado, e é um segundo lugar
  de verdade); store global (não existe no projeto e não resolve recarregar).

## R2 — Como restaurar a rolagem

- **Decisão**: hook `useRestaurarRolagem(chave, { restaurar, pronto })` em `@manto/ui`, sem
  dependência do roteador. Guarda `window.scrollY` no `sessionStorage` por chave (a `location.key`
  da entrada do histórico) enquanto a lista está montada; na volta (`navigationType === "POP"`),
  espera a lista ficar pronta e rola até o ponto salvo, tentando de novo por até ~1,5 s enquanto a
  página ainda não tem altura (fotos chegando) e desistindo se a pessoa rolar antes.
  Complemento: `RolarAoTopoEmNovaPagina` em cada app — numa navegação NOVA (PUSH/REPLACE) que troca
  de caminho, a janela vai ao topo (hoje o detalhe abre na rolagem da lista, e voltar pelo menu à
  lista abre no meio).
- **Por quê**: `<ScrollRestoration>` do React Router exige migrar os dois apps para
  `createBrowserRouter` (≈100 rotas no interno) — risco desproporcional. O hook é pequeno, serve aos
  dois apps (o público e o interno têm roteadores diferentes) e fica pronto para outras listas.
  `location.key` vive no `history.state`, então sobrevive a recarregar a página.
- **Alternativas**: `history.scrollRestoration = "manual"` global (tiraria a restauração parcial que
  o navegador já faz nas outras telas — fora do escopo mexer); salvar o id do item aberto e rolar até
  ele (frágil quando o item some do filtro; a posição em pixels já resolve).

## R3 — Os atalhos "Voltar" das páginas de detalhe

- **Decisão**: o link da lista para o detalhe leva uma marca no `state` da navegação
  (`{ daLista: true }`); o atalho "Voltar" do detalhe faz `navigate(-1)` quando a marca está lá e
  `navigate(<lista>)` quando não está (link direto, vindo de outra tela). Hook `useVoltarParaLista`
  em cada app (depende do roteador).
- **Por quê**: o rótulo diz "Voltar ao catálogo"/"Talentos ativos"; voltar para outra tela seria
  mentir. `navigate(-1)` reaproveita a entrada do histórico — com filtros no endereço e a rolagem
  guardada pela chave dela.
- **Alternativas**: `location.key !== "default"` (voltaria para onde quer que a pessoa estivesse,
  inclusive fora da lista).

## R4 — Visualizador de arquivo

- **Decisão**: componente `VisualizadorDeArquivo` em `@manto/ui` (tela cheia, sobre
  `@radix-ui/react-dialog`, que o pacote já usa): barra fixa com "Voltar", nome do arquivo e
  "Baixar"; foto em `<img>`; PDF desenhado página a página pelo **pdf.js** (`pdfjs-dist@4.10.38`,
  carregado sob demanda só quando um PDF abre); outros tipos com "Baixar". No interno, um provedor
  (`ArquivoViewerProvider`) liga o visualizador ao histórico e um `LinkDeArquivo` substitui os
  `<a target="_blank">`.
- **Por quê PDF pelo pdf.js**: o aparelho da equipe é o iPhone (resposta do dono). Num `<iframe>`, o
  Safari do iPhone mostra o PDF sem rolagem confiável e às vezes só a primeira página; não há como
  provar isso daqui. O pdf.js desenha em `<canvas>` igual no Chrome do computador e no iPhone, e o
  verify consegue conferir que as páginas foram desenhadas. Carregado sob demanda: não pesa nas
  outras telas nem nos apps público e portal.
- **Por quê 4.10.38**: última da linha 4 (jan/2025), API conhecida (`getDocument` + `page.render`);
  as linhas 5 e 6 declaram `node >= 22` e o Render builda com Node 20 (`render.yaml:116`).
- **Histórico**: abrir faz um PUSH do mesmo endereço com uma marca no `state`
  (`{ ...state, arquivoAberto: <id> }`); fechar ("Voltar", Esc, toque fora) faz `navigate(-1)`; o
  voltar do navegador/gesto tira a marca e o provedor fecha. Recarregar a página com a marca no
  histórico não reabre nada (o arquivo aberto vive no estado do React) e o provedor limpa a marca
  com `replace`.
- **Baixar**: em tela de toque com `navigator.canShare({ files })` (iPhone), abre a folha de
  compartilhar do sistema ("Salvar em Arquivos", Fotos, WhatsApp) — um `<a download>` no app da Tela
  de Início abriria o arquivo na mesma janela, a armadilha de novo. No computador, `<a download>`.
- **Alternativas**: `<iframe>` para PDF (rejeitado acima); abrir na mesma janela (sem botão de
  voltar no app instalado — é o problema); `react-pdf` (camada a mais sobre o mesmo pdf.js);
  converter PDF em imagem no servidor (backend novo, sem necessidade).

## R5 — Detectar o "app instalado"

- **Decisão**: `matchMedia("(display-mode: standalone)").matches || navigator.standalone === true`
  (o segundo é o do iOS), num utilitário `estaComoAppInstalado()` em `@manto/ui`.
- **Uso**: só na História 4 (menu "Catálogo" na mesma janela + "← Voltar ao sistema" no catálogo).
  O visualizador vale em qualquer modo — no navegador comum ele também é melhor que uma aba nova.

## R6 — Verificação

- **Decisão**: `verify_320.py` (orquestrador, padrão do Princípio VIII: usuário descartável
  SUPERADMIN criado no `manto_local`, login só por `POST /api/auth/login`, limpeza no `finally`)
  chama `verify_320_navegador.mjs`, que dirige um Chromium de verdade pelo Playwright já instalado em
  `frontend/node_modules` (feature 180; navegador `chromium-1228` em `ms-playwright`). Os cenários de
  iPhone usam viewport 390×844 com toque; o modo app instalado é simulado definindo
  `navigator.standalone = true` antes da página carregar (`addInitScript`) — o mesmo sinal que o iOS
  dá (a emulação de mídia do Playwright não cobre `display-mode`).
- **Dados**: lê do `manto_local` gastos com comprovante cujo arquivo existe em
  `instance/uploads/expenses` (há 3 JPG e 15 PDF locais), talentos e catálogo reais. Nada é escrito
  além do usuário descartável.
- **Por quê**: o comportamento é só de navegador; um `.py` com `test_client` não exercita
  histórico, rolagem nem sobreposição.
