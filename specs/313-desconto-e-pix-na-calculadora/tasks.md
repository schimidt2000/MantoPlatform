---
description: "Tasks da feature 313 — desconto e PIX na calculadora"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Feature 313 — desconto e PIX na calculadora

**Input**: artefatos em `/specs/313-desconto-e-pix-na-calculadora/`

**Pré-requisitos**: plan.md, spec.md (histórias e "Verificação"), research.md (R1–R12), data-model.md,
contracts/api.md, `pesquisa/reconferencia-2026-10-21.md` (as linhas `arquivo:linha` abaixo vêm dela, contra
`c074657b`).

**Verificação (Princípio VIII)**: `gabarito_paridade.py` e `verify_313.py` na Foundational, antes do núcleo; a
primeira rodada contra a `main` fica em `verify_313_primeira_falha.txt`.

**Histórias** (spec): US1 = desconto (H1), US2 = proposta e PIX (H2), US3 = a ordem da conta (H3), US4 = o evento
(H4). A ordem de construção é US3 → US1 → US2 → US4 (o desconto se aplica sobre a conta da US3).

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [ ] T001 Conferir `.specify/feature.json` → `specs/313-desconto-e-pix-na-calculadora`; criar `env313.ps1` no
      scratchpad (o `env312.ps1` com `C:\tmp\mp313`); contar os `form_snapshot` do `manto_local` (só leitura) e anotar
- [ ] T002 Copiar `.local-db-url` (já na raiz do worktree) e conferir que `specs/305-…/verify_305.py`,
      `specs/307-…/verify_307.py`, `specs/309-…/verify_309.py` e `specs/235-…/verify_235.py` rodam verdes na
      `c074657b` — a base da regressão (o `scripts/db/verify_190_paridade_orcamento_educamanto.py` saiu: importa
      `EducaMantoPackage`, que a 235 removeu)

---

## Phase 2: Foundational (bloqueia as histórias)

- [ ] T003 Escrever `specs/313-desconto-e-pix-na-calculadora/gabarito_paridade.py` (só leitura, sem
      `create_app` de threads: `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`): para cada `OrcamentoHistory` com
      `form_snapshot` JSON, montar o payload como o "Recalcular" faz (`personalizado_ativo` → `personalizado`,
      `OrcamentoCalculadoraPage.tsx:249-278`) e chamar `quote_ops.calculate_quote`; gravar `{id: {quote, snapshot}
      | {erro}}` em JSON no caminho dado por `--gravar`; e `--comparar <json>` que devolve as diferenças por chave
      (ignorando as chaves novas do data-model)
- [ ] T004 Rodar o gabarito na `c074657b` (antes de qualquer mudança em `app/`) → `<scratchpad>\gabarito313.json`;
      anotar contagem, erros e o hash
- [ ] T005 Escrever `specs/313-desconto-e-pix-na-calculadora/verify_313.py` inteiro — os cenários 1–16 e L da spec
      (tabela "Verificação"), no molde do `verify_312.py` (usuários descartáveis Comercial/Superadmin/Financeiro/
      Casting/Revendedor EducaManto; Google dublado; `cenario()`, `--so`, limpeza no `finally`; escrita conferida por
      conexão separada; orçamentos montados por `POST /api/orcamento/calcular` + `/salvar`, nunca `EventRole`
      inventada). O cenário 1 chama o `--comparar` do T003 e confere cada exceção da R11 pela fórmula; o 13 usa um
      orçamento salvo **sem** `versao_conta` (o caso do `verify_305` cen_04: BV de 375 em 6h); o 16 roda as
      regressões do T002 como subprocesso
- [ ] T006 Rodar o `verify_313.py` contra a `main` e guardar a saída em
      `specs/313-desconto-e-pix-na-calculadora/verify_313_primeira_falha.txt` (verdes esperados: 7, 13, 15, 16, L)
