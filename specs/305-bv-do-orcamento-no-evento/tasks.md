---
description: "Tasks da feature 305 — BV do orçamento chega ao evento"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Feature 305 — O BV do orçamento chega ao evento

**Input**: `specs/305-bv-do-orcamento-no-evento/` (spec, plan, research R1–R11, data-model, contracts/api.md)

**Verificação (Princípio VIII)**: `verify_305.py` é escrito na Phase 2, ANTES do núcleo, e roda
vermelho pelos motivos certos; cada história fecha com os seus cenários verdes.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 Conferir `.specify/feature.json` → `specs/305-bv-do-orcamento-no-evento` e recontar no espelho, só leitura (`docs/backlog/ferramentas/sql_ro.py`): orçamentos com BV (35), eventos ligados sem linha (1218, 1236, 1268), linhas em `event_acrescimos` (5; 1 BV sem PIX, evento 403); anotar em `specs/305-bv-do-orcamento-no-evento/contagem_2026-10-14.txt`

---

## Phase 2: Foundational (bloqueia as histórias)

- [X] T002 Escrever `specs/305-bv-do-orcamento-no-evento/verify_305.py` com TODOS os cenários da tabela da spec (1–27, 31–40, 42–49, 51–56, limpeza 50): Google dublado (molde `verify_273.py`), login só por `POST /api/auth/login`, requisições fora do `app_context`, escrita conferida por conexão separada (a comissão lida SEM abrir a Planilha — o `_resync` esconde o defeito), eventos R&I, usuários Comercial/Financeiro/Casting/Artista 3D/Superadmin descartáveis, orçamentos fictícios (inclusive um como o 2407: Outro 13.800 + Outro 3.500 + BV 10%), constante do corte trocada por monkeypatch em `orcamento_evento_ops`, datas com folga > 3h (TZ do manto_local), mutações declaradas dos cenários 17 e 49, limpeza no `finally`
- [X] T003 Rodar o verify contra a HEAD e guardar a saída em `specs/305-bv-do-orcamento-no-evento/verify_305_primeira_falha.txt` (esperado: vermelho em B1–B10; verdes já: 19–24, 27 parcial)

---

## Phase 3: História 1 — criação leva o BV certo (P1) 🎯 MVP

**Fecha com**: cenários 1–8, 10–13, 31 (criação), 37, 40, 44, 46 verdes.

- [X] T004 [P] [US1] `app/orcamento/quote_ops.py`: importar `NF_DIVISOR` (float) de `app/educamanto/pricing_ops.py` e usá-lo em `:364`; função pura `bv_que_acompanha(bv, venda, total) -> Decimal` (Decimal(str()), HALF_UP, total ≤ 0 → 0,00, |venda − total| ≤ 0,01 → cheio; docstring R3)
- [X] T005 [US1] `app/orcamento/quote_ops.py`: B2 — no laço `:346-353` gravar `a["valores_brl"]` (4 durações, Decimal HALF_UP, `float`), sem tocar `valores`; no ramo personalizado (`:374-382`) zerar `[0.0]*4`; tipo `valores_brl?: number[]` em `frontend/apps/internal/src/lib/orcamento.ts:76-81`
- [X] T006 [US1] `app/calendar/orcamento_evento_ops.py`: B1 `acrescimos_do_orcamento(entry, duracao)` — `valores_brl` válido (lista de 4 finitos ≥ 0 ≤ total) → senão conta inversa com base quantizada → senão pula a linha; duração > 4h pela régua linear com o total do prefill/`total_custom`; personalizado → vazio; nunca levanta exceção (R1)
- [X] T007 [US1] `app/calendar/orcamento_evento_ops.py`: `bv_que_vai_nascer(...)` (a pergunta da B8, mesmas guardas da B3) e B3 `gravar_acrescimos_do_orcamento(event, entry, duracao, *, recebedor, pix, duracao_origem)` — guarda por consulta (evento cancelado ou com qualquer linha), todas as linhas em R$ na proporção (R3), origem na `descricao` (≤ 200), BV `nao_pago` com recebedor/PIX, resultado (criados, total de BV, duração/origem, motivo); flush + `expire(event, ["acrescimos"])`
- [X] T008 [US1] `app/calendar/routes.py`: em `_create_event_core`, chamar a B3 no `if entry is not None:` depois de `:3736` e antes do `EventLog` de `:3767`; `EventLog` do BV sem PIX; descartar `data["acrescimos"]` em TODA criação; remover `_criar_acrescimos_do_orcamento` (`:3273-3305`) e a chamada de `:3361`; limpar `ROUND_HALF_UP`/`EventAcrescimo` dos imports se ficarem sem uso
- [X] T009 [US1] `app/api/agenda_write.py`: `_build_create_event_data` lê `bv_recipient`/`bv_pix` (texto; outro tipo → 400) e `duracao_informada`; `api_create_event` faz a B8 depois da guarda 1:1 (`:892-903`) e antes do Google (`:905`), 400 com `fields` e a mensagem do PIX no topo
- [X] T010 [US1] `app/calendar/routes.py`: dedução de duração (valor bruto ±0,01 → horas 1–4h ou `duracao_custom` → não grava) quando o corpo veio sem `duracao`; B8 na criação Jinja (depois de `validation_errors`, antes do Google, `_render_error` "crie pela tela nova…")
- [X] T011 [US1] `app/calendar/routes.py`: B5 — `_build_orcamento_prefill` usa `snapshot_do_orcamento` e devolve `acrescimos_do_orcamento` (personalizado, linhas com `valores_brl` 1–4 e `custom`); a chave antiga continua
- [X] T012 [US1] Rodar o verify: cenários da US1 verdes; ruff nos tocados

