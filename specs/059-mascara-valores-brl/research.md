# Research: Máscara padrão para campos de valor em reais (059)

Decisões técnicas. Sem `NEEDS CLARIFICATION`.

## 1. Estado atual (diagnóstico)

- **Máscara já existe e é exatamente a pedida**: `app/static/js/money-mask.js` aplica a todo
  `input.brl-input` uma máscara "calculadora" (RTL, `.` milhar, `,` centavos, 2 casas). Expõe
  `window.MoneyMask = { init, format, applyMask }` e auto-inicializa no load + para nós
  dinâmicos via `MoneyMask.init(root)`.
- **Backend já tem parser único**: `app/money.py` → `parse_brl` (aceita mascarado BR, cru e
  americano), `parse_brl_int`, `format_brl` (filtro Jinja `brl`).
- **A maioria dos campos de R$ já usa `class="brl-input"`** (eventos, pagamentos, salário,
  gastos). Esses estão OK.
- **Campos de R$ fora do padrão** (usam `type="number"` nativo):
  - `orcamento/index.html`: `acrescimo_valor`, `cust_valor_1h|2h|4h` — **alimentam cálculo ao
    vivo** em `orcamento.js` via `parseFloat`.
  - `orcamento/settings.html`: `ator_*`, `cantor_base_*` (preços em R$). *(NÃO `markup_*` —
    multiplicadores.)*
  - `orcamento/historico.html`: `min_val`, `max_val` (filtros de R$).
  - `educamanto/package_form.html`: `ensemble_1s|2s|_days`, `item_cost_1s|2s|_days` (R$). *(NÃO
    `margin_*`, `discount_pct`, `commission_rate` = %/multiplicador; NÃO `item_qty`,
    `item_ensemble_add` = contagens.)*
  - `event_create.html`: `desc-val` (valor de desconto em R$, calc ao vivo). *(NÃO `desc-pct`.)*

## 2. Reutilizar a máscara (não recriar) — Princípio I

- **Decisão**: aplicar `class="brl-input"` + `type="text" inputmode="decimal"` aos campos de R$
  hoje fora do padrão, removendo `type="number"`/`step`/`min`/`max` (incompatíveis com texto).
- **Rationale**: FR-001/FR-002 — uma única fonte de comportamento já testada em produção.

## 3. Calculadoras ao vivo (Orçamento / desconto do evento) — ponto de risco

- **Problema**: `orcamento.js` faz `parseFloat(el.value)` em `acrescimo_valor`/`cust_valor_*`;
  `event_create` faz o mesmo em `desc-val`. Com a máscara, `parseFloat("1.500,00") → 1.5`.
- **Decisão**: estender `MoneyMask` com um helper **`parseNumber(valueOrInput)`** (dígitos →
  centavos → número com 2 casas) e trocar os `parseFloat` desses campos por `MoneyMask.parseNumber`.
  Onde o JS **escreve** valor de volta no campo (ex.: default de markup `el.value = markup[i]`),
  usar `MoneyMask.format`/`applyMask` para gravar já formatado.
- **Rationale**: Princípio IV (não quebrar o cálculo). Mantém a fonte única (estende, não duplica).
- **Alternativa rejeitada**: deixar esses campos fora do padrão — contraria "TODOS os campos".

## 4. Backend: trocar `float()/int()` por `parse_brl`/`parse_brl_int`

- **Decisão**: nas rotas que hoje leem os campos convertidos com `float()/int()` direto, usar
  `parse_brl`/`parse_brl_int`:
  - `app/educamanto/routes.py` — `ensemble_*` (→ `parse_brl`), `item_cost_*` (→ `parse_brl`).
    *(`item_qty`, `item_ensemble_add` seguem `int()`.)*
  - `app/orcamento/settings.py` — preços `ator_*`/`cantor_base_*` (→ `parse_brl`/`parse_brl_int`
    conforme o tipo guardado). *(`markup_*` seguem `float()`.)*
  - `app/orcamento/routes.py` — filtros `min_val`/`max_val` do histórico (→ `parse_brl`).
  - `acrescimo_valor`/`cust_valor_*`: chegam ao backend via **snapshot JSON numérico** gerado
    pelo `orcamento.js`; como o JS passa a guardar número (via `parseNumber`), o
    `float(snap.get("acrescimo_valor"))` em `calendar/routes.py` **continua válido** — sem
    mudança de backend ali.
- **Rationale**: `parse_brl` aceita tanto cru quanto mascarado → conversão segura e
  retrocompatível (FR-005, FR-008).

## 5. Campos dinâmicos

- **Decisão**: garantir `MoneyMask.init(novaLinha)` ao adicionar linhas (itens de pacote
  Educamanto, parcelas/personagens). Várias telas já chamam; auditar e completar.

## 6. Sem mudança de modelo / migration

- **Decisão**: nenhuma. Colunas `Float`/`Numeric` continuam guardando reais; a máscara é
  apresentação + parsing. Sem migration.

## 7. Classificação R$ vs não-R$ (escopo)

- **R$ (recebem máscara)**: cachê, viagem, venda (bruto/líquido), pagamentos/parcelas (valor),
  salário, gastos, preços/custos de orçamento e educamanto, acréscimo em valor, desconto em R$.
- **NÃO R$ (inalterados)**: %/taxas (comissão %, desconto %, tax_rate, fator_r), markup/margens
  (multiplicadores), contagens (parcelas, quantidades, `ensemble_add`), dimensões (altura),
  tempos (minutos).
