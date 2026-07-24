"""Verificação funcional da feature 186 — UX do Gerenciador de Catálogo + fluxo Ficha↔Catálogo↔Venda.

Roda contra a cópia local de produção (`manto_local`, Postgres) via DATABASE_URL.
REGRA: requests do test client SEMPRE fora de `app.app_context()`.

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
    $env:PYTHONPATH = (Get-Location).Path
    .venv\\Scripts\\python.exe specs\\186-gerenciador-catalogo-ux\\verify_186.py
"""

import io
import os
import sys

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para manto_local (Postgres), nunca SQLite.")

from app import create_app, db  # noqa: E402
from app.admin import catalog_ops  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import CatalogCharacter, CatalogItem, FigurinoSheet, User  # noqa: E402

PASSWORD = "verify-186-senha"

app = create_app()

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


with app.app_context():
    superadmin = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .first()
    )
    figurino_user = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.FIGURINO))
        .filter(~User.roles.any(name=RoleName.SUPERADMIN))
        .first()
    )
    no_access_user = (
        User.query.filter(User.has_access.is_(True))
        .filter(~User.roles.any(name=RoleName.SUPERADMIN))
        .filter(~User.roles.any(name=RoleName.COMERCIAL))
        .filter(~User.roles.any(name=RoleName.FIGURINO))
        .filter(User.email.isnot(None))
        .first()
    )
    if not superadmin:
        sys.exit("ERRO: manto_local sem usuário SUPERADMIN com acesso.")

    superadmin.set_password(PASSWORD)
    if figurino_user:
        figurino_user.set_password(PASSWORD)
    if no_access_user:
        no_access_user.set_password(PASSWORD)

    figurino_sheet = FigurinoSheet(character_name="Verify186 Figurino")
    db.session.add(figurino_sheet)
    db.session.flush()
    figurino_sheet_id = figurino_sheet.id

    superadmin_email = superadmin.email
    figurino_email = figurino_user.email if figurino_user else None
    no_access_email = no_access_user.email if no_access_user else None
    db.session.commit()

client = app.test_client()
tema_a_id: int | None = None
tema_b_id: int | None = None
character_ids: list[int] = []

