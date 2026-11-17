"""Verificação da 346 — o painel de Figurino da Home não lista evento que já passou.

Cenários (spec.md):
 1. Nenhum item de `figurino.pending` do GET /api/dashboard começa antes de hoje 0h (SP).
 2. Os ids e o `total` batem com o SELECT direto (conexão separada), com o corte novo.
 3. Fronteira com relógio fixo num dia D do espelho: com "agora" = D às 23h59, a vaga do evento
    de D fica (já aconteceu, mas é de hoje); a do dia anterior sai.
 4. `release_date` no futuro continua mandando: nada antes dele.
 5. O Casting não muda: vaga de evento passado continua em `casting.pending` (regra da 308).
 6. DEVE FALHAR: CASTING sem o papel FIGURINO recebe `figurino: null`.
 7. Limpeza (apaga os usuários do verify).

Só lê elenco: não semeia EventRole (o sync do Google apagaria e mandaria e-mail de remoção).
Requisições FORA do `app.app_context()`.

Rodar (PowerShell; aqui contra o espelho `manto_346`, porque o `manto_local` está parado numa
migration do CRM sem push)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\346-figurino-sem-evento-passado\\verify_346.py
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, time, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.api import dashboard_service  # noqa: E402
from app.constants import MARCADORES_COMPROMISSO_INTERNO, RoleName, now_sp  # noqa: E402
from app.models import Role, User  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

PREFIX = "__v346_"
SENHA = "verify-346-senha"

app = create_app()
app.config["TESTING"] = True
app.config["RATELIMIT_ENABLED"] = False

_engine_externo = create_engine(os.environ["DATABASE_URL"])

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}

# Mesmos filtros de `compute_figurino_tasks`, menos o compromisso interno (filtrado em Python, como
# na 308) e com o corte como parâmetro.
_SQL_FIGURINO = """
    SELECT r.id, e.title, e.start_at, r.figurino_done_at IS NULL AS pendente
    FROM event_roles r JOIN calendar_events e ON e.id = r.event_id
    WHERE r.talent_id IS NOT NULL
      AND r.invite_status <> 'rejected' AND r.role_type <> 'extra'
      AND e.title NOT LIKE '🟧 ENSAIO%' AND e.start_at >= :corte AND e.cancelled_at IS NULL
