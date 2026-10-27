# Pesquisa — Feature 314

Decisões tomadas no plano, com a razão e o que se descartou. Fonte: leitura do HEAD `3fbada6f` (main e60aae53
mesclada) em 27/10/2026 e o mapa da tela feito em 21/10.

## D1. Onde mora a regra da situação

- **Decisão**: no núcleo, `gastos_ops.situacao_do_gasto(expense) -> str`, serializada como `situacao` em cada gasto
  do `GET /api/gastos`.
- **Razão**: a regra "o que vai à Planilha de Pagamentos" já é do backend (`api_financeiro_pagamentos`,
  `app/api/financeiro_read.py`: aprovado, com desembolso, sem `paid_at_creation`), e a situação "pago" depende dela
  (o aprovado que nunca vai à planilha nunca vira "pago" lá). Calcular no React duplicaria a regra num segundo
  lugar (Princípio I) e deixaria o verify sem o que provar. No servidor ela é uma função pura, testável contra o
  banco.
- **Descartado**: derivar no React a partir de `status`/`payment_status`/`paid_at_creation`/`disbursement_type`. Os
  campos já chegam e não haveria mudança de backend. Mas seria a regra da planilha num segundo lugar, livre para
  divergir na próxima mudança dela.
- **Ponte de deploy**: `situacao?` é opcional no tipo TS (armadilha 21). Sem a chave (backend antigo por alguns
  minutos), o gasto é tratado como pede-ação e fica na lista principal, com o selo antigo. Nunca some num grupo
  recolhido.

## D2. A regra

Ordem de decisão, a primeira que casa vence:

1. `status == "rejeitado"` → `rejeitado`
2. `status == "pendente"` → `aguardando_aprovacao` (mesmo com `paid_at_creation`: ainda não foi aprovado)
3. aprovado e (`paid_at_creation` **ou** `disbursement_type` vazio **ou** `payment_status == "pago"`) → `pago`
4. aprovado e `payment_status == "no_banco"` → `no_banco`
5. aprovado → `a_pagar`

Os casos 3a e 3b são as respostas do dono de 27/10: o aprovado sem desembolso e o pago no cadastro contam como
resolvidos. Um `payment_status` desconhecido cai em `a_pagar`, que fica à vista. É o erro do lado seguro: mostra
demais, nunca esconde.

## D3. Cartões e totais: na tela, não no servidor

- **Decisão**: os cartões-filtro somam a lista que já chegou, depois dos filtros de busca, categoria, desembolso e
  mês. O `totals` do servidor continua no payload, sem uso nesta tela.
- **Razão**: FR-009 pede números do recorte filtrado, e o recorte é feito na tela. Totais do servidor seriam um
  segundo número que discorda do primeiro assim que alguém digita na busca. Para o não gestor, a lista já é só a
  dele, então os números também são (FR-015).
- **Descartado**: estender `expense_totals` por situação. Não serve ao recorte e duplicaria a soma.
- **`totals` fica**: tirá-lo mudaria um contrato sem ganho. A remoção vira candidata a dívida no `docs/05`.

## D4. Grupos recolhidos

- **Decisão**: `AccordionRow` do `@manto/ui` (feature 187), um por grupo, fechado por padrão.
- **Razão**: já tem `aria-expanded`/`aria-controls`, altura animada com `useReducedMotion` e estado próprio. O estado
  sobrevive à revalidação da query porque o componente não desmonta (chave estável), o que cumpre FR-014.
- **Descartado**: `GrupoDeLinhas` da Home (298). Ele é "mostrar as N primeiras + Mostrar todas", não abre e fecha um
  bloco inteiro. Também se descartou um componente novo.

## D5. Cartão-filtro compartilhado

- **Decisão**: extrair o `TotalCard` de `PagamentosPage.tsx` para `components/CartaoFiltro.tsx`. O tom passa a vir
  por prop (`tone: BucketTone | null`) em vez de por `bucket`, e a unidade da contagem também vira prop ("item/itens"
  em Pagamentos, "gasto/gastos" aqui).
- **Razão**: Princípio I. O dono pediu "como em Pagamentos", e uma cópia do cartão divergiria na primeira correção.
- **Risco**: mexe numa tela que funciona. A troca é mecânica (mesmas classes, mesmo `aria-pressed`) e Pagamentos
  entra na conferência de tela.

## D6. Busca

- **Decisão**: `normalizeSearch`, `searchTerms` e `matchesSearch` de `lib/pagamentos.ts`, importados. O índice do
  gasto (`searchIndexOfGasto`, em `lib/gastos.ts`) reúne data (dd/mm/aaaa e ISO), descrição, observação, categoria,
  quem recebe, PIX, evento, autor, rótulo da situação e o valor formatado e cru (`rawAmount`, também de lá).
- **Razão**: é a busca que a equipe já usa em Pagamentos: sem acento, várias palavras somadas (E).
- **Descartado**: mover as funções para um `lib/busca.ts` neutro. Seria refatoração lateral sem pedido. Importar
  de `lib/pagamentos` é reuso.

## D7. Mês

- **Decisão**: abre sem mês (Clarifications). O mês é filtro opcional: ‹ › + `Input type="month"`, e "Todos os
  meses" limpa. As setas sem mês escolhido partem do mês corrente. Recorte por `expense_date.slice(0, 7)`
  (data pura, sem `Date`: armadilha 1).
- **Razão**: um pendente de setembro não pode sumir porque a tela abriu em outubro.

## D8. Largura e tabela

- **Decisão**: raiz sem `max-w`. Tabela `table-fixed` de 7 colunas a partir de `xl`, cartões abaixo (plan.md, "O
  desenho da tela").
- **Razão**: as 10 colunas de hoje com `whitespace-nowrap` em Ações exigiam `min-w-[960px]` dentro de 1152 px, e a
  rolagem ficava no rodapé de 186 linhas. Categoria e autor viram linhas da coluna Gasto, e a nota fiscal vira ação.
  Sem mudar nada, cabem 7 colunas.
- **Descartado**: `max-w-[1600px]` (vazio nos monitores largos que o dono usa); menu "Mais ações" (Radix, esconde o
  que hoje está à vista e é chato de conferir no Browser pane); manter 10 colunas com rolagem (é o defeito).

## D9. O que fica igual

O `window.prompt` (motivo da rejeição) fica: é dívida de tela, não pedido, e vira candidato no `docs/05`. O
`window.confirm` da exclusão **sai**: a ação é reescrita nesta feature, e o Princípio V exige `ConfirmDialog` para
ação destrutiva (achado C1 do `/speckit-analyze`, 27/10). O formulário de criar/editar não muda.
