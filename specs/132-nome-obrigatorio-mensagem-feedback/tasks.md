# Tasks — Nome Obrigatório na Avaliação + Mensagem Pronta ao Copiar o Link (132)

- [X] T001 `app/models.py` + migration: `ClientFeedback.client_name` (`String(200)`,
      `nullable=True`); checar colisão de revision-id antes de finalizar
- [X] T002 `app/feedback/routes.py::avaliar_submit`: valida `client_name` obrigatório
      (mesma rota de erro já usada pra nota inválida), salva no `ClientFeedback`
- [X] T003 `app/templates/feedback/public.html`: campo "Seu nome" no topo do form, antes
      das estrelas, `required`
- [X] T004 `app/templates/event_detail.html`: `buildFeedbackMsg(url)` com o texto fixo do
      FR-006; wiring do `btn-feedback-cliente` troca `copiar(data.url, bf)` por
      `copiar(buildFeedbackMsg(data.url), bf)`
- [X] T005 `app/templates/event_detail.html` (painel Feedback da Cliente) +
      `app/templates/clientes/avaliacoes.html` (lista + pontos de atenção): exibem
      `fb.client_name` (fallback pra avaliações antigas sem nome)
- [X] T006 Verificação funcional vs `manto_local`: envio sem nome rejeitado; envio com
      nome salva e aparece nas duas telas; avaliação antiga sem nome não quebra a
      renderização; texto copiado bate com o modelo, link real interpolado, token
      reaproveitado (não muda a cada clique)
- [X] T007 `ruff check` nos arquivos tocados; changelog (`docs/changelog.html`,
      republicar no link já existente); commit, merge em `main`, push
