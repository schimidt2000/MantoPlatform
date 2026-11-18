<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Gasto extra parcelado

**Branch**: `353-gasto-extra-parcelado` (da `352-fornecedores-gastos-extras`) | **Data**: 2026-11-17 |
**Spec**: [spec.md](./spec.md)

## Resumo

Tabela `gasto_parcelas` (uma linha por parcela, com a própria situação de pagamento). Núcleo novo
`app/gastos/parcela_ops.py`: valida e grava as parcelas do gasto (criar e editar, com a parcela paga travada), deriva
`amount` = soma e `payment_status` do gasto, monta os itens da Planilha e marca a situação de uma parcela. O gasto
parcelado sai do item `"expense"` da Planilha e entra como itens `"expense_parcela"` (id = id da parcela, inteiro), na
leitura do mês, nos atrasados (331), no set-status e no lote. A DRE e o custo do evento não mudam (leem `expense_date` e
`amount`). Na tela: "Pagar em parcelas" no formulário do gasto, as parcelas na lista de Gastos Extras e o tipo novo na
Planilha.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy); TypeScript + React 18 (Vite)

**Armazenamento**: PostgreSQL; verificação no `manto_352` (o espelho da 352, já com `f352a1b2c3d4`; a 353 aplica por
cima) — mesma exceção ao Princípio VIII registrada na 352.

**Verificação**: `verify_353.py` (11 cenários); `verify_352.py` e `specs/331-atrasados-na-planilha/verify_331.py`
rodados de novo (regressão da Planilha); typecheck; telas no Browser pane.

**Restrições**: o `item_type` desconhecido no set-status cai no cachê (`EventRole`) de mesmo id
(`financeiro_write.py:194-208`) — o tipo novo tem ramo próprio ANTES do `else`; o lote manda um array por tipo
(`parcela_ids`), nunca id composto (o React faz `Number(id)`); campo novo do payload é opcional no React.

**Escala/escopo**: 1 tabela, 0 colunas novas, 0 endpoints novos (4 alterados: `POST/PATCH /api/gastos`,
`GET /api/financeiro/pagamentos`, `POST …/set-status`, `POST …/bulk-action`), 2 telas alteradas.

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar | itens montados no formato de `_build_payment_items`; `STATUS_EM_ABERTO` de `atrasados_ops`; `MoneyInput`, `brl`, `formatDate`; o padrão "uma linha por parcela com status próprio" já existe em `RecurringExpenseEntry` (não reaproveitado: a FK é obrigatória para conta recorrente e a DRE o soma como recorrente — contaria em dobro) |
| II. Padrões | type hints/docstrings; `ruff format` só nos novos; TS estrito |
| III. Camadas | regra em `parcela_ops.py` (puro); views só gate + chamada; `financeiro_read`/`write` chamam o núcleo |
| IV. Não quebrar | gasto não parcelado idêntico (um item, mesma data); DRE intocada; regressão com `verify_331` e `verify_352`; o Jinja de pagamentos (não servido em produção) segue com a cópia antiga do filtro — mostra o parcelado inteiro, registrado |
| V. Feedback | erro no campo da parcela (`fields["parcelas.N.valor"]`), nada digitado se perde; botões com loading |
| VI/VII | esteira completa; spec antes |
| VIII. Verify antes | `verify_353.py` na Foundational |
| IX. BRL | `MoneyInput` por parcela; `Numeric(10,2)`; soma em `Decimal` |
| X/XI | tela interna em 390 px; `Modal` já anima |
| XII. Combobox | não se aplica (datas e valores) |
| XIII. RBAC | gates inalterados; o tipo novo herda o gate do set-status e do lote (Financeiro/Superadmin) |
| XIV | sem env nova |
| XV. Texto | "Pagar em parcelas", "Adicionar parcela", "Remover parcela", "Parcela 1 de 2", "Total das parcelas", erros "Informe a data da parcela.", "Informe o valor da parcela.", "Parcelado precisa de pelo menos duas parcelas.", "Parcela paga não muda: desmarque o pagamento na Planilha de Pagamentos primeiro." |
| Stack | migration à mão `f353a1b2c3d4` (`down_revision = f352a1b2c3d4`) |
| Operação e Deploy | toca backend e frontend; aditiva; sobe junto com a 352 |

## Decisões de desenho

### 1. Contrato das parcelas no gasto

- `POST /api/gastos` (multipart): campo `parcelas` = JSON `[{"data": "AAAA-MM-DD", "valor": 500.0}, …]`.
- `PATCH /api/gastos/<id>` (JSON): `parcelas` = lista `[{"id"?: int, "data", "valor"}]`.
  - **ausente** → as parcelas gravadas ficam como estão (e o `amount` enviado tem de bater com a soma, senão 400
    `fields.amount`): bundle antigo editando gasto parcelado não apaga nada;
  - **`[]`** → deixa de ser parcelado (recusado se alguma está paga/no banco);
  - **lista** → vira o conjunto de parcelas (2..24).
- Resposta do gasto (`_expense_dict`): `parcelas: [{id, numero, data, valor, payment_status}]` (`[]` no não
  parcelado).

### 2. Gravar as parcelas (`parcela_ops.gravar_parcelas(expense, itens)`)

