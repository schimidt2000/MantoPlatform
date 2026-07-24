# Quickstart: verificar a feature 185 localmente

## 1. Backend

```powershell
# Aplicar a migration nova na cópia local (manto_local, Postgres)
.\scripts\db\run-local.ps1
python -m flask db upgrade

# Rodar a API
.\scripts\db\run-local.ps1   # equivale a setar DATABASE_URL e rodar python run.py
```

## 2. Frontend

```powershell
cd frontend
npm run dev:public     # http://localhost:<porta> — Catálogo Público
npm run dev:internal   # staff — Gerenciador Interno em /admin/catalogo e Novo Evento em /events/new
```

## 3. Roteiro manual de verificação (cobre as 5 User Stories da spec)

1. **US3 (gerenciador)**: `/admin/catalogo` → criar um Tema "Show Teste" com 1 foto e um
   `video_url` do Vimeo. Adicionar 2 Personagens: um com foto+vídeo MP4 e vínculo a uma Ficha de
   Figurino existente; outro só com nome. Digitar 2 tags via chip input (Enter/vírgula) e
   confirmar autocomplete ao editar um segundo produto com tag parecida.
2. **US1 + US2 (público)**: abrir `/catalogo/show-teste` sem sessão (janela anônima) — conferir
   seção "Elenco Individual" com os 2 Personagens, vídeo do Tema em autoplay mudo, alternância
   suave entre foto e vídeo na galeria, botões de som/tela cheia, e adicionar tanto o Tema quanto
   1 Personagem à lista de interesse separadamente.
3. **US5 (SEO)**: inspecionar `<head>` de `/catalogo` e `/catalogo/show-teste` — confirmar
   `<meta name="robots" content="noindex, nofollow">`.
4. **US4 (eventos)**: `/events/new` → na seção Elenco, buscar o Tema "Show Teste" e escolher o
   Personagem com figurino vinculada — conferir que a ficha aparece pré-selecionada na linha.
5. **Regressão**: abrir um produto do catálogo criado **antes** desta feature (sem Personagens,
   sem vídeo) e confirmar que continua funcionando sem erros (FR-015/SC-005).

## 4. Verificação automatizada (obrigatória antes do merge)

```powershell
# Backend — lint + verificação funcional contra manto_local
ruff check app/catalogo app/admin/catalog_ops.py app/api/catalogo_read.py app/api/admin_catalogo_read.py app/api/admin_catalogo_write.py app/api/agenda_read.py
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\verify_catalogo_185.py   # script de verificação a ser criado nas tasks

# Frontend — typecheck + build
cd frontend\apps\public
npx tsc --noEmit; npm run build
cd ..\internal
npx tsc --noEmit; npm run build

# Playwright — NÃO existe configuração no monorepo ainda; esta feature adiciona um setup mínimo
# em frontend/e2e/ (novo), rodando contra manto_local + npm run dev:public/dev:internal locais
npx playwright test catalogo
```
