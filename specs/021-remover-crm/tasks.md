# Tasks: Remover o módulo de CRM

**Input**: `specs/021-remover-crm/`
**Tests**: boot + ruff + render das páginas principais + migration.

## Phase 1: Interface e blueprint
- [ ] T001 base.html: remover a seção de menu "CRM".
- [ ] T002 app/__init__.py: remover import + `register_blueprint(crm_bp)`.
- [ ] T003 apagar diretórios `app/crm/` e `app/templates/crm/`.

## Phase 2: Referências em outras áreas
- [ ] T004 financeiro/routes.py: remover import CRMDeal/CRMStage, o bloco CRM e os kwargs do render.
- [ ] T005 financeiro/dashboard.html: remover KPIs de CRM, ciclo de venda e coluna LTV.
- [ ] T006 calendar/routes.py: remover import CRMDeal + a linha de nullificação + docstring.
- [ ] T007 admin_settings.html + admin/routes.py: remover bloco/handler ClickSign.

## Phase 3: Modelos + migration
- [ ] T008 models.py: remover as 6 classes CRM.
- [ ] T009 migration à mão: drop das tabelas crm_* (filho→pai); `flask db upgrade`.

## Phase 4: Verificação
- [ ] T010 boot do app + ruff; migration aplica; test client: agenda/financeiro/vendas/admin OK,
      excluir evento OK, `/crm/` → 404.

## Dependencies
- T001–T007 antes de T008 (remover usos antes dos modelos). T008→T009. T010 ao fim.

## Notes
- Remoção irreversível (drop das tabelas). Colunas clicksign do SiteSetting ficam (inertes).