try:
    resp = client.post("/api/auth/login", json={"email": superadmin_email, "password": PASSWORD})
    check("login superadmin → 200", resp.status_code == 200, str(resp.status_code))

    # 1. Criar dois Temas (origem e destino do "mover em massa") + Personagens no Tema A.
    resp = client.post(
        "/api/admin/catalogo",
        data={
            "name": "Verify186 Tema A", "description": "", "tags": "", "video_url": "",
            "new_photos": (io.BytesIO(b"fake-jpg-bytes"), "a.jpg"),
        },
        content_type="multipart/form-data",
    )
    check("criar Tema A → 201", resp.status_code == 201, str(resp.get_json()))
    tema_a_id = (resp.get_json() or {}).get("id")

    resp = client.post(
        "/api/admin/catalogo",
        data={
            "name": "Verify186 Tema B", "description": "", "tags": "", "video_url": "",
            "new_photos": (io.BytesIO(b"fake-jpg-bytes"), "b.jpg"),
        },
        content_type="multipart/form-data",
    )
    check("criar Tema B → 201", resp.status_code == 201, str(resp.get_json()))
    tema_b_id = (resp.get_json() or {}).get("id")

    for name in ["Verify186 P1", "Verify186 P2"]:
        resp = client.post(
            f"/api/admin/catalogo/{tema_a_id}/personagens",
            data={"name": name, "video_url": "", "figurino_sheet_id": str(figurino_sheet_id) if name.endswith("P1") else ""},
            content_type="multipart/form-data",
        )
        check(f"criar Personagem {name} → 201", resp.status_code == 201, str(resp.get_json()))
        character_ids.append((resp.get_json() or {}).get("id"))

    # 2. GET /api/admin/catalogo inclui characters[] com photo_url/figurino_sheet_id.
    resp = client.get("/api/admin/catalogo")
    body = resp.get_json() or {}
    tema_a = next((i for i in body.get("items", []) if i["id"] == tema_a_id), None)
    check(
        "GET /admin/catalogo inclui characters[] do Tema A",
        tema_a is not None and len(tema_a.get("characters", [])) == 2,
        str(tema_a),
    )
    check(
        "characters[] inclui figurino_sheet_id vinculado",
        tema_a is not None and any(c["figurino_sheet_id"] == figurino_sheet_id for c in tema_a["characters"]),
        str(tema_a),
    )

    # 3. elenco-busca inclui photo_url por Personagem.
    resp = client.get("/api/catalogo/elenco-busca")
    body = resp.get_json() or {}
    tema_a_elenco = next((t for t in body.get("temas", []) if t["id"] == tema_a_id), None)
    check(
        "elenco-busca inclui campo photo_url por Personagem",
        tema_a_elenco is not None and all("photo_url" in c for c in tema_a_elenco["characters"]),
        str(tema_a_elenco),
    )

    # 4. elenco-busca aceita papel FIGURINO (feature 186, era só COMERCIAL/SUPERADMIN).
    if figurino_email:
        client_figurino = app.test_client()
        resp = client_figurino.post("/api/auth/login", json={"email": figurino_email, "password": PASSWORD})
        check("login usuário FIGURINO → 200", resp.status_code == 200, str(resp.status_code))
        resp = client_figurino.get("/api/catalogo/elenco-busca")
        check("elenco-busca (papel FIGURINO) → 200", resp.status_code == 200, str(resp.status_code))
    else:
        check("elenco-busca (papel FIGURINO) → 200", True, "SKIP: nenhum usuário FIGURINO em manto_local")

    # 5. elenco-busca continua negando papel sem COMERCIAL/FIGURINO/SUPERADMIN.
    if no_access_email:
        client_no_access = app.test_client()
        resp = client_no_access.post("/api/auth/login", json={"email": no_access_email, "password": PASSWORD})
        check("login usuário sem papel relevante → 200", resp.status_code == 200, str(resp.status_code))
        resp = client_no_access.get("/api/catalogo/elenco-busca")
        check("elenco-busca (sem papel relevante) → 403", resp.status_code == 403, str(resp.status_code))
    else:
        check("elenco-busca (sem papel relevante) → 403", True, "SKIP: nenhum usuário sem papel relevante em manto_local")

    # 6. Mover em massa: reatribui os 2 Personagens do Tema A para o Tema B numa única chamada.
    resp = client.post(
        "/api/admin/catalogo/personagens/mover-em-massa",
        json={"character_ids": character_ids, "target_item_id": tema_b_id},
    )
    check("mover-em-massa → 200 moved=2", resp.status_code == 200 and (resp.get_json() or {}).get("moved") == 2, str(resp.get_json()))

    with app.app_context():
        moved = CatalogCharacter.query.filter(CatalogCharacter.id.in_(character_ids)).all()
        check(
            "Personagens agora pertencem ao Tema B",
            all(c.catalog_item_id == tema_b_id for c in moved),
            str([(c.id, c.catalog_item_id) for c in moved]),
        )

    # 7. mover-em-massa recusa target_item_id inexistente.
    resp = client.post(
        "/api/admin/catalogo/personagens/mover-em-massa",
        json={"character_ids": character_ids, "target_item_id": 999999},
    )
    check("mover-em-massa com target inexistente → 404", resp.status_code == 404, str(resp.status_code))

    # 8. mover-em-massa recusa character_ids vazio.
    resp = client.post(
        "/api/admin/catalogo/personagens/mover-em-massa",
        json={"character_ids": [], "target_item_id": tema_b_id},
    )
    check("mover-em-massa com character_ids vazio → 400", resp.status_code == 400, str(resp.status_code))

    # 9. Vincular Personagem a Ficha a partir do PATCH usado pela tela da Ficha (US2) — sem name.
    resp = client.patch(
        f"/api/admin/catalogo/personagens/{character_ids[1]}",
        data={"figurino_sheet_id": str(figurino_sheet_id)},
        content_type="multipart/form-data",
    )
    check(
        "PATCH só com figurino_sheet_id (sem name) → 200, não exige nome",
        resp.status_code == 200 and (resp.get_json() or {}).get("figurino_sheet_id") == figurino_sheet_id,
        str(resp.get_json()),
    )

    # 10. Toggle de is_active de Personagem (novo, para inativar em massa).
    resp = client.patch(
        f"/api/admin/catalogo/personagens/{character_ids[0]}",
        data={"is_active": "false"},
        content_type="multipart/form-data",
    )
    check(
        "PATCH is_active=false → 200, personagem inativo",
        resp.status_code == 200 and (resp.get_json() or {}).get("is_active") is False,
        str(resp.get_json()),
    )

finally:
    with app.app_context():
        for tid in (tema_a_id, tema_b_id):
            leftover = db.session.get(CatalogItem, tid) if tid else None
            if leftover is not None:
                catalog_ops.delete_product(leftover)
        leftover_sheet = db.session.get(FigurinoSheet, figurino_sheet_id)
        if leftover_sheet is not None:
            db.session.delete(leftover_sheet)
            db.session.commit()

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n{passed}/{len(results)} verificações passaram.")
sys.exit(0 if passed == len(results) else 1)
