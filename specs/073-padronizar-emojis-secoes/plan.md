# Implementation Plan: Padronizar emojis das seções da home (073)

**Branch**: `073-padronizar-emojis-secoes` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

## Summary

Adicionar emoji aos três cabeçalhos de seção da home que ainda não têm — Casting (👥), Ensaio (🎭),
Figurino (👗) — alinhando ao padrão de Nota Fiscal (🧾) e Comercial (💰). **Só template.**

## Technical Context

**Language/Version**: Jinja2 (`app/templates/home.html`).

**Primary Dependencies**: nenhuma.

**Storage**: N/A.

**Testing**: render da home contra `manto_local`; conferir os emojis nos rótulos.

**Constraints**: não alterar contadores/badges nem comportamento; pt-BR.

**Scale/Scope**: `app/templates/home.html` — 3 rótulos de `span.badge` (Casting, Ensaio, Figurino).

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Mesmo padrão dos rótulos já existentes.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Só o texto do rótulo muda.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/templates/home.html
  - badge "Casting"  → "👥 Casting"
  - badge "Ensaio"   → "🎭 Ensaio"
  - badge "Figurino" → "👗 Figurino"
```

**Structure Decision**: Edição de rótulos no template. Sem migration.

## Complexity Tracking

> Sem violações.
