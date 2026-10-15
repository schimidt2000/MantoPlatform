---
description: "Tasks da feature 307 — Papai Noel em data especial na Calculadora"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Papai Noel em data especial — faixa de 24 e 25/12 na tabela de preços e gatilho pela data

**Input**: artefatos em `/specs/307-natal-papai-noel-calculadora/`

**Pré-requisitos**: plan.md, spec.md (histórias e "Verificação"), research.md (D1–D10),
data-model.md, contracts/api.md, quickstart.md

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `specs/307-natal-papai-noel-calculadora/verify_307.py`
contra `manto_local`, escrito na fase Foundational e rodado vermelho antes do núcleo (primeira
execução em `verify_307_primeira_falha.txt`, inclusive a prova de 1/2/12 contra o `settings.py` da
`main`); salva a configuração de preços real, aplica a de teste e restaura no `finally` por conexão
separada. **O portão é `--regressao`** (sem a flag o 17 sai PULADO, fora da contagem). Sem migration.

**Organização**: por história da spec, na ordem pedida pelo dono (tabela normal → cálculo → teto →
EducaManto → endpoint/card → calculadora/resultado → polimento), todas P1 primeiro.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1 = História 1 (cálculo na faixa) · US2 = História 2 (tabela normal) · US3 =
  História 3 (teto) · US4 = História 4 (config) · US5 = História 5 (calculadora/resultado) · US6 =
  História 6 (EducaManto)

## Caminhos (Manto)

- Backend: `app/orcamento/{settings,pricing,quote_ops,pdf}.py` · `app/calendar/routes.py` ·
  `app/calendar/orcamento_evento_ops.py` · `app/educamanto/quote_ops.py` · `app/api/orcamento_write.py`
- Frontend: `frontend/apps/internal/src/lib/orcamento.ts` ·
  `frontend/apps/internal/src/pages/{OrcamentoConfigPrecosPage,OrcamentoCalculadoraPage,OrcamentoResultadoPage}.tsx` ·
  `frontend/apps/internal/src/components/orcamento/{PriceTable,DatasEspeciaisCard}.tsx`
- Verificação: `specs/307-natal-papai-noel-calculadora/verify_307.py`

## Phase 1: Setup

- [x] T001 Conferir no espelho (só leitura; `docs/backlog/ferramentas/sql_ro.py` é ferramenta local
      não versionada, ou script no scratchpad) o `pricing_config` atual: `especiais."Papai Noel"`
      (`[600,650,675,700]` ✔), `markup.receptivo` (`[2.6,2.5,2.45,2.4]` ✔), `coordenador.false`
      (`[250,…]` ✔), `especiais_excluidos` (`["Ajudante Especial"]` ✔) — anotados no docstring do
      `verify_307.py` como premissa dos cenários 1, 2 e 12

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar. **O verify vem primeiro.**

- [x] T002 **`specs/307-natal-papai-noel-calculadora/verify_307.py`** — cenários 1–18 da spec
      (`verify_305.py` como esqueleto: login só por `POST /api/auth/login` com SUPERADMIN e COMERCIAL
      descartáveis; cookie do próprio `test_client`; requisições fora do `app_context`; config real
      lida por conexão separada, config de teste gravada — Noel no cachê ANTIGO, sem Ajudante, sem
      bloco —, restaurada no `finally` e conferida por conexão separada; orçamentos descartáveis
      apagados; cenário 14 DEVE falhar; 17 só com `--regressao`, senão PULADO; vínculo 273 provado com
      evento transitório + espião) — escrito e rodado vermelho; saída em
      `verify_307_primeira_falha.txt`. *Desvio registrado: o T003–T005 foi escrito antes; a prova
      vermelha de 1/2/12 foi refeita contra o `settings.py` da `main` e anexada ao mesmo arquivo.*
- [x] T003 `app/orcamento/settings.py`: constantes `MARKUP_FAIXA_MIN/MAX`, `PAPAI_NOEL_CACHE_ANTIGO`,
      `NOTA_FAIXA_MAX_CHARS`, `ROTULO_FAIXA_MAX_CHARS`, `CHAVE_FAIXA_RE`; DEFAULTS ganham
      `especiais["Papai Noel"] = [712, 800, 850, 900]`, `especiais["Ajudante do Noel"] =
      [423, 480, 510, 540]` e o bloco `datas_especiais` (data-model §1), com comentário do porquê
