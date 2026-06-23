# Implementation Plan: Security hardening (074)

**Branch**: `074-security-hardening` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

## Summary

Hardening defensivo de alto impacto e baixo risco: remover senha hardcoded, `SECRET_KEY` robusto,
cookies de sessão seguros sempre, cabeçalhos de segurança, correção de open redirect e de XSS via
JSON em `<script>`, e limite global de upload. **Sem migration, sem mudança de modelo.** CSRF por
token fica como recomendação (alto risco de quebra) — mitigado por SameSite + form-action.

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2.

**Primary Dependencies**: nenhuma nova (usa `secrets`, `werkzeug`). `flask-limiter` já presente.

**Storage**: sem migration. `instance/.secret_key` (arquivo) como fallback de chave em produção.

**Testing**: contra **`manto_local`** — app boota; `GET /health` e uma página autenticada trazem os
cabeçalhos; cookie de sessão com flags; `next` externo ignorado; login OK; `ruff` sem erros novos.

**Constraints**: **não quebrar produção** — CSP mínima (sem `default-src`/`script-src`), Secure só
em HTTPS, seed muda só banco vazio, limite de upload generoso (64 MB).

**Scale/Scope**: `config.py`, `app/__init__.py`, `seed.py`, `app/financeiro/routes.py`,
`app/orcamento/routes.py`, `app/educamanto/routes.py`.

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Usa libs já presentes; helpers pequenos.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Mudanças conservadoras; verificação em `manto_local`;
  CSP/limites escolhidos para não afetar fluxos atuais; seed só em banco vazio.
- **VI. Segurança**: ✅ Foco do trabalho.

**Resultado**: PASS — sem migration.

## Project Structure

```text
config.py                      # _resolve_secret_key(); sessão na base; MAX_CONTENT_LENGTH
app/__init__.py                # after_request (headers); _safe_next p/ impersonate referrer
seed.py                        # senha super admin via env/aleatória + must_change_password=True
app/financeiro/routes.py       # _safe_next nos redirect(next_url)
app/orcamento/routes.py        # json_for_script(settings_json)
app/educamanto/routes.py       # json_for_script(packages_json)
```

**Structure Decision**: Correções pontuais de configuração e rotas. Sem migration.

## Complexity Tracking

> Sem violações. CSRF por token registrado como follow-up (fora de escopo por risco de quebra).
