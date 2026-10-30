"""Verificação da feature 325 — Conversas: o WhatsApp da Manto dentro da Plataforma.

Os 21 cenários da tabela da spec (seção "Verificação"). A Meta NUNCA é chamada: as funções de
`app.integracoes.whatsapp_client` viram um dublê em memória (`MetaFalsa`), e um disjuntor de rede
derruba qualquer conexão de saída que não seja o Postgres local — instalado ANTES de importar o
app, em `socket.socket.connect` E em `socket.create_connection` (molde do verify_317).

Tudo de teste leva `v325-`: nome de perfil das conversas, wamids (`wamid.v325-…`), ids de mídia,
o `phone_number_id` falso (é por ele que os avisos crus são achados na limpeza), usuários e a
ficha de cliente. A mídia vai para uma pasta temporária, nunca para `instance/`.

Escrita conferida por **conexão separada** e requisições HTTP **fora** de `app.app_context()`.

Rodar contra o manto_local (PowerShell, na raiz do repositório)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
    $env:PYTHONUTF8 = '1'; .venv\\Scripts\\python.exe specs/325-crm-whatsapp-fundacao/verify_325.py [--so=1,2] [--manter]

`--manter` deixa uma conversa de demonstração (e os usuários) para conferir a tela; rode de novo
sem a flag para limpar.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import shutil
import socket
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
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
        raise OSError(f"verify 325: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 325: conexão de saída bloqueada para {_host_de(endereco)}")
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
from app.models import Client, Role, User  # noqa: E402

PREFIX = "v325-"
SENHA = "verify-325-senha"
SEGREDO = "segredo-do-app-v325"
VERIFICA = "verifica-v325"
NUMERO_ID = "v325-phone"
NUMERO_MANTO = "5511900000325"
# Celular de cliente (8 dígitos finais começando com 8 = celular): a ficha guarda COM o 9 e a Meta
# manda SEM o 9 — é o caso do nono dígito (cenário 4).
TEL_FICHA = "5511987325325"
WA_DA_FICHA = "551187325325"
WA_NOVO = "5511963250001"
WA_ECO = "5511963250002"
WA_MIDIA = "5511963250003"
WA_GRUPO = "5511963250004"
PASTA_MIDIA = tempfile.mkdtemp(prefix="v325-midia-")

app = create_app()
# A trava REAL, antes de qualquer override: contra o `manto_local` ela tem de nascer ligada (T050).
TRAVA_DE_FABRICA = app.config.get("WHATSAPP_SUPPRESS_SEND")
app.config["TESTING"] = True
app.config["WHATSAPP_ACCESS_TOKEN"] = "token-falso-v325"
app.config["WHATSAPP_APP_SECRET"] = SEGREDO
app.config["WHATSAPP_VERIFY_TOKEN"] = VERIFICA
app.config["WHATSAPP_PHONE_NUMBER_ID"] = NUMERO_ID
app.config["WHATSAPP_WABA_ID"] = "v325-waba"
app.config["WHATSAPP_AVISO_SINCRONO"] = True
# A "liberação de teste" do quickstart §3, mas com o dublê no lugar da Meta (e o disjuntor atrás).
app.config["WHATSAPP_SUPPRESS_SEND"] = False
app.config["CONVERSAS_MEDIA_FOLDER"] = PASTA_MIDIA
limiter.enabled = False

# ── O dublê da Meta ──────────────────────────────────────────────────────────────────────────────
import app.integracoes.whatsapp_client as _wc  # noqa: E402

_REAIS = {
    nome: getattr(_wc, nome)
    for nome in (
        "enviar",
        "marcar_lida",
        "subir_midia",
        "consultar_midia",
        "baixar_midia",
        "listar_modelos",
    )
}
BYTES_DA_FOTO = b"\x89PNG\r\n\x1a\nfoto-do-salao-v325"


class MetaFalsa:
    """Responde como a Meta, registra cada chamada e nunca sai da máquina."""

    def __init__(self) -> None:
        self.chamadas: dict[str, list] = {nome: [] for nome in _REAIS}
        self.seq = 0
        self.falhar_download = 0  # quantas consultas de mídia falham antes de funcionar

    def _travada(self, conexao) -> None:
        if conexao.travada:
            raise _wc.WhatsappTravado("travado (dublê)")

    def enviar(self, conexao, corpo):
        self._travada(conexao)
        self.chamadas["enviar"].append(corpo)
        self.seq += 1
        return {"id": f"wamid.{PREFIX}env-{self.seq}", "wa_id": corpo.get("to")}

    def marcar_lida(self, conexao, wamid):
        self._travada(conexao)
        self.chamadas["marcar_lida"].append(wamid)

    def subir_midia(self, conexao, dados, mime, nome):
        self._travada(conexao)
        self.chamadas["subir_midia"].append((len(dados), mime, nome))
        return f"{PREFIX}upload-{len(self.chamadas['subir_midia'])}"

    def consultar_midia(self, conexao, media_id):
        self._travada(conexao)
        self.chamadas["consultar_midia"].append(media_id)
        if self.falhar_download > 0:
            self.falhar_download -= 1
            raise _wc.WhatsappIndisponivel("Meta fora (dublê)")
        return {
            "url": f"https://meta.invalid/{media_id}",
            "mime_type": "image/png",
            "file_size": len(BYTES_DA_FOTO),
        }

    def baixar_midia(self, conexao, url, limite_bytes):
        self._travada(conexao)
        self.chamadas["baixar_midia"].append(url)
        return BYTES_DA_FOTO

    def listar_modelos(self, conexao):
        self._travada(conexao)
        self.chamadas["listar_modelos"].append(True)
        return [
            {
                "name": "retomar_orcamento",
                "language": "pt_BR",
                "status": "APPROVED",
                "category": "MARKETING",
                "components": [{"type": "BODY", "text": "Oi, {{1}}! Ainda pensando na festa?"}],
            },
            {
                "name": "rascunho_v325",
                "language": "pt_BR",
                "status": "PENDING",
                "category": "UTILITY",
                "components": [{"type": "BODY", "text": "não aprovado"}],
            },
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


def _usuario(sufixo: str, papel: str) -> str:
    email = f"{PREFIX}{sufixo}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        db.session.add(user)
    user.set_password(SENHA)
    user.roles.clear()
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.commit()
    return email


def _chamar(email: str, metodo: str, url: str, corpo: dict | None = None, **kwargs):
    """Uma requisição autenticada, fora de qualquer contexto de aplicação."""
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
        _garante(r.status_code == 200, f"login {email} → {r.status_code}")
        if corpo is not None:
            kwargs["json"] = corpo
        return getattr(c, metodo)(url, **kwargs)


def _post_aviso(corpo: dict, segredo: str | None = SEGREDO):
    """POST do aviso da Meta com `X-Hub-Signature-256` do corpo bruto (ou sem/errado)."""
    bruto = json.dumps(corpo).encode()
    cabecalhos = {"Content-Type": "application/json"}
    if segredo is not None:
        cabecalhos["X-Hub-Signature-256"] = (
            "sha256=" + hmac.new(segredo.encode(), bruto, hashlib.sha256).hexdigest()
        )
    with app.test_client() as c:
        return c.post("/api/webhooks/whatsapp", data=bruto, headers=cabecalhos)


def _valor(contatos: list[dict], **campos) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "v325-waba",
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


def _aviso_texto(wa_id: str, nome: str, wamid: str, corpo_texto: str) -> dict:
    return _valor(
        [{"profile": {"name": nome}, "wa_id": wa_id, "user_id": f"BR.{PREFIX}{wa_id}"}],
        messages=[
            {
                "from": wa_id,
                "id": wamid,
                "timestamp": str(int(time.time())),
                "type": "text",
                "text": {"body": corpo_texto},
            }
        ],
    )


def _aviso_status(wamid: str, wa_id: str, status: str, erro: int | None = None) -> dict:
    item = {
        "id": wamid,
        "status": status,
        "timestamp": str(int(time.time())),
        "recipient_id": wa_id,
    }
    if erro is not None:
        item["errors"] = [
            {"code": erro, "title": "x", "message": "x", "error_data": {"details": "x"}}
        ]
    return _valor([], statuses=[item])


def _conversa(contato_id: str):
    return _no_banco(
        "SELECT id, client_id, telefone, nome_perfil, nao_lidas, ultima_recebida_em, contato_bsuid "
        "FROM conversas WHERE canal='whatsapp' AND contato_id=:c",
        c=contato_id,
    )


def _mensagem(wamid: str):
    return _no_banco(
        "SELECT id, direcao, tipo, texto, situacao, autor_id, origem, erro_codigo, erro_motivo, "
        "modelo_nome FROM conversa_mensagens WHERE externo_id=:w",
        w=wamid,
    )


# ── Cenários ───────────────────────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    with app.test_client() as c:
        ok = c.get(
            f"/api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token={VERIFICA}&hub.challenge=8325"
        )
        ruim = c.get(
            "/api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=errado&hub.challenge=1"
        )
    _garante(
        ok.status_code == 200 and ok.get_data(as_text=True) == "8325", f"desafio → {ok.status_code}"
    )
    _garante(ruim.status_code == 404, f"token errado → {ruim.status_code} (esperado 404)")


def cen_02() -> None:
    r = _post_aviso(
        _aviso_texto(WA_NOVO, f"{PREFIX}Ana Nova", f"wamid.{PREFIX}in-1", "Oi, quero um orçamento")
    )
    _garante(r.status_code == 200, f"POST → {r.status_code}")
    conv = _conversa(WA_NOVO)
    _garante(conv is not None, "conversa não nasceu")
    _garante(conv.nome_perfil == f"{PREFIX}Ana Nova", f"nome_perfil={conv.nome_perfil}")
    _garante(conv.telefone == WA_NOVO, f"telefone={conv.telefone}")
    _garante(conv.nao_lidas == 1 and conv.ultima_recebida_em is not None, "não lidas/janela")
    _garante(conv.contato_bsuid == f"BR.{PREFIX}{WA_NOVO}", f"bsuid={conv.contato_bsuid}")
    msg = _mensagem(f"wamid.{PREFIX}in-1")
    _garante(
        msg is not None and msg.direcao == "recebida" and msg.situacao == "recebida", "mensagem"
    )
    _garante(
        msg.texto == "Oi, quero um orçamento" and msg.origem == "contato", f"texto/origem {msg}"
    )
    aviso = _no_banco(
        "SELECT estado FROM whatsapp_avisos WHERE corpo LIKE :p ORDER BY id DESC LIMIT 1",
        p=f"%wamid.{PREFIX}in-1%",
    )
    _garante(aviso is not None and aviso.estado == "processado", f"aviso cru {aviso}")


def cen_02b_grupo() -> None:
    """Mensagem de grupo (Groups API) não vira conversa 1:1 (T052)."""
    aviso = _aviso_texto(WA_GRUPO, f"{PREFIX}Grupo", f"wamid.{PREFIX}grupo-1", "oi, grupo")
    aviso["entry"][0]["changes"][0]["value"]["messages"][0]["group_id"] = f"{PREFIX}grupo"
    r = _post_aviso(aviso)
    _garante(r.status_code == 200, f"POST → {r.status_code}")
    _garante(_conversa(WA_GRUPO) is None, "a mensagem de grupo virou conversa")
    _garante(_mensagem(f"wamid.{PREFIX}grupo-1") is None, "a mensagem de grupo foi gravada")


def cen_03() -> None:
    cen_02b_grupo()
    r = _post_aviso(
        _aviso_texto(WA_NOVO, f"{PREFIX}Ana Nova", f"wamid.{PREFIX}in-1", "Oi, quero um orçamento")
    )
    _garante(r.status_code == 200, f"POST repetido → {r.status_code}")
    n = _no_banco(
        "SELECT count(*) FROM conversa_mensagens WHERE externo_id=:w", w=f"wamid.{PREFIX}in-1"
    )[0]
    _garante(n == 1, f"{n} mensagens com o mesmo wamid")
    _garante(_conversa(WA_NOVO).nao_lidas == 1, "o reenvio contou como não lida de novo")
    avisos = _no_banco(
        "SELECT count(*) FROM whatsapp_avisos WHERE corpo LIKE :p", p=f"%wamid.{PREFIX}in-1%"
    )[0]
    _garante(avisos == 2, f"os dois avisos crus deviam estar gravados ({avisos})")


def cen_04() -> None:
    # Duas fichas para o mesmo número (uma com o 9, outra sem): vale a do telefone exato (T053).
    with app.app_context():
        db.session.add(
            Client(name=f"{PREFIX}Ficha duplicada sem o 9", phone=WA_DA_FICHA, source="manual")
        )
        db.session.commit()
    r = _post_aviso(
        _aviso_texto(WA_DA_FICHA, f"{PREFIX}Cliente da ficha", f"wamid.{PREFIX}in-ficha", "Olá")
    )
    _garante(r.status_code == 200, f"POST → {r.status_code}")
    conv = _conversa(WA_DA_FICHA)
    _garante(conv is not None and conv.client_id == estado["cliente_id"], f"vínculo {conv}")
    _garante(conv.telefone == TEL_FICHA, f"telefone com o nono: {conv.telefone}")


def cen_05() -> None:
    r = _post_aviso(
        _aviso_texto(WA_NOVO, "x", f"wamid.{PREFIX}forjado", "forjado"), segredo="errado"
    )
    _garante(r.status_code == 404, f"assinatura errada → {r.status_code} (esperado 404)")
    r2 = _post_aviso(_aviso_texto(WA_NOVO, "x", f"wamid.{PREFIX}forjado", "forjado"), segredo=None)
    _garante(r2.status_code == 404, f"sem assinatura → {r2.status_code} (esperado 404)")
    n = _no_banco(
        "SELECT count(*) FROM whatsapp_avisos WHERE corpo LIKE :p", p=f"%wamid.{PREFIX}forjado%"
    )[0]
    _garante(n == 0, "aviso forjado foi gravado")


def cen_06() -> None:
    import app.conversas.aviso_ops as aviso_ops
    from app.conversas import varredura

    original = aviso_ops._processar_change

    def _quebrado(*_a, **_k):
        raise RuntimeError("quebra simulada (verify 325)")

    aviso_ops._processar_change = _quebrado
    try:
        r = _post_aviso(
            _aviso_texto(WA_NOVO, f"{PREFIX}Ana Nova", f"wamid.{PREFIX}in-2", "segunda")
        )
    finally:
        aviso_ops._processar_change = original
    _garante(r.status_code == 200, f"POST → {r.status_code} (a quebra não pode virar 5xx)")
    aviso = _no_banco(
        "SELECT id, estado, erro FROM whatsapp_avisos WHERE corpo LIKE :p",
        p=f"%wamid.{PREFIX}in-2%",
    )
    _garante(
        aviso is not None and aviso.estado == "pendente" and aviso.erro,
        f"aviso devia voltar a pendente: {aviso}",
    )
    _garante(_mensagem(f"wamid.{PREFIX}in-2") is None, "mensagem gravada apesar da quebra")
    _no_banco_escrever(
        "UPDATE whatsapp_avisos SET recebido_em = recebido_em - interval '5 minutes' WHERE id=:i",
        i=aviso.id,
    )
    with app.app_context():
        resumo = varredura.reprocessar_avisos()
    _garante(resumo.get("processados", 0) >= 1, f"varredura: {resumo}")
    _garante(_mensagem(f"wamid.{PREFIX}in-2") is not None, "a varredura não gravou a mensagem")
    estado_final = _no_banco("SELECT estado FROM whatsapp_avisos WHERE id=:i", i=aviso.id).estado
    _garante(estado_final == "processado", f"aviso ficou {estado_final}")


def cen_07() -> None:
    conv = _conversa(WA_NOVO)
    antes = len(meta.chamadas["enviar"])
    r = _chamar(
        estado["comercial"],
        "post",
        f"/api/conversas/{conv.id}/mensagens",
        {"texto": "Oi, Ana! Já preparo.", "chave_envio": f"{PREFIX}chave-07"},
    )
    _garante(r.status_code == 201, f"envio → {r.status_code} {r.get_data(as_text=True)[:200]}")
    corpo = r.get_json()["mensagem"]
    _garante(corpo["situacao"] == "enviada" and corpo["direcao"] == "enviada", f"payload {corpo}")
    _garante(len(meta.chamadas["enviar"]) == antes + 1, "a Meta (dublê) não foi chamada")
    enviado = meta.chamadas["enviar"][-1]
    _garante(
        enviado.get("to") == WA_NOVO and enviado["text"]["body"] == "Oi, Ana! Já preparo.",
        f"corpo {enviado}",
    )
    linha = _no_banco(
        "SELECT situacao, autor_id, origem, externo_id FROM conversa_mensagens WHERE chave_envio=:c",
        c=f"{PREFIX}chave-07",
    )
    _garante(
        linha.situacao == "enviada" and linha.autor_id == estado["comercial_id"], f"linha {linha}"
    )
    _garante(
        linha.origem == "plataforma" and linha.externo_id.startswith(f"wamid.{PREFIX}env-"),
        f"linha {linha}",
    )
    estado["wamid_07"] = linha.externo_id
    lida = _chamar(estado["comercial"], "post", f"/api/conversas/{conv.id}/lida", {})
    _garante(lida.status_code == 204, f"lida → {lida.status_code}")
    _garante(_conversa(WA_NOVO).nao_lidas == 0, "não lidas não zerou")
    _garante(meta.chamadas["marcar_lida"], "a última recebida não foi marcada como lida na Meta")


def cen_08() -> None:
    wamid = estado["wamid_07"]
    for status in ("delivered", "read", "sent"):  # o "sent" chega atrasado
        r = _post_aviso(_aviso_status(wamid, WA_NOVO, status))
        _garante(r.status_code == 200, f"status {status} → {r.status_code}")
    situacao = _no_banco(
        "SELECT situacao FROM conversa_mensagens WHERE externo_id=:w", w=wamid
    ).situacao
    _garante(situacao == "lida", f"situação {situacao} (esperado lida, sem regredir)")
    r = _post_aviso(_aviso_status(wamid, WA_NOVO, "failed", erro=131026))
    situacao = _no_banco(
        "SELECT situacao FROM conversa_mensagens WHERE externo_id=:w", w=wamid
    ).situacao
    _garante(situacao == "lida", f"falha atrasada cobriu a lida: {situacao}")


def cen_09() -> None:
    conv = _conversa(WA_NOVO)
    _no_banco_escrever(
        "UPDATE conversas SET ultima_recebida_em = now() at time zone 'utc' - interval '25 hours' WHERE id=:i",
        i=conv.id,
    )
    antes = len(meta.chamadas["enviar"])
    r = _chamar(
        estado["comercial"],
        "post",
        f"/api/conversas/{conv.id}/mensagens",
        {"texto": "fora da janela", "chave_envio": f"{PREFIX}chave-09"},
    )
    erro = (r.get_json() or {}).get("error") or {}
    _garante(
        r.status_code == 409 and erro.get("codigo") == "janela_fechada", f"→ {r.status_code} {erro}"
    )
    _garante(len(meta.chamadas["enviar"]) == antes, "a Meta foi chamada com a janela fechada")
    _no_banco_escrever(
        "UPDATE conversas SET ultima_recebida_em = now() at time zone 'utc' WHERE id=:i", i=conv.id
    )


def cen_10() -> None:
    conv = _conversa(WA_NOVO)
    r = _chamar(
        estado["comercial"],
        "post",
        f"/api/conversas/{conv.id}/mensagens",
        {"texto": "vai falhar", "chave_envio": f"{PREFIX}chave-10"},
    )
    _garante(r.status_code == 201, f"envio → {r.status_code}")
    wamid = _no_banco(
        "SELECT externo_id FROM conversa_mensagens WHERE chave_envio=:c", c=f"{PREFIX}chave-10"
    ).externo_id
    _post_aviso(_aviso_status(wamid, WA_NOVO, "failed", erro=131026))
    linha = _mensagem(wamid)
    _garante(linha.situacao == "falhou" and linha.erro_codigo == 131026, f"linha {linha}")
    _garante(linha.erro_motivo and "WhatsApp" in linha.erro_motivo, f"motivo {linha.erro_motivo}")


def _aviso_imagem(wamid: str, media_id: str) -> dict:
    return _valor(
        [{"profile": {"name": f"{PREFIX}Mídia"}, "wa_id": WA_MIDIA}],
        messages=[
            {
                "from": WA_MIDIA,
                "id": wamid,
                "timestamp": str(int(time.time())),
                "type": "image",
                "image": {
                    "id": media_id,
                    "mime_type": "image/png",
                    "sha256": "x",
                    "caption": "o salão",
                },
            }
        ],
    )


def cen_11() -> None:
    r = _post_aviso(_aviso_imagem(f"wamid.{PREFIX}img-1", f"{PREFIX}media-1"))
    _garante(r.status_code == 200, f"POST → {r.status_code}")
    msg = _mensagem(f"wamid.{PREFIX}img-1")
    _garante(msg is not None and msg.tipo == "imagem" and msg.texto == "o salão", f"mensagem {msg}")
    midia = _no_banco(
        "SELECT id, estado, caminho, tamanho FROM conversa_midias WHERE mensagem_id=:m", m=msg.id
    )
    _garante(midia is not None and midia.estado == "guardada", f"mídia {midia}")
    arquivo = Path(PASTA_MIDIA) / midia.caminho
    _garante(arquivo.is_file() and arquivo.read_bytes() == BYTES_DA_FOTO, f"arquivo {arquivo}")
    estado["midia_id"] = midia.id
    servido = _chamar(estado["comercial"], "get", f"/api/conversas/midia/{midia.id}")
    _garante(
        servido.status_code == 200 and servido.data == BYTES_DA_FOTO,
        f"servir → {servido.status_code}",
    )
    # Envio de arquivo pela Plataforma (FR-011).
    conv = _conversa(WA_MIDIA)
    antes = len(meta.chamadas["subir_midia"])
    envio = _chamar(
        estado["comercial"],
        "post",
        f"/api/conversas/{conv.id}/mensagens",
        data={
            "chave_envio": f"{PREFIX}chave-11",
            "legenda": "o orçamento",
            "arquivo": (io.BytesIO(b"%PDF-1.4 v325"), "orcamento.pdf", "application/pdf"),
        },
        content_type="multipart/form-data",
    )
    _garante(
        envio.status_code == 201,
        f"envio de arquivo → {envio.status_code} {envio.get_data(as_text=True)[:200]}",
    )
    _garante(len(meta.chamadas["subir_midia"]) == antes + 1, "o arquivo não subiu para a Meta")
    enviado = meta.chamadas["enviar"][-1]
    _garante(
        enviado.get("type") == "document" and enviado["document"]["filename"] == "orcamento.pdf",
        f"{enviado}",
    )
    linha = _no_banco(
        "SELECT m.tipo, d.estado, d.caminho FROM conversa_mensagens m JOIN conversa_midias d ON d.mensagem_id=m.id "
        "WHERE m.chave_envio=:c",
        c=f"{PREFIX}chave-11",
    )
    _garante(linha.tipo == "documento" and linha.estado == "guardada", f"cópia local {linha}")
    _garante(
        (Path(PASTA_MIDIA) / linha.caminho).is_file(), "a cópia local do arquivo enviado sumiu"
    )


def cen_12() -> None:
    from app.conversas import varredura

    meta.falhar_download = 1
    _post_aviso(_aviso_imagem(f"wamid.{PREFIX}img-2", f"{PREFIX}media-2"))
    msg = _mensagem(f"wamid.{PREFIX}img-2")
    _garante(
        msg is not None, "a mensagem com mídia tem de ser gravada mesmo com o download falhando"
    )
    midia = _no_banco("SELECT id, estado, erro FROM conversa_midias WHERE mensagem_id=:m", m=msg.id)
    _garante(midia.estado == "pendente" and midia.erro, f"mídia devia ficar pendente: {midia}")
    with app.app_context():
        cedo = varredura.reprocessar_midias()
    _garante(cedo.get("guardadas", 0) == 0, f"a varredura não respeitou o espaçamento: {cedo}")
    # Muitas tentativas não matam a mídia nova (T049): só a idade de 48 h.
    meta.falhar_download = 1
    _no_banco_escrever(
        "UPDATE conversa_midias SET tentativas = 12, tentado_em = tentado_em - interval '2 hours' WHERE id=:i",
        i=midia.id,
    )
    with app.app_context():
        varredura.reprocessar_midias()
    depois = _no_banco("SELECT estado, tentativas FROM conversa_midias WHERE id=:i", i=midia.id)
    _garante(
        depois.estado == "pendente" and depois.tentativas == 13, f"mídia nova esgotou: {depois}"
    )
    _no_banco_escrever(
        "UPDATE conversa_midias SET tentado_em = tentado_em - interval '2 hours' WHERE id=:i",
        i=midia.id,
    )
    with app.app_context():
        resumo = varredura.reprocessar_midias()
    _garante(resumo.get("guardadas", 0) >= 1, f"varredura de mídia: {resumo}")
    final = _no_banco("SELECT estado FROM conversa_midias WHERE id=:i", i=midia.id).estado
    _garante(final == "guardada", f"mídia ficou {final}")


def cen_13() -> None:
    r = _chamar(estado["casting"], "get", f"/api/conversas/midia/{estado['midia_id']}")
    _garante(r.status_code == 404, f"Casting na mídia → {r.status_code} (esperado 404)")


def cen_14() -> None:
    r = _chamar(estado["comercial"], "get", "/api/conversas/modelos")
    _garante(r.status_code == 200, f"modelos → {r.status_code}")
    modelos = r.get_json()["modelos"]
    nomes = [m["nome"] for m in modelos]
    _garante(nomes == ["retomar_orcamento"], f"só os aprovados: {nomes}")
    _garante(
        modelos[0]["variaveis"] == 1 and "{{1}}" in modelos[0]["texto"], f"modelo {modelos[0]}"
    )


def cen_15() -> None:
    conv = _conversa(WA_NOVO)
    _no_banco_escrever(
        "UPDATE conversas SET ultima_recebida_em = now() at time zone 'utc' - interval '30 hours' WHERE id=:i",
        i=conv.id,
    )
    r = _chamar(
        estado["comercial"],
        "post",
        f"/api/conversas/{conv.id}/modelo",
        {
            "nome": "retomar_orcamento",
            "idioma": "pt_BR",
            "variaveis": ["Ana"],
            "chave_envio": f"{PREFIX}chave-15",
        },
    )
    _garante(r.status_code == 201, f"modelo → {r.status_code} {r.get_data(as_text=True)[:200]}")
    enviado = meta.chamadas["enviar"][-1]
    _garante(
        enviado.get("type") == "template" and enviado["template"]["name"] == "retomar_orcamento",
        f"{enviado}",
    )
    linha = _no_banco(
        "SELECT tipo, texto, modelo_nome FROM conversa_mensagens WHERE chave_envio=:c",
        c=f"{PREFIX}chave-15",
    )
    _garante(linha.tipo == "modelo" and linha.modelo_nome == "retomar_orcamento", f"linha {linha}")
    _garante(linha.texto == "Oi, Ana! Ainda pensando na festa?", f"texto final {linha.texto!r}")
    errado = _chamar(
        estado["comercial"],
        "post",
        f"/api/conversas/{conv.id}/modelo",
        {
            "nome": "rascunho_v325",
            "idioma": "pt_BR",
            "variaveis": [],
            "chave_envio": f"{PREFIX}chave-15b",
        },
    )
    _garante(
        errado.status_code == 422, f"modelo não aprovado → {errado.status_code} (esperado 422)"
    )
    _no_banco_escrever(
        "UPDATE conversas SET ultima_recebida_em = now() at time zone 'utc' WHERE id=:i", i=conv.id
    )


def _conversas_ligadas(email: str) -> bool | None:
    return _chamar(email, "get", "/api/auth/me").get_json().get("conversas_ligadas")


def cen_16() -> None:
    _garante(
        _conversas_ligadas(estado["comercial"]) is True, "Comercial com o módulo ligado sem o menu"
    )
    token = app.config["WHATSAPP_ACCESS_TOKEN"]
    app.config["WHATSAPP_ACCESS_TOKEN"] = ""
    try:
        with app.test_client() as c:
            g = c.get(
                f"/api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token={VERIFICA}&hub.challenge=1"
            )
        p = _post_aviso(_aviso_texto(WA_NOVO, "x", f"wamid.{PREFIX}desligado", "x"))
        conv = _conversa(WA_NOVO)
        e = _chamar(
            estado["comercial"],
            "post",
            f"/api/conversas/{conv.id}/mensagens",
            {"texto": "x", "chave_envio": f"{PREFIX}chave-16"},
        )
        menu = _conversas_ligadas(estado["comercial"])
    finally:
        app.config["WHATSAPP_ACCESS_TOKEN"] = token
    _garante(menu is False, f"menu com a configuração vazia: conversas_ligadas={menu}")
    _garante(
        g.status_code == 404 and p.status_code == 404,
        f"webhook desligado → {g.status_code}/{p.status_code}",
    )
    erro = (e.get_json() or {}).get("error") or {}
    _garante(
        e.status_code == 503 and erro.get("codigo") == "nao_configurado",
        f"envio → {e.status_code} {erro}",
    )


def cen_17() -> None:
    from app.config import _suppress_whatsapp

    _garante(
        TRAVA_DE_FABRICA is True,
        f"create_app() contra o manto_local nasceu destravado ({TRAVA_DE_FABRICA})",
    )
    _garante(_suppress_whatsapp() is True, "_suppress_whatsapp() não travou o banco local")
    os.environ["WHATSAPP_ALLOW_LOCAL_SEND"] = "true"
    try:
        liberado = _suppress_whatsapp()
    finally:
        os.environ.pop("WHATSAPP_ALLOW_LOCAL_SEND", None)
    _garante(liberado is False, "WHATSAPP_ALLOW_LOCAL_SEND=true não liberou o local")
    app.config["WHATSAPP_SUPPRESS_SEND"] = True
    antes = sum(len(v) for v in meta.chamadas.values())
    try:
        conv = _conversa(WA_NOVO)
        r = _chamar(
            estado["comercial"],
            "post",
            f"/api/conversas/{conv.id}/mensagens",
            {"texto": "travado", "chave_envio": f"{PREFIX}chave-17"},
        )
    finally:
        app.config["WHATSAPP_SUPPRESS_SEND"] = False
    erro = (r.get_json() or {}).get("error") or {}
    _garante(
        r.status_code == 409 and erro.get("codigo") == "envio_travado", f"→ {r.status_code} {erro}"
    )
    _garante(
        sum(len(v) for v in meta.chamadas.values()) == antes,
        "a Meta (dublê) foi chamada com a trava",
    )


def cen_18() -> None:
    conv = _conversa(WA_NOVO)
    lista = _chamar(estado["casting"], "get", "/api/conversas")
    envio = _chamar(
        estado["casting"],
        "post",
        f"/api/conversas/{conv.id}/mensagens",
        {"texto": "x", "chave_envio": f"{PREFIX}chave-18"},
    )
    _garante(lista.status_code == 403, f"Casting na lista → {lista.status_code} (esperado 403)")
    _garante(envio.status_code == 403, f"Casting no envio → {envio.status_code} (esperado 403)")
    menu = _conversas_ligadas(estado["casting"])
    _garante(menu is False, f"Casting vê o menu Conversas: conversas_ligadas={menu}")


def cen_19() -> None:
    _post_aviso(_aviso_texto(WA_ECO, f"{PREFIX}Eco", f"wamid.{PREFIX}in-eco", "oi"))
    antes = _conversa(WA_ECO).ultima_recebida_em
    eco = _valor(
        [],
        field="smb_message_echoes",
        message_echoes=[
            {
                "from": NUMERO_MANTO,
                "to": WA_ECO,
                "id": f"wamid.{PREFIX}eco-1",
                "timestamp": str(int(time.time())),
                "type": "text",
                "text": {"body": "respondi pelo celular"},
            }
        ],
    )
    for _ in range(2):
        r = _post_aviso(eco)
        _garante(r.status_code == 200, f"eco → {r.status_code}")
    n = _no_banco(
        "SELECT count(*) FROM conversa_mensagens WHERE externo_id=:w", w=f"wamid.{PREFIX}eco-1"
    )[0]
    _garante(n == 1, f"eco duplicado ({n})")
    msg = _mensagem(f"wamid.{PREFIX}eco-1")
    _garante(
        msg.direcao == "enviada" and msg.origem == "celular" and msg.autor_id is None, f"eco {msg}"
    )
    _garante(_conversa(WA_ECO).ultima_recebida_em == antes, "o eco reabriu a janela")


def cen_20() -> None:
    conv = _conversa(WA_NOVO)
    antes = len(meta.chamadas["enviar"])
    corpo = {"texto": "clique duplo", "chave_envio": f"{PREFIX}chave-20"}
    r1 = _chamar(estado["comercial"], "post", f"/api/conversas/{conv.id}/mensagens", corpo)
    r2 = _chamar(estado["comercial"], "post", f"/api/conversas/{conv.id}/mensagens", corpo)
    _garante(
        r1.status_code == 201 and r2.status_code in (200, 201),
        f"→ {r1.status_code}/{r2.status_code}",
    )
    _garante(r1.get_json()["mensagem"]["id"] == r2.get_json()["mensagem"]["id"], "duas mensagens")
    _garante(len(meta.chamadas["enviar"]) == antes + 1, "a Meta foi chamada duas vezes")


def cen_leitura() -> None:
    """Lista e conversa aberta pela API (FR-013/FR-014), com o contrato dos campos."""
    r = _chamar(estado["comercial"], "get", "/api/conversas?busca=v325")
    _garante(r.status_code == 200, f"lista → {r.status_code}")
    corpo = r.get_json()
    _garante(
        corpo.get("configurado") is True and corpo.get("envio_travado") is False, f"flags {corpo}"
    )
    itens = {c["telefone"]: c for c in corpo["conversas"]}
    _garante(WA_NOVO in itens and TEL_FICHA in itens, f"busca não achou: {list(itens)}")
    _garante(itens[TEL_FICHA]["cliente"]["id"] == estado["cliente_id"], "cliente da ficha ausente")
    _garante(itens[WA_NOVO]["ultima_mensagem_em"].endswith("+00:00"), "horário sem fuso explícito")
    aberta = _chamar(estado["comercial"], "get", f"/api/conversas/{itens[WA_NOVO]['id']}")
    _garante(aberta.status_code == 200, f"conversa → {aberta.status_code}")
    msgs = aberta.get_json()["mensagens"]
    _garante(len(msgs) >= 3 and msgs[0]["momento"] <= msgs[-1]["momento"], "ordem das mensagens")
    _garante(
        any(m["autor"] for m in msgs if m["direcao"] == "enviada"), "autor ausente nas enviadas"
    )


# ── Preparo e limpeza ──────────────────────────────────────────────────────────────────────────────


def preparar() -> None:
    for tel in (TEL_FICHA, WA_DA_FICHA, WA_NOVO, WA_ECO, WA_MIDIA, WA_GRUPO):
        dono = Client.query.filter_by(phone=tel).first()
        _garante(
            dono is None or dono.name.startswith(PREFIX),
            f"telefone de teste {tel} já é de uma ficha real",
        )
    estado["comercial"] = _usuario("comercial", RoleName.COMERCIAL)
    estado["casting"] = _usuario("casting", RoleName.CASTING)
    estado["comercial_id"] = User.query.filter_by(email=estado["comercial"]).one().id
    cliente = Client.query.filter_by(phone=TEL_FICHA).first()
    if cliente is None:
        cliente = Client(name=f"{PREFIX}Cliente da ficha", phone=TEL_FICHA, source="manual")
        db.session.add(cliente)
        db.session.commit()
    estado["cliente_id"] = cliente.id


def limpar() -> None:
    db.session.rollback()
    padrao = f"{PREFIX}%"
    contatos = [WA_DA_FICHA, WA_NOVO, WA_ECO, WA_MIDIA, WA_GRUPO]
    db.session.execute(
        text("DELETE FROM conversas WHERE nome_perfil LIKE :p OR contato_id = ANY(:c)"),
        {"p": padrao, "c": contatos},
    )
    db.session.execute(
        text("DELETE FROM whatsapp_avisos WHERE corpo LIKE :p"), {"p": f"%{NUMERO_ID}%"}
    )
    Client.query.filter(Client.name.like(padrao)).delete(synchronize_session=False)
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
    sobras = _no_banco("SELECT count(*) FROM conversas WHERE contato_id = ANY(:c)", c=contatos)[0]
    _garante(sobras == 0, f"sobraram {sobras} conversas de teste")


CENARIOS = [
    ("1. desafio de verificação (token certo × errado)", cen_01),
    ("2. texto de telefone novo: conversa + mensagem + aviso cru", cen_02),
    ("3. reenvio do mesmo aviso não duplica", cen_03),
    ("4. ficha ligada pelo número sem o nono dígito", cen_04),
    ("5. assinatura errada ou ausente (DEVE falhar)", cen_05),
    ("6. processamento quebrado → varredura refaz", cen_06),
    ("7. envio de texto na janela, com autor, e marcar como lida", cen_07),
    ("8. status avança e não regride", cen_08),
    ("9. texto fora da janela (DEVE falhar)", cen_09),
    ("10. status failed com motivo legível", cen_10),
    ("11. mídia recebida guardada e servida; arquivo enviado", cen_11),
    ("12. download falha → pendente → varredura guarda", cen_12),
    ("13. Casting na mídia (DEVE falhar)", cen_13),
    ("14. só modelos aprovados", cen_14),
    ("15. modelo com variável fora da janela", cen_15),
    ("16. configuração vazia (DEVE falhar)", cen_16),
    ("17. banco local sem liberação (DEVE falhar)", cen_17),
    ("18. Casting na lista e no envio (DEVE falhar)", cen_18),
    ("19. eco do celular: enviada, origem celular, sem duplicar", cen_19),
    ("20. clique duplo: uma mensagem só", cen_20),
    ("20b. lista e conversa aberta pela API", cen_leitura),
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

    print("Feature 325 — Conversas (WhatsApp), contra manto_local")
    try:
        for indice, (nome, fn) in enumerate(CENARIOS, start=1):
            if so is None or indice in so:
                cenario(nome, fn)
    finally:
        if manter:
            print(
                "  --manter: conversas e usuários v325- ficam para conferir a tela (senha: verify-325-senha)"
            )
        else:
            with app.app_context():
                cenario("21. limpeza", limpar)
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
