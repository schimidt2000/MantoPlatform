# Implementation Plan: Máscara padrão para campos de valor em reais

**Branch**: `059-mascara-valores-brl` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/059-mascara-valores-brl/spec.md`

## Summary

Padronizar **todos** os campos onde o usuário digita valores em reais para usarem a mesma
máscara "calculadora" (RTL, `.` milhar, `,` centavos) que **já existe** em `money-mask.js` e
hoje cobre a maioria dos campos. O trabalho é: (1) converter os campos de R$ que ainda usam
`type="number"` nativo para `class="brl-input"`; (2) ajustar as calculadoras ao vivo (Orçamento
e desconto do evento) para lerem o valor mascarado via um novo helper `MoneyMask.parseNumber`;
(3) trocar `float()/int()` por `parse_brl`/`parse_brl_int` nas rotas que recebem esses campos.
**Sem mudança de modelo, sem migration.**

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + HTML/CSS/JS vanilla.

**Primary Dependencies**: Nenhuma nova. Reutiliza `app/static/js/money-mask.js` e `app/money.py`.

**Storage**: PostgreSQL (prod) / SQLite (dev). **Sem mudança de schema, sem migration.**

**Testing**: Verificação contra a **cópia local `manto_local` (PostgreSQL)** — nunca SQLite
vazio (regra do projeto). Roteiro em `quickstart.md`; submissão de formulários via test client.

**Target Platform**: App web (Railway), mobile-first.

**Project Type**: Web application (monolito Flask).

**Constraints**: Reusar a máscara/parsers existentes (fonte única); não quebrar as calculadoras
ao vivo; retrocompatível com valores já gravados; textos pt-BR.

**Scale/Scope**: ~5 templates (orcamento/index, orcamento/settings, orcamento/historico,
educamanto/package_form, event_create), `money-mask.js` (+ `parseNumber`), `orcamento.js`,
e ~3 rotas (educamanto, orcamento/settings, orcamento/historico).

## Constitution Check

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Usa `money-mask.js` (estende com
  `parseNumber`, não duplica) e `parse_brl`/`parse_brl_int` de `money.py`. Zero lógica de
  formatação nova.
- **II. Padrões Python**: ✅ Mudanças de parsing pequenas, com `parse_brl` tipado já existente.
- **III. Arquitetura em camadas**: ✅ Parsing na borda (rota); apresentação no template/JS.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ Calculadoras ao vivo ajustadas junto
  com a máscara; `parse_brl` aceita formato cru e mascarado (retrocompatível); verificação em
  `manto_local`. Risco mapeado: campos calc do Orçamento (ver research §3).
- **V. UI/UX consistente (pt-BR)**: ✅ É exatamente uma melhoria de consistência de UX.
- **VI. Planejar antes de codar**: ✅ Este plano + research + contracts.
- **VII. Valores monetários BR (NÃO-NEGOCIÁVEL)**: ✅ Centraliza o padrão BR em 100% dos campos
  de entrada de R$.

**Resultado**: PASS — sem violações, sem migration.

## Project Structure

### Documentation (this feature)

```text
specs/059-mascara-valores-brl/
├── plan.md  spec.md  research.md  data-model.md  quickstart.md
├── contracts/money-fields.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── static/js/
│   ├── money-mask.js          # + MoneyMask.parseNumber(valueOrInput)
│   └── orcamento.js           # parseFloat -> MoneyMask.parseNumber nos campos de R$; format ao escrever
├── templates/
│   ├── orcamento/index.html       # acrescimo_valor, cust_valor_1h|2h|4h -> brl-input
│   ├── orcamento/settings.html    # ator_*, cantor_base_* -> brl-input (markup_* NÃO)
│   ├── orcamento/historico.html   # min_val, max_val -> brl-input
│   ├── educamanto/package_form.html  # ensemble_*, item_cost_* -> brl-input (margins/qty NÃO)
│   └── event_create.html          # desc-val -> brl-input (desc-pct NÃO)
├── educamanto/routes.py       # ensemble_*/item_cost_* -> parse_brl
└── orcamento/
    ├── settings.py            # ator_*/cantor_base_* -> parse_brl/parse_brl_int
    └── routes.py              # min_val/max_val (histórico) -> parse_brl
```

**Structure Decision**: Monolito Flask existente. Sem novo blueprint, sem novo módulo, sem
migration. Estende a fonte única (`MoneyMask`) e reutiliza `parse_brl`.

## Complexity Tracking

> Sem violações de constituição. Único ponto de atenção (não-violação): as calculadoras ao vivo
> do Orçamento precisam ser ajustadas no mesmo passo da conversão dos campos — tratado como
> tarefa dedicada com verificação específica (não pode regredir o cálculo).
