# Contrato — endpoints do agente de marketing

Base: `/api/marketing-agent/<token>/…`. Token = env `MARKETING_AGENT_TOKEN` (arquivo local `.marketing-agent-token`, gitignored). Token ausente/errado ⇒ **404** `{"error":{"message":"Não encontrado"}}` (molde `audit_agent.py`). Sem env configurado, tudo responde 404 — interruptor geral. Nenhum destes endpoints usa sessão/login.

## `GET /context?window_start=<ISO>&window_end=<ISO>&card_holder_email=<e-mail>`

Contexto do ERP para a rodada (somente leitura). `card_holder_email` vem do `config.py` do agente (`CARD_HOLDER_EMAIL`) e precisa ser usuário interno ativo — senão 403 `{"error":{"message":"Titular do cartão não é usuário interno ativo"}}`. Resposta 200:

```json
{
  "window": ["2026-08-11T09:00:00+00:00", "2026-08-18T09:00:00+00:00"],
  "card_holder": {"user_id": 1, "name": "João …", "email": "joao@…"},
  "posts": [{"id": 12, "title": "Reels 15 anos", "platform": "Instagram", "publish_date": "2026-08-14", "permalink": "https://www.instagram.com/reel/ABC/", "status": "publicado"}],
  "goals": [{"id": 3, "name": "15 Anos", "target_interval_days": 15, "last_posted_date": "2026-07-20", "status": "delayed", "days_overdue": 10}],
  "new_clients_by_month": [{"month": "2026-08", "total": 9, "kommo": 6, "formulario": 2, "manual": 1}],
  "marketing_expenses": [{"id": 88, "description": "Anúncios Meta Ads — agosto/2026 (auditor de marketing)", "amount": "412.30", "expense_date": "2026-08-31", "status": "pendente", "batch": {"platform": "Meta Ads", "month_ref": "2026-08"}}],
  "attributed_clients": [{"client_id": 501, "created_at": "2026-08-12", "utm_campaign": "festa-15-anos-sp", "utm_source": "google", "events": [{"event_id": 9001, "start_at": "2026-09-20", "sale_value": "3500.00"}]}]
}
```

Erros: 400 janela inválida (`window_start >= window_end` ou não ISO); 403 titular inválido.

## `POST /run`

Ingestão idempotente de uma rodada. Corpo (resumo — ver `data-model.md` para campos):

```json
{
  "run_id": "20260818-063012",
  "mode": "prod",
  "window": ["…", "…"],
  "card_holder_email": "joao@…",
  "files": [{"filename": "conteudo.csv", "sha256": "…", "kind": "meta_content", "period_start": "2026-08-01", "period_end": "2026-08-17", "status": "accepted", "reason": null, "row_count": 23}],
  "post_metrics": [{"platform": "Instagram", "platform_post_id": "1789…", "permalink": "https://www.instagram.com/reel/ABC/", "post_type": "Reels", "caption": "…", "published_at": "2026-08-14T18:02:00", "snapshot_date": "2026-08-17", "reach": 5400, "likes": 210, "comments": 8, "saves": 31, "shares": 12, "views": 9100}],
  "campaign_metrics": [{"platform": "Google Ads", "campaign_id": "h:festa-15-anos-sp", "campaign_name": "Festa 15 anos SP", "period_start": "2026-08-12", "period_end": "2026-08-12", "spend": "38.90", "currency": "BRL", "impressions": 1200, "clicks": 41, "conversions": 2}],
  "account_metrics": [{"platform": "Instagram", "metric_date": "2026-08-12", "followers": 12840, "reach": 3300, "profile_views": 120}],
  "findings": [{"code": "arquivo_rejeitado", "severity": "atencao", "title": "google.csv: colunas faltantes (Custo)", "details": {}}]
}
```

Resposta 200 (gravada pelo agente em `runs/<id>/resultado.json`):

```json
{
  "run_id": "20260818-063012",
  "replayed": false,
  "files": {"accepted": 3, "rejected": 1, "skipped_duplicate": 0},
  "upserted": {"post_metrics": 23, "campaign_metrics": 14, "account_metrics": 7},
  "post_links": {"permalink": 5, "date": 2, "none": 3, "linked": {"1789…": {"card_id": 12, "title": "Reels 15 anos", "method": "permalink"}}, "unlinked_posts": [{"platform_post_id": "…", "published_at": "…", "candidates": [12, 13]}]},
  "ad_spend": [
    {"platform": "Meta Ads", "month_ref": "2026-08", "action": "created", "expense_id": 88, "amount": "412.30", "lines": 3},
    {"platform": "Google Ads", "month_ref": "2026-08", "action": "updated", "expense_id": 89, "amount": "251.10", "lines": 2},
    {"platform": "Google Ads", "month_ref": "2026-07", "action": "frozen_divergent", "expense_id": 71, "erp_amount": "980.00", "reported_amount": "1012.40"},
    {"platform": "Meta Ads", "month_ref": "2026-07", "action": "skipped_manual", "expense_id": 64, "erp_amount": "500.00", "reported_amount": "512.00"},
    {"platform": "Google Ads", "month_ref": "2026-08", "action": "skipped_currency", "currency": "USD", "reported_amount": "120.00"}
  ],
  "findings_server": [{"code": "gasto_divergente", "severity": "critico", "title": "Google Ads julho/2026: lançado R$ 980,00 × reportado R$ 1.012,40"}]
}
```

`action` ∈ {`created`, `updated`, `frozen_ok`, `frozen_divergent`, `skipped_manual`, `skipped_currency`}. Regras: `run_id` repetido ⇒ 200 com `replayed: true` e o resultado original; `card_holder_email` inválido ⇒ 403 antes de qualquer escrita; `mode: "local"` nunca cria Gasto Extra em produção (o servidor recusa `mode=local` quando `FLASK_ENV != development` ⇒ 400). Validação de corpo ⇒ 400 com `error.fields`. Tudo numa transação: qualquer falha ⇒ 500 sem efeito parcial.

## `POST /report`

`{"subject": "…", "html": "…", "to": ["joao@…"], "run_id": "…"}` ⇒ `{"sent": 1, "rejected": []}`. Destinatários filtrados a usuários internos ativos (`User.is_active`, `has_access`) como no auditor 221; marca `report_sent` na rodada. Reutiliza `send_audit_report_email` com parâmetro de rótulo ("auditor de marketing").

## Escopo negativo (garantias)

- Nenhum endpoint lê arquivos do disco nem aceita upload.
- Única escrita além das tabelas de métrica/rodada: `special_expenses` (+ lotes/linhas) — e só com categoria `Marketing`, `disbursement_type = "reembolso"`, `status = "pendente"`.
- `mode=local` só é aceito com `FLASK_ENV=development` (espelho `manto_local`).
