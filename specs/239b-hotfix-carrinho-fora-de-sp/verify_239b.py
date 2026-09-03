"""Verificação do hotfix 239b — o carrinho de transporte não pode sumir por "fora de SP desconhecido".

Cenários:
 1. `_lookup_sp_status`: sem CEP, o Geocoding decide — "Porto Feliz/SP" → fora; "São Paulo/SP" →
    dentro; Google sem cidade → desconhecido (texto sem "São Paulo"); texto com "São Paulo" → dentro.
 2. Criação pela API com endereço fora de SP → `is_outside_sp=True` e distância estimada.
 3. PATCH em bloco trocando o endereço → reclassifica (fora → dentro); endereço igual e flag
    desconhecida → reclassifica (cura); endereço igual e flag conhecida → não chama o Google.
 4. Marcar transporte: evento desconhecido → 200 e o evento vira fora de SP (com distância);
    evento dentro de SP → 400; evento fora → 200.
 5. "Estimar via Google Maps" reclassifica um evento desconhecido.
 6. Script de reclassificação: dry-run não grava; `--execute` classifica e busca distância.
 7. Limpeza.

Google DUBLADO: `app.maps.cidade_do_endereco` responde por dicionário; `_fetch_travel_data` grava
42 km sem sair da máquina; `insert_event`/`update_event`/`delete_event` da Agenda são no-op.
Nenhuma chamada real ao Google.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\239b-hotfix-carrinho-fora-de-sp\\verify_239b.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
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
from app.models import CalendarEvent, EventRole, Role, User  # noqa: E402

PREFIX = "__v239b_"
SENHA = "verify-239b-senha"

app = create_app()
app.config["TESTING"] = True

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês ──────────────────────────────────────────────────────────────────────────────────────
GEOCODE: dict[str, tuple[str | None, str | None]] = {
    f"{PREFIX}Fazenda Boa Vista, Porto Feliz": ("Porto Feliz", "SP"),
    f"{PREFIX}Buffet Wishes Tatuapé": ("São Paulo", "SP"),
    f"{PREFIX}Cachola": (None, None),
    f"{PREFIX}Buffet Jujuba Jundiaí": ("Jundiaí", "SP"),
    f"{PREFIX}Sítio, Mogi das Cruzes": ("Mogi das Cruzes", "SP"),
}
chamadas_geocode: list[str] = []


def _fake_cidade(endereco: str):
    chamadas_geocode.append(endereco)
    return GEOCODE.get(endereco, (None, None))


def _fake_travel(event, _settings):
    event.travel_distance_km = 42.0
    event.travel_time_minutes = 55
    return {"distance_km": 42.0}


maps.cidade_do_endereco = _fake_cidade
cal_routes._fetch_travel_data = _fake_travel
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


def _login(c, user: User) -> None:
    r = c.post("/api/auth/login", json={"email": user.email, "password": SENHA})
    _garante(r.status_code == 200, f"login → {r.status_code}")


def _payload(sufixo: str, location: str, *, dias: int = 45) -> dict:
    d = (now_sp().date() + timedelta(days=dias)).isoformat()
    return {
        "title": f"{PREFIX}{sufixo}", "event_type": "R&I", "date": d, "start": "15:00", "end": "17:00",
        "location": location, "description": "", "needs_rehearsal": False,
        "sale_value": 3000, "sale_value_gross": 3000, "transport_value": 0, "acrescimo_value": 0,
        "with_invoice": False, "is_cortesia_permuta": False, "seller_id": estado["sa"].id,
        "sale_date": None, "payment_method": None, "payment_installments": None, "payment_due_date": None,
        "orcamento_history_id": None, "duracao": "1", "characters": [], "orc_caches": [], "acrescimos": [],
        "client_pairs": [], "observations": [],
    }


def _flag(eid: int):
    return _no_banco("SELECT is_outside_sp, travel_distance_km FROM calendar_events WHERE id = :i", i=eid)[0]


def _evento_orm(sufixo: str, location: str, flag, *, dias: int = 50) -> CalendarEvent:
    inicio = datetime.combine(now_sp().date() + timedelta(days=dias), datetime.min.time()).replace(hour=15)
    ev = CalendarEvent(
        title=f"{PREFIX}{sufixo}", start_at=inicio, end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}{uuid.uuid4().hex[:8]}", source="platform", location=location,
        is_outside_sp=flag,
    )
    db.session.add(ev)
    db.session.flush()
    role = EventRole(event_id=ev.id, character_name="Elsa", role_type="character")
    db.session.add(role)
    db.session.commit()
    return ev


def preparar() -> None:
    limpar()
    user = User(name=f"{PREFIX}sa", email=f"{PREFIX}sa@manto.local", is_active=True, has_access=True)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=RoleName.SUPERADMIN).one())
    db.session.add(user)
    db.session.commit()
    estado["sa"] = user


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
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ───────────────────────────── cenários ─────────────────────────────

def cen_01_lookup() -> None:
    f = cal_routes._lookup_sp_status
    _garante(f(f"{PREFIX}Fazenda Boa Vista, Porto Feliz") is True, "Porto Feliz devia ser fora")
    _garante(f(f"{PREFIX}Buffet Wishes Tatuapé") is False, "Tatuapé (São Paulo) devia ser dentro")
    _garante(f(f"{PREFIX}Cachola") is None, "sem cidade no Google e sem 'São Paulo' devia ser desconhecido")
    _garante(f(f"{PREFIX}Cachola, São Paulo") is False, "texto com 'São Paulo' devia cair no fallback dentro")
    _garante(f("") is None, "vazio devia ser desconhecido")


def cen_02_criacao_classifica() -> None:
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.post("/api/events", json=_payload("criado fora", f"{PREFIX}Buffet Jujuba Jundiaí"))
        _garante(r.status_code == 201, f"POST → {r.status_code} {r.get_data(as_text=True)[:200]}")
        estado["ev_fora"] = r.get_json()["event"]["id"] if "event" in r.get_json() else r.get_json()["id"]
    flag, km = _flag(estado["ev_fora"])
    _garante(flag is True and km == 42.0, f"criação: flag={flag} km={km}")


def cen_03_patch_reclassifica() -> None:
    eid = estado["ev_fora"]
    corpo = _payload("criado fora", f"{PREFIX}Buffet Wishes Tatuapé")
    for k in ("orcamento_history_id", "duracao", "orc_caches", "acrescimos", "observations"):
        corpo.pop(k, None)
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{eid}", json=corpo)
        _garante(r.status_code == 200, f"PATCH → {r.status_code} {r.get_data(as_text=True)[:200]}")
        _garante(_flag(eid)[0] is False, "trocar o endereço para São Paulo não reclassificou")
        # Endereço igual + flag conhecida: não consulta o Google.
        antes = len(chamadas_geocode)
        r = c.patch(f"/api/events/{eid}", json=corpo)
        _garante(r.status_code == 200 and len(chamadas_geocode) == antes, "endereço igual e flag conhecida consultou o Google")
    # Endereço igual + flag desconhecida (legado): cura.
    ev = _evento_orm("legado desconhecido", f"{PREFIX}Sítio, Mogi das Cruzes", None)
    corpo2 = _payload("legado desconhecido", f"{PREFIX}Sítio, Mogi das Cruzes", dias=50)
    for k in ("orcamento_history_id", "duracao", "orc_caches", "acrescimos", "observations"):
        corpo2.pop(k, None)
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.patch(f"/api/events/{ev.id}", json=corpo2)
        _garante(r.status_code == 200, f"PATCH legado → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(_flag(ev.id)[0] is True, "flag desconhecida não foi curada na edição")


def cen_04_marcar_transporte() -> None:
    desconhecido = _evento_orm("desconhecido", f"{PREFIX}Cachola", None)
    dentro = _evento_orm("dentro", f"{PREFIX}Buffet Wishes Tatuapé", False)
    fora = _evento_orm("fora", f"{PREFIX}Fazenda Boa Vista, Porto Feliz", True)
    papel = {ev.id: EventRole.query.filter_by(event_id=ev.id).first().id for ev in (desconhecido, dentro, fora)}
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.post(f"/api/roles/{papel[desconhecido.id]}/transporte")
        _garante(r.status_code == 200, f"marcar em desconhecido → {r.status_code} {r.get_data(as_text=True)[:200]}")
        flag, km = _flag(desconhecido.id)
        _garante(flag is True and km == 42.0, f"marcar não classificou como fora: {flag}/{km}")
        _garante(_no_banco("SELECT does_transport FROM event_roles WHERE id = :i", i=papel[desconhecido.id])[0][0] is True, "marcação não gravou")
        r = c.post(f"/api/roles/{papel[dentro.id]}/transporte")
        _garante(r.status_code == 400, f"marcar dentro de SP → {r.status_code}, esperava 400")
        r = c.post(f"/api/roles/{papel[fora.id]}/transporte")
        _garante(r.status_code == 200, f"marcar fora → {r.status_code}")


def cen_05_estimar_reclassifica() -> None:
    ev = _evento_orm("estimar", f"{PREFIX}Buffet Jujuba Jundiaí", None)
    with app.test_client() as c:
        _login(c, estado["sa"])
        r = c.post(f"/api/events/{ev.id}/travel-estimate")
        _garante(r.status_code == 200, f"estimar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    flag, km = _flag(ev.id)
    _garante(flag is True and km == 42.0, f"estimar não reclassificou: {flag}/{km}")


def cen_06_script() -> None:
    # O script roda em processo próprio, sem os dublês: aqui ele só precisa provar dry-run × execute
    # com um endereço que o fallback por texto resolve sem Google ("São Paulo" no texto).
    ev = _evento_orm("script", f"{PREFIX}Salão, São Paulo - SP", None)
    script = REPO_ROOT / "specs" / "239b-hotfix-carrinho-fora-de-sp" / "reclassificar_fora_de_sp.py"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    saida = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, env=env, cwd=REPO_ROOT, encoding="utf-8")
    _garante(saida.returncode == 0 and "Nada gravado" in saida.stdout, f"dry-run: {saida.stderr[-300:]}")
    _garante(_flag(ev.id)[0] is None, "dry-run gravou")
    saida = subprocess.run([sys.executable, str(script), "--execute"], capture_output=True, text=True, env=env, cwd=REPO_ROOT, encoding="utf-8")
    _garante(saida.returncode == 0, f"execute: {saida.stderr[-300:]}")
    _garante(_flag(ev.id)[0] is False, f"execute não classificou pelo texto: {_flag(ev.id)}")
    print(f"         ({saida.stdout.strip().splitlines()[-2]})")


def cen_07_limpeza() -> None:
    limpar()
    _garante(CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0, "evento sobrou")


def main() -> int:
    print("Hotfix 239b — carrinho de transporte e a classificação fora de SP")
    with app.app_context():
        preparar()
        try:
            cenario("1. _lookup_sp_status com Geocoding (fora / dentro / desconhecido / texto)", cen_01_lookup)
            cenario("2. criação pela API classifica e estima trajeto", cen_02_criacao_classifica)
            cenario("3. PATCH reclassifica ao trocar endereço e cura flag desconhecida", cen_03_patch_reclassifica)
            cenario("4. marcar transporte: desconhecido vira fora; dentro → 400; fora → 200", cen_04_marcar_transporte)
            cenario("5. 'Estimar via Google Maps' reclassifica", cen_05_estimar_reclassifica)
            cenario("6. script: dry-run não grava; execute classifica", cen_06_script)
        finally:
            cenario("7. limpeza", cen_07_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
