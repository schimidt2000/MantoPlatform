"""Verificação da feature 339 — mudança no evento avisa o Casting, e o teto do cachê acompanha.

Cenários = tabela "Verificação" da spec (numeração dela). Dois DEVEM falhar como recusa: 12 ("Ciente"
no aviso de outra pessoa → 404) e 21 (Casting não grava teto autorizado).

Dublês: Google Agenda (`service.update_event/insert_event/delete_event` gravam as chamadas num
`GoogleFalso`; um modo "recusa" levanta erro), Maps (no-op), e-mail (`MAIL_SUPPRESS_SEND` conferido no
início, espião de `send_removal_email`, espião do e-mail do Ensaio). Eventos descartáveis marcados pelo
`google_event_id` com o prefixo — o título fica limpo, porque é dele que o sistema conta personagens.
Requisições HTTP FORA do `app_context`; escrita conferida por conexão separada.

Rodar (PowerShell, a partir do worktree)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\339-evento-mudou-avisa-casting\\verify_339.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
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

from app import create_app, db, email_service, limiter, maps  # noqa: E402
from app.calendar import casting_ops, event_ops, teto_ops, titulo_ops  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, EventRole, OrcamentoHistory, Role, Talent, User  # noqa: E402
from app.notificacoes import notificacoes_ops as nops  # noqa: E402

PREFIX = "__v339_"
SENHA = "verify-339-senha"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(
    os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql+psycopg://"),
    future=True,
)


# ── dublês ──────────────────────────────────────────────────────────────────────────────────────


class GoogleFalso:
    """Agenda de mentira: grava cada `update_event` e, no modo recusa, levanta como o Google fora."""

    def __init__(self) -> None:
        self.updates: list[tuple[str, str]] = []
        self.recusar = False

    def update_event(self, _cal, google_id, title, *_a, **_k):
        if self.recusar:
            raise RuntimeError("Google recusou (dublê)")
        self.updates.append((google_id, title))
        return {}


google = GoogleFalso()
cal_service.update_event = google.update_event
cal_service.insert_event = lambda *a, **k: {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}"}
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = cal_service.insert_event
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_routes._lookup_sp_status = lambda _loc: False
cal_routes._mark_talents_worked = lambda: None

remocoes: list[str] = []
emails_do_ensaio: list[int] = []


def _espiao_remocao(_talent, _event, nome, *_a, **_k):
    remocoes.append(nome)
    return True


email_service.send_removal_email = _espiao_remocao
casting_ops.send_removal_email = _espiao_remocao
event_ops.notify_ensaio_team = lambda ev: emails_do_ensaio.append(ev.id)


# ── utilitários ─────────────────────────────────────────────────────────────────────────────────


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — o relatório precisa de todos os cenários
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _email(chave: str) -> str:
    return f"{PREFIX}{chave}@manto.local"


def _usuario(chave: str, *papeis: str) -> int:
    user = User(name=f"{PREFIX}{chave}", email=_email(chave), is_active=True, has_access=True)
    user.set_password(SENHA)
    for p in papeis:
        user.roles.append(Role.query.filter_by(name=p).one())
    db.session.add(user)
    db.session.commit()
    return user.id


def _cliente(chave: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": _email(chave), "password": SENHA})
    _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


def _orcamento(performers: list[dict], *, has_show: bool) -> int:
    data = (now_sp().date() + timedelta(days=30)).isoformat()
    snap = {
        "performers": performers,
        "coordenador_qty": 1,
        "fora_sp": False,
        "km_ida": 0,
        "transporte_tipo": "carro",
        "num_carros": 1,
        "num_colaboradores": len(performers) + 1,
        "event_date": data,
        "event_time": "15:00",
        "nota_fiscal": True,
        "acrescimos": [],
    }
    entry = OrcamentoHistory(
        user_id=estado["sa"],
        client_name=f"{PREFIX}Cliente",
        event_location="Rua Teste 1, São Paulo",
        event_date=data,
        total_1h=Decimal("3000"),
        total_2h=Decimal("4200"),
        total_3h=Decimal("5000"),
        total_4h=Decimal("5600"),
        has_show=has_show,
        form_snapshot=json.dumps(snap),
    )
    db.session.add(entry)
    db.session.commit()
    return entry.id


def _tetos(orc_id: int, *, show: bool | None) -> dict[str, Decimal]:
    """Teto de 3h por rótulo, pela MESMA conta da criação (com o show trocado quando pedido)."""
    entry = OrcamentoHistory.query.get(orc_id)
    from app.calendar.orcamento_evento_ops import snapshot_do_orcamento

    snap = (
        teto_ops._snapshot_com_show(entry, show)
        if show is not None
        else snapshot_do_orcamento(entry)
    )
    dia = (now_sp().date() + timedelta(days=30)).isoformat()
    tetos: dict[str, Decimal] = {}
    for item in cal_routes._compute_performer_caches(snap, horas_extra=None, data_evento=dia):
        tetos.setdefault(item["label"].strip(), Decimal(str(item["cache_3h"])))
    return tetos


def _evento(
    titulo: str,
    vagas: list[tuple[str, int | None]],
    *,
    orc_id: int | None = None,
    tipo: str = "R&I",
    fonte: str = "platform",
    dias: int = 30,
    tetos: dict[str, Decimal] | None = None,
    coordenador: bool = False,
) -> int:
    inicio = datetime.combine(now_sp().date() + timedelta(days=dias), datetime.min.time()).replace(
        hour=15
    )
    ev = CalendarEvent(
        title=titulo,
        event_type=tipo,
        start_at=inicio,
        end_at=inicio + timedelta(hours=3),
        google_event_id=f"{PREFIX}{uuid.uuid4().hex[:10]}",
        source=fonte,
        location="Rua Teste 1, São Paulo",
        is_outside_sp=False,
        orcamento_history_id=orc_id,
        sale_value=Decimal("1000"),
        sale_value_gross=Decimal("1000"),
        seller_id=estado["com"],
    )
    db.session.add(ev)
    db.session.flush()
    for nome, talent_id in vagas:
        db.session.add(
            EventRole(
                event_id=ev.id,
                character_name=nome,
                talent_id=talent_id,
                cache_cap=(tetos or {}).get(nome),
                assigned_at=now_sp() if talent_id else None,
                invite_status="pending" if talent_id else None,
            )
        )
    if coordenador:
        db.session.add(
            EventRole(
                event_id=ev.id,
                character_name="Coordenador",
                role_type="extra",
                cache_cap=(tetos or {}).get("Coordenador"),
            )
        )
    db.session.commit()
    return ev.id


def _ensaio(pai_id: int, *, dias: int) -> int:
    pai = CalendarEvent.query.get(pai_id)
    inicio = datetime.combine(now_sp().date() + timedelta(days=dias), datetime.min.time()).replace(
        hour=9
    )
    en = CalendarEvent(
        title=f"{event_ops.ENSAIO_TITLE_PREFIX}{pai.title}",
        event_type="ENSAIO",
        start_at=inicio,
        end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}{uuid.uuid4().hex[:10]}",
        parent_event_id=pai_id,
        location="Manto",
        is_outside_sp=False,
    )
    db.session.add(en)
    db.session.commit()
    return en.id


def _vagas(eid: int) -> list:
    return _no_banco(
        "SELECT id, character_name, role_type, talent_id, cache_value, cache_cap, teto_autorizado, "
        "teto_autorizado_por, teto_autorizado_em, sobrando_desde FROM event_roles WHERE event_id = :i ORDER BY id",
        i=eid,
    )


def _vaga(eid: int, nome: str):
    achadas = [v for v in _vagas(eid) if v.character_name == nome]
    _garante(
        len(achadas) == 1,
        f"vaga {nome!r}: {len(achadas)} — {[v.character_name for v in _vagas(eid)]}",
    )
    return achadas[0]


def _titulo(eid: int) -> str:
    return _no_banco("SELECT title FROM calendar_events WHERE id = :i", i=eid)[0][0]


def _logs(eid: int) -> list[str]:
    return [
        r[0]
        for r in _no_banco("SELECT message FROM event_logs WHERE event_id = :i ORDER BY id", i=eid)
    ]


def _avisos(eid: int, kind: str) -> list:
    return _no_banco(
        "SELECT id, user_id, dedupe_key, read_at, ciente_em FROM notifications "
        "WHERE entity_type = 'calendar_event' AND entity_id = :i AND kind = :k ORDER BY id",
        i=eid,
        k=kind,
    )


def _assign(chave: str, role_id: int, talent_id: int | None, cache) -> dict:
    r = _cliente(chave).post(
        f"/api/roles/{role_id}/assign", json={"talent_id": talent_id, "cache_value": cache}
    )
    _garante(
        r.status_code == 200, f"assign ({chave}) → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    return r.get_json()


def _basico(chave: str, eid: int, *, titulo: str | None = None, tipo: str | None = None) -> dict:
    with app.app_context():
        ev = CalendarEvent.query.get(eid)
        corpo = {
            "title": titulo if titulo is not None else ev.title,
            "event_type": tipo if tipo is not None else ev.event_type,
            "date": ev.start_at.date().isoformat(),
            "start": ev.start_at.strftime("%H:%M"),
            "end": ev.end_at.strftime("%H:%M"),
            "location": ev.location,
            "description": "",
        }
    r = _cliente(chave).patch(f"/api/events/{eid}/basico", json=corpo)
    _garante(
        r.status_code == 200,
        f"PATCH basico ({chave}) → {r.status_code} {r.get_data(as_text=True)[:300]}",
    )
    return r.get_json()


def _detalhe(chave: str, eid: int) -> dict:
    r = _cliente(chave).get(f"/api/events/{eid}")
    _garante(r.status_code == 200, f"GET evento ({chave}) → {r.status_code}")
    return r.get_json()


def _cap_efetivo(eid: int, nome: str) -> Decimal:
    elenco = {r["character_name"]: r for r in _detalhe("sa", eid)["elenco"]}
    return Decimal(str(elenco[nome]["cache_cap_efetivo"]))


# ── preparação e limpeza ────────────────────────────────────────────────────────────────────────


def preparar() -> None:
    with app.app_context():
        _garante(
            app.config.get("MAIL_SUPPRESS_SEND") is True,
            "MAIL_SUPPRESS_SEND desligado — e-mail iria a gente real",
        )
        limpar()
        estado["sa"] = _usuario("sa", RoleName.SUPERADMIN)
        estado["com"] = _usuario("com", RoleName.COMERCIAL)
        estado["com2"] = _usuario("com2", RoleName.COMERCIAL)
        estado["castA"] = _usuario("castA", RoleName.CASTING)
        estado["castB"] = _usuario("castB", RoleName.CASTING)
        estado["ens"] = _usuario("ens", RoleName.ENSAIO)
        talentos = [
            t.id for t in Talent.query.filter_by(status="active").order_by(Talent.id).limit(4).all()
        ]
        _garante(len(talentos) == 4, "o espelho precisa de 4 talentos ativos")
        estado["t"] = talentos
        estado["orc_ri"] = _orcamento(
            [
                {"type": "ator", "subtipo": "boneco", "nome": "Stormtroopers", "show": False},
                {"type": "ator", "subtipo": "boneco", "nome": "Darth Vader", "show": False},
                {"type": "ator", "subtipo": "cara_limpa", "nome": "Luke", "show": False},
            ],
            has_show=False,
        )
        estado["orc_show"] = _orcamento(
            [
                {"type": "ator", "subtipo": "boneco", "nome": "Stormtroopers", "show": True},
                {"type": "ator", "subtipo": "boneco", "nome": "Darth Vader", "show": True},
                {"type": "ator", "subtipo": "cantor", "nome": "Luke", "show": True},
            ],
            has_show=True,
        )
        estado["tetos_ri"] = _tetos(estado["orc_ri"], show=None)
        estado["tetos_show"] = _tetos(estado["orc_ri"], show=True)
        estado["tetos_orc_show"] = _tetos(estado["orc_show"], show=None)
        estado["ev_teto"] = _evento(
            "(R&I) STORMTROOPERS + DARTH VADER + LUKE",
            [("Stormtroopers", None), ("Darth Vader", None), ("Luke", None)],
            orc_id=estado["orc_ri"],
            tetos=estado["tetos_ri"],
            coordenador=True,
        )


def limpar() -> None:
    ids = [
        r[0]
        for r in _no_banco(
            "SELECT id FROM calendar_events WHERE google_event_id LIKE :p ORDER BY parent_event_id NULLS LAST",
            p=f"{PREFIX}%",
        )
    ]
    for eid in ids:
        db.session.execute(
            text(
                "DELETE FROM notifications WHERE entity_type = 'calendar_event' AND entity_id = :i"
            ),
            {"i": eid},
        )
        for tabela in ("commission_payments", "event_logs", "event_roles", "event_clients"):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        db.session.execute(
            text("DELETE FROM calendar_events WHERE parent_event_id = :i"), {"i": eid}
        )
        db.session.execute(text("DELETE FROM calendar_events WHERE id = :i"), {"i": eid})
    db.session.commit()
    for o in OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).all():
        db.session.delete(o)
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        db.session.execute(text("DELETE FROM notifications WHERE user_id = :u"), {"u": u.id})
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ── História 1 — teto autorizado na vaga ────────────────────────────────────────────────────────


def cen_01() -> None:
    eid, luke = estado["ev_teto"], _vaga(estado["ev_teto"], "Luke")
    estado["autorizado"] = Decimal(luke.cache_cap) + 75
    _assign("sa", luke.id, estado["t"][0], float(estado["autorizado"]))
    v = _vaga(eid, "Luke")
    _garante(
        v.teto_autorizado == estado["autorizado"],
        f"teto autorizado {v.teto_autorizado} ≠ {estado['autorizado']}",
    )
    _garante(
        v.teto_autorizado_por == estado["sa"] and v.teto_autorizado_em is not None,
        "autor/data não gravados",
    )


def cen_02() -> None:
    eid, luke = estado["ev_teto"], _vaga(estado["ev_teto"], "Luke")
    _assign("castA", luke.id, None, 0)
    _garante(
        _vaga(eid, "Luke").teto_autorizado == estado["autorizado"],
        "tirar a pessoa mexeu no teto autorizado",
    )
    _assign("castA", luke.id, estado["t"][1], float(estado["autorizado"]))
    v = _vaga(eid, "Luke")
    _garante(
        Decimal(v.cache_value) == estado["autorizado"],
        f"Casting não salvou o autorizado: {v.cache_value}",
    )
    ultimo = _logs(eid)[-1]
    _garante(
        "autorizado pelo admin" not in ultimo, f"log marcou o Casting como autorização: {ultimo}"
    )


def cen_03() -> None:
    eid, luke = estado["ev_teto"], _vaga(estado["ev_teto"], "Luke")
    _assign("castA", luke.id, estado["t"][1], float(estado["autorizado"] + 50))
    _garante(
        Decimal(_vaga(eid, "Luke").cache_value) == estado["autorizado"],
        "acima do autorizado não voltou",
    )


def cen_04() -> None:
    eid, luke = estado["ev_teto"], _vaga(estado["ev_teto"], "Luke")
    menor = Decimal(luke.cache_cap) + 10
    _assign("sa", luke.id, estado["t"][1], float(menor))
    _garante(_vaga(eid, "Luke").teto_autorizado == menor, "o último valor do Superadmin não mandou")
    _assign("sa", luke.id, estado["t"][1], float(Decimal(luke.cache_cap) - 10))
    _garante(
        _vaga(eid, "Luke").teto_autorizado is None, "valor dentro do teto não limpou a autorização"
    )


def cen_21() -> None:
    """DEVE falhar como recusa: o Casting não autoriza acima do limite."""
    eid, vader = estado["ev_teto"], _vaga(estado["ev_teto"], "Darth Vader")
    _assign("castA", vader.id, estado["t"][2], float(Decimal(vader.cache_cap) + 100))
    v = _vaga(eid, "Darth Vader")
    _garante(
        Decimal(v.cache_value) == Decimal(vader.cache_cap),
        f"Casting passou do limite: {v.cache_value}",
    )
    _garante(v.teto_autorizado is None, "Casting gravou teto autorizado")


# ── História 2 — virar SHOW ─────────────────────────────────────────────────────────────────────


def cen_06_preparo() -> None:
    eid, vader = estado["ev_teto"], _vaga(estado["ev_teto"], "Darth Vader")
    _assign("sa", vader.id, estado["t"][2], 999)
    _garante(
        _vaga(eid, "Darth Vader").teto_autorizado == Decimal("999"),
        "preparo do 6: autorização não gravou",
    )


def cen_05() -> None:
    eid = estado["ev_teto"]
    antes = {v.character_name: v.cache_value for v in _vagas(eid)}
    emails_do_ensaio.clear()
    resp = _basico("com", eid, tipo="SHOW")
    show = estado["tetos_show"]
    for nome in ("Stormtroopers", "Darth Vader", "Luke"):
        _garante(
            Decimal(_vaga(eid, nome).cache_cap) == show[nome],
            f"{nome}: teto {_vaga(eid, nome).cache_cap} ≠ {show[nome]}",
        )
    _garante(
        Decimal(_vaga(eid, "Coordenador").cache_cap) == show["Coordenador"],
        "coordenador sem teto de show",
    )
    som = _vaga(eid, cal_routes.SOUND_TECH_CHARACTER)
    _garante(
        som.cache_cap is not None and Decimal(som.cache_cap) == show["Técnico de Som"],
        f"técnico: {som.cache_cap}",
    )
    _garante(_vaga(eid, cal_routes.PRESENCE_CHARACTER).cache_cap is None, "presença ganhou teto")
    depois = {v.character_name: v.cache_value for v in _vagas(eid)}
    _garante(all(depois[n] == antes[n] for n in antes), "a troca mexeu em cachê")
    _garante(
        any("Limites de cachê recalculados" in m for m in _logs(eid)), "histórico sem os tetos"
    )
    _garante(
        event_ops.AVISO_VINCULE_ORCAMENTO_DO_SHOW in resp.get("warnings", []),
        f"sem aviso FR-013: {resp.get('warnings')}",
    )


def cen_06() -> None:
    _garante(
        _cap_efetivo(estado["ev_teto"], "Darth Vader") == Decimal("999"),
        "autorizado não ficou por cima do teto de show",
    )


def cen_07() -> None:
    eid = estado["ev_teto"]
    quem = {r.user_id for r in _avisos(eid, nops.KIND_EVENTO_TIPO_SHOW)}
    for chave in ("castA", "castB", "ens", "sa"):
        _garante(estado[chave] in quem, f"{chave} não recebeu o aviso")
    _garante(emails_do_ensaio == [eid], f"e-mail do Ensaio: {emails_do_ensaio}")
    for chave in ("castA", "ens"):
        avisos = _detalhe(chave, eid).get("avisos") or []
        _garante(
            any(
                a["kind"] == nops.KIND_EVENTO_TIPO_SHOW and a["dados"].get("entrou") for a in avisos
            ),
            f"faixa ausente para {chave}: {avisos}",
        )


def cen_08() -> None:
    quem = {r.user_id for r in _avisos(estado["ev_teto"], nops.KIND_EVENTO_TIPO_SHOW)}
    _garante(estado["com"] not in quem, "o autor recebeu o próprio aviso")
    _garante(estado["com2"] not in quem, "Comercial recebeu aviso de Casting")


def cen_10() -> None:
    eid = estado["ev_teto"]
    meu = [r for r in _avisos(eid, nops.KIND_EVENTO_TIPO_SHOW) if r.user_id == estado["castA"]][0]
    r = _cliente("castA").post(f"/api/notificacoes/{meu.id}/ciente")
    _garante(r.status_code == 200, f"ciente → {r.status_code}")
    _garante(
        not [a for a in _detalhe("castA", eid)["avisos"] if a["id"] == meu.id],
        "faixa continuou para A",
    )
    _garante(
        any(a["kind"] == nops.KIND_EVENTO_TIPO_SHOW for a in _detalhe("castB", eid)["avisos"]),
        "faixa sumiu para B",
    )


def cen_11() -> None:
    eid = estado["ev_teto"]
    dele = [r for r in _avisos(eid, nops.KIND_EVENTO_TIPO_SHOW) if r.user_id == estado["castB"]][0]
    estado["aviso_B"] = dele.id
    r = _cliente("castB").post(f"/api/notificacoes/{dele.id}/lida")
    _garante(r.status_code == 200, f"lida → {r.status_code}")
    _garante(
        any(a["id"] == dele.id for a in _detalhe("castB", eid)["avisos"]),
        "ler no sino apagou a faixa",
    )


def cen_12() -> None:
    """DEVE falhar como recusa: "Ciente" no aviso de outra pessoa."""
    r = _cliente("castA").post(f"/api/notificacoes/{estado['aviso_B']}/ciente")
    _garante(r.status_code == 404, f"Ciente alheio → {r.status_code} (esperado 404)")
    linha = _no_banco("SELECT ciente_em FROM notifications WHERE id = :i", i=estado["aviso_B"])[0]
    _garante(linha.ciente_em is None, "o Ciente alheio gravou")


def cen_09() -> None:
    eid = estado["ev_teto"]
    _basico("com", eid, tipo="R&I")
    ri = estado["tetos_ri"]
    for nome in ("Stormtroopers", "Luke"):
        _garante(
            Decimal(_vaga(eid, nome).cache_cap) == ri[nome], f"{nome} não voltou ao teto sem show"
        )
    _garante(
        _cap_efetivo(eid, "Darth Vader") == Decimal("999"), "piso do autorizado perdido na saída"
    )
    saidas = [r for r in _avisos(eid, nops.KIND_EVENTO_TIPO_SHOW) if ":saiu:" in r.dedupe_key]
    _garante(
        {estado["castA"], estado["ens"]} <= {r.user_id for r in saidas}, "saída de SHOW sem aviso"
    )


# ── História 4 — vaga a mais ────────────────────────────────────────────────────────────────────


def cen_13() -> None:
    with app.app_context():
        eid = _evento(
            "(R&I) STORMTROOPERS + STORMTROOPERS + LUKE",
            [("Stormtroopers", estado["t"][0]), ("Stormtroopers", None), ("Luke", None)],
        )
    _basico("com", eid, titulo="(R&I) STORMTROOPERS + LUKE")
    storm = [v for v in _vagas(eid) if v.character_name == "Stormtroopers"]
    _garante(
        len(storm) == 1 and storm[0].talent_id == estado["t"][0],
        f"vagas: {[tuple(v) for v in storm]}",
    )
    _garante(any("vaga vazia removida" in m for m in _logs(eid)), "histórico sem a remoção")


def cen_14() -> None:
    remocoes.clear()
    with app.app_context():
        eid = _evento(
            "(R&I) STORMTROOPERS + STORMTROOPERS + LUKE",
            [("Stormtroopers", estado["t"][0]), ("Stormtroopers", estado["t"][1]), ("Luke", None)],
        )
    estado["ev_sobra"] = eid
    _basico("com", eid, titulo="(R&I) STORMTROOPERS + LUKE")
    storm = [v for v in _vagas(eid) if v.character_name == "Stormtroopers"]
    _garante(
        len(storm) == 2 and all(v.sobrando_desde for v in storm),
        "vagas ocupadas sumiram ou ficaram sem marca",
    )
    _garante(remocoes == [], f"e-mail de remoção: {remocoes}")
    quem = {r.user_id for r in _avisos(eid, nops.KIND_EVENTO_VAGA_SOBRANDO)}
    _garante(
        {estado["castA"], estado["castB"], estado["sa"]} <= quem, "Casting/Superadmin sem aviso"
    )
    _garante(estado["com"] not in quem, "autor recebeu o aviso")
    elenco = [r for r in _detalhe("castA", eid)["elenco"] if r["character_name"] == "Stormtroopers"]
    _garante(
        all(r.get("sobrando") == {"pedido": 1, "vagas": 2} for r in elenco),
        f"payload: {[r.get('sobrando') for r in elenco]}",
    )


def cen_16() -> None:
    eid = estado["ev_sobra"]
    antes = len(_avisos(eid, nops.KIND_EVENTO_VAGA_SOBRANDO))
    with app.app_context():
        ev = CalendarEvent.query.get(eid)
        titulo_ops.reconciliar_vagas_pelo_titulo(
            ev,
            "(R&I) STORMTROOPERS + STORMTROOPERS + LUKE",
            ev.title,
            autor_id=None,
            autor_nome="verify",
            autor_papel="Sistema",
            agora=now_sp(),
        )
        db.session.commit()
    _garante(len(_avisos(eid, nops.KIND_EVENTO_VAGA_SOBRANDO)) == antes, "aviso repetido")


def cen_15() -> None:
    eid = estado["ev_sobra"]
    alvo = [v for v in _vagas(eid) if v.character_name == "Stormtroopers"][-1]
    _assign("castA", alvo.id, None, 0)
    storm = [v for v in _vagas(eid) if v.character_name == "Stormtroopers"]
    _garante(
        len(storm) == 1 and storm[0].sobrando_desde is None,
        f"sobra não resolvida: {[tuple(v) for v in storm]}",
    )
    _garante(
        all(r.ciente_em for r in _avisos(eid, nops.KIND_EVENTO_VAGA_SOBRANDO)),
        "aviso continuou pendente",
    )
    _garante(_titulo(eid) == "(R&I) STORMTROOPERS + LUKE", f"título mexido: {_titulo(eid)}")


def cen_15b() -> None:
    """Converge: o título volta a pedir o personagem → marca e aviso encerram (data-model, FR-017)."""
    with app.app_context():
        eid = _evento(
            "(R&I) STORMTROOPERS + STORMTROOPERS",
            [("Stormtroopers", estado["t"][0]), ("Stormtroopers", estado["t"][1])],
        )
    _basico("com", eid, titulo="(R&I) STORMTROOPERS")
    _garante(all(v.sobrando_desde for v in _vagas(eid)), "preparo: sem marca")
    _basico("com", eid, titulo="(R&I) STORMTROOPERS + STORMTROOPERS")
    _garante(all(v.sobrando_desde is None for v in _vagas(eid)), "a marca ficou com o título pedindo de novo")
    _garante(
        all(r.ciente_em for r in _avisos(eid, nops.KIND_EVENTO_VAGA_SOBRANDO)),
        "aviso continuou pendente",
    )
    _garante(len(_vagas(eid)) == 2, "vaga sumiu")


def cen_17() -> None:
    remocoes.clear()
    with app.app_context():
        eid = _evento(
            "(R&I) ELSA + OLAF",
            [("ELSA", estado["t"][0]), ("OLAF", estado["t"][1])],
            fonte="google_calendar",
        )
        ev = CalendarEvent.query.get(eid)
        item = {
            "id": ev.google_event_id,
            "summary": "(R&I) ELSA",
            "status": "confirmed",
            "start": {"dateTime": ev.start_at.strftime("%Y-%m-%dT%H:%M:%S-03:00")},
            "end": {"dateTime": ev.end_at.strftime("%Y-%m-%dT%H:%M:%S-03:00")},
            "location": ev.location,
            "htmlLink": "https://exemplo",
        }
        cal_routes.sync_events([item])
    olaf = _vaga(eid, "OLAF")
    _garante(
        olaf.talent_id == estado["t"][1] and olaf.sobrando_desde is not None, f"OLAF: {tuple(olaf)}"
    )
    _garante(remocoes == [], f"sync mandou e-mail de remoção: {remocoes}")
    _garante(_avisos(eid, nops.KIND_EVENTO_VAGA_SOBRANDO), "sync sem aviso")


def cen_18() -> None:
    with app.app_context():
        _garante(
            titulo_ops.contar_personagens("(R&I) ELSA + Coordenador + Técnico de Som")
            == {"elsa": 1},
            "nome de equipe contou como personagem",
        )
        pai = _evento("(SHOW) ANNA + ELSA", [("ANNA", None)])
        en = CalendarEvent.query.get(_ensaio(pai, dias=10))
        res = titulo_ops.reconciliar_vagas_pelo_titulo(
            en,
            "A + B",
            "A",
            autor_id=None,
            autor_nome="verify",
            autor_papel="Sistema",
            agora=now_sp(),
        )
        _garante(not res.removidas and not res.marcadas, "regra rodou em ENSAIO")


def cen_22() -> None:
    with app.app_context():
        eid = _evento("(R&I) DARTH VADER + LUKE", [("Vader", None), ("Luke", None)])
    _basico("com", eid, titulo="(R&I) DARTH VADER")
    nomes = [v.character_name for v in _vagas(eid)]
    _garante("Vader" in nomes and "Luke" not in nomes, f"vagas: {nomes}")


# ── História 5 — orçamento novo ─────────────────────────────────────────────────────────────────


def cen_19() -> None:
    with app.app_context():
        eid = _evento(
            "(SHOW) STORMTROOPERS + DARTH VADER + LUKE",
            [("Stormtroopers", None), ("Darth Vader", estado["t"][2]), ("Luke", None)],
            orc_id=estado["orc_ri"],
            tipo="SHOW",
            tetos=estado["tetos_show"],
        )
        db.session.execute(
            text("UPDATE calendar_events SET orcamento_history_id = NULL WHERE id = :i"),
            {"i": estado["ev_teto"]},
        )
        db.session.commit()
    estado["ev_orc"] = eid
    vader = _vaga(eid, "Darth Vader")
    _assign("sa", vader.id, estado["t"][2], 1500)
    r = _cliente("sa").patch(
        f"/api/events/{eid}/orcamento", json={"orcamento_history_id": estado["orc_show"]}
    )
    _garante(r.status_code == 200, f"vínculo → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(
        Decimal(_vaga(eid, "Luke").cache_cap) == estado["tetos_orc_show"]["Luke"],
        f"Luke {_vaga(eid, 'Luke').cache_cap} ≠ cantor {estado['tetos_orc_show']['Luke']}",
    )
    _garante(
        any("Limites de cachê do orçamento" in m for m in _logs(eid)),
        "histórico sem os tetos do vínculo",
    )


def cen_20() -> None:
    _garante(
        _cap_efetivo(estado["ev_orc"], "Darth Vader") == Decimal("1500"),
        "vínculo baixou o autorizado",
    )


# ── História 6 — título ↔ vagas ↔ ensaio ────────────────────────────────────────────────────────


def cen_23() -> None:
    google.updates.clear()
    with app.app_context():
        eid = _evento(
            "(R&I) STORMTROOPERS + STORMTROOPERS + DARTH VADER",
            [("Stormtroopers", None), ("Stormtroopers", None), ("Darth Vader", None)],
        )
        futuro, passado = _ensaio(eid, dias=5), _ensaio(eid, dias=-5)
        estado.update(ev_tit=eid, en_futuro=futuro, en_passado=passado)
        g_ev = CalendarEvent.query.get(eid).google_event_id
        g_fut = CalendarEvent.query.get(futuro).google_event_id
    alvo = [v for v in _vagas(eid) if v.character_name == "Stormtroopers"][-1]
    r = _cliente("castA").delete(f"/api/roles/{alvo.id}")
    _garante(r.status_code == 200, f"DELETE → {r.status_code}")
    novo = "(R&I) STORMTROOPERS + DARTH VADER"
    _garante(_titulo(eid) == novo, f"título: {_titulo(eid)}")
    _garante((g_ev, novo) in google.updates, f"Google sem o título do evento: {google.updates}")
    _garante(
        (g_fut, f"{event_ops.ENSAIO_TITLE_PREFIX}{novo}") in google.updates,
        "Google sem o título do ensaio",
    )


def cen_25() -> None:
    _garante(
        _titulo(estado["en_futuro"]).endswith("STORMTROOPERS + DARTH VADER"),
        "ensaio futuro não acompanhou",
    )
    _garante(
        "STORMTROOPERS + STORMTROOPERS" in _titulo(estado["en_passado"]),
        "ensaio passado foi mexido",
    )


def cen_24() -> None:
    eid = estado["ev_tit"]
    c = _cliente("castA")
    r = c.post(
        f"/api/events/{eid}/roles", json={"character_name": "Yoda", "role_type": "character"}
    )
    _garante(r.status_code == 200 and _titulo(eid).endswith("+ YODA"), f"Yoda: {_titulo(eid)}")
    r = c.post(
        f"/api/events/{eid}/roles", json={"character_name": "Coordenador", "role_type": "extra"}
    )
    _garante(
        r.status_code == 200 and "COORDENADOR" not in _titulo(eid).upper(),
        f"equipe entrou no título: {_titulo(eid)}",
    )


def cen_26() -> None:
    eid = estado["ev_tit"]
    with app.app_context():
        db.session.add(EventRole(event_id=eid, character_name="Ewok"))
        db.session.commit()
    antes = _titulo(eid)
    ewok = _vaga(eid, "Ewok")
    r = _cliente("castA").delete(f"/api/roles/{ewok.id}")
    _garante(r.status_code == 200 and _titulo(eid) == antes, f"título mudou: {_titulo(eid)}")
    _garante(any("não foi encontrado" in m for m in _logs(eid)), "histórico sem 'não encontrado'")


def cen_27() -> None:
    eid = estado["ev_tit"]
    google.recusar = True
    try:
        yoda = _vaga(eid, "Yoda")
        r = _cliente("castA").delete(f"/api/roles/{yoda.id}")
    finally:
        google.recusar = False
    _garante(r.status_code == 200, f"DELETE com Google fora → {r.status_code}")
    _garante(
        titulo_ops.AVISO_FALHA_GOOGLE in (r.get_json().get("warnings") or []),
        "sem aviso de falha do Google",
    )
    _garante("Yoda" not in [v.character_name for v in _vagas(eid)], "vaga não saiu")


def cen_27b() -> None:
    with app.app_context():
        eid = _evento(
            "(R&I) STORMTROOPERS + STORMTROOPERS",
            [("Stormtroopers", estado["t"][0]), ("Stormtroopers", estado["t"][1])],
        )
    _basico("com", eid, titulo="(R&I) STORMTROOPERS")
    alvo = [v for v in _vagas(eid) if v.character_name == "Stormtroopers"][-1]
    r = _cliente("castA").delete(f"/api/roles/{alvo.id}")
    _garante(r.status_code == 200, f"DELETE → {r.status_code}")
    _garante(_titulo(eid) == "(R&I) STORMTROOPERS", f"o nome saiu duas vezes: {_titulo(eid)}")
    _garante(all(v.sobrando_desde is None for v in _vagas(eid)), "marca não limpou")


def cen_28_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(
            not _no_banco(
                "SELECT 1 FROM calendar_events WHERE google_event_id LIKE :p", p=f"{PREFIX}%"
            ),
            "evento sobrou",
        )
        _garante(
            not _no_banco("SELECT 1 FROM users WHERE email LIKE :p", p=f"{PREFIX}%"),
            "usuário sobrou",
        )


def main() -> int:
    print("Feature 339 — mudança no evento avisa o Casting, e o teto do cachê acompanha")
    preparar()
    passos = [
        ("1. Superadmin acima do teto grava teto autorizado da vaga", cen_01),
        ("2. Casting troca a pessoa e salva o valor autorizado", cen_02),
        ("3. Casting acima do autorizado volta ao autorizado", cen_03),
        ("4. último valor do Superadmin manda", cen_04),
        ("21. Casting não grava teto autorizado (DEVE falhar como recusa)", cen_21),
        ("6a. preparo: autorização acima do teto de show", cen_06_preparo),
        ("5. R&I → SHOW: tetos de show, cachês intactos, histórico, aviso FR-013", cen_05),
        ("6. autorizado fica por cima do teto de show", cen_06),
        ("7. aviso a Casting, Ensaio e Superadmin; e-mail do Ensaio; faixa", cen_07),
        ("8. autor e Comercial sem aviso", cen_08),
        ("10. Ciente de A não some para B", cen_10),
        ("11. ler no sino não apaga a faixa", cen_11),
        ("12. Ciente no aviso alheio → 404 (DEVE falhar como recusa)", cen_12),
        ("9. SHOW → R&I: tetos sem show, piso do autorizado, aviso", cen_09),
        ("13. título 2 → 1 com vaga vazia: a vazia sai", cen_13),
        ("14. título 2 → 1 com as duas ocupadas: marca e avisa, sem e-mail", cen_14),
        ("16. mesma reconciliação de novo: nenhum aviso repetido", cen_16),
        ("15. Casting tira um artista: vaga vazia sai, marca e aviso encerram", cen_15),
        ("15b. título volta a pedir: marca e aviso encerram (converge)", cen_15b),
        ("17. evento do Google: vaga ocupada fica, sem e-mail, marcada", cen_17),
        ("18. nome de equipe e ENSAIO: regra de hoje", cen_18),
        ("22. vaga com grafia diferente do título não é tocada", cen_22),
        ("19. vínculo do orçamento novo: teto de cantor com show", cen_19),
        ("20. vínculo não baixa o autorizado", cen_20),
        ("23. remover uma de duas vagas: título perde uma ocorrência, Google chamado", cen_23),
        ("25. só o ensaio futuro acompanha o título", cen_25),
        ("24. vaga nova entra no fim do título; equipe não entra", cen_24),
        ("26. vaga fora do título: título igual, histórico 'não encontrado'", cen_26),
        ("27. Google recusa: vaga sai e a resposta avisa", cen_27),
        ("27b. remover a vaga sobrando não tira o nome duas vezes", cen_27b),
    ]
    manter = os.environ.get("VERIFY_339_MANTER") == "1"
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        if manter:
            print(
                "  (VERIFY_339_MANTER=1: limpeza pulada)",
                {k: v for k, v in estado.items() if k.startswith("ev_")},
            )
        else:
            cenario("28. limpeza", cen_28_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