- [ ] T007 Commit `docs(313): gabarito de paridade e verify antes do núcleo`

---

## Phase 3: US3 — A ordem da conta: o acréscimo uma vez, o BV sobre tudo (P1)

**Objetivo**: FR-006, FR-007, FR-008 (marca), FR-009, FR-018 (só a parte do editor). **Prova**: cenários 1, 8, 9, 10.

- [ ] T008 [US3] Em `app/orcamento/quote_ops.py`, criar `aplicar_acrescimos(base, acrescimos, nota)` (R1): (a) não
      BV — R$ inteiro, % sobre a `base`; (b) BV em % sobre `base + Σ(a)`, cada BV sobre o mesmo número; BV em reais
      inteiro; (c) `÷ NF_DIVISOR` se `nota`. Devolve o preço e os valores por linha (o que cada uma somou). Float
      com `round(x, 2)` como a conta de hoje (`:443-480`), **na mesma ordem de soma** nos casos sem exceção (`add` a
      partir de 0,0 na ordem do snapshot; a base do BV = `t + add_dos_não_BV`, sem arredondar — analyze B5);
      docstring com a ordem do dono (Q7)
- [ ] T009 [US3] Em `quote_ops.py`, trocar o trecho de acréscimos + nota (`:443-480`) por `aplicar_acrescimos` por
      coluna, guardando antes as `bases` (o `totals` antes dos acréscimos); manter a memória ("Acréscimo: …", "Nota
      fiscal") com os valores da função e `valores_brl` em Decimal HALF_UP a partir dos valores da função (305,
      `:452-466`)
- [ ] T010 [US3] Em `quote_ops.py`, criar `preco_na_duracao(snap, horas)` (R1): base da duração (1–4h = `bases[i]`;
      >4h = `(bases[3] − produtos_total) ÷ 4 × h + produtos_total`) + `aplicar_acrescimos`; **acima de 4h sem acréscimo
      em R$ (nem BV em reais) e sem produto, `round(bruto_4h ÷ 4 × h, 2)`** (o arredondamento de hoje — analyze A2);
      devolve `{bruto, linhas, total}` (o `total` com o desconto do snapshot, quando houver — a US1 preenche); no personalizado, acima de 4h, a
      régua sobre `brutos["4h"]` e o final = cheio × (1 − d) (analyze B7). Trocar a extra (`:482-488`) por ela;
      `produtos.total_na_duracao` fica só para o legado (`produtos.py:283-292`, sem mudança)
- [ ] T011 [US3] Snapshot (`quote_ops.py:715-749`): `versao_conta: 2` (constante `VERSAO_CONTA`), `bases`,
      `brutos` (data-model); o `quote` ganha `base_4h`
- [ ] T012 [US3] Personalizado (`quote_ops.py:493-534`): continua sem acréscimos; `brutos` = os valores
      personalizados; `bases` ausente (R7)
- [ ] T013 [US3] Conferir `produtos.parte_do_produto_no_total` (`produtos.py:269-280`) e
      `_produtos.bloco_da_mensagem` para orçamento novo: nenhum chamador novo depende do `(1+Σ%)÷0,84` (só o legado
      pelo `total_na_duracao`); registrar no research se algum depender
- [ ] T014 [P] [US3] EducaManto (`app/educamanto/quote_ops.py:124-129`): `pop` de `desconto_pct`, `desconto_valor`,
      `desconto_duracao` junto dos de `event_date`/`produtos` (R8)
- [ ] T015a [US3] Atualizar `specs/309-produtos-de-tabela/verify_309.py` para a regra da 313 (analyze A1): as chaves
      novas do data-model em `CHAVES_NOVAS` (`:70`); o caso "6h com BV 10% + fixo 200" (`:765-788`) com os números da
      Q7 (BV sobre a base com o fixo, o fixo uma vez); registrar no `docs/03` da 313 que o golden da 309 mudou por
      regra do dono
