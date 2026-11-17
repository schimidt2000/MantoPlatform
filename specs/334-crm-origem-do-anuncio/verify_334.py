"""Verificação da feature 334 — De qual anúncio veio cada cliente.

Os cenários da tabela da spec, contra o `manto_local`. Nada sai da máquina: os clientes da Meta viram dublês (o envio
do WhatsApp e do Instagram, o perfil e a consulta do anúncio, que conta as chamadas e pode recusar ou responder que o
anúncio não existe), e um disjuntor de rede derruba qualquer conexão que não seja o Postgres local. As conversas nascem
pelo webhook assinado, com o `referral` que a Meta manda.

Tudo de teste leva `v334-`. Rodar (PowerShell, na raiz)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
    $env:PYTHONUTF8 = '1'; .venv\\Scripts\\python.exe specs/334-crm-origem-do-anuncio/verify_334.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import socket
import sys
import tempfile
import time
import traceback
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from datetime import time as hora
from decimal import Decimal
from pathlib import Path

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
        raise OSError(f"verify 334: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 334: conexão de saída bloqueada para {_host_de(endereco)}")
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

from app import create_app, db, limiter  # noqa: E402
from app.constants import TZ_SP, RoleName  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    Client,
    EventClient,
    MarketingAgentRun,
    MarketingCampaignMetric,
    OrcamentoHistory,
    Role,
    User,
)

PREFIX = "v334-"
SENHA = "verify-334-senha"
SEGREDO = "segredo-do-app-v334"
NUMERO_ID = "v334-phone"
NUMERO_MANTO = "5511900000334"
CONTA_IG = "v334-conta-ig"
PAGINA_IG = "v334-pagina"
WA_A = "5511963340001"  # ficha sem origem; anúncio 1, depois o 2 (repescagem)
WA_B = "5511963340002"  # o mesmo anúncio 1, sem ficha
WA_C = "5511963340003"  # orgânica: a ficha nasce no envio do orçamento
WA_D = "5511963340004"  # ficha antiga sem origem, ligada sozinha pelo telefone
WA_E = "5511963340005"  # anúncio 4: a Meta recusa, depois responde
WA_F = "5511963340006"  # anúncio 6 com o ambiente travado
WA_G = "5511963340007"  # clique numa publicação
WA_H = "5511963340008"  # anúncio 5, que não existe na Meta
IG_A = "3343340000000001"  # abertura pelo anúncio 3, sem mensagem
IG_B = "3343340000000002"  # orgânica no Instagram
IG_C = "3343340000000003"  # anúncio 7 sem token de consulta
WA_I = "5511963340009"  # ficha do Kommo com origem e campanha próprias, chega pelo anúncio 8
WA_J = "5511963340010"  # anúncio 1 sem ficha; o vendedor liga a uma ficha existente
WA_K = "5511963340011"  # anúncio 1 sem ficha; a ficha nasce depois e liga pelo telefone
WA_L = "5511963340012"  # anúncio 9: a consulta quebra de um jeito inesperado
CONTATOS = [
    WA_A,
    WA_B,
    WA_C,
    WA_D,
    WA_E,
    WA_F,
    WA_G,
    WA_H,
    IG_A,
    IG_B,
    IG_C,
    WA_I,
    WA_J,
    WA_K,
    WA_L,
]
TEL_IG_A = "5511963340091"
TEL_IG_B = "5511963340092"
TEL_J = "5511963340093"
TEL_NOITE = "5511963340094"  # lead das 22 h de ontem (São Paulo), já "hoje" em UTC
TEL_KOMMO = "5511963340095"  # do Kommo sem data: fora dos leads
TELEFONES = [
    WA_A, WA_B, WA_C, WA_D, WA_E, WA_F, WA_G, WA_H, WA_I, WA_J, WA_K, WA_L,
    TEL_IG_A, TEL_IG_B, TEL_J, TEL_NOITE, TEL_KOMMO,
]  # fmt: skip
AD = {n: f"{PREFIX}ad-{n}" for n in range(1, 10)}
CAMPANHA_KOMMO = f"{PREFIX}Campanha do Kommo"
TOKEN_ANUNCIOS = "token-dos-anuncios-v334"
CAMPANHA_FESTA = f"{PREFIX}Festa infantil SP"
CAMPANHA_REPESCAGEM = f"{PREFIX}Repescagem"
CAMPANHAS = {
    AD[1]: CAMPANHA_FESTA,
    AD[2]: CAMPANHA_REPESCAGEM,
    AD[3]: CAMPANHA_FESTA,
    AD[4]: CAMPANHA_FESTA,
    AD[6]: CAMPANHA_FESTA,
    AD[7]: CAMPANHA_FESTA,
    AD[8]: CAMPANHA_FESTA,
}
PASTA_MIDIA = tempfile.mkdtemp(prefix="v334-midia-")

app = create_app()
app.config["TESTING"] = True
app.config.update(
    WHATSAPP_ACCESS_TOKEN="token-falso-v334",
    WHATSAPP_APP_SECRET=SEGREDO,
    WHATSAPP_VERIFY_TOKEN="verifica-v334",
    WHATSAPP_PHONE_NUMBER_ID=NUMERO_ID,
    WHATSAPP_AVISO_SINCRONO=True,
    WHATSAPP_SUPPRESS_SEND=False,
    INSTAGRAM_ACCESS_TOKEN="token-ig-v334",
    INSTAGRAM_PAGE_ID=PAGINA_IG,
    INSTAGRAM_ACCOUNT_ID=CONTA_IG,
    META_ANUNCIOS_TOKEN="",
    CONVERSAS_MEDIA_FOLDER=PASTA_MIDIA,
    WEB_PUSH_SUPPRESS=True,
)
limiter.enabled = False

# ── Dublês da Meta ───────────────────────────────────────────────────────────────────────────────
import app.integracoes.instagram_client as _ic  # noqa: E402
import app.integracoes.meta_anuncios_client as _mac  # noqa: E402
import app.integracoes.whatsapp_client as _wc  # noqa: E402

_REAIS = {
    "ic": {n: getattr(_ic, n) for n in ("enviar", "enviar_arquivo", "perfil")},
    "wc": {n: getattr(_wc, n) for n in ("enviar", "subir_midia", "marcar_lida")},
    "mac": {"consultar_anuncio": _mac.consultar_anuncio},
}


class MetaFalsa:
    """Responde como a Meta e registra as consultas de anúncio (o resto só responde)."""

    def __init__(self) -> None:
        self.consultas: list[str] = []
        self.tokens: list[str] = []
        self.recusar: set[str] = set()
        self.quebrar: set[str] = set()
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

    def ig_enviar(self, conexao, corpo):
        return {"id": self._id("mid-")}

    def ig_arquivo(self, conexao, destino, tipo, dados, mime, nome, extras=None):
        return {"id": self._id("mid-")}

    def perfil(self, conexao, igsid):
        return {"nome": f"{PREFIX}Perfil {igsid[-1]}", "usuario": f"v334.perfil{igsid[-1]}"}

    def anuncio(self, conexao, anuncio_id):
        self.consultas.append(anuncio_id)
        self.tokens.append(conexao.token)
        _garante(conexao.token, "consulta sem token")
        if anuncio_id in self.quebrar:
            raise RuntimeError("resposta inesperada (dublê)")
        if anuncio_id in self.recusar:
            # O código 100/33 é o que a Graph devolve sem acesso à conta de anúncios — e também para o
            # que não existe: não pode virar definitivo.
            raise _wc.WhatsappRecusou(
                "Unsupported get request. Object does not exist, cannot be loaded due to missing "
                "permissions (dublê)",
                status=400,
                code=100,
                subcode=33,
            )
        if anuncio_id not in CAMPANHAS:
            raise _wc.WhatsappRecusou("Not found (dublê)", status=404, code=803)
        return {
            "nome": f"Anúncio {anuncio_id}",
            "campanha_id": f"c-{anuncio_id}",
            "campanha_nome": CAMPANHAS[anuncio_id],
        }


meta = MetaFalsa()
_wc.enviar, _wc.subir_midia, _wc.marcar_lida = meta.wa_enviar, meta.wa_subir, meta.wa_lida
_ic.enviar, _ic.enviar_arquivo, _ic.perfil = meta.ig_enviar, meta.ig_arquivo, meta.perfil
_mac.consultar_anuncio = meta.anuncio

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchone()


def _no_banco_todas(sql: str, **params):
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _no_banco_escrever(sql: str, **params) -> None:
    with _engine_externo.begin() as conn:
        conn.execute(text(sql), params)


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


def _chamar(email: str, metodo: str, url: str, corpo: dict | None = None):
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
        _garante(r.status_code == 200, f"login {email} → {r.status_code}")
        return getattr(c, metodo)(url, json=corpo) if corpo is not None else getattr(c, metodo)(url)


def _assinado(corpo: dict, rota: str) -> None:
    bruto = json.dumps(corpo).encode()
    assinatura = "sha256=" + hmac.new(SEGREDO.encode(), bruto, hashlib.sha256).hexdigest()
    with app.test_client() as c:
        r = c.post(
            rota,
            data=bruto,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": assinatura},
        )
    _garante(r.status_code == 200, f"aviso → {r.status_code}")


def _wa(wa_id: str, wamid: str, nome: str, referral: dict | None = None) -> int:
    """A cliente escreve no WhatsApp (com o `referral` de quem veio do anúncio)."""
    mensagem = {
        "from": wa_id,
        "id": f"wamid.{PREFIX}{wamid}",
        "timestamp": str(int(time.time())),
        "type": "text",
        "text": {"body": "Vi o anúncio, quero saber o preço"},
    }
    if referral:
        mensagem["referral"] = referral
    valor = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": NUMERO_MANTO, "phone_number_id": NUMERO_ID},
        "contacts": [{"profile": {"name": f"{PREFIX}{nome}"}, "wa_id": wa_id}],
        "messages": [mensagem],
    }
    corpo = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "v334-waba", "changes": [{"field": "messages", "value": valor}]}],
    }
    _assinado(corpo, "/api/webhooks/whatsapp")
    return _no_banco("SELECT id FROM conversas WHERE contato_id=:c", c=wa_id).id


def _ref_wa(anuncio: str, titulo: str, tipo: str = "ad") -> dict:
    return {
        "source_url": f"https://fb.me/{anuncio}",
        "source_id": anuncio,
        "source_type": tipo,
        "headline": titulo,
        "body": "Personagens para festa infantil",
        "media_type": "image",
        "ctwa_clid": f"clid-{anuncio}",
    }


def _ig(item: dict) -> None:
    item = {"timestamp": int(time.time() * 1000), **item}
    _assinado(
        {"object": "instagram", "entry": [{"id": CONTA_IG, "time": 1, "messaging": [item]}]},
        "/api/webhooks/instagram",
    )


def _ref_ig(anuncio: str, titulo: str) -> dict:
    return {
        "ref": "v334",
        "ad_id": anuncio,
        "source": "ADS",
        "type": "OPEN_THREAD",
        "ads_context_data": {"ad_title": titulo, "photo_url": "https://x.invalid/foto.jpg"},
    }


def _conversa(contato: str):
    return _no_banco("SELECT id, client_id FROM conversas WHERE contato_id=:c", c=contato)


def _contatos(conversa_id: int):
    return _no_banco_todas(
        "SELECT tipo, anuncio_id, titulo, link FROM conversa_anuncios WHERE conversa_id=:c ORDER BY momento, id",
        c=conversa_id,
    )


def _ficha(client_id: int):
    return _no_banco(
        "SELECT lead_origin, utm_source, utm_medium, utm_campaign, anuncio_origem_id, anuncio_origem_em, "
        "anuncio_recente_id, anuncio_recente_em FROM clients WHERE id=:i",
        i=client_id,
    )


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
            event_date=(datetime.now(UTC) + timedelta(days=30)).date().isoformat(),
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


# ── Cenários ───────────────────────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    conv = _wa(WA_A, "a-1", "Ana", _ref_wa(AD[1], "Festa com personagens"))
    contatos = _contatos(conv)
    _garante(len(contatos) == 1 and contatos[0].tipo == "anuncio", f"contatos {contatos}")
    _garante(
        contatos[0].anuncio_id == AD[1] and contatos[0].titulo == "Festa com personagens",
        f"{contatos[0]}",
    )
    _garante(contatos[0].link == f"https://fb.me/{AD[1]}", f"link {contatos[0].link}")
    _garante(meta.consultas == [AD[1]], f"consultas {meta.consultas}")
    anuncio = _no_banco(
        "SELECT campanha_nome, nome FROM anuncios_meta WHERE anuncio_id=:a", a=AD[1]
    )
    _garante(anuncio is not None and anuncio.campanha_nome == CAMPANHA_FESTA, f"anúncio {anuncio}")
    f = _ficha(estado["ficha_a"])
    _garante(
        (f.lead_origin, f.utm_source, f.utm_medium, f.utm_campaign)
        == ("Anúncio do WhatsApp", "meta", "anuncio", CAMPANHA_FESTA),
        f"origem {f}",
    )
    _garante(
        f.anuncio_origem_id == AD[1] and f.anuncio_recente_id == AD[1], f"primeiro/recente {f}"
    )
    estado["conv_a"] = conv


def cen_02() -> None:
    _wa(WA_A, "a-1", "Ana", _ref_wa(AD[1], "Festa com personagens"))  # reenvio do mesmo aviso
    _garante(len(_contatos(estado["conv_a"])) == 1, "o reenvio duplicou o contato")
    conv_b = _wa(WA_B, "b-1", "Bruna", _ref_wa(AD[1], "Festa com personagens"))
    _garante(len(_contatos(conv_b)) == 1, "a outra conversa não registrou")
    _garante(meta.consultas == [AD[1]], f"consultou de novo {meta.consultas}")
    estado["conv_b"] = conv_b


def cen_03() -> None:
    time.sleep(1.1)  # o timestamp do aviso é em segundos: o segundo anúncio é mais novo
    _wa(WA_A, "a-2", "Ana", _ref_wa(AD[2], "Volte a festejar"))
    f = _ficha(estado["ficha_a"])
    _garante(f.anuncio_recente_id == AD[2], f"o mais recente não mudou {f}")
    _garante(
        f.anuncio_origem_id == AD[1] and f.utm_campaign == CAMPANHA_FESTA, f"o primeiro mudou {f}"
    )
    _garante(f.anuncio_recente_em > f.anuncio_origem_em, "as datas não andaram")


def cen_04() -> None:
    _ig(
        {
            "sender": {"id": IG_A},
            "recipient": {"id": CONTA_IG},
            "referral": _ref_ig(AD[3], "Festa no Instagram"),
        }
    )
    conv = _conversa(IG_A)
    _garante(conv is not None, "a abertura pelo anúncio não criou a conversa")
    contatos = _contatos(conv.id)
    _garante(len(contatos) == 1 and contatos[0].anuncio_id == AD[3], f"contatos IG {contatos}")
    _ig(
        {
            "sender": {"id": IG_A},
            "recipient": {"id": CONTA_IG},
            "message": {"mid": f"{PREFIX}ig-a1", "text": "Oi!"},
        }
    )
    r = _chamar(
        estado["ana"],
        "post",
        f"/api/conversas/{conv.id}/ficha",
        {"nome": f"{PREFIX}Iara", "telefone": TEL_IG_A},
    )
    _garante(r.status_code == 200, f"ligar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    ficha = _conversa(IG_A).client_id
    f = _ficha(ficha)
    _garante(
        f.lead_origin == "Anúncio do Instagram" and f.anuncio_origem_id == AD[3], f"ficha IG {f}"
    )
    _garante(f.utm_campaign == CAMPANHA_FESTA, f"campanha IG {f.utm_campaign}")


def cen_05() -> None:
    conv_c = _wa(WA_C, "c-1", "Carla")
    r = _chamar(
        estado["ana"],
        "post",
        f"/api/conversas/{conv_c}/orcamento",
        {"orcamento_id": estado["orc_c"], "chave_envio": str(uuid.uuid4())},
    )
    _garante(r.status_code == 201, f"envio C → {r.status_code} {r.get_data(as_text=True)[:200]}")
    f = _ficha(_conversa(WA_C).client_id)
    _garante(f.lead_origin == "WhatsApp" and f.utm_campaign is None, f"orgânica WhatsApp {f}")
    _ig(
        {
            "sender": {"id": IG_B},
            "recipient": {"id": CONTA_IG},
            "message": {"mid": f"{PREFIX}ig-b1", "text": "Oi"},
        }
    )
    conv_ig = _conversa(IG_B).id
    r = _chamar(
        estado["ana"],
        "post",
        f"/api/conversas/{conv_ig}/ficha",
        {"nome": f"{PREFIX}Bia", "telefone": TEL_IG_B},
    )
    _garante(r.status_code == 200, f"ligar IG B → {r.status_code}")
    _garante(_ficha(_conversa(IG_B).client_id).lead_origin == "Instagram", "orgânica Instagram")
    _wa(WA_D, "d-1", "Dora")
    _garante(_conversa(WA_D).client_id == estado["ficha_d"], "a ficha antiga não ligou")
    _garante(_ficha(estado["ficha_d"]).lead_origin is None, "a ficha antiga ganhou o canal")


def _varrer() -> None:
    """Uma passada da varredura só com a reconsulta: refazer avisos e mídias de outras linhas do
    `manto_local` sairia para a rede, e o alerta de espera mexe no sino de gente de verdade."""
    from app.conversas import equipe_ops, varredura

    reais = (varredura.reprocessar_avisos, varredura.reprocessar_midias, equipe_ops.alertar_esperas)
    varredura.reprocessar_avisos = varredura.reprocessar_midias = equipe_ops.alertar_esperas = dict
    try:
        with app.app_context():
            resumo = varredura.ciclo_de_varredura()
    finally:
        varredura.reprocessar_avisos, varredura.reprocessar_midias, equipe_ops.alertar_esperas = (
            reais
        )
    _garante("anuncios_consultados" in resumo, f"a varredura não passou pela reconsulta {resumo}")


def cen_06() -> None:
    meta.recusar.add(AD[4])
    _wa(WA_E, "e-1", "Elisa", _ref_wa(AD[4], "Personagens"))
    anuncio = _no_banco(
        "SELECT campanha_nome, erro, definitivo FROM anuncios_meta WHERE anuncio_id=:a", a=AD[4]
    )
    _garante(
        anuncio is not None and anuncio.campanha_nome is None and anuncio.erro, f"recusa {anuncio}"
    )
    _garante(not anuncio.definitivo, "a recusa de permissão virou definitiva")
    f = _ficha(estado["ficha_e"])
    _garante(
        f.lead_origin == "Anúncio do WhatsApp" and f.utm_campaign is None, f"ficha sem campanha {f}"
    )
    # O dia seguinte: a permissão chegou e a varredura tenta de novo.
    meta.recusar.discard(AD[4])
    _varrer()
    _garante(meta.consultas.count(AD[4]) == 1, "a varredura não esperou o prazo")
    _no_banco_escrever(
        "UPDATE anuncios_meta SET consultado_em = consultado_em - interval '25 hours' WHERE anuncio_id=:a",
        a=AD[4],
    )
    _varrer()
    anuncio = _no_banco(
        "SELECT campanha_nome, erro FROM anuncios_meta WHERE anuncio_id=:a", a=AD[4]
    )
    _garante(
        anuncio.campanha_nome == CAMPANHA_FESTA and anuncio.erro is None, f"reconsulta {anuncio}"
    )
    _garante(
        _ficha(estado["ficha_e"]).utm_campaign == CAMPANHA_FESTA, "a campanha não chegou à ficha"
    )
    # Anúncio que não existe na Meta: definitivo, sem nova tentativa.
    _wa(WA_H, "h-1", "Helena", _ref_wa(AD[5], "Apagado"))
    apagado = _no_banco("SELECT definitivo FROM anuncios_meta WHERE anuncio_id=:a", a=AD[5])
    _garante(apagado is not None and apagado.definitivo, f"404 {apagado}")
    _no_banco_escrever(
        "UPDATE anuncios_meta SET consultado_em = consultado_em - interval '25 hours' WHERE anuncio_id=:a",
        a=AD[5],
    )
    _varrer()
    _garante(meta.consultas.count(AD[5]) == 1, "tentou de novo o anúncio que não existe")


def cen_07() -> None:
    antes = len(meta.consultas)
    app.config["WHATSAPP_SUPPRESS_SEND"] = True
    try:
        conv_f = _wa(WA_F, "f-1", "Fabi", _ref_wa(AD[6], "Travado"))
    finally:
        app.config["WHATSAPP_SUPPRESS_SEND"] = False
    _garante(len(_contatos(conv_f)) == 1, "o contato travado não ficou registrado")
    _garante(len(meta.consultas) == antes, "consultou a Meta com o ambiente travado")
    app.config["WHATSAPP_ACCESS_TOKEN"] = ""
    try:
        _ig(
            {
                "sender": {"id": IG_C},
                "recipient": {"id": CONTA_IG},
                "referral": _ref_ig(AD[7], "Sem token"),
            }
        )
    finally:
        app.config["WHATSAPP_ACCESS_TOKEN"] = "token-falso-v334"
    _garante(len(_contatos(_conversa(IG_C).id)) == 1, "o contato sem token não ficou registrado")
    _garante(len(meta.consultas) == antes, "consultou a Meta sem token")


def cen_08() -> None:
    # A Ana vira ficha antiga (entrou há 60 dias): o anúncio 2 de hoje é um retorno da repescagem, e o
    # evento criado agora é dele.
    _no_banco_escrever(
        "UPDATE clients SET created_at = now() - interval '60 days' WHERE id=:i",
        i=estado["ficha_a"],
    )
    ontem_22h = datetime.combine(date.today() - timedelta(days=1), hora(22))
    with app.app_context():
        evento = CalendarEvent(
            google_event_id=f"{PREFIX}evento-{uuid.uuid4().hex[:8]}",
            title=f"{PREFIX}Festa da Ana",
            start_at=datetime.now() + timedelta(days=30),
            source="platform",
        )
        db.session.add(evento)
        db.session.flush()
        db.session.add(EventClient(event_id=evento.id, client_id=estado["ficha_a"]))
        db.session.commit()
    # Fora dos leads de hoje: a das 22 h de ontem em São Paulo (01 h de hoje em UTC) e a do Kommo sem data.
    atribuida = {"utm_source": "meta", "utm_medium": "anuncio", "utm_campaign": CAMPANHA_FESTA}
    _nova_ficha(
        f"{PREFIX}Noite",
        TEL_NOITE,
        source="conversa",
        created_at=ontem_22h.replace(tzinfo=TZ_SP).astimezone(UTC).replace(tzinfo=None),
        **atribuida,
    )
    _nova_ficha(f"{PREFIX}Kommo sem data", TEL_KOMMO, source="kommo_import", **atribuida)
    hoje = date.today().isoformat()  # a máquina do verify está em São Paulo, como a janela da tela
    r = _chamar(estado["sa"], "get", f"/api/marketing/desempenho?start={hoje}&end={hoje}")
    _garante(r.status_code == 200, f"desempenho → {r.status_code} {r.get_data(as_text=True)[:200]}")
    campanhas = {c["campaign_name"]: c for c in r.get_json()["campaigns"]}
    festa, repescagem = campanhas.get(CAMPANHA_FESTA), campanhas.get(CAMPANHA_REPESCAGEM)
    _garante(festa is not None and repescagem is not None, f"campanhas {list(campanhas)}")
    # Leads de hoje na Festa: a ficha da Elisa (anúncio 4) e a do Instagram (anúncio 3).
    _garante(festa["leads"] == 2, f"leads da Festa {festa['leads']}")
    _garante(
        (repescagem.get("returns"), repescagem.get("return_events")) == (1, 1),
        f"retornos da Repescagem {repescagem.get('returns')}/{repescagem.get('return_events')}",
    )
    _garante(
        (festa.get("returns"), festa.get("return_events")) == (1, 1),
        f"retornos da Festa (o anúncio 1 da Ana) {festa.get('returns')}/{festa.get('return_events')}",
    )


def cen_09() -> None:
    conversa = _chamar(estado["ana"], "get", f"/api/conversas/{estado['conv_a']}").get_json()
    anuncio = conversa.get("anuncio")
    _garante(
        anuncio
        and anuncio["titulo"] == "Volte a festejar"
        and anuncio["campanha"] == CAMPANHA_REPESCAGEM,
        f"anúncio da conversa {anuncio}",
    )
    ficha = _chamar(estado["ana"], "get", f"/api/clientes/{estado['ficha_a']}").get_json()
    origem = ficha.get("origem") or {}
    _garante(origem.get("lead_origin") == "Anúncio do WhatsApp", f"origem {origem}")
    _garante(origem.get("campanha") == CAMPANHA_FESTA, f"campanha {origem}")
    _garante(
        (origem.get("primeiro") or {}).get("anuncio_id") == AD[1],
        f"primeiro {origem.get('primeiro')}",
    )
    _garante(
        (origem.get("recente") or {}).get("campanha") == CAMPANHA_REPESCAGEM,
        f"recente {origem.get('recente')}",
    )


def cen_10() -> None:
    antes = len(meta.consultas)
    conv = _wa(WA_G, "g-1", "Gabi", _ref_wa(f"{PREFIX}post-1", "Publicação", tipo="post"))
    contatos = _contatos(conv)
    _garante(
        len(contatos) == 1 and contatos[0].tipo == "publicacao", f"contato da publicação {contatos}"
    )
    novas = meta.consultas[antes:]
    _garante(f"{PREFIX}post-1" not in novas, "consultou a Meta para uma publicação")
    # Os anúncios que esperaram a trava e o token (cenário 7) saem na primeira consulta liberada.
    _garante(sorted(novas) == sorted([AD[6], AD[7]]), f"a fila não andou {novas}")
    f = _ficha(estado["ficha_g"])
    _garante(
        f.lead_origin is None and f.anuncio_origem_id is None,
        f"publicação virou origem de anúncio {f}",
    )


def cen_11() -> None:
    # (a) Ficha do Kommo com origem e campanha próprias chega pelo anúncio 8, ainda não consultado, com o
    # token próprio dos anúncios: origem e campanha ficam; o primeiro anúncio é registrado.
    app.config["META_ANUNCIOS_TOKEN"] = TOKEN_ANUNCIOS
    try:
        _wa(WA_I, "i-1", "Isis", _ref_wa(AD[8], "Personagens"))
    finally:
        app.config["META_ANUNCIOS_TOKEN"] = ""
    _garante(AD[8] in meta.consultas, "não consultou o anúncio 8")
    _garante(meta.tokens[meta.consultas.index(AD[8])] == TOKEN_ANUNCIOS, "não usou o token próprio")
    f = _ficha(estado["ficha_i"])
    _garante(
        (f.lead_origin, f.utm_source, f.utm_campaign) == ("Indicação", "kommo", CAMPANHA_KOMMO),
        f"a origem do Kommo mudou {f}",
    )
    _garante(f.anuncio_origem_id == AD[8], f"o primeiro anúncio não ficou {f}")
    # (b) Conversa com anúncio e sem ficha; o vendedor liga a uma ficha existente de outro telefone.
    conv_j = _wa(WA_J, "j-1", "Joana", _ref_wa(AD[1], "Festa com personagens"))
    _garante(_conversa(WA_J).client_id is None, "ligou sozinha a uma ficha")
    r = _chamar(
        estado["ana"], "post", f"/api/conversas/{conv_j}/ficha", {"client_id": estado["ficha_j"]}
    )
    _garante(r.status_code == 200, f"ligar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    f = _ficha(estado["ficha_j"])
    _garante(
        (f.lead_origin, f.utm_campaign, f.anuncio_origem_id)
        == ("Anúncio do WhatsApp", CAMPANHA_FESTA, AD[1]),
        f"ficha ligada à mão {f}",
    )
    # (c) A ficha nasce depois (cadastro com o telefone) e a próxima mensagem a liga sozinha.
    _wa(WA_K, "k-1", "Kátia", _ref_wa(AD[1], "Festa com personagens"))
    ficha_k = _nova_ficha(f"{PREFIX}Kátia", WA_K)
    _wa(WA_K, "k-2", "Kátia")
    _garante(_conversa(WA_K).client_id == ficha_k, "a ficha nova não ligou pelo telefone")
    f = _ficha(ficha_k)
    _garante(
        (f.lead_origin, f.utm_campaign) == ("Anúncio do WhatsApp", CAMPANHA_FESTA),
        f"ficha que chegou depois {f}",
    )
    # (d) A consulta quebra de um jeito inesperado: o aviso fecha processado e o anúncio volta depois.
    meta.quebrar.add(AD[9])
    _wa(WA_L, "l-1", "Lia", _ref_wa(AD[9], "Inesperado"))
    aviso = _no_banco(
        "SELECT estado FROM whatsapp_avisos WHERE corpo LIKE :p ORDER BY id DESC",
        p=f"%wamid.{PREFIX}l-1%",
    )
    _garante(aviso is not None and aviso.estado == "processado", f"aviso {aviso}")
    anuncio = _no_banco("SELECT erro, definitivo FROM anuncios_meta WHERE anuncio_id=:a", a=AD[9])
    _garante(anuncio.erro and not anuncio.definitivo, f"anúncio 9 {anuncio}")
    # (e) A campanha que não chegou à ficha (a corrida de dois workers) volta pela varredura.
    _no_banco_escrever("UPDATE clients SET utm_campaign = NULL WHERE id=:i", i=ficha_k)
    _varrer()
    _garante(_ficha(ficha_k).utm_campaign == CAMPANHA_FESTA, "a varredura não repôs a campanha")


def preparar() -> None:
    estado["ana"], estado["ana_id"] = _usuario("Ana", RoleName.COMERCIAL)
    estado["sa"], estado["sa_id"] = _usuario("SA", RoleName.SUPERADMIN)
    estado["ficha_a"] = _nova_ficha(f"{PREFIX}Ana Souza", WA_A)
    estado["ficha_d"] = _nova_ficha(f"{PREFIX}Dora Antiga", WA_D)
    estado["ficha_e"] = _nova_ficha(f"{PREFIX}Elisa", WA_E)
    estado["ficha_g"] = _nova_ficha(f"{PREFIX}Gabi", WA_G)
    estado["ficha_i"] = _nova_ficha(
        f"{PREFIX}Isis do Kommo",
        WA_I,
        source="kommo_import",
        kommo_created_at=datetime.now() - timedelta(days=90),
        lead_origin="Indicação",
        utm_source="kommo",
        utm_campaign=CAMPANHA_KOMMO,
    )
    estado["ficha_j"] = _nova_ficha(f"{PREFIX}Joana", TEL_J)
    estado["orc_c"] = _orcamento(f"{PREFIX}Carla Lima")
    with app.app_context():
        run = MarketingAgentRun(
            run_id=f"{PREFIX}{uuid.uuid4().hex[:12]}",
            mode="local",
            window_start=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
            window_end=datetime.now(UTC).replace(tzinfo=None),
        )
        db.session.add(run)
        db.session.flush()
        for nome in (CAMPANHA_FESTA, CAMPANHA_REPESCAGEM):
            db.session.add(
                MarketingCampaignMetric(
                    platform="Meta Ads",
                    campaign_id=f"c-{nome}",
                    campaign_name=nome,
                    period_start=date.today(),
                    period_end=date.today(),
                    is_daily=True,
                    spend=Decimal("100.00"),
                    currency="BRL",
                    run_id=run.id,
                )
            )
        db.session.commit()


def limpar() -> None:
    db.session.rollback()
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
    db.session.execute(text("DELETE FROM conversas WHERE contato_id = ANY(:c)"), {"c": CONTATOS})
    db.session.execute(
        text("DELETE FROM whatsapp_avisos WHERE corpo LIKE :p OR corpo LIKE :q"),
        {"p": f"%{NUMERO_ID}%", "q": f"%{CONTA_IG}%"},
    )
    db.session.execute(
        text("DELETE FROM anuncios_meta WHERE anuncio_id LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text("DELETE FROM marketing_campaign_metrics WHERE campaign_name LIKE :p"),
        {"p": f"{PREFIX}%"},
    )
    db.session.execute(
        text("DELETE FROM marketing_agent_runs WHERE run_id LIKE :p"), {"p": f"{PREFIX}%"}
    )
    eventos = "SELECT id FROM calendar_events WHERE google_event_id LIKE :p"
    db.session.execute(
        text(f"DELETE FROM event_clients WHERE event_id IN ({eventos})"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text("DELETE FROM calendar_events WHERE google_event_id LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text("DELETE FROM clients WHERE phone = ANY(:t) OR name LIKE :p"),
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
        "(SELECT count(*) FROM anuncios_meta WHERE anuncio_id LIKE :p)",
        c=CONTATOS,
        t=TELEFONES,
        p=f"{PREFIX}%",
    )[0]
    _garante(sobras == 0, f"sobraram {sobras} registros de teste")


CENARIOS = [
    ("1. mensagem do WhatsApp com anúncio: contato, campanha e ficha", cen_01),
    ("2. o mesmo aviso e o mesmo anúncio em outra conversa não duplicam", cen_02),
    ("3. a cliente volta por outro anúncio: muda só o mais recente", cen_03),
    ("4. Instagram: abertura pelo anúncio, depois a ficha", cen_04),
    ("5. orgânica: o canal na ficha nova; a ficha antiga fica como está", cen_05),
    (
        "6. a Meta recusa; a varredura no dia seguinte; o anúncio que não existe (DEVE falhar)",
        cen_06,
    ),
    ("7. ambiente travado e sem token (DEVE falhar)", cen_07),
    ("8. Desempenho: leads da conversa e retornos", cen_08),
    ("9. conversa e ficha na API", cen_09),
    ("10. clique numa publicação", cen_10),
    ("11. ficha com origem, ligada à mão e que chega depois; consulta que quebra", cen_11),
]


def main() -> int:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        limpar()
        preparar()
    print("Feature 334 — De qual anúncio veio cada cliente, contra manto_local")
    try:
        for nome, fn in CENARIOS:
            cenario(nome, fn)
    finally:
        with app.app_context():
            cenario("12. limpeza", limpar)
        for nome, real in _REAIS["ic"].items():
            setattr(_ic, nome, real)
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
