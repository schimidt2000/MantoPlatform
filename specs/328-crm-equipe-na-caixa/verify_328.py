"""Verificação da feature 328 — Conversas em equipe.

Os 20 cenários da tabela da spec (seção "Verificação"): responsável e fila livre, alerta de cliente
esperando, notas internas, respostas rápidas e áudio gravado. A Meta NUNCA é chamada: as funções de
`app.integracoes.whatsapp_client` viram um dublê em memória (`MetaFalsa`), e um disjuntor de rede
derruba qualquer conexão de saída que não seja o Postgres local — instalado ANTES de importar o app
(molde do verify_325).

Tudo de teste leva `v328-`: usuários (Ana e Bia no Comercial, Cris no Casting), nome de perfil das
conversas, wamids, respostas rápidas e o `phone_number_id` falso (é por ele que os avisos crus são
achados na limpeza). O alerta sem responsável vai para a equipe REAL do `manto_local` (é a regra):
são linhas de `notifications` locais, apagadas na limpeza pela entidade (a conversa de teste).

Os cenários de horário chamam `equipe_ops.alertar_esperas(agora_sp=...)` com o relógio injetado, e
cada um conta só os avisos da própria conversa (outra conversa de teste esperando não interfere).

Escrita conferida por **conexão separada** e requisições HTTP **fora** de `app.app_context()`.

Rodar contra o manto_local (PowerShell, na raiz do repositório)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
    $env:PYTHONUTF8 = '1'; .venv\\Scripts\\python.exe specs/328-crm-equipe-na-caixa/verify_328.py [--so=1,2] [--manter]

`--manter` deixa as conversas, notas, respostas rápidas e os usuários para conferir a tela (senha
`verify-328-senha`); rode de novo sem a flag para limpar.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from datetime import time as hora
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# ── Disjuntor de rede (antes de importar o app) ────────────────────────────────────────────────────
_ESCAPES: list[str] = []
_LOCAIS = ("localhost", "127.0.0.1", "::1")
_connect_original = socket.socket.connect
_create_connection_original = socket.create_connection


def _host_de(endereco) -> str:
    return str(endereco[0]) if isinstance(endereco, tuple) and endereco else str(endereco)


def _connect_local(self, endereco):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 328: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 328: conexão de saída bloqueada para {_host_de(endereco)}")
    return _create_connection_original(endereco, *args, **kwargs)


socket.socket.connect = _connect_local
socket.create_connection = _create_connection_local

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ.pop("WHATSAPP_ALLOW_LOCAL_SEND", None)
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import TZ_SP, RoleName, now_sp  # noqa: E402
from app.models import Role, User  # noqa: E402

PREFIX = "v328-"
SENHA = "verify-328-senha"
SEGREDO = "segredo-do-app-v328"
NUMERO_ID = "v328-phone"
NUMERO_MANTO = "5511900000328"
WA_FILA = "5511963280001"
WA_ECO = "5511963280002"
WA_ESPERA = "5511963280003"
WA_SEM_DONO = "5511963280004"
WA_NOITE = "5511963280005"
WA_MODELO = "5511963280006"
WA_FALHA = "5511963280007"
CONTATOS = [WA_FILA, WA_ECO, WA_ESPERA, WA_SEM_DONO, WA_NOITE, WA_MODELO, WA_FALHA]
PASTA_MIDIA = tempfile.mkdtemp(prefix="v328-midia-")

app = create_app()
app.config["TESTING"] = True
app.config["WHATSAPP_ACCESS_TOKEN"] = "token-falso-v328"
app.config["WHATSAPP_APP_SECRET"] = SEGREDO
app.config["WHATSAPP_VERIFY_TOKEN"] = "verifica-v328"
app.config["WHATSAPP_PHONE_NUMBER_ID"] = NUMERO_ID
app.config["WHATSAPP_WABA_ID"] = "v328-waba"
app.config["WHATSAPP_AVISO_SINCRONO"] = True
# A "liberação de teste" do quickstart da 325, com o dublê no lugar da Meta (e o disjuntor atrás).
app.config["WHATSAPP_SUPPRESS_SEND"] = False
app.config["CONVERSAS_MEDIA_FOLDER"] = PASTA_MIDIA
limiter.enabled = False

# ── O dublê da Meta ──────────────────────────────────────────────────────────────────────────────
import app.integracoes.whatsapp_client as _wc  # noqa: E402

_REAIS = {
    nome: getattr(_wc, nome) for nome in ("enviar", "marcar_lida", "subir_midia", "listar_modelos")
}


class MetaFalsa:
    """Responde como a Meta, registra cada chamada e nunca sai da máquina."""

    def __init__(self) -> None:
        self.chamadas: dict[str, list] = {nome: [] for nome in _REAIS}
        self.seq = 0
        self.recusar_envio = False  # o próximo envio volta 131026 (cenário 19)

    def enviar(self, conexao, corpo):
        self.chamadas["enviar"].append(corpo)
        if self.recusar_envio:
            self.recusar_envio = False
            raise _wc.WhatsappRecusou("sem WhatsApp (dublê)", status=400, code=131026)
        self.seq += 1
        return {"id": f"wamid.{PREFIX}env-{self.seq}", "wa_id": corpo.get("to")}

    def marcar_lida(self, conexao, wamid):
        self.chamadas["marcar_lida"].append(wamid)

    def subir_midia(self, conexao, dados, mime, nome):
        self.chamadas["subir_midia"].append((dados, mime, nome))
        return f"{PREFIX}upload-{len(self.chamadas['subir_midia'])}"

    def listar_modelos(self, conexao):
        self.chamadas["listar_modelos"].append(True)
        return [
            {
                "name": "retomar_orcamento",
                "language": "pt_BR",
                "status": "APPROVED",
                "category": "MARKETING",
                "components": [{"type": "BODY", "text": "Oi, {{1}}! Ainda pensando na festa?"}],
            }
        ]


meta = MetaFalsa()
for _nome in _REAIS:
    setattr(_wc, _nome, getattr(meta, _nome))

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    """Lê pelo banco, por fora da sessão do app (o autoflush esconde falta de commit)."""
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
    except Exception as exc:  # noqa: BLE001 — harness: registra e segue
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


def _chamar(email: str, metodo: str, url: str, corpo: dict | None = None, **kwargs):
    """Uma requisição autenticada, fora de qualquer contexto de aplicação."""
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
        _garante(r.status_code == 200, f"login {email} → {r.status_code}")
        if corpo is not None:
            kwargs["json"] = corpo
        return getattr(c, metodo)(url, **kwargs)


def _post_aviso(corpo: dict):
    """POST do aviso da Meta com `X-Hub-Signature-256` do corpo bruto."""
    bruto = json.dumps(corpo).encode()
    assinatura = "sha256=" + hmac.new(SEGREDO.encode(), bruto, hashlib.sha256).hexdigest()
    with app.test_client() as c:
        r = c.post(
            "/api/webhooks/whatsapp",
            data=bruto,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": assinatura},
        )
    _garante(r.status_code == 200, f"aviso → {r.status_code}")
    return r


def _valor(contatos: list[dict], **campos) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "v328-waba",
                "changes": [
                    {
                        "field": campos.pop("field", "messages"),
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": NUMERO_MANTO,
                                "phone_number_id": NUMERO_ID,
                            },
                            "contacts": contatos,
                            **campos,
                        },
                    }
                ],
            }
        ],
    }


def _recebida(wa_id: str, nome: str, sufixo: str, corpo_texto: str = "Oi, quero um orçamento"):
    """A cliente escreve (aviso assinado). Devolve o id da conversa."""
    _post_aviso(
        _valor(
            [{"profile": {"name": f"{PREFIX}{nome}"}, "wa_id": wa_id}],
            messages=[
                {
                    "from": wa_id,
                    "id": f"wamid.{PREFIX}in-{sufixo}",
                    "timestamp": str(int(time.time())),
                    "type": "text",
                    "text": {"body": corpo_texto},
                }
            ],
        )
    )
    return _conversa(wa_id).id


def _eco(wa_id: str, sufixo: str, tipo: str = "text") -> None:
    item = {
        "from": NUMERO_MANTO,
        "to": wa_id,
        "id": f"wamid.{PREFIX}eco-{sufixo}",
        "timestamp": str(int(time.time())),
        "type": tipo,
    }
    if tipo == "text":
        item["text"] = {"body": "respondi pelo celular"}
    _post_aviso(_valor([], field="smb_message_echoes", message_echoes=[item]))


def _status(wamid: str, wa_id: str, status: str, erro: int | None = None) -> None:
    item = {
        "id": wamid,
        "status": status,
        "timestamp": str(int(time.time())),
        "recipient_id": wa_id,
    }
    if erro is not None:
        item["errors"] = [{"code": erro, "title": "x", "message": "x"}]
    _post_aviso(_valor([], statuses=[item]))


def _conversa(contato_id: str):
    return _no_banco(
        "SELECT id, responsavel_id, assumida_em, aguardando_desde FROM conversas "
        "WHERE canal='whatsapp' AND contato_id=:c",
        c=contato_id,
    )


def _texto(email: str, conversa_id: int, chave: str, texto: str = "Oi! Já preparo."):
    return _chamar(
        email,
        "post",
        f"/api/conversas/{conversa_id}/mensagens",
        {"texto": texto, "chave_envio": f"{PREFIX}{chave}"},
    )


def _responsavel(email: str, conversa_id: int, acao: str, responsavel_id: int | None = None):
    corpo: dict = {"acao": acao}
    if responsavel_id is not None:
        corpo["responsavel_id"] = responsavel_id
    return _chamar(email, "post", f"/api/conversas/{conversa_id}/responsavel", corpo)


def _avisos(conversa_id: int, kind: str):
    return _no_banco_todas(
        "SELECT user_id, title, link_path, severity FROM notifications "
        "WHERE entity_type='conversa' AND entity_id=:i AND kind=:k",
        i=conversa_id,
        k=kind,
    )


def _erro(r) -> dict:
    """O objeto de erro do envelope de `json_error` (`{"error": {...}}`)."""
    return (r.get_json() or {}).get("error") or {}


def _utc_de_sp(momento_sp: datetime) -> datetime:
    return momento_sp.replace(tzinfo=TZ_SP).astimezone(UTC).replace(tzinfo=None)


def _alertar(momento_sp: datetime) -> dict:
    from app.conversas import equipe_ops

    with app.app_context():
        return equipe_ops.alertar_esperas(agora_sp=momento_sp)


def _esperando_desde(conversa_id: int, momento_utc: datetime) -> None:
    _no_banco_escrever(
        "UPDATE conversas SET aguardando_desde=:t WHERE id=:i", t=momento_utc, i=conversa_id
    )


def _as(h: int, m: int = 0, dias: int = 0) -> datetime:
    """Um horário de São Paulo de hoje (ou de `dias` depois), sem fuso — como `now_sp()`."""
    return datetime.combine(now_sp().date() + timedelta(days=dias), hora(h, m))


# ── História 1 — fila livre e responsável ──────────────────────────────────────────────────────────


def cen_01() -> None:
    estado["fila"] = _recebida(WA_FILA, "Ana Souza", "fila-1")
    conv = _conversa(WA_FILA)
    _garante(conv.responsavel_id is None, f"conversa nova com responsável {conv.responsavel_id}")
    r = _chamar(estado["ana"], "get", "/api/conversas?filtro=sem_responsavel")
    _garante(r.status_code == 200, f"lista sem responsável → {r.status_code}")
    item = next((c for c in r.get_json()["conversas"] if c["id"] == estado["fila"]), None)
    _garante(item is not None and item["responsavel"] is None, f"item {item}")


def cen_02() -> None:
    r = _texto(estado["ana"], estado["fila"], "c02")
    _garante(r.status_code == 201, f"envio → {r.status_code} {r.get_data(as_text=True)[:200]}")
    conv = _conversa(WA_FILA)
    _garante(conv.responsavel_id == estado["ana_id"], f"responsável {conv.responsavel_id}")
    _garante(conv.assumida_em is not None, "assumida_em vazio")
    minhas = _chamar(estado["ana"], "get", "/api/conversas?filtro=minhas").get_json()["conversas"]
    _garante(any(c["id"] == estado["fila"] for c in minhas), "não está em Minhas da Ana")
    da_bia = _chamar(estado["bia"], "get", "/api/conversas?filtro=minhas").get_json()["conversas"]
    _garante(not any(c["id"] == estado["fila"] for c in da_bia), "apareceu em Minhas da Bia")
    item = next(c for c in minhas if c["id"] == estado["fila"])
    _garante(item["responsavel"]["id"] == estado["ana_id"], f"payload {item['responsavel']}")
    invalido = _chamar(estado["ana"], "get", "/api/conversas?filtro=qualquer")
    _garante(invalido.status_code == 422, f"filtro inválido → {invalido.status_code}")


def cen_03() -> None:
    r = _texto(estado["bia"], estado["fila"], "c03", "Complementando a resposta da Ana.")
    _garante(r.status_code == 201, f"envio da Bia → {r.status_code}")
    _garante(_conversa(WA_FILA).responsavel_id == estado["ana_id"], "a resposta da Bia roubou")


def cen_04() -> None:
    r = _responsavel(estado["bia"], estado["fila"], "assumir")
    _garante(r.status_code == 409, f"assumir conversa da Ana → {r.status_code} (esperado 409)")
    erro = _erro(r)
    _garante(erro.get("codigo") == "ja_assumida", f"código {erro}")
    _garante(f"{PREFIX}Ana" in (erro.get("message") or ""), f"mensagem sem o nome: {erro}")
    _garante(_conversa(WA_FILA).responsavel_id == estado["ana_id"], "o 409 mudou o responsável")


def cen_05() -> None:
    r = _responsavel(estado["ana"], estado["fila"], "transferir", estado["bia_id"])
    _garante(r.status_code == 200, f"transferir → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(_conversa(WA_FILA).responsavel_id == estado["bia_id"], "não foi para a Bia")
    avisos = _avisos(estado["fila"], "conversa.transferida")
    _garante(
        len(avisos) == 1 and avisos[0].user_id == estado["bia_id"],
        f"aviso de transferência {avisos}",
    )
    _garante("transferiu a conversa com" in avisos[0].title, f"título {avisos[0].title!r}")
    _garante(avisos[0].link_path == f"/conversas?c={estado['fila']}", f"link {avisos[0].link_path}")
    casting = _responsavel(estado["bia"], estado["fila"], "transferir", estado["cris_id"])
    _garante(casting.status_code == 422, f"transferir ao Casting → {casting.status_code}")
    _garante("responsavel_id" in (_erro(casting).get("fields") or {}), "sem fields")
    devolve = _responsavel(estado["bia"], estado["fila"], "devolver")
    _garante(devolve.status_code == 200, f"devolver → {devolve.status_code}")
    _garante(_conversa(WA_FILA).responsavel_id is None, "devolver não tirou o responsável")
    assume = _responsavel(estado["ana"], estado["fila"], "assumir")
    _garante(assume.status_code == 200, f"assumir da fila → {assume.status_code}")
    _garante(len(_avisos(estado["fila"], "conversa.transferida")) == 1, "assumir gerou aviso")


def cen_06() -> None:
    conversa_id = _recebida(WA_ECO, "Eco", "eco-1")
    _garante(_conversa(WA_ECO).aguardando_desde is not None, "a recebida não abriu a espera")
    _eco(WA_ECO, "1")
    conv = _conversa(WA_ECO)
    _garante(conv.responsavel_id is None, "o eco do celular atribuiu responsável")
    _garante(conv.aguardando_desde is None, "o eco do celular não encerrou a espera")
    _recebida(WA_ECO, "Eco", "eco-2", "e agora?")
    _eco(WA_ECO, "2", tipo="revoke")
    _garante(_conversa(WA_ECO).aguardando_desde is not None, "o 'apagada' encerrou a espera")
    estado["eco"] = conversa_id


# ── História 2 — alerta de cliente esperando ───────────────────────────────────────────────────────


def cen_07() -> None:
    estado["espera"] = _recebida(WA_ESPERA, "Carla Lima", "espera-1")
    _garante(_responsavel(estado["bia"], estado["espera"], "assumir").status_code == 200, "assumir")
    r = _responsavel(estado["bia"], estado["espera"], "transferir", estado["ana_id"])
    _garante(r.status_code == 200, f"transferir à Ana → {r.status_code}")
    as_14 = _as(14)
    _esperando_desde(estado["espera"], _utc_de_sp(as_14) - timedelta(minutes=16))
    _alertar(as_14)
    avisos = _avisos(estado["espera"], "conversa.esperando")
    _garante(
        [a.user_id for a in avisos] == [estado["ana_id"]], f"avisos {[a.user_id for a in avisos]}"
    )
    _garante("espera resposta há 16 min" in avisos[0].title, f"título {avisos[0].title!r}")
    _garante(avisos[0].severity == "urgent", f"severidade {avisos[0].severity}")
    _garante(avisos[0].link_path == f"/conversas?c={estado['espera']}", "link")


def cen_08() -> None:
    estado["sem_dono"] = _recebida(WA_SEM_DONO, "Dora Melo", "sem-dono-1")
    as_14 = _as(14)
    _esperando_desde(estado["sem_dono"], _utc_de_sp(as_14) - timedelta(minutes=20))
    _alertar(as_14)
    destinos = {a.user_id for a in _avisos(estado["sem_dono"], "conversa.esperando")}
    _garante({estado["ana_id"], estado["bia_id"]} <= destinos, f"equipe sem aviso: {destinos}")
    _garante(estado["cris_id"] not in destinos, "o Casting recebeu o aviso")


def cen_09() -> None:
    antes = len(_avisos(estado["sem_dono"], "conversa.esperando"))
    _alertar(_as(14))
    _alertar(_as(14, 1))
    depois = len(_avisos(estado["sem_dono"], "conversa.esperando"))
    _garante(depois == antes, f"aviso repetido: {antes} → {depois}")
    _garante(len(_avisos(estado["espera"], "conversa.esperando")) == 1, "repetiu para a Ana")


def cen_10() -> None:
    noite = _recebida(WA_NOITE, "Eva Noite", "noite-1")
    as_2230 = _as(22, 30)
    _esperando_desde(noite, _utc_de_sp(as_2230) - timedelta(minutes=20))
    _alertar(as_2230)
    _garante(not _avisos(noite, "conversa.esperando"), "avisou às 22h30")
    _alertar(_as(9, 0, dias=1))
    _garante(_avisos(noite, "conversa.esperando"), "não avisou às 9h do dia seguinte")
    estado["noite"] = noite


def cen_11() -> None:
    r = _texto(estado["ana"], estado["espera"], "c11", "Oi, Carla! Desculpe a demora.")
    _garante(r.status_code == 201, f"resposta → {r.status_code}")
    _garante(_conversa(WA_ESPERA).aguardando_desde is None, "a resposta não encerrou a espera")
    _garante(not _avisos(estado["espera"], "conversa.esperando"), "o aviso de espera ficou")
    _garante(_avisos(estado["espera"], "conversa.transferida"), "apagou o aviso de transferência")
    modelo = _recebida(WA_MODELO, "Fabi Modelo", "modelo-1")
    r2 = _chamar(
        estado["bia"],
        "post",
        f"/api/conversas/{modelo}/modelo",
        {
            "nome": "retomar_orcamento",
            "idioma": "pt_BR",
            "variaveis": ["Fabi"],
            "chave_envio": f"{PREFIX}c11-modelo",
        },
    )
    _garante(r2.status_code == 201, f"modelo → {r2.status_code} {r2.get_data(as_text=True)[:200]}")
    conv = _conversa(WA_MODELO)
    _garante(conv.responsavel_id == estado["bia_id"], "o modelo não atribuiu")
    _garante(conv.aguardando_desde is None, "o modelo não encerrou a espera")


# ── História 3 — notas internas ────────────────────────────────────────────────────────────────────


def cen_12() -> None:
    antes = len(meta.chamadas["enviar"])
    texto_nota = "Cliente quer saber do Papai Noel em dezembro, ligar amanhã."
    r = _chamar(
        estado["ana"], "post", f"/api/conversas/{estado['fila']}/notas", {"texto": texto_nota}
    )
    _garante(r.status_code == 201, f"nota → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(len(meta.chamadas["enviar"]) == antes, "a nota chamou a Meta")
    linha = _no_banco(
        "SELECT autor_id, texto FROM conversa_notas WHERE conversa_id=:i ORDER BY id DESC",
        i=estado["fila"],
    )
    _garante(linha and linha.autor_id == estado["ana_id"] and linha.texto == texto_nota, f"{linha}")
    detalhe = _chamar(estado["bia"], "get", f"/api/conversas/{estado['fila']}").get_json()
    notas = detalhe.get("notas") or []
    _garante(notas and notas[-1]["texto"] == texto_nota, f"notas no detalhe {notas}")
    _garante(notas[-1]["autor"]["id"] == estado["ana_id"], f"autor {notas[-1]['autor']}")


def cen_13() -> None:
    url = f"/api/conversas/{estado['fila']}/notas"
    vazia = _chamar(estado["ana"], "post", url, {"texto": "   "})
    _garante(vazia.status_code == 422, f"nota vazia → {vazia.status_code} (esperado 422)")
    _garante("texto" in (_erro(vazia).get("fields") or {}), "sem fields.texto")
    longa = _chamar(estado["ana"], "post", url, {"texto": "x" * 2001})
    _garante(longa.status_code == 422, f"nota longa → {longa.status_code} (esperado 422)")


# ── História 4 — respostas rápidas ─────────────────────────────────────────────────────────────────

URL_RESPOSTAS = "/api/conversas/respostas-rapidas"


def cen_14() -> None:
    criar = _chamar(
        estado["bia"],
        "post",
        URL_RESPOSTAS,
        {
            "titulo": f"{PREFIX}Pagamento",
            "atalho": f"/{PREFIX}Pag",
            "texto": "Olá, {nome}! Aceitamos PIX e cartão.",
        },
    )
    _garante(
        criar.status_code == 201, f"criar → {criar.status_code} {criar.get_data(as_text=True)}"
    )
    resposta = criar.get_json()["resposta"]
    _garante(resposta["atalho"] == f"{PREFIX}pag", f"atalho normalizado {resposta['atalho']!r}")
    alterar = _chamar(
        estado["ana"],
        "patch",
        f"{URL_RESPOSTAS}/{resposta['id']}",
        {"texto": "Olá, {nome}! Aceitamos PIX, cartão e boleto."},
    )
    _garante(alterar.status_code == 200, f"alterar → {alterar.status_code}")
    linha = _no_banco(
        "SELECT texto, criado_por_id, alterado_por_id FROM respostas_rapidas WHERE id=:i",
        i=resposta["id"],
    )
    _garante(linha.texto.endswith("e boleto."), f"texto {linha.texto!r}")
    _garante(
        linha.criado_por_id == estado["bia_id"] and linha.alterado_por_id == estado["ana_id"],
        f"autoria {linha}",
    )
    lista = _chamar(estado["ana"], "get", URL_RESPOSTAS).get_json()["respostas"]
    _garante(any(r["id"] == resposta["id"] for r in lista), "não está na lista da equipe")
    excluir = _chamar(estado["ana"], "delete", f"{URL_RESPOSTAS}/{resposta['id']}")
    _garante(excluir.status_code == 204, f"excluir → {excluir.status_code}")
    _garante(
        _no_banco("SELECT id FROM respostas_rapidas WHERE id=:i", i=resposta["id"]) is None,
        "a resposta excluída ficou no banco",
    )


def cen_15() -> None:
    base = {"titulo": f"{PREFIX}Endereço", "atalho": f"{PREFIX}end", "texto": "Rua X, 100."}
    _garante(_chamar(estado["ana"], "post", URL_RESPOSTAS, base).status_code == 201, "criar base")
    casos = [
        ({**base, "titulo": f"{PREFIX}ENDEREÇO", "atalho": None}, "titulo"),
        ({**base, "titulo": f"{PREFIX}Outro"}, "atalho"),
        ({**base, "titulo": f"{PREFIX}Com espaço", "atalho": "com espaco"}, "atalho"),
        ({**base, "titulo": "  ", "atalho": None}, "titulo"),
        ({**base, "titulo": f"{PREFIX}Sem texto", "atalho": None, "texto": ""}, "texto"),
    ]
    for corpo, campo in casos:
        r = _chamar(estado["bia"], "post", URL_RESPOSTAS, corpo)
        _garante(r.status_code == 422, f"{corpo} → {r.status_code} (esperado 422)")
        _garante(campo in (_erro(r).get("fields") or {}), f"{corpo}: sem fields.{campo}")


def cen_16() -> None:
    cris = estado["cris"]
    chamadas = [
        ("get", URL_RESPOSTAS, None),
        ("post", URL_RESPOSTAS, {"titulo": f"{PREFIX}Casting", "texto": "x"}),
        ("get", "/api/conversas/equipe", None),
        ("post", f"/api/conversas/{estado['fila']}/responsavel", {"acao": "assumir"}),
        ("post", f"/api/conversas/{estado['fila']}/notas", {"texto": "x"}),
    ]
    for metodo, url, corpo in chamadas:
        r = _chamar(cris, metodo, url, corpo)
        _garante(r.status_code == 403, f"Casting {metodo} {url} → {r.status_code} (esperado 403)")
    equipe = _chamar(estado["ana"], "get", "/api/conversas/equipe").get_json()["equipe"]
    ids = {p["id"] for p in equipe}
    _garante({estado["ana_id"], estado["bia_id"]} <= ids, f"equipe {ids}")
    _garante(estado["cris_id"] not in ids, "o Casting aparece na equipe")


# ── História 5 — áudio gravado ─────────────────────────────────────────────────────────────────────


def _webm_de_teste() -> bytes | None:
    """1 s de Opus em webm, como o Chrome grava. None quando a máquina não tem ffmpeg."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    saida = Path(PASTA_MIDIA) / "teste.webm"
    for codec in (["-c:a", "libopus"], ["-c:a", "opus", "-strict", "-2"]):
        r = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1",
                "-ac",
                "1",
                "-ar",
                "48000",
                *codec,
                str(saida),
            ],
            capture_output=True,
            timeout=60,
        )
        if r.returncode == 0 and saida.is_file():
            return saida.read_bytes()
    return None


