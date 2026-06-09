# Tasks: Anotações e warning do talento

**Input**: `specs/036-talento-notas-warning/`
**Tests**: boot + ruff + migration up/down + verificação no app. Inclui a 035.

## Phase 1: Banco
- [x] T001 `app/models.py`: `Talent.notes` (Text, nullable) e `Talent.warning_level`
      (String(20), nullable).
- [x] T002 Migration `k7e8f9a0b1c2_talent_notes_warning.py` (down_revision `j6d7e8f9a0b1`):
      add `notes`, `warning_level` em `talents`. up/down.

## Phase 2: Salvar
- [x] T003 `app/talents/routes.py`: `POST /talents/<id>/notes` (acesso `_can_edit_talent`) — valida
      `warning_level` em {"", leve, moderado, grave}; salva `notes` + `warning_level`; flash; redirect.

## Phase 3: Telas
- [x] T004 `talent_detail.html`: bloco "Anotações internas e alerta" (textarea + select de nível +
      Salvar) se `can_edit`; senão somente leitura. Badge do alerta atual junto ao nome.
- [x] T005 `talents_list.html`: badge colorido ao lado do nome quando houver `warning_level`
      (leve/moderado/grave com cores distintas); sem alerta → nada.

## Phase 4: Verificação
- [x] T006 boot + `ruff check`; migration up/down. Cenários: salvar nota+alerta e reabrir (persiste);
      remover alerta (some); badge por nível na lista; acesso negado a quem não edita; portal do
      talento não exibe nota/alerta.

## Dependencies
- T001 → T002. T003. T004/T005. T006 por último.

## Notes
- Campos nullable; internos (não no portal). Reusa _can_edit_talent. Migration manual.
