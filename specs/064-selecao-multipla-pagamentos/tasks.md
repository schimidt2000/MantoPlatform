# Tasks: Seleção múltipla estilo planilha nos pagamentos

**Feature**: `064-selecao-multipla-pagamentos` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Tudo em `app/templates/financeiro/pagamentos.html` (JS). Reusa a seleção em lote existente.
Sem backend, sem migration.

---

## Fase 1 — Soma dos selecionados (US1)

- [X] T001 [US1] Em `updateBulkBar()`, somar `tr.dataset.amount` das linhas marcadas e exibir no `#bulk-count` como "N selecionado(s) · R$ soma". Adicionar helper `fmtBRL(v)` (formato BR: ponto de milhar, vírgula de centavos). Itens sem valor contam como 0.

## Fase 2 — Seleção por Shift (US2)

- [X] T002 [US2] Adicionar handler de `click` nas `.row-check`: manter `lastIndex`; quando `shiftKey` e houver `lastIndex`, aplicar o estado da caixa atual a todas as `.row-check` **visíveis** no intervalo `[min,max]` (usar `isRowVisible`); chamar `updateBulkBar()`. Clique sem Shift segue o toggle nativo (individual).

## Fase 3 — Verificação

- [X] T003 Verificar contra **`manto_local`**: GET `/financeiro/pagamentos` retorna 200 e o HTML contém os hooks novos (`fmtBRL`, handler de shift). Conferir manualmente no navegador: soma correta, Shift seleciona intervalo (respeitando filtro), clique individual e ações em lote sem regressão.

---

## Dependências

- T001 e T002 independentes (mesmo arquivo). T003 ao final.

## MVP

T001 (soma) + T002 (Shift) entregam o pedido completo.
