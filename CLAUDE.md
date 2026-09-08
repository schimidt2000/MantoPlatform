# CLAUDE.md — como trabalhar na Plataforma Manto

Lido automaticamente pelo Claude Code. Aqui moram só **regras de trabalho e ponteiros**. Fatos do
sistema: `docs/00..05`. Princípios e portões: `.specify/memory/constitution.md` (v3.0.0 — em
conflito, ela prevalece). Como rodar, publicar e operar: `DEVELOPMENT.md`.

## 0. Antes de qualquer tarefa

* Leia `docs/00_MAPA_DO_SISTEMA.md` §4 (RBAC), §5 (convenções), §6 (armadilhas transversais) e
  §9 (como se verifica) — ~5k tokens. A tabela do §8 diz o que mais abrir por tipo de tarefa.
* Orçamento de leitura: nunca abra `docs/03_HISTORICO_MUTACOES.md` nem `docs/historico/*`
  inteiros — ache a feature no índice e leia só a entrada (`Read` com `offset`/`limit`).
  `app/models.py`, `app/calendar/routes.py`, `app/financeiro/routes.py` e
  `app/marketing/virtuais_ops.py` não têm índice: `Grep` e depois `Read` com `offset`.
* Uma fonte por tipo de fato (`docs/00` §10): escreva o fato num documento e aponte dos outros.
  Citação `arquivo:linha` se confere contra HEAD (`git show HEAD:<arquivo>`), não contra o disco.
* Antes de qualquer `/speckit-*`, `.specify/feature.json` tem de apontar para a pasta em que
  você está trabalhando. Nunca apague o arquivo: sem ele os scripts abortam.

## 1. O projeto em cinco linhas

* ERP de produtora de eventos; a agenda é o centro. Flask = API JSON estrita em `/api/*`. Três
  SPAs React (`frontend/apps/{internal,public,portal}`) sobre três pacotes
  (`frontend/packages/{ui,api-client,money}`), servidas por `frontend/server.js`, que faz proxy
  para o Flask. Topologia e domínios: `docs/00` §2-§3.
* Banco: PostgreSQL em produção (Render) e `manto_local` (Postgres, espelho da produção) em
  desenvolvimento. O fallback SQLite de `app/config.py` só faz o app subir — não vale para
  verificar nada.
* Fonte única no código: dinheiro via `@manto/money`; arquivo do Flask via `assetUrl()`; núcleo
  de negócio em `app/<dominio>/<nome>_ops.py` (puro, sem `flask.request`); endpoint em
  `app/api/<dominio>_{read,write}.py` só valida RBAC (função no início da view, não decorator),
  chama `*_ops` e serializa. Não existe camada de repositório; não crie uma. Onde isso NÃO vale
  (calendar, financeiro): `docs/00` §7 — não refatore sem ler.
* Rota pública nova fora de `/api` exige entrada em `BACKEND_PREFIXES` (`frontend/server.js`);
  módulo novo em `app/api/` só existe se importado em `app/api/__init__.py`; componente novo em
  `@manto/ui` só existe se exportado em `packages/ui/src/index.ts`. Nada disso acusa erro.
* O Jinja legado está registrado e VIVO em parte dos domínios; a remoção está pausada por decisão
  do dono (`docs/PARADA_REMOCAO_JINJA.md`). Código novo nunca devolve HTML; código velho não se
  "limpa" de passagem.

## 2. Ambiente e produção (Render)

* Produção = **Render** desde 28/08/2026 (Railway banido em definitivo — só história, `docs/03`
  264). O único arquivo que descreve produção é `render.yaml`: `manto-backend` (python, gunicorn,
  disco persistente em `/opt/render/project/src/instance`, `healthCheckPath: /health`),
  `manto-frontend` (node, `server.js`, SEM healthcheck), `manto-postgres`. Detalhe: `docs/01` §5.
* **Push na `main` É o deploy** (`autoDeploy: true`): ~60s até o bundle novo, com ~1 min de 502
  na porta pública. Não há staging. Só publique quando o dono pedir ("push", "sobe", "publica");
  "push" significa merge na `main` + `git push origin main`, não push da branch. Skill
  `manto-deploy`.
* Publicar = agrupar num deploy só, fora do horário da equipe (a partir das ~19h BRT). A
  calculadora de orçamento dispara request a cada tecla e é a primeira a sangrar.
