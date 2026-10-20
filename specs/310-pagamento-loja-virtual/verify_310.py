"""Verificação da feature 310 — pagamento da loja virtual ligado com segurança.

Roda contra o `manto_local` (Postgres). Escrito ANTES do núcleo (Princípio VIII): contra `98192e8`
os cenários marcados "deve falhar no HEAD" falham pelo motivo descrito na spec.

  B1  1–7    Um horário, uma família (venda dupla em seis formas; mesmo pedido em paralelo) + R-22
  B2  8–15   Todo pagamento termina em venda ou devolução (retorno, semântica da reconsulta,
             reprocessamento, pagamento em dobro, valor, reentrega, aviso forjado)
  B3  16–24  Ligar e desligar com segurança (trava local, interruptor, publicar, tela de config,
             recusa da operadora, aviso lento, RBAC)
  B4  25–26  Limites por família (IP do cliente)
  B5  27–29  Privacidade e segredo (pacote à operadora, máscara do log, aviso sem token)
  B6  30–32, 36  Equipe: a conferir, RBAC, sino, cancelar pedido pago
  B7  33–35  Família: seconds_left, client_token, estados de espera (texto: tela aberta)
  B8  37–38  Sala até a chamada; evento da loja não importado pela sincronização
  B9  39–40  API Key: link com validade e pagamento único / sem chave, pacote legado
  B10 41–42  Campanha fora da vitrine; limpeza de venda de teste
  B11 44     Limpeza; nada de rede escapou do dublê

O cenário 43 (regressão 205/304) roda à parte (tasks T056): são suítes longas.

A INFINITEPAY E O GOOGLE SÃO DUBLÊS QUE FALHAM FECHADO. A reconsulta imita o contrato provado em
produção (20/10/2026): sem `transaction_nsu`+`slug` que batam com a cobrança, responde
`nao_encontrado` (`{"success": false}`); com eles, `pago` ou `nao_pago`. Um disjuntor de rede
recusa qualquer conexão que não seja local. O Google conta chamadas e devolve ids falsos.

O núcleo novo é chamado PELO NOME em tempo de execução (`_ops(nome)`): função ausente vira
BLOQUEADO, não erro de import — para o verify rodar contra o HEAD e dizer o que falta.

Escrita conferida por conexão separada (`_db`). Requisições HTTP FORA de `app.app_context()`.
Limpeza no `finally`, com as configurações da loja restauradas.

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\310-pagamento-loja-virtual\\verify_310.py [--ate B3] [--rodadas 20]
"""

from __future__ import annotations

import argparse
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para manto_local (Postgres), nunca SQLite.")
if os.environ.get("MANTO_SEM_THREADS") != "1":
    sys.exit("ERRO: rode com MANTO_SEM_THREADS=1 (o manto_local tem credenciais reais).")
if "localhost" not in os.environ["DATABASE_URL"] and "127.0.0.1" not in os.environ["DATABASE_URL"]:
    sys.exit("ERRO: este verify só roda contra banco local.")

parser = argparse.ArgumentParser()
parser.add_argument("--ate", default="B11")
parser.add_argument("--rodadas", type=int, default=20)
ARGS = parser.parse_args()
ATE = int(ARGS.ate.lstrip("Bb"))

# ── Disjuntor de rede: nada sai da máquina ──────────────────────────────────────────────────
_ESCAPES: list[str] = []
_create_connection_original = socket.create_connection


