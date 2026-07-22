# Contrato de API — Feedback Público por Token (164)

Estende `specs/144-migracao-react-spa/contracts/api-conventions.md`. Ambas as rotas são públicas
(sem `@login_required`, sem RBAC) — mesma acessibilidade de `/avaliar/<token>` hoje.

## `GET /api/avaliar/<token>`

- Público, sem rate limit (só leitura).
- 404 se o token não corresponder a nenhum evento: `{"error": {"message": "Link não encontrado"}}`.
- 200: `{"event_title", "event_date" (DD/MM/AAAA ou null), "positive_tags": string[], "attention_tags": string[]}`.

## `POST /api/avaliar/<token>`

- Público. Rate limit: `10 per hour` por IP (mesmo limite do Jinja).
- `Content-Type: application/json` — corpo: `{"client_name", "score" (1-5), "tags"?: string[], "comment"?}`.
- 404 se o token não corresponder a nenhum evento (mesma mensagem do `GET`).
- 400 se faltar `client_name`: `{"error": {"message": "Informe seu nome antes de enviar a avaliação.", "fields": {"client_name": "..."}}}`.
- 400 se `score` fora de 1–5: `{"error": {"message": "Selecione uma nota de 1 a 5 estrelas.", "fields": {"score": "..."}}}`.
- Etiquetas fora da categoria correspondente à nota são silenciosamente descartadas (mesmo
  comportamento do Jinja — `_tags_for_score` filtra antes de salvar, nunca retorna erro por
  causa disso).
- 201: `{"ok": true}`.
