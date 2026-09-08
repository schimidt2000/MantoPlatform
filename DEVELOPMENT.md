# Guia de Desenvolvimento — Manto Platform

O sistema está em produção no **Render** desde 28/08/2026 (auto-deploy do GitHub: todo push na
`main` dispara build e deploy, ~60s). O blueprint é o `render.yaml` na raiz — é o único arquivo que
descreve produção. A conta do Railway foi banida em definitivo em 28/08/2026; nenhuma instrução
antiga que o cite continua válida (história em `docs/03`, entrada 264; registro do incidente em
`docs/CONTINGENCIA_RENDER.md`).

Este guia é o **como**: rodar localmente, escrever a verificação, publicar e operar a produção.
Princípios e portões: `.specify/memory/constitution.md`. Regras de trabalho do agente:
`CLAUDE.md`. Contrato técnico do deploy: `docs/01_SISTEMA_E_BANCO.md` §5.

---

## Branches

| Branch | Propósito |
|--------|-----------|
| `NNN-nome-da-feature` | Nível 1 (feature): criada pelo `/speckit-specify` (o hook `before_specify` aloca o `NNN` e faz o `git checkout -b`) |
| `NNNb-nome` | Nível 2 (correção): criada à mão a partir da `main`, herdando o número da feature que conserta |
| `main` | Produção — todo push dispara deploy no Render |

**Merge na `main` é o deploy.** Trabalhe sempre numa branch; só faça o merge com a mudança
verificada (portões da constituição) e quando o dono pedir. A branch `dev` que existia como
"tronco de desenvolvimento" morreu em 23/04/2026 (887 commits atrás da `main`) e foi apagada —
não a recrie.

```bash
# Nível 1 — o /speckit-specify cria a branch NNN-nome e a pasta specs/NNN-nome/ (não faça à mão)

# Nível 2 — correção pequena
git checkout main && git pull
git checkout -b 267b-nome-curto            # herda o número da feature que conserta
# ... trabalha, verifica ...
git add caminho/do/arquivo                 # nunca `git add -A`: a raiz tem tokens e untracked
git commit -F mensagem.txt                 # mensagem multi-linha por arquivo (PowerShell 5.1)

# Publicar (só quando o dono pedir — é produção)
git checkout main
git merge --no-ff 267b-nome-curto -m "merge: 267b — título"
git push origin main                       # Render detecta e deploya em ~60s
```

---

## Como nasce uma mudança (constituição, Princípio VI)

| | Nível 1 — FEATURE | Nível 2 — CORREÇÃO |
|---|---|---|
| Quando | migration, endpoint novo, tela nova, mais de um domínio, ou o dono chamou de feature | hotfix de feature entregue; ajuste pequeno num domínio sem migration; só docs/harness |
| Número | `/speckit-specify` aloca `max(specs/, branches, refs remotos) + 1` | pasta `specs/NNNb-nome/` à mão (sufixo da feature-mãe) |
| Comandos | `/speckit-specify` → `-clarify` → `-plan` → `-checklist` → `-tasks` → `-analyze` → `-implement` → `-converge` | só `/speckit-clarify` (os demais exigem `plan.md`) |
| Artefatos | `spec.md`, `plan.md`, `tasks.md`, `checklists/`, `verify_NNN.py` | `spec.md` curto, `verify_NNNb.py` se toca comportamento |
| Sempre | entrada no topo de `docs/03` + docs por fonte única + portões | idem |

- `.specify/feature.json` é o ponteiro que todos os scripts do Spec Kit leem. O `/speckit-specify`
  o grava; no Nível 2 aponte-o à mão (`{"feature_directory": "specs/NNNb-nome"}`). Nunca apague.
- Os sufixos `b`/`c` são ignorados pelo alocador: hotfix não consome número. `docs/03` registra a
  entrega, não reserva número; plano que enumera trabalho futuro usa números provisórios.
- Commits: `feat(NNN):`, `fix(NNNb):`, `docs(NNN):`, `chore(NNN):`, `merge: NNN — …`.

---

## Rodando localmente

### Pré-requisitos

```bash
pip install -r requirements.txt -r requirements-dev.txt   # ruff vem no -dev
cd frontend && npm install                                  # workspaces: 3 apps + 3 pacotes
```

### Banco: `manto_local`, a cópia da produção

Sem `DATABASE_URL`, o app cai em SQLite (`app/config.py`). Isso serve só para o app subir —
**nenhuma verificação vale nesse modo** (constituição, Stack e Portões). Desenvolvimento e
verificação rodam contra `manto_local`, a cópia local do Postgres de produção.

`scripts/db/` **não é versionado** (contém caminhos e credenciais locais). O que ele contém:

| Script | Faz |
|---|---|
| `run-local.ps1` | define `DATABASE_URL` a partir de `.local-db-url` e sobe o Flask (`python run.py`) |
| `refresh-local-db.ps1 [-Fresh]` | restaura o dump mais recente em `manto_local`; `-Fresh` baixa um dump novo da produção antes |
| `backup-railway.ps1` | nome herdado — dumpa o Postgres **do Render** (URL externa em `.railway-db-url`) para `backups/manto_<data>.dump`; roda sozinho às 02:00 pela Tarefa Agendada |
| `verify_<n>.py` (antigos) | verificações anteriores à 266; as novas vivem em `specs/NNN-nome/` |

Segredos de banco ficam em `.local-db-url` (local) e `.railway-db-url` (produção; nome herdado) —
ambos gitignored.

### Subir o app

```powershell
$env:MANTO_SEM_THREADS = '1'; $env:FLASK_ENV = 'development'   # SEMPRE — ver abaixo
.\scripts\db\run-local.ps1
```

Ou pelo Browser pane (`.claude/launch.json`): `manto-backend-local` (5000, já com as duas
variáveis), `manto-internal` (5173), `manto-portal` (5174), `manto-public` (5175),
`manto-prod-server` (3000, `frontend/server.js`).

⚠️ **O `manto_local` é espelho FIEL da produção**: traz `SiteSetting.google_token`, as
credenciais de e-mail e as flags ligadas. Um processo apontado para ele **escreve no calendário
real** (`eventos@mantoproducoes.com.br`) e manda e-mail para artista de verdade. As travas
`_suppress_mail` / `_suppress_calendar_invites` (`app/config.py`) derivam do host do banco e
cobrem e-mail e convite; `MANTO_SEM_THREADS=1` desliga as threads de fundo (auto-import de
talentos, sync da agenda, backup) e `FLASK_ENV=development` segura o resto. Integração nova
precisa da própria trava (constituição XIV).

### Frontend

```powershell
cd frontend
npm run dev:internal        # staff (proxy Vite /api → Flask local; rode o backend em paralelo)
npm run dev:public          # visitante anônimo (catálogo, /cadastro, formulários, loja)
npm run dev:portal          # Portal do Artista (mobile-first)
npm run typecheck           # UM comando, cobre os três apps — nunca `npx tsc --noEmit` app a app
npm run build               # produção (os três apps)
```

Cada app precisa do SEU proxy de mídia no `vite.config.ts` (`/uploads`, `/catalogo/midia`,
`/catalogo/og`, `/portal/photo`); rota do React Router que compartilha prefixo com rota Jinja
(`/figurinos`) só entra por regex escopada ao sub-path.

---

## Variáveis de ambiente

O `.env` local (nunca commitado) carrega via `python-dotenv` **apenas em `run.py`** —
`python script.py` não o lê. Modelo comentado: `.env.example`. O que o código lê está em
`app/config.py` (`os.getenv`).

| Variável | Local | Produção (Render) |
|----------|-------|-------------------|
| `FLASK_ENV` | `development` | `production` |
| `DATABASE_URL` | `manto_local` (de `.local-db-url`) | injetada pelo `manto-postgres` (`fromDatabase`) |
| `MANTO_SEM_THREADS` | `1` em todo script e no preview | só em comando de manutenção no Shell/SSH |
| `SECRET_KEY` | qualquer valor | chave segura (`sync: false`) |
| `MAIL_*` | supressão automática (banco em localhost); `MAIL_ALLOW_LOCAL_SEND=true` só de propósito | reais (`sync: false`) |
| `PORTAL_URL` | `http://localhost:5000` (opcional) | **não definir** — o default é `PORTAL_BASE_URL` (`https://portal.mantoproducoes.com.br`); valor local é ignorado por quem envia e-mail de verdade (269b) |
| `PUBLIC_BASE_URL` | (ausente) | **não definir** — default `PLATFORM_BASE_URL` |
| `GOOGLE_OAUTH_REDIRECT_URI` | `http://localhost:5000/google/callback` | URL pública registrada no Google Cloud Console + `/google/callback` (`sync: false`) — nunca copiar o valor local |
| `GOOGLE_CLIENT_ID/SECRET`, `GOOGLE_MAPS_API_KEY` | do `.env` | `sync: false` |
| `SESSION_COOKIE_DOMAIN` | (ausente) | **não definir** — cookie host-only basta; trocar o domínio é mudança de duas partes (`SESSION_COOKIE_DOMINIOS_OBSOLETOS`) |
| `CORS_ALLOWED_ORIGINS` | (ausente) | lista dos domínios públicos (`render.yaml`) |
| `AUDIT_AGENT_TOKEN`, `MARKETING_AGENT_TOKEN` | arquivos `.audit-agent-token` / `.marketing-agent-token` | `sync: false` — **hoje ausentes no painel** (os agentes semanais respondem 404; pendência em `docs/05`) |
| `BACKUP_DRIVE_FOLDER_ID` | (ausente = backup desligado) | id do Drive compartilhado |
| `USE_S3` | `false` | `false` — os arquivos moram no disco persistente do `manto-backend` |

