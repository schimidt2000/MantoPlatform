"""Verificação da feature 341 — Papai Noel para qualquer idade e vídeo com data de entrega.

Roda contra o `manto_340` (dump de 10/11 com a migration da 340; o `manto_local` está no CRM 334).
Escrito ANTES do núcleo (Princípio VIII): contra `ad0ff2c7` os cenários de texto FALHAM e os de
prazo ficam BLOQUEADOS (função ausente) ou FALHAM.

  1  erros da ficha sem idade        5  prazo com data passada (função)
  2  e-mails sem "criança"           6  prazo sem data (função)
  3  "Para:" no evento da venda      7  gestão grava, limpa, recusa inválida (deve falhar)
  4  prazo com data (fluxo)          8  API pública e e-mail do vídeo com a data
  9  limpeza

InfinitePay e Google são dublês; nenhum e-mail sai (`_send` capturado); nada de rede sai da máquina.

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\341-papai-noel-para-todos\\verify_341.py
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para o Postgres local, nunca SQLite.")
if os.environ.get("MANTO_SEM_THREADS") != "1":
    sys.exit("ERRO: rode com MANTO_SEM_THREADS=1 (o espelho tem credenciais reais).")
if "localhost" not in os.environ["DATABASE_URL"] and "127.0.0.1" not in os.environ["DATABASE_URL"]:
    sys.exit("ERRO: este verify só roda contra banco local.")

_ESCAPES: list[str] = []
_create_connection_original = socket.create_connection


def _so_local(address, *args, **kwargs):
    host = str(address[0])
    if host not in ("localhost", "127.0.0.1", "::1"):
        _ESCAPES.append(host)
        raise OSError(f"[verify_341] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, email_service, limiter  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.integracoes import infinitepay_client as ipc  # noqa: E402
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import (  # noqa: E402
    CatalogCharacter,
    SiteSetting,
    User,
    VirtualCampaign,
    VirtualCampaignSlot,
)

RUN = secrets.token_hex(3)
PASSWORD = "verify-341-senha"
app = create_app()
app.config["VIRTUAIS_AVISO_SINCRONO"] = True
app.config["CALENDAR_SUPPRESS_EVENT_WRITES"] = False
_engine = create_engine(os.environ["DATABASE_URL"].strip())


def _db(sql: str, **p):
    with _engine.connect() as conn:
        return conn.execute(text(sql), p).fetchall()


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


# ── Dublês ──────────────────────────────────────────────────────────────────────────────────
class Operadora:
    def __init__(self) -> None:
        self.cobrancas: dict[str, dict] = {}

    def pagar(self, nsu: str, valor: Decimal) -> dict:
        c = {"tx": f"tx341-{RUN}-{secrets.token_hex(4)}", "slug": f"sl-{secrets.token_hex(4)}",
             "valor": valor}
        self.cobrancas[nsu] = c
        return c

    def aviso(self, nsu: str, c: dict) -> dict:
        centavos = int(c["valor"] * 100)
        return {"order_nsu": nsu, "transaction_nsu": c["tx"], "invoice_slug": c["slug"],
                "amount": centavos, "paid_amount": centavos, "capture_method": "pix",
                "receipt_url": "https://recibo/x", "items": []}

    def criar_link_pagamento(self, **kw):
        return {"payment_url": f"https://checkout.dublê/{kw['order_nsu']}"}

    def consultar_pagamento(self, *, handle, order_nsu, transaction_nsu=None, slug=None, **kw):
        c = self.cobrancas.get(order_nsu)
        if c and transaction_nsu == c["tx"] and slug == c["slug"]:
            return {"resultado": "pago", "paid": True, "amount": c["valor"],
                    "paid_amount": c["valor"], "capture_method": "pix", "raw": {"success": True}}
        return {"resultado": "nao_encontrado", "paid": False, "amount": None,
                "paid_amount": None, "capture_method": None, "raw": {"success": False}}


OP = Operadora()
ipc.criar_link_pagamento = OP.criar_link_pagamento
ipc.consultar_pagamento = OP.consultar_pagamento

from app.calendar import service as gcal  # noqa: E402

GOOGLE: list[dict] = []


def _g_insert(calendar_id, title, start_dt, end_dt, description="", location="",
              conference_request_id=None, **kw):
    GOOGLE.append({"title": title, "description": description})
    gid = f"g341{RUN}{len(GOOGLE)}"
    return {"id": gid, "htmlLink": f"https://cal/{gid}", "hangoutLink": f"https://meet/{gid}"}


gcal.insert_event = _g_insert
gcal.delete_event = lambda calendar_id, gid: None
gcal.fetch_single_event = lambda calendar_id, gid: {"id": gid, "hangoutLink": f"https://meet/{gid}"}

EMAILS: list[dict] = []
_send_original = email_service._send


def _captura(**kwargs):
    EMAILS.append(kwargs)
    return True


email_service._send = _captura

# ── Fixtures ────────────────────────────────────────────────────────────────────────────────
client = app.test_client()
CRIADAS: list[int] = []
SETTINGS_ORIGINAIS: dict = {}
TOKEN = f"tok341-{RUN}-{secrets.token_hex(8)}"
SUPERADMIN: dict = {}

with app.app_context():
    s = SiteSetting.query.get(1)
    for campo in ("infinitepay_handle", "infinitepay_webhook_token", "virtuais_pagamento_ativo"):
        SETTINGS_ORIGINAIS[campo] = getattr(s, campo, None)
    s.infinitepay_handle = "verify-341"
    s.infinitepay_webhook_token = TOKEN
    s.virtuais_pagamento_ativo = True
    PERSONAGEM_ID = CatalogCharacter.query.filter_by(is_active=True).first().id
    u = (User.query.filter(User.has_access.is_(True)).filter(User.roles.any(name=RoleName.SUPERADMIN))
         .filter(User.email.isnot(None)).order_by(User.id).first())
    u.set_password(PASSWORD)
    SUPERADMIN["email"] = u.email
    db.session.commit()

limiter.enabled = False
_SEQ = [0]


def nova_campanha(**extra) -> tuple[int, str]:
    with app.app_context():
        c = ops.criar_campanha(
            catalog_character_id=PERSONAGEM_ID, title=f"Verify341 {RUN} {len(CRIADAS)}",
            price_live=Decimal("100.00"), price_recorded=Decimal("60.00"),
            recorded_capacity=5, tolerance_terms="termos",
            cover_url="/catalogo/midia/campanhas/x.jpg",
        )
        c.max_reservations_per_origin = 10_000
        c.status = "publicada"
        for k, v in extra.items():
            setattr(c, k, v)
        db.session.commit()
        CRIADAS.append(c.id)
        return c.id, c.slug


def novo_horario(camp_id: int) -> int:
    _SEQ[0] += 1
    with app.app_context():
        h = VirtualCampaignSlot(campaign_id=camp_id,
                                start_at=datetime(2031, 6, 2, 9, 0) + timedelta(minutes=10 * _SEQ[0]),
                                status="livre")
        db.session.add(h)
        db.session.commit()
        return h.id


def reservar(slug: str, slot_id: int | None, *, modalidade="ao_vivo", nome="Teo", idade=6):
    tel = f"119{secrets.randbelow(10**8):08d}"
    return client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={"modality": modalidade, "slot_id": slot_id, "child_name": nome, "child_age": idade,
              "contact_phone": tel, "contact_email": f"v341-{RUN}@example.com",
              "client_token": secrets.token_hex(8)},
        headers={"X-Manto-Client-Ip": "203.0.113.41", "User-Agent": "verify-341"},
    )


def pagar(nsu: str) -> None:
    total = Decimal(str(_db("select total_value from virtual_orders where order_nsu=:n",
                            n=nsu)[0][0]))
    c = OP.pagar(nsu, total)
    r = client.post(f"/api/webhooks/infinitepay/{TOKEN}", json=OP.aviso(nsu, c))
    assert r.status_code == 200, r.status_code


def prazo_da_entrega(nsu: str):
    linha = _db("select d.due_date from virtual_media_deliveries d join virtual_orders o "
                "on o.id = d.order_id where o.order_nsu=:n", n=nsu)
    return linha[0][0] if linha else None


# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("1  erros da ficha falam de quem vai receber, sem idade")
def c1():
    cid, slug = nova_campanha()
    h = novo_horario(cid)
    sem_nome = (reservar(slug, h, nome="").get_json() or {}).get("error", {}).get("fields", {})
    sem_idade = (reservar(slug, h, idade="").get_json() or {}).get("error", {}).get("fields", {})
    check("1.1 sem nome", sem_nome.get("child_name") == "Informe o nome de quem vai receber.",
          str(sem_nome))
    check("1.2 sem idade", sem_idade.get("child_age") == "Informe a idade.", str(sem_idade))
    adulto = reservar(slug, h, nome="Vó Cida", idade=82)
    check("1.3 adulto de 82 anos reserva", adulto.status_code in (200, 201), str(adulto.status_code))


@cenario("2  e-mails sem 'criança' fora da cartinha condicionada")
def c2():
    EMAILS.clear()
    with app.app_context():
        campanha = SimpleNamespace(title="Uma chamada com o Papai Noel", recorded_delivery_days=7,
                                   recorded_delivery_until=date(2026, 12, 13), slug="papai-noel")
        base = dict(campaign=campanha, child_name="Cida", contact_email="familia@example.com",
                    total_value=Decimal("120.00"), public_token="tok341")
        ao_vivo = SimpleNamespace(**base, modality="ao_vivo",
                                  slot=SimpleNamespace(start_at=datetime(2026, 12, 6, 14, 0)))
        gravado = SimpleNamespace(**base, modality="gravado", slot=None,
                                  media_delivery=SimpleNamespace(due_date=date(2026, 12, 13)))
        email_service.send_virtual_order_confirmed_email(ao_vivo)
        email_service.send_virtual_order_confirmed_email(gravado)
        email_service.send_virtual_video_ready_email(gravado)
    vivo, video_compra, video_pronto = (e["html"] for e in EMAILS[:3])
    check("2.1 ao vivo: cartinha só 'se for uma criança'",
          "cartinha" in vivo and vivo.count("criança") == vivo.count("se for uma criança")
          + vivo.count("Se for uma criança"), vivo[-600:])
    check("2.2 vídeo comprado: sem 'criança'", "criança" not in video_compra, "")
    check("2.3 vídeo pronto: sem 'criança'", "criança" not in video_pronto, "")
    check("8.2 e-mail de compra do vídeo com a data da entrega", "13/12/2026" in video_compra,
          video_compra[-500:])


@cenario("3  descrição do evento da venda diz 'Para:'")
def c3():
    cid, slug = nova_campanha()
    r = reservar(slug, novo_horario(cid), nome="Vó Cida", idade=82)
    GOOGLE.clear()
    pagar(r.get_json()["order_nsu"])
    descricoes = [g["description"] for g in GOOGLE]
    check("3.1 'Para: Vó Cida, 82 anos'", any("Para: Vó Cida, 82 anos" in d for d in descricoes),
          str(descricoes)[:200])
    check("3.2 sem 'Criança:'", not any("Criança:" in d for d in descricoes), "")


@cenario("4  com data de entrega, vídeo pago antes dela vence na data")
def c4():
    limite = (now_sp() + timedelta(days=40)).date()
    cid, slug = nova_campanha(recorded_delivery_until=limite) if hasattr(
        VirtualCampaign, "recorded_delivery_until") else (None, None)
    if cid is None:
        raise Bloqueado("VirtualCampaign.recorded_delivery_until ainda não existe")
    r = reservar(slug, None, modalidade="gravado")
    nsu = r.get_json()["order_nsu"]
    pagar(nsu)
    check("4.1 due_date = data da campanha", prazo_da_entrega(nsu) == limite,
          f"{prazo_da_entrega(nsu)} ≠ {limite}")


@cenario("5  data já passada → pagamento + dias")
def c5():
    fn = _ops("prazo_do_video")
    hoje = date(2026, 12, 20)
    campanha = SimpleNamespace(recorded_delivery_until=date(2026, 12, 13), recorded_delivery_days=7)
    check("5.1 20/12 + 7", fn(campanha, hoje) == date(2026, 12, 27), str(fn(campanha, hoje)))
    no_dia = fn(campanha, date(2026, 12, 13))
    check("5.2 pago no próprio dia → a data", no_dia == date(2026, 12, 13), str(no_dia))


@cenario("6  sem data → pagamento + dias, como antes")
def c6():
    fn = _ops("prazo_do_video")
    campanha = SimpleNamespace(recorded_delivery_until=None, recorded_delivery_days=7)
    check("6.1 15/11 + 7", fn(campanha, date(2026, 11, 15)) == date(2026, 11, 22), "")
    cid, slug = nova_campanha()
    nsu = reservar(slug, None, modalidade="gravado").get_json()["order_nsu"]
    pagar(nsu)
    esperado = now_sp().date() + timedelta(days=7)
    check("6.2 fluxo sem data: hoje + 7", prazo_da_entrega(nsu) == esperado,
          f"{prazo_da_entrega(nsu)} ≠ {esperado}")


@cenario("7  gestão grava, limpa e recusa data inválida (deve falhar)")
def c7():
    cid, _ = nova_campanha()
    client.post("/api/auth/logout")
    login = client.post("/api/auth/login",
                        json={"email": SUPERADMIN["email"], "password": PASSWORD})
    if login.status_code != 200:
        raise Bloqueado(f"login falhou: {login.status_code}")
    try:
        r = client.patch(f"/api/virtuais/campanhas/{cid}",
                         json={"recorded_delivery_until": "2026-12-13"})
        gravado = _db("select recorded_delivery_until from virtual_campaigns where id=:c", c=cid)
        check("7.1 grava (conexão separada)", r.status_code == 200
              and gravado[0][0] == date(2026, 12, 13)
              and (r.get_json() or {}).get("recorded_delivery_until") == "2026-12-13",
              f"{r.status_code} {gravado}")
        r = client.patch(f"/api/virtuais/campanhas/{cid}", json={"recorded_delivery_until": ""})
        limpo = _db("select recorded_delivery_until from virtual_campaigns where id=:c", c=cid)
        check("7.2 vazio limpa", r.status_code == 200 and limpo[0][0] is None, str(limpo))
        r = client.patch(f"/api/virtuais/campanhas/{cid}",
                         json={"recorded_delivery_until": "2026-02-31"})
        campos = ((r.get_json() or {}).get("error") or {}).get("fields") or {}
        check("7.3 inválida → 400 no campo", r.status_code == 400
              and "recorded_delivery_until" in campos, f"{r.status_code} {campos}")
    finally:
        client.post("/api/auth/logout")


@cenario("8  API pública traz a data")
def c8():
    _, slug = nova_campanha(recorded_delivery_until=date(2026, 12, 13)) if hasattr(
        VirtualCampaign, "recorded_delivery_until") else (None, None)
    if slug is None:
        raise Bloqueado("VirtualCampaign.recorded_delivery_until ainda não existe")
    dados = client.get(f"/api/virtuais/campanhas/{slug}").get_json() or {}
    check("8.1 recorded_delivery_until no JSON público",
          dados.get("recorded_delivery_until") == "2026-12-13", str(dados.get("recorded_delivery_until")))


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
                conn.execute(text("update virtual_campaign_slots set order_id=null "
                                  "where campaign_id=:c"), {"c": cid})
                for tabela in ("virtual_payment_notifications", "virtual_refund_requests",
                               "virtual_order_notifications", "virtual_media_deliveries"):
                    conn.execute(text(f"delete from {tabela} where order_id = any(:o)"),
                                 {"o": ordens})
                conn.execute(text("delete from virtual_orders where campaign_id=:c"), {"c": cid})
            for ev in eventos:
                if conn.execute(text("select 1 from information_schema.tables where "
                                     "table_name='event_3d_gifts'")).first():
                    conn.execute(text("delete from event_3d_gifts where event_id=:e"), {"e": ev})
                conn.execute(text("delete from event_roles where event_id=:e"), {"e": ev})
                conn.execute(text("delete from calendar_events where id=:e"), {"e": ev})
            conn.execute(text("delete from virtual_campaign_slots where campaign_id=:c"), {"c": cid})
            if conn.execute(text("select 1 from information_schema.tables where "
                                 "table_name='virtual_campaign_acervo'")).first():
                conn.execute(text("delete from virtual_campaign_acervo where campaign_id=:c"),
                             {"c": cid})
            conn.execute(text("delete from virtual_campaigns where id=:c"), {"c": cid})
    with app.app_context():
        s = SiteSetting.query.get(1)
        for campo, valor in SETTINGS_ORIGINAIS.items():
            setattr(s, campo, valor)
        db.session.commit()


try:
    for fn in (c1, c2, c3, c4, c5, c6, c7, c8):
        fn()
finally:
    email_service._send = _send_original
    try:
        limpar()
        check("9.1 limpeza", True)
    except Exception as exc:  # noqa: BLE001
        check("9.1 limpeza", False, f"{type(exc).__name__}: {exc}"[:200])
    check("9.2 nenhuma conexão externa escapou", not _ESCAPES, str(_ESCAPES[:5]))

ok = sum(1 for r in resultados if r[1] == "OK")
falha = sum(1 for r in resultados if r[1] == "FALHA")
bloq = sum(1 for r in resultados if r[1] == "BLOQUEADO")
print(f"\n{ok} OK · {falha} FALHA · {bloq} BLOQUEADO (de {len(resultados)})")
sys.exit(1 if (falha or bloq) else 0)