* Mudança no `startCommand` do `manto-backend` vai em commit sozinho, fora do horário, com os
  Events do Render abertos, depois de `python scripts/validar_startcommand.py` verde. Serviço
  com disco não sobrepõe deploy: start que falha = produção fora.
* Backend vivo se prova por um endpoint `/api/` devolvendo JSON, nunca pelo `/health` na URL
  pública (cai no fallback da SPA e responde 200 com o Flask morto). 502 isolado nos minutos
  após o push é troca de container, não regressão — repita a sondagem.
* Comando de manutenção em produção roda no `manto-backend` (SSH ou Shell do Render) com
  `MANTO_SEM_THREADS=1` na frente; deploy troca o container (mata `nohup`, limpa `/tmp`, que é
  RAM). Receita: `DEVELOPMENT.md` §Operar a produção.
* Variável de ambiente nova nasce desligada em produção (foi assim que `AUDIT_AGENT_TOKEN` e
  `MARKETING_AGENT_TOKEN` sumiram na migração): default real em `app/config.py`, env só sobrepõe.

## 3. Como o trabalho flui (esteira em dois níveis — constituição VI)

* O número nasce em `specs/`: Nível 1 pelo `/speckit-specify` (o hook cria a branch `NNN-nome`,
  a skill cria `specs/NNN-nome/` e o ponteiro); Nível 2 pela pasta criada à mão. `docs/03`
  registra a entrega, não reserva número. Hotfix de feature entregue herda o número com sufixo
  (`267b`, `269c`).
* **Nível 1 — FEATURE** (migration, endpoint novo, tela nova, mais de um domínio, ou o dono
  chamou de feature): `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` →
  `/speckit-checklist` → `/speckit-tasks` (verify ANTES do núcleo) → `/speckit-analyze` →
  `/speckit-implement` → `/speckit-converge` → portões (§4) → docs (§6) → merge quando o dono
  pedir. Comandos com HÍFEN; `/speckit.plan` não existe.
* **Nível 2 — CORREÇÃO** (hotfix de feature entregue; ajuste pequeno sem migration num domínio;
  docs/harness): pasta `specs/NNN[b]-nome/` com `spec.md` curto (Branch · Created · Status ·
  Migration; O pedido; O que muda; Verificação; Fora de escopo), branch da `main`,
  `verify_NNN[b].py` se toca comportamento, entrada no `docs/03`. Só `/speckit-clarify` se
  aplica; os outros exigem `plan.md` e abortam. Cresceu (migration, segundo domínio)? Vira
  Nível 1 antes de codar.
* Commits: `feat(NNN):`, `fix(NNNb):`, `docs(NNN):`, `merge: …` — mensagem multi-linha por
  arquivo (§7). **Nunca `git add -A`**: a raiz tem untracked não ignorado e tokens
  (`.audit-agent-token`, `.marketing-agent-token`, `.railway-db-url`). Adicione por caminho.
* Antes de dizer "está em produção": `git status --short` limpo, `git log --oneline -1` batendo
  com o cabeçalho do `docs/03`, `migrations/versions/` sem untracked, sonda `/api/` com JSON.

## 4. Verificação (a lista normativa é a constituição §Portões de Qualidade)

* Não há pytest nem `tests/`. Verificação = `specs/NNN-nome/verify_NNN.py` contra `manto_local`
  (os anteriores à 266 vivem em `scripts/db/`, que é gitignored). Esqueleto e armadilhas: skill
  `manto-verify` e `DEVELOPMENT.md` §Escrever um verify.
* Todo script que chama `create_app()` roda com
  `$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development';
  $env:MANTO_SEM_THREADS = '1'` — o `.env` não é lido por `python script.py`. Sem isso sobem as
  threads de fundo, e o `manto_local` traz token do Google e credenciais de e-mail REAIS: escreve
  no calendário da empresa e manda e-mail para artista. As travas `_suppress_mail` /
  `_suppress_calendar_invites` (`app/config.py`) cobrem só e-mail e convite.
* Verify de escrita confere por conexão separada (o autoflush esconde falta de commit); login só
  por `POST /api/auth/login`; requisições FORA de `app.app_context()`; cookie montado à mão exige
  `test_client(use_cookies=False)`; todo verify de autorização tem um cenário que DEVE falhar.
* Nunca semeie `EventRole` com `character_name` inventado: o sync do Google apaga a role e
  dispara e-mail de remoção a gente de verdade. Assuma role existente com `talent_id IS NULL`.
