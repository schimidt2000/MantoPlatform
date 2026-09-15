"""Verificação da feature 299 — sem valor e cobranças: o grupo é uma venda só.

Cenários (17 linhas da tabela da spec):
  1. Corte: maio fora; grupo com evento vivo em 31/05 fora; com o de 31/05 cancelado, dentro.
  2. O que é "sem valor": vazio, 0, 0,01 e 0,99 entram, 1,00 não; hoje em "ainda vai acontecer";
     ordem dos dois grupos; cores 7/8/31.
  3. Fora de "sem valor": cancelado, ensaio, cortesia, 🟧, 🟠, Loja Virtual; visita agrupada.
  4. Grupos em "sem valor": principal com valor, sem valor, cortesia e de R$ 0,01.
  5. Valor a definir pela API, R$ 0,01 recusado (cadastro e aba Comercial) e comissão tardia
     (R22/R42/R45: 5e, 5e', 5f, 5g, 5h, 5h', controle 5j).
  6. Edição completa (importado, R$ 0,01, satélite) e orçamento sobre o R$ 0,01.
  7. Grupo em Cobranças: réplica do 344 sai; o de 10 mil vira uma linha.
  8. Data do grupo com um evento cancelado que tem comprovante.
  9. Vencimento: 2 dias antes, data combinada, parcela, data combinada vence parcela, piso na venda.
 10. Centavos e sinal pendente.
 11. Metade paga e evento a 20 dias aparece.
 12. Fora de Cobranças: 0,01, cortesia com valor, Loja Virtual, 🟧, ensaio, cancelado.
 13. Conteúdo, cor, selo, ordem e as chaves antigas.
 14. Total, cards e a falha forçada (R44/R47).
 15. Página do evento no grupo.
 16. CASTING e FINANCEIRO recusados (DEVEM falhar), com controles.
 17. Limpeza.

O GOOGLE AGENDA NUNCA É CHAMADO (R27). `routes.insert_event` e as `update_event` viram falsos que
contam; `service.insert_event` e `service.load_credentials` estouram se alguém chegar ao Google real.
Todo evento de teste tem "[TESTE verify 299] pode apagar" no título e `v299-` no `google_event_id`.

Escrita conferida por **conexão separada** e requisições HTTP **fora** de `app.app_context()`.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    .venv/Scripts/python.exe specs/299-sem-valor-cobrancas/verify_299.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    Client,
    CommissionPayment,
    EventClient,
    EventInstallment,
    EventPayment,
    OrcamentoHistory,
    Role,
    SiteSetting,
    User,
)

PREFIX = "v299-"
SENHA = "verify-299-senha"
TITULO_TESTE = "[TESTE verify 299] pode apagar"
CORTE_ESPERADO = date(2026, 6, 1)
SELO_VALIDO = re.compile(r"^(Atrasado|Vence hoje|Sinal pendente|Vence em 1 dia|Vence em \d+ dias)$")
CHAVES_ANTIGAS = ("event_id", "event_title", "start_at", "sale", "received", "saldo", "severity", "due_date")

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False  # pelo OBJETO: `RATELIMIT_ENABLED` só é lido no `init_app`

# ── O Google fica de fora ────────────────────────────────────────────────────────────────────────
import app.calendar.event_ops as _event_ops  # noqa: E402
import app.calendar.routes as _rotas  # noqa: E402
import app.calendar.service as _servico  # noqa: E402

_google = {"insert": 0, "update": 0}


def _insert_falso(*_args, **_kwargs):
    _google["insert"] += 1
    return {"id": f"{PREFIX}gc-{_google['insert']}"}


def _update_falso(*_args, **_kwargs):
    _google["update"] += 1
    return {}


def _google_real(*_args, **_kwargs):
    raise RuntimeError("verify 299: Google real")


_rotas.insert_event = _insert_falso
for _modulo in (_rotas, _servico, _event_ops):
    if hasattr(_modulo, "update_event"):
        _modulo.update_event = _update_falso
_servico.insert_event = _google_real
_servico.load_credentials = _google_real

resultados: list[tuple[str, bool, str]] = []
estado: dict = {"ids": {}}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    """Lê pelo banco, por fora da sessão do app (o autoflush esconde falta de commit)."""
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchone()


def _no_banco_todas(sql: str, **params):
    """Como `_no_banco`, todas as linhas."""
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — harness: registra e segue
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def D(valor) -> Decimal:  # noqa: N802 — curto de propósito: é o comparador de dinheiro
    """Dinheiro do JSON comparado como `Decimal`, nunca como `float`."""
    _garante(valor is not None, "valor ausente no JSON (chave nova não veio)")
    return Decimal(str(valor)).quantize(Decimal("0.01"))


def _usuario(sufixo: str, papel: str) -> tuple[str, int]:
    email = f"{PREFIX}{sufixo}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        db.session.add(user)
    user.set_password(SENHA)
    user.roles.clear()
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.commit()
    return email, user.id


def _login(c, email: str) -> None:
    r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
    _garante(r.status_code == 200, f"login {email} → {r.status_code}")


def _chamar(email: str, metodo: str, url: str, corpo: dict | None = None):
    """Uma requisição autenticada, fora de qualquer contexto de aplicação."""
    with app.test_client() as c:
        _login(c, email)
        return getattr(c, metodo)(url, json=corpo) if corpo is not None else getattr(c, metodo)(url)


# ── Semeadura (direto no banco) ──────────────────────────────────────────────────────────────────


def _d(dias: int) -> date:
    return estado["hoje"] + timedelta(days=dias)


def _evento(nome: str, dia: date, valor=None, **opcoes) -> int:
    """Um evento de teste; `lider` faz dele outro evento de um grupo (campos comerciais vazios)."""
    inicio = datetime.combine(dia, time(15, 0))
    v = None if valor is None else Decimal(str(valor))
    bruto = opcoes.get("bruto", "igual")
    lider = opcoes.get("lider")
    ev = CalendarEvent(
        title=f"{opcoes.get('marcador', '')}{nome} {TITULO_TESTE}",
        start_at=inicio,
        end_at=inicio + timedelta(hours=3),
        google_event_id=f"{PREFIX}{nome}",
        source=opcoes.get("fonte", "platform"),
        event_type=opcoes.get("tipo"),
        sale_value=None if lider else v,
        sale_value_gross=None if lider else (v if bruto == "igual" else bruto),
        is_cortesia_permuta=bool(opcoes.get("cortesia")),
        payment_method=opcoes.get("forma"),
        payment_due_date=opcoes.get("data_combinada"),
        sale_date=opcoes.get("venda_em"),
        seller_id=opcoes.get("vendedor"),
        group_leader_id=lider,
        group_name=opcoes.get("grupo"),
        is_outside_sp=False,
        cancelled_at=datetime.utcnow() if opcoes.get("cancelado") else None,
        deletion_requested_at=datetime.utcnow() if opcoes.get("exclusao") else None,
    )
    if opcoes.get("cadastrado_em"):
        ev.created_at = opcoes["cadastrado_em"]
    db.session.add(ev)
    db.session.flush()
    estado["ids"][nome] = ev.id
    return ev.id


def _pag(event_id: int, valor) -> None:
    db.session.add(EventPayment(event_id=event_id, file_path="v299/fake.pdf", amount=Decimal(str(valor))))


def _parcela(event_id: int, dia: date, valor) -> None:
    db.session.add(EventInstallment(event_id=event_id, due_date=dia, amount=Decimal(str(valor))))


def _cliente(event_id: int, nome: str, relacao: str, telefone: str) -> None:
    cl = Client(name=f"{PREFIX}{nome}", phone=telefone, phone_display=f"+{telefone}", source="manual")
    db.session.add(cl)
    db.session.flush()
    db.session.add(EventClient(event_id=event_id, client_id=cl.id, relationship_type=relacao))


def _comissao(event_id: int, valor, status: str) -> None:
    db.session.add(
        CommissionPayment(
            event_id=event_id,
            event_title=f"{PREFIX}comissão {TITULO_TESTE}",
            seller_id=estado["comercial_id"],
            sale_date=estado["mes_passado"],
            amount=Decimal(str(valor)),
            status=status,
            paid_at=estado["hoje"] if status == "pago" else None,
        )
    )


def _orcamento(dono_id: int) -> int:
    snap = {
        "performers": [], "coordenador_qty": 0, "fora_sp": False, "km_ida": 0,
        "transporte_tipo": "carro", "num_carros": 1, "num_colaboradores": 0,
        "event_date": _d(29).isoformat(), "event_time": "15:00", "nota_fiscal": False, "acrescimos": [],
    }
    entry = OrcamentoHistory(
        user_id=dono_id, client_name=f"{PREFIX}cliente", event_location=f"{PREFIX}local",
        event_date=_d(29).isoformat(), total_1h=Decimal("3000"), total_2h=Decimal("4200"),
        total_3h=Decimal("5000"), total_4h=Decimal("5600"), has_show=False, form_snapshot=json.dumps(snap),
    )
    db.session.add(entry)
    db.session.flush()
    return entry.id


def _preparar_listas(e: dict) -> None:
    """Cenários 1 a 4: corte, o que é sem valor, quem fica fora e grupos."""
    _evento("s1-maio-sem", date(2026, 5, 20))
    _evento("s1-maio-com", date(2026, 5, 20), 1000)
    g1 = _evento("s1-g1p", date(2026, 6, 2), 1000, grupo="G1")
    _evento("s1-g1s", date(2026, 5, 31), lider=g1)
    g2 = _evento("s1-g2p", date(2026, 6, 2), 1000, grupo="G2")
    _evento("s1-g2s", date(2026, 5, 31), lider=g2, cancelado=True)

    for nome, valor, dias in (("s2-vazio", None, 40), ("s2-zero", 0, 41), ("s2-001", "0.01", 42),
                              ("s2-099", "0.99", 43), ("s2-100", "1.00", 44)):
        _evento(nome, _d(dias), valor)
    for nome, dias in (("s2-hoje", 0), ("s2-m5", -5), ("s2-m20", -20), ("s2-p7", 7), ("s2-p8", 8), ("s2-p31", 31)):
        _evento(nome, _d(dias))

    _evento("s3-canc", _d(10), cancelado=True)
    _evento("s3-ensaio", _d(10), tipo="ENSAIO")
    _evento("s3-cort", _d(10), 0, cortesia=True)
    _evento("s3-visita", _d(10), marcador="🟧 ")
    _evento("s3-grav", _d(10), marcador="🟠 ")
    _evento("s3-virtual", _d(10), tipo="VIRTUAL")
    show = _evento("s3-show", _d(12), grupo="Show com visita")
    _evento("s3-vt", _d(11), lider=show, marcador="🟧 ")
    _evento("s3-exclusao", _d(13), exclusao=True)

    ga = _evento("s4-ga", _d(15), 2000, grupo="GA")
    _evento("s4-ga-s", _d(16), lider=ga)
    gb = _evento("s4-gb", _d(17), grupo="GB")
    _pag(_evento("s4-gb-s", _d(18), lider=gb), 300)
    gc = _evento("s4-gc", _d(19), 0, cortesia=True, grupo="GC")
    _evento("s4-gc-s", _d(20), lider=gc)
    gd = _evento("s4-gd", _d(21), "0.01", grupo="GD")
    _evento("s4-gd-s", _d(22), lider=gd)


def _preparar_escritas(e: dict) -> None:
    """Cenários 5, 6 e 16: eventos que as requisições vão alterar."""
    antes = datetime.utcnow() - timedelta(days=35)
    mes = estado["mes_passado"]
    vend = estado["comercial_id"]
    _evento("s5e", _d(30), venda_em=mes, cadastrado_em=antes, vendedor=vend)
    _comissao(_evento("s5f", _d(30), 1500, venda_em=mes, cadastrado_em=antes, vendedor=vend), "37.50", "pago")
    _comissao(_evento("s5g", _d(30), "0.01", venda_em=mes, cadastrado_em=antes, vendedor=vend), "0.00", "a_pagar")
    _comissao(_evento("s5h", _d(30), "0.01", venda_em=mes, cadastrado_em=antes, vendedor=vend), "0.00", "pago")
    _evento("s5i", _d(30), vendedor=vend)

    _evento("s6a", _d(26), fonte="google_calendar")
    _evento("s6b1", _d(26), "0.01", vendedor=vend)
    _evento("s6b2", _d(26), "0.01", bruto=None, vendedor=vend)
    c6 = _evento("s6c-p", _d(27), 3000, grupo="G6C", vendedor=vend)
    _evento("s6c-s", _d(28), lider=c6)
    _evento("s6d", _d(29), "0.01", vendedor=vend)
    e["orc_comercial"] = _orcamento(vend)

    _evento("s16-orc", _d(35), vendedor=vend)
    e["orc_financeiro"] = _orcamento(estado["financeiro_id"])


def _preparar_cobrancas(e: dict) -> None:
    """Cenários 7 a 13: grupos, vencimento, centavos, sinal, fora de Cobranças, conteúdo."""
    a = _evento("s7a", _d(2), 5508, grupo="344 réplica")
    _pag(a, 3078)
    _pag(_evento("s7a-s", _d(3), lider=a), 3078)
    b = _evento("s7b", _d(12), 10000, grupo="Grupo de 10 mil")
    _pag(b, 2000)
    _pag(_evento("s7b-s", _d(13), lider=b), 3000)

    p8 = _evento("s8", date(2026, 6, 21), 3000, grupo="G8")
    _pag(p8, 2000)
    _evento("s8-s", date(2026, 6, 20), lider=p8)
    _pag(_evento("s8-c", date(2026, 6, 19), lider=p8, cancelado=True), 500)

    _pag(_evento("s9a", _d(16), 4000, forma="avista"), 2000)
    _pag(_evento("s9b", _d(16), 4000, forma="avista", data_combinada=_d(6)), 2000)
    _evento("s9c", _d(-4), 3000, forma="faturado", data_combinada=_d(26))
    d9 = _evento("s9d", _d(30), 3000, forma="parcelado_datas")
    for dias in (5, 15, 25):
        _parcela(d9, _d(dias), 1000)
    _parcela(_evento("s9e", _d(30), 3000, data_combinada=_d(28)), _d(20), 3000)
    f9 = _evento("s9f", _d(30), 3000, grupo="G9F", forma="parcelado_datas")
    for dias in (-3, 10, 20):
        _parcela(f9, _d(dias), 1000)
    _pag(_evento("s9f-s", _d(31), lider=f9), 1000)
    _evento("s9g", _d(1), 2000, venda_em=estado["hoje"])

    _pag(_evento("s10a", _d(20), 1000), "999.50")
    _pag(_evento("s10b", _d(20), 9235), 4617)
    _evento("s10c", _d(20), 2000, venda_em=estado["hoje"])
    _evento("s10d", _d(20), 2000, forma="faturado", data_combinada=_d(30))
    e10 = _evento("s10e", _d(25), 3000, forma="parcelado_datas")
    _parcela(e10, _d(10), 1500)
    _parcela(e10, _d(20), 1500)
    _pag(_evento("s11", _d(20), 4000), 2000)

    _evento("s12a", _d(1), "0.01")
    _evento("s12b", _d(1), 800, cortesia=True)
    _evento("s12c", _d(1), 150, tipo="VIRTUAL")
    _evento("s12d", _d(1), 1000, marcador="🟧 ")
    _evento("s12e", _d(1), 1000, tipo="ENSAIO")
    _evento("s12f", _d(1), 1000, cancelado=True)
    _preparar_conteudo()


def _preparar_conteudo() -> None:
    """Cenário 13: cliente, cor, selo e ordem."""
    a = _evento("s13a", _d(20), 1000)
    _cliente(a, "Outra", "Aniversariante", "5511929901301")
    _cliente(a, "Contratante", "Contratante", "5511929901302")
    b = _evento("s13b", _d(20), 1000)
    _cliente(b, "Primeira", "Mãe", "5511929901303")
    for nome, dias in (("s13a", None), ("s13b", None), ("s13c", 20), ("s13d2", 4), ("s13d3", 5), ("s13d31", 33)):
        eid = estado["ids"][nome] if dias is None else _evento(nome, _d(dias), 1000)
        _pag(eid, 500)
    _evento("s13e", _d(3), 1000)
    _evento("s13f", _d(42), 1000)


def preparar() -> None:
    e = estado
    e["comercial"], e["comercial_id"] = _usuario("comercial", RoleName.COMERCIAL)
    e["financeiro"], e["financeiro_id"] = _usuario("financeiro", RoleName.FINANCEIRO)
    e["casting"], e["casting_id"] = _usuario("casting", RoleName.CASTING)
    settings = db.session.get(SiteSetting, 1)
    corte = settings.release_date if settings and settings.release_date else None
    _garante(corte == CORTE_ESPERADO, f"corte do espelho diferente de 01/06 ({corte})")
    e["hoje"] = now_sp().date()
    e["mes_passado"] = e["hoje"].replace(day=1) - timedelta(days=1)
    _preparar_listas(e)
    _preparar_escritas(e)
    _preparar_cobrancas(e)
    db.session.commit()


# ── Leitura ──────────────────────────────────────────────────────────────────────────────────────


def _home(email: str | None = None) -> dict:
    r = _chamar(email or estado["comercial"], "get", "/api/dashboard")
    _garante(r.status_code == 200, f"/api/dashboard → {r.status_code}")
    return r.get_json()


def _comercial(j: dict) -> dict:
    c = j.get("comercial")
    _garante(isinstance(c, dict), "bloco `comercial` ausente")
    return c


def _cobranca(c: dict, eid: int) -> dict | None:
    return next((x for x in c.get("pending_payments") or [] if x.get("event_id") == eid), None)


def _sem_valor(c: dict, eid: int) -> tuple[str, dict] | None:
    sv = c.get("sem_valor")
    _garante(isinstance(sv, dict), "bloco `sem_valor` ausente")
    for grupo in ("a_acontecer", "ja_aconteceu"):
        for linha in sv.get(grupo) or []:
            if linha.get("event_id") == eid:
                return grupo, linha
    return None


def _detalhe(email: str, eid: int) -> dict:
    r = _chamar(email, "get", f"/api/events/{eid}")
    _garante(r.status_code == 200, f"GET /api/events/{eid} → {r.status_code}")
    return r.get_json()


def _ids() -> dict:
    return estado["ids"]


def _corpo_evento(titulo: str, dia: date, **extra) -> dict:
    corpo = {
        "title": f"{titulo} {TITULO_TESTE}", "event_type": "", "date": dia.isoformat(), "start": "15:00",
        "end": "18:00", "location": "", "description": "", "characters": [], "needs_rehearsal": False,
        "clients": [], "seller_id": estado["comercial_id"], "payment_method": "avista",
    }
    corpo.update(extra)
    return corpo


def _corpo_comercial(valor, **extra) -> dict:
    corpo = {
        "sale_value": valor, "sale_value_gross": valor, "transport_value": None, "with_invoice": False,
        "is_cortesia_permuta": False, "seller_id": estado["comercial_id"], "sale_date": None,
        "commission_rate": None, "payment_method": "avista", "payment_installments": None,
        "payment_due_date": None,
    }
    corpo.update(extra)
    return corpo


def _campos_do_erro(r) -> dict:
    return ((r.get_json() or {}).get("error") or {}).get("fields") or {}


def _comissoes(eid: int) -> list:
    return _no_banco_todas(
        "SELECT status, amount, payable_from FROM commission_payments "
        "WHERE event_id = :i AND status <> 'cancelado' ORDER BY id",
        i=eid,
    )


# ── Cenários ─────────────────────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    e, c = _ids(), _comercial(_home())
    _garante(_sem_valor(c, e["s1-maio-sem"]) is None, "evento de maio sem valor apareceu em Sem valor")
    _garante(_cobranca(c, e["s1-maio-com"]) is None, "evento de maio com saldo apareceu em Cobranças")
    _garante(_cobranca(c, e["s1-g1p"]) is None and _sem_valor(c, e["s1-g1p"]) is None,
             "grupo com outro evento vivo em 31/05 deveria ficar fora (data do grupo)")
    linha = _cobranca(c, e["s1-g2p"])
    _garante(linha is not None, "grupo com o evento de 31/05 cancelado deveria aparecer")
    _garante(linha.get("data_evento") == "2026-06-02", f"data do grupo {linha.get('data_evento')}")


def cen_02() -> None:
    e, c = _ids(), _comercial(_home())
    for nome, a_definir, simbolico in (("s2-vazio", True, False), ("s2-zero", True, False),
                                       ("s2-001", False, True), ("s2-099", False, True)):
        achado = _sem_valor(c, e[nome])
        _garante(achado is not None, f"{nome} fora de Sem valor")
        linha = achado[1]
        _garante(linha.get("a_definir") is a_definir and linha.get("valor_simbolico") is simbolico,
                 f"{nome}: a_definir={linha.get('a_definir')} valor_simbolico={linha.get('valor_simbolico')}")
    _garante(_sem_valor(c, e["s2-100"]) is None, "R$ 1,00 não é sem valor")
    grupo, linha = _sem_valor(c, e["s2-hoje"])
    _garante(grupo == "a_acontecer" and linha.get("dias_ate_o_evento") == 0, f"hoje em {grupo}")
    _garante(_sem_valor(c, e["s2-m5"])[0] == "ja_aconteceu", "o de 5 dias atrás deveria estar em já aconteceu")
    cores = {n: _sem_valor(c, e[n])[1].get("severidade") for n in ("s2-m5", "s2-hoje", "s2-p7", "s2-p8", "s2-p31")}
    esperado = {"s2-m5": "vermelho", "s2-hoje": "vermelho", "s2-p7": "vermelho", "s2-p8": "amarelo", "s2-p31": "cinza"}
    _garante(cores == esperado, f"cores {cores}")
    ordem = [x["event_id"] for x in c["sem_valor"]["a_acontecer"]]
    posicoes = [ordem.index(e[n]) for n in ("s2-hoje", "s2-p7", "s2-p8", "s2-p31")]
    _garante(posicoes == sorted(posicoes), f"ainda vai acontecer fora de ordem: {posicoes}")
    passados = [x["event_id"] for x in c["sem_valor"]["ja_aconteceu"]]
    _garante(passados.index(e["s2-m5"]) < passados.index(e["s2-m20"]), "já aconteceu: o mais recente primeiro")


def cen_03() -> None:
    e, c = _ids(), _comercial(_home())
    for nome in ("s3-canc", "s3-ensaio", "s3-cort", "s3-visita", "s3-grav", "s3-virtual", "s3-vt"):
        _garante(_sem_valor(c, e[nome]) is None, f"{nome} não deveria estar em Sem valor")
    achado = _sem_valor(c, e["s3-show"])
    _garante(achado is not None, "o show agrupado com a visita técnica deveria aparecer")
    _garante(achado[1].get("data_evento") == _d(12).isoformat(),
             f"a data do grupo deveria ignorar a visita: {achado[1].get('data_evento')}")
    _garante(_sem_valor(c, e["s3-exclusao"]) is not None, "controle: pedido de exclusão continua na lista")


def cen_04() -> None:
    e, c = _ids(), _comercial(_home())
    for nome in ("s4-ga", "s4-ga-s", "s4-gb-s", "s4-gc", "s4-gc-s", "s4-gd-s"):
        _garante(_sem_valor(c, e[nome]) is None, f"{nome} não deveria estar em Sem valor")
    achado = _sem_valor(c, e["s4-gb"])
    _garante(achado is not None, "grupo com principal sem valor deveria ter uma linha")
    linha = achado[1]
    _garante((linha.get("grupo_comercial") or {}).get("eventos") == 2, f"grupo_comercial {linha.get('grupo_comercial')}")
    _garante(D(linha.get("recebido")) == D(300), f"recebido do grupo {linha.get('recebido')}")
    _garante(_sem_valor(c, e["s4-gd"]) is not None, "principal de R$ 0,01 deveria estar em Sem valor")
    _garante(_cobranca(c, e["s4-gd"]) is None, "principal de R$ 0,01 não pode estar em Cobranças")


def cen_05() -> None:
    e, com = _ids(), estado["comercial"]
    r = _chamar(com, "post", "/api/events", _corpo_evento("5a", _d(25), valor_a_definir=True,
                                                          sale_value=None, sale_value_gross=None))
    _garante(r.status_code == 201, f"(a) POST com a marca → {r.status_code} {_campos_do_erro(r)}")
    eid = e["s5a"] = r.get_json()["event"]["id"]
    banco = _no_banco("SELECT sale_value, sale_value_gross, sale_date FROM calendar_events WHERE id=:i", i=eid)
    _garante(banco[0] is None and banco[1] is None, f"(a) valores gravados {banco[:2]}")
    _garante(banco[2] == estado["hoje"], f"(a) data da venda {banco[2]}")
    _garante(_sem_valor(_comercial(_home()), eid) is not None, "(a) o evento novo deveria estar em Sem valor")
    cob = _detalhe(com, eid).get("cobranca") or {}
    _garante(D(cob.get("outstanding")) == 0 and cob.get("sem_valor") is True and cob.get("enabled") is False,
             f"(a) cobranca {cob}")
    _cen_05_recusas()
    _cen_05_valor_posto(eid)
    _cen_05_comissao()


def _cen_05_recusas() -> None:
    com = estado["comercial"]
    antes = _google["insert"]
    for valor in (None, 0.5):
        r = _chamar(com, "post", "/api/events", _corpo_evento("5b", _d(25), sale_value=valor, sale_value_gross=valor))
        _garante(r.status_code == 400 and "sale_value" in _campos_do_erro(r), f"(b) sem a marca, {valor} → {r.status_code}")
    _garante(_google["insert"] == antes, "(b) a recusa chamou o Google")
    _garante(_no_banco("SELECT count(*) FROM calendar_events WHERE title LIKE :t", t=f"%5b {TITULO_TESTE}%")[0] == 0,
             "(b) evento recusado foi gravado")
    r = _chamar(com, "post", "/api/events", _corpo_evento("5c", _d(25), valor_a_definir=True, sale_value=None,
                                                          sale_value_gross=None, seller_id=None))
    _garante(r.status_code == 400 and "seller_id" in _campos_do_erro(r), f"(c) sem vendedor → {r.status_code}")


def _cen_05_valor_posto(eid: int) -> None:
    com, e = estado["comercial"], _ids()
    r = _chamar(com, "patch", f"/api/events/{eid}/comercial", _corpo_comercial(1500))
    _garante(r.status_code == 200, f"(d) PATCH /comercial com 1.500 → {r.status_code}")
    c = _comercial(_home())
    _garante(_sem_valor(c, eid) is None, "(d) saiu de Sem valor")
    linha = _cobranca(c, eid)
    _garante(linha is not None and linha.get("selo") == "Sinal pendente", f"(d) linha {linha}")
    _garante(_no_banco("SELECT sale_date FROM calendar_events WHERE id=:i", i=eid)[0] == estado["hoje"],
             "(d) a data da venda mudou")
    r = _chamar(com, "patch", f"/api/events/{e['s5i']}/comercial", _corpo_comercial(0.5))
    campos = _campos_do_erro(r)
    _garante(r.status_code == 400 and ("sale_value" in campos or "sale_value_gross" in campos),
             f"(i) /comercial com 0,50 → {r.status_code}")
    r = _chamar(com, "patch", f"/api/events/{e['s5i']}/comercial", _corpo_comercial(None))
    _garante(r.status_code == 200, f"(i) /comercial vazio → {r.status_code}")


def _cen_05_comissao() -> None:
    com, e, hoje = estado["comercial"], _ids(), estado["hoje"]
    mes = estado["mes_passado"].isoformat()
    r = _chamar(com, "patch", f"/api/events/{e['s5e']}/comercial", _corpo_comercial(1500, sale_date=mes))
    _garante(r.status_code == 200, f"(e) → {r.status_code}")
    linhas = _comissoes(e["s5e"])
    _garante(len(linhas) == 1 and linhas[0][2] == hoje, f"(e) comissão tardia: {linhas}")
    _chamar(com, "patch", f"/api/events/{e['s5e']}/comercial", _corpo_comercial(1500, sale_date=mes, payment_method="cartao"))
    _garante(_comissoes(e["s5e"])[0][2] == hoje, "(e') a 2ª sincronização apagou o payable_from")
    for corpo in (_corpo_comercial(None, sale_date=mes), _corpo_comercial(1500, sale_date=mes)):
        _chamar(com, "patch", f"/api/events/{e['s5f']}/comercial", corpo)
    linhas = _comissoes(e["s5f"])
    _garante(len(linhas) == 1 and linhas[0][0] == "pago" and D(linhas[0][1]) == D("37.50"), f"(f) {linhas}")
    _chamar(com, "patch", f"/api/events/{e['s5g']}/comercial", _corpo_comercial(1500, sale_date=mes))
    linhas = _comissoes(e["s5g"])
    _garante(len(linhas) == 1 and linhas[0][0] == "a_pagar" and linhas[0][2] == hoje and D(linhas[0][1]) > 0,
             f"(g) {linhas}")
    _cen_05_comissao_paga_de_zero(mes)
    r = _chamar(com, "post", "/api/events", _corpo_evento("5j", _d(25), sale_value=1500, sale_value_gross=1500,
                                                          sale_date=mes))
    _garante(r.status_code == 201, f"(j) POST → {r.status_code} {_campos_do_erro(r)}")
    linhas = _comissoes(r.get_json()["event"]["id"])
    _garante(len(linhas) == 1 and linhas[0][2] is None, f"(j) venda lançada agora com data do mês passado: {linhas}")


def _cen_05_comissao_paga_de_zero(mes: str) -> None:
    com, e, hoje = estado["comercial"], _ids(), estado["hoje"]
    _chamar(com, "patch", f"/api/events/{e['s5h']}/comercial", _corpo_comercial(1500, sale_date=mes))
    linhas = _comissoes(e["s5h"])
    pagas = [x for x in linhas if x[0] == "pago"]
    a_pagar = [x for x in linhas if x[0] == "a_pagar"]
    _garante(len(pagas) == 1 and D(pagas[0][1]) == 0, f"(h) a paga de 0,00 mudou: {linhas}")
    _garante(len(a_pagar) == 1 and a_pagar[0][2] == hoje, f"(h) comissão de verdade: {linhas}")
    _chamar(com, "patch", f"/api/events/{e['s5h']}/comercial", _corpo_comercial(1500, sale_date=mes))
    with app.app_context():
        from app.financeiro.comissoes_ops import _sync_commission_payment

        _sync_commission_payment(CalendarEvent.query.get(e["s5h"]))
        db.session.commit()
    linhas = _comissoes(e["s5h"])
    _garante(sorted(x[0] for x in linhas) == ["a_pagar", "pago"], f"(h') a sincronização seguinte duplicou: {linhas}")


def cen_06() -> None:
    com, e = estado["comercial"], _ids()
    r = _chamar(com, "patch", f"/api/events/{e['s6a']}", _corpo_evento("s6a novo", _d(26), valor_a_definir=True,
                                                                     sale_value=None, sale_value_gross=None))
    _garante(r.status_code == 200, f"(a) importado sem valor, troca de título → {r.status_code} {_campos_do_erro(r)}")
    r = _chamar(com, "patch", f"/api/events/{e['s6b1']}", _corpo_evento("s6b1 novo", _d(26), sale_value=0.01,
                                                                      sale_value_gross=0.01))
    _garante(r.status_code == 200, f"(b) R$ 0,01 mantendo o valor → {r.status_code} {_campos_do_erro(r)}")
    r = _chamar(com, "patch", f"/api/events/{e['s6b2']}", _corpo_evento("s6b2 novo", _d(26), sale_value=0.01,
                                                                      sale_value_gross=None))
    _garante(r.status_code == 200, f"(b) R$ 0,01 com bruto vazio → {r.status_code} {_campos_do_erro(r)}")
    r = _chamar(com, "patch", f"/api/events/{e['s6b1']}", _corpo_evento("s6b1 novo", _d(26), sale_value=0.5,
                                                                      sale_value_gross=0.01))
    _garante(r.status_code == 400 and "sale_value" in _campos_do_erro(r), f"(b) trocar para 0,50 → {r.status_code}")
    r = _chamar(com, "patch", f"/api/events/{e['s6c-s']}", _corpo_evento("s6c-s novo", _d(28), sale_value=999,
                                                                       sale_value_gross=999, seller_id=None))
    _garante(r.status_code == 200, f"(c) satélite → {r.status_code} {_campos_do_erro(r)}")
    banco = _no_banco("SELECT sale_value, sale_value_gross, seller_id, payment_method FROM calendar_events "
                      "WHERE id=:i", i=e["s6c-s"])
    _garante(tuple(banco) == (None, None, None, None), f"(c) satélite gravou venda: {tuple(banco)}")
    corpo = {"orcamento_history_id": estado["orc_comercial"], "aplicar_valores_duracao": 2, "aplicar_equipe": False}
    r = _chamar(com, "patch", f"/api/events/{e['s6d']}/orcamento", corpo)
    _garante(r.status_code == 200, f"(d) orçamento sobre R$ 0,01 → {r.status_code}")
    _garante((r.get_json().get("relatorio_orcamento") or {}).get("valores") == 2,
             f"(d) relatório {r.get_json().get('relatorio_orcamento')}")
    valor = _no_banco("SELECT sale_value FROM calendar_events WHERE id=:i", i=e["s6d"])[0]
    _garante(valor is not None and D(valor) == D("4200"), f"(d) valor aplicado {valor}")


def cen_07() -> None:
    e, c = _ids(), _comercial(_home())
    _garante(_cobranca(c, e["s7a"]) is None, "réplica do 344 (3.078 + 3.078 de 5.508) ainda em Cobranças")
    linha = _cobranca(c, e["s7b"])
    _garante(linha is not None, "grupo de 10 mil deveria aparecer")
    _garante(D(linha["received"]) == D(5000) and D(linha["saldo"]) == D(5000), f"grupo de 10 mil: {linha}")
    _garante((linha.get("grupo_comercial") or {}).get("eventos") == 2, f"grupo_comercial {linha.get('grupo_comercial')}")
    _garante(_cobranca(c, e["s7b-s"]) is None, "o outro evento do grupo virou linha própria")


def cen_08() -> None:
    e, c = _ids(), _comercial(_home())
    linha = _cobranca(c, e["s8"])
    _garante(linha is not None, "grupo de junho deveria aparecer")
    _garante(linha.get("data_evento") == "2026-06-20" and linha.get("vencimento") == "2026-06-18",
             f"data {linha.get('data_evento')} vencimento {linha.get('vencimento')}")
    _garante(D(linha["received"]) == D(2500), f"o comprovante do cancelado deveria contar: {linha['received']}")
    _garante(linha.get("selo") == "Atrasado", f"selo {linha.get('selo')}")


def cen_09() -> None:
    e, c = _ids(), _comercial(_home())

    def linha(nome: str) -> dict:
        achada = _cobranca(c, e[nome])
        _garante(achada is not None, f"{nome} fora de Cobranças")
        return achada

    a = linha("s9a")
    _garante(a["vencimento"] == _d(14).isoformat() and a["vencimento_origem"] == "politica"
             and a["selo"] == "Vence em 14 dias", f"(a) {a['vencimento']} {a['vencimento_origem']} {a['selo']}")
    b = linha("s9b")
    _garante(b["vencimento"] == _d(6).isoformat() and b["vencimento_origem"] == "data_combinada", f"(b) {b['vencimento']}")
    _garante(linha("s9c")["selo"] == "Vence em 26 dias", f"(c) {linha('s9c')['selo']}")
    d9 = linha("s9d")
    _garante(d9["vencimento"] == _d(5).isoformat() and d9["vencimento_origem"] == "parcela", f"(d) {d9['vencimento']}")
    e9 = linha("s9e")
    _garante(e9["vencimento"] == _d(28).isoformat() and e9["vencimento_origem"] == "data_combinada", f"(e) {e9['vencimento']}")
    f9 = linha("s9f")
    _garante(f9["vencimento"] == _d(10).isoformat() and f9["selo"] != "Atrasado", f"(f) {f9['vencimento']} {f9['selo']}")
    g = linha("s9g")
    _garante((g["selo"], g["severidade"], g["nota"]) == ("Vence hoje", "vermelho", "sem sinal"),
             f"(g) {g['selo']} {g['severidade']} {g['nota']}")


def cen_10() -> None:
    e, c = _ids(), _comercial(_home())
    _garante(_cobranca(c, e["s10a"]) is None, "saldo de R$ 0,50 virou cobrança")
    for nome, esperado in (("s10b", False), ("s10c", True), ("s10d", False), ("s10e", False)):
        linha = _cobranca(c, e[nome])
        _garante(linha is not None, f"{nome} fora de Cobranças")
        _garante(linha.get("sinal_pendente") is esperado, f"{nome}: sinal_pendente={linha.get('sinal_pendente')}")


def cen_11() -> None:
    linha = _cobranca(_comercial(_home()), _ids()["s11"])
    _garante(linha is not None, "metade paga e evento a 20 dias continua escondida")
    _garante(linha.get("vencimento") == _d(18).isoformat() and linha.get("severidade") == "amarelo",
             f"{linha.get('vencimento')} {linha.get('severidade')}")


def cen_12() -> None:
    e, c = _ids(), _comercial(_home())
    for nome in ("s12a", "s12b", "s12c", "s12d", "s12e", "s12f"):
        _garante(_cobranca(c, e[nome]) is None, f"{nome} não deveria estar em Cobranças")


def cen_13() -> None:
    e, c = _ids(), _comercial(_home())
    linhas = c.get("pending_payments") or []
    for linha in linhas:
        _garante(all(k in linha for k in CHAVES_ANTIGAS), f"linha sem as chaves antigas: {linha.get('event_id')}")
        _garante(bool(SELO_VALIDO.match(linha.get("selo") or "")), f"selo fora do conjunto: {linha.get('selo')}")
    _garante(_cobranca(c, e["s13a"]).get("cliente") == f"{PREFIX}Contratante", "cliente: a Contratante primeiro")
    _garante(_cobranca(c, e["s13b"]).get("cliente") == f"{PREFIX}Primeira", "cliente: a 1ª cliente")
    sem_cliente = _cobranca(c, e["s13c"])
    _garante(sem_cliente.get("cliente") is None and TITULO_TESTE in sem_cliente.get("titulo", ""), "sem cliente: o título")
    for nome, cor, severity in (("s13d2", "vermelho", "urgent"), ("s13d3", "amarelo", "warn"),
                                ("s13d31", "cinza", "info"), ("s8", "vermelho", "atrasado")):
        linha = _cobranca(c, e[nome])
        _garante((linha.get("severidade"), linha.get("severity")) == (cor, severity),
                 f"{nome}: {linha.get('severidade')}/{linha.get('severity')}")
    amanha = _cobranca(c, e["s13e"])
    _garante((amanha["selo"], amanha["nota"], amanha["severidade"]) == ("Vence em 1 dia", "sem sinal", "vermelho"),
             f"sem sinal vencendo amanhã: {amanha['selo']} {amanha['nota']} {amanha['severidade']}")
    longe = _cobranca(c, e["s13f"])
    _garante((longe["selo"], longe["severidade"]) == ("Sinal pendente", "amarelo"), f"sem sinal a 40 dias: {longe['selo']}")
    ids = [x["event_id"] for x in linhas]
    cinzas = [i for i, x in enumerate(linhas) if x.get("severidade") == "cinza"]
    _garante(not cinzas or ids.index(e["s13f"]) < min(cinzas), "a venda sem sinal deveria vir antes das cinza")


def cen_14() -> None:
    j = _home()
    c = _comercial(j)
    linhas = c.get("pending_payments") or []
    resumo, sv = c.get("cobrancas_resumo"), c.get("sem_valor")
    _garante(isinstance(resumo, dict) and isinstance(sv, dict), "cobrancas_resumo/sem_valor ausentes")
    _confere_cores(resumo, linhas, "cobranças")
    _confere_cores(sv, (sv.get("a_acontecer") or []) + (sv.get("ja_aconteceu") or []), "sem valor")
    soma = sum((D(x["saldo"]) for x in linhas), Decimal("0"))
    _garante(D(resumo.get("total_em_aberto")) == soma, f"total_em_aberto {resumo.get('total_em_aberto')} ≠ {soma}")
    form = j.get("formularios") or {}
    linhas_form = (form.get("a_chegar") or []) + (form.get("ja_passou") or [])
    agir = sum(1 for x in linhas_form if x.get("severidade") in ("vermelho", "amarelo"))
    _garante(form.get("para_agir") == agir, f"formularios.para_agir {form.get('para_agir')} ≠ {agir}")
    _garante({"casting", "figurino", "comercial", "formularios"} <= set(j), f"blocos da Home: {sorted(j)}")
    for funcao in ("vendas_desde", "listar_cobrancas"):
        _confere_falha(funcao)


def _confere_cores(bloco: dict, linhas: list, nome: str) -> None:
    contagem = {cor: sum(1 for x in linhas if x.get("severidade") == cor) for cor in ("vermelho", "amarelo", "cinza")}
    _garante(bloco.get("por_cor") == contagem, f"{nome}: por_cor {bloco.get('por_cor')} ≠ {contagem}")
    _garante(bloco.get("para_agir") == contagem["vermelho"] + contagem["amarelo"], f"{nome}: para_agir")


def _confere_falha(funcao: str) -> None:
    from app.financeiro import cobranca_ops

    original = getattr(cobranca_ops, funcao)

    def quebra(*_args, **_kwargs):
        raise RuntimeError(f"verify 299: {funcao} forçada a falhar")

    setattr(cobranca_ops, funcao, quebra)
    try:
        j = _home()
    finally:
        setattr(cobranca_ops, funcao, original)
    c = j.get("comercial")
    _garante(c is not None, f"falha em {funcao}: o bloco comercial sumiu (deveria vir com os avisos)")
    _garante(c.get("cobrancas_resumo") is None and c.get("sem_valor") is None and c.get("pending_payments") == [],
             f"falha em {funcao}: envelope {({k: c.get(k) for k in ('cobrancas_resumo', 'sem_valor')})}")
    _garante(isinstance(j.get("formularios"), dict), f"falha em {funcao}: derrubou os formulários")


def cen_15() -> None:
    e, com = _ids(), estado["comercial"]
    det = _detalhe(com, e["s7b"])
    cob = det.get("cobranca") or {}
    _garante(D(cob.get("recebido")) == D(5000) and D(cob.get("outstanding")) == D(5000), f"principal: {cob}")
    _garante((det.get("mensagens") or {}).get("cobranca_amount") == "R$ 5.000,00",
             f"mensagem {(det.get('mensagens') or {}).get('cobranca_amount')}")
    outros = (det.get("pagamentos") or {}).get("outros_do_grupo") or []
    _garante(any(x.get("event_id") == e["s7b-s"] and D(x.get("total")) == D(3000) and x.get("quantidade") == 1
                 for x in outros), f"outros_do_grupo {outros}")
    det = _detalhe(com, e["s7b-s"])
    cob = det.get("cobranca") or {}
    _garante(cob.get("escopo") == "grupo_outro" and D(cob.get("recebido")) == D(5000)
             and D(cob.get("outstanding")) == D(5000) and cob.get("enabled") is False, f"satélite: {cob}")
    _garante(((det.get("event") or {}).get("group") or {}).get("leader", {}).get("id") == e["s7b"], "ponteiro do principal")
    cob = _detalhe(com, e["s10a"]).get("cobranca") or {}
    _garante(cob.get("quitado") is True and cob.get("enabled") is False, f"faltando 0,50: {cob}")
    cob = _detalhe(com, e["s12b"]).get("cobranca") or {}
    _garante(cob.get("sem_valor") is False and cob.get("enabled") is False and cob.get("cortesia") is True
             and cob.get("quitado") is False, f"cortesia: {cob}")
    # Cortesia nunca comissiona (dono, 15/09), nem a antiga com valor gravado e vendedor.
    with app.app_context():
        from app.financeiro.comissoes_ops import _sync_commission_payment

        ev = CalendarEvent.query.get(e["s12b"])
        ev.seller_id = estado["comercial_id"]
        _sync_commission_payment(ev)
        db.session.commit()
    vivas = [x for x in _comissoes(e["s12b"]) if x[0] != "cancelado"]
    _garante(not vivas, f"cortesia com valor ganhou comissão: {vivas}")


def cen_16() -> None:
    e = _ids()
    j = _home(estado["casting"])
    _garante(j.get("comercial") is None, "CASTING recebeu o bloco comercial")
    det = _chamar(estado["casting"], "get", f"/api/events/{e['s7b']}").get_json() or {}
    _garante(det.get("cobranca") is None and det.get("venda") is None, "CASTING recebeu a cobrança do evento")
    fin = estado["financeiro"]
    antes = _google["insert"]
    r = _chamar(fin, "post", "/api/events", _corpo_evento("16", _d(25), sale_value=1500, sale_value_gross=1500))
    _garante(r.status_code == 403, f"FINANCEIRO criando evento → {r.status_code} (esperado exatamente 403)")
    titulo = _no_banco("SELECT title FROM calendar_events WHERE id=:i", i=e["s11"])[0]
    r = _chamar(fin, "patch", f"/api/events/{e['s11']}", _corpo_evento("s11 alterado", _d(20), sale_value=4000))
    _garante(r.status_code == 403, f"FINANCEIRO editando evento → {r.status_code} (esperado exatamente 403)")
    _garante(_google["insert"] == antes, "a recusa chamou o Google")
    _garante(_no_banco("SELECT title FROM calendar_events WHERE id=:i", i=e["s11"])[0] == titulo, "o evento foi alterado")
    _garante(_cobranca(_comercial(_home(fin)), e["s7b"]) is not None, "controle: FINANCEIRO vê a cobrança do grupo")
    corpo = {"orcamento_history_id": estado["orc_financeiro"], "aplicar_valores_duracao": 2, "aplicar_equipe": False}
    r = _chamar(fin, "patch", f"/api/events/{e['s16-orc']}/orcamento", corpo)
    _garante(r.status_code == 200, f"controle: FINANCEIRO aplica orçamento → {r.status_code}")


# ── Limpeza ──────────────────────────────────────────────────────────────────────────────────────


def _tabelas_filhas() -> list[tuple[str, str]]:
    """Toda tabela com FK para `calendar_events` (menos ela mesma), lida do próprio banco."""
    linhas = db.session.execute(text(
        "SELECT DISTINCT tc.table_name, kcu.column_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema "
        "JOIN information_schema.constraint_column_usage ccu "
        "  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema "
        "WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'calendar_events' "
        "  AND tc.table_name <> 'calendar_events'"
    )).fetchall()
    return [(tabela, coluna) for tabela, coluna in linhas]


def limpar() -> None:
    db.session.rollback()
    padrao = f"{PREFIX}%"
    ids = [i for (i,) in db.session.execute(
        text("SELECT id FROM calendar_events WHERE google_event_id LIKE :p"), {"p": padrao})]
    if ids:
        db.session.execute(text("UPDATE calendar_events SET group_leader_id = NULL, parent_event_id = NULL, "
                                "orcamento_history_id = NULL WHERE id = ANY(:ids)"), {"ids": ids})
        for tabela, coluna in _tabelas_filhas():
            db.session.execute(text(f"DELETE FROM {tabela} WHERE {coluna} = ANY(:ids)"), {"ids": ids})
        db.session.execute(text("DELETE FROM calendar_events WHERE id = ANY(:ids)"), {"ids": ids})
    db.session.execute(text("DELETE FROM sync_logs WHERE google_event_id LIKE :p"), {"p": padrao})
    db.session.execute(text("DELETE FROM orcamento_history WHERE client_name LIKE :p"), {"p": padrao})
    Client.query.filter(Client.name.like(padrao)).delete(synchronize_session=False)
    usuarios = User.query.filter(User.email.like(f"{PREFIX}%@manto.local")).all()
    if usuarios:
        db.session.execute(text("DELETE FROM notifications WHERE user_id = ANY(:ids)"),
                           {"ids": [u.id for u in usuarios]})
    for user in usuarios:
        user.roles.clear()
        db.session.delete(user)
    db.session.commit()
    sobras = _no_banco("SELECT count(*) FROM calendar_events WHERE google_event_id LIKE :p", p=padrao)[0]
    _garante(sobras == 0, f"sobraram {sobras} eventos de teste")


def main() -> int:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True,
                 "MAIL_SUPPRESS_SEND desligado — o script mandaria e-mail de verdade")
        limpar()  # sobra de uma rodada interrompida
        preparar()

    print("Feature 299 — sem valor e cobranças, contra manto_local")
    try:
        cenario("1. corte pela data do grupo", cen_01)
        cenario("2. o que é sem valor; ordem e cores", cen_02)
        cenario("3. quem fica fora de Sem valor", cen_03)
        cenario("4. grupos em Sem valor", cen_04)
        cenario("5. valor a definir, R$ 0,01 recusado e comissão tardia", cen_05)
        cenario("6. edição completa e orçamento sobre o R$ 0,01", cen_06)
        cenario("7. grupo em Cobranças (344 e 10 mil)", cen_07)
        cenario("8. data do grupo e comprovante do cancelado", cen_08)
        cenario("9. vencimento", cen_09)
        cenario("10. centavos e sinal pendente", cen_10)
        cenario("11. metade paga a 20 dias aparece", cen_11)
        cenario("12. fora de Cobranças", cen_12)
        cenario("13. conteúdo, cor, selo, ordem e chaves antigas", cen_13)
        cenario("14. total, cards e falha forçada", cen_14)
        cenario("15. página do evento no grupo", cen_15)
        cenario("16. CASTING e FINANCEIRO recusados (DEVEM falhar)", cen_16)
    finally:
        with app.app_context():
            cenario("17. limpeza", limpar)

    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK · Google falso: {_google['insert']} insert, {_google['update']} update")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
