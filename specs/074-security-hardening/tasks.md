# Tasks: Security hardening (074)

**Feature**: `074-security-hardening` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem migration. Verificação contra **`manto_local`**.

---

## Fase 1 — Segredos (C1/H1)

- [X] T001 `seed.py`: senha do super admin inicial via `SEED_SUPERADMIN_PASSWORD` (env); fallback aleatório (`secrets.token_urlsafe`); `must_change_password=True`; remover a senha hardcoded. Só afeta banco vazio.
- [X] T002 `config.py`: `_resolve_secret_key()` — usa env; em produção, se ausente/fraca, gera chave forte e persiste em `instance/.secret_key` (fallback aleatório em memória + log crítico). Dev mantém default.

## Fase 2 — Sessão + limites (M1/M4)

- [X] T003 `config.py`: mover `SESSION_COOKIE_HTTPONLY=True` e `SESSION_COOKIE_SAMESITE="Lax"` para a `Config` base (sempre); `Secure` só em produção. Adicionar `MAX_CONTENT_LENGTH = 64*1024*1024`.

## Fase 3 — Cabeçalhos de segurança (H2/H3)

- [X] T004 `app/__init__.py`: `@app.after_request` adicionando nosniff, `X-Frame-Options: SAMEORIGIN`, Referrer-Policy, Permissions-Policy, CSP mínima (`object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'`) e HSTS quando HTTPS. Sem `default-src`/`script-src` (não quebrar inline/integrações).

## Fase 4 — Open redirect + XSS JSON (M2/M3)

- [X] T005 `app/__init__.py`: helper `_safe_next(value, default)` (só caminhos internos) usado nos redirects de impersonação (`request.referrer`).
- [X] T006 `app/financeiro/routes.py`: aplicar validação interna aos `redirect(next_url)` (5 sítios) via `_safe_next`.
- [X] T007 `app/orcamento/routes.py` e `app/educamanto/routes.py`: escapar JSON injetado em `<script>` (`json_for_script`: escapa `<`,`>`,`&`,U+2028/2029) em `settings_json`/`packages_json`.

## Fase 5 — Verificação

- [X] T008 Contra **`manto_local`**: app boota; `GET /health` e página autenticada trazem os cabeçalhos; cookie de sessão com `HttpOnly`/`SameSite`; `next` externo é ignorado; login funciona; `ruff check` sem erros novos.

---

## Dependências

- T001/T002/T003 (config/seed) → T004/T005/T006/T007 → T008.

## MVP

T001 (segredo) + T002 (SECRET_KEY) + T004 (headers) são o núcleo; demais completam o hardening.
