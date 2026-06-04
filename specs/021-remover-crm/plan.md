# Implementation Plan: Remover o módulo de CRM

**Branch**: `021-remover-crm` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Remoção completa do CRM: menu, blueprint/rotas, templates, modelos, bloco no painel financeiro,
referência na exclusão de evento e a integração ClickSign (exclusiva do CRM). Drop das tabelas
`crm_*` via migration à mão (irreversível, decisão do usuário). `/vendas` (Financeiro) permanece.

## Constitution Check
- **I. Reutilizar / IV. Não quebrar** ✅ — remoção isolada; demais áreas verificadas no app (boot +
  páginas principais respondem). Migration à mão (autogenerate quebrado).
- **V. UI/UX** ✅ — menu sem itens órfãos; painel financeiro segue íntegro.
- **VI. Planejar antes de codar** ✅ — este plano; footprint mapeado.

## Pontos a tocar (mapeados)

| Arquivo | Ação |
|---|---|
| `app/templates/base.html` | remover a seção de menu "CRM" (Pipeline/Organizações/Métricas) |
| `app/__init__.py` | remover import e `register_blueprint(crm_bp)` |
| `app/crm/` (dir) | apagar (routes.py, __init__.py, clicksign_service.py) |
| `app/templates/crm/` (dir) | apagar (8 templates) |
| `app/financeiro/routes.py` | tirar import CRMDeal/CRMStage; remover bloco "CRM — Pipeline e Conversão" + kwargs do render |
| `app/templates/financeiro/dashboard.html` | remover 2 KPIs de CRM, o KPI de ciclo de venda e a coluna "Maiores Clientes (LTV)" |
| `app/calendar/routes.py` | tirar import CRMDeal; remover a linha que nullifica `CRMDeal.calendar_event_id` + menção no docstring |
| `app/templates/admin_settings.html` | remover bloco ClickSign |
| `app/admin/routes.py` | remover handler de `clicksign_token`/`clicksign_sandbox` |
| `app/models.py` | remover classes CRMStage/Organization/Contact/Deal/Note/Reminder (728–902) |
| `migrations/versions/<nova>.py` | drop das tabelas `crm_reminders, crm_notes, crm_deals, crm_contacts, crm_organizations, crm_stages` (filho→pai) |

> ClickSign: as colunas `SiteSetting.clicksign_token/sandbox` **permanecem** no banco (evita migration
> extra de drop de coluna); só a UI/uso some. São inertes.

## Migration
- `g3a4b5c6d7e8` (down_revision `f2a3b4c5d6e7`): `op.drop_table` em ordem filho→pai. `downgrade()`
  documentado como no-op (remoção é irreversível por decisão de produto).

## Verificação
- `python -c "import app"` / boot do app sem erro (modelos/blueprint removidos).
- ruff nos .py tocados (sem novos erros).
- Migration `upgrade` aplica (tabelas crm_* somem); chain íntegra.
- Test client: `/agenda`, `/financeiro/`, `/financeiro/vendas/`, `/admin/configuracoes` (settings),
  excluir evento — todos OK; `/crm/` → 404.

## Fora de escopo
- Unir Usuários + Funcionários (próxima feature).
- Drop das colunas clicksign do SiteSetting (inertes; ficam).
