"""Verificação da feature 333 — Orçamento e formulário pela conversa, com o orçamento ligado à ficha.

Os cenários da tabela da spec, contra o `manto_local`. Nada sai da máquina: os clientes da Meta (WhatsApp e
Instagram) viram dublês que registram o que receberam, e um disjuntor de rede derruba qualquer conexão que não seja o
Postgres local. As conversas nascem pelo webhook assinado (a mensagem da cliente abre a janela), como em produção.

Tudo de teste leva `v333-`. Rodar (PowerShell, na raiz)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
    $env:PYTHONUTF8 = '1'; .venv\\Scripts\\python.exe specs/333-crm-orcamento-na-conversa/verify_333.py
"""

from __future__ import annotations

import hashlib
import hmac
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
        raise OSError(f"verify 333: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 333: conexão de saída bloqueada para {_host_de(endereco)}")
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
from app.config import PLATFORM_BASE_URL  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import Client, OrcamentoHistory, Role, User  # noqa: E402

PREFIX = "v333-"
SENHA = "verify-333-senha"
SEGREDO = "segredo-do-app-v333"
NUMERO_ID = "v333-phone"
NUMERO_MANTO = "5511900000333"
CONTA_IG = "v333-conta-ig"
PAGINA_IG = "v333-pagina"
WA_A = "5511963330001"  # com ficha (ligada sozinha pelo telefone)
WA_B = "5511963330002"  # sem ficha
WA_C = "5511963330003"  # ficha antiga gravada sem o nono dígito
WA_C_SEM_NOVE = "551163330003"
WA_D = "5511963330004"  # janela fechada, sem nome
WA_E = "5511963330005"  # ficha trocada à mão
WA_E_OUTRA = "5511963330055"
WA_F = "5511963330006"  # sem ficha; recebe orçamento que já é de outra ficha
WA_US = "14155550333"  # número dos EUA: 11 dígitos, sem o "55"
IG_A = "3333330000000001"
TELEFONE_IG = "5511963330009"
CONTATOS = [WA_A, WA_B, WA_C, WA_D, WA_E, WA_F, WA_US, IG_A]
TELEFONES = [
    WA_A,
    WA_B,
    WA_C,
    WA_C_SEM_NOVE,
    WA_D,
    WA_E,
    WA_E_OUTRA,
    WA_F,
    WA_US,
    "55" + WA_US,
    TELEFONE_IG,
]
PASTA_MIDIA = tempfile.mkdtemp(prefix="v333-midia-")

# Mensagem pronta com parágrafos, acentos e emoji: passa de 1.000 bytes (Instagram divide).
PARAGRAFO = (
    "Olá! Segue o orçamento da festa com a Manto Produções. Personagens caracterizados, recreação "
    "com brincadeiras e muita música para a criançada se divertir 🎉. "
)
MENSAGEM = "\n\n".join(f"*Parte {i}* — {PARAGRAFO * 2}".strip() for i in range(1, 6))

app = create_app()
app.config["TESTING"] = True
app.config.update(
    WHATSAPP_ACCESS_TOKEN="token-falso-v333",
    WHATSAPP_APP_SECRET=SEGREDO,
    WHATSAPP_VERIFY_TOKEN="verifica-v333",
    WHATSAPP_PHONE_NUMBER_ID=NUMERO_ID,
    WHATSAPP_AVISO_SINCRONO=True,
    WHATSAPP_SUPPRESS_SEND=False,
    INSTAGRAM_ACCESS_TOKEN="token-ig-v333",
    INSTAGRAM_PAGE_ID=PAGINA_IG,
    INSTAGRAM_ACCOUNT_ID=CONTA_IG,
    CONVERSAS_MEDIA_FOLDER=PASTA_MIDIA,
    WEB_PUSH_SUPPRESS=True,
)
limiter.enabled = False

# ── Dublês da Meta ───────────────────────────────────────────────────────────────────────────────
import app.integracoes.instagram_client as _ic  # noqa: E402
import app.integracoes.whatsapp_client as _wc  # noqa: E402

_REAIS = {
    "ic": {n: getattr(_ic, n) for n in ("enviar", "enviar_arquivo", "perfil")},
    "wc": {n: getattr(_wc, n) for n in ("enviar", "subir_midia", "marcar_lida")},
}


