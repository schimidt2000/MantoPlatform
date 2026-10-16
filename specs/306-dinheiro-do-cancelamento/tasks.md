---
description: "Tasks da feature 306 — o dinheiro do cancelamento"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Feature 306 — Cancelar devolvendo o dinheiro

**Input**: `specs/306-dinheiro-do-cancelamento/` (spec FR-001–FR-074 e 59 cenários; plan §Fases de construção;
research R0–R30; data-model §1–§11; contracts/api.md §0–§23; quickstart §1–§9; checklists com a Living Spec de
16/10).

**Onde se trabalha**: no worktree `C:\tmp\mp306`, branch `306-dinheiro-do-cancelamento`, base `main` em
`6356b80`. O checkout principal (`C:\Users\schim\Desktop\Manto_Platform`) é de outro chat: não trocar de branch
lá. O `.venv` e o `scripts\db\` são os do checkout principal, por caminho absoluto (quickstart, Pré-requisitos).

**Verificação (Princípio VIII)**: `verify_306.py`, `retrato_main_branch.py` e `contagem_pre_deploy.py` nascem na
Fase 2, ANTES de qualquer linha de núcleo, e rodam vermelhos pelos motivos certos. Cada fase fecha com a rodada
inteira (sem argumentos): os cenários da fase e das anteriores verdes, os das seguintes vermelhos pelos motivos da
tabela, e verde fora de hora é defeito (quickstart §1, "Por fase"). Todo script que chama `create_app()` roda com
`DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development` e `MANTO_SEM_THREADS=1`.

**Nada de push**: merge e push só quando o dono pedir (CLAUDE.md §2). Commits pequenos por tarefa ou por grupo
de tarefas da mesma fase, sempre `git add` por caminho.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa aberta)
- **[US1]–[US6]**: Histórias 1–6 da spec (H1 comissão e BV, H2 cancelar e devolver, H3 DRE e comercial, H4 dados
  de venda do cancelado, H5 vários dias, H6 ensaio, avisos, cachê pago e multa)
- As âncoras `arquivo:linha` são do HEAD `6356b80` (plan, tabela de arquivos); confira com `git show HEAD:<arquivo>`
  antes de editar

---

## Phase 1: Setup

- [ ] T001 Conferir o ambiente do worktree `C:\tmp\mp306`: `.specify/feature.json` → `specs/306-dinheiro-do-cancelamento`, `git log --oneline -1` sobre `6356b80`, `.local-db-url` presente, `flask db heads` com uma cabeça só (`a7c3e91f4d28`); anotar a data do espelho `manto_local` (o banco é compartilhado com o outro chat: refresh só com ele parado)
- [ ] T002 Recontar no espelho, só leitura (`C:\Users\schim\Desktop\Manto_Platform\docs\backlog\ferramentas\sql_ro.py`), os números do plan §Contexto técnico (cancelados, `legado`, linhas `no_banco`, BVs não pagos sem PIX, grupos, satélites com comissão própria — hoje só o 287, R$ 137,50 paga) e gravar em `specs/306-dinheiro-do-cancelamento/contagem_2026-10-16.txt`

---

## Phase 2: Foundational — verify primeiro, modelo, comissão cheia e resumo (bloqueia as histórias)

**Fecha com (B0)**: 1, 23, 26, 27 e a parte de regressão do 41 (comissões dos grupos e cobranças da Home sem
devolução, `main` × branch); com `--nucleo`, a variante 16b cheia 0. Os demais vermelhos.

### Verify antes do núcleo

- [ ] T003 Escrever o esqueleto de `specs/306-dinheiro-do-cancelamento/verify_306.py` (molde `verify_303.py` e `verify_305.py`): guarda de ambiente (exit 2) e de `calendar_auto_sync_at`; trava de e-mail e espião de `send_removal_email`; dublê de `app.calendar.service.delete_event` que conta chamadas; `_esperar_threads`; login só por `POST /api/auth/login`, requisições fora do `app_context`, `test_client(use_cookies=False)` com cookie montado à mão; conexão separada para toda escrita; descartáveis com prefixo `__v306_` (usuários SUPERADMIN, COMERCIAL, FINANCEIRO, CASTING, FIGURINO, ENSAIO, MARKETING, ARTISTA_3D; um vendedor; um talento com e-mail de teste numa vaga existente com `talent_id IS NULL`, nunca `EventRole` inventada); limpeza (cenário 27) no `finally`, na ordem da spec; opções `--so=`, `--nucleo`, `--regressao`, `--semear-tela`, `--limpar-tela` (quickstart §1 e §8); `_deve_quebrar` para as mutações
- [ ] T004 Acrescentar a `verify_306.py` os instrumentos e o harness: matriz de `hoje` (dias 1–5 × depois do dia 5) trocando `now_sp` nos módulos de comissão; Planilha aquecida de M−1 a M+2 com a lista do que fica no espelho; retrato linha a linha de toda tabela pendurada no evento (passagem); retrato das tabelas tocadas antes e depois de cada GET de prévia (mutação "simular escreve"); harness `main` × branch por `git archive` de `git merge-base HEAD main` no `%TEMP%`, os dois lados em subprocesso, comparação exata (Decimal 0,01; percentual 0,1)
- [ ] T005 Codificar em `verify_306.py` os cenários da Fundação e da H1: 1 (casca da comissão `main` × branch em todos os eventos, pelas 8 chamadas), 7–11, 12, 13, 14, 14b, 17, 23 (chama o `retrato_main_branch.py`), 26, 30, as variantes 9/10-desfazer, 16/17-`paid_amount`, 16b cheia 0 e, no 8, `reconciliar(simular=True)` × `simular=False`; no `--nucleo`, semear `event_cancellations` por ORM e chamar a reconciliação e `bv_da_planilha` direto; a parte de regressão do 41 (comissões de todos os grupos e cobranças da Home de toda venda sem devolução, pelas chamadas de hoje)
- [ ] T006 Codificar em `verify_306.py` os cenários da H2: 2 (+ variante 2/8 prévia = execução com `hoje` no dia 2 e no dia 10), 2b, 3, 4 (todas as recusas, inclusive imposto no corte e o piso da devolução do corte), 5 (+ 5-grupo), 6, 15, 16 (+ 16-vivo), 18 (+ 18-inverso), 19 (com o FINANCEIRO), 25 (com as flags do vivo), 28, 31, 32, 34, 36, com as afirmações da tabela da spec e os "deve falhar" com código e nada gravado
- [ ] T007 Codificar em `verify_306.py` os cenários da H3 e da H4: 20 (+ mutação contra a `main`; mês sem cancelado com `paineis.cancelamentos.quantidade == 0`), 21, 22, 24 (+ status "cancelado", `/vendas/`, contagens da cliente), 16b, 16c (mutações: um beneficiário só, nota sem prefixo), 16d (mutação apagar e recriar; BV pago com outro valor mantém o pago), 16e (mutação taxa de hoje)
- [ ] T008 Codificar em `verify_306.py` os cenários da H5 e da H6: 29, 35, 37 (+ 37-devolução; comissão própria do satélite fora da conta), 37b, 38 (+ 38-comprovante), 38c, 39 (+ variante devolução do dia depois do principal cancelado), 40, 41, 42 (mutação apagar e recriar), 42b, 42c (mutação data antiga), 42d, 42e, 33, 43, 44 (+ dois sinos), 45, 45b, 45c (mutações: lista lida da escala; remoção sem a condição)
- [ ] T009 [P] Escrever `specs/306-dinheiro-do-cancelamento/retrato_main_branch.py` (plan Fase 1, item 2; quickstart §3): relógio fixo (`datetime` em `app.financeiro.routes`, `app.api.financeiro_read` e, se existir, `app.financeiro.dre_ops`); `ensure_recurring_entries` neutralizado; DRE Jinja por `template_rendered`; nos meses sem cancelamento, `GET /api/financeiro/dashboard`, `/api/vendas/pipeline`, `/api/admin/desempenho`, `/api/clientes/<id>` (toda cliente com evento), `/api/clientes/`, `/api/clientes/metricas`, `/api/dashboard`, `/api/financeiro/comissoes`, `/api/financeiro/pagamentos`; a `main` aquece Comissões e Planilha antes; fora da comparação e listados à parte: ticket médio Jinja, `sale_count`, item aberto de soma zero e os meses de cada `legado`; não importa nada que só exista na branch
- [ ] T010 [P] Escrever `specs/306-dinheiro-do-cancelamento/contagem_pre_deploy.py` (molde do da 303; plan Fase 1, item 3; quickstart §2): sem `create_app` nem `import app`, `psycopg` ou `psycopg2`, `default_transaction_read_only=on`, `DATABASE_URL` sem `+psycopg`; conta tudo da lista do quickstart §2, inclusive itens abertos de soma zero com linha de valor, `legado` sem dinheiro, devoluções ligadas a evento vivo e vendas vivas com devolução lançada à mão
- [ ] T011 Primeira rodada, sem núcleo: `verify_306.py --regressao | Out-File -Encoding utf8 specs\306-dinheiro-do-cancelamento\verify_306_primeira_falha.txt`, mais o `retrato_main_branch.py` e a contagem; conferir que os verdes são só 1, 23, 26, 27, a regressão do 41 e as partes do 6 e do 28 que já valem hoje, e que o 5 está vermelho (o HEAD dá 400 ao "já cancelado"); qualquer outro verde é defeito do verify; as últimas linhas são a base dos verifies antigos (quickstart §5); commit `test(306): verify, retrato e contagem antes do núcleo`

### Modelo, constantes e migration

- [ ] T012 [P] `app/constants.py`, perto de `NOTA_CICLO_VALOR_TARDIO` (`:466`) e de `SITUACAO_*` (`:573-575`): `REGIME_*` (`venda`, `satelite`, `virtual`, `dia`; `REGIME_LEGADO` derivado, nunca gravado), `MODO_*`, `ALCANCE_TODOS`/`ALCANCE_SO_ESTE_DIA`, `DIA_DO_REPASSE = 5`, `MOTIVOS_AJUSTE_COMISSAO` (prefixo e código da 1e, FR-033), `NOTA_COMISSAO_PROPRIA_DO_DIA` e os 18 `CODIGO_*` com os valores do data-model §6.2 (inclusive `CODIGO_EVENTO_CANCELADO = "cancelado"` e `CODIGO_VALOR_MUDOU`); sem `NOTA_CICLO_CANCELAMENTO`
- [ ] T013 `app/models.py`: `EventCancellation`, `EventCancellationBv` e `EventCancellationElenco` depois de `Event3DDismissal` (`:2376-2403`), colunas, nulidade e índices do data-model §1–§3 (`paid_amount`, `commission_cost`, `sale_handed_over`, `special_expense_id` UNIQUE, `day_event_id` CASCADE NOT NULL), relação declarada no filho com `foreign_keys=` (backrefs `cancelamento` `uselist=False`, `bvs`, `elenco`, `cascade="all, delete-orphan"`); `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO` em `CATEGORIES` (`:1070-1073`); docstrings de `is_cancelled` (`:399-407`), `CommissionPayment` (`:946-956`), `SpecialExpense` (`:1066-1069`, `:1091`, `:1114-1117`) e `is_devolucao_cliente` (`:1159-1162`)
- [ ] T014 `migrations/versions/<rev>_dinheiro_do_cancelamento.py`, escrita à mão (nunca `flask db migrate`): 3 × `create_table`, `down_revision = "a7c3e91f4d28"`, `downgrade` elenco → bvs → cancelamentos, docstring do data-model §10 (aditiva; rollback assimétrico); rodar `flask db upgrade` + `python seed.py` no `manto_local`, conferir `create_app()` com os mappers configurados e a ida e volta do quickstart §4

### Comissão cheia, contas puras, resumo e predicados

- [ ] T015 `app/financeiro/comissoes_ops.py`: comissão cheia em duas camadas (FR-027; plan Fase 1, item 5) — `_base_da_comissao(event, settings, *, venda=None, taxa=None, bv_total=None, custo=None)` com o corpo de hoje de `_event_commission` (`:766-796`) intocado; `_event_commission` vira casca sem argumento; `_beneficiario_comissionado(event, settings)` extraído de `should_have` (`:926-936`); `comissao_cheia_do_evento(...) -> (cheia, beneficiario_id, taxa_usada)` com o portão do beneficiário; `comissao_do_retido(cheia, retido, venda)` pela mesma conta de `bv_que_acompanha` (`orcamento/quote_ops.py:58-85`), teto na cheia, ROUND_HALF_UP, tolerância de R$ 0,01 (FR-028)
- [ ] T016 `app/financeiro/comissoes_ops.py`: predicados únicos — `filtro_estorno_orfao()`, `linha_abre_ciclo` (Python e SQL), `tipo_da_linha(cp)`, `ciclo_de_pagamento_da_linha(cp)` (espelho de `:212-216`, 3º degrau em UTC); o verify compara Python e SQL em todas as linhas do espelho
- [ ] T017 `app/calendar/cancel_ops.py`: exceções e regra — `CancelValidationError(message, field=None, status=400, codigo=None, **extras)` (`:39-44`; `EventoMarcadoError` continua subclasse), `EventoCanceladoError`, `pode_editar_venda_do_cancelado(user)` (Superadmin pelo papel real, o mesmo de `_can_delete()`); `bv_do_retido(cheio, retido, venda) = min(cheio, bv_que_acompanha(cheio, retido, venda))`
- [ ] T018 `app/calendar/cancel_ops.py`: resumo e período (FR-004, FR-005, FR-044) — `filtro_devolucao()` (categoria + `event_id` + aprovado, nunca `disbursement_type`; substitui o `.first()` de `:361-372`), `devolucoes_por_evento(ids)` (molde `cobranca_ops.comprovantes_por_evento`, `:197-214`), `ids_do_grupo(principal_ids)` por consulta, `ResumoCancelado`/`resumo_cancelado`/`resumos_cancelados`/`serializar_resumo_cancelado` (`selectinload` montado dentro da função, nunca constante de módulo), `cancelados_do_periodo(inicio, fim, *, seller_id=None, educamanto_only=False)` (outerjoin com o congelado, vendedor por `coalesce`, filtro de tipo seguro contra nulo, faixa sem fuso, sem dinheiro = fora), `totais_cancelamentos`, `retido_por_vendedor`; `cancel_ops` é folha: `cobranca_ops`, `comissoes_ops`, `group_ops`, `comercial_ops` e `routes` só por import tardio
- [ ] T019 Rodar a rodada inteira e `--nucleo`: B0 verde (1, 23, 26, 27, regressão do 41; 16b cheia 0 no núcleo), resto vermelho pelos motivos da tabela; `ruff check` nos tocados (nenhum erro novo sobre a base de 14) e `ruff format` nos três scripts novos; commit `feat(306): fundação — modelo, migration, comissão cheia em duas camadas e resumo`

**Checkpoint**: o modelo sobe com o `create_app`, a comissão do vivo não mudou número (1, 23) e o núcleo pode começar.

---

## Phase 3: História 1 — a comissão e o BV acompanham o retido (P1) 🎯 MVP (núcleo)

**Objetivo**: retido, comissão do retido e BV do retido calculados, reconciliados por beneficiário no primeiro
repasse aberto, e mostrados em Comissões e na Planilha, sem reescrever o pago.

**Teste independente**: `verify_306.py --nucleo` com os cenários semeados por ORM.

**Fecha com (B1)**: 13, 14, 14b; com `--nucleo`, 7–11, 12 (sem a DRE), 17, 30, as variantes 9/10-desfazer e
16/17-`paid_amount` e, no 8, `simular=True` × `simular=False`. Vermelhos: 2–6, 15, 16, 18, 19, 25, 28, 31, 32, 34,
36 (o ato e as rotas) e H3–H6. Verifies antigos: `verify_305`, `verify_267b`, `verify_267c`, `verify_299`.

- [ ] T020 [US1] `app/financeiro/comissoes_ops.py`: `primeiro_repasse_aberto(seller_id, hoje, *, excluir_event_id=None, travar=False) -> date` (FR-031; R5): mês anterior só nos dias 1 a `DIA_DO_REPASSE` e só se o beneficiário ainda tem ali linha que abre ciclo; senão o corrente; senão o seguinte; "liquidado" = tem linha e nenhuma abre ciclo; teto de 24 ciclos com fallback no corrente; datas da linha = hoje presa ao ciclo; `excluir_event_id` para a prévia não divergir pelo autoflush
- [ ] T021 [US1] `app/financeiro/comissoes_ops.py`: `reconciliar_comissao_do_cancelado(event, alvos, *, motivo, hoje=None, simular=False)` (FR-030, FR-032, FR-033; data-model §7.3): por beneficiário, `falta = alvo − liquidadas` (pago + no banco); falta 0 cancela toda `a_pagar` (nunca linha de R$ 0,00); falta ≠ 0 vai à `a_pagar` mais antiga, as outras canceladas; sem `a_pagar`, linha nova ± ligada à paga (`original_id`) no primeiro repasse aberto; alvo 0 para todo outro beneficiário com linha viva do próprio evento (FR-030); só as linhas do evento, ignorando a comissão própria de outro dia e as marcadas `NOTA_COMISSAO_PROPRIA_DO_DIA` (P-51); EducaManto a pagar na data do evento e positiva nova nessa data se ela não passou; motivo por prefixo de `MOTIVOS_AJUSTE_COMISSAO` e `audit()` por linha; nenhuma mutação de ORM com `simular=True`
- [ ] T022 [US1] `app/financeiro/comissoes_ops.py`: `_sync_commission_payment` (`:914-986`) mantém o retorno da Loja Virtual (`:918-921`), ganha `if event.is_cancelled: return`, perde o `and not event.is_cancelled` (`:930-932`) com `should_have` = `sale_value` ∧ `_beneficiario_comissionado` não nulo, e ganha a regra nova (b): com ajuste vivo e a base de volta a `a_pagar`, reconcilia com alvo = cheia (FR-057, cenário 38c); `_comissao_existente` (`:886-911`) com `original_id IS NULL` e sem a marca da comissão própria
- [ ] T023 [US1] `app/financeiro/comissoes_ops.py`: `_resync_pending_commissions` (`:989-1011`) percorre os eventos por id com `FOR NO KEY UPDATE SKIP LOCKED`, relê `cancelled_at`, pula o travado e commita por evento (Travas, item 4); `liquidar_periodo` (`:249-258`) e `pay_seller_month` (`:631-638`) com `order_by(CommissionPayment.id)`; o desfazer da 267c em `liquidar_item_de_comissao` (`:296-361`) trava os eventos das linhas (`ORDER BY id FOR UPDATE`) antes de `liquidar_periodo(…, linhas="pagas")`
- [ ] T024 [US1] `app/financeiro/comissoes_ops.py`: Comissões — órfão por `filtro_estorno_orfao()` em `_pending_reversals_query` (`:434-450`) e `reversal_ids` (`:548-553`); `no_banco` em `STATUS_LABELS` (`:31-35`), `_month_scoped_query` (`:410`) e `month_ids` (`:533`); `CommissionEntry`/`_to_entry` (`:46-74`, `:453-465`) com `tipo`, `original_id`, `evento_cancelado` (consulta em lote), `ciclo`, `motivo?`; `CommissionKpis`/`get_month_kpis` (`:77-91`, `:581-594`) com `total_no_banco` e `total_month` = pago + no banco + a pagar; `get_month_summary_by_seller` com `month_status` "pendente" por `a_pagar` ≠ 0 (órfão incluído) e `sale_count` só de `original_id IS NULL` (`:570-573`); docstrings `:434-442` e `:468-482`
- [ ] T025 [US1] `app/calendar/cancel_ops.py`: `bv_da_planilha(acr)` (tabela da decisão (a), R8/R9: vivo = valor; `venda` pago ou no banco = `paid_amount`; `venda` não pago = proporcional, `None` quando dá zero; sem congelado = só o pago) e `marcar_status_do_bv(acr_id, status, valor_esperado, actor_name)`: `valor_esperado` não numérico → 400 "Valor esperado inválido." antes de travar; `travar_evento(principal)` → acréscimo `FOR UPDATE populate_existing` → congelados → `atual is None` → 409 `bv_nao_esta_a_pagar`; divergente → 409 `valor_mudou` com a frase da 305 e o `atual`; grava `paid_amount` (data-model §7.4) e `audit`; o desfazer volta ao proporcional
- [ ] T026 [US1] `app/api/financeiro_write.py`: o ramo BV (`:163-194`) chama `marcar_status_do_bv` e responde `{status}` com o `codigo` nos 409; `app/financeiro/routes.py`: o ramo BV do Jinja `set_payment_status` (`:1190-1197`) chama `marcar_status_do_bv(valor_esperado=None)` com `flash` em `bv_nao_esta_a_pagar`
- [ ] T027 [US1] `app/financeiro/routes.py`: `_build_commission_items` (`:904-975`) com `linhas` nos dois itens e o "soma zero com linha de valor não some" só no grupo aberto (`:951-953`); `_build_bv_items` (`:870-901`) com `amount = bv_da_planilha(a)` por import tardio (`None` pula) e resumos em lote; `app/api/financeiro_read.py`: `_serialize_pagamento_item` (`:598-643`) com `commission_lines` e `api_financeiro_comissoes` (`:548-595`) com os campos novos
- [ ] T028 [US1] Exclusão (FR-036): `app/calendar/cancel_ops.py` `aplicar_estorno_comissao` (`:146-173`) com `primeiro_repasse_aberto` por import tardio, ramo `no_banco`, motivo "Exclusão do evento", sem copiar as datas da venda; `app/calendar/routes.py` `_delete_event_flow` (`:4348-4382`) e `app/calendar/sumico_ops.py` `_apagar_vazio` (`:341-356`) travam e releem o evento antes de `_delete_event`
- [ ] T029 [P] [US1] `frontend/apps/internal/src/lib/financeiro.ts`: `CommissionStatus` com `no_banco` (`:194`), `CommissionEntry` (`:198`) e `CommissionKpis` (`:217`) com os campos novos opcionais, `PagamentoItem.commission_lines?` (`:344-362`), `invalidarFinanceiro` exportada (`:300`), `exportComissoesCsv` (`:309`) com o mesmo rótulo de status
- [ ] T030 [P] [US1] `frontend/apps/internal/src/pages/ComissoesPage.tsx`: `formatDate` fatiando a string (`:40-43`), filtro "No banco" (`:243-245`), 4º card tolerando `undefined` (`:378-396`), colunas tipo e ciclo (`:164-170`, `:252-259`, `:435-441`)
- [ ] T031 [US1] `frontend/apps/internal/src/components/Pagamentos/PagamentoItemViews.tsx`: `commission_lines` no detalhe dos dois itens e o valor negativo (`:245`)
- [ ] T032 [US1] Rodar a rodada inteira e `--nucleo`: B1 verde, o resto vermelho pela tabela; `verify_305` (o ramo BV passa por `marcar_status_do_bv`), `verify_267b`, `verify_267c` e `verify_299` contra a base; `cd frontend && npm run typecheck`; ruff; commit `feat(306): história 1 — reconciliação por beneficiário, Comissões e Planilha`

**Checkpoint**: com cancelamentos semeados, a comissão e o BV seguem o retido sem tocar o pago.

---

## Phase 4: História 2 — cancelar e devolver (P1)

**Objetivo**: o Superadmin cancela com Tudo/Parte/Nada, com prévia igual à execução; a devolução nasce aprovada
e fica travada em Gastos Extras; a regra única do cancelado vale em toda porta de dinheiro.

**Teste independente**: cancelar pela API um evento avulso com pago, conferir comissão, BV, devolução e
travas pela conexão separada.

**Fecha com (B2)**: pela API, 2 e 8 (+ prévia = execução nos dias 2 e 10), 2b (sem o aviso), 3, 4 (sem o corte e
a multa), 5 (sem o 5-grupo), 6, 7, 9–11; 12 e 32 sem a DRE; 15, 16 (+ 16-vivo), 17 (sem o satélite), 18 (+
18-inverso), 19 (com o FINANCEIRO), 25 (com as flags do vivo), 28, 30, 31, 34, 36; as variantes 9/10-desfazer e
16/17-`paid_amount` pela API; as partes "COMERCIAL/FINANCEIRO → 409" do 16b, 16c(v) e 16d. Vermelhos: DRE (20–22,
24), 16b–16e do Superadmin, grupo (29, 35, 37–42d) e H6 (33, 40, 42e, 43–45c). Verifies antigos: `verify_303` e
`verify_267` reescritos, `verify_215b`, `verify_205`, `verify_273`, `verify_301`, `verify_307`.

### Núcleo do ato

- [ ] T033 [US2] `app/calendar/cancel_ops.py`: `travar_grupo(event)` (T1: ids por `ids_do_grupo`, `SELECT … WHERE id IN (…) ORDER BY id FOR UPDATE` + `populate_existing()`, relê a composição e dá 409 `grupo_mudou` se mudou; avulso = uma linha) e as leituras T2 (congelados com `populate_existing`), T3 (acréscimos do principal `ORDER BY id FOR UPDATE populate_existing`), T4 (um SELECT só das linhas de comissão, `event_id IN (grupo) OR (seller_id IN beneficiários AND status IN ('a_pagar','no_banco'))`, só com `simular=False`) e T5 (devoluções do grupo, pendentes inclusive) — data-model §8.10
- [ ] T034 [US2] `app/calendar/cancel_ops.py`: `cancelar_evento` (`:254-341`) fatiado em passos de ~30 linhas, na ordem única do plan §Travas: T1–T5 → validar (FR-007; FR-009 com imposto obrigatório só no `venda` com nota, 400 sem nota, negativo ou no corte; FR-010 `_validar_pix_do_bv` gravando recebedor e PIX no acréscimo depois de T3 por `erros_do_bv`; FR-012 com a pendente de qualquer dia do grupo e o extra `dias`) → `desmarcar(motivo=MOTIVO_CANCELADO)` → `flush` → congelar (`commission_rate` por `Decimal(str(…))`, `commission_cost` pela régua da comissão, `paid_at_cancellation`/`paid_amount` sob T3) → `_registrar_devolucao` (`:176-209`, teto = pago do grupo − já devolvido, nome e PIX obrigatórios, aprovada, `cliente`, data de SP) → `flush` → alvo → `reconciliar_comissao_do_cancelado` → `cancelled_at` → limpeza do pedido (`:310-316`) → `ao_cancelar(event, alcance=ALCANCE_TODOS, novo_principal=None)` (sem efeito, FR-062) → `EventLog` sem `created_at` e `_log_sync` → commit; `IntegrityError` do UNIQUE → 409 `ja_cancelado`; 40P01 → 409 `tente_de_novo`; a recusa do líder (`:289-292`) fica até a H5; sai a recusa do marcado (`:282-283`)
- [ ] T035 [US2] `app/calendar/cancel_ops.py`: Google depois do commit, com os ids guardados antes — `gcal.delete_event` (`service.py:495-501`) pelo atributo do módulo, `CALENDAR_SUPPRESS_EVENT_WRITES` lida a cada chamada (chave ausente = travado), pulando marcado, `virtual-local-` e evento sem id; 404/410 = "já não estava"; falha vira `aviso` sem o texto cru (FR-014, FR-015)
- [ ] T036 [US2] `app/calendar/cancel_ops.py`: `resumo_impacto` (`:95-143`) com as chaves novas do contracts §2 (`regime`, `sumiu_do_google`, `ja_devolvido`, `max_devolucao`, `com_nota`, `imposto_aliquota`, `bvs[]`, `comissao{…}`, `acao: "cancelar"` para todo marcado em `:114`) e `previa_cancelamento` com `simular=True` e a mesma conta da execução (`EfeitoCancelamento`, `imposto_referencia` = alíquota × retido ao centavo)
- [ ] T037 [US2] `app/calendar/cancel_ops.py`: `alterar_devolucao(event, *, devolucao_total, nome, pix, observacao, imposto_retido, actor)` nos regimes `venda` e `legado` (FR-017; contracts §3; data-model §7.2): 400 só se `devolucao_total` faltar ou não for número → T1 → T2 → T4 (só no `venda`) → T5 → 409 `nao_cancelado` → 409 `regime_sem_retido` → 400 `fields` → 409 `abaixo_do_piso` → `_aplicar_novo_total(dono, …)` (a aberta absorve e fica uma só; zerada, excluída com `gastos_ops._log`; sem aberta, complemento; regrava `cliente` e completa nome e PIX) → imposto regravado se vier → `reaplicar_cancelado`; `reaplicar_cancelado(event, *, motivo)` no ramo do dinheiro e `reaplicar_por_dinheiro(event)` com a guarda 409 `pago_abaixo_do_devolvido` (decisão (c))
- [ ] T038 [US2] Exclusão e marcado: `app/calendar/cancel_ops.py` `EventoMarcadoError.MENSAGEM` (`:56-59`) "devolva ao Google ou cancele"; `app/calendar/routes.py` `_delete_event_flow` recusa cancelado antes do líder e `delete_calendar_event` (`:4471-4499`) mostra o `flash`; `app/api/agenda_write.py` `api_delete_event` (`:534`) recusa cancelado antes da condição de `:555`, com `codigo`, e mantém o marcado só na exclusão (`calendar/routes.py:4368-4371`); `app/calendar/sumico_ops.py` `MOTIVO_CANCELADO` em `_MOTIVOS_DE_DESMARCAR` (`:60-62`) e `_apagar_vazio` recusando cancelado (FR-021)

### Endpoints e portas

- [ ] T039 [US2] `app/api/agenda_write.py`: `api_cancelar_evento` (`:579`) com o corpo novo e a ordem do contracts §1 (401 → 404 → 403 → trava → 409s → 400 de campo → 409 `max_devolucao_mudou`), `CancelValidationError` → `json_error(msg, status, fields, codigo, **extras)`, sem o `except EventoMarcadoError` (`:607-608`), sem o 400 fixo em `fields.motivo` (`:609-610`); `api_impacto_exclusao` (`:514`) com `?devolucao=`/`&venda_nova=` → `{efeito}`; `PATCH /api/events/<id>/devolucao` novo (contracts §3) com comentário `RBAC:`; `api_listar_cancelamentos` (`:693`) com `resumo` em lote e `devolucao` mantido um ciclo; helper `_recusa_do_cancelado`; 40P01 → rollback + 409 `tente_de_novo` nos endpoints da 306
- [ ] T040 [US2] `app/api/agenda_write.py` e núcleos: regra única do cancelado nas portas (a)–(h) para quem passa no gate de hoje e não é Superadmin (409 `cancelado`; FR-047; contracts §6–§13): `api_update_event_comercial` (`:1210`) na ordem 404 → 403 → satélite (`:1224-1229`) → 409 → 215b (`:1256-1259`); notas (`:1489`, `:1524`, `:1562`), `api_set_parcelas` (`:1644`) e reembolsos (`:1823`, `:1859`) com `travar_evento` do próprio evento e releitura antes do 409 (FR-053); `api_set_acrescimos` (`:1588`) com o 409 e, no vivo, 409 `estado_mudou` quando `substituir_acrescimos` relê cancelado; `app/calendar/comercial_ops.py` `substituir_acrescimos` devolvendo `[]` depois de `travar_evento` (`:208`, `:218`); `app/calendar/orcamento_evento_ops.py` `set_event_orcamento` (`:935`) com 409 para todos que passam em `_can_manage_sale`, antes de aplicar a venda; `api_update_event` (`:1067`) e `app/calendar/event_ops.py` `_gravar_venda_da_edicao` (`:846-879`) com 409 para todos quando um campo de venda chega diferente (`_mesmo_valor`, `_mesma_taxa`, `_mesmo_vendedor`), depois do 400 de `_validate_event_core`
- [ ] T041 [US2] Comprovantes (decisão (c); contracts §9): `app/api/agenda_write.py` `:1747`, `:1778`, `:1803` tomam T1 também no evento vivo, releem `is_cancelled`, dão 409 `cancelado` (só no POST, antes de `_add_payment_record`, `calendar/routes.py:1132-1155`) e chamam `reaplicar_por_dinheiro`; no POST, um 409 depois de salvar o arquivo (`tente_de_novo`, `grupo_mudou`) faz rollback e remove o arquivo novo; resposta = detalhe (201 no POST)
- [ ] T042 [US2] Jinja (contracts §21): `app/calendar/routes.py` despachante `event_detail` (`:1657-1671`), depois de `travar_evento` e de reler, recusa para todos os papéis `update_comercial`, `update_sale`, os três de comprovante e os três de reembolso; `app/financeiro/routes.py` `set_commission_status` (`:1561-1582`) com guarda de uma linha (`flash`) para linha de evento cancelado e `set_payment_status`, ramo de gasto (`:1182-1189`), travando o evento antes de mudar o status de uma devolução de cancelado
- [ ] T043 [US2] `app/api/agenda_read.py` `serialize_event_detail` (`:711`; contracts §0, §5): `event.cancelamento` só com `show_comercial` (dinheiro, PIX e `taxa?` com `show_financeiro`; `elenco?` com a flag); `kpi` ausente no cancelado (`:1105-1110`); `flags.can_edit_venda_cancelado` e `flags.can_edit_pagamentos` calculadas depois de `_role_flags` (`:155-204`); `venda.pode_mudar_taxa`/`pode_trocar_vendedor` (`:998-999`) ∧ flag só no cancelado; `_serialize_acrescimos` (`:544-563`) sem `bv_pix` no cancelado para quem não tem a flag; `_serialize_gastos` (`:507`) no cancelado com o próprio dia e, no `venda`, os dias do ato

### Gastos Extras, Planilha e usuário

- [ ] T044 [US2] `app/gastos/gastos_ops.py` (FR-019, FR-020; R11): `GastoLockedError(field, message, event_id)`, `devolucao_de_cancelado(expense)` avaliado no gasto gravado **e** no gasto como ficaria (caminho inverso: categoria trocada para devolução num gasto ligado a cancelado, multa inclusive → `fields.category`; devolução viva religada a cancelado → `fields.event_id`), `_travar_devolucao` (`travar_evento`; com `event_id` trocado ou no vincular, os dois eventos por id; gasto `with_for_update().populate_existing()`); `_validate_expense_data(…, tipo_atual=None)` (`:194-238`) com o tipo `cliente` só se já era; `create_expense` (`:256-318`), `approve_expense` (`:321-330`), `reject_expense` (`:333-346`), `delete_expense` (`:356-360`), `link_expense_to_event` (`:363-378`) e `edit_expense` (`:381-442`, trava antes das atribuições `:420-428`, comparação depois de normalizar, nome e PIX só com valor não vazio, nunca `approved_with_edits`, `aprovar=True` recusado)
- [ ] T045 [US2] `app/api/gastos_write.py`: os seis endpoints (`:49`, `:82`, `:99`, `:117`, `:153`, `:172`) capturam `GastoLockedError` → `rollback()` + `json_error(msg, 409, fields=…, event_id=…, codigo=CODIGO_DEVOLUCAO_TRAVADA)`, na ordem de cada porta do contracts §16 (o DELETE ganha o `try`); `app/api/gastos_read.py` `_expense_dict` (`:31-57`) com `locked` e `event_cancelled`, e a lista de categorias (`:72`) com "Multa de cancelamento"
- [ ] T046 [US2] `app/api/financeiro_write.py` ramo `expense` (`:147-161`): na devolução de cancelado, `travar_evento`, gasto `FOR UPDATE populate_existing` e `valor_esperado` contra `amount` (divergente → 409 `valor_mudou` "A devolução mudou para R$ X…"); sem o campo, como hoje
- [ ] T047 [P] [US2] `app/admin/user_ops.py` `delete_user` (`:417-442`): bloqueio "cancelamentos" para o vendedor congelado (FR-073)

### Frontend

- [ ] T048 [P] [US2] `frontend/apps/internal/src/lib/eventOps.ts`: tipos opcionais (`ImpactoElenco` `:93-98`, `ImpactoExclusao` `:102-115`, `CancelarEventoInput` `:126-129`, `EventoCancelado` `:243-257`), a união `CodigoRecusaCancelamento` com os 18 códigos ao lado de `CodigoDevolverAoGoogle`, `usePreviaCancelamento` (chave `["evento-previa-cancelamento", id, valor]`, `keepPreviousData`, ≥ 400 ms, decimal com ponto), `useAlterarDevolucao`, `useCancelarEvento.onSuccess` (`:135-155`) invalidando sumidos, notificações, `financeiro-*`, `vendas-dashboard`, `gastos-extras`, `cancelamentos` e `["event"]`, `useDeleteEvent` (`:72-87`) com `invalidarSumidosGoogle`
- [ ] T049 [P] [US2] `frontend/apps/internal/src/lib/agenda.ts` (`cancelamento?` com `taxa?` e `elenco?`; flags `can_edit_pagamentos?`/`can_edit_venda_cancelado?`), `frontend/apps/internal/src/lib/gastos.ts` (`DisbursementType` com `cliente` `:5`, `GastoExtra.locked?`/`event_cancelled?` `:17-41`, `UpdateGastoInput` `:144`) e `lib/eventAttachments.ts` `useEventMutation` (`:46-60`) invalidando `["event"]`, `financeiro-*`, `vendas-dashboard` e `cancelamentos`
- [ ] T050 [P] [US2] Novos `frontend/apps/internal/src/components/EventDetail/CancelamentoDevolucaoBloco.tsx` (Tudo/Parte/Nada, nome e PIX, prévia mantida na tela, "A cliente pagou R$ X") e `CancelamentoBvBloco.tsx` (BV cheio, proporcional e "já pago"; recebedor e PIX obrigatórios quando faltam), com `@manto/money`
- [ ] T051 [US2] `frontend/apps/internal/src/components/EventDetail/ExcluirEventoDialog.tsx`: estado e reset (`:99-118`), `ResumoImpacto` (`:30-74`), confirmação (`:123-152`) com os dois blocos, imposto ("<alíquota>% do retido" pela `imposto_aliquota`), efeito e trava de capacidade (`regime === undefined` → "O sistema está atualizando"); 409 divergente refaz o impacto, 409 `ja_cancelado` invalida e fecha; virtual só com o motivo; marcado com aviso; textos `:68-70` e `:218-221`; nenhum botão morto
- [ ] T052 [US2] Novos `frontend/apps/internal/src/components/EventDetail/ResultadoCancelamento.tsx` (substitui o `KpiGrid` de `ComercialSection.tsx:81-177` no cancelado; botão "Alterar devolução") e `AlterarDevolucaoDialog.tsx` (novo total, piso e teto do servidor, nome, PIX, observação, imposto); `ComercialSection.tsx` escolhe o bloco (`:1225-1236`) e o link de Comissões (`:93-96`); `ResumoSection.tsx` "Recebimento — em aberto" (`:391-411`) → devolução e retido
- [ ] T053 [P] [US2] `frontend/apps/internal/src/components/EventDetail/EventHeader.tsx` (`MOTIVO_SO_DEVOLVER` `:39-41`; "Excluir ou cancelar" sem o `disabled` do marcado `:349-357`; caixa do cancelado `:408-420`; "Analisar e decidir" `:436-444`; "Editar tudo" `:339-346` escondido no cancelado) e `SumiuDoGoogleBanner.tsx` (prop `onCancelar`, botão `w-full sm:w-auto`, texto `:68-69`)
- [ ] T054 [P] [US2] `frontend/apps/internal/src/components/EventDetail/FinanceiroSection.tsx`: `PagamentosPanel` (`:307-386`) com `can_edit_pagamentos !== false` e `error.message` (`:379-381`), erro em editar e excluir (`:129-207`), `NotasFiscaisPanel` (`:388-480`) e `ReembolsosPanel` (`:534-660`) pela flag no cancelado
- [ ] T055 [P] [US2] `frontend/apps/internal/src/components/Pagamentos/PagamentoItemViews.tsx`: `valor_esperado: item.amount` também no `expense` (`:112-116`)
- [ ] T056 [P] [US2] `frontend/apps/internal/src/pages/GastosExtrasPage.tsx`: "Devolução à cliente" no formulário e na tabela (`:528`), `GastoFormValues` (`:124-130`), `formFromExpense` (`:150-160`), `DesembolsoFields` (`:164-242`), `buildPayload` (`:313-316`) carregando e reenviando nome e PIX do tipo `cliente`, campos travados por `expense.locked` com link para o evento (`:369-396`, `:483-590`)
- [ ] T057 [P] [US2] `frontend/apps/internal/src/pages/EventosCancelamentosPage.tsx`: `STATUS_DEVOLUCAO` com `no_banco` (`:29-32`), resumo e todas as devoluções (`:146-176`), PIX só com `show_financeiro`

### Verifies antigos e fechamento

- [ ] T058 [US2] Reescrever `specs/303-sync-nao-apaga-venda/verify_303.py` (`c12_nao_cancela` em `:2339` passa a cancelar o marcado; a exclusão continua recusada com o `MSG_MARCADO` novo em `:167`) e `specs/267-integridade-comissao/verify_267.py` (`:278-289` lê o bloco `cancelamento` de um `legado`)
- [ ] T059 [US2] Rodar a rodada inteira: B2 verde, o resto vermelho pela tabela; `verify_303`, `verify_267`, `verify_215b`, `verify_205`, `verify_273` (base 8/15), `verify_301` e `verify_307` contra a base; typecheck; ruff; commit `feat(306): história 2 — cancelar devolvendo, prévia, devolução travada e regra única do cancelado`

**Checkpoint (MVP)**: o cancelamento de evento avulso devolve, retém, ajusta a comissão e o BV e trava a
devolução. H1 + H2 fecham o valor principal da entrega.

---

## Phase 5: História 3 — DRE e comercial pelo que ficou (P1)

**Objetivo**: o retido entra na DRE (API e Jinja) do mês do cancelamento, e os relatórios comerciais contam o
retido como venda do vendedor congelado.

**Teste independente**: DRE do mês do cancelamento nas duas telas e o retrato `main` × branch dos meses sem
cancelamento.

**Fecha com (B3)**: 20, 22, 24; a parte da DRE do 12 e do 32; o 21 menos o satélite (virtual fecha aqui; a multa
semeada por ORM com `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`); o 23 segue verde. Vermelhos: H4–H6. Verifies
antigos: `verify_271` (Performance da Home).

- [ ] T060 [US3] Novo `app/financeiro/dre_ops.py`: `ROTULO_RETIDO`; `gastos_extras_do_periodo(start, end)` (aprovado menos `filtro_devolucao` ∧ evento cancelado, de qualquer regime, em `Decimal`), que substitui `financeiro/routes.py:294-301` e `financeiro_read.py:243-250`; `tendencia_mensal(today, meses=6)` (tira o cancelado; o retido entra pelo mês de `cancelled_at`, só quando ≠ 0), que substitui `routes.py:394-415` e `financeiro_read.py:365-385`; helpers `_is_permuta`, `_month_range`, `_prev_month`, `_pct` por import tardio de `financeiro/routes.py`
- [ ] T061 [US3] `app/financeiro/routes.py` (Jinja vivo; nada movido): `_compute_drg(…, cancelamentos=None)` (`:205-257`) somando sob `if cancelamentos and cancelamentos["quantidade"]` em receita (`:218`), impostos depois do quantize (`:219-222`), CPV (`:227`) e comissões (`:231`), `retido_cancelamentos` e `n_cancelados` sempre no retorno; `dashboard()` (`:263-575`): `cancelamentos=` em `:316`/`:319` (Projetado `:318` intocado), ticket médio (`:327-330`), barra (`:375-379`), Top Vendedores com o retido antes do corte do top 5 (`:381-392`), Recebimentos Previstos (`:469-473`), selo da NF (`:496-503`), comentário `:280-282`; `/vendas/` `events_q` (`:1454`) com `cancelled_at IS NULL`; `app/templates/financeiro/dashboard.html`: uma linha depois de `:123`, condicionada a `drg_total.n_cancelados`
- [ ] T062 [US3] `app/api/financeiro_read.py` `api_financeiro_dashboard` (`:185-545`): os mesmos toques (`:243-250`, `:262`/`:264`, `:341-342`, `:348-363`, `:365-385`, `:428-432`), NF com `cancelado?`/`retido?` (`:456-465`), `paineis.cancelamentos` sempre (`:522-535`, quantidade 0 sem cancelado), docstring `:188-189` e comentário `:231-232`
- [ ] T063 [US3] `app/financeiro/vendas_ops.py`: `build_kpis(…, cancelados=())` (`:249-298`) com o retido em `total_vendido` do vendedor congelado e a comissão do retido em `comissao_prevista` do beneficiário congelado, `kpis.retido_cancelamentos`, `kpis.n_cancelados`, `kpis.comissao_retido`; `event_payment_status(…, cancelado=False)` e o rótulo (`:32-66`); docstring `:154-157`; `app/api/financeiro_read.py` `api_vendas_pipeline` (`:120-175`) passando `cancelados_do_periodo(start, end, seller_id=scope.seller_id, educamanto_only=scope.educamanto_only)`
- [ ] T064 [P] [US3] `app/api/admin_config_read.py` `api_admin_desempenho` (`:117-178`): filtro `cancelled_at IS NULL` (`:149-157`), `retido_por_vendedor(start.date(), (end − 1 dia).date())` mapeado de id para nome, `vendas[].retido?`, `cancelados?`, `totals.retido?`
- [ ] T065 [P] [US3] `app/clientes/client_ops.py`: `get_client_detail` (`:132-159`; total = vivos + retido, resumos só se houver cancelado), `list_clients` (`:111-129`) e `client_metrics` (`:183-225`) filtrando o cancelado; `app/api/clientes_read.py` (`:90-91`)
- [ ] T066 [P] [US3] `app/api/dashboard_service.py` `compute_performance`: `perf_filter` (`:290-293`) com `cancelled_at IS NULL`
- [ ] T067 [US3] Frontend, no mesmo commit (os dois `Record` de status): `frontend/apps/internal/src/lib/financeiro.ts` (`DreView` `:7-25`, `TopSeller` `:46-51`, `MonthlyTrendItem` `:53`, `FinanceiroPaineis` `:80`, `NotaFiscalPendente` `:119`), `pages/FinanceiroDashboardPage.tsx` (`DreRowKind` `:21`, `dreRows` `:33-58`, `Record` de status com `cancelado` `:60-74`, `DreTable` `:138`, `?? 0` em `:171`, rodapé `:410-414`, barra `:443-472`, selo da NF `:583-598`, tendência `:622-655`; linha do retido por `n_cancelados > 0`) e `pages/VendasPipelinePage.tsx` (`Record` de status `:39-45`)
- [ ] T068 [P] [US3] `frontend/apps/internal/src/lib/vendas.ts` (`VendasKpis` `:43-49` com `retido_cancelamentos?`, `n_cancelados?`, `comissao_retido?`) e `pages/VendasPipelinePage.tsx` `KpiGrid` (`:81-121`, sublinha "inclui R$ X retidos de N cancelamento(s)" somada à do desconto `:96-102`); `lib/adminConfig.ts` (`:87-99`) e `pages/AdminDesempenhoPage.tsx` (`:86-108`); `lib/clientes.ts` (`:41-49`)
- [ ] T069 [US3] Rodar a rodada inteira e o `retrato_main_branch.py`: B3 verde, o 23 idêntico com as mudanças de propósito listadas à parte; `verify_271`; typecheck; ruff; commit `feat(306): história 3 — o retido na DRE e nos relatórios comerciais`

---

## Phase 6: História 4 — dados de venda do cancelado, só o Superadmin (P2)

**Objetivo**: o Superadmin corrige venda, taxa, cortesia, vendedor, acréscimos, parcelas, notas e reembolsos do
cancelado, e tudo se recongela na mesma transação.

**Teste independente**: o Superadmin corrige a venda de um cancelado e a comissão e o BV do retido acompanham.

**Fecha com (B4)**: 16b (sem o satélite, com a variante cheia 0 pela API), 16c, 16d, 16e. Vermelhos: H5–H6.
Verifies antigos: `verify_305` antes de usar a extração no cancelado (T072) e de novo aqui; `verify_215b`.

- [ ] T070 [US4] `app/calendar/event_ops.py` `update_event_comercial` (`:1169-1240`): relê `is_cancelled` depois de `estado_da_venda` (`:1204`) e recusa com 409 `estado_mudou` se o estado mudou; o gancho `sincronizar_comissao` (`:1230-1231`, antes do commit de `:1240`) vira despachante: cancelado → `reaplicar_cancelado`, vivo → `_sync` (B10 da 305 intacta no vivo)
- [ ] T071 [US4] `app/calendar/cancel_ops.py` `reaplicar_cancelado` estendido (FR-049–FR-051; R20): `comissao_cheia_do_evento(…, taxa=congelada, bv_total=Σ original_amount das linhas vivas, custo=commission_cost)`; cortesia/permuta → cheia 0 pelo portão; taxa por `_mesma_taxa`, vendedor por `_mesmo_vendedor`; troca de vendedor por beneficiário (o antigo com alvo 0 no primeiro repasse aberto dele, o novo com o alvo inteiro, congelado regravado); motivos "taxa corrigida" e "correção da venda", para mais e para menos; `updated_at`/`updated_by_id`; `EventLog` UTC
- [ ] T072 [US4] `app/calendar/comercial_ops.py`: extrair `_montar_acrescimos` de `:216-404` em cinco passos de ~30 linhas (ler os itens; casar o bundle antigo sem `id`; recusar BV pago removido ou trocado de tipo; a régua do BV; montar o registro com BV, `valor_visto` e `trocas`), cada um com docstring do porquê; o vivo segue com o `delete`/`add` de `:407-411`; rodar o `verify_305` logo depois, antes de qualquer uso no cancelado (se um passo passar de ~30 linhas sem partir uma regra da 305, registrar no Rastreamento de complexidade do plan)
- [ ] T073 [US4] `app/calendar/comercial_ops.py` `alterar_acrescimos_do_cancelado` (data-model §7.4; contracts §8) reusando `_montar_acrescimos`: grava no lugar pelo `id`, sem `delete`/`add`; 400 `items` para BV pago ausente e para página sem nenhum `id`; `id` repetido; `valor_visto` contra o cheio; BV pago com outro valor ou unidade mantém o gravado (sem recusa, como no vivo); tipo diferente → 400; BV novo em % → 400 "lance em reais"; BV novo nasce com a linha congelada; BV não pago removido apaga acréscimo e congelado; `trocas` com `audit`; `app/api/agenda_write.py` `api_set_acrescimos`, ramo do Superadmin: T1 → T2 → T3 → gravar → `expire(event, ["acrescimos"])` → T4 → `reaplicar_cancelado(motivo="Cancelamento: correção da venda")` → commit → detalhe
- [ ] T074 [US4] Frontend: `frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx` (`VendaPanel.canEdit` pela flag `:919`; `VendaForm` `:186-437` confirma "o retido e a comissão do retido passam a <novo>" e a troca de vendedor; `OrcamentoPanel` `:561-` sem ações; `GrupoPanel` `:1050-1212` sem "Agrupar mais um" nem "Desfazer" no dia cancelado), `ColecoesComerciaisPanel.tsx` (`AcrescimosPanel.canEdit` `:67` pela flag no cancelado; BV pago só leitura), `lib/eventInline.ts` `useUpdateEventComercial` (`:107-114`) invalidando `financeiro-dashboard`, `vendas-dashboard` e `cancelamentos`, e `lib/eventOps.ts` `useSetAcrescimos` (`:313-337`) com `invalidarComercial` (`:300-310`)
- [ ] T075 [US4] Rodar a rodada inteira: B4 verde, o resto vermelho pela tabela; `verify_305` e `verify_215b` contra a base; typecheck; ruff; commit `feat(306): história 4 — o Superadmin corrige a venda do cancelado e tudo se recongela`

---

## Phase 7: História 5 — venda de vários dias (P2)

**Objetivo**: cancelar todos os dias, só um dia, ou o 1º dia com a passagem da venda, com soma igual antes e
depois e o custo sem o dia cancelado.

**Teste independente**: um grupo semeado cancelado das três formas, com o retrato linha a linha da passagem.

**Fecha com (B5)**: a variante 5-grupo; 29, 35, 37 (+ 37-devolução), 37b, 38 (+ 38-comprovante), 38c, 39 (+ a
variante do dia depois do principal cancelado), 41; 42 (sem aviso e ensaio), 42b (sem a multa), 42c, 42d (sem o
cachê pago); as partes de satélite e de corte do 4 (com o piso da devolução do corte), do 16b, do 17 e do 21; do
40, desagrupar e agrupar. Vermelhos: H6. Verifies antigos: `verify_271` (cobrança da Home).

- [ ] T076 [US5] `app/calendar/group_ops.py`: `dias_vivos(event)` (régua única de dias vivos); `CAMPOS_DA_PASSAGEM`/`TABELAS_DA_PASSAGEM` (FR-059; data-model §6.3); `validar_agrupamento` (`:116-139`) e `desagrupar` (`:204-231`) travam e releem em ordem de id e recusam cancelado como principal, satélite e dia a soltar; docstring `:1-32`; `group_events` (`:64-75`) intocado
- [ ] T077 [US5] Traduzir a recusa do grupo nas portas: `app/api/agenda_write.py` `api_agrupar_eventos` (`:2365`), `api_desagrupar_evento` (`:2431`) e `api_remover_satelite` (`:2455`, hoje viraria 500; docstring `:2456-2461`); `app/calendar/routes.py` `_handle_ungroup_event` (`:1580-1591`) e `_handle_group_events` (`:1536-1547`) com `flash`
- [ ] T078 [US5] `app/calendar/group_ops.py` `passar_venda(antigo, novo, *, actor_name, agora)`, sem commit (FR-058–FR-060; R16): T4 nas linhas antes do `UPDATE event_id`; move pelas listas, `orcamento_history_id`, clientes que faltam, `group_leader_id` dos dias; `audit` por linha; `sale_handed_over = true` na linha `dia` do antigo 1º dia; `EventLog` nos dois dias com o retrato e as somas por tipo; `expire` de `satellites`, `group_leader` e das coleções movidas; injetada no `cancel_ops` como o `agrupar` injeta `sincronizar_comissao`
- [ ] T079 [US5] `app/calendar/cancel_ops.py`, o laço do grupo (FR-054, FR-055): `alcance` e `novo_principal_id` (400 `alcance`; 409 `sem_outro_dia_vivo`; 409 `grupo_mudou` se não é o dia vivo mais cedo); "todos": regime `satelite` em cada dia, `desmarcar` por dia, pago e devolvido do grupo, dia já cancelado intocado; `ao_cancelar` por dia (`("todos", None)`; corte `("so_este_dia", None)`; passagem, depois dela, `("so_este_dia", novo)`); a pendente de qualquer dia do grupo recusa com `dias`; a comissão própria de outro dia fora da conta (P-51); sai a recusa do líder (`:289-292`); `resumo_impacto.grupo{principal_id, dias, proximo_principal}`
- [ ] T080 [US5] `app/calendar/cancel_ops.py`, regime `dia` (FR-056, FR-057): `venda_nova` (0 < v ≤ atual) e `sale_value_gross` na mesma proporção (cheio × venda nova ÷ venda, ROUND_HALF_UP); piso da devolução do corte = (pago do grupo − já devolvido − venda nova) − máx(0, pago do grupo − já devolvido − venda atual), abaixo dele 400 `fields.devolucao_valor` (Parte) ou `fields.devolucao_modo` (Nada), e `devolucao_minima` na prévia; teto = pago do grupo − já devolvido; sem PIX do BV; `antes = estado_da_venda(principal)` → venda nova → uma chamada a `acompanhar_bv_da_venda` → `flush` → reconciliar o principal vivo ("Corte de dia: venda diminuiu"); congela antes/depois; `NOTA_COMISSAO_PROPRIA_DO_DIA` marca a comissão própria do novo principal na passagem
- [ ] T081 [US5] `app/calendar/cancel_ops.py`, correções em dia de grupo: `alterar_devolucao` no `dia` (piso = devoluções do dia pagas ou no banco; teto = pago do grupo − aprovadas dos outros dias; 409 `acima_do_teto`; com o principal vivo nada se refaz; com o principal já cancelado em `venda`, T4 e `reaplicar_cancelado(principal)` na mesma transação) e no `venda` em grupo (piso = pagas ou no banco de todos os dias + aprovadas dos dias `dia`; a aberta do principal absorve primeiro e depois as abertas dos `satelite`, por id); comprovante em dia de grupo (`reaplicar_por_dinheiro` refaz o principal cancelado em `venda`; com o principal vivo, só a guarda)
- [ ] T082 [US5] Custo sem o dia cancelado, por `dias_vivos`: `app/api/agenda_read.py` `_compute_kpi` (`:352-421`; cachê `:371-379`, gastos `:380-389`, BV `:390-396`) e `_serialize_gastos` do principal vivo; KPI Jinja em `app/calendar/routes.py` (por volta de `:1781`, `:1814-1816`); `app/financeiro/comissoes_ops.py` `_group_cost` (`:725-730`)
- [ ] T083 [US5] `app/financeiro/cobranca_ops.py`: `VendaResumo` (`:98-195`) com `devolvido` à parte e `recebido` bruto; `saldo`, `quitada`, `sinal_pendente` e `_primeira_parcela_descoberta` (`:265-275`) por recebido − devolvido; `recebido_da_venda` (`:217-221`), `resumir_venda` (`:301-327`); `data_do_grupo` (`:236-243`) intocada; docstrings `:3-6` e `:104-106`
- [ ] T084 [US5] Frontend: novo `frontend/apps/internal/src/components/EventDetail/CancelamentoDiasBloco.tsx` (dias vivos, `alcance`, "Novo valor da venda" com a devolução mínima da prévia, "a venda passa para DD/MM"); `ExcluirEventoDialog.tsx` sem o aviso de líder (`:174-190`) e sem o `disabled` por `is_group_leader` (`:283`), corpo com `alcance`, `novo_principal_id` e `venda_nova`; tipos `grupo?` em `lib/eventOps.ts`; `onSuccess` invalidando `["event"]`; link "a venda passou para DD/MM" no `ResultadoCancelamento.tsx`
- [ ] T085 [US5] Rodar a rodada inteira: B5 verde, H6 vermelha; o 41 (`main` × branch em todos os grupos e cobranças) e o retrato de linhas do 42; `verify_271`; typecheck; ruff; commit `feat(306): história 5 — cancelar todos os dias, só um dia e a passagem da venda`

---

## Phase 8: História 6 — ensaio, avisos, cachê pago e multa (P2)

**Objetivo**: cachê pago recusa o ato; os ensaios caem; elenco e equipes são avisados uma vez; a multa por
escalação vira Gasto Extra, no ato ou depois.

**Teste independente**: cancelar um show com ensaio e dois escalados, com multa para um, e conferir sinos,
e-mails no espião, ensaios no dublê e gastos.

**Fecha com (B6)**: 33, 40, 42e, 43, 44 (+ dois sinos), 45, 45b, 45c e o que faltava do 2b, 4, 42, 42b e 42d. A
rodada chega a `59/59 OK`. Verifies antigos: `verify_272`, `verify_238`.

- [ ] T086 [US6] `app/calendar/cancel_ops.py`: `cache_pago_do_evento(event)` (escalação com talento em pago ou no banco, fora a vaga de presença `e_vaga_de_presenca`), T6 (escalações com talento dos dias alcançados, `ORDER BY id FOR UPDATE`, só no ato), 409 `cache_pago` com `dias` sem gravar nada; 409 `ensaio` para `event_type == "ENSAIO"` (FR-063, FR-064)
- [ ] T087 [US6] `app/calendar/event_ops.py` `delete_ensaio` (`:1791-1811`) separa `_apagar_ensaio_no_banco` (`_clear_event_side_tables`, `apagar_por_entidade("calendar_event", id)`, `delete`, sem commit), com o botão e `_sair_de_show` (`:445-504`) iguais; no ato, ensaios do show capturados antes (id, `google_event_id`, data, local) e apagados no banco na ordem única; Google dos ensaios depois do commit, com a trava (FR-065)
- [ ] T088 [US6] `app/notificacoes/notificacoes_ops.py`: `KIND_EVENTO_CANCELADO` e `KIND_EVENTO_CANCELADO_ESCALA` no catálogo e em `DESTINATARIOS_POR_KIND` (`:54-71`); produtores no molde de `notificar_convite_recusado` (`:252-277`), por `resolver_destinatarios` e na transação: `evento.cancelado` (ENSAIO, um por ato, só com ensaio, `dedupe_key = evento.cancelado:<id da URL>`) e `evento.cancelado_escala` (CASTING sem SUPERADMIN, um por dia com escalados, `?aba=producao`, `urgent` por `ANTECEDENCIA_URGENTE_DIAS`, `dedupe_key = evento.cancelado_escala:<id da URL>:<dia_id>`) (FR-067)
- [ ] T089 [US6] E-mail ao elenco: `send_removal_email` por `send_async` depois do commit, uma vez por pessoa (título e data do principal e do 1º dia vivo), fora quem recusou e a vaga de presença; `app/calendar/casting_ops.py` `assign_role`: o `if` do e-mail de remoção (`:153-161`) ganha `and not event.is_cancelled` (FR-066, FR-069)
- [ ] T090 [US6] `app/calendar/cancel_ops.py`: `event_cancellation_elenco` gravada no ato, uma linha por escalação (vaga × dia); `lancar_multas_do_cancelado` pelo ORM (aprovado, `fornecedor`, `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`, nome e `Talent.pix_key`, PIX vazio permitido; data do cancelamento no ato e do lançamento depois, P-34), nunca por `create_expense`; vazio ou 0 ignorado; 400 `fields.multa_<id>` para negativo, inválido, vaga fora dos dias alcançados, linha de outro evento ou já lançada; multas no ato na ordem única (`cancelled_at` → `ao_cancelar` → ensaios, sinos e multas → `EventLog`) (FR-070–FR-072)
- [ ] T091 [US6] `app/api/agenda_write.py`: `POST /api/events/<id>/multas` novo (contracts §4: 401 → 404 → 403 → T1, T2 → 409 `nao_cancelado` → 400; nada com valor > 0 → 400 `fields.multas` "Informe a multa de ao menos um artista") com comentário `RBAC:`; impacto com `ensaios`, `elenco[].role_id`, `talent_pix_informado`, `faltam_dias`, `cache_pago`; `cancelamento.elenco?` só com a flag; `EventLog` com ensaios, multas e avisados
- [ ] T092 [US6] Frontend: novo `frontend/apps/internal/src/components/EventDetail/MultaAoElencoBloco.tsx` (uma linha por escalação com artista, vaga e dia, cachê de referência, "faltavam N dias", aviso de talento sem PIX) e `LancarMultaDialog.tsx` (botão "Lançar multa ao elenco" no `ResultadoCancelamento.tsx`); `useLancarMultas` em `lib/eventOps.ts`; no `ExcluirEventoDialog.tsx`, a recusa de cachê pago sem botão e apontando Gastos Extras, e as frases do ensaio e dos avisos; ícones dos dois kinds em `components/notificacoes/NotificacaoItem.tsx` (`:7-13`)
- [ ] T093 [US6] Rodar a rodada inteira: `59/59 OK` com todas as variantes e mutações quebrando; `verify_272` e `verify_238` contra a base; typecheck; ruff; commit `feat(306): história 6 — cachê pago, ensaios, avisos e multa ao elenco`

---

## Phase 9: Polimento e portões

- [ ] T094 FR-074, os textos que mentem: `ExcluirEventoDialog.tsx` (`:68-70`, `:218-221`), `lib/eventOps.ts` (`:131-134`), docstrings de `cancel_ops` (`:147-156`, `:183-185`, `:264-265`) e de `api_cancelar_evento` (`agenda_write.py:580-586`), `financeiro_read.py` (`:188-189`, `:231-232`), `financeiro/routes.py:280-282`, `cobranca_ops.py` (`:3-6`, `:104-106`), `vendas_ops.py:154-157`, comentários de `models.py`, `group_ops.py:1-32`, `config.py:145-162`
- [ ] T095 Portões de código: `cd frontend && npm run typecheck` (três SPAs) e `npm run build`; `ruff check` nos `.py` alterados contra a `main` (nenhum erro novo sobre a base de 14) e `ruff format` só nos arquivos novos (`verify_306.py`, `retrato_main_branch.py`, `contagem_pre_deploy.py`, `dre_ops.py`)
- [ ] T096 Portões de verificação: `verify_306.py` sem argumentos (`59/59 OK`) e com `--regressao`; `retrato_main_branch.py` idêntico; os verifies antigos do quickstart §5 (`303`, `267`, `267b`, `267c`, `299`, `215b`, `305`, `205`, `266`, `258`, `256`, `273`, `301`, `272`, `238`, `271`, `307`) iguais ou melhores que a base; a ida e volta da migration (quickstart §4)
- [ ] T097 Tela aberta (skill `manto-conferir-tela`; quickstart §8, os 21 itens), com `verify_306.py --semear-tela`, o Flask do worktree com o Google dublado e o app interno do worktree no Browser pane, logado com os descartáveis; `--limpar-tela` no fim
- [ ] T098 Contagem final no espelho com `contagem_pre_deploy.py`, gravada em `specs/306-dinheiro-do-cancelamento/contagem_<data>.txt`
- [ ] T099 Docs (CLAUDE.md §6; plan §Docs): `docs/00` §4 (regra única do cancelado) e §6 (ordem de travas e "relê depois de travar"); `docs/01` §4.3 (os dois endpoints novos, `_can_delete()` com o `PATCH …/devolucao`, uma linha por porta alterada), contratos, catálogo de notificações, categoria, modelos, códigos 409, correção de `:770-771`; `docs/02` (diálogo, tela do cancelado, Gastos, Comissões, Planilha, DRE, marcado; `:464-465`, `:1500-1501`); `docs/04` (invariantes; `:314`, `:316-318`, `:320`, `:359`); `docs/05` (as dívidas do plan §8 Polimento e da spec, riscando o que quita, inclusive a 101); `DEVELOPMENT.md` (`:110-115`, `:151`) e `CLAUDE.md` §4
- [ ] T100 `docs/03`: entrada no topo e linha no índice (a 224g passa a fechada), com as mudanças de comportamento intencionais (plan H3), o rollback assimétrico e os números da contagem; a entrada só diz "EM PRODUÇÃO" depois do push que o dono pedir
- [ ] T101 `/speckit-converge` sem gaps (revisão adversarial da entrega; cada achado confirmado vira cenário vermelho antes da correção, como na 305)
- [ ] T102 Antes do merge (quickstart §7 e §9): branch rebaseada sobre a `main` do dia com as citações reconferidas; build num venv Python 3.11 com `requirements.txt`, `pip freeze` comparado com o da produção (SSH só leitura), `flask db downgrade a7c3e91f4d28 && flask db upgrade && python seed.py` e o verify nesse venv; contagem em produção por SSH, só leitura; `git status --short` limpo e `migrations/versions/` sem untracked; relatório ao dono com o que muda nos dados de hoje (quickstart §9). **Não fazer push**: o merge e o push são do pedido do dono

---

## Dependências e ordem

- **Setup (T001–T002)** → **Foundational (T003–T019)**: o verify e os scripts (T003–T011) vêm antes de qualquer
  linha de núcleo; T012–T018 dependem da primeira rodada (T011).
- **US1 (T020–T032)** depende da Fundação. **US2 (T033–T059)** depende da US1 (reconciliação, `bv_da_planilha`,
  `marcar_status_do_bv`). **US3 (T060–T069)** depende da US2 (o ato grava o que a DRE lê). **US4 (T070–T075)**
  depende da US2. **US5 (T076–T085)** depende de US2 e US4 (`reaplicar_cancelado`, acréscimos no lugar). **US6
  (T086–T093)** depende de US2 e US5 (o ato e os dias alcançados). **Polimento (T094–T102)** depois de tudo.
- A ordem das fases é a do plan; cada uma fecha com a rodada inteira antes de abrir a seguinte (verde fora de hora
  é defeito).
- Arquivos que várias fases tocam (`cancel_ops.py`, `agenda_write.py`, `comissoes_ops.py`, `financeiro/routes.py`,
  `ExcluirEventoDialog.tsx`) seguem sequenciais, na ordem das tarefas.

## Paralelismo

- **Fundação**: T009 e T010 em paralelo com T005–T008 (arquivos diferentes); T012 em paralelo com T013.
- **US1**: T029 e T030 (frontend) em paralelo com T020–T028 (backend).
- **US2**: T047 em paralelo com o núcleo; T048–T050 e T053–T057 (frontend, arquivos diferentes) em paralelo entre
  si e com T044–T046.
- **US3**: T064, T065, T066 e T068 em paralelo com T060–T063.
- **US4–US6**: frontend (T074, T084, T092) depois do backend da própria fase, porque lê os contratos novos.

## Estratégia

- **MVP**: Fundação + US1 + US2 — o cancelamento de evento avulso com devolução, retido, comissão e BV certos e a
  devolução travada. É o que o dono pediu primeiro ("dinheiro primeiro").
- **Incremento 2**: US3 (DRE e relatórios), que fecha as P1.
- **Incremento 3**: US4, US5 e US6 (P2), cada uma com a rodada inteira verde até ali.
- **Entrega**: um deploy só, à noite, quando o dono pedir (plan §Deploy); nada de push parcial.
