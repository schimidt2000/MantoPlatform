"""Verificação da 308 — compromisso interno (🟧/🟠) fora do casting da Home; dispensar pela Home.

Cenários (spec.md):
 1. Nenhuma vaga de evento com título 🟧/🟠 (inclusive "🟧 - ENSAIO", que escapava do filtro
    antigo) aparece em `casting.pending` nem em `casting.rejected_invites` do GET /api/dashboard.
 2. Vaga de evento sem marcador continua em `casting.pending` (a regra não apaga o resto).
 3. SUPERADMIN dispensa uma vaga: some de `pending`, entra em `dismissed_casting`, `dismissed_at`
    gravado (conferido por conexão separada); restaura: volta a `pending`.
 4. DEVE FALHAR: CASTING tenta dispensar → 403 e o banco não muda.
 5. CASTING não recebe `dismissed_casting` (a lista de restaurar é só do SUPERADMIN).
 6. Limpeza (devolve `dismissed_at` original, apaga logs e usuários do verify).

Não semeia EventRole (o sync do Google apagaria e mandaria e-mail de remoção): usa vagas que já
existem no espelho com `talent_id IS NULL`. Requisições FORA do `app.app_context()`.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\308-casting-sem-compromisso-interno\\verify_308.py
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.api.dashboard_service import dashboard_cutoff  # noqa: E402
from app.constants import MARCADORES_COMPROMISSO_INTERNO, RoleName  # noqa: E402
from app.models import Role, User  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

PREFIX = "__v308_"
SENHA = "verify-308-senha"

app = create_app()
app.config["TESTING"] = True
app.config["RATELIMIT_ENABLED"] = False

_engine_externo = create_engine(os.environ["DATABASE_URL"])

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}


def _no_banco(sql: str, **params):
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _interno(titulo: str | None) -> bool:
    return (titulo or "").lstrip().startswith(MARCADORES_COMPROMISSO_INTERNO)


def _cliente(papel: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": estado[papel], "password": SENHA})
    _garante(r.status_code == 200, f"login {papel} → {r.status_code}")
    return c


def _dashboard(papel: str) -> dict:
    r = _cliente(papel).get("/api/dashboard")
    _garante(r.status_code == 200, f"dashboard {papel} → {r.status_code}")
    return r.get_json()


def _ids_pendentes(dados: dict) -> set[int]:
    return {t["role_id"] for t in dados["casting"]["pending"]}


# ── preparo e limpeza ───────────────────────────────────────────────────────────────────────────
def _usuario(apelido: str, papel: str) -> str:
    email = f"{PREFIX}{apelido}@manto.local"
    user = User(name=f"{PREFIX}{apelido}", email=email, is_active=True, has_access=True)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(user)
    return email


# Mesmos filtros da Home (dashboard_service._base_filters), menos o marcador — é o "antes".
_SQL_PENDENTES = """
    SELECT r.id, e.title FROM event_roles r JOIN calendar_events e ON e.id = r.event_id
    WHERE r.talent_id IS NULL AND r.dismissed_at IS NULL
      AND r.character_name <> :presenca
      AND e.title NOT LIKE '🟧 ENSAIO%' AND e.start_at >= :corte AND e.cancelled_at IS NULL
    ORDER BY e.start_at
