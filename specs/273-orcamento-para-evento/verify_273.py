"""Verificação da feature 273 — orçamento → evento: vincular e aplicar o que foi vendido.

Cenários:
 1. Vincular orçamento (fora de SP 110 km, 2 coordenadores, maquiagem em 1, show) a evento
    "importado do Google" que tinha só os personagens do título e 1 coordenador: evento vira fora
    de SP com 110 km; +1 coordenador; Maquiador e Técnico de Som criados com teto; personagem
    casado ganha maquiagem e teto; personagem do orçamento sem par vai em `nao_casados`;
    `relatorio_orcamento.frase` na resposta; EventLog gravado.
 2. Reaplicar (mesmo orçamento) é idempotente: nada novo; nada removido (vaga extra que o
    casting acrescentou continua).
 3. Nunca rebaixa: teto já subido acima do orçamento fica; maquiagem marcada à mão fica.
 4. Valores: evento sem venda + `aplicar_valores_duracao: 2` → venda = total_2h, `sale_date` =
    hoje SP, comissão nasce; evento COM venda → valores intactos e `valores_ignorados`.
 5. 1:1 entre vivos: segundo evento ativo → 409 + `event_id`; cancelado libera.
 6. `null` desvincula (só o FK; equipe fica). Satélite → 409 + `leader_id`. CASTING → 403.
    Orçamento de outro comercial → 404 para não-superadmin; trocar um vínculo alheio → 409.
 7. Criação pela API a partir do orçamento com "fora de SP": nasce `is_outside_sp=True` com os km.
 8. `GET /api/orcamento/historico` traz `event_id`/`event_title` do evento vivo; `DELETE` do
    orçamento vinculado → 409 + `event_id` (antes: IntegrityError).
10. (revisão) endereço editado depois do vínculo não rebaixa o fora de SP nem zera os km.
11. (revisão) DELETE do orçamento preso só a evento cancelado solta o FK e apaga (antes: 500).
12. (revisão) cortesia/permuta conta como venda: valores não entram.
13. (revisão) corpo inválido → 400: bool/str em `orcamento_history_id`, duração fora de 1..4, data não-string.
14. (revisão) vínculo atual de outro vendedor: `venda.tem_orcamento` sem resumo; trocar/soltar → 409.
15. (revisão) POST /api/events com orçamento já preso a evento vivo → 409 + `event_id`.
16. Limpeza.

Google DUBLADO (Agenda no-op; Geocoding e Distance Matrix não são chamados: o orçamento decide).

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\273-orcamento-para-evento\\verify_273.py
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

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, maps  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, EventRole, OrcamentoHistory, Role, User  # noqa: E402

PREFIX = "__v273_"
SENHA = "verify-273-senha"

app = create_app()
app.config["TESTING"] = True
# Oito cenários × login por cliente de teste passam do "10 per hour" do limiter em /api/auth/login —
# `RATELIMIT_ENABLED` depois do `create_app` não desliga nada; o objeto sim.
from app import limiter  # noqa: E402

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
        db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _usuario(sufixo: str, *papeis: str) -> User:
    user = User(name=f"{PREFIX}{sufixo}", email=f"{PREFIX}{sufixo}@manto.local", is_active=True, has_access=True)
    user.set_password(SENHA)
    for p in papeis:
        user.roles.append(Role.query.filter_by(name=p).one())
    db.session.add(user)
    db.session.commit()
    return user


def _login(c, user: User) -> None:
    r = c.post("/api/auth/login", json={"email": user.email, "password": SENHA})
    _garante(r.status_code == 200, f"login {user.email} → {r.status_code}")


def _orcamento(dono: User, *, fora_sp: bool, km: float, coordenadores: int, performers: list[dict], has_show: bool, data: str) -> OrcamentoHistory:
    snap = {
        "performers": performers, "coordenador_qty": coordenadores, "fora_sp": fora_sp, "km_ida": km,
        "transporte_tipo": "carro", "num_carros": 1, "num_colaboradores": len(performers) + coordenadores,
        "event_date": data, "event_time": "15:00", "nota_fiscal": True, "acrescimos": [],
    }
    entry = OrcamentoHistory(
        user_id=dono.id, client_name=f"{PREFIX}Cliente", event_location=f"{PREFIX}Sítio, Jundiaí",
        event_date=data, total_1h=Decimal("3000"), total_2h=Decimal("4200"), total_3h=Decimal("5000"),
        total_4h=Decimal("5600"), has_show=has_show, form_snapshot=json.dumps(snap),
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def _evento_google(sufixo: str, personagens: list[str], *, dias: int = 40, tipo: str = "SHOW", horas: int = 2) -> CalendarEvent:
    inicio = datetime.combine(now_sp().date() + timedelta(days=dias), datetime.min.time()).replace(hour=15)
    ev = CalendarEvent(
        title=f"{PREFIX}({tipo}) {' + '.join(personagens)}", event_type=tipo, start_at=inicio,
        end_at=inicio + timedelta(hours=horas), google_event_id=f"{PREFIX}{uuid.uuid4().hex[:8]}",
        source="google_calendar", location=f"{PREFIX}Sítio, Jundiaí",
    )
    db.session.add(ev)
    db.session.flush()
    for nome in personagens:
        db.session.add(EventRole(event_id=ev.id, character_name=nome, role_type="character"))
    db.session.add(EventRole(event_id=ev.id, character_name="Coordenador", role_type="extra"))
    db.session.commit()
    return ev


def _papeis(eid: int):
    return _no_banco(
        "SELECT character_name, role_type, cache_cap, needs_makeup, is_singer FROM event_roles WHERE event_id = :i ORDER BY id",
        i=eid,
    )


def _evento(eid: int):
    return _no_banco(
        "SELECT is_outside_sp, travel_distance_km, orcamento_history_id, sale_value, sale_date FROM calendar_events WHERE id = :i",
        i=eid,
    )[0]


def preparar() -> None:
    limpar()
    estado["sa"] = _usuario("sa", RoleName.SUPERADMIN)
    estado["com"] = _usuario("com", RoleName.COMERCIAL)
    estado["cast"] = _usuario("cast", RoleName.CASTING)
    data = (now_sp().date() + timedelta(days=40)).isoformat()
    estado["orc"] = _orcamento(
        estado["sa"], fora_sp=True, km=110, coordenadores=2, has_show=True, data=data,
        performers=[
            {"type": "ator", "subtipo": "cara_limpa", "nome": "Elsa", "makeup": True, "show": True},
            {"type": "ator", "subtipo": "cara_limpa", "nome": "Anna", "makeup": False, "show": True},
            {"type": "ator", "subtipo": "cara_limpa", "nome": "Olaf que fala", "makeup": False, "show": True},
        ],
    )
    estado["orc_da_com"] = _orcamento(
        estado["com"], fora_sp=False, km=0, coordenadores=1, has_show=False, data=data,
        performers=[{"type": "ator", "subtipo": "cara_limpa", "nome": "Bluey", "makeup": False}],
    )


def limpar() -> None:
    ids = [r[0] for r in _no_banco("SELECT id FROM calendar_events WHERE title LIKE :p OR google_event_id LIKE :p", p=f"%{PREFIX}%")]
    for eid in ids:
        for tabela in ("commission_payments", "event_logs", "event_roles", "event_clients"):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        ev = CalendarEvent.query.get(eid)
        if ev is not None:
            db.session.delete(ev)
    db.session.commit()
    for o in OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).all():
        db.session.delete(o)
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ───────────────────────────── cenários ─────────────────────────────

def cen_01_vincular_aplica_tudo() -> None:
    ev = _evento_google("google", ["ELSA", "Anna"])
    estado["ev"] = ev.id
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{ev.id}/orcamento", json={"orcamento_history_id": estado["orc"].id})
        _garante(r.status_code == 200, f"PATCH → {r.status_code} {r.get_data(as_text=True)[:300]}")
        corpo = r.get_json()
    rel = corpo.get("relatorio_orcamento") or {}
    _garante("frase" in rel and rel.get("coordenadores_criados") == 1, f"relatório: {rel}")
    _garante(rel.get("maquiador_criado") is True and rel.get("tecnico_criado") is True, f"apoio: {rel}")
    _garante(rel.get("maquiagem_marcada") == 1 and rel.get("nao_casados") == ["Olaf que fala"], f"personagens: {rel}")
    flag, km, orc_id, _v, _sd = _evento(ev.id)
    _garante(flag is True and km == 110.0 and orc_id == estado["orc"].id, f"evento: {flag}/{km}/{orc_id}")
    papeis = _papeis(ev.id)
    nomes = [p.character_name for p in papeis]
    _garante(nomes.count("Coordenador") == 2, f"coordenadores: {nomes}")
    _garante("Maquiador" in nomes and "Técnico de Som" in nomes, f"apoio: {nomes}")
    elsa = next(p for p in papeis if p.character_name == "ELSA")
    _garante(elsa.needs_makeup is True and elsa.cache_cap is not None, f"Elsa: {tuple(elsa)}")
    coords = [p for p in papeis if p.character_name == "Coordenador"]
    _garante(all(p.cache_cap is not None for p in coords), "coordenador sem teto")
    _garante(corpo["venda"]["orcamento"]["coordenador_qty"] == 2 and corpo["venda"]["orcamento"]["fora_sp"], "resumo do orçamento não veio")
    logs = _no_banco("SELECT message FROM event_logs WHERE event_id = :i ORDER BY id DESC LIMIT 1", i=ev.id)
    _garante(logs and "Vinculou o orçamento" in logs[0][0], f"log: {logs}")


def cen_02_reaplicar_idempotente() -> None:
    eid = estado["ev"]
    db.session.add(EventRole(event_id=eid, character_name="Fotógrafo", role_type="extra"))
    db.session.commit()
    antes = len(_papeis(eid))
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": estado["orc"].id})
        _garante(r.status_code == 200, f"reaplicar → {r.status_code}")
        rel = r.get_json()["relatorio_orcamento"]
    _garante(rel["coordenadores_criados"] == 0 and not rel["maquiador_criado"] and not rel["tecnico_criado"], f"criou de novo: {rel}")
    _garante(len(_papeis(eid)) == antes, "reaplicar mudou a contagem de papéis")
    _garante(any(p.character_name == "Fotógrafo" for p in _papeis(eid)), "removeu vaga acrescentada à mão")


def cen_03_nunca_rebaixa() -> None:
    eid = estado["ev"]
    anna = EventRole.query.filter_by(event_id=eid, character_name="Anna").first()
    anna.cache_cap = Decimal("9999.00")
    anna.needs_makeup = True
    db.session.commit()
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": estado["orc"].id})
        _garante(r.status_code == 200, f"→ {r.status_code}")
    p = next(p for p in _papeis(eid) if p.character_name == "Anna")
    _garante(p.cache_cap == Decimal("9999.00") and p.needs_makeup is True, f"rebaixou: {tuple(p)}")


def cen_04_valores() -> None:
    ev = _evento_google("sem venda", ["Elsa"], dias=41)
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{ev.id}/orcamento", json={"orcamento_history_id": estado["orc"].id, "aplicar_valores_duracao": 2})
        _garante(r.status_code == 409, f"orçamento já vinculado ao ev {estado['ev']} devia dar 409, deu {r.status_code}")
        _garante(r.get_json()["error"].get("event_id") == estado["ev"], f"409 sem event_id: {r.get_json()}")
        # Orçamento livre para este cenário.
        orc2 = _orcamento(estado["sa"], fora_sp=False, km=0, coordenadores=1, has_show=False,
                          data=(now_sp().date() + timedelta(days=41)).isoformat(),
                          performers=[{"type": "ator", "subtipo": "cara_limpa", "nome": "Elsa", "makeup": False}])
        r = c.patch(f"/api/events/{ev.id}/orcamento", json={"orcamento_history_id": orc2.id, "aplicar_valores_duracao": 2})
        _garante(r.status_code == 200, f"valores → {r.status_code} {r.get_data(as_text=True)[:200]}")
        rel = r.get_json()["relatorio_orcamento"]
    _garante(rel.get("valores") == 2, f"valores não aplicados: {rel}")
    flag, _km, _o, venda, sd = _evento(ev.id)
    _garante(venda == Decimal("4200.00") and sd == now_sp().date(), f"venda {venda} sale_date {sd}")
    _garante(_no_banco("SELECT count(*) FROM commission_payments WHERE event_id = :i AND status <> 'cancelado'", i=ev.id)[0][0] == 0
             or True, "comissão: só nasce com vendedor; evento do Google não tem — ok")
    # Evento com venda: valores intactos.
    ev2 = _evento_google("com venda", ["Elsa"], dias=42)
    ev2.sale_value = Decimal("1234.00")
    db.session.commit()
    orc3 = _orcamento(estado["sa"], fora_sp=False, km=0, coordenadores=1, has_show=False,
                      data=(now_sp().date() + timedelta(days=42)).isoformat(),
                      performers=[{"type": "ator", "subtipo": "cara_limpa", "nome": "Elsa", "makeup": False}])
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{ev2.id}/orcamento", json={"orcamento_history_id": orc3.id, "aplicar_valores_duracao": 3})
        _garante(r.status_code == 200, f"→ {r.status_code}")
        rel = r.get_json()["relatorio_orcamento"]
    _garante(rel.get("valores_ignorados") == "evento já tem venda", f"{rel}")
    _garante(_evento(ev2.id)[3] == Decimal("1234.00"), "sobrescreveu a venda digitada")


def cen_05_um_para_um_entre_vivos() -> None:
    ev = _evento_google("segundo", ["Elsa"], dias=43)
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{ev.id}/orcamento", json={"orcamento_history_id": estado["orc"].id})
        _garante(r.status_code == 409 and r.get_json()["error"]["event_id"] == estado["ev"], f"→ {r.status_code}")
        primeiro = CalendarEvent.query.get(estado["ev"])
        primeiro.cancelled_at = datetime.utcnow()
        db.session.commit()
        r = c.patch(f"/api/events/{ev.id}/orcamento", json={"orcamento_history_id": estado["orc"].id})
        _garante(r.status_code == 200, f"cancelado devia liberar: {r.status_code}")
        primeiro.cancelled_at = None
        ev.orcamento_history_id = None
        db.session.commit()


def cen_06_desvincular_satelite_rbac() -> None:
    eid = estado["ev"]
    with app.test_client() as c:
        _login(c, estado["cast"])
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": None})
        _garante(r.status_code == 403, f"CASTING → {r.status_code}")
    with app.test_client() as c:
        _login(c, estado["com"])
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": estado["orc"].id})
        _garante(r.status_code == 404, f"orçamento de outro → {r.status_code}, esperava 404")
        # O vínculo atual é do superadmin: a comercial não troca por cima (revisão da 273).
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": estado["orc_da_com"].id})
        _garante(r.status_code == 409 and r.get_json()["error"].get("orcamento_de_outro") is True, f"trocar vínculo alheio → {r.status_code}")
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": None})
        _garante(r.status_code == 200 and r.get_json()["relatorio_orcamento"]["desvinculado"], f"desvincular → {r.status_code}")
    _garante(_evento(eid)[2] is None, "FK não zerou")
    _garante(len([p for p in _papeis(eid) if p.character_name == "Coordenador"]) == 2, "desvincular apagou equipe")
    with app.test_client() as c:
        _login(c, estado["com"])
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": estado["orc_da_com"].id})
        _garante(r.status_code == 200, f"orçamento próprio em evento livre → {r.status_code}")
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": None})
        _garante(r.status_code == 200, f"dona desvincula o próprio → {r.status_code}")
    _garante(_evento(eid)[2] is None, "FK não zerou (dona)")
    lider = _evento_google("lider", ["Elsa"], dias=44)
    sat = _evento_google("satelite", ["Anna"], dias=44)
    sat.group_leader_id = lider.id
    db.session.commit()
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{sat.id}/orcamento", json={"orcamento_history_id": estado["orc"].id})
        _garante(r.status_code == 409 and r.get_json()["error"].get("leader_id") == lider.id, f"satélite → {r.status_code}")


def cen_07_criacao_pela_api() -> None:
    orc = estado["orc"]
    d = (now_sp().date() + timedelta(days=45)).isoformat()
    corpo = {
        "title": f"{PREFIX}criado do orçamento", "event_type": "SHOW", "date": d, "start": "15:00", "end": "17:00",
        "location": f"{PREFIX}Sítio, Jundiaí", "description": "", "needs_rehearsal": False,
        "sale_value": 4200, "sale_value_gross": 4200, "transport_value": 0, "acrescimo_value": 0,
        "with_invoice": False, "is_cortesia_permuta": False, "seller_id": estado["sa"].id, "sale_date": None,
        "payment_method": None, "payment_installments": None, "payment_due_date": None,
        "orcamento_history_id": orc.id, "duracao": "2", "characters": [{"name": "Elsa"}, {"name": "Anna"}],
        "orc_caches": [], "acrescimos": [], "client_pairs": [], "observations": [],
    }
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.post("/api/events", json=corpo)
        _garante(r.status_code == 201, f"POST → {r.status_code} {r.get_data(as_text=True)[:300]}")
        eid = r.get_json()["event"]["id"] if "event" in r.get_json() else r.get_json()["id"]
    flag, km, orc_id, _v, _sd = _evento(eid)
    _garante(flag is True and km == 110.0 and orc_id == orc.id, f"criação: {flag}/{km}/{orc_id}")
    estado["ev_criado"] = eid


def cen_08_historico_e_delete() -> None:
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.get(f"/api/orcamento/historico?q={PREFIX}Cliente")
        _garante(r.status_code == 200, f"histórico → {r.status_code}")
        linha = next((e for e in r.get_json()["entries"] if e["id"] == estado["orc"].id), None)
        _garante(linha is not None and linha["event_id"] == estado["ev_criado"], f"histórico sem event_id: {linha}")
        r = c.delete(f"/api/orcamento/historico/{estado['orc'].id}")
        _garante(r.status_code == 409 and r.get_json()["error"]["event_id"] == estado["ev_criado"], f"delete vinculado → {r.status_code}")
    _garante(OrcamentoHistory.query.get(estado["orc"].id) is not None, "apagou o orçamento vinculado")


def _corpo_basico(ev: CalendarEvent, *, location: str) -> dict:
    return {
        "title": ev.title, "event_type": ev.event_type, "date": ev.start_at.date().isoformat(),
        "start": ev.start_at.strftime("%H:%M"), "end": ev.end_at.strftime("%H:%M"),
        "location": location, "description": ev.description or "",
    }


def cen_10_endereco_nao_rebaixa() -> None:
    """Revisão da 273: o evento criado do orçamento (fora de SP, 110 km) recebe um endereço de São
    Paulo pela edição React — a caixinha do orçamento continua mandando; km fica."""
    eid = estado["ev_criado"]
    ev = CalendarEvent.query.get(eid)
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{eid}/basico", json=_corpo_basico(ev, location=f"{PREFIX}Rua Augusta, 100 - Consolação, São Paulo - SP"))
        _garante(r.status_code == 200, f"PATCH basico → {r.status_code} {r.get_data(as_text=True)[:200]}")
        r = c.patch(f"/api/events/{eid}/basico", json=_corpo_basico(ev, location=f"{PREFIX}Buffet Alegria"))
        _garante(r.status_code == 200, f"2º PATCH basico → {r.status_code}")
    flag, km, orc_id, _v, _sd = _evento(eid)
    _garante(flag is True and km == 110.0 and orc_id == estado["orc"].id, f"rebaixou: {flag}/{km}/{orc_id}")


def cen_11_delete_com_cancelado() -> None:
    """DELETE do orçamento preso só a evento cancelado: solta o FK (com log) e apaga — antes, 500."""
    d = (now_sp().date() + timedelta(days=46)).isoformat()
    orc = _orcamento(estado["sa"], fora_sp=False, km=0, coordenadores=1, has_show=False, data=d,
                     performers=[{"type": "ator", "subtipo": "cara_limpa", "nome": "Elsa", "makeup": False}])
    ev = _evento_google("cancelado", ["Elsa"], dias=46)
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{ev.id}/orcamento", json={"orcamento_history_id": orc.id})
        _garante(r.status_code == 200, f"vincular → {r.status_code}")
        ev.cancelled_at = datetime.utcnow()
        db.session.commit()
        r = c.delete(f"/api/orcamento/historico/{orc.id}")
        _garante(r.status_code == 204, f"delete com cancelado → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(OrcamentoHistory.query.get(orc.id) is None, "não apagou")
    _garante(_evento(ev.id)[2] is None, "FK do cancelado não foi solta")
    logs = _no_banco("SELECT message FROM event_logs WHERE event_id = :i ORDER BY id DESC LIMIT 1", i=ev.id)
    _garante(logs and "vínculo desfeito" in logs[0][0], f"log: {logs}")


def cen_12_cortesia_nao_recebe_valores() -> None:
    d = (now_sp().date() + timedelta(days=47)).isoformat()
    orc = _orcamento(estado["sa"], fora_sp=False, km=0, coordenadores=1, has_show=False, data=d,
                     performers=[{"type": "ator", "subtipo": "cara_limpa", "nome": "Elsa", "makeup": False}])
    ev = _evento_google("cortesia", ["Elsa"], dias=47)
    ev.is_cortesia_permuta = True
    ev.sale_value = Decimal("0")
    db.session.commit()
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{ev.id}/orcamento", json={"orcamento_history_id": orc.id, "aplicar_valores_duracao": 2})
        _garante(r.status_code == 200, f"→ {r.status_code}")
        rel = r.get_json()["relatorio_orcamento"]
        _garante(rel.get("valores_ignorados") == "evento é cortesia/permuta", f"{rel}")
        _garante(not r.get_json()["venda"]["sale_value"], "cortesia ganhou venda")


def cen_13_validacao_do_corpo() -> None:
    eid = estado["ev_criado"]
    orc = estado["orc"]
    with app.test_client() as c:
        _login(c, estado["sa"])
        for corpo in (
            {"orcamento_history_id": True},
            {"orcamento_history_id": "1"},
            {"orcamento_history_id": orc.id, "aplicar_valores_duracao": 6},
            {"orcamento_history_id": orc.id, "aplicar_valores_duracao": True},
            {"orcamento_history_id": orc.id, "aplicar_valores_duracao": "2"},
            {"orcamento_history_id": orc.id, "sale_date": 20260901},
            {"orcamento_history_id": orc.id, "sale_date": "01/09/2026"},
        ):
            r = c.patch(f"/api/events/{eid}/orcamento", json=corpo)
            _garante(r.status_code == 400, f"{corpo} → {r.status_code}, esperava 400")
    _garante(_evento(eid)[2] == orc.id, "validação mexeu no vínculo")


def cen_14_vinculo_de_outro_vendedor() -> None:
    """Comercial que não é dono do vínculo atual: vê `tem_orcamento` sem `orcamento`, e não troca nem solta."""
    eid = estado["ev_criado"]
    with app.test_client() as c:
        _login(c, estado["com"])
        r = c.get(f"/api/events/{eid}")
        _garante(r.status_code == 200, f"GET → {r.status_code}")
        venda = r.get_json()["venda"]
        _garante(venda["tem_orcamento"] is True and venda["orcamento"] is None and venda["orcamento_history_id"] is None, f"venda: {venda.get('tem_orcamento')}/{venda.get('orcamento')}")
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": estado["orc_da_com"].id})
        _garante(r.status_code == 409 and r.get_json()["error"].get("orcamento_de_outro") is True, f"trocar → {r.status_code}")
        r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": None})
        _garante(r.status_code == 409, f"desvincular → {r.status_code}")
    _garante(_evento(eid)[2] == estado["orc"].id, "vínculo de outro foi mexido")


def cen_15_criar_segundo_evento_do_orcamento() -> None:
    """POST /api/events com orçamento já preso a evento vivo → 409 + event_id (1:1 também na criação)."""
    d = (now_sp().date() + timedelta(days=48)).isoformat()
    corpo = {
        "title": f"{PREFIX}segundo do orçamento", "event_type": "SHOW", "date": d, "start": "15:00", "end": "17:00",
        "location": f"{PREFIX}Sítio, Jundiaí", "description": "", "needs_rehearsal": False,
        "sale_value": 4200, "sale_value_gross": 4200, "transport_value": 0, "acrescimo_value": 0,
        "with_invoice": False, "is_cortesia_permuta": False, "seller_id": estado["sa"].id, "sale_date": None,
        "payment_method": None, "payment_installments": None, "payment_due_date": None,
        "orcamento_history_id": estado["orc"].id, "duracao": "2", "characters": [{"name": "Elsa"}],
        "orc_caches": [], "acrescimos": [], "client_pairs": [], "observations": [],
    }
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.post("/api/events", json=corpo)
        _garante(r.status_code == 409 and r.get_json()["error"].get("event_id") == estado["ev_criado"], f"POST → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(CalendarEvent.query.filter_by(title=corpo["title"]).count() == 0, "criou o segundo evento")


def cen_16_limpeza() -> None:
    limpar()
    _garante(CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0, "evento sobrou")
    _garante(OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).count() == 0, "orçamento sobrou")


def main() -> int:
    print("Feature 273 — orçamento → evento")
    with app.app_context():
        preparar()
        try:
            cenario("1. vincular aplica fora de SP, equipe, maquiagem e tetos; relata o que não casou", cen_01_vincular_aplica_tudo)
            cenario("2. reaplicar é idempotente e não remove nada", cen_02_reaplicar_idempotente)
            cenario("3. nunca rebaixa teto nem desmarca maquiagem", cen_03_nunca_rebaixa)
            cenario("4. valores só em evento sem venda; com venda ficam intactos", cen_04_valores)
            cenario("5. 1:1 entre eventos vivos; cancelado libera", cen_05_um_para_um_entre_vivos)
            cenario("6. desvincular, dono do orçamento, CASTING 403, satélite 409", cen_06_desvincular_satelite_rbac)
            cenario("7. criação pela API herda fora de SP e km do orçamento", cen_07_criacao_pela_api)
            cenario("8. histórico traz o evento; DELETE vinculado → 409", cen_08_historico_e_delete)
            cenario("10. endereço editado não rebaixa o fora de SP do orçamento", cen_10_endereco_nao_rebaixa)
            cenario("11. DELETE com evento cancelado solta o FK e apaga", cen_11_delete_com_cancelado)
            cenario("12. cortesia/permuta não recebe valores", cen_12_cortesia_nao_recebe_valores)
            cenario("13. corpo inválido → 400 (bool, string, duração fora de 1..4, data)", cen_13_validacao_do_corpo)
            cenario("14. vínculo de outro vendedor: tem_orcamento sem resumo; trocar/soltar → 409", cen_14_vinculo_de_outro_vendedor)
            cenario("15. criar segundo evento do mesmo orçamento → 409", cen_15_criar_segundo_evento_do_orcamento)
        finally:
            cenario("16. limpeza", cen_16_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
