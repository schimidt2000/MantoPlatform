"""Verificação funcional da feature 173 — endpoints de impersonação ("Ver como").

Roda contra a cópia local de produção (`manto_local`, Postgres) via DATABASE_URL.
REGRA: requests do test client SEMPRE fora de `app.app_context()` (contexto
persistente vaza o usuário logado entre requests).

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
    $env:PYTHONPATH = (Get-Location).Path
    .venv\\Scripts\\python.exe specs\\173-design-system-shell\\verify_173.py
"""

import os
import sys

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para manto_local (Postgres), nunca SQLite.")

from app import create_app, db  # noqa: E402
from app.constants import IMPERSONABLE_ROLES, RoleName  # noqa: E402
from app.models import User  # noqa: E402

PASSWORD = "verify-173-senha"

app = create_app()

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


# ── Setup: garante um SUPERADMIN e um não-SUPERADMIN com senha conhecida ──────
with app.app_context():
    superadmin = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .first()
    )
    normal = (
        User.query.filter(User.has_access.is_(True))
        .filter(~User.roles.any(name=RoleName.SUPERADMIN))
        .filter(User.email.isnot(None))
        .first()
    )
    if not superadmin or not normal:
        sys.exit("ERRO: manto_local sem usuários adequados (superadmin/não-superadmin).")
    superadmin.set_password(PASSWORD)
    normal.set_password(PASSWORD)
    db.session.commit()
    superadmin_email = superadmin.email
    normal_email = normal.email

# ── 1. Sem sessão → 401 ───────────────────────────────────────────────────────
client = app.test_client()
resp = client.post("/api/auth/impersonate", json={"role": "CASTING"})
check("impersonate sem sessão → 401", resp.status_code == 401, str(resp.status_code))

# ── 2. SUPERADMIN: login e campos novos do /me ────────────────────────────────
client = app.test_client()
resp = client.post("/api/auth/login", json={"email": superadmin_email, "password": PASSWORD})
check("login SUPERADMIN → 200", resp.status_code == 200, str(resp.status_code))

resp = client.get("/api/auth/me")
me = resp.get_json() or {}
check(
    "/me expõe is_real_superadmin=True e is_educamanto_responsavel (bool)",
    me.get("is_real_superadmin") is True and isinstance(me.get("is_educamanto_responsavel"), bool),
    str(me),
)
check("/me sem impersonação → impersonating null", me.get("impersonating") is None, str(me))

# ── 3. POST cada papel válido ────────────────────────────────────────────────
for role in IMPERSONABLE_ROLES:
    resp = client.post("/api/auth/impersonate", json={"role": role})
    body = resp.get_json() or {}
    check(
        f"impersonate {role} → 200 + impersonating={role}",
        resp.status_code == 200
        and body.get("impersonating") == role
        and body.get("is_superadmin") is False
        and body.get("is_real_superadmin") is True,
        f"{resp.status_code} {body.get('impersonating')}",
    )

# ── 4. Efeito RBAC real: /api/dashboard respeita a sessão de impersonação ────
# (paridade com o Jinja: o "Ver como" filtra o dashboard/agenda; os gates do
#  financeiro NÃO olham a sessão — nem no Jinja legado — ver research.md)
resp = client.post("/api/auth/impersonate", json={"role": "CASTING"})
casting_dash = client.get("/api/dashboard").get_json() or {}
check(
    "sob CASTING, /api/dashboard omite a seção financeiro",
    casting_dash.get("financeiro") is None and casting_dash.get("casting") is not None,
    str(list(casting_dash.keys())),
)

# ── 5. Papel inválido / minúsculas ───────────────────────────────────────────
resp = client.post("/api/auth/impersonate", json={"role": "MARKETING"})
check("papel fora da lista → 400", resp.status_code == 400, str(resp.status_code))
resp = client.post("/api/auth/impersonate", json={})
check("payload sem role → 400", resp.status_code == 400, str(resp.status_code))
resp = client.post("/api/auth/impersonate", json={"role": "financeiro"})
body = resp.get_json() or {}
check(
    "papel em minúsculas é normalizado → 200 FINANCEIRO",
    resp.status_code == 200 and body.get("impersonating") == "FINANCEIRO",
    f"{resp.status_code} {body.get('impersonating')}",
)

# ── 6. DELETE (reset) idempotente ────────────────────────────────────────────
resp = client.delete("/api/auth/impersonate")
body = resp.get_json() or {}
check(
    "reset → 200 + impersonating null + is_superadmin True",
    resp.status_code == 200 and body.get("impersonating") is None and body.get("is_superadmin") is True,
    f"{resp.status_code} {body}",
)
resp = client.delete("/api/auth/impersonate")
check("reset repetido (idempotente) → 200", resp.status_code == 200, str(resp.status_code))

resp = client.get("/api/financeiro/dashboard")
check("após reset, /api/financeiro/dashboard volta a responder 200", resp.status_code == 200, str(resp.status_code))

# ── 7. Não-SUPERADMIN → 403 ─────────────────────────────────────────────────
client2 = app.test_client()
resp = client2.post("/api/auth/login", json={"email": normal_email, "password": PASSWORD})
check("login não-SUPERADMIN → 200", resp.status_code == 200, f"{resp.status_code} {normal_email}")
resp = client2.post("/api/auth/impersonate", json={"role": "CASTING"})
check("não-SUPERADMIN impersonate → 403", resp.status_code == 403, str(resp.status_code))
resp = client2.delete("/api/auth/impersonate")
check("não-SUPERADMIN reset → 403", resp.status_code == 403, str(resp.status_code))
me2 = client2.get("/api/auth/me").get_json() or {}
check("/me não-SUPERADMIN → is_real_superadmin False", me2.get("is_real_superadmin") is False, str(me2))

# ── Resultado ────────────────────────────────────────────────────────────────
passed = sum(1 for _, ok, _ in results if ok)
print(f"\n{passed}/{len(results)} verificações passaram.")
sys.exit(0 if passed == len(results) else 1)
