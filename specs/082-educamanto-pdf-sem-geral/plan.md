# Implementation Plan: Remover "Geral" de "O que está incluso" (082)

**Branch**: `082-educamanto-pdf-sem-geral` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

## Summary

Remover o item "Geral" de cada plano em `LONG_DESC` (descrição longa do PDF), mantendo Iluminação,
Sonorização e Cenografia. O resumo geral segue na descrição curta (abaixo do título). **Só
`pdf.py`; sem backend/migration.**

## Technical Context

**Language/Version**: Python (reportlab) — `app/educamanto/pdf.py`.

**Testing**: contra **`manto_local`** — gerar PDF e confirmar que "Geral" não aparece em "O QUE ESTÁ
INCLUSO" e que Iluminação/Sonorização/Cenografia continuam; descrição curta inalterada. `ruff` sem
erros novos.

**Scale/Scope**: `app/educamanto/pdf.py` — remover a primeira tupla ("Geral", …) de cada lista em
`LONG_DESC`.

## Constitution Check

- **IV. Não quebrar**: ✅ Só remove um item da lista; resto inalterado.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/educamanto/pdf.py — LONG_DESC: remover ("Geral", …) de master/intermediario/economica
```

## Complexity Tracking

> Sem violações.