def _enviar_audio(chave: str, dados: bytes):
    return _chamar(
        estado["ana"],
        "post",
        f"/api/conversas/{estado['fila']}/mensagens",
        data={
            "chave_envio": f"{PREFIX}{chave}",
            "arquivo": (io.BytesIO(dados), "audio.webm", "audio/webm;codecs=opus"),
        },
        content_type="multipart/form-data",
    )


def cen_17() -> None:
    dados = _webm_de_teste()
    if dados is None:
        print("         (pulado: sem ffmpeg nesta máquina)")
        return
    r = _enviar_audio("c17", dados)
    _garante(r.status_code == 201, f"áudio → {r.status_code} {r.get_data(as_text=True)[:200]}")
    subido, mime, nome = meta.chamadas["subir_midia"][-1]
    _garante(mime == "audio/ogg" and nome.endswith(".ogg"), f"subiu {mime} {nome}")
    _garante(subido[:4] == b"OggS", "o arquivo subido não é ogg")
    enviado = meta.chamadas["enviar"][-1]
    _garante(enviado.get("type") == "audio" and enviado["audio"].get("voice") is True, f"{enviado}")
    linha = _no_banco(
        "SELECT d.mime, d.caminho FROM conversa_mensagens m JOIN conversa_midias d "
        "ON d.mensagem_id=m.id WHERE m.chave_envio=:c",
        c=f"{PREFIX}c17",
    )
    _garante(linha.mime == "audio/ogg", f"cópia guardada {linha.mime}")
    _garante((Path(PASTA_MIDIA) / linha.caminho).read_bytes()[:4] == b"OggS", "cópia não é ogg")


