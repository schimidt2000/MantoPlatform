# Tasks: Orçamento — dropdown ao adicionar + consistência + revisão

**Input**: `specs/019-orcamento-dropdown-revisao/`
**Tests**: render + verificação lógica/manual.

## Phase 1: Dropdown ao adicionar
- [ ] T001 [app/templates/orcamento/index.html](../../app/templates/orcamento/index.html): trocar os
      botões "+ Ator/Cantor" e "+ Especial" por dois `<select>` (subtipos / lista de especiais),
      com `onchange="addFromDropdown(...)"`.
- [ ] T002 [app/static/js/orcamento.js](../../app/static/js/orcamento.js): `addPerformer(type,
      choice)` (choice opcional) + `addFromDropdown(type, sel)` (adiciona e reseta o select).

## Phase 2: Consistência do cantor
- [ ] T003 [app/static/js/orcamento.js](../../app/static/js/orcamento.js) `buildCard`: Show/Maquiagem
      sem "(+R$100)/(+R$20)"; remover a variável morta `fantasia`. Sem tocar no cálculo.

## Phase 3: Falha silenciosa
- [ ] T004 [app/orcamento/settings.py](../../app/orcamento/settings.py) `load()`: trocar
      `except Exception: pass` por log (`logging.exception`), mantendo o fallback p/ DEFAULTS.

## Phase 4: Revisão + verificação
- [ ] T005 Escrever [REVIEW.md](./REVIEW.md) com os pontos estruturais e recomendações.
- [ ] T006 ruff nos .py; render do index (200) com os selects; sanidade de cálculo (cenário
      conhecido inalterado); conferência manual dos dropdowns e do cantor.

## Dependencies
- T001→T002. T003, T004 independentes. T005 a qualquer momento. T006 ao fim.

## Notes
- Cálculo de preços inalterado. Refactor estrutural deferido (REVIEW.md).