class MetaFalsa:
    """Responde como a Meta, registra cada chamada na ordem e nunca sai da máquina."""

    def __init__(self) -> None:
        self.saidas: list[dict] = []  # tudo o que saiu, na ordem: {"canal", "tipo", ...}
        self.seq = 0
        self.falhar_upload = False

    def _id(self, prefixo: str) -> str:
        self.seq += 1
        return f"{prefixo}{PREFIX}{self.seq}"

    def wa_enviar(self, conexao, corpo):
        self.saidas.append({"canal": "whatsapp", "tipo": corpo.get("type"), "corpo": corpo})
        return {"id": self._id("wamid."), "wa_id": corpo.get("to")}

    def wa_subir(self, conexao, dados, mime, nome):
        if self.falhar_upload:
            self.falhar_upload = False
            raise _wc.WhatsappRecusou("upload recusado (dublê)", status=400, code=131053)
        self.saidas.append(
            {"canal": "whatsapp", "tipo": "upload", "dados": dados, "mime": mime, "nome": nome}
        )
        return self._id("media-")

    def wa_lida(self, conexao, wamid):
        return None

    def ig_enviar(self, conexao, corpo):
        self.saidas.append({"canal": "instagram", "tipo": "texto", "corpo": corpo})
        return {"id": self._id("mid-")}

    def ig_arquivo(self, conexao, destino, tipo, dados, mime, nome, extras=None):
        self.saidas.append(
            {"canal": "instagram", "tipo": tipo, "dados": dados, "mime": mime, "nome": nome}
        )
        return {"id": self._id("mid-")}

    def perfil(self, conexao, igsid):
        return {"nome": f"{PREFIX}Perfil IG", "usuario": "v333.perfil"}


meta = MetaFalsa()
_wc.enviar, _wc.subir_midia, _wc.marcar_lida = meta.wa_enviar, meta.wa_subir, meta.wa_lida
_ic.enviar, _ic.enviar_arquivo, _ic.perfil = meta.ig_enviar, meta.ig_arquivo, meta.perfil

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


def _erro(r) -> dict:
    return (r.get_json() or {}).get("error") or {}


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


def _wa(wa_id: str, wamid: str, nome: str) -> int:
    """A cliente escreve no WhatsApp (abre a janela). Devolve o id da conversa."""
    mensagem = {
        "from": wa_id,
        "id": f"wamid.{PREFIX}{wamid}",
        "timestamp": str(int(time.time())),
        "type": "text",
        "text": {"body": "Quero um orçamento"},
    }
    valor = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": NUMERO_MANTO, "phone_number_id": NUMERO_ID},
        "contacts": [{"profile": {"name": f"{PREFIX}{nome}"}, "wa_id": wa_id}],
        "messages": [mensagem],
    }
    corpo = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "v333-waba", "changes": [{"field": "messages", "value": valor}]}],
    }
    _assinado(corpo, "/api/webhooks/whatsapp")
    return _no_banco("SELECT id FROM conversas WHERE contato_id=:c", c=wa_id).id


def _ig(igsid: str, mid: str) -> int:
    item = {
        "sender": {"id": igsid},
        "recipient": {"id": CONTA_IG},
        "timestamp": int(time.time() * 1000),
        "message": {"mid": f"{PREFIX}{mid}", "text": "Oi! Quanto fica a festa?"},
    }
    _assinado(
        {"object": "instagram", "entry": [{"id": CONTA_IG, "time": 1, "messaging": [item]}]},
        "/api/webhooks/instagram",
    )
    return _no_banco("SELECT id FROM conversas WHERE contato_id=:c", c=igsid).id


def _orcamento(sufixo: str, cliente: str, *, com_mensagem: bool = True) -> int:
    """Um orçamento salvo como a calculadora salva (o snapshot congelado com a mensagem pronta)."""
    from app.orcamento import quote_ops

    dono = db.session.get(User, estado["ana_id"])
    entry = OrcamentoHistory(
        user_id=dono.id,
        client_name=cliente,
        event_location=f"{PREFIX}Buffet {sufixo}, São Paulo",
        event_date=(datetime.now(UTC) + timedelta(days=40)).date().isoformat(),
        total_1h=Decimal("1800"),
        total_2h=Decimal("2400"),
        total_3h=Decimal("3000"),
        total_4h=Decimal("3500"),
        has_show=False,
    )
    db.session.add(entry)
    db.session.flush()
    if com_mensagem:
        quote = quote_ops.legacy_quote(entry)
        quote["message"] = MENSAGEM
        entry.result_snapshot = json.dumps(quote, ensure_ascii=False)
    db.session.commit()
    return entry.id


