"""Verificação da feature 348 — Origem completa: de qual anúncio, clique ou conversa veio cada venda.

Os cenários da tabela da spec, contra o espelho `manto_348` (dump noturno de 17/11; exceção ao `manto_local`
compartilhado registrada no `plan.md`). Nada sai da máquina: a Meta e o Google Agenda viram dublês e um disjuntor de
rede derruba qualquer conexão que não seja o Postgres local. As conversas nascem pelo webhook assinado.

Tudo de teste leva `v348-`. Rodar (PowerShell, na raiz do worktree)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs/348-origem-completa/verify_348.py
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import time
import traceback
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

_ESCAPES: list[str] = []
_LOCAIS = ("localhost", "127.0.0.1", "::1")
_connect_original = socket.socket.connect
_create_connection_original = socket.create_connection


def _host_de(endereco) -> str:
    return str(endereco[0]) if isinstance(endereco, tuple) and endereco else str(endereco)


def _connect_local(self, endereco):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 348: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 348: conexão de saída bloqueada para {_host_de(endereco)}")
    return _create_connection_original(endereco, *args, **kwargs)


socket.socket.connect = _connect_local
socket.create_connection = _create_connection_local

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, email_service, limiter, maps  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    Client,
    MarketingAgentRun,
    MarketingCampaignMetric,
    OrcamentoHistory,
    Role,
    User,
)

PREFIX = "v348-"
SENHA = "verify-348-senha"
SEGREDO = "segredo-do-app-v348"
NUMERO_ID = "v348-phone"
NUMERO_MANTO = "5511900000348"
WA_A = "5511963480001"  # anúncio 1 com ctwa_clid; ficha antiga sem origem
WA_B = "5511963480002"  # contatos antigos para o preenchimento retroativo
WA_C = "5511963480003"  # chega pelo código do site; ficha sem origem
WA_D = "5511963480004"  # tenta usar código já usado, vencido e inexistente
WA_E = "5511963480005"  # anúncio 2; recebe o orçamento pela conversa
WA_F = "5511963480006"  # cliente recorrente: anúncio A, depois anúncio B
WA_G = "5511963480007"  # só um anúncio de 120 dias atrás
CONTATOS = [WA_A, WA_B, WA_C, WA_D, WA_E, WA_F, WA_G]
TEL_FORM = "11963480091"
TELEFONES = CONTATOS + [f"55{TEL_FORM}", TEL_FORM]
AD = {n: f"{PREFIX}ad-{n}" for n in range(1, 6)}
CAMPANHA_GOOGLE = f"{PREFIX}Festa Google"
DATA_FORM = "2031-04-17"
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
PASTA_MIDIA = tempfile.mkdtemp(prefix="v348-midia-")

app = create_app()
app.config["TESTING"] = True
app.config.update(
    WHATSAPP_ACCESS_TOKEN="token-falso-v348",
    WHATSAPP_APP_SECRET=SEGREDO,
    WHATSAPP_VERIFY_TOKEN="verifica-v348",
    WHATSAPP_PHONE_NUMBER_ID=NUMERO_ID,
    WHATSAPP_AVISO_SINCRONO=True,
    WHATSAPP_SUPPRESS_SEND=False,
    META_ANUNCIOS_TOKEN="token-dos-anuncios-v348",
    CONVERSAS_MEDIA_FOLDER=PASTA_MIDIA,
    WEB_PUSH_SUPPRESS=True,
)
limiter.enabled = False

# ── Dublês da Meta e do Google ───────────────────────────────────────────────────────────────────
import app.integracoes.meta_anuncios_client as _mac  # noqa: E402
import app.integracoes.whatsapp_client as _wc  # noqa: E402

_REAIS = {
    "wc": {n: getattr(_wc, n) for n in ("enviar", "subir_midia", "marcar_lida", "requisitar")},
    "mac": {"consultar_anuncio": _mac.consultar_anuncio},
}


class MetaFalsa:
    """Responde como a Meta: envio, mídia e a consulta do anúncio (com o conjunto)."""

    def __init__(self) -> None:
        self.seq = 0

    def _id(self, prefixo: str) -> str:
        self.seq += 1
        return f"{prefixo}{PREFIX}{self.seq}"

    def wa_enviar(self, conexao, corpo):
        return {"id": self._id("wamid."), "wa_id": corpo.get("to")}

    def wa_subir(self, conexao, dados, mime, nome):
        return self._id("media-")

    def wa_lida(self, conexao, wamid):
        return None

    def anuncio(self, conexao, anuncio_id):
        return {
            "nome": f"Anúncio {anuncio_id}",
            "campanha_id": f"c-{anuncio_id}",
            "campanha_nome": f"{PREFIX}Campanha {anuncio_id}",
            "conjunto_id": f"cj-{anuncio_id}",
            "conjunto_nome": f"{PREFIX}Conjunto {anuncio_id}",
        }


meta = MetaFalsa()
_wc.enviar, _wc.subir_midia, _wc.marcar_lida = meta.wa_enviar, meta.wa_subir, meta.wa_lida
_mac.consultar_anuncio = meta.anuncio

GOOGLE = {"insercoes": 0}


def _g_insert(*a, **k):
    GOOGLE["insercoes"] += 1
    return {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}"}


maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_service.insert_event = _g_insert
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = _g_insert
email_service._send = lambda *a, **k: True
email_service.send_async = lambda fn, *args: None

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchone()


def _no_banco_todas(sql: str, **params):
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _no_banco_escrever(sql: str, **params):
    with _engine_externo.begin() as conn:
        return conn.execute(text(sql), params)


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


def _usuario(sufixo: str, papel: str) -> tuple[str, int]:
    email = f"{PREFIX}{sufixo.lower()}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        db.session.add(user)
    user.set_password(SENHA)
    user.roles.clear()
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.commit()
    return email, user.id


def _http(email: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
    _garante(r.status_code == 200, f"login {email} → {r.status_code}")
    return c


def _assinado(corpo: dict) -> None:
    bruto = json.dumps(corpo).encode()
    assinatura = "sha256=" + hmac.new(SEGREDO.encode(), bruto, hashlib.sha256).hexdigest()
    with app.test_client() as c:
        r = c.post(
            "/api/webhooks/whatsapp",
            data=bruto,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": assinatura},
        )
    _garante(r.status_code == 200, f"aviso → {r.status_code}")


def _wa(
    wa_id: str, wamid: str, nome: str, referral: dict | None = None, texto: str | None = None
) -> int:
    """A cliente escreve no WhatsApp (com o `referral` de quem veio do anúncio)."""
    mensagem = {
        "from": wa_id,
        "id": f"wamid.{PREFIX}{wamid}",
        "timestamp": str(int(time.time())),
        "type": "text",
        "text": {"body": texto or "Oi, quero saber o preço"},
    }
    if referral:
        mensagem["referral"] = referral
    valor = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": NUMERO_MANTO, "phone_number_id": NUMERO_ID},
        "contacts": [{"profile": {"name": f"{PREFIX}{nome}"}, "wa_id": wa_id}],
        "messages": [mensagem],
    }
    _assinado(
        {
            "object": "whatsapp_business_account",
            "entry": [{"id": "v348-waba", "changes": [{"field": "messages", "value": valor}]}],
        }
    )
    return _no_banco("SELECT id FROM conversas WHERE contato_id=:c", c=wa_id).id


def _ref_wa(anuncio: str) -> dict:
    return {
        "source_url": f"https://fb.me/{anuncio}",
        "source_id": anuncio,
        "source_type": "ad",
        "headline": f"Título {anuncio}",
        "body": "Personagens para festa infantil",
        "media_type": "image",
        "ctwa_clid": f"clid-{anuncio}",
    }


def _nova_ficha(nome: str, telefone: str, **campos) -> int:
    with app.app_context():
        client = Client(name=nome, phone=telefone, **{"source": "manual", **campos})
        db.session.add(client)
        db.session.commit()
        return client.id


def _orcamento(cliente: str) -> int:
    from app.orcamento import quote_ops

    with app.app_context():
        entry = OrcamentoHistory(
            user_id=estado["ana_id"],
            client_name=cliente,
            event_location=f"{PREFIX}Buffet",
            event_date=(datetime.now(UTC) + timedelta(days=40)).date().isoformat(),
            total_1h=Decimal("1800"),
            total_2h=Decimal("2400"),
            total_3h=Decimal("3000"),
            total_4h=Decimal("3500"),
            has_show=False,
        )
        db.session.add(entry)
        db.session.flush()
        quote = quote_ops.legacy_quote(entry)
        quote["message"] = "Olá! Segue o orçamento."
        entry.result_snapshot = json.dumps(quote, ensure_ascii=False)
        db.session.commit()
        return entry.id


def _evento(titulo: str, *, tipo: str = "R&I", venda: str = "1800", **campos) -> int:
    with app.app_context():
        inicio = datetime.combine(
            now_sp().date() + timedelta(days=50), datetime.min.time()
        ).replace(hour=15)
        ev = CalendarEvent(
            google_event_id=f"{PREFIX}g{uuid.uuid4().hex[:10]}",
            title=f"{PREFIX}{titulo}",
            event_type=tipo,
            start_at=inicio,
            end_at=inicio + timedelta(hours=2),
            source="platform",
            sale_value=Decimal(venda) if venda else None,
            sale_value_gross=Decimal(venda) if venda else None,
            sale_date=now_sp().date() if venda else None,
            seller_id=estado["ana_id"],
            **campos,
        )
        db.session.add(ev)
        db.session.commit()
        return ev.id


def _contato(chave: str):
    return _no_banco(
        "SELECT id, conversa_id, tipo, anuncio_id, titulo, link, ctwa_clid, codigo_id FROM conversa_anuncios "
        "WHERE chave=:c",
        c=chave,
    )


def _codigo(codigo: str):
    return _no_banco(
        "SELECT id, codigo, gclid, utm_source, utm_campaign, campanha_id, pagina, procedencia, conversa_id, "
        "usado_em, form_response_id, created_at FROM origem_codigos WHERE codigo=:c",
        c=codigo,
    )


def _ficha(client_id: int):
    return _no_banco(
        "SELECT lead_origin, utm_source, utm_medium, utm_campaign, utm_campaign_id FROM clients WHERE id=:i",
        i=client_id,
    )


def _venda(tabela: str, registro_id: int) -> tuple:
    linha = _no_banco(
        f"SELECT conversa_id, origem_contato_id FROM {tabela} WHERE id=:i", i=registro_id
    )
    return tuple(linha) if linha is not None else (None, None)


def _criar_codigo(**marcadores) -> str:
    from app.conversas import codigo_ops

    with app.app_context():
        registro = codigo_ops.criar_codigo(marcadores)
        return registro.codigo


def _corpo_criacao(titulo: str, *, tipo: str = "R&I", extra: dict | None = None) -> dict:
    d = (now_sp().date() + timedelta(days=60)).isoformat()
    corpo = {
        "title": f"{PREFIX}{titulo}",
        "event_type": tipo,
        "date": d,
        "start": "15:00",
        "end": "17:00",
        "location": f"{PREFIX}Buffet, São Paulo",
        "description": "",
        "needs_rehearsal": False,
        "sale_value": 1800.0,
        "sale_value_gross": 1800.0,
        "transport_value": 0,
        "acrescimo_value": 0,
        "with_invoice": False,
        "is_cortesia_permuta": False,
        "seller_id": estado["ana_id"],
        "sale_date": None,
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
        "duracao": "2",
        "characters": [],
        "orc_caches": [],
        "acrescimos": [],
        "observations": [],
        "clients": [],
    }
    corpo.update(extra or {})
    return corpo


def _criar_evento(corpo: dict, esperado: int = 201):
    r = _http(estado["ana"]).post("/api/events", json=corpo)
    _garante(
        r.status_code == esperado,
        f"POST /api/events → {r.status_code} {r.get_data(as_text=True)[:300]}",
    )
    if esperado != 201:
        return r
    j = r.get_json()
    return j["event"]["id"] if "event" in j else j["id"]


def _corpo_comercial(eid: int, **troca) -> dict:
    with app.app_context():
        ev = db.session.get(CalendarEvent, eid)
        corpo = {
            "sale_value": float(ev.sale_value) if ev.sale_value is not None else None,
            "sale_value_gross": float(ev.sale_value_gross)
            if ev.sale_value_gross is not None
            else None,
            "transport_value": float(ev.transport_value or 0),
            "with_invoice": bool(ev.with_invoice),
            "is_cortesia_permuta": False,
            "seller_id": ev.seller_id,
            "sale_date": ev.sale_date.isoformat() if ev.sale_date else None,
            "commission_rate": None,
            "payment_method": ev.payment_method,
            "payment_installments": ev.payment_installments,
            "payment_due_date": ev.payment_due_date.isoformat() if ev.payment_due_date else None,
        }
    corpo.update(troca)
    return corpo


def _payload_formulario(nome: str, **extra) -> dict:
    from app.formularios.formularios_ops import FORM_META, _load_fields

    dados: dict[str, str] = {}
    with app.app_context():
        campos = _load_fields("comum")
    for campo in campos:
        if not campo.required:
            continue
        tipo = campo.field_type
        if tipo == "data":
            dados[campo.field_key] = DATA_FORM
        elif tipo == "hora":
            dados[campo.field_key] = "14:00"
        elif tipo == "email":
            dados[campo.field_key] = "verify348@example.com"
        elif tipo == "telefone":
            dados[f"{campo.field_key}_ddi"] = "+55"
            dados[f"{campo.field_key}_national"] = TEL_FORM
        elif tipo == "sim_nao":
            dados[campo.field_key] = "Sim"
        elif tipo == "selecao":
            dados[campo.field_key] = (campo.options_list or [""])[0]
        elif tipo == "cpf":
            dados[campo.field_key] = "12345678901"
        elif tipo == "cnpj":
            dados[campo.field_key] = "12345678000190"
        elif tipo == "cep":
            dados[campo.field_key] = "01310100"
        else:
            dados[campo.field_key] = f"{PREFIX}valor"
    dados[FORM_META["comum"]["name_key"]] = nome
    dados["whatsapp_ddi"] = "+55"
    dados["whatsapp_national"] = TEL_FORM
    dados.update(extra)
    return dados


# ── História 1 — o clique no anúncio de WhatsApp ───────────────────────────────────────────────────


def cen_01() -> None:
    _wa(WA_A, "a-1", "Ana", _ref_wa(AD[1]))
    contato = _contato(f"wamid.{PREFIX}a-1")
    _garante(contato is not None and contato.tipo == "anuncio", f"contato pelo anúncio {contato}")
    _garante(contato.ctwa_clid == f"clid-{AD[1]}", f"ctwa_clid {contato.ctwa_clid!r}")
    f = _ficha(estado["ficha_a"])
    _garante(f.utm_campaign == f"{PREFIX}Campanha {AD[1]}", f"campanha na ficha {f}")
    _garante(f.utm_campaign_id == f"c-{AD[1]}", f"id da campanha na ficha {f.utm_campaign_id!r}")


def _migration():
    caminho = REPO_ROOT / "migrations" / "versions" / "a348c0d1e2f3_origem_completa.py"
    spec = importlib.util.spec_from_file_location("mig_a348", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def cen_02() -> None:
    conversa = _wa(WA_B, "b-1", "Bia")
    agora = datetime.now(UTC).replace(tzinfo=None)
    linhas = (
        (
            "b-velha",
            json.dumps({"id": "x", "referral": {"source_id": AD[3], "ctwa_clid": "clid-velho"}}),
        ),
        ("b-ruim", "{isto não é json"),
        ("b-sem", json.dumps({"id": "y", "referral": {"source_id": AD[3]}})),
    )
    for sufixo, dados in linhas:
        chave = f"wamid.{PREFIX}{sufixo}"
        _no_banco_escrever(
            "INSERT INTO conversa_mensagens (conversa_id, direcao, tipo, texto, externo_id, situacao, origem, dados, "
            "momento, created_at) VALUES (:c, 'recebida', 'texto', 'Oi', :e, 'recebida', 'contato', :d, :m, :m)",
            c=conversa,
            e=chave,
            d=dados,
            m=agora,
        )
        _no_banco_escrever(
            "INSERT INTO conversa_anuncios (conversa_id, canal, chave, tipo, anuncio_id, momento, created_at) "
            "VALUES (:c, 'whatsapp', :k, 'anuncio', :a, :m, :m)",
            c=conversa,
            k=chave,
            a=AD[3],
            m=agora,
        )
    mig = _migration()
    with _engine_externo.begin() as conn:
        mig._preencher_ctwa_clid(conn)
    _garante(
        _contato(f"wamid.{PREFIX}b-velha").ctwa_clid == "clid-velho", "o retroativo não preencheu"
    )
    _garante(
        _contato(f"wamid.{PREFIX}b-ruim").ctwa_clid is None, "a mensagem corrompida ganhou valor"
    )
    _garante(_contato(f"wamid.{PREFIX}b-sem").ctwa_clid is None, "o referral sem clid ganhou valor")


def cen_03() -> None:
    meta_row = _no_banco(
        "SELECT conjunto_id, conjunto_nome FROM anuncios_meta WHERE anuncio_id=:a", a=AD[1]
    )
    _garante(
        meta_row is not None and meta_row.conjunto_id == f"cj-{AD[1]}",
        f"conjunto gravado {meta_row}",
    )
    pedidos: list[dict] = []

    def _requisitar(conexao, metodo, url, params=None, **kw):
        pedidos.append(params or {})
        return {
            "name": "Anúncio X",
            "campaign": {"id": "11", "name": "C"},
            "adset": {"id": "99", "name": "Mães SP"},
        }

    _wc.requisitar = _requisitar
    try:
        conexao = _wc.ConexaoMeta(
            base="https://x.invalid", versao="v26.0", token="t", phone_number_id="", travada=False
        )
        dados = _REAIS["mac"]["consultar_anuncio"](conexao, "123")
    finally:
        _wc.requisitar = _REAIS["wc"]["requisitar"]
    _garante("adset{id,name}" in (pedidos[0].get("fields") or ""), f"campos pedidos {pedidos}")
    _garante(
        dados.get("conjunto_id") == "99" and dados.get("conjunto_nome") == "Mães SP",
        f"conjunto {dados}",
    )


# ── História 2 — o clique no site chega à conversa ─────────────────────────────────────────────────


def cen_04() -> None:
    c = app.test_client()
    r = c.post(
        "/api/origem/codigo",
        json={
            "gclid": f"{PREFIX}gclid-1",
            "gad_campaignid": "777",
            "utm_source": "google",
            "utm_campaign": CAMPANHA_GOOGLE,
            "pagina": "/catalogo/f/pre-contrato?gclid=abc",
            "procedencia": "www.google.com",
            "estranho": "x",
            "utm_term": 123,
        },
    )
    _garante(r.status_code == 201, f"código → {r.status_code} {r.get_data(as_text=True)[:200]}")
    codigo = r.get_json()["codigo"]
    _garante(
        re.fullmatch(f"[{ALFABETO}]{{5}}", codigo) is not None, f"formato do código {codigo!r}"
    )
    _garante(r.get_json()["linha"] == f"Código do site: #{codigo}", f"linha {r.get_json()}")
    linha = _codigo(codigo)
    _garante(
        linha.gclid == f"{PREFIX}gclid-1" and linha.campanha_id == "777", f"marcadores {linha}"
    )
    _garante(linha.pagina == "/catalogo/f/pre-contrato", f"página sem a query {linha.pagina!r}")
    estado["codigo_api"] = codigo
    r = c.post(
        "/api/origem/codigo",
        json={"utm_id": "555", "utm_source": "meta", "utm_campaign": f"{PREFIX}Meta"},
    )
    _garante(
        r.status_code == 201 and _codigo(r.get_json()["codigo"]).campanha_id == "555",
        "utm_id não virou o id",
    )
    # DEVE falhar: sem marcador nenhum.
    r = c.post("/api/origem/codigo", json={"pagina": "/catalogo/", "procedencia": "www.google.com"})
    _garante(r.status_code == 400, f"sem marcador deveria ser 400, veio {r.status_code}")


def cen_05() -> None:
    codigo = _criar_codigo(gclid=f"{PREFIX}gclid-form", utm_campaign=CAMPANHA_GOOGLE)
    c = app.test_client()
    r = c.post(
        "/api/formularios/comum",
        data=_payload_formulario(f"{PREFIX}Fernanda", origem_codigo=codigo),
    )
    _garante(r.status_code == 201, f"formulário → {r.status_code} {r.get_data(as_text=True)[:200]}")
    mensagem = unquote(r.get_json()["wa_link"])
    _garante(f"Código do site: #{codigo}" in mensagem, "a mensagem não levou o código")
    resposta = _no_banco(
        "SELECT id FROM form_responses WHERE contact_name=:n ORDER BY id DESC",
        n=f"{PREFIX}Fernanda",
    )
    _garante(
        _codigo(codigo).form_response_id == resposta.id, "a resposta não ficou ligada ao código"
    )
    r = c.post(
        "/api/formularios/comum",
        data=_payload_formulario(f"{PREFIX}Fernanda 2", origem_codigo="QQQQQ"),
    )
    _garante(r.status_code == 201, f"formulário 2 → {r.status_code}")
    _garante(
        "Código do site" not in unquote(r.get_json()["wa_link"]),
        "código inexistente entrou na mensagem",
    )


def cen_06() -> None:
    codigo = _criar_codigo(
        gclid=f"{PREFIX}gclid-c",
        gad_campaignid="777",
        utm_campaign=CAMPANHA_GOOGLE,
        pagina="/catalogo/",
    )
    estado["codigo_c"] = codigo
    conversa = _wa(
        WA_C, "c-1", "Carla", texto=f"Olá! Vi os personagens.\n\nCódigo do site: #{codigo.lower()}"
    )
    estado["conv_c"] = conversa
    linha = _codigo(codigo)
    _garante(
        linha.conversa_id == conversa and linha.usado_em is not None, f"código não ligou {linha}"
    )
    contato = _contato(f"site:{codigo}")
    _garante(
        contato is not None and contato.tipo == "site" and contato.codigo_id == linha.id,
        f"contato {contato}",
    )
    _garante(
        contato.titulo == CAMPANHA_GOOGLE and contato.conversa_id == conversa, f"contato {contato}"
    )
    f = _ficha(estado["ficha_c"])
    _garante(
        f.lead_origin == "Site" and f.utm_source == "google" and f.utm_medium == "cpc", f"ficha {f}"
    )
    _garante(
        f.utm_campaign == CAMPANHA_GOOGLE and f.utm_campaign_id == "777", f"campanha na ficha {f}"
    )


def cen_07() -> None:
    usado = estado["codigo_c"]
    vencido = _criar_codigo(gclid=f"{PREFIX}gclid-vencido")
    _no_banco_escrever(
        "UPDATE origem_codigos SET created_at = created_at - interval '91 days' WHERE codigo=:c",
        c=vencido,
    )
    conversa = _wa(WA_D, "d-1", "Dani", texto=f"#{usado} #{vencido} #QQQQQ Oi")
    _garante(_codigo(usado).conversa_id == estado["conv_c"], "o código usado trocou de conversa")
    _garante(_codigo(vencido).conversa_id is None, "o código vencido ligou")
    sites = _no_banco(
        "SELECT count(*) FROM conversa_anuncios WHERE conversa_id=:c AND tipo='site'", c=conversa
    )[0]
    _garante(sites == 0, f"a conversa D ganhou {sites} contato(s) do site")


# ── História 3 — a venda sabe de qual conversa veio ────────────────────────────────────────────────


def cen_08() -> None:
    conversa = _wa(WA_E, "e-1", "Eva", _ref_wa(AD[2]))
    estado["conv_e"] = conversa
    contato = _contato(f"wamid.{PREFIX}e-1")
    orcamento = _orcamento(f"{PREFIX}Eva Lima")
    estado["orc_e"] = orcamento
    r = _http(estado["ana"]).post(
        f"/api/conversas/{conversa}/orcamento",
        json={"orcamento_id": orcamento, "chave_envio": str(uuid.uuid4())},
    )
    _garante(r.status_code == 201, f"envio → {r.status_code} {r.get_data(as_text=True)[:200]}")
    venda = _venda("orcamento_history", orcamento)
    _garante(venda == (conversa, contato.id), f"orçamento {venda}")
    # O envio seguinte, por outra conversa, não troca.
    r = _http(estado["ana"]).post(
        f"/api/conversas/{estado['conv_c']}/orcamento",
        json={"orcamento_id": orcamento, "chave_envio": str(uuid.uuid4())},
    )
    _garante(r.status_code == 201, f"segundo envio → {r.status_code}")
    _garante(
        _venda("orcamento_history", orcamento)[0] == conversa, "o segundo envio trocou a conversa"
    )
    # Orçamento da conversa C (veio pelo site), para o cenário 10.
    orc_c = _orcamento(f"{PREFIX}Carla Lima")
    estado["orc_c"] = orc_c
    r = _http(estado["ana"]).post(
        f"/api/conversas/{estado['conv_c']}/orcamento",
        json={"orcamento_id": orc_c, "chave_envio": str(uuid.uuid4())},
    )
    _garante(r.status_code == 201, f"envio C → {r.status_code}")
    _garante(
        _venda("orcamento_history", orc_c)[1] == _contato(f"site:{estado['codigo_c']}").id,
        "o orçamento da C não ficou com o contato do site",
    )


def cen_09() -> None:
    from app.conversas import origem_ops

    conversa = _wa(WA_F, "f-1", "Fabi", _ref_wa(AD[4]))
    estado["conv_f"] = conversa
    _no_banco_escrever(
        "UPDATE conversa_anuncios SET momento = momento - interval '10 days' WHERE chave=:k",
        k=f"wamid.{PREFIX}f-1",
    )
    toque_a = _contato(f"wamid.{PREFIX}f-1").id
    ev1 = _evento("Primeira festa da Fabi")
    with app.app_context():
        origem_ops.ligar_evento(db.session.get(CalendarEvent, ev1), conversa)
        db.session.commit()
    _wa(WA_F, "f-2", "Fabi", _ref_wa(AD[5]))
    toque_b = _contato(f"wamid.{PREFIX}f-2").id
    ev2 = _evento("Segunda festa da Fabi")
    with app.app_context():
        origem_ops.ligar_evento(db.session.get(CalendarEvent, ev2), conversa)
        db.session.commit()
    _garante(
        _venda("calendar_events", ev1) == (conversa, toque_a),
        f"venda 1 {_venda('calendar_events', ev1)}",
    )
    _garante(
        _venda("calendar_events", ev2) == (conversa, toque_b),
        f"venda 2 {_venda('calendar_events', ev2)}",
    )
    # Só um anúncio de 120 dias atrás: a venda fica com a conversa e sem contato (orgânica).
    conv_g = _wa(WA_G, "g-1", "Gabi", _ref_wa(AD[3]))
    _no_banco_escrever(
        "UPDATE conversa_anuncios SET momento = momento - interval '120 days' WHERE chave=:k",
        k=f"wamid.{PREFIX}g-1",
    )
    ev3 = _evento("Festa da Gabi")
    with app.app_context():
        origem_ops.ligar_evento(db.session.get(CalendarEvent, ev3), conv_g)
        db.session.commit()
    _garante(
        _venda("calendar_events", ev3) == (conv_g, None),
        f"venda orgânica {_venda('calendar_events', ev3)}",
    )
    # Nunca pela ficha: um evento da mesma cliente, criado sem conversa, fica sem conversa.
    ficha_f = _no_banco("SELECT client_id FROM conversas WHERE id=:c", c=conversa).client_id
    ev4 = _evento("Terceira festa da Fabi", client_id=ficha_f)
    _garante(_venda("calendar_events", ev4) == (None, None), "o evento ligou pela ficha")


def cen_10() -> None:
    # (a) evento criado a partir do orçamento herda a conversa e o contato.
    ev = _criar_evento(
        _corpo_criacao("Festa da Eva", extra={"orcamento_history_id": estado["orc_e"]})
    )
    estado["ev_eva"] = ev
    _garante(
        _venda("calendar_events", ev) == tuple(_venda("orcamento_history", estado["orc_e"])),
        f"criação não herdou {_venda('calendar_events', ev)}",
    )
    # (b) ligar e desligar o orçamento leva junto o que veio dele.
    ev_x = _evento("Festa da Carla")
    r = _http(estado["ana"]).patch(
        f"/api/events/{ev_x}/orcamento",
        json={"orcamento_history_id": estado["orc_c"], "aplicar_equipe": False},
    )
    _garante(
        r.status_code == 200, f"ligar orçamento → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    _garante(
        _venda("calendar_events", ev_x) == tuple(_venda("orcamento_history", estado["orc_c"])),
        f"ligar não herdou {_venda('calendar_events', ev_x)}",
    )
    r = _http(estado["ana"]).patch(
        f"/api/events/{ev_x}/orcamento", json={"orcamento_history_id": None}
    )
    _garante(r.status_code == 200, f"desligar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(
        _venda("calendar_events", ev_x) == (None, None),
        f"desligar não levou {_venda('calendar_events', ev_x)}",
    )
    # (c) a ligação feita pela conversa não é apagada por um orçamento sem conversa.
    from app.conversas import origem_ops

    ev_y = _evento("Festa ligada pela conversa")
    with app.app_context():
        origem_ops.ligar_evento(db.session.get(CalendarEvent, ev_y), estado["conv_f"])
        db.session.commit()
    antes = _venda("calendar_events", ev_y)
    orc_sem = _orcamento(f"{PREFIX}Sem conversa")
    r = _http(estado["ana"]).patch(
        f"/api/events/{ev_y}/orcamento",
        json={"orcamento_history_id": orc_sem, "aplicar_equipe": False},
    )
    _garante(r.status_code == 200, f"ligar sem conversa → {r.status_code}")
    _garante(_venda("calendar_events", ev_y) == antes, "o orçamento sem conversa apagou a ligação")


def cen_11() -> None:
    ev = _criar_evento(
        _corpo_criacao("Festa pela conversa", extra={"conversa_id": estado["conv_f"]})
    )
    toque_b = _contato(f"wamid.{PREFIX}f-2").id
    _garante(
        _venda("calendar_events", ev) == (estado["conv_f"], toque_b),
        f"criação {_venda('calendar_events', ev)}",
    )
    _garante(
        _no_banco("SELECT frente FROM calendar_events WHERE id=:i", i=ev).frente is None,
        "a sugestão por exclusão foi gravada na criação",
    )
    # DEVE falhar: conversa inexistente, antes do Google.
    antes = GOOGLE["insercoes"]
    r = _criar_evento(
        _corpo_criacao("Festa conversa falsa", extra={"conversa_id": 999999999}), esperado=400
    )
    _garante("conversa_id" in (r.get_json()["error"].get("fields") or {}), f"campo {r.get_json()}")
    _garante(GOOGLE["insercoes"] == antes, "o Google foi chamado antes da recusa")


# ── História 4 — a frente ──────────────────────────────────────────────────────────────────────────


def cen_12() -> None:
    ev = _evento("Festa da Sofia")
    estado["ev_sofia"] = ev
    url = f"/api/events/{ev}/comercial"
    c = _http(estado["ana"])
    # DEVE falhar: venda sem frente.
    r = c.patch(url, json=_corpo_comercial(ev, frente=None))
    _garante(r.status_code == 400, f"sem frente → {r.status_code}")
    _garante(
        r.get_json()["error"]["fields"].get("frente") == "Selecione a frente da venda.",
        f"{r.get_json()}",
    )
    # DEVE falhar: frente fora da lista.
    r = c.patch(url, json=_corpo_comercial(ev, frente="xyz"))
    _garante(
        r.status_code == 400 and "frente" in r.get_json()["error"]["fields"],
        f"inválida → {r.status_code}",
    )
    r = c.patch(url, json=_corpo_comercial(ev, frente="social"))
    _garante(r.status_code == 200, f"social → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(
        _no_banco("SELECT frente FROM calendar_events WHERE id=:i", i=ev).frente == "social",
        "não gravou",
    )
    frente = r.get_json()["venda"]["frente"]
    _garante(frente["frente"] == "social" and frente["definida"] is True, f"detalhe {frente}")
    _garante(
        frente["sugestao"] == "festas" and frente["sugestao_certa"] is False, f"sugestão {frente}"
    )
    # Bundle antigo (sem a chave) e `null` não apagam.
    r = c.patch(url, json=_corpo_comercial(ev))
    _garante(r.status_code == 200, f"bundle antigo → {r.status_code}")
    r = c.patch(url, json=_corpo_comercial(ev, frente=None))
    _garante(r.status_code == 200, f"null → {r.status_code}")
    _garante(
        _no_banco("SELECT frente FROM calendar_events WHERE id=:i", i=ev).frente == "social",
        "apagou",
    )
    # Criação: a sugestão certa é gravada; a frente do corpo vence.
    ev_corp = _criar_evento(_corpo_criacao("Convenção", tipo="CORP"))
    _garante(
        _no_banco("SELECT frente FROM calendar_events WHERE id=:i", i=ev_corp).frente
        == "corporativo",
        "CORP",
    )
    ev_soc = _criar_evento(_corpo_criacao("Festa da Lia", extra={"frente": "social"}))
    _garante(
        _no_banco("SELECT frente FROM calendar_events WHERE id=:i", i=ev_soc).frente == "social",
        "corpo",
    )
    r = _criar_evento(_corpo_criacao("Festa inválida", extra={"frente": "xyz"}), esperado=400)
    _garante("frente" in r.get_json()["error"]["fields"], "criação com frente inválida")


_REGRA_DE_16_11 = """
CASE
  WHEN COALESCE(title, '') ILIKE '(EDU%' OR COALESCE(event_type, '') = 'EDUCAMANTO' THEN 'educamanto'
  WHEN COALESCE(event_type, '') = 'CORP' THEN 'corporativo'
  WHEN COALESCE(title, '') ~* '(15 anos|debut|casamento|noiv|bodas)' THEN 'social'
  WHEN COALESCE(event_type, '') IN ('VM', 'VIRTUAL') THEN 'loja'
  ELSE 'festas'
