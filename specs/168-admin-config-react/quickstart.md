# Quickstart — Configurações/Logs/Sync/Desempenho/Migração (168)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1
npm run dev:internal
```

## Roteiro manual

1. `/admin/configuracoes` — editar campos e logo, conferir persistência.
2. `/admin/logs` — filtrar por tipo/ator.
3. `/admin/desempenho` — trocar o mês.
4. `/admin/sync` — disparar sync/limpeza (ambiente real fala com o Google — testar com cautela
   ou só conferir a tela carregando).
5. `/admin/anuncio-portal` — disparar o anúncio (cuidado: envia email de verdade em produção).
6. `/admin/migrar-arquivos` e `/admin/importar-catalogo` — conferir status e disparo.
7. Como usuário sem Superadmin, confirmar 403 em todas as telas/API.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_168_admin_config_react.py
```

Cobre configurações, logs, desempenho, gate 403; sync/anúncio/migração/importação são cobertos
via mocks (sem chamar Google/email/threads reais).