- [x] T004 `app/orcamento/settings.py`: `_migrar_307(data)` chamado por `_migrate()` — `setdefault`
      do bloco; bloco/faixa não-dict → padrão; faixa sem `dias` lista → padrão; listas de 3 →
      `_ensure4`; `cache` não-dict → `{}`; sobrescrita malformada DESCARTADA; `dias: []` aceito
      (desligada); troca de "Papai Noel" **só** se `== PAPAI_NOEL_CACHE_ANTIGO`; **nunca levanta** (D5)
- [x] T005 `app/orcamento/settings.py`: `faixa_especial(event_date, settings=None) -> dict | None`
      (recorte `MM-DD`; primeira faixa que casar; cópia com `chave`; `settings` evita reler o banco)

**Checkpoint**: verify vermelho pelos motivos certos; DEFAULTS, migração e `faixa_especial` prontos.

---

## Phase 3: História 2 — Tabela normal com Papai Noel 712 e Ajudante do Noel 423 (Prioridade: P1) 🎯 MVP

**Verificação da história (obrigatória)**: cenários 1, 2 e 12 em PASS.

- [x] T006 [US2] Cenários 1, 2 e 12 verdes (T003–T005 entregam a história); `ruff check
      app/orcamento/settings.py`

---

## Phase 4: História 1 — Orçamento em 24 ou 25/12 pela tabela de Natal (Prioridade: P1)

**Verificação da história (obrigatória)**: cenários 3–9, 15 e 16 em PASS; 1, 2 e 12 continuam.

- [x] T007 [US1] `app/orcamento/pricing.py`: `markup_vigente(show, faixa=None, settings=None)` (fonte
      única do markup), `aplicar_markup(totais, show, faixa=None, settings=None)`,
      `get_especial_prices(…, faixa=None)` (sobrescrita vale para qualquer variante),
      `get_coordenador_prices(show, qty, faixa=None)`, `aplicar_piso(prices, faixa)`,
      `cache_na_faixa(performer, prices, faixa) -> (prices, marca)` (fonte única "sobrescrita × piso",
      usada pela venda E pelo teto) e as marcas `MARCA_CACHE_FAIXA`/`MARCA_PISO_FAIXA`
- [x] T008 [US1] `app/orcamento/quote_ops.py` `calculate_quote`: `cfg_precos = _cfg.load()` uma vez;
      `faixa = _cfg.faixa_especial(raw_date, cfg_precos)`; getters com `faixa`; `cache_na_faixa` em
      cada performer (marca nas `partes`); coordenador marcado; `markup_vigente` para a memória
      (detalhe `"<rótulo> · DD/MM"`, via `_rotulo_da_faixa`) e para `markup_used`; `aplicar_markup`
      com `faixa`/`settings`; `quote["data_especial"] = {chave, rotulo, markup, nota_mensagem}`;
      `nota_especial` em itálico junto da `deslocamento_nota`; comentário do noturno corrigido
      ("somado DEPOIS do markup")
- [x] T009 [P] [US1] `app/orcamento/pdf.py`: `_FONT_ITALIC = "Helvetica-Oblique"`; a nota de
      `quote.get("data_especial").get("nota_mensagem")` desenhada após a frase de deslocamento, em
      itálico, quebrada por `simpleSplit` na largura útil (`_RIGHT - _LEFT`)
- [x] T010 [US1] Cenários 3–9, 15 e 16 verdes; `ruff check` em `pricing.py`, `quote_ops.py`, `pdf.py`

---

## Phase 5: História 3 — O teto de cachê das vagas honra a data (Prioridade: P1)

**Verificação da história (obrigatória)**: cenário 11 em PASS.

- [x] T011 [US3] `app/calendar/routes.py` `_compute_performer_caches(snapshot, horas_extra=None,
      data_evento=None)`: `cfg_precos = _orc_cfg.load()`; `faixa = faixa_especial(data_evento or
      snapshot["event_date"], cfg_precos)`; getters com `faixa`; `cache_na_faixa` em `prices` e
      `base_prices` (marca entra em `marcas` → cap_note); `descricao`/`coord_desc` com ` · <rótulo>`;
      docstring atualizada
- [x] T012 [US3] `app/calendar/orcamento_evento_ops.py`: helper `data_do_evento(event) -> str |
      None` (`start_at.date().isoformat()`; `None` sem `start_at`) — fonte única da data do teto