- [ ] T015 [US3] Rodada: cenários 1, 8, 9, 10 verdes; `verify_309` verde (com a T015a) (o 1 com as exceções conferidas pela fórmula); `ruff`; commit
      `feat(313): a ordem da conta — o acréscimo uma vez e o BV sobre tudo (Q7/Q9)`

---

## Phase 4: US1 — O desconto em % ou pelo valor fechado (P1)

**Objetivo**: FR-001, FR-002, FR-003, FR-005, FR-008 (desconto), FR-010. **Prova**: cenários 2, 3, 4.

- [ ] T016 [US1] Em `quote_ops.calculate_quote` (`:106`), ler `desconto_pct`, `desconto_valor`, `desconto_duracao`
      (contracts); validar (FR-010, `QuoteValidationError` com o campo, `:43-49`); com valor + duração, achar `d`
      sem arredondar sobre o cheio daquela duração (R6: só durações que o resultado mostra — `show` já forçado em
      1h no só-produto, `:580-583`; "extra" só com `total_custom`); valor igual ao cheio = sem desconto
- [ ] T017 [US1] Passo do desconto, último da conta: `bruto_* = totals` antes; `total_* = round(bruto × (1 − d ÷
      100), 2)`, a duração digitada com o valor exato; também a extra e o personalizado (R7); memória "Desconto (N%)"
      tipo `pos`, negativa, depois da nota — só com desconto (analyze A4)
- [ ] T018 [US1] `quote` com `bruto_*`, `desconto_pct` (exato), `desconto_pct_texto` (R5: `floor(round(d, 6) × 10) ÷
      10`, vírgula, sem ",0"), `desconto_modo`; snapshot com o digitado (`desconto_pct_digitado`, `desconto_valor`,
      `desconto_duracao`) e `desconto_aplicado`; `preco_na_duracao`
      aplicando `desconto_aplicado` (e o valor exato quando a extra foi a digitada)
- [ ] T019 [US1] BV que acompanha no `quote`: `bv_*` = `bv_que_acompanha(BV cheio da coluna, total, bruto)`
      (`quote_ops.py:59-86`, sem mudar a função); memória "BV a repassar a quem indicou" tipo `subtotal` depois do
      total, quando há BV **e desconto** (sem desconto a memória é a de hoje — analyze A4); `bv_*` como `float()` no
      `quote` (o `bv_que_acompanha` devolve Decimal, que o `jsonify` viraria texto — analyze B9)
- [ ] T020 [P] [US1] Histórico: `_entry_summary` (`app/api/orcamento_read.py:125`) ganha `desconto_pct` lido do
      `form_snapshot` (`desconto_aplicado` > 0; um `json.loads` por linha, até 300 — aceito, analyze A19)
- [ ] T021 [US1] Rodada: + cenários 2, 3, 4 verdes; regressão 1, 8, 9, 10 continua; commit `feat(313): o desconto em
      % ou pelo valor fechado`

---

## Phase 5: US2 — A proposta diz o desconto e o PIX vale o maior (P1)

**Objetivo**: FR-004, FR-011–FR-015. **Prova**: cenários 5, 6, 7.

- [ ] T022 [US2] PIX no núcleo: `PIX_PCT_PADRAO = round((1 − AVISTA_FATOR) × 100, 6)` (`app/educamanto/pricing_ops.py:29`,
      importado ao lado do `NF_DIVISOR`, `quote_ops.py:18`; sem o `round` dá 5,000…04 — analyze A3); `pix_pct`, `pix_*`
      (R4), a frase do "já está aplicado" com `round(d, 6) >= PIX_PCT_PADRAO`; com negociado ≥ 5%, `pix_d = total_d`
      e `bv_pix_d = bv_d` sem recalcular (analyze B4); senão `bv_pix_*` pela mesma função