def _ficha(nome: str, telefone: str) -> int:
    client = Client(name=nome, phone=telefone, source="manual")
    db.session.add(client)
    db.session.commit()
    return client.id


def _enviar(email: str, conversa_id: int, orcamento_id: int, chave: str | None = None, **extra):
    corpo = {"orcamento_id": orcamento_id, "chave_envio": chave or str(uuid.uuid4()), **extra}
    return _chamar(email, "post", f"/api/conversas/{conversa_id}/orcamento", corpo)


def _envios(orcamento_id: int):
    return _no_banco_todas(
        "SELECT id, conversa_id, autor_id, chave_envio, texto_mensagem_id, pdf_mensagem_id "
        "FROM orcamento_envios WHERE orcamento_id=:o ORDER BY id",
        o=orcamento_id,
    )


def _ficha_da_conversa(conversa_id: int):
    return _no_banco("SELECT client_id, ficha_manual FROM conversas WHERE id=:i", i=conversa_id)


# ── Cenários ───────────────────────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    antes = len(meta.saidas)
    chave = str(uuid.uuid4())
    r = _enviar(estado["ana"], estado["conv_a"], estado["orc_1"], chave)
    _garante(r.status_code == 201, f"envio → {r.status_code} {r.get_data(as_text=True)[:300]}")
    saidas = meta.saidas[antes:]
    tipos = [s["tipo"] for s in saidas]
    _garante(tipos == ["text", "upload", "document"], f"ordem do que saiu {tipos}")
    _garante(saidas[0]["corpo"]["text"]["body"] == MENSAGEM, "o texto não é a mensagem pronta")
    _garante(
        saidas[1]["dados"][:4] == b"%PDF" and saidas[1]["mime"] == "application/pdf", "não é PDF"
    )
    _garante(
        saidas[2]["corpo"]["document"]["filename"] == f"Orcamento_Manto_{PREFIX}Ana_Souza.pdf",
        f"nome do PDF {saidas[2]['corpo']['document']}",
    )
    envios = _envios(estado["orc_1"])
    _garante(len(envios) == 1, f"{len(envios)} registros de envio")
    e = envios[0]
    _garante(e.autor_id == estado["ana_id"] and e.conversa_id == estado["conv_a"], f"registro {e}")
    _garante(e.texto_mensagem_id and e.pdf_mensagem_id, f"mensagens do registro {e}")
    orc = _no_banco("SELECT client_id FROM orcamento_history WHERE id=:i", i=estado["orc_1"])
    _garante(orc.client_id == estado["ficha_a"], f"orçamento ligado a {orc.client_id}")
    corpo = r.get_json()
    _garante(
        len(corpo["mensagens"]) == 2 and corpo["conversa"]["cliente"]["id"] == estado["ficha_a"],
        f"{corpo}",
    )
    estado["chave_1"] = chave


def cen_02() -> None:
    antes = len(meta.saidas)
    r = _enviar(estado["ana"], estado["conv_a"], estado["orc_1"], estado["chave_1"])
    _garante(r.status_code == 200, f"repetido → {r.status_code}")
    _garante(len(meta.saidas) == antes, f"{len(meta.saidas) - antes} chamadas à Meta no repetido")
    _garante(len(_envios(estado["orc_1"])) == 1, "o repetido criou outro registro")


