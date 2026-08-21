# Contrato — API interna (sessão) da tela e do card

RBAC: mesmo gate de `GET /api/marketing/posts` (papéis `MARKETING`, `SUPERADMIN`); demais ⇒ 403 `json_error`.

## `GET /api/marketing/desempenho?weeks=12` ou `?start=YYYY-MM-DD&end=YYYY-MM-DD`

`weeks` ∈ {4, 12, 26}; ausente ⇒ 12; `start/end` têm precedência e exigem `start <= end` (400 caso contrário).

```json
{
  "period": {"start": "2026-05-26", "end": "2026-08-17", "weeks": 12},
  "headline": {"kind": "leads", "value": 14, "cost_per_lead": "61.40", "fallback_reason": null},
  "weekly": [
    {"week_start": "2026-08-11", "reach": 18400, "followers": 12840, "spend": "690.40", "clicks": 212, "leads": 6, "events": 1, "posts_published": 3}
  ],
  "campaigns": [
    {"platform": "Google Ads", "campaign_name": "Festa 15 anos SP", "spend": "251.10", "impressions": 8100, "clicks": 133, "cpc": "1.89", "leads": 4, "cost_per_lead": "62.78", "events": 1, "cost_per_event": "251.10"}
  ],
  "posts": [
    {"platform": "Instagram", "platform_post_id": "…", "permalink": "…", "published_at": "…", "post_type": "Reels", "caption": "…", "reach": 5400, "likes": 210, "comments": 8, "saves": 31, "shares": 12, "views": 9100, "marketing_post": {"id": 12, "title": "Reels 15 anos"}, "link_method": "permalink", "snapshot_date": "2026-08-17"}
  ],
  "goals": [{"id": 3, "name": "15 Anos", "status": "delayed", "days_overdue": 10, "last_posted_date": "2026-07-20"}],
  "cac": {"month": "2026-08", "spend": "663.40", "new_clients": 9, "value": "73.71"},
  "runs": [{"run_id": "20260818-063012", "executed_at": "…", "window": ["…", "…"], "files_accepted": 3, "files_rejected": 1, "report_sent": true, "rejected_files": [{"filename": "google.csv", "reason": "colunas faltantes: Custo"}]}],
  "empty": false
}
```

`empty: true` (sem nenhuma rodada) ⇒ a tela mostra o estado vazio com instruções (pasta de entrada + horário da rotina). Dinheiro em string decimal; a tela formata com `formatBRL`.

## `PATCH /api/marketing/posts/<id>` — campo novo

Aceita `permalink: string | null`. Validação em `marketing_ops._validate_permalink`: http(s), ≤ 500 chars, normalização (sem querystring `utm_*`, sem barra final, `www.` removido para comparação, mas a URL gravada mantém o host original). Inválido ⇒ 400 `{"error": {"message": "…", "fields": {"permalink": "Informe um link http(s) válido"}}}`. `serialize_post` passa a incluir `permalink`.

## `GET /api/gastos/...` (serializer de Gasto Extra) — campo novo

`marketing_batch: null | {"platform": "Meta Ads", "month_ref": "2026-08", "reported_total": "412.30", "frozen": false, "run_id": "…", "lines": [{"campaign_name": "…", "amount": "…", "clicks": 41, "results": 2}]}`. Sem mudança nos campos existentes.

## Frontend — `lib/marketing.ts`

- `MarketingPost` ganha `permalink: string | null`.
- `useMarketingDesempenho(params)` (TanStack Query, `queryKey: ["marketing", "desempenho", params]`, `placeholderData: keepPreviousData`).
- Tipos `DesempenhoResponse`, `DesempenhoWeek`, `DesempenhoCampaign`, `DesempenhoPost`, `DesempenhoRun`.
