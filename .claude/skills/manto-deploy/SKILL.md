---
name: manto-deploy
description: >
  Publicar uma mudança da Manto (merge na main + push = deploy automático no Render, ~60s) e
  operar a produção (SSH/Shell do Render, startCommand, sondagem, rollback). Use quando o dono
  disser "push", "sobe", "publica", "deploy", "roda em produção", ou para conferir se a produção
  está no ar. Regra normativa: constituição §Operação e Deploy. Detalhe técnico: docs/01 §5.3.
  Procedimento: DEVELOPMENT.md §Publicar e §Operar a produção.
---

# manto-deploy — publicar e operar a produção (Render)

## "Push" significa produção

`autoDeploy: true` nos dois serviços do `render.yaml`: push na `main` publica em ~60s, sem
staging. "Push" = merge da branch na `main` (merge commit, estilo `merge: NNN — …`) +
`git push origin main`. Parar no push da branch não é entregar. Só publique quando o dono pedir.

## Antes do merge

1. Portões da constituição verdes (typecheck das três SPAs, `ruff`, `verify_NNN.py`, tela aberta).
2. `git status --short` limpo; `migrations/versions/` sem untracked — migration fora do commit não
   existe para o `flask db upgrade` do start.
3. Migration destrutiva? Ensaio em banco descartável com dump fresco (`DEVELOPMENT.md`
   §Migrations).
4. Tocou o `startCommand` do `render.yaml`? `python scripts/validar_startcommand.py` verde e
   **commit sozinho**, fora do horário, com os Events do Render abertos.
5. Horário: publicar em lote e fora do expediente (~19h BRT em diante). Cada deploy abre ~1 min
   de 502 na porta pública (o `manto-frontend` não tem healthcheck); a calculadora de orçamento
   dispara request a cada tecla e é a primeira a sangrar.

## Publicar

```powershell
git checkout main; git merge --no-ff NNN-nome -m "merge: NNN — <título>"; git push origin main
```

Depois: Events do Render abertos nos dois serviços, e a sonda do BACKEND por um endpoint `/api/`:

```powershell
curl.exe -s https://app.mantoproducoes.com.br/api/formularios/comum/schema
```

JSON = Flask no ar e migration aplicada (o start é `flask db upgrade && python seed.py &&
gunicorn`). **Nunca** use `/health` na URL pública: não está em `BACKEND_PREFIXES`, cai no
fallback da SPA e devolve 200 com o Flask morto. 502 isolado nos primeiros minutos é troca de
container — repita antes de investigar. `curl -w '%{http_code}' || echo 000` vira `000000` em
falha e finge que voltou.

Antes de dizer "está em produção": `git log --oneline -1` = cabeçalho do `docs/03`.

## Se caiu

- `git revert <merge>` + push (rollback = novo deploy). Nunca `--force`.
- Antes de empurrar um segundo deploy às cegas, peça ao dono o log de Events/Logs do painel.
- Assinatura "CPU parada + p99 alto + 0% de erro" = requisição presa segurando thread do gunicorn,
  não carga; o 502 nasce no proxy Node (`docs/01` §5.3).

## Operar a produção

- SSH: `ssh -i ~/.ssh/render_manto_ed25519 srv-da8o06on74is73ehf4q0@ssh.oregon.render.com`
  (backend — tem o disco e o `flask`); o frontend é `srv-da8nvsgn74is73ehe9a0`. Plano B: Shell do
  painel do Render (alguns scripts o classificador bloqueia por SSH). A sessão já vem com as env
  vars do serviço.
- Comando de app: `cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD
  .venv/bin/flask <cmd>` — sem `MANTO_SEM_THREADS` o `create_app()` sobe o auto-import de
  talentos (escreve no banco), o sync da agenda e o backup; sem `PYTHONPATH` o Python 3.11 não
  põe o CWD no `sys.path`.
- Rodada longa: `setsid nohup … > instance/x.log &` **só sem push na fila** — deploy troca o
  container (mata `nohup`, limpa `/tmp`, que é RAM: temporário grande vai para `instance/`,
  `_tmp_no_disco()`).
- Comandos de mídia (`fix-heic → compress-images → warm-thumbnails`, `midia-orfa`) rodam LÁ, com
  dry-run antes de `--execute`; o conjunto de arquivos local é outro.
- Bug com dado real: dump noturno (`backups/manto_AAAA-MM-DD_0200.dump`) restaurado em banco
  descartável — nunca conexão direta na produção.
- Env nova: quem preenche o painel é o dono; mudar env redeploya (janela de 502). Até lá a
  feature está desligada e registrada em `docs/05`.
