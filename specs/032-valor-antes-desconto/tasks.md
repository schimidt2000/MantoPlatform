# Tasks: "Valor antes do desconto" no evento

**Input**: `specs/032-valor-antes-desconto/`
**Tests**: boot + ruff + migration up/down + verificação no app. Inclui 030/031.

## Phase 1: Banco
- [x] T001 `app/models.py`: `CalendarEvent.sale_value_gross = db.Column(db.Numeric(12, 2),
      nullable=True)` (valor antes do desconto).
- [x] T002 Migration manual `j6d7e8f9a0b1_sale_value_gross.py` (down_revision `i5c6d7e8f9a0`):
      adiciona coluna `sale_value_gross` em `calendar_events`. up/down.

## Phase 2: Template
- [x] T003 `event_create.html`: novo campo "Valor antes do desconto (R$) *" ao lado de "Valor de
      venda" (`name="sale_value_gross"`, `id="sale-value-gross"`, `.brl-input`), com prefill
      (orçamento → total).
- [x] T004 `event_create.html`: remover o campo "Valor no contrato (R$)" (`contract_amount`).

## Phase 3: JS
- [x] T005 `event_create.html`: `selectDuracao` também seta `sale-value-gross`; validação de submit
      inclui o novo campo (vazio/≤0 → destaque, como o valor de venda). `applyDesconto` permanece só
      no valor de venda.

## Phase 4: Servidor
- [x] T006 `app/calendar/routes.py` `create_event`: ler `sale_value_gross`, validar obrigatório (> 0)
      → "Informe o valor antes do desconto.", e persistir em `CalendarEvent(...)`.

## Phase 5: Verificação
- [x] T007 boot + `ruff check`; migration up/down. Cenários: (a) campo aparece ao lado do valor de
      venda; "Valor no contrato" sumiu; (b) vazio/zero bloqueia (cliente + servidor), dados
      preservados; (c) de orçamento prefilled + troca de duração acompanha + desconto reduz só venda;
      (d) criar salva `sale_value_gross` no banco; (e) tudo certo → 302.

## Dependencies
- T001 → T002. T003/T004/T005 (template). T006 (servidor). T007 por último.

## Notes
- Reusa máscara/parse_brl e validação por campo (031). Coluna nullable (eventos antigos intactos).
  Relatório de desconto é follow-up.
