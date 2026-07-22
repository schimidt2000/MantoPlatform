# Contract: Dashboard Financeiro (DRE) Endpoint (157)

Convenção geral: `specs/144-migracao-react-spa/contracts/api-conventions.md`.

## `GET /api/financeiro/dashboard`

- **Auth**: sessão válida + (FINANCEIRO/SUPERADMIN), senão 403 — paridade com `require_financeiro`.
- **Query params** (todos opcionais, mesmo default da view Jinja):
  - `period`: `este_mes` (default) | `30d` | `mes_anterior` | `custom`
  - `start`, `end`: ISO `YYYY-MM-DD`, usados só quando `period=custom`
- **200**:

```json
{
  "period": "este_mes",
  "period_label": "Este mês",
  "start": "2026-07-01",
  "end": "2026-07-31",
  "is_full_month": true,
  "dre": {
    "realizado": {
      "receita_bruta": 15000.0, "impostos": 800.0, "receita_liquida": 14200.0,
      "cpv": 6000.0, "lucro_bruto": 8200.0, "margem_bruta": 57.7,
      "marketing": 0.0, "comissoes": 375.0, "pessoal": 4000.0,
      "ebitda": 3825.0, "margem_ebitda": 26.9,
      "gastos_extras": 200.0, "gastos_recorrentes": 150.0,
      "resultado_liquido": 3475.0,
      "n_eventos": 6, "n_normais": 5, "n_permutas": 1
    },
    "projetado": { "...": "mesma forma, custo fixo zerado" },
    "total": { "...": "mesma forma, consolidado do período" }
  },
  "kpis": {
    "ticket_medio": 2500.0,
    "ratio_custo_talento": 42.3,
    "breakeven_pct": 91.4,
    "breakeven_atingido": false,
    "fixed_cost": 4375.0,
    "fator_r_pct": 26.7,
    "fator_r_threshold": 28.0,
    "fator_r_protegido": false
  },
  "paineis": {
    "a_receber_clientes": 3200.0,
    "pagamentos_pendentes": 1200,
    "pagamentos_realizados": 4800,
    "receita_por_tipo": { "SHOW": 10000, "FESTA": 5000 },
    "receita_tipo_max": 10000,
    "top_sellers": [
      { "user_id": 12, "user_name": "Fulano", "receita": 8000, "lucro": 4500 }
    ],
    "monthly_trend": [
      { "label": "02/26", "receita": 12000, "custo": 5000, "lucro": 7000, "margem": 58.3, "n_eventos": 5 }
    ],
    "auditoria": [
      { "event_id": 88, "title": "Evento sem valor", "start_at": "2026-07-15T20:00:00" }
    ]
  },
  "eventos": [
    {
      "event_id": 123, "title": "Show Exemplo", "group_label": null,
      "start_at": "2026-07-10T20:00:00", "custo": 1200.0, "lucro": 1800.0,
      "comissao": 75.0, "rate": 2.5, "is_projetado": false, "status": "parcial"
    }
  ],
  "pendencias": {
    "recebimentos_previstos": [
      { "date": "2026-07-20", "event_id": 123, "event_title": "Show Exemplo", "amount": 1500.0 }
    ],
    "recebimentos_previstos_total": 1500.0,
    "nf_a_emitir": [
      { "id": 5, "date": null, "event_id": 123, "event_title": "Show Exemplo", "amount": 3000.0 }
    ],
    "nf_a_emitir_total": 3000.0,
    "custo_nota_itens": [
      { "event_id": 123, "event_title": "Show Exemplo", "amount": 3000.0, "date": "2026-07-05", "status": "emitida", "custo": 480.0 }
    ],
    "custo_nota_total": 480.0
  }
}
```

- Todos os valores monetários e percentuais são `number` (Decimal→float), nunca string
  formatada — mesma convenção da 156.
- `eventos` não inclui satélites (consolidados no evento principal via `custo`/`lucro`).
- `403`: usuário sem papel Financeiro/Superadmin.