def cen_03() -> None:
    r = _enviar(estado["bia"], estado["conv_b"], estado["orc_2"])
    _garante(r.status_code == 201, f"envio B → {r.status_code} {r.get_data(as_text=True)[:300]}")
    ficha = _no_banco("SELECT id, name, source FROM clients WHERE phone=:p", p=WA_B)
    _garante(ficha is not None, "a ficha não nasceu")
    _garante(ficha.name == f"{PREFIX}Bruna Lima" and ficha.source == "conversa", f"ficha {ficha}")
    _garante(_ficha_da_conversa(estado["conv_b"]).client_id == ficha.id, "a conversa não ligou")
    orc = _no_banco("SELECT client_id FROM orcamento_history WHERE id=:i", i=estado["orc_2"])
    _garante(orc.client_id == ficha.id, "o orçamento não ligou à ficha nova")
    estado["ficha_b"] = ficha.id
    legivel = _no_banco("SELECT phone_display FROM clients WHERE id=:i", i=ficha.id).phone_display
    _garante(legivel == "(11) 96333-0002", f"phone_display {legivel!r}")
    # Número estrangeiro (EUA, 11 dígitos): a ficha guarda o wa_id como veio, sem o "55".
    r = _enviar(estado["ana"], estado["conv_us"], estado["orc_7"])
    _garante(r.status_code == 201, f"envio US → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(
        _no_banco("SELECT id FROM clients WHERE phone=:p", p=WA_US) is not None, "ficha estrangeira"
    )
    _garante(
        _no_banco("SELECT id FROM clients WHERE phone=:p", p="55" + WA_US) is None,
        "pôs 55 no número",
    )
    # Ficha antiga sem o nono dígito, gravada depois de a conversa existir: o envio a reaproveita.
    with app.app_context():
        estado["ficha_c"] = _ficha(f"{PREFIX}Carla Antiga", WA_C_SEM_NOVE)
    r = _enviar(estado["ana"], estado["conv_c"], estado["orc_3"])
    _garante(r.status_code == 201, f"envio C → {r.status_code}")
    _garante(
        _ficha_da_conversa(estado["conv_c"]).client_id == estado["ficha_c"], "não reaproveitou"
    )
    _garante(
        _no_banco("SELECT id FROM clients WHERE phone=:p", p=WA_C) is None, "criou ficha repetida"
    )


def cen_04() -> None:
    antes = len(meta.saidas)
    sem = _enviar(estado["ana"], estado["conv_ig"], estado["orc_4"])
    _garante(
        sem.status_code == 422 and "cliente" in (_erro(sem).get("fields") or {}),
        f"Instagram sem ficha → {sem.status_code} {_erro(sem)}",
    )
    _garante(len(meta.saidas) == antes and not _envios(estado["orc_4"]), "saiu algo sem a ficha")
    r = _enviar(
        estado["ana"],
        estado["conv_ig"],
        estado["orc_4"],
        cliente={"nome": f"{PREFIX}Iara Ramos", "telefone": "(11) 96333-0009"},
    )
    _garante(r.status_code == 201, f"Instagram → {r.status_code} {r.get_data(as_text=True)[:300]}")
    saidas = meta.saidas[antes:]
    textos = [s["corpo"]["message"]["text"] for s in saidas if s["tipo"] == "texto"]
    _garante(len(textos) >= 2, f"{len(textos)} partes")
    _garante(all(len(t.encode("utf-8")) <= 1000 for t in textos), "parte acima de 1.000 bytes")
    junta = re.sub(r"\s+", " ", " ".join(textos)).strip()
    _garante(junta == re.sub(r"\s+", " ", MENSAGEM).strip(), "as partes não remontam a mensagem")
    _garante(
        saidas[-1]["tipo"] != "texto" and saidas[-1]["mime"] == "application/pdf",
        "o PDF não veio por último",
    )
    ficha = _no_banco("SELECT id, source FROM clients WHERE phone=:p", p=TELEFONE_IG)
    _garante(ficha is not None and ficha.source == "conversa", f"ficha do Instagram {ficha}")
    _garante(_ficha_da_conversa(estado["conv_ig"]).client_id == ficha.id, "a conversa não ligou")


