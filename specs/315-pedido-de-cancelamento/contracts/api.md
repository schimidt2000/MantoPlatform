# Contratos — Feature 315

Erros no envelope de `json_error` (`docs/00` §5): `{error: {message, fields?, codigo?, …}}`. Códigos novos:
`pedido_pendente`, `sem_pedido` — união própria `CODIGOS_RECUSA_DO_PEDIDO` (`app/constants.py`) e
`CodigoRecusaPedido` (`lib/eventOps.ts`); reusa `cancelado`, `ensaio`, `cache_pago`.

## `POST /api/events/<id>/pedido-cancelamento` (pedir) · alias `POST …/solicitar-exclusao`

RBAC: Comercial ou Superadmin, **papel real** (`_can_request_delete`, `agenda_write.py:185-189`).

Corpo (forma do cancelar da 306):

```json
{"motivo": "texto", "alcance": "todos | so_este_dia",
 "devolucao": {"modo": "tudo | parte | nada", "valor": "600.00", "nome": "…", "pix": "…"},
 "venda_nova": "1800.00"}
```

- `alcance`: só no principal com outro dia vivo (obrigatório lá; enviado fora dele → 400 `fields.alcance`).
- `devolucao`: obrigatória (menos na venda virtual, onde é ignorada); `valor` em Parte; `nome`/`pix` em Tudo e Parte.
- `venda_nova`: obrigatória no pedido de um dia só (satélite, ou principal com `so_este_dia`); proibida fora dele.
- Pelo **alias**: o corpo velho `{motivo}` é aceito sem `devolucao` e sem `alcance` (pedido "sem devolução
  informada"; alcance nulo, lido como "todos").

Ordem das respostas (a da 306: estado antes da forma): 404 → 403 → 409 `cancelado` (trava da 312) → 409 `ensaio` → 409
`cache_pago` do próprio dia (frase da 306) → 400 `fields.{motivo, alcance, devolucao_modo, devolucao_valor,
devolucao_nome, devolucao_pix, venda_nova}` (todos de uma vez) → 409 `cache_pago` dos outros dias que "todos" alcança
(com os dias) → claim → 409 `pedido_pendente` (`message`: "Já existe um pedido de <nome> aguardando o Superadmin").

200: o **detalhe do evento** (`serialize_event_detail`).

## `DELETE /api/events/<id>/pedido-cancelamento` (recusar) · alias `DELETE …/solicitar-exclusao`

RBAC: só Superadmin, **papel real** (`_can_delete`). Todo outro papel, inclusive o autor → 403, nada muda.

Corpo: `{"motivo": "texto opcional"}`. Respostas: 404 → 403 → claim → 409 `sem_pedido` ("Este pedido já foi
decidido"). 200: o detalhe do evento.

## `GET /api/events/<id>` (detalhe) — chaves alteradas

```json
"deletion_request": {
  "requested_at": "…", "alcance": "todos | so_este_dia | null",
  "requested_by": "…", "requested_by_id": 1, "reason": "…",
  "devolucao": {"modo": "parte", "valor": "600.00", "nome": "…", "pix": "…"},
  "venda_nova": "1800.00"
},
"pedido_bloqueado": {"codigo": "ensaio | cache_pago", "frase": "…"},
"escolha_do_alcance": {"dias": 3, "proximo": {"id": 1, "start_at": "…"}}
```

Corte por papel em `data-model.md` (tabela "Leitura da devolução"): para quem não trata do cancelamento o bloco traz
só `requested_at` e `alcance`. `pedido_bloqueado` só quando o evento recusaria o pedido pelo **próprio dia** (ensaio; cachê pago
nele) e o usuário pode pedir — cachê pago só noutro dia não bloqueia o item: "Só este dia" vale, e "Todos os dias"
leva o 409 com os dias. `escolha_do_alcance` só no principal com outro dia vivo: N dias vivos e o dia que receberia a
venda (o critério da passagem da 306, que pula compromisso interno). No satélite cujo principal tem pedido de "todos", `situacao =
exclusao_solicitada` e um bloco `pedido_da_venda: {requested_at, principal_id}` (só leitura; o pedido é do principal).

## `GET /api/events/sumidos-google` (faixa) — chave nova

RBAC: o de hoje (`_ve_faixa_sumidos`: Comercial ou Superadmin, papel efetivo); quem não vê recebe `{pode_ver: false}`
sem tocar no banco. Chave **opcional** nova, ao lado de `total`/`items` (que seguem só do sumiço):

```json
"pedidos": {"total": 1, "items": [{"id": 1350, "title": "…", "start_at": "…"}]}
```

Sem dinheiro, motivo nem autor.

## `GET /api/events/cancelamentos` (fila)

RBAC sem mudança (Superadmin ou Financeiro, papel real). Cada item de `pendentes[]` ganha `alcance` e `devolucao`
(+`venda_nova`), e `requested_by`/`reason`/`devolucao` passam pelo mesmo corte do detalhe (`ver_motivo` e P20).

## Resumo da agenda (mês, dia, busca) e portal

- `situacao = "exclusao_solicitada"` também no satélite cujo principal tem pedido de "todos" (lote, research R6);
  `situacao_desde` = o carimbo do pedido.
- Portal: `em_confirmacao = is_google_missing or has_pending_deletion_request or <pedido da venda>` — sem campo novo.

## `POST /api/events/<id>/cancelar` e `DELETE /api/events/<id>`

Corpos e RBAC sem mudança. Efeitos novos: o cancelamento fecha o pedido de cada dia que encerra e responde ao autor;
a exclusão responde "Evento excluído" ao autor, sem link.

## Sino

`evento.pedido_cancelamento` e `evento.pedido_decidido` (`data-model.md`). Texto e link prontos do servidor; a tela
escolhe só o ícone.