- [x] T013 [US3] `app/calendar/routes.py` criação (`_create_event_core`, bloco `orc_caches`):
      `data_evento=data_do_evento(event)` (o `event` já existe nesse ponto);
      `app/calendar/orcamento_evento_ops.py` `aplicar_equipe_do_orcamento`: idem
- [x] T014 [US3] Cenário 11 verde (24/12; noturno; 20/12; `data_evento` 24/12 com snap de 20/12; piso
      do boneco com cap_note; vínculo 273 espionado passando "2026-12-24" e `None` sem `start_at`);
      `ruff check` nos dois arquivos (routes.py: só os 8 erros que já estão na `main`)

---

## Phase 6: História 6 — O EducaManto não muda (Prioridade: P3, barata e protege a 235)

**Verificação da história (obrigatória)**: cenário 10 em PASS (depois de provar a faixa ativa).

- [x] T015 [US6] `app/educamanto/quote_ops.py` `_totais_contratacao`: `payload.pop("event_date",
      None)` ao lado de `nota_fiscal`/`fora_sp`, com comentário
- [x] T016 [US6] Cenário 10 verde; `ruff check app/educamanto/quote_ops.py`

---

## Phase 7: História 4 — Superadmin edita a faixa na Configuração de Preços (Prioridade: P2)

**Verificação da história (obrigatória)**: cenários 13 e 14 (DEVE falhar) em PASS; tela
`/orcamento/configuracoes` aberta, inclusive um 400 apontando o campo.

- [x] T017 [US4] `app/orcamento/settings.py`: `SettingsValidationError(message, fields)`,
      `validar_datas_especiais(bloco, especiais) -> dict` (+ `_validar_faixa`, `_validar_dias`,
      `_validar_cache`, `_lista_de_4` via `parse_brl`, `_markup_de_4` com 2 casas HALF_UP) e
      `remover_especial_das_faixas(data, nome)`; `app/api/orcamento_write.py`
      `api_orcamento_settings_save`: `try: s["datas_especiais"] = _cfg.validar_datas_especiais(...)
      except SettingsValidationError → json_error(exc.message, 400, fields=exc.fields)`;
      `api_orcamento_delete_especial` chama `remover_especial_das_faixas`
- [x] T018 [P] [US4] `frontend/apps/internal/src/lib/orcamento.ts`: `FaixaEspecial`;
      `PricingSettings.datas_especiais?` (OPCIONAL — bundle novo pode falar com backend velho);
      `Quote.data_especial?: { chave, rotulo, markup, nota_mensagem } | null`
- [x] T019 [US4] `components/orcamento/PriceTable.tsx` (extraída da página, com `DUR_LABELS` e
      `INPUT_PRECOS`) e `components/orcamento/DatasEspeciaisCard.tsx` (rótulo; chips de dias
      `DD/MM` com `AnimatePresence`/`motion.span` + `useReducedMotion`; `PriceTable` para markup,
      coordenador, piso e cachês sobrescritos — `MoneyInput`, como o card de Markup; chips "+ Nome"/
      "× Nome" para sobrescrever, SEM `<select>`; textarea da nota; `erros` → `aria-invalid`, borda
      vermelha, mensagem e foco no primeiro inválido; erros de linhas da tabela listados acima dela);
      `OrcamentoConfigPrecosPage.tsx` usa os dois, passa `save.error.fields` e, ao remover um
      especial, tira a sobrescrita dele das faixas no estado local
- [x] T020 [US4] Cenários 13 e 14 verdes; tela aberta: card com 24/12 e 25/12, 3,34, 500/650/1.000/650;
      markup 33,40 → 400 com "datas_especiais.natal.markup" no card; salvar válido → "salvas com sucesso"

---

## Phase 8: História 5 — A calculadora avisa e não grava resultado velho (Prioridade: P2)

**Verificação da história (obrigatória)**: telas `/orcamento` (vazia, 20/12, 24/12) e `/orcamento/:id`
abertas; cenário 15 continua verde.

- [x] T021 [US5] `OrcamentoCalculadoraPage.tsx`: `DataEspecialAlert` lendo `result.quote.data_especial`
      (fonte: servidor; sem recalcular a faixa no React), `AnimatePresence` + `motion.div` +
      `useReducedMotion`, markup com `toLocaleString("pt-BR")` ("3,34×"); dica sob a Data com os dias
      da tabela quando vazia; `calcPendente` + `seq` (ref) ligados no efeito do recálculo e
      descartando resposta antiga; botão "Recalculando…" `disabled={saved || calcPendente ||
      calcular.isPending || calcular.isError}`; nota "🎄 Valores da data especial" no painel de resultado
