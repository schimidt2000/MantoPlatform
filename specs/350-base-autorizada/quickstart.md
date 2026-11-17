# Quickstart — validar a 350

## Pré-requisitos

- Worktree `350-base-autorizada` com `.venv` (junção para o do checkout principal) e
  `frontend/node_modules` próprio (`npm ci`; os `@manto/*` são junções absolutas — não reaproveite as do
  checkout principal).
- Banco próprio `manto_350` (dump noturno `backups/manto_2026-11-17_0200.dump`) com a URL em
  `.local-db-url` da worktree (ignorado pelo git).

## 1. Migration

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
.venv\Scripts\flask.exe db upgrade
```

Esperado: `d334b2c4e6f8 -> a350b1c2d3e4`. `flask db downgrade d334b2c4e6f8` e `upgrade` de novo devem
passar (ensaio da reversão).

## 2. Verify

```powershell
$env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe specs/350-base-autorizada/verify_350.py
```

Esperado: todos os cenários OK, nenhuma conexão de saída (o disjuntor lista escapes), limpeza feita.
`--manter` deixa as fichas, o evento e os usuários `v350-` para conferir a tela.

## 3. Telas (backend 5350, Vite 6350)

- Backend: cópia temporária de `scripts/db/run-local-sem-google.py` com a porta 5350, rodando da worktree.
- Vite: `vite.config.6350.ts` temporário no app interno (e no público) com o proxy para 5350.
- Login no console da aba: `fetch('/api/auth/login', {method: 'POST', headers: {'Content-Type':
  'application/json'}, body: JSON.stringify({email, password})})` com o usuário `v350-` do `--manter`.
- Conferir em 390 px: ficha (Consentimentos, Indicação), cabeçalho da conversa, Clientes › Pós-evento,
  Aniversários, Parceiros, diálogo "Pós-evento" no evento. Público em 375×812:
  `/catalogo/avaliar/<token>` → enviar nota → bloco de consentimento e "Indicar uma amiga".
- Apagar os temporários antes do commit.

## 4. Portões

```powershell
.venv\Scripts\ruff.exe check <arquivos tocados>
cd frontend; npm run typecheck
```
