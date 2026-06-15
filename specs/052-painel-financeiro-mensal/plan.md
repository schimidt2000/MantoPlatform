# Plano de Implementação — Painel Financeiro Mês a Mês

**Branch**: `052-painel-financeiro-mensal` · **Stack**: Flask + Jinja2 + CSS/JS vanilla (sem React/Tailwind)

## Arquitetura de dados

Migration manual encadeada em `o1d2e3f4a5b6` (head atual):
- `calendar_events.is_cortesia_permuta` — Boolean, default false, server_default '0'
- `site_settings.tax_rate` — Float, default 16.0
- `site_settings.fator_r_threshold` — Float, default 28.0

Reuso de `calendar_events.with_invoice` para "Emitir Nota" (já existe).

## Camada de cálculo (refatorar `app/financeiro/routes.py`)

Funções auxiliares novas/ajustadas (puras, `Decimal`, divisão-zero-safe):
- `_period_from_request()` → resolve "este_mes" | "30d" | "mes_anterior" | "custom" → (start_date, end_date, is_full_month).
- `_split_realizado_projetado(events, now_sp)` → (realizados, projetados) pela data do evento.
- `_is_permuta(event)` → bool.
- `_event_sale(event)` → 0 se permuta, senão `sale_value or 0`.
- `_compute_drg(events, settings, salary_cost)` → dict com a cascata completa (receita_bruta, impostos, receita_liquida, cpv, lucro_bruto, marketing, comissoes, pessoal, ebitda, gastos_extras, resultado_liquido + margens). Aplicada 2×: realizado e projetado.
- `_salary_cost(start, end, is_full_month)` → real (`SalaryPayment` do mês) ou pro-rata.
- `_fixed_cost_nominal(...)` → Salários + Comissões (ponto de extensão p/ gastos recorrentes futuros).
- `_fator_r(folha, faturamento, threshold)` → (% , status).
- `_audit_eventos_zerados(events)` → eventos venda 0 sem flag permuta.

DRE: impostos só sobre `with_invoice`; CPV exclui permutas; Marketing = cachês de permutas.

## Camada de apresentação

- `app/templates/financeiro/dashboard.html` reescrito em CSS Grid (bento):
  - Top: filtros + seletor de mês.
  - Row 1: 8 KPI cards (grid compacto).
  - Row 2: DRE (≈65%) + [Receita por Tipo / Top Vendedores] (≈35%).
  - Row 3: Tendência 6 meses + Card Auditoria.
  - Row 4: Tabela de eventos com badges de status.
- Usa variáveis CSS de cor já existentes no `financeiro_layout.html`.

## Configuração

- `admin_settings.html` + `admin/routes.py`: campos taxa de imposto e corte Fator R.

## Flag no evento

- `event_detail.html` (seção "Dados de Venda") + rota que salva o evento: checkbox "Cortesia/Permuta" (`is_cortesia_permuta`).

## Verificação

- `pytest tests/ -v`, `python run.py` smoke, conferir cenários P1 (permuta não distorce CPV; realizado vs projetado).