def _so_local(address, *args, **kwargs):
    host = str(address[0])
    if host not in ("localhost", "127.0.0.1", "::1"):
        _ESCAPES.append(host)
        raise OSError(f"[verify_310] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.integracoes import infinitepay_client as ipc  # noqa: E402
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import (  # noqa: E402
    CatalogCharacter,
    SiteSetting,
    User,
    VirtualCampaign,
    VirtualCampaignSlot,
    VirtualOrder,
)

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
PASSWORD = "verify-310-senha"
RUN = secrets.token_hex(3)

app = create_app()
app.config["VIRTUAIS_AVISO_SINCRONO"] = True  # costura do verify: aviso processado na requisição
# O Google é dublê (abaixo): a trava de escrita de evento pode ser aberta neste processo.
app.config["CALENDAR_SUPPRESS_EVENT_WRITES"] = False
_engine = create_engine(os.environ["DATABASE_URL"])


def _db(sql: str, **p):
    with _engine.connect() as conn:
        return conn.execute(text(sql), p).fetchall()


# ── Resultado ───────────────────────────────────────────────────────────────────────────────
resultados: list[tuple[str, str, str]] = []


class Bloqueado(Exception):
    pass


def check(nome: str, ok: bool, detalhe: str = "") -> None:
    estado = "OK" if ok else "FALHA"
    resultados.append((nome, estado, detalhe))
    print(f"{estado:9} {nome}" + (f"  [{detalhe}]" if detalhe and not ok else ""), flush=True)


def cenario(nome: str):
    def deco(fn):
        def run():
            try:
                fn()
            except Bloqueado as exc:
                resultados.append((nome, "BLOQUEADO", str(exc)))
                print(f"BLOQUEADO {nome}  [{exc}]", flush=True)
            except Exception as exc:  # noqa: BLE001
                with app.app_context():
                    db.session.rollback()
                resultados.append((nome, "FALHA", f"{type(exc).__name__}: {exc}"[:300]))
                print(f"FALHA     {nome}  [{type(exc).__name__}: {str(exc)[:240]}]", flush=True)
        run.__name__ = fn.__name__
        return run
    return deco


def _ops(nome: str):
    fn = getattr(ops, nome, None)
    if fn is None:
        raise Bloqueado(f"virtuais_ops.{nome} ainda não existe")
    return fn


# ── Dublê da InfinitePay ────────────────────────────────────────────────────────────────────
class Operadora:
    """Cobranças conhecidas por order_nsu; a reconsulta imita o contrato real."""

    def __init__(self) -> None:
        self.cobrancas: dict[str, dict] = {}  # order_nsu -> {tx, slug, paid, paid_amount, amount}
        self.extras: dict[tuple[str, str], dict] = {}  # (order_nsu, tx) -> segunda cobrança
        self.forcar: dict[str, object] = {}  # order_nsu -> resultado forçado (str|Exception|callable)
        self.links: list[dict] = []
        self.consultas: list[dict] = []
        self.recusar_link: Exception | None = None

    def pagar(self, order_nsu: str, valor: Decimal, *, tx: str | None = None,
              paid_amount: Decimal | None = None) -> dict:
        c = {"tx": tx or f"tx-{RUN}-{secrets.token_hex(4)}", "slug": f"sl-{secrets.token_hex(4)}",
             "paid": True, "amount": valor, "paid_amount": valor if paid_amount is None else paid_amount}
        self.cobrancas[order_nsu] = c
        return c

    def aviso(self, order_nsu: str, c: dict) -> dict:
        return {"order_nsu": order_nsu, "transaction_nsu": c["tx"], "invoice_slug": c["slug"],
                "amount": int(c["amount"] * 100), "paid_amount": int(c["paid_amount"] * 100),
                "installments": 1, "capture_method": "pix", "receipt_url": "https://recibo/x",
                "items": []}

    def criar_link_pagamento(self, **kw):
        if self.recusar_link is not None:
            raise self.recusar_link
        self.links.append(kw)
        return {"payment_url": f"https://checkout.dublê/{kw['order_nsu']}"}

    def consultar_pagamento(self, *, handle, order_nsu, transaction_nsu=None, slug=None, **kw):
        self.consultas.append({"order_nsu": order_nsu, "tx": transaction_nsu, "slug": slug})
        forcado = self.forcar.get(order_nsu)
        if callable(forcado):
            forcado = forcado(transaction_nsu, slug)
        if isinstance(forcado, Exception):
            raise forcado
        if forcado is not None:
            return forcado
        c = None
        base = self.cobrancas.get(order_nsu)
        if base and transaction_nsu == base["tx"] and slug == base["slug"]:
            c = base
        extra = self.extras.get((order_nsu, transaction_nsu or ""))
        if extra and slug == extra["slug"]:
            c = extra
        if c is None:
            return {"resultado": "nao_encontrado", "paid": False, "amount": None,
                    "paid_amount": None, "capture_method": None, "raw": {"success": False}}
        return {"resultado": "pago" if c["paid"] else "nao_pago", "paid": c["paid"],
                "amount": c["amount"], "paid_amount": c["paid_amount"], "capture_method": "pix",
                "raw": {"success": True, "paid": c["paid"]}}


OP = Operadora()
_ipc_criar_original = ipc.criar_link_pagamento
_ipc_consultar_original = ipc.consultar_pagamento
ipc.criar_link_pagamento = OP.criar_link_pagamento
ipc.consultar_pagamento = OP.consultar_pagamento

# ── Dublê do Google ─────────────────────────────────────────────────────────────────────────
from app.calendar import service as gcal  # noqa: E402

GOOGLE = {"insert": [], "delete": [], "fetch": [], "lento": 0.0, "fora": False}


def _g_insert(calendar_id, title, start_dt, end_dt, description="", location="",
              conference_request_id=None, **kw):
    if GOOGLE["lento"]:
        time.sleep(GOOGLE["lento"])
    if GOOGLE["fora"]:
        raise RuntimeError("Google fora (dublê)")
    GOOGLE["insert"].append({"title": title, "start": start_dt, "kw": kw,
                             "conf": conference_request_id})
    gid = f"g{RUN}{len(GOOGLE['insert'])}"
    return {"id": gid, "htmlLink": f"https://cal/{gid}",
            "hangoutLink": f"https://meet/{gid}" if conference_request_id else None}


def _g_delete(calendar_id, google_event_id):
    GOOGLE["delete"].append(google_event_id)


def _g_fetch(calendar_id, google_event_id):
    GOOGLE["fetch"].append(google_event_id)
    return {"id": google_event_id, "hangoutLink": f"https://meet/{google_event_id}"}


gcal.insert_event = _g_insert
gcal.delete_event = _g_delete
gcal.fetch_single_event = _g_fetch

# ── Fixtures ────────────────────────────────────────────────────────────────────────────────
client = app.test_client()
CRIADAS: list[int] = []
SETTINGS_ORIGINAIS: dict = {}
TOKEN = f"tok-{RUN}-{secrets.token_hex(8)}"
USUARIOS: dict[str, str] = {}

with app.app_context():
    s = SiteSetting.query.get(1)
    for campo in ("infinitepay_handle", "infinitepay_webhook_token", "virtuais_pagamento_ativo",
                  "infinitepay_webhook_token_anterior", "infinitepay_webhook_token_anterior_ate",
                  "email_notifications_enabled", "whatsapp_form_number", "release_date"):
        SETTINGS_ORIGINAIS[campo] = getattr(s, campo, None)
    s.infinitepay_handle = "verify-310"
    s.infinitepay_webhook_token = TOKEN
    if hasattr(s, "virtuais_pagamento_ativo"):
        s.virtuais_pagamento_ativo = True
    personagem = CatalogCharacter.query.filter_by(is_active=True).first()
    PERSONAGEM_ID = personagem.id
    for papel in (RoleName.SUPERADMIN, RoleName.COMERCIAL):
        u = (User.query.filter(User.has_access.is_(True)).filter(User.roles.any(name=papel))
             .filter(User.email.isnot(None)).first())
        if u is not None:
            u.set_password(PASSWORD)
            USUARIOS[papel] = u.email
    outro = (User.query.filter(User.has_access.is_(True))
             .filter(~User.roles.any(name=RoleName.SUPERADMIN))
             .filter(~User.roles.any(name=RoleName.COMERCIAL))
             .filter(User.email.isnot(None)).first())
    if outro is not None:
        outro.set_password(PASSWORD)
        USUARIOS["outro"] = outro.email
    db.session.commit()

limiter.enabled = False
_SEQ = [0]
_BASE_DIA = datetime(2031, 3, 3, 9, 0)


def nova_campanha(**extra) -> tuple[int, str]:
    with app.app_context():
        c = ops.criar_campanha(
            catalog_character_id=PERSONAGEM_ID, title=f"Verify310 {RUN} {len(CRIADAS)}",
            price_live=Decimal("100.00"), price_recorded=Decimal("60.00"),
            recorded_capacity=extra.pop("capacidade", 0), tolerance_terms="termos",
            cover_url="/catalogo/midia/campanhas/x.jpg",
        )
        c.max_reservations_per_origin = 10_000
        for k, v in extra.items():
            setattr(c, k, v)
        c.status = "publicada"
        db.session.commit()
        CRIADAS.append(c.id)
        return c.id, c.slug


def novo_horario(camp_id: int, *, inicio: datetime | None = None) -> int:
    _SEQ[0] += 1
    with app.app_context():
        h = VirtualCampaignSlot(campaign_id=camp_id,
                                start_at=inicio or (_BASE_DIA + timedelta(minutes=10 * _SEQ[0])),
                                status="livre")
        db.session.add(h)
        db.session.commit()
        return h.id


def reservar(slug: str, slot_id: int | None, *, ip: str = "203.0.113.1", modalidade="ao_vivo",
             token: str | None = None, nome="Teo") -> tuple[int, dict]:
    tel = f"119{secrets.randbelow(10**8):08d}"
    r = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={"modality": modalidade, "slot_id": slot_id, "child_name": nome, "child_age": 6,
              "contact_phone": tel, "contact_email": f"v310-{RUN}@example.com",
              "client_token": token},
        headers={"X-Manto-Client-Ip": ip, "X-Forwarded-For": ip, "User-Agent": "verify-310"},
    )
    return r.status_code, (r.get_json() or {})


def pedido(nsu: str) -> dict:
    linha = _db("select id, status, slot_id, event_id, transaction_nsu, invoice_slug, "
                "total_value, expired_unverified from virtual_orders where order_nsu=:n", n=nsu)
    if not linha:
        return {}
    k = ["id", "status", "slot_id", "event_id", "tx", "slug", "total", "unverified"]
    return dict(zip(k, linha[0]))


