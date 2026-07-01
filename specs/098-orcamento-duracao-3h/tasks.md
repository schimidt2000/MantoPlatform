# Tasks: Duração de 3 horas na calculadora de orçamentos

**Feature**: 098-orcamento-duracao-3h | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> Testar contra `manto_local`. Migração manual (down_revision `b4e5f6a7c8d9`). Cuidado com índices:
> após inserir 3h no índice 2, **4h passa a ser o índice 3**.

## Phase 1 — Config e derivação de 3h (US2, P1)

- [ ] **T001** Em [settings.py](../../app/orcamento/settings.py): adicionar helper `interpolar_3h(v2, v4)`
  (média arredondada — inteiro p/ cachê, decimal p/ markup) e um utilitário que insere o 3h (índice 2)
  em qualquer lista de 3 valores.

- [ ] **T002** Em [settings.py](../../app/orcamento/settings.py): atualizar `DEFAULTS` para 4 valores
  `[1h,2h,3h,4h]` em todas as tabelas (markup, ator, cantor {base/show_extra/make_extra}, tecnico_som,
  coordenador, especiais e variantes). 3h = média(2h,4h). Cobre FR-001, FR-002.

- [ ] **T003** Em [settings.py](../../app/orcamento/settings.py) `_migrate`: injetar 3h em toda config
  **salva** com arrays de tamanho 3 (percorrendo markup/ator/cantor/tecnico_som/coordenador/especiais,
  inclusive dicts de variantes), sem alterar os valores existentes. Idempotente (não duplica se já tem 4).
  Cobre FR-003, edge "config antiga".

- [ ] **T004** Em [pricing.py](../../app/orcamento/pricing.py): `range(3)`→`range(4)` em `aplicar_markup`
  e garantir que todos os getters retornam 4 valores.

## Phase 2 — Modelo + migração (US3)

- [ ] **T005** Em [models.py](../../app/models.py) `OrcamentoHistory`: adicionar `total_3h =
  Numeric(10,2) nullable`.

- [ ] **T006** Migração manual `migrations/versions/<hash>_orcamento_total_3h.py`
  (down_revision `b4e5f6a7c8d9`): `add_column('orcamento_history', total_3h)`. Aplicar em `manto_local`.

## Phase 3 — Cálculo do orçamento (US1, P1) 🎯 MVP

- [ ] **T007** Em [orcamento/routes.py](../../app/orcamento/routes.py) (cálculo ~linhas 258-354): todos os
  `for i in range(3)` → `range(4)`.

- [ ] **T008** Ajustar toda referência "índice 2 = 4h" para índice 3: `total_custom = totals[3]/4*N`
  (~359); `total_custom` só quando `duracao_custom not in (1,2,3,4)` (~358). Cobre edge duração custom.

- [ ] **T009** Durações na mensagem/seleção: `dur_labels` ganha 3h (horas e entradas); `incluir` default
  inclui 3h na ordem 1h/2h/3h/4h; `show` (4 posições); `_idx={"1h":0,"2h":1,"3h":2,"4h":3}`; `_pix_durs`
  com 3h; personalizado lê `cust_mult_3h`/`cust_valor_3h`. Cobre FR-005, FR-006.

- [ ] **T010** Sessão/histórico: `session["orcamento_quote"]` ganha `total_3h=totals[2]`, `show_3h`, e
  `total_4h=totals[3]`; `OrcamentoHistory(total_3h=totals[2], total_4h=totals[3])`; snapshot com
  `cust_mult_3h`/`cust_valor_3h`. Cobre FR-008.

- [ ] **T011** POST de settings (mesmo arquivo): ler 4 índices por tabela (`_0.._3`) ao salvar preços.
  Cobre FR-004.

## Phase 4 — Templates + JS

- [ ] **T012** [settings.html](../../app/templates/orcamento/settings.html): `range(3)`→`range(4)` e
  cabeçalhos com coluna **3h** em todas as tabelas (markup, ator, cantor, tecnico, coordenador, especiais).

- [ ] **T013** [index.html](../../app/templates/orcamento/index.html): checkbox "3 horas"
  (`incluir_duracao=3h`) entre 2h e 4h; `total-3h`/`lbl-3h`; base `cb-3h`; personalizado
  `cust_valor_3h`/`cust_mult_3h`; textos "1h/2h/4h" → incluir 3h. Cobre FR-005.

- [ ] **T014** [resultado.html](../../app/templates/orcamento/resultado.html): exibir a duração de 3h
  quando incluída (linha/valor + PIX). Cobre FR-006.

- [ ] **T015** [orcamento.js](../../app/static/js/orcamento.js): replicar cálculos client-side para 4
  durações (base, totais, personalizado, exibição). Cobre FR-006, FR-007.

## Phase 5 — Criação de evento a partir do orçamento (US3)

- [ ] **T016** [calendar/routes.py](../../app/calendar/routes.py) `_compute_performer_caches`: incluir
  `cache_3h` (média 2h/4h ou índice correspondente) em cada item retornado.

- [ ] **T017** [calendar/routes.py](../../app/calendar/routes.py) prefill/criação: ler `total_3h`;
  `dur_idx`/`duracao` mapear "3"→2 e "4"→3; `duracao_custom not in (1,2,3,4)`. Cobre FR-009.

## Phase 6 — Verificação e qualidade

- [ ] **T018** Verificação contra `manto_local`: (a) `interpolar_3h` e migração de config antiga (3→4
  valores, 3h=média); (b) cálculo de um orçamento com 3h → valor entre 2h e 4h; (c) histórico grava
  `total_3h`; (d) settings salva/edita 3h; (e) criar evento por 3h. Cobre SC-001..SC-005, FR-010.

- [ ] **T019** [P] `ruff format`/`ruff check` nos arquivos Python alterados; Jinja parse dos templates;
  boot do app.

## Dependências

- T001→T002→T003 (derivação antes de DEFAULTS/migração). T004 após T001.
- T005→T006 antes de gravar total_3h (T010). Phase 3 depende de Phase 1.
- Phase 4 depende do cálculo (Phase 3). Phase 5 depende de T005/T006 e da config.
- Phase 6 ao final.

## Critério de pronto

- 3h existe em todas as tabelas (padrão = média 2h/4h) e é editável; config antiga migra sozinha.
- Vendedor seleciona 3h e vê valor coerente (entre 2h e 4h); PIX/à vista incluídos.
- Histórico grava total_3h; evento criado por 3h reflete venda/cachês de 3h.
- Orçamentos/config antigos sem erro. Checklist "Pronto" do CLAUDE.md (ruff + verificação em manto_local).
