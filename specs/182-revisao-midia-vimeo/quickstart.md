# Quickstart: Revisão de Mídia estilo Vimeo

## Rodar localmente

```powershell
# Backend, apontando para manto_local (Postgres) — SEMPRE, nunca SQLite vazio
.\scripts\db\run-local.ps1

# Frontend (em outro terminal)
cd frontend
npm run dev:internal
```

Abra `http://localhost:5173/revisao`, entre em um espaço existente (ou crie um via
`RevisaoSpaceCreatePage`) e abra um material de vídeo para ver a nova tela.

## Aplicar a migration nova

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
python -m flask db upgrade
```

## Verificação funcional (backend)

Script com Flask test client contra `manto_local`, cobrindo:
- `GET` do asset retorna `status: "em_revisao"` para um material recém-criado.
- `PATCH /api/revisao/asset/<id>/status` com usuário `can_manage` → 200 e valor persistido.
- `PATCH` com usuário sem `can_manage` (ex.: revisor comum) → 403.
- `PATCH` com valor inválido (`"foo"`) → 400.
- `POST /api/revisao/asset/<id>/replace` → `status` volta para `"em_revisao"` mesmo se estava
  `"aprovado"`.

## Verificação de tipos e build (frontend)

```powershell
cd frontend/apps/internal
npx tsc --noEmit
npm run build
```

## E2E (Playwright)

```powershell
cd frontend/apps/internal
npx playwright test e2e/revisao-asset.spec.ts
```

Pré-requisito: backend rodando contra `manto_local` (mesma premissa dos demais e2e do app, ver
`e2e/global-setup.ts`).