"""


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


def _hoje_0h() -> datetime:
    return datetime.combine(now_sp().date(), time.min)


def _figurino_no_banco(corte: datetime) -> tuple[set[int], int]:
    """(ids pendentes, total) direto do banco, sem o compromisso interno."""
    linhas = [ln for ln in _no_banco(_SQL_FIGURINO, corte=corte) if not _interno(ln.title)]
    return {ln.id for ln in linhas if ln.pendente}, len(linhas)


def _cliente(papel: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": estado[papel], "password": SENHA})
    _garante(r.status_code == 200, f"login {papel} → {r.status_code}")
    return c


def _dashboard(papel: str) -> dict:
    r = _cliente(papel).get("/api/dashboard")
    _garante(r.status_code == 200, f"dashboard {papel} → {r.status_code}")
    return r.get_json()


def _figurino_com_relogio(agora: datetime, cutoff: datetime) -> set[int]:
    """Roda o núcleo com o "agora" de São Paulo fixado (o painel lê `now_sp` do próprio módulo)."""
    original = dashboard_service.now_sp
    dashboard_service.now_sp = lambda: agora
    try:
        with app.app_context():
            return {r.id for r in dashboard_service.compute_figurino_tasks(cutoff)["pending"]}
    finally:
        dashboard_service.now_sp = original


# ── preparo e limpeza ───────────────────────────────────────────────────────────────────────────
def _usuario(apelido: str, papel: str) -> str:
    email = f"{PREFIX}{apelido}@manto.local"
    user = User(name=f"{PREFIX}{apelido}", email=email, is_active=True, has_access=True)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(user)
    return email


def preparar() -> None:
    with app.app_context():
        limpar()
        estado["superadmin"] = _usuario("superadmin", RoleName.SUPERADMIN)
        estado["casting"] = _usuario("casting", RoleName.CASTING)
        db.session.commit()
        estado["release"] = dashboard_service.dashboard_cutoff()
    estado["corte"] = max(estado["release"], _hoje_0h())
    # Pendências antigas, pelo corte de antes (release_date): é o que aparecia no print.
    antigas = [
        ln
        for ln in _no_banco(_SQL_FIGURINO, corte=estado["release"])
        if ln.pendente and not _interno(ln.title)
    ]
    passadas = [ln for ln in antigas if ln.start_at < _hoje_0h()]
    print(
        f"  (release_date {estado['release']:%d/%m/%Y}; {len(antigas)} pendentes pelo corte antigo, "
        f"{len(passadas)} de evento que já passou)"
    )
    _garante(passadas, "o espelho não tem figurino pendente de evento passado — nada a provar")
    # Dia D da fronteira: o mais recente com pendência que tenha outro dia pendente antes dele.
    dias = sorted({ln.start_at.date() for ln in passadas})
    _garante(len(dias) >= 2, "o espelho precisa de dois dias passados com figurino pendente")
    estado["dia_d"], estado["dia_antes"] = dias[-1], dias[-2]
    estado["vagas_d"] = {ln.id for ln in passadas if ln.start_at.date() == estado["dia_d"]}
    estado["vagas_antes"] = {ln.id for ln in passadas if ln.start_at.date() == estado["dia_antes"]}


def limpar() -> None:
    db.session.rollback()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ── cenários ────────────────────────────────────────────────────────────────────────────────────
def cen_01_sem_passado_na_api() -> None:
    pendentes = _dashboard("superadmin")["figurino"]["pending"]
    hoje = _hoje_0h()
    velhos = [t for t in pendentes if datetime.fromisoformat(t["start_at"]) < hoje]
    _garante(not velhos, f"{len(velhos)} de evento passado, ex.: {velhos[:2]}")


def cen_02_bate_com_o_banco() -> None:
    figurino = _dashboard("superadmin")["figurino"]
    ids_api = {t["role_id"] for t in figurino["pending"]}
    ids_banco, total = _figurino_no_banco(estado["corte"])
    _garante(
        ids_api == ids_banco,
        f"api−banco {sorted(ids_api - ids_banco)[:5]}, banco−api {sorted(ids_banco - ids_api)[:5]}",
    )
    _garante(figurino["total"] == total, f"total {figurino['total']} ≠ banco {total}")
    _garante(figurino["done"] == total - len(ids_banco), f"done {figurino['done']} não fecha")
    print(f"         ({len(ids_api)} pendentes de hoje em diante; total {total})")


def cen_03_fronteira_do_dia() -> None:
    d = estado["dia_d"]
    agora = datetime.combine(d, time(23, 59))
    pendentes = _figurino_com_relogio(agora, estado["release"])
    faltam = estado["vagas_d"] - pendentes
    _garante(not faltam, f"vaga(s) do próprio dia {d:%d/%m} sumiram: {sorted(faltam)[:5]}")
    sobram = estado["vagas_antes"] & pendentes
    _garante(
        not sobram, f"vaga(s) de {estado['dia_antes']:%d/%m} ainda pendentes: {sorted(sobram)[:5]}"
    )


def cen_04_release_futuro_manda() -> None:
    futuro = _hoje_0h() + timedelta(days=30)
    with app.app_context():
        pendentes = dashboard_service.compute_figurino_tasks(futuro)["pending"]
        cedo = [r.id for r in pendentes if r.event.start_at < futuro]
    _garante(not cedo, f"{len(cedo)} antes do release_date futuro, ex.: {cedo[:5]}")


def cen_05_casting_nao_muda() -> None:
    pendentes = _dashboard("superadmin")["casting"]["pending"]
    hoje = _hoje_0h()
    passadas = [
        t for t in pendentes if t["start_at"] and datetime.fromisoformat(t["start_at"]) < hoje
    ]
    _garante(passadas, "o casting perdeu as vagas de evento passado (a 308 as mantém de propósito)")


def cen_06_casting_sem_figurino() -> None:
    dados = _dashboard("casting")
    _garante(dados.get("figurino") is None, "CASTING recebeu o painel de figurino")


def cen_07_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "sobrou usuário")


def main() -> int:
    print("346 — painel de Figurino da Home sem evento passado")
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "e-mail não está suprimido")
    preparar()
    try:
        cenario("1. figurino.pending sem evento antes de hoje 0h", cen_01_sem_passado_na_api)
        cenario("2. ids, total e done batem com o banco", cen_02_bate_com_o_banco)
        cenario("3. fronteira: o dia D fica, o anterior sai", cen_03_fronteira_do_dia)
        cenario("4. release_date futuro continua mandando", cen_04_release_futuro_manda)
        cenario("5. casting mantém vaga de evento passado", cen_05_casting_nao_muda)
        cenario("6. DEVE FALHAR: CASTING sem painel de figurino", cen_06_casting_sem_figurino)
    finally:
        cenario("7. limpeza", cen_07_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
