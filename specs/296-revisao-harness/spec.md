# Feature 296 — Revisão do harness: Render como presente, esteira em dois níveis, harness versionado

**Branch**: `296-revisao-harness` (da `main`) · **Created**: 2026-09-08 · **Status**: Em andamento ·
**Migration**: nenhuma · **Nível**: 2 (correção/harness — só documentação, configuração do Spec Kit e
arquivos de deploy; nenhuma linha de comportamento do sistema muda)

## O pedido, nas palavras do dono

"Precisamos revisar o harness do projeto. Faz algum tempo que não mexo no claude.md, constitution e
coisas do tipo. Como mudamos do railway para o render, acho que é importante darmos essa revisada.
Pois sinto que as mudanças atualmente estão dando problema justamente por falta desse contexto mais
direcionado. E quero voltar a trabalhar diretamente com spec kit, para padronização."

## O que o diagnóstico mostrou

Auditoria multi-agente em 08/09/2026 (4 auditores → verificação em 2 lentes → crítico → arquiteto;
148 achados confirmados, 5 refutados). O padrão é um só: o harness parou em 30/07 e o sistema não
parou.

- `CLAUDE.md` não dizia que push na `main` é deploy, não mandava ler `docs/00`, ensinava typecheck
  app a app (esquece o portal) e trazia parâmetros de API (`effort`, `max_tokens`) como regra.
- Constituição v2.2.0: Stack dizia Railway; Princípio VI prometia 8 comandos com sintaxe `/speckit.X`
  que não existe (as skills são `/speckit-X`); o portão de `/speckit-converge` aborta em 14 das 20
  pastas recentes porque `check-prerequisites.sh` exige `plan.md`; a regra de RBAC sumiu na 2.2.0.
- `DEVELOPMENT.md`: Railway em toda parte, fluxo `dev → main` (branch morta desde 23/04), SQLite como
  "modo ideal", `flask db migrate` (autogenerate proibido), módulos que não existem.
- Spec Kit: `.specify/scripts/bash/` (o que as skills chamam) untracked; `.claude/` inteiro
  gitignored; `feature.json` na 256; templates stock; `constitution OLD.md` untracked.
- As regras operacionais que evitam incidente viviam só na memória do agente.
- `railway.json`, `nixpacks.toml` e os dois do `frontend/` seguiam na raiz e o
  `scripts/validar_startcommand.py` validava eles, não o `render.yaml`.

## Decisões do dono (08/09)

1. Esteira em **dois níveis** (FEATURE completa × CORREÇÃO curta) — é o que o repositório pratica.
2. Versionar `.claude/` parcialmente (skills, `settings.json`, `launch.json`; fora só
   `settings.local.json`).
3. Apagar os 4 arquivos de deploy do Railway e a branch `dev` (com tag antes, depois do push).
4. `settings.json`: podar e acrescentar `deny` (`flask db migrate`, `git add -A`, `git add .`,
   `git push --force`).

## O que muda (por arquivo)

| Área | Mudança |
|---|---|
| `.gitignore` | diff pendente commitado; `/ct/` e `/.tmp.drivedownload/`; `.claude/` → só `settings.local.json` |
| `specs/296-revisao-harness/`, `.specify/feature.json` | esta spec; ponteiro aponta para a 296 |
| `.specify/` | `scripts/bash/` versionado; `scripts/powershell/` removido; `constitution OLD.md` → `docs/archive/constitution-2.1.0.md`; hooks de auto-commit desligados em `extensions.yml`; templates adaptados no lugar |
| `scripts/validar_startcommand.py`, `render.yaml`, `app/config.py` (comentários) | validador lê o `startCommand` do `render.yaml`; 4 arquivos do Railway removidos; lições do `nixpacks.toml` viram comentário no blueprint |
| `.specify/memory/constitution.md` | v3.0.0: Sync Impact Report, hífen nos comandos, VI em dois níveis com Regra Zero, VIII = `verify_NNN.py`, XIII (RBAC) e XIV (config/efeito externo) novos, seção Operação e Deploy, Portões reescritos, Governança completa |
| `.claude/` | symlinks mortos e 4 skills genéricas fora; `manto-verify`, `manto-deploy`, `manto-conferir-tela` criadas; `settings.json` podado + `deny`; `launch.json` com `MANTO_SEM_THREADS`/`FLASK_ENV` |
| `CLAUDE.md` | reescrito (≤ 160 linhas): regras de trabalho + ponteiros; produção (Render), esteira, verificação, ferramental Windows |
| `DEVELOPMENT.md` | reescrito: branches reais, dois níveis, rodar local, variáveis, migrations à mão + ensaio destrutivo, verify, publicar, operar a produção |
| `docs/00`, `docs/01` §5, `docs/05` §10, `docs/CONTINGENCIA_RENDER.md`, `docs/PLANO_REMOCAO_JINJA.md`, `.env.example` | Railway só como história; Render como presente; `/health` público não prova nada; `docs/01` §5.3 vira a casa única de operação |
| `docs/03` | entrada 296 no topo + linha no índice (correções por referência às entradas 264 e 265) |

## Verificação (sem tocar produção)

| Passo | Comando | Esperado |
|---|---|---|
| Ponteiro | `cat .specify/feature.json` | `specs/296-revisao-harness` |
| Scripts | `bash .specify/scripts/bash/check-prerequisites.sh --json --paths-only` | exit 0 |
| Numeração | `bash .specify/extensions/git/scripts/bash/create-new-feature.sh --json --dry-run --short-name x "x"` | `FEATURE_NUM` = 297 |
| Validador | `python scripts/validar_startcommand.py` | todos `[OK]`, lendo `render.yaml` |
| Railway morto | `grep -rin railway CLAUDE.md DEVELOPMENT.md .env.example render.yaml .specify/memory/constitution.md docs/00_* docs/01_* docs/05_*` | só frases históricas |
| Clone limpo | `git ls-files .claude/skills .specify/scripts/bash .specify/templates` | skills `speckit-*` + `manto-*`, 5 `.sh`, 5 templates |
| Segredo | `git ls-files \| grep -i "settings.local\|db-url"` | vazio |
| Código intocado | `cd frontend && npm run typecheck`; `ruff check app/` | limpos |
| Produção (após o push) | `curl -s https://app.mantoproducoes.com.br/api/formularios/comum/schema` | JSON |

## Fora de escopo (registrado em `docs/05`)

Healthcheck/`watchPatterns` do `manto-frontend`; `npm ci`; renomear `.railway-db-url`/
`backup-railway.ps1`; mover `docs/planos.md` e `EspecificacoesEducamanto.md`; limpar ~282 branches
antigas; `docs/04` defasado; drift do Alembic; tokens dos agentes no painel do Render (o dono
preenche).

## Docs a atualizar

`docs/00` (§2, §6, §9, §10), `docs/01` (§5), `docs/03` (entrada 296), `docs/05` (§10 e novas
dívidas), `docs/CONTINGENCIA_RENDER.md`, `DEVELOPMENT.md`, `CLAUDE.md`.
