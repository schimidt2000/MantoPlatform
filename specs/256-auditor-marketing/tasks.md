# Tasks: Auditor de marketing semanal e mensuração no ERP (feature 256)

**Input**: Design documents from `/specs/256-auditor-marketing/` — plan.md, spec.md, research.md, data-model.md, contracts/ (agent-endpoints, desempenho-api, csv-inbox), quickstart.md

**Tests**: OBRIGATÓRIOS (Princípio VIII — Test-First): `verify_256.py` + fixtures vêm **antes** do núcleo de cada história; rodar o verify ao fim de cada fase.

**Organization**: fases por história (US1 → US5) depois da fundação; cada fase é um incremento testável sozinho.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: US1 relatório semanal · US2 reembolso mensal · US3 tela Desempenho · US4 permalink/vínculo · US5 atribuição

## Path Conventions

Backend Flask em `app/`, migrations em `migrations/versions/`, rotina em `scripts/marketing/`, SPA em `frontend/apps/internal/src/`, verificação e fixtures em `specs/256-auditor-marketing/`.

---

## Phase 1: Setup (infra compartilhada)

- [x] T001 Criar esqueleto `scripts/marketing/` com `README.md` (propósito + ponteiro para `contracts/csv-inbox.md`); as pastas `inbox/`, `processed/`, `runs/`, `data/` são ignoradas pelo git e criadas em runtime por `config.ensure_dirs()` (o README documenta)
- [x] T002 [P] Adicionar ao `.gitignore`: `/scripts/marketing/inbox/`, `/scripts/marketing/processed/`, `/scripts/marketing/runs/`, `/scripts/marketing/data/`, `.marketing-agent-token` (bloco comentado no molde do auditor 221, linhas ~38-42)
- [x] T003 [P] `app/config.py`: `MARKETING_AGENT_TOKEN = os.getenv("MARKETING_AGENT_TOKEN", "")` ao lado de `AUDIT_AGENT_TOKEN` (linha ~180); gerar `.marketing-agent-token` local (`secrets.token_urlsafe(48)`) — nunca versionar
- [x] T004 [P] `app/constants.py`: `MARKETING_AGENT_PLATFORMS = ["Instagram", "Meta Ads", "Google Ads"]`, `MARKETING_IMPORT_KINDS = ["meta_content", "meta_account", "meta_ads", "google_ads", "unknown"]`, códigos de achado (`FINDING_ARQUIVO_REJEITADO`, `FINDING_GASTO_DIVERGENTE`, `FINDING_GASTO_MANUAL_EXISTENTE`, `FINDING_PERIODO_SOBREPOSTO`, `FINDING_POST_NAO_VINCULADO`, `FINDING_MOEDA_NAO_BRL`, `FINDING_META_ATRASADA`, `FINDING_SEM_ARQUIVO`) e severidades (`critico`, `atencao`, `info`)
- [x] T005 [P] Criar fixtures em `specs/256-auditor-marketing/fixtures/`: `meta_conteudo.csv` (3 posts, colunas pt-BR do research R5, 1 com permalink), `meta_conta.csv` (7 dias), `meta_ads_dia.csv` (2 campanhas × 7 dias, `Valor usado (BRL)` em `1.234,56`), `google_ads_dia.csv` (preâmbulo 2 linhas + `Dia` + rodapé `Total`), `google_ads_agregado.csv` (sem `Dia`, período no preâmbulo), `invalido_colunas.csv` (sem custo), `meta_ads_usd.csv` (`Valor usado (USD)`), `kommo_utm.csv` (2 leads com `Origem do Lead`/`utm_campaign` = nome de campanha do google_ads_dia)

---

## Phase 2: Foundational (bloqueia todas as histórias)

