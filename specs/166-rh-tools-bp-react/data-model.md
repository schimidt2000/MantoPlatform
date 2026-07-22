# Data Model: RH em React + destino do blueprint órfão `tools_bp` (166)

Nenhuma tabela/campo novo. RH não tem modelo próprio — usa `User.has_permission(code)` já
existente. `tools_bp` (removido nesta fatia) também não tinha modelo próprio.

## Valores computados

- `can_view_rh` = `current_user.has_permission("rh.view")` — mesma regra de hoje
  (`require_permission`), gate do endpoint.
- `can_manage_users` = `current_user.has_permission("user.manage")` — mesmo campo passado ao
  template `rh_dashboard.html` hoje, reaproveitado sem mudança na serialização JSON.
