"""Verificação da feature 305 — o BV do orçamento chega ao evento.

A tabela de cenários está na `spec.md` (seção "Verificação"); a numeração é a do plano do backlog
(28, 29, 30 e 41 saíram com o script do passado). Escrito ANTES do núcleo (Princípio VIII): a primeira
rodada fica em `verify_305_primeira_falha.txt`.

O Google é DUBLADO (insert/update/delete e o tempo de deslocamento) antes de qualquer cenário, e o
dublê conta as chamadas — o cenário 31 prova que a recusa do PIX acontece ANTES do Google. Eventos são
R&I (SHOW cria ensaio e e-mail). Requisições correm FORA do `app.app_context()`; toda conferência de
escrita é por conexão separada, e a comissão é lida SEM abrir a Planilha (o `_resync` da Planilha
esconderia a coleção velha). Prefixo `__v305_`; limpeza no `finally`.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\305-bv-do-orcamento-no-evento\\verify_305.py [--regressao]

`--regressao` roda também o cenário 27 (os verifies de 273, 267b, 301, 215b, 267c e 267, em subprocesso).
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import threading
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

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
from app.models import CalendarEvent, OrcamentoHistory, Role, SiteSetting, User  # noqa: E402

PREFIX = "__v305_"
SENHA = "verify-305-senha"
CENTAVO = Decimal("0.01")
PIX = "verify305-pix@exemplo.test"
QUEM = f"{PREFIX}Buffet Parceiro"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês do Google (com contador) ─────────────────────────────────────────────────────────────
GOOGLE = {"insert": 0}


def _fake_insert(*_a, **_k):
    GOOGLE["insert"] += 1
    return {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}", "htmlLink": "https://fake.local"}


maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_service.insert_event = _fake_insert
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = _fake_insert
for _nome in ("update_event", "delete_event"):
    if hasattr(cal_routes, _nome):
        setattr(cal_routes, _nome, lambda *a, **k: None)


# ── utilidades ──────────────────────────────────────────────────────────────────────────────────
def q(x) -> Decimal:
    return Decimal(str(x)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


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
        ultima = traceback.format_exc().strip().splitlines()[-1]
        resultados.append((nome, False, ultima))
        print(f"  FALHA  {nome}: {str(exc)[:400]}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _deve_quebrar(fn: Callable[[], None], rotulo: str) -> None:
    """Prova por mutação: com a regra errada ligada, o cenário TEM de falhar."""
    try:
        fn()
    except AssertionError:
        return
    raise AssertionError(f"mutação '{rotulo}' passou despercebida — o cenário não protege a regra")


def _cliente(papel: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": estado[papel]["email"], "password": SENHA})
    _garante(r.status_code == 200, f"login {papel} → {r.status_code}")
    return c


def _erro(r) -> dict:
    corpo = r.get_json(silent=True) or {}
    return corpo.get("error") or {}


def _linhas(eid: int) -> list[dict]:
    rows = _no_banco(
        "SELECT id, tipo, descricao, is_percent, value, amount_brl, is_bv, bv_recipient, bv_pix, "
        "bv_payment_status FROM event_acrescimos WHERE event_id = :i ORDER BY id",
        i=eid,
    )
    chaves = (
        "id",
        "tipo",
        "descricao",
        "is_percent",
        "value",
        "amount_brl",
        "is_bv",
        "bv_recipient",
        "bv_pix",
        "bv_payment_status",
    )
    return [dict(zip(chaves, r, strict=True)) for r in rows]


def _bvs(eid: int) -> list[dict]:
    return [linha for linha in _linhas(eid) if linha["is_bv"]]


def _evento(eid: int) -> dict:
    r = _no_banco(
        "SELECT sale_value, sale_value_gross, with_invoice, orcamento_history_id, seller_id, cancelled_at "
        "FROM calendar_events WHERE id = :i",
        i=eid,
    )[0]
    return dict(zip(("venda", "bruto", "nota", "orc", "vendedor", "cancelado"), r, strict=True))


def _comissao(eid: int):
    rows = _no_banco(
        "SELECT amount, status FROM commission_payments WHERE event_id = :i AND status <> 'cancelado' "
        "ORDER BY id",
        i=eid,
    )
    return rows[0] if rows else None


def _taxa() -> Decimal:
    with app.app_context():
        s = db.session.get(SiteSetting, 1) or SiteSetting.query.first()
        return Decimal(
            str(s.default_commission_rate if s and s.default_commission_rate is not None else 2)
        )


def _comissao_esperada(venda, bv) -> Decimal:
    return q((Decimal(str(venda)) - Decimal(str(bv))) * _taxa() / Decimal("100"))


def _logs(eid: int) -> list[str]:
    return [
        r[0]
        for r in _no_banco("SELECT message FROM event_logs WHERE event_id = :i ORDER BY id", i=eid)
    ]


def _contar_eventos(titulo: str) -> int:
    return _no_banco("SELECT count(*) FROM calendar_events WHERE title = :t", t=titulo)[0][0]


# ── fixtures ────────────────────────────────────────────────────────────────────────────────────
def _usuario(apelido: str, papel: str) -> dict:
    email = f"{PREFIX}{apelido}@manto.local"
    u = User(
        name=f"{PREFIX}{apelido}",
        email=email,
        is_active=True,
        has_access=True,
        receives_commission=True,
    )
    u.set_password(SENHA)
    u.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(u)
    db.session.flush()
    return {"id": u.id, "email": email}


def _orc(
    rotulo: str,
    *,
    totais: tuple,
    acrescimos: list[dict],
    nota: bool = False,
    dono: str = "sa",
    personalizado: bool = False,
    duracao_custom: int = 0,
    total_custom: float | None = None,
    com_valores_brl: list | None = None,
    snapshot_cru: str | None = None,
) -> int:
    """Orçamento fictício congelado. `totais` = (1h, 2h, 3h, 4h)."""
    acr = []
    for i, a in enumerate(acrescimos):
        linha = {
            "tipo": a["tipo"],
            "descricao": a.get("descricao", ""),
            "is_percent": a["is_percent"],
            "value": a["value"],
            "is_bv": a["tipo"] == "BV",
        }
        if com_valores_brl is not None and com_valores_brl[i] is not None:
            linha["valores_brl"] = com_valores_brl[i]
        acr.append(linha)
    snap = {
        "performers": [],
        "coordenador_qty": 1,
        "nota_fiscal": nota,
        "acrescimos": acr,
        "personalizado_ativo": personalizado,
        "duracao_custom": str(duracao_custom),
        "event_time": "15:00",
        "fora_sp": False,
    }
    with app.app_context():
        e = OrcamentoHistory(
            user_id=estado[dono]["id"],
            client_name=f"{PREFIX}{rotulo}",
            event_location=f"{PREFIX}Salão",
            event_date=(now_sp().date() + timedelta(days=60)).isoformat(),
            total_1h=Decimal(str(totais[0])),
            total_2h=Decimal(str(totais[1])),
            total_3h=Decimal(str(totais[2])),
            total_4h=Decimal(str(totais[3])),
            has_show=False,
            form_snapshot=snapshot_cru if snapshot_cru is not None else json.dumps(snap),
            result_snapshot=json.dumps({"total_custom": total_custom})
            if total_custom is not None
            else None,
        )
        db.session.add(e)
        db.session.commit()
        return e.id


def _orc_d2(rotulo: str) -> int:
    """D2: preço 1.000 (1h), BV 10%, nota → 1.309,52. Bases 1.000/1.500/2.000/2.500."""
    tot = tuple(
        float(q(b * Decimal("1.1") / Decimal("0.84")))
        for b in map(Decimal, ("1000", "1500", "2000", "2500"))
    )
    return _orc(
        rotulo, totais=tot, nota=True, acrescimos=[{"tipo": "BV", "is_percent": True, "value": 10}]
    )


def _orc_2031(rotulo: str, *, dono: str = "sa") -> int:
    """Como o 2031: sem nota, BV 10%; 2h = 1.622,50 (BV cheio 147,50)."""
    return _orc(
        rotulo,
        totais=(1100, 1622.50, 2200, 2750),
        dono=dono,
        acrescimos=[{"tipo": "BV", "is_percent": True, "value": 10}],
    )


def _orc_fixo(rotulo: str) -> int:
    """BV fixo de R$ 10,00, sem nota; preços 1.000/1.500/2.000/2.500."""
    return _orc(
        rotulo,
        totais=(1010, 1510, 2010, 2510),
        acrescimos=[{"tipo": "BV", "is_percent": False, "value": 10}],
    )


def _orc_2407(rotulo: str) -> int:
    """Como o 2407: Outro 13.800 + Outro 3.500 + BV 10%, sem nota; 2h = 22.085 (BV 435)."""
    bases = (4000, 4350, 5000, 6000)
    tot = tuple(b + b * 0.1 + 17300 for b in bases)
    return _orc(
        rotulo,
        totais=tot,
        acrescimos=[
            {"tipo": "Outro", "descricao": "Palco", "is_percent": False, "value": 13800},
            {"tipo": "Outro", "descricao": "Som", "is_percent": False, "value": 3500},
            {"tipo": "BV", "is_percent": True, "value": 10},
        ],
    )


def _orc_sem(rotulo: str) -> int:
    return _orc(rotulo, totais=(1000, 1500, 2000, 2500), acrescimos=[])


def _corpo_criacao(
    titulo: str,
    orc: int | None,
    *,
    venda,
    bruto=None,
    duracao: str | None = "2",
    dias: int = 60,
    inicio: str = "15:00",
    fim: str = "17:00",
    **extra,
) -> dict:
    d = (now_sp().date() + timedelta(days=dias)).isoformat()
    corpo = {
        "title": titulo,
        "event_type": "R&I",
        "date": d,
        "start": inicio,
        "end": fim,
        "location": f"{PREFIX}Salão",
        "description": "",
        "needs_rehearsal": False,
        "sale_value": venda,
        "sale_value_gross": bruto if bruto is not None else venda,
        "transport_value": 0,
        "acrescimo_value": 0,
        "with_invoice": False,
        "is_cortesia_permuta": False,
        "seller_id": estado["sa"]["id"],
        "sale_date": None,
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
        "orcamento_history_id": orc,
        "characters": [],
        "orc_caches": [],
        "acrescimos": [],
        "client_pairs": [],
        "observations": [],
    }
    if duracao is not None:
        corpo["duracao"] = duracao
    corpo.update(extra)
    return corpo


def _criar(papel: str, corpo: dict):
    r = _cliente(papel).post("/api/events", json=corpo)
    if r.status_code != 201:
        return r, None
    j = r.get_json()
    return r, (j.get("event") or j).get("id")


def _evento_google(
    rotulo: str, *, dias: int = 60, horas: int = 2, venda=None, nota=False, mes_passado=False
) -> int:
    with app.app_context():
        base = now_sp().date() + timedelta(days=dias)
        if mes_passado:
            base = now_sp().date().replace(day=1) - timedelta(days=10)
        inicio = datetime.combine(base, datetime.min.time()).replace(hour=15)
        ev = CalendarEvent(
            title=f"{PREFIX}(R&I) {rotulo}",
            event_type="R&I",
            start_at=inicio,
            end_at=inicio + timedelta(hours=horas),
            google_event_id=f"{PREFIX}{uuid.uuid4().hex[:8]}",
            source="google_calendar",
            location=f"{PREFIX}Salão",
            sale_value=Decimal(str(venda)) if venda is not None else None,
            sale_value_gross=Decimal(str(venda)) if venda is not None else None,
            with_invoice=nota,
            seller_id=estado["sa"]["id"] if venda is not None else None,
        )
        db.session.add(ev)
        db.session.commit()
        return ev.id


def _bv_item(valor, *, pct=False, quem=QUEM, pix=PIX, id_=None, descricao=None, tipo="BV") -> dict:
    item = {"tipo": tipo, "is_percent": pct, "value": valor, "bv_recipient": quem, "bv_pix": pix}
    if id_ is not None:
        item["id"] = id_
    if descricao is not None:
        item["descricao"] = descricao
    return item


def _put(papel: str, eid: int, itens: list[dict]):
    return _cliente(papel).put(f"/api/events/{eid}/acrescimos", json={"items": itens})


def _como_carregou(eid: int) -> list[dict]:
    """O que a tela nova manda ao salvar sem mexer: o que o GET devolveu."""
    acr = _cliente("com").get(f"/api/events/{eid}").get_json().get("acrescimos") or []
    return [
        {
            k: a.get(k)
            for k in ("id", "tipo", "descricao", "is_percent", "value", "bv_recipient", "bv_pix")
        }
        for a in acr
    ]


def _corpo_comercial(eid: int, **mudar) -> dict:
    ev = _evento(eid)
    corpo = {
        "sale_value": float(ev["venda"]) if ev["venda"] is not None else None,
        "sale_value_gross": float(ev["bruto"]) if ev["bruto"] is not None else None,
        "transport_value": 0,
        "with_invoice": bool(ev["nota"]),
        "is_cortesia_permuta": False,
        "seller_id": ev["vendedor"],
        "sale_date": now_sp().date().isoformat(),
        "commission_rate": None,
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
    }
    corpo.update(mudar)
    return corpo


def _set_status_bv(eid: int, status: str) -> None:
    with _externo.begin() as conn:
        conn.execute(
            text(
                "UPDATE event_acrescimos SET bv_payment_status = :s WHERE event_id = :i AND is_bv"
            ),
            {"s": status, "i": eid},
        )


def _corte(quando: datetime | None) -> None:
    from app.calendar import orcamento_evento_ops

    orcamento_evento_ops.CORTE_ALERTA_BV = quando


def _pendente(papel: str, eid: int):
    venda = _cliente(papel).get(f"/api/events/{eid}").get_json().get("venda")
    return None if venda is None else venda.get("bv_do_orcamento_pendente")


# ── preparo e limpeza ───────────────────────────────────────────────────────────────────────────
def preparar() -> None:
    with app.app_context():
        limpar()
        for apelido, papel in (
            ("sa", RoleName.SUPERADMIN),
            ("com", RoleName.COMERCIAL),
            ("com2", RoleName.COMERCIAL),
            ("fin", RoleName.FINANCEIRO),
            ("cast", RoleName.CASTING),
            ("a3d", RoleName.ARTISTA_3D),
        ):
            estado[apelido] = _usuario(apelido, papel)
        db.session.commit()
    # O corte do alerta fica bem no passado: tudo o que o verify cria é "depois do deploy" (o TZ do
    # manto_local grava o EventLog em hora de SP, 3h atrás do relógio UTC do created_at).
    _corte(datetime(2000, 1, 1))


def limpar() -> None:
    ids = [
        r[0]
        for r in _no_banco(
            "SELECT id FROM calendar_events WHERE title LIKE :p OR google_event_id LIKE :p",
            p=f"%{PREFIX}%",
        )
    ]
    for eid in ids:
        for tabela in (
            "commission_payments",
            "event_logs",
            "event_roles",
            "event_clients",
            "event_acrescimos",
        ):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        ev = db.session.get(CalendarEvent, eid)
        if ev is not None:
            db.session.delete(ev)
    db.session.commit()
    db.session.execute(
        text("DELETE FROM orcamento_history WHERE client_name LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text("DELETE FROM audit_logs WHERE entity_name LIKE :p"), {"p": f"%{PREFIX}%"}
    )
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ── 1–7 · a conta (pura) ────────────────────────────────────────────────────────────────────────
def _b1(orc_id: int, duracao):
    from app.calendar.orcamento_evento_ops import acrescimos_do_orcamento

    with app.app_context():
        entry = db.session.get(OrcamentoHistory, orc_id)
        return acrescimos_do_orcamento(entry, duracao)


def _bv_de(res) -> Decimal | None:
    bvs = [linha for linha in res["linhas"] if linha["is_bv"]]
    return Decimal(str(bvs[0]["amount_brl"])) if bvs else None


def cen_01_d2() -> None:
    res = _b1(_orc_d2("c01"), 1)
    _garante(_bv_de(res) == Decimal("100.00"), f"D2: {res}")
    _garante(Decimal(str(res["total"])) == Decimal("1309.52"), f"total: {res['total']}")


def cen_02_base_comum() -> None:
    # preço 1.000 + BV 10% + Outro fixo 300 + Outro 10%, sem nota → 1.500.
    oid = _orc(
        "c02",
        totais=(1500, 1500, 1500, 1500),
        acrescimos=[
            {"tipo": "BV", "is_percent": True, "value": 10},
            {"tipo": "Outro", "is_percent": False, "value": 300},
            {"tipo": "Outro", "is_percent": True, "value": 10},
        ],
    )
    res = _b1(oid, 1)
    valores = [Decimal(str(linha["amount_brl"])) for linha in res["linhas"]]
    _garante(valores == [Decimal("100.00"), Decimal("300.00"), Decimal("100.00")], f"{valores}")


def cen_03_fixo() -> None:
    oid = _orc_fixo("c03")
    _garante(
        _bv_de(_b1(oid, 1)) == Decimal("10.00") and _bv_de(_b1(oid, 4)) == Decimal("10.00"), "fixo"
    )


def cen_04_duracao_extra() -> None:
    oid = _orc(
        "c04",
        totais=(1100, 1650, 2200, 2750),
        duracao_custom=6,
        total_custom=4125.0,
        acrescimos=[{"tipo": "BV", "is_percent": True, "value": 10}],
    )
    res = _b1(oid, 6)
    _garante(_bv_de(res) == Decimal("375.00"), f"6h: {res}")
    _garante(Decimal(str(res["total"])) == Decimal("4125.00"), f"total 6h: {res['total']}")


def cen_05_personalizado() -> None:
    oid = _orc(
        "c05",
        totais=(900, 900, 900, 900),
        personalizado=True,
        acrescimos=[{"tipo": "BV", "is_percent": True, "value": 10}],
    )
    _garante(_b1(oid, 2)["linhas"] == [], "personalizado com linha")


def cen_06_paridade_espelho() -> None:
    rows = _no_banco(
        "SELECT id, result_snapshot FROM orcamento_history WHERE form_snapshot LIKE '%\"is_bv\": true%' "
        "AND result_snapshot LIKE '%memoria%' AND client_name NOT LIKE :p",
        p=f"{PREFIX}%",
    )
    pares = 0
    for oid, rs in rows:
        mem = (json.loads(rs) or {}).get("memoria") or []
        bv_mem = [
            m
            for m in mem
            if str(m.get("rotulo") or m.get("label") or "").startswith("Acréscimo: BV")
        ]
        if not bv_mem:
            continue
        valores = bv_mem[0].get("valores") or []
        for d in range(1, 5):
            if d - 1 >= len(valores) or valores[d - 1] is None:
                continue
            res = _b1(oid, d)
            got = _bv_de(res)
            _garante(
                got is not None and abs(got - q(valores[d - 1])) <= CENTAVO,
                f"orçamento {oid} {d}h: memória {valores[d - 1]} × conta {got}",
            )
            pares += 1
    _garante(pares >= 40, f"poucos pares conferidos ({pares}) — a memória mudou de forma?")
    print(f"         ({pares} pares conferidos com tolerância de R$ 0,01)")


def cen_07_valores_brl_no_snapshot() -> None:
    from app.orcamento.quote_ops import calculate_quote

    payload = {
        "performers": [{"type": "ator", "subtipo": "cara_limpa", "nome": "Teste", "makeup": False}],
        "coordenador_qty": 1,
        "nota_fiscal": True,
        "event_time": "15:00",
        "acrescimos": [{"tipo": "BV", "is_percent": True, "value": 10}],
    }
    with app.app_context():
        r1 = calculate_quote(payload)
        acr = r1["snapshot"]["acrescimos"][0]
        _garante(
            isinstance(acr.get("valores_brl"), list) and len(acr["valores_brl"]) == 4, f"{acr}"
        )
        mem = [
            m
            for m in (r1["quote"].get("memoria") or [])
            if str(m.get("rotulo") or m.get("label") or "").startswith("Acréscimo: BV")
        ]
        if mem and mem[0].get("valores"):
            for a, b in zip(acr["valores_brl"], mem[0]["valores"], strict=False):
                _garante(
                    abs(q(a) - q(b)) <= CENTAVO,
                    f"valores_brl {acr['valores_brl']} × memória {mem[0]['valores']}",
                )
        payload2 = json.loads(json.dumps(payload))
        payload2["acrescimos"][0]["valores_brl"] = [999, 999, 999, 999]
        r2 = calculate_quote(payload2)
        t1 = [r1["quote"].get(f"total_{h}h") for h in range(1, 5)]
        t2 = [r2["quote"].get(f"total_{h}h") for h in range(1, 5)]
        _garante(t1 == t2, f"valores_brl de entrada mudou o total: {t1} × {t2}")


# ── 8–9 · leitura ───────────────────────────────────────────────────────────────────────────────
def cen_08_prefill() -> None:
    oid = _orc_d2("c08")
    j = _cliente("com").get(f"/api/events/new/prefill?orcamento_id={oid}").get_json()
    ado = j.get("acrescimos_do_orcamento") or {}
    linhas = ado.get("linhas") or []
    _garante(len(linhas) == 1 and linhas[0]["is_bv"], f"{ado}")
    vb = linhas[0]["valores_brl"]
    _garante(q(vb["1"]) == Decimal("100.00") and q(vb["4"]) == Decimal("250.00"), f"{vb}")
    _garante("acrescimos" in j, "a chave antiga sumiu")
    j2 = _cliente("com").get(f"/api/events/new/prefill?orcamento_id={_orc_sem('c08b')}").get_json()
    _garante(
        (j2.get("acrescimos_do_orcamento") or {}).get("linhas") == [],
        f"{j2.get('acrescimos_do_orcamento')}",
    )


def cen_09_detalhe() -> None:
    eid = _evento_google("c09", venda=2000)
    _garante(_put("com", eid, [_bv_item(200)]).status_code == 200, "PUT de preparo")
    acr = _cliente("com").get(f"/api/events/{eid}").get_json().get("acrescimos") or []
    _garante(acr and acr[0].get("bv_pix") == PIX and "descricao" in acr[0], f"{acr}")
    _garante(
        not _cliente("cast").get(f"/api/events/{eid}").get_json().get("acrescimos"),
        "Casting viu acréscimos",
    )


# ── 10–18 · escrita ─────────────────────────────────────────────────────────────────────────────
def cen_10_criacao() -> None:
    oid = _orc_2031("c10")
    r, eid = _criar(
        "com", _corpo_criacao(f"{PREFIX}c10", oid, venda=1622.50, bv_recipient=QUEM, bv_pix=PIX)
    )
    _garante(eid, f"POST → {r.status_code} {r.get_data(as_text=True)[:300]}")
    estado["ev10"] = eid
    bvs = _bvs(eid)
    _garante(len(bvs) == 1, f"linhas BV: {bvs}")
    b = bvs[0]
    _garante(b["is_percent"] is False and q(b["amount_brl"]) == Decimal("147.50"), f"{b}")
    _garante(
        f"#{oid}" in (b["descricao"] or "")
        and b["bv_recipient"] == QUEM
        and b["bv_pix"] == PIX
        and b["bv_payment_status"] == "nao_pago",
        f"{b}",
    )
    com = _comissao(eid)
    _garante(
        com is not None and q(com[0]) == _comissao_esperada(1622.50, 147.50), f"comissão {com}"
    )


def cen_11_lista_do_navegador() -> None:
    oid = _orc_2031("c11")
    corpo = _corpo_criacao(
        f"{PREFIX}c11",
        oid,
        venda=1622.50,
        bv_recipient=QUEM,
        bv_pix=PIX,
        acrescimos=[{"tipo": "BV", "is_percent": False, "value": 9999}],
    )
    r, eid = _criar("com", corpo)
    _garante(eid, f"POST → {r.status_code}")
    _garante([q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("147.50")], f"{_linhas(eid)}")


def cen_12_proporcao() -> None:
    oid = _orc_2031("c12")
    r, eid = _criar(
        "com",
        _corpo_criacao(
            f"{PREFIX}c12", oid, venda=1541.38, bruto=1622.50, bv_recipient=QUEM, bv_pix=PIX
        ),
    )
    _garante(eid, f"POST → {r.status_code}")
    b = _bvs(eid)[0]
    _garante(
        q(b["amount_brl"]) == Decimal("140.13") and "proporção" in (b["descricao"] or ""), f"{b}"
    )
    _garante(
        q(_comissao(eid)[0]) == _comissao_esperada(1541.38, 140.13), f"comissão {_comissao(eid)}"
    )


def cen_13_cortesia_e_a_definir() -> None:
    for sufixo, extra in (
        ("c13a", {"is_cortesia_permuta": True}),
        ("c13b", {"valor_a_definir": True}),
    ):
        oid = _orc_2031(sufixo)
        corpo = _corpo_criacao(
            f"{PREFIX}{sufixo}", oid, venda=1622.50 if "c13a" == sufixo else None, **extra
        )
        r, eid = _criar("com", corpo)
        _garante(eid, f"{sufixo}: POST → {r.status_code} {r.get_data(as_text=True)[:200]}")
        _garante(_linhas(eid) == [], f"{sufixo}: linhas {_linhas(eid)}")
        estado[f"ev_{sufixo}"] = eid


def cen_14_vincular_e_aplicar() -> None:
    oid = _orc_2031("c14")
    eid = _evento_google("c14")
    corpo = {
        "orcamento_history_id": oid,
        "aplicar_valores_duracao": 2,
        "bv_recipient": QUEM,
        "bv_pix": PIX,
    }
    r = _cliente("com").patch(f"/api/events/{eid}/orcamento", json=corpo)
    _garante(r.status_code == 200, f"→ {r.status_code} {r.get_data(as_text=True)[:300]}")
    rel = r.get_json().get("relatorio_orcamento") or {}
    _garante(
        rel.get("acrescimos_criados") == 1 and q(rel.get("bv_total")) == Decimal("147.50"), f"{rel}"
    )
    _garante([q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("147.50")], f"{_linhas(eid)}")
    corpo2 = {
        "orcamento_history_id": oid,
        "aplicar_valores_duracao": 2,
        "bv_recipient": QUEM,
        "bv_pix": PIX,
    }
    _cliente("com").patch(f"/api/events/{eid}/orcamento", json=corpo2)
    _garante(len(_bvs(eid)) == 1, "reaplicar duplicou")
    estado["ev14"] = eid


def cen_15_venda_digitada() -> None:
    # (a) vínculo em evento com venda.
    oid = _orc_2031("c15a")
    eid = _evento_google("c15a", venda=1622.50)
    r = _cliente("com").patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": oid})
    _garante(r.status_code == 200, f"→ {r.status_code}")
    rel = r.get_json().get("relatorio_orcamento") or {}
    _garante(rel.get("acrescimos_ignorados") == "evento já tem venda", f"{rel}")
    _garante(_linhas(eid) == [] and _pendente("com", eid) is not None, "sem alerta")
    # (b) "a definir" que recebe valor pelo /comercial.
    oid_b = _orc_2031("c15b")
    r, eid_b = _criar(
        "com", _corpo_criacao(f"{PREFIX}c15b", oid_b, venda=None, valor_a_definir=True)
    )
    _garante(eid_b, f"POST → {r.status_code}")
    r = _cliente("com").patch(
        f"/api/events/{eid_b}/comercial",
        json=_corpo_comercial(eid_b, sale_value=1622.50, sale_value_gross=1622.50),
    )
    _garante(r.status_code == 200, f"/comercial → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(
        _linhas(eid_b) == [] and _pendente("com", eid_b) is not None,
        "sem alerta depois do /comercial",
    )
    _garante(_put("com", eid_b, [_bv_item(147.50)]).status_code == 200, "lançar o BV")
    _garante(_pendente("com", eid_b) is None, "o alerta não sumiu")
    # (c) cancelado.
    oid_c = _orc_2031("c15c")
    eid_c = _evento_google("c15c", venda=1622.50)
    _cliente("com").patch(f"/api/events/{eid_c}/orcamento", json={"orcamento_history_id": oid_c})
    with _externo.begin() as conn:
        conn.execute(
            text("UPDATE calendar_events SET cancelled_at = now() WHERE id = :i"), {"i": eid_c}
        )
    _garante(
        _pendente("com", eid_c) is None and _linhas(eid_c) == [], "cancelado com alerta ou linha"
    )


def cen_16_salvar_sem_mexer() -> None:
    eid = estado["ev10"]
    antes = _bvs(eid)[0]
    _set_status_bv(eid, "pago")
    itens = _como_carregou(eid)
    _garante(_put("com", eid, itens).status_code == 200, "PUT como carregou")
    depois = _bvs(eid)[0]
    _garante(
        depois["bv_pix"] == PIX
        and depois["bv_payment_status"] == "pago"
        and q(depois["amount_brl"]) == q(antes["amount_brl"]),
        f"{depois}",
    )
    itens = _como_carregou(eid)
    for i in itens:
        i["bv_pix"] = ""
    _garante(_put("com", eid, itens).status_code == 200, "PUT com PIX vazio")
    depois = _bvs(eid)[0]
    _garante(depois["bv_pix"] == PIX and depois["bv_payment_status"] == "pago", f"{depois}")


def _cen_17_corpo(regua_mutante: Callable | None = None) -> None:
    from app.calendar import comercial_ops

    original = getattr(comercial_ops, "valor_do_bv_percentual", None)
    if regua_mutante is not None:
        comercial_ops.valor_do_bv_percentual = regua_mutante
    try:
        # com nota: 1.309,52 → 100,00
        e1 = _evento_google("c17a", venda=1309.52, nota=True)
        c_antes = _comissao(e1)
        _garante(_put("com", e1, [_bv_item(10, pct=True)]).status_code == 200, "PUT 10%")
        _garante([q(b["amount_brl"]) for b in _bvs(e1)] == [Decimal("100.00")], f"{_bvs(e1)}")
        _garante(_comissao(e1) != c_antes, "a comissão a pagar não mudou na mesma requisição")
        # "Outro" de 300 + BV 10%, venda 1.430 sem nota → 130,00
        e2 = _evento_google("c17b", venda=1430)
        _put(
            "com",
            e2,
            [{"tipo": "Outro", "is_percent": False, "value": 300}, _bv_item(10, pct=True)],
        )
        _garante([q(b["amount_brl"]) for b in _bvs(e2)] == [Decimal("130.00")], f"{_bvs(e2)}")
        # BV R$ 50 + BV 10% + Outro 300, venda 1.480 → % = 130 e R$ = 50
        e3 = _evento_google("c17c", venda=1480)
        _put(
            "com",
            e3,
            [
                {"tipo": "Outro", "is_percent": False, "value": 300},
                _bv_item(10, pct=True),
                _bv_item(50, quem=f"{PREFIX}Outro Parceiro"),
            ],
        )
        valores = sorted(q(b["amount_brl"]) for b in _bvs(e3))
        _garante(valores == [Decimal("50.00"), Decimal("130.00")], f"{valores}")
    finally:
        if regua_mutante is not None:
            comercial_ops.valor_do_bv_percentual = original


def cen_17_regua_do_percentual() -> None:
    _cen_17_corpo()
    # BV % gravado como a 273 grava hoje (130,95 sobre 1.309,52 com nota): a pagar → 100; pago → fica.
    for status, esperado in (("nao_pago", Decimal("100.00")), ("pago", Decimal("130.95"))):
        e = _evento_google(f"c17d-{status}", venda=1309.52, nota=True)
        with _externo.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO event_acrescimos (event_id, tipo, descricao, is_percent, value, amount_brl, is_bv, "
                    "bv_recipient, bv_pix, bv_payment_status, created_at) "
                    "VALUES (:e, 'BV', '', true, 10, 130.95, true, :q, :p, :s, now())"
                ),
                {"e": e, "q": QUEM, "p": PIX, "s": status},
            )
        _garante(_put("com", e, _como_carregou(e)).status_code == 200, "PUT legado")
        _garante([q(b["amount_brl"]) for b in _bvs(e)] == [esperado], f"{status}: {_bvs(e)}")
    from app.calendar import comercial_ops

    original = comercial_ops.valor_do_bv_percentual

    def mutante(venda, with_invoice, percentual, soma_bv_reais, soma_perc_bv):  # o BV em R$ na base
        return original(venda, with_invoice, percentual, Decimal("0"), soma_perc_bv)

    _deve_quebrar(lambda: _cen_17_corpo(mutante), "BV em R$ dentro da base do %")


def cen_18_planilha() -> None:
    eid = estado["ev14"]
    mes = _no_banco(
        "SELECT to_char(start_at, 'YYYY-MM') FROM calendar_events WHERE id = :i", i=eid
    )[0][0]
    itens = (
        _cliente("fin").get(f"/api/financeiro/pagamentos?month={mes}").get_json().get("items") or []
    )
    meus = [i for i in itens if i.get("type") == "bv" and i.get("event_id") == eid]
    _garante(
        len(meus) == 1
        and q(meus[0]["amount"]) == Decimal("147.50")
        and meus[0].get("pix_key") == PIX
        and meus[0].get("missing_data") is False,
        f"{meus}",
    )


# ── 19–22 · RBAC (devem falhar) ─────────────────────────────────────────────────────────────────
def cen_19_prefill_casting() -> None:
    r = _cliente("cast").get(f"/api/events/new/prefill?orcamento_id={_orc_2031('c19')}")
    _garante(r.status_code == 403, f"Casting abriu o prefill: {r.status_code}")


def cen_20_criacao_financeiro() -> None:
    r, eid = _criar("fin", _corpo_criacao(f"{PREFIX}c20", None, venda=1000))
    _garante(r.status_code == 403 and eid is None, f"Financeiro criou: {r.status_code}")


def cen_21_put_casting_e_satelite() -> None:
    eid = _evento_google("c21", venda=1000)
    r = _put("cast", eid, [_bv_item(50)])
    _garante(r.status_code == 403, f"Casting salvou: {r.status_code}")
    with app.app_context():
        lider = _evento_google("c21-lider", venda=1000)
        sat = db.session.get(CalendarEvent, eid)
        sat.group_leader_id = lider
        db.session.commit()
    r = _put("com", eid, [_bv_item(50)])
    _garante(r.status_code == 409, f"satélite aceitou: {r.status_code}")


def cen_22_vinculo_casting() -> None:
    eid = _evento_google("c22")
    r = _cliente("cast").patch(
        f"/api/events/{eid}/orcamento", json={"orcamento_history_id": _orc_2031("c22")}
    )
    _garante(r.status_code == 403, f"Casting vinculou: {r.status_code}")


# ── 23–27 · regressão ───────────────────────────────────────────────────────────────────────────
def cen_23_sem_orcamento() -> None:
    # A lista do navegador é ignorada em TODA criação (FR-006): um BV ali nasceria sem PIX.
    corpo = _corpo_criacao(
        f"{PREFIX}c23",
        None,
        venda=2000,
        acrescimos=[
            {"tipo": "BV", "is_percent": False, "value": 300, "bv_recipient": "", "bv_pix": ""}
        ],
    )
    r, eid = _criar("com", corpo)
    _garante(eid and _linhas(eid) == [], f"→ {r.status_code} {_linhas(eid) if eid else ''}")
    _garante(q(_comissao(eid)[0]) == _comissao_esperada(2000, 0), f"{_comissao(eid)}")


def cen_57_bv_pago_nao_sai() -> None:
    eid = _evento_com_bv_reais("c57", nota=False)
    _set_status_bv(eid, "pago")
    antes = _linhas(eid)
    r = _put("com", eid, [{"tipo": "Outro", "is_percent": False, "value": 50}])
    _garante(
        r.status_code == 400 and _linhas(eid) == antes,
        f"BV pago apagado: {r.status_code} {_linhas(eid)}",
    )
    itens = _como_carregou(eid)
    itens[0]["tipo"] = "Outro"
    r = _put("com", eid, itens)
    _garante(
        r.status_code == 400 and _linhas(eid) == antes, f"BV pago virou outro tipo: {r.status_code}"
    )
    itens = _como_carregou(eid)
    itens[0]["value"] = 20
    _garante(_put("com", eid, itens).status_code == 200, "PUT do BV pago com outro valor")
    _garante(
        [q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("200.00")],
        f"BV pago mudou de valor: {_bvs(eid)}",
    )


def cen_24_orcamento_sem_acrescimos() -> None:
    r, eid = _criar("com", _corpo_criacao(f"{PREFIX}c24", _orc_sem("c24"), venda=1500))
    _garante(eid and _linhas(eid) == [], f"→ {r.status_code}")
    ev = _evento(eid)
    _garante(q(ev["venda"]) == Decimal("1500.00"), f"{ev}")


def cen_25_comissao_paga_intacta() -> None:
    r, eid = _criar("com", _corpo_criacao(f"{PREFIX}c25", None, venda=2000))
    _garante(eid, f"→ {r.status_code}")
    with _externo.begin() as conn:
        conn.execute(
            text(
                "UPDATE commission_payments SET status='pago', paid_at=CURRENT_DATE WHERE event_id=:i"
            ),
            {"i": eid},
        )
    antes = _comissao(eid)
    _garante(_put("com", eid, [_bv_item(200)]).status_code == 200, "PUT")
    _garante(_comissao(eid) == antes, f"comissão paga mudou: {antes} → {_comissao(eid)}")


def cen_26_dre() -> None:
    from app.financeiro.routes import _compute_drg

    eid = _evento_google("c26", venda=2000)
    with app.app_context():
        settings = SiteSetting.query.first()
        cpv_antes = _compute_drg(
            [db.session.get(CalendarEvent, eid)], settings, Decimal(0), Decimal(0)
        )["cpv"]
    _put("com", eid, [_bv_item(200)])
    with app.app_context():
        db.session.expire_all()
        cpv_depois = _compute_drg(
            [db.session.get(CalendarEvent, eid)], settings, Decimal(0), Decimal(0)
        )["cpv"]
    _garante(
        q(Decimal(str(cpv_depois)) - Decimal(str(cpv_antes))) == Decimal("200.00"),
        f"{cpv_antes} → {cpv_depois}",
    )


def cen_27_regressao() -> None:
    if "--regressao" not in sys.argv:
        print("         (cenário 27 pulado: rode com --regressao)")
        return
    alvos = [
        "specs/273-orcamento-para-evento/verify_273.py",
        "specs/267b-hotfix-data-da-venda/verify_267b.py",
        "specs/301-orcamentos-visiveis-comercial/verify_301.py",
        "specs/215b-hotfix-taxa-e-vendedor/verify_215b.py",
        "specs/267c-hotfix-trava-do-lote/verify_267c.py",
        "specs/267-integridade-comissao/verify_267.py",
    ]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    # Linha de base conhecida, medida na `main` sem a 305 em 14/10/2026: o verify_273 ficou para trás
    # da 301 (espera 404 onde a 301 passou a responder 409 `orcamento_de_outro`, e o resto cai em
    # cascata). Regressão é ficar PIOR que a base — registrado como dívida no docs/05.
    base_conhecida = {"specs/273-orcamento-para-evento/verify_273.py": "8/15 OK"}
    falhas = []
    for alvo in alvos:
        s = subprocess.run(
            [sys.executable, alvo],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=900,
        )
        ultima = (s.stdout.strip().splitlines() or ["?"])[-1]
        print(f"         {alvo.split('/')[-1]}: {ultima}")
        if s.returncode != 0 and not ultima.startswith(base_conhecida.get(alvo, "\0")):
            falhas.append(alvo)
    _garante(not falhas, f"regressão vermelha: {falhas}")


# ── 31–43 · crítica de completude ───────────────────────────────────────────────────────────────
def cen_31_pix_obrigatorio() -> None:
    oid = _orc_2031("c31")
    titulo = f"{PREFIX}c31"
    google = GOOGLE["insert"]
    r, eid = _criar("com", _corpo_criacao(titulo, oid, venda=1622.50))
    campos = _erro(r).get("fields") or {}
    _garante(
        r.status_code == 400 and "bv_recipient" in campos and "bv_pix" in campos,
        f"{r.status_code} {_erro(r)}",
    )
    _garante("PIX" in (_erro(r).get("message") or ""), f"mensagem de topo sem o PIX: {_erro(r)}")
    _garante(
        GOOGLE["insert"] == google and _contar_eventos(titulo) == 0,
        "Google chamado ou evento criado",
    )
    r, _ = _criar("com", _corpo_criacao(titulo, oid, venda=1622.50, bv_recipient=QUEM))
    _garante(
        r.status_code == 400 and "bv_pix" in (_erro(r).get("fields") or {}),
        f"só quem recebe: {_erro(r)}",
    )
    r, _ = _criar(
        "com", _corpo_criacao(titulo, oid, venda=1622.50, bv_recipient=QUEM, bv_pix="x" * 141)
    )
    _garante(r.status_code == 400, f"PIX de 141: {r.status_code}")
    r, _ = _criar("com", _corpo_criacao(titulo, oid, venda=1622.50, bv_recipient=123, bv_pix=PIX))
    _garante(r.status_code == 400, f"quem recebe numérico: {r.status_code}")
    # vínculo sem os campos
    eid = _evento_google("c31-vinculo")
    papeis = _no_banco("SELECT count(*) FROM event_roles WHERE event_id = :i", i=eid)[0][0]
    r = _cliente("com").patch(
        f"/api/events/{eid}/orcamento",
        json={"orcamento_history_id": _orc_2031("c31b"), "aplicar_valores_duracao": 2},
    )
    _garante(r.status_code == 400, f"vínculo sem PIX: {r.status_code}")
    ev = _evento(eid)
    _garante(
        ev["orc"] is None
        and ev["venda"] is None
        and _no_banco("SELECT count(*) FROM event_roles WHERE event_id = :i", i=eid)[0][0]
        == papeis,
        f"{ev}",
    )
    # editor sem PIX e sem PIX anterior
    e2 = _evento_google("c31-put", venda=1000)
    _put("com", e2, [{"tipo": "Outro", "is_percent": False, "value": 100}])
    antes = _linhas(e2)
    r = _put(
        "com", e2, [{"tipo": "Outro", "is_percent": False, "value": 100}, _bv_item(50, pix="")]
    )
    _garante(
        r.status_code == 400 and "items.1.bv_pix" in (_erro(r).get("fields") or {}),
        f"{r.status_code} {_erro(r)}",
    )
    _garante(_linhas(e2) == antes, "a recusa apagou as linhas")


def cen_32_autoria_301() -> None:
    oid = _orc_2031("c32", dono="com")
    eid = _evento_google("c32")
    r = _cliente("com").patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": oid})
    _garante(r.status_code == 200, f"vínculo da autora → {r.status_code}")
    r = _cliente("com2").patch(
        f"/api/events/{eid}/orcamento",
        json={
            "orcamento_history_id": oid,
            "aplicar_valores_duracao": 2,
            "bv_recipient": QUEM,
            "bv_pix": PIX,
        },
    )
    _garante(r.status_code == 409 and _linhas(eid) == [], f"não-autora: {r.status_code}")
    e2 = _evento_google("c32b")
    r = _cliente("fin").patch(
        f"/api/events/{e2}/orcamento",
        json={
            "orcamento_history_id": _orc_2031("c32c", dono="com"),
            "aplicar_valores_duracao": 2,
            "bv_recipient": QUEM,
            "bv_pix": PIX,
        },
    )
    _garante(
        r.status_code == 404 and _linhas(e2) == [],
        f"Financeiro com orçamento alheio: {r.status_code}",
    )


def cen_33_resto_rbac() -> None:
    eid = estado["ev14"]
    r = app.test_client().put(f"/api/events/{eid}/acrescimos", json={"items": []})
    _garante(r.status_code == 401, f"sem sessão: {r.status_code}")
    bv_id = _bvs(eid)[0]["id"]
    r = _cliente("com").post(
        "/api/financeiro/pagamentos/set-status",
        json={"item_type": "bv", "item_id": bv_id, "status": "pago"},
    )
    _garante(r.status_code == 403, f"Comercial marcou BV pago: {r.status_code}")
    _garante(
        not _cliente("a3d").get(f"/api/events/{eid}").get_json().get("acrescimos"), "Artista 3D viu"
    )
    c = _cliente("sa")
    c.post("/api/auth/impersonate", json={"role": "CASTING"})
    _garante(
        not c.get(f"/api/events/{eid}").get_json().get("acrescimos"),
        "Superadmin 'como Casting' viu",
    )
    c.delete("/api/auth/impersonate")


def cen_34_concorrencia() -> None:
    oid = _orc_2031("c34")
    eid = _evento_google("c34")
    corpo = {
        "orcamento_history_id": oid,
        "aplicar_valores_duracao": 2,
        "bv_recipient": QUEM,
        "bv_pix": PIX,
    }
    respostas = []

    def aplicar():
        respostas.append(
            _cliente("sa").patch(f"/api/events/{eid}/orcamento", json=corpo).status_code
        )

    threads = [threading.Thread(target=aplicar) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    _garante(len(_bvs(eid)) == 1, f"duas aplicações deram {len(_bvs(eid))} linhas ({respostas})")


def cen_35_bundle_antigo_editor() -> None:
    eid = estado["ev10"]
    _set_status_bv(eid, "no_banco")
    origem = _bvs(eid)[0]["descricao"]
    itens = [
        {k: v for k, v in i.items() if k not in ("descricao", "id")} for i in _como_carregou(eid)
    ]
    _garante(_put("com", eid, itens).status_code == 200, "PUT bundle antigo")
    b = _bvs(eid)[0]
    _garante(b["descricao"] == origem and b["bv_payment_status"] == "no_banco", f"{b}")
    itens = _como_carregou(eid)
    itens[0]["descricao"] = ""
    _put("com", eid, itens)
    _garante((_bvs(eid)[0]["descricao"] or "") == "", "descricao vazia não apagou")


def cen_36_erro_sem_estrago() -> None:
    from app.calendar.comercial_ops import AcrescimosRecusados, substituir_acrescimos

    eid = _evento_google("c36", venda=1000)
    _put("com", eid, [{"tipo": "Outro", "is_percent": False, "value": 100}, _bv_item(50)])
    antes = _linhas(eid)
    r = _put(
        "com",
        eid,
        [
            {"tipo": "Outro", "is_percent": False, "value": 100},
            _bv_item(70, quem="", pix=""),
            _bv_item(50),
        ],
    )
    _garante(r.status_code == 400 and _linhas(eid) == antes, f"{r.status_code} {_linhas(eid)}")
    with app.app_context():
        ev = db.session.get(CalendarEvent, eid)
        ev.sale_value = Decimal("999")
        try:
            substituir_acrescimos(
                ev,
                [
                    {
                        "tipo": "BV",
                        "is_percent": False,
                        "value": "70",
                        "bv_recipient": "",
                        "bv_pix": "",
                    }
                ],
            )
            raise AssertionError("o gêmeo Jinja aceitou BV sem PIX")
        except AcrescimosRecusados:
            db.session.rollback()
    _garante(
        _linhas(eid) == antes and q(_evento(eid)["venda"]) == Decimal("1000.00"),
        "rollback não desfez",
    )


def cen_37_duracao_sem_chave() -> None:
    oid = _orc_2031("c37a")
    r, eid = _criar(
        "com",
        _corpo_criacao(
            f"{PREFIX}c37a", oid, venda=1622.50, duracao=None, bv_recipient=QUEM, bv_pix=PIX
        ),
    )
    _garante(
        eid and [q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("147.50")],
        f"pelo valor: {_linhas(eid) if eid else r.status_code}",
    )
    _garante(
        any("pelo valor" in m for m in _logs(eid)), f"log sem a origem da duração: {_logs(eid)}"
    )
    # dia inteiro, valor que não bate, orçamento com linha em R$ → não grava
    oid_b = _orc_fixo("c37b")
    r, eid = _criar(
        "com",
        _corpo_criacao(
            f"{PREFIX}c37b",
            oid_b,
            venda=1777,
            duracao=None,
            inicio="09:00",
            fim="21:00",
            bv_recipient=QUEM,
            bv_pix=PIX,
        ),
    )
    _garante(
        eid and _linhas(eid) == [], f"dia inteiro gravou: {_linhas(eid) if eid else r.status_code}"
    )
    # o mesmo só com %: nasce pela proporção
    oid_c = _orc_2031("c37c")
    r, eid = _criar(
        "com",
        _corpo_criacao(
            f"{PREFIX}c37c",
            oid_c,
            venda=1777,
            duracao=None,
            inicio="09:00",
            fim="21:00",
            bv_recipient=QUEM,
            bv_pix=PIX,
        ),
    )
    esperado = q(Decimal("1777") * Decimal("10") / Decimal("110"))
    _garante(
        eid and [q(b["amount_brl"]) for b in _bvs(eid)] == [esperado],
        f"só %: {_linhas(eid) if eid else r.status_code}",
    )


def cen_38_trocar_e_voltar() -> None:
    eid = estado["ev14"]
    antes = _bvs(eid)
    # O orçamento atual (c14) é do Superadmin: só ele troca (feature 301).
    r = _cliente("sa").patch(
        f"/api/events/{eid}/orcamento", json={"orcamento_history_id": _orc_d2("c38")}
    )
    _garante(r.status_code == 200 and _bvs(eid) == antes, f"trocar mexeu no BV: {r.status_code}")
    frase = json.dumps(r.get_json().get("relatorio_orcamento") or {}, ensure_ascii=False)
    _garante("Acréscimos" in frase, f"o relatório não avisa: {frase[:300]}")
    r = _cliente("com").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=None, sale_value_gross=None),
    )
    _garante(r.status_code == 200, f"a definir → {r.status_code}")
    r = _cliente("com").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=1622.50, sale_value_gross=1622.50),
    )
    _garante(r.status_code == 200 and len(_bvs(eid)) == 1, f"{r.status_code} {_bvs(eid)}")
    _garante(
        "confira o bv" in (r.get_json().get("aviso_bv") or "").lower(),
        f"sem aviso: {r.get_json().get('aviso_bv')}",
    )


def cen_39_rastro_sem_pix() -> None:
    for eid in (estado["ev10"], estado["ev14"]):
        logs = _logs(eid)
        _garante(any("BV" in m and QUEM in m for m in logs), f"sem log do BV em {eid}: {logs}")
        _garante(not any(PIX in m for m in logs), f"PIX no histórico de {eid}")
    eid = _evento_google("c39", venda=1000)
    _cliente("com").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=1200, sale_value_gross=1200),
    )
    _garante(not any("BV" in m for m in _logs(eid)), f"log de BV sem BV: {_logs(eid)}")


def cen_40_entradas_ruins() -> None:
    casos = [
        _orc(
            "c40a",
            totais=(0, 0, 0, 0),
            acrescimos=[{"tipo": "BV", "is_percent": True, "value": 10}],
        ),
        _orc(
            "c40b",
            totais=(100, 100, 100, 100),
            acrescimos=[
                {"tipo": "Outro", "is_percent": False, "value": 500},
                {"tipo": "BV", "is_percent": True, "value": 10},
            ],
        ),
        _orc(
            "c40c",
            totais=(1000, 1000, 1000, 1000),
            acrescimos=[{"tipo": "BV", "is_percent": True, "value": -150}],
        ),
        _orc(
            "c40d",
            totais=(1100, 1100, 1100, 1100),
            acrescimos=[{"tipo": "BV", "is_percent": True, "value": 10}],
            com_valores_brl=[[math.nan, 1e309, -5, 99999]],
        ),
        _orc("c40e", totais=(1100, 1100, 1100, 1100), acrescimos=[], snapshot_cru="[1, 2, 3]"),
        _orc("c40f", totais=(1100, 1100, 1100, 1100), acrescimos=[], snapshot_cru="{não é json"),
    ]
    for oid in casos:
        for d in (1, 2, 4, 6):
            res = _b1(oid, d)  # não pode levantar
            for linha in res["linhas"]:
                v = Decimal(str(linha["amount_brl"]))
                _garante(v.is_finite() and v >= 0, f"orçamento {oid} {d}h deu {v}")
    res = _b1(casos[3], 1)
    _garante(
        _bv_de(res) == Decimal("100.00"),
        f"valores_brl inválidos não caíram na conta inversa: {res}",
    )


def cen_42_mes_passado() -> None:
    oid = _orc_2031("c42")
    eid = _evento_google("c42", mes_passado=True)
    r = _cliente("com").patch(
        f"/api/events/{eid}/orcamento",
        json={
            "orcamento_history_id": oid,
            "aplicar_valores_duracao": 2,
            "bv_recipient": QUEM,
            "bv_pix": PIX,
        },
    )
    _garante(r.status_code == 200, f"→ {r.status_code}")
    mes = _no_banco(
        "SELECT to_char(start_at, 'MM/YYYY') FROM calendar_events WHERE id = :i", i=eid
    )[0][0]
    frase = json.dumps(r.get_json().get("relatorio_orcamento") or {}, ensure_ascii=False)
    _garante(f"Planilha de {mes}" in frase, f"sem o mês da Planilha: {frase[:300]}")


def cen_43_gemeo_jinja() -> None:
    from app.calendar.comercial_ops import substituir_acrescimos

    e_api = _evento_google("c43-api", venda=1430)
    e_jinja = _evento_google("c43-jinja", venda=1430)
    _put(
        "com",
        e_api,
        [{"tipo": "Outro", "is_percent": False, "value": "300"}, _bv_item("10", pct=True)],
    )
    with app.app_context():
        ev = db.session.get(CalendarEvent, e_jinja)
        substituir_acrescimos(
            ev,
            [
                {
                    "tipo": "Outro",
                    "is_percent": False,
                    "value": "300",
                    "descricao": "",
                    "bv_recipient": "",
                    "bv_pix": "",
                },
                {
                    "tipo": "BV",
                    "is_percent": True,
                    "value": "10",
                    "descricao": "",
                    "bv_recipient": QUEM,
                    "bv_pix": PIX,
                },
            ],
        )
        db.session.commit()

    def chave(eid):
        return [(linha["tipo"], q(linha["amount_brl"])) for linha in _linhas(eid)]

    _garante(chave(e_api) == chave(e_jinja), f"API {chave(e_api)} × Jinja {chave(e_jinja)}")


# ── 44–49 · respostas do dono ───────────────────────────────────────────────────────────────────
def cen_44_proporcao_pura() -> None:
    from app.orcamento.quote_ops import bv_que_acompanha as f

    _garante(
        f(Decimal("147.50"), Decimal("1622.50"), Decimal("1622.50")) == Decimal("147.50"), "igual"
    )
    _garante(
        f(Decimal("147.50"), Decimal("1541.38"), Decimal("1622.50")) == Decimal("140.13"), "140,13"
    )
    _garante(f(Decimal("100"), Decimal("1244.04"), Decimal("1309.52")) == Decimal("95.00"), "95,00")
    _garante(f(Decimal("10"), Decimal("1434.50"), Decimal("1510")) == Decimal("9.50"), "9,50")
    _garante(f(Decimal("100"), Decimal("2000"), Decimal("1000")) == Decimal("200.00"), "acima sobe")
    _garante(
        f(Decimal("100"), Decimal("1309.51"), Decimal("1309.52")) == Decimal("100.00"),
        "centavo = igual",
    )
    _garante(f(Decimal("100"), Decimal("500"), Decimal("0")) == Decimal("0.00"), "total zero")
    _garante(f(Decimal("100"), Decimal("500"), None) == Decimal("0.00"), "total nulo")


def cen_45_alerta() -> None:
    oid = _orc_2031("c45a")
    eid = _evento_google("c45a", venda=1622.50)
    _cliente("com").patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": oid})
    p_com, p_fin = _pendente("com", eid), _pendente("fin", eid)
    _garante(p_com and p_fin and q(p_com["valor"]) == Decimal("147.50"), f"com {p_com} fin {p_fin}")
    _garante("orcamento_history_id" not in json.dumps(p_fin), "id do orçamento para o Financeiro")
    _garante(
        _cliente("cast").get(f"/api/events/{eid}").get_json().get("venda") is None,
        "Casting viu venda",
    )
    # corte: criado e ligado antes → ausente
    _corte(datetime.utcnow() + timedelta(days=1))
    _garante(_pendente("com", eid) is None, "antes do corte com alerta")
    # "Reaplicou" depois do corte num ligado antes → ausente
    _cliente("com").patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": oid})
    _garante(_pendente("com", eid) is None, "Reaplicou acendeu o alerta")
    _corte(datetime(2000, 1, 1))
    # ausências: satélite, cortesia, a definir, personalizado, sem BV
    e_sem = _evento_google("c45-sem", venda=1500)
    _cliente("com").patch(
        f"/api/events/{e_sem}/orcamento", json={"orcamento_history_id": _orc_sem("c45s")}
    )
    _garante(_pendente("com", e_sem) is None, "alerta sem BV no orçamento")
    e_pers = _evento_google("c45-pers", venda=900)
    oid_p = _orc(
        "c45p",
        totais=(900, 900, 900, 900),
        personalizado=True,
        acrescimos=[{"tipo": "BV", "is_percent": True, "value": 10}],
    )
    _cliente("com").patch(f"/api/events/{e_pers}/orcamento", json={"orcamento_history_id": oid_p})
    _garante(_pendente("com", e_pers) is None, "alerta em personalizado")
    _garante(
        _pendente("com", estado["ev_c13a"]) is None and _pendente("com", estado["ev_c13b"]) is None,
        "alerta em cortesia ou a definir",
    )


def cen_46_bundle_antigo_criacao() -> None:
    r, eid = _criar("com", _corpo_criacao(f"{PREFIX}c46a", _orc_sem("c46a"), venda=1500))
    _garante(eid, f"sem BV não criou: {r.status_code}")
    r, eid = _criar("com", _corpo_criacao(f"{PREFIX}c46b", _orc_2031("c46b"), venda=1622.50))
    _garante(
        r.status_code == 400 and "PIX" in (_erro(r).get("message") or ""),
        f"{r.status_code} {_erro(r)}",
    )


def cen_47_bv_antigo_sem_pix() -> None:
    eid = _evento_google("c47", venda=1000)
    with _externo.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO event_acrescimos (event_id, tipo, descricao, is_percent, value, amount_brl, is_bv, "
                "bv_recipient, bv_pix, bv_payment_status, created_at) "
                "VALUES (:e, 'BV', '', false, 80, 80, true, :q, NULL, 'no_banco', now())"
            ),
            {"e": eid, "q": QUEM},
        )
    itens = _como_carregou(eid)
    r = _put("com", eid, itens)
    _garante(r.status_code == 400, f"antigo sem PIX passou: {r.status_code}")
    itens[0]["bv_pix"] = PIX
    r = _put("com", eid, itens)
    b = _bvs(eid)[0]
    _garante(
        r.status_code == 200 and b["bv_pix"] == PIX and b["bv_payment_status"] == "no_banco", f"{b}"
    )


def _evento_com_bv_reais(rotulo: str, *, venda=2000, nota=True, valor=200) -> int:
    eid = _evento_google(rotulo, venda=venda, nota=nota)
    _garante(_put("com", eid, [_bv_item(valor)]).status_code == 200, "PUT do BV em R$")
    return eid


def cen_48_venda_muda() -> None:
    eid = _evento_com_bv_reais("c48")
    r = _cliente("com").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=1800, sale_value_gross=1800),
    )
    _garante(r.status_code == 200, f"→ {r.status_code}")
    _garante([q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("180.00")], f"{_bvs(eid)}")
    _garante(
        "de R$ 200,00 para R$ 180,00" in (r.get_json().get("aviso_bv") or ""),
        f"{r.get_json().get('aviso_bv')}",
    )
    _garante(not any(PIX in m for m in _logs(eid)), "PIX no log")
    _garante(q(_comissao(eid)[0]) == _comissao_esperada(1800, 180), f"comissão {_comissao(eid)}")
    # pago e no banco ficam
    for status in ("pago", "no_banco"):
        e2 = _evento_com_bv_reais(f"c48-{status}")
        _set_status_bv(e2, status)
        _cliente("com").patch(
            f"/api/events/{e2}/comercial",
            json=_corpo_comercial(e2, sale_value=1800, sale_value_gross=1800),
        )
        _garante(
            [q(b["amount_brl"]) for b in _bvs(e2)] == [Decimal("200.00")], f"{status}: {_bvs(e2)}"
        )
    # para "a definir": a linha fica
    e3 = _evento_com_bv_reais("c48-adef")
    _cliente("com").patch(
        f"/api/events/{e3}/comercial",
        json=_corpo_comercial(e3, sale_value=None, sale_value_gross=None),
    )
    _garante(
        [q(b["amount_brl"]) for b in _bvs(e3)] == [Decimal("200.00")], f"a definir: {_bvs(e3)}"
    )


def _cen_49_corpo() -> None:
    eid = _evento_com_bv_reais("c49")
    b = _bvs(eid)[0]
    _garante(
        q(b["amount_brl"]) == Decimal("200.00") and b["is_percent"] is False, f"como digitado: {b}"
    )
    _garante(q(_comissao(eid)[0]) == _comissao_esperada(2000, 200), f"comissão {_comissao(eid)}")
    _put("com", eid, _como_carregou(eid))
    _garante(q(_bvs(eid)[0]["amount_brl"]) == Decimal("200.00"), "reenviado mudou")
    c = _cliente("com")
    c.patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=1800, sale_value_gross=1800),
    )
    _garante(q(_bvs(eid)[0]["amount_brl"]) == Decimal("180.00"), f"1.800: {_bvs(eid)}")
    c.patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=2000, sale_value_gross=2000),
    )
    _garante(q(_bvs(eid)[0]["amount_brl"]) == Decimal("200.00"), f"volta 2.000: {_bvs(eid)}")
    c.patch(f"/api/events/{eid}/comercial", json=_corpo_comercial(eid, payment_method="avista"))
    _garante(q(_bvs(eid)[0]["amount_brl"]) == Decimal("200.00"), "venda parada mudou o BV")


def cen_49_bv_em_reais() -> None:
    _cen_49_corpo()
    from app.calendar import comercial_ops

    original = comercial_ops.substituir_acrescimos

    def mutante(event, items):  # trata o BV em R$ como %: vira "200%" pela régua
        for i in items:
            if (i.get("tipo") or "").strip().upper() == "BV":
                i["is_percent"] = True
        return original(event, items)

    comercial_ops.substituir_acrescimos = mutante
    try:
        _deve_quebrar(_cen_49_corpo, "BV em R$ pela régua do %")
    finally:
        comercial_ops.substituir_acrescimos = original


# ── 51–56 · achados da pesquisa (14/10) ─────────────────────────────────────────────────────────
def cen_51_virgula_e_tipo() -> None:
    eid = _evento_google("c51", venda=2000)
    r = _put("com", eid, [_bv_item("100,00"), _bv_item("10,5", pct=True, quem=f"{PREFIX}Dois")])
    _garante(
        r.status_code == 200 and len(_bvs(eid)) == 2, f"vírgula: {r.status_code} {_linhas(eid)}"
    )
    _garante(Decimal("100.00") in [q(b["amount_brl"]) for b in _bvs(eid)], f"{_bvs(eid)}")
    antes = _linhas(eid)
    r = _put("com", eid, [_bv_item("abc")])
    _garante(
        r.status_code == 400
        and "items.0.value" in (_erro(r).get("fields") or {})
        and _linhas(eid) == antes,
        f"ilegível: {r.status_code} {_erro(r)}",
    )
    e2 = _evento_google("c51b", venda=2000)
    r = _put("com", e2, [_bv_item(50, tipo="bv")])
    _garante(
        r.status_code == 200 and _bvs(e2) and _bvs(e2)[0]["tipo"] == "BV",
        f"tipo minúsculo: {_linhas(e2)}",
    )
    r = _put("com", e2, [_bv_item(50, tipo="bv", pix="")])
    _garante(r.status_code in (200, 400), "PIX vazio em 'bv'")


def cen_52_identidade() -> None:
    eid = _evento_com_bv_reais("c52", nota=False)
    _set_status_bv(eid, "pago")
    itens = _como_carregou(eid) + [
        _bv_item(60)
    ]  # novo BV, sem id, para a mesma pessoa e o mesmo PIX
    _garante(_put("com", eid, itens).status_code == 200, "PUT")
    status = sorted((q(b["amount_brl"]), b["bv_payment_status"]) for b in _bvs(eid))
    _garante(status == [(Decimal("60.00"), "nao_pago"), (Decimal("200.00"), "pago")], f"{status}")


def cen_53_so_a_nota() -> None:
    # A nota que entra com a MESMA venda muda o preço (líquido 2.000 → 1.680): o BV em R$ acompanha.
    e1 = _evento_com_bv_reais("c53a", venda=2000, nota=False)
    _cliente("com").patch(
        f"/api/events/{e1}/comercial", json=_corpo_comercial(e1, with_invoice=True)
    )
    _garante(
        [q(b["amount_brl"]) for b in _bvs(e1)] == [Decimal("168.00")],
        f"R$ com a nota (líquido): {_bvs(e1)}",
    )
    # A nota que SAI com a venda caindo 16% (a cliente desistiu da nota): o preço não mudou, o BV fica.
    e1b = _evento_com_bv_reais("c53c", venda=2000, nota=True)
    _cliente("com").patch(
        f"/api/events/{e1b}/comercial",
        json=_corpo_comercial(e1b, with_invoice=False, sale_value=1680, sale_value_gross=1680),
    )
    _garante(
        [q(b["amount_brl"]) for b in _bvs(e1b)] == [Decimal("200.00")],
        f"desistir da nota mexeu no BV: {_bvs(e1b)}",
    )
    e2 = _evento_google("c53b", venda=1309.52, nota=True)
    _put("com", e2, [_bv_item(10, pct=True)])
    _garante([q(b["amount_brl"]) for b in _bvs(e2)] == [Decimal("100.00")], f"{_bvs(e2)}")
    _cliente("com").patch(
        f"/api/events/{e2}/comercial", json=_corpo_comercial(e2, with_invoice=False)
    )
    _garante(
        [q(b["amount_brl"]) for b in _bvs(e2)] == [q(q(Decimal("1309.52") / Decimal("1.1")) / 10)],
        f"% sem nota: {_bvs(e2)}",
    )


def cen_54_percentual_sem_venda() -> None:
    eid = _evento_google("c54", venda=1100)
    _put("com", eid, [_bv_item(10, pct=True)])
    _garante([q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("100.00")], f"{_bvs(eid)}")
    _cliente("com").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=None, sale_value_gross=None),
    )
    _put("com", eid, _como_carregou(eid))
    _garante(
        [q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("100.00")],
        f"% existente zerou: {_bvs(eid)}",
    )
    r = _put("com", eid, _como_carregou(eid) + [_bv_item(5, pct=True, quem=f"{PREFIX}Novo")])
    _garante(r.status_code == 400, f"% novo com venda a definir: {r.status_code}")
    _cliente("com").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=2200, sale_value_gross=2200),
    )
    _garante(
        [q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("200.00")], f"% na volta: {_bvs(eid)}"
    )


def cen_55_comissao_na_hora() -> None:
    r, eid = _criar("com", _corpo_criacao(f"{PREFIX}c55", None, venda=2000))
    _garante(eid, f"→ {r.status_code}")
    _put("com", eid, [_bv_item(300)])
    _garante(
        q(_comissao(eid)[0]) == _comissao_esperada(2000, 300), f"depois do PUT: {_comissao(eid)}"
    )
    _cliente("com").patch(
        f"/api/events/{eid}/comercial",
        json=_corpo_comercial(eid, sale_value=1000, sale_value_gross=1000),
    )
    _garante(
        q(_comissao(eid)[0]) == _comissao_esperada(1000, 150), f"depois da B10: {_comissao(eid)}"
    )


def cen_56_alerta_em_reais() -> None:
    oid = _orc_2407("c56")
    eid = _evento_google("c56", venda=22085)
    _cliente("com").patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": oid})
    p = _pendente("com", eid)
    _garante(p and p.get("valor") is not None and q(p["valor"]) == Decimal("435.00"), f"{p}")


# ── 58–68 · achados do converge (14/10) ─────────────────────────────────────────────────────────
def cen_58_corte_vazio() -> None:
    from app.calendar import orcamento_evento_ops as oeo

    original = estado.get("corte_original")
    _garante(original is None or original.tzinfo is None, f"CORTE_ALERTA_BV com fuso: {original!r}")
    try:
        # (a) A constante DO COMMIT (não a do monkeypatch): os três eventos do passado com orçamento
        # com BV e venda digitada não acendem nem ganham linha (T030; 3a-Q4 = A).
        _corte(original)
        with app.app_context():
            for eid in (1218, 1236, 1268):
                ev = db.session.get(CalendarEvent, eid)
                if ev is None:
                    continue
                _garante(oeo.bv_do_orcamento_pendente(ev) is None, f"evento {eid} acendeu o alerta")
                _garante(not _bvs(eid), f"evento {eid} ganhou linha BV")
        # (b) Sem corte gravado, nada acende pelo GET — a falha fecha (só o vínculo novo avisa).
        _corte(None)
        oid = _orc_2031("c58")
        eid = _evento_google("c58", venda=1622.50)
        _cliente("com").patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": oid})
        _garante(_pendente("com", eid) is None, "corte vazio acendeu o alerta")
    finally:
        _corte(datetime(2000, 1, 1))


def cen_59_nota_diferente() -> None:
    # Orçamento COM nota (1h 1.309,52, BV 100) e evento SEM nota a 1.100,00: o mesmo preço líquido.
    oid = _orc_d2("c59a")
    r, eid = _criar(
        "com",
        _corpo_criacao(
            f"{PREFIX}c59a", oid, venda=1100, duracao="1", fim="16:00", bv_recipient=QUEM, bv_pix=PIX
        ),
    )
    _garante(eid, f"POST → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante([q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("100.00")], f"sem nota: {_bvs(eid)}")
    # Orçamento SEM nota (1h 1.100, BV 100) e evento COM nota a 1.309,52.
    oid_b = _orc_2031("c59b")
    r, eid_b = _criar(
        "com",
        _corpo_criacao(
            f"{PREFIX}c59b", oid_b, venda=1309.52, duracao="1", fim="16:00", with_invoice=True,
            bv_recipient=QUEM, bv_pix=PIX,
        ),
    )
    _garante(eid_b, f"POST → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante([q(b["amount_brl"]) for b in _bvs(eid_b)] == [Decimal("100.00")], f"com nota: {_bvs(eid_b)}")
    # O alerta propõe pela mesma régua.
    oid_c = _orc_d2("c59c")
    eid_c = _evento_google("c59c", venda=1100, horas=1)
    _cliente("com").patch(f"/api/events/{eid_c}/orcamento", json={"orcamento_history_id": oid_c})
    p = _pendente("com", eid_c)
    _garante(p and p.get("valor") is not None and q(p["valor"]) == Decimal("100.00"), f"alerta: {p}")


def cen_60_bv_sem_valor() -> None:
    eid = _evento_com_bv_reais("c60", nota=False)
    antes = _linhas(eid)
    for vazio in ("", "0", 0, None):
        itens = _como_carregou(eid)
        itens[0]["value"] = vazio
        r = _put("com", eid, itens)
        _garante(
            r.status_code == 400
            and "items.0.value" in (_erro(r).get("fields") or {})
            and _linhas(eid) == antes,
            f"valor {vazio!r}: {r.status_code} {_linhas(eid)}",
        )
    r = _put("com", eid, _como_carregou(eid) + [{"tipo": "", "value": ""}])
    _garante(r.status_code == 200 and len(_bvs(eid)) == 1, f"linha em branco: {r.status_code}")


def cen_61_milhar_e_extremos() -> None:
    eid = _evento_google("c61", venda=2000)
    for ambiguo in ("1.500", "R$ 1.200", "1,309.52"):
        r = _put("com", eid, [_bv_item(ambiguo)])
        _garante(
            r.status_code == 400 and "items.0.value" in (_erro(r).get("fields") or {}) and not _linhas(eid),
            f"{ambiguo!r}: {r.status_code} {_linhas(eid)}",
        )
    for enorme in ("130952000000", 1e30):
        r = _put("com", eid, [{"tipo": "Outro", "is_percent": False, "value": enorme}])
        _garante(
            r.status_code == 400 and "items.0.value" in (_erro(r).get("fields") or {}),
            f"{enorme!r}: {r.status_code}",
        )
    r = _put("com", eid, [{"id": float("inf"), "tipo": "Outro", "is_percent": False, "value": 10}])
    _garante(r.status_code in (200, 400), f"id infinito: {r.status_code}")
    r = _put("com", eid, [_bv_item("1.500,00"), _bv_item(1500, quem=f"{PREFIX}Num")])
    _garante(
        r.status_code == 200 and [q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("1500.00")] * 2,
        f"1.500,00 e 1500: {r.status_code} {_bvs(eid)}",
    )


def cen_62_id_repetido() -> None:
    eid = _evento_com_bv_reais("c62", nota=False, valor=100)
    _set_status_bv(eid, "pago")
    antes = _linhas(eid)
    itens = _como_carregou(eid)
    copia = dict(itens[0], value=5000, bv_recipient=f"{PREFIX}Outra", bv_pix="outra@exemplo.test")
    r = _put("com", eid, itens + [copia])
    _garante(
        r.status_code == 400 and "items.1.id" in (_erro(r).get("fields") or {}) and _linhas(eid) == antes,
        f"id repetido: {r.status_code} {_erro(r)} {_linhas(eid)}",
    )


def cen_63_bv_negativo() -> None:
    eid = _evento_google("c63", venda=2000)
    comissao_antes = _comissao(eid)
    for item in (_bv_item("-100"), _bv_item(-10, pct=True)):
        r = _put("com", eid, [item])
        _garante(
            r.status_code == 400 and "items.0.value" in (_erro(r).get("fields") or {}) and not _linhas(eid),
            f"{item['value']!r}: {r.status_code} {_linhas(eid)}",
        )
    _garante(_comissao(eid) == comissao_antes, "a comissão mudou")
    r = _put("com", eid, [{"tipo": "Outro", "is_percent": False, "value": "-50"}])
    _garante(r.status_code == 200, f"desconto que não é BV: {r.status_code}")


def cen_64_vincular_roda_a_b10() -> None:
    # BV em % a pagar; a venda vai a "a definir" e volta pelo "Vincular e aplicar".
    eid = _evento_google("c64a", venda=1100)
    _put("com", eid, [_bv_item(10, pct=True)])
    _cliente("com").patch(
        f"/api/events/{eid}/comercial", json=_corpo_comercial(eid, sale_value=None, sale_value_gross=None)
    )
    _garante([q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("100.00")], f"a definir: {_bvs(eid)}")
    r = _cliente("com").patch(
        f"/api/events/{eid}/orcamento",
        json={"orcamento_history_id": _orc_sem("c64a"), "aplicar_valores_duracao": 2},
    )
    _garante(r.status_code == 200, f"vínculo → {r.status_code} {r.get_data(as_text=True)[:200]}")
    esperado = q(q(Decimal("1500") / Decimal("1.1")) * 10 / 100)
    _garante(q(_evento(eid)["venda"]) == Decimal("1500.00"), f"venda {_evento(eid)}")
    _garante([q(b["amount_brl"]) for b in _bvs(eid)] == [esperado], f"% na volta pelo vínculo: {_bvs(eid)}")
    _garante(q(_comissao(eid)[0]) == _comissao_esperada(1500, esperado), f"comissão {_comissao(eid)}")
    # BV em reais: fica, e a frase do vínculo manda conferir.
    e2 = _evento_com_bv_reais("c64b", venda=2000, nota=False)
    _cliente("com").patch(
        f"/api/events/{e2}/comercial", json=_corpo_comercial(e2, sale_value=None, sale_value_gross=None)
    )
    r = _cliente("com").patch(
        f"/api/events/{e2}/orcamento",
        json={"orcamento_history_id": _orc_sem("c64b"), "aplicar_valores_duracao": 2},
    )
    frase = ((r.get_json() or {}).get("relatorio_orcamento") or {}).get("frase") or ""
    _garante([q(b["amount_brl"]) for b in _bvs(e2)] == [Decimal("200.00")], f"R$: {_bvs(e2)}")
    _garante("BV em reais ficou" in frase, f"frase sem o aviso: {frase!r}")


def _post_jinja(eid: int, venda: str, valor_bv: str) -> None:
    form = {
        "action": "update_comercial",
        "sale_value": venda,
        "sale_value_gross": venda,
        "acrescimo_tipo[]": ["BV"],
        "acrescimo_descricao[]": [""],
        "acrescimo_value[]": [valor_bv],
        "acrescimo_is_percent[]": ["0"],
        "acrescimo_bv_recipient[]": [QUEM],
        "acrescimo_bv_pix[]": [PIX],
    }
    r = _cliente("com").post(f"/events/{eid}", data=form)
    _garante(r.status_code in (200, 302), f"Jinja → {r.status_code}")


def cen_65_jinja_bv_redigitado() -> None:
    # Redigitado junto com a venda: fica como digitado (não é proporcionado de novo).
    eid = _evento_com_bv_reais("c65a", venda=1000, nota=False, valor=100)
    _post_jinja(eid, "2.000,00", "150,00")
    _garante([q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("150.00")], f"redigitado: {_bvs(eid)}")
    # Reenviado sem mexer: acompanha a venda.
    e2 = _evento_com_bv_reais("c65b", venda=1000, nota=False, valor=100)
    _post_jinja(e2, "2.000,00", "100,00")
    _garante([q(b["amount_brl"]) for b in _bvs(e2)] == [Decimal("200.00")], f"sem mexer: {_bvs(e2)}")


def _segurar_evento(eid: int, sql_dentro: list[str], acao: Callable[[], None]) -> None:
    """Outra transação trava a linha do evento (`FOR UPDATE`), escreve e só comita depois que a
    `acao` (numa thread) já está esperando — a corrida de duas gravações, sem sorte."""
    import time

    erro: list[BaseException] = []

    def alvo() -> None:
        try:
            acao()
        except BaseException as exc:  # noqa: BLE001
            erro.append(exc)

    with _externo.connect() as conn:
        tx = conn.begin()
        conn.execute(text("SELECT id FROM calendar_events WHERE id = :i FOR UPDATE"), {"i": eid})
        for sql in sql_dentro:
            conn.execute(text(sql), {"i": eid})
        t = threading.Thread(target=alvo)
        t.start()
        time.sleep(2)
        tx.commit()
    t.join(30)
    if erro:
        raise erro[0]


def cen_66_corridas() -> None:
    # (a) Duas mudanças de venda: a outra (1.000 → 1.200, BV 120) comita enquanto esta (→ 1.500) espera.
    eid = _evento_com_bv_reais("c66a", venda=1000, nota=False, valor=100)
    corpo = _corpo_comercial(eid, sale_value=1500, sale_value_gross=1500)
    _segurar_evento(
        eid,
        [
            "UPDATE calendar_events SET sale_value = 1200, sale_value_gross = 1200 WHERE id = :i",
            "UPDATE event_acrescimos SET amount_brl = 120, value = 120 WHERE event_id = :i AND is_bv",
        ],
        lambda: _cliente("com").patch(f"/api/events/{eid}/comercial", json=corpo),
    )
    _garante([q(b["amount_brl"]) for b in _bvs(eid)] == [Decimal("150.00")], f"B10 dobrada: {_bvs(eid)}")
    # (b) O editor (BV 10%) contra a venda que muda ao mesmo tempo: a régua usa a venda nova.
    e2 = _evento_google("c66b", venda=1000)
    _segurar_evento(
        e2,
        ["UPDATE calendar_events SET sale_value = 2000, sale_value_gross = 2000 WHERE id = :i"],
        lambda: _put("com", e2, [_bv_item(10, pct=True)]),
    )
    esperado = q(q(Decimal("2000") / Decimal("1.1")) * 10 / 100)
    _garante([q(b["amount_brl"]) for b in _bvs(e2)] == [esperado], f"régua com venda velha: {_bvs(e2)}")


def cen_67_marcar_pago_confere_o_valor() -> None:
    eid = _evento_com_bv_reais("c67", nota=False, valor=200)
    bv = _bvs(eid)[0]
    c = _cliente("fin")
    corpo = {"item_type": "bv", "item_id": bv["id"], "status": "pago", "valor_esperado": 150}
    r = c.post("/api/financeiro/pagamentos/set-status", json=corpo)
    _garante(
        r.status_code == 409 and _bvs(eid)[0]["bv_payment_status"] == "nao_pago",
        f"valor diferente: {r.status_code} {_bvs(eid)}",
    )
    r = c.post("/api/financeiro/pagamentos/set-status", json=dict(corpo, valor_esperado=200))
    _garante(r.status_code == 200 and _bvs(eid)[0]["bv_payment_status"] == "pago", f"igual: {r.status_code}")
    r = c.post(
        "/api/financeiro/pagamentos/set-status",
        json={"item_type": "bv", "item_id": bv["id"], "status": "nao_pago"},
    )
    _garante(r.status_code == 200, f"sem valor_esperado (bundle antigo): {r.status_code}")


def cen_68_rastro_do_bv_pago() -> None:
    eid = _evento_com_bv_reais("c68", nota=False, valor=200)
    _set_status_bv(eid, "pago")
    itens = _como_carregou(eid)
    itens[0]["bv_pix"] = "novo-pix-9876@exemplo.test"
    _garante(_put("com", eid, itens).status_code == 200, "PUT")
    rows = _no_banco(
        "SELECT detail FROM audit_logs WHERE entity_type = 'event_bv' AND entity_id = :i "
        "AND detail LIKE 'BV pago%'", i=eid
    )
    _garante(len(rows) == 1, f"rastro: {rows}")
    detalhe = rows[0][0] or ""
    _garante("PIX" in detalhe and "novo-pix-9876@exemplo.test" not in detalhe and PIX not in detalhe,
             f"rastro sem máscara: {detalhe!r}")
    # Sem troca, sem rastro.
    _put("com", eid, _como_carregou(eid))
    _garante(len(_no_banco(
        "SELECT id FROM audit_logs WHERE entity_type = 'event_bv' AND entity_id = :i "
        "AND detail LIKE 'BV pago%'", i=eid
    )) == 1, "rastro sem troca")


def cen_50_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(
            CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0,
            "evento sobrou",
        )
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")


CENARIOS = [
    ("1. D2: 1.309,52 com nota → BV 100,00", cen_01_d2),
    ("2. % sobre a mesma base, com fixo e outro %", cen_02_base_comum),
    ("3. BV fixo em 1h e 4h", cen_03_fixo),
    ("4. duração extra (6h)", cen_04_duracao_extra),
    ("5. personalizado → vazio", cen_05_personalizado),
    ("6. paridade com a memória do espelho (±0,01)", cen_06_paridade_espelho),
    ("7. valores_brl no snapshot; total intacto", cen_07_valores_brl_no_snapshot),
    ("8. prefill com os 4 valores", cen_08_prefill),
    ("9. detalhe com descricao e PIX; Casting sem", cen_09_detalhe),
    ("10. criação: linha cheia em R$, comissão sobre venda − BV", cen_10_criacao),
    ("11. a lista do navegador é ignorada", cen_11_lista_do_navegador),
    ("12. venda 5% abaixo → 140,13", cen_12_proporcao),
    ("13. cortesia e a definir: sem linha, sem 400", cen_13_cortesia_e_a_definir),
    ("14. vincular e aplicar: a mesma linha; não duplica", cen_14_vincular_e_aplicar),
    ("15. venda digitada: sem linha, alerta; lançar apaga; cancelado sem", cen_15_venda_digitada),
    ("16. salvar sem mexer preserva PIX e pago", cen_16_salvar_sem_mexer),
    ("17. régua do % (100; 130; R$ 50 junto; legado) + mutação", cen_17_regua_do_percentual),
    ("18. Planilha com PIX e sem 'falta PIX'", cen_18_planilha),
    ("19. DEVE FALHAR: prefill como Casting", cen_19_prefill_casting),
    ("20. DEVE FALHAR: criação como Financeiro", cen_20_criacao_financeiro),
    ("21. DEVE FALHAR: editor como Casting; satélite", cen_21_put_casting_e_satelite),
    ("22. DEVE FALHAR: vínculo como Casting", cen_22_vinculo_casting),
    ("23. sem orçamento: igual a hoje", cen_23_sem_orcamento),
    ("24. orçamento sem acréscimos: igual a hoje", cen_24_orcamento_sem_acrescimos),
    ("25. comissão paga intacta", cen_25_comissao_paga_intacta),
    ("26. DRE: o CPV sobe o BV", cen_26_dre),
    ("27. regressão (--regressao)", cen_27_regressao),
    ("31. DEVE FALHAR: PIX obrigatório (criação, vínculo, editor)", cen_31_pix_obrigatorio),
    ("32. DEVE FALHAR: autoria da 301", cen_32_autoria_301),
    (
        "33. DEVE FALHAR: sem sessão, BV pago pela Comercial, Artista 3D, 'como Casting'",
        cen_33_resto_rbac,
    ),
    ("34. concorrência: uma linha", cen_34_concorrencia),
    ("35. bundle antigo no editor", cen_35_bundle_antigo_editor),
    ("36. DEVE FALHAR: erro sem estrago (API e Jinja)", cen_36_erro_sem_estrago),
    ("37. duração sem a chave", cen_37_duracao_sem_chave),
    ("38. trocar orçamento; voltar a definir", cen_38_trocar_e_voltar),
    ("39. rastro sem PIX", cen_39_rastro_sem_pix),
    ("40. entradas ruins sem exceção", cen_40_entradas_ruins),
    ("42. mês passado: a frase diz a Planilha", cen_42_mes_passado),
    ("43. gêmeo Jinja igual ao PUT", cen_43_gemeo_jinja),
    ("44. bv_que_acompanha", cen_44_proporcao_pura),
    ("45. alerta: papéis, corte, ausências", cen_45_alerta),
    ("46. DEVE FALHAR: bundle antigo na criação com BV", cen_46_bundle_antigo_criacao),
    ("47. DEVE FALHAR: BV antigo sem PIX", cen_47_bv_antigo_sem_pix),
    ("48. a venda muda: BV a pagar acompanha; pago e a definir ficam", cen_48_venda_muda),
    ("49. BV em R$ como digitado; 1.800 → 180; volta 200 + mutação", cen_49_bv_em_reais),
    ("51. DEVE FALHAR: vírgula aceita; ilegível recusado; 'bv' é BV", cen_51_virgula_e_tipo),
    ("52. BV novo sem id nasce a pagar", cen_52_identidade),
    ("53. só a nota muda", cen_53_so_a_nota),
    ("54. DEVE FALHAR: % com venda a definir", cen_54_percentual_sem_venda),
    ("55. comissão na hora (conexão separada)", cen_55_comissao_na_hora),
    ("56. alerta em reais (como o 2407)", cen_56_alerta_em_reais),
    ("57. DEVE FALHAR: BV pago não sai, não muda de tipo nem de valor", cen_57_bv_pago_nao_sai),
    ("58. corte do commit e corte vazio: o passado não acende", cen_58_corte_vazio),
    ("59. nota diferente entre orçamento e evento: o mesmo BV", cen_59_nota_diferente),
    ("60. DEVE FALHAR: BV sem valor não some", cen_60_bv_sem_valor),
    ("61. DEVE FALHAR: '1.500' e números enormes recusados", cen_61_milhar_e_extremos),
    ("62. DEVE FALHAR: id repetido não duplica BV pago", cen_62_id_repetido),
    ("63. DEVE FALHAR: BV negativo", cen_63_bv_negativo),
    ("64. vincular e aplicar roda a B10", cen_64_vincular_roda_a_b10),
    ("65. Jinja: BV redigitado com a venda fica como digitado", cen_65_jinja_bv_redigitado),
    ("66. corridas: B10 e editor contra a venda que muda", cen_66_corridas),
    ("67. DEVE FALHAR: marcar pago confere o valor mostrado", cen_67_marcar_pago_confere_o_valor),
    ("68. rastro da troca de PIX no BV pago", cen_68_rastro_do_bv_pago),
]


def main() -> int:
    print("Feature 305 — o BV do orçamento chega ao evento")
    from app.calendar import orcamento_evento_ops

    # A constante como está no commit, antes do monkeypatch (cenário 58).
    estado["corte_original"] = orcamento_evento_ops.CORTE_ALERTA_BV
    preparar()
    try:
        # `--so=58,59` roda só esses (iteração rápida; o portão é a rodada inteira).
        so = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--so=")), None)
        for nome, fn in CENARIOS:
            if so is None or nome.split(".", 1)[0] in so:
                cenario(nome, fn)
    finally:
        cenario("50. limpeza", cen_50_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK · chamadas ao Google: {GOOGLE['insert']}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