- [x] T006 `app/models.py`: adicionar `MarketingAgentRun`, `MarketingImportFile`, `MarketingPostMetric`, `MarketingCampaignMetric`, `MarketingAccountMetric`, `MarketingAdSpendBatch`, `MarketingAdSpendLine` (colunas, uniques e FKs exatamente como `data-model.md`), `MarketingPost.permalink` (String(500)), `Client.lead_origin` (String(120)), `Client.utm_source/utm_medium/utm_campaign` (String(200)); docstrings explicando fotografia × diário e o lote mensal
- [x] T007 Migration manual `migrations/versions/c4d1e7b2a9f3_marketing_auditor.py` (`down_revision = "b3f8d27a9e14"`): 7 tabelas + 5 colunas, índices/uniques nomeados (`uq_marketing_post_metrics_snapshot`, `uq_marketing_campaign_metrics_period`, `uq_marketing_account_metrics_day`, `uq_marketing_ad_spend_batches_month`, `uq_marketing_import_files_sha256`), `downgrade()` completo em ordem inversa
- [x] T008 Aplicar no `manto_local`: `flask db upgrade` → `flask db downgrade -1` → `flask db upgrade` sem erro; registrar o head novo no cabeçalho de `docs/01_SISTEMA_E_BANCO.md` (só o estado do repositório; detalhes na fase de polish)
- [x] T009 Esqueleto Test-First `specs/256-auditor-marketing/verify_256.py`: bootstrap igual a `verify_255.py` (sys.path, `FLASK_ENV=development`, `.local-db-url`), usuário descartável `__v256_marketing@manto.local` com papel MARKETING + segundo com CASTING, login via `POST /api/auth/login`, helper `cenario(nome, fn)` com contagem `N/N OK`, limpeza no `finally` (`roles.clear()` + delete; registros por prefixo `__v256_`; lotes/gastos/métricas da rodada de teste), 12 cenários do quickstart §2 como funções que **falham** até a implementação (`raise NotImplementedError` vira FALHA, não crash)
- [x] T010 [P] `app/marketing/desempenho_ops.py` (módulo novo): cabeçalho/docstring, dataclasses de resultado (`IngestResult`, `AdSpendAction`), helpers puros `normalize_permalink(url) -> str`, `normalize_campaign_name(name) -> str`, `month_ref(date) -> str`, `last_day_of_month(date) -> date`, constantes de tolerância (`TOLERANCIA_DIVERGENCIA = Decimal("0.01")`)
- [x] T011 [P] `app/api/marketing_agent.py` (módulo novo): `_token_valido()` lendo `MARKETING_AGENT_TOKEN` (molde `audit_agent.py`), resposta 404 padrão, `_mode_permitido(mode)` (local só com `FLASK_ENV=development`), e registro do módulo onde `audit_agent` é importado (`app/api/__init__.py`)

**Checkpoint**: migration aplicada, verify roda e reporta 0/12 OK sem estourar, módulos novos importáveis.

---

## Phase 3: User Story 1 — Relatório semanal a partir dos exports (P1) 🎯 MVP

**Goal**: pasta → reconhecimento → ingestão no ERP → relatório por e-mail com blocos do FR-020 e "sem dado" explícito; skill + tarefa agendada.

**Independent Test**: quickstart §2 cenários 1–3 e §3 (rodada local completa gera `relatorio.html` e `--send` entrega ao dono).

### Tests (escrever primeiro)

- [x] T012 [US1] Implementar em `verify_256.py` os cenários 1 (parsers com as fixtures válidas/inválidas/agregado/ambíguo), 2 (token ausente/errado/certo em `GET /context`) e 3 (ingestão idempotente: contagens, `replayed`, `skipped_duplicate`) — devem FALHAR agora

### Implementation

