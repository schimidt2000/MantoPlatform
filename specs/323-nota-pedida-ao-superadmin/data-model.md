# Modelo de dados — 323

Migration à mão, **aditiva**, `down_revision = "c322a7e1b9d4"` (head da `origin/main` em 28/10).
Sem backfill: o legado fica com tudo nulo (nota sem "pedida por" nunca dispara aviso; o painel mostra
o vendedor da venda).

## `calendar_events` — os dados da nota (da venda)

| Coluna | Tipo | Regra |
|---|---|---|
| `nota_tomador_doc` | `String(14)`, nulo | só dígitos; 14 (CNPJ) ou 11 (CPF). Vazio → vale o do cliente contratante |
| `nota_iss_retido` | `Boolean`, nulo | nulo = não |
| `nota_municipio` | `String(120)`, nulo | obrigatório quando `nota_iss_retido`; apagado quando não |
| `nota_referencia` | `String(120)`, nulo | AF, pedido de compra |
| `nota_observacoes` | `Text`, nulo | até 1.000 caracteres; vai ao fim da discriminação |

Só se gravam quando o corpo traz a chave `nota` (bundle antigo não apaga nada). Desligar o chip não
apaga os dados — religar recupera o que o cliente pediu.

## `event_invoices` — o pedido de cada nota

| Coluna | Tipo | Regra |
|---|---|---|
| `pedida_por_id` | `Integer`, FK `users.id` `ON DELETE SET NULL`, nulo | quem ligou o chip |
| `pedida_em` | `DateTime`, nulo | `now_sp()` |
| `aviso_enviado_em` | `DateTime`, nulo | `now_sp()`; reivindicado por `UPDATE … WHERE aviso_enviado_em IS NULL` |

## Transições

```
chip desligado ──liga (sem nenhuma nota)──▶ nota a_emitir (pedida_por, pedida_em)
                                              │ commit da venda
                                              ▼
                                   aviso reivindicado → e-mail aos Superadmins
                                              │ Superadmin insere o PDF (PATCH …/invoices/<id>)
                                              ▼
                                         nota emitida (sai do painel)
chip ligado ──desliga──▶ notas a_emitir excluídas; emitidas ficam
```

- Venda que já tem qualquer nota não ganha outra ao religar/salvar.
- Cancelado e satélite: `acompanhar_pedido` não faz nada.

## Cliente (`clients`) — sem coluna nova

Documento digitado de 14 dígitos completa `clients.cnpj` se vazio; de 11, `clients.cpf` se vazio.
Nunca sobrescreve. O cliente é o contratante (`EventClient.relationship_type == "Contratante"`;
sem ele, `CalendarEvent.client_id`).

## Valores derivados (não gravados)

- **Tomador**: nome (`company` ou `name` do cliente), documento (`nota_tomador_doc` ou do cliente),
  e-mail, endereço — no painel e no e-mail.
- **Vencimento**: `payment_due_date`; senão primeira `EventInstallment.due_date` ≥ hoje (SP).
- **Discriminação**: research R6.
