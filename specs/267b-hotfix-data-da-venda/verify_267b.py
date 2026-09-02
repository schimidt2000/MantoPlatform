"""Verificação do hotfix 267b — venda sem "Data da venda" não pode sumir da Planilha de Pagamentos.

Cenários (spec.md):
 1. POST /api/events com venda e sem sale_date → sale_date = hoje (SP); comissão nasce com a mesma
    data e aparece no item da Planilha do mês seguinte.
 2. POST sem venda → sale_date NULL.
 3. PATCH /events/<id>/comercial que REGISTRA a venda (antes não havia) sem data → hoje.
 4. Legado: venda com data NULL + PATCH sem data → continua NULL (não inventa data velha).
 5. PATCH com data explícita → a informada; venda com data + PATCH sem data → mantém.
 6. Comissão legada sem sale_date cai no ciclo do mês do created_at (planilha) e é liquidada pela
    mesma expressão.
 7. Backfill: dry-run não escreve; --execute preenche evento e comissão pela fonte certa.
 8. Limpeza.

O Google Agenda é DUBLADO: `insert_event`/`update_event`/`delete_event` de `app.calendar.service` e o
`insert_event` reexportado em `app.calendar.routes` são substituídos antes de qualquer cenário —
nada chega à agenda real. Ids gerados aqui têm o prefixo `__v267b_`.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\267b-hotfix-data-da-venda\\verify_267b.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.financeiro import comissoes_ops  # noqa: E402
from app.financeiro.routes import _build_commission_items  # noqa: E402
from app.models import CalendarEvent, EventLog, Role, User  # noqa: E402

PREFIX = "__v267b_"
SENHA = "verify-267b-senha"

app = create_app()
app.config["TESTING"] = True

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


# ── dublê do Google ─────────────────────────────────────────────────────────────────────────────
def _fake_insert(*_a, **_k):
    return {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}", "htmlLink": "https://fake.local"}


def _fake_noop(*_a, **_k):
    return None


cal_service.insert_event = _fake_insert
cal_service.update_event = _fake_noop
cal_service.delete_event = _fake_noop
cal_routes.insert_event = _fake_insert
if hasattr(cal_routes, "update_event"):
    cal_routes.update_event = _fake_noop
if hasattr(cal_routes, "delete_event"):
    cal_routes.delete_event = _fake_noop


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _login(c, user: User) -> None:
    r = c.post("/api/auth/login", json={"email": user.email, "password": SENHA})
    _garante(r.status_code == 200, f"login → {r.status_code}")


def _payload_evento(sufixo: str, *, venda: float | None, sale_date: str | None = None, dias: int = 45) -> dict:
    d = (now_sp().date() + timedelta(days=dias)).isoformat()
    return {
        "title": f"{PREFIX}{sufixo}",
        "event_type": "R&I",
        "date": d,
        "start": "15:00",
        "end": "17:00",
        "location": "",
        "description": "",
        "needs_rehearsal": False,
        "sale_value": venda,
        "sale_value_gross": venda,
        "transport_value": 0,
        "acrescimo_value": 0,
        "with_invoice": False,
        "is_cortesia_permuta": False,
        "seller_id": estado["vendedora"].id,
        "sale_date": sale_date,
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
        "orcamento_history_id": None,
        "duracao": "1",
        "characters": [],
        "orc_caches": [],
        "acrescimos": [],
        "client_pairs": [],
        "observations": [],
    }


def _evento_no_banco(eid: int):
    return _no_banco("SELECT sale_value, sale_date FROM calendar_events WHERE id = :i", i=eid)[0]


def _comissao_viva(eid: int):
    rows = _no_banco(
        "SELECT id, sale_date, status, amount, created_at FROM commission_payments "
        "WHERE event_id = :i AND status <> 'cancelado' ORDER BY id", i=eid)
    return rows[0] if rows else None


def preparar() -> None:
    limpar()
    email = f"{PREFIX}sa@manto.local"
    user = User(name=f"{PREFIX}sa", email=email, is_active=True, has_access=True, receives_commission=True)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=RoleName.SUPERADMIN).one())
    db.session.add(user)
    db.session.commit()
    estado["superadmin"] = user
    estado["vendedora"] = user  # SUPERADMIN pode ser vendedor; recebe comissão
    estado["hoje"] = now_sp().date()


def limpar() -> None:
    ids = [r[0] for r in _no_banco("SELECT id FROM calendar_events WHERE title LIKE :p OR google_event_id LIKE :p", p=f"%{PREFIX}%")]
    for eid in ids:
        db.session.execute(text("DELETE FROM commission_payments WHERE event_id = :i"), {"i": eid})
        db.session.execute(text("DELETE FROM event_logs WHERE event_id = :i"), {"i": eid})
        db.session.execute(text("DELETE FROM event_roles WHERE event_id = :i"), {"i": eid})
        db.session.execute(text("DELETE FROM event_clients WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        ev = CalendarEvent.query.get(eid)
        if ev is not None:
            db.session.delete(ev)
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ───────────────────────────── cenários ─────────────────────────────

def cen_01_criacao_sem_data_ganha_hoje() -> None:
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        r = c.post("/api/events", json=_payload_evento("venda sem data", venda=4000))
        _garante(r.status_code == 201, f"POST → {r.status_code} {r.get_data(as_text=True)[:200]}")
        eid = r.get_json()["event"]["id"] if "event" in r.get_json() else r.get_json()["id"]
    estado["ev1"] = eid
    venda, sd = _evento_no_banco(eid)
    _garante(sd == estado["hoje"], f"sale_date {sd}, esperava hoje {estado['hoje']}")
    cp = _comissao_viva(eid)
    _garante(cp is not None and cp.sale_date == estado["hoje"], f"comissão sem a data de hoje: {cp}")
    # Item da Planilha do mês seguinte (ciclo = mês da venda), sem `vencer` de ninguém.
    ini = estado["hoje"].replace(day=1)
    fim = (ini + timedelta(days=32)).replace(day=1)
    itens = _build_commission_items(ini, fim, fim.replace(day=5), estado["hoje"])
    meu = [i for i in itens if i["id"].startswith(f"{estado['vendedora'].id}:")]
    _garante(meu and Decimal(str(meu[0]["amount"])) >= cp.amount, f"item da planilha não traz a comissão: {meu}")


def cen_02_criacao_sem_venda_sem_data() -> None:
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        # A validação exige venda > 0; o único jeito de nascer sem venda pela API é cortesia/permuta
        # (o servidor zera a venda) — que é exatamente o caso "sem venda, sem data".
        corpo = _payload_evento("cortesia", venda=1, dias=46)
        corpo["is_cortesia_permuta"] = True
        r = c.post("/api/events", json=corpo)
        _garante(r.status_code == 201, f"POST → {r.status_code}")
        eid = r.get_json()["event"]["id"] if "event" in r.get_json() else r.get_json()["id"]
    estado["ev2"] = eid
    venda, sd = _evento_no_banco(eid)
    _garante(sd is None, f"sem venda ganhou data {sd}")


def cen_03_patch_registra_venda_sem_data() -> None:
    eid = estado["ev2"]
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        r = c.patch(f"/api/events/{eid}/comercial", json={"sale_value": 2500, "sale_value_gross": 2500, "seller_id": estado["vendedora"].id})
        _garante(r.status_code == 200, f"PATCH comercial → {r.status_code} {r.get_data(as_text=True)[:200]}")
    venda, sd = _evento_no_banco(eid)
    _garante(float(venda) == 2500 and sd == estado["hoje"], f"venda nova sem data: {venda} / {sd}")
    cp = _comissao_viva(eid)
    _garante(cp is not None and cp.sale_date == estado["hoje"], f"comissão: {cp}")


def cen_04_legado_nulo_continua_nulo() -> None:
    inicio = datetime.combine(now_sp().date() + timedelta(days=50), datetime.min.time()).replace(hour=15)
    ev = CalendarEvent(
        title=f"{PREFIX}(R&I) LEGADO", start_at=inicio, end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}legado", source="platform", sale_value=Decimal("3000"),
        sale_date=None, seller_id=estado["vendedora"].id,
    )
    db.session.add(ev)
    db.session.commit()
    estado["ev_legado"] = ev.id
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        r = c.patch(f"/api/events/{ev.id}/comercial", json={"sale_value": 3000, "sale_value_gross": 3000, "seller_id": estado["vendedora"].id})
        _garante(r.status_code == 200, f"PATCH → {r.status_code}")
    venda, sd = _evento_no_banco(ev.id)
    _garante(sd is None, f"editar venda antiga sem data inventou {sd}")


def cen_05_data_informada_e_mantida() -> None:
    eid = estado["ev1"]
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        r = c.patch(f"/api/events/{eid}/comercial", json={"sale_value": 4000, "sale_value_gross": 4000, "seller_id": estado["vendedora"].id, "sale_date": "2026-08-20"})
        _garante(r.status_code == 200, f"PATCH com data → {r.status_code}")
        _garante(_evento_no_banco(eid)[1] == date(2026, 8, 20), "data informada não valeu")
        r = c.patch(f"/api/events/{eid}/comercial", json={"sale_value": 4100, "sale_value_gross": 4100, "seller_id": estado["vendedora"].id})
        _garante(r.status_code == 200, f"PATCH sem data → {r.status_code}")
        _garante(_evento_no_banco(eid)[1] == date(2026, 8, 20), "editar sem data apagou a data existente")
    cp = _comissao_viva(eid)
    _garante(cp.sale_date == date(2026, 8, 20), f"comissão não acompanhou a data: {cp}")


def cen_06_legado_cai_no_ciclo_do_created_at() -> None:
    eid = estado["ev_legado"]
    # A comissão do legado (cenário 4) nasceu sem sale_date — como as 38 da produção.
    cp = _comissao_viva(eid)
    _garante(cp is not None and cp.sale_date is None, f"esperava comissão sem data: {cp}")
    criada = cp.created_at.date()
    ini = criada.replace(day=1)
    fim = (ini + timedelta(days=32)).replace(day=1)
    itens = _build_commission_items(ini, fim, fim.replace(day=5), estado["hoje"])
    meu = [i for i in itens if i["id"].startswith(f"{estado['vendedora'].id}:")]
    _garante(bool(meu), "comissão sem data caiu fora da planilha (o fallback por created_at não valeu)")
    tocadas = comissoes_ops.liquidar_periodo(estado["vendedora"].id, ini, fim, "no_banco")
    _garante(any(c.id == cp.id for c in tocadas), "liquidar_periodo não alcançou a comissão sem data")
    db.session.rollback()


def cen_07_backfill() -> None:
    script = REPO_ROOT / "specs" / "267b-hotfix-data-da-venda" / "backfill_data_da_venda.py"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    eid = estado["ev_legado"]
    antes = _evento_no_banco(eid)[1]
    saida = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, env=env, cwd=REPO_ROOT, encoding="utf-8")
    _garante(saida.returncode == 0, f"dry-run falhou: {saida.stderr[-400:]}")
    _garante("DRY-RUN" in saida.stdout and "Nada gravado" in saida.stdout, "dry-run não se declarou")
    _garante(_evento_no_banco(eid)[1] == antes, "dry-run gravou")
    # Fonte esperada para o legado: a linha de comissão (criada hoje) → hoje.
    saida = subprocess.run([sys.executable, str(script), "--execute"], capture_output=True, text=True, env=env, cwd=REPO_ROOT, encoding="utf-8")
    _garante(saida.returncode == 0, f"execute falhou: {saida.stderr[-400:]}")
    _garante(_evento_no_banco(eid)[1] == estado["hoje"], f"backfill não preencheu pelo created_at da comissão: {_evento_no_banco(eid)}")
    cp = _comissao_viva(eid)
    _garante(cp.sale_date == estado["hoje"], f"comissão não recebeu a data: {cp}")
    # Segundo legado SEM comissão mas com log de venda → data do log.
    inicio = datetime.combine(now_sp().date() + timedelta(days=52), datetime.min.time()).replace(hour=15)
    ev = CalendarEvent(
        title=f"{PREFIX}(R&I) LEGADO LOG", start_at=inicio, end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}legadolog", source="google_calendar", sale_value=Decimal("1800"), sale_date=None,
    )
    db.session.add(ev)
    db.session.flush()
    db.session.add(EventLog(event_id=ev.id, actor_name="verify", message="Atualizou dados comerciais: venda R$ 1800.00",
                            created_at=datetime(2026, 7, 2, 18, 47)))  # UTC → 02/07 15:47 SP
    db.session.commit()
    estado["ev_log"] = ev.id
    saida = subprocess.run([sys.executable, str(script), "--execute"], capture_output=True, text=True, env=env, cwd=REPO_ROOT, encoding="utf-8")
    _garante(saida.returncode == 0, f"execute 2 falhou: {saida.stderr[-400:]}")
    _garante(_evento_no_banco(ev.id)[1] == date(2026, 7, 2), f"fonte 'log da venda' não valeu: {_evento_no_banco(ev.id)}")
    print(f"         ({saida.stdout.strip().splitlines()[-1]})")


def cen_08_limpeza() -> None:
    limpar()
    _garante(CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0, "evento sobrou")
    _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")


def main() -> int:
    print("Hotfix 267b — data da venda e ciclo da comissão")
    with app.app_context():
        preparar()
        try:
            cenario("1. criação com venda e sem data → hoje (evento, comissão e planilha)", cen_01_criacao_sem_data_ganha_hoje)
            cenario("2. criação como cortesia (venda zerada) → sem data", cen_02_criacao_sem_venda_sem_data)
            cenario("3. PATCH que registra a venda sem data → hoje", cen_03_patch_registra_venda_sem_data)
            cenario("4. legado sem data + PATCH sem data → continua sem data", cen_04_legado_nulo_continua_nulo)
            cenario("5. data informada vale; editar sem data mantém a existente", cen_05_data_informada_e_mantida)
            cenario("6. comissão sem data cai no ciclo do created_at e é liquidável", cen_06_legado_cai_no_ciclo_do_created_at)
            cenario("7. backfill: dry-run não grava; execute preenche pela fonte certa", cen_07_backfill)
        finally:
            cenario("8. limpeza", cen_08_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