- [x] T013 [P] [US1] `scripts/marketing/config.py`: `REPO_ROOT`, pastas (`INBOX_DIR`, `PROCESSED_DIR`, `RUNS_DIR`, `DATA_DIR`, `STORE_PATH`/`STORE_PATH_LOCAL`), `PROD_BASE_URL`/`LOCAL_BASE_URL`, `REPORT_RECIPIENTS = ["joao@mantoproducoes.com.br"]`, `CARD_HOLDER_EMAIL`, `agent_token()` lendo `.marketing-agent-token`, `base_url(local)`, `ensure_dirs()` — molde `scripts/auditor/config.py`, **sem** leitura de URL de banco
- [x] T014 [P] [US1] `scripts/marketing/column_maps.json`: por `kind`, `required` (grupos com alternativas "ou") e `optional` com aliases pt-BR/en-US (tabela de `contracts/csv-inbox.md`), mais `number_columns`, `date_columns`, `currency_label_regex`
- [x] T015 [P] [US1] `scripts/marketing/store.py`: SQLite com tabelas `runs(run_id, window_start, window_end, started_at, finished_at, report_sent)`, `files(sha256 PK, filename, kind, run_id, seen_at)` e `findings(code, key, first_run_id, last_run_id)`; `set_mode(local)`, `last_window_end()`, `open_run()`, `close_run()`, `file_seen(sha)`, `remember_file()`, `finding_seen(code, key)`, `remember_finding()` — molde `scripts/auditor/store.py`
- [x] T016 [US1] `scripts/marketing/parsers.py`: `sniff_dialect(path)`, `read_rows(path)` (BOM, utf-8→latin-1, preâmbulo/rodapé Google), `parse_number(raw)` (BR/US/ambíguo ⇒ `AmbiguousNumber`), `parse_date(raw)` (5 formatos), `classify(headers, maps) -> kind`, `normalize_<kind>(rows, file_meta)` para os 4 tipos devolvendo listas no shape do `POST /run` + `FileVerdict(status, reason, period, row_count)`; regra dos 10 % de linhas rejeitadas; moeda do rótulo/coluna; funções ≤ 30 linhas
- [x] T017 [US1] `scripts/marketing/collect.py`: `--local`, `--desde`; janela desde `store.last_window_end()`; varre `inbox/*.csv`, sha256, `store.file_seen` ⇒ `skipped_duplicate`; classifica/normaliza; grava `runs/<id>/manifest.json` (janela, arquivos+veredito) e `normalizado.json`; move arquivos para `processed/<id>/` (sufixo `_REJEITADO`); imprime `run_id`
- [x] T018 [US1] `desempenho_ops.ingest_run(payload, *, mode) -> IngestResult`: transação única; `run_id` repetido ⇒ replay do resultado guardado em `findings_json`/colunas da rodada; arquivos por sha256 (`skipped_duplicate`); upserts com `ON CONFLICT DO UPDATE` (`sqlalchemy.dialects.postgresql.insert`) para as 3 tabelas de métrica; contagens; validação de shape ⇒ `ValueError` com campo (a rota converte em 400)
- [x] T019 [US1] `desempenho_ops.agent_context(window_start, window_end, card_holder_email) -> dict`: `card_holder` resolvido por e-mail (usuário interno ativo, senão `PermissionError` ⇒ 403 na rota), `posts` publicados na janela (+`permalink`), `goals` via `marketing_ops.goal_health()`, `new_clients_by_month` via `client_ops.client_metrics()`, `marketing_expenses` do mês corrente e anterior (categoria Marketing) com `batch` quando houver, `attributed_clients: []` (preenchido na US5)
- [x] T020 [US1] `app/api/marketing_agent.py`: `GET /marketing-agent/<token>/context`, `POST /marketing-agent/<token>/run`, `POST /marketing-agent/<token>/report` (reusa `send_audit_report_email` — adicionar parâmetro `agent_label: str = "auditor financeiro"` em `app/email_service.py` para o rodapé/assunto, sem mudar o comportamento atual); respostas exatamente como `contracts/agent-endpoints.md`; `mode=local` fora de development ⇒ 400
- [x] T021 [US1] `scripts/marketing/publish.py --run <id> [--local]`: `GET /context` (grava `contexto.json`), monta payload do `POST /run` a partir de `manifest.json` + `normalizado.json`, grava `resultado.json`; sai com código ≠ 0 se HTTP ≠ 200
- [x] T022 [US1] `scripts/marketing/checks.py --run <id>`: consolida achados locais (arquivo rejeitado/sem arquivo por tipo na janela, posts do export sem card — a partir de `contexto.json`, metas `delayed`, gasto gerado sem comprovante "aguardando fatura do cartão") com `findings_server` do `resultado.json` em `findings.json` ordenado por severidade; **suprime repetição** entre rodadas via `store.finding_seen(code, key)` (chave = plataforma+mês para gastos, sha256 para arquivos, id do post para vínculos) — o achado sai uma vez, como no auditor 221
- [x] T023 [US1] `scripts/marketing/report.py --run <id> [--send|--save-only] [--local]`: `build_html()` com blocos na ordem do FR-020 (manchete `leads` ou fallback `alcance` com motivo), barras HTML/CSS (`_barra(label, valor, max)` em tabela), `_brl()` copiado do auditor, bloco "sem dado" e "arquivos rejeitados", janela + número da rodada (+ aviso se > 8 dias); `resumo.md` em pt-BR; `POST /report` com `config.REPORT_RECIPIENTS`; `store.close_run(report_sent=...)`
- [x] T024 [US1] `scripts/marketing/README.md`: instruções de export (csv-inbox.md §operador), comandos da rodada, modo `--local`, onde ficam os segredos, o que a rotina escreve no ERP (só Gasto Extra de Marketing + histórico)
- [x] T025 [US1] `.claude/skills/marketing-auditor/SKILL.md` (local, gitignored): passo a passo collect → publish → checks → report → resumo no chat; regras invioláveis (única escrita = Gasto Extra de Marketing via endpoint; nunca expor token; nunca inventar número; arquivo rejeitado é achado); linguagem de dono de empresa no resumo
- [x] T026 [US1] Criar scheduled task `auditoria-marketing-semanal` (MCP scheduled-tasks): cron `30 6 * * 1`, descrição "Auditoria de marketing semanal da Manto: lê exports da Meta/Google na pasta, grava histórico no ERP, gera reembolso de anúncios e envia relatório", prompt apontando para a skill e para `C:\Users\schim\Desktop\Manto_Platform\scripts\marketing`
- [x] T027 [US1] Rodar `verify_256.py` (cenários 1–3 devem passar) e quickstart §3 com as fixtures (`relatorio.html` abre no navegador com barras; `--send --local` ⇒ `enviados >= 1`)

