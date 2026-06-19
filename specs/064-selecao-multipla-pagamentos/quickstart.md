# Quickstart — Verificação manual da feature 064

**Rodar contra a cópia local `manto_local` (Postgres)**: `.\scripts\db\run-local.ps1`, abrir
`/financeiro/pagamentos`.

## Passo 1 — Quantidade + soma (US1, FR-001/002/007)

1. Marcar alguns pagamentos.
   - ✅ A barra mostra "N selecionados · R$ soma", batendo com os itens marcados.
2. Marcar um item sem valor (—).
   - ✅ Conta como R$ 0; a soma não quebra.
3. Desmarcar tudo.
   - ✅ A barra some.

## Passo 2 — Shift (intervalo) + individual (US2, FR-003/004/005)

1. Marcar uma linha; segurar **Shift** e clicar numa linha mais abaixo.
   - ✅ Todas as linhas entre as duas ficam marcadas; quantidade e soma refletem.
2. Com a busca/filtro ativo, repetir o Shift.
   - ✅ Só as linhas **visíveis** do intervalo são marcadas.
3. Clicar numa caixinha sem Shift.
   - ✅ Alterna só aquela linha (individual), como antes.

## Passo 3 — Sem regressão (SC-004)

1. Usar "Marcar pago / No banco / Não pago / Excluir" sobre uma seleção.
   - ✅ Funcionam como antes.

## Checklist de qualidade (Portões da constituição)

- [ ] Sem migration / sem backend novo.
- [ ] Página renderiza (200) contra `manto_local`; hooks presentes no HTML.
- [ ] Ações em lote, filtro e "selecionar tudo" sem regressão (verificação no navegador).
