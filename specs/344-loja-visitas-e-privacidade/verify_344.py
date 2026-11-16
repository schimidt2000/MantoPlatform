"""Verificação da feature 344 — a loja conta as visitas e pede licença.

Roda contra o `manto_344` (dump de produção de 16/11/2026 02:00; o `manto_local` está no CRM 334).
Escrito ANTES do núcleo (Princípio VIII): sem a migration e as rotas, os cenários FALHAM ou ficam
BLOQUEADOS (função ausente).

   1  visita com origem=instagram           10  venda de telefone que já é cliente
   2  WhatsApp / origem desconhecida        11  falha forçada na ficha não derruba a venda
   3  google / sem origem (direto)          12  dicas vencidas somem (pedido, evento, Google)
   4  campanha pausada não conta            13  dicas dentro do prazo / Google fora ficam
   5  funil: visita, reserva e venda        14  CRM: origem Loja no gráfico e aceite na ficha
   6  funil sem papel de loja (deve falhar) 15  rastreamento sem ID
   7  reserva sem aceite                    16  Superadmin grava o ID do pixel; não-dígito 400
   8  reserva com aceite e nome             17  papel sem acesso grava o ID (deve falhar)
   9  venda com aceite → ficha nova         18  limpeza; nenhuma conexão externa

InfinitePay e Google são dublês; nenhum e-mail sai (`_send` capturado); nada de rede sai da máquina.

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\344-loja-visitas-e-privacidade\\verify_344.py
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
from datetime import datetime, timedelta
from decimal import Decimal

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
        raise OSError(f"[verify_344] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import constants as consts  # noqa: E402
from app import create_app, db, email_service, limiter  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.integracoes import infinitepay_client as ipc  # noqa: E402
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import (  # noqa: E402
    CatalogCharacter,
    Client,
    SiteSetting,
    User,
    VirtualCampaignSlot,
)

RUN = secrets.token_hex(3)
PASSWORD = f"verify-344-{secrets.token_hex(6)}"
app = create_app()
app.config["VIRTUAIS_AVISO_SINCRONO"] = True
app.config["CALENDAR_SUPPRESS_EVENT_WRITES"] = False
_engine = create_engine(os.environ["DATABASE_URL"].strip())


def _db(sql: str, **p):
    # Conexão separada: o autoflush da sessão do app esconderia um commit que não aconteceu.
    with _engine.connect() as conn:
        return conn.execute(text(sql), p).fetchall()


def _exec(sql: str, **p) -> None:
    with _engine.begin() as conn:
        conn.execute(text(sql), p)


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
        c = {
            "tx": f"tx344-{RUN}-{secrets.token_hex(4)}",
            "slug": f"sl-{secrets.token_hex(4)}",
            "valor": valor,
        }
        self.cobrancas[nsu] = c
        return c

    def aviso(self, nsu: str, c: dict) -> dict:
        centavos = int(c["valor"] * 100)
        return {
            "order_nsu": nsu,
            "transaction_nsu": c["tx"],
            "invoice_slug": c["slug"],
            "amount": centavos,
            "paid_amount": centavos,
            "capture_method": "pix",
            "receipt_url": "https://recibo/x",
            "items": [],
        }

    def criar_link_pagamento(self, **kw):
        return {"payment_url": f"https://checkout.dublê/{kw['order_nsu']}"}

    def consultar_pagamento(self, *, handle, order_nsu, transaction_nsu=None, slug=None, **kw):
        c = self.cobrancas.get(order_nsu)
        if c and transaction_nsu == c["tx"] and slug == c["slug"]:
            return {
                "resultado": "pago",
                "paid": True,
                "amount": c["valor"],
                "paid_amount": c["valor"],
                "capture_method": "pix",
                "raw": {"success": True},
            }
        return {
            "resultado": "nao_encontrado",
            "paid": False,
            "amount": None,
            "paid_amount": None,
            "capture_method": None,
            "raw": {"success": False},
        }


OP = Operadora()
ipc.criar_link_pagamento = OP.criar_link_pagamento
ipc.consultar_pagamento = OP.consultar_pagamento

from app.calendar import service as gcal  # noqa: E402

GOOGLE: list[dict] = []
GOOGLE_UPDATES: list[dict] = []
GOOGLE_FORA = [False]


def _g_insert(
    calendar_id,
    title,
    start_dt,
    end_dt,
    description="",
    location="",
    conference_request_id=None,
    **kw,
):
    GOOGLE.append({"title": title, "description": description})
    gid = f"g344{RUN}{len(GOOGLE)}"
    return {"id": gid, "htmlLink": f"https://cal/{gid}", "hangoutLink": f"https://meet/{gid}"}


def _g_update(calendar_id, google_event_id, title, start_dt, end_dt, description="", location=""):
    if GOOGLE_FORA[0]:
        raise RuntimeError("Google fora (dublê)")
    GOOGLE_UPDATES.append({"id": google_event_id, "description": description})
    return {"id": google_event_id}


gcal.insert_event = _g_insert
gcal.update_event = _g_update
gcal.delete_event = lambda calendar_id, gid: None
gcal.fetch_single_event = lambda calendar_id, gid: {"id": gid, "hangoutLink": f"https://meet/{gid}"}

EMAILS: list[dict] = []
_send_original = email_service._send
email_service._send = lambda **kw: EMAILS.append(kw) or True

# ── Fixtures ────────────────────────────────────────────────────────────────────────────────
client = app.test_client()
CRIADAS: list[int] = []
TELEFONES: list[str] = []  # dígitos com DDI, como o CRM guarda
SETTINGS_ORIGINAIS: dict = {}
TOKEN = f"tok344-{RUN}-{secrets.token_hex(8)}"
USUARIOS: dict[str, str] = {}

with app.app_context():
    s = SiteSetting.query.get(1)
    for campo in (
        "infinitepay_handle",
        "infinitepay_webhook_token",
        "virtuais_pagamento_ativo",
        "meta_pixel_id",
    ):
        SETTINGS_ORIGINAIS[campo] = getattr(s, campo, None)
    s.infinitepay_handle = "verify-344"
    s.infinitepay_webhook_token = TOKEN
    s.virtuais_pagamento_ativo = True
    if hasattr(s, "meta_pixel_id"):
        s.meta_pixel_id = None
    PERSONAGEM_ID = CatalogCharacter.query.filter_by(is_active=True).first().id
    gestor = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .filter(User.email.isnot(None))
        .order_by(User.id)
        .first()
    )
    # Dívida 206: o "outro" não pode ser Revendedor EducaManto (o guard da 078 dá 403 em tudo).
    outro = (
        User.query.filter(User.has_access.is_(True))
        .filter(~User.roles.any(name=RoleName.SUPERADMIN))
        .filter(~User.roles.any(name=RoleName.COMERCIAL))
        .filter(~User.roles.any(name=RoleName.REVENDEDOR_EDUCAMANTO))
        .filter(User.email.isnot(None))
        .order_by(User.id)
        .first()
    )
    for papel, u in (("gestor", gestor), ("outro", outro)):
        if u is not None:
            u.set_password(PASSWORD)
            USUARIOS[papel] = u.email
    db.session.commit()

limiter.enabled = False
_SEQ = [0]


def login(papel: str) -> None:
    if papel not in USUARIOS:
        raise Bloqueado(f"sem usuário {papel} no espelho")
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": USUARIOS[papel], "password": PASSWORD})
    if r.status_code != 200:
        raise Bloqueado(f"login {papel}: {r.status_code}")


def logout() -> None:
    client.post("/api/auth/logout")


def nova_campanha(status: str = "publicada") -> tuple[int, str, str]:
    with app.app_context():
        c = ops.criar_campanha(
            catalog_character_id=PERSONAGEM_ID,
            title=f"Verify344 {RUN} {len(CRIADAS)}",
            price_live=Decimal("100.00"),
            price_recorded=Decimal("60.00"),
            recorded_capacity=5,
            tolerance_terms="termos",
            cover_url="/catalogo/midia/campanhas/x.jpg",
        )
        c.max_reservations_per_origin = 10_000
        c.status = status
        db.session.commit()
        CRIADAS.append(c.id)
        return c.id, c.slug, c.title


def novo_horario(camp_id: int) -> int:
    _SEQ[0] += 1
    with app.app_context():
        h = VirtualCampaignSlot(
            campaign_id=camp_id,
            start_at=datetime(2031, 6, 2, 9, 0) + timedelta(minutes=15 * _SEQ[0]),
            status="livre",
        )
        db.session.add(h)
        db.session.commit()
        return h.id


def telefone_novo() -> str:
    tel = f"119{secrets.randbelow(10**8):08d}"
    TELEFONES.append("55" + tel)
    return tel


def reservar(
    slug: str,
    slot_id: int | None,
    *,
    tel: str | None = None,
    modalidade="ao_vivo",
    extra: dict | None = None,
):
    corpo = {
        "modality": modalidade,
        "slot_id": slot_id,
        "child_name": f"Crianca{RUN}",
        "child_age": 6,
        "behavior_notes": f"gosta de dinossauro {RUN}",
        "contact_phone": tel or telefone_novo(),
        "contact_email": f"v344-{RUN}-{secrets.token_hex(2)}@example.com",
        "client_token": secrets.token_hex(8),
        **(extra or {}),
    }
    r = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json=corpo,
        headers={"X-Manto-Client-Ip": "203.0.113.44", "User-Agent": "verify-344"},
    )
    assert r.status_code == 201, f"reservar {r.status_code} {r.get_data(as_text=True)[:200]}"
    return r.get_json()["order_nsu"]


def pagar(nsu: str) -> None:
    total = Decimal(
        str(_db("select total_value from virtual_orders where order_nsu=:n", n=nsu)[0][0])
    )
    c = OP.pagar(nsu, total)
    r = client.post(f"/api/webhooks/infinitepay/{TOKEN}", json=OP.aviso(nsu, c))
    assert r.status_code == 200, r.status_code


def visita(slug: str, origem) -> int:
    corpo = {} if origem is None else {"origem": origem}
    return client.post(f"/api/virtuais/campanhas/{slug}/visita", json=corpo).status_code


def contagem(camp_id: int) -> dict[str, int]:
    linhas = _db(
        "select origem, visits from virtual_campaign_visits where campaign_id=:c and day=:d",
        c=camp_id,
        d=now_sp().date(),
    )
    return {o: n for o, n in linhas}


CAMP_A, SLUG_A, TITULO_A = nova_campanha()


# ── História 1: contagem ────────────────────────────────────────────────────────────────────
@cenario("1  visita com origem=instagram conta 1 no dia")
def c1():
    logout()
    st = visita(SLUG_A, "instagram")
    check("1.1 204", st == 204, str(st))
    check(
        "1.2 1 visita em instagram", contagem(CAMP_A).get("instagram") == 1, str(contagem(CAMP_A))
    )


@cenario("2  WhatsApp com maiúscula e origem desconhecida")
def c2():
    visita(SLUG_A, "WhatsApp")
    visita(SLUG_A, "panfleto")
    cont = contagem(CAMP_A)
    check("2.1 whatsapp", cont.get("whatsapp") == 1, str(cont))
    check("2.2 desconhecida vira outro", cont.get("outro") == 1, str(cont))
    validas = {"instagram", "facebook", "whatsapp", "google", "tiktok", "email", "outro", "direto"}
    check("2.3 nenhuma origem fora da lista", set(cont) <= validas, str(set(cont) - validas))


@cenario("3  google e sem origem (direto)")
def c3():
    visita(SLUG_A, "google")
    visita(SLUG_A, None)
    visita(SLUG_A, "")
    cont = contagem(CAMP_A)
    check("3.1 google", cont.get("google") == 1, str(cont))
    check("3.2 direto conta 2", cont.get("direto") == 2, str(cont))


@cenario("4  campanha pausada não conta")
def c4():
    cid, slug, _ = nova_campanha(status="pausada")
    st = visita(slug, "instagram")
    # Mesmo critério da landing (`_campanha_publicada_ou_erro`): pausada responde 410.
    check("4.1 410 (pausada)", st == 410, str(st))
    check("4.2 nada gravado", contagem(cid) == {}, str(contagem(cid)))


@cenario("5  funil: visita, reserva e venda na mesma origem")
def c5():
    nsu = reservar(SLUG_A, novo_horario(CAMP_A), extra={"origem": "Instagram"})
    origem = _db("select origem from virtual_orders where order_nsu=:n", n=nsu)[0][0]
    check("5.1 pedido guarda a origem reduzida", origem == "instagram", str(origem))
    pagar(nsu)
    login("gestor")
    r = client.get(f"/api/virtuais/campanhas/{CAMP_A}/funil")
    corpo = r.get_json() or {}
    check("5.2 200", r.status_code == 200, f"{r.status_code} {str(corpo)[:160]}")
    linha = next((x for x in corpo.get("por_origem", []) if x.get("origem") == "instagram"), {})
    check(
        "5.3 instagram: 1 visita, 1 reserva, 1 venda",
        (linha.get("visitas"), linha.get("reservas"), linha.get("vendas")) == (1, 1, 1),
        str(linha),
    )
    check("5.4 conversão 100.0", linha.get("conversao") == 100.0, str(linha.get("conversao")))
    tot = corpo.get("totais", {})
    check(
        "5.5 totais: 6 visitas, 1 reserva, 1 venda",
        (tot.get("visitas"), tot.get("reservas"), tot.get("vendas")) == (6, 1, 1),
        str(tot),
    )
    check("5.6 14 dias", len(corpo.get("por_dia", [])) == 14, str(len(corpo.get("por_dia", []))))
    links = {x.get("origem"): x.get("url") for x in corpo.get("links", [])}
    check(
        "5.7 link do WhatsApp no domínio da loja",
        links.get("whatsapp") == f"https://alo.mantoproducoes.com.br/{SLUG_A}?origem=whatsapp",
        str(links.get("whatsapp")),
    )
    logout()


@cenario("6  funil sem papel de loja → 403 (deve falhar)")
def c6():
    login("outro")
    r = client.get(f"/api/virtuais/campanhas/{CAMP_A}/funil")
    check("6.1 403", r.status_code == 403, str(r.status_code))
    logout()


# ── História 2: LGPD ────────────────────────────────────────────────────────────────────────
ESTADO: dict = {}


@cenario("7  reserva sem aceite não registra nada")
def c7():
    nsu = reservar(SLUG_A, novo_horario(CAMP_A))
    linha = _db(
        "select marketing_opt_in_at, marketing_opt_in_version, buyer_name "
        "from virtual_orders where order_nsu=:n",
        n=nsu,
    )[0]
    check("7.1 sem data de aceite", linha[0] is None, str(linha[0]))
    check("7.2 sem versão", linha[1] is None, str(linha[1]))
    check("7.3 sem nome (servidor aceita)", linha[2] is None, str(linha[2]))


@cenario("8  reserva com aceite e nome")
def c8():
    tel = telefone_novo()
    nsu = reservar(
        SLUG_A,
        novo_horario(CAMP_A),
        tel=tel,
        extra={
            "marketing_opt_in": True,
            "buyer_name": "  Maria Teste  ",
            "origem": "whatsapp",
        },
    )
    linha = _db(
        "select marketing_opt_in_at, marketing_opt_in_version, buyer_name "
        "from virtual_orders where order_nsu=:n",
        n=nsu,
    )[0]
    check("8.1 data do aceite", linha[0] is not None)
    check(
        "8.2 versão do texto",
        linha[1] == getattr(consts, "VIRTUAL_ACEITE_VERSAO", "?"),
        str(linha[1]),
    )
    check("8.3 nome limpo", linha[2] == "Maria Teste", str(linha[2]))
    ESTADO["c8"] = (nsu, tel)


@cenario("9  venda com aceite → ficha nova no CRM, sem dados de quem recebe")
def c9():
    if "c8" not in ESTADO:
        raise Bloqueado("cenário 8 não criou o pedido")
    nsu, tel = ESTADO["c8"]
    pagar(nsu)
    ficha = _db(
        "select id, name, email, source, marketing_opt_in_at, marketing_opt_in_source, "
        "utm_source, notes from clients where phone=:p",
        p="55" + tel,
    )
    check("9.1 ficha criada", len(ficha) == 1, str(len(ficha)))
    if not ficha:
        return
    cid, nome, email, source, aceite, aceite_origem, utm, notas = ficha[0]
    check("9.2 origem loja_virtual", source == "loja_virtual", str(source))
    check("9.3 nome de quem compra", nome == "Maria Teste", str(nome))
    check("9.4 e-mail", (email or "").startswith(f"v344-{RUN}"), str(email))
    check(
        "9.5 aceite com data e campanha",
        aceite is not None and TITULO_A in (aceite_origem or ""),
        f"{aceite} {aceite_origem}",
    )
    check("9.6 origem do acesso", utm == "whatsapp", str(utm))
    linha = " ".join(str(x) for x in ficha[0] if x is not None)
    check(
        "9.7 nada de quem recebe na ficha",
        f"Crianca{RUN}" not in linha and "dinossauro" not in linha and not notas,
        linha[:200],
    )
    evento = _db("select event_id from virtual_orders where order_nsu=:n", n=nsu)[0][0]
    ligado = _db("select 1 from event_clients where event_id=:e and client_id=:c", e=evento, c=cid)
    check("9.8 evento ligado à ficha", bool(ligado))
    ESTADO["c9_client"] = cid


@cenario("10 venda de telefone que já é cliente mantém nome e e-mail")
def c10():
    tel = telefone_novo()
    with app.app_context():
        db.session.add(
            Client(
                name="Nome Antigo", phone="55" + tel, email="antigo@example.com", source="manual"
            )
        )
        db.session.commit()
    nsu = reservar(
        SLUG_A,
        novo_horario(CAMP_A),
        tel=tel,
        extra={"marketing_opt_in": True, "buyer_name": "Outro Nome"},
    )
    pagar(nsu)
    ficha = _db(
        "select id, name, email, source, marketing_opt_in_at from clients where phone=:p",
        p="55" + tel,
    )
    check("10.1 continua uma ficha", len(ficha) == 1, str(len(ficha)))
    if not ficha:
        return
    cid, nome, email, source, aceite = ficha[0]
    check(
        "10.2 nome e e-mail como estavam",
        (nome, email) == ("Nome Antigo", "antigo@example.com"),
        f"{nome} {email}",
    )
    check("10.3 origem da ficha não muda", source == "manual", str(source))
    check("10.4 ganhou o aceite", aceite is not None)
    evento = _db("select event_id from virtual_orders where order_nsu=:n", n=nsu)[0][0]
    check(
        "10.5 evento ligado",
        bool(
            _db("select 1 from event_clients where event_id=:e and client_id=:c", e=evento, c=cid)
        ),
    )


@cenario("11 falha forçada na ficha não derruba a venda")
def c11():
    _ops("_cliente_da_venda")
    original = ops._cliente_da_venda

    def _boom(*a, **k):
        raise RuntimeError("CRM fora (dublê)")

    ops._cliente_da_venda = _boom
    try:
        nsu = reservar(SLUG_A, novo_horario(CAMP_A), extra={"marketing_opt_in": True})
        pagar(nsu)
    finally:
        ops._cliente_da_venda = original
    status, evento = _db("select status, event_id from virtual_orders where order_nsu=:n", n=nsu)[0]
    check("11.1 venda efetivada", status == "pago" and evento is not None, f"{status} {evento}")


def _vencer(nsu: str, dias: int) -> None:
    """Empurra a data de referência do pedido `dias` para trás (horário e evento juntos)."""
    quando = now_sp() - timedelta(days=dias)
    # O pedido nasce antes da chamada: criação e pagamento vão junto, um dia antes do horário.
    _exec(
        "update virtual_orders set created_at=:c, paid_at=:c where order_nsu=:n",
        c=quando - timedelta(days=1),
        n=nsu,
    )
    _exec(
        "update virtual_campaign_slots set start_at=:q where id=(select slot_id from "
        "virtual_orders where order_nsu=:n)",
        q=quando,
        n=nsu,
    )
    _exec(
        "update calendar_events set start_at=:q, end_at=:q2 where id=(select event_id from "
        "virtual_orders where order_nsu=:n)",
        q=quando,
        q2=quando + timedelta(minutes=10),
        n=nsu,
    )


def _notas(nsu: str):
    return _db(
        "select o.behavior_notes, e.description, e.google_event_id from virtual_orders o "
        "left join calendar_events e on e.id = o.event_id where o.order_nsu=:n",
        n=nsu,
    )[0]


@cenario("12 dicas vencidas somem do pedido, do evento e do Google")
def c12():
    apagar = _ops("apagar_dicas_vencidas")
    vivo = reservar(SLUG_A, novo_horario(CAMP_A))
    pagar(vivo)
    _vencer(vivo, 31)
    gravado = reservar(SLUG_A, None, modalidade="gravado")
    pagar(gravado)
    _exec(
        "update virtual_media_deliveries set due_date=:d where order_id=(select id from "
        "virtual_orders where order_nsu=:n)",
        d=(now_sp() - timedelta(days=31)).date(),
        n=gravado,
    )
    _exec(
        "update virtual_orders set created_at=:c, paid_at=:c where order_nsu=:n",
        c=now_sp() - timedelta(days=40),
        n=gravado,
    )
    largado = reservar(SLUG_A, novo_horario(CAMP_A))
    _exec(
        "update virtual_orders set status='expirado', locked_until=null, created_at=:q "
        "where order_nsu=:n",
        q=now_sp() - timedelta(days=31),
        n=largado,
    )
    gid = _notas(vivo)[2]
    GOOGLE_UPDATES.clear()
    with app.app_context():
        apagar()
    n_vivo, d_vivo, _ = _notas(vivo)
    check("12.1 ao vivo: pedido sem dicas", n_vivo is None, str(n_vivo))
    check("12.2 ao vivo: evento sem dicas", "dinossauro" not in (d_vivo or ""), str(d_vivo))
    chamada = next((u for u in GOOGLE_UPDATES if u["id"] == gid), None)
    check(
        "12.3 Google reescrito sem as dicas",
        chamada is not None and "dinossauro" not in chamada["description"],
        str(chamada),
    )
    check("12.4 vídeo vencido: sem dicas", _notas(gravado)[0] is None)
    check("12.5 reserva largada há 31 dias: sem dicas", _notas(largado)[0] is None)


@cenario("13 dicas no prazo e Google fora: ficam")
def c13():
    apagar = _ops("apagar_dicas_vencidas")
    recente = reservar(SLUG_A, novo_horario(CAMP_A))
    pagar(recente)
    _vencer(recente, 29)
    sem_google = reservar(SLUG_A, novo_horario(CAMP_A))
    pagar(sem_google)
    _vencer(sem_google, 31)
    GOOGLE_FORA[0] = True
    try:
        with app.app_context():
            apagar()
    finally:
        GOOGLE_FORA[0] = False
    check("13.1 29 dias: dicas ficam", _notas(recente)[0] is not None)
    n, d, _ = _notas(sem_google)
    check(
        "13.2 Google fora: nada apagado pela metade",
        n is not None and "dinossauro" in (d or ""),
        f"{n} | {d}",
    )


@cenario("14 CRM: origem Loja no gráfico e aceite na ficha")
def c14():
    login("gestor")
    r = client.get("/api/clientes/metricas")
    meses = (r.get_json() or {}).get("new_by_month", [])
    atual = next((m for m in meses if m.get("month") == now_sp().strftime("%Y-%m")), {})
    check("14.1 balde loja no mês", (atual.get("loja") or 0) >= 1, str(atual))
    cid = ESTADO.get("c9_client")
    if cid:
        ficha = client.get(f"/api/clientes/{cid}").get_json() or {}
        check(
            "14.2 ficha mostra o aceite", bool(ficha.get("marketing_opt_in_at")), str(ficha)[:200]
        )
        check(
            "14.3 ficha mostra de onde",
            TITULO_A in (ficha.get("marketing_opt_in_source") or ""),
            str(ficha.get("marketing_opt_in_source")),
        )
    logout()


# ── História 3: pixel ───────────────────────────────────────────────────────────────────────
@cenario("15 rastreamento sem ID devolve vazio")
def c15():
    r = client.get("/api/virtuais/rastreamento")
    check(
        "15.1 200 e null",
        r.status_code == 200
        and (r.get_json() or {}).get("meta_pixel_id") is None
        and "meta_pixel_id" in (r.get_json() or {}),
        f"{r.status_code} {r.get_data(as_text=True)[:80]}",
    )


@cenario("16 Superadmin grava o ID; não-dígito é recusado")
def c16():
    login("gestor")
    r = client.patch("/api/admin/settings", json={"meta_pixel_id": " 123456789012345 "})
    check("16.1 grava 200", r.status_code == 200, str(r.status_code))
    pub = client.get("/api/virtuais/rastreamento").get_json() or {}
    check("16.2 rastreamento devolve o ID", pub.get("meta_pixel_id") == "123456789012345", str(pub))
    lido = client.get("/api/admin/settings").get_json() or {}
    check(
        "16.3 configurações devolvem o ID",
        lido.get("meta_pixel_id") == "123456789012345",
        str(lido.get("meta_pixel_id")),
    )
    r = client.patch("/api/admin/settings", json={"meta_pixel_id": "abc123"})
    corpo = r.get_json() or {}
    check(
        "16.4 não-dígito → 400 no campo",
        r.status_code == 400 and "meta_pixel_id" in (corpo.get("error", {}).get("fields") or {}),
        f"{r.status_code} {corpo}",
    )
    r = client.patch("/api/admin/settings", json={"meta_pixel_id": ""})
    pub = client.get("/api/virtuais/rastreamento").get_json() or {}
    check("16.5 vazio desliga", r.status_code == 200 and pub.get("meta_pixel_id") is None, str(pub))
    logout()


@cenario("17 papel sem acesso grava o ID → 403 (deve falhar)")
def c17():
    login("outro")
    r = client.patch("/api/admin/settings", json={"meta_pixel_id": "999"})
    check("17.1 403", r.status_code == 403, str(r.status_code))
    valor = _db("select meta_pixel_id from site_settings where id=1")[0][0]
    check("17.2 nada mudou", valor is None, str(valor))
    logout()


def limpar() -> None:
    with app.app_context():
        db.session.rollback()
    with _engine.begin() as conn:

        def tem(tabela: str) -> bool:
            return bool(
                conn.execute(
                    text("select 1 from information_schema.tables where table_name=:t"),
                    {"t": tabela},
                ).first()
            )

        for cid in CRIADAS:
            ordens = [
                r[0]
                for r in conn.execute(
                    text("select id from virtual_orders where campaign_id=:c"), {"c": cid}
                )
            ]
            eventos = [
                r[0]
                for r in conn.execute(
                    text(
                        "select event_id from virtual_orders where campaign_id=:c and event_id is not null"
                    ),
                    {"c": cid},
                )
            ]
            if ordens:
                conn.execute(
                    text("update virtual_campaign_slots set order_id=null where campaign_id=:c"),
                    {"c": cid},
                )
                for tabela in (
                    "virtual_payment_notifications",
                    "virtual_refund_requests",
                    "virtual_order_notifications",
                    "virtual_media_deliveries",
                ):
                    conn.execute(
                        text(f"delete from {tabela} where order_id = any(:o)"), {"o": ordens}
                    )
                conn.execute(text("delete from virtual_orders where campaign_id=:c"), {"c": cid})
            for ev in eventos:
                conn.execute(text("delete from event_clients where event_id=:e"), {"e": ev})
                if tem("event_3d_gifts"):
                    conn.execute(text("delete from event_3d_gifts where event_id=:e"), {"e": ev})
                conn.execute(text("delete from event_roles where event_id=:e"), {"e": ev})
                conn.execute(text("delete from calendar_events where id=:e"), {"e": ev})
            if tem("virtual_campaign_visits"):
                conn.execute(
                    text("delete from virtual_campaign_visits where campaign_id=:c"), {"c": cid}
                )
            conn.execute(
                text("delete from virtual_campaign_slots where campaign_id=:c"), {"c": cid}
            )
            if tem("virtual_campaign_acervo"):
                conn.execute(
                    text("delete from virtual_campaign_acervo where campaign_id=:c"), {"c": cid}
                )
            conn.execute(text("delete from virtual_campaigns where id=:c"), {"c": cid})
        if TELEFONES:
            conn.execute(
                text(
                    "delete from event_clients where client_id in "
                    "(select id from clients where phone = any(:p))"
                ),
                {"p": TELEFONES},
            )
            conn.execute(text("delete from clients where phone = any(:p)"), {"p": TELEFONES})
    with app.app_context():
        s = SiteSetting.query.get(1)
        for campo, valor in SETTINGS_ORIGINAIS.items():
            if hasattr(s, campo):
                setattr(s, campo, valor)
        db.session.commit()


try:
    for fn in (c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15, c16, c17):
        fn()
finally:
    email_service._send = _send_original
    try:
        limpar()
        check("18.1 limpeza", True)
    except Exception as exc:  # noqa: BLE001
        check("18.1 limpeza", False, f"{type(exc).__name__}: {exc}"[:200])
    check("18.2 nenhuma conexão externa escapou", not _ESCAPES, str(_ESCAPES[:5]))

ok = sum(1 for r in resultados if r[1] == "OK")
falha = sum(1 for r in resultados if r[1] == "FALHA")
bloq = sum(1 for r in resultados if r[1] == "BLOQUEADO")
print(f"\n{ok} OK · {falha} FALHA · {bloq} BLOQUEADO (de {len(resultados)})")
sys.exit(1 if falha or bloq else 0)