Regra: **nunca copiar o `.env` inteiro para o painel** — foi assim que `PORTAL_URL=localhost`
entrou em produção e todo link de e-mail saiu morto (269b). Os `sync: false` são preenchidos um a
um pelo dono.

### Google OAuth em desenvolvimento

O Google OAuth exige que a URI de redirecionamento esteja registrada no Console do Google. Para
usar localmente:

1. Acesse [console.cloud.google.com](https://console.cloud.google.com) → seu projeto →
   **APIs & Serviços → Credenciais**
2. Edite o **OAuth 2.0 Client ID**
3. Em **URIs de redirecionamento autorizados**, adicione: `http://localhost:5000/google/callback`
4. O `.env` local já aponta para essa URI:
   ```
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost:5000/google/callback
   ```

---

## Migrations

Migrations são **escritas à mão**. Copie o cabeçalho de uma migration recente em
`migrations/versions/`, ponha `down_revision` = head atual (`flask db heads`), escreva `upgrade()`
e `downgrade()` com **só a mudança da sua feature**, e aplique no `manto_local`:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
python -m flask db heads
python -m flask db upgrade
```

**Nunca rode `flask db migrate`** (autogenerate; está em `deny` no `.claude/settings.json`):
`flask db check` acusa um drift antigo entre `models.py` e o banco (índices, FKs, a UNIQUE de
`clients.phone`) que não é seu — ele entraria na migration e o `flask db upgrade` do start
derrubaria a produção. Commite o arquivo da migration junto do código que a motivou e confira
que não ficou untracked.

### Ensaio de migração destrutiva (obrigatório antes do merge)

O `manto_local` já está migrado e não prova nada sobre o estado da produção. Antes de mergear
uma migration que apaga, altera ou cria UNIQUE:

1. Dump fresco da produção (`.\scripts\db\backup-railway.ps1`).
2. `psql -c "CREATE DATABASE manto_preflight"` + `pg_restore --no-owner --no-privileges` do dump
   (URL com esquema `postgresql+psycopg://`).
3. `DATABASE_URL=<preflight>` e a sequência real do deploy: `flask db upgrade` e `python seed.py`.
4. Exercite os dados que só existem lá; guarde um recorte pré-migração em arquivo.
5. Drope o banco descartável (é cópia de dados reais).

---

## Escrever um `verify_<n>.py` (constituição, Princípio VIII)

Vive em `specs/NNN-nome/verify_NNN.py`, versionado. Modelo: `specs/266-costuras-funil/verify_266.py`.
Skill: `manto-verify`.

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
.venv\Scripts\python.exe specs\NNN-nome\verify_NNN.py
```

Esqueleto:

- docstring com os cenários e o comando; `sys.stdout.reconfigure(encoding="utf-8")`;
  `REPO_ROOT` no `sys.path`; `FLASK_ENV`/`DATABASE_URL` com `setdefault`;
- `app = create_app()`; `TESTING = True`; `RATELIMIT_ENABLED = False`;
- **conexão separada** (`create_engine(DATABASE_URL)` + `_no_banco(sql)`) para TODA asserção de
  escrita — o autoflush da sessão do app esconde falta de commit (hotfix 257);
- usuário descartável com `set_password()` e login **só** por `POST /api/auth/login` — sessão
  montada com `session_transaction()` devolve 401;
- setup de banco dentro de `app.app_context()`, requisições HTTP **fora** dele — contexto
  persistente faz o `g` sobreviver e `/api/auth/me` responde 200 até para cookie inválido;
- teste de cookie (duplicado, domínio, ordem) exige `app.test_client(use_cookies=False)` — o
  test_client reescreve o cabeçalho a partir do próprio jar;
- um cenário que **deve falhar** (papel sem permissão → 403/404);
- limpeza no `finally`: `db.session.rollback()` → `user.roles.clear()` → `db.session.delete(user)`
  (delete em massa estoura a FK de `user_roles`);
- prefixo único nos dados (`__vNNN_`); saída `N/N OK`; código de retorno 1 se algo falhou.

Fixtures que não explodem: nunca criar `EventRole` com `character_name` inventado (o sync do
Google apaga a role e dispara e-mail de remoção a artista real — assuma role com
`talent_id IS NULL`); datas distantes para isolar cenários de agenda; excluir show cascateia para
ensaios.

### Estado conhecido do `manto_local`

- `SiteSetting.manto_address` costuma ter lixo de verify antigo → toda conta de distância devolve
  400 "Endereço não encontrado pelo Google Maps". Restaure um endereço real (ou
  `refresh-local-db.ps1`) antes de suspeitar do código.
- `SiteSetting.google_maps_api_key` está vazia no espelho; a chave vem do `.env`, que script cru
  não lê.
- A senha do SUPERADMIN local muda a cada verify (eles chamam `set_password`): redefina, não peça.

---

## Publicar (skill `manto-deploy`)

1. Portões da constituição verdes: `cd frontend && npm run typecheck`, `ruff check` nos tocados,
   `verify_NNN.py`, tela aberta, docs por fonte única.
2. `git status --short` limpo; `migrations/versions/` sem untracked.
3. Tocou o `startCommand` do `render.yaml`? `python scripts/validar_startcommand.py` verde e
   **commit sozinho**, fora do horário, com os Events do Render abertos.
4. Horário: em lote e fora do expediente (~19h BRT em diante). Cada deploy abre ~1 min de 502 na
   porta pública (o `manto-frontend` não tem healthcheck).
5. Merge na `main` + `git push origin main`. Acompanhe os Events dos dois serviços.
6. Sonda o **backend** por um endpoint `/api/`:
   ```powershell
   curl.exe -s https://app.mantoproducoes.com.br/api/formularios/comum/schema
   ```
   JSON = Flask no ar e migration aplicada. **Nunca** `/health` na URL pública (cai no fallback da
   SPA e devolve 200 com o Flask morto). 502 isolado nos primeiros minutos é troca de container —
   repita. `curl -w '%{http_code}' || echo 000` vira `000000` em falha.
7. Caiu? `git revert <merge>` + push. Antes de um segundo deploy às cegas, peça ao dono o log do
   painel.

---

## Operar a produção (Render)

- **SSH**: `ssh -i ~/.ssh/render_manto_ed25519 <srv-id>@ssh.oregon.render.com` — ids e o mapa do
  disco em `docs/01` §5.3. O backend tem o disco (`/opt/render/project/src/instance`) e o
  `.venv/bin/flask`; a sessão já vem com as env vars do serviço. Plano B: Shell do painel.
- **Comando de app**: `cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD
  .venv/bin/flask <cmd>` — sem `MANTO_SEM_THREADS` sobem auto-import de talentos (escreve no
  banco), sync da agenda e backup; sem `PYTHONPATH` o 3.11 não põe o CWD no `sys.path`.
- **Rodada longa**: `setsid nohup … > instance/x.log &` só sem push na fila — deploy troca o
  container (mata `nohup`, limpa `/tmp`, que é RAM: temporário grande vai para `instance/`).
- **Mídia**: `flask fix-heic → compress-images → warm-thumbnails` e `midia-orfa` rodam LÁ, com
  dry-run antes de `--execute`; o conjunto de arquivos local é outro.
- **Bug com dado real**: dump noturno (`backups/manto_AAAA-MM-DD_0200.dump`) restaurado em banco
  descartável — nunca conexão direta na produção. Timestamps do banco são UTC.
- **"Não consigo acessar"**: exonere o servidor em três níveis com a sessão REAL da pessoa (ops
  direto no ORM; gunicorn no ar; caminho público com cookie assinado) antes de culpá-lo — na 294 o
  defeito era o portal engolir o motivo.
- **Env nova**: o dono preenche o painel; mudar env redeploya (janela de 502).

---

## Estado do repositório nesta máquina

- Vivo e **não versionado**: `scripts/db/`, `scripts/oneoff/`, `.env`, `.local-db-url`,
  `.railway-db-url`, `.audit-agent-token`, `.marketing-agent-token`, `recuperacao/`, `backups/`,
  `instance/`. "Pode apagar que o git guarda" é falso para tudo isso — mova para
  `Desktop\Manto_Platform_arquivo\` (nada foi apagado na limpeza de 19/08/2026; está lá).
- A pasta é sincronizada pelo Google Drive Desktop (`.tmp.drive*` na raiz). Se for intencional,
  exclua `.git/`, `instance/` e `backups/` do sync — são segredos e dados reais.

---

## Estrutura de módulos

Mapa completo: `docs/00_MAPA_DO_SISTEMA.md` §3. Em resumo: `app/api/<dominio>_read.py` |
`_write.py` = endpoints JSON (registrados em `app/api/__init__.py`); `app/<dominio>/<nome>_ops.py`
= núcleo de negócio puro; `app/<dominio>/routes.py` = resíduo Jinja (remoção pausada);
`frontend/apps/{internal,public,portal}` + `frontend/packages/{ui,api-client,money}`.