- [ ] T023 [US2] Mensagem (`quote_ops.py:555-650`): `_dur_block` pelo cheio (`:555-562`, a quebra `:558`) com "de/por"
      e "_(desconto de N% aplicado)_" quando há desconto; os três formatos (durações, produto + avulsos,
      só-produto — o "Total da visita" sempre aparece com desconto, `:586-592`); o bloco do PIX pelos `pix_*` com as
      duas frases (contracts); sem desconto, a string de hoje byte a byte
- [ ] T024 [US2] PDF (`app/orcamento/pdf.py:160-193`, `:235-245`): "R$ Y (de R$ X)" na linha de cada duração, uma
      linha "Desconto de N% aplicado", o PIX lido de `pix_*` (legado `round(total × 0,95, 2)`), a frase do PIX com
      negociado ≥ 5%; conferir que cabe na página com a nota da data especial (`:215-228`)
- [ ] T025 [US2] Rodada: + cenários 5, 6, 7 verdes; regressão; commit `feat(313): a proposta diz o desconto e o PIX
      vale o maior`

---

## Phase 6: US4 — O evento nasce com o cheio e a venda (P1)

**Objetivo**: FR-021 (servidor), FR-023, FR-024; FR-025 (sem mudança de regra, provada no cenário 12). **Prova**:
cenários 11, 12, 14 (7, 13 e 15 são regressão, verdes desde a Foundational).

- [ ] T026 [US4] `app/calendar/orcamento_evento_ops.py`: `_bruto_da_duracao(entry, d)` ao lado de
      `_total_da_duracao` (`:165-191`) — legado (sem `versao_conta`, ou snapshot inválido pela validação da R2, com o
      cruzamento `bases` × `brutos` — analyze B8) = hoje, os dois iguais; v2 = `brutos[f"{d}h"]` /
      `preco_na_duracao(...)` (R3); personalizado v2 acima de 4h pela R7
- [ ] T027 [US4] `acrescimos_do_orcamento` (`:283-344`): v2 tira as linhas, de 1h a 4h, do `valores_brl` (a fonte do
      `bv_*` do `quote` — analyze B8) e, acima de 4h, de `preco_na_duracao(...)["linhas"]` (sem
      `_conta_inversa` nem `_linhas_na_duracao`, `:233-280`) e devolve como `total` o **cheio**; legado igual;
      `_valor_gravado` com o cheio como teto (`:216-230`)
- [ ] T028 [US4] `deduzir_duracao` (`:347-369`) compara o `bruto` com o cheio e, sem casar, com o final (o bruto
      vazio, o gêmeo Jinja e o bundle velho gravam bruto = final — analyze B6); `bv_nasce_no_vinculo` (`:452-463`) usa
      o final como venda; `plano_dos_acrescimos` (`:383-442`) sem mudança além do `total` que recebe (a proporção
      entre líquidos fica, research R3)
- [ ] T029 [US4] Prefill — `_build_orcamento_prefill` (`app/calendar/routes.py:3322-3416`): `bruto_1h..4h`,
      `bruto_custom`, `desconto_pct` (o `desconto_aplicado` do snapshot — analyze A5), `extra_por_horas` (5–24, v2 não
      personalizado) e `total_custom` pela R1 para v2; `_acrescimos_do_prefill` (`:3419-3452`) com `valores_final` por
      linha (analyze A7); legado como hoje (`:3376-3393`)
- [ ] T030 [US4] Vínculo 273 — `aplicar_valores_do_orcamento` (`:864-916`): `sale_value` = final, `sale_value_gross`
      = cheio (`:904-905`), pelo prefill da T029, com `bruto_{d}h ?? total_{d}h` para o legado (analyze B12)
- [ ] T031 [US4] Rodada: + cenários 11, 12, 14 verdes (o 12 com o alerta de BV pendente — analyze A14); `verify_305 --regressao` verde (cen_04); commit
      `feat(313): o evento nasce com o cheio e a venda, e o BV encolhe junto`

---

## Phase 7: Telas (US1–US4)