def cen_18() -> None:
    import app.impressoes3d.video_ops as video_ops

    original = video_ops.caminho_do_ffmpeg
    video_ops.caminho_do_ffmpeg = lambda: None
    antes = (len(meta.chamadas["enviar"]), len(meta.chamadas["subir_midia"]))
    try:
        r = _enviar_audio("c18", b"\x1aE\xdf\xa3webm-de-mentira")
    finally:
        video_ops.caminho_do_ffmpeg = original
    _garante(r.status_code == 422, f"sem ffmpeg → {r.status_code} (esperado 422)")
    motivo = (_erro(r).get("fields") or {}).get("arquivo")
    _garante(
        motivo == "Não foi possível preparar o áudio. Envie o arquivo pelo clipe.", f"{motivo!r}"
    )
    depois = (len(meta.chamadas["enviar"]), len(meta.chamadas["subir_midia"]))
    _garante(depois == antes, "algo saiu para a Meta")
    _garante(
        _no_banco("SELECT id FROM conversa_mensagens WHERE chave_envio=:c", c=f"{PREFIX}c18")
        is None,
        "a mensagem recusada foi gravada",
    )


def cen_19() -> None:
    falha = _recebida(WA_FALHA, "Gabi Falha", "falha-1")
    inicio = _conversa(WA_FALHA).aguardando_desde
    _garante(inicio is not None, "a recebida não abriu a espera")
    meta.recusar_envio = True
    r = _texto(estado["ana"], falha, "c19a")
    _garante(r.status_code == 201 and r.get_json()["mensagem"]["situacao"] == "falhou", f"{r}")
    conv = _conversa(WA_FALHA)
    _garante(conv.responsavel_id is None, "o envio que falhou atribuiu")
    _garante(conv.aguardando_desde == inicio, "o envio que falhou encerrou a espera")
    _garante(_texto(estado["bia"], falha, "c19b").status_code == 201, "segundo envio")
    _garante(_conversa(WA_FALHA).aguardando_desde is None, "o envio aceito não encerrou")
    wamid = _no_banco(
        "SELECT externo_id FROM conversa_mensagens WHERE chave_envio=:c", c=f"{PREFIX}c19b"
    ).externo_id
    _status(wamid, WA_FALHA, "failed", erro=131026)
    _garante(
        _conversa(WA_FALHA).aguardando_desde == inicio,
        f"a falha tardia não reabriu a espera ({_conversa(WA_FALHA).aguardando_desde} ≠ {inicio})",
    )