def vencer(nsu: str) -> None:
    passado = now_sp() - timedelta(minutes=1)
    with _engine.begin() as conn:
        conn.execute(text("update virtual_orders set locked_until=:p where order_nsu=:n"),
                     {"p": passado, "n": nsu})
        conn.execute(text("update virtual_campaign_slots set locked_until=:p where order_id="
                          "(select id from virtual_orders where order_nsu=:n)"),
                     {"p": passado, "n": nsu})


def gravar_ids(nsu: str, c: dict) -> None:
    """Simula identificadores já conhecidos (como se um aviso anterior os tivesse trazido)."""
    with _engine.begin() as conn:
        conn.execute(text("update virtual_orders set transaction_nsu=:t, invoice_slug=:s "
                          "where order_nsu=:n"), {"t": c["tx"], "s": c["slug"], "n": nsu})


def varrer() -> dict:
    with app.app_context():
        return ops.expirar_reservas()


def avisar(payload: dict, token: str | None = None):
    return client.post(f"/api/webhooks/infinitepay/{token or TOKEN}", json=payload)


def pagos_no_horario(slot_id: int) -> int:
    return _db("select count(*) from virtual_orders where slot_id=:s and status='pago'",
               s=slot_id)[0][0]


def devolucoes(nsu: str) -> list[str]:
    return [r[0] for r in _db(
        "select r.reason from virtual_refund_requests r join virtual_orders o on o.id=r.order_id "
        "where o.order_nsu=:n", n=nsu)]


def invariantes(camp_id: int) -> list[str]:
    erros = []
    for (sid, n) in _db("select slot_id, count(*) from virtual_orders where campaign_id=:c and "
                        "status='pago' and slot_id is not null group by slot_id", c=camp_id):
        if n > 1:
            erros.append(f"horário {sid} com {n} pedidos pagos")
    for (oid, st, ow) in _db(
            "select o.id, s.status, s.order_id from virtual_orders o join virtual_campaign_slots s "
            "on s.id=o.slot_id where o.campaign_id=:c and o.status='pago'", c=camp_id):
        if st != "vendido" or ow != oid:
            erros.append(f"pedido pago {oid} com horário {st}/{ow}")
    return erros


def login(papel: str) -> None:
    email = USUARIOS.get(papel)
    if not email:
        raise Bloqueado(f"sem usuário {papel} no espelho")
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    if r.status_code != 200:
        raise Bloqueado(f"login {papel} falhou: {r.status_code}")


# ════════════════════════════════════════════════════════════════════════════════════════════
# B1 — Um horário, uma família
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("1  trava vencida, B reserva, varredura acha A pago → A devolução, horário com B")
def c1():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.1")
    a = ra["order_nsu"]
    vencer(a)
    _, rb = reservar(slug, h, ip="198.51.100.2")
    b = rb.get("order_nsu")
    check("1.0 B conseguiu reservar o horário vencido de A", bool(b), str(rb)[:120])
    gravar_ids(a, OP.pagar(a, Decimal("100.00")))
    varrer()
    pa = pedido(a)
    check("1.1 A não vira venda (devolução aberta)", pa["status"] == "cancelado"
          and devolucoes(a), str(pa))
    dono = _db("select order_id, status from virtual_campaign_slots where id=:h", h=h)[0]
    check("1.2 horário continua de B", dono[0] == pedido(b)["id"], str(dono))
    cb = OP.pagar(b, Decimal("100.00"))
    avisar(OP.aviso(b, cb))
    check("1.3 no máximo 1 pago no horário", pagos_no_horario(h) <= 1, str(pagos_no_horario(h)))
    check("1.4 invariantes", not invariantes(cid), str(invariantes(cid)))


@cenario("2  A confirmado pela varredura enquanto B segura o horário; B expira")
def c2():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.3")
    a = ra["order_nsu"]
    vencer(a)
    _, rb = reservar(slug, h, ip="198.51.100.4")
    b = rb["order_nsu"]
    gravar_ids(a, OP.pagar(a, Decimal("100.00")))
    varrer()
    cb = OP.pagar(b, Decimal("100.00"))
    cb["paid"] = False
    gravar_ids(b, cb)
    vencer(b)
    varrer()
    check("2.1 nenhum pedido pago com horário livre ou de outro", not invariantes(cid),
          str(invariantes(cid)))


@cenario("3  aviso confirma A enquanto a varredura decide 'não pago' → A termina pago")
def c3():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.5")
    a = ra["order_nsu"]
    c = OP.pagar(a, Decimal("100.00"))
    vencer(a)
    consultou = threading.Event()
    aviso_feito = threading.Event()

    def resposta(tx, slug_):
        if tx is None:  # a varredura (sem identificadores) responde "não pago" e espera o aviso
            consultou.set()
            aviso_feito.wait(30)
            return {"resultado": "nao_pago", "paid": False, "amount": Decimal("100.00"),
                    "paid_amount": None, "capture_method": None, "raw": {}}
        return None if tx == c["tx"] else {"resultado": "nao_encontrado", "paid": False,
                                           "amount": None, "paid_amount": None,
                                           "capture_method": None, "raw": {}}

    def resposta_ids(tx, slug_):
        r = resposta(tx, slug_)
        if r is None:
            return {"resultado": "pago", "paid": True, "amount": Decimal("100.00"),
                    "paid_amount": Decimal("100.00"), "capture_method": "pix", "raw": {}}
        return r

    OP.forcar[a] = resposta_ids
    t = threading.Thread(target=varrer)
    t.start()
    consultou.wait(30)
    avisar(OP.aviso(a, c))
    aviso_feito.set()
    t.join(60)
    OP.forcar.pop(a, None)
    pa = pedido(a)
    check("3.1 A termina pago (venda não regride)", pa["status"] == "pago", str(pa))
    check("3.2 invariantes", not invariantes(cid), str(invariantes(cid)))


@cenario("4  dois pagamentos atrasados de expirados no mesmo horário → 1 venda + 1 devolução")
def c4():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.6")
    a = ra["order_nsu"]
    vencer(a)
    varrer()  # sem cobrança conhecida: nao_encontrado → expira
    _, rc = reservar(slug, h, ip="198.51.100.7")
    c_ = rc["order_nsu"]
    vencer(c_)
    varrer()
    ca, cc = OP.pagar(a, Decimal("100.00")), OP.pagar(c_, Decimal("100.00"))
    avisar(OP.aviso(a, ca))
    avisar(OP.aviso(c_, cc))
    check("4.1 1 pago no horário", pagos_no_horario(h) == 1, str(pagos_no_horario(h)))
    check("4.2 o outro em devolução", bool(devolucoes(c_) or devolucoes(a)),
          f"{devolucoes(a)} {devolucoes(c_)}")
    check("4.3 invariantes", not invariantes(cid), str(invariantes(cid)))


@cenario("5  pagamento de horário que começa em menos de 30 min → devolução")
def c5():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.8")
    a = ra["order_nsu"]
    with _engine.begin() as conn:
        conn.execute(text("update virtual_campaign_slots set start_at=:t where id=:h"),
                     {"t": now_sp() + timedelta(minutes=10), "h": h})
    c = OP.pagar(a, Decimal("100.00"))
    avisar(OP.aviso(a, c))
    check("5.1 vira devolução horario_passou", "horario_passou" in devolucoes(a),
          f"{pedido(a)} {devolucoes(a)}")


