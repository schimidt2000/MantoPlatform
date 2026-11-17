# Modelo de dados — Feature 351

Migration à mão `a351b0c1d2e3_painel_atribuido.py`, `down_revision = "d334b2c4e6f8"` (head da `main` em 17/11).
Toda mudança é **aditiva** (colunas anuláveis, tabela nova). O `downgrade` remove o que criou. A 348, a 349 e a 350
encadeiam na mesma head: o reencadeamento é da sessão principal no lote de merge.

## `marketing_frentes` (existe — feature 345)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `meta_vendas_mes` | `Integer`, nulo | ≥ 0; nulo = sem meta |
| `verba_mes` | `Numeric(12,2)`, nulo | ≥ 0; nulo = sem verba definida |

## `marketing_calendario` (nova)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | `Integer` PK | |
| `frente` | `String(16)`, FK `marketing_frentes.slug` ON DELETE CASCADE | uma das 5 frentes |
| `mes` | `SmallInteger` | CHECK 1–12 |
| `meta_vendas` | `Integer`, nulo | vence `meta_vendas_mes` da frente naquele mês |
| `verba` | `Numeric(12,2)`, nulo | vence `verba_mes` da frente naquele mês |
| `foco` | `Text`, nulo | o que vender/prospectar no mês |
| `updated_by_id` | FK `users.id` SET NULL, nulo | |
| `updated_at` | `DateTime`, nulo | UTC |

`UNIQUE(frente, mes)` (`uq_marketing_calendario_frente_mes`). As 60 linhas nascem na migration, com o `foco` do
calendário de 12 meses da pesquisa de 17/11 (§4.6) e números vazios.

Valor efetivo do mês: `calendario.meta_vendas ?? frente.meta_vendas_mes` (idem verba).

## `marketing_posts` (existe — features 204/345)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `conceito` | `String(120)`, nulo | texto curto, aparado; vazio vira nulo |

## `marketing_propostas` (existe — feature 345)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `frente` | `String(16)`, nulo | uma das 5 frentes ou nulo |
| `valor_antes_num` | `Numeric(12,2)`, nulo | verba por dia antes (ou o valor numérico da proposta) |
| `valor_depois_num` | `Numeric(12,2)`, nulo | verba por dia depois |

Derivado na leitura (não gravado): `impacto_mensal`, `teto` e `verba_mes` da frente.

## `marketing_diario` (existe — feature 345)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `alvo_platform` | `String(20)`, nulo | `Meta Ads` ou `Google Ads` |
| `alvo_tipo` | `String(10)`, nulo | `campanha` / `conjunto` / `anuncio` |
| `alvo_id` | `String(80)`, nulo | id na plataforma |
| `alvo_nome` | `String(300)`, nulo | |
| `metrica` | `String(20)`, nulo | `conversas` / `custo_conversa` / `gasto` / `cliques` / `cadastros` |
| `mudou_em` | `Date`, nulo | dia da mudança (padrão: dia da criação, SP) |
| `janela_dias` | `SmallInteger`, nulo | 3–28 (padrão 7) |
| `linha_base` | `Numeric(14,4)`, nulo | congelada na criação |
| `controle_tipo` | `String(10)`, nulo | como `alvo_tipo` |
| `controle_id` | `String(80)`, nulo | |
| `controle_nome` | `String(300)`, nulo | |

Teste = entrada com `alvo_id` e `metrica`. O controle usa a mesma plataforma do alvo.

## `notifications` (existe — feature 272)

Sem coluna nova: `kind = "marketing.proposta"` entra no catálogo de `notificacoes_ops`.

## Venda atribuída (derivada, não gravada)

```
VendaAtribuida
  event_id, sale_date, sale_value, frente_venda (frente_venda_sql)
  toque: Toque(client_id, momento UTC, fonte conversa|ficha|utm, platform,
               anuncio_id?, campaign_id?, campaign_name?)
  frente: frente da campanha do toque | None
```
