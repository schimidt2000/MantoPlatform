---
description: "Tarefas da feature 340 — caixa de avisos fora do deploy"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 340 — o pagamento da loja não se perde num push

**Input**: artefatos em `/specs/340-caixa-de-avisos/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/manto-avisos.md,
quickstart.md

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `specs/340-caixa-de-avisos/verify_340.py` contra
`manto_340` (exceção registrada no `plan.md`). Escrito na fase Foundational, ANTES do núcleo: os
cenários do receptor e do dreno ficam BLOQUEADOS (arquivo/função ausente) e os de config e
`render.yaml` FALHAM até a história correspondente.

**Organização**: por história da spec (H1–H6 → US1–US6).

## Formato: `[ID] [P?] [Story] Descrição`

## Phase 1: Setup

- [X] T001 Constantes `VIRTUAL_CAIXA_ARRENDAMENTO_MIN = 5`, `VIRTUAL_CAIXA_ALERTA_HORAS = 1`,
      `VIRTUAL_CAIXA_LOTE = 50` em `app/constants.py`, junto das `VIRTUAL_AVISO_*` (comentário com o
      porquê de cada número)
- [X] T002 [P] Config em `app/config.py`: constante de módulo `AVISOS_BASE_URL =
      "https://manto-avisos.onrender.com"` ao lado de `PLATFORM_BASE_URL`;
      `Config.INFINITEPAY_AVISO_BASE_URL = _url_para_fora(os.getenv("INFINITEPAY_AVISO_BASE_URL"),
      AVISOS_BASE_URL, "INFINITEPAY_AVISO_BASE_URL", permitir_local=MAIL_SUPPRESS_SEND)` perto de
      `PUBLIC_BASE_URL`; `Config.VIRTUAL_CAIXA_INTERVAL = int(os.getenv("VIRTUAL_CAIXA_INTERVAL", "10"))`
      perto de `VIRTUAL_SWEEP_INTERVAL`
- [X] T003 [P] Pasta `servicos/avisos/` com `requirements.txt` (`gunicorn==23.0.0`,
      `psycopg[binary]==3.3.4`, research R3) e `README.md` (o que é, por que não importa `app/`, como rodar local,
      contrato em `specs/340-caixa-de-avisos/contracts/manto-avisos.md`)

---

## Phase 2: Foundational (bloqueia as histórias)

- [X] T004 Modelo `VirtualPaymentInbox` em `app/models.py`, logo depois de
      `VirtualPaymentNotification`, conforme `data-model.md` (docstring com o porquê: guardar antes
      de decidir; nunca o segredo; relógio `now_sp`)
- [X] T005 Migration manual `migrations/versions/e340c1a2b3d4_caixa_de_avisos.py` (`down_revision =
      "d323b5a1c0e7"`): tabela, FK `ON DELETE SET NULL` para `virtual_payment_notifications`, índice
      parcial `ix_virtual_payment_inbox_pendentes` (`WHERE drained_at IS NULL`); `downgrade`
      completo; aplicar no `manto_340` com `flask db upgrade`
- [X] T006 **`specs/340-caixa-de-avisos/verify_340.py`** — os 18 cenários da seção "Verificação" da
      spec, no molde do `verify_310.py` (disjuntor de rede, dublês da InfinitePay e do Google,
      `_db` por conexão separada, `cenario()` com BLOQUEADO para função/arquivo ausente, limpeza no
      `finally` restaurando `site_settings`); o receptor carregado por `importlib` de
      `servicos/avisos/app.py` e exercitado com `werkzeug.test.Client`; o cenário 9 confere a thread
      **no código** (nunca `create_app()` sem `MANTO_SEM_THREADS`); o cenário 11 passa o
      `startCommand` do `manto-avisos` pelo parser real do gunicorn (stubs do
      `scripts/validar_startcommand.py`); rodar e registrar que falha pelos motivos certos

**Checkpoint**: tabela no `manto_340`, verify falhando/bloqueando pelos motivos certos.

---

## Phase 3: História 1 — pagamento durante um deploy vira venda sozinho (P1) 🎯 MVP

**Objetivo**: o aviso guardado na caixa vira venda pela mesma regra da 310 quando o backend drena.

**Verificação da história**: cenários 1, 2, 13–17 do `verify_340.py` em PASS.

- [X] T007 [US1] `servicos/avisos/app.py`: fábrica `criar_aplicacao(database_url)` e
      `aplicacao = criar_aplicacao(os.environ.get("DATABASE_URL"))` no módulo (o verify cria uma
      com URL inválida para o "banco fora"), com o caminho feliz de
      `POST /api/webhooks/infinitepay/<token>` — leitura do corpo com teto, conferência do segredo
      contra `site_settings` (atual; anterior enquanto `…_anterior_ate` > agora em São Paulo; vazio
      nunca vale; `hmac.compare_digest`), `INSERT` em `virtual_payment_inbox` com `received_at` em São
      Paulo, 200 `{"success": true, "message": null}`; falha de banco ao conferir ou gravar → 400 com
      corpo fixo; conexão psycopg 3 curta (`connect_timeout=3`), URL normalizada (`postgres://`,
      `postgresql+driver://` → `postgresql://`)