# ── Preparo e limpeza ──────────────────────────────────────────────────────────────────────────────


def preparar() -> None:
    estado["ana"], estado["ana_id"] = _usuario("Ana", RoleName.COMERCIAL)
    estado["bia"], estado["bia_id"] = _usuario("Bia", RoleName.COMERCIAL)
    estado["cris"], estado["cris_id"] = _usuario("Cris", RoleName.CASTING)


def limpar() -> None:
    db.session.rollback()
    ids = [
        linha[0]
        for linha in db.session.execute(
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
        text("DELETE FROM whatsapp_avisos WHERE corpo LIKE :p"), {"p": f"%{NUMERO_ID}%"}
    )
    db.session.execute(
        text("DELETE FROM respostas_rapidas WHERE titulo LIKE :p"), {"p": f"{PREFIX}%"}
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
    sobras = _no_banco("SELECT count(*) FROM conversas WHERE contato_id = ANY(:c)", c=CONTATOS)[0]
    _garante(sobras == 0, f"sobraram {sobras} conversas de teste")


CENARIOS = [
    ("1. conversa nova sem responsável", cen_01),
    ("2. primeira resposta pela Plataforma atribui", cen_02),
    ("3. resposta de outra pessoa não rouba", cen_03),
    ("4. assumir conversa já assumida (DEVE falhar)", cen_04),
    ("5. transferir (com aviso), Casting (DEVE falhar) e devolver", cen_05),
    ("6. eco do celular encerra a espera e não atribui", cen_06),
    ("7. espera de 16 min às 14h avisa a responsável", cen_07),
    ("8. espera sem responsável avisa a equipe", cen_08),
    ("9. varredura de novo não repete o aviso", cen_09),
    ("10. às 22h30 não avisa; às 9h sim", cen_10),
    ("11. resposta e modelo encerram a espera", cen_11),
    ("12. nota interna gravada sem chamar a Meta", cen_12),
    ("13. nota vazia ou longa (DEVE falhar)", cen_13),
    ("14. CRUD de resposta rápida pela equipe", cen_14),
    ("15. título, atalho ou texto inválidos (DEVE falhar)", cen_15),
    ("16. Casting nas rotas novas (DEVE falhar)", cen_16),
    ("17. áudio webm sai como ogg com voice", cen_17),
    ("18. sem ffmpeg (DEVE falhar)", cen_18),
    ("19. envio que falhou, na hora ou depois", cen_19),
]


def main() -> int:
    so = None
    manter = "--manter" in sys.argv[1:]
    for arg in sys.argv[1:]:
        if arg.startswith("--so="):
            so = {int(n) for n in arg.split("=", 1)[1].split(",") if n.strip()}
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        limpar()  # sobra de uma rodada interrompida
        preparar()

    print("Feature 328 — Conversas em equipe, contra manto_local")
    try:
        for indice, (nome, fn) in enumerate(CENARIOS, start=1):
            if so is None or indice in so:
                cenario(nome, fn)
    finally:
        if manter:
            print(f"  --manter: dados {PREFIX} ficam para conferir a tela (senha: {SENHA})")
        else:
            with app.app_context():
                cenario("20. limpeza", limpar)
        for _nome, _fn in _REAIS.items():
            setattr(_wc, _nome, _fn)
        shutil.rmtree(PASTA_MIDIA, ignore_errors=True)

    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK · escapes de rede: {len(_ESCAPES)}")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) and not _ESCAPES else 1


if __name__ == "__main__":
    sys.exit(main())
