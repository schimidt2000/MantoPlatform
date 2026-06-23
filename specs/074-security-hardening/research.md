# Research / Auditoria de Segurança (074)

Auditoria defensiva do app Flask. Foco: alto impacto, baixo risco de quebra. Sem migration.

## Achados e decisões

### C1 — Senha do super admin hardcoded (`seed.py`) — CRÍTICO
- `user.set_password("$ch!m1dT@9")` + `must_change_password=False`, em código e histórico git.
- **Decisão**: senha vem de `SEED_SUPERADMIN_PASSWORD` (env); se ausente, gera aleatória
  (`secrets.token_urlsafe`) e imprime uma vez; `must_change_password=True`. Só afeta banco vazio
  (prod existente intacto). **Ação do dono**: trocar a senha viva (a antiga vazou no histórico).

### H1 — `SECRET_KEY` default fraco — ALTO
- `os.getenv("SECRET_KEY", "dev-secret-key")`. Sem env em prod → chave conhecida → forja de sessão.
- **Decisão**: `_resolve_secret_key()` — usa env se forte; em produção, se ausente/fraca, gera chave
  forte e **persiste em `instance/.secret_key`** (compartilhada entre workers, estável no deploy);
  se não conseguir escrever, usa chave aleatória em memória + log crítico. Dev mantém default.

### H2 — Sem cabeçalhos de segurança — ALTO
- **Decisão**: `@app.after_request` adiciona: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy: geolocation=(), microphone=(), camera=()`,
  `Content-Security-Policy: object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'`,
  e `Strict-Transport-Security` quando HTTPS. CSP **sem** `default-src`/`script-src` para não
  quebrar scripts inline, Google Fonts/Maps e o iframe de preview (verificado: scripts são locais,
  nenhum `<form action=http>` externo).

### H3 — CSRF — ALTO (mitigado)
- Sem token CSRF nos formulários. **Decisão**: mitigar com `SameSite=Lax` (cookie não vai em POST
  cross-site) **sempre** + `form-action 'self'`. Token CSRF global exigiria alterar dezenas de
  formulários e chamadas `fetch` → alto risco de quebra; fica como recomendação de defesa em
  profundidade.

### M1 — Segurança dependia de `FLASK_ENV` — MÉDIO
- Cookies seguros só na `ProductionConfig`. **Decisão**: mover `SESSION_COOKIE_HTTPONLY` e
  `SESSION_COOKIE_SAMESITE='Lax'` para a `Config` base (sempre on); `Secure` continua só em prod
  (HTTP em dev). ProxyFix já é aplicado em prod (run.py).

### M2 — Open redirect — MÉDIO
- `redirect(next_url)` (5x em financeiro) e `redirect(request.referrer or ...)` (impersonate).
- **Decisão**: `_safe_next(value, default)` aceita só caminhos **internos** (sem esquema/host).
  Aplicado aos `next_url` e aos redirects de impersonação.

### M3 — XSS via `| safe` em JSON — MÉDIO
- `settings_json`/`packages_json` = `json.dumps(...)` com `| safe` em `<script>`. Campo admin com
  `</script>` quebra o contexto. **Decisão**: escapar `<`,`>`,`&`,`U+2028/2029` no JSON antes de
  injetar (helper `json_for_script`), mantendo JSON válido.

### M4 — Sem limite global de upload — MÉDIO
- **Decisão**: `MAX_CONTENT_LENGTH = 64 MB` (acima dos limites por arquivo de 10–20 MB; evita DoS).

## Já seguro (sem mudança)
- Hash **bcrypt**; **ORM** (sem SQLi); SQL bruto **parametrizado** (`text()` com binds);
  **rate-limit** no login (10/min); `session.clear()` no login (anti-fixation); sem
  `eval/exec/pickle/subprocess/os.system`; uploads com `secure_filename` + checagem de tamanho +
  download via rota autenticada.

## Verificação
- App boota; resposta traz os cabeçalhos; cookie de sessão com flags; `next` externo é ignorado;
  login segue funcionando; `ruff` sem erros novos. Tudo contra `manto_local`.