**Checkpoint**: MVP — o dono recebe o relatório semanal a partir da pasta; histórico no ERP; sem reembolso ainda.

---

## Phase 4: User Story 2 — Gasto de anúncios vira reembolso mensal (P2)

**Goal**: lote por plataforma × mês ⇒ Gasto Extra `pendente` com reembolso ao titular e linhas por campanha; atualização enquanto pendente; congelamento; divergência vira achado.

**Independent Test**: quickstart §2 cenários 4, 5 e 11.

### Tests (escrever primeiro)

- [x] T028 [US2] Cenários 4 (created → updated → frozen_divergent; manual ⇒ skipped_manual; USD ⇒ sem gasto), 5 (sobreposição diário × agregado) e 11 (serializer `marketing_batch`) em `verify_256.py` — devem FALHAR agora

### Implementation

- [x] T029 [US2] `app/gastos/gastos_ops.py`: `create_expense(..., require_receipt: bool = True)` repassando para `_validate_expense_data`; docstring explicando que só o agente de marketing cria sem comprovante (a fatura do cartão vem depois)
- [x] T030 [US2] `desempenho_ops.sync_ad_spend(run, *, card_holder) -> list[AdSpendAction]` (`card_holder` = usuário resolvido de `payload.card_holder_email`, 403 antes de qualquer escrita) chamado dentro de `ingest_run`; `action` ∈ {created, updated, frozen_ok, frozen_divergent, skipped_manual, skipped_currency}: agrega gasto BRL por (plataforma, mês) usando só linhas diárias quando existirem (senão agregadas) e registra `periodo_sobreposto`; lote inexistente + sem gasto manual ⇒ `create_expense()` (categoria `Marketing`, `disbursement_type="reembolso"`, `reimburse_user_id`, `expense_date=last_day_of_month`, descrição `Anúncios <plataforma> — <mês/ano> (auditor de marketing)`, `notes` com "reembolso previsto dia 10/<mês seguinte>" e `run_id`, `require_receipt=False`) + lote + linhas; lote com gasto `pendente` ⇒ atualiza `amount`, `reported_total`, substitui linhas; gasto não pendente ⇒ `frozen_at` + comparação ⇒ `gasto_divergente` se `> TOLERANCIA`; gasto manual de Marketing no mês cuja descrição contém a plataforma ⇒ `skipped_manual` + achado; moeda ≠ BRL ⇒ `skipped_currency` + achado
- [x] T031 [US2] Serializer do Gasto Extra (localizar `serialize`/`_expense_to_dict` em `app/api/gastos*.py` ou `gastos_ops.py`): campo `marketing_batch` conforme `contracts/desempenho-api.md`; `agent_context.marketing_expenses[].batch` usa o mesmo helper
- [x] T032 [US2] Frontend `frontend/apps/internal/src/pages/GastosExtrasPage.tsx` (+ tipo em `lib/` correspondente): quando `marketing_batch` existir, bloco `DenseCard` "Gerado pelo auditor de marketing — <plataforma> <mês>" com linhas por campanha (`formatBRL`), total reportado e selo "congelado" quando `frozen`; nenhum comportamento existente alterado
- [x] T033 [US2] Rodar `verify_256.py` (cenários 4, 5, 11 passam; 1–3 continuam) e conferir na tela de Gastos Extras (browser) o bloco do gasto gerado

