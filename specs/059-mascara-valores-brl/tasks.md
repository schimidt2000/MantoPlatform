# Tasks: Máscara padrão para campos de valor em reais

**Feature**: `059-mascara-valores-brl` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Reutiliza `money-mask.js` (front) e `parse_brl`/`parse_brl_int` de `money.py` (back). Sem
migration. Verificação contra **`manto_local` (Postgres)**, não SQLite.

Convenção: `[P]` = paralelizável (arquivos diferentes); `[US#]` = história relacionada.

---

## Fase 1 — Fundação (pré-requisito de tudo)

- [X] T001 Adicionar `MoneyMask.parseNumber(valueOrInput)` em `app/static/js/money-mask.js` — recebe string ou input `.brl-input`, retorna `Number` (ex.: `"1.500,00"` → `1500`), `0` se vazio/ inválido. Expor em `window.MoneyMask`. Reusa `digitsToCents` (não duplicar lógica).

---

## Fase 2 — US2: Converter campos de entrada de R$ + parsing no backend (P1)

**Objetivo**: campos de R$ hoje fora do padrão passam a usar a máscara e gravam corretamente.
**Teste independente**: abrir cada tela, conferir máscara, salvar e reabrir com valor correto.

### Templates (front) — paralelizáveis

- [X] T002 [P] [US2] `app/templates/gastos/index.html`: adicionar `class="brl-input"` ao input `amount` (já é `text inputmode=decimal`, só falta a classe).
- [X] T003 [P] [US2] `app/templates/orcamento/settings.html`: converter `ator_*` e `cantor_base_*` (preços R$) para `type="text" inputmode="decimal" class="brl-input"` (remover `step`). **NÃO** tocar em `markup_*` (multiplicadores).
- [X] T004 [P] [US2] `app/templates/orcamento/historico.html`: converter filtros `min_val`/`max_val` para `class="brl-input"` (remover `type=number`/`step`/`min`).
- [X] T005 [P] [US2] `app/templates/educamanto/package_form.html`: converter `ensemble_1s|2s|1s_days|2s_days` e `item_cost_1s|2s|1s_days|2s_days` para `class="brl-input"`. **NÃO** tocar `margin_*`, `discount_pct`, `commission_rate`, `item_qty`, `item_ensemble_add`, `discount_days`. Garantir que a linha de item criada por JS (`addRow`) chame `MoneyMask.init(novaLinha)`.

### Backend (rotas) — após os templates correspondentes

- [X] T006 [US2] Rota de criação de gasto (`app/gastos/` ou onde processa `POST` de gasto): ler `amount` com `parse_brl` (não `float()` direto). Conferir o nome do arquivo da rota.
- [X] T007 [US2] `app/educamanto/routes.py`: trocar `float(request.form.get("ensemble_*"))` e os `item_cost_*` por `parse_brl(...)` (com defaults preservados). `item_qty`/`item_ensemble_add` seguem `int()`.
- [X] T008 [US2] `app/orcamento/settings.py`: ler preços `ator_*`/`cantor_base_*` com `parse_brl`/`parse_brl_int` (conforme tipo guardado). `markup_*` seguem `float()`.
- [X] T009 [US2] `app/orcamento/routes.py`: ler filtros `min_val`/`max_val` (histórico) com `parse_brl`.

**Checkpoint US2**: salvar e reabrir um pacote Educamanto, um preço de Orçamento, um gasto e um
filtro de histórico — valores corretos; registro inalterado permanece idêntico (FR-008).

---

## Fase 3 — US1: Calculadoras ao vivo padronizadas sem regressão (P1)

**Objetivo**: campos de R$ que alimentam cálculo ao vivo passam a usar a máscara, com o cálculo
intacto. **Teste independente**: digitar valores e conferir que os totais ao vivo batem.

- [X] T010 [US1] `app/templates/orcamento/index.html`: converter `cust_valor_1h|2h|4h` para `class="brl-input"`. **Exceção**: `acrescimo_valor` NÃO convertido — é campo duplo (R$ **ou** %, conforme o radio); mascará-lo quebraria o modo percentual. Documentado como exceção (igual aos campos de %).
- [X] T011 [US1] `app/static/js/orcamento.js`: em `setAcrescimo` e `setPersonalizadoVal`, trocar `parseFloat(val)` por `MoneyMask.parseNumber(val)`. Onde escreve valor de volta no campo (default de markup `el.value = markup[i]` e o teste `parseFloat(el.value)===0`), usar `MoneyMask.format`/`applyMask` e `MoneyMask.parseNumber`. Garantir `MoneyMask.init` após render que cria esses inputs.
- [X] T012 [US1] `app/templates/event_create.html` (+ JS de `calcDesconto`): converter `desc-val` para `class="brl-input"` e ler seu valor via `MoneyMask.parseNumber` em `calcDesconto`. **NÃO** tocar `desc-pct` (%).

**Checkpoint US1**: acréscimo de `R$ 500,00` soma 500 (não 5); valores personalizados e desconto
em R$ refletem corretamente nos totais.

---

## Fase 4 — US3: Garantir que campos não-monetários ficaram intactos (P2)

- [X] T013 [US3] Revisar os arquivos tocados e confirmar que nenhum campo de %/taxa, markup/ margem, contagem (parcelas, quantidades, `ensemble_add`), dimensão (altura) ou tempo (minutos) recebeu `brl-input`. (Conferência negativa — diff review.)

---

## Fase 5 — Polish & Verificação

- [X] T014 Verificar contra **`manto_local`** seguindo `quickstart.md` (passos 1–4): submeter formulários (Educamanto, Orçamento settings, gasto, histórico) via app real/test client e conferir gravação; conferir calculadoras ao vivo.
- [X] T015 `ruff check` nos arquivos Python tocados — comparar contagem com `git stash` para garantir **zero erros novos**.
- [X] T016 Marcar itens do `quickstart.md` e fechar `tasks.md`.

---

## Dependências

- **T001** bloqueia T011 e T012 (usam `parseNumber`).
- Templates (T002–T005, T010, T012-front) podem ir em paralelo; cada rota (T006–T009) depende do template correspondente apenas para o teste, não para editar.
- T013–T016 ao final.

## MVP

US2 (Fase 2) já entrega a maior parte do valor: a maioria dos campos hoje fora do padrão fica
consistente. US1 (Fase 3) completa o pedido "TODOS os campos" cobrindo as calculadoras ao vivo.
