"""Verificação funcional da feature 182 — status de aprovação da Revisão de Mídia.

Roda contra a cópia local de produção (`manto_local`, Postgres) via DATABASE_URL.
REGRA: requests do test client SEMPRE fora de `app.app_context()` (contexto
persistente vaza o usuário logado entre requests).

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
    $env:PYTHONPATH = (Get-Location).Path
    .venv\\Scripts\\python.exe specs\\182-revisao-midia-vimeo\\verify_182.py
"""

import io
import os
import sys

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para manto_local (Postgres), nunca SQLite.")

from app import create_app, db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import ReviewAsset, ReviewReviewer, ReviewSpace, User  # noqa: E402
from app.revisao import review_ops  # noqa: E402

PASSWORD = "verify-182-senha"

app = create_app()

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


# ── Setup: superadmin (dono do espaço) + revisor comum (sem can_manage) ─────
with app.app_context():
    superadmin = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .first()
    )
    revisor = (
        User.query.filter(User.has_access.is_(True))
        .filter(~User.roles.any(name=RoleName.SUPERADMIN))
        .filter(User.email.isnot(None))
        .first()
    )
    if not superadmin or not revisor:
        sys.exit("ERRO: manto_local sem usuários adequados (superadmin/revisor comum).")
    superadmin.set_password(PASSWORD)
    revisor.set_password(PASSWORD)

    space = ReviewSpace(title="Verificação 182 — status", created_by=superadmin.id)
    db.session.add(space)
    db.session.flush()
    db.session.add(ReviewReviewer(space_id=space.id, user_id=revisor.id))
    asset = ReviewAsset(
        space_id=space.id,
        file_path="review/verify182.webm",
        original_name="verify182.webm",
        media_type="video",
        position=0,
    )
    db.session.add(asset)
    db.session.commit()
    superadmin_email = superadmin.email
    revisor_email = revisor.email
    space_id = space.id
    asset_id = asset.id

client = app.test_client()

try:
    resp = client.post("/api/auth/login", json={"email": superadmin_email, "password": PASSWORD})
    check("login superadmin (dono do espaço) → 200", resp.status_code == 200, str(resp.status_code))

    # 1. Material recém-criado nasce "em_revisao".
    resp = client.get(f"/api/revisao/{space_id}/asset/{asset_id}")
    body = resp.get_json() or {}
    check(
        "GET asset → status default 'em_revisao'",
        resp.status_code == 200 and body.get("asset", {}).get("status") == "em_revisao",
        str(body.get("asset")),
    )

    # 2. can_manage muda o status → 200 e persiste.
    resp = client.patch(f"/api/revisao/asset/{asset_id}/status", json={"status": "aprovado"})
    check(
        "PATCH status (can_manage) → 200 'aprovado'",
        resp.status_code == 200 and (resp.get_json() or {}).get("status") == "aprovado",
        str(resp.get_json()),
    )
    resp = client.get(f"/api/revisao/{space_id}/asset/{asset_id}")
    body = resp.get_json() or {}
    check(
        "status persiste após reload (GET)",
        body.get("asset", {}).get("status") == "aprovado",
        str(body.get("asset")),
    )

    # 3. Valor inválido → 400.
    resp = client.patch(f"/api/revisao/asset/{asset_id}/status", json={"status": "foo"})
    check("PATCH status inválido → 400", resp.status_code == 400, str(resp.status_code))

    # 4. replace_asset reseta o status para 'em_revisao', mesmo vindo de 'aprovado'.
    resp = client.post(
        f"/api/revisao/asset/{asset_id}/replace",
        data={"file": (io.BytesIO(b"dados falsos de video v2"), "v2.webm")},
        content_type="multipart/form-data",
    )
    check("POST replace (nova versão) → 200", resp.status_code == 200, str(resp.status_code))
    resp = client.get(f"/api/revisao/{space_id}/asset/{asset_id}")
    body = resp.get_json() or {}
    check(
        "replace_asset reseta status para 'em_revisao'",
        body.get("asset", {}).get("status") == "em_revisao",
        str(body.get("asset")),
    )

    # 5. Usuário sem can_manage (revisor comum) → 403 ao tentar mudar status.
    client2 = app.test_client()
    resp = client2.post("/api/auth/login", json={"email": revisor_email, "password": PASSWORD})
    check("login revisor comum → 200", resp.status_code == 200, str(resp.status_code))
    resp = client2.patch(f"/api/revisao/asset/{asset_id}/status", json={"status": "rejeitado"})
    check("PATCH status sem can_manage → 403", resp.status_code == 403, str(resp.status_code))

finally:
    # Limpeza: remove o espaço de teste (e os arquivos reais gravados pelo /replace) independentemente
    # do resultado acima — via review_ops.delete_space, não db.session.delete direto, para não deixar
    # arquivo órfão em instance/uploads/review.
    with app.app_context():
        leftover = db.session.get(ReviewSpace, space_id)
        if leftover is not None:
            review_ops.delete_space(leftover)

# ── Resultado ────────────────────────────────────────────────────────────────
passed = sum(1 for _, ok, _ in results if ok)
print(f"\n{passed}/{len(results)} verificações passaram.")
sys.exit(0 if passed == len(results) else 1)
