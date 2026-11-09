# Contratos da API — Feature 339

Envelope de erro de sempre (`json_error`, `docs/00` §5). Todo campo novo do payload é **opcional** no
React (`docs/00` §6 item 21: backend e bundle ficam em versões diferentes por minutos no deploy).

## Novo — `POST /api/notificacoes/<id>/ciente`

- **Gate**: `@api_login_required`; sem papel. Escopo por `current_user.id` (regra da 272, `docs/00` §4).
- **Corpo**: vazio.
- **200**: `{"notificacao": <serializar(n)>}` com `ciente_em` preenchido (e `read_at`, se estava vazio).
  Idempotente: repetir devolve 200 com o mesmo `ciente_em`.
- **404**: id inexistente, de outra pessoa, ou de `kind` fora de `KINDS_COM_CIENTE` — mesma mensagem
  para os três (não confirma existência).
- `serializar` passa a incluir `ciente_em` (null para os outros `kind`).

## Alterado — `GET /api/events/<id>` (e toda escrita que devolve o detalhe)

Chave nova no topo, para **qualquer** usuário que abre o evento (sem gate extra: só traz linhas dele):

```json
"avisos": [
  {
    "id": 9123,
    "kind": "evento.tipo_show",
    "title": "Evento virou SHOW: STORMTROOPERS + DARTH VADER…",
    "body": "13/11 15:00 · Confira a disponibilidade do elenco para o ensaio e revise os cachês.",
    "severity": "urgent",
    "created_at": "2026-11-09T16:26:52",
    "dados": {"entrou": true, "autor": "Thays"}
  }
]
```

`dados` por `kind`: `evento.tipo_show` → `{entrou: bool, autor: str | null}`; `evento.vaga_sobrando`
→ `{personagem: str, pedido: int, vagas: int}`. Derivado no serializer da `dedupe_key`, que carrega
esses valores (`evento.tipo_show:{id}:{entrou|saiu}:{autor_id|0}:{carimbo}`,
`evento.vaga_sobrando:{id}:{nome}:{pedido}:{vagas}`) — nenhuma coluna JSON nova.

Em cada item de `elenco` (`_serialize_role`):

| Campo | Para quem | Tipo |
|---|---|---|
| `sobrando` | todos que veem o elenco | `{"pedido": int, "vagas": int} \| null` |
| `teto_autorizado` | só Superadmin (mesmo corte de `cache_cap`) | `number \| null` |
| `teto_autorizado_por` | só Superadmin | `string \| null` (nome) |
| `teto_autorizado_em` | só Superadmin | `string \| null` (ISO de parede) |
| `cache_cap_efetivo` | como hoje (`show_casting`) | fórmula nova de `teto_ops.teto_efetivo` |

## Alterado — `POST /api/roles/<id>/assign`

Gate de hoje (`_can_edit_event()`; no cancelado, `_can_casting()`). Efeitos novos: teto autorizado
(Superadmin); resolução da sobra (talento tirado de vaga marcada → vaga vazia sai se ainda sobrar).
Resposta: o detalhe do evento, como hoje — sem `warnings`: a remoção pela sobra não muda o título,
então não há Google a avisar.

## Alterado — `POST /api/events/<id>/roles` e `DELETE /api/roles/<id>`

Gates de hoje (`_can_edit_event()` + `trava_do_cancelado`; `_can_casting()`). Efeitos novos: ajuste do
título (FR-027/028), propagação aos ensaios futuros (FR-030), push ao Google depois do commit,
resolução da sobra (`DELETE`). Resposta: detalhe do evento + `warnings: string[]`. Falha do Google →
`warnings: ["Não foi possível atualizar o título no Google Agenda. Corrija o título por lá."]`, status
200 (a vaga foi gravada).

## Alterado — `PATCH /api/events/<id>` e `PATCH /api/events/<id>/basico`

Gate de hoje (`_can_create_event()`: Comercial e Superadmin). Efeitos novos: recálculo de teto e aviso
na troca de tipo com SHOW (só quando a troca é aplicada; 409 `EventTypeChangeBlocked` continua sem
efeito colateral), reconciliação título × vagas (FR-018), propagação aos ensaios. `warnings` ganha a
frase do FR-013 na entrada em SHOW com orçamento ligado: "Os limites de cachê foram recalculados pela
tabela de show. Se houver orçamento do show, vincule-o na aba Comercial."

## Alterado — `PATCH /api/events/<id>/orcamento`

Gate de hoje. Vínculo novo reescreve `cache_cap`/`cache_cap_note` das vagas casadas (FR-025); o
relatório ganha `tetos_reescritos: int`.

## Sem endpoint — `sync_events` (`app/calendar/routes.py:2362`)

Reconciliação título antigo × novo para evento da plataforma e do Google; vaga ocupada nunca é apagada
pelo sync (FR-023); propagação do título aos ensaios futuros quando o título mudou.
