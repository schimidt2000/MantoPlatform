"""Verificação da correção 336 — buscar evento por data no vínculo da tag NFC (e onde mais a busca vale).

Cenários (spec §Verificação):
 1. Sem login, `GET /api/agenda/search` responde 401.                     (DEVE falhar se vazar)
 2. "07/11" devolve eventos, todos de um dia 7 de novembro, nenhum cancelado.  (falha no antigo)
 3. "07/11/2026", "7/11/26", "07-11-2026" e "2026-11-07" devolvem o MESMO conjunto, só de 2026.
 4. A busca por data bate com o banco (conexão separada): mesmos ids que o SELECT direto.
 5. "31/02" não é data: cai na busca de texto e responde 200 sem erro.
 6. A busca por texto continua: "ariel" traz eventos com "ariel" no título.
 7. Limpeza (usuário descartável apagado).

Só leitura sobre eventos; o único registro gravado é o usuário descartável.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\336-busca-evento-tag-nfc\\verify_336.py
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import Role, User  # noqa: E402

PREFIX = "__v336_"
SENHA = "verify-336-senha"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, str(exc)))
        print(f"  FALHOU {nome}: {exc}")
        traceback.print_exc()


def _busca(q: str, http=None) -> tuple[int, list[dict]]:
    r = (http or estado["http"]).get("/api/agenda/search", query_string={"q": q})
    corpo = r.get_json(silent=True) or {}
    return r.status_code, corpo.get("items", [])


def _dia(item: dict) -> datetime:
    return datetime.fromisoformat(item["start_at"])


def preparar() -> None:
    with app.app_context():
        user = User(
            name=f"{PREFIX}comercial",
            email=f"{PREFIX}comercial@manto.local",
            is_active=True,
            has_access=True,
        )
        user.set_password(SENHA)
        user.roles.append(Role.query.filter_by(name=RoleName.COMERCIAL).one())
        db.session.add(user)
        db.session.commit()
    c = app.test_client()
    r = c.post(
        "/api/auth/login", json={"email": f"{PREFIX}comercial@manto.local", "password": SENHA}
    )
    _garante(r.status_code == 200, f"login → {r.status_code}")
    estado["http"] = c


def c1_sem_login() -> None:
    status, _ = _busca("07/11", http=app.test_client())
    _garante(status == 401, f"sem login → {status}, esperado 401")


def c2_dia_mes() -> None:
    status, itens = _busca("07/11")
    _garante(status == 200, f"status {status}")
    _garante(len(itens) > 0, "nenhum evento em 07/11 — a busca por data não pegou")
    fora = [i["title"] for i in itens if (_dia(i).day, _dia(i).month) != (7, 11)]
    _garante(not fora, f"eventos fora de 07/11: {fora[:3]}")
    cancelados = [i["title"] for i in itens if i.get("situacao") == "cancelado"]
    _garante(not cancelados, f"cancelado na busca: {cancelados[:3]}")
    estado["ids_2026"] = {i["id"] for i in itens if _dia(i).year == 2026}


def c3_formatos_com_ano() -> None:
    conjuntos = {}
    for termo in ("07/11/2026", "7/11/26", "07-11-2026", "2026-11-07"):
        status, itens = _busca(termo)
        _garante(status == 200, f"{termo} → {status}")
        _garante(all(_dia(i).year == 2026 for i in itens), f"{termo} trouxe outro ano")
        conjuntos[termo] = {i["id"] for i in itens}
    _garante(
        len({frozenset(s) for s in conjuntos.values()}) == 1, f"formatos divergem: {conjuntos}"
    )
    _garante(
        conjuntos["07/11/2026"] == estado["ids_2026"],
        "com ano ≠ parte de 2026 do sem ano",
    )
    estado["ids_com_ano"] = conjuntos["07/11/2026"]


def c4_bate_com_banco() -> None:
    linhas = _no_banco(
        "SELECT id FROM calendar_events WHERE start_at >= '2026-11-07' AND start_at < '2026-11-08'"
        " AND cancelled_at IS NULL ORDER BY start_at DESC LIMIT 30"
    )
    _garante({r[0] for r in linhas} == estado["ids_com_ano"], "ids ≠ SELECT direto")


def c5_data_invalida() -> None:
    status, _ = _busca("31/02")
    _garante(status == 200, f"31/02 → {status}")


def c6_texto_continua() -> None:
    status, itens = _busca("ariel")
    _garante(status == 200 and itens, "busca 'ariel' vazia")
    _garante(any("ariel" in i["title"].lower() for i in itens), "nenhum título com 'ariel'")


def limpar() -> None:
    with app.app_context():
        for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
            u.roles.clear()
            db.session.delete(u)
        db.session.commit()
    sobra = _no_banco("SELECT count(*) FROM users WHERE email LIKE :p", p=f"{PREFIX}%")[0][0]
    _garante(sobra == 0, f"{sobra} usuário(s) descartável(is) sobrando")


if __name__ == "__main__":
    print("verify_336 — busca de evento por data")
    try:
        preparar()
        cenario("1. sem login → 401", c1_sem_login)
        cenario("2. '07/11' só traz 7 de novembro", c2_dia_mes)
        cenario("3. formatos com ano devolvem o mesmo conjunto", c3_formatos_com_ano)
        cenario("4. bate com o banco (conexão separada)", c4_bate_com_banco)
        cenario("5. '31/02' não quebra", c5_data_invalida)
        cenario("6. busca por texto continua", c6_texto_continua)
    finally:
        cenario("7. limpeza", limpar)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} cenários OK")
    sys.exit(0 if ok == len(resultados) else 1)
