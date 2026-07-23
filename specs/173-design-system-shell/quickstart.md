# Quickstart — 173 Design System Global e Shell (FASE A)

## Rodar em dev

```powershell
# Backend contra a cópia local de produção (Postgres)
.\scripts\db\run-local.ps1

# Frontend staff (proxy /api → Flask)
cd frontend; npm run dev:internal
```

## O que conferir manualmente

1. **Shell**: logar → toda rota autenticada renderiza com sidebar roxa (`#1f1a30`) no
   desktop; item ativo destacado; fundo do conteúdo `#f4f5f7`.
2. **Mobile (375px)**: sidebar vira drawer via hambúrguer; fecha ao navegar/tocar fora;
   sem overflow horizontal.
3. **RBAC do menu**: logar (ou "Ver como") com cada papel e comparar item a item com o
   menu Jinja (`/` no Flask) — paridade conforme tabela do research.md §3.
4. **Ver como**: como SUPERADMIN → pill CASTING → menu/telas mudam na hora; pill Admin
   (reset) → volta. Não-SUPERADMIN não vê o bloco.
5. **Regressão**: navegar pelas telas principais (agenda, criar evento, talentos,
   figurino, pagamentos, admin) e executar uma ação em cada.

## Portões antes do merge

```powershell
# Tipos + build (internal E public — ambos consomem o preset novo)
cd frontend\apps\internal; npx tsc --noEmit; npm run build
cd ..\public; npx tsc --noEmit; npm run build

# Lint backend
ruff check app/

# Verificação funcional dos endpoints novos (contra manto_local, fora de app_context)
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe specs\173-design-system-shell\verify_173.py
```

## Changelog

Ao concluir: entrada em `docs/changelog.html` (visual novo do beta + "Ver como") e
republicar no MESMO artifact.