1. Valida cada item: data ISO (`fields["parcelas.N.data"]`), valor > 0 (`fields["parcelas.N.valor"]`); 2 ≤ N ≤ 24
   (`fields["parcelas"]`).
2. Recusa parcelamento quando: sem desembolso ou `cliente`; categoria devolução ou multa (306 reescreve o valor delas);
   `paid_at_creation`; gasto do auditor de marketing (`MarketingAdSpendBatch` reescreve o valor do pendente).
3. Parcela gravada `pago`/`no_banco`: tem de vir com o mesmo `id`, data e valor; senão 400 no índice dela (ou em
   `parcelas` se sumiu).
4. As não pagas que não vieram são apagadas; as que vieram com `id` são atualizadas; sem `id` (ou id alheio) nascem
   `nao_pago`.
5. Renumera por (data, ordem de chegada); `amount` = Σ; `payment_status` do gasto = derivado.

Chamado por `gastos_ops.create_expense`/`edit_expense` depois de `_validate_expense_data` (o `amount` do corpo é
substituído pela soma antes da validação). A trava da devolução (306) segue antes de tudo.

### 3. Planilha de Pagamentos

- `_pagamentos_gastos_entre` (`app/financeiro/routes.py`) ganha `~SpecialExpense.parcelas.any()`: o parcelado sai do
  item `"expense"` (a mudança alcança a API e os atrasados, que usam a função; a página Jinja tem cópia própria e não é
  servida em produção).
- `parcela_ops.parcelas_da_planilha_entre(desde, ate)`: parcelas de gasto aprovado, com desembolso, sem
  `paid_at_creation`, com `data` em [desde, ate). `parcela_ops.itens_da_planilha(parcelas, hoje)`: um item por parcela
  no formato de `_build_payment_items` — `type "expense_parcela"`, `id = parcela.id`, `date = parcela.data`,
  `event_title "Gasto: {categoria}"`, `sublabel "{descrição} · Parcela N de M"`, `person_name`/`pix_key` do gasto,
  `amount = parcela.valor`, `status = parcela.payment_status`, `is_future = data > hoje`.
- `api_financeiro_pagamentos` soma os itens das parcelas do mês; `atrasados_ops._do_evento_e_dos_gastos` soma as
  parcelas em aberto dos meses anteriores (o mês de origem é o da data da parcela).
- Set-status: `elif item_type == "expense_parcela"` → `parcela_ops.marcar_situacao(parcela, status, ator)` (grava a
  parcela, rederiva o gasto, auditoria). Lote: `parcela_ids: number[]`; "excluir" pula parcelas, como pula gastos.

### 4. Tela

- **Formulário** (`GastosExtrasPage` + `components/Gastos/ParcelasCampo.tsx` novo): com desembolso reembolso ou
  fornecedor (e categoria que não seja devolução/multa), a caixa "Pagar em parcelas". Ligada: o "Valor (R$)" vira o total
  (somente leitura) e aparecem as linhas data + valor (`MoneyInput`) + "Remover parcela" (até 2 restantes), "Adicionar
  parcela" (até 24) e "Total das parcelas". Ao ligar, nascem duas linhas: a primeira com a "Data do gasto" e o valor
  digitado, a segunda vazia. Parcela paga/no banco: campos desligados, selo da situação, sem remover.
- **Lista** (`GastoItemViews`): bloco "Parcelas" sob a descrição (cartão e tabela): "20/11/2026 · R$ 500,00 · Pago".
- **Planilha** (`lib/financeiro.ts`, `lib/pagamentos.ts`, `PagamentosPage.tsx`): tipo `"expense_parcela"` com o mesmo
  rótulo "Gasto", selecionável, as mesmas opções de situação do gasto; o lote manda `parcela_ids`. Marcar na Planilha
  invalida também `["gastos-extras"]`.

## Estrutura

```text
app/models.py                                      # GastoParcela; SpecialExpense.parcelas
migrations/versions/f353a1b2c3d4_gasto_parcelas.py
app/gastos/parcela_ops.py                          # NOVO
app/gastos/gastos_ops.py                           # create/edit chamam gravar_parcelas
app/api/gastos_read.py · gastos_write.py           # parcelas no gasto (ler e gravar)
app/financeiro/routes.py                           # _pagamentos_gastos_entre exclui parcelado
app/financeiro/atrasados_ops.py                    # parcelas em aberto dos meses anteriores
app/api/financeiro_read.py · financeiro_write.py   # itens, set-status e lote do tipo novo
frontend/apps/internal/src/lib/gastos.ts · financeiro.ts · pagamentos.ts
frontend/apps/internal/src/components/Gastos/ParcelasCampo.tsx (NOVO) · GastoItemViews.tsx
frontend/apps/internal/src/pages/GastosExtrasPage.tsx · PagamentosPage.tsx
```

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify no `manto_352`, não no `manto_local` | o mesmo da 352: `manto_local` compartilhado com as sessões 348–351 e sem a migration da 352 | refazer o `manto_local` apaga o estado das outras sessões |
| Função nova chamada de `app/financeiro/routes.py` (zona do `docs/00` §7) | a Planilha inteira mora ali; a mudança é um filtro a mais em `_pagamentos_gastos_entre`, sem renomear nada | mover a montagem da Planilha para um `_ops` é refatoração fora do pedido |