**Checkpoint**: US1 + US2 — o reembolso entra sozinho, uma vez por mês e plataforma.

---

## Phase 5: User Story 3 — Tela "Marketing → Desempenho" (P3)

**Goal**: histórico de 4/12/26 semanas com gráficos SVG, tabelas de posts/campanhas, rodadas e estado vazio; RBAC de marketing; mobile.

**Independent Test**: quickstart §2 cenário 9 e §4.

### Tests (escrever primeiro)

- [x] T034 [US3] Cenário 9 (MARKETING 200 com todas as chaves; CASTING 403; `start > end` 400; sem rodadas ⇒ `empty: true`) em `verify_256.py` — deve FALHAR agora

### Implementation

- [x] T035 [US3] `desempenho_ops.desempenho_summary(start, end) -> dict`: `weekly` (alcance = soma de `reach` da fotografia mais recente por post publicado na semana; `followers` = último do período; `spend`/`clicks` por semana de linhas diárias; `posts_published`), `campaigns` (gasto, impressões, cliques, `cpc`; `leads/events/cost_per_*` em `null` até a US5), `posts` (última fotografia + card), `goals` via `goal_health()`, `cac` (mês corrente), `runs` (+`rejected_files`), `headline` (`leads` quando houver atribuição senão `alcance` com `fallback_reason`), `empty`
- [x] T036 [US3] `app/api/marketing_read.py`: `GET /marketing/desempenho` com o mesmo gate RBAC de `GET /marketing/posts`; parse de `weeks`/`start`/`end` (400 em ordem inválida); decimais como string
- [x] T037 [P] [US3] `frontend/apps/internal/src/lib/marketing.ts`: tipos `DesempenhoResponse`, `DesempenhoWeek`, `DesempenhoCampaign`, `DesempenhoPost`, `DesempenhoRun`, `DesempenhoParams`; hook `useMarketingDesempenho(params)` com `placeholderData: keepPreviousData`
- [x] T038 [P] [US3] Componentes SVG em `frontend/apps/internal/src/components/charts/`: `LineSeriesChart.tsx` (1–2 séries, `viewBox`, eixo por semana, `<title>` por ponto, legenda textual), `BarListChart.tsx` (barras horizontais com rótulo e valor formatado via render prop), `FunnelChart.tsx` (gasto → cliques → leads → eventos); cores via classes de token (`text-accent`, `text-gold`, `text-green`, `text-muted`), **sem `style={{}}`**, `useReducedMotion()` para a animação de entrada (`motion.path` / `motion.rect`); carregar a skill `dataviz` antes de desenhar
- [x] T039 [US3] `frontend/apps/internal/src/pages/MarketingDesempenhoPage.tsx`: `PageHeader` com seletor segmentado 4/12/26 semanas + intervalo livre (padrão do `HomePerformance`), manchete (KPI) + CAC, `LineSeriesChart` alcance/seguidores, `BarListChart` gasto por campanha, `FunnelChart`, tabela de posts (título do card ou legenda, `link_method`, métricas, link externo), tabela de campanhas (CPC/CPL), lista de rodadas com arquivos rejeitados; `Skeleton`/erro; estado vazio com as instruções de export; grade responsiva sem rolagem horizontal (tabelas em `overflow-x-auto` próprio)
- [x] T040 [US3] `frontend/apps/internal/src/lib/navigation.tsx` (item "Desempenho" na seção Marketing, mesmo gate dos outros dois) + rota `/marketing/desempenho` em `frontend/apps/internal/src/App.tsx`
- [x] T041 [US3] `npx tsc --noEmit`; conferir no navegador a 1440 px e 375 px (`scrollWidth === 375`), tema claro/escuro; medir `GET /api/marketing/desempenho?weeks=12` (< 1 s no servidor, `time` no verify) e o carregamento da tela (< 3 s percebidos — SC-006); rodar `verify_256.py` (cenário 9 passa)