@cenario("6  vídeo com 1 vaga, duas famílias → nunca vende acima da capacidade")
def c6():
    cid, slug = nova_campanha(capacidade=1)
    s1, r1 = reservar(slug, None, ip="198.51.100.9", modalidade="gravado")
    s2, r2 = reservar(slug, None, ip="198.51.100.10", modalidade="gravado")
    for st, r in ((s1, r1), (s2, r2)):
        if st == 201:
            avisar(OP.aviso(r["order_nsu"], OP.pagar(r["order_nsu"], Decimal("60.00"))))
    vend, cap = _db("select recorded_sold, recorded_capacity from virtual_campaigns where id=:c",
                    c=cid)[0]
    check("6.1 vendidos <= capacidade", vend <= cap, f"{vend}/{cap} (reservas {s1},{s2})")


@cenario("7  aviso e varredura no MESMO pedido em paralelo → 1 venda, 1 evento, Google 1×")
def c7():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.11")
    a = ra["order_nsu"]
    c = OP.pagar(a, Decimal("100.00"))
    gravar_ids(a, c)
    vencer(a)
    antes = len(GOOGLE["insert"])
    barreira = threading.Barrier(2, timeout=30)

    def paralelo(tx, slug_):
        try:
            barreira.wait()
        except threading.BrokenBarrierError:
            pass
        return {"resultado": "pago", "paid": True, "amount": Decimal("100.00"),
                "paid_amount": Decimal("100.00"), "capture_method": "pix", "raw": {}}

    OP.forcar[a] = paralelo

    def pelo_aviso():
        c2 = app.test_client()
        c2.post(f"/api/webhooks/infinitepay/{TOKEN}", json=OP.aviso(a, c))

    t1, t2 = threading.Thread(target=pelo_aviso), threading.Thread(target=varrer)
    t1.start(), t2.start()
    t1.join(60), t2.join(60)
    OP.forcar.pop(a, None)
    eventos = _db("select count(*) from calendar_events where description like :d or title like :t",
                  d=f"%{a}%", t="%VIRTUAL%")
    check("7.1 um pago", pagos_no_horario(h) == 1, str(pagos_no_horario(h)))
    check("7.2 Google chamado no máximo 1×", len(GOOGLE["insert"]) - antes <= 1,
          str(len(GOOGLE["insert"]) - antes))
    check("7.3 invariantes", not invariantes(cid), str(invariantes(cid)) + str(eventos))


def r22():
    """R-22: os cenários de concorrência da H1 repetidos N vezes."""
    falhas = 0
    for _ in range(ARGS.rodadas):
        antes = sum(1 for r in resultados if r[1] != "OK")
        c3()
        c7()
        if sum(1 for r in resultados if r[1] != "OK") > antes:
            falhas += 1
    check(f"R-22 {ARGS.rodadas} rodadas de concorrência sem venda dupla", falhas == 0,
          f"{falhas} rodada(s) com falha")


# ════════════════════════════════════════════════════════════════════════════════════════════
# B2 — Todo pagamento termina em venda ou devolução
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("8  retorno com identificadores, sem aviso → reconsulta confirma (SC-003)")
def c8():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.12")
    a, tok = ra["order_nsu"], ra["public_token"]
    c = OP.pagar(a, Decimal("100.00"))
    t0 = time.time()
    r = client.post(f"/api/virtuais/pedidos/{tok}/retorno",
                    json={"order_nsu": a, "slug": c["slug"], "transaction_nsu": c["tx"],
                          "capture_method": "pix", "receipt_url": "https://recibo/8"})
    dt = time.time() - t0
    check("8.1 retorno responde 200", r.status_code == 200, str(r.status_code))
    check("8.2 pedido pago pelo retorno", pedido(a).get("status") == "pago", str(pedido(a)))
    check("8.3 em menos de 60 s", dt < 60, f"{dt:.1f}s")
    rec = _db("select receipt_url from virtual_orders where order_nsu=:n", n=a)
    check("8.4 recibo guardado", bool(rec and rec[0][0]), str(rec))


@cenario("9  retorno com order_nsu de outro pedido → 404, nada gravado (deve falhar)")
def c9():
    cid, slug = nova_campanha()
    h1, h2 = novo_horario(cid), novo_horario(cid)
    _, ra = reservar(slug, h1, ip="198.51.100.13")
    _, rb = reservar(slug, h2, ip="198.51.100.14")
    c = OP.pagar(rb["order_nsu"], Decimal("100.00"))
    r = client.post(f"/api/virtuais/pedidos/{ra['public_token']}/retorno",
                    json={"order_nsu": rb["order_nsu"], "slug": c["slug"],
                          "transaction_nsu": c["tx"]})
    check("9.1 404", r.status_code == 404, str(r.status_code))
    check("9.2 nada gravado em A", pedido(ra["order_nsu"]).get("tx") is None,
          str(pedido(ra["order_nsu"])))


@cenario("10 reconsulta 'não encontrado' sem identificadores → não vira 'não sei' nem 'não pago' cego")
def c10():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.15")
    a = ra["order_nsu"]
    vencer(a)
    varrer()
    pa = pedido(a)
    check("10.1 abandono expira na primeira consulta", pa["status"] == "expirado", str(pa))
    motivo = _db("select unverified_reason from virtual_orders where order_nsu=:n", n=a)
    check("10.2 abandono não entra em 'a conferir'", motivo and motivo[0][0] is None, str(motivo))
    _, rb = reservar(slug, novo_horario(cid), ip="198.51.100.16")
    b = rb["order_nsu"]
    OP.forcar[b] = ipc.InfinitePayIndisponivel("fora (dublê)")
    vencer(b)
    for _ in range(4):
        with _engine.begin() as conn:
            conn.execute(text("update virtual_orders set grace_until=:p where order_nsu=:n"),
                         {"p": now_sp() - timedelta(minutes=5), "n": b})
        varrer()
    OP.forcar.pop(b, None)
    motivo = _db("select unverified_reason, status from virtual_orders where order_nsu=:n", n=b)
    check("10.3 operadora fora esgotada → nao_sei (a conferir)", motivo and
          motivo[0][0] == "nao_sei", str(motivo))


@cenario("11 aviso retido de pedido expirado, operadora volta → reprocessado até decidir")
def c11():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.17")
    a = ra["order_nsu"]
    vencer(a)
    varrer()
    c = OP.pagar(a, Decimal("100.00"))
    OP.forcar[a] = ipc.InfinitePayIndisponivel("fora (dublê)")
    avisar(OP.aviso(a, c))
    OP.forcar.pop(a, None)
    reprocessar = _ops("reprocessar_avisos")
    with _engine.begin() as conn:
        conn.execute(text("update virtual_payment_notifications set last_attempt_at=:p "
                          "where order_nsu=:n"), {"p": now_sp() - timedelta(hours=1), "n": a})
    with app.app_context():
        reprocessar()
    check("11.1 decidido: pago", pedido(a).get("status") == "pago", str(pedido(a)))


