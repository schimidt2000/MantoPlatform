# Tasks: Busca na Planilha de Pagamentos

**Input**: `specs/045-busca-pagamentos/`
**Tests**: boot + ruff + test client (HTML/JS presentes). Sem migration — mudança só no template
`app/templates/financeiro/pagamentos.html` (busca client-side integrada ao applyFilter da 044).

- [x] T001 Campo de busca acima da tabela (ícone, placeholder, botão limpar ✕) + resumo
      "N itens · R$ X" quando há busca ativa.
- [x] T002 JS: normalização (caixa/acentos), índice de texto por linha (textContent +
      valor sem milhar), `applyView()` = filtro de situação E busca; select-all/bulk continuam
      operando só sobre visíveis; desmarca ocultas; estado vazio com "limpar busca".
- [x] T003 Verificação: ruff + boot + test client (elementos presentes no HTML; lógica única de
      visibilidade); commit.

## Dependencies
- T001 → T002 → T003.
