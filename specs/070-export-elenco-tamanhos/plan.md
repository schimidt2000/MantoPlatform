# Implementation Plan: Tamanhos no Exportar Elenco (070)

**Branch**: `070-export-elenco-tamanhos` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

## Summary

Adicionar 4 checkboxes (Top, Bottom, Calçado, Altura) ao modal "Exportar elenco" e incluí-los no
texto gerado. Dados já existem no talento (`clothing_size_top`, `clothing_size_bottom`, `shoe_size`,
`height_cm`). **Sem modelo, sem migration, sem backend.**

## Technical Context

**Language/Version**: Jinja2 + JS vanilla (template `app/templates/event_detail.html`).

**Primary Dependencies**: nenhuma. Reusa o modal e a função `generateElenco()` existentes.

**Storage**: N/A (sem mudança de dados).

**Testing**: render do template contra `manto_local` (página do evento abre sem erro Jinja); checagem
visual do modal e do texto gerado.

**Constraints**: novos campos opcionais (desmarcados por padrão); omitir campo vazio por talento;
pt-BR.

**Scale/Scope**: 1 arquivo — `app/templates/event_detail.html` (modal + array `_ELENCO` + função
`generateElenco`).

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Reusa o modal/JS existentes; só adiciona campos.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Campos opcionais; sem alterar o texto padrão.
- Demais princípios: ✅ (mudança mínima de UI).

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/templates/event_detail.html
  - modal "Exportar elenco": + checkboxes Top/Bottom/Calçado/Altura
  - const _ELENCO: + top/bottom/shoe/height por talento
  - generateElenco(): + montagem dos novos campos (omitindo vazios)
```

**Structure Decision**: Edição cirúrgica de template. Sem migration.

## Complexity Tracking

> Sem violações.
