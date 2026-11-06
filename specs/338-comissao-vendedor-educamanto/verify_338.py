"""Verificação da feature 338 — comissão do vendedor e lucro real no EducaManto.

Cenários (spec §Verificação):
 1. Jundiaí Shopping (1321, real): com Thaís e R$ 1.500, o responsável recebe R$ 771,82.  (sem gravar)
 2. Colégio Santo Américo (354, real): imposto e gastos saem da base → R$ 61,01.          (sem gravar)
 3. O Comercial salva R$ 1.000 no card de um EducaManto: nasce a linha do vendedor (fonte própria,
    ciclo do evento) e a do responsável cai na mesma medida × 5%.
 4. Valor muda, vendedor troca, chave ausente não mexe, valor apagado cancela a linha a pagar.
 5. Linha do vendedor paga: o valor muda e a paga fica.
 6. Vendedor sem comissão: nenhuma linha, base cheia.
 7. Validação (acima da venda, negativo, fora do EducaManto, venda "a definir") e o 403 do Casting.
    (o 403 DEVE sair)
 8. Cancelamento com 50% retido: vendedor R$ 500, responsável cheia × 50%; o valor do cancelado não
    muda (409 `cancelado`), o mesmo valor passa.
 9. DRE e comissão prevista somam a comissão do vendedor.
 9b. Comissão comum: o número de hoje, ao centavo (SC-003).
10. API: o detalhe separa as duas comissões; Comissões rotula a linha do vendedor.
11. Limpeza.

Contra o espelho `manto_338` (research R9). Google DUBLADO (agenda falsa que só responde a id que
conhece); e-mail num coletor. Requisições HTTP FORA do `app_context`; escrita conferida por conexão
separada. O `responsável EducaManto` de Configurações é trocado por um usuário descartável e
restaurado no fim. Por isso nenhum cenário chama rota que roda `_resync_pending_commissions`
(Comissões, Planilha): com o responsável trocado, ela passaria as comissões EducaManto REAIS do
espelho ao descartável, e a limpeza as apagaria — o cenário 10 lê as entradas pela função.

Rodar (PowerShell)::

    cd C:\\tmp\\mp338
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\338-comissao-vendedor-educamanto\\verify_338.py
"""

from __future__ import annotations

import copy
import os
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()
if "localhost" not in os.environ["DATABASE_URL"] and "127.0.0.1" not in os.environ["DATABASE_URL"]:
    raise SystemExit("verify_338 só roda contra banco local (DATABASE_URL não é localhost)")

import httplib2  # noqa: E402
from googleapiclient.errors import HttpError  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, email_service, limiter, maps  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import ORIGEM_VENDEDOR_EDUCAMANTO, RoleName, now_sp  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    EventPayment,
    Role,
    SiteSetting,
    SpecialExpense,
    User,
)

PREFIX = "__v338_"
GID = "__v338_gid"
# No LIKE, `_` é curinga: sem escapar, "__v338_%" casaria também "__v338u…" de outra coisa.
PREFIX_LIKE = PREFIX.replace("_", "\\_")
GID_LIKE = GID.replace("_", "\\_")
SENHA = "verify-338-senha"
CENTAVO = Decimal("0.01")
JUNDIAI, SANTO_AMERICO = 1321, 354

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {"eventos": []}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


# ── dublês ──────────────────────────────────────────────────────────────────────────────────────
def _http(status: int) -> HttpError:
    return HttpError(
        httplib2.Response({"status": str(status)}), b'{"error": {"message": "duble 338"}}'
    )


class _Pedido:
    def __init__(self, fn: Callable[[], object]):
        self._fn = fn

    def execute(self, **_kw):
        return self._fn()


class _GoogleFalso:
    """Agenda falsa que falha fechado: só responde a id que ela conhece."""

    def __init__(self) -> None:
        self.itens: dict[str, dict] = {}

    def registrar(self, item: dict) -> None:
        self.itens[item["id"]] = item

    def _get(self, gid: str):
        if gid not in self.itens:
            raise _http(503)
        return copy.deepcopy(self.itens[gid])

    def _patch(self, gid: str, body: dict):
        if gid not in self.itens:
            raise _http(503)
        self.itens[gid].update(copy.deepcopy(body))
        return copy.deepcopy(self.itens[gid])

    def _delete(self, gid: str):
        if gid not in self.itens:
            raise _http(503)
        self.itens.pop(gid)
        return ""