"""


def preparar() -> None:
    from app.calendar.routes import PRESENCE_CHARACTER

    with app.app_context():
        limpar()
        estado["superadmin"] = _usuario("superadmin", RoleName.SUPERADMIN)
        estado["casting"] = _usuario("casting", RoleName.CASTING)
        db.session.commit()
        corte = dashboard_cutoff()
    linhas = _no_banco(_SQL_PENDENTES, presenca=PRESENCE_CHARACTER, corte=corte)
    estado["internas"] = {rid for rid, titulo in linhas if _interno(titulo)}
    estado["normais"] = [rid for rid, titulo in linhas if not _interno(titulo)]
    print(
        f"  (antes: {len(linhas)} pendentes; {len(estado['internas'])} de compromisso interno; "
        f"ficam {len(estado['normais'])})"
    )
    _garante(estado["internas"], "o espelho não tem vaga pendente em evento 🟧/🟠 — nada a provar")
    _garante(estado["normais"], "o espelho não tem vaga pendente fora do laranja")
    estado["alvo"] = estado["normais"][0]


def limpar() -> None:
    db.session.rollback()
    alvo = estado.get("alvo")
    if alvo is not None:
        # A vaga é real: volta como estava (o preparo só escolhe vaga não dispensada).
        db.session.execute(
            text("UPDATE event_roles SET dismissed_at = NULL, dismissed_by = NULL WHERE id = :id"),
            {"id": alvo},
        )
    db.session.execute(text("DELETE FROM event_logs WHERE actor_name LIKE :p"), {"p": f"{PREFIX}%"})
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ── cenários ────────────────────────────────────────────────────────────────────────────────────
def cen_01_laranja_fora() -> None:
    casting = _dashboard("superadmin")["casting"]
    vazou = [t for t in casting["pending"] if _interno(t["event_title"])]
    _garante(not vazou, f"{len(vazou)} vaga(s) laranja na Home, ex.: {vazou[:2]}")
    recusou = [t for t in casting["rejected_invites"] if _interno(t["event_title"])]
    _garante(not recusou, f"recusado laranja na Home: {recusou[:2]}")


def cen_02_resto_fica() -> None:
    pendentes = _ids_pendentes(_dashboard("superadmin"))
    faltam = set(estado["normais"]) - pendentes
    _garante(not faltam, f"{len(faltam)} vaga(s) normal(is) sumiram, ex.: {sorted(faltam)[:5]}")


def cen_03_dispensar_e_restaurar() -> None:
    alvo = estado["alvo"]
    c = _cliente("superadmin")
    r = c.post(f"/api/roles/{alvo}/dismiss")
    _garante(r.status_code == 200, f"dismiss → {r.status_code} {r.get_data(as_text=True)[:200]}")
    (gravado,) = _no_banco("SELECT dismissed_at FROM event_roles WHERE id = :id", id=alvo)[0]
    _garante(gravado is not None, "dismissed_at não chegou ao banco")
    dados = c.get("/api/dashboard").get_json()
    _garante(alvo not in _ids_pendentes(dados), "dispensada continua em pending")
    _garante(
        alvo in {t["role_id"] for t in dados["dismissed_casting"]}, "não entrou em dispensados"
    )
    r = c.post(f"/api/roles/{alvo}/restore")
    _garante(r.status_code == 200, f"restore → {r.status_code}")
    (gravado,) = _no_banco("SELECT dismissed_at FROM event_roles WHERE id = :id", id=alvo)[0]
    _garante(gravado is None, "restore não limpou dismissed_at")
    _garante(alvo in _ids_pendentes(c.get("/api/dashboard").get_json()), "não voltou a pending")


def cen_04_casting_nao_dispensa() -> None:
    alvo = estado["alvo"]
    r = _cliente("casting").post(f"/api/roles/{alvo}/dismiss")
    _garante(r.status_code == 403, f"CASTING dispensou: {r.status_code}")
    (gravado,) = _no_banco("SELECT dismissed_at FROM event_roles WHERE id = :id", id=alvo)[0]
    _garante(gravado is None, "o 403 gravou dismissed_at mesmo assim")


def cen_05_casting_sem_lista_de_dispensados() -> None:
    dados = _dashboard("casting")
    _garante(dados["dismissed_casting"] == [], "CASTING recebeu a lista de dispensados")


def cen_06_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "sobrou usuário")
    (gravado,) = _no_banco(
        "SELECT dismissed_at FROM event_roles WHERE id = :id", id=estado["alvo"]
    )[0]
    _garante(gravado is None, "a vaga real ficou dispensada")


def main() -> int:
    print("308 — compromisso interno fora do casting da Home; dispensar pela Home")
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "e-mail não está suprimido")
    preparar()
    try:
        cenario("1. vaga de evento 🟧/🟠 fora de pending e recusados", cen_01_laranja_fora)
        cenario("2. vaga de evento sem marcador continua em pending", cen_02_resto_fica)
        cenario("3. SUPERADMIN dispensa e restaura", cen_03_dispensar_e_restaurar)
        cenario("4. DEVE FALHAR: CASTING dispensa → 403", cen_04_casting_nao_dispensa)
        cenario("5. CASTING não recebe dispensados", cen_05_casting_sem_lista_de_dispensados)
    finally:
        cenario("6. limpeza", cen_06_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
