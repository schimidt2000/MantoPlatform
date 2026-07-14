# Tasks — Página de Clientes Organizada + Botão de Feedback Trava Após Envio (131)

- [X] T001 `app/clientes/routes.py`: rota `GET /avaliacoes` (`@require_vendas`) — filtros
      período/nota/tag/cliente, join `ClientFeedback`→`CalendarEvent`→`Client` (left join,
      evento pode não ter cliente), resumo (média/total/distribuição/pontos de atenção),
      selects populados a partir dos dados reais + tags fixas reaproveitadas de
      `app.feedback.routes`
- [X] T002 `app/templates/clientes/avaliacoes.html` (novo): chips de período/nota, selects
      de card/cliente, `.kpi-grid`, distribuição por nota, painel "Pontos de atenção",
      lista de avaliações (nota, cards, cliente com link, comentário, data), estado vazio
- [X] T003 `app/templates/clientes/list.html`: link "⭐ Ver avaliações" pra nova tela
- [X] T004 `app/templates/base.html`: item de sidebar "Avaliações" em Comercial, logo
      abaixo de "Clientes", mesmo gating
- [X] T005 `app/templates/event_detail.html`: botão `#btn-feedback-cliente` ganha o mesmo
      padrão condicional `disabled`/estilo/`title` já usado por `#btn-cobranca`, baseado
      em `client_feedbacks` (já carregado); guard no JS de wiring (`!bf.disabled`)
- [X] T006 Verificação funcional vs `manto_local`: cada filtro isolado e combinado; resumo/
      distribuição/pontos de atenção batem com o filtro aplicado; estado vazio (sem dado e
      sem resultado de filtro); permissão igual à de `/clientes/`; botão de feedback
      clicável antes do 1º envio e desabilitado depois, com explicação
- [X] T007 `ruff check` nos arquivos tocados; changelog (`docs/changelog.html`,
      republicar no link já existente); commit, merge em `main`, push
