# Data Model — Feature 256

Migration única, aditiva, manual: `migrations/versions/<rev>_marketing_auditor.py` (`down_revision = "b3f8d27a9e14"`). Dinheiro sempre `Numeric(12, 2)`. Datas de métrica são `Date` (dia civil da plataforma, fuso da conta); carimbos de execução `DateTime` UTC como o resto do `models.py`.

## Tabelas novas

### `marketing_agent_runs` — Rodada
| coluna | tipo | regra |
|--------|------|-------|
| id | PK | |
| run_id | String(40) unique | carimbo `YYYYMMDD-HHMMSS` gerado pelo agente |
| mode | String(10) | `prod` \| `local` |
| window_start / window_end | DateTime | janela coberta (UTC) |
| executed_at | DateTime | |
| files_accepted / files_rejected | Integer | contagens |
| posts_upserted / campaigns_upserted / account_upserted | Integer | contagens |
| findings_json | Text | achados serializados (lista) |
| report_sent | Boolean | atualizado pelo `POST /report` |
| result_json | Text | resposta do `POST /run` guardada para o replay do mesmo `run_id` |

### `marketing_import_files` — Arquivo de entrada
| coluna | tipo | regra |
|--------|------|-------|
| id | PK | |
| run_id | FK runs.id (CASCADE) | |
| filename | String(300) | |
| sha256 | String(64) **unique** | mesmo conteúdo nunca entra duas vezes (FR-004) |
| kind | String(30) | `meta_content` \| `meta_account` \| `meta_ads` \| `google_ads` \| `unknown` |
| period_start / period_end | Date nullable | deduzidos do conteúdo |
| status | String(10) | `accepted` \| `rejected` |
| reason | Text nullable | motivo da rejeição (colunas faltantes, moeda, vazio…) |
| row_count | Integer | |

### `marketing_post_metrics` — Fotografia de post
| coluna | tipo | regra |
|--------|------|-------|
| id | PK | |
| platform | String(20) | `Instagram` (valores de `MARKETING_PLATFORMS`) |
| platform_post_id | String(80) | id do export |
| permalink | String(500) nullable | normalizado |
| post_type | String(40) nullable | Reels/Imagem/Carrossel… |
| caption | String(300) nullable | primeiros 300 chars |
| published_at | DateTime nullable | |
| snapshot_date | Date | data do export (FR-006) |
| reach, impressions, likes, comments, saves, shares, views | Integer nullable | |
| extra_json | Text nullable | colunas reconhecidas mas não modeladas |
| marketing_post_id | FK marketing_posts.id (SET NULL) nullable | vínculo com o card |
| link_method | String(10) | `permalink` \| `date` \| `none` |
| run_id | FK runs.id | rodada que gravou/atualizou |
| **unique** | (platform, platform_post_id, snapshot_date) | reprocessar substitui (FR-009) |

### `marketing_campaign_metrics` — Campanha por período
| coluna | tipo | regra |
|--------|------|-------|
| id | PK | |
| platform | String(20) | `Meta Ads` \| `Google Ads` |
| campaign_id | String(80) | id do export; Google sem id → hash do nome |
| campaign_name | String(200) | |
| period_start / period_end | Date | diário ⇒ iguais |
| is_daily | Boolean | `period_start == period_end` (coluna gerada no serviço, persistida p/ índice) |
| spend | Numeric(12,2) | |
| currency | String(3) | `BRL` exigido para reembolso (FR-018) |
| impressions, reach, clicks, results, conversions | Integer nullable | |
| result_type | String(80) nullable | |
| run_id | FK runs.id | |
| **unique** | (platform, campaign_id, period_start, period_end) | |

### `marketing_account_metrics` — Conta por dia
| coluna | tipo | regra |
|--------|------|-------|
| id | PK | |
| platform | String(20) | |
| metric_date | Date | |
| followers, reach, profile_views | Integer nullable | |
| extra_json | Text nullable | |
| run_id | FK runs.id | |
| **unique** | (platform, metric_date) | |

