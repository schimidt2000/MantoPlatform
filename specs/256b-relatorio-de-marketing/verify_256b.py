"""verify_256b — o relatório da rotina de marketing sai pelo `POST /report` (hotfix da 256).

Desde a 256 o endpoint chamava `send_audit_report_email(..., preheader=...)`, e a função nunca teve o
parâmetro: 500 antes de enviar. Achado na 1ª rodada em produção (17/11/2026).

Roda contra um espelho local (dump de produção). O envio é dublado (`email_service._send`), o token do
agente é gerado aqui e nenhuma conexão externa sai (socket bloqueado). Cenário 1 FALHA com o código da
`main` de 17/11 (`2cff4499`).

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path
    python specs/256b-relatorio-de-marketing/verify_256b.py
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
from unittest import mock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para o Postgres local, nunca SQLite.")
if os.environ.get("MANTO_SEM_THREADS") != "1":
    sys.exit("ERRO: rode com MANTO_SEM_THREADS=1 (o espelho tem credenciais reais).")
if "localhost" not in os.environ["DATABASE_URL"] and "127.0.0.1" not in os.environ["DATABASE_URL"]:
    sys.exit("ERRO: este verify só roda contra banco local.")

_ESCAPES: list[str] = []
_original = socket.create_connection


def _so_local(address, *args, **kwargs):
    host = str(address[0])
    if host not in ("localhost", "127.0.0.1", "::1"):
        _ESCAPES.append(host)
        raise OSError(f"[verify_256b] conexão externa bloqueada: {host}")
    return _original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import (  # noqa: E402
    create_app,
    db,
    email_service,  # noqa: E402
)
from app.models import User  # noqa: E402

RUN = secrets.token_hex(3)
TOKEN = f"tok256b-{RUN}-{secrets.token_hex(8)}"
EMAIL = f"verify256b-{RUN}@example.invalid"
app = create_app()
app.config["MARKETING_AGENT_TOKEN"] = TOKEN
_engine = create_engine(os.environ["DATABASE_URL"].strip())
resultados: list[tuple[str, bool, str]] = []


def check(nome: str, ok: bool, detalhe: str = "") -> None:
    resultados.append((nome, ok, detalhe))
    print(
        f"{'OK' if ok else 'FALHA':6} {nome}" + (f"  [{detalhe}]" if detalhe and not ok else ""),
        flush=True,
    )


def _corpo(to: list[str]) -> dict:
    return {"subject": "Marketing · teste 256b", "html": "<p>relatório de teste</p>", "to": to}


# Fixture: um usuário interno descartável, ativo e com acesso (o endpoint só envia para o quadro interno).
with app.app_context():
    u = User(
        name=f"Verify 256b {RUN}",
        email=EMAIL,
        has_access=True,
        is_active=True,
        receives_commission=False,
    )
    u.set_password(secrets.token_urlsafe(12))
    db.session.add(u)
    db.session.commit()

client = app.test_client(use_cookies=False)
enviados: list[dict] = []


def _send_dublado(to: str, subject: str, body: str = "", html: str = "") -> bool:
    enviados.append({"to": to, "subject": subject, "html": html})
    return True


try:
    with mock.patch.object(email_service, "_send", side_effect=_send_dublado):
        # 1. O relatório de marketing sai (DEVE falhar com o código de antes: 500).
        r = client.post(f"/api/marketing-agent/{TOKEN}/report", json=_corpo([EMAIL]))
        corpo = r.get_json(silent=True) or {}
        check(
            "1. POST /report → 200 e um e-mail",
            r.status_code == 200 and corpo.get("sent") == 1,
            f"{r.status_code} {corpo}",
        )
        check(
            "1b. prévia do e-mail é a do marketing",
            bool(enviados) and "Relatório semanal do auditor de marketing." in enviados[-1]["html"],
        )

        # 2. O auditor financeiro continua com a prévia dele (chamada sem o parâmetro novo).
        with app.app_context():
            dest = User.query.filter_by(email=EMAIL).one()
            n = email_service.send_audit_report_email("Financeiro · teste", "<p>x</p>", [dest])
        check(
            "2. auditor financeiro mantém a prévia própria",
            n == 1 and "Relatório semanal da auditoria financeira." in enviados[-1]["html"],
        )

        # 3. Destinatário fora do quadro interno não recebe nada.
        antes = len(enviados)
        r = client.post(
            f"/api/marketing-agent/{TOKEN}/report", json=_corpo(["fora@example.invalid"])
        )
        corpo = r.get_json(silent=True) or {}
        check(
            "3. fora do quadro interno: nenhum envio",
            r.status_code == 200 and corpo.get("sent") == 0 and len(enviados) == antes,
            f"{r.status_code} {corpo}",
        )

        # 4. Token errado continua 404 (portão).
        r = client.post("/api/marketing-agent/token-errado/report", json=_corpo([EMAIL]))
        check("4. token errado → 404", r.status_code == 404, str(r.status_code))
finally:
    with _engine.begin() as conn:
        conn.execute(
            text("DELETE FROM user_roles WHERE user_id IN (SELECT id FROM users WHERE email = :e)"),
            {"e": EMAIL},
        )
        conn.execute(text("DELETE FROM users WHERE email = :e"), {"e": EMAIL})
    with _engine.connect() as conn:
        sobrou = conn.execute(
            text("SELECT count(*) FROM users WHERE email = :e"), {"e": EMAIL}
        ).scalar()
    check("5. limpeza", sobrou == 0)
    check("6. nenhuma conexão externa", not _ESCAPES, ", ".join(_ESCAPES))

ok = sum(1 for _, b, _ in resultados if b)
print(f"\n{ok}/{len(resultados)} OK")
sys.exit(0 if ok == len(resultados) else 1)
