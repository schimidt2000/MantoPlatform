# Contrato — Impersonação de papel via API (`/api/auth/impersonate`)

Segue as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md`
(cookie de sessão HttpOnly, `credentials: "include"`, erros via `json_error`).

## POST /api/auth/impersonate

Ativa a simulação de papel ("Ver como") para o SUPERADMIN real autenticado.

**Request**: `{"role": "CASTING"}` — papel ∈ `IMPERSONABLE_ROLES`
(CASTING, FIGURINO, COMERCIAL, FINANCEIRO, ENSAIO; case-insensitive no input,
normalizado para maiúsculas).

**Responses**:
- `200` — corpo = `AuthUser` atualizado (`impersonating` preenchido,
  `is_superadmin: false`, `is_real_superadmin: true`).
- `400` — papel ausente ou fora da lista: `{"error": "Papel inválido para simulação"}`.
- `401` — sem sessão (padrão `api_login_required`).
- `403` — usuário autenticado não é SUPERADMIN real:
  `{"error": "Apenas administradores podem simular papéis"}`.

**Efeito colateral**: `session["impersonate_role"] = role` — todos os endpoints da API
passam a responder sob o papel simulado imediatamente (mesma semântica do Jinja).

## DELETE /api/auth/impersonate

Limpa a simulação e volta ao papel real.

**Responses**:
- `200` — corpo = `AuthUser` atualizado (`impersonating: null`). Idempotente: limpar sem
  simulação ativa também responde `200`.
- `401` — sem sessão.
- `403` — não-SUPERADMIN real (paridade com o guard do POST).

## GET /api/auth/me (alterado — campos aditivos)

Ganha `is_real_superadmin: boolean` e `is_educamanto_responsavel: boolean` (ver
`data-model.md`). Nenhum campo existente muda de nome/semântica — compatível com os
consumidores atuais (`useAuth.ts`, `RequireAuth`).

## Frontend

- `useImpersonate()` / `useImpersonateReset()` em `lib/useAuth.ts`: mutations que, no
  sucesso, fazem `queryClient.setQueryData(ME_KEY, user)` + `queryClient.invalidateQueries()`
  (invalidação global — qualquer dado sensível a RBAC refaz o fetch sob a nova sessão).
- Pills "Ver como" na sidebar mostram estado pending (botão desabilitado/spinner)
  enquanto a mutation roda — nenhum botão morto (Princípio V).
