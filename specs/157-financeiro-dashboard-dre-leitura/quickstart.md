# Quickstart — Dashboard Financeiro (DRE) em React (157)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/financeiro` — como Financeiro/Superadmin, conferir DRE (realizado/projetado/total) do mês
   corrente com os mesmos valores da tela antiga (`/financeiro/`).
2. Trocar o filtro de período (Este mês / Últimos 30 dias / Mês anterior / Personalizado) e
   conferir que DRE, KPIs e tabela recalculam corretamente.
3. Conferir KPIs: ticket médio, ratio custo-talento, termômetro de break-even, alerta do Fator R.
4. Conferir painéis: receita por tipo, top vendedores, tendência de 6 meses, auditoria de
   eventos sem receita.
5. Conferir tabela de eventos do período: status financeiro por linha (permuta/sem_valor/
   pago_total/parcial/pendente); evento satélite não aparece como linha própria.
6. Conferir painel de pendências: recebimentos previstos e notas fiscais a emitir/emitidas.
7. Como usuário sem papel Financeiro/Superadmin, confirmar que a tela/API recusa acesso (403).

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_157_financeiro_dashboard.py
```

Cobre paridade API×Jinja (DRE realizado/projetado/total, KPIs, tabela de eventos, pendências),
exclusão de satélites, filtros de período (este_mes/30d/mes_anterior/custom), e o gate de acesso
(403 para papel fora de Financeiro/Superadmin).
