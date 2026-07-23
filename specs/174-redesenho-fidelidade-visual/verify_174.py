"""Verificação funcional da feature 174 — extensão de `/api/dashboard` (comercial/performance).

Roda contra a cópia local de produção (`manto_local`, Postgres) via DATABASE_URL.
REGRA: requests do test client SEMPRE fora de `app.app_context()` (contexto
persistente vaza o usuário logado entre requests).

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
    $env:PYTHONPATH = (Get-Location).Path
    .venv\\Scripts\\python.exe specs\\174-redesenho-fidelidade-visual\\verify_174.py
"""

import os
import sys

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para manto_local (Postgres), nunca SQLite.")

from app import create_app, db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import User  # noqa: E402

PASSWORD = "verify-174-senha"

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

client = app.test_client()
resp = client.post("/api/auth/login", json={"email": superadmin_email, "password": PASSWORD})
check("login SUPERADMIN → 200", resp.status_code == 200, str(resp.status_code))

# ── 1. Sem parâmetro: performance/comercial presentes p/ SUPERADMIN real ────
resp = client.get("/api/dashboard")
check("GET /api/dashboard (sem parâmetro) → 200", resp.status_code == 200, str(resp.status_code))
body = resp.get_json() or {}
perf = body.get("performance")
check(
    "performance presente e com range default '7'",
    isinstance(perf, dict) and perf.get("range") == "7",
    str(perf),
)
check(
    "performance tem os 5 campos numéricos esperados",
    isinstance(perf, dict)
    and all(
        k in perf
        for k in ("casting_total", "casting_done", "figurino_total", "figurino_done", "money_total")
    ),
    str(perf),
)
check(
    "comercial presente (SUPERADMIN) com pending_payments (lista)",
    isinstance(body.get("comercial"), dict) and isinstance(body["comercial"].get("pending_payments"), list),
    str(body.get("comercial")),
)

# ── 2. perf_range=30 ──────────────────────────────────────────────────────────
resp = client.get("/api/dashboard?perf_range=30")
body30 = resp.get_json() or {}
check(
    "perf_range=30 → performance.range == '30'",
    resp.status_code == 200 and (body30.get("performance") or {}).get("range") == "30",
    str(body30.get("performance")),
)

# ── 3. perf_range=custom sem datas → performance null (fallback silencioso) ──
resp = client.get("/api/dashboard?perf_range=custom")
bodyc = resp.get_json() or {}
check(
    "perf_range=custom sem datas → 200 + performance null",
    resp.status_code == 200 and bodyc.get("performance") is None,
    str(bodyc.get("performance")),
)

# ── 4. perf_range=custom com start > end → performance null ─────────────────
resp = client.get("/api/dashboard?perf_range=custom&perf_start=2026-06-01&perf_end=2026-01-01")
bodyi = resp.get_json() or {}
check(
    "perf_range=custom com start > end → 200 + performance null",
    resp.status_code == 200 and bodyi.get("performance") is None,
    str(bodyi.get("performance")),
)

# ── 5. perf_range=custom válido ──────────────────────────────────────────────
resp = client.get("/api/dashboard?perf_range=custom&perf_start=2026-01-01&perf_end=2026-01-31")
bodyv = resp.get_json() or {}
perfv = bodyv.get("performance") or {}
check(
    "perf_range=custom válido → range/start/end ecoados",
    resp.status_code == 200
    and perfv.get("range") == "custom"
    and perfv.get("start") == "2026-01-01"
    and perfv.get("end") == "2026-01-31",
    str(perfv),
)

# ── 6. Durante impersonação, performance nunca aparece ───────────────────────
resp = client.post("/api/auth/impersonate", json={"role": "CASTING"})
check("impersonate CASTING → 200", resp.status_code == 200, str(resp.status_code))
resp = client.get("/api/dashboard")
body_imp = resp.get_json() or {}
check(
    "sob impersonação CASTING, performance é null e comercial é null",
    body_imp.get("performance") is None and body_imp.get("comercial") is None,
    str({"performance": body_imp.get("performance"), "comercial": body_imp.get("comercial")}),
)
check(
    "sob impersonação CASTING, casting continua presente",
    body_imp.get("casting") is not None,
    str(body_imp.get("casting")),
)

resp = client.post("/api/auth/impersonate", json={"role": "FINANCEIRO"})
resp = client.get("/api/dashboard")
body_fin = resp.get_json() or {}
check(
    "sob impersonação FINANCEIRO, comercial presente e performance null",
    isinstance(body_fin.get("comercial"), dict) and body_fin.get("performance") is None,
    str({"performance": body_fin.get("performance"), "comercial": body_fin.get("comercial")}),
)

resp = client.delete("/api/auth/impersonate")
check("reset impersonação → 200", resp.status_code == 200, str(resp.status_code))

# ── 7. Paridade Jinja: home() não quebra após a extração (compute_* extraído) ─
resp = client.get("/")
check("GET / (home Jinja) → 200 após extração de compute_performance/compute_comercial_pending", resp.status_code == 200, str(resp.status_code))
resp = client.get("/?perf_range=30")
check("GET /?perf_range=30 (home Jinja) → 200", resp.status_code == 200, str(resp.status_code))

# ── 8. Não-SUPERADMIN nunca vê performance ───────────────────────────────────
client2 = app.test_client()
resp = client2.post("/api/auth/login", json={"email": normal_email, "password": PASSWORD})
check("login não-SUPERADMIN → 200", resp.status_code == 200, str(resp.status_code))
resp = client2.get("/api/dashboard")
body_n = resp.get_json() or {}
check(
    "não-SUPERADMIN → performance sempre null",
    resp.status_code == 200 and body_n.get("performance") is None,
    str(body_n.get("performance")),
)

# ── Resultado ────────────────────────────────────────────────────────────────
passed = sum(1 for _, ok, _ in results if ok)
print(f"\n{passed}/{len(results)} verificações passaram.")
sys.exit(0 if passed == len(results) else 1)