@cenario("12 segundo pagamento de pedido pago → devolução do segundo; pedido segue pago")
def c12():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.18")
    a = ra["order_nsu"]
    c = OP.pagar(a, Decimal("100.00"))
    avisar(OP.aviso(a, c))
    c2 = {"tx": f"tx2-{RUN}-{secrets.token_hex(3)}", "slug": f"sl2-{secrets.token_hex(3)}",
          "paid": True, "amount": Decimal("100.00"), "paid_amount": Decimal("100.00")}
    OP.extras[(a, c2["tx"])] = c2
    avisar(OP.aviso(a, c2))
    check("12.1 pedido segue pago", pedido(a).get("status") == "pago", str(pedido(a)))
    check("12.2 devolução pagamento_em_dobro", "pagamento_em_dobro" in devolucoes(a),
          str(devolucoes(a)))


@cenario("13 valor menor / zerado, pelo aviso e pela varredura → não vira venda (deve falhar)")
def c13():
    cid, slug = nova_campanha()
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.19")
    a = ra["order_nsu"]
    avisar(OP.aviso(a, OP.pagar(a, Decimal("100.00"), paid_amount=Decimal("1.00"))))
    check("13.1 aviso com valor menor não vira venda", pedido(a)["status"] != "pago", str(pedido(a)))
    _, rb = reservar(slug, novo_horario(cid), ip="198.51.100.20")
    b = rb["order_nsu"]
    cb = OP.pagar(b, Decimal("100.00"), paid_amount=Decimal("0.00"))
    gravar_ids(b, cb)
    vencer(b)
    varrer()
    check("13.2 varredura com paid_amount 0 não vira venda", pedido(b)["status"] != "pago",
          str(pedido(b)))


@cenario("14 reentrega de aviso sem desfecho final → processada")
def c14():
    cid, slug = nova_campanha()
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.21")
    a = ra["order_nsu"]
    c = OP.pagar(a, Decimal("100.00"))
    OP.forcar[a] = ipc.InfinitePayIndisponivel("fora (dublê)")
    avisar(OP.aviso(a, c))
    OP.forcar.pop(a, None)
    avisar(OP.aviso(a, c))  # a mesma reentrega, agora com a operadora de volta
    check("14.1 reentrega decidiu: pago", pedido(a).get("status") == "pago", str(pedido(a)))


@cenario("15 aviso forjado com identificadores inventados não contamina (deve falhar)")
def c15():
    cid, slug = nova_campanha()
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.22")
    a = ra["order_nsu"]
    forjado = {"order_nsu": a, "transaction_nsu": f"forjado-{RUN}", "invoice_slug": "forjado",
               "amount": 10000, "paid_amount": 10000}
    avisar(forjado)
    c = OP.pagar(a, Decimal("100.00"))
    avisar(OP.aviso(a, c))
    check("15.1 o pagamento verdadeiro confirma", pedido(a).get("status") == "pago", str(pedido(a)))
    check("15.2 identificador gravado é o verdadeiro", pedido(a).get("tx") == c["tx"],
          str(pedido(a).get("tx")))


# ════════════════════════════════════════════════════════════════════════════════════════════
# B3 — Ligar e desligar com segurança
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("16 banco local: o cliente real nunca sai para a InfinitePay")
def c16():
    with app.app_context():
        travada = app.config.get("INFINITEPAY_SUPPRESS_CALLS")
    check("16.1 trava ligada no manto_local", travada is True, str(travada))
    antes = len(_ESCAPES)
    try:
        _ipc_criar_original(handle="x", order_nsu="y", total=Decimal("1.00"), description="d",
                            redirect_url="https://r", webhook_url="https://w",
                            travada=bool(travada))
        saiu = True
    except getattr(ipc, "InfinitePayTravada", ipc.InfinitePayIndisponivel):
        saiu = False
    except TypeError as exc:
        raise Bloqueado(f"cliente sem o parâmetro de trava: {exc}") from exc
    check("16.2 travado: nenhuma requisição", not saiu and len(_ESCAPES) == antes, str(_ESCAPES))


@cenario("17 interruptor desligado: sem link novo; aviso de pedido aberto segue")
def c17():
    cid, slug = nova_campanha()
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.23")
    a = ra["order_nsu"]
    with app.app_context():
        s = SiteSetting.query.get(1)
        if not hasattr(s, "virtuais_pagamento_ativo"):
            raise Bloqueado("sem coluna virtuais_pagamento_ativo")
        s.virtuais_pagamento_ativo = False
        db.session.commit()
    try:
        st, _ = reservar(slug, novo_horario(cid), ip="198.51.100.24")
        check("17.1 reserva recusada com 503", st == 503, str(st))
        avisar(OP.aviso(a, OP.pagar(a, Decimal("100.00"))))
        check("17.2 aviso do pedido aberto segue", pedido(a).get("status") == "pago", str(pedido(a)))
    finally:
        with app.app_context():
            SiteSetting.query.get(1).virtuais_pagamento_ativo = True
            db.session.commit()


@cenario("18 publicar sem pagamento ligado → recusado (deve falhar)")
def c18():
    cid, _ = nova_campanha()
    with app.app_context():
        s = SiteSetting.query.get(1)
        if not hasattr(s, "virtuais_pagamento_ativo"):
            raise Bloqueado("sem interruptor")
        s.virtuais_pagamento_ativo = False
        c = VirtualCampaign.query.get(cid)
        c.status = "rascunho"
        db.session.commit()
        try:
            ops.alterar_status(c, "publicada")
            recusou = False
        except ops.VirtuaisValidationError:
            db.session.rollback()
            recusou = True
        s = SiteSetting.query.get(1)
        s.virtuais_pagamento_ativo = True
        db.session.commit()
    check("18.1 publicação recusada", recusou)


@cenario("19 caixa de segredo novo: troca uma vez; o anterior vale 24 h")
def c19():
    login(RoleName.SUPERADMIN)
    client.patch("/api/admin/settings", json={"infinitepay_regenerate_token": "true"})
    t1 = _db("select infinitepay_webhook_token from site_settings where id=1")[0][0]
    ant = _db("select infinitepay_webhook_token_anterior from site_settings where id=1")
    check("19.1 o anterior guardado", ant and ant[0][0] == TOKEN, str(ant))
    r = avisar({"order_nsu": "inexistente", "transaction_nsu": f"t19-{RUN}"}, token=TOKEN)
    check("19.2 o segredo anterior ainda é aceito", r.status_code == 200, str(r.status_code))
    with app.app_context():
        s = SiteSetting.query.get(1)
        s.infinitepay_webhook_token = TOKEN
        db.session.commit()
    check("19.3 segredo trocado de fato", t1 != TOKEN)


