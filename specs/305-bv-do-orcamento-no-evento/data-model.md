# Modelo de dados — Feature 305

**Sem migration.** Nenhuma tabela ou coluna nova; uma chave nova, opcional, num JSON que já existe.

## `event_acrescimos` (`EventAcrescimo`, `app/models.py:1841-1875`) — sem mudança de schema

| Coluna | Tipo | Uso nesta feature |
|---|---|---|
| `tipo` | `String(40)` | `"BV"` normalizado (`strip().upper() == "BV"` grava `"BV"`) |
| `descricao` | `String(200)` | a origem: "10% no orçamento #2031", "…, na proporção da venda"; cortada em 200 |
| `is_percent` | bool | B3 grava `false`; à mão, `true` (%) ou `false` (R$) |
| `value` | `Numeric(12,2)` | o número digitado (% arredondado a 2 casas, ou R$); na linha em R$, = `amount_brl` |
| `amount_brl` | `Numeric(12,2)` | o R$ congelado — é o que vai à comissão, à DRE e à Planilha |
| `is_bv` | bool | `tipo == "BV"` |
| `bv_recipient` | `String(200)` | obrigatório em linha BV (B8) |
| `bv_pix` | `String(140)` | obrigatório em linha BV (B8); vazio no corpo = mantém o da linha de mesmo `id` |
| `bv_payment_status` | `String` | `nao_pago` (nasce sempre assim sem `id`) · `pago` · `no_banco` |

Cascata: cai com o evento (`cascade="all, delete-orphan"`, `models.py:360-363`).

### Estados de uma linha BV

```text
nasce:  B3 (criação, vínculo) e editor (linha sem id) ──▶ nao_pago

nao_pago ◀──────────────▶ no_banco ◀──────────────▶ pago
   │      Planilha: Financeiro/Superadmin, qualquer direção (marcar e desmarcar)
   │
   └─ só aqui o valor se move: régua do % ao salvar (R7) e a venda que muda (B10, R9)

no_banco / pago: amount_brl e value congelados (P-20); não saem nem mudam de tipo pelo editor.
Desmarcado de volta a nao_pago, o BV volta a seguir as regras (régua, venda) no próximo evento.
```

- `nao_pago`: o único estado em que o valor se move (régua do %, proporção da venda).
- `pago` / `no_banco`: valor congelado (R$ **e** %); quem recebe e PIX ainda editáveis.
- Linha recebida **sem `id`** no `PUT`: nasce `nao_pago` (exceto a heurística do bundle antigo, R7).

### Invariantes

1. Nenhuma linha BV gravada sem `bv_recipient` e `bv_pix` não vazios (B8) — exceto a linha antiga sem
   PIX (evento 403), que fica até alguém salvar os Acréscimos daquele evento.
2. A linha que nasce do orçamento é em reais (`is_percent=false`), com a origem na `descricao`.
3. `amount_brl` de BV `pago`/`no_banco` nunca muda por conta automática nem pelo editor.
4. Os caminhos automáticos (criação, vínculo) não tocam evento que já tem **qualquer** linha.
5. Depois de qualquer escrita, a coleção `event.acrescimos` em memória é a do banco (flush + expire).

## `orcamento_history` (`OrcamentoHistory`) — chave nova opcional no JSON

`form_snapshot.acrescimos[i]` hoje: `{tipo, descricao, is_percent, value, is_bv}`. Passa a ter, nos
orçamentos salvos depois do deploy:

```json
{ "tipo": "BV", "descricao": "", "is_percent": true, "value": 10, "is_bv": true,
  "valores_brl": [44.0, 100.0, 147.5, 196.0] }
```

- `valores_brl[d-1]` = o que a calculadora somou na duração `d` (1–4h), arredondado HALF_UP; zeros no
  orçamento personalizado. Ausente nos 2.484 orçamentos de antes: a conta inversa cobre (R1).
- Fonte controlada pelo navegador (o `/salvar` grava o snapshot devolvido): a R1 só a aceita finita,
  ≥ 0 e ≤ total da duração.
- `total_1h..total_4h` (`Numeric(10,2)`), `result_snapshot.total_custom` e `form_snapshot.duracao_custom`
  (string) seguem como estão; são os denominadores da proporção.

## `calendar_events` (`CalendarEvent`) — lido, sem coluna nova

`sale_value`, `sale_value_gross`, `with_invoice`, `is_cortesia_permuta`, `orcamento_history_id`,
`cancelled_at`, `is_satellite`/`group_leader_id`, `created_at` (naive UTC; corte do alerta).
`acrescimo_value` (escalar morto) não é tocado.

## `event_logs` (`EventLog`) — frases novas, sem PIX

- "BV do orçamento #N: R$ X (10%, 2h, pelo valor; na proporção da venda de R$ Y), para <quem recebe>"
- "BV acompanhou a venda: de R$ Z para R$ W — venda de R$ X para R$ Y, para <quem recebe>"
- Lido: "Vinculou o orçamento #N (" (corte do alerta). "Reaplicou o orçamento" não conta.

## `commission_payments` — sem mudança

A base (venda − BV; no EducaManto, venda − BV − cachês) já lê `_event_bv_total`. Só a linha `a_pagar`
acompanha (`comissoes_ops.py:975`); o 267c garante que o lote não mexe na paga.
