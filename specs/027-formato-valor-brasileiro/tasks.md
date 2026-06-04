# Tasks: Padronizar valores monetários no padrão brasileiro

**Input**: `specs/027-formato-valor-brasileiro/`
**Tests**: boot + ruff + verificação no app real (digitação + exibição). Sem migration.

## Phase 1: Fonte única (backend)
- [x] T001 `app/money.py` (novo, sem deps p/ evitar import circular): `format_brl(value, prefix=False)`,
      `parse_brl(text) -> Decimal|None`, `parse_brl_int(text) -> int|None`. Tolerante a BR/cru/americano.
- [x] T002 `app/__init__.py`: filtro `brl` passa a usar `format_brl`.
- [x] T003 Consolidar formatadores: `_fmt_brl` (gastos, orcamento/routes, orcamento/pdf) e
      `br_money` (tools) agora delegam a `format_brl`.

## Phase 2: Máscara única (frontend)
- [x] T004 `app/static/js/money-mask.js` (novo): máscara calculadora p/ `input.brl-input`
      (auto-init em DOMContentLoaded; `window.MoneyMask.init` p/ linhas dinâmicas).
- [x] T005 `app/templates/base.html`: incluir `money-mask.js` (defer, global).
- [x] T004b Remover máscaras inline duplicadas em `event_create.html` e `event_detail.html`
      (mantidos só os helpers de cálculo parseBRL/formatBRL/fmtBRL).

## Phase 3: Aplicar exibição
- [x] T006 `event_detail.html`: trocados os 2 `"{:,.2f}".format(...)` (US) por `| brl`.
- [x] T007 Exibições crus → `| brl`: `admin_users` (salário), `admin_user_edit` (histórico salário),
      `event_detail` (sugestões de viagem). Financeiro/comissões/pagamentos/gastos/vendas já usavam `brl`.

## Phase 4: Aplicar entrada + parse no servidor
- [x] T008 Inputs de dinheiro `type="number"` → `.brl-input`: event_detail (contrato, pagamento,
      cachê x2), event_create (contrato, pagamentos x2), admin salário. % de comissão NÃO tocado.
- [x] T009 Parses → util: `_handle_add_contract`/`_handle_add_payment` (`parse_brl_int`),
      criar-evento (`parse_brl`/`parse_brl_int`), `add_salary` (`parse_brl_int`),
      orçamento acréscimo (`_parse_num`, BR-aware). 5 parsers locais duplicados removidos.

## Phase 5: Verificação
- [x] T010 boot OK; ruff sem novas pendências; templates compilam; static servido; máscara validada
      (400000→4.000,00; 5→0,05; roundtrip ok); `parse_brl` cobre BR/cru/US.

## Deferido (calculadoras acopladas a JS `parseFloat` — risco de quebrar; Princípio IV + freeze 020)
- Orçamento `index.html` (cust_valor/cust_mult/acrescimo) — `orcamento.js` lê/escreve via `parseFloat`.
- Orçamento `settings.html` (matriz de preços) e Educamanto `package_form.html` (grade de custos).
  Continuam `type="number"` (sem vazar formato americano). Migrar exige reescrever o parse desses JS.

## Dependencies
- T001 → T002/T003. T004 → T005 → T008. T001 → T009. T006/T007 independentes após T002.
- T010 por último.

## Notes
- Estilo calculadora (decisão do usuário). Backend normaliza via `parse_brl` (não precisa desmascarar
  no submit), mas todo input de dinheiro deve ter `.brl-input`.
- Porcentagens (comissão) ficam fora — não são dinheiro.
- Sem migration; FR-010/SC-003: não alterar dado gravado.
