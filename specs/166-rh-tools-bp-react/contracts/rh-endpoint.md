# Contrato de API — RH (166)

Segue as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md`.

## `GET /api/rh/dashboard`

- Gate: usuário autenticado com permissão `rh.view` (`current_user.has_permission("rh.view")`).
- 200: `{"can_manage_users": bool}`.
- 401: sem sessão válida.
- 403: `{"error": {"message": "Sem permissão"}}` sem a permissão `rh.view`.

## `tools_bp` (removido nesta fatia)

Sem contrato — decisão foi remover, não migrar (ver `spec.md`, Assumptions).
