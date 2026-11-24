# Quickstart — validar a feature 360

Tudo a partir da worktree `C:\tmp\mp360` (branch `360-conferencia-de-personagens`).

## Pré-requisitos

- Espelho `manto_360` restaurado de `backups/manto_2026-11-24_0200.dump`; URL em `.local-db-url`
  (não versionado).
- `.venv` e `frontend/node_modules` ligados por junção ao checkout principal.

## 1. Migration

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:FLASK_APP = 'app:create_app'; .venv\Scripts\python.exe -m flask db upgrade
```

Esperado: `f353a1b2c3d4 -> f360a1b2c3d4`; as duas tabelas existem e estão vazias.

## 2. Verify

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe specs\360-conferencia-de-personagens\verify_360.py
```

Esperado: 18 cenários verdes (ver a tabela da [spec](./spec.md)); ao fim, as tabelas da conferência
voltam vazias e as do catálogo têm a mesma contagem de antes. `--manter` deixa a leitura carregada
para a conferência de tela.

## 3. Portões

```powershell
cd frontend; npm run typecheck
```

```powershell
.venv\Scripts\python.exe -m ruff check app/admin/catalog_conferencia_ops.py app/api/admin_catalogo_conferencia_read.py app/api/admin_catalogo_conferencia_write.py app/models.py migrations/versions/f360a1b2c3d4_conferencia_de_personagens.py
```

## 4. Tela

Backend e Vite próprios da worktree em outra porta (memória "conferir tela em worktree"), login de
Superadmin descartável, e abrir `/admin/catalogo/conferencia` a 390×844 e em tela larga:

1. fila com contadores e filtros; "Continuar conferência";
2. um tema (recortes, corrigir nome, trocar ficha, "Não criar", "Criar sem foto", acrescentar e excluir);
3. um avulso e um genérico (um toque em "Conferir e ir para o próximo");
4. reabrir um conferido; tentar editar conferido (recusa visível);
5. busca "frozen" e filtro por tipo e situação; recarregar e voltar ao mesmo ponto.

## 5. Depois do deploy (quando o dono pedir o push)

1. Sonda: `GET /api/admin/catalogo/conferencia` devolve JSON (401 sem sessão já prova o Flask vivo).
2. Com a sessão do Superadmin, abrir a tela e acionar "Carregar leitura" uma vez.
3. Conferir os contadores contra a regra da fila na produção.
