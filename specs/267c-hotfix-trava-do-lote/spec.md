# Hotfix 267c — comissão paga volta a "a pagar" com o valor cheio

**Branch**: `267c-hotfix-trava-do-lote` · **Created**: 2026-10-14 · **Status**: Pronto · **Migration**: nenhuma

## O pedido

O dono descreveu: "a gente paga, marca como pago, ele muda e depois ele volta para o banco o valor
total, sendo que parte já foi paga". O plano 1e (`docs/backlog/1e-comissao-acompanha-a-venda.md`,
seção 2) achou a causa; a 1e-Q5 = A (lida) decidiu quem desfaz. Liberado em 14/10/2026 ("começar a
produzir"); noite 1 do backlog, depois do 215b.

A Planilha soma, por vendedor e ciclo, as comissões `a_pagar`, `no_banco` **e** `pago` num item só,
com status "não pago" quando há mistura. O seletor do item chama `liquidar_periodo`, que regravava
**todas** as linhas do ciclo — inclusive as pagas. O "Não pago" de um item misto devolvia a "a pagar"
o que já tinha saído, a ressincronização (`_resync_pending_commissions`) recalculava a linha pela
venda de hoje, e o vendedor aparecia devendo o valor cheio; o "Pago" recarimbava a data das pagas.
No espelho, o item de maio dizia R$ 2.133,88 "Não pago" com R$ 1.996,38 já pagos.

## O que muda

- `liquidar_periodo(..., linhas="abertas")`: o lote mexe só em `a_pagar`/`no_banco`, com
  `with_for_update`. `linhas="pagas"` é só o desfazer.
- `liquidar_item_de_comissao()` — as quatro portas (API e Jinja, individual e em massa) passam por
  ela. Item aberto: lote. Item `…:pago`: "Pago" não faz nada; "No banco" → 409; "Não pago" → só o
  Superadmin (403), com motivo (400), que vai ao histórico de cada evento. Em massa e no Jinja não há
  motivo, então o pago nunca sai por lá.
- `_build_commission_items` parte o item: `<vendedor>:<AAAA-MM>` (o que falta) e
  `<vendedor>:<AAAA-MM>:pago` ("— pago").
- Tela antiga de Comissões (`/financeiro/comissoes/set-status`, por linha): não tira de `pago`.
- Planilha React: o item pago mostra "Pago" sem seletor; o Superadmin tem o seletor sem "No banco" e
  o "Não pago" pede o motivo; a mensagem do servidor aparece no erro.

## Verificação

`verify_267c.py` contra o `manto_local`: 10/10 com o conserto; 3/10 sem ele (o defeito reproduzido:
a paga voltou a "a pagar", a data dela foi recarimbada, o Jinja a tirou de pago). Regressão:
`verify_267` 9/9, `verify_267b` 8/8, `verify_215b` 9/9. Typecheck e ruff limpos nos arquivos novos
(`financeiro/routes.py` já tinha o aviso de ordem de import, anterior).

## Fora de escopo (fica na 1e, precisa de coluna)

O valor pago gravado e travado, quem pagou e o lote, a guarda no modelo, a tela de Comissões com
Pago × No banco × A pagar por evento, e o "Desfazer pagamento" com o valor registrado. O desfazer
deste hotfix devolve a linha a "a pagar", que volta a acompanhar a venda — é o certo para pagamento
marcado por engano.