- [X] T008 [US1] `app/marketing/virtuais_ops.py`: `drenar_caixa_de_avisos(limite=VIRTUAL_CAIXA_LOTE)`
      + auxiliares (`_reivindicar_caixa` — `UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED)
      RETURNING id` com arrendamento de 5 min; `_drenar_linha` — `secret_ok` → `registrar_aviso` →
      marca `drained_at`/`notification_id` (commit) → `processar_aviso`; `secret_ok` falso →
      `registrar_aviso_invalido`; falha → `attempts`/`error`, sem marcar); corpo que não é objeto JSON
      vira `{}`; as funções da 310 não mudam
- [X] T009 [US1] `app/marketing/virtuais_ops.py`: `("caixa", drenar_caixa_de_avisos)` como PRIMEIRA
      rotina de `ciclo_de_varredura()` (docstring: por que antes de `expirar_reservas`)

**Checkpoint**: aviso guardado → venda; duplicado, concorrência, ordem e retorno forjado cobertos.

---

## Phase 4: História 2 — com o backend no ar, decidido em segundos (P1)

**Objetivo**: dreno a cada 10 s e links novos avisando o receptor.

**Verificação da história**: cenário 9 do `verify_340.py` em PASS.

- [X] T010 [US2] `app/__init__.py`: `_start_caixa_de_avisos(app)` no molde de `_start_virtual_sweep`
      (thread daemon `caixa-de-avisos`, `VIRTUAL_CAIXA_INTERVAL`, uma volta do laço em função própria
      `_volta_da_caixa(app)` — o verify chama só ela, `app_context` dentro,
      `except Exception` com log, guarda de `WERKZEUG_RUN_MAIN` em desenvolvimento), chamada no bloco
      que `MANTO_SEM_THREADS=1` desliga
- [X] T011 [US2] `app/marketing/virtuais_ops.py` (~linha 1081): `webhook_url` montado de
      `current_app.config["INFINITEPAY_AVISO_BASE_URL"]`; `redirect_url` segue em `PUBLIC_BASE_URL`;
      comentário com o porquê (a rota antiga continua para links já abertos)

**Checkpoint**: H1 + H2 entregam o caminho do dinheiro completo.

---

## Phase 5: História 3 — o receptor só guarda o que é da operadora (P1)

**Objetivo**: recusas, limites e segredo fora do log, conforme o contrato.

**Verificação da história**: cenários 3–8 e 10 do `verify_340.py` em PASS (3 e 4b DEVEM falhar a
autenticação → 404).