@cenario("20 tag inválida recusada; troca registrada antigo→novo (deve falhar)")
def c20():
    login(RoleName.SUPERADMIN)
    r = client.patch("/api/admin/settings",
                     json={"infinitepay_handle": "https://app.infinitepay.io/x y"})
    check("20.1 tag inválida → 400", r.status_code == 400, str(r.status_code))
    client.patch("/api/admin/settings", json={"infinitepay_handle": "verify-310-b"})
    log = _db("select detail from audit_logs where detail like :d order by id desc limit 1",
              d="%verify-310-b%")
    check("20.2 auditoria com antigo e novo", bool(log) and "verify-310" in log[0][0], str(log))
    with app.app_context():
        SiteSetting.query.get(1).infinitepay_handle = "verify-310"
        db.session.commit()


@cenario("21 salvar só o logo não muda e-mails, WhatsApp nem data de corte")
def c21():
    login(RoleName.SUPERADMIN)
    # Valores preenchidos ANTES: com os campos já vazios, o defeito (zerar de carona) não aparece.
    with _engine.begin() as conn:
        conn.execute(text("update site_settings set email_notifications_enabled=true, "
                          "whatsapp_form_number='5511900000310', release_date='2026-06-01' "
                          "where id=1"))
    antes = _db("select email_notifications_enabled, whatsapp_form_number, release_date "
                "from site_settings where id=1")[0]
    import io
    client.patch("/api/admin/settings", data={"logo": (io.BytesIO(b"\x89PNG\r\n"), "logo.png")},
                 content_type="multipart/form-data")
    depois = _db("select email_notifications_enabled, whatsapp_form_number, release_date "
                 "from site_settings where id=1")[0]
    check("21.1 nada mudou de carona", tuple(antes) == tuple(depois), f"{antes} → {depois}")


@cenario("22 operadora recusa o link → mensagem honesta, código gravado, sem repetir")
def c22():
    cid, slug = nova_campanha()
    OP.recusar_link = ipc.InfinitePayRecusou("External checkout is not enabled",
                                             **({"code": "external_checkout_not_enabled",
                                                 "status": 404}
                                                if "code" in ipc.InfinitePayRecusou.__init__.__code__
                                                .co_varnames else {}))
    n0 = len(OP.links)
    try:
        st, body = reservar(slug, novo_horario(cid), ip="198.51.100.25")
    finally:
        OP.recusar_link = None
    check("22.1 502", st == 502, str(st))
    erro = _db("select payment_link_error from virtual_orders where campaign_id=:c "
               "order by id desc limit 1", c=cid)
    check("22.2 código gravado", bool(erro) and "external_checkout_not_enabled" in (erro[0][0] or ""),
          str(erro))
    check("22.3 sem repetir a chamada recusada", len(OP.links) == n0)


@cenario("23 aviso lento (Google parado) → resposta rápida; processamento conclui depois")
def c23():
    cid, slug = nova_campanha()
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.26")
    a = ra["order_nsu"]
    c = OP.pagar(a, Decimal("100.00"))
    app.config["VIRTUAIS_AVISO_SINCRONO"] = False
    GOOGLE["lento"] = 3.0
    try:
        t0 = time.time()
        r = avisar(OP.aviso(a, c))
        dt = time.time() - t0
        check("23.1 resposta em menos de 1 s", r.status_code == 200 and dt < 1.0, f"{dt:.2f}s")
        fim = time.time() + 30
        while time.time() < fim and pedido(a).get("status") != "pago":
            time.sleep(0.5)
        check("23.2 processamento concluiu", pedido(a).get("status") == "pago", str(pedido(a)))
    finally:
        app.config["VIRTUAIS_AVISO_SINCRONO"] = True
        GOOGLE["lento"] = 0.0


@cenario("24 COMERCIAL no PATCH de configurações → 403 (deve falhar)")
def c24():
    login(RoleName.COMERCIAL)
    r = client.patch("/api/admin/settings", json={"virtuais_pagamento_ativo": False})
    check("24.1 403", r.status_code == 403, str(r.status_code))


# ════════════════════════════════════════════════════════════════════════════════════════════
# B4 — Limites por família
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("25 duas famílias, IPs distintos: uma estoura o limite, a outra segue")
def c25():
    limiter.enabled = True
    limiter.reset()
    try:
        cid, slug = nova_campanha()
        _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.27")
        tok = ra["public_token"]
        # O retorno (20/min por IP) e não a confirmação por telefone: esta tem um bloqueio POR
        # PEDIDO depois de erros, que dá 429 para qualquer IP e mascararia o teste.
        cod = [client.post(f"/api/virtuais/pedidos/{tok}/retorno", json={"order_nsu": "x"},
                           headers={"X-Manto-Client-Ip": "192.0.2.1"}).status_code
               for _ in range(22)]
        outra = client.post(f"/api/virtuais/pedidos/{tok}/retorno", json={"order_nsu": "x"},
                            headers={"X-Manto-Client-Ip": "192.0.2.2"}).status_code
        check("25.1 a primeira estourou", 429 in cod, str(cod))
        check("25.2 a outra não", outra != 429, str(outra))
    finally:
        limiter.enabled = False


@cenario("26 IP forjado à esquerda do XFF não vale (deve falhar)")
def c26():
    from app import api_utils
    fn = getattr(api_utils, "ip_do_cliente", None)
    if fn is None:
        raise Bloqueado("api_utils.ip_do_cliente ainda não existe")
    with app.test_request_context(headers={"X-Forwarded-For": "6.6.6.6, 10.0.0.9",
                                           "X-Manto-Client-Ip": "203.0.113.50"}):
        check("26.1 usa o cabeçalho do Node", fn() == "203.0.113.50", fn())


# ════════════════════════════════════════════════════════════════════════════════════════════
# B5 — Privacidade e segredo
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("27 pacote enviado à operadora sem nome da criança")
def c27():
    cid, slug = nova_campanha()
    reservar(slug, novo_horario(cid), ip="198.51.100.28", nome="Maria Secreta")
    kw = OP.links[-1]
    texto = repr(kw)
    check("27.1 nome da criança fora do pacote", "Maria Secreta" not in texto, texto[:200])
    check("27.2 customer sem name", "name" not in (kw.get("customer") or {}), str(kw.get("customer")))
    import requests as _rq
    capturado = {}

    def _post_falso(url, json=None, timeout=None, headers=None):
        capturado.update(json or {})

        class R:
            status_code = 200

            def json(self):
                return {"url": "https://x"}
        return R()

    orig = _rq.post
    _rq.post = _post_falso
    try:
        try:
            _ipc_criar_original(handle="h", order_nsu="n", total=Decimal("1.00"),
                                description="Campanha — pedido n", redirect_url="https://r",
                                webhook_url="https://w", customer={"email": "a@b.c",
                                                                   "phone_number": "11999999999"},
                                travada=False)
        except TypeError as exc:
            raise Bloqueado(str(exc)) from exc
    finally:
        _rq.post = orig
    check("27.3 cliente real monta itens em centavos", capturado.get("items", [{}])[0]
          .get("price") == 100, str(capturado)[:200])


@cenario("28 token do aviso mascarado nos logs")
def c28():
    from app import api_utils
    fn = getattr(api_utils, "mascarar_url_webhook", None)
    if fn is None:
        raise Bloqueado("api_utils.mascarar_url_webhook ainda não existe")
    linha = f"POST /api/webhooks/infinitepay/{TOKEN} 200"
    check("28.1 Python mascara", TOKEN not in fn(linha), fn(linha))
    js = (RAIZ / "frontend" / "server.js").read_text(encoding="utf-8")
    check("28.2 proxy Node mascara", "mascararUrl(req.url)" in js and "infinitepay" in js
          and "$1***" in js)


