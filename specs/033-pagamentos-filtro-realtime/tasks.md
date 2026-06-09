# Tasks: Filtro por card + troca de situação em tempo real (Pagamentos)

**Input**: `specs/033-pagamentos-filtro-realtime/`
**Tests**: boot + ruff + verificação no app real. Sem migration.

## Phase 1: Backend (resposta em tempo real)
- [x] T001 `app/financeiro/routes.py` `set_payment_status`: detectar AJAX
      (`X-Requested-With` ou `ajax=1`); manter toda a lógica atual e, se AJAX, retornar
      `jsonify({"ok": True, "status": <efetivo>})` (commission → "pago"/"nao_pago"); inválido →
      `jsonify({"ok": False}), 400`. Não-AJAX continua `redirect` (reserva).

## Phase 2: Template (dados + cards)
- [x] T002 `pagamentos.html`: em cada `<tr>` adicionar `data-status`, `data-future`, `data-amount`.
- [x] T003 `pagamentos.html`: tornar os 5 KPIs clicáveis (`data-filter` = all/pago/no_banco/pendente/
      futuro, `role=button`, cursor, estilo "ativo") + linha de estado vazio do filtro.

## Phase 3: JS (filtro + tempo real)
- [x] T004 `pagamentos.html` (extra_scripts): `applyFilter(f)` (mostra/oculta por status/future, card
      ativo, toggle, persiste em localStorage e reaplica no load).
- [x] T005 `pagamentos.html`: trocar `form.submit()` do select por `fetch` AJAX; em sucesso atualizar
      linha (status/classes/select) + recomputar totais + reaplicar filtro; em falha reverter + avisar.
- [x] T006 `pagamentos.html`: `recomputeTotals()` somando `data-amount` por categoria (regra igual à do
      servidor), formatando em pt-BR.

## Phase 4: Verificação
- [x] T007 boot + `ruff check`. Cenários no app: (a) cada card filtra; toggle/"Total" limpa;
      (b) trocar situação sem reload + linha/totais atualizam + filtro mantido; (c) item sai do filtro
      ao deixar de casar; (d) falha de rede reverte + avisa; (e) troca de mês / bulk reaplica filtro;
      (f) `set-status` sem AJAX (reserva) ainda redireciona e salva; bulk/export intactos.

## Dependencies
- T001 independente. T002 → T003 → T004/T005/T006. T007 por último.

## Notes
- Reusa `set_payment_status` (acrescenta JSON), totais do servidor como ponto de partida e formato BR.
  Caminho de formulário mantido como reserva. Sem migration.