- [X] T012 [US3] `servicos/avisos/app.py`: segredo errado → 404 e linha `secret_ok=false` com 2 KB,
      até 120/h em memória (acima, 404 sem gravar); corpo > 64 KB com ou sem `Content-Length` → 413;
      60/min por cliente (último item do `X-Forwarded-For`, senão `REMOTE_ADDR`) → 429; outros
      caminhos/métodos → 404/405 com corpo fixo
- [X] T013 [US3] `servicos/avisos/app.py`: log de uma linha por chamada sem a URL
      (`[avisos] <código> id=<linha|-> bytes=<n> ms=<n>`); `GET /health` (sem banco) e
      `GET /health/banco` (`SELECT 1`, 503 se falhar)

**Checkpoint**: receptor completo pelo contrato.

---

## Phase 6: História 4 — a família que volta durante a troca é atendida (P2)

**Objetivo**: o retorno do checkout tenta de novo em erro de rede ou 5xx.

**Verificação da história**: tela aberta em 375×812 com o backend parado e levantado; `npm run
typecheck`.

- [X] T014 [US4] `frontend/apps/public/src/lib/virtuais.ts`: `useRetornoCheckout` com `retry`
      (até 3, só quando o erro não é `ApiRequestError` ou tem `status >= 500`) e `retryDelay`
      (5 s, 20 s, 60 s), constantes nomeadas e comentário com o porquê

**Checkpoint**: página de retorno resiste à troca do backend.

---

## Phase 7: História 5 — push que não mexe no backend não derruba nada (P2)

**Objetivo**: `render.yaml` com o serviço novo, o healthcheck do frontend e o filtro do backend.

**Verificação da história**: cenário 11 do `verify_340.py` em PASS; `python
scripts/validar_startcommand.py` verde; Events do Render no primeiro deploy (quickstart §2.6).

- [X] T015 [US5] `render.yaml`: serviço `manto-avisos` (python, `plan: starter`, `region: oregon`,
      `rootDir: servicos/avisos`, `buildCommand: pip install -r requirements.txt`, `startCommand`
      gunicorn `app:aplicacao` com 1 worker, threads, `--access-logformat` sem `%(U)s`,
      `healthCheckPath: /health`, `autoDeploy: true`, `DATABASE_URL` do `manto-postgres`,
      `PYTHON_VERSION`), sem disco; comentário com o porquê — **commit sozinho**
- [X] T016 [US5] `render.yaml`: `healthCheckPath: /` no `manto-frontend` e o comentário de "ausência
      conhecida" reescrito — **commit sozinho**
