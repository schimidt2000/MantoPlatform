# Contrato: extensão de `GET /api/dashboard`

Extensão **aditiva** — nenhum campo/parâmetro existente muda de nome, tipo ou semântica.

## Request

```
GET /api/dashboard?perf_range=7|30|custom&perf_start=YYYY-MM-DD&perf_end=YYYY-MM-DD
```

- `perf_range` (opcional, default `"7"`): `"7"` | `"30"` | `"custom"`.
- `perf_start`/`perf_end` (obrigatórios só quando `perf_range=custom`): data ISO (`YYYY-MM-DD`).
- Parâmetros ignorados quando o usuário efetivo não é o papel real SUPERADMIN (sem erro —
  resposta simplesmente omite `performance`, igual ao comportamento atual de `dismissed_casting`).

## Response — campos novos

```jsonc
{
  // ...campos existentes inalterados (casting, figurino, financeiro, dismissed_casting)...
  "comercial": {
    "pending_payments": [
      {
        "event_id": 123,
        "event_title": "Show Fulano",
        "start_at": "2026-08-10T20:00:00",
        "sale": 12000.0,
        "received": 4000.0,
        "saldo": 8000.0,
        "severity": "urgent",   // "atrasado" | "vencido" | "urgent" | "warn" | "info"
        "due_date": null
      }
    ]
  },
  "performance": {
    "range": "7",
    "start": "2026-07-16",
    "end": "2026-07-23",
    "casting_total": 42,
    "casting_done": 38,
    "figurino_total": 42,
    "figurino_done": 30,
    "money_total": 18500.0
  }
}
```

- `comercial`: `null` quando o papel efetivo não tem `show_comercial` (mesma regra de
  `COMERCIAL`/`FINANCEIRO`/SUPERADMIN de `app/__init__.py::home()`).
- `performance`: `null` sempre que `impersonate` estiver ativo ou o usuário não for
  SUPERADMIN real — nunca aparece para papéis simulados.
- Em `perf_range=custom` com `perf_start > perf_end` ou datas ausentes/inválidas: o backend
  responde `200` com `performance: null` (mesmo fallback silencioso que o Jinja já faz hoje —
  não é um erro de validação bloqueante, é ausência de período válido) e o frontend trata como
  "sem dados para o período", sem quebrar o restante do dashboard.

## Origem da lógica (fonte única)

`compute_performance()` e `compute_comercial_pending()` (novas funções em
`app/api/dashboard_service.py`) extraem exatamente o cálculo hoje inline em
`app/__init__.py::home()` (linhas ~528–650). `home()` passa a chamar essas funções em vez de
duplicar a query — paridade de comportamento validada por teste funcional comparando os dois
call sites com o mesmo estado de banco (`manto_local`).