def cen_05() -> None:
    _no_banco_escrever(
        "UPDATE conversas SET ultima_recebida_em = now() at time zone 'utc' - interval '2 days' WHERE id=:i",
        i=estado["conv_d"],
    )
    antes = len(meta.saidas)
    fechada = _enviar(estado["ana"], estado["conv_d"], estado["orc_5"])
    _garante(
        fechada.status_code == 409 and _erro(fechada).get("codigo") == "janela_fechada",
        f"janela fechada → {fechada.status_code} {_erro(fechada)}",
    )
    app.config["WHATSAPP_SUPPRESS_SEND"] = True
    try:
        travado = _enviar(estado["ana"], estado["conv_a"], estado["orc_5"])
    finally:
        app.config["WHATSAPP_SUPPRESS_SEND"] = False
    _garante(
        travado.status_code == 409 and _erro(travado).get("codigo") == "envio_travado",
        f"travado → {travado.status_code} {_erro(travado)}",
    )
    _garante(len(meta.saidas) == antes, "saiu algo")
    _garante(not _envios(estado["orc_5"]), "registrou o envio recusado")
    _garante(
        _no_banco("SELECT id FROM clients WHERE phone=:p", p=WA_D) is None,
        "nasceu ficha no recusado",
    )
    orc = _no_banco("SELECT client_id FROM orcamento_history WHERE id=:i", i=estado["orc_5"])
    _garante(orc.client_id is None, "ligou o orçamento no recusado")


def cen_06() -> None:
    envio = _enviar(estado["cris"], estado["conv_a"], estado["orc_1"])
    ficha = _chamar(
        estado["cris"], "post", f"/api/conversas/{estado['conv_a']}/ficha", {"client_id": 1}
    )
    tira = _chamar(estado["cris"], "delete", f"/api/conversas/{estado['conv_a']}/ficha")
    forms = _chamar(estado["cris"], "get", f"/api/conversas/{estado['conv_a']}/formularios")
    codigos = [envio.status_code, ficha.status_code, tira.status_code, forms.status_code]
    _garante(codigos == [403, 403, 403, 403], f"Casting → {codigos}")


