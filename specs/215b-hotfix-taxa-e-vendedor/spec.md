# Hotfix 215b — a Comercial muda a taxa e troca o vendedor de qualquer evento na tela nova

**Branch**: `215b-hotfix-taxa-e-vendedor` · **Created**: 2026-10-14 · **Status**: Pronto · **Migration**: nenhuma

## O pedido

Achado pelo plano 1e (`docs/backlog/1e-comissao-acompanha-a-venda.md`, seção 2) e liberado pelo dono
em 14/10/2026 ("começar a produzir"). Ordem: noite 1 do backlog (`docs/backlog/ENCAVALAMENTO.md`).

A tela antiga (`calendar/routes.py`, `_handle_update_comercial`) tinha a regra: a **taxa** de comissão
do evento só o Superadmin altera; o **vendedor**, Financeiro e Superadmin trocam, e a Comercial só
preenche quando está vazio. A tela nova (feature 215) perdeu as duas: `PATCH /api/events/<id>/comercial`
gravava `commission_rate` e `seller_id` de quem passasse no gate de criar evento (Comercial ou
Superadmin), e `PATCH /api/events/<id>` (edição completa) gravava `seller_id`. A comissão a pagar
acompanhava (`_sync_commission_payment`), e a taxa não deixava rastro no histórico.

Reproduzido no `manto_local` antes do conserto: a Comercial mudou a taxa para 9% e trocou o vendedor
pelas duas portas, com 200 (`verify_215b.py`, cenários 2, 4 e 5 vermelhos).

## O que muda

- `event_ops.taxa_e_vendedor_negados()` — a regra, num lugar só: compara o pedido com o que está
  gravado (o formulário manda o corpo inteiro, inclusive os campos travados; o valor de sempre passa;
  `7` × `7.0` é a mesma taxa).
- `agenda_write.py`: `/comercial` e a edição completa respondem **403** com `fields` nomeando o campo
  negado. Na edição completa de satélite não há checagem (a venda não é gravada ali).
- `agenda_read.py`: o detalhe ganha `venda.pode_mudar_taxa` e `venda.pode_trocar_vendedor`.
- Aba Comercial: taxa e vendedor travados com a frase do motivo. Edição completa: vendedor travado
  aparece como texto (sem `register`, para o valor gravado seguir no envio).

## Verificação

`verify_215b.py` contra o `manto_local`: 9/9 com o conserto; 4/9 sem ele (prova de que os cenários
"deve falhar" pegam o defeito). Typecheck e ruff limpos.

## Fora de escopo

- O Financeiro continua sem acesso ao `/comercial` e à edição completa (gate de criar evento, anterior
  a este hotfix): na tela nova ele ainda não troca vendedor. Se o dono quiser, é outro pedido.
- O histórico da taxa e a taxa pela data de venda são da 1e.
- Comissões já mexidas pelo defeito não são revistas aqui (o plano 1e trata o passado).
