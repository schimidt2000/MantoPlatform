# Quickstart — Planilha de Pagamentos em React (159)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/financeiro/pagamentos` — como Financeiro/Superadmin, conferir a lista de itens do mês
   corrente (cachês, salários, BV, comissões, recorrentes) com os mesmos valores da tela antiga
   (`/financeiro/pagamentos`).
2. Trocar o mês (seletor `YYYY-MM`) e conferir que a lista e os 5 totais recalculam, inclusive
   gerando os lançamentos de salário do mês se ainda não existirem.
3. Conferir um item de salário com adiantamento lançado: valor líquido exibido, com o bruto e os
   adiantamentos (valor, data, comprovante) disponíveis para conferência.
4. Conferir um repasse de BV sem chave PIX cadastrada: sinalizado como pendente de dados.
5. Como usuário sem papel Financeiro/Superadmin, confirmar que a tela/API recusa acesso (403).

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_159_financeiro_pagamentos.py
```

Cobre paridade API×Jinja (itens por tipo, valores, status, os 5 totais) para o mês corrente e para
um mês com adiantamento/BV sem PIX/conta recorrente, filtro de mês (válido/inválido/default), e o
gate de acesso (403 fora de Financeiro/Superadmin).
