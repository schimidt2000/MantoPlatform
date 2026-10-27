# Quickstart — validar a Feature 320

## Pré-requisitos

- Worktree `C:\tmp\mp320` com `frontend/node_modules` instalado (`npm ci` em `frontend/`).
- Navegador do Playwright já baixado (`%LOCALAPPDATA%\ms-playwright\chromium-1228`).
- Backend local sobre o `manto_local`, sem threads e sem Google — a feature não toca o Flask, então
  pode ser o do checkout principal: entrada `manto-backend-local-sem-google` do `launch.json`
  (porta 5000).
- Vite do **worktree** (não o do checkout principal — `preview_start` sobe o principal):
  - interno: `npm run dev --prefix C:\tmp\mp320\frontend\apps\internal -- --port 5320 --strictPort`
  - público: `npm run dev --prefix C:\tmp\mp320\frontend\apps\public -- --port 5321 --strictPort`

## Rodar o verify

PowerShell, na raiz do worktree:

```powershell
$env:DATABASE_URL = (Get-Content C:\Users\schim\Desktop\Manto_Platform\.local-db-url -Raw).Trim()
$env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
$env:VERIFY_320_INTERNO = 'http://localhost:5320'; $env:VERIFY_320_PUBLICO = 'http://localhost:5321'
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\320-voltar-sem-perder-o-lugar\verify_320.py
```

Esperado: `12/12` (o cenário 12 é a contraprova: roda 1, 5 e 7 contra o Vite da `main` em
`VERIFY_320_MAIN_INTERNO`/`VERIFY_320_MAIN_PUBLICO` e exige que **falhem**; sem essas variáveis ele
é pulado e o total vira `11/11 (contraprova pulada)`).

## Conferência de tela (Browser pane, viewport de iPhone 390×844)

1. `http://localhost:5321/` → buscar "princesa", escolher uma categoria, rolar, abrir um tema,
   "← Voltar ao catálogo": mesma busca, mesma categoria, o tema aberto à vista.
2. `http://localhost:5320/admin/catalogo` → filtrar, rolar, "Editar" pelo menu do card, "‹ Catálogo".
3. `http://localhost:5320/talents` → Pendentes, busca, página 2, abrir ficha, voltar.
4. `http://localhost:5320/gastos` → "Ver" num comprovante JPG e num PDF: abre por cima, "Voltar"
   fecha no mesmo ponto; "Baixar".
5. Planilha de Pagamentos → adiantamentos → "Ver comprovante": o diálogo continua aberto ao voltar.
6. Desktop: Esc fecha o visualizador e o foco volta ao "Ver".
