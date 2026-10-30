"""Verificação do hotfix 239c — o coordenador escolhido na criação vale também com orçamento.

Cenários (spec §Verificação):
 1. Criação do orçamento (1 coordenador) com coordenador escolhido: a vaga do orçamento recebe o
    talento, mantém o teto e leva "escalado pelo comercial".          (DEVE falhar no código antigo)
 2. O escolhido recebe o convite (como a pré-escala de personagem).    (DEVE falhar no código antigo)
 3. Orçamento com 2 coordenadores: o escolhido ocupa a primeira vaga; a segunda fica aberta, com teto.
 4. Orçamento sem coordenador escolhido: a vaga nasce aberta, com teto (regressão).
 5. Sem orçamento, com coordenador escolhido: 1 vaga, com o talento, sem a marca do sistema (regressão 322).
 6. Coordenador igual ao talento de um personagem: não escala duas vezes; a vaga fica aberta.
 7. Limpeza.

Google DUBLADO (Agenda no-op; Maps não é chamado). E-mail: `MAIL_SUPPRESS_SEND` conferido no início
(a pré-escala dispara convite a talento real do espelho). Requisições HTTP FORA do `app_context`;
toda asserção de escrita lê por conexão separada.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    .venv\\Scripts\\python.exe specs\\239c-coordenador-pre-escalado-com-orcamento\\verify_239c.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter, maps  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, OrcamentoHistory, Role, Talent, User  # noqa: E402

PREFIX = "__v239c_"
SENHA = "verify-239c-senha"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês ──────────────────────────────────────────────────────────────────────────────────────
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_service.insert_event = lambda *a, **k: {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}"}
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = cal_service.insert_event


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
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


# ── preparação ──────────────────────────────────────────────────────────────────────────────────


def _usuario(sufixo: str, *papeis: str) -> int:
    user = User(
        name=f"{PREFIX}{sufixo}",
        email=f"{PREFIX}{sufixo}@manto.local",
        is_active=True,
        has_access=True,
    )
    user.set_password(SENHA)
    for p in papeis:
        user.roles.append(Role.query.filter_by(name=p).one())
    db.session.add(user)
    db.session.commit()
    return user.id


def _cliente(chave: str):
    """Cliente de teste logado pela API (fora do app_context)."""
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": f"{PREFIX}{chave}@manto.local", "password": SENHA})
    _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


def _orcamento(dono_id: int, *, coordenadores: int, data: str) -> int:
    snap = {
        "performers": [{"type": "ator", "subtipo": "cara_limpa", "nome": "Mickey"}],
        "coordenador_qty": coordenadores,
        "fora_sp": False,
        "km_ida": 0,
        "transporte_tipo": "carro",
        "num_carros": 1,
        "num_colaboradores": 1 + coordenadores,
        "event_date": data,
        "event_time": "12:00",
        "nota_fiscal": False,
        "acrescimos": [],
    }
    entry = OrcamentoHistory(
        user_id=dono_id,
        client_name=f"{PREFIX}Cliente",
        event_location=f"{PREFIX}Buffet, São Paulo",
        event_date=data,
        total_1h=Decimal("600"),
        total_2h=Decimal("650"),
        total_3h=Decimal("800"),
        total_4h=Decimal("900"),
        has_show=False,
        form_snapshot=json.dumps(snap),
    )
    db.session.add(entry)
    db.session.commit()
    return entry.id


def _corpo(
    titulo: str,
    *,
    dias: int,
    characters: list[dict],
    orc_id: int | None = None,
    coordenador: int | None = None,
) -> dict:
    d = (now_sp().date() + timedelta(days=dias)).isoformat()
    corpo = {
        "title": f"{PREFIX}{titulo}",
        "event_type": "R&I",
        "date": d,
        "start": "12:00",
        "end": "14:00",
        "location": f"{PREFIX}Buffet, São Paulo",
        "description": "",
        "needs_rehearsal": False,
        "sale_value": 650,
        "sale_value_gross": 650,
        "transport_value": 0,
        "acrescimo_value": 0,
        "with_invoice": False,
        "is_cortesia_permuta": False,
        "seller_id": estado["com"],
        "sale_date": None,
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
        "duracao": "2",
        "characters": characters,
        "orc_caches": [],
        "acrescimos": [],
        "client_pairs": [],
        "observations": [],
    }
    if orc_id is not None:
        corpo["orcamento_history_id"] = orc_id
    if coordenador is not None:
        corpo["coordinator_talent_id"] = coordenador
    return corpo


def _criar(chave: str, corpo: dict) -> int:
    c = _cliente(chave)
    r = c.post("/api/events", json=corpo)
    _garante(
        r.status_code == 201, f"POST /api/events → {r.status_code} {r.get_data(as_text=True)[:300]}"
    )
    j = r.get_json()
    return j["event"]["id"] if "event" in j else j["id"]


def _coordenadores(eid: int) -> list:
    return _no_banco(
        "SELECT id, talent_id, cache_cap, escalado_pelo_comercial, criada_pelo_sistema, invite_status "
        "FROM event_roles WHERE event_id = :i AND character_name = 'Coordenador' AND role_type = 'extra' "
        "ORDER BY id",
        i=eid,
    )


def preparar() -> None:
    with app.app_context():
        _garante(
            app.config.get("MAIL_SUPPRESS_SEND") is True,
            "MAIL_SUPPRESS_SEND desligado — convite iria a talento real",
        )
        limpar()
        estado["com"] = _usuario("com", RoleName.COMERCIAL)
        talentos = [
            t.id for t in Talent.query.filter_by(status="active").order_by(Talent.id).limit(2).all()
        ]
        _garante(len(talentos) == 2, "o espelho precisa de 2 talentos ativos")
        estado["talentos"] = talentos
        data = (now_sp().date() + timedelta(days=60)).isoformat()
        estado["orc_1"] = _orcamento(estado["com"], coordenadores=1, data=data)
        estado["orc_2"] = _orcamento(estado["com"], coordenadores=2, data=data)
        estado["orc_sem"] = _orcamento(estado["com"], coordenadores=1, data=data)
        estado["orc_mesmo"] = _orcamento(estado["com"], coordenadores=1, data=data)


def limpar() -> None:
    ids = [
        r[0]
        for r in _no_banco(
            "SELECT id FROM calendar_events WHERE title LIKE :p OR google_event_id LIKE :p",
            p=f"%{PREFIX}%",
        )
    ]
    for eid in ids:
        for tabela in ("commission_payments", "event_logs", "event_roles", "event_clients"):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        ev = CalendarEvent.query.get(eid)
        if ev is not None:
            db.session.delete(ev)
    db.session.commit()
    for orc in OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).all():
        db.session.delete(orc)
    db.session.commit()
    for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        user.roles.clear()
        db.session.delete(user)
    db.session.commit()


# ── cenários ────────────────────────────────────────────────────────────────────────────────────


def cen_01_orcamento_com_coordenador_escolhido() -> None:
    t1, _t2 = estado["talentos"]
    eid = _criar(
        "com",
        _corpo(
            "orc1",
            dias=60,
            orc_id=estado["orc_1"],
            coordenador=t1,
            characters=[{"name": "Mickey", "talent_id": None}],
        ),
    )
    estado["ev_1"] = eid
    coords = _coordenadores(eid)
    _garante(len(coords) == 1, f"{len(coords)} vagas de Coordenador: {[tuple(c) for c in coords]}")
    c = coords[0]
    _garante(c.talent_id == t1, f"coordenador escolhido descartado: talent_id={c.talent_id}")
    _garante(c.cache_cap is not None, "a vaga perdeu o teto do orçamento")
    _garante(c.escalado_pelo_comercial is True, "sem a marca de escalado pelo comercial")


def cen_02_convite_do_coordenador() -> None:
    c = _coordenadores(estado["ev_1"])[0]
    _garante(
        c.invite_status is not None,
        f"o coordenador escolhido não recebeu convite (invite_status={c.invite_status})",
    )


def cen_03_dois_coordenadores() -> None:
    t1, _t2 = estado["talentos"]
    eid = _criar(
        "com",
        _corpo(
            "orc2",
            dias=61,
            orc_id=estado["orc_2"],
            coordenador=t1,
            characters=[{"name": "Mickey", "talent_id": None}],
        ),
    )
    coords = _coordenadores(eid)
    _garante(len(coords) == 2, f"{len(coords)} vagas de Coordenador (esperado 2)")
    _garante(
        coords[0].talent_id == t1 and coords[1].talent_id is None,
        f"ocupação: {[c.talent_id for c in coords]}",
    )
    _garante(all(c.cache_cap is not None for c in coords), "alguma vaga sem teto")


def cen_04_orcamento_sem_escolha() -> None:
    eid = _criar(
        "com",
        _corpo(
            "orcsem",
            dias=62,
            orc_id=estado["orc_sem"],
            characters=[{"name": "Mickey", "talent_id": None}],
        ),
    )
    coords = _coordenadores(eid)
    _garante(
        len(coords) == 1 and coords[0].talent_id is None and coords[0].cache_cap is not None,
        f"vagas: {[tuple(c) for c in coords]}",
    )
    _garante(coords[0].escalado_pelo_comercial is None, "vaga aberta com a marca do comercial")


def cen_05_sem_orcamento() -> None:
    t1, _t2 = estado["talentos"]
    eid = _criar(
        "com",
        _corpo(
            "manual", dias=63, coordenador=t1, characters=[{"name": "Mickey", "talent_id": None}]
        ),
    )
    coords = _coordenadores(eid)
    _garante(len(coords) == 1, f"{len(coords)} vagas de Coordenador")
    c = coords[0]
    _garante(c.talent_id == t1 and c.escalado_pelo_comercial is True, f"vaga: {tuple(c)}")
    _garante(c.criada_pelo_sistema is None, "coordenador escolhido levou a marca do sistema")


def cen_06_mesmo_talento_do_personagem() -> None:
    t1, _t2 = estado["talentos"]
    eid = _criar(
        "com",
        _corpo(
            "mesmo",
            dias=64,
            orc_id=estado["orc_mesmo"],
            coordenador=t1,
            characters=[{"name": "Mickey", "talent_id": t1}],
        ),
    )
    coords = _coordenadores(eid)
    _garante(
        len(coords) == 1 and coords[0].talent_id is None, f"vagas: {[tuple(c) for c in coords]}"
    )


def cen_07_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(
            CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0,
            "evento sobrou",
        )
        _garante(
            OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).count()
            == 0,
            "orçamento sobrou",
        )
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")


def main() -> int:
    print("Hotfix 239c — coordenador escolhido na criação vale com orçamento")
    preparar()
    passos = [
        (
            "1. orçamento + coordenador escolhido: vaga ocupada, com teto e marca (DEVE falhar no antigo)",
            cen_01_orcamento_com_coordenador_escolhido,
        ),
        (
            "2. o coordenador escolhido recebe convite (DEVE falhar no antigo)",
            cen_02_convite_do_coordenador,
        ),
        (
            "3. 2 coordenadores no orçamento: o escolhido na primeira, a segunda aberta",
            cen_03_dois_coordenadores,
        ),
        ("4. orçamento sem escolha: vaga aberta com teto", cen_04_orcamento_sem_escolha),
        ("5. sem orçamento: 1 vaga com o talento, sem a marca do sistema", cen_05_sem_orcamento),
        (
            "6. coordenador = talento do personagem: não escala duas vezes",
            cen_06_mesmo_talento_do_personagem,
        ),
    ]
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("7. limpeza", cen_07_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
