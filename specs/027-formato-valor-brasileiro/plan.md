# Implementation Plan: Padronizar valores monetários no padrão brasileiro

**Branch**: `027-formato-valor-brasileiro` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Criar **uma fonte única** de formatação de dinheiro (backend) e **um helper único** de máscara
(frontend, estilo calculadora), aplicar em todas as exibições e campos de valor, e garantir que o
backend converta a string mascarada de volta para número antes de salvar. Sem migration; não altera
dado gravado.

## Constitution Check

- **I. Reutilizar** ✅ — consolida os parsers/formatadores duplicados em um só; reaproveita o filtro
  `brl` e os parsers BR já existentes em vez de criar paralelos.
- **III. Camadas / sem string mágica** ✅ — formatação/parse viram util compartilhado, não cópias
  inline por template/rota.
- **IV. Não quebrar** ✅ — todo campo recém-mascarado tem seu parse no servidor revisado; verificação
  no app real. Sem migration.
- **V. Feedback** ✅ — valor preservado e formatado após erro de validação.
- **VII. Valor monetário BR (novo)** ✅ — é a razão da feature.

## Decisão de UX (confirmada com o usuário)

Máscara **estilo calculadora**: os dígitos preenchem da direita pra esquerda, centavos sempre
presentes. Ex.: digitar `400000` → `4.000,00`. Resolve a ambiguidade do "4000".

## Estado atual (levantamento)

### Formatação de exibição — hoje duplicada
- `brl` (filtro Jinja) em `app/__init__.py:90` — **fonte a manter/consolidar**.
- `_fmt_brl` em `app/gastos/routes.py:43`, `app/orcamento/routes.py:57`, `app/orcamento/pdf.py:33`;
  `br_money` em `app/tools/routes.py:7`. → consolidar no util.
- **Padrão americano leaking** em `app/templates/event_detail.html:1314` e `:1343`
  (`"{:,.2f}".format(...)`). → trocar por `| brl`.

### Parsers de entrada — hoje duplicados
- Já tratam BR (mask-safe): `_parse_brl_dec` (calendar:411), `_pf` (calendar:599),
  `_parse_brl` (gastos:31), `_parse_brl_or_int` (calendar:1990), `_parse_num` (orcamento).
- **Quebram com máscara** (parse cru `int`/`isdigit`/`float`):
  - `_handle_add_contract` → `int(amount_raw)` (calendar:576).
  - `_handle_add_payment` → `int(amount_raw)` (calendar:718).
  - `add_salary` → `salary_raw.isdigit()` (admin:209).
  - `_process_quote` → `float(request.form.get("acrescimo_valor"))` (orcamento:130).
  - fluxo criar-evento-com-dados (calendar:1835-1837) — confirmar parse.

### Campos de entrada — hoje inconsistentes
- Já mascaráveis (têm `inputmode="decimal"` e/ou classe `brl-input`): cachê, viagem, sale_value.
- **Crus** (`type="number"` placeholder `0`): contract_amount, payment_amount (event_detail),
  cache_value em alguns blocos (event_detail:479, :621), salário (admin), acréscimo (orçamento),
  campos de orçamento, transporte (tools).
- ⚠️ **Não mascarar campos de PORCENTAGEM** (`commission_rate`, `default_commission_rate`): são taxa
  (ex.: 2,5%), não dinheiro. Ficam fora desta feature.

### Frontend
- A classe `brl-input` é usada em alguns inputs, mas **não há JS de máscara** (nenhum match em
  `app/static`). Precisa ser criada.

## Design Detalhado

### 1. Fonte única no backend — `app/utils/money.py`
```text
format_brl(value, *, prefix=False) -> str   # 1500.5 → "1.500,50" (ou "R$ 1.500,50")
parse_brl(text) -> Decimal | None           # "R$ 1.500,50"/"1.500,50"/"1500.50" → Decimal; None se vazio/inválido
parse_brl_int(text) -> int | None           # idem, arredonda p/ inteiro (contratos/pagamentos)
```
- Tolerante: aceita já-formatado BR, número cru, e (defensivo) americano por heurística simples.
- `app/__init__.py`: o filtro `brl` passa a chamar `format_brl` (mantém o nome `brl`).
- Substituir `_fmt_brl`/`br_money` por import de `format_brl`; substituir os parsers locais por
  `parse_brl`/`parse_brl_int`. Remover as cópias.

### 2. Helper único no frontend — `app/static/js/money-mask.js`
- Auto-init em `DOMContentLoaded`: para todo `input.brl-input`, aplica máscara calculadora.
- Funções `formatBRL(digits)` e o handler de `input` (mantém só dígitos, divide por 100, agrupa
  milhar com `.`, decimal com `,`). Cobre paste e backspace.
- Incluir `<script src=".../money-mask.js" defer>` no `base.html` (global, uma vez).
- O backend já normaliza via `parse_brl`, então não é preciso "desmascarar" no submit; ainda assim
  garantir que todo campo de valor tenha a classe `brl-input`.

### 3. Aplicar nas telas
- Trocar `type="number"` de campos de **dinheiro** por `type="text" inputmode="decimal"
  class="brl-input"` e exibir valor inicial via `| brl`.
- Corrigir as 2 exibições americanas em `event_detail.html`.
- Revisar parses quebráveis (contrato, pagamento, salário, acréscimo orçamento) → usar
  `parse_brl`/`parse_brl_int`.

### 4. Verificação (app real)
- Digitar em cada tipo de campo → vê formatação calculadora; salva → valor numérico correto.
- Exibição: evento, financeiro, comissões, pagamentos, gastos, orçamento, usuários — todos BR.
- Erro de validação preserva valor formatado.
- Campo de porcentagem (comissão) **não** recebe máscara de dinheiro.

## Project Structure
```text
app/utils/money.py            # NOVO — fonte única (format_brl, parse_brl, parse_brl_int)
app/utils/__init__.py         # garantir pacote
app/__init__.py               # filtro brl → format_brl
app/static/js/money-mask.js   # NOVO — máscara calculadora p/ .brl-input
app/templates/base.html       # incluir money-mask.js
app/gastos/routes.py          # usar util; remover _fmt_brl/_parse_brl locais
app/orcamento/routes.py       # usar util; remover _fmt_brl; parse acréscimo
app/orcamento/pdf.py          # usar util; remover _fmt_brl
app/tools/routes.py           # usar util; remover br_money
app/calendar/routes.py        # parsers → util (contrato/pagamento int); remover cópias
app/admin/routes.py           # salário parse → util
app/templates/*.html          # inputs de dinheiro → .brl-input + | brl; corrigir 2 spots US
```

## Fora de escopo
- Campos de porcentagem/taxa (comissão) — não são dinheiro.
- Mudança de banco / migration.
- Refactor maior das rotas além do necessário para o parse correto.
