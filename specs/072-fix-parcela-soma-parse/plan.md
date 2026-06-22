# Implementation Plan: Corrigir soma das parcelas (072)

**Branch**: `072-fix-parcela-soma-parse` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

## Summary

A soma das parcelas (e das notas) era calculada na carga da página antes de `money-mask.js` (carregado
com `defer`) executar; sem `window.MoneyMask`, caía em `parseFloat("9.400,00") = 9.4`. Correção:
calcular a soma com uma leitura **BR-segura e independente da ordem de carga** — sempre extrair os
dígitos e dividir por 100 (igual à máscara calculadora), e formatar a soma em pt-BR. **Sem backend,
sem migration.**

## Technical Context

**Language/Version**: Jinja2 + JS vanilla (`app/templates/event_detail.html`).

**Primary Dependencies**: nenhuma. Remove a dependência da ordem de carga do `money-mask.js` nesse
cálculo.

**Storage**: N/A.

**Testing**: render de `event_detail` contra `manto_local` para um evento com parcelas em milhar;
conferir no HTML/JS a leitura BR-segura. Checagem lógica do parser (9.400,00 → 9400; soma 18.800,00).

**Constraints**: manter exibição em pt-BR; aviso de divergência só quando real; pt-BR; não quebrar a
máscara de digitação (que segue por `money-mask.js`).

**Scale/Scope**: `app/templates/event_detail.html` — `recompParcelas` e `recompNotas` passam a usar
helpers locais `_brlSum`/`_brlSumFmt` (sem `window.MoneyMask ? … : parseFloat…`).

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Mesma regra da máscara (dígitos→centavos), agora local e
  estável.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Máscara de digitação intacta; só o cálculo da soma muda.
- **VII. Valores BR (NÃO-NEGOCIÁVEL)**: ✅ Leitura e formatação em pt-BR.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/templates/event_detail.html
  - _brlSum(inp): dígitos → /100 (BR-safe, independente do MoneyMask)
  - _brlSumFmt(n): formata em pt-BR
  - recompParcelas(): usa _brlSum/_brlSumFmt
  - recompNotas():    usa _brlSum/_brlSumFmt
```

**Structure Decision**: Correção cirúrgica de cálculo no template. Sem migration.

## Complexity Tracking

> Sem violações.