- [X] T017 [US5] `render.yaml`: `buildFilter.ignoredPaths` no `manto-backend` (`docs/**`, `specs/**`,
      `frontend/**`, `servicos/**`, `.claude/**`, `.specify/**`) e o comentário do topo ("todo push
      redeploya os dois serviços") corrigido — **commit sozinho**; rodar o validador

**Checkpoint**: deploy de docs e de tela sem queda; receptor só reinicia pela própria pasta.

---

## Phase 8: História 6 — a equipe fica sabendo de aviso empacado (P3)

**Objetivo**: sino para linha parada há mais de 1 h.

**Verificação da história**: cenário 12 do `verify_340.py` em PASS.

- [X] T018 [US6] `app/marketing/virtuais_ops.py`: dentro de `drenar_caixa_de_avisos`, linhas com
      `drained_at` nulo, `received_at` há mais de `VIRTUAL_CAIXA_ALERTA_HORAS` e `alerted_at` nulo →
      `_avisar_a_conferir("virtual.caixa:<id>", "Loja virtual: aviso de pagamento parado na caixa",
      …)` e `alerted_at` gravado

**Checkpoint**: todas as histórias entregues.

---

## Phase 9: Polimento e transversais

- [X] T019 Regressão contra `manto_340`: `verify_310.py`, `verify_304.py` e `verify_205.py` (este em
      `scripts/db/` do checkout principal, se existir) — diferenças só as intencionais
- [X] T020 `ruff check` nos `.py` tocados; `ruff format` em `servicos/avisos/app.py`, no verify e na
      migration; `cd frontend && npm run typecheck`
- [X] T021 Tela aberta (skill `manto-conferir-tela`): página do pedido em 375×812, retorno com o
      backend local parado e levantado
- [X] T022 Princípio XV: texto do sino revisado (tom interno); nenhum texto visível novo na loja
- [X] T023 [P] Constituição 3.2.0 em `.specify/memory/constitution.md` (Operação e Deploy §1: quarto
      serviço, frontend com healthcheck, aviso pela caixa, sem janela proibida por pagamento; Sync
      Impact Report e changelog)
- [X] T024 [P] `DEVELOPMENT.md` (§Publicar, §Operar a produção: R-20 substituída, sonda do
      `/health/banco`, desligar o caminho novo) e `.claude/skills/manto-deploy/SKILL.md` (item 6)
- [X] T025 [P] `CLAUDE.md` §2 (serviços do `render.yaml`, regra de horário) e `docs/00` §2
      (topologia)
- [X] T026 [P] `docs/01`: §2.10 (tabela `virtual_payment_inbox`), §4.3 (rota do receptor), §5
      (`render.yaml`, deploy sem queda do frontend, filtro do backend, `manto-avisos`, sondas)
- [X] T027 [P] `docs/02` (página do pedido: retentativa do retorno) e `docs/04` §Loja Virtual (o aviso
      entra pela caixa; ordem caixa → expiração)
- [X] T028 [P] `docs/05`: quitar a dívida 22 (e corrigir o registro: o frontend já filtrava por
      `rootDir`); registrar "tirar o disco do `manto-backend` — janeiro" e "preview environments"
- [X] T029 `docs/03`: entrada nova no topo + linha no índice + Loja de Interações Virtuais; inclui a
      pegadinha do `create-new-feature.sh` (ignora branches `+` de outro worktree e propôs 337)
- [X] T030 `quickstart.md` §1 executado de ponta a ponta; §2 fica para o deploy com o dono

---

## Dependências e ordem

- Setup (T001–T003) → Foundational (T004–T006) → US1 (T007–T009) → US2 (T010–T011) → US3
  (T012–T013) → US4 (T014) → US5 (T015–T017) → US6 (T018) → Polimento (T019–T030)
- T007 e T012/T013 tocam o mesmo arquivo (`servicos/avisos/app.py`): em sequência. T008, T009, T011
  e T018 tocam `virtuais_ops.py`: em sequência.
- US4 (T014) e US5 (T015–T017) independem do backend e podem andar em paralelo às US1–US3.
- T015–T017 são três commits separados no mesmo arquivo: em sequência.

## Paralelismo

- T002 ∥ T003 (arquivos diferentes).
- T014 ∥ T008 (frontend × backend).
- T023 ∥ T024 ∥ T025 ∥ T026 ∥ T027 ∥ T028 (documentos diferentes).

## Estratégia

- **MVP**: Setup + Foundational + US1 + US2 + US3 — o caminho do dinheiro completo e seguro. US4 e
  US5 completam a promessa de "push de dia"; US6 é rede de segurança.
- Merge e push só quando o dono pedir, à noite, com os Events abertos (quickstart §2).

---

## Phase 10: Convergence

- [X] T031 `servicos/avisos/app.py`: captura geral em `Receptor.__call__` — exceção inesperada vira 400 de corpo fixo e log só com o tipo, nunca sobe ao gunicorn (que loga `Error handling request <URI>` com o segredo e responde 500, que a operadora não reenvia) per FR-008, FR-006 (partial)
- [X] T032 `specs/340-caixa-de-avisos/verify_340.py`: cenário 8.4 — exceção forçada na conferência do segredo → 400 e nenhuma linha de log com o segredo per spec §Verificação #8 (partial)
