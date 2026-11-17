# Quickstart — conferir a feature 351

Pré-requisitos: espelho `manto_351` (restaurado do dump noturno; URL em `.local-db-url` do worktree), migration
`a351b0c1d2e3` aplicada.

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
.\.venv\Scripts\flask.exe db upgrade
$env:PYTHONUTF8 = '1'; .\.venv\Scripts\python.exe specs\351-painel-atribuido\verify_351.py
```

Esperado: todos os cenários `OK`, os dois cenários de RBAC recusados (403), limpeza sem resto.

Telas (backend 5351, Vite 6351, usuário descartável Superadmin):

1. `/marketing/desempenho` — cada frente com misto, atribuído e atribuído com desconto; premissa escrita; mês
   corrente com meta e verba; bloco "Vendas atribuídas" e funil por frente/anúncio/peça/conceito com custo; campanhas
   em cartões em 390 px.
2. `/marketing/decisoes` — proposta com frente, teto, impacto no mês; soma do mês no topo; diário com o teste (antes,
   depois, variação, controle).
3. `/marketing/temas` — 50 por página, página no endereço.
4. `/marketing/painel` — filtros frente, tipo, "Minhas peças"; card com frente; diálogo com conceito, "no ar" e o
   resultado real.
5. Diálogo "Metas, verba e tetos" e "Calendário do ano" (Superadmin).
6. `/funil` — divisões novas, sem dinheiro.

Contratos: [contracts/api-351.md](contracts/api-351.md). Dados: [data-model.md](data-model.md).