- [ ] T032 [P] [US1] `frontend/apps/internal/src/lib/orcamento.ts`: tipos opcionais — Input (`:169-202`) com as três
      chaves; `Quote` (`:230-280`) com `bruto_*`, `base_4h`, `desconto_*`, `pix_*`, `bv_*`, `bv_pix_*`;
      FormSnapshot (`:455-484`) com o digitado; `OrcamentoHistoricoEntry` (`:396-413`) com `desconto_pct`
- [ ] T033 [P] [US1] `frontend/apps/internal/src/lib/desconto.ts` (novo): `textoDoPercentual(d)` (R5) e
      `percentualDoDesconto(bruto, venda)`
- [ ] T034 [US1] `OrcamentoCalculadoraPage.tsx`: bloco Desconto no card "Ajustes Finos" (`:707-820`) — campo de % e
      "ou fechar [duração] por R$" (`MoneyInput`), as durações pelos `show_*`/`valor_unico`/`total_custom` do
      resultado (R6); o payload (`:311-367`) só com o modo ativo; o outro campo só leitura do resultado vivo; erro
      do desconto ao lado do bloco (hoje soltos em `:825-829`); o % mostrado é o `desconto_pct_texto` do servidor
      quando vier (analyze A20); estado em `INITIAL_STATE` (`:64-88`), `resetAll`
      (`:280-306`) e "Recalcular" (`:249-278`, zerando em snapshot antigo); frase do personalizado (Session 5)
- [ ] T035 [US1] Card Resultado (`:831-887`): cheio riscado e final; linha do PIX; "BV a repassar" (com desconto e
      no PIX) quando há BV; esmaecido "recalculando…"/"corrija os campos" por `resultadoVivo` (R9, hoje só
      `calcular.isPending`, `:837`); ajuda da "Duração extra" (`:720-730`, a frase de `:729`) com a conta da Q7
- [ ] T036 [P] [US3] (FR-018, a parte do editor — a única tarefa de tela da US3) `components/orcamento/AcrescimosEditor.tsx`: props `tipoBv` e `ajuda` (R8); a linha que troca
      para o tipo BV nasce com "%" marcado; a gravada reabre como foi; passar as props na calculadora (`:702`) e no
      EducaManto (`EducaMantoCalculadoraPage.tsx:886-892`, ajuda sem "acompanha o desconto")
- [ ] T037 [P] [US2] `OrcamentoResultadoPage.tsx`: "de/por" e o PIX por duração (`:37-57`), BV a repassar fora da
      mensagem (só com desconto); fallback `bruto ?? total`, PIX só quando `pix_*` vier; o card do transporte
      (`:261-292`) não muda
- [ ] T038 [P] [US1] `OrcamentoHistoricoPage.tsx`: selo "−N%" ao lado do Badge de show (`:275`) por `desconto_pct`
- [ ] T039 [US4] `lib/eventCreate.ts` (`OrcamentoPrefill`, `:51-71`): `bruto_*`, `bruto_custom`, `desconto_pct`,
      `extra_por_horas` opcionais; `EventCreatePage.tsx`: prefill (`:212-213`), `selectDuracao` (`:286-293`) e
      `selectDuracaoExtra` (`:301-314`) gravando cheio e final separados (`bruto ?? total`, o legado — analyze B12); "Outra (h)" (`:750-801`, preço `:779-796`)
      pelo `extra_por_horas` quando vier, com o campo de 5 a 24 h (legado: a régua de hoje — analyze A8)
- [ ] T040 [US4] `components/EventFormBlocks/BvDoOrcamentoBlock.tsx` (`:60-90`; montado em
      `EventCreatePage.tsx:818-842`): mostra o `valores_final` da linha (o servidor fez a conta) quando a venda é o
      total do orçamento; venda digitada à mão → "calculado ao salvar", como hoje (nenhuma conta de dinheiro no
      navegador — analyze A7); o aviso de "valor diferente" (`:73-79`, `:90-95`) cala quando a venda é o total