def cen_07() -> None:
    conv = estado["conv_e"]
    _garante(
        _ficha_da_conversa(conv).client_id == estado["ficha_e"],
        "a ligação automática não aconteceu",
    )
    r = _chamar(
        estado["ana"], "post", f"/api/conversas/{conv}/ficha", {"client_id": estado["ficha_e2"]}
    )
    _garante(r.status_code == 200, f"trocar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    linha = _ficha_da_conversa(conv)
    _garante(linha.client_id == estado["ficha_e2"] and linha.ficha_manual, f"troca {linha}")
    _wa(WA_E, "e-2", "Elisa")
    _garante(
        _ficha_da_conversa(conv).client_id == estado["ficha_e2"], "a automática desfez a troca"
    )
    r = _chamar(estado["ana"], "delete", f"/api/conversas/{conv}/ficha")
    _garante(
        r.status_code == 200 and r.get_json()["conversa"]["cliente"] is None,
        f"remover → {r.status_code}",
    )
    _wa(WA_E, "e-3", "Elisa")
    _garante(_ficha_da_conversa(conv).client_id is None, "a automática religou depois de remover")
    r = _chamar(
        estado["ana"],
        "post",
        f"/api/conversas/{conv}/ficha",
        {"nome": f"{PREFIX}Elisa Nova", "telefone": WA_E},
    )
    corpo = r.get_json()
    _garante(
        r.status_code == 200 and corpo["reaproveitada"] is True,
        f"reaproveitar → {r.status_code} {corpo}",
    )
    _garante(
        _ficha_da_conversa(conv).client_id == estado["ficha_e"], "não ligou à ficha do telefone"
    )


def cen_08() -> None:
    r = _enviar(estado["ana"], estado["conv_b"], estado["orc_1"])
    _garante(r.status_code == 201, f"reenvio → {r.status_code}")
    envios = _envios(estado["orc_1"])
    _garante(len(envios) == 2 and envios[-1].conversa_id == estado["conv_b"], f"envios {envios}")
    orc = _no_banco("SELECT client_id FROM orcamento_history WHERE id=:i", i=estado["orc_1"])
    _garante(orc.client_id == estado["ficha_a"], "o reenvio trocou a ficha do orçamento")
    # O orçamento da Carla (já com ficha) para uma conversa sem ficha: a ficha nova leva o nome do
    # perfil, nunca o da Carla com o telefone de outra pessoa.
    r = _enviar(estado["ana"], estado["conv_f"], estado["orc_3"])
    _garante(r.status_code == 201, f"envio F → {r.status_code}")
    ficha = _no_banco("SELECT name FROM clients WHERE phone=:p", p=WA_F)
    _garante(ficha is not None and ficha.name == f"{PREFIX}Fabi", f"ficha nova {ficha}")


def cen_09() -> None:
    r = _chamar(estado["ana"], "get", f"/api/conversas/{estado['conv_a']}/formularios")
    _garante(r.status_code == 200, f"formulários → {r.status_code}")
    # Hotfix 342b: cada formulário vem com nota e sem nota; a chave é (tipo, versão).
    forms = {(f["tipo"], f["versao"]): f for f in r.get_json()["formularios"]}
    _garante(
        set(forms)
        == {(t, v) for t in ("comum", "corporativo") for v in ("com-nota", "sem-nota")},
        f"tipos {set(forms)}",
    )
    comum = forms[("comum", "com-nota")]
    _garante(
        comum["link"] == f"{PLATFORM_BASE_URL}/f/pre-contrato/com-nota", f"link {comum}"
    )
    _garante(
        forms[("corporativo", "sem-nota")]["link"]
        == f"{PLATFORM_BASE_URL}/f/corporativo/sem-nota",
        "link corporativo",
    )
    _garante(
        comum["texto"]
        == f"Oi, {PREFIX}Ana! Para reservarmos a data, preencha o formulário: {comum['link']}",
        f"texto {comum['texto']!r}",
    )
    _no_banco_escrever("UPDATE conversas SET nome_perfil=NULL WHERE id=:i", i=estado["conv_d"])
    sem_nome = _chamar(
        estado["ana"], "get", f"/api/conversas/{estado['conv_d']}/formularios"
    ).get_json()
    texto = sem_nome["formularios"][0]["texto"]
    _garante(texto.startswith("Oi! Para reservarmos a data"), f"sem nome {texto!r}")
    # A ficha batizada pelo telefone (nasceu sem nome) também não vira "Oi, (11)!".
    with app.app_context():
        ficha_d = _ficha("(11) 96333-0004", WA_D)
    _no_banco_escrever(
        "UPDATE conversas SET client_id=:f WHERE id=:i", f=ficha_d, i=estado["conv_d"]
    )
    pelo_telefone = _chamar(
        estado["ana"], "get", f"/api/conversas/{estado['conv_d']}/formularios"
    ).get_json()["formularios"][0]["texto"]
    _garante(
        pelo_telefone.startswith("Oi! Para reservarmos"), f"ficha com telefone {pelo_telefone!r}"
    )


def cen_10() -> None:
    lista = _chamar(estado["ana"], "get", f"/api/orcamento/historico?q={PREFIX}").get_json()[
        "entries"
    ]
    por_id = {e["id"]: e for e in lista}
    _garante(por_id[estado["orc_1"]]["enviado_em"], "sem o selo do enviado")
    ultimo = _no_banco(
        "SELECT max(created_at) AS q FROM orcamento_envios WHERE orcamento_id=:o", o=estado["orc_1"]
    ).q
    selo = datetime.fromisoformat(por_id[estado["orc_1"]]["enviado_em"]).replace(tzinfo=None)
    _garante(selo == ultimo, f"o selo não é o último envio: {selo} × {ultimo}")
    _garante(por_id[estado["orc_5"]]["enviado_em"] is None, "selo no não enviado")
    detalhe = _chamar(
        estado["ana"], "get", f"/api/orcamento/historico/{estado['orc_1']}"
    ).get_json()
    _garante(
        detalhe["cliente"] == {"id": estado["ficha_a"], "nome": f"{PREFIX}Ana Souza"},
        f"{detalhe['cliente']}",
    )
    envios = detalhe["envios"]
    _garante(len(envios) == 2, f"{len(envios)} envios")
    _garante(
        envios[0]["conversa_id"] == estado["conv_b"] and envios[0]["canal"] == "whatsapp",
        f"{envios[0]}",
    )
    _garante(envios[1]["autor"] == f"{PREFIX}Ana" and envios[1]["quando"], f"{envios[1]}")


def cen_11() -> None:
    r = _chamar(estado["ana"], "get", f"/api/events/new/prefill?orcamento_id={estado['orc_1']}")
    _garante(r.status_code == 200, f"prefill → {r.status_code}")
    cliente = r.get_json().get("cliente")
    _garante(
        cliente == {"id": estado["ficha_a"], "nome": f"{PREFIX}Ana Souza"}, f"cliente {cliente}"
    )
    sem = _chamar(
        estado["ana"], "get", f"/api/events/new/prefill?orcamento_id={estado['orc_5']}"
    ).get_json()
    _garante(sem.get("cliente") is None, f"cliente no orçamento sem ficha {sem.get('cliente')}")


def cen_12() -> None:
    meta.falhar_upload = True
    r = _enviar(estado["ana"], estado["conv_a"], estado["orc_6"])
    _garante(r.status_code == 201, f"envio → {r.status_code}")
    envio = _envios(estado["orc_6"])
    _garante(len(envio) == 1, "o envio não ficou registrado")
    situacoes = _no_banco_todas(
        "SELECT tipo, situacao FROM conversa_mensagens WHERE chave_envio LIKE :c ORDER BY id",
        c=envio[0].chave_envio + ":%",
    )
    _garante(
        [(s.tipo, s.situacao) for s in situacoes]
        == [("texto", "enviada"), ("documento", "falhou")],
        f"situações {situacoes}",
    )
    # "Enviar só o PDF": sai só o PDF, num pedido novo; a mensagem não vai de novo para a cliente.
    antes = len(meta.saidas)
    r = _enviar(estado["ana"], estado["conv_a"], estado["orc_6"], somente_pdf=True)
    _garante(r.status_code == 201, f"só o PDF → {r.status_code}")
    tipos = [s["tipo"] for s in meta.saidas[antes:]]
    _garante(tipos == ["upload", "document"], f"só o PDF mandou {tipos}")
    envios = _envios(estado["orc_6"])
    _garante(
        len(envios) == 2 and envios[-1].texto_mensagem_id is None, f"registro do só o PDF {envios}"
    )


def cen_14() -> None:
    """Queda no meio: o texto saiu e o servidor caiu antes do PDF. A mesma chave manda só o PDF."""
    from app.conversas import costura_ops

    real = costura_ops._pdf
    chave = str(uuid.uuid4())

    def _queda(*_a, **_k):
        raise RuntimeError("queda simulada (verify 333)")

    costura_ops._pdf = _queda
    try:
        try:
            _enviar(estado["ana"], estado["conv_a"], estado["orc_8"], chave)
        except RuntimeError:
            pass
    finally:
        costura_ops._pdf = real
    registro = _envios(estado["orc_8"])
    _garante(
        len(registro) == 1 and registro[0].texto_mensagem_id and not registro[0].pdf_mensagem_id,
        f"registro depois da queda {registro}",
    )
    antes = len(meta.saidas)
    r = _enviar(estado["ana"], estado["conv_a"], estado["orc_8"], chave)
    _garante(r.status_code == 200, f"repetido depois da queda → {r.status_code}")
    tipos = [s["tipo"] for s in meta.saidas[antes:]]
    _garante(tipos == ["upload", "document"], f"depois da queda saiu {tipos} (só o PDF)")
    partes = _no_banco_todas(
        "SELECT chave_envio FROM conversa_mensagens WHERE chave_envio LIKE :c ORDER BY id",
        c=chave + ":%",
    )
    _garante([p.chave_envio for p in partes] == [f"{chave}:1", f"{chave}:pdf"], f"partes {partes}")


def cen_13() -> None:
    legado = _enviar(estado["ana"], estado["conv_a"], estado["orc_legado"])
    _garante(
        legado.status_code == 422
        and (_erro(legado).get("fields") or {}).get("orcamento")
        == "Este orçamento não tem a mensagem pronta. Use Recalcular e envie o novo orçamento.",
        f"legado → {legado.status_code} {_erro(legado)}",
    )
    ruim = _chamar(
        estado["ana"],
        "post",
        f"/api/conversas/{estado['conv_d']}/ficha",
        {"nome": f"{PREFIX}X", "telefone": "123"},
    )
    _garante(
        ruim.status_code == 422
        and (_erro(ruim).get("fields") or {}).get("telefone")
        == "Telefone inválido. Inclua DDD (e DDI se houver).",
        f"telefone → {ruim.status_code} {_erro(ruim)}",
    )


def preparar() -> None:
    estado["ana"], estado["ana_id"] = _usuario("Ana", RoleName.COMERCIAL)
    estado["bia"], estado["bia_id"] = _usuario("Bia", RoleName.COMERCIAL)
    estado["cris"], estado["cris_id"] = _usuario("Cris", RoleName.CASTING)
    estado["ficha_a"] = _ficha(f"{PREFIX}Ana Souza", WA_A)
    estado["ficha_e"] = _ficha(f"{PREFIX}Elisa", WA_E)
    estado["ficha_e2"] = _ficha(f"{PREFIX}Elisa (mãe)", WA_E_OUTRA)
    estado["conv_a"] = _wa(WA_A, "a-1", "Ana")
    estado["conv_b"] = _wa(WA_B, "b-1", "Bruna")
    estado["conv_c"] = _wa(WA_C, "c-1", "Carla")
    estado["conv_d"] = _wa(WA_D, "d-1", "Dora")
    estado["conv_e"] = _wa(WA_E, "e-1", "Elisa")
    estado["conv_f"] = _wa(WA_F, "f-1", "Fabi")
    estado["conv_us"] = _wa(WA_US, "us-1", "Kim")
    estado["conv_ig"] = _ig(IG_A, "ig-1")
    estado["orc_1"] = _orcamento("1", f"{PREFIX}Ana Souza")
    estado["orc_2"] = _orcamento("2", f"{PREFIX}Bruna Lima")
    estado["orc_3"] = _orcamento("3", f"{PREFIX}Carla")
    estado["orc_4"] = _orcamento("4", f"{PREFIX}Iara")
    estado["orc_5"] = _orcamento("5", f"{PREFIX}Dora")
    estado["orc_6"] = _orcamento("6", f"{PREFIX}Ana Souza")
    estado["orc_7"] = _orcamento("7", f"{PREFIX}Kim")
    estado["orc_8"] = _orcamento("8", f"{PREFIX}Ana Souza")
    estado["orc_legado"] = _orcamento("L", f"{PREFIX}Legado", com_mensagem=False)


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
        "(SELECT count(*) FROM orcamento_history WHERE client_name LIKE :p)",
        c=CONTATOS,
        t=TELEFONES,
        p=f"{PREFIX}%",
    )[0]
    _garante(sobras == 0, f"sobraram {sobras} registros de teste")


