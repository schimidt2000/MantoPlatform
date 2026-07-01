# Tasks: Acréscimos tipados com BV (repasse) e pagamento por PIX

**Feature**: 099-orcamento-acrescimos-bv | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> Testar contra `manto_local`. Migração manual (down_revision `c5f6a7b8d9e0`). `[P]` = paralelizável.

## Phase 1 — Modelo, tipos e migração (base)

- [ ] **T001** Em [constants.py](../../app/constants.py): `ACRESCIMO_TIPOS` (lista fixa + "BV" + "Outro") e
  helper para identificar o tipo BV.

- [ ] **T002** Em [models.py](../../app/models.py): `class EventAcrescimo` (event_id, tipo, descricao,
  is_percent, value, amount_brl, is_bv, bv_recipient, bv_pix, bv_payment_status, created_at) +
  relationship `CalendarEvent.acrescimos` (cascade). Property helper `is_bv`/amount.

- [ ] **T003** Migração manual `migrations/versions/<hash>_event_acrescimos.py` (down_revision
  `c5f6a7b8d9e0`): cria `event_acrescimos`. Aplicar e validar em `manto_local`.

## Phase 2 — Regras financeiras do BV (US2, P1)

- [ ] **T004** Em [financeiro/routes.py](../../app/financeiro/routes.py): `_event_bv_total(event)` (soma
  `amount_brl` dos acréscimos `is_bv`). Cobre FR-008.

- [ ] **T005** `_event_commission`: base = `sale_value − _event_bv_total(event)`. Cobre FR-006. Garantir
  que `_sync_commission_payment` (que usa `_event_commission`) exclui BV automaticamente.

- [ ] **T006** Lucro: descontar `bv_total` no cálculo do dashboard (receita/lucro) e no
  `event_detail` (a fórmula `lucro = venda − custo − gastos`). Cobre FR-005, FR-007. Acréscimos não-BV
  seguem inclusos.

## Phase 3 — Tela comercial do evento (US3, P1)

- [ ] **T007** [event_detail.html](../../app/templates/event_detail.html) "Dados de venda": editor de
  **acréscimos** (add/remover; tipo; valor; R$/%; descrição p/ Outro) substituindo o campo único; quando
  há BV, campos **PIX** e **nome** do recebedor. Cobre FR-001(parte evento), FR-009.

- [ ] **T008** `_handle_update_comercial` ([calendar/routes.py](../../app/calendar/routes.py)): ler/gravar
  a lista de acréscimos (recriar `EventAcrescimo`), computar `amount_brl` (R$ direto; % sobre
  `sale_value`), marcar `is_bv`, salvar `bv_recipient/bv_pix`. Manter `acrescimo_value` legado. Cobre
  FR-003, FR-008.

## Phase 4 — Planilha de pagamentos (US3, P1)

- [ ] **T009** Em [financeiro/routes.py](../../app/financeiro/routes.py) `pagamentos()`/
  `_build_payment_items`: adicionar itens de **BV** dos eventos do mês (valor `amount_brl`, recebedor,
  PIX, status `bv_payment_status`), sinalizando **pendente de dados** quando sem PIX. Cobre FR-010, FR-011.

- [ ] **T010** Endpoint set-status: permitir marcar o item de BV como **pago/não pago**
  (atualiza `bv_payment_status`). [pagamentos.html](../../app/templates/financeiro/pagamentos.html) exibe
  a linha de BV com recebedor/PIX/valor/status. Cobre FR-010, FR-012.

## Phase 5 — Orçamento (US1, P1) 🎯 MVP

- [ ] **T011** [orcamento/index.html](../../app/templates/orcamento/index.html): UI **"Adicionar
  acréscimo"** repetível (tipo, valor, R$/%, descrição p/ Outro) no lugar do acréscimo único. Cobre
  FR-001.

- [ ] **T012** [orcamento/routes.py](../../app/orcamento/routes.py): ler a lista de acréscimos; somar ao
  total (percentuais sobre o total pré-acréscimos); guardar no snapshot; **não** rotular BV na mensagem/
  PDF. Cobre FR-002, FR-004.

- [ ] **T013** [orcamento.js](../../app/static/js/orcamento.js): replicar o cálculo client-side dos
  múltiplos acréscimos (preview de totais). Cobre FR-002.

- [ ] **T014** Criação de evento a partir do orçamento ([calendar/routes.py](../../app/calendar/routes.py)):
  criar `EventAcrescimo` a partir do snapshot. Cobre FR-003.

## Phase 6 — Verificação e qualidade

- [ ] **T015** Verificação contra `manto_local`: (a) 2 acréscimos (R$ e %) somam certo; (b) evento com BV
  → comissão sobre `venda − BV` e lucro desconta BV; (c) BV aparece na planilha (com e sem PIX); (d)
  proposta sem "BV"; (e) evento/legado sem BV inalterado. Cobre SC-001..SC-005.

- [ ] **T016** [P] `ruff format`/`ruff check` nos arquivos Python alterados; Jinja parse dos templates;
  JS com chaves balanceadas; boot do app.

## Dependências

- T001→T002→T003. Phase 2 depende de T002/T003. Phase 3 e 4 dependem de Phase 2. Phase 5 depende de T002
  (transporte) e reusa o editor de T007. Phase 6 ao final.

## Critério de pronto

- Acréscimos tipados no orçamento e no evento; BV desconta lucro, sai da comissão e vira pagamento com PIX.
- BV oculto ao cliente; legado e eventos sem BV sem regressão.
- Checklist "Pronto" do CLAUDE.md (ruff + verificação em `manto_local`).