---

## Phase 4: História 2 — "Vincular e aplicar" (P2)

**Fecha com**: 14, 31 (vínculo), 32, 34, 38 (troca), 42.

- [X] T013 [US2] `app/calendar/orcamento_evento_ops.py`: `aplicar_valores_do_orcamento` ganha `bv_recipient`/`bv_pix`, relê o evento com `FOR UPDATE` ANTES da guarda "sem venda" (`:290`), chama a B3 no lugar de `:308-312` e devolve o resultado; `set_event_orcamento` repassa os campos, monta `acrescimos_criados`, `bv_total`, `acrescimos_ignorados` (fora do `if aplicar…`), e a frase (`_frase_relatorio`: BV, quem recebe, mês da Planilha, efeito na comissão; "confira o BV" quando o evento já tinha linha BV); `resumo_do_orcamento` ganha `bv`
- [X] T014 [US2] `app/api/agenda_write.py`: `api_set_event_orcamento` lê `bv_recipient`/`bv_pix` e faz a B8 depois da autoria da 301 (`:1345-1355`) e antes de `set_event_orcamento` (`:1357`), só com `entry` e `aplicar_valores_duracao`
- [X] T015 [US2] Rodar o verify: cenários da US2 verdes

---

## Phase 5: História 3 — editor de Acréscimos (P2)

**Fecha com**: 9, 16, 17, 18, 21, 33, 35, 36, 43, 47, 49 (parte 1), 51, 52, 55.

- [X] T016 [US3] `app/calendar/comercial_ops.py`: reescrever `substituir_acrescimos` — linhas antigas por `SELECT … FOR UPDATE`; casar por `id` (herda status, PIX vazio, descrição ausente, valor congelado de pago/no banco); sem id nasce `nao_pago` (heurística só do bundle antigo); valor por `parse_brl`; tipo normalizado ("bv" → "BV"); % arredondado a 2 casas; régua do BV em % (R7) só `nao_pago`; venda sem valor: % existente mantém, % novo recusado; BV em R$ como digitado; pago/no banco congelados (R$ e %); B8 (recebedor/PIX obrigatórios, 200/140) ANTES do delete; recusa levanta `AcrescimosRecusados` com erros por índice da requisição; no fim flush + `expire(event, ["acrescimos"])`; régua não roda em cancelado
- [X] T017 [US3] `app/api/agenda_write.py`: `api_set_acrescimos` captura `AcrescimosRecusados` → rollback + 400 com `fields` `items.<i>.<campo>`; sincroniza a comissão (`_sync_commission_payment`) antes do commit; atualizar a docstring (`:1511-1517`)
- [X] T018 [US3] `app/calendar/routes.py`: `_handle_update_comercial` captura `AcrescimosRecusados` → `db.session.rollback()` + `flash` + return; corrigir o comentário de `:857-858`
- [X] T019 [P] [US3] `app/api/agenda_read.py`: `_serialize_acrescimos` devolve `descricao` e `bv_pix` (só no bloco `show_comercial`, já gateado no chamador)
- [X] T020 [US3] Rodar o verify: cenários da US3 verdes; `verify_249`/`verify_251` locais

---

## Phase 6: História 4 — alerta (P2)

**Fecha com**: 15, 45, 56.