@cenario("29 aviso sem token não ocupa o NSU de um aviso real; 404 (deve falhar)")
def c29():
    cid, slug = nova_campanha()
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.29")
    a = ra["order_nsu"]
    c = OP.pagar(a, Decimal("100.00"))
    r = avisar(OP.aviso(a, c), token="errado")
    check("29.1 404", r.status_code == 404, str(r.status_code))
    avisar(OP.aviso(a, c))
    check("29.2 o aviso real ainda confirma", pedido(a).get("status") == "pago", str(pedido(a)))


# ════════════════════════════════════════════════════════════════════════════════════════════
# B6 — A equipe vê o que precisa de ação
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("30 lista 'a conferir' traz o divergente; resolver audita")
def c30():
    cid, slug = nova_campanha()
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.30")
    a = ra["order_nsu"]
    avisar(OP.aviso(a, OP.pagar(a, Decimal("100.00"), paid_amount=Decimal("50.00"))))
    login(RoleName.COMERCIAL)
    r = client.get("/api/virtuais/pagamentos-a-conferir")
    itens = (r.get_json() or {}).get("itens", []) if r.status_code == 200 else []
    meu = [i for i in itens if i.get("order_nsu") == a]
    check("30.1 aparece com o NSU", r.status_code == 200 and bool(meu), f"{r.status_code} {len(itens)}")
    if meu:
        r2 = client.patch(f"/api/virtuais/pagamentos-a-conferir/{meu[0]['tipo']}/{meu[0]['id']}",
                          json={"resolvido": True, "nota": "verify"})
        check("30.2 resolver 200", r2.status_code == 200, str(r2.status_code))


@cenario("31 papel sem acesso lê a lista → 403 (deve falhar)")
def c31():
    login("outro")
    r = client.get("/api/virtuais/pagamentos-a-conferir")
    check("31.1 403", r.status_code == 403, str(r.status_code))


@cenario("32 devolução nova → notificação no sino")
def c32():
    n0 = _db("select count(*) from notifications where kind like 'virtual.%'")[0][0] \
        if _db("select 1 from information_schema.tables where table_name='notifications'") else None
    if n0 is None:
        raise Bloqueado("tabela de notificações não encontrada")
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.31")
    a = ra["order_nsu"]
    vencer(a)
    _, rb = reservar(slug, h, ip="198.51.100.32")
    avisar(OP.aviso(a, OP.pagar(a, Decimal("100.00"))))
    n1 = _db("select count(*) from notifications where kind like 'virtual.%'")[0][0]
    check("32.1 sino ganhou aviso", n1 > n0, f"{n0}→{n1}")


@cenario("36 cancelar pedido pago → horário volta, evento sai, devolução pendente")
def c36():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    _, ra = reservar(slug, h, ip="198.51.100.33")
    a = ra["order_nsu"]
    avisar(OP.aviso(a, OP.pagar(a, Decimal("100.00"))))
    pa = pedido(a)
    login(RoleName.COMERCIAL)
    r = client.post(f"/api/virtuais/pedidos/{pa['id']}/cancelar", json={"motivo": "doente"})
    check("36.1 200", r.status_code == 200, str(r.status_code))
    check("36.2 desistência pendente", "desistencia" in devolucoes(a), str(devolucoes(a)))
    st = _db("select status from virtual_campaign_slots where id=:h", h=h)[0][0]
    check("36.3 horário de volta", st == "livre", st)
    ev = _db("select count(*) from calendar_events where id=:e", e=pa["event_id"] or -1)[0][0]
    check("36.4 evento apagado", ev == 0, str(ev))


# ════════════════════════════════════════════════════════════════════════════════════════════
# B7 — Família
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("33 seconds_left calculado no servidor")
def c33():
    cid, slug = nova_campanha()
    st, ra = reservar(slug, novo_horario(cid), ip="198.51.100.34")
    s = ra.get("seconds_left")
    check("33.1 reserva traz seconds_left ~900", isinstance(s, int) and 850 <= s <= 900, str(s))
    r = client.get(f"/api/virtuais/pedidos/{ra['public_token']}").get_json() or {}
    check("33.2 pedido traz seconds_left", isinstance(r.get("seconds_left"), int), str(r)[:120])


@cenario("34 mesma aba, outro horário → pedido novo")
def c34():
    cid, slug = nova_campanha()
    tok = f"aba-{RUN}-{secrets.token_hex(3)}"
    _, r1 = reservar(slug, novo_horario(cid), ip="198.51.100.35", token=tok)
    _, r2 = reservar(slug, novo_horario(cid), ip="198.51.100.35", token=tok)
    check("34.1 pedidos diferentes", r1.get("order_nsu") != r2.get("order_nsu"),
          f"{r1.get('order_nsu')} {r2.get('order_nsu')}")


@cenario("35 pedido em confirmação expõe 'confirming'")
def c35():
    cid, slug = nova_campanha()
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.36")
    r = client.get(f"/api/virtuais/pedidos/{ra['public_token']}").get_json() or {}
    check("35.1 campo confirming presente", "confirming" in r, str(list(r))[:160])


# ════════════════════════════════════════════════════════════════════════════════════════════
# B8 — Sala e agenda
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("37 Google fora na venda e volta horas depois → sala criada antes do horário")
def c37():
    cid, slug = nova_campanha()
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.37")
    a = ra["order_nsu"]
    GOOGLE["fora"] = True
    try:
        avisar(OP.aviso(a, OP.pagar(a, Decimal("100.00"))))
        with app.app_context():
            for _ in range(4):
                with _engine.begin() as conn:
                    conn.execute(text("update virtual_orders set meet_last_attempt_at=:p "
                                      "where order_nsu=:n"),
                                 {"p": now_sp() - timedelta(minutes=5), "n": a})
                ops.retentar_salas()
    finally:
        GOOGLE["fora"] = False
    with _engine.begin() as conn:
        conn.execute(text("update virtual_orders set meet_last_attempt_at=:p where order_nsu=:n"),
                     {"p": now_sp() - timedelta(hours=1), "n": a})
    with app.app_context():
        ops.retentar_salas()
    sala = _db("select meet_url, meet_pending from virtual_orders where order_nsu=:n", n=a)[0]
    check("37.1 sala criada depois das 3 tentativas", bool(sala[0]) and not sala[1], str(sala))


@cenario("38 evento da loja no Google não é importado pela sincronização")
def c38():
    from app.calendar import routes as croutes
    fn = getattr(croutes, "_eh_evento_da_loja", None)
    if fn is None:
        raise Bloqueado("calendar.routes._eh_evento_da_loja ainda não existe")
    item = {"id": "x", "summary": "🎥 VIRTUAL — Papai Noel para Teo",
            "extendedProperties": {"private": {"manto_virtual_nsu": "205-1-abc"}}}
    check("38.1 marca reconhecida", fn(item) is True)
    check("38.2 evento comum não", fn({"id": "y", "summary": "SHOW"}) is False)


