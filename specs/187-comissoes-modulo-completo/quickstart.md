# Quickstart: Módulo de Comissões (feature 187)

## Rodar localmente

```powershell
# Backend contra a cópia local real (Postgres) — nunca o SQLite vazio
.\scripts\db\run-local.ps1

# Frontend (staff), em outro terminal
cd frontend; npm run dev:internal
```

Acessar `http://localhost:5173/financeiro/comissoes` (ou porta do Vite configurada), logado
como:
- Usuário só com papel **Comercial** → deve ver "Minhas Comissões", só os próprios dados, sem
  botões de pagamento.
- Usuário com papel **Financeiro** ou **Superadmin** → deve ver "Comissões", seletor de mês,
  filtro por vendedor, as duas abas e o botão "Pagar Mês" habilitado quando há pendências.

## Verificação funcional obrigatória

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_187_comissoes.py
```

Cobre (test client do Flask, requests fora de `app_context`):
1. Vendedor comum: `GET /api/financeiro/comissoes` só retorna o próprio `seller_id`.
2. Vendedor comum: `POST /api/financeiro/comissoes/pagar-mes` (mesmo tentando o próprio
   `seller_id`) → 403, nenhum registro alterado.
3. Financeiro: `POST .../pagar-mes` de um vendedor com pendências → todos os `a_pagar`
   elegíveis viram `pago`, `changed_count` bate com a quantidade movida.
4. Financeiro: repetir a mesma chamada → `changed_count: 0`, sem erro (idempotência).
5. KPIs (`GET`) batem centavo a centavo com `SUM()` direto na tabela para o mês testado.

## Checks antes de declarar pronto

```powershell
ruff check app/financeiro/comissoes_ops.py app/api/financeiro_read.py app/api/financeiro_write.py
cd frontend/apps/internal; npx tsc --noEmit; npm run build
```
