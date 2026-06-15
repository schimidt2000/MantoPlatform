# Tasks — Painel Financeiro Mês a Mês

- [ ] **T01** Migration manual `p2e3f4a5b6c7_painel_financeiro_mensal.py` (down_revision `o1d2e3f4a5b6`): add `is_cortesia_permuta`, `tax_rate`, `fator_r_threshold`.
- [ ] **T02** Models: adicionar as 3 colunas em `CalendarEvent` e `SiteSetting`.
- [ ] **T03** `flask db upgrade` e verificar schema.
- [ ] **T04** Settings: campos taxa de imposto + corte Fator R em `admin/routes.py` e `admin_settings.html`.
- [ ] **T05** Evento: checkbox "Cortesia/Permuta" em `event_detail.html` + persistência na rota de salvar venda.
- [ ] **T06** Refatorar `financeiro/routes.py`: período (este_mes/30d/mes_anterior/custom), split realizado/projetado, `_compute_drg`, marketing, impostos, salário real/pro-rata, fator R, break-even, auditoria.
- [ ] **T07** Reescrever `financeiro/dashboard.html` em bento grid (KPIs, DRE realizado/projetado, receita por tipo + top vendedores, tendência, auditoria, tabela com badges).
- [ ] **T08** Robustez: divisão-zero-safe em todos os ratios; estados vazios.
- [ ] **T09** Verificar: `pytest`, smoke `python run.py`, cenários P1.
- [ ] **T10** Commit atômico + merge na main.
