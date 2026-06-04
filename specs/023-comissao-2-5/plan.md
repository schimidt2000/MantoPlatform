# Implementation Plan: Comissão padrão 2,5% + vendedor visível + taxa travada

**Branch**: `023-comissao-2-5` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

(1) Padrão de comissão 2% → **2,5%**: muda a constante de fallback e corrige o valor salvo via
**migração de dados** (vale em produção). (2) Aba comercial do evento mostra o **vendedor
responsável** ao comercial (Financeiro/Superadmin continuam editando). (3) **Taxa de comissão por
evento** vira editável **só pelo super admin**; comercial e financeiro veem travada (a vigente).
Sem nova coluna.

## Constitution Check
- **IV. Não quebrar** ✅ — eventos com taxa própria não mudam; servidor valida quem edita a taxa;
  verificação no app. Migração de dados é direcionada ao SiteSetting.
- **V. UI/UX** ✅ — vendedor visível; taxa travada com rótulo claro.
- **VI. Planejar antes de codar** ✅ — este plano; pergunta do usuário respondida.
- **Migration à mão** ✅ (autogenerate quebrado).

## Pontos a tocar

| Arquivo | Ação |
|---|---|
| `app/financeiro/routes.py` | `DEFAULT_COMMISSION = Decimal("2.5")` (fallback) |
| `migrations/versions/<nova>.py` | data: `UPDATE site_settings SET default_commission_rate=2.5 WHERE é 2.0/NULL` |
| `app/calendar/routes.py` (`_handle_update_comercial`) | edição da `commission_rate` só SUPERADMIN; seller segue Financeiro/Superadmin |
| `app/calendar/routes.py` (`event_detail`) | passar `is_superadmin` ao template |
| `app/templates/event_detail.html` | seller (editável fin/sa, leitura p/ comercial) + taxa (editável superadmin, travada p/ demais), dentro de `show_comercial` |
| `app/templates/admin_settings.html` | fallback de exibição `or 2.0` → `or 2.5` |
| `app/models.py` | comentário "default 2.0" → "2.5" (cosmético) |

## Design Detalhado

### 1. Padrão 2,5%
- `DEFAULT_COMMISSION = Decimal("2.5")` (usado quando não há valor salvo).
- Migração de dados (`h4b5c6d7e8f9`, down_revision `g3a4b5c6d7e8`):
  `UPDATE site_settings SET default_commission_rate = 2.5 WHERE default_commission_rate IS NULL OR default_commission_rate = 2.0`.
  downgrade volta para 2.0 nas mesmas condições.

### 2. Permissão de edição da taxa (`_handle_update_comercial`)
- Hoje: Financeiro/Superadmin setam `seller_id` **e** `commission_rate`.
- Mudança: separar — `seller_id` segue Financeiro/Superadmin; `commission_rate` **só SUPERADMIN**.
  (Não-superadmin não altera a taxa, mesmo que envie o campo.)

### 3. Template (event_detail, bloco comercial)
- Tirar seller+taxa de dentro de `{% if show_financeiro %}`; passar a mostrar dentro de
  `show_comercial`:
  - **Vendedor**: `show_financeiro` → `<select>` (como hoje); senão → texto
    `{{ event.seller.name or '— não definido —' }}`.
  - **Taxa**: `is_superadmin` → `<input commission_rate>` (como hoje); senão → texto travado
    `{{ event.commission_rate or default_commission }}%` + dica "(travada — só super admin)".
- `event_detail` passa `is_superadmin`.

### Verificação
- Migração: default vira 2,5 (e volta no downgrade).
- `_get_commission_rate` p/ evento sem taxa → 2.5; com taxa própria → a própria.
- Comercial vê vendedor (texto) e taxa travada; super admin edita taxa; financeiro edita vendedor
  mas não taxa (POST de taxa por não-superadmin não altera).
- Eventos com taxa própria não mudam.

### Fora de escopo
- Congelar comissão por evento (não pedido; maio deve sair a 2,5%).
