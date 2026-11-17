---
description: "Tasks da feature 345 — marketing integrado ao sistema"
---
# Tasks: Feature 345 — marketing integrado ao sistema

**Input**: artefatos em `/specs/345-marketing-integrado/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/api-345.md

**Verificação (Princípio VIII)**: `specs/345-marketing-integrado/verify_345.py` contra `manto_345`. Ele é escrito
na fase Foundational, antes do núcleo, e nasce falhando nos cenários ainda não construídos.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [ ] T001 Constantes em `app/constants.py`:
  - `MARKETING_FRENTES` (slug → nome);
  - `MARKETING_FRENTE_PREFIXOS` (`CORP`, `SOCIAL`, `EDU`, `FESTA`, `LOJA`);
  - `MARKETING_FORMATOS` e o mapa formato → foto|vídeo;
  - `LICENCA_ORIGENS`, `LIBERADO_VALORES`;
  - `PROPOSTA_TIPOS`, `PROPOSTA_SITUACOES`, `PROPOSTA_VALIDADE_DIAS = 7`;
  - `DIARIO_VEREDITOS`, `DIARIO_REAVALIAR_DIAS = 14`;
  - `TETO_FRACAO_MARGEM = Decimal("0.25")`.

---

## Phase 2: Foundational (bloqueia as histórias)

- [ ] T002 Models em `app/models.py`, conforme `data-model.md`:
  - colunas novas em `CatalogItem`, `MarketingPost`, `MarketingCampaignMetric` e `SiteSetting`;
  - `MarketingFrente`, `MarketingCampanhaFrente`, `MarketingAdMetric`, `MarketingPostAnuncio`, `MarketingProposta`,
    `MarketingDiario`.
- [ ] T003 Migration manual `migrations/versions/f345c0a1b2d3_marketing_integrado.py`:
  - `down_revision = "e344a1b2c3d4"`; semeia as 5 frentes; downgrade completo;
  - aplicar no `manto_345` com `flask db upgrade`.
- [ ] T004 Esqueleto de `app/marketing/comando_ops.py`:
  - `ComandoError(codigo, message, field, status)`;
  - `frente_da_campanha`;
  - a expressão SQL da frente da venda;
  - `tema_liberado`.
- [ ] T005 **`specs/345-marketing-integrado/verify_345.py`**:
  - os 17 cenários da spec, com login só pela API, escrita conferida por conexão separada e limpeza no `finally`;
  - roda e falha nos cenários ainda não construídos.

---

## Phase 3: US1 — painel por frente (P1) 🎯 MVP

**Teste independente**: cenários 1–5.

- [ ] T006 [US1] Em `app/marketing/desempenho_ops.py`:
  - `conversations` e `leads` em `_CAMPAIGN_INT_COLS`;
  - `ingest_ad_metrics(items)`, upsert idempotente em `marketing_ad_metrics`.
- [ ] T007 [US1] Em `app/marketing/comando_ops.py`:
  - `vendas_por_frente(inicio, fim)` (vendas, cliente novo, faturamento);
  - `gasto_por_frente(inicio, fim)` (reusa `_effective_campaign_rows`);
  - `teto_padrao(slug)`, `tetos()`, `resumo_frentes(inicio, fim)`, `campanhas_sem_frente(inicio, fim)`;
  - `situacao_plataformas(inicio)`;
  - `corrigir_frente_campanha(...)`.
- [ ] T008 [US1] O `desempenho_summary` em `app/marketing/desempenho_ops.py` ganha `frentes`, `sem_frente` e
  `plataformas`.
- [ ] T009 [US1] `app/api/marketing_comando_read.py` (`GET /api/marketing/frentes`) e
  `app/api/marketing_comando_write.py` (`PATCH /api/marketing/frentes`, `PATCH /api/marketing/campanhas/frente`),
  importados em `app/api/__init__.py`.
- [ ] T010 [US1] Agente em `app/api/marketing_agent.py`: `POST …/anuncios` e `GET …/comando`.
- [ ] T011 [P] [US1] Tipos e hooks em `frontend/apps/internal/src/lib/marketing.ts`:
  - `DesempenhoFrente`, `PlataformaSituacao`, `CampanhaSemFrente`, `FrentesConfig`;
  - `useFrentesConfig`, `useSalvarFrentes`, `useCorrigirFrente`.
- [ ] T012 [US1] Bloco "Por frente" em `frontend/apps/internal/src/pages/MarketingDesempenhoPage.tsx`:
  - os cards de frente, o aviso de teto e o "sem venda";
  - a lista "Campanhas sem frente" com `<select>`;
  - a faixa das plataformas.
- [ ] T013 [P] [US1] `frontend/apps/internal/src/components/marketing/FrentesConfigDialog.tsx`, só para Superadmin:
  - o teto por frente com `MoneyInput`;
  - as responsáveis por foto e vídeo com `Combobox`.

---

## Phase 4: US2 — só tema liberado vai para anúncio (P1)

**Teste independente**: cenários 6–8.

- [ ] T014 [US2] Em `app/marketing/comando_ops.py`:
  - `listar_temas_licenca(filtros)`, `confirmar_sugestoes(ids, user)`, `marcar_licenca(item, user, origem, liberado)`
    (403 para liberar licenciado sem Superadmin);
  - `gravar_sugestoes(items)` para o agente.
- [ ] T015 [US2] Em `app/marketing/marketing_ops.py`:
  - campos `tipo`, `frente`, `formato`, `briefing_*`;
  - validação "tema não liberado em card de anúncio" (422 `tema_nao_liberado`, campo `catalog_item_ids`);
  - `serialize_post` com os campos novos, `origem`, `anuncios` e `resultado`.
  - Em `app/api/marketing_write.py`, `POST_FIELDS` + a tradução do 422.
- [ ] T016 [US2] Endpoints de licença: `GET /api/marketing/temas-licenca`, `POST …/confirmar` e `PATCH …/<id>` nos
  módulos de comando; agente `POST …/licencas/sugestoes`.
- [ ] T017 [P] [US2] `frontend/apps/internal/src/pages/MarketingTemasPage.tsx`:
  - busca e filtros no endereço;
  - selects de origem e liberado;
  - a confirmação em lote das sugestões;
  - "Liberar" só com `pode_liberar_licenciado`.
- [ ] T018 [US2] Rota `/marketing/temas` em `frontend/apps/internal/src/App.tsx` e item no menu em
  `frontend/apps/internal/src/lib/navigation.tsx`.

---

## Phase 5: US3 — pedido de criativo (P2)

**Teste independente**: cenários 9–11.

- [ ] T019 [US3] Em `app/marketing/comando_ops.py`:
  - `criar_pedidos(items)`: responsável pelo formato, `origem='rotina'`, regra do tema liberado;
  - `cards_prontos_sem_anuncio()`, `vincular_anuncio(post, platform, ad_id)`, `resultado_do_card(post)`.
- [ ] T020 [US3] Agente: `POST …/pedidos` e `POST …/posts/<id>/anuncios` em `app/api/marketing_agent.py`.
- [ ] T021 [US3] Diálogo do card em `frontend/apps/internal/src/components/MarketingPostDialog.tsx`:
  - tipo, frente, formato e briefing (objetivo, o que mostrar, letreiro);
  - o lembrete da regra de imagem;
  - os anúncios vinculados com o resultado;
  - o erro de tema não liberado no campo.
- [ ] T022 [P] [US3] Selos "Anúncio" e "Pedido da rotina" no card em
  `frontend/apps/internal/src/components/MarketingKanban.tsx`.

---

## Phase 6: US4 — propostas com aprovação (P2)

**Teste independente**: cenários 12–14.

- [ ] T023 [US4] Em `app/marketing/comando_ops.py`:
  - `expirar_pendentes()`, `criar_proposta(dados)` (regra do tema liberado via `post_id`);
  - `listar_propostas(situacao)`;
  - `decidir(proposta_id, user, decisao, obs)`, com trava e releitura (409 `ja_decidida` / `expirada`);
  - `propostas_a_executar()`;
  - `marcar_execucao(id, resultado, detalhe)`, que cria a entrada do diário.
- [ ] T024 [US4] `GET /api/marketing/propostas` e `POST …/<id>/decidir` (só SUPERADMIN); agente `POST …/propostas` e
  `POST …/propostas/<id>/execucao`.
- [ ] T025 [US4] Aba "Propostas" de `frontend/apps/internal/src/pages/MarketingDecisoesPage.tsx`:
  - os cards pendentes com Aprovar/Recusar e a observação;
  - o histórico;
  - 390 px sem rolagem lateral.

---

## Phase 7: US5 — diário de decisões (P3)

**Teste independente**: cenário 15.

- [ ] T026 [US5] Em `app/marketing/comando_ops.py`: `listar_diario()`, `criar_entrada(dados, autor)`,
  `diario_a_reavaliar()` e `gravar_resultado(id, texto, veredito)`.
- [ ] T027 [US5] `GET|POST /api/marketing/diario` e o agente `POST …/diario/<id>/resultado`.
- [ ] T028 [US5] Aba "Diário" em `MarketingDecisoesPage.tsx`, com a nova entrada e o selo "a reavaliar"; rota
  `/marketing/decisoes` e item no menu.

---

## Phase 8: Rotina, portões e documentação

- [ ] T029 Reescrever `.claude/skills/marketing-auditor/SKILL.md`:
  - a rotina pelos conectores (Meta MCP, Google MCP), na ordem: `POST /run` + `/anuncios` → executar as aprovadas →
    reavaliar o diário → sugerir licenças → propostas e pedidos → relatório;
  - as regras de marca (só liberado, sem imagem de IA) e as boas práticas da `research.md` R5;
  - o CSV fica como plano B.
- [ ] T030 Portões:
  - `verify_345.py` 17/17;
  - `ruff check` nos tocados e `ruff format` nos novos;
  - `cd frontend && npm run typecheck`;
  - telas no Browser pane (desktop e 390 px na de decisões).
- [ ] T031 Docs:
  - `docs/01` (§Agente de marketing + §4.3);
  - `docs/02` (Desempenho, Temas, Decisões, Kanban);
  - `docs/03` (entrada no topo + índice);
  - `docs/04` (§Marketing);
  - `docs/05` (custo misto até a atribuição; rotina 256 depende do token no Render).
- [ ] T032 Commits por caminho (`feat(345):`, `docs(345):`), nunca `git add -A`. Merge e push só quando o dono pedir.

## Dependências

- Setup → Foundational → US1 → US2 → (US3 ∥ US4) → US5 → Phase 8.
- US3 e US4 dependem da regra do tema liberado (US2).
- US5 depende de `marcar_execucao` (US4).

## Paralelo

- T011 e T013 (frontend US1) correm enquanto o backend da US1 fecha.
- T017 corre com T014–T016.
- T022 corre com T021.

## Estratégia

MVP = US1 + US2: painel por frente e trava do tema liberado. Logo depois vêm US3 e US4, que tiram a Gabi do
Gerenciador, e por fim a US5. Cada fase termina com os cenários dela verdes no `verify_345.py`.
