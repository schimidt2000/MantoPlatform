# 327 — O coordenador vê o nome da cliente depois de aceitar

**Branch**: `327-cliente-para-coordenador` · **Created**: 2026-11-03 · **Status**: pronta · **Migration**: nenhuma

## O pedido

O dono (03/11): "Preciso mostrar apenas o nome do contratante para os coordenadores do evento. Após aceitarem eles
têm essa informação lá."

Até aqui o Portal do Artista não mostrava nada da cliente a ninguém: o coordenador chegava ao evento sem saber
quem contratou.

## O que muda

- `portal_ops._cliente_para_o_coordenador`: para cada escalação de **cargo Coordenador** (`role_type="extra"`,
  nome "Coordenador", o mesmo teste de `is_event_coordinator`) com **convite aceito**, o nome da cliente pelo
  `vendas_ops.contratante_name` (vínculo "Contratante" → primeiro vínculo → `client_id` legado). Dia de venda
  agrupada sem cliente próprio usa a cliente do principal (no espelho de 03/11, 1 de 22 dias tem cliente; 19 dos
  principais têm). Os vínculos vêm em lote (uma consulta por relação para a lista inteira), sem N+1.
- `GET /api/portal/agenda`: cada escalação ganha `cliente` (texto ou `null`). Só em `upcoming`; `pending_invites` e
  `history` levam sempre `null`, e `GET /api/portal/historico` também.
- Portal, aba Agenda: o cartão do coordenador ganha a linha **"Cliente: <nome>"** sob a Função. O campo é opcional no
  TypeScript (bundle e servidor sobem em momentos diferentes).

Fica de fora de propósito:
- **Convite pendente** — ainda pode ser recusado; o nome só aparece depois de "Aceitar".
- **Convite nunca enviado** (`invite_status` nulo) — não é aceite. No espelho: 1 cargo futuro de coordenador assim,
  contra 1 aceito; no passado, 3 contra 202.
- **Elenco e outros cargos** (Técnico de Som, Maquiador etc.) — não veem.
- **Telefone, e-mail e documento da cliente** — nunca saem para o portal.
- A regra é por **escalação**: quem coordena e tem personagem pendente no mesmo evento vê o nome só no cartão do
  coordenador.

## Verificação

`verify_327.py` (14 cenários, massa descartável com prefixo próprio): 14/14 com a correção e **9/14 no código antigo**
(caem os cinco em que o nome deve aparecer). `verify_302.py` 22/22 (mesma agenda do portal). Tela aberta no portal
local em 375 px: a linha aparece no cartão do coordenador aceito, não aparece em Convites, e aparece depois de clicar
em "Aceitar"; sem rolagem horizontal, texto de 14 px.

## Fora de escopo

- Mostrar a cliente no Histórico, na ficha de figurino ou no e-mail de convite.
- Contato da cliente (telefone) para o coordenador.