**Checkpoint**: US1–US3 — e-mail e tela lendo o mesmo histórico.

---

## Phase 6: User Story 4 — Post do painel vinculado às métricas (P4)

**Goal**: campo "Link do post publicado" no card; vínculo permalink → data → nenhum; relatório e tela falam pelo título do card.

**Independent Test**: quickstart §2 cenários 6 e 10, §5.

### Tests (escrever primeiro)

- [x] T042 [US4] Cenários 6 (vínculo por permalink / por data / ambíguo / revínculo) e 10 (`PATCH` permalink inválido 400 com `fields.permalink`; válido normalizado) em `verify_256.py` — devem FALHAR agora

### Implementation

- [x] T043 [US4] `app/marketing/marketing_ops.py`: `_validate_permalink(raw) -> str | None` (http/https, ≤ 500, `normalize_permalink` de `desempenho_ops` para comparação, grava URL limpa sem `utm_*`), `create_post`/`update_post` aceitam `permalink`, `serialize_post` expõe; `app/api/marketing_write.py` PATCH repassa o campo (erro de campo no envelope `fields`)
- [x] T044 [US4] `desempenho_ops.link_post_metrics(run) -> dict` dentro de `ingest_run`: por fotografia sem vínculo: permalink normalizado igual ⇒ `permalink`; senão exatamente 1 card `publicado` da mesma plataforma com `publish_date` = data de publicação ⇒ `date`; senão `none` com `candidates`; revincula `link_method="none"` de rodadas anteriores; resultado `post_links` na resposta do `POST /run`
- [x] T045 [US4] `frontend/apps/internal/src/components/MarketingPostDialog.tsx` + `lib/marketing.ts` (`permalink` no tipo e no payload): campo "Link do post publicado" (`Input type="url"`), ao escolher status `publicado` sem link o campo ganha destaque (`border-gold`/texto de ajuda "Cole o link do post para o relatório semanal reconhecer esta publicação") sem bloquear; erro da API aparece no campo preservando os demais valores; card da lista/Kanban mostra ícone de link quando preenchido
- [x] T046 [US4] `scripts/marketing/report.py` e `checks.py`: usar `post_links` do `resultado.json` — posts pelo título do card quando vinculados, bloco "Posts sem card (informe o link)" com os `unlinked_posts` e candidatos
- [x] T047 [US4] Rodar `verify_256.py` (cenários 6 e 10 passam) e conferir o dialog no navegador (publicar sem link ⇒ destaque; link inválido ⇒ erro no campo; válido ⇒ salvo)

**Checkpoint**: o ciclo planejamento → publicação → resultado fecha dentro do ERP.

---

## Phase 7: User Story 5 — De qual campanha veio o lead e o evento (P5)

**Goal**: importador do Kommo guarda origem/utms; atribuição por campanha (leads, eventos, CPL, custo por evento) e CAC do mês; manchete = leads.

**Independent Test**: quickstart §2 cenários 7 e 8.

### Tests (escrever primeiro)

