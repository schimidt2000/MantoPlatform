# Quickstart — Gestão de Usuários (Admin) em React (167)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/admin/usuarios` (React) — como Superadmin e como Financeiro, conferir a lista com paridade
   contra `/admin/users` (Jinja).
2. Criar um usuário "com acesso" (papéis + senha temporária) e um "só pagamento", cada um com
   PIX e salário, e conferir os dados gravados.
3. Editar identidade/papéis de um usuário existente como Superadmin; confirmar 403 como
   Financeiro na mesma ação.
4. Atualizar PIX e registrar salário como Financeiro.
5. Conceder acesso a uma pessoa só-pagamento, resetar senha e tentar excluir um usuário com
   histórico financeiro (bloqueado) e um sem histórico (excluído) — tudo como Superadmin.
6. Tentar excluir o próprio usuário logado e confirmar bloqueio.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_167_admin_usuarios_react.py
```

Cobre paridade API×Jinja de todas as 8 ações, os dois níveis de RBAC (SUPERADMIN vs.
SUPERADMIN/FINANCEIRO), e os bloqueios de exclusão (auto-exclusão, histórico financeiro).
