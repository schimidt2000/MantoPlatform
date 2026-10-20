# Modelo de dados — 310

Migration **aditiva**, escrita à mão, `down_revision = 'a7c3e91f4d28'` (head da `main` em `98192e8`).
**Atenção ao merge**: a 306 (`C:\tmp\mp306`) e a 309 (`C:\tmp\mp309`) também penduram migration nesse
head; quem mergear por último ajusta o `down_revision` para a cabeça vigente (sem `flask db merge`
automático — o `startCommand` roda `flask db upgrade` e duas cabeças derrubam o deploy).

Nenhuma coluna é removida ou renomeada; todas têm default ou aceitam nulo → sem ensaio destrutivo,
mas o `upgrade`/`downgrade` roda no `manto_local` e num banco descartável com dump fresco antes do
merge (constituição, Operação e Deploy).

## Colunas novas

### `site_settings`

| coluna | tipo | default | para quê |
|---|---|---|---|
| `virtuais_pagamento_ativo` | bool not null | `false` | interruptor (R6) |
| `infinitepay_webhook_token_anterior` | varchar(64) null | — | segredo antigo aceito por 24 h depois de regerar (R7) |
| `infinitepay_webhook_token_anterior_ate` | timestamp null | — | até quando o antigo vale |

### `virtual_orders`

| coluna | tipo | para quê |
|---|---|---|
| `payment_link_error` | varchar(200) null | código/motivo da recusa da operadora ao criar o link (R4/FR-026) |
| `receipt_url` | varchar(500) null | comprovante da operadora (FR-033) |
| `unverified_reason` | varchar(24) null | `nao_sei` quando liberado sem prova por indisponibilidade (R10) |
| `conferido_em` | timestamp null | "a conferir" resolvido |
| `conferido_por` | varchar(120) null | quem resolveu |

`expired_unverified` (existente) continua; `unverified_reason` distingue indisponibilidade de abandono.

### `virtual_payment_notifications`

| coluna | tipo | para quê |
|---|---|---|
| `state` | varchar(12) not null default `'pendente'` | `pendente` → `processando` → `decidido` |
| `attempts` | int not null default 0 | tentativas de processamento (política 0/1/2 min, depois a cada 10 min até 48 h) |
| `last_attempt_at` | timestamp null | |
| `resolvido_em` | timestamp null | "a conferir" resolvido |
| `resolvido_por` | varchar(120) null | |

`transaction_nsu` segue `UNIQUE` e passa a ficar **nulo** para aviso sem token (R2). Linhas antigas:
`state='decidido'` quando `outcome` não é nulo (backfill na própria migration, um `UPDATE`).

### `virtual_campaigns`

| coluna | tipo | default | para quê |
|---|---|---|---|
| `listada` | bool not null | `true` | aparece na vitrine (R14) |

## Constantes novas (`app/constants.py`)

- `VIRTUAL_ANTECEDENCIA_RESERVA_HORAS = 2`, `VIRTUAL_MIN_MINUTOS_NO_PAGAMENTO = 30`
- `VIRTUAL_SALA_ALERTA_HORAS = 6`, `VIRTUAL_SALA_RETRY_LONGO_MIN = 10`,
  `VIRTUAL_AVISO_REPROCESSA_HORAS = 48`
- Motivos de devolução: `pagamento_em_dobro`, `pagamento_sem_pedido_ativo`, `horario_passou`,
  `sem_vaga_de_video`, `desistencia` (+ rótulos em `VIRTUAL_REFUND_REASON_LABELS`)
- Desfechos do aviso: `efetivado`, `devolucao_aberta`, `conflito`, `duplicado`, `divergente`,
  `orfao`, `retido`, `pendente_prova` (finais: os seis primeiros)
- `KIND_VIRTUAL_ATENCAO = "virtual.atencao"` em `notificacoes_ops` (COMERCIAL, SUPERADMIN)

## Máquina de estados do pedido (vai para `docs/04`)

```text
reservado ──link ok──▶ aguardando ──decidir_pagamento: paga+confere+horário ok──▶ pago
   │                       │                     └─ horário tomado / passou / sem vaga ─▶ cancelado (+devolução)
   │ link recusado         │ trava venceu, reconsulta nao_encontrado/nao_pago ─▶ expirado
   ▼                       │ trava venceu, nao_sei esgotado ─▶ expirado (unverified_reason=nao_sei → a conferir)
expirado ◀─────────────────┘
expirado ──pagamento atrasado provado──▶ decidir_pagamento (mesma regra: pago OU cancelado+devolução)
pago ──cancelar (equipe)──▶ cancelado (+devolução "desistencia")
pago ──segunda cobrança provada──▶ pago (+devolução "pagamento_em_dobro")
cancelado ──pagamento provado──▶ cancelado (+devolução "pagamento_sem_pedido_ativo")
```

Invariantes (o verify confere todas):

1. No máximo **um** pedido `pago` por `slot_id`.
2. Horário `vendido` ⇒ `order_id` aponta para o pedido `pago` dele.
3. Pedido `pago` nunca muda para `expirado`.
4. Todo pagamento provado termina em `pago` ou numa `VirtualRefundRequest`.
5. `recorded_sold <= recorded_capacity`.
6. Ordem de travas: pedido → horário → campanha.