class _Eventos:
    def __init__(self, g: _GoogleFalso):
        self.g = g

    def list(self, **_kw):
        return _Pedido(lambda: (_ for _ in ()).throw(_http(503)))

    def list_next(self, *_a, **_k):
        return None

    def get(self, calendarId=None, eventId=None, **_kw):  # noqa: N803 — nomes da API do Google
        return _Pedido(lambda: self.g._get(eventId))

    def insert(self, calendarId=None, body=None, **_kw):  # noqa: N803
        return _Pedido(lambda: (_ for _ in ()).throw(_http(503)))

    def patch(self, calendarId=None, eventId=None, body=None, **_kw):  # noqa: N803
        return _Pedido(lambda: self.g._patch(eventId, body or {}))

    def update(self, calendarId=None, eventId=None, body=None, **_kw):  # noqa: N803
        return _Pedido(lambda: self.g._patch(eventId, body or {}))

    def delete(self, calendarId=None, eventId=None, **_kw):  # noqa: N803
        return _Pedido(lambda: self.g._delete(eventId))


class _Servico:
    def __init__(self, g: _GoogleFalso):
        self.g = g

    def events(self):
        return _Eventos(self.g)


class _CredFalsa:
    valid = True
    expired = False
    token = "verify-338"


google = _GoogleFalso()
cal_service.build = lambda *a, **k: _Servico(google)
cal_service.load_credentials = lambda: _CredFalsa()
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: None
email_service._send = lambda *a, **k: True
email_service.send_async = lambda fn, *args: fn(*args)


