# Data model — 318

Migration aditiva `<rev>_pix_recebido_por_email.py` (à mão; `down_revision` = head da main no merge). Downgrade
remove tudo; o downgrade de `file_path` só é possível se não houver pagamento sem arquivo (o downgrade apaga antes os
pagamentos `origem='pix_email'` sem arquivo — documentado no docstring).

## `contas_recebimento` (nova) — `ContaRecebimento`

| Coluna | Tipo | Regra |
|---|---|---|
| id | Integer PK | |
| apelido | String(60) NOT NULL UNIQUE | "Inter MEI", "Inter Prime", "InfinitePay Prime", "Cora Monta" |
| titular_tipo | String(10) NOT NULL | `mei` \| `pj` |
| banco | String(30) NOT NULL | `inter` \| `infinitepay` \| `cora` |
| numero_conta | String(30) NULL UNIQUE | como aparece no aviso ("na conta N"); preenchido pelo Superadmin; **nunca semeado** |
| ativa | Boolean NOT NULL default true | |
| created_at | DateTime | |

Semente na migration: as 4 linhas, `numero_conta = NULL`.

## `pix_recebidos` (nova) — `PixRecebido`

| Coluna | Tipo | Regra |
|---|---|---|
| id | Integer PK | |
| origem | String(20) NOT NULL | `email_inter` |
| message_id | String(255) NOT NULL UNIQUE | cabeçalho `Message-ID` — idempotência |
| e2e_id | String(64) NULL UNIQUE | reservado a fontes futuras |
| tipo | String(12) NOT NULL | `pix` \| `devolucao` \| `desconhecido` |
| conta_id | FK contas_recebimento NULL | pelo `numero_conta_lido` |
| numero_conta_lido | String(30) NULL | |
| titular_lido | String(20) NULL | saudação do aviso ("JOAO", "PRIME") — par do repasse antes do cadastro do número |
| valor | Numeric(12,2) NULL | NULL só em `nao_entendido` |
| pagador_nome | String(200) NULL | como veio |
| pagador_norm | String(200) NULL, index | normalizado (R-05) |
| recebido_em | DateTime NOT NULL, index | cabeçalho `Date` em horário de parede SP |
| autenticado | Boolean NOT NULL | DKIM do Inter |
| estado | String(20) NOT NULL, index | ver estados |
| tipo_sugestao | String(25) NULL | `venda` \| `repasse_infinitepay` |
| candidatos | JSON NULL | `[{"event_id", "motivos": [...], "valor_alvo", "pontos"}]` (≤ 3; repasse: grupos de 1–3 vendas) |
| descartados | JSON NOT NULL default `[]` | ids de evento descartados |
| motivo | Text NULL | por que ligou / ignorou ("valor = saldo; nome bate"; "repasse da Prime"; "taxa R$ 50,00") |
| event_payment_id | FK event_payments NULL UNIQUE, ON DELETE SET NULL | pagamento criado ou conciliado (repasse com várias vendas: o primeiro; os demais em `pagamentos_extra`) |
| pagamentos_extra | JSON NOT NULL default `[]` | ids de `event_payments` do repasse multi-venda |
| decidido_por_id | FK users NULL | NULL = sistema |
| decidido_em | DateTime NULL | |
| assunto, remetente | String(200) NULL | só para `nao_entendido` (diagnóstico) |
| created_at | DateTime | |

**Estados** (`PIX_ESTADOS`):

```
novo ─┬─► ligado_auto ──────────────┐
      ├─► para_conferir ─┬─► ligado_confirmado
      │                  ├─► sem_venda (descartou tudo / "não é de venda")
      │                  └─► (desfazer) ◄────────┘ volta a para_conferir
      ├─► sem_venda ──(reavaliado por 7 dias)──► ligado_auto | para_conferir
      ├─► conta_propria (pagador próprio / repasse da Prime)
      ├─► ignorado (devolução; anterior a pix_email_ativo_desde)
      └─► nao_entendido
```

Regras: `ligado_*` ⇔ `event_payment_id IS NOT NULL`; `para_conferir` ⇔ `candidatos` não vazio; `decidido_por_id` só
em `ligado_confirmado`/`sem_venda` por clique/desfazer.

## `event_payments` (existente) — `EventPayment`

| Mudança | Tipo | Regra |
|---|---|---|
| file_path | String(300) **NULL** (era NOT NULL) | NULL só quando `origem='pix_email'` (CHECK `file_path IS NOT NULL OR origem = 'pix_email'`) |
| conta_id | FK contas_recebimento NULL | do PIX ou escolhido no comprovante manual |
| origem | String(20) NOT NULL server_default `'comprovante'` | `comprovante` \| `pix_email` |

A soma do recebido (`comprovantes_por_evento` e cópias) não muda: o pagamento de PIX é um `event_payments` como
qualquer outro.

## `site_settings` (existente) — `SiteSetting`

| Coluna | Tipo | Default |
|---|---|---|
| pix_email_ativo | Boolean NOT NULL | false |
| pix_email_ativo_desde | DateTime NULL | preenchido ao ligar |
| pix_pagadores_proprios | Text NULL | "Prime Dreams\nMonta Producoes" (o nome do sócio o Superadmin acrescenta) |
| pix_email_ultimo_erro | Text NULL | |
| pix_email_ultimo_erro_em | DateTime NULL | |

## `import_state` (existente)

Linha `key='pix_email'` criada na primeira rodada (molde `bounce_ops.claim_sweep`); `last_checked_at` = claim,
`last_import_count` = avisos novos na última rodada.

## `notifications` (existente)

Kinds novos: `pix.para_conferir` (vendedor da 1ª sugestão + FINANCEIRO, SUPERADMIN), `pix.ligado` (vendedor, info),
`pix.repasse_infinitepay` (FINANCEIRO, SUPERADMIN). `dedupe_key = f"pix:{id}:{kind}"`, `entidade = ("pix_recebido",
id)`; resolver marca lidas por entidade.