- [x] T048 [US5] Cenários 7 (import com utms preenche `Client`; export sem as colunas importa como antes) e 8 (`GET /context` com `attributed_clients` casando `utm_campaign` normalizado; `goals` iguais ao endpoint de metas) em `verify_256.py` — devem FALHAR agora

### Implementation

- [x] T049 [US5] `app/clientes/importer.py`: constantes `COL_ORIGEM = "Origem do Lead"`, `COL_UTM_SOURCE = "utm_source"`, `COL_UTM_MEDIUM = "utm_medium"`, `COL_UTM_CAMPAIGN = "utm_campaign"`; `_apply_metadata` grava nos campos novos com a regra "mais recente sobrescreve" (bloco `is_newer`), truncando ao tamanho da coluna; colunas ausentes ⇒ nada muda
- [x] T050 [US5] `desempenho_ops`: `attributed_clients` no `agent_context` (clientes com `kommo_created_at` na janela e `utm_campaign` não nulo, com eventos via `EventClient` e `start_at >= kommo_created_at`); em `desempenho_summary`: `leads`/`events`/`cost_per_lead`/`cost_per_event` por campanha (`normalize_campaign_name` dos dois lados), `weekly.leads/events`, `cac` (gasto do mês ÷ `new_by_month[mês].total`; zero ⇒ `value: null` com motivo), `headline.kind = "leads"` quando houver ≥ 1 cliente com utm no período
- [x] T051 [US5] `scripts/marketing/report.py`: manchete de leads por campanha e custo por lead (fallback alcance com `fallback_reason` "utms/import do CRM ausentes"), bloco "Leads e eventos por campanha", CAC do mês com os dois números de base; `checks.py`: achado `info` quando nenhum cliente da janela tem utm
- [x] T052 [US5] Rodar `verify_256.py` (cenários 7 e 8 passam; total 12/12) e quickstart §3 completo de novo com `kommo_utm.csv` importado

**Checkpoint**: todas as histórias funcionando de forma independente.

---

## Phase 8: Polish & Cross-Cutting

- [x] T053 [P] `docs/01_SISTEMA_E_BANCO.md`: 7 tabelas, 5 colunas, endpoints do agente e `GET /marketing/desempenho`, RBAC, env `MARKETING_AGENT_TOKEN` (interruptor geral), head da migration
- [x] T054 [P] `docs/02_MAPA_DE_PAGINAS_E_UX.md`: `/marketing/desempenho` (UX, estado vazio, gráficos, RBAC), campo de link no card, bloco do gasto gerado em Gastos Extras, rotina semanal (onde salvar os exports, horário, o que o e-mail traz)
- [x] T055 [P] `docs/03_HISTORICO_MUTACOES.md`: entrada no topo (migration, motivação, regras — mês civil, congelamento, sobreposição, vínculo, atribuição — e pegadinhas encontradas na implementação)
- [x] T056 `ruff check app scripts/marketing specs/256-auditor-marketing` limpo
- [x] T057 `npx tsc --noEmit` em `frontend/apps/internal` limpo
- [ ] T058 `verify_256.py` 12/12 ✅ + quickstart §3 ✅ §4 ✅ §5 ✅ — **falta só §6**: executar a task `auditoria-marketing-semanal` manualmente uma vez ("Run now" na barra lateral) com a inbox preenchida, para pré-aprovar as ferramentas
- [x] T059 Registrar na memória do projeto e em `docs/03`: para ativar em produção é preciso deploy + env `MARKETING_AGENT_TOKEN` no Railway com o valor de `.marketing-agent-token` (mesmo padrão da 221); sem o env os endpoints respondem 404
- [x] T060 `/speckit-converge` — fechar gaps entre spec, plano, tasks e código

---

## Dependencies & Execution Order

- **Phase 1 → Phase 2 → US1**: obrigatórias nesta ordem (fundação bloqueia tudo).
- **US2** depende de US1 (ingestão e `POST /run` existem) — `sync_ad_spend` roda dentro de `ingest_run`.
- **US3** depende da fundação + dados gravados pela US1 (pode começar em paralelo à US2: arquivos diferentes — `marketing_read.py`, página, charts).
- **US4** depende de US1 (fotografias gravadas) e toca `report.py` (US1) — T046 depois de T023.
- **US5** depende de US2 (gasto por campanha para CPL) e de US3 (campos `leads/events` da tela); o importador (T049) é independente e pode ser feito a qualquer momento após a migration.
- **Polish** depois de todas.

