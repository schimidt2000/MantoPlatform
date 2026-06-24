# Implementation Plan: Correções da calculadora EducaManto (079)

**Branch**: `079-educamanto-calc-fixes` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

## Summary

Três correções na calculadora client-side do EducaManto: (1) tempo real — remover a chamada a
`_brlSum` (inexistente nesta tela, causava ReferenceError e travava `calcular()`); (2) "Pessoas no
transporte" = headcount do "Catering apresentação" (somente leitura, cresce com ensemble); (3)
acréscimo só soma no sem NF e o com NF é calculado sobre (original + acréscimo). **Só template, sem
backend/migration.**

## Technical Context

**Language/Version**: Jinja2 + JS vanilla (`app/templates/educamanto/index.html`).

**Storage**: N/A.

**Testing**: contra **`manto_local`** — página renderiza; `_brlSum` não é mais chamado; réplica do
`valoresPacote` confirma sem/com NF (com = (orig+acr)/0,84) e pessoas = catering apresentação.

**Constraints**: paridade tela/PDF; transporte segue plano; pt-BR.

**Scale/Scope**: `app/templates/educamanto/index.html` (acrescimoValor local; cateringApresentacaoQty/
syncPessoasTransporte; valoresPacote com acréscimo no gross-up; calcular/gerar; t-pessoas readonly).

## Constitution Check

- **I. Reutilizar**: ✅ Reusa o motor existente; helpers locais pequenos.
- **IV. Não quebrar**: ✅ Corrige bug; transporte/decimais preservados; verificado em `manto_local`.
- **VII. Valores BR**: ✅ Leitura BR-segura local do acréscimo.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/templates/educamanto/index.html
  - acrescimoValor(): parse local (dígitos→centavos), sem _brlSum  → corrige tempo real
  - cateringApresentacaoQty(E) + syncPessoasTransporte(E): pessoas = catering apresentação
  - valoresPacote(p,d1,d2,E,acrescimo): acréscimo no sem; com = (orig+acr)/0,84
  - calcular()/gerarOrcamento(): usam acréscimo; transporte plano; t-pessoas readonly/auto
```

**Structure Decision**: Correções pontuais na calculadora. Sem migration.

## Complexity Tracking

> Sem violações.
