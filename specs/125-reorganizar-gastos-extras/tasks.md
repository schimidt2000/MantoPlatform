# Tasks — Reorganizar e Filtrar Gastos Extras (125)

- [X] T001 `app/templates/gastos/index.html`: cabeçalho — `page_subtitle` com contagem
      (padrão `clientes/list.html`) + `page_actions` com botão "+ Novo gasto"
- [X] T002 `app/templates/gastos/index.html`: painel "Registrar novo gasto" vira
      recolhível (`id="novo-gasto-panel"`, oculto por padrão, aberto se houver flash de
      erro), toggle via botão do cabeçalho — campos/validação do formulário inalterados
- [X] T003 `app/templates/gastos/index.html`: barra de filtro por situação — `kpi-grid`
      com 4 cartões clicáveis (Todos/Pendentes/Aprovados/Rejeitados), contagem visível a
      todos, soma R$ só para `is_superadmin`; badges de status/desembolso trocados para
      `.badge-green`/`.badge-amber`/`.badge-red`/`.badge-blue`/`.badge-gray`. Classes
      `.kpi-filter`/`.kpi-active` promovidas de `financeiro/pagamentos.html` (onde eram
      locais) para `app/static/style.css` — fonte única (Princípio I), reaproveitadas
      pelas duas telas.
- [X] T004 `app/templates/gastos/index.html`: `<tr class="gasto-row" data-status="...">`
      + `data-noindex` nas colunas Nota Fiscal/Ações; JS de busca (`buildGastoRowIndex`/
      `normTxtGasto`) e filtro (`applyGastoView`/`applyGastoFilter`, `localStorage`
      `gastos_filtro`) adaptado de `financeiro/pagamentos.html`; linha "sem resultado
      para o filtro" distinta do estado vazio "nenhum gasto registrado"
- [X] T005 Verificação vs manto_local (20/20 automatizados): render sem quebrar para
      superadmin e usuário comum; contagem no cabeçalho bate com o banco; painel de
      cadastro começa fechado e reabre sozinho quando há flash de erro (testado
      explicitamente simulando um POST inválido); formulário com todos os campos
      originais intactos; badges sem cor inline antiga; usuário comum não vê coluna
      Autor nem rótulo de superadmin; `/financeiro/pagamentos` continua íntegro após a
      extração de CSS para `style.css`. Ruff comparado contra worktree do `main`: 93/93,
      zero novo (mudança é template/CSS). **Interação de clique/busca no navegador não
      verificada visualmente neste ambiente** (sem ferramenta de automação de browser) —
      lógica JS conferida por leitura cuidadosa, adaptada 1:1 do padrão já em produção em
      `financeiro/pagamentos.html`.
- [ ] T006 Commit, merge em main, push
