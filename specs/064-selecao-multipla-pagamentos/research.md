# Research: Seleção múltipla estilo planilha nos pagamentos (064)

Decisões técnicas. Sem `NEEDS CLARIFICATION`. **Feature client-side** (sem backend/migration).

## 1. Estado atual

- `financeiro/pagamentos.html` já tem: caixas `.row-check` por linha, `#select-all`, barra de
  ações em lote (`#bulk-bar`), contador `#bulk-count` ("N selecionado(s)"), realce
  `tr.row-selected`, e cada linha (`tr.pay-row`) com **`data-amount`** (valor em float).
- A função `updateBulkBar()` já recalcula o contador e o realce a cada `change` de checkbox.
- Filtro/busca esconde linhas via `display:none` (há `isRowVisible(cb)`).

## 2. Soma dos selecionados

- **Decisão**: em `updateBulkBar()`, somar `tr.dataset.amount` das linhas marcadas e exibir junto
  do contador (`#bulk-count`): "N selecionados · R$ X". Itens sem valor → `data-amount=0`.
- **Formato BR**: helper local `fmtBRL(v)` (ponto de milhar, vírgula de centavos) — autossuficiente
  na página (não depende de `money-mask.js`).
- **Rationale**: reusa o `data-amount` já presente e o ponto único de atualização da seleção.

## 3. Seleção por Shift (intervalo) + individual

- **Decisão**: indexar as `.row-check` na ordem do DOM; manter `lastIndex` do último clique. No
  `click` de uma caixa: se `shiftKey` e há `lastIndex`, aplicar o estado (`checked`) da caixa
  atual a todas as caixas **visíveis** no intervalo `[min,max]`; atualizar `lastIndex` sempre.
- **Ctrl / clique simples**: comportamento nativo de checkbox (alterna a linha) — já é o "um a
  um" pedido; sem mudança.
- **Respeitar filtro**: no preenchimento do intervalo, pular linhas ocultas (`isRowVisible`).
- **Rationale**: padrão "explorador de arquivos" com o mínimo de código, reusando `updateBulkBar`
  e `isRowVisible`. `click` dispara após a caixa alternar, então `cb.checked` já reflete o alvo.

## 4. Sem backend / migration

- **Decisão**: nenhuma. Só JS na página; as ações em lote e o servidor não mudam.

## 5. Verificação

- Server: GET da página (render 200) contra `manto_local`. O comportamento de Shift/soma é
  **client-side** → verificação funcional é manual no navegador (test client não roda JS);
  confirmo a presença dos hooks (fmtBRL, handler de shift) no HTML servido.
