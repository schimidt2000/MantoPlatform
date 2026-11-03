# 331 — O que ficou em aberto vem para o mês atual da Planilha de Pagamentos

**Branch**: `331-atrasados-na-planilha` · **Created**: 2026-11-03 · **Status**: Entregue na branch
(`verify_331.py` 10/10), aguardando o merge a pedido do dono · **Migration**: nenhuma

## O pedido

O dono (03/11): a Planilha de Pagamentos funciona por mês, mas o evento do dia 30 só se paga no mês
seguinte, e há coisas atrasadas de meses para trás — "no mês 8 tem pendente um pagamento para o
Roberto Mantovani". Quando o mês vira, o que está pendente deve passar para o mês seguinte, ainda
pendente, com aviso e mantendo o dia certo, para o Superadmin e o Financeiro não precisarem voltar
todos os meses para conferir. E hoje há itens "No banco" de outubro e de novembro, e a soma do que
está no banco fica espalhada em dois meses.

Análise apresentada e aprovada na mesma conversa ("Sim, pode fazer"), com os dois padrões propostos:
o atraso conta a partir da planilha de maio/2026 e a data de pagamento fica de fora.

## O que muda

- **Só a tela traz o item; o banco não muda.** A DRE soma cada custo pela data de origem: cachê e BV
  pelo evento, salário pelo `month_ref` (`_salary_cost`), gasto pela `expense_date`. Mover a data
  levaria o custo de um mês para outro. E o salário "não pago" de um mês é apagado e regerado quando o
  mês é aberto (`_ensure_salary_payments`), por isso o atraso nunca chama os `ensure_*` dos meses
  passados: só lê o que existe.
- **`GET /api/financeiro/pagamentos` do mês atual** (o mês de hoje em São Paulo) soma aos itens do mês
  tudo que está **Não pago** ou **No banco** nas planilhas de meses anteriores, desde a de **maio/2026**
  (`PLANILHA_ATRASADOS_DESDE`, `app/constants.py`). Os seis tipos entram: cachê, salário, gasto, BV,
  comissão e conta recorrente. Cada item mantém id, data, valor e situação de sempre, e ganha
  `de_mes_anterior: true` e `dias_em_atraso` (dias desde a data do item; nunca negativo). O payload
  ganha `totals.anteriores`, `mes_atual` e `atrasados_desde`. Meses passados e futuros não mudam.
- **Pertence ao mês anterior o que aparece na planilha de um mês anterior**: cachê e BV pelo mês do
  evento, salário e conta recorrente pelo `month_ref`, gasto pela `expense_date`, comissão pelo mês do
  repasse (o ciclo de outubro é o item de 05/11). Os montadores de item são os da própria planilha
  (`_build_*` em `app/financeiro/routes.py`), e os filtros de cachê e de gasto saem de uma função só,
  usada pelo mês e pelo atraso. Assim o item que vem de outubro é o mesmo item de outubro.
- **Marcar pago no mês atual já funciona**: situação e lote gravam pelo id do item, não pelo mês. A
  comissão leva o ciclo no id (`vendedor:2026-09`) e quita o ciclo certo (lição da 267).
- **CSV do mês atual** (cachês) inclui os cachês em aberto de meses anteriores, com a data original na
  coluna "Data". As colunas não mudam.
- **Tela**: no mês atual, cartão-filtro "De meses anteriores" (quantidade e valor), e cada item vindo
  de antes leva a etiqueta "De outubro · há 14 dias". Os cartões Pendentes e No banco já somam esses
  itens, então "No banco" mostra tudo que está no banco hoje. Num mês passado com item em aberto, uma
  linha avisa que ele também está na planilha do mês atual, com o atalho para ela.
- **Fica antes do corte** (não vem para o mês atual): salários "não pagos" de janeiro e abril/2026 e
  comissões da Thays de dez/2025 a mar/2026, gerados antes de a planilha entrar em uso. O dono confere
  esses itens uma vez, na planilha do mês deles.

## Verificação

`verify_331.py` contra o `manto_local`, com o relógio de hoje em São Paulo (rodado em 03/11/2026, com o
espelho de 30/10). Resultado: **10/10** (4/10 antes do núcleo, pelos motivos certos). No espelho, novembro
traz 126 itens de antes, R$ 134.390,09.

1. No mês atual, todo item com `de_mes_anterior` é de planilha anterior desde maio/2026, está Não pago
   ou No banco, e tem `dias_em_atraso` coerente com a data.
2. Cada item que vem de antes é o mesmo item da planilha do mês dele (mesmo id, data, valor e
   situação), e todo item em aberto e vencido das planilhas de maio a outubro aparece no mês atual.
3. Nada de antes de maio/2026 vem para o mês atual (salários de janeiro e abril, comissões de março).
4. Mês passado e mês futuro não recebem item de antes (`totals.anteriores` = 0).
5. `totals` do mês atual somam os itens que vêm de antes, e `totals.anteriores` bate com eles.
6. Marcar pago um cachê de outubro pela tela de novembro grava (conferido por conexão separada) e
   tira o item de novembro; outubro passa a mostrá-lo pago. Desfeito no `finally`.
7. O CSV de novembro traz o cachê de outubro em aberto; o de outubro não muda.
8. A DRE de outubro (`GET /api/financeiro/dashboard`) sai idêntica antes e depois de abrir novembro.
9. Cenário que deve falhar: papel COMERCIAL recebe 403 na planilha.

## Fora de escopo

- **Data de pagamento** em cachê, gasto e BV (para o cartão "Pagos" de novembro contar o que saiu do
  caixa em novembro): pede migration em três tabelas; fica para uma feature se o dono pedir.
- A tela Jinja da planilha (`/financeiro/pagamentos`) não muda (`docs/PARADA_REMOCAO_JINJA.md`).
- Conferir e baixar os itens antigos (antes de maio/2026): é decisão do dono, item a item.
- O lote continua sem BV e conta recorrente (já era assim).