END
"""


def cen_13() -> None:
    from app.calendar import frente_ops

    casos = (
        (("(EDU) Escola Aurora", "R&I"), ("educamanto", True)),
        (("Teatro", "EDUCAMANTO"), ("educamanto", True)),
        (("Convenção", "CORP"), ("corporativo", True)),
        (("Debutante 15 anos da Lia", "R&I"), ("social", True)),
        (("Casamento Ana e Leo", "SHOW"), ("social", True)),
        (("Papai Noel", "VM"), ("loja", True)),
        (("Festa da Sofia", "R&I"), ("festas", False)),
        ((None, None), ("festas", False)),
    )
    for entrada, esperado in casos:
        _garante(
            frente_ops.sugestao(*entrada) == esperado,
            f"sugestão {entrada} → {frente_ops.sugestao(*entrada)}",
        )
    with app.app_context():
        satelite = CalendarEvent(
            google_event_id=f"{PREFIX}g{uuid.uuid4().hex[:10]}",
            title=f"{PREFIX}Dia 2 da Sofia",
            event_type="R&I",
            source="platform",
            group_leader_id=estado["ev_sofia"],
        )
        db.session.add(satelite)
        db.session.commit()
        _garante(
            frente_ops.frente_do_evento(satelite)["frente"] == "social",
            "o satélite não leu o principal",
        )
        # Python = SQL em todos os eventos reais (principais), e a função = a regra de 16/11 sem frente gravada.
        pelo_sql = dict(
            db.session.query(CalendarEvent.id, frente_ops.frente_sql())
            .filter(CalendarEvent.group_leader_id.is_(None))
            .all()
        )
        divergentes = [
            ev.id
            for ev in CalendarEvent.query.filter(CalendarEvent.group_leader_id.is_(None)).all()
            if frente_ops.frente_do_evento(ev)["frente"] != pelo_sql[ev.id]
        ]
        _garante(not divergentes, f"Python × SQL divergem em {divergentes[:10]}")
        antigos = db.session.execute(
            text(f"SELECT id, {_REGRA_DE_16_11} AS regra FROM calendar_events WHERE frente IS NULL")
        ).fetchall()
        _garante(len(antigos) > 100, f"poucos eventos reais para comparar ({len(antigos)})")
        mudaram = [i for i, regra in antigos if pelo_sql.get(i, regra) != regra]
        _garante(not mudaram, f"a frente mudou em eventos sem frente gravada: {mudaram[:10]}")


def cen_14() -> None:
    from app.conversas import origem_ops

    # DEVE falhar: Figurino não grava a venda.
    r = _http(estado["fig"]).patch(
        f"/api/events/{estado['ev_sofia']}/comercial",
        json=_corpo_comercial(estado["ev_sofia"], frente="festas"),
    )
    _garante(r.status_code == 403, f"Figurino no comercial → {r.status_code}")
    r = _http(estado["fig"]).get(f"/api/events/{estado['ev_eva']}")
    _garante(r.status_code == 200, f"Figurino lê o evento → {r.status_code}")
    venda = r.get_json().get("venda")
    _garante(not venda, f"Figurino recebeu o bloco comercial {str(venda)[:120]}")
    r = _http(estado["ana"]).get(f"/api/events/{estado['ev_eva']}")
    origem = r.get_json()["venda"]["origem"]
    _garante(
        origem["conversa_id"] == estado["conv_e"] and origem["pode_abrir"] is True,
        f"origem Ana {origem}",
    )
    _garante(
        origem["contato"]["tipo"] == "anuncio" and origem["contato"]["conjunto"],
        f"contato {origem}",
    )
    r = _http(estado["fin"]).get(f"/api/events/{estado['ev_eva']}")
    _garante(
        r.get_json()["venda"]["origem"]["pode_abrir"] is False,
        "o Financeiro ganhou o link da conversa",
    )
    with app.app_context():
        _garante(
            origem_ops.origem_da_venda(db.session.get(CalendarEvent, estado["ev_sofia"])) is None,
            "venda sem conversa com origem",
        )


# ── História 5 — lead × campanha pelo id ───────────────────────────────────────────────────────────


def cen_15() -> None:
    from app.marketing import desempenho_ops

    hoje = now_sp().date()
    with app.app_context():
        run = MarketingAgentRun(
            run_id=f"{PREFIX}{uuid.uuid4().hex[:12]}",
            mode="local",
            window_start=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2),
            window_end=datetime.now(UTC).replace(tzinfo=None),
        )
        db.session.add(run)
        db.session.flush()
        for dia, nome in (
            (hoje - timedelta(days=1), f"{PREFIX}Nome Antigo"),
            (hoje, f"{PREFIX}Nome Novo"),
        ):
            db.session.add(
                MarketingCampaignMetric(
                    platform="Meta Ads",
                    campaign_id=f"{PREFIX}c-ren",
                    campaign_name=nome,
                    period_start=dia,
                    period_end=dia,
                    is_daily=True,
                    spend=Decimal("50.00"),
                    currency="BRL",
                    run_id=run.id,
                )
            )
        db.session.commit()
    _nova_ficha(
        f"{PREFIX}Lead pelo id",
        "5511963480081",
        utm_source="meta",
        utm_campaign=f"{PREFIX}Nome Antigo",
        utm_campaign_id=f"{PREFIX}c-ren",
    )
    _nova_ficha(
        f"{PREFIX}Lead pelo nome",
        "5511963480082",
        utm_source="meta",
        utm_campaign=f"{PREFIX}Nome Novo",
    )
    with app.app_context():
        resumo = desempenho_ops.desempenho_summary(hoje - timedelta(days=6), hoje)
    linhas = [c for c in resumo["campaigns"] if str(c.get("campaign_name", "")).startswith(PREFIX)]
    _garante(len(linhas) == 1, f"a campanha renomeada partiu em {len(linhas)} linhas: {linhas}")
    linha = linhas[0]
    _garante(linha["campaign_name"] == f"{PREFIX}Nome Novo", f"nome {linha['campaign_name']}")
    _garante(
        Decimal(str(linha["spend"])) == Decimal("100.00") and linha["leads"] == 2, f"linha {linha}"
    )


# ── Preparação e limpeza ───────────────────────────────────────────────────────────────────────────


def preparar() -> None:
    estado["ana"], estado["ana_id"] = _usuario("Ana", RoleName.COMERCIAL)
    estado["fig"], _ = _usuario("Fig", RoleName.FIGURINO)
    estado["fin"], _ = _usuario("Fin", RoleName.FINANCEIRO)
    estado["ficha_a"] = _nova_ficha(f"{PREFIX}Ana Souza", WA_A)
    estado["ficha_c"] = _nova_ficha(f"{PREFIX}Carla Site", WA_C)
    estado["ficha_f"] = _nova_ficha(f"{PREFIX}Fabi Recorrente", WA_F)


def limpar() -> None:
    db.session.rollback()
    eventos = "SELECT id FROM calendar_events WHERE google_event_id LIKE :p OR title LIKE :p"
    for tabela in (
        "commission_payments",
        "event_logs",
        "event_roles",
        "event_clients",
        "event_invoices",
    ):
        db.session.execute(
            text(f"DELETE FROM {tabela} WHERE event_id IN ({eventos})"), {"p": f"{PREFIX}%"}
        )
    db.session.execute(
        text(f"UPDATE calendar_events SET group_leader_id = NULL WHERE id IN ({eventos})"),
        {"p": f"{PREFIX}%"},
    )
    db.session.execute(
        text("DELETE FROM calendar_events WHERE google_event_id LIKE :p OR title LIKE :p"),
        {"p": f"{PREFIX}%"},
    )
    db.session.execute(
        text("DELETE FROM orcamento_history WHERE client_name LIKE :p"), {"p": f"{PREFIX}%"}
    )
    ids = [
        r[0]
        for r in db.session.execute(
            text("SELECT id FROM conversas WHERE contato_id = ANY(:c)"), {"c": CONTATOS}
        )
    ]
    if ids:
        db.session.execute(
            text("DELETE FROM notifications WHERE entity_type='conversa' AND entity_id = ANY(:i)"),
            {"i": ids},
        )
    db.session.execute(
        text(
            "DELETE FROM origem_codigos WHERE gclid LIKE :p OR utm_campaign LIKE :p OR conversa_id = ANY(:i)"
        ),
        {"p": f"{PREFIX}%", "i": ids or [0]},
    )
    db.session.execute(text("DELETE FROM conversas WHERE contato_id = ANY(:c)"), {"c": CONTATOS})
    db.session.execute(
        text("DELETE FROM whatsapp_avisos WHERE corpo LIKE :p"), {"p": f"%{NUMERO_ID}%"}
    )
    db.session.execute(
        text("DELETE FROM anuncios_meta WHERE anuncio_id LIKE :p"), {"p": f"{PREFIX}%"}
    )
    rids = [
        r[0]
        for r in db.session.execute(
            text("SELECT id FROM form_responses WHERE contact_name LIKE :p"), {"p": f"{PREFIX}%"}
        )
    ]
    for rid in rids:
        db.session.execute(
            text("DELETE FROM notifications WHERE entity_type='form_response' AND entity_id=:i"),
            {"i": rid},
        )
        db.session.execute(
            text("UPDATE origem_codigos SET form_response_id = NULL WHERE form_response_id=:i"),
            {"i": rid},
        )
        db.session.execute(text("DELETE FROM form_responses WHERE id = :i"), {"i": rid})
    db.session.execute(
        text("DELETE FROM marketing_campaign_metrics WHERE campaign_id LIKE :p"),
        {"p": f"{PREFIX}%"},
    )
    db.session.execute(
        text("DELETE FROM marketing_agent_runs WHERE run_id LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text(
            "DELETE FROM clients WHERE phone = ANY(:t) OR name LIKE :p OR phone LIKE '55119634800%'"
        ),
        {"t": TELEFONES, "p": f"{PREFIX}%"},
    )
    usuarios = User.query.filter(User.email.like(f"{PREFIX}%@manto.local")).all()
    if usuarios:
        db.session.execute(
            text("DELETE FROM notifications WHERE user_id = ANY(:ids)"),
            {"ids": [u.id for u in usuarios]},
        )
    for user in usuarios:
        user.roles.clear()
        db.session.delete(user)
    db.session.commit()
    sobras = _no_banco(
        "SELECT (SELECT count(*) FROM conversas WHERE contato_id = ANY(:c)) + "
        "(SELECT count(*) FROM clients WHERE phone = ANY(:t)) + "
        "(SELECT count(*) FROM origem_codigos WHERE gclid LIKE :p OR utm_campaign LIKE :p) + "
        "(SELECT count(*) FROM calendar_events WHERE google_event_id LIKE :p OR title LIKE :p)",
        c=CONTATOS,
        t=TELEFONES,
        p=f"{PREFIX}%",
    )[0]
    _garante(sobras == 0, f"sobraram {sobras} registros de teste")


CENARIOS = [
    ("1. aviso com referral: o ctwa_clid fica no contato; a ficha ganha o id da campanha", cen_01),
    ("2. preenchimento retroativo da migration (mensagem corrompida e sem clid)", cen_02),
    ("3. consulta à Meta pede e grava o conjunto", cen_03),
    ("4. POST /api/origem/codigo; sem marcador (DEVE falhar)", cen_04),
    ("5. formulário público com o código: linha na mensagem e resposta ligada", cen_05),
    ("6. mensagem com o código: liga, contato 'site', ficha 'Site'", cen_06),
    ("7. código usado, vencido e inexistente não ligam (DEVE falhar)", cen_07),
    ("8. orçamento pela conversa guarda a conversa e o contato; o seguinte não troca", cen_08),
    (
        "9. cliente recorrente: cada venda com o seu anúncio; janela de 90 dias; nunca pela ficha",
        cen_09,
    ),
    ("10. evento herda do orçamento; trocar e desligar levam junto", cen_10),
    ("11. criação com conversa_id; conversa inexistente (DEVE falhar)", cen_11),
    ("12. frente na aba Comercial e na criação (recusas DEVEM falhar)", cen_12),
    ("13. função da frente: sugestão, satélite, Python = SQL, regra de 16/11 intacta", cen_13),
    ("14. RBAC: Figurino no comercial (DEVE falhar); origem só no bloco comercial", cen_14),
    ("15. Desempenho: campanha renomeada numa linha; lead casado pelo id", cen_15),
]


def main() -> int:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        banco = db.session.execute(text("SELECT current_database()")).scalar()
        _garante(banco == "manto_348", f"o verify só roda no espelho manto_348 (veio {banco})")
        limpar()
        preparar()
    print("Feature 348 — Origem completa, contra manto_348")
    try:
        for nome, fn in CENARIOS:
            cenario(nome, fn)
    finally:
        with app.app_context():
            cenario("16. limpeza", limpar)
        for nome, real in _REAIS["wc"].items():
            setattr(_wc, nome, real)
        _mac.consultar_anuncio = _REAIS["mac"]["consultar_anuncio"]
        shutil.rmtree(PASTA_MIDIA, ignore_errors=True)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK · escapes de rede: {len(_ESCAPES)}")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) and not _ESCAPES else 1


if __name__ == "__main__":
    sys.exit(main())