* `cd frontend && npm run typecheck` (um comando, três SPAs); `ruff check` nos arquivos tocados;
  `ruff format` só em arquivo novo. `tsc` limpo não é verificação de UI: abra a tela (skill
  `manto-conferir-tela`); superfície pública em viewport mobile.
* Migration é escrita à mão (`flask db migrate` é proibido e está em `deny`: o drift antigo
  entraria e derrubaria o `startCommand`). Migração destrutiva: ensaio em banco descartável com
  dump fresco, rodando `flask db upgrade && python seed.py` na ordem real — `DEVELOPMENT.md`
  §Migrations.

## 5. Código

Regras de Python, TypeScript e UI: constituição §II, §V, §X–§XII — não repetidas aqui.
Comentário explica o PORQUÊ, em pt-BR. Contrato de erro da API é o envelope de `json_error`
(`docs/00` §5).

## 6. Documentação viva (ao fechar o ciclo)

Uma fonte por fato (`docs/00` §10): contrato/schema/deploy → `docs/01`; tela → `docs/02`;
motivação, decisão, pegadinha → `docs/03` (append-only: entrada nova no topo + linha na tabela do
índice; correção é entrada nova referenciando a antiga); fluxo/invariante de domínio → `docs/04`;
dívida → `docs/05` (risque o que quitou, registre o que criou). `docs/00` só se mudou topologia,
RBAC ou convenção; `docs/01` §5 só se mudou deploy/infra.

## 7. Ferramental nesta máquina (Windows 11 · PowerShell 5.1 · Git Bash)

* Edição de arquivo é SEMPRE pelo Edit/Write tool. `Get-Content -Raw` + `-replace` +
  `Set-Content` regrava UTF-8 como mojibake (`período` → `perÃ­odo`) e acrescenta BOM; `tsc` e
  `ruff` não acusam.
* Commit multi-linha: mensagem em arquivo do scratchpad + `git commit -F <arquivo>` (here-string
  com aspas duplas vira pathspec). Idem `gh pr create --body-file`.
* Heredoc do Bash come uma barra invertida de cada par (`[\\/]` chega como `[\/]`): prefira o
  Write tool; se usar heredoc, confira o disco (`cat -A`) antes de rodar. Script combinado grande
  no Bash pode nem executar (erro de parse) — chamadas curtas.
* `PYTHONUTF8=1` na frente de qualquer Python que imprima acento (console em cp1252).
* Sondar HTTP: `Invoke-WebRequest -SkipHttpErrorCheck` não existe no PS 5.1 (vira falso "SEM
  RESPOSTA"); capture `[System.Net.WebException]`. `curl -w '%{http_code}' || echo 000` vira
  `000000` e finge que voltou. Confirme queda por duas sondagens antes de "consertar" produção.
* Nunca apague untracked — mova (`Desktop\Manto_Platform_arquivo\` ou `scripts/oneoff/`): boa
  parte do repo é viva e não versionada (`scripts/db/`, `.env`, `recuperacao/`, tokens,
  `backups/`).

## 8. Autonomia

* Vá direto ao ponto; sem preâmbulo nem resumo do que acabou de fazer. Spec ambígua: pergunte
  antes do plano. Commits pequenos; `tasks.md` sem passos inventados.
* Escopo focado: não implemente o que não está no `tasks.md`/spec; sem refatoração lateral.
  Isso NÃO vale para verificação — os portões (§4) são obrigatórios mesmo que o `tasks.md` não
  os liste.
* Delegação: subagente para LEITURA ampla e paralelizável (mapear N domínios, auditar o repo
  contra uma regra, achar consumidores de um contrato — devolve achados com arquivo:linha).
  Implementação, migration e decisão de arquitetura são suas; subagente não edita arquivo.
* Não repita a mesma tentativa mais de duas vezes: pare, explique o que tentou e reformule.

## 9. Skills de projeto

`manto-verify` (escrever/rodar verify contra o `manto_local`), `manto-deploy` (publicar e operar a
produção no Render), `manto-conferir-tela` (verificar tela React no Browser pane), `financeiro`,
`financeiro-auditor`, `marketing-auditor`. As skills `speckit-*` são geradas pelo Spec Kit — não
edite à mão; regra do projeto vai na constituição e nos templates de `.specify/templates/`.
