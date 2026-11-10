# Contrato — serviço `manto-avisos`

Base: `https://manto-avisos.onrender.com` (constante `AVISOS_BASE_URL`). Sem sessão, sem CORS.

## `POST /api/webhooks/infinitepay/<token>`

Quem chama: a InfinitePay, no endereço que vai no campo `webhook_url` de cada link de pagamento.

**Entrada**: corpo JSON da operadora (o receptor não interpreta: guarda como veio).

| Condição | Resposta | Efeito |
|---|---|---|
| corpo > 65 536 bytes (com ou sem `Content-Length`) | `413` `{"success": false, "message": "Payload too large"}` | nada |
| mais de 60 chamadas no último minuto do mesmo cliente | `429` `{"success": false, "message": "Too many requests"}` | nada |
| segredo ≠ atual e ≠ anterior válido | `404` `{"success": false, "message": "Not found"}` | linha `secret_ok=false` com os primeiros 2 KB, até 120/h |
| segredo certo, gravou | `200` `{"success": true, "message": null}` | linha `secret_ok=true` com o corpo inteiro |
| segredo certo, banco fora / erro ao gravar | `400` `{"success": false, "message": "Try again"}` | nada (a operadora reenvia) |
| banco fora ao conferir o segredo | `400` | nada |
| qualquer exceção inesperada | `400` `{"success": false, "message": "Try again"}` | nada; log só com o tipo — subir ao gunicorn logaria a URI com o segredo e responderia 500, que a operadora não reenvia |

Segredo válido = `site_settings.infinitepay_webhook_token` (id 1), ou
`infinitepay_webhook_token_anterior` enquanto `infinitepay_webhook_token_anterior_ate` > agora em São
Paulo; comparação em tempo constante; vazio nunca vale.

Log: uma linha por chamada **sem a URL** — `[avisos] <código> id=<linha|-> bytes=<n> ms=<n>`. O log
de acesso do gunicorn não leva `%(U)s`.

## `GET /health`

`200` `{"ok": true}` sempre que o processo responde. É o `healthCheckPath` do Render: não toca o
banco, para um soluço do Postgres não fazer o Render reiniciar o serviço.

## `GET /health/banco`

`200` `{"ok": true}` se `SELECT 1` responde em até 3 s; `503` `{"ok": false}` senão. Usado pela
sondagem do quickstart e do `manto-deploy`.

## Qualquer outro caminho ou método

`404` `{"success": false, "message": "Not found"}` / `405`
`{"success": false, "message": "Method not allowed"}`.

---

# Contrato — backend (sem endpoint novo)

- `virtuais_ops.drenar_caixa_de_avisos(limite: int = 50) -> dict[str, int]` — `{"drenadas",
  "falhas", "alertadas"}`. Chamada por `ciclo_de_varredura()` (primeira rotina, chave `"caixa"`) e
  pela thread `caixa-de-avisos`.
- `POST /api/webhooks/infinitepay/<token>` do backend: **inalterado** (links criados antes do deploy
  e plano B).
- `webhook_url` dos links novos: `{INFINITEPAY_AVISO_BASE_URL}/api/webhooks/infinitepay/{token}`.
