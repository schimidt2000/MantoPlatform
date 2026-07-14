# Tasks — Bloquear Indexação em Buscadores (127)

- [X] T001 `app/__init__.py`: `_security_headers()` ganha
      `X-Robots-Tag: noindex, nofollow, noarchive` em toda resposta
- [X] T002 `app/__init__.py`: nova rota `GET /robots.txt` retornando
      `User-agent: *\nDisallow: /`
- [X] T003 Verificação funcional vs manto_local (10/10): login, home, `/gastos/` (tela
      interna), os dois formulários públicos e até uma resposta 404 respondem com
      `X-Robots-Tag: noindex, nofollow, noarchive`; `/robots.txt` responde
      `Disallow: /`. Ruff: 8/8 erros pré-existentes (baseline de `app/__init__.py`),
      zero novo.
- [X] T004 Commit, merge em main, push