- [X] T021 [US4] `app/calendar/orcamento_evento_ops.py`: constante `CORTE_ALERTA_BV` (naive UTC) e `bv_do_orcamento_pendente(event, *, novo_vinculo=False)` — condições da R8 (sem linha BV com valor > 0; venda de verdade; não cancelado, não satélite; corte por `created_at` ou `EXISTS` "Vinculou o orçamento #<id> (" ≥ corte); devolve `{valor, percentual, duracao}` com o valor em R$ pela B1 + proporção e a duração deduzida
- [X] T022 [US4] `app/api/agenda_read.py`: bloco `venda` ganha `bv_do_orcamento_pendente` e `orcamento.bv` (sem o id do orçamento para quem não tem o módulo; buscar o orçamento pelo `event.orcamento_history_id`, nunca pela variável mascarada de `:939-941`)
- [X] T023 [US4] `app/calendar/event_ops.py`: `update_event_core` acrescenta em `warnings` a linha do alerta quando a gravação o deixa aceso
- [X] T024 [US4] Rodar o verify: cenários da US4 verdes

---

## Phase 7: História 5 — a venda que muda depois (P3)

**Fecha com**: 38, 39, 48, 49 (parte 2), 53, 54.

- [X] T025 [US5] `app/calendar/comercial_ops.py`: `acompanhar_bv_da_venda(event, antes, *, actor_name, tz) -> str | None` (R9): gatilho venda ou nota; R$ `nao_pago` pelo líquido (grava `amount_brl` e `value`); % pela régua; volta de "a definir": % recalculado, R$ só aviso; pago/no banco intactos; cancelado/satélite: nada; `EventLog` sem PIX; devolve o aviso
- [X] T026 [US5] `app/calendar/event_ops.py`: `update_event_comercial` captura (venda, nota, cortesia) antes de `:1186`, chama a B10 antes do sync e devolve o aviso; `_gravar_venda_da_edicao` idem, com o aviso em `warnings` de `update_event_core`
- [X] T027 [US5] `app/api/agenda_write.py`: `api_update_event_comercial` devolve `aviso_bv` (re-serializa, molde de `:1076-1078`), mantendo a recusa da 215b antes
- [X] T028 [US5] `app/calendar/routes.py`: `_handle_update_comercial` captura (venda, nota, cortesia) ANTES de `:841`, roda a B10 DEPOIS de `substituir_acrescimos` (`:883`) e antes do sync, `flash` do aviso; pula cancelado/satélite
- [X] T029 [US5] Rodar o verify: cenários da US5 verdes

---

## Phase 8: História 6 — o passado (P3)

- [X] T030 [US6] Conferir no verify os cenários 25 e 45 (lado "antes do corte") e que 1218/1236/1268 não ganham linha nem alerta no espelho

---

## Phase 9: Frontend (interno)

- [X] T031 [P] `frontend/apps/internal/src/lib/{eventCreate,agenda,eventInline,eventOps}.ts`: tipos opcionais (`acrescimos_do_orcamento?`, `bv_recipient?`/`bv_pix?` nos corpos, `EventAcrescimo.descricao?`/`bv_pix?`, `AcrescimoInput.id?`, `venda.orcamento.bv?`, `venda.bv_do_orcamento_pendente?`, relatório `acrescimos_criados?`/`bv_total?`/`acrescimos_ignorados?`, `aviso_bv?`); invalidar `["financeiro-pagamentos"]` e `["financeiro-comissoes"]` nas mutações de criação, edição, `/comercial`, `/orcamento` e acréscimos
- [X] T032 F1 `frontend/apps/internal/src/pages/EventCreatePage.tsx`: quadro do BV na duração (valores do servidor), aviso de proporção, campos "Quem recebe o BV" e "PIX de quem recebe" fora do react-hook-form (obrigatórios quando o BV vai nascer; `maxLength`; 400 caindo neles, inclusive quando o prefill falhou), textos de cortesia/"a definir"/personalizado; hooks antes de qualquer return
- [X] T033 F2 `frontend/apps/internal/src/components/EventDetail/ColecoesComerciaisPanel.tsx`: abrir com `id`, `descricao` só quando presente, `bv_pix ?? ""`; valor em `MoneyInput` (R$) ou parse pt-BR (%) enviando número; rótulo do % do BV e a ajuda com os dois exemplos; linha BV nova em %; recebedor/PIX obrigatórios com `maxLength`; erro do 400 na linha pelo índice; "Lançar o BV" por `?lancar=bv` com `useEffect` (preenche em R$, apaga o parâmetro); bloqueia o Salvar se os BVs mudaram no cache desde o abrir(); alerta F4 no topo
- [X] T034 F3 `frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx` (OrcamentoPanel): chip do BV, campos no "Vincular e aplicar" (lidos do prefill; aparecem também quando o 400 os traz), frase do relatório
- [X] T035 F4 `ComercialSection.tsx` (VendaPanel/VendaForm, sem tocar as linhas do 215b) e `frontend/apps/internal/src/pages/EventEditPage.tsx` (entre `ValoresBlock` e `PagamentoBlock`): o alerta com "Lançar o BV" levando a `?aba=comercial&lancar=bv`; `aviso_bv` sobe do VendaForm ao VendaPanel e aparece depois do salvar
- [X] T036 `cd frontend && npm run typecheck` limpo

