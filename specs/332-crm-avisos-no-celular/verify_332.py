"""Verificação da feature 332 — Avisos das Conversas no celular (Web Push).

Os cenários da tabela da spec. Nada sai da máquina: a entrega (`app.push.webpush.enviar`) vira um dublê
que registra cada aviso, os clientes da Meta viram dublês, e um disjuntor de rede derruba qualquer
conexão que não seja o Postgres local. A CIFRA não é dublê: o cenário 0 a confere contra o vetor oficial
do RFC 8291 (apêndice A), byte a byte.

Tudo de teste leva `v332-`. Rodar (PowerShell, na raiz)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
    $env:PYTHONUTF8 = '1'; .venv\\Scripts\\python.exe specs/332-crm-avisos-no-celular/verify_332.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import sys
import time
import traceback
import types
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from datetime import time as hora
from pathlib import Path
from urllib.parse import urlsplit

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
        raise OSError(f"verify 332: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 332: conexão de saída bloqueada para {_host_de(endereco)}")
    return _create_connection_original(endereco, *args, **kwargs)


socket.socket.connect = _connect_local
socket.create_connection = _create_connection_local

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ.pop("WEB_PUSH_ALLOW_LOCAL", None)
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature  # noqa: E402
from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import TZ_SP, RoleName, now_sp  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.push import webpush  # noqa: E402

PREFIX = "v332-"
SENHA = "verify-332-senha"
SEGREDO = "segredo-do-app-v332"
NUMERO_ID = "v332-phone"
NUMERO_MANTO = "5511900000332"
CONTA_IG = "v332-conta-ig"
WA_A = "5511963320001"
WA_B = "5511963320002"
WA_C = "5511963320003"
IG_A = "3323320000000001"
CONTATOS = [WA_A, WA_B, WA_C, IG_A]
ENDPOINT = "https://fcm.googleapis.com/fcm/send/" + PREFIX
VAPID_PUBLICA, VAPID_PRIVADA = webpush.gerar_chaves()

app = create_app()
# A trava que o banco local deriva sozinho (FR-008), antes de o verify liberar o envio de mentira.
SUPRESSAO_DERIVADA = app.config.get("WEB_PUSH_SUPPRESS")
app.config["TESTING"] = True
app.config.update(
    WHATSAPP_ACCESS_TOKEN="token-falso-v332",
    WHATSAPP_APP_SECRET=SEGREDO,
    WHATSAPP_VERIFY_TOKEN="verifica-v332",
    WHATSAPP_PHONE_NUMBER_ID=NUMERO_ID,
    WHATSAPP_AVISO_SINCRONO=True,
    WHATSAPP_SUPPRESS_SEND=False,
    INSTAGRAM_ACCESS_TOKEN="token-ig-v332",
    INSTAGRAM_PAGE_ID="v332-pagina",
    INSTAGRAM_ACCOUNT_ID=CONTA_IG,
    WEB_PUSH_VAPID_PUBLICA=VAPID_PUBLICA,
    WEB_PUSH_VAPID_PRIVADA=VAPID_PRIVADA,
    WEB_PUSH_SUPPRESS=False,
    WEB_PUSH_SINCRONO=True,
)
limiter.enabled = False

import app.integracoes.instagram_client as _ic  # noqa: E402

_REAIS = {"requests": webpush.requests, "perfil": _ic.perfil}
# O que o navegador guarda de cada aparelho de teste: a chave privada e o segredo de autenticação,
# para o serviço falso decifrar o aviso como o celular decifraria.
APARELHOS: dict[str, tuple[ec.EllipticCurvePrivateKey, bytes]] = {}


def _h(chave: bytes, dados: bytes) -> bytes:
    return hmac.new(chave, dados, hashlib.sha256).digest()


def _decifrar(endpoint: str, dados: bytes) -> dict:
    """RFC 8291 do lado do aparelho, escrito à parte do ``webpush.cifrar`` (senão um erro se anularia)."""
    privada, auth = APARELHOS[endpoint]
    sal, rs, idlen = dados[:16], int.from_bytes(dados[16:20], "big"), dados[20]
    _garante(rs == 4096 and idlen == 65, f"cabeçalho aes128gcm: rs={rs} idlen={idlen}")
    chave_do_servidor = dados[21 : 21 + idlen]
    efemera = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), chave_do_servidor)
    segredo = privada.exchange(ec.ECDH(), efemera)
    do_aparelho = privada.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    ikm = _h(_h(auth, segredo), b"WebPush: info\x00" + do_aparelho + chave_do_servidor + b"\x01")
    prk = _h(sal, ikm)
    cek = _h(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = _h(prk, b"Content-Encoding: nonce\x00\x01")[:12]
    claro = AESGCM(cek).decrypt(nonce, dados[21 + idlen :], None).rstrip(b"\x00")
    _garante(claro.endswith(b"\x02"), "sem o delimitador do último registro")
    return json.loads(claro[:-1])


def _conferir_vapid(url: str, cabecalho: str) -> None:
    """O JWT ES256 do RFC 8292: assinatura com a chave pública da Plataforma, aud, exp e sub."""
    _garante(
        cabecalho.startswith("vapid t=") and ", k=" in cabecalho, f"Authorization {cabecalho[:40]}"
    )
    token, k = cabecalho[len("vapid t=") :].split(", k=")
    _garante(k == VAPID_PUBLICA, "k não é a chave pública da Plataforma")
    cab, corpo, assinatura = token.split(".")
    _garante(
        json.loads(webpush.b64_decodificar(cab)) == {"typ": "JWT", "alg": "ES256"}, "cabeçalho JWT"
    )
    claims = json.loads(webpush.b64_decodificar(corpo))
    partes = urlsplit(url)
    _garante(claims["aud"] == f"{partes.scheme}://{partes.netloc}", f"aud {claims['aud']}")
    _garante(time.time() < claims["exp"] <= time.time() + 24 * 3600, f"exp {claims['exp']}")
    _garante(claims["sub"] == app.config["WEB_PUSH_CONTATO"], f"sub {claims['sub']}")
    crua = webpush.b64_decodificar(assinatura)
    _garante(len(crua) == 64, "assinatura não é r||s")
    der = encode_dss_signature(int.from_bytes(crua[:32], "big"), int.from_bytes(crua[32:], "big"))
    publica = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), webpush.b64_decodificar(VAPID_PUBLICA)
    )
    publica.verify(der, f"{cab}.{corpo}".encode(), ec.ECDSA(hashes.SHA256()))


class ServicoFalso:
    """O serviço de avisos de mentira (o FCM): confere o VAPID e os cabeçalhos, decifra o corpo com a
    chave do aparelho e responde 201 — ou o status fabricado para aquele endpoint (410, 500)."""

    def __init__(self) -> None:
        self.avisos: list[dict] = []
        self.respostas: dict[str, int] = {}
        self.problemas: list[str] = []

    def post(self, url, data=None, headers=None, timeout=None):
        try:
            _conferir_vapid(url, headers["Authorization"])
            _garante(headers["Content-Encoding"] == "aes128gcm", "Content-Encoding")
            _garante(headers["Content-Type"] == "application/octet-stream", "Content-Type")
            _garante(headers["TTL"] == str(24 * 3600), f"TTL {headers['TTL']}")
            _garante(headers["Urgency"] in ("high", "normal"), f"Urgency {headers['Urgency']}")
            _garante(timeout is not None, "sem timeout")
            corpo = _decifrar(url, data)
        except Exception as exc:  # noqa: BLE001 — vira problema do verify, não do código
            self.problemas.append(f"{url}: {exc}")
            return types.SimpleNamespace(status_code=400, text=str(exc))
        status = self.respostas.get(url, 201)
        if status < 300:
            self.avisos.append(
                {
                    "endpoint": url,
                    "corpo": corpo,
                    "urgencia": headers["Urgency"],
                    "ttl": headers["TTL"],
                }
            )
        return types.SimpleNamespace(status_code=status, text="")

    def para(self, endpoint: str) -> list[dict]:
        return [a for a in self.avisos if a["endpoint"] == endpoint]


entrega = ServicoFalso()
# Só o `requests` do webpush: a cifra, o JWT e o mapeamento 404/410/500 rodam de verdade.
webpush.requests = types.SimpleNamespace(
    post=entrega.post, RequestException=_REAIS["requests"].RequestException
)
_ic.perfil = lambda conexao, igsid: {"nome": f"{PREFIX}Perfil IG", "usuario": "v332.perfil"}

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchone()


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


def _chaves_do_aparelho(endpoint: str | None = None) -> dict:
    privada = ec.generate_private_key(ec.SECP256R1())
    ponto = privada.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    auth = os.urandom(16)
    if endpoint:
        APARELHOS[endpoint] = (privada, auth)
    return {"p256dh": webpush.b64_codificar(ponto), "auth": webpush.b64_codificar(auth)}


def _registrar(email: str, sufixo: str):
    return _chamar(
        email,
        "post",
        "/api/push/aparelhos",
        {"endpoint": ENDPOINT + sufixo, "keys": _chaves_do_aparelho(ENDPOINT + sufixo)},
    )


def _assinado(corpo: dict, rota: str):
    bruto = json.dumps(corpo).encode()
    assinatura = "sha256=" + hmac.new(SEGREDO.encode(), bruto, hashlib.sha256).hexdigest()
    with app.test_client() as c:
        r = c.post(
            rota,
            data=bruto,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": assinatura},
        )
    _garante(r.status_code == 200, f"aviso → {r.status_code}")


def _wa(
    wa_id: str,
    wamid: str,
    nome: str = "Cliente",
    tipo: str = "text",
    extra: dict | None = None,
    eco=False,
):
    if eco:
        valor = {
            "message_echoes": [
                {
                    "from": NUMERO_MANTO,
                    "to": wa_id,
                    "id": wamid,
                    "timestamp": str(int(time.time())),
                    "type": "text",
                    "text": {"body": "oi"},
                }
            ]
        }
        campo = "smb_message_echoes"
    else:
        mensagem = {"from": wa_id, "id": wamid, "timestamp": str(int(time.time())), "type": tipo}
        mensagem.update(extra or {"text": {"body": "Quero orçamento para sábado"}})
        valor = {
            "contacts": [{"profile": {"name": f"{PREFIX}{nome}"}, "wa_id": wa_id}],
            "messages": [mensagem],
        }
        campo = "messages"
    corpo = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "v332-waba",
                "changes": [
                    {
                        "field": campo,
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": NUMERO_MANTO,
                                "phone_number_id": NUMERO_ID,
                            },
                            **valor,
                        },
                    }
                ],
            }
        ],
    }
    _assinado(corpo, "/api/webhooks/whatsapp")


def _conversa(contato: str):
    return _no_banco("SELECT id FROM conversas WHERE contato_id=:c", c=contato)


def _aparelho(sufixo: str):
    return _no_banco("SELECT user_id FROM push_assinaturas WHERE endpoint=:e", e=ENDPOINT + sufixo)


# ── Cenários ───────────────────────────────────────────────────────────────────────────────────────


def cen_00() -> None:
    privada = ec.derive_private_key(
        int.from_bytes(
            webpush.b64_decodificar("yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"), "big"
        ),
        ec.SECP256R1(),
    )
    corpo = webpush.cifrar(
        b"When I grow up, I want to be a watermelon",
        "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4",
        "BTBZMqHH6r4Tts7J_aSIgg",
        privada_efemera=privada,
        sal=webpush.b64_decodificar("DGv6ra1nlYgDCS1FRnbzlw"),
    )
    esperado = (
        "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6"
        "PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN"
    )
    _garante(webpush.b64_codificar(corpo) == esperado, "a cifra não bate com o vetor do RFC 8291")


def cen_01() -> None:
    r = _chamar(estado["ana"], "get", "/api/push/chave").get_json()
    _garante(r == {"ligado": True, "chave_publica": VAPID_PUBLICA}, f"chave {r}")


def cen_02() -> None:
    r = _registrar(estado["ana"], "a")
    _garante(r.status_code == 201, f"registro → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(_aparelho("a").user_id == estado["ana_id"], "não ficou da Ana")


def cen_03() -> None:
    _garante(_registrar(estado["bia"], "a").status_code == 201, "registro da Bia")
    n = _no_banco("SELECT count(*) FROM push_assinaturas WHERE endpoint=:e", e=ENDPOINT + "a")[0]
    _garante(
        n == 1 and _aparelho("a").user_id == estado["bia_id"],
        f"{n} registros; dono {_aparelho('a')}",
    )
    _garante(_registrar(estado["ana"], "ana").status_code == 201, "aparelho da Ana")


def cen_04() -> None:
    _garante(_registrar(estado["ana"], "tchau").status_code == 201, "registro")
    r = _chamar(estado["ana"], "delete", "/api/push/aparelhos", {"endpoint": ENDPOINT + "tchau"})
    _garante(r.status_code == 204 and _aparelho("tchau") is None, f"desativar → {r.status_code}")


def cen_05() -> None:
    casting = _registrar(estado["cris"], "cris")
    _garante(casting.status_code == 403, f"Casting → {casting.status_code} (esperado 403)")
    sem = _chamar(
        estado["ana"], "post", "/api/push/aparelhos", {"endpoint": ENDPOINT + "x", "keys": {}}
    )
    _garante(
        sem.status_code == 422 and "aparelho" in (_erro(sem).get("fields") or {}),
        f"sem chaves → {sem.status_code}",
    )
    http = _chamar(
        estado["ana"],
        "post",
        "/api/push/aparelhos",
        {"endpoint": "http://x.invalid/a", "keys": _chaves_do_aparelho()},
    )
    _garante(http.status_code == 422, f"endpoint http → {http.status_code}")
    # SSRF: o servidor faz POST no endereço registrado; só os serviços de aviso conhecidos.
    outro = _chamar(
        estado["ana"],
        "post",
        "/api/push/aparelhos",
        {"endpoint": "https://127.0.0.1/interno", "keys": _chaves_do_aparelho()},
    )
    _garante(outro.status_code == 422, f"endpoint fora dos serviços de aviso → {outro.status_code}")
    _garante(_aparelho("x") is None, "gravou o registro sem chaves")
    fora_da_curva = {
        "p256dh": webpush.b64_codificar(b"\x04" + bytes(64)),
        "auth": webpush.b64_codificar(bytes(16)),
    }
    curva = _chamar(
        estado["ana"],
        "post",
        "/api/push/aparelhos",
        {"endpoint": ENDPOINT + "x", "keys": fora_da_curva},
    )
    _garante(curva.status_code == 422, f"ponto fora da curva → {curva.status_code}")
    # Filtro no envio: um aparelho do Casting gravado à força (papel trocado depois) não toca.
    chaves = _chaves_do_aparelho()
    _no_banco_escrever(
        "INSERT INTO push_assinaturas (user_id, endpoint, p256dh, auth, created_at) "
        "VALUES (:u, :e, :p, :a, now())",
        u=estado["cris_id"],
        e=ENDPOINT + "cris",
        p=chaves["p256dh"],
        a=chaves["auth"],
    )
    from app.push import push_ops

    with app.app_context():
        aviso = push_ops.Aviso(titulo="t", corpo="c", link="/conversas", tag="v332")
        entregues = push_ops.entregar([estado["cris_id"]], aviso)
    _garante(entregues == 0 and not entrega.para(ENDPOINT + "cris"), "o Casting recebeu aviso")


def cen_06() -> None:
    antes = len(entrega.avisos)
    _wa(WA_A, f"wamid.{PREFIX}a-1", "Ana Souza")
    conv = _conversa(WA_A)
    novos = entrega.avisos[antes:]
    destinos = {a["endpoint"] for a in novos}
    _garante({ENDPOINT + "a", ENDPOINT + "ana"} <= destinos, f"destinos {destinos}")
    corpo = novos[0]["corpo"]
    _garante(corpo["titulo"] == f"{PREFIX}Ana Souza", f"título {corpo}")
    _garante(corpo["corpo"] == "Quero orçamento para sábado", f"corpo {corpo}")
    _garante(
        corpo["link"] == f"/conversas?c={conv.id}" and corpo["tag"] == f"conversa-{conv.id}",
        f"{corpo}",
    )
    _garante(novos[0]["urgencia"] == "high", "urgência")
    estado["a"] = conv.id


def cen_07() -> None:
    _wa(WA_B, f"wamid.{PREFIX}b-1", "Bruna")
    conv = _conversa(WA_B)
    _no_banco_escrever(
        "UPDATE conversas SET responsavel_id=:u WHERE id=:i", u=estado["ana_id"], i=conv.id
    )
    antes = len(entrega.avisos)
    _wa(WA_B, f"wamid.{PREFIX}b-2", "Bruna")
    destinos = {a["endpoint"] for a in entrega.avisos[antes:]}
    _garante(destinos == {ENDPOINT + "ana"}, f"destinos {destinos} (só a Ana)")
    estado["b"] = conv.id


def cen_08() -> None:
    antes = len(entrega.avisos)
    _wa(WA_A, f"wamid.{PREFIX}a-1", "Ana Souza")  # reenvio do mesmo aviso
    _wa(WA_A, f"wamid.{PREFIX}a-eco", eco=True)
    _wa(
        WA_A,
        f"wamid.{PREFIX}a-reacao",
        tipo="reaction",
        extra={"reaction": {"message_id": "x", "emoji": "👍"}},
    )
    _garante(len(entrega.avisos) == antes, f"{len(entrega.avisos) - antes} avisos falsos")
    _ig(
        {
            "sender": {"id": CONTA_IG},
            "recipient": {"id": IG_A},
            "message": {"mid": f"{PREFIX}ig-eco", "is_echo": True, "text": "Respondi pelo app"},
        }
    )
    _ig(
        {
            "sender": {"id": IG_A},
            "recipient": {"id": CONTA_IG},
            "reaction": {"mid": f"{PREFIX}ig-1", "action": "react", "emoji": "❤"},
        }
    )
    _garante(
        len(entrega.avisos) == antes, f"{len(entrega.avisos) - antes} avisos falsos (Instagram)"
    )
    # O eco e a reação foram gravados de verdade (senão o cenário passaria sem testar nada).
    eco_ig = _no_banco("SELECT id FROM conversa_mensagens WHERE externo_id=:w", w=f"{PREFIX}ig-eco")
    _garante(eco_ig is not None, "o eco do Instagram não foi gravado")
    reacao_ig = _no_banco(
        "SELECT id FROM conversa_mensagens WHERE externo_id LIKE :w", w=f"reacao:{PREFIX}ig-1:%"
    )
    _garante(reacao_ig is not None, "a reação do Instagram não foi gravada")
    for wamid in (f"wamid.{PREFIX}a-eco", f"wamid.{PREFIX}a-reacao"):
        linha = _no_banco("SELECT id FROM conversa_mensagens WHERE externo_id=:w", w=wamid)
        _garante(linha is not None, f"{wamid} não foi gravada")


def _ig(item: dict) -> None:
    item = {"timestamp": int(time.time() * 1000), **item}
    _assinado(
        {"object": "instagram", "entry": [{"id": CONTA_IG, "time": 1, "messaging": [item]}]},
        "/api/webhooks/instagram",
    )


def cen_09() -> None:
    antes = len(entrega.avisos)
    _ig(
        {
            "sender": {"id": IG_A},
            "recipient": {"id": CONTA_IG},
            "message": {"mid": f"{PREFIX}ig-1", "text": "Oi! Vi o reels."},
        }
    )
    novos = entrega.avisos[antes:]
    _garante(
        novos and novos[0]["corpo"]["titulo"] == f"{PREFIX}Perfil IG",
        f"aviso do Instagram {novos[:1]}",
    )
    # Toque em botão é a cliente puxando assunto: toca (Instagram e WhatsApp).
    antes = len(entrega.avisos)
    _ig(
        {
            "sender": {"id": IG_A},
            "recipient": {"id": CONTA_IG},
            "postback": {"mid": f"{PREFIX}ig-pb", "title": "Ver pacotes", "payload": "pacotes"},
        }
    )
    corpos = [a["corpo"]["corpo"] for a in entrega.avisos[antes:]]
    _garante(corpos and corpos[0] == 'Tocou em "Ver pacotes".', f"postback {corpos}")
    antes = len(entrega.avisos)
    _wa(
        WA_A,
        f"wamid.{PREFIX}a-botao",
        "Ana Souza",
        tipo="interactive",
        extra={
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "b1", "title": "Quero saber mais"},
            }
        },
    )
    corpos = [a["corpo"]["corpo"] for a in entrega.avisos[antes:]]
    _garante(corpos and corpos[0] == "Quero saber mais", f"botão do WhatsApp {corpos}")
    # O corpo é a última mensagem da cliente, não a prévia: a reação não muda o aviso.
    _wa(
        WA_A,
        f"wamid.{PREFIX}a-reacao2",
        tipo="reaction",
        extra={"reaction": {"message_id": f"wamid.{PREFIX}a-botao", "emoji": "🙏"}},
    )
    with app.app_context():
        from app.conversas import celular_ops
        from app.models import Conversa

        trecho = celular_ops.aviso_da_mensagem(db.session.get(Conversa, estado["a"])).corpo
    _garante(trecho == "Quero saber mais", f"o corpo virou a reação: {trecho!r}")


def cen_10() -> None:
    _garante(_aparelho("a") is not None, "o aparelho a não existia antes do 410")
    _garante(_registrar(estado["ana"], "quinhentos").status_code == 201, "aparelho do 500")
    # Aparelho gravado antes da checagem da curva: a cifra levanta só na hora do aviso.
    _no_banco_escrever(
        "INSERT INTO push_assinaturas (user_id, endpoint, p256dh, auth, created_at) "
        "VALUES (:u, :e, :p, :a, now())",
        u=estado["ana_id"],
        e=ENDPOINT + "veneno",
        p=webpush.b64_codificar(b"\x04" + bytes(64)),
        a=webpush.b64_codificar(bytes(16)),
    )
    antes = len(entrega.avisos)
    entrega.respostas.update({ENDPOINT + "a": 410, ENDPOINT + "quinhentos": 500})
    try:
        _wa(WA_C, f"wamid.{PREFIX}c-1", "Carla")
    finally:
        entrega.respostas.clear()
    _garante(_aparelho("a") is None, "o aparelho que sumiu (410) não foi apagado")
    _garante(_aparelho("quinhentos") is not None, "o 500 apagou o aparelho")
    _garante(_aparelho("veneno") is not None, "o aparelho envenenado foi apagado sem 410")
    destinos = {a["endpoint"] for a in entrega.avisos[antes:]}
    _garante(destinos == {ENDPOINT + "ana"}, f"os outros aparelhos não receberam: {destinos}")
    ultimo = _no_banco(
        "SELECT ultimo_aviso_em FROM push_assinaturas WHERE endpoint=:e", e=ENDPOINT + "ana"
    )
    _garante(ultimo is not None and ultimo[0] is not None, "ultimo_aviso_em não foi gravado")
    _no_banco_escrever(
        "DELETE FROM push_assinaturas WHERE endpoint IN (:q, :v)",
        q=ENDPOINT + "quinhentos",
        v=ENDPOINT + "veneno",
    )
    estado["c"] = _conversa(WA_C).id


def _utc_de_sp(momento: datetime) -> datetime:
    return momento.replace(tzinfo=TZ_SP).astimezone(UTC).replace(tzinfo=None)


def cen_11() -> None:
    from app.conversas import equipe_ops

    _garante(_registrar(estado["bia"], "bia").status_code == 201, "aparelho da Bia")
    as_14 = datetime.combine(now_sp().date(), hora(14, 0))
    for conversa_id in (estado["b"], estado["c"]):
        _no_banco_escrever(
            "UPDATE conversas SET aguardando_desde=:t WHERE id=:i",
            t=_utc_de_sp(as_14) - timedelta(minutes=20),
            i=conversa_id,
        )
    antes = len(entrega.avisos)
    with app.app_context():
        equipe_ops.alertar_esperas(agora_sp=as_14)
    novos = [a for a in entrega.avisos[antes:] if a["corpo"]["tag"] == f"espera-{estado['b']}"]
    _garante([a["endpoint"] for a in novos] == [ENDPOINT + "ana"], f"alerta {novos}")
    _garante("espera resposta" in novos[0]["corpo"]["titulo"], f"título {novos[0]['corpo']}")
    da_equipe = {
        a["endpoint"]
        for a in entrega.avisos[antes:]
        if a["corpo"]["tag"] == f"espera-{estado['c']}"
    }
    _garante(
        da_equipe == {ENDPOINT + "ana", ENDPOINT + "bia"}, f"alerta sem responsável {da_equipe}"
    )


def cen_12() -> None:
    _garante(_registrar(estado["bia"], "bia").status_code == 201, "aparelho da Bia")
    antes = len(entrega.avisos)
    r = _chamar(
        estado["ana"],
        "post",
        f"/api/conversas/{estado['b']}/responsavel",
        {"acao": "transferir", "responsavel_id": estado["bia_id"]},
    )
    _garante(r.status_code == 200, f"transferir → {r.status_code}")
    novos = [a for a in entrega.avisos[antes:] if a["corpo"]["tag"] == f"transferida-{estado['b']}"]
    _garante([a["endpoint"] for a in novos] == [ENDPOINT + "bia"], f"transferência {novos}")


def cen_13() -> None:
    app.config["WEB_PUSH_SUPPRESS"] = True
    antes = len(entrega.avisos)
    try:
        _wa(WA_A, f"wamid.{PREFIX}a-travado", "Ana Souza")
        registro = _registrar(estado["ana"], "travado")
    finally:
        app.config["WEB_PUSH_SUPPRESS"] = False
    _garante(len(entrega.avisos) == antes, "saiu aviso com o ambiente travado")
    _garante(
        registro.status_code == 201, "o registro deveria funcionar travado (para conferir a tela)"
    )


def cen_15() -> None:
    """O caminho de produção: a entrega numa thread própria, sem segurar o webhook."""
    app.config["WEB_PUSH_SINCRONO"] = False
    antes = len(entrega.avisos)
    try:
        _wa(WA_A, f"wamid.{PREFIX}a-thread", "Ana Souza")
        limite = time.time() + 10
        while time.time() < limite and len(entrega.avisos) == antes:
            time.sleep(0.1)
    finally:
        app.config["WEB_PUSH_SINCRONO"] = True
    tags = {a["corpo"]["tag"] for a in entrega.avisos[antes:]}
    _garante(f"conversa-{estado['a']}" in tags, f"a thread não entregou: {tags}")


def cen_14() -> None:
    app.config["WEB_PUSH_VAPID_PRIVADA"] = ""
    try:
        chave = _chamar(estado["ana"], "get", "/api/push/chave").get_json()
        registro = _registrar(estado["ana"], "sem-chave")
    finally:
        app.config["WEB_PUSH_VAPID_PRIVADA"] = VAPID_PRIVADA
    _garante(chave == {"ligado": False, "chave_publica": None}, f"chave {chave}")
    _garante(
        registro.status_code == 503 and _erro(registro).get("codigo") == "nao_configurado",
        f"{registro.status_code}",
    )


def preparar() -> None:
    estado["ana"], estado["ana_id"] = _usuario("Ana", RoleName.COMERCIAL)
    estado["bia"], estado["bia_id"] = _usuario("Bia", RoleName.COMERCIAL)
    estado["cris"], estado["cris_id"] = _usuario("Cris", RoleName.CASTING)


def limpar() -> None:
    db.session.rollback()
    db.session.execute(
        text("DELETE FROM push_assinaturas WHERE endpoint LIKE :p"), {"p": ENDPOINT + "%"}
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
        "SELECT count(*) FROM push_assinaturas WHERE endpoint LIKE :p", p=ENDPOINT + "%"
    )[0]
    _garante(sobras == 0, f"sobraram {sobras} aparelhos de teste")


CENARIOS = [
    ("0. cifra contra o vetor oficial do RFC 8291", cen_00),
    ("1. chave pública", cen_01),
    ("2. Ana registra o aparelho", cen_02),
    ("3. mesmo aparelho pela Bia: um registro só", cen_03),
    ("4. desativar", cen_04),
    ("5. Casting e registro inválido (DEVE falhar)", cen_05),
    ("6. mensagem nova sem responsável avisa a equipe", cen_06),
    ("7. mensagem numa conversa da Ana avisa só a Ana", cen_07),
    ("9. Instagram com o nome do perfil e toque em botão (Instagram e WhatsApp)", cen_09),
    ("8. reenvio, eco e reação não avisam (WhatsApp e Instagram)", cen_08),
    ("10. 410 apaga; 500 e aparelho envenenado não cortam os outros", cen_10),
    ("11. alerta de 15 min: o responsável ou a equipe", cen_11),
    ("12. transferência toca no celular do destino", cen_12),
    ("13. ambiente travado (DEVE falhar)", cen_13),
    ("14. sem chaves (DEVE falhar)", cen_14),
    ("15. entrega pela thread (caminho de produção)", cen_15),
]


def main() -> int:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        _garante(SUPRESSAO_DERIVADA is True, "o banco local não travou o aviso no celular sozinho")
        limpar()
        preparar()
    print("Feature 332 — Avisos no celular, contra manto_local")
    try:
        for nome, fn in CENARIOS:
            cenario(nome, fn)
    finally:
        with app.app_context():
            cenario("16. limpeza", limpar)
        webpush.requests = _REAIS["requests"]
        _ic.perfil = _REAIS["perfil"]
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(
        f"\n{ok}/{len(resultados)} OK · escapes de rede: {len(_ESCAPES)}"
        f" · problemas no serviço falso: {len(entrega.problemas)}"
    )
    for problema in entrega.problemas:
        print(f"  ! {problema}")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) and not _ESCAPES and not entrega.problemas else 1


if __name__ == "__main__":
    sys.exit(main())