## Parallel Opportunities

- Phase 1: T002, T003, T004, T005 em paralelo.
- Phase 2: T010 e T011 em paralelo após T006/T007.
- US1: T013, T014, T015 em paralelo; depois T016 → T017; T018/T019 (backend) em paralelo a T016/T017 (scripts); T020 depois de T018/T019; T021–T023 depois de T020.
- US3: T037 e T038 em paralelo a T035/T036; T039 depois de todos.
- Polish: T053, T054, T055 em paralelo.

## Implementation Strategy

1. **MVP = Phases 1–3 (US1)**: o dono já recebe o relatório semanal a partir da pasta, com histórico no ERP. Validar uma segunda-feira real antes de seguir.
2. **Incremento 2 = US2**: reembolso mensal — é a parte financeira; exige o verify 4/5/11 verde e uma conferência humana do primeiro gasto gerado.
3. **Incremento 3 = US3**: tela — valor analítico.
4. **Incremento 4 = US4 + US5**: fecham o ciclo com o painel e o CRM (dependem de hábito do time: link no card, utms nas campanhas, import do Kommo).
5. Cada incremento termina com `verify_256.py` verde nos cenários da história + `tsc` + `ruff`, e um commit atômico por história (quando o dono autorizar o commit).

## Notes

- Tarefas [P] = arquivos diferentes e sem dependência pendente.
- Nunca criar Gasto Extra em produção a partir de rodada `--local` (o servidor recusa `mode=local` fora de development — T011/T020).
- Segredos: `.marketing-agent-token` nunca versionado; nunca citar token/URL de banco em relatório, `resumo.md` ou chat.

## Phase 9: Convergence

- [x] T061 CRITICAL — Extrair funções para respeitar o limite de ~30 linhas: `app/marketing/desempenho_ops.py` (`ingest_run` → `_upsert_all`/`_apply_run_totals`; `link_post_metrics` → `_card_indexes`/`_resolve_card`; `_spend_by_month` → `_campaign_rows_for_months`/`_daily_dates`/`_accumulate`; `sync_ad_spend` → `_skip_currency`/`_skip_manual`), `scripts/marketing/collect.py` (`_processar_inbox`/`_gravar_saidas`), `scripts/marketing/report.py` (`_carregar_rodada`/`_enviar_e_fechar`), `app/clientes/importer.py` (`_apply_attribution`) per Constitution II (contradicts)
- [x] T062 Desambiguar a atribuição quando a mesma campanha existe em duas plataformas: `desempenho_ops._campaign_table` e `scripts/marketing/report.py::atribuir_leads` escolhem a plataforma pelo `utm_source` (google/adwords → Google Ads; ig/instagram/fb/facebook/meta → Meta Ads), senão a de maior gasto; cenário 8 do `verify_256.py` passa a exigir o lead na campanha do Google per US5/AC1 (partial)
- [x] T063 Arrastar o card para "Publicado" no Kanban sem link abre o Dialog do card (`frontend/apps/internal/src/components/MarketingKanban.tsx` após `move.mutate` com `status === "publicado" && !post.permalink`) per FR-010 (partial)
- [x] T064 `POST /run` devolve `post_links.linked` ({platform_post_id → card_id, title, method}) e `scripts/marketing/report.py` usa esse mapa para nomear os posts (inclusive vínculo por data) per US4/AC1 (partial)
- [x] T065 Atualizar `specs/256-auditor-marketing/data-model.md` (`marketing_agent_runs.result_json`, relação `last_run`) e `contracts/agent-endpoints.md` (`post_links.linked`) per plan: data-model (partial)
- [ ] T066 Executar a task agendada `auditoria-marketing-semanal` manualmente uma vez ("Run now") com a inbox preenchida para pré-aprovar as ferramentas (ação do dono) per quickstart §6 (partial)
