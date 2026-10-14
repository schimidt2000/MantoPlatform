"""Verificação do hotfix 267c — o lote de comissão da Planilha não mexe mais no que já foi pago.

Cenário-base: um vendedor com três comissões no ciclo de março/2026 — uma PAGA (R$ 100, paga em
05/04), uma A PAGAR (R$ 50) e uma NO BANCO (R$ 30).

 1. A Planilha parte o item: aberto "S:2026-03" com R$ 80 ("não pago") e "S:2026-03:pago" com R$ 100.
 2. Financeiro marca o aberto "Não pago": o "no banco" volta, e a PAGA continua paga (o defeito:
    voltava a "a pagar" e a ressincronização a recalculava pela venda de hoje).
 3. Financeiro marca o aberto "Pago": as abertas pagam; a data da que já estava paga não muda.
 4. DEVE FALHAR: Financeiro tira o item "— pago" de pago → 403.
 5. DEVE FALHAR: Superadmin sem motivo → 400.
 6. DEVE FALHAR: "No banco" num item pago → 409.
 7. DEVE FALHAR: em massa (API) o item "— pago" não sai de pago.
 8. DEVE FALHAR: a tela antiga de Comissões (Jinja, por linha) não tira linha de pago.
 9. Superadmin desfaz com motivo → as linhas voltam a "a pagar" e o motivo vai ao histórico do evento.
10. Limpeza.

Requisições FORA do `app.app_context()`; conferência por conexão separada. Prefixo `__v267c_`.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\267c-hotfix-trava-do-lote\\verify_267c.py
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from datetime import date, datetime
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
from app.constants import RoleName  # noqa: E402
from app.models import CalendarEvent, CommissionPayment, Role, User  # noqa: E402

PREFIX = "__v267c_"
SENHA = "verify-267c-senha"
INICIO, FIM = date(2026, 3, 1), date(2026, 4, 1)
PAGO_EM = date(2026, 4, 5)

app = create_app()
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


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


def _linhas() -> dict[str, tuple]:
    """`{rótulo: (status, paid_at)}` das três comissões, lidas por conexão separada."""
    rows = _no_banco(
        "SELECT notes, status, paid_at FROM commission_payments WHERE seller_id = :s",
        s=estado["vendedor"]["id"],
    )
    return {r[0]: (r[1], r[2]) for r in rows}


def _item(sufixo: str = "") -> str:
    return f"{estado['vendedor']['id']}:2026-03{sufixo}"


def _set_status(papel: str, item_id: str, status: str, motivo: str | None = None):
    corpo = {"item_type": "commission", "item_id": item_id, "status": status}
    if motivo is not None:
        corpo["motivo"] = motivo
    return _cliente(papel).post("/api/financeiro/pagamentos/set-status", json=corpo)


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


def _comissao(
    rotulo: str, valor: str, status: str, *, evento: int | None, pago_em: date | None = None
) -> None:
    db.session.add(
        CommissionPayment(
            event_id=evento,
            event_title=f"{PREFIX}{rotulo}",
            seller_id=estado["vendedor"]["id"],
            sale_date=date(2026, 3, 10),
            amount=Decimal(valor),
            status=status,
            paid_at=pago_em,
            notes=rotulo,
        )
    )


def preparar() -> None:
    with app.app_context():
        limpar()
        estado["sa"] = _novo_usuario("sa", RoleName.SUPERADMIN)
        estado["fin"] = _novo_usuario("fin", RoleName.FINANCEIRO)
        estado["vendedor"] = _novo_usuario("vendedor", RoleName.COMERCIAL)
        inicio = datetime(2026, 3, 20, 15, 0)
        ev = CalendarEvent(
            title=f"{PREFIX}(R&I) evento da comissão paga",
            start_at=inicio,
            end_at=inicio.replace(hour=17),
            google_event_id=f"{PREFIX}ev",
            source="platform",
        )
        db.session.add(ev)
        db.session.flush()
        estado["ev"] = ev.id
        # Só a paga aponta para o evento: as abertas sem evento não são recalculadas pela
        # ressincronização, e o teste mede só a liquidação.
        _comissao("paga", "100.00", "pago", evento=ev.id, pago_em=PAGO_EM)
        _comissao("a_pagar", "50.00", "a_pagar", evento=None)
        _comissao("no_banco", "30.00", "no_banco", evento=None)
        db.session.commit()


def limpar() -> None:
    ids = [
        r[0]
        for r in _no_banco("SELECT id FROM calendar_events WHERE title LIKE :p", p=f"{PREFIX}%")
    ]
    db.session.execute(
        text("DELETE FROM commission_payments WHERE event_title LIKE :p"), {"p": f"{PREFIX}%"}
    )
    for eid in ids:
        db.session.execute(text("DELETE FROM event_logs WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        ev = db.session.get(CalendarEvent, eid)
        if ev is not None:
            db.session.delete(ev)
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ── cenários ────────────────────────────────────────────────────────────────────────────────────
def cen_01_planilha_parte_o_item() -> None:
    from app.financeiro.routes import _build_commission_items

    with app.app_context():
        itens = _build_commission_items(INICIO, FIM, date(2026, 4, 5), date(2026, 10, 14))
    meus = {i["id"]: i for i in itens if i["id"].startswith(f"{estado['vendedor']['id']}:")}
    _garante(set(meus) == {_item(), _item(":pago")}, f"itens: {list(meus)}")
    aberto, pago = meus[_item()], meus[_item(":pago")]
    _garante(
        Decimal(str(aberto["amount"])) == Decimal("80.00") and aberto["status"] == "nao_pago",
        f"aberto: {aberto}",
    )
    _garante(
        Decimal(str(pago["amount"])) == Decimal("100.00") and pago["status"] == "pago",
        f"pago: {pago}",
    )
    _garante(pago["event_title"].endswith("— pago"), f"rótulo: {pago['event_title']}")


def cen_02_nao_pago_nao_mexe_na_paga() -> None:
    r = _set_status("fin", _item(), "nao_pago")
    _garante(r.status_code == 200, f"→ {r.status_code} {r.get_data(as_text=True)[:200]}")
    linhas = _linhas()
    _garante(linhas["paga"][0] == "pago", f"a paga voltou: {linhas['paga']}")
    _garante(linhas["no_banco"][0] == "a_pagar", f"no banco não voltou: {linhas['no_banco']}")


def cen_03_pago_nao_recarimba_a_paga() -> None:
    r = _set_status("fin", _item(), "pago")
    _garante(r.status_code == 200, f"→ {r.status_code}")
    linhas = _linhas()
    _garante(linhas["a_pagar"][0] == "pago" and linhas["no_banco"][0] == "pago", f"{linhas}")
    _garante(linhas["paga"] == ("pago", PAGO_EM), f"a data da paga mudou: {linhas['paga']}")


def cen_04_financeiro_nao_desfaz() -> None:
    r = _set_status("fin", _item(":pago"), "nao_pago", motivo="teste")
    _garante(r.status_code == 403, f"Financeiro desfez: {r.status_code}")
    _garante(all(s == "pago" for s, _ in _linhas().values()), f"{_linhas()}")


def cen_05_superadmin_sem_motivo() -> None:
    r = _set_status("sa", _item(":pago"), "nao_pago")
    _garante(r.status_code == 400, f"desfez sem motivo: {r.status_code}")
    _garante(all(s == "pago" for s, _ in _linhas().values()), f"{_linhas()}")


def cen_06_no_banco_em_item_pago() -> None:
    r = _set_status("sa", _item(":pago"), "no_banco", motivo="teste")
    _garante(r.status_code == 409, f"pago → no banco: {r.status_code}")
    _garante(all(s == "pago" for s, _ in _linhas().values()), f"{_linhas()}")


def cen_07_em_massa_nao_desfaz() -> None:
    r = _cliente("sa").post(
        "/api/financeiro/pagamentos/bulk-action",
        json={
            "action": "nao_pago",
            "role_ids": [],
            "salary_ids": [],
            "expense_ids": [],
            "commission_ids": [_item(":pago")],
            "month": "2026-04",
        },
    )
    _garante(
        r.status_code in (200, 400), f"em massa → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    _garante(all(s == "pago" for s, _ in _linhas().values()), f"em massa desfez: {_linhas()}")


def cen_08_jinja_por_linha_nao_desfaz() -> None:
    cp_id = _no_banco(
        "SELECT id FROM commission_payments WHERE seller_id = :s AND notes = 'paga'",
        s=estado["vendedor"]["id"],
    )[0][0]
    r = _cliente("fin").post(
        "/financeiro/comissoes/set-status", data={"cp_id": cp_id, "status": "a_pagar"}
    )
    _garante(r.status_code in (302, 303), f"Jinja → {r.status_code}")
    _garante(_linhas()["paga"][0] == "pago", f"Jinja tirou de pago: {_linhas()['paga']}")


def cen_09_superadmin_desfaz_com_motivo() -> None:
    r = _set_status("sa", _item(":pago"), "nao_pago", motivo="marcado por engano no teste")
    _garante(r.status_code == 200, f"→ {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(all(s == "a_pagar" and p is None for s, p in _linhas().values()), f"{_linhas()}")
    logs = _no_banco("SELECT message FROM event_logs WHERE event_id = :i", i=estado["ev"])
    _garante(
        any("marcado por engano no teste" in m[0] for m in logs), f"histórico sem o motivo: {logs}"
    )


def cen_10_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(
            CommissionPayment.query.filter(CommissionPayment.event_title.like(f"{PREFIX}%")).count()
            == 0,
            "comissão sobrou",
        )
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")


def main() -> int:
    print("Hotfix 267c — o lote de comissão não mexe no que já foi pago")
    preparar()
    try:
        cenario(
            "1. a Planilha parte o item: aberto R$ 80 e '— pago' R$ 100",
            cen_01_planilha_parte_o_item,
        )
        cenario("2. 'Não pago' no aberto não devolve a paga", cen_02_nao_pago_nao_mexe_na_paga)
        cenario("3. 'Pago' no aberto não recarimba a paga", cen_03_pago_nao_recarimba_a_paga)
        cenario("4. DEVE FALHAR: Financeiro desfaz o pago → 403", cen_04_financeiro_nao_desfaz)
        cenario("5. DEVE FALHAR: Superadmin sem motivo → 400", cen_05_superadmin_sem_motivo)
        cenario("6. DEVE FALHAR: pago → no banco → 409", cen_06_no_banco_em_item_pago)
        cenario("7. DEVE FALHAR: em massa não desfaz o pago", cen_07_em_massa_nao_desfaz)
        cenario(
            "8. DEVE FALHAR: Jinja por linha não tira de pago", cen_08_jinja_por_linha_nao_desfaz
        )
        cenario(
            "9. Superadmin desfaz com motivo; motivo no histórico",
            cen_09_superadmin_desfaz_com_motivo,
        )
    finally:
        cenario("10. limpeza", cen_10_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
