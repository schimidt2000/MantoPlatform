# Quickstart — Gestão de Catálogo (169)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1
npm run dev:internal
```

## Roteiro manual

1. `/admin/catalogo` — buscar/filtrar, conferir paridade com a tela antiga.
2. Criar categoria nova e um produto com 2+ fotos, tags e categoria; definir capa diferente da
   1ª foto.
3. Editar o produto: remover uma foto, adicionar outra, reordenar (mover-esquerda/direita),
   trocar a capa.
4. Ativar/inativar e excluir um produto.
5. Como usuário sem Superadmin, confirmar 403.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_169_admin_catalogo_react.py
```