# ── harness ────────────────────────────────────────────────────────────────────────────────────
def q(x) -> Decimal:
    return Decimal(str(x)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _no_banco_grava(sql: str, **params) -> None:
    with _externo.begin() as conn:
        conn.execute(text(sql), params)


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — o harness registra e segue para o próximo cenário
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _usuario(sufixo: str, nome: str, papel: str, *, comissiona: bool = True) -> int:
    user = User(name=nome, email=f"{PREFIX}{sufixo}@manto.local", is_active=True, has_access=True)
    user.set_password(SENHA)
    user.receives_commission = comissiona
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(user)
    db.session.commit()
    return user.id


def _cliente(chave: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": f"{PREFIX}{chave}@manto.local", "password": SENHA})
    _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


def _evento(rotulo: str, *, venda: float | None, vendedor: str | None, nota: bool = False,
            dias: int = 12, titulo: str | None = None) -> int:  # fmt: skip
    """Evento pelo ORM, sem elenco (nenhuma vaga inventada), registrado na agenda falsa."""
    inicio = datetime.combine(now_sp().date() + timedelta(days=dias), datetime.min.time()).replace(
        hour=15
    )
    gid = f"{GID}-{uuid.uuid4().hex[:10]}"
    titulo = titulo or f"(EDUCAMANTO) {PREFIX}{rotulo}"
    google.registrar({"id": gid, "status": "confirmed", "summary": titulo})
    with app.app_context():
        ev = CalendarEvent(
            title=titulo, event_type="EDUCAMANTO" if titulo.startswith("(EDU") else "CORP",
            start_at=inicio, end_at=inicio + timedelta(hours=2), google_event_id=gid, source="platform",
            location=f"{PREFIX}Escola, São Paulo",
            sale_value=Decimal(str(venda)) if venda is not None else None,
            sale_value_gross=Decimal(str(venda)) if venda is not None else None,
            with_invoice=nota, seller_id=estado[vendedor] if vendedor else None,
            sale_date=now_sp().date() if venda is not None else None,
        )  # fmt: skip
        db.session.add(ev)
        db.session.commit()
        estado["eventos"].append(ev.id)
        return ev.id


def _gasto(eid: int, valor: float, status: str = "aprovado", categoria: str = "Outros") -> None:
    with app.app_context():
        db.session.add(SpecialExpense(
            description=f"{PREFIX}gasto", category=categoria, amount=Decimal(str(valor)),
            expense_date=now_sp().date(), status=status, created_by_id=estado["sa"], event_id=eid,
            disbursement_type="fornecedor", supplier_name=f"{PREFIX}Fornecedor",
        ))  # fmt: skip
        db.session.commit()


def _corpo_comercial(eid: int, **troca) -> dict:
    with app.app_context():
        ev = db.session.get(CalendarEvent, eid)
        corpo = {
            "sale_value": float(ev.sale_value) if ev.sale_value is not None else None,
            "sale_value_gross": float(ev.sale_value_gross) if ev.sale_value_gross is not None else None,
            "transport_value": float(ev.transport_value or 0), "with_invoice": bool(ev.with_invoice),
            "is_cortesia_permuta": False, "seller_id": ev.seller_id,
            "sale_date": ev.sale_date.isoformat() if ev.sale_date else None,
            "commission_rate": None, "payment_method": ev.payment_method,
            "payment_installments": ev.payment_installments, "payment_due_date": None,
        }  # fmt: skip
    corpo.update(troca)
    return corpo


def _comercial(chave: str, eid: int, esperado: int = 200, **troca):
    r = _cliente(chave).patch(f"/api/events/{eid}/comercial", json=_corpo_comercial(eid, **troca))
    _garante(r.status_code == esperado,
             f"PATCH comercial {eid} ({chave}) → {r.status_code} {r.get_data(as_text=True)[:300]}")  # fmt: skip
    return r


def _linhas(eid: int, *, fonte: str | None) -> list:
    cond = "source IS NULL" if fonte is None else "source = :f"
    return _no_banco(
        f"SELECT id, seller_id, amount, status, payable_from, sale_date, original_id FROM commission_payments "
        f"WHERE event_id = :i AND {cond} ORDER BY id",
        i=eid, f=fonte,
    )  # fmt: skip


def _vivas(eid: int, *, fonte: str | None) -> list:
    return [x for x in _linhas(eid, fonte=fonte) if x.status != "cancelado"]


def _soma_viva(eid: int, seller_id: int, *, fonte: str | None) -> Decimal:
    return q(
        sum(
            (Decimal(x.amount) for x in _vivas(eid, fonte=fonte) if x.seller_id == seller_id),
            Decimal("0"),
        )
    )


def _responsavel(eid: int) -> Decimal:
    return _soma_viva(eid, estado["resp"], fonte=None)


def _data_do_evento(eid: int):
    return _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=eid)[0][0].date()


# ── preparo e limpeza ──────────────────────────────────────────────────────────────────────────
def limpar() -> None:
    ids = [r[0] for r in _no_banco(
        "SELECT id FROM calendar_events WHERE title LIKE :p OR google_event_id LIKE :g",
        p=f"%{PREFIX_LIKE}%", g=f"{GID_LIKE}%",
    )]  # fmt: skip
    tabelas = [r[0] for r in _no_banco(
        "SELECT table_name FROM information_schema.columns WHERE column_name = 'event_id' "
        "AND table_schema = 'public' AND table_name <> 'calendar_events'"
    )]  # fmt: skip
    usuarios = [r[0] for r in _no_banco("SELECT id FROM users WHERE email LIKE :p", p=f"{PREFIX_LIKE}%")]
    with _externo.begin() as conn:
        if ids:
            conn.execute(
                text("UPDATE commission_payments SET original_id = NULL WHERE event_id = ANY(:i)"),
                {"i": ids},
            )
            conn.execute(text(
                "DELETE FROM event_cancellation_bvs WHERE cancellation_id IN "
                "(SELECT id FROM event_cancellations WHERE event_id = ANY(:i))"
            ), {"i": ids})  # fmt: skip
            for t in ("event_cancellation_elenco",):
                conn.execute(text(
                    f"DELETE FROM {t} WHERE cancellation_id IN (SELECT id FROM event_cancellations WHERE event_id = ANY(:i))"
                ), {"i": ids})  # fmt: skip
            for t in sorted(tabelas):
                conn.execute(text(f"DELETE FROM {t} WHERE event_id = ANY(:i)"), {"i": ids})
            conn.execute(
                text("UPDATE calendar_events SET group_leader_id = NULL WHERE id = ANY(:i)"),
                {"i": ids},
            )
            conn.execute(text("DELETE FROM calendar_events WHERE id = ANY(:i)"), {"i": ids})
        conn.execute(
            text("DELETE FROM special_expenses WHERE description LIKE :p"), {"p": f"{PREFIX_LIKE}%"}
        )
        if usuarios:
            conn.execute(
                text("DELETE FROM commission_payments WHERE seller_id = ANY(:u)"), {"u": usuarios}
            )
            conn.execute(text("DELETE FROM notifications WHERE user_id = ANY(:u)"), {"u": usuarios})
            conn.execute(text("DELETE FROM user_roles WHERE user_id = ANY(:u)"), {"u": usuarios})
            conn.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": usuarios})


def _linhas_reais_do_responsavel() -> list:
    """As comissões do responsável EducaManto real do espelho — o verify não pode mexer nelas."""
    return [
        tuple(r)
        for r in _no_banco(
            "SELECT cp.id, cp.seller_id, cp.amount, cp.status FROM commission_payments cp "
            "JOIN site_settings s ON s.id = 1 WHERE cp.seller_id = s.educamanto_seller_id ORDER BY cp.id"
        )
    ]


def preparar() -> None:
    limpar()
    with app.app_context():
        st = SiteSetting.query.get(1)
        estado["edu_real"] = st.educamanto_seller_id
        estado["linhas_reais"] = _linhas_reais_do_responsavel()
        estado["thays"] = User.query.filter_by(email="thays@mantoproducoes.com.br").one().id
        estado["sa"] = _usuario("sa", f"{PREFIX}Super", RoleName.SUPERADMIN)
        estado["com"] = _usuario("com", f"{PREFIX}Comercial", RoleName.COMERCIAL)
        estado["vend"] = _usuario("vend", f"{PREFIX}Vendedora", RoleName.COMERCIAL)
        estado["vend2"] = _usuario("vend2", f"{PREFIX}Vendedor Dois", RoleName.COMERCIAL)
        estado["semcom"] = _usuario(
            "semcom", f"{PREFIX}Sem Comissão", RoleName.COMERCIAL, comissiona=False
        )
        estado["resp"] = _usuario("resp", f"{PREFIX}Responsável", RoleName.COMERCIAL)
        estado["cast"] = _usuario("cast", f"{PREFIX}Casting", RoleName.CASTING)
        st = SiteSetting.query.get(1)
        st.educamanto_seller_id = estado["resp"]
        db.session.commit()


def restaurar_configuracoes() -> None:
    with app.app_context():
        st = SiteSetting.query.get(1)
        st.educamanto_seller_id = estado.get("edu_real")
        db.session.commit()


# ── cenários ───────────────────────────────────────────────────────────────────────────────────
def _comissao_real(
    eid: int, *, vendedor: int | None = None, valor: Decimal | None = None
) -> tuple[Decimal, Decimal]:
    """A comissão do responsável REAL de um evento do espelho, sem gravar nada (rollback no fim)."""
    from app.financeiro.comissoes_ops import _event_commission, comissao_do_vendedor_edu

    with app.app_context():
        try:
            st = SiteSetting.query.get(1)
            st.educamanto_seller_id = estado["edu_real"]
            ev = db.session.get(CalendarEvent, eid)
            _garante(
                ev is not None and ev.is_educamanto, f"evento {eid} não é EducaManto no espelho"
            )
            if vendedor is not None:
                ev.seller_id = vendedor
                ev.educamanto_seller_commission = valor
            comissao = _event_commission(ev, st)
            do_vendedor, _quem = comissao_do_vendedor_edu(ev, st)
            return q(comissao), q(do_vendedor)
        finally:
            db.session.rollback()


def cen_01_jundiai() -> None:
    sem, _ = _comissao_real(JUNDIAI)
    _garante(sem == q("846.82"), f"Jundiaí sem a Thaís: {sem} (esperado 846,82 = 5% × 16.936,35)")
    com, vend = _comissao_real(JUNDIAI, vendedor=estado["thays"], valor=Decimal("1500"))
    _garante(vend == q("1500"), f"comissão da vendedora {vend}")
    _garante(com == q("771.82"), f"Jundiaí com a Thaís: {com} (esperado 771,82)")


def cen_02_santo_americo() -> None:
    com, _ = _comissao_real(SANTO_AMERICO)
    _garante(com == q("61.01"), f"Santo Américo: {com} (esperado 61,01 = 5% × 1.220,13)")


def cen_03_comercial_salva() -> None:
    e1 = _evento("e1", venda=10000, vendedor="vend")
    estado["e1"] = e1
    _gasto(e1, 500)
    _gasto(e1, 300, status="pendente")
    _gasto(e1, 200, categoria=SpecialExpense.CATEGORY_DEVOLUCAO)
    _comercial("com", e1, educamanto_seller_commission=1000)
    ev = _no_banco("SELECT educamanto_seller_commission FROM calendar_events WHERE id = :i", i=e1)[
        0
    ]
    _garante(q(ev[0]) == q(1000), f"coluna do evento {ev[0]}")
    vend = _vivas(e1, fonte=ORIGEM_VENDEDOR_EDUCAMANTO)
    _garante(len(vend) == 1, f"linhas do vendedor {vend}")
    linha = vend[0]
    _garante(linha.seller_id == estado["vend"] and q(linha.amount) == q(1000) and linha.status == "a_pagar",
             f"linha do vendedor {linha}")  # fmt: skip
    _garante(
        linha.payable_from == _data_do_evento(e1), f"ciclo {linha.payable_from} ≠ dia do evento"
    )
    _garante(linha.sale_date == now_sp().date(), f"data da venda {linha.sale_date}")
    _garante(
        _responsavel(e1) == q("425.00"), f"responsável {_responsavel(e1)} (esperado 5% × 8.500)"
    )


def cen_04_acompanha() -> None:
    e1 = estado["e1"]
    _comercial("sa", e1, educamanto_seller_commission=1200)
    vend = _vivas(e1, fonte=ORIGEM_VENDEDOR_EDUCAMANTO)
    _garante(len(vend) == 1 and q(vend[0].amount) == q(1200), f"valor não acompanhou {vend}")
    _garante(_responsavel(e1) == q("415.00"), f"responsável {_responsavel(e1)}")
    linha_id = vend[0].id
    _comercial("sa", e1, seller_id=estado["vend2"], educamanto_seller_commission=1200)
    vend = _vivas(e1, fonte=ORIGEM_VENDEDOR_EDUCAMANTO)
    _garante(len(vend) == 1 and vend[0].id == linha_id and vend[0].seller_id == estado["vend2"],
             f"troca de vendedor {vend}")  # fmt: skip
    corpo = _corpo_comercial(e1)  # sem a chave nova: o bundle antigo
    r = _cliente("sa").patch(f"/api/events/{e1}/comercial", json=corpo)
    _garante(r.status_code == 200, f"PATCH sem a chave → {r.status_code}")
    valor = _no_banco(
        "SELECT educamanto_seller_commission FROM calendar_events WHERE id = :i", i=e1
    )[0][0]
    _garante(q(valor) == q(1200), f"chave ausente apagou o valor ({valor})")
    _comercial("sa", e1, educamanto_seller_commission=None)
    _garante(
        not _vivas(e1, fonte=ORIGEM_VENDEDOR_EDUCAMANTO),
        "valor apagado e a linha a pagar seguiu viva",
    )
    _garante(_responsavel(e1) == q("475.00"), f"responsável {_responsavel(e1)}")


def cen_05_paga_fica() -> None:
    e1 = estado["e1"]
    _comercial("sa", e1, educamanto_seller_commission=800)
    vend = _vivas(e1, fonte=ORIGEM_VENDEDOR_EDUCAMANTO)
    _garante(len(vend) == 1 and q(vend[0].amount) == q(800), f"linha nova {vend}")
    _no_banco_grava("UPDATE commission_payments SET status = 'pago', paid_at = :d WHERE id = :i",
                    d=now_sp().date(), i=vend[0].id)  # fmt: skip
    _comercial("sa", e1, educamanto_seller_commission=900)
    vend = _vivas(e1, fonte=ORIGEM_VENDEDOR_EDUCAMANTO)
    _garante(
        len(vend) == 1 and vend[0].status == "pago" and q(vend[0].amount) == q(800),
        f"paga mudou {vend}",
    )
    _garante(_responsavel(e1) == q("430.00"), f"responsável {_responsavel(e1)}")


def cen_06_sem_comissao() -> None:
    e2 = _evento("e2", venda=8000, vendedor="semcom")
    estado["e2"] = e2
    _comercial("sa", e2, educamanto_seller_commission=1000)
    _garante(not _vivas(e2, fonte=ORIGEM_VENDEDOR_EDUCAMANTO), "vendedor sem comissão ganhou linha")
    _garante(
        _responsavel(e2) == q("400.00"), f"responsável {_responsavel(e2)} (esperado 5% × 8.000)"
    )


def cen_07_validacao_e_403() -> None:
    e2 = estado["e2"]
    for valor in (9000, -5, "abc"):
        r = _comercial("sa", e2, esperado=400, educamanto_seller_commission=valor)
        campos = (r.get_json().get("error") or {}).get("fields") or {}
        _garante("educamanto_seller_commission" in campos, f"{valor}: sem o campo no erro {campos}")
    corp = _evento("corp", venda=5000, vendedor="vend", titulo=f"(CORP) {PREFIX}corp")
    _comercial("sa", corp, esperado=400, educamanto_seller_commission=100)
    a_definir = _evento("adef", venda=None, vendedor="vend")
    _comercial("sa", a_definir, educamanto_seller_commission=500)
    _garante(
        not _vivas(a_definir, fonte=ORIGEM_VENDEDOR_EDUCAMANTO),
        "venda a definir com linha do vendedor",
    )
    # O que DEVE falhar: o Casting não grava o card Comercial.
    r = _cliente("cast").patch(f"/api/events/{e2}/comercial",
                               json=_corpo_comercial(e2, educamanto_seller_commission=10))  # fmt: skip
    _garante(r.status_code == 403, f"Casting gravou o card ({r.status_code}) — DEVIA ser 403")


def cen_08_cancelado() -> None:
    e3 = _evento("e3", venda=10000, vendedor="vend")
    estado["e3"] = e3
    _gasto(e3, 500)
    _comercial("sa", e3, educamanto_seller_commission=1000)
    _garante(_responsavel(e3) == q("425.00"), f"antes do ato: responsável {_responsavel(e3)}")
    with app.app_context():
        db.session.add(
            EventPayment(event_id=e3, file_path=f"{PREFIX}comprovante.pdf", amount=Decimal("5000"))
        )
        db.session.commit()
    corpo = {"motivo": "Cliente desistiu (verify 338)", "devolucao": {"modo": "nada"}}
    r = _cliente("sa").post(f"/api/events/{e3}/cancelar", json=corpo)
    _garante(r.status_code == 200, f"cancelar → {r.status_code} {r.get_data(as_text=True)[:300]}")
    canc = _no_banco(
        "SELECT educamanto_seller_id, educamanto_seller_commission, commission_cost FROM event_cancellations "
        "WHERE event_id = :i", i=e3,
    )[0]  # fmt: skip
    _garante(canc[0] == estado["vend"] and q(canc[1]) == q(1000), f"congelado do vendedor {canc}")
    _garante(q(canc[2]) == q(1500), f"custo congelado {canc[2]} (esperado 500 de gastos + 1.000)")
    vend = _soma_viva(e3, estado["vend"], fonte=ORIGEM_VENDEDOR_EDUCAMANTO)
    _garante(vend == q("500.00"), f"vendedor no cancelado {vend} (esperado 1.000 × 50%)")
    _garante(
        _responsavel(e3) == q("212.50"), f"responsável no cancelado {_responsavel(e3)} (425 × 50%)"
    )
    r = _comercial("sa", e3, esperado=409, educamanto_seller_commission=2000)
    codigo = (r.get_json().get("error") or {}).get("codigo") or r.get_json().get("codigo")
    _garante(codigo == "cancelado", f"409 sem o código cancelado: {r.get_json()}")
    _comercial("sa", e3, educamanto_seller_commission=1000)  # o mesmo valor passa
    from app.calendar.cancel_ops import resumos_cancelados, totais_cancelamentos

    with app.app_context():
        totais = totais_cancelamentos(list(resumos_cancelados([e3]).values()))
    _garante(
        q(totais["comissao_retido"]) == q("712.50"),
        f"comissão do retido nos totais {totais['comissao_retido']}",
    )
    # Convergência (T029, FR-005): a troca de vendedor no cancelado leva a comissão do vendedor
    # do retido ao novo — o antigo vai a 0 (a linha a pagar dele é cancelada), o novo leva R$ 500.
    _comercial("sa", e3, seller_id=estado["vend2"], educamanto_seller_commission=1000)
    _garante(
        _soma_viva(e3, estado["vend"], fonte=ORIGEM_VENDEDOR_EDUCAMANTO) == q("0.00"),
        "troca no cancelado: o vendedor antigo ficou com a comissão do vendedor",
    )
    _garante(
        _soma_viva(e3, estado["vend2"], fonte=ORIGEM_VENDEDOR_EDUCAMANTO) == q("500.00"),
        f"troca no cancelado: o novo {_soma_viva(e3, estado['vend2'], fonte=ORIGEM_VENDEDOR_EDUCAMANTO)}",
    )
    congelado = _no_banco(
        "SELECT educamanto_seller_id FROM event_cancellations WHERE event_id = :i", i=e3
    )[0][0]
    _garante(congelado == estado["vend2"], f"congelado do vendedor não passou ao novo ({congelado})")
    _garante(
        _responsavel(e3) == q("212.50"), f"troca no cancelado mexeu no responsável {_responsavel(e3)}"
    )


def cen_09_dre() -> None:
    from app.financeiro.routes import _compute_drg
    from app.financeiro.vendas_ops import build_kpis

    with app.app_context():
        st = SiteSetting.query.get(1)
        e1 = db.session.get(CalendarEvent, estado["e1"])
        drg = _compute_drg([e1], st, Decimal("0"), Decimal("0"))
        _garante(
            q(drg["comissoes"]) == q("1330.00"), f"DRE comissões {drg['comissoes']} (430 + 900)"
        )
        kpis = build_kpis([e1], st, estado["vend2"])
        _garante(
            q(kpis["comissao_prevista"]) == q("900.00"), f"comissão prevista do vendedor {kpis}"
        )
        kpis = build_kpis([e1], st, None)
        _garante(q(kpis["comissao_prevista"]) == q("1330.00"), f"comissão prevista total {kpis}")


def cen_09b_comum() -> None:
    from app.financeiro.comissoes_ops import (
        _event_bv_total,
        _event_commission,
        _get_commission_rate,
    )

    with app.app_context():
        st = SiteSetting.query.get(1)
        eventos = (
            CalendarEvent.query.filter(
                CalendarEvent.sale_value > 0, CalendarEvent.cancelled_at.is_(None),
                CalendarEvent.group_leader_id.is_(None), CalendarEvent.is_cortesia_permuta.is_(False),
                ~CalendarEvent.title.ilike("(EDU%"), CalendarEvent.event_type != "VIRTUAL",
                CalendarEvent.seller_id.isnot(None),
            ).order_by(CalendarEvent.id.desc()).limit(200).all()
        )  # fmt: skip
        conferidos = 0
        for ev in eventos:
            if not ev.seller or not ev.seller.receives_commission:
                continue
            base = Decimal(ev.sale_value) - _event_bv_total(ev)
            esperado = q(max(base, Decimal("0")) * _get_commission_rate(ev, st) / Decimal("100"))
            _garante(
                q(_event_commission(ev, st)) == esperado,
                f"evento {ev.id}: {_event_commission(ev, st)} ≠ {esperado}",
            )
            conferidos += 1
        _garante(conferidos >= 50, f"só {conferidos} comissões comuns conferidas")


def cen_10_api() -> None:
    e1 = estado["e1"]
    r = _cliente("sa").get(f"/api/events/{e1}")
    _garante(r.status_code == 200, f"detalhe → {r.status_code}")
    j = r.get_json()
    venda, kpi = j.get("venda") or {}, j.get("kpi") or {}
    _garante(
        venda.get("educamanto_seller_commission") == 900.0,
        f"venda.educamanto_seller_commission {venda.get('educamanto_seller_commission')}",
    )
    _garante(venda.get("mostra_comissao_do_vendedor") is True, "venda.mostra_comissao_do_vendedor")
    _garante(
        q(kpi.get("commission")) == q("430.00"),
        f"kpi.commission {kpi.get('commission')} (só o responsável)",
    )
    _garante(
        q(kpi.get("seller_commission") or 0) == q("800.00"),
        f"kpi.seller_commission {kpi.get('seller_commission')}",
    )
    _garante(
        kpi.get("seller_commission_name") == f"{PREFIX}Vendedor Dois",
        f"kpi.seller_commission_name {kpi.get('seller_commission_name')}",
    )
    # As entradas de Comissões pela função, e NÃO por `GET /api/financeiro/comissoes`: a rota
    # recalcula toda linha a pagar do espelho, e com o responsável EducaManto trocado pelo
    # descartável ela passaria as comissões reais do responsável para ele (e a limpeza as apagaria).
    from app.financeiro.comissoes_ops import get_month_entries

    mes = now_sp().date().strftime("%Y-%m")
    with app.app_context():
        entradas = [e.to_dict() for e in get_month_entries(mes, estado["vend2"]) if e.event_id == e1]
    _garante(entradas and all(e.get("origem") == ORIGEM_VENDEDOR_EDUCAMANTO for e in entradas),
             f"origem nas entradas {entradas}")  # fmt: skip


def cen_11_limpeza() -> None:
    restaurar_configuracoes()
    limpar()
    _garante(
        not _no_banco("SELECT 1 FROM calendar_events WHERE title LIKE :p", p=f"%{PREFIX_LIKE}%"),
        "evento sobrou",
    )
    _garante(
        not _no_banco("SELECT 1 FROM users WHERE email LIKE :p", p=f"{PREFIX_LIKE}%"), "usuário sobrou"
    )
    _garante(
        not _no_banco("SELECT 1 FROM special_expenses WHERE description LIKE :p", p=f"{PREFIX_LIKE}%"),
        "gasto sobrou",
    )
    with app.app_context():
        _garante(
            SiteSetting.query.get(1).educamanto_seller_id == estado.get("edu_real"),
            "responsável não restaurado",
        )
    _garante(
        _linhas_reais_do_responsavel() == estado.get("linhas_reais"),
        "o verify mexeu nas comissões reais do responsável EducaManto do espelho",
    )


def main() -> int:
    print("Feature 338 — comissão do vendedor e lucro real no EducaManto")
    preparar()
    passos = [
        ("1. Jundiaí Shopping: R$ 771,82 com a Thaís e os R$ 1.500", cen_01_jundiai),
        ("2. Santo Américo: imposto e gastos → R$ 61,01", cen_02_santo_americo),
        ("3. card Comercial cria a linha do vendedor; responsável cai", cen_03_comercial_salva),
        (
            "4. valor e vendedor acompanham; chave ausente não mexe; apagar cancela",
            cen_04_acompanha,
        ),
        ("5. linha do vendedor paga fica", cen_05_paga_fica),
        ("6. vendedor sem comissão: sem linha, base cheia", cen_06_sem_comissao),
        ("7. validação e o 403 do Casting (o 403 DEVE sair)", cen_07_validacao_e_403),
        ("8. cancelado: vendedor e responsável × retido; 409 ao alterar", cen_08_cancelado),
        ("9. DRE e comissão prevista somam o vendedor", cen_09_dre),
        ("9b. comissão comum sem mudança", cen_09b_comum),
        ("10. API: detalhe separa as duas; Comissões rotula", cen_10_api),
    ]
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("11. limpeza", cen_11_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
