# Tasks: Orçamento congelado (registro imutável)

**Input**: `specs/020-orcamento-congelado/`
**Tests**: render + verificação lógica/manual + migration.

## Phase 1: Dados
- [ ] T001 [app/models.py](../../app/models.py): `OrcamentoHistory.result_snapshot` (Text, nullable).
- [ ] T002 Migration à mão `f2a3b4c5d6e7` (down_revision `e0f1a2b3c4d5`): add_column; `flask db upgrade`.

## Phase 2: Congelar na geração
- [ ] T003 [app/orcamento/routes.py](../../app/orcamento/routes.py) `_process_quote`: calcular
      `markup_used` e incluir no dict da sessão; gravar `result_snapshot` no `OrcamentoHistory`.

## Phase 3: Ver congelado
- [ ] T004 [app/orcamento/routes.py](../../app/orcamento/routes.py): rota
      `GET /historico/<id>/ver` — carrega snapshot (ou `_legacy_quote` p/ antigos), seta na sessão,
      redireciona p/ `resultado`.

## Phase 4: UI do histórico
- [ ] T005 [app/static/js/orcamento.js](../../app/static/js/orcamento.js) `renderHistory`: botão
      "Ver" (link p/ /ver) + "Recalcular" (restoreFromHistory); manter "Criar evento" e "✕".
- [ ] T006 [app/templates/orcamento/historico.html](../../app/templates/orcamento/historico.html):
      link "Ver" + renomear "Reabrir" → "Recalcular (preços atuais)".

## Phase 5: Verificação
- [ ] T007 ruff; migration up/down; gerar orçamento → snapshot gravado; "Ver" mostra original;
      mudar preço (teste) → antigo mantém, recalcular muda; entry antigo (null) abre sem erro.

## Dependencies
- T001→T002→T003→T004. T005/T006 após T004. T007 ao fim.

## Notes
- Migration à mão. Totais salvos nunca recalculados. Reusa resultado.html/PDF/email via sessão.
