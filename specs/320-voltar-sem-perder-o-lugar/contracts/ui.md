# Contrato de UI — Feature 320

Nenhum endpoint muda. O contrato é entre componentes e com o endereço da página.

## `@manto/ui` (sem dependência do roteador)

### `useRestaurarRolagem(chave: string, opcoes: { restaurar: boolean; pronto: boolean }): void`

- Enquanto montado, guarda `window.scrollY` sob `chave` no `sessionStorage` (`manto:rolagem`, até
  50 entradas), a cada rolagem (limitado a um registro por quadro) e ao desmontar.
- Se `restaurar` era verdadeiro **na montagem**, quando `pronto` virar verdadeiro rola até o ponto
  guardado; enquanto a página for mais curta que o ponto, tenta de novo a cada quadro por até 1,5 s;
  para se a pessoa rolar, tocar ou usar a roda antes.
- Troca de `chave` com o componente montado (busca escrita com `replace`) só muda onde se guarda;
  não restaura de novo.

### `estaComoAppInstalado(): boolean`

`matchMedia("(display-mode: standalone)").matches || navigator.standalone === true`. Seguro fora do
navegador (devolve `false`).

### `VisualizadorDeArquivo`

```ts
interface VisualizadorDeArquivoProps {
  arquivo: { url: string; nome?: string } | null; // null = fechado
  onFechar: () => void;                           // "Voltar", Esc, toque fora
}
```

- Tela cheia sobre tudo (`z-[60]`, acima de `Dialog` z-50 e `Modal` z-50), foco preso, Esc fecha.
- Barra fixa no topo: botão **"Voltar"** (ícone de seta + texto), nome do arquivo (cortado com "…"),
  botão **"Baixar"**.
- Tipo pela extensão do caminho (sem a query): `pdf` → páginas do pdf.js; `jpg jpeg png webp gif
  heic heif avif` → `<img>`; resto → "Este tipo de arquivo não tem prévia." + "Baixar".
- PDF: `pdfjs-dist@4.10.38` importado sob demanda; cada página vira um `<canvas>` na largura da área
  (densidade de pixel limitada a 2), desenhado quando chega perto da tela; enquanto isso, um
  `Skeleton` do tamanho da página.
- Erro de carga (img `onError`, pdf.js rejeitou): "Não foi possível abrir o arquivo. Tente
  novamente." + "Tentar novamente" (remonta) — "Voltar" continua na barra.
- "Baixar": tela de toque (`(pointer: coarse)`) com `navigator.canShare({ files })` → busca o arquivo
  e abre a folha de compartilhar; senão `<a href download>`. Se o compartilhar falhar (não
  cancelado), cai no `<a download>`.

### `AppLayout` — item `external` do menu

`estaComoAppInstalado()` → `<a href>` sem `target` (mesma janela); senão como hoje.

## App interno

### `ArquivoViewerProvider` (em volta das rotas, dentro do `BrowserRouter`)

- `useAbrirArquivo(): (arquivo: { url: string; nome?: string }) => void`.
- Abrir = `navigate(location, { state: { ...location.state, arquivoAberto: n } })` (PUSH do mesmo
  endereço) + guarda o arquivo no estado do React.
- Fecha quando a marca `arquivoAberto` da localização atual deixa de ser `n` (voltar do navegador).
- `onFechar` do visualizador = `navigate(-1)`.
- Montou com marca no `state` e nenhum arquivo aberto (recarregou) → `navigate(location, { replace:
  true, state: <sem a marca> })`.

### `LinkDeArquivo` (`forwardRef<HTMLAnchorElement>`, aceita as props de `<a>`)

```ts
interface LinkDeArquivoProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  caminho: string;  // caminho do Flask ("/uploads/..." ou relativo) ou URL absoluta
  nome?: string;    // título na barra do visualizador
}
```

- `href = assetUrl(caminho)`. URL de outro site (`http(s)://` de outra origem) → link comum em outra
  aba, sem visualizador (ex.: comprovante da InfinitePay, link de material).
- Clique simples → `preventDefault()` + abre o visualizador. Ctrl/⌘/Shift/clique do meio → deixa o
  navegador agir (abrir em outra aba no computador continua possível).
