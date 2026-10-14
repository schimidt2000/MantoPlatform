"""Verificação do hotfix 215b — a Comercial não muda mais a taxa nem troca o vendedor na tela nova.

Cenários (spec.md):
 1. O detalhe do evento diz à tela o que travar: Comercial não muda taxa nem troca vendedor;
    Superadmin muda os dois.
 2. DEVE FALHAR: Comercial muda a taxa pela aba Comercial → 403, taxa gravada intacta.
 3. Comercial salva a aba Comercial com a taxa e o vendedor de sempre (o form manda o corpo
    inteiro) → 200, a venda muda.
 4. DEVE FALHAR: Comercial troca o vendedor pela aba Comercial → 403, vendedor intacto.
 5. DEVE FALHAR: Comercial troca o vendedor pela edição completa → 403, vendedor intacto.
 6. Comercial preenche o vendedor de evento que não tem → 200.
 7. Superadmin muda taxa e vendedor → 200, e a comissão a pagar acompanha.
 8. Comercial reenviando a taxa que o Superadmin pôs (7 × 7.0) → 200.
 9. Limpeza.

O Google Agenda é DUBLADO antes de qualquer cenário — nada chega à agenda real. As requisições
correm FORA do `app.app_context()`; a conferência é por conexão separada (o autoflush esconde falta
de commit). Ids gerados aqui têm o prefixo `__v215b_`.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\215b-hotfix-taxa-e-vendedor\\verify_215b.py
"""

from __future__ import annotations

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
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, Role, User  # noqa: E402

PREFIX = "__v215b_"
SENHA = "verify-215b-senha"

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
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _cliente(papel: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": estado[papel]["email"], "password": SENHA})
    _garante(r.status_code == 200, f"login {papel} → {r.status_code}")
    return c


def _evento(eid: int):
    return _no_banco(
        "SELECT sale_value, seller_id, commission_rate FROM calendar_events WHERE id = :i", i=eid
    )[0]


def _comissao_viva(eid: int):
    rows = _no_banco(
        "SELECT seller_id, amount, status FROM commission_payments "
        "WHERE event_id = :i AND status <> 'cancelado' ORDER BY id",
        i=eid,
    )
    return rows[0] if rows else None


def _corpo_comercial(eid: int, **mudar) -> dict:
    """O corpo que a aba Comercial manda: tudo, inclusive os campos travados com o valor gravado."""
    venda, vendedor, taxa = _evento(eid)
    corpo = {
        "sale_value": float(venda) if venda is not None else None,
        "sale_value_gross": float(venda) if venda is not None else None,
        "transport_value": 0,
        "with_invoice": False,
        "is_cortesia_permuta": False,
        "seller_id": vendedor,
        "sale_date": now_sp().date().isoformat(),
        "commission_rate": taxa,
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
    }
    corpo.update(mudar)
    return corpo


def _corpo_edicao(sufixo: str, vendedor: int, venda: float, dias: int = 60) -> dict:
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
        "seller_id": vendedor,
        "sale_date": now_sp().date().isoformat(),
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
        "characters": [],
        "clients": [],
    }


# ── preparo e limpeza ───────────────────────────────────────────────────────────────────────────
def _novo_usuario(apelido: str, papel: str) -> dict:
    email = f"{PREFIX}{apelido}@manto.local"
    user = User(
        name=f"{PREFIX}{apelido}",
        email=email,
        is_active=True,
        has_access=True,
        receives_commission=True,
    )
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(user)
    db.session.flush()
    return {"id": user.id, "email": email}


def _novo_evento(sufixo: str, *, vendedor: int | None, dias: int) -> int:
    inicio = datetime.combine(now_sp().date() + timedelta(days=dias), datetime.min.time()).replace(
        hour=15
    )
    ev = CalendarEvent(
        title=f"{PREFIX}(R&I) {sufixo}",
        start_at=inicio,
        end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}{sufixo}",
        source="platform",
        sale_value=Decimal("3000"),
        sale_value_gross=Decimal("3000"),
        sale_date=now_sp().date(),
        seller_id=vendedor,
    )
    db.session.add(ev)
    db.session.flush()
    return ev.id


def preparar() -> None:
    with app.app_context():
        limpar()
        estado["sa"] = _novo_usuario("sa", RoleName.SUPERADMIN)
        estado["comercial"] = _novo_usuario("comercial", RoleName.COMERCIAL)
        estado["comercial2"] = _novo_usuario("comercial2", RoleName.COMERCIAL)
        estado["ev"] = _novo_evento("com vendedor", vendedor=estado["comercial"]["id"], dias=60)
        estado["ev_vazio"] = _novo_evento("sem vendedor", vendedor=None, dias=61)
        db.session.commit()


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
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ── cenários ────────────────────────────────────────────────────────────────────────────────────
def cen_01_detalhe_diz_o_que_travar() -> None:
    eid = estado["ev"]
    venda = _cliente("comercial").get(f"/api/events/{eid}").get_json()["venda"]
    _garante(
        venda["pode_mudar_taxa"] is False, f"Comercial pode mudar taxa? {venda['pode_mudar_taxa']}"
    )
    _garante(
        venda["pode_trocar_vendedor"] is False,
        f"Comercial pode trocar? {venda['pode_trocar_vendedor']}",
    )
    venda = _cliente("sa").get(f"/api/events/{eid}").get_json()["venda"]
    _garante(
        venda["pode_mudar_taxa"] is True and venda["pode_trocar_vendedor"] is True,
        f"SA travado: {venda}",
    )