### `marketing_ad_spend_batches` — Lote de reembolso (plataforma × mês)
| coluna | tipo | regra |
|--------|------|-------|
| id | PK | |
| platform | String(20) | |
| month_ref | String(7) | `YYYY-MM` |
| special_expense_id | FK special_expenses.id (CASCADE) unique | o Gasto Extra gerado |
| reported_total | Numeric(12,2) | último total apurado pelas plataformas |
| last_run_id | FK runs.id | relação `last_run` (usada no serializer do lote) |
| frozen_at | DateTime nullable | preenchido quando o gasto deixou de estar `pendente` |
| **unique** | (platform, month_ref) | idempotência (FR-016) |

### `marketing_ad_spend_lines` — Detalhe por campanha do lote
| coluna | tipo | regra |
|--------|------|-------|
| id | PK | |
| batch_id | FK batches.id (CASCADE) | |
| campaign_name | String(200) | |
| amount | Numeric(12,2) | |
| clicks, results | Integer nullable | contexto para o financeiro |

Linhas são **substituídas** a cada atualização do lote (delete + insert na mesma transação).

## Colunas novas em tabelas existentes

| tabela | coluna | tipo | regra |
|--------|--------|------|-------|
| marketing_posts | permalink | String(500) nullable | URL http(s) validada em `marketing_ops`; normalizada ao salvar |
| clients | lead_origin | String(120) nullable | "Origem do Lead" do Kommo |
| clients | utm_source / utm_medium / utm_campaign | String(200) nullable | do Kommo; regra "mais recente sobrescreve" |

## Regras de negócio (em `app/marketing/desempenho_ops.py`)

1. **Ingestão idempotente** (`ingest_run(payload)`): transação única; `run_id` repetido → responde o resultado anterior (sem reprocessar); arquivos por `sha256` já existentes → `skipped`; métricas por chave única → upsert (`ON CONFLICT DO UPDATE`).
2. **Gasto mensal** (`sync_ad_spend(run)`): para cada (plataforma, mês) com gasto BRL nas métricas diárias (ou agregadas sem sobreposição): lote inexistente → `create_expense()` com categoria `Marketing`, `disbursement_type="reembolso"`, `reimburse_user_id` = titular, `expense_date` = último dia do mês, descrição padrão, `notes` com "reembolso previsto dia 10/<mês seguinte>" e `run_id`; **sem comprovante** (`require_receipt=False` via parâmetro novo em `_validate_expense_data` — a fatura do cartão não existe na hora da rodada; achado lembra de anexar); lote existente com gasto `pendente` → atualiza `amount` + linhas; gasto não pendente → congela e compara (`|reported − amount| > 0.01` ⇒ achado `gasto_divergente`). Gasto manual de Marketing no mês/plataforma (sem lote, descrição contendo o nome da plataforma) ⇒ não cria, achado `gasto_manual_existente`.
3. **Vínculo de post** (`link_post_metrics(run)`): ordem permalink → data → nenhum (research R7); revincula métricas `link_method="none"` de rodadas anteriores.
4. **Contexto** (`agent_context(window)`): posts publicados na janela (+permalink), `goal_health()` de todas as metas, `client_metrics()`, gastos de Marketing do mês corrente e anterior, clientes com utm na janela e seus eventos, titular resolvido.
5. **Agregações da tela** (`desempenho_summary(start, end)`): série semanal (alcance = soma de `reach` das fotografias mais recentes por post publicado na semana; seguidores = último `followers` da semana), gasto por campanha no período, funil por campanha (gasto → cliques → leads → eventos), tabela de posts (última fotografia + card), rodadas.

## Estados

- **Lote de reembolso**: `aberto` (gasto pendente, atualizável) → `congelado` (gasto aprovado/rejeitado; `frozen_at`); nunca volta.
- **Arquivo**: `accepted` | `rejected`; um sha256 só existe uma vez.
- **Vínculo de post**: `none` → `date`/`permalink` (pode melhorar; nunca piora).
