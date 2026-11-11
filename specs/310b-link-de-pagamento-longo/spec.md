# 310b — O link de pagamento da loja não cabe mais em 500 caracteres

**Branch**: `310b-link-de-pagamento-longo` · **Created**: 2026-11-11 · **Status**: pronto, aguardando
deploy (`verify_310b.py` 12/12) · **Migration**: `f310b2a4c6e8` (`down_revision = d342a7c1e9f3`), só
alarga uma coluna

> Nível 2 com migration, por exceção: a loja do Papai Noel está publicada e a maior parte das reservas
> reais falharia. A migration troca o tipo de uma coluna (`varchar(500)` → `text`, só metadado no
> PostgreSQL); não há dado novo nem regra nova, só um domínio.

## O pedido

No Teste A pela caixa de avisos (11/11/2026, ~02h20), o dono clicou em "Reservar e pagar" na campanha
de teste e nada aconteceu; no segundo clique a página ficou em "Gerando o pagamento…" para sempre. O
dono: "corrija".

## O que estava errado

A InfinitePay cria o link normalmente, mas ele leva a cobrança inteira codificada num parâmetro só
(`lenc`): cresce com o título da campanha, o e-mail, o telefone e o segredo do endereço de aviso. O da
campanha de teste ("Teste interno — não comprar") veio com **513** caracteres; o
`virtual_orders.payment_url` era `varchar(500)`. O `commit` falhava (`StringDataRightTruncation`), a
reserva respondia 500 e o pedido ficava `reservado` sem link. Medido em produção com o contato do dono:
o link do **Papai Noel** dá **504** — a maior parte das famílias cairia no mesmo erro.

No Teste A de 20/10 o segredo do aviso e o título eram outros e o link coube.

## O que muda

- `VirtualOrder.payment_url`: `db.Text` (`app/models.py`), com o porquê.
- Migration `f310b2a4c6e8_link_de_pagamento_longo.py`: `ALTER COLUMN payment_url TYPE text`; o
  `downgrade` volta a `varchar(500)` anulando os links mais longos.

## Verificação

`verify_310b.py` contra o `manto_310b` (dump de produção de 11/11 02h, porque o `manto_local` está no
CRM 334), InfinitePay por dublê que devolve um link do tamanho pedido, conferência por conexão separada:
link de 513 e de 2.000 → 201, pedido `aguardando` com o link inteiro; link curto continua; a página do
pedido devolve o link inteiro; a coluna é `text`. **Antes da migration**: 4 FALHA pelo motivo certo
(`valor é muito longo para tipo character varying(500)`). Depois: 12/12. `flask db downgrade` e
`upgrade` ensaiados no mesmo banco. Regressão: `verify_310.py` e `verify_340.py` no `manto_310b`.

Produção, depois do deploy: uma reserva no Papai Noel pela página pública chega ao checkout (e é
abandonada sem pagar).

## Fora de escopo

Registrados no `docs/05` (208–209): o pedido que fica `reservado` sem link quando o erro é nosso e não
da operadora (sem botão de desistir na página), e o código por SMS da InfinitePay que vai para o
telefone digitado na ficha — um número errado prende a família.
