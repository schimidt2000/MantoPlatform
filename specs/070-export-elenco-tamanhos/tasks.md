# Tasks: Tamanhos no Exportar Elenco (070)

**Feature**: `070-export-elenco-tamanhos` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem modelo/migration. Verificação de render contra **`manto_local`**.

---

## Fase 1 — UI do modal

- [X] T001 [US1] `app/templates/event_detail.html` (modal "Exportar elenco"): adicionar checkboxes `ee-top`, `ee-bottom`, `ee-shoe`, `ee-height` (Top / Bottom / Calçado / Altura), desmarcados por padrão, no mesmo padrão dos existentes.

## Fase 2 — Dados + geração de texto

- [X] T002 [US1] `const _ELENCO`: incluir `top` (`talent.clothing_size_top`), `bottom` (`talent.clothing_size_bottom`), `shoe` (`talent.shoe_size`), `height` (`talent.height_cm`) por talento.
- [X] T003 [US1] `generateElenco()`: ler os 4 checkboxes e adicionar ao texto os campos marcados que tiverem valor — `Top: …`, `Bottom: …`, `Calçado: …`, `Altura: …cm` — omitindo vazios por talento.

## Fase 3 — Verificação

- [X] T004 Render da página do evento contra **`manto_local`** (sem erro de template); conferir os 4 checkboxes no modal e que o texto inclui os campos marcados e omite vazios. `ruff` sem erros novos (sem mudança .py).

---

## Dependências

- T001 → T002 → T003 → T004.

## MVP

T001–T003 entregam a feature; T004 valida.