# ════════════════════════════════════════════════════════════════════════════════════════════
# B9 — API Key
# ════════════════════════════════════════════════════════════════════════════════════════════
def _payload_real(**kw) -> dict:
    import requests as _rq
    capturado: dict = {}

    def _post_falso(url, json=None, timeout=None, headers=None):
        capturado["json"], capturado["headers"] = json, headers

        class R:
            status_code = 200

            def json(self):
                return {"url": "https://x"}
        return R()

    orig = _rq.post
    _rq.post = _post_falso
    try:
        _ipc_criar_original(handle="h", order_nsu="n", total=Decimal("1.00"), description="d",
                            redirect_url="https://r", webhook_url="https://w", travada=False, **kw)
    except TypeError as exc:
        raise Bloqueado(str(exc)) from exc
    finally:
        _rq.post = orig
    return capturado


@cenario("39 com API Key: X-Api-Key + valid_until + single_payment")
def c39():
    cap = _payload_real(api_key="chave-falsa", valid_until="2031-03-03T09:15:00-03:00")
    opts = (cap.get("json") or {}).get("options", {})
    check("39.1 header", (cap.get("headers") or {}).get("X-Api-Key") == "chave-falsa")
    check("39.2 options", opts.get("single_payment") is True and opts.get("valid_until"), str(opts))


@cenario("40 sem API Key: pacote legado intacto")
def c40():
    cap = _payload_real()
    check("40.1 sem options nem header", "options" not in cap["json"] and not cap["headers"],
          str(cap)[:200])


# ════════════════════════════════════════════════════════════════════════════════════════════
# B10 — Teste e operação
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("41 campanha fora da vitrine: some da lista, abre pelo link")
def c41():
    cid, slug = nova_campanha()
    with app.app_context():
        c = VirtualCampaign.query.get(cid)
        if not hasattr(c, "listada"):
            raise Bloqueado("sem coluna listada")
        c.listada = False
        db.session.commit()
    vit = client.get("/api/virtuais/vitrine").get_json() or {}
    check("41.1 fora da vitrine", slug not in [x["slug"] for x in vit.get("campanhas", [])])
    check("41.2 abre pelo link", client.get(f"/api/virtuais/campanhas/{slug}").status_code == 200)


@cenario("42 limpeza de venda de teste")
def c42():
    script = AQUI / "limpar_venda_teste.py"
    if not script.exists():
        raise Bloqueado("limpar_venda_teste.py ainda não existe")
    cid, slug = nova_campanha(listada=False)  # campanha de teste: fora da vitrine
    _, ra = reservar(slug, novo_horario(cid), ip="198.51.100.38")
    a = ra["order_nsu"]
    avisar(OP.aviso(a, OP.pagar(a, Decimal("100.00"))))
    pa = pedido(a)
    saida = subprocess.run([sys.executable, str(script), "--pedido", str(pa["id"]), "--execute"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "PYTHONPATH": str(RAIZ)}, cwd=str(RAIZ))
    depois = pedido(a)
    ev = _db("select count(*) from calendar_events where id=:e", e=pa["event_id"] or -1)[0][0]
    check("42.1 pedido cancelado e evento fora", depois["status"] == "cancelado" and ev == 0,
          f"{depois} ev={ev} {saida.stdout[-200:]}{saida.stderr[-200:]}")


# ════════════════════════════════════════════════════════════════════════════════════════════
BLOCOS = {
    1: [c1, c2, c3, c4, c5, c6, c7],
    2: [c8, c9, c10, c11, c12, c13, c14, c15],
    3: [c16, c17, c18, c19, c20, c21, c22, c23, c24],
    4: [c25, c26],
    5: [c27, c28, c29],
    6: [c30, c31, c32, c36],
    7: [c33, c34, c35],
    8: [c37, c38],
    9: [c39, c40],
    10: [c41, c42],
}


def limpar() -> None:
    with app.app_context():
        db.session.rollback()
    with _engine.begin() as conn:
        for cid in CRIADAS:
            ordens = [r[0] for r in conn.execute(text(
                "select id from virtual_orders where campaign_id=:c"), {"c": cid})]
            eventos = [r[0] for r in conn.execute(text(
                "select event_id from virtual_orders where campaign_id=:c and event_id is not null"),
                {"c": cid})]
            if ordens:
                conn.execute(text("update virtual_campaign_slots set order_id=null where campaign_id=:c"),
                             {"c": cid})
                for tabela in ("virtual_payment_notifications", "virtual_refund_requests",
                               "virtual_order_notifications", "virtual_media_deliveries"):
                    conn.execute(text(f"delete from {tabela} where order_id = any(:o)"),
                                 {"o": ordens})
                conn.execute(text("delete from virtual_orders where campaign_id=:c"), {"c": cid})
            for ev in eventos:
                conn.execute(text("delete from event_3d_gifts where event_id=:e"), {"e": ev}) \
                    if conn.execute(text("select 1 from information_schema.tables where "
                                         "table_name='event_3d_gifts'")).first() else None
                conn.execute(text("delete from event_roles where event_id=:e"), {"e": ev})
                conn.execute(text("delete from calendar_events where id=:e"), {"e": ev})
            conn.execute(text("delete from virtual_campaign_slots where campaign_id=:c"), {"c": cid})
            conn.execute(text("delete from virtual_campaign_acervo where campaign_id=:c"), {"c": cid}) \
                if conn.execute(text("select 1 from information_schema.tables where "
                                     "table_name='virtual_campaign_acervo'")).first() else None
            conn.execute(text("delete from virtual_campaigns where id=:c"), {"c": cid})
        conn.execute(text("delete from virtual_payment_notifications where order_id is null and "
                          "(transaction_nsu like :t or order_nsu = 'inexistente' or raw_payload like :r)"),
                     {"t": f"%{RUN}%", "r": f"%{RUN}%"})
    with app.app_context():
        s = SiteSetting.query.get(1)
        for campo, valor in SETTINGS_ORIGINAIS.items():
            if hasattr(s, campo):
                setattr(s, campo, valor)
        db.session.commit()


try:
    for n in range(1, min(ATE, 10) + 1):
        print(f"\n── B{n} " + "─" * 60, flush=True)
        for fn in BLOCOS[n]:
            fn()
        if n == 1 and ARGS.rodadas > 0:
            r22()
finally:
    try:
        limpar()
        check("44.1 limpeza", True)
    except Exception as exc:  # noqa: BLE001
        check("44.1 limpeza", False, f"{type(exc).__name__}: {exc}"[:200])
    check("44.2 nenhuma conexão externa escapou", not _ESCAPES, str(_ESCAPES[:5]))

ok = sum(1 for r in resultados if r[1] == "OK")
falha = sum(1 for r in resultados if r[1] == "FALHA")
bloq = sum(1 for r in resultados if r[1] == "BLOQUEADO")
print(f"\n{ok} OK · {falha} FALHA · {bloq} BLOQUEADO (de {len(resultados)})")
sys.exit(1 if (falha or bloq) else 0)
