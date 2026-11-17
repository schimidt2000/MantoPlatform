# Quickstart — validar a 349

## Pré-requisitos

- Worktree `.claude/worktrees/349-comercial-mede-e-fecha-4ea0ce`, branch `349-comercial-mede-e-fecha`.
- Banco **`manto_349`** (espelho do dump noturno de 17/11). A URL fica em `.local-db-url` do worktree (ignorado pelo
  git). Nunca o `manto_local` nem a produção.
- `.venv` e `frontend/node_modules` como junção para o checkout principal.

## 1. Migration

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
.venv\Scripts\flask.exe db upgrade
```

Esperado: `alembic_version = a349c0e1f2a3`; `\d conversas` com as 13 colunas de `data-model.md`.

## 2. Verify

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
.venv\Scripts\python.exe specs\349-comercial-mede-e-fecha\verify_349.py
```

Esperado: os 18 cenários da spec em OK, inclusive os três de recusa (5, 13, 17) passando por recusarem.

## 3. Portões

```powershell
.venv\Scripts\ruff.exe check <arquivos Python tocados>
cd frontend; npm run typecheck
```

## 4. Telas (Browser pane)

Backend próprio na **5349** (cópia de `scripts/db/run-local-sem-google.py` com a porta trocada, no scratchpad) e Vite
na **6349** (`vite.config` temporário com o proxy para a 5349, fora do commit). Usuários descartáveis de fixture; login
por `fetch('/api/auth/login')` no console da aba.

1. `/conversas` em 390 × 844: selos na lista, os três recortes (sem rolagem lateral), "Orçamento parado" com 2/5/9.
2. Conversa aberta: faixa da venda (etapa, qualificação com os sinais, 1ª resposta com e sem autor), "Marcar como
   perdida" com o motivo "Outro" sem frase (erro no campo) e com frase, "Reabrir", "Lembrar amanhã" e "Cancelar
   lembrete", "Criar evento".
3. Envio de orçamento → "Fazer orçamento" → calculadora com o nome e a faixa → "Gerar orçamento" → volta à conversa com
   o envio aberto e o orçamento escolhido.
4. `/events/new?orcamento_id=…&conversa=…`: ficha como Contratante e vendedor = responsável da conversa.
5. `/funil`: cartões de primeira resposta, qualificadas e perdidas; colunas novas na tabela por vendedor; "Pararam em"
   com selos e "Lembrar amanhã".
