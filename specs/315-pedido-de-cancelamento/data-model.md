# Modelo de dados — Feature 315

## `calendar_events` — o pedido continua no evento

Migration **aditiva**, escrita à mão: `migrations/versions/<rev>_solicitacao_de_cancelamento.py`, `down_revision =
"c5d2f7a9e306"` (head da 306; nada depois — reconferência §A.5). Duas colunas nulas ao lado das três da 224
(`models.py:304-306`):

| Coluna | Tipo | Valores | Nula quando |
|---|---|---|---|
| `deletion_requested_at` (224) | `DateTime` | carimbo do pedido, horário de SP (naive, como hoje) | sem pedido |
| `deletion_requested_by_id` (224) | FK `users.id` | quem pediu | sem pedido; autor apagado |
| `deletion_request_reason` (224) | `Text` | o motivo | sem pedido |
| **`deletion_request_scope`** (nova) | `String(16)` | `todos` \| `so_este_dia` (`ALCANCE_*`, `constants.py:481-482`) | sem pedido; pedido de antes do deploy |
| **`deletion_request_refund`** (nova) | `Text` (JSON) | `{"devolucao": {"modo", "valor", "nome", "pix"}, "venda_nova"}` — valores em texto decimal | sem pedido; venda virtual; pedido de antes do deploy; pelo caminho velho |

`downgrade` = `drop_column` das duas (perde alcance e devolução de pedidos pendentes, nunca dinheiro). Sem backfill:
o pedido pendente de hoje (1350) fica com as duas nulas ("sem devolução informada"). Sem script no Shell do Render.

### Ciclo de vida

```text
sem pedido ──pedir (claim)──▶ pendente ──recusar (claim)──────────▶ sem pedido   (resposta "recusado")
                                 │      ──cancelar (fecho, R2)─────▶ cancelado   (resposta "cancelado"/"dia")
                                 │      ──excluir (vazio)──────────▶ (linha some) (resposta "excluído", sem link)
                                 └──────devolver ao Google: não muda o pedido
```

Saídas que gravam zeram as **cinco** colunas; a exclusão as leva junto com a linha. Só o Superadmin fecha (Q5 = D).

### Propriedades

- `has_pending_deletion_request` (`models.py:414-416`) e `situacao` (`:430-442`, valor `exclusao_solicitada` mantido
  como contrato — só o rótulo da tela muda) **não mudam**: leem só o próprio evento.
- A herança do satélite (pedido de "todos" no principal) é calculada em lote por quem serializa (research R6), nunca
  na propriedade.

## Leitura da devolução (por papel, research R8)

| Campo | Comercial | Financeiro | Superadmin | Autor do pedido | Demais papéis internos |
|---|---|---|---|---|---|
| `requested_at`, `alcance` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `requested_by`, `requested_by_id`, `reason` | ✓ | ✓ | ✓ | ✓ | — |
| `devolucao.modo`, `devolucao.valor`, `venda_nova` | ✓ | ✓ | ✓ | ✓ | — |
| `devolucao.nome`, `devolucao.pix` | — (só o autor) | ✓ | ✓ | ✓ (sem "Ver como") | — |

Pelo papel **em uso** (o "Ver como" vale); o autor é comparado pelo id do usuário e só conta sem "Ver como" — o
Superadmin autor em "Ver como Casting" não lê nome nem PIX (nome/PIX exigem também `show_comercial`). O **histórico do evento** (o
`EventLog` com o motivo) continua só do Superadmin, como hoje (`agenda_read.py:900-901`). Em **Nada**, o JSON não
guarda nome nem PIX.

## `notifications` — dois kinds

| kind | destinatários | severidade | chave (dedupe) | entidade / link |
|---|---|---|---|---|
| `evento.pedido_cancelamento` | SUPERADMIN ativos | `urgent` se o evento é em ≤ 7 dias ou já passou, senão `info` | `evento.pedido_cancelamento:<event_id>:<carimbo>` | `calendar_event` / `/events/<id>` |
| `evento.pedido_decidido` | só o autor (explícito) | `info` | `evento.pedido_decidido:<event_id>:<decisão>:<carimbo>` | idem; **sem** no "excluído" |

Na decisão, os `evento.pedido_cancelamento` do evento são marcados lidos (não apagados); na exclusão,
`apagar_por_entidade` já os apaga.

## Histórico e auditoria

- `EventLog`: "Pediu o cancelamento (<alcance>): <motivo> — devolução combinada: <modo> <valor>" e "Recusou o pedido de
  cancelamento: <motivo>" — sem `created_at` explícito (vale o default UTC do modelo; quita a parte da 224 da dívida
  76). Nome e PIX nunca entram.
- `AuditLog` por `_log_sync`: `cancel_requested`, `cancel_request_refused` (o fecho no cancelamento já tem o
  `event_cancelled` da 306).
