# Contratos — 332 Avisos no celular

Todos os endpoints exigem `api_login_required` e o gate `pode_conversas()` (COMERCIAL/SUPERADMIN, papel real) no
início da view, com o erro no envelope de `json_error`.

## `GET /api/push/chave`

`{"ligado": bool, "chave_publica": str | null}`. Sem as chaves VAPID: `ligado: false`, chave `null`.

## `POST /api/push/aparelhos`

- **Corpo** (o `PushSubscription.toJSON()` do navegador): `{"endpoint": "https://…", "keys": {"p256dh": "…", "auth":
  "…"}}`.
- **201** `{"ok": true}`: grava ou atualiza o aparelho pelo `endpoint` (UNIQUE), da pessoa logada.
- **Recusas**:
  - endpoint que não é https, ou chaves ausentes → 422 `fields.aparelho` "Não foi possível registrar este aparelho.
    Tente novamente.";
  - desligado → 503 `codigo: "nao_configurado"` "Os avisos no celular ainda não foram configurados.".

## `DELETE /api/push/aparelhos`

Corpo `{"endpoint": "…"}` → 204. Só apaga o aparelho da própria pessoa; o endpoint de outra pessoa é ignorado.

## O aviso (corpo cifrado que o service worker recebe)

`{"titulo": "…", "corpo": "…", "link": "/conversas?c=12", "tag": "conversa-12"}`.
