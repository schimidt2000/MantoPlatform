# Implementation Plan: Corrigir acréscimos ausentes no orçamento final

**Branch**: `103-fix-acrescimo-orcamento-final` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/103-fix-acrescimo-orcamento-final/spec.md`

## Summary

Correção de defeito: os campos do editor de acréscimos da **calculadora** (`orcamento.js`,
`orcAcrescimoRowHtml`) têm apenas **classes CSS** (`acr-tipo`, `acr-desc`, `acr-value`, `acr-unit`) e
**não têm `name`**. Por isso, ao submeter o formulário, o navegador não envia esses campos e o servidor
(`_process_quote`) lê listas vazias em `acrescimo_tipo[]`/`acrescimo_value[]`/`acrescimo_is_percent[]`/
`acrescimo_descricao[]` — o acréscimo entra na prévia (lida por classe no cliente) mas **não** na
mensagem/PDF (calculados no servidor). A correção é **adicionar os `name`** esperados aos campos.

## Technical Context

**Language/Version**: JavaScript (template string em `orcamento.js`). Sem Python novo.

**Primary Dependencies**: Nenhuma nova.

**Storage**: N/A (sem alteração de dados). Já existe leitura no servidor e no snapshot.

**Testing**: Verificação contra `manto_local`: submeter um orçamento com acréscimo e conferir que os
totais do resultado (sessão `orcamento_quote`) incluem o acréscimo.

**Constraints**: Não alterar o cálculo nem o editor do evento (que já tem `name`). Não quebrar a prévia
(que lê por classe) nem a reabertura do histórico.

**Scale/Scope**: 1 função em `app/static/js/orcamento.js` (`orcAcrescimoRowHtml`).

## Constitution Check

- **Sem duplicação**: usa exatamente os `name` que o servidor já espera (mesmos do editor do evento). ✅
- **Não quebrar**: adicionar `name` não afeta a leitura por classe da prévia. ✅
- **Sem migração/segredos**. ✅

Resultado: PASS.

## Project Structure

```text
app/static/js/orcamento.js   # orcAcrescimoRowHtml: adicionar name="acrescimo_*[]" aos campos
```

**Structure Decision**: Correção mínima e cirúrgica no HTML da linha de acréscimo gerada por JS,
adicionando os atributos `name` (tipo, descrição, valor, unidade) que o servidor já consome.

## Implementation Approach

1. Em `orcAcrescimoRowHtml` (orcamento.js), adicionar:
   - `name="acrescimo_tipo[]"` no select de tipo,
   - `name="acrescimo_descricao[]"` no input de descrição,
   - `name="acrescimo_value[]"` no input de valor,
   - `name="acrescimo_is_percent[]"` no select de unidade (R$/%; value 0/1, como o servidor espera).
2. Verificar contra `manto_local`: gerar orçamento com acréscimo e conferir que o total do resultado
   inclui o acréscimo (bate com a prévia).

## Complexity Tracking

> Sem violações de constituição. Correção pontual de atributos de formulário.
