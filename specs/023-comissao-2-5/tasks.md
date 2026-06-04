# Tasks: Comissão padrão 2,5% + vendedor visível + taxa travada

**Input**: `specs/023-comissao-2-5/`
**Tests**: migration + boot + ruff + render/RBAC manual.

## Phase 1: Padrão 2,5%
- [ ] T001 financeiro/routes.py: `DEFAULT_COMMISSION = Decimal("2.5")`.
- [ ] T002 migração de dados `h4b5c6d7e8f9` (down_revision g3a4b5c6d7e8): atualiza
      `site_settings.default_commission_rate` 2.0/NULL → 2.5; `flask db upgrade`.
- [ ] T003 admin_settings.html fallback `or 2.0` → `or 2.5`; comentário do model (cosmético).

## Phase 2: Edição da taxa só super admin
- [ ] T004 calendar/routes.py `_handle_update_comercial`: separar — seller_id (Financeiro/Superadmin),
      commission_rate (SUPERADMIN apenas).
- [ ] T005 calendar/routes.py `event_detail`: passar `is_superadmin` ao template.

## Phase 3: UI da aba comercial
- [ ] T006 event_detail.html: vendedor (select p/ fin/sa; texto p/ comercial) + taxa (input p/
      superadmin; travada p/ demais) dentro de `show_comercial`.

## Phase 4: Verificação
- [ ] T007 migration up/down; boot+ruff; evento sem taxa → 2,5%; comercial vê vendedor + taxa
      travada; super admin edita taxa; financeiro edita vendedor mas não taxa.

## Dependencies
- T001/T002/T003. T004→T005→T006. T007 ao fim.

## Notes
- Migração de dados (direcionada ao SiteSetting). Eventos com taxa própria não mudam.