- [ ] T040a [US4] `components/EventDetail/ComercialSection.tsx` (o vínculo 273, `:786-797`): o BV que o vínculo vai
      gravar pelo `valores_final` do prefill, não o `valores_brl` cheio (analyze B3)
- [ ] T041 [P] [US4] `components/EventFormBlocks/ValoresBlock.tsx`: o selo (`:74`, `:186-190`) por
      `textoDoPercentual` (FR-022)
- [ ] T042 Typecheck (`cd frontend && npm run typecheck`); commit `feat(313): telas — o desconto na calculadora, a
      proposta, o histórico e o Novo evento`

---

## Phase 8: Polimento

- [ ] T043 Rodada inteira do `verify_313.py` duas vezes seguidas; limpeza com zero sobra
- [ ] T044 [P] Regressão: `verify_305.py --regressao`, `verify_307.py`, `verify_309.py` (com a T015a),
      `verify_235.py`; `ruff check` nos tocados contra HEAD
- [ ] T045 Tela aberta (skill `manto-conferir-tela`) pela lista do `quickstart.md` §3; o PDF aberto de verdade; a
      mensagem e o PDF no viewport mobile
- [ ] T046 [P] `docs/01` (contrato do cálculo, prefill, vínculo; a ordem da conta; a linha de RBAC em §4.3 — nenhum
      gate muda), `docs/02` (calculadora, orçamento
      gerado, histórico — o filtro por valor passa a olhar o total final, analyze B13 —, Novo evento), `docs/04` (a ordem da conta do orçamento e o BV do evento pelo cheio),
      `docs/05` (o núcleo em float — a justificativa do plano; riscar o que quitar)
- [ ] T047 `docs/03`: entrada nova no topo + linha no índice (a reconferência; as exceções da Q7 e quantos
      orçamentos atingem; as premissas da Session)
- [ ] T048 `/speckit-converge` e, por achado confirmado, cenário vermelho no verify antes da correção
- [ ] T049 Pré-merge: `main` do dia na branch, rodada inteira e regressão de novo; `git status` limpo; merge e push
      **só quando o dono pedir**, à noite

---

## Dependências e ordem

- Setup → Foundational (T003–T007) → US3 → US1 → US2 → US4 → Telas → Polimento.
- US1 depende da US3 (o desconto incide sobre a conta nova); US2 depende da US1 (o PIX e a proposta leem o cheio e
  o desconto); US4 depende da US1 e da US3 (o evento lê `versao_conta`, `bases`, `brutos`).
- As telas dependem das chaves do servidor (fases 3–6), mas cada arquivo é independente.

## Paralelismo

- US3: T014 em paralelo com T008–T013 (arquivo do EducaManto).
- US1: T020 em paralelo (arquivo do histórico).
- US4: T030 depois da T029 (o vínculo lê o prefill).
- Telas: T032, T033, T036, T037, T038, T041 em paralelo; T034/T035 (mesmo arquivo) sequenciais; T039/T040 depois
  do T032.

## Cenários por fase (esperado ao fechar)

| Fase | Verdes | Vermelhos |
|---|---|---|
| Foundational (T006, contra a `main`) | 7, 13, 15, 16, L | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14 |
| US3 | + 1, 8, 9, 10 | 2–6, 11, 12, 14 |
| US1 | + 2, 3, 4 | 5, 6, 11, 12, 14 |
| US2 | + 5, 6 | 11, 12, 14 |
| US4 | todos (7, 13 e 15 seguem verdes como regressão) | — |

## Estratégia

Uma entrega só (a noite do desconto), sem migration, num push à noite quando o dono pedir. MVP = US3 + US1 + US2 (a
calculadora e a proposta); a US4 entra no mesmo deploy, porque sem ela o evento grava o cheio igual à venda (o bruto
se perderia) e o BV não encolheria.
