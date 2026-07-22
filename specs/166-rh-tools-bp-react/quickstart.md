# Quickstart — RH em React + destino do `tools_bp` (166)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/rh` (React) — com um usuário com permissão `rh.view`, conferir que o painel carrega e que
   `can_manage_users` reflete corretamente a permissão `user.manage` do usuário.
2. Com um usuário sem `rh.view`, confirmar 403 na tela e na API.
3. Confirmar que `app/tools/` e `app/templates/tools/` não existem mais no repositório.
4. Abrir o fluxo de Orçamento (cálculo de transporte) e confirmar que continua funcionando
   normalmente — não depende de `app/tools/`.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_166_rh_tools_bp.py
```

Cobre paridade API×Jinja do painel de RH (com/sem `user.manage`), o gate 403 sem `rh.view`, e
confirma que `app/orcamento/transport.py` segue funcionando (import direto, sem depender de
`app/tools/`).