- Funciona com `<Button asChild>`.

### Pontos que passam a usar `LinkDeArquivo`

| Arquivo (HEAD `e60aae53`) | O quê |
|---|---|
| `pages/GastosExtrasPage.tsx:719` | comprovante do gasto extra ("Ver") — hoje sem `assetUrl` |
| `components/EventDetail/GastosVinculados.tsx:28` | comprovante do gasto vinculado |
| `components/EventDetail/FinanceiroSection.tsx:67` | contrato |
| `components/EventDetail/FinanceiroSection.tsx:254` | comprovante de pagamento |
| `components/EventDetail/FinanceiroSection.tsx:574` | nota fiscal |
| `components/EventDetail/FinanceiroSection.tsx:732` | nota do gasto |
| `components/EventDetail/FinanceiroSection.tsx:761` | comprovante de recebimento |
| `components/EventDetail/LogisticaSection.tsx:224` | material do evento (arquivo; `link` segue externo) |
| `components/Pagamentos/SalaryAdvancesDialog.tsx:159` | comprovante de adiantamento (dentro de diálogo) |
| `pages/VirtuaisDevolucoesPage.tsx:150` | comprovante da devolução (externo → segue em outra aba) |
| `pages/FigurinoProducaoDetailPage.tsx:349,550,701` | orçamento, foto do registro, foto da peça |
| `pages/RevisaoAssetPage.tsx:191` | PDF do material em revisão ("Abrir PDF em nova aba" → "Ver PDF") |
| `pages/TalentDetailPage.tsx:498,677` | documento do talento em PDF ("Abrir PDF" → "Ver PDF") |

Ficam como estão (não são arquivo do sistema): WhatsApp, Google Maps, Meet, Drive, post de rede
social, página pública do catálogo/formulário, impressão de figurino (`window.open`), link de
observação.

### Listas

- `TalentsListPage`, `AdminCatalogoListPage`: estado no endereço (`data-model.md` §1) +
  `useRestaurarRolagem(location.key, { restaurar: navigationType === "POP", pronto: <lista na tela> })`.
- Links para o detalhe levam `state={{ daLista: true }}`: `TalentMosaic`, `CatalogCardGrid` (nome e
  "Editar" do menu — este troca `window.location.assign` por `navigate`), `CatalogTreeView`.
- `useVoltarParaLista(fallback)` → função: `daLista` → `navigate(-1)`; senão `navigate(fallback)`.
  Usado em `TalentDetailPage` (atalho do topo e depois de rejeitar) e `AdminCatalogoFormPage`
  (atalho do topo e depois de salvar a edição).
- `RolarAoTopoEmNovaPagina`: PUSH/REPLACE que muda `pathname` → `window.scrollTo(0, 0)`, em
  `useLayoutEffect`, montado ANTES das `<Routes>` — telas que rolam até um elemento ao abrir
  (`Tags3DPage.tsx:158`, `ProductDetailPage.tsx:30`) rodam depois e continuam valendo. Abas do
  evento são `?aba=` (mesmo caminho) e não sobem.

## App público (catálogo)

- `CatalogGridPage`: `q` e `categoria` no endereço; `useRestaurarRolagem` com `pronto = data
  carregada`. `CategoryDetailPage`: `useRestaurarRolagem`.
- `ProductCard`: `state={{ daLista: true }}`.
- `ProductDetailPage` ("← Voltar ao catálogo", nos dois lugares) e `CategoryDetailPage` ("←" para
  `/categorias`): `useVoltarParaLista`.
- `RolarAoTopoEmNovaPagina` no `App`.
- `VoltarAoSistema`: só com `estaComoAppInstalado()`; botão fixo "← Voltar ao sistema" (tom público,
  claro); só aparece se houver entrada antes do catálogo (`history.length > idx + 1`, com o `idx` que
  o React Router grava); clique → `history.go(-(idx + 1))` — pula o que a pessoa navegou dentro do
  catálogo e cai na tela do sistema —, senão `window.location.assign("/")`.
  Mostrado nas páginas do catálogo (grade, categorias, categoria, tema, lista de desejos), não na
  loja `/v`, no cadastro, nos formulários, na avaliação nem na NFC.