def cen_02_comercial_nao_muda_taxa() -> None:
    eid = estado["ev"]
    r = _cliente("comercial").patch(
        f"/api/events/{eid}/comercial", json=_corpo_comercial(eid, commission_rate=9)
    )
    _garante(
        r.status_code == 403,
        f"Comercial mudou a taxa: {r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    _garante(
        "commission_rate" in ((r.get_json().get("error") or {}).get("fields") or {}),
        f"403 sem o campo: {r.get_json()}",
    )
    _garante(_evento(eid)[2] is None, f"a taxa mudou no banco: {_evento(eid)}")


def cen_03_comercial_salva_com_campos_travados() -> None:
    eid = estado["ev"]
    r = _cliente("comercial").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=3200, sale_value_gross=3200),
    )
    _garante(
        r.status_code == 200,
        f"salvar com taxa e vendedor iguais → {r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    venda, vendedor, taxa = _evento(eid)
    _garante(
        float(venda) == 3200 and vendedor == estado["comercial"]["id"] and taxa is None,
        f"{_evento(eid)}",
    )


def cen_04_comercial_nao_troca_vendedor_na_aba() -> None:
    eid = estado["ev"]
    r = _cliente("comercial").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, seller_id=estado["comercial2"]["id"]),
    )
    _garante(r.status_code == 403, f"Comercial trocou o vendedor: {r.status_code}")
    _garante(
        "seller_id" in ((r.get_json().get("error") or {}).get("fields") or {}),
        f"403 sem o campo: {r.get_json()}",
    )
    _garante(_evento(eid)[1] == estado["comercial"]["id"], f"vendedor mudou: {_evento(eid)}")


def cen_05_comercial_nao_troca_vendedor_na_edicao() -> None:
    eid = estado["ev"]
    corpo = _corpo_edicao("(R&I) com vendedor", estado["comercial2"]["id"], 3200)
    r = _cliente("comercial").patch(f"/api/events/{eid}", json=corpo)
    _garante(
        r.status_code == 403,
        f"edição completa trocou o vendedor: {r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    _garante(_evento(eid)[1] == estado["comercial"]["id"], f"vendedor mudou: {_evento(eid)}")
    # O mesmo corpo com o vendedor de sempre passa (prova que o 403 é do vendedor, e não do corpo).
    corpo["seller_id"] = estado["comercial"]["id"]
    r = _cliente("comercial").patch(f"/api/events/{eid}", json=corpo)
    _garante(
        r.status_code == 200,
        f"edição com o mesmo vendedor → {r.status_code} {r.get_data(as_text=True)[:300]}",
    )


def cen_06_comercial_preenche_o_vazio() -> None:
    eid = estado["ev_vazio"]
    r = _cliente("comercial").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, seller_id=estado["comercial2"]["id"]),
    )
    _garante(
        r.status_code == 200,
        f"preencher vendedor vazio → {r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    _garante(_evento(eid)[1] == estado["comercial2"]["id"], f"vendedor não gravou: {_evento(eid)}")


def cen_07_superadmin_muda_os_dois() -> None:
    eid = estado["ev"]
    r = _cliente("sa").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, seller_id=estado["comercial2"]["id"], commission_rate=7),
    )
    _garante(r.status_code == 200, f"SA → {r.status_code} {r.get_data(as_text=True)[:200]}")
    venda, vendedor, taxa = _evento(eid)
    _garante(vendedor == estado["comercial2"]["id"] and float(taxa) == 7, f"{_evento(eid)}")
    cp = _comissao_viva(eid)
    _garante(
        cp is not None and cp[0] == estado["comercial2"]["id"],
        f"comissão não foi ao novo vendedor: {cp}",
    )
    _garante(Decimal(str(cp[1])) == Decimal("224.00"), f"comissão não usa 7% de 3.200: {cp}")


def cen_08_taxa_reenviada_igual_passa() -> None:
    eid = estado["ev"]
    corpo = _corpo_comercial(eid, commission_rate=7.0)
    corpo["commission_rate"] = 7  # inteiro, como o input numérico manda
    r = _cliente("comercial2").patch(f"/api/events/{eid}/comercial", json=corpo)
    _garante(
        r.status_code == 200, f"7 × 7.0 recusado: {r.status_code} {r.get_data(as_text=True)[:200]}"
    )


def cen_09_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(
            CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0,
            "evento sobrou",
        )
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")


def main() -> int:
    print("Hotfix 215b — taxa e vendedor da comissão na tela nova")
    preparar()
    try:
        cenario(
            "1. o detalhe diz o que travar (Comercial × Superadmin)",
            cen_01_detalhe_diz_o_que_travar,
        )
        cenario("2. DEVE FALHAR: Comercial muda a taxa → 403", cen_02_comercial_nao_muda_taxa)
        cenario(
            "3. Comercial salva com taxa e vendedor iguais → 200",
            cen_03_comercial_salva_com_campos_travados,
        )
        cenario(
            "4. DEVE FALHAR: Comercial troca o vendedor na aba → 403",
            cen_04_comercial_nao_troca_vendedor_na_aba,
        )
        cenario(
            "5. DEVE FALHAR: Comercial troca o vendedor na edição completa → 403",
            cen_05_comercial_nao_troca_vendedor_na_edicao,
        )
        cenario("6. Comercial preenche vendedor vazio → 200", cen_06_comercial_preenche_o_vazio)
        cenario(
            "7. Superadmin muda taxa e vendedor; comissão acompanha", cen_07_superadmin_muda_os_dois
        )
        cenario("8. taxa reenviada igual (7 × 7.0) → 200", cen_08_taxa_reenviada_igual_passa)
    finally:
        cenario("9. limpeza", cen_09_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