CENARIOS = [
    ("1. orçamento pela conversa do WhatsApp com ficha", cen_01),
    ("2. a mesma chave não manda de novo", cen_02),
    (
        "3. sem ficha: nasce a ficha (legível, estrangeira); a sem o nono dígito reaproveitada",
        cen_03,
    ),
    ("4. Instagram: pede a ficha; depois o texto em partes e o PDF", cen_04),
    ("5. janela fechada e ambiente travado (DEVE falhar)", cen_05),
    ("6. Casting (DEVE falhar)", cen_06),
    ("7. ligar, trocar e remover à mão; a automática respeita", cen_07),
    ("8. reenvio para outra ficha mantém a primeira", cen_08),
    ("9. formulários da conversa", cen_09),
    ("10. histórico e detalhe do orçamento", cen_10),
    ("11. Criar evento traz a cliente", cen_11),
    ("12. a Meta recusa o PDF: o texto fica; Enviar só o PDF", cen_12),
    ("13. orçamento sem mensagem e telefone inválido (DEVE falhar)", cen_13),
    ("14. queda no meio: a mesma chave manda só o que faltou", cen_14),
]


def main() -> int:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        limpar()
        preparar()
    print("Feature 333 — Orçamento e formulário pela conversa, contra manto_local")
    try:
        for nome, fn in CENARIOS:
            cenario(nome, fn)
    finally:
        with app.app_context():
            cenario("15. limpeza", limpar)
        for nome, real in _REAIS["ic"].items():
            setattr(_ic, nome, real)
        for nome, real in _REAIS["wc"].items():
            setattr(_wc, nome, real)
        shutil.rmtree(PASTA_MIDIA, ignore_errors=True)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK · escapes de rede: {len(_ESCAPES)}")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) and not _ESCAPES else 1


if __name__ == "__main__":
    sys.exit(main())
