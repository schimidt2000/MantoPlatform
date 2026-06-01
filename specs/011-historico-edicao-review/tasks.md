# Tasks: Indicar edição e ver histórico de uma avaliação

**Input**: `specs/011-historico-edicao-review/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Fundação (model + migration)

- [ ] T001 Em [app/models.py](../../app/models.py): `EventRating.edited_at` (DateTime, null) +
      `edit_count` (Integer, default 0); nova `EventRatingVersion` (rating_id FK, snapshot Text,
      replaced_at DateTime) + relationship `versions`.
- [ ] T002 Migration à mão `rating_versions` (down_revision = `c8d9e0f1a2b3`): add_column x2 +
      create_table; `flask db upgrade`.

## Phase 2: Captura de versões (P1)

- [ ] T003 Helper `_snapshot_rating(rating) -> dict` em
      [app/talent_portal/routes.py](../../app/talent_portal/routes.py).
- [ ] T004 `submit_rating` (POST): se `existing` e conteúdo mudou, gravar EventRatingVersion do
      estado anterior, `edit_count += 1`, `edited_at = now`.
- [ ] T005 `rate_event_detail` (POST): snapshot antes de recriar sub-avaliações de avaliação
      existente; registrar versão só se o conteúdo diferir do último snapshot (evita duplicar
      versão entre as etapas geral+detalhe).

## Phase 3: Exibição staff (P1)

- [ ] T006 [app/talents/routes.py](../../app/talents/routes.py): `given_ratings` carrega
      edited_at/edit_count/versions (passar ao template).
- [ ] T007 [app/templates/talent_detail.html](../../app/templates/talent_detail.html): selo
      "editada · {data}" quando edit_count>0; expansor "ver histórico (N)" listando versões
      (nota, comentário, sub-avaliações, data).

## Phase 4: Polish

- [ ] T008 `ruff check` nos .py tocados.
- [ ] T009 Verificação no app real: editar 2x → 2 versões + selo; edição sem mudança → sem nova
      versão; nunca editada → sem selo/histórico; migration aplica.

## Dependencies
- T001 → T002 → T003 → T004/T005. T006 → T007.

## Notes
- Snapshot via JSON reaproveita dados existentes (sem tabelas espelho por categoria).
- Migration à mão (autogenerate quebrado). Registro vale daqui pra frente.
