"""Verificação da feature 330 — Instagram Direct na caixa de Conversas.

Os cenários da tabela da spec (seção "Verificação"). A Meta NUNCA é chamada: as funções do
`instagram_client` e do `whatsapp_client` viram dublês em memória, e um disjuntor de rede derruba
qualquer conexão de saída que não seja o Postgres local — instalado ANTES de importar o app.

Tudo de teste leva `v330-` (usuários, nomes, mids, a conta e a Página falsas) e IGSIDs que começam
com `330330`. Escrita conferida por **conexão separada**; requisições HTTP **fora** de `app.app_context()`.

Rodar contra o manto_local (PowerShell, na raiz do repositório)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
    $env:PYTHONUTF8 = '1'; .venv\\Scripts\\python.exe specs/330-crm-instagram-direct/verify_330.py [--manter]
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
        raise OSError(f"verify 330: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 330: conexão de saída bloqueada para {_host_de(endereco)}")
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
from app.constants import RoleName  # noqa: E402
from app.models import Role, User  # noqa: E402

PREFIX = "v330-"
SENHA = "verify-330-senha"
SEGREDO = "segredo-do-app-v330"
VERIFICA = "verifica-v330"
CONTA_IG = "v330-conta-ig"
PAGINA_IG = "v330-pagina"
NUMERO_ID = "v330-phone"
NUMERO_MANTO = "5511900000330"
WA_FILTRO = "5511963300001"
IG_A = "3303300000000001"
IG_B = "3303300000000002"
IG_C = "3303300000000003"
IG_D = "3303300000000004"
IG_E = "3303300000000005"
CONTATOS = [IG_A, IG_B, IG_C, IG_D, IG_E, WA_FILTRO]
PASTA_MIDIA = tempfile.mkdtemp(prefix="v330-midia-")
BYTES_DA_FOTO = b"\x89PNG\r\n\x1a\nfoto-v330"
PNG_MINIMO = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

app = create_app()
app.config["TESTING"] = True
app.config.update(
    WHATSAPP_ACCESS_TOKEN="token-falso-v330",
    WHATSAPP_APP_SECRET=SEGREDO,
    WHATSAPP_VERIFY_TOKEN=VERIFICA,
    WHATSAPP_PHONE_NUMBER_ID=NUMERO_ID,
    WHATSAPP_WABA_ID="v330-waba",
    WHATSAPP_AVISO_SINCRONO=True,
    WHATSAPP_SUPPRESS_SEND=False,
    INSTAGRAM_ACCESS_TOKEN="token-ig-falso-v330",
    INSTAGRAM_PAGE_ID=PAGINA_IG,
    INSTAGRAM_ACCOUNT_ID=CONTA_IG,
    CONVERSAS_MEDIA_FOLDER=PASTA_MIDIA,
)
limiter.enabled = False

# ── Dublês da Meta ───────────────────────────────────────────────────────────────────────────────
import app.integracoes.instagram_client as _ic  # noqa: E402
import app.integracoes.whatsapp_client as _wc  # noqa: E402

_REAIS_IG = {nome: getattr(_ic, nome) for nome in ("enviar", "enviar_arquivo", "perfil")}
_REAIS_WA = {
    nome: getattr(_wc, nome) for nome in ("enviar", "marcar_lida", "baixar_midia", "baixar_arquivo")
}


class MetaFalsa:
    """Responde como a Meta, registra cada chamada e nunca sai da máquina."""

    def __init__(self) -> None:
        self.chamadas: dict[str, list] = {
            "enviar": [],
            "enviar_arquivo": [],
            "perfil": [],
            "baixar": [],
            "wa_enviar": [],
        }
        self.seq = 0
        self.recusar: _wc.WhatsappErro | None = None
        self.perfil_indisponivel: set[str] = set()

    def _mid(self) -> str:
        self.seq += 1
        return (
            f"{PREFIX}mid-enviado-" + "x" * 140 + f"-{self.seq}"
        )  # mid longo, como o do Instagram

    def _talvez_recusar(self) -> None:
        if self.recusar is not None:
            erro, self.recusar = self.recusar, None
            raise erro

    def enviar(self, conexao, corpo):
        self.chamadas["enviar"].append(corpo)
        self._talvez_recusar()
        return {"id": self._mid()}

    def enviar_arquivo(self, conexao, destino, tipo, dados, mime, nome, extras=None):
        self.chamadas["enviar_arquivo"].append(
            {
                "destino": destino,
                "tipo": tipo,
                "dados": dados,
                "mime": mime,
                "nome": nome,
                "extras": extras,
            }
        )
        self._talvez_recusar()
        return {"id": self._mid()}

    def perfil(self, conexao, igsid):
        self.chamadas["perfil"].append(igsid)
        if igsid in self.perfil_indisponivel:
            raise _wc.WhatsappIndisponivel("perfil fora (dublê)")
        return {"nome": f"{PREFIX}Perfil {igsid[-1]}", "usuario": f"v330.perfil{igsid[-1]}"}

    def baixar_midia(self, conexao, url, limite_bytes):
        self.chamadas["baixar"].append(url)
        return BYTES_DA_FOTO

    def baixar_arquivo(self, conexao, url, limite_bytes):
        self.chamadas["baixar"].append(url)
        self.chamadas.setdefault("token_do_download", []).append(conexao.token)
        return BYTES_DA_FOTO, "image/png"

    def wa_enviar(self, conexao, corpo):
        self.chamadas["wa_enviar"].append(corpo)
        return {"id": f"wamid.{PREFIX}{len(self.chamadas['wa_enviar'])}", "wa_id": corpo.get("to")}

    def wa_marcar_lida(self, conexao, wamid):
        return None


meta = MetaFalsa()
_ic.enviar, _ic.enviar_arquivo, _ic.perfil = meta.enviar, meta.enviar_arquivo, meta.perfil
_wc.enviar, _wc.marcar_lida, _wc.baixar_midia = (
    meta.wa_enviar,
    meta.wa_marcar_lida,
    meta.baixar_midia,
)
_wc.baixar_arquivo = meta.baixar_arquivo

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


def _erro(r) -> dict:
    return (r.get_json() or {}).get("error") or {}


def _assinado(corpo: dict, rota: str, segredo: str | None = SEGREDO):
    bruto = json.dumps(corpo).encode()
    cabecalhos = {"Content-Type": "application/json"}
    if segredo is not None:
        cabecalhos["X-Hub-Signature-256"] = (
            "sha256=" + hmac.new(segredo.encode(), bruto, hashlib.sha256).hexdigest()
        )
    with app.test_client() as c:
        return c.post(rota, data=bruto, headers=cabecalhos)


def _agora_ms() -> int:
    return int(time.time() * 1000)


def _aviso_ig(itens: list[dict], chave: str = "messaging") -> dict:
    return {"object": "instagram", "entry": [{"id": CONTA_IG, "time": _agora_ms(), chave: itens}]}


def _item(igsid: str, mensagem: dict | None = None, eco: bool = False, **outros) -> dict:
    remetente, destino = (CONTA_IG, igsid) if eco else (igsid, CONTA_IG)
    item = {"sender": {"id": remetente}, "recipient": {"id": destino}, "timestamp": _agora_ms()}
    if mensagem is not None:
        item["message"] = {**mensagem, **({"is_echo": True} if eco else {})}
    item.update(outros)
    return item


def _post_ig(itens: list[dict], chave: str = "messaging", segredo: str | None = SEGREDO):
    return _assinado(_aviso_ig(itens, chave), "/api/webhooks/instagram", segredo)


def _recebida(igsid: str, mid: str, texto: str = "Oi! Vi o reels de vocês.") -> int:
    r = _post_ig([_item(igsid, {"mid": f"{PREFIX}{mid}", "text": texto})])
    _garante(r.status_code == 200, f"aviso → {r.status_code}")
    return _conversa(igsid).id


def _conversa(contato: str):
    return _no_banco(
        "SELECT id, canal, telefone, client_id, nome_perfil, usuario, perfil_em, responsavel_id, "
        "aguardando_desde, ultima_recebida_em FROM conversas WHERE contato_id=:c",
        c=contato,
    )


def _mensagens(conversa_id: int):
    return _no_banco_todas(
        "SELECT externo_id, direcao, tipo, texto, situacao, origem, erro_motivo FROM conversa_mensagens "
        "WHERE conversa_id=:i ORDER BY momento, id",
        i=conversa_id,
    )


def _texto(email: str, conversa_id: int, chave: str, texto: str = "Oi! Tudo certo para a festa?"):
    return _chamar(
        email,
        "post",
        f"/api/conversas/{conversa_id}/mensagens",
        {"texto": texto, "chave_envio": f"{PREFIX}{chave}"},
    )


def _arquivo(email: str, conversa_id: int, chave: str, dados: bytes, nome: str, mime: str):
    return _chamar(
        email,
        "post",
        f"/api/conversas/{conversa_id}/mensagens",
        data={"chave_envio": f"{PREFIX}{chave}", "arquivo": (io.BytesIO(dados), nome, mime)},
        content_type="multipart/form-data",
    )


def _ultima_da_cliente(conversa_id: int, atras: timedelta) -> None:
    momento = datetime.now(UTC).replace(tzinfo=None) - atras
    _no_banco_escrever(
        "UPDATE conversas SET ultima_recebida_em=:m WHERE id=:i", m=momento, i=conversa_id
    )


def _cartao(email: str, conversa_id: int) -> dict:
    return _chamar(email, "get", f"/api/conversas/{conversa_id}").get_json()["conversa"]


# ── História 1 — o Direct chega ────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    with app.test_client() as c:
        ok = c.get(
            f"/api/webhooks/instagram?hub.mode=subscribe&hub.verify_token={VERIFICA}&hub.challenge=330"
        )
        errado = c.get(
            "/api/webhooks/instagram?hub.mode=subscribe&hub.verify_token=x&hub.challenge=330"
        )
    _garante(
        ok.status_code == 200 and ok.get_data(as_text=True) == "330", f"desafio → {ok.status_code}"
    )
    _garante(errado.status_code == 404, f"token errado → {errado.status_code} (esperado 404)")


def cen_02() -> None:
    estado["a"] = _recebida(IG_A, "a-1")
    conv = _conversa(IG_A)
    _garante(conv.canal == "instagram", f"canal {conv.canal}")
    _garante(conv.telefone is None and conv.client_id is None, "o IGSID virou telefone ou ficha")
    _garante(
        conv.nome_perfil == f"{PREFIX}Perfil 1" and conv.usuario == "v330.perfil1", f"perfil {conv}"
    )
    _garante(conv.aguardando_desde is not None, "a recebida não abriu a espera")
    cartao = _cartao(estado["ana"], estado["a"])
    _garante(
        cartao["canal"] == "instagram" and cartao["usuario"] == "v330.perfil1", f"cartão {cartao}"
    )
    _garante(cartao["janela"] == "aberta", f"janela {cartao['janela']}")


def cen_03() -> None:
    _recebida(IG_A, "a-1")
    n = _no_banco("SELECT count(*) FROM conversa_mensagens WHERE externo_id=:m", m=f"{PREFIX}a-1")[
        0
    ]
    _garante(n == 1, f"{n} mensagens com o mesmo mid")


def cen_04() -> None:
    corpo = [_item(IG_A, {"mid": f"{PREFIX}forjado", "text": "forjado"})]
    errado = _post_ig(corpo, segredo="errado")
    sem = _post_ig(corpo, segredo=None)
    _garante(
        errado.status_code == 404 and sem.status_code == 404,
        f"→ {errado.status_code}/{sem.status_code}",
    )
    n = _no_banco(
        "SELECT count(*) FROM whatsapp_avisos WHERE corpo LIKE :p", p=f"%{PREFIX}forjado%"
    )[0]
    _garante(n == 0, "aviso forjado foi gravado")


def cen_05() -> None:
    url = "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=v330"
    _post_ig(
        [
            _item(
                IG_A,
                {
                    "mid": f"{PREFIX}a-foto",
                    "attachments": [{"type": "image", "payload": {"url": url}}],
                },
            )
        ]
    )
    linha = _no_banco(
        "SELECT d.id, d.estado, d.caminho FROM conversa_mensagens m JOIN conversa_midias d "
        "ON d.mensagem_id=m.id WHERE m.externo_id=:m",
        m=f"{PREFIX}a-foto",
    )
    _garante(linha is not None and linha.estado == "guardada", f"mídia {linha}")
    _garante(url in meta.chamadas["baixar"], "não baixou pelo link do anexo")
    _garante(
        (Path(PASTA_MIDIA) / linha.caminho).read_bytes() == BYTES_DA_FOTO, "cópia local errada"
    )
    r = _chamar(estado["ana"], "get", f"/api/conversas/midia/{linha.id}")
    _garante(r.status_code == 200, f"mídia servida → {r.status_code}")
    _garante(meta.chamadas["token_do_download"][-1] == "", "o download do Instagram levou o token")
    url2 = "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=v330-2"
    duas = [{"type": "image", "payload": {"url": url}}, {"type": "image", "payload": {"url": url2}}]
    _post_ig([_item(IG_A, {"mid": f"{PREFIX}a-duas", "attachments": duas})])
    segunda = _no_banco(
        "SELECT d.estado FROM conversa_mensagens m JOIN conversa_midias d ON d.mensagem_id=m.id "
        "WHERE m.externo_id=:m",
        m=f"{PREFIX}a-duas#1",
    )
    _garante(segunda is not None and segunda.estado == "guardada", f"segundo anexo {segunda}")
    _garante(meta.chamadas["baixar"][-1] == url2, "o segundo anexo baixou o link errado")


def cen_06() -> None:
    anexos = [
        {"type": "share", "payload": {"url": "https://instagram.com/p/v330"}},
        {"type": "ig_reel", "payload": {"url": "https://instagram.com/reel/v330"}},
        {"type": "ephemeral", "payload": {}},
    ]
    _post_ig(
        [
            _item(IG_A, {"mid": f"{PREFIX}a-partes", "attachments": anexos}),
            _item(IG_A, {"mid": f"{PREFIX}a-nao", "is_unsupported": True}),
            _item(
                IG_A,
                {
                    "mid": f"{PREFIX}a-story",
                    "text": "Que lindo!",
                    "reply_to": {"story": {"id": "s"}},
                },
            ),
        ]
    )
    textos = {m.externo_id: m.texto for m in _mensagens(estado["a"])}
    _garante(textos.get(f"{PREFIX}a-partes") == "Compartilhou uma publicação.", f"{textos}")
    _garante(textos.get(f"{PREFIX}a-partes#1") == "Compartilhou um reels.", f"{textos}")
    _garante(
        textos.get(f"{PREFIX}a-partes#2") == "Mídia temporária. Abra no Instagram para ver.",
        f"{textos}",
    )
    _garante("Abra no Instagram" in (textos.get(f"{PREFIX}a-nao") or ""), f"{textos}")
    _garante(
        (textos.get(f"{PREFIX}a-story") or "").startswith("Respondeu ao seu story."), f"{textos}"
    )
    link_story = "https://instagram.com/stories/v330"
    _post_ig(
        [
            _item(
                IG_A,
                {
                    "mid": f"{PREFIX}a-mencao",
                    "attachments": [{"type": "story_mention", "payload": {"url": link_story}}],
                },
            )
        ]
    )
    detalhe = _chamar(estado["ana"], "get", f"/api/conversas/{estado['a']}").get_json()["mensagens"]
    mencao = next((m for m in detalhe if m["texto"] == "Mencionou a Manto no story."), None)
    _garante(mencao is not None and mencao.get("link") == link_story, f"menção {mencao}")
    publicacao = next((m for m in detalhe if m["texto"] == "Compartilhou uma publicação."), None)
    _garante(
        publicacao and publicacao.get("link") == "https://instagram.com/p/v330",
        "sem o link da publicação",
    )


def cen_07() -> None:
    _recebida(IG_A, "a-apagar", "mensagem errada")
    _post_ig([_item(IG_A, {"mid": f"{PREFIX}a-apagar", "is_deleted": True})])
    linha = _no_banco(
        "SELECT texto FROM conversa_mensagens WHERE externo_id=:m", m=f"{PREFIX}a-apagar"
    )
    _garante(linha.texto == "Mensagem apagada pela cliente.", f"texto {linha.texto!r}")
    foto = "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=v330-apagar"
    _post_ig(
        [
            _item(
                IG_A,
                {
                    "mid": f"{PREFIX}a-foto-apagar",
                    "attachments": [{"type": "image", "payload": {"url": foto}}],
                },
            )
        ]
    )
    _post_ig([_item(IG_A, {"mid": f"{PREFIX}a-foto-apagar", "is_deleted": True})])
    apagada = _no_banco(
        "SELECT m.tipo, m.texto, d.id AS midia FROM conversa_mensagens m "
        "LEFT JOIN conversa_midias d ON d.mensagem_id=m.id WHERE m.externo_id=:m",
        m=f"{PREFIX}a-foto-apagar",
    )
    _garante(
        apagada.midia is None and apagada.texto == "Mensagem apagada pela cliente.", f"{apagada}"
    )
    previa = _no_banco(
        "SELECT ultima_previa FROM conversas WHERE id=:i", i=estado["a"]
    ).ultima_previa
    _garante(previa == "Mensagem apagada pela cliente.", f"prévia {previa!r}")


def cen_09() -> None:
    meta.perfil_indisponivel.add(IG_B)
    estado["b"] = _recebida(IG_B, "b-1")
    cartao = _cartao(estado["ana"], estado["b"])
    _garante(cartao["nome"] == "Contato do Instagram", f"nome {cartao['nome']!r}")
    _garante(_conversa(IG_B).perfil_em is not None, "não carimbou a tentativa")
    antes = meta.chamadas["perfil"].count(IG_B)
    _recebida(IG_B, "b-2")
    _garante(meta.chamadas["perfil"].count(IG_B) == antes, "buscou o perfil de novo no mesmo dia")
    meta.perfil_indisponivel.discard(IG_B)
    _no_banco_escrever(
        "UPDATE conversas SET perfil_em = perfil_em - interval '25 hours' WHERE id=:i",
        i=estado["b"],
    )
    _recebida(IG_B, "b-3")
    _garante(
        _conversa(IG_B).nome_perfil == f"{PREFIX}Perfil 2", "não buscou o perfil depois de um dia"
    )


# ── História 2 — responder ─────────────────────────────────────────────────────────────────────────


def cen_10() -> None:
    r = _texto(estado["ana"], estado["a"], "c10")
    _garante(r.status_code == 201, f"envio → {r.status_code} {r.get_data(as_text=True)[:200]}")
    corpo = meta.chamadas["enviar"][-1]
    _garante(corpo["recipient"] == {"id": IG_A}, f"destino {corpo}")
    _garante(corpo["message"] == {"text": "Oi! Tudo certo para a festa?"}, f"mensagem {corpo}")
    _garante("tag" not in corpo, "marca humana dentro das 24 h")
    linha = _no_banco(
        "SELECT externo_id, situacao FROM conversa_mensagens WHERE chave_envio=:c", c=f"{PREFIX}c10"
    )
    _garante(linha.situacao == "enviada" and len(linha.externo_id) > 128, f"linha {linha}")
    estado["mid_c10"] = linha.externo_id
    conv = _conversa(IG_A)
    _garante(conv.responsavel_id == estado["ana_id"], "a Ana não virou responsável")
    _garante(conv.aguardando_desde is None, "a resposta não encerrou a espera")


def cen_11() -> None:
    _ultima_da_cliente(estado["a"], timedelta(hours=30))
    _garante(_cartao(estado["bia"], estado["a"])["janela"] == "humana", "janela não é humana")
    r = _texto(estado["bia"], estado["a"], "c11")
    _garante(r.status_code == 201, f"envio → {r.status_code} {r.get_data(as_text=True)[:200]}")
    corpo = meta.chamadas["enviar"][-1]
    _garante(
        corpo.get("messaging_type") == "MESSAGE_TAG" and corpo.get("tag") == "HUMAN_AGENT",
        f"{corpo}",
    )


def cen_12() -> None:
    _ultima_da_cliente(estado["a"], timedelta(days=8))
    cartao = _cartao(estado["ana"], estado["a"])
    _garante(cartao["janela"] == "fechada" and cartao["janela_aberta"] is False, f"cartão {cartao}")
    antes = len(meta.chamadas["enviar"])
    r = _texto(estado["ana"], estado["a"], "c12")
    _garante(r.status_code == 409, f"depois de 7 dias → {r.status_code} (esperado 409)")
    _garante(_erro(r).get("codigo") == "janela_fechada", f"{_erro(r)}")
    _garante("7 dias" in (_erro(r).get("message") or ""), f"texto {_erro(r)}")
    _garante(len(meta.chamadas["enviar"]) == antes, "algo saiu para a Meta")
    modelo = _chamar(
        estado["ana"],
        "post",
        f"/api/conversas/{estado['a']}/modelo",
        {"nome": "x", "idioma": "pt_BR", "variaveis": [], "chave_envio": f"{PREFIX}c12m"},
    )
    _garante(
        modelo.status_code == 409 and _erro(modelo).get("codigo") == "sem_modelos",
        f"{modelo.status_code}",
    )
    _ultima_da_cliente(estado["a"], timedelta(minutes=1))


def cen_13() -> None:
    r = _arquivo(estado["ana"], estado["a"], "c13", PNG_MINIMO, "salao.png", "image/png")
    _garante(r.status_code == 201, f"foto → {r.status_code} {r.get_data(as_text=True)[:200]}")
    envio = meta.chamadas["enviar_arquivo"][-1]
    _garante(
        envio["tipo"] == "image" and envio["mime"] == "image/png",
        f"{envio['tipo']} {envio['mime']}",
    )
    _garante(envio["destino"] == {"id": IG_A}, f"destino {envio['destino']}")
    linha = _no_banco(
        "SELECT d.estado FROM conversa_mensagens m JOIN conversa_midias d ON d.mensagem_id=m.id "
        "WHERE m.chave_envio=:c",
        c=f"{PREFIX}c13",
    )
    _garante(linha is not None and linha.estado == "guardada", "sem cópia local")


def _webm_de_teste() -> bytes | None:
    from app.impressoes3d import video_ops

    with app.app_context():
        ffmpeg = video_ops.caminho_do_ffmpeg()
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
            check=False,
        )
        if r.returncode == 0 and saida.is_file():
            return saida.read_bytes()
    return None


def cen_14() -> None:
    dados = _webm_de_teste()
    _garante(dados is not None, "PULADO: sem ffmpeg nesta máquina, o áudio não foi conferido")
    r = _arquivo(estado["ana"], estado["a"], "c14", dados, "audio.webm", "audio/webm;codecs=opus")
    _garante(r.status_code == 201, f"áudio → {r.status_code} {r.get_data(as_text=True)[:200]}")
    envio = meta.chamadas["enviar_arquivo"][-1]
    _garante(
        envio["tipo"] == "audio" and envio["mime"] == "audio/mp4",
        f"{envio['tipo']} {envio['mime']}",
    )
    _garante(envio["nome"].endswith(".m4a"), f"nome {envio['nome']}")
    _garante(envio["dados"][4:8] == b"ftyp", "o arquivo enviado não é mp4/m4a")


def cen_15() -> None:
    planilha = _arquivo(
        estado["ana"],
        estado["a"],
        "c15a",
        b"PK\x03\x04planilha",
        "custos.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    _garante(planilha.status_code == 422, f"planilha → {planilha.status_code} (esperado 422)")
    _garante(
        "Instagram" in (_erro(planilha).get("fields") or {}).get("arquivo", ""),
        f"{_erro(planilha)}",
    )
    grande = _arquivo(
        estado["ana"],
        estado["a"],
        "c15b",
        PNG_MINIMO + b"\x00" * (8 * 1024 * 1024),
        "g.png",
        "image/png",
    )
    _garante(grande.status_code == 422, f"foto de 8 MB+ → {grande.status_code} (esperado 422)")
    longo = _texto(estado["ana"], estado["a"], "c15c", "ã" * 501)
    _garante(
        longo.status_code == 422 and "texto" in (_erro(longo).get("fields") or {}),
        "texto > 1.000 bytes",
    )


def cen_16() -> None:
    visto = _item(IG_A, read={"mid": estado["mid_c10"]})
    visto["timestamp"] = _agora_ms() - 3_600_000  # horário antigo: só o `mid` decide
    _post_ig([visto])
    linha = _no_banco(
        "SELECT situacao FROM conversa_mensagens WHERE externo_id=:m", m=estado["mid_c10"]
    )
    _garante(linha.situacao == "lida", f"situação {linha.situacao}")


def cen_17() -> None:
    _ultima_da_cliente(estado["a"], timedelta(hours=30))
    meta.recusar = _wc.WhatsappRecusou("permissão (dublê)", status=400, code=10)
    r = _texto(estado["ana"], estado["a"], "c17")
    _garante(
        r.status_code == 201 and r.get_json()["mensagem"]["situacao"] == "falhou",
        f"{r.status_code}",
    )
    motivo = _no_banco(
        "SELECT erro_motivo FROM conversa_mensagens WHERE chave_envio=:c", c=f"{PREFIX}c17"
    )[0]
    _garante(
        motivo == "A Meta ainda não liberou a resposta depois de 24 horas no Instagram.",
        f"{motivo!r}",
    )
    _ultima_da_cliente(estado["a"], timedelta(minutes=1))


def cen_17b() -> None:
    meta.recusar = _wc.WhatsappRecusou("outro app (dublê)", status=400, code=10, subcode=2018300)
    r = _texto(estado["ana"], estado["a"], "c17b")
    _garante(r.status_code == 201, f"→ {r.status_code}")
    motivo = _no_banco(
        "SELECT erro_motivo FROM conversa_mensagens WHERE chave_envio=:c", c=f"{PREFIX}c17b"
    )[0]
    _garante("outro app no Instagram" in (motivo or ""), f"{motivo!r}")


def cen_08() -> None:
    estado["c"] = _recebida(IG_C, "c-1", "Quanto custa?")
    _no_banco_escrever("UPDATE conversas SET aguardando_desde=NULL WHERE id=:i", i=estado["c"])
    _post_ig(
        [
            _item(IG_C, reaction={"mid": f"{PREFIX}c-1", "action": "react", "emoji": "❤"}),
            _item(IG_C, reaction={"mid": f"{PREFIX}c-1", "action": "unreact"}),
        ]
    )
    textos = [m.texto for m in _mensagens(estado["c"]) if m.tipo == "reacao"]
    _garante(textos == ["Reagiu com ❤", "Reação removida."], f"reações {textos}")
    _garante(_conversa(IG_C).aguardando_desde is None, "a reação abriu a espera")


# ── História 3 — piloto ao lado do Kommo ──────────────────────────────────────────────────────────


def cen_18() -> None:
    estado["d"] = _recebida(IG_D, "d-1", "Vocês fazem festa de 15 anos?")
    _post_ig([_item(IG_D, {"mid": f"{PREFIX}d-eco", "text": "Fazemos sim!"}, eco=True)])
    eco = _no_banco(
        "SELECT direcao, origem FROM conversa_mensagens WHERE externo_id=:m", m=f"{PREFIX}d-eco"
    )
    _garante(eco is not None and eco.direcao == "enviada" and eco.origem == "outro", f"eco {eco}")
    conv = _conversa(IG_D)
    _garante(conv.aguardando_desde is None, "o eco não encerrou a espera")
    _garante(conv.responsavel_id is None, "o eco atribuiu responsável")


def cen_18b() -> None:
    _post_ig([_item(IG_E, {"mid": f"{PREFIX}e-standby", "text": "Olá"})], chave="standby")
    conv = _conversa(IG_E)
    _garante(conv is not None, "a mensagem em espera não foi gravada")
    estado["e"] = conv.id
    _garante(len(_mensagens(conv.id)) == 1, "standby gravou errado")


def cen_19() -> None:
    _post_ig(
        [_item(IG_A, {"mid": estado["mid_c10"], "text": "Oi! Tudo certo para a festa?"}, eco=True)]
    )
    n = _no_banco(
        "SELECT count(*) FROM conversa_mensagens WHERE externo_id=:m", m=estado["mid_c10"]
    )[0]
    _garante(n == 1, f"o eco da própria mensagem duplicou ({n})")


def cen_20() -> None:
    app.config["INSTAGRAM_ACCESS_TOKEN"] = ""
    try:
        r = _post_ig([_item(IG_A, {"mid": f"{PREFIX}desligado", "text": "x"})])
        with app.test_client() as c:
            g = c.get(
                f"/api/webhooks/instagram?hub.mode=subscribe&hub.verify_token={VERIFICA}&hub.challenge=1"
            )
        envio = _texto(estado["ana"], estado["a"], "c20")
        lista = _chamar(estado["ana"], "get", "/api/conversas").get_json()
    finally:
        app.config["INSTAGRAM_ACCESS_TOKEN"] = "token-ig-falso-v330"
    _garante(
        r.status_code == 404 and g.status_code == 404,
        f"webhook desligado → {r.status_code}/{g.status_code}",
    )
    _garante(
        envio.status_code == 503 and _erro(envio).get("codigo") == "nao_configurado",
        f"{envio.status_code}",
    )
    _garante("Instagram" in (_erro(envio).get("message") or ""), f"{_erro(envio)}")
    _garante(
        "instagram" not in (lista.get("canais_ligados") or []),
        f"canais {lista.get('canais_ligados')}",
    )


def cen_21() -> None:
    for metodo, url, corpo in (
        ("get", "/api/conversas?canal=instagram", None),
        (
            "post",
            f"/api/conversas/{estado['a']}/mensagens",
            {"texto": "x", "chave_envio": f"{PREFIX}c21"},
        ),
    ):
        r = _chamar(estado["cris"], metodo, url, corpo)
        _garante(r.status_code == 403, f"Casting {metodo} {url} → {r.status_code} (esperado 403)")


def cen_22() -> None:
    wa = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "v330-waba",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": NUMERO_MANTO,
                                "phone_number_id": NUMERO_ID,
                            },
                            "contacts": [{"profile": {"name": f"{PREFIX}Zap"}, "wa_id": WA_FILTRO}],
                            "messages": [
                                {
                                    "from": WA_FILTRO,
                                    "id": f"wamid.{PREFIX}in-zap",
                                    "timestamp": str(int(time.time())),
                                    "type": "text",
                                    "text": {"body": "oi"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    _garante(_assinado(wa, "/api/webhooks/whatsapp").status_code == 200, "aviso do WhatsApp")
    so_ig = _chamar(estado["ana"], "get", "/api/conversas?canal=instagram").get_json()
    so_wa = _chamar(estado["ana"], "get", "/api/conversas?canal=whatsapp").get_json()
    _garante(
        so_ig["conversas"] and all(c["canal"] == "instagram" for c in so_ig["conversas"]),
        "filtro IG",
    )
    _garante(
        any(c["id"] == estado["a"] for c in so_ig["conversas"]), "a conversa A sumiu do filtro IG"
    )
    _garante(
        all(c["canal"] == "whatsapp" for c in so_wa["conversas"]),
        "filtro WhatsApp trouxe Instagram",
    )
    _garante(
        set(so_ig.get("canais_ligados") or []) == {"whatsapp", "instagram"},
        f"{so_ig.get('canais_ligados')}",
    )
    invalido = _chamar(estado["ana"], "get", "/api/conversas?canal=telegram")
    _garante(invalido.status_code == 422, f"canal inválido → {invalido.status_code}")


def cen_06b() -> None:
    _post_ig(
        [
            _item(
                IG_C,
                postback={"mid": f"{PREFIX}c-botao", "title": "Quero orçamento", "payload": "X"},
            )
        ]
    )
    conv = _conversa(IG_C)
    textos = [m.texto for m in _mensagens(conv.id)]
    _garante('Tocou em "Quero orçamento".' in textos, f"textos {textos}")
    _garante(conv.aguardando_desde is not None, "o toque no botão não abriu a espera")


def cen_19b() -> None:
    _no_banco_escrever(
        "INSERT INTO conversa_mensagens (conversa_id, direcao, tipo, texto, chave_envio, situacao, origem, "
        "momento, created_at) VALUES (:c, 'enviada', 'texto', 'em voo', :k, 'pendente', 'plataforma', "
        "now() at time zone 'utc', now() at time zone 'utc')",
        c=estado["d"],
        k=f"{PREFIX}em-voo",
    )
    try:
        _post_ig([_item(IG_D, {"mid": f"{PREFIX}d-eco-cedo", "text": "chegou antes"}, eco=True)])
        n = _no_banco(
            "SELECT count(*) FROM conversa_mensagens WHERE externo_id=:m", m=f"{PREFIX}d-eco-cedo"
        )[0]
        estado_aviso = _no_banco(
            "SELECT estado FROM whatsapp_avisos WHERE corpo LIKE :p ORDER BY id DESC",
            p=f"%{PREFIX}d-eco-cedo%",
        ).estado
    finally:
        _no_banco_escrever(
            "DELETE FROM conversa_mensagens WHERE chave_envio=:k", k=f"{PREFIX}em-voo"
        )
    _garante(
        n == 0 and estado_aviso == "pendente",
        f"eco antes do mid: {n} gravadas, aviso {estado_aviso}",
    )


def cen_20b() -> None:
    app.config["WHATSAPP_SUPPRESS_SEND"] = True
    try:
        r = _texto(estado["ana"], estado["a"], "c20b")
    finally:
        app.config["WHATSAPP_SUPPRESS_SEND"] = False
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "envio_travado",
        f"travado → {r.status_code}",
    )
    _garante("Instagram" in (_erro(r).get("message") or ""), f"{_erro(r)}")


def cen_20c() -> None:
    import app as pacote
    import app.conversas.varredura as varredura

    passadas = []
    original = varredura.ciclo_de_varredura
    app.config["WHATSAPP_ACCESS_TOKEN"] = ""
    varredura.ciclo_de_varredura = lambda: passadas.append(True) or {}
    try:
        me = _chamar(estado["ana"], "get", "/api/auth/me").get_json()
        lista = _chamar(estado["ana"], "get", "/api/conversas").get_json()
        pacote._passada_whatsapp(app)
    finally:
        varredura.ciclo_de_varredura = original
        app.config["WHATSAPP_ACCESS_TOKEN"] = "token-falso-v330"
    _garante(me.get("conversas_ligadas") is True, "só o Instagram ligado não abre o menu")
    _garante(
        lista.get("configurado") is True and lista.get("canais_ligados") == ["instagram"],
        f"{lista.get('canais_ligados')}",
    )
    _garante(passadas, "a varredura não roda com só o Instagram ligado")


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
        text("DELETE FROM whatsapp_avisos WHERE corpo LIKE :p OR corpo LIKE :q"),
        {"p": f"%{CONTA_IG}%", "q": f"%{NUMERO_ID}%"},
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
    avisos = _no_banco(
        "SELECT count(*) FROM whatsapp_avisos WHERE corpo LIKE :p", p=f"%{CONTA_IG}%"
    )[0]
    _garante(sobras == 0 and avisos == 0, f"sobraram {sobras} conversas e {avisos} avisos de teste")


CENARIOS = [
    ("1. desafio de verificação (token errado DEVE falhar)", cen_01),
    ("2. texto do Instagram: conversa, perfil, espera, sem telefone", cen_02),
    ("3. mesmo aviso reenviado não duplica", cen_03),
    ("4. assinatura errada ou ausente (DEVE falhar)", cen_04),
    ("5. foto recebida baixada pelo link e servida", cen_05),
    ("6. publicação, reels, efêmera, não suportada, story e menção", cen_06),
    ("7. cliente apaga a mensagem", cen_07),
    ("9. perfil indisponível e nova busca depois de um dia", cen_09),
    ("10. Ana responde na janela: corpo, responsável, espera", cen_10),
    ("11. entre 24 h e 7 dias: marca de resposta humana", cen_11),
    ("12. depois de 7 dias e modelo no Instagram (DEVE falhar)", cen_12),
    ("13. foto enviada", cen_13),
    ("14. áudio webm sai como m4a", cen_14),
    ("15. planilha, foto grande e texto longo (DEVE falhar)", cen_15),
    ("16. visto da cliente", cen_16),
    ("17. Meta recusa a marca humana", cen_17),
    ("17b. Meta recusa porque a conversa está com outro app", cen_17b),
    ("8. reação e reação removida não abrem espera", cen_08),
    ("6b. toque em botão abre a conversa e a espera", cen_06b),
    ("18. eco de outro app", cen_18),
    ("18b. mensagem em espera (standby)", cen_18b),
    ("19. eco da própria mensagem não duplica", cen_19),
    ("19b. eco antes do mid do envio volta à fila", cen_19b),
    ("20. canal desligado (DEVE falhar)", cen_20),
    ("20b. envio travado no Instagram (DEVE falhar)", cen_20b),
    ("20c. só o Instagram ligado: menu e varredura", cen_20c),
    ("21. Casting no Instagram (DEVE falhar)", cen_21),
    ("22. filtro por canal", cen_22),
]


def main() -> int:
    manter = "--manter" in sys.argv[1:]
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        limpar()
        preparar()
    print("Feature 330 — Instagram Direct, contra manto_local")
    try:
        for nome, fn in CENARIOS:
            cenario(nome, fn)
    finally:
        if manter:
            print(f"  --manter: dados {PREFIX} ficam para conferir a tela (senha: {SENHA})")
        else:
            with app.app_context():
                cenario("23. limpeza", limpar)
        for nome, fn in _REAIS_IG.items():
            setattr(_ic, nome, fn)
        for nome, fn in _REAIS_WA.items():
            setattr(_wc, nome, fn)
        shutil.rmtree(PASTA_MIDIA, ignore_errors=True)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK · escapes de rede: {len(_ESCAPES)}")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) and not _ESCAPES else 1


if __name__ == "__main__":
    sys.exit(main())
