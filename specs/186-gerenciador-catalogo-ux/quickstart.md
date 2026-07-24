# Quickstart: verificar a feature 186 localmente

## 1. Backend

```powershell
.\scripts\db\run-local.ps1
```

## 2. Frontend (dev normal, sem prefixo)

```powershell
cd frontend
npm run dev:internal
npm run dev:public
```

## 3. Verificar o deploy dual-app localmente (build de produção)

```powershell
cd frontend
npm run build            # compila os dois apps
node server.js            # sobe o servidor único na porta $PORT (default 3000)
```

Abrir `http://localhost:3000/admin/catalogo` (app interno) e
`http://localhost:3000/catalogo/` (app público, sob o prefixo) — confirmar que os dois carregam,
que navegar/recarregar uma rota profunda de qualquer um dos dois funciona (ex.:
`http://localhost:3000/catalogo/algum-slug` direto na barra de endereço).

## 4. Roteiro manual

1. `/admin/catalogo` → alternar Cards/Árvore, expandir um Tema com Personagens, conferir foto +
   status de figurino de cada filho.
2. Selecionar 2+ itens → confirmar barra flutuante → testar "Mover para…" escolhendo outro Tema.
3. Abrir uma Ficha de Figurino sem vínculo → usar "Vincular a um Personagem do Catálogo" → abrir o
   Personagem escolhido no catálogo e confirmar que mostra essa mesma ficha.
4. `/events/new` → buscar personagem no elenco → confirmar foto em miniatura nas sugestões e que
   Temas pai não aparecem.
5. Editar um Tema → clicar "Definir como capa" numa foto diferente da atual → confirmar selo "⭐
   Capa" migra; arrastar uma foto para reordenar.
6. Clicar "Catálogo" no menu lateral (só funciona de ponta a ponta contra o `node server.js` do
   passo 3, não contra `npm run dev:internal` sozinho) → confirmar que abre a vitrine pública.

## 5. Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe specs\186-gerenciador-catalogo-ux\verify_186.py

cd frontend\apps\internal
npx tsc --noEmit; npm run build
npx playwright test catalogo-ux.spec.ts

cd ..\public
npx tsc --noEmit; npm run build
npx playwright test
```