- [x] T022 [P] [US5] `OrcamentoResultadoPage.tsx`: nota "🎄 Valores da data especial: {rotulo}." junto
      da nota de NF
- [x] T023 [US5] `cd frontend && npm run typecheck` limpo; telas conferidas por JS no Browser pane:
      sem data 2.501,20 + dica; 24/12 → "Recalculando…" desabilitado durante o debounce, depois
      5.010,00 / 10.020,00 e o aviso; 20/12 → aviso some, 2.501,20; "Gerar Orçamento" em 24/12 →
      `/orcamento/:id` com a nota no card e na mensagem

---

## Phase 9: Polimento e transversais

- [x] T024 `cd frontend && npm run typecheck` limpo (três SPAs); `ruff check` em todos os Python tocados
      (routes.py: nenhum erro novo contra a `main`); `ruff format` só no `verify_307.py` (novo)
- [x] T025 `verify_307.py --regressao` em **18/18** (305 verde; 273 na linha de base 8/15; config real
      restaurada); `git status --short` só com os arquivos da feature (os untracked `docs/backlog/` e
      `specs/306-…/` são da 306 e NÃO entram em commit)
- [x] T026 Docs por fonte única: `docs/01` (cabeçalho; §2.10 `datas_especiais` e a migração; §3.13
      feature 307; §4.3 `orcamento_write` na linha de `_require_superadmin`), `docs/02` (A.7:
      `/orcamento`, `/orcamento/:id`, `/orcamento/configuracoes`), `docs/03` (cabeçalho com a 305 e a
      307; entrada 307 no topo; linha no índice; "Orçamento e EducaManto"), `docs/04` (linha
      Orçamento: faixa, teto pela data do evento, noturno DEPOIS do markup, pegadinhas), `docs/05`
      (linha 208 atualizada; baixa da 307 com #103 select do PerformersEditor, #104 alerta por nome,
      #105 rehydrate, #106 funções grandes, #107 eventos de 24/25 pré-deploy)
- [x] T027 `quickstart.md` executado (verify com `--regressao`, typecheck, telas); `spec.md` com
      Status "Implementada em 15/10/2026"
- [ ] T028 Commits por caminho: `feat(307): tabela e cálculo` (orcamento + educamanto + api),
      `feat(307): teto das vagas` (calendar), `feat(307): configuração e telas` (frontend),
      `docs(307): …` (specs + docs + `.specify/feature.json`); nunca `git add -A`
- [ ] T029 `/speckit-converge` (workflow: leitores por história + cético) e aplicar os achados como
      `fix(307): converge`. Depois, **só quando o dono pedir**: merge na `main` + `git push origin main`
      a partir das ~19h; antes de "em produção": `git status --short` limpo (fora os untracked da
      306), `git log -1` = cabeçalho do `docs/03`, `migrations/versions/` sem untracked, sonda `/api/`
      com JSON; pós-deploy: `/orcamento/configuracoes` em produção (Papai Noel 712, Ajudante do Noel
      423, bloco de Natal), orçamento de 20/12 e de 24/12, consulta só de leitura dos eventos de
      24/25/12 já criados com orçamento (tetos antigos — #107) para o superadmin, aviso à equipe
      (parar o "Outro"; usar "Ajudante do Noel"); voltar à 306 e `git stash pop`

---

## Dependências e ordem

- Setup (T001) → Foundational (T002 verify → T003–T005) → US2 (T006) → US1 (T007–T010) → US3
  (T011–T014) → US6 (T015–T016) → US4 (T017–T020) → US5 (T021–T023) → Polimento (T024–T029)
- O verify é escrito antes (T002) e falha antes de implementar; passa história a história

## Estratégia

- **MVP**: Setup + Foundational + US2 + US1 + US3 **+ US6** (sem o `pop` do EducaManto o musical de
  24/12 levaria o markup de Natal) → cenários 1–12, 15 e 16 verdes; US4/US5 fecham a edição pela
  tela e o aviso
- **Incremental**: cada fase deixa o verify verde no que já existe; sem faixa nada muda
- Commit por grupo lógico (`feat(307):`), sempre por caminho; deploy em lote à noite
