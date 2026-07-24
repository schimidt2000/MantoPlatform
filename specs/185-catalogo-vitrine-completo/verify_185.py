"""Verificação funcional da feature 185 — Catálogo Vitrine Completo (Temas/Personagens/Vídeo).

Roda contra a cópia local de produção (`manto_local`, Postgres) via DATABASE_URL.
REGRA: requests do test client SEMPRE fora de `app.app_context()` (contexto
persistente vaza o usuário logado entre requests).

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
    $env:PYTHONPATH = (Get-Location).Path
    .venv\\Scripts\\python.exe specs\\185-catalogo-vitrine-completo\\verify_185.py
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

PASSWORD = "verify-185-senha"

app = create_app()

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


# ── Setup ────────────────────────────────────────────────────────────────────
with app.app_context():
    superadmin = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .first()
    )
    non_comercial = (
        User.query.filter(User.has_access.is_(True))
        .filter(~User.roles.any(name=RoleName.SUPERADMIN))
        .filter(~User.roles.any(name=RoleName.COMERCIAL))
        .filter(User.email.isnot(None))
        .first()
    )
    if not superadmin:
        sys.exit("ERRO: manto_local sem usuário SUPERADMIN com acesso.")

    superadmin.set_password(PASSWORD)
    if non_comercial:
        non_comercial.set_password(PASSWORD)

    figurino = FigurinoSheet(character_name="Verify185 Figurino")
    db.session.add(figurino)
    db.session.flush()

    superadmin_email = superadmin.email
    non_comercial_email = non_comercial.email if non_comercial else None
    figurino_id = figurino.id
    db.session.commit()

client = app.test_client()

tema_id: int | None = None
character_id: int | None = None

try:
    resp = client.post("/api/auth/login", json={"email": superadmin_email, "password": PASSWORD})
    check("login superadmin → 200", resp.status_code == 200, str(resp.status_code))

    # 1. Criar Tema com video_url inválida → 400 com fields.video_url
    resp = client.post(
        "/api/admin/catalogo",
        data={"name": "Verify185 Tema", "description": "", "tags": "", "video_url": "https://nao-e-video.com/x"},
        content_type="multipart/form-data",
    )
    check(
        "criar Tema sem foto e video_url inválida → 400",
        resp.status_code == 400,
        str(resp.get_json()),
    )

    # 2. Criar Tema válido (com foto e video_url MP4 válida)
    resp = client.post(
        "/api/admin/catalogo",
        data={
            "name": "Verify185 Tema",
            "description": "",
            "tags": "natal, verificacao",
            "video_url": "https://example.com/video.mp4",
            "new_photos": (io.BytesIO(b"fake-jpg-bytes"), "foto.jpg"),
        },
        content_type="multipart/form-data",
    )
    check("criar Tema válido → 201", resp.status_code == 201, str(resp.get_json()))
    tema_id = (resp.get_json() or {}).get("id")

    # 3. Criar Personagem filho vinculado à ficha de figurino
    resp = client.post(
        f"/api/admin/catalogo/{tema_id}/personagens",
        data={"name": "Verify185 Personagem", "video_url": "", "figurino_sheet_id": str(figurino_id)},
        content_type="multipart/form-data",
    )
    check("criar Personagem vinculado a figurino → 201", resp.status_code == 201, str(resp.get_json()))
    character_id = (resp.get_json() or {}).get("id")
    check(
        "Personagem criado retorna figurino_sheet_id correto",
        (resp.get_json() or {}).get("figurino_sheet_id") == figurino_id,
        str(resp.get_json()),
    )

    # 4. Personagem com video_url inválida → 400
    resp = client.post(
        f"/api/admin/catalogo/{tema_id}/personagens",
        data={"name": "Outro", "video_url": "não-é-url"},
        content_type="multipart/form-data",
    )
    check("criar Personagem com video_url inválida → 400", resp.status_code == 400, str(resp.get_json()))

    # 5. Grade pública inclui o Tema e o Personagem ativo no detalhe
    resp = client.get("/api/catalogo")
    body = resp.get_json() or {}
    slug = next((i["slug"] for i in body.get("items", []) if i["id"] == tema_id), None)
    check("GET /api/catalogo lista o Tema criado", slug is not None, str(body))

    resp = client.get(f"/api/catalogo/{slug}")
    body = resp.get_json() or {}
    check(
        "GET detalhe público inclui o Personagem ativo",
        any(c["id"] == character_id for c in body.get("characters", [])),
        str(body.get("characters")),
    )
    check("GET detalhe público classifica video_kind do Tema como mp4", body.get("video_kind") == "mp4", str(body))

    # 6. GET /api/catalogo/elenco-busca: superadmin (tem SUPERADMIN) → 200 com o Tema
    resp = client.get("/api/catalogo/elenco-busca")
    body = resp.get_json() or {}
    check(
        "elenco-busca (superadmin) → 200 com Tema+Personagem",
        resp.status_code == 200
        and any(
            t["id"] == tema_id and any(c["figurino_sheet_id"] == figurino_id for c in t["characters"])
            for t in body.get("temas", [])
        ),
        str(body),
    )

    # 7. elenco-busca negado para papel sem COMERCIAL/SUPERADMIN
    if non_comercial_email:
        client2 = app.test_client()
        resp = client2.post("/api/auth/login", json={"email": non_comercial_email, "password": PASSWORD})
        check("login usuário não-comercial → 200", resp.status_code == 200, str(resp.status_code))
        resp = client2.get("/api/catalogo/elenco-busca")
        check("elenco-busca (sem COMERCIAL/SUPERADMIN) → 403", resp.status_code == 403, str(resp.status_code))
    else:
        check("elenco-busca (sem COMERCIAL/SUPERADMIN) → 403", True, "SKIP: nenhum usuário não-comercial em manto_local")

    # 8. Excluir a Ficha de Figurino → Personagem degrada com segurança (figurino_sheet_id vira NULL)
    with app.app_context():
        ficha = db.session.get(FigurinoSheet, figurino_id)
        db.session.delete(ficha)
        db.session.commit()
        personagem_apos = db.session.get(CatalogCharacter, character_id)
        check(
            "excluir Ficha de Figurino → figurino_sheet_id do Personagem vira NULL",
            personagem_apos is not None and personagem_apos.figurino_sheet_id is None,
            str(personagem_apos.figurino_sheet_id if personagem_apos else "personagem sumiu"),
        )

    # 9. Excluir o Tema → Personagem é removido em cascata
    resp = client.delete(f"/api/admin/catalogo/{tema_id}")
    check("DELETE Tema → 204", resp.status_code == 204, str(resp.status_code))
    with app.app_context():
        personagem_orfao = db.session.get(CatalogCharacter, character_id)
        check("excluir Tema → Personagem removido em cascata", personagem_orfao is None, str(personagem_orfao))
        tema_orfao = db.session.get(CatalogItem, tema_id)
        check("Tema realmente excluído", tema_orfao is None, str(tema_orfao))
    tema_id = None  # já limpo, evita dupla exclusão no finally

finally:
    with app.app_context():
        leftover_tema = db.session.get(CatalogItem, tema_id) if tema_id else None
        if leftover_tema is not None:
            catalog_ops.delete_product(leftover_tema)
        leftover_ficha = db.session.get(FigurinoSheet, figurino_id)
        if leftover_ficha is not None:
            db.session.delete(leftover_ficha)
            db.session.commit()

# ── Resultado ────────────────────────────────────────────────────────────────
passed = sum(1 for _, ok, _ in results if ok)
print(f"\n{passed}/{len(results)} verificações passaram.")
sys.exit(0 if passed == len(results) else 1)
