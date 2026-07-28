"""Auditoria de segurança da Plataforma Manto (feature 191).

Roda contra a cópia local do banco real (`manto_local`, PostgreSQL) com o test client do Flask e
valida três famílias de barreira:

1. **Cookies de sessão** — `HttpOnly`, `SameSite` e `Secure` nas sessões de Staff e de Talento,
   mais o isolamento hermético entre elas (um cookie de talento não abre a API de staff, e
   vice-versa).
2. **RBAC** — talento tentando alcançar endpoints do app interno, e staff de um papel tentando
   alcançar dados de outro (vendedor × salários/financeiro).
3. **Resiliência de e-mail** — com `SiteSetting.email_notifications_enabled = False` (log
   silencioso, sem 500) e com a flag ligada mas o SMTP quebrado (mensagem limpa, sem 500).

Uso (PowerShell, a partir da raiz do repositório):

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
    $env:PYTHONPATH = (Get-Location).Path
    .venv\\Scripts\\python.exe scripts\\security\\overnight_security_audit.py

Saída: relatório no stdout e um resumo em Markdown em `scripts/security/relatorio_seguranca.md`.
Código de saída 1 se qualquer verificação falhar — serve como portão de CI.

REGRA DO PROJETO respeitada aqui: nenhuma request do test client roda dentro de
`with app.app_context()` — contexto persistente vaza o usuário logado entre requests.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from app import create_app, db
from app.models import Role, SiteSetting, Talent, User

app = create_app()

TALENT_PASSWORD = "Audit!Pw191"
STAFF_PASSWORD = "Audit!Staff191"
MARKER = "AUDIT191"

REPORT_PATH = Path(__file__).with_name("relatorio_seguranca.md")


class Finding(NamedTuple):
    """Um item verificado pela auditoria."""

    section: str
    name: str
    passed: bool
    detail: str


findings: list[Finding] = []
_current_section = "geral"


def section(title: str) -> None:
    """Inicia uma seção do relatório."""
    global _current_section
    _current_section = title
    print(f"\n=== {title} ===")


def check(name: str, passed: bool, detail: str = "") -> bool:
    """Registra o resultado de uma verificação e o imprime."""
    findings.append(Finding(_current_section, name, bool(passed), detail))
    status = "OK  " if passed else "FALHA"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return bool(passed)


# ── Massa de teste ─────────────────────────────────────────────────────────────


def cleanup() -> None:
    """Remove tudo que a auditoria cria, para poder rodar quantas vezes for preciso.

    Apaga objeto a objeto (não `query.delete()`): o DELETE em massa não passa pelo ORM e deixa
    órfãs as linhas da tabela de associação `user_roles`, estourando a FK.
    """
    with app.app_context():
        for user in User.query.filter(User.name.like(f"{MARKER}%")).all():
            user.roles.clear()
            db.session.delete(user)
        for talent in Talent.query.filter(Talent.full_name.like(f"{MARKER}%")).all():
            db.session.delete(talent)
        db.session.commit()


def make_talent() -> int:
    """Cria um talento com senha e termos aceitos (conta em dia)."""
    with app.app_context():
        talent = Talent(
            full_name=f"{MARKER} Talento",
            cpf="99900011122",
            email_contact=f"{MARKER.lower()}.talento@audit.local",
            status="active",
        )
        talent.set_password(TALENT_PASSWORD)
        talent.must_change_password = False
        talent.terms_accepted_at = datetime.utcnow()
        db.session.add(talent)
        db.session.commit()
        return talent.id


def make_staff(suffix: str, role_names: list[str]) -> str:
    """Cria um usuário de staff com os papéis informados e devolve o e-mail de login."""
    with app.app_context():
        email = f"{MARKER.lower()}.{suffix}@audit.local"
        user = User(name=f"{MARKER} {suffix}", email=email, has_access=True)
        user.set_password(STAFF_PASSWORD)
        user.must_change_password = False
        for role_name in role_names:
            role = Role.query.filter_by(name=role_name).first()
            if role is not None:
                user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        return email


# ── 1. Cookies de sessão ───────────────────────────────────────────────────────


def parse_set_cookie(response: Any) -> str | None:
    """Cabeçalho `Set-Cookie` do cookie de sessão da resposta, ou `None` se não houver."""
    for header, value in response.headers:
        if header.lower() == "set-cookie" and value.split("=", 1)[0] == "session":
            return value
    return None


def audit_cookie(label: str, set_cookie: str | None, expect_secure: bool) -> None:
    """Confere as flags de segurança de um `Set-Cookie` de sessão."""
    if not check(f"{label}: login emite cookie de sessão", bool(set_cookie)):
        return

    assert set_cookie is not None
    lowered = set_cookie.lower()

    # Só os ATRIBUTOS do cookie entram no relatório — nunca o valor assinado da sessão, que é
    # credencial e acabaria versionado junto com o Markdown.
    attributes = "; ".join(part.strip() for part in set_cookie.split(";")[1:]) or "(sem atributos)"

    check(
        f"{label}: cookie tem HttpOnly (bloqueia leitura por XSS)",
        "httponly" in lowered,
        attributes,
    )

    samesite = re.search(r"samesite=(\w+)", lowered)
    value = samesite.group(1) if samesite else None
    check(
        f"{label}: cookie tem SameSite=Lax ou Strict (bloqueia CSRF cross-site)",
        value in {"lax", "strict"},
        f"SameSite={value or 'ausente'}",
    )

    # Em dev o app roda em HTTP, então `Secure` fica desligado de propósito
    # (`DevelopmentConfig`). A auditoria confere o valor esperado para o ambiente carregado e
    # valida separadamente que ProductionConfig liga a flag.
    check(
        f"{label}: flag Secure coerente com o ambiente",
        ("secure" in lowered) == expect_secure,
        f"Secure={'presente' if 'secure' in lowered else 'ausente'} (esperado: {expect_secure})",
    )


def audit_production_cookie_config() -> None:
    """Confere que a config de produção endurece o cookie, mesmo rodando a auditoria em dev."""
    from app.config import ProductionConfig

    check(
        "ProductionConfig: SESSION_COOKIE_SECURE = True",
        ProductionConfig.SESSION_COOKIE_SECURE is True,
    )
    check(
        "ProductionConfig: SESSION_COOKIE_HTTPONLY = True",
        ProductionConfig.SESSION_COOKIE_HTTPONLY is True,
    )
    check(
        "ProductionConfig: SESSION_COOKIE_SAMESITE em {Lax, Strict}",
        ProductionConfig.SESSION_COOKIE_SAMESITE in {"Lax", "Strict"},
        f"SameSite={ProductionConfig.SESSION_COOKIE_SAMESITE}",
    )


def audit_cookies(staff_email: str) -> None:
    """Cookies das duas sessões + isolamento hermético entre Staff e Talento."""
    section("1. Cookies de sessão (HttpOnly / SameSite / Secure)")

    expect_secure = bool(app.config.get("SESSION_COOKIE_SECURE"))

    with app.test_client() as client:
        response = client.post(
            "/api/portal/auth/login",
            json={"login": "99900011122", "password": TALENT_PASSWORD},
        )
        check("Portal: login do talento responde 200", response.status_code == 200)
        audit_cookie("Portal (Talento)", parse_set_cookie(response), expect_secure)

    with app.test_client() as client:
        response = client.post(
            "/api/auth/login", json={"email": staff_email, "password": STAFF_PASSWORD}
        )
        check("App interno: login de staff responde 200", response.status_code == 200)
        audit_cookie("App interno (Staff)", parse_set_cookie(response), expect_secure)

    audit_production_cookie_config()

    section("1b. Isolamento entre sessão de Staff e de Talento")

    # Talento logado não pode alcançar a API de staff.
    with app.test_client() as client:
        client.post(
            "/api/portal/auth/login",
            json={"login": "99900011122", "password": TALENT_PASSWORD},
        )
        response = client.get("/api/auth/me")
        check(
            "Cookie de Talento NÃO autentica na API de Staff (/api/auth/me)",
            response.status_code in (401, 403),
            f"HTTP {response.status_code}",
        )

    # Staff logado não pode alcançar a API do portal.
    with app.test_client() as client:
        client.post("/api/auth/login", json={"email": staff_email, "password": STAFF_PASSWORD})
        response = client.get("/api/portal/auth/me")
        check(
            "Cookie de Staff NÃO autentica na API do Portal (/api/portal/auth/me)",
            response.status_code in (401, 403),
            f"HTTP {response.status_code}",
        )
        response = client.get("/api/portal/agenda")
        check(
            "Cookie de Staff NÃO alcança a Agenda do Portal",
            response.status_code in (401, 403),
            f"HTTP {response.status_code}",
        )

    # Login de talento sobre sessão de staff derruba a sessão anterior (session.clear()).
    with app.test_client() as client:
        client.post("/api/auth/login", json={"email": staff_email, "password": STAFF_PASSWORD})
        client.post(
            "/api/portal/auth/login",
            json={"login": "99900011122", "password": TALENT_PASSWORD},
        )
        response = client.get("/api/auth/me")
        check(
            "Login de Talento encerra a sessão de Staff no mesmo cookie",
            response.status_code in (401, 403),
            f"HTTP {response.status_code}",
        )

    # E o caminho inverso.
    with app.test_client() as client:
        client.post(
            "/api/portal/auth/login",
            json={"login": "99900011122", "password": TALENT_PASSWORD},
        )
        client.post("/api/auth/login", json={"email": staff_email, "password": STAFF_PASSWORD})
        response = client.get("/api/portal/auth/me")
        check(
            "Login de Staff encerra a sessão de Talento no mesmo cookie",
            response.status_code in (401, 403),
            f"HTTP {response.status_code}",
        )


# ── 2. RBAC ────────────────────────────────────────────────────────────────────

#: Endpoints do app interno que um talento jamais pode alcançar.
INTERNAL_ENDPOINTS_FOR_TALENT = [
    ("GET", "/api/auth/me"),
    ("GET", "/api/dashboard"),
    ("GET", "/api/financeiro/dashboard"),
    ("GET", "/api/financeiro/pagamentos"),
    ("GET", "/api/vendas/pipeline"),
    ("GET", "/api/admin/users"),
    ("GET", "/api/admin/settings"),
    ("GET", "/api/admin/logs"),
    ("GET", "/api/rh/dashboard"),
    ("GET", "/api/talents"),
    ("GET", "/api/talents/directory"),
    ("GET", "/api/agenda"),
    ("GET", "/api/clientes"),
]

#: Endpoints sensíveis que um vendedor (COMERCIAL) não deve alcançar.
CROSS_ROLE_ENDPOINTS = [
    ("GET", "/api/admin/users", "painel de usuários (SUPERADMIN/FINANCEIRO)"),
    ("GET", "/api/rh/dashboard", "painel de RH / salários"),
    ("GET", "/api/financeiro/pagamentos", "planilha de pagamentos"),
    ("GET", "/api/admin/settings", "configurações do sistema"),
    ("GET", "/api/admin/logs", "logs de auditoria"),
    ("GET", "/api/admin/desempenho", "painel de desempenho"),
]


def existing_routes() -> set[str]:
    """Regras registradas no app, para pular endpoints que não existem neste build."""
    with app.app_context():
        return {str(rule) for rule in app.url_map.iter_rules()}


def audit_rbac_talent_vs_internal(routes: set[str]) -> None:
    """Talento autenticado tentando forçar acesso ao app interno."""
    section("2. RBAC — Talento tentando alcançar o App Interno")

    with app.test_client() as client:
        client.post(
            "/api/portal/auth/login",
            json={"login": "99900011122", "password": TALENT_PASSWORD},
        )
        for method, path in INTERNAL_ENDPOINTS_FOR_TALENT:
            if path not in routes:
                check(f"{method} {path}", True, "rota inexistente neste build — ignorada")
                continue
            response = client.open(path, method=method)
            check(
                f"Talento bloqueado em {method} {path}",
                response.status_code in (401, 403),
                f"HTTP {response.status_code}",
            )


def audit_rbac_anonymous(routes: set[str]) -> None:
    """Sem sessão nenhuma, todo endpoint autenticado precisa recusar."""
    section("2b. RBAC — Anônimo (sem sessão)")

    protected = [
        ("GET", "/api/financeiro/dashboard"),
        ("GET", "/api/admin/users"),
        ("GET", "/api/portal/agenda"),
        ("GET", "/api/portal/profile"),
        ("GET", "/api/portal/historico"),
        ("GET", "/api/portal/ratings/pending"),
    ]
    with app.test_client() as client:
        for method, path in protected:
            if path not in routes:
                check(f"{method} {path}", True, "rota inexistente neste build — ignorada")
                continue
            response = client.open(path, method=method)
            check(
                f"Anônimo bloqueado em {method} {path}",
                response.status_code in (401, 403),
                f"HTTP {response.status_code}",
            )


def audit_rbac_cross_staff(seller_email: str, routes: set[str]) -> None:
    """Staff de um papel tentando alcançar área de outro papel."""
    section("2c. RBAC — Acesso cruzado entre papéis de Staff (vendedor)")

    with app.test_client() as client:
        response = client.post(
            "/api/auth/login", json={"email": seller_email, "password": STAFF_PASSWORD}
        )
        if not check("Vendedor (COMERCIAL) autentica", response.status_code == 200):
            return

        for method, path, description in CROSS_ROLE_ENDPOINTS:
            if path not in routes:
                check(f"{method} {path}", True, "rota inexistente neste build — ignorada")
                continue
            response = client.open(path, method=method)
            check(
                f"Vendedor bloqueado em {description} ({method} {path})",
                response.status_code in (401, 403),
                f"HTTP {response.status_code}",
            )


def audit_rbac_talent_data_isolation() -> None:
    """Um talento não pode agir sobre recursos de outro talento (IDOR)."""
    section("2d. RBAC — Isolamento de dados entre talentos (IDOR)")

    with app.app_context():
        other = Talent(
            full_name=f"{MARKER} Outro Talento",
            cpf="99900011133",
            email_contact=f"{MARKER.lower()}.outro@audit.local",
            status="active",
        )
        other.set_password(TALENT_PASSWORD)
        other.must_change_password = False
        other.terms_accepted_at = datetime.utcnow()
        db.session.add(other)
        db.session.commit()

    with app.test_client() as client:
        client.post(
            "/api/portal/auth/login",
            json={"login": "99900011122", "password": TALENT_PASSWORD},
        )
        # Convite/escalação inexistente ou de terceiro: nunca 200.
        for path in (
            "/api/portal/invites/999999/accept",
            "/api/portal/invites/999999/reject",
            "/api/portal/roles/999999/ack-change",
        ):
            response = client.post(path)
            check(
                f"Talento não age sobre escalação alheia — POST {path}",
                response.status_code == 404,
                f"HTTP {response.status_code}",
            )

        response = client.delete("/api/portal/profile/media/999999")
        check(
            "Talento não apaga mídia alheia — DELETE /api/portal/profile/media/<id>",
            response.status_code == 404,
            f"HTTP {response.status_code}",
        )

        response = client.get("/api/portal/events/999999/figurino")
        check(
            "Talento não lê figurino de evento em que não está escalado",
            response.status_code in (403, 404),
            f"HTTP {response.status_code}",
        )

        # O perfil devolvido é SEMPRE o da sessão, mesmo pedindo outro id no corpo.
        response = client.patch("/api/portal/profile", json={"id": 999999, "artistic_name": "X"})
        body = response.get_json() or {}
        check(
            "PATCH /api/portal/profile ignora `id` do cliente (usa o da sessão)",
            response.status_code == 200 and body.get("full_name", "").startswith(MARKER),
            f"HTTP {response.status_code}, nome={body.get('full_name')!r}",
        )


# ── 3. Resiliência do fluxo de e-mails ─────────────────────────────────────────


def set_email_flag(enabled: bool) -> bool | None:
    """Liga/desliga `SiteSetting.email_notifications_enabled`; devolve o valor anterior."""
    with app.app_context():
        settings = SiteSetting.query.first()
        if settings is None:
            return None
        previous = settings.email_notifications_enabled
        settings.email_notifications_enabled = enabled
        db.session.commit()
        return previous


def audit_email_flow_disabled() -> None:
    """Com notificações desligadas, os disparadores registram log e não quebram a request."""
    section("3. E-mails — flag desligada (log silencioso, sem 500)")

    previous = set_email_flag(False)
    if previous is None:
        check("SiteSetting encontrado para alternar a flag", False, "nenhum SiteSetting no banco")
        return

    try:
        with app.test_client() as client:
            response = client.post(
                "/api/portal/auth/forgot-password",
                json={"login": "99900011122", "email": f"{MARKER.lower()}.talento@audit.local"},
            )
            check(
                "Reset de senha do Talento não estoura com e-mail desligado",
                response.status_code == 200,
                f"HTTP {response.status_code}",
            )

        with app.test_client() as client:
            response = client.post(
                "/api/portal/auth/first-access", json={"login": "99900011133"}
            )
            check(
                "Primeiro acesso do Talento não estoura com e-mail desligado",
                response.status_code in (200, 400),
                f"HTTP {response.status_code}",
            )

        from app.email_service import _send

        with app.app_context():
            sent = _send("ninguem@audit.local", "Assunto de auditoria", body="corpo")
        check(
            "email_service._send devolve False (não levanta) com a flag desligada",
            sent is False,
        )
    finally:
        set_email_flag(previous)


def audit_email_flow_smtp_down() -> None:
    """Com a flag ligada mas o SMTP quebrado, a request continua limpa (sem 500)."""
    section("3b. E-mails — flag ligada com SMTP quebrado (falha limpa, sem 500)")

    previous = set_email_flag(True)
    if previous is None:
        check("SiteSetting encontrado para alternar a flag", False, "nenhum SiteSetting no banco")
        return

    from app import email_service

    original_send = email_service.mail.send

    def explode(_message: Any) -> None:
        raise OSError("SMTP indisponível (simulado pela auditoria)")

    email_service.mail.send = explode  # type: ignore[assignment]
    try:
        with app.app_context():
            sent = email_service._send("ninguem@audit.local", "Assunto", body="corpo")
        check(
            "email_service._send devolve False (não propaga) quando o SMTP falha",
            sent is False,
        )

        with app.test_client() as client:
            response = client.post(
                "/api/portal/auth/forgot-password",
                json={"login": "99900011122", "email": f"{MARKER.lower()}.talento@audit.local"},
            )
            body = response.get_json() or {}
            check(
                "Reset de senha responde 200 mesmo com SMTP fora do ar",
                response.status_code == 200,
                f"HTTP {response.status_code}",
            )
            check(
                "Resposta traz mensagem amigável, não stack trace",
                isinstance(body.get("message"), str) and "Traceback" not in str(body),
                str(body.get("message"))[:80],
            )

        with app.test_client() as client:
            response = client.post("/api/portal/auth/first-access", json={"login": "99900011133"})
            check(
                "Primeiro acesso responde sem 500 com SMTP fora do ar",
                response.status_code in (200, 400),
                f"HTTP {response.status_code}",
            )
    finally:
        email_service.mail.send = original_send  # type: ignore[assignment]
        set_email_flag(previous)


def audit_email_no_account_enumeration() -> None:
    """O fluxo de reset não pode revelar se um CPF/e-mail existe."""
    section("3c. E-mails — reset de senha não revela existência de conta")

    with app.test_client() as client:
        real = client.post(
            "/api/portal/auth/forgot-password",
            json={"login": "99900011122", "email": f"{MARKER.lower()}.talento@audit.local"},
        )
        fake = client.post(
            "/api/portal/auth/forgot-password",
            json={"login": "00000000000", "email": "naoexiste@audit.local"},
        )

    check(
        "Mesmo status HTTP para conta existente e inexistente",
        real.status_code == fake.status_code == 200,
        f"real={real.status_code}, falsa={fake.status_code}",
    )
    check(
        "Mesmo corpo de resposta para conta existente e inexistente",
        real.get_json() == fake.get_json(),
    )


def audit_email_triggers_mapped() -> None:
    """Mapeia os disparadores de e-mail exigidos pela auditoria e confere que existem.

    Cada disparador é conferido pelo nome da função em `app/email_service.py`. Um nome ausente
    não é um bug de segurança em si — é um fluxo que NÃO existe, e a auditoria registra isso
    explicitamente para o mapa não ficar com um buraco silencioso.
    """
    section("3d. E-mails — mapa de disparadores")

    from app import email_service

    triggers = [
        ("Reset de senha — Talento", "send_password_reset_email", "/api/portal/auth/forgot-password"),
        ("Primeiro acesso / boas-vindas — Talento", "send_welcome_email", "/api/portal/auth/first-access"),
        ("Envio de proposta/orçamento", "send_quote_email", "/api/orcamento/* (orcamento_write)"),
        ("Convite de elenco na página do evento", "send_invite_email", "casting_ops.send_invite"),
        ("Remoção do elenco", "send_removal_email", "casting_ops.replace/remove"),
        ("Alteração de horário/local do evento", "send_event_changed_email", "event_ops/casting_ops"),
        ("Comunicado do portal", "send_portal_announcement_email", "/api/admin/config (announcement)"),
        ("Alerta de ensaio", "send_ensaio_alert_email", "cron de ensaio"),
    ]
    for label, function_name, origin in triggers:
        check(
            f"Disparador mapeado: {label} (`{function_name}`)",
            hasattr(email_service, function_name),
            origin,
        )

    # Reset de senha de STAFF não existe por e-mail: um SUPERADMIN define a senha temporária à
    # mão em `user_ops.reset_password`, sem disparo. Registrado como observação, não falha.
    from app.admin import user_ops

    check(
        "Reset de senha de Staff é manual (sem e-mail) — `user_ops.reset_password`",
        hasattr(user_ops, "reset_password"),
        "não há fluxo self-service por e-mail para staff; ver relatório",
    )


def _enclosing_function(source_lines: list[str], line_index: int) -> str:
    """Nome da função que contém a linha informada (varre para trás até um `def` de topo)."""
    for i in range(line_index, -1, -1):
        match = re.match(r"def (\w+)\(", source_lines[i])
        if match:
            return match.group(1)
    return "<módulo>"


def audit_email_dispatch_is_guarded() -> None:
    """Todo `mail.send(` precisa estar sob try/except E atrás do gate de notificações.

    Não basta contar chamadas: `send_quote_email` legitimamente não usa `_send` (precisa anexar
    um PDF, que `_send` não suporta) e reimplementa o guarda. O que importa é a propriedade —
    nenhum caminho de envio pode propagar exceção de SMTP nem ignorar a flag.
    """
    section("3e. E-mails — todo caminho de envio é guardado")

    path = Path(__file__).resolve().parents[2] / "app" / "email_service.py"
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()

    senders: list[str] = []
    for index, line in enumerate(lines):
        if re.search(r"\bmail\.send\(", line):
            senders.append(_enclosing_function(lines, index))

    check("Existe ao menos um caminho de envio mapeado", bool(senders), ", ".join(senders))

    for name in senders:
        body_match = re.search(rf"\ndef {name}\(.*?(?=\ndef |\Z)", source, re.DOTALL)
        body = body_match.group(0) if body_match else ""
        check(
            f"`{name}` envolve o envio em try/except (SMTP fora do ar não propaga)",
            "except Exception" in body,
        )
        check(
            f"`{name}` respeita SiteSetting.email_notifications_enabled",
            "_emails_enabled()" in body,
        )

    check(
        "`send_async` roda em thread com try/except (não derruba a request)",
        bool(re.search(r"def send_async\(.*?except Exception", source, re.DOTALL)),
    )


def audit_quote_email_resilience() -> None:
    """`send_quote_email` (proposta/orçamento) tem seu próprio caminho — precisa ser testado."""
    section("3f. E-mails — proposta/orçamento (caminho com anexo PDF)")

    from app import email_service

    original_send = email_service.mail.send

    def explode(_message: Any) -> None:
        raise OSError("SMTP indisponível (simulado pela auditoria)")

    previous = set_email_flag(False)
    if previous is None:
        check("SiteSetting encontrado para alternar a flag", False, "nenhum SiteSetting no banco")
        return

    try:
        with app.app_context():
            sent = email_service.send_quote_email(
                to="ninguem@audit.local", client_name="Auditoria", pdf_bytes=b"%PDF-1.4 fake"
            )
        check("Orçamento não é enviado com a flag desligada (devolve False)", sent is False)

        set_email_flag(True)
        email_service.mail.send = explode  # type: ignore[assignment]
        with app.app_context():
            sent = email_service.send_quote_email(
                to="ninguem@audit.local", client_name="Auditoria", pdf_bytes=b"%PDF-1.4 fake"
            )
        check("Orçamento devolve False (não propaga) com SMTP fora do ar", sent is False)
    finally:
        email_service.mail.send = original_send  # type: ignore[assignment]
        set_email_flag(previous)


# ── Relatório ──────────────────────────────────────────────────────────────────


def write_report() -> None:
    """Grava o resumo em Markdown ao lado do script."""
    total = len(findings)
    failed = [f for f in findings if not f.passed]
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        "# Relatório de Auditoria de Segurança — Plataforma Manto",
        "",
        f"**Gerado em:** {generated_at}  ",
        f"**Banco:** `{app.config['SQLALCHEMY_DATABASE_URI'].rsplit('@', 1)[-1]}`  ",
        f"**Resultado:** {total - len(failed)}/{total} verificações passaram"
        + (" — **tudo OK**" if not failed else f" — **{len(failed)} FALHA(S)**"),
        "",
        "Gerado por `scripts/security/overnight_security_audit.py` (feature 191).",
        "",
    ]

    current: str | None = None
    for finding in findings:
        if finding.section != current:
            current = finding.section
            lines += ["", f"## {current}", "", "| Resultado | Verificação | Detalhe |", "| --- | --- | --- |"]
        icon = "✅" if finding.passed else "❌"
        lines.append(f"| {icon} | {finding.name} | {finding.detail or '—'} |")

    if failed:
        lines += ["", "## Falhas a tratar", ""]
        lines += [f"- **{f.section}** — {f.name}" + (f" ({f.detail})" if f.detail else "") for f in failed]

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nRelatório salvo em {REPORT_PATH}")


def main() -> int:
    print("Auditoria de segurança da Plataforma Manto — feature 191")
    print(f"Banco: {app.config['SQLALCHEMY_DATABASE_URI'].rsplit('@', 1)[-1]}")

    cleanup()
    try:
        make_talent()
        staff_email = make_staff("superadmin", ["SUPERADMIN"])
        seller_email = make_staff("vendedor", ["COMERCIAL"])
        routes = existing_routes()

        audit_cookies(staff_email)
        audit_rbac_talent_vs_internal(routes)
        audit_rbac_anonymous(routes)
        audit_rbac_cross_staff(seller_email, routes)
        audit_rbac_talent_data_isolation()
        audit_email_triggers_mapped()
        audit_email_dispatch_is_guarded()
        audit_email_flow_disabled()
        audit_email_flow_smtp_down()
        audit_quote_email_resilience()
        audit_email_no_account_enumeration()
    finally:
        cleanup()

    failed = [f for f in findings if not f.passed]
    print(f"\n{'=' * 70}")
    print(f"RESULTADO: {len(findings) - len(failed)}/{len(findings)} verificações passaram")
    if failed:
        print(f"\n{len(failed)} FALHA(S):")
        for finding in failed:
            print(f"  - [{finding.section}] {finding.name}" + (f" — {finding.detail}" if finding.detail else ""))

    write_report()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
