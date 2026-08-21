"""Verificação da feature 258 — cadastro manual de cliente pela tela de Clientes.

Cenários:
 1. Cria com todos os campos (nome, telefone, e-mail, empresa, CPF, CNPJ, endereço) e a ficha
    nasce com `source="manual"`.
 2. Telefone repetido devolve o cliente existente com `reused: true`, sem duplicar e **sem
    sobrescrever** o que já estava lá.
 3. Telefone em formato humano ("(11) 98888-0002") vira a forma canônica com DDI 55;
    `phone_display` guarda o que foi digitado.
 4. Nome vazio e telefone inválido devolvem 400 com o campo apontado.
 5. RBAC: CASTING recebe 403; COMERCIAL cria.
 6. O cliente novo aparece na listagem (`GET /api/clientes/`) e nas métricas.
 7. Limpeza total.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .venv/Scripts/python.exe specs/258-cliente-manual/verify_258.py
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from app import create_app, db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import Client, Role, User  # noqa: E402

PREFIX = "__v258_"
SENHA = "verify-258-senha"
TEL_BASE = "11988880001"
# `normalize_phone` acrescenta o DDI 55 a números com DDD (docstring do importador).
TEL_CANONICO = "55" + TEL_BASE

app = create_app()
app.config["TESTING"] = True
resultados: list[tuple[str, bool, str]] = []
estado: dict = {}


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — harness: registra e segue
        db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _usuario(sufixo: str, papel: str) -> User:
    email = f"{PREFIX}{sufixo}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        db.session.add(user)
    user.set_password(SENHA)
    user.roles.clear()
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.commit()
    return user


def _cliente(client, email: str = None):  # noqa: ANN001 - helper de teste
    return client


def _login(c, user: User) -> None:
    r = c.post("/api/auth/login", json={"email": user.email, "password": SENHA})
    _garante(r.status_code == 200, f"login {user.email} → {r.status_code}")


def cen_01_cria_completo() -> None:
    with app.test_client() as c:
        _login(c, estado["comercial"])
        r = c.post("/api/clientes/quick-create", json={
            "name": f"{PREFIX}Maria Souza", "phone": TEL_BASE, "phone_display": "(11) 98888-0001",
            "email": "maria.v258@example.com", "company": "Festas Souza",
            "cpf": "123.456.789-00", "cnpj": "12.345.678/0001-90", "address": "Rua Teste, 100 — São Paulo",
        })
        _garante(r.status_code == 200, f"criar → {r.status_code} {r.get_data(as_text=True)[:200]}")
        body = r.get_json()
        _garante(body["reused"] is False, "cliente novo não pode vir como reaproveitado")
        estado["client_id"] = body["id"]
    cliente = db.session.get(Client, estado["client_id"])
    db.session.refresh(cliente)
    _garante(cliente.source == "manual", f"source: {cliente.source}")
    _garante(cliente.phone == TEL_CANONICO, f"telefone normalizado: {cliente.phone}")
    _garante(cliente.phone_display == "(11) 98888-0001", f"phone_display: {cliente.phone_display}")
    _garante(cliente.email == "maria.v258@example.com" and cliente.company == "Festas Souza", "e-mail/empresa")
    _garante(cliente.cpf == "123.456.789-00" and cliente.cnpj == "12.345.678/0001-90", f"documentos: {cliente.cpf} {cliente.cnpj}")
    _garante(cliente.address and "Rua Teste" in cliente.address, f"endereço: {cliente.address}")


def cen_02_telefone_repetido() -> None:
    antes = Client.query.filter(Client.name.like(f"{PREFIX}%")).count()
    with app.test_client() as c:
        _login(c, estado["comercial"])
        r = c.post("/api/clientes/quick-create", json={
            "name": f"{PREFIX}Outro Nome", "phone": TEL_BASE, "email": "outro.v258@example.com",
            "cpf": "999.999.999-99",
        })
        _garante(r.status_code == 200, f"repetido → {r.status_code}")
        body = r.get_json()
        _garante(body["reused"] is True, "telefone repetido tinha que voltar como reaproveitado")
        _garante(body["id"] == estado["client_id"], f"devolveu outra ficha: {body['id']}")
    _garante(Client.query.filter(Client.name.like(f"{PREFIX}%")).count() == antes, "duplicou cliente")
    cliente = db.session.get(Client, estado["client_id"])
    db.session.refresh(cliente)
    _garante(cliente.name == f"{PREFIX}Maria Souza", f"nome foi sobrescrito: {cliente.name}")
    _garante(cliente.cpf == "123.456.789-00", f"CPF foi sobrescrito: {cliente.cpf}")


def cen_03_telefone_humano() -> None:
    with app.test_client() as c:
        _login(c, estado["comercial"])
        r = c.post("/api/clientes/quick-create", json={
            "name": f"{PREFIX}Ana Lima", "phone": "(11) 98888-0002", "phone_display": "(11) 98888-0002",
        })
        _garante(r.status_code == 200, f"criar → {r.status_code}")
        estado["client_id_2"] = r.get_json()["id"]
    cliente = db.session.get(Client, estado["client_id_2"])
    _garante(cliente.phone == "5511988880002", f"normalização do telefone: {cliente.phone}")


def cen_04_validacao() -> None:
    with app.test_client() as c:
        _login(c, estado["comercial"])
        r = c.post("/api/clientes/quick-create", json={"name": "", "phone": TEL_BASE})
        _garante(r.status_code == 400, f"sem nome → {r.status_code}")
        _garante("name" in (r.get_json().get("error", {}).get("fields") or {}), f"campo apontado: {r.get_json()}")
        r = c.post("/api/clientes/quick-create", json={"name": f"{PREFIX}Sem Telefone", "phone": "123"})
        _garante(r.status_code == 400, f"telefone curto → {r.status_code}")
        _garante("phone" in (r.get_json().get("error", {}).get("fields") or {}), f"campo apontado: {r.get_json()}")
    _garante(not Client.query.filter(Client.name == f"{PREFIX}Sem Telefone").first(), "criou cliente inválido")


def cen_05_rbac() -> None:
    with app.test_client() as c:
        _login(c, estado["casting"])
        r = c.post("/api/clientes/quick-create", json={"name": f"{PREFIX}Proibida", "phone": "11988880003"})
        _garante(r.status_code == 403, f"CASTING → {r.status_code}")
    _garante(not Client.query.filter(Client.name == f"{PREFIX}Proibida").first(), "criou sem permissão")


def cen_06_aparece_na_lista() -> None:
    with app.test_client() as c:
        _login(c, estado["comercial"])
        r = c.get(f"/api/clientes/?q={PREFIX}Maria")
        _garante(r.status_code == 200, f"lista → {r.status_code}")
        ids = [item["id"] for item in r.get_json()["items"]]
        _garante(estado["client_id"] in ids, f"cliente novo fora da busca: {ids}")
        r = c.get("/api/clientes/metricas")
        _garante(r.status_code == 200, f"métricas → {r.status_code}")
        meses = r.get_json()["new_by_month"]
        _garante(meses and meses[-1]["manual"] >= 2, f"métrica de manuais do mês: {meses[-1] if meses else None}")


def preparar() -> None:
    limpar()
    estado["comercial"] = _usuario("comercial", RoleName.COMERCIAL)
    estado["casting"] = _usuario("casting", RoleName.CASTING)


def limpar() -> None:
    db.session.rollback()
    Client.query.filter(Client.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    for sufixo in ("comercial", "casting"):
        user = User.query.filter_by(email=f"{PREFIX}{sufixo}@manto.local").first()
        if user:
            user.roles.clear()
            db.session.delete(user)
    db.session.commit()


def main() -> int:
    with app.app_context():
        try:
            preparar()
            print("Feature 258 — cadastro manual de cliente contra manto_local")
            cenario("1. cria com todos os campos", cen_01_cria_completo)
            cenario("2. telefone repetido reaproveita sem sobrescrever", cen_02_telefone_repetido)
            cenario("3. telefone humano é normalizado", cen_03_telefone_humano)
            cenario("4. validação de nome e telefone", cen_04_validacao)
            cenario("5. RBAC (CASTING barrado)", cen_05_rbac)
            cenario("6. aparece na lista e nas métricas", cen_06_aparece_na_lista)
        finally:
            cenario("7. limpeza", limpar)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