---

## Phase 10: Polimento

- [X] T037 Regressão (cenário 27): `verify_273`, `verify_267b`, `verify_301`, `verify_215b`, `verify_267c`, `verify_267`, locais 249/251/210; verify_305 inteiro verde com as mutações quebrando
- [X] T038 Tela aberta (quickstart §4) no Browser pane com usuários temporários, backend sem Google
- [X] T039 Docs: `docs/01` (contratos), `docs/02` (Novo evento, aba Comercial, alerta), `docs/03` (entrada + índice), `docs/04` (corrigir "só o Jinja escreve acréscimos"; invariantes do BV), `docs/05` (riscar o que toca acréscimos; cinco dívidas novas + "cancelar e recriar lista dois BVs até a 1b")
- [X] T040 `ruff check` nos tocados, `ruff format` nos novos, `npm run build`
- [ ] T041 Antes do merge: recontagem só leitura em produção (3.7) e `CORTE_ALERTA_BV` com o momento do deploy no último commit (literal naive em UTC; o cenário 58 confere)

## Phase 11: Converge (14/10) — revisão adversarial, 29 de 37 achados confirmados

- [X] T042 Cenários 58–68 no `verify_305.py`, rodados vermelhos antes (`verify_305_converge_primeira_falha.txt`); `--so=` para iterar
- [X] T043 Backend: corte vazio fecha; proporção pelo líquido (`plano_dos_acrescimos(nota=)`); `_valor_digitado` recusa o ambíguo e ≥ 10¹⁰; BV vazio/zero/negativo e `id` repetido → 400; `travar_evento` em `estado_da_venda` e `substituir_acrescimos`; B10 no "Vincular e aplicar"; Jinja não reproporciona o BV redigitado; `AuditLog` da troca de PIX no BV pago; `set-status` com `valor_esperado` (409) em `app/calendar/{orcamento_evento_ops,comercial_ops,routes}.py`, `app/api/{agenda_write,financeiro_write}.py`
- [X] T044 Frontend: R$ por `MoneyInput` e % convertido (número no PUT); "Lançar o BV" em reais; a linha que vira BV não reinterpreta valor digitado; `salvar.reset()` ao abrir/cancelar/remover; `?lancar=bv` com o editor aberto só acrescenta; `setQueryData` no PUT; invalidação financeira na criação e na edição; Cancelar do painel Orçamento limpa quem recebe/PIX; campos do BV no Novo evento quando o 400 os pede; `valor_esperado` na Planilha
- [X] T045 Regressão: verify_305 64/64 com `--regressao`; locais 249/251 ajustados ao "[] não apaga BV pago" (18/18, 19/19); typecheck das três SPAs; tela conferida; docs 01/03/04/05 e research/contracts/data-model/quickstart

## Phase 12: Segundo converge (15/10) — 14 achados sobre as correções, 12 confirmados

- [X] T046 Cenários 69–72 e o 59 com a nota trocada; o 58 passa a exigir o literal da T041 (fica vermelho até ela) — `verify_305_converge2_primeira_falha.txt`
- [X] T047 Backend: Jinja BV a BV (`bvs_a_pagar_por_valor`, `acompanhar_bv_da_venda(so_os_reenviados=)`), texto cru no Jinja, `valor_visto` no PUT, `_valor_digitado` ao centavo, `populate_existing` nos `FOR UPDATE`, `travar_evento` em `set_event_clients` e antes dos clientes no Jinja, nota e divisor no prefill
- [X] T048 Frontend: quadro do Novo evento compara líquidos; `valor_visto`; lixeira e Cancelar travados durante o Salvar/Aplicando; o negativo não BV mantém o sinal
- [X] T049 Regressão, typecheck e docs

## Dependências

Setup → Foundational → US1 (MVP) → US2 → US3 → US4 → US5 → US6 → Frontend → Polimento. US2, US4 e US5
reusam B1/B3 da US1; US4 e US5 reusam a régua da US3. Paralelo: T004 com T006; T019 com T016; T031
com o backend.
