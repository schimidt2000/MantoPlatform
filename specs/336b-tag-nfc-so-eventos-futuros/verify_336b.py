"""Verificação da correção 336b — o vínculo da tag NFC só lista eventos de hoje em diante.

Cenários (spec §Verificação):
 1. Sem login, `GET /api/agenda/search?futuros=1` responde 401.           (DEVE falhar se vazar)
 2. Sem `futuros`, a busca de texto continua trazendo passados, do mais novo ao mais antigo.
 3. Com `futuros=1`, nenhum evento antes de hoje (São Paulo) e a ordem é do mais próximo ao
    mais distante.                                                         (falha no antigo)
 4. `futuros=1` bate com o banco (conexão separada): mesmos ids e ordem do SELECT direto.
 5. Data passada digitada com `futuros=1` ainda devolve os eventos daquele dia.
 6. Limpeza (usuário descartável apagado).

Só leitura sobre eventos; o único registro gravado é o usuário descartável.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    .venv/Scripts/python.exe specs/336b-tag-nfc-so-eventos-futuros/verify_336b.py
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
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import Role, User  # noqa: E402

PREFIX = "__v336b_"
SENHA = "verify-336b-senha"

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


TERMO = "show"  # está em centenas de títulos, passados e futuros


def _busca(q: str, futuros: bool = False, http=None) -> tuple[int, list[dict]]:
    params = {"q": q, "futuros": "1"} if futuros else {"q": q}
    r = (http or estado["http"]).get("/api/agenda/search", query_string=params)
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


def _hoje() -> datetime:
    return now_sp().replace(hour=0, minute=0, second=0, microsecond=0)


def c1_sem_login() -> None:
    status, _ = _busca(TERMO, futuros=True, http=app.test_client())
    _garante(status == 401, f"sem login → {status}, esperado 401")


def c2_sem_parametro_inalterado() -> None:
    # Termo de um evento passado conhecido: sem o parâmetro ele tem de continuar aparecendo.
    linha = _no_banco(
        "SELECT id, title FROM calendar_events WHERE start_at < :h AND cancelled_at IS NULL"
        " AND length(title) > 12 ORDER BY start_at DESC LIMIT 1",
        h=_hoje(),
    )[0]
    estado["passado"] = linha
    status, itens = _busca(TERMO)
    _garante(status == 200 and itens, f"busca '{TERMO}' vazia ({status})")
    dias = [_dia(i) for i in itens]
    _garante(dias == sorted(dias, reverse=True), "sem `futuros` a ordem deixou de ser decrescente")


def c3_so_futuros() -> None:
    status, itens = _busca(TERMO, futuros=True)
    _garante(status == 200 and itens, f"`futuros=1` vazio ({status})")
    antigos = [i["title"] for i in itens if _dia(i) < _hoje()]
    _garante(not antigos, f"evento passado com `futuros=1`: {antigos[:3]}")
    dias = [_dia(i) for i in itens]
    _garante(dias == sorted(dias), "`futuros=1` não está do mais próximo ao mais distante")
    estado["ids_futuros"] = [i["id"] for i in itens]


def c4_bate_com_banco() -> None:
    linhas = _no_banco(
        "SELECT id, start_at FROM calendar_events WHERE lower(title) LIKE :t AND start_at >= :h"
        " AND cancelled_at IS NULL ORDER BY start_at ASC",
        t=f"%{TERMO}%",
        h=_hoje(),
    )
    # O título é só uma das três portas da busca (cliente e telefone também casam): todo id do
    # banco por título, dentro do corte dos 30, tem de estar na resposta.
    corte = _no_banco(
        "SELECT start_at FROM calendar_events WHERE id = :i", i=estado["ids_futuros"][-1]
    )[0][0]
    esperados = {r[0] for r in linhas if r[1] < corte}
    faltando = esperados - set(estado["ids_futuros"])
    _garante(not faltando, f"ids do banco fora da resposta: {sorted(faltando)[:5]}")


def c5_data_passada_aparece() -> None:
    dia = _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=estado["passado"][0])[
        0
    ][0]
    status, itens = _busca(dia.strftime("%d/%m/%Y"), futuros=True)
    _garante(status == 200, f"status {status}")
    _garante(
        estado["passado"][0] in {i["id"] for i in itens},
        f"evento passado de {dia:%d/%m/%Y} sumiu da busca por data",
    )


def limpar() -> None:
    with app.app_context():
        for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
            u.roles.clear()
            db.session.delete(u)
        db.session.commit()
    sobra = _no_banco("SELECT count(*) FROM users WHERE email LIKE :p", p=f"{PREFIX}%")[0][0]
    _garante(sobra == 0, f"{sobra} usuário(s) descartável(is) sobrando")


if __name__ == "__main__":
    print("verify_336b — tag NFC só lista eventos de hoje em diante")
    try:
        preparar()
        cenario("1. sem login → 401", c1_sem_login)
        cenario("2. sem `futuros` nada muda", c2_sem_parametro_inalterado)
        cenario("3. `futuros=1` só de hoje em diante, mais próximo primeiro", c3_so_futuros)
        cenario("4. bate com o banco (conexão separada)", c4_bate_com_banco)
        cenario("5. data passada digitada ainda aparece", c5_data_passada_aparece)
    finally:
        cenario("6. limpeza", limpar)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} cenários OK")
    sys.exit(0 if ok == len(resultados) else 1)
