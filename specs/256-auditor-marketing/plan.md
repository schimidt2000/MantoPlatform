# Implementation Plan: Auditor de marketing semanal e mensuração no ERP

**Branch**: `256-auditor-marketing` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/256-auditor-marketing/spec.md`

## Summary

Rotina semanal local (Claude Code por assinatura, zero API) que lê exports CSV da Meta (conteúdo, conta, anúncios) e do Google Ads numa pasta de entrada, normaliza e envia o histórico para o ERP por endpoints exclusivos do agente, cruza com posts/metas/clientes/gastos já existentes, cria (uma vez por plataforma e mês, idempotente) o Gasto Extra de Marketing para reembolso do titular do cartão com detalhe por campanha, e entrega um relatório por e-mail com gráficos CSS + uma tela "Marketing → Desempenho" com gráficos SVG e histórico. Molde operacional: `scripts/auditor/` (feature 221); diferença deliberada: os scripts falam **só HTTP** com o ERP (contexto, ingestão, relatório) — sem URL de banco no lado do agente — porque a única escrita permitida precisa passar pela regra de negócio do servidor (idempotência, RBAC de destinatário, validações de Gasto Extra).

## Technical Context

**Language/Version**: Python 3.14 (backend Flask + scripts do agente; `.venv`), TypeScript 5.7 / React 18 (Vite 6)

**Primary Dependencies**: Flask + SQLAlchemy + Alembic (já no projeto); scripts: `requests` (já usado pelo auditor 221), `csv`/`sqlite3` da stdlib — **nenhuma dependência nova**; frontend: TanStack Query, Framer Motion, `@manto/ui`, `@manto/money` — gráficos em componentes SVG próprios (sem lib de chart)

**Storage**: PostgreSQL (produção Railway / `manto_local`) — 6 tabelas novas + 1 coluna em `marketing_posts` + 4 colunas em `clients` (migration manual Alembic, `down_revision = b3f8d27a9e14`); memória local do agente em SQLite (`scripts/marketing/data/`) só para janela/hashes/rodadas, como em 221

**Testing**: `specs/256-auditor-marketing/verify_256.py` contra `manto_local` (login via `POST /api/auth/login`, usuário descartável, padrão `verify_255.py`); fixtures CSV em `specs/256-auditor-marketing/fixtures/`; `npx tsc --noEmit` em `frontend/apps/internal`; `ruff check`

**Target Platform**: Backend Linux (Railway) + Windows 11 do dono para a rotina (scheduled task do Claude Code, segunda 06:30 com catch-up) + navegador desktop/mobile para a tela

**Project Type**: web-service (Flask JSON) + SPA React + CLI/rotina local (scripts Python)

**Performance Goals**: ingestão de uma rodada típica (≤ 4 arquivos, ≤ 2.000 linhas) em < 10 s ponta a ponta; `GET /api/marketing/desempenho` (12 semanas) < 1 s no servidor; tela percebida < 3 s (SC-006)

**Constraints**: zero API paga; escrita do agente restrita a Gasto Extra de Marketing + histórico de métricas, por token próprio (`MARKETING_AGENT_TOKEN`, 404 sem env); nenhum segredo em relatório/tela; nenhuma integração externa disparada; dinheiro `Numeric(12,2)` e exibição via `@manto/money`; mobile-first na tela; `useReducedMotion()` em toda animação

**Scale/Scope**: 1 rodada/semana; ~50–200 posts/ano; ≤ 20 campanhas ativas; 1 tela nova, 1 dialog alterado, 4 endpoints novos, 1 migration, 1 skill + 1 scheduled task

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano atende | Status |
|-----------|---------------------|--------|
| I. Reutilizar antes de criar | Molde de `scripts/auditor/` (config/store/report), endpoint gated por token copiado de `app/api/audit_agent.py`, `send_audit_report_email` generalizado em vez de segundo remetente, `goal_health()` e `client_metrics()` reutilizados via endpoint de contexto (zero segunda implementação de meta/CAC), `create_expense()`/`_validate_expense_data()` de `gastos_ops` para o Gasto Extra, importador do Kommo estendido (não reescrito) | ✅ |
| II. Padrões de código | Type hints + docstrings Google; funções ≤ ~30 linhas (parsers por tipo de arquivo em funções separadas); constantes (`MARKETING_PLATFORMS`, chaves de coluna) em `constants.py`/`column_maps.json`; TS estrito sem `any`; **zero `style={{}}`** — barras SVG recebem dimensões por atributos SVG (`width`/`x`), não por estilo inline | ✅ |
| III. API First / camadas | Rotas só validam token/RBAC e chamam `app/marketing/desempenho_ops.py` (ingestão, agregações, reembolso); scripts não tocam no banco de produção | ✅ |
| IV. Não quebrar | `PATCH /api/marketing/posts/<id>` ganha campo opcional (compatível); importador do Kommo só adiciona campos; serializer de Gasto Extra ganha chave opcional `marketing_batch`; migration aditiva; verify contra `manto_local` antes de qualquer commit | ✅ |
| V. UI/UX com feedback | Tela com Skeleton/erro/vazio; campo de link no dialog com validação de URL apontada no campo; botões com estado de envio | ✅ |
| VI/VII. SDD + Living Spec | Esteira completa (specify → clarify → plan → tasks → analyze → implement → converge); spec já ajustada com as decisões de planejamento (mês civil, gráficos CSS no e-mail) | ✅ |
| VIII. Test-First | `verify_256.py` e fixtures CSV vêm **antes** das tarefas de núcleo em `tasks.md` | ✅ |
| IX. Dinheiro BR | `Numeric(12,2)` no banco; `formatBRL` na tela; `_brl()` do relatório reaproveitado do auditor | ✅ |
| X. Mobile-first | Tela interna, mas o dono usa celular: 375 px sem rolagem horizontal; gráficos rolam dentro do bloco | ✅ |
| XI. Framer Motion | Entrada de cards/tabelas e troca de período com `useReducedMotion()` | ✅ |
| XII. Dados complexos | Seletor de período com ≤ 5 opções (botões segmentados, não `<select>`); nenhuma lista > 10 itens em dropdown | ✅ |
| Stack | Sem Jinja; sem lib nova de gráfico (SVG próprio); migration manual | ✅ |
| Segredos | `.marketing-agent-token` + `scripts/marketing/{inbox,processed,runs,data}` no `.gitignore`; `.claude/` já ignorado | ✅ |

Nenhuma violação a justificar → Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/256-auditor-marketing/
├── plan.md              # Este arquivo
├── research.md          # Fase 0 — decisões e alternativas
├── data-model.md        # Fase 1 — tabelas, colunas, regras
├── quickstart.md        # Fase 1 — roteiro de validação
├── contracts/
│   ├── agent-endpoints.md     # /api/marketing-agent/<token>/{context,run,report}
│   ├── desempenho-api.md      # GET /api/marketing/desempenho + PATCH permalink + serializer do gasto
│   └── csv-inbox.md           # pasta de entrada, tipos de arquivo, mapa de colunas, regras de rejeição
├── fixtures/            # CSVs de exemplo (Meta conteúdo/conta/anúncios, Google Ads) — criados na fase de tasks
├── verify_256.py        # Verificação funcional contra manto_local — criado na fase de tasks
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── models.py                         # +MarketingAgentRun, MarketingImportFile, MarketingPostMetric,
│                                     #  MarketingCampaignMetric, MarketingAccountMetric,
│                                     #  MarketingAdSpendBatch, MarketingAdSpendLine;
│                                     #  MarketingPost.permalink; Client.lead_origin/utm_*
├── constants.py                      # MARKETING_AGENT_PLATFORMS, chaves de achado
├── config.py                         # MARKETING_AGENT_TOKEN
├── marketing/
│   ├── marketing_ops.py              # permalink no create/update/serialize; vínculo post↔métrica
│   └── desempenho_ops.py             # NOVO: ingestão idempotente, reembolso mensal, agregações da tela,
│                                     #  contexto para o agente (metas, CAC, atribuição, gastos)
├── clientes/importer.py              # COL_ORIGEM/COL_UTM_* → Client
├── gastos/gastos_ops.py              # serializer do gasto expõe `marketing_batch`
├── api/
│   ├── marketing_agent.py            # NOVO: GET context · POST run · POST report (token)
│   ├── marketing_read.py             # GET /marketing/desempenho
│   └── marketing_write.py            # PATCH aceita permalink
├── email_service.py                  # send_audit_report_email → parâmetro de "assinatura" do agente
migrations/versions/<rev>_marketing_auditor.py

scripts/marketing/                    # NOVO — molde de scripts/auditor
├── README.md
├── config.py                         # pastas, token, destinatários, titular do cartão, base_url
├── column_maps.json                  # aliases de colunas por tipo de arquivo (editável sem código)
├── parsers.py                        # sniff de delimitador/BOM/preâmbulo, números BR/US, datas
├── collect.py                        # inbox → manifest + normalizados (runs/<id>/), move p/ processed/
├── publish.py                        # POST /run (ingestão) e guarda a resposta (gastos, vínculos)
├── checks.py                         # achados: sobreposição, divergência gasto ERP×plataforma, não vinculados…
├── report.py                         # HTML (barras CSS) + POST /report
├── store.py                          # SQLite: rodadas, hashes, última janela (modo local × prod)
├── inbox/ processed/ runs/ data/     # gitignored

frontend/apps/internal/src/
├── pages/MarketingDesempenhoPage.tsx # NOVA: /marketing/desempenho
├── components/charts/                # NOVOS: LineSeriesChart.tsx, BarListChart.tsx, FunnelChart.tsx (SVG)
├── components/MarketingPostDialog.tsx# campo "Link do post publicado" (pede ao publicar)
├── lib/marketing.ts                  # tipos + hooks de desempenho; permalink no MarketingPost
├── lib/navigation.tsx                # item "Desempenho" na seção Marketing
└── App.tsx                           # rota

.claude/skills/marketing-auditor/SKILL.md        # local, gitignored
~/.claude/scheduled-tasks/auditoria-marketing-semanal  # segunda 06:30, catch-up
```

**Structure Decision**: web-service + SPA existentes ganham um módulo (`app/marketing/desempenho_ops.py` + `app/api/marketing_agent.py`) e uma página; a rotina vive em `scripts/marketing/` espelhando `scripts/auditor/` para o operador (e o Claude da rodada) reconhecer o fluxo. Decisões de desenho em [research.md](research.md).

## Complexity Tracking

Sem violações da constituição. Observações de escopo que **não** são violações mas merecem registro:

| Escolha | Por quê | Alternativa rejeitada |
|---------|---------|-----------------------|
| 6 tabelas novas | Histórico por post/campanha/conta tem chaves e granularidades diferentes; misturar em uma tabela "métrica genérica" inviabiliza as unicidades da spec (FR-006/007/008) | Tabela única EAV — perde constraints e deixa a tela lenta |
| Lote de reembolso (`MarketingAdSpendBatch`) em vez de colunas em `SpecialExpense` | Idempotência por plataforma+mês e o detalhe por campanha são conceitos do marketing; o Gasto Extra continua genérico | Colunas `agent_source`/`period_key` em `SpecialExpense` — sujam um modelo compartilhado por 6 telas |
