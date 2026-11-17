"""Verificação da feature 349 — o comercial mede e fecha pela conversa.

Os 18 cenários da tabela da spec, contra o espelho **`manto_349`** (o `manto_local` é compartilhado pelas features
348–351 e não recebe esta migration). As mensagens entram pelo webhook assinado (o mesmo caminho da produção), os
envios pela API, e a Meta é um dublê em memória; a criação de evento troca o `insert_event` do Google por um dublê.
Um disjuntor de rede derruba qualquer conexão que não seja o Postgres local. Escrita conferida por conexão separada.

Tudo de teste leva `v349-`. Rodar (PowerShell, na raiz do worktree)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
    $env:PYTHONUTF8 = '1'; .venv\\Scripts\\python.exe specs/349-comercial-mede-e-fecha/verify_349.py [--so=1,2] [--manter]
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
        raise OSError(f"verify 349: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 349: conexão de saída bloqueada para {_host_de(endereco)}")
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

from sqlalchemy import create_engine, event, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import TZ_SP, RoleName, now_sp  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    Client,
    ConversaAnuncio,
    EventClient,
    OrcamentoEnvio,
    OrcamentoHistory,
    Role,
    User,
)

PREFIX = "v349-"
SENHA = "verify-349-senha"
SEGREDO = "segredo-do-app-v349"
NUMERO_ID = "v349-phone"
NUMERO_MANTO = "5511900000349"
# Um número por conversa de teste (o último par de dígitos é o número do cenário que a usa).
WA = {n: f"55119634900{n:02d}" for n in range(1, 15)}
CONTATOS = list(WA.values())

app = create_app()
app.config["TESTING"] = True
app.config["WHATSAPP_ACCESS_TOKEN"] = "token-falso-v349"
app.config["WHATSAPP_APP_SECRET"] = SEGREDO
app.config["WHATSAPP_VERIFY_TOKEN"] = "verifica-v349"
app.config["WHATSAPP_PHONE_NUMBER_ID"] = NUMERO_ID
app.config["WHATSAPP_WABA_ID"] = "v349-waba"
app.config["WHATSAPP_AVISO_SINCRONO"] = True
# A "liberação de teste" do quickstart da 325, com o dublê no lugar da Meta (e o disjuntor atrás).
app.config["WHATSAPP_SUPPRESS_SEND"] = False
limiter.enabled = False

# ── Dublês: Meta e Google ────────────────────────────────────────────────────────────────────────
import app.calendar.routes as _rotas  # noqa: E402
import app.integracoes.whatsapp_client as _wc  # noqa: E402

_REAIS = {nome: getattr(_wc, nome) for nome in ("enviar", "marcar_lida")}
_INSERT_EVENT_REAL = _rotas.insert_event


class MetaFalsa:
    """Responde como a Meta, registra cada chamada e nunca sai da máquina."""

    def __init__(self) -> None:
        self.enviados: list[dict] = []
        self.seq = 0

    def enviar(self, conexao, corpo):
        self.enviados.append(corpo)
        self.seq += 1
        return {"id": f"wamid.{PREFIX}env-{self.seq}", "wa_id": corpo.get("to")}

    def marcar_lida(self, conexao, wamid):
        return None


meta = MetaFalsa()
for _nome in _REAIS:
    setattr(_wc, _nome, getattr(meta, _nome))
google: list[str] = []


def _insert_event_falso(calendar_id, title, start, end, **kwargs):
    google.append(title)
    return {"id": f"{PREFIX}google-{uuid.uuid4().hex[:10]}"}


_rotas.insert_event = _insert_event_falso

resultados: list[tuple[str, bool, str]] = []
estado: dict = {"conv": {}, "ficha": {}}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)
_consultas = {"contando": False, "n": 0}


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


def _agora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _utc_de_sp(momento_sp: datetime) -> datetime:
    return momento_sp.replace(tzinfo=TZ_SP).astimezone(UTC).replace(tzinfo=None)


def _as(h: int, m: int = 0) -> datetime:
    """Um horário de São Paulo de hoje, sem fuso — como `now_sp()`."""
    return datetime.combine(now_sp().date(), hora(h, m))


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


def _chamar(email: str, metodo: str, url: str, corpo: dict | None = None, contar: bool = False):
    """Uma requisição autenticada, fora de qualquer contexto de aplicação."""
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
        _garante(r.status_code == 200, f"login {email} → {r.status_code}")
        kwargs = {"json": corpo} if corpo is not None else {}
        _consultas.update(contando=contar, n=0)
        try:
            return getattr(c, metodo)(url, **kwargs)
        finally:
            _consultas["contando"] = False


def _erro(r) -> dict:
    return (r.get_json() or {}).get("error") or {}


def _post_aviso(corpo: dict) -> None:
    bruto = json.dumps(corpo).encode()
    assinatura = "sha256=" + hmac.new(SEGREDO.encode(), bruto, hashlib.sha256).hexdigest()
    with app.test_client() as c:
        r = c.post(
            "/api/webhooks/whatsapp",
            data=bruto,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": assinatura},
        )
    _garante(r.status_code == 200, f"aviso → {r.status_code}")


def _valor(contatos: list[dict], **campos) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "v349-waba",
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


def _recebida(n: int, sufixo: str, atras_s: int = 0, tipo: str = "text") -> int:
    """A cliente `n` escreve, `atras_s` segundos atrás. Devolve o id da conversa."""
    item = {
        "from": WA[n],
        "id": f"wamid.{PREFIX}in-{n}-{sufixo}",
        "timestamp": str(int(time.time()) - atras_s),
        "type": tipo,
    }
    if tipo == "text":
        item["text"] = {"body": "Quero um orçamento"}
    else:
        item["reaction"] = {"message_id": "x", "emoji": "👍"}
    _post_aviso(
        _valor([{"profile": {"name": f"{PREFIX}Cliente {n}"}, "wa_id": WA[n]}], messages=[item])
    )
    return _conversa_id(n)


def _eco(n: int, sufixo: str, atras_s: int = 0) -> None:
    item = {
        "from": NUMERO_MANTO,
        "to": WA[n],
        "id": f"wamid.{PREFIX}eco-{n}-{sufixo}",
        "timestamp": str(int(time.time()) - atras_s),
        "type": "text",
        "text": {"body": "respondi pelo celular"},
    }
    _post_aviso(_valor([], field="smb_message_echoes", message_echoes=[item]))


def _status_falhou(wamid: str, n: int) -> None:
    item = {
        "id": wamid,
        "status": "failed",
        "timestamp": str(int(time.time())),
        "recipient_id": WA[n],
        "errors": [{"code": 131026, "title": "x", "message": "x"}],
    }
    _post_aviso(_valor([], statuses=[item]))


def _conversa_id(n: int) -> int:
    linha = _no_banco("SELECT id FROM conversas WHERE canal='whatsapp' AND contato_id=:c", c=WA[n])
    _garante(linha is not None, f"conversa {n} não nasceu")
    estado["conv"][n] = linha[0]
    return linha[0]


def _texto(email: str, conversa_id: int, chave: str):
    r = _chamar(
        email,
        "post",
        f"/api/conversas/{conversa_id}/mensagens",
        {
            "texto": "Oi! Já preparo o orçamento.",
            "chave_envio": f"{PREFIX}{chave}-{uuid.uuid4().hex[:8]}",
        },
    )
    _garante(
        r.status_code in (200, 201), f"envio → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    return r


def _primeira(conversa_id: int):
    return _no_banco(
        "SELECT primeira_recebida_em, primeira_resposta_em, primeira_resposta_por_id, "
        "primeira_resposta_origem FROM conversas WHERE id=:i",
        i=conversa_id,
    )


def _venda(email: str, conversa_id: int) -> dict:
    r = _chamar(email, "get", f"/api/conversas/{conversa_id}/venda")
    _garante(r.status_code == 200, f"venda → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()


def _ficha(n: int, **campos) -> int:
    with app.app_context():
        ficha = Client(name=f"{PREFIX}Cliente {n}", phone=WA[n], source="conversa", **campos)
        db.session.add(ficha)
        db.session.commit()
        estado["ficha"][n] = ficha.id
        return ficha.id


def _ligar_ficha(conversa_id: int, ficha_id: int) -> None:
    _no_banco_escrever("UPDATE conversas SET client_id=:f WHERE id=:i", f=ficha_id, i=conversa_id)


def _orcamento(ficha_id: int | None, criado: datetime, data_evento: date | None) -> int:
    with app.app_context():
        return _orcamento_no_contexto(ficha_id, criado, data_evento)


def _orcamento_no_contexto(ficha_id: int | None, criado: datetime, data_evento: date | None) -> int:
    entry = OrcamentoHistory(
        user_id=estado["ana_id"],
        client_name=f"{PREFIX}Orçamento",
        client_id=ficha_id,
        event_location=f"{PREFIX}Buffet",
        event_date=data_evento.isoformat() if data_evento else None,
        total_1h=Decimal("1800"),
        total_2h=Decimal("2400"),
        total_3h=Decimal("0"),
        total_4h=Decimal("0"),
        has_show=False,
        created_at=criado,
    )
    db.session.add(entry)
    db.session.commit()
    return entry.id


def _envio(orcamento_id: int, conversa_id: int, criado: datetime) -> None:
    with app.app_context():
        db.session.add(
            OrcamentoEnvio(
                orcamento_id=orcamento_id,
                conversa_id=conversa_id,
                autor_id=estado["ana_id"],
                chave_envio=f"{PREFIX}{uuid.uuid4().hex[:16]}",
                created_at=criado,
            )
        )
        db.session.commit()


def _conversa_direta(
    n: int, criada: datetime, ficha_id: int | None, responsavel_id: int | None
) -> int:
    """Conversa semeada direto no banco (sem mensagem): a régua e o recorte só leem a conversa e o orçamento."""
    with _engine_externo.begin() as conn:
        linha = conn.execute(
            text(
                "INSERT INTO conversas (canal, contato_id, telefone, nome_perfil, client_id, ficha_manual, "
                "nao_lidas, responsavel_id, primeira_recebida_em, ultima_mensagem_em, created_at, updated_at) "
                "VALUES ('whatsapp', :c, :c, :n, :f, true, 0, :r, :t, :t, :t, :t) RETURNING id"
            ),
            {
                "c": WA[n],
                "n": f"{PREFIX}Perfil {n}",
                "f": ficha_id,
                "r": responsavel_id,
                "t": criada,
            },
        ).fetchone()
    return linha[0]


def _avisos(conversa_id: int, kind: str):
    return _no_banco_todas(
        "SELECT user_id, title, dedupe_key FROM notifications "
        "WHERE entity_type='conversa' AND entity_id=:i AND kind=:k ORDER BY id",
        i=conversa_id,
        k=kind,
    )


def _avisar(momento_sp: datetime) -> dict:
    from app.conversas import parado_ops

    with app.app_context():
        return parado_ops.avisar_lembretes(agora_sp=momento_sp)


def _lista(email: str, extra: str = "", contar: bool = False) -> dict:
    r = _chamar(email, "get", f"/api/conversas{extra}", contar=contar)
    _garante(
        r.status_code == 200, f"lista {extra} → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    return r.get_json()


def _periodo() -> str:
    hoje = now_sp().date()
    return f"inicio={hoje - timedelta(days=10)}&fim={hoje}"


def _funil(email: str) -> dict:
    r = _chamar(email, "get", f"/api/conversas/funil?{_periodo()}&dividir=vendedor")
    _garante(r.status_code == 200, f"funil → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()


# ── História 1 — primeira resposta ───────────────────────────────────────────────────────────────


def cen_01() -> None:
    cid = _recebida(1, "a", atras_s=12 * 60)
    _recebida(1, "b", atras_s=6 * 60)  # a segunda dela não muda a primeira
    _texto(estado["ana"], cid, "c1")
    linha = _primeira(cid)
    _garante(linha.primeira_recebida_em is not None, "primeira mensagem não gravada")
    _garante(
        abs((_agora() - timedelta(minutes=12) - linha.primeira_recebida_em).total_seconds()) < 5,
        f"primeira mensagem {linha.primeira_recebida_em} não é a de 12 min atrás",
    )
    _garante(linha.primeira_resposta_em is not None, "primeira resposta não gravada")
    _garante(
        linha.primeira_resposta_por_id == estado["ana_id"], "autor da primeira resposta errado"
    )
    _garante(
        linha.primeira_resposta_origem == "plataforma", f"origem {linha.primeira_resposta_origem}"
    )
    pr = _venda(estado["ana"], cid)["primeira_resposta"]
    _garante(pr["minutos"] in (11, 12, 13), f"minutos {pr['minutos']}")
    _garante((pr["autor"] or {}).get("id") == estado["ana_id"], f"autor no painel {pr['autor']}")
    _texto(estado["bia"], cid, "c1b")  # a segunda resposta não troca a primeira
    _garante(
        _primeira(cid).primeira_resposta_por_id == estado["ana_id"],
        "a segunda resposta trocou a primeira",
    )


def cen_02() -> None:
    cid = _recebida(2, "a", atras_s=30 * 60)
    _eco(2, "a", atras_s=20 * 60)
    _texto(estado["ana"], cid, "c2")
    linha = _primeira(cid)
    _garante(
        linha.primeira_resposta_origem == "celular", f"origem {linha.primeira_resposta_origem}"
    )
    _garante(linha.primeira_resposta_por_id is None, "eco do celular ganhou autor")
    pr = _venda(estado["ana"], cid)["primeira_resposta"]
    _garante(pr["autor"] is None and pr["origem"] == "celular", f"painel {pr}")
    _garante(pr["minutos"] in (9, 10, 11), f"minutos {pr['minutos']}")


def cen_03() -> None:
    # (a) a primeira resposta recusada depois do aceite deixa de valer; a próxima toma o lugar.
    cid = _recebida(3, "a", atras_s=5 * 60)
    _texto(estado["ana"], cid, "c3a")
    wamid = _no_banco(
        "SELECT externo_id FROM conversa_mensagens WHERE conversa_id=:i AND direcao='enviada' "
        "ORDER BY id DESC LIMIT 1",
        i=cid,
    )[0]
    _garante(
        _primeira(cid).primeira_resposta_por_id == estado["ana_id"], "primeira resposta não gravada"
    )
    _status_falhou(wamid, 3)
    linha = _primeira(cid)
    _garante(linha.primeira_resposta_em is None, f"resposta recusada continua valendo: {linha}")
    _texto(estado["bia"], cid, "c3b")
    _garante(
        _primeira(cid).primeira_resposta_por_id == estado["bia_id"],
        "a resposta seguinte não tomou o lugar",
    )
    # (b) o envio da equipe ANTES da primeira mensagem dela não conta.
    _eco(4, "antes", atras_s=10 * 60)
    cid4 = _conversa_id(4)
    _garante(
        _primeira(cid4).primeira_resposta_em is None, "eco antes da cliente virou primeira resposta"
    )
    _recebida(4, "a", atras_s=5 * 60)
    linha = _primeira(cid4)
    _garante(
        linha.primeira_recebida_em is not None and linha.primeira_resposta_em is None,
        f"envio anterior contou: {linha}",
    )
    # (c) reação da cliente não é primeira mensagem.
    _recebida(5, "reacao", atras_s=60, tipo="reaction")
    _garante(
        _primeira(_conversa_id(5)).primeira_recebida_em is None, "reação virou primeira mensagem"
    )


# ── História 2 — perdida ─────────────────────────────────────────────────────────────────────────


def cen_04() -> None:
    cid = estado["conv"][1]
    r = _chamar(estado["ana"], "post", f"/api/conversas/{cid}/lembrete", {})
    _garante(r.status_code == 200, f"lembrete → {r.status_code} {r.get_data(as_text=True)[:200]}")
    r = _chamar(estado["ana"], "post", f"/api/conversas/{cid}/perdida", {"motivo": "preco"})
    _garante(r.status_code == 200, f"perdida → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(r.get_json()["venda"]["perda"]["rotulo"] == "Achou caro", "rótulo do motivo")
    linha = _no_banco(
        "SELECT perdida_em, perdida_motivo, perdida_por_id, lembrar_em FROM conversas WHERE id=:i",
        i=cid,
    )
    _garante(
        linha.perdida_em is not None and linha.perdida_motivo == "preco",
        f"perda não gravada: {linha}",
    )
    _garante(linha.perdida_por_id == estado["ana_id"], "quem marcou")
    _garante(linha.lembrar_em is None, "marcar perdida não cancelou o lembrete")
    # FR-009a: a mensagem nova da cliente não reabre.
    _recebida(1, "volta")
    _garante(
        _no_banco("SELECT perdida_em FROM conversas WHERE id=:i", i=cid)[0] is not None,
        "mensagem nova reabriu a perdida",
    )
    r = _chamar(estado["bia"], "delete", f"/api/conversas/{cid}/perdida")
    _garante(r.status_code == 200, f"reabrir → {r.status_code}")
    linha = _no_banco(
        "SELECT perdida_em, perdida_motivo, perdida_nota, perdida_por_id FROM conversas WHERE id=:i",
        i=cid,
    )
    _garante(tuple(linha) == (None, None, None, None), f"reabrir não apagou: {linha}")


def cen_05() -> None:
    cid = estado["conv"][2]
    url = f"/api/conversas/{cid}/perdida"
    r = _chamar(estado["ana"], "post", url, {"motivo": "outro"})
    _garante(
        r.status_code == 422 and "frase" in (_erro(r).get("fields") or {}),
        f"outro sem frase → {r.status_code}",
    )
    r = _chamar(estado["ana"], "post", url, {"motivo": "inventado"})
    _garante(
        r.status_code == 422 and "motivo" in (_erro(r).get("fields") or {}),
        f"motivo inventado → {r.status_code}",
    )
    r = _chamar(estado["ana"], "post", url, {"motivo": "outro", "frase": "x" * 301})
    _garante(
        r.status_code == 422 and "frase" in (_erro(r).get("fields") or {}),
        f"frase longa → {r.status_code}",
    )
    _garante(
        _no_banco("SELECT perdida_em FROM conversas WHERE id=:i", i=cid)[0] is None,
        "a recusa gravou",
    )
    r = _chamar(estado["ana"], "post", url, {"motivo": "outro", "frase": "Mudou de cidade."})
    _garante(r.status_code == 200, f"outro com frase → {r.status_code}")
    _chamar(estado["ana"], "delete", url)


def cen_06() -> None:
    antes = estado["funil_antes"]
    cid3 = estado["conv"][3]
    r = _chamar(estado["ana"], "post", f"/api/conversas/{cid3}/perdida", {"motivo": "sem_resposta"})
    _garante(r.status_code == 200, f"perdida → {r.status_code}")
    depois = _funil(estado["ana"])
    _garante(depois["perdidas"] - antes.get("perdidas", 0) == 1, f"perdidas {depois['perdidas']}")
    motivos = {m["codigo"]: m["quantidade"] for m in depois["motivos_de_perda"]}
    motivos_antes = {m["codigo"]: m["quantidade"] for m in antes.get("motivos_de_perda", [])}
    _garante(
        motivos.get("sem_resposta", 0) - motivos_antes.get("sem_resposta", 0) == 1,
        f"motivos {motivos}",
    )
    pr, pr_antes = depois["primeira_resposta"], antes.get("primeira_resposta") or {}
    # Conversas 1, 2 e 3 respondidas (a 2 sem autor); a 4 ainda sem resposta.
    _garante(pr["respondidas"] - pr_antes.get("respondidas", 0) == 3, f"respondidas {pr}")
    _garante(pr["sem_autor"] - pr_antes.get("sem_autor", 0) == 1, f"sem autor {pr}")
    _garante(pr["sem_resposta"] - pr_antes.get("sem_resposta", 0) >= 1, f"sem resposta {pr}")
    _garante(pr["mediana_minutos"] is not None, "mediana vazia")
    _garante("qualificadas" in depois, "funil sem qualificadas")
    grupo = next((g for g in depois["grupos"] if g["chave"] == str(estado["ana_id"])), None)
    _garante(
        grupo is not None and grupo.get("mediana_minutos") is not None, f"grupo da Ana {grupo}"
    )
    r = _chamar(estado["ana"], "get", f"/api/conversas/funil/parados?{_periodo()}&etapa=chegou")
    parada = next((c for c in r.get_json()["conversas"] if c["id"] == cid3), None)
    _garante(
        parada is not None and (parada.get("perdida") or {}).get("motivo") == "sem_resposta",
        f"parados sem a perda: {parada}",
    )


# ── História 3 — qualificada ─────────────────────────────────────────────────────────────────────


def cen_07() -> None:
    ficha7 = _ficha(7)
    cid7 = _recebida(7, "a", atras_s=3600)
    _ligar_ficha(cid7, ficha7)
    _orcamento(ficha7, _agora(), now_sp().date() + timedelta(days=30))
    q = _venda(estado["ana"], cid7)["qualificacao"]
    sinais = {s["chave"] for s in q["sinais"]}
    _garante(q["pontos"] == 3 and sinais == {"orcamento", "data_proxima"}, f"pontuação {q}")
    _garante(q["qualificada"] is True and q["pela"] == "regra", f"qualificada {q}")
    # Recompra: a ficha já tinha um evento vivo antes do primeiro contato.
    ficha8 = _ficha(8)
    with app.app_context():
        evento = CalendarEvent(
            google_event_id=f"{PREFIX}antigo-{uuid.uuid4().hex[:8]}",
            title=f"{PREFIX}Festa antiga",
            start_at=datetime.now() - timedelta(days=380),
            source="platform",
            created_at=_agora() - timedelta(days=400),
        )
        db.session.add(evento)
        db.session.flush()
        db.session.add(
            EventClient(event_id=evento.id, client_id=ficha8, relationship_type="Contratante")
        )
        db.session.commit()
    cid8 = _recebida(8, "a", atras_s=600)
    _ligar_ficha(cid8, ficha8)
    q = _venda(estado["ana"], cid8)["qualificacao"]
    _garante(
        q["pontos"] == 2 and [s["chave"] for s in q["sinais"]] == ["recompra"], f"recompra {q}"
    )
    _garante(q["qualificada"] is False, "2 pontos não qualifica")


def cen_08() -> None:
    cid7 = estado["conv"][7]
    url = f"/api/conversas/{cid7}/qualificacao"
    r = _chamar(estado["bia"], "post", url, {"decisao": "nao_qualificada"})
    _garante(r.status_code == 200, f"decisão → {r.status_code} {r.get_data(as_text=True)[:200]}")
    q = r.get_json()["venda"]["qualificacao"]
    _garante(q["qualificada"] is False and q["pela"] == "decisao", f"decisão não venceu: {q}")
    _garante(
        (q["decidida_por"] or {}).get("id") == estado["bia_id"] and q["pontos"] == 3,
        f"quem/pontos {q}",
    )
    r = _chamar(estado["bia"], "post", url, {"decisao": "talvez"})
    _garante(
        r.status_code == 422 and "decisao" in (_erro(r).get("fields") or {}),
        f"decisão inválida → {r.status_code}",
    )
    r = _chamar(estado["bia"], "post", url, {"decisao": None})
    q = r.get_json()["venda"]["qualificacao"]
    _garante(
        q["qualificada"] is True and q["pela"] == "regra" and q["decidida_por"] is None,
        f"regra não voltou: {q}",
    )


# ── História 4 — lista ───────────────────────────────────────────────────────────────────────────


def cen_09() -> None:
    cid9 = _recebida(9, "a", atras_s=120)
    with app.app_context():
        db.session.add(
            ConversaAnuncio(
                conversa_id=cid9,
                canal="whatsapp",
                chave=f"{PREFIX}anuncio-9",
                tipo="anuncio",
                anuncio_id=f"{PREFIX}ad-9",
                titulo="Festa com personagens",
                momento=_agora() - timedelta(minutes=3),
                created_at=_agora(),
            )
        )
        db.session.commit()
    _chamar(estado["ana"], "post", f"/api/conversas/{cid9}/lembrete", {})
    lista = _lista(estado["ana"], contar=True)
    estado["consultas_da_lista"] = _consultas["n"]
    itens = {c["id"]: c for c in lista["conversas"]}
    v9, v7, v3 = (
        itens[cid9]["venda"],
        itens[estado["conv"][7]]["venda"],
        itens[estado["conv"][3]]["venda"],
    )
    _garante(
        v9["anuncio"] is True and v9["etapa"] == "chegou" and v9["lembrete_em"], f"selos da 9: {v9}"
    )
    _garante(
        v7["anuncio"] is False and v7["etapa"] == "orcamento" and v7["qualificada"] is True,
        f"selos da 7: {v7}",
    )
    _garante((v3["perdida"] or {}).get("motivo") == "sem_resposta", f"selos da 3: {v3}")
    # SC-007: o resumo é em lote — o número de consultas não cresce com a página.
    _garante(_consultas["n"] <= 25, f"a lista fez {_consultas['n']} consultas")


def cen_10() -> None:
    cid9 = estado["conv"][9]
    esperando = _lista(estado["ana"], "?recorte=esperando")["conversas"]
    _garante(any(c["id"] == cid9 for c in esperando), "a 9 (esperando) não veio")
    _garante(all(c["aguardando_desde"] for c in esperando), "veio conversa sem espera")
    anuncio = _lista(estado["ana"], "?recorte=anuncio")["conversas"]
    _garante(
        [c["id"] for c in anuncio if c["id"] in estado["conv"].values()] == [cid9],
        f"anúncio {anuncio}",
    )


def cen_11() -> None:
    agora = _agora()
    oito = agora - timedelta(days=8)
    for n in (11, 12, 13, 14):
        _ficha(n)
    c11 = _conversa_direta(11, oito, estado["ficha"][11], estado["bia_id"])
    c12 = _conversa_direta(12, oito, estado["ficha"][12], estado["bia_id"])
    c13 = _conversa_direta(13, oito, estado["ficha"][13], None)
    c14 = _conversa_direta(14, oito, estado["ficha"][14], None)
    estado["conv"].update({11: c11, 12: c12, 13: c13, 14: c14})
    for n, cid, dias in ((11, c11, 6), (12, c12, 3), (13, c13, 6), (14, c14, 6)):
        orc = _orcamento(
            estado["ficha"][n], agora - timedelta(days=dias), now_sp().date() + timedelta(days=20)
        )
        _envio(orc, cid, agora - timedelta(days=dias))
        estado.setdefault("orcamentos", {})[n] = orc
    _no_banco_escrever(
        "INSERT INTO form_responses (form_type, data, contact_name, client_id, event_link_ambiguous, "
        "event_link_locked, created_at) VALUES ('comum', '[]', :n, :c, false, false, :t)",
        n=f"{PREFIX}Formulário 13",
        c=estado["ficha"][13],
        t=agora - timedelta(days=1),
    )
    _no_banco_escrever(
        "UPDATE conversas SET perdida_em=:t, perdida_motivo='preco' WHERE id=:i", t=agora, i=c14
    )

    def ids(dias: int) -> set[int]:
        lista = _lista(estado["ana"], f"?recorte=orcamento_parado&dias={dias}")["conversas"]
        return {c["id"] for c in lista} & {c11, c12, c13, c14}

    _garante(ids(2) == {c11, c12}, f"2 dias: {ids(2)}")
    _garante(ids(5) == {c11}, f"5 dias: {ids(5)}")
    _garante(ids(9) == set(), f"9 dias: {ids(9)}")
    r = _chamar(estado["ana"], "get", "/api/conversas?recorte=xyz")
    _garante(
        r.status_code == 422 and "recorte" in (_erro(r).get("fields") or {}),
        f"recorte inválido → {r.status_code}",
    )
    r = _chamar(estado["ana"], "get", "/api/conversas?recorte=orcamento_parado&dias=4")
    _garante(
        r.status_code == 422 and "dias" in (_erro(r).get("fields") or {}),
        f"dias inválido → {r.status_code}",
    )


# ── História 6 — criar evento ────────────────────────────────────────────────────────────────────


def _corpo_do_evento(conversa_id, ficha_id: int, orcamento_id: int | None) -> dict:
    return {
        "title": f"{PREFIX}Festa da conversa",
        "event_type": "",
        "date": (now_sp().date() + timedelta(days=20)).isoformat(),
        "start": "14:00",
        "end": "15:00",
        "valor_a_definir": True,
        "seller_id": estado["bia_id"],
        "orcamento_history_id": orcamento_id,
        "clients": [{"client_id": ficha_id, "relation": "Contratante"}],
        "conversa_id": conversa_id,
    }


def cen_12() -> None:
    c11 = estado["conv"][11]
    fech = _venda(estado["ana"], c11)["fechamento"]
    _garante(fech["orcamento_id"] == estado["orcamentos"][11], f"orçamento {fech}")
    _garante((fech["cliente"] or {}).get("id") == estado["ficha"][11], f"ficha {fech}")
    _garante((fech["vendedor"] or {}).get("id") == estado["bia_id"], f"vendedor {fech}")
    _no_banco_escrever(
        "UPDATE conversas SET perdida_em=:t, perdida_motivo='preco' WHERE id=:i", t=_agora(), i=c11
    )
    # A ficha vai sem os `clients` da tela: o ponto único a põe entre as clientes do evento.
    corpo = _corpo_do_evento(c11, estado["ficha"][11], None)
    corpo["clients"] = []
    r = _chamar(estado["ana"], "post", "/api/events", corpo)
    _garante(
        r.status_code == 201, f"criar evento → {r.status_code} {r.get_data(as_text=True)[:300]}"
    )
    evento_id = r.get_json()["event"]["id"]
    estado["evento_criado"] = evento_id
    ligada = _no_banco(
        "SELECT count(*) FROM event_clients WHERE event_id=:e AND client_id=:c",
        e=evento_id,
        c=estado["ficha"][11],
    )[0]
    _garante(ligada == 1, "a ficha da conversa não entrou no evento")
    _garante(
        _no_banco("SELECT perdida_em FROM conversas WHERE id=:i", i=c11)[0] is None,
        "a perda não saiu",
    )


def cen_13() -> None:
    antes = len(google)
    eventos = _no_banco("SELECT count(*) FROM calendar_events WHERE title LIKE :p", p=f"{PREFIX}%")[
        0
    ]
    r = _chamar(
        estado["ana"],
        "post",
        "/api/events",
        _corpo_do_evento(999_999_999, estado["ficha"][12], None),
    )
    # Lote de 17/11: a validação da 348 (`_erros_da_origem`) recusa a conversa junto com os outros campos do
    # formulário (400 + `fields`), antes da conferência da 349 e antes do Google. O que importa é a recusa com o
    # campo marcado e nada criado.
    _garante(
        r.status_code == 400 and "conversa_id" in (_erro(r).get("fields") or {}),
        f"conversa inexistente → {r.status_code}",
    )
    r = _chamar(
        estado["ana"], "post", "/api/events", _corpo_do_evento("abc", estado["ficha"][12], None)
    )
    _garante(r.status_code == 400, f"conversa_id texto → {r.status_code}")
    depois = _no_banco("SELECT count(*) FROM calendar_events WHERE title LIKE :p", p=f"{PREFIX}%")[
        0
    ]
    _garante(
        depois == eventos and len(google) == antes, "a recusa criou evento ou falou com o Google"
    )


# ── História 7 — lembrete e régua ────────────────────────────────────────────────────────────────


def cen_14() -> None:
    cid7 = estado["conv"][7]
    r = _chamar(estado["ana"], "post", f"/api/conversas/{cid7}/lembrete", {})
    _garante(r.status_code == 200, f"lembrete → {r.status_code}")
    amanha_9h = datetime.combine(now_sp().date() + timedelta(days=1), hora(9))
    linha = _no_banco("SELECT lembrar_em, lembrar_para_id FROM conversas WHERE id=:i", i=cid7)
    _garante(linha.lembrar_em == _utc_de_sp(amanha_9h), f"lembrete às {linha.lembrar_em}")
    _garante(linha.lembrar_para_id == estado["ana_id"], "lembrete de outra pessoa")
    momento = _as(10)
    _no_banco_escrever(
        "UPDATE conversas SET lembrar_em=:t WHERE id=:i",
        t=_utc_de_sp(momento) - timedelta(minutes=1),
        i=cid7,
    )
    _avisar(momento)
    _avisar(momento)
    avisos = _avisos(cid7, "conversa.lembrete")
    _garante([a.user_id for a in avisos] == [estado["ana_id"]], f"avisos do lembrete {avisos}")
    _garante(
        _no_banco("SELECT lembrar_em FROM conversas WHERE id=:i", i=cid7)[0] is None,
        "lembrete vencido ficou",
    )
    r = _chamar(estado["ana"], "post", f"/api/conversas/{cid7}/lembrete", {})
    r = _chamar(estado["ana"], "delete", f"/api/conversas/{cid7}/lembrete")
    _garante(
        r.status_code == 200 and r.get_json()["venda"]["lembrete"] is None, "cancelar lembrete"
    )


def cen_15() -> None:
    c11, c12, c13, c14 = (estado["conv"][n] for n in (11, 12, 13, 14))
    # c11 virou evento no cenário 12: volta a ser só orçamento parado para a régua.
    _no_banco_escrever(
        "UPDATE calendar_events SET cancelled_at=:t WHERE id=:e",
        t=_agora(),
        e=estado["evento_criado"],
    )
    # A rodada das 10h do cenário 14 já pode ter avisado a 12 (degrau 2): conta-se a diferença.
    antes = {c: len(_avisos(c, "conversa.orcamento_parado")) for c in (c11, c12)}
    _avisar(_as(22))
    depois = {c: len(_avisos(c, "conversa.orcamento_parado")) for c in (c11, c12)}
    _garante(depois == antes, f"a régua avisou às 22h: {antes} → {depois}")
    _avisar(_as(10))
    _avisar(_as(10, 30))
    a11, a12 = _avisos(c11, "conversa.orcamento_parado"), _avisos(c12, "conversa.orcamento_parado")
    _garante(len(a11) == 1 and a11[0].user_id == estado["bia_id"], f"régua da 11: {a11}")
    _garante(
        "há 5 dias" in a11[0].title and a11[0].dedupe_key.endswith(":5"), f"degrau da 11: {a11[0]}"
    )
    _garante(len(a12) == 1 and a12[0].dedupe_key.endswith(":2"), f"régua da 12: {a12}")
    _garante(not _avisos(c13, "conversa.orcamento_parado"), "a régua avisou a que tem formulário")
    _garante(not _avisos(c14, "conversa.orcamento_parado"), "a régua avisou a perdida")


def cen_16() -> None:
    ids = list(estado["conv"].values())
    antes = _no_banco("SELECT count(*) FROM conversa_mensagens WHERE conversa_id = ANY(:i)", i=ids)[
        0
    ]
    enviados = len(meta.enviados)
    _no_banco_escrever(
        "UPDATE conversas SET lembrar_em=:t, lembrar_para_id=:u WHERE id=:i",
        t=_utc_de_sp(_as(11)) - timedelta(minutes=1),
        u=estado["ana_id"],
        i=estado["conv"][9],
    )
    _avisar(_as(11))
    depois = _no_banco(
        "SELECT count(*) FROM conversa_mensagens WHERE conversa_id = ANY(:i)", i=ids
    )[0]
    _garante(
        depois == antes and len(meta.enviados) == enviados, "lembrete ou régua escreveu na conversa"
    )


def cen_17() -> None:
    cid = estado["conv"][7]
    chamadas = (
        ("get", f"/api/conversas/{cid}/venda", None),
        ("post", f"/api/conversas/{cid}/perdida", {"motivo": "preco"}),
        ("delete", f"/api/conversas/{cid}/perdida", None),
        ("post", f"/api/conversas/{cid}/qualificacao", {"decisao": "qualificada"}),
        ("post", f"/api/conversas/{cid}/lembrete", {}),
        ("delete", f"/api/conversas/{cid}/lembrete", None),
        ("get", "/api/conversas?recorte=esperando", None),
    )
    for metodo, url, corpo in chamadas:
        r = _chamar(estado["cris"], metodo, url, corpo)
        _garante(r.status_code == 403, f"Casting {metodo.upper()} {url} → {r.status_code}")
    linha = _no_banco(
        "SELECT perdida_em, qualificacao, lembrar_em FROM conversas WHERE id=:i", i=cid
    )
    _garante(
        linha.perdida_em is None and linha.qualificacao is None and linha.lembrar_em is None,
        "o Casting gravou",
    )


# ── Preparo e limpeza ────────────────────────────────────────────────────────────────────────────


def preparar() -> None:
    estado["ana"], estado["ana_id"] = _usuario("Ana", RoleName.COMERCIAL)
    estado["bia"], estado["bia_id"] = _usuario("Bia", RoleName.COMERCIAL)
    estado["cris"], estado["cris_id"] = _usuario("Cris", RoleName.CASTING)

    def contar(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        if _consultas["contando"]:
            _consultas["n"] += 1

    event.listen(db.engine, "before_cursor_execute", contar)


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
    # A exclusão local da agenda (sem o Google): limpa as tabelas sem cascade e o elenco que a criação gera.
    from app.calendar.routes import _delete_event

    for evento in CalendarEvent.query.filter(CalendarEvent.title.like(f"%{PREFIX}%")).all():
        db.session.execute(text("DELETE FROM event_clients WHERE event_id=:e"), {"e": evento.id})
        _delete_event(evento, also_from_google=False)
    db.session.flush()
    db.session.execute(
        text("DELETE FROM form_responses WHERE contact_name LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text("DELETE FROM orcamento_history WHERE client_name LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text(
            "DELETE FROM event_clients WHERE client_id IN (SELECT id FROM clients WHERE name LIKE :p)"
        ),
        {"p": f"{PREFIX}%"},
    )
    db.session.execute(text("DELETE FROM clients WHERE name LIKE :p"), {"p": f"{PREFIX}%"})
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
        "(SELECT count(*) FROM clients WHERE name LIKE :p) + "
        "(SELECT count(*) FROM calendar_events WHERE title LIKE :p) + "
        "(SELECT count(*) FROM orcamento_history WHERE client_name LIKE :p)",
        c=CONTATOS,
        p=f"{PREFIX}%",
    )[0]
    _garante(sobras == 0, f"sobraram {sobras} registros de teste")


CENARIOS = [
    ("1. primeira mensagem, primeira resposta, autor e origem", cen_01),
    ("2. eco do celular: primeira resposta sem autor", cen_02),
    ("3. falha depois do aceite, envio antes da cliente e reação", cen_03),
    ("4. perdida, lembrete cancelado, mensagem não reabre, reabrir", cen_04),
    ("5. motivo inválido e 'Outro' sem frase (DEVE falhar)", cen_05),
    ("6. funil: perdidas, motivos, primeira resposta e parados", cen_06),
    ("7. pontuação por regras e recompra", cen_07),
    ("8. decisão manual vence e volta para a regra", cen_08),
    ("9. lista com selos, em lote", cen_09),
    ("10. recortes esperando e anúncio", cen_10),
    ("11. recorte orçamento parado 2/5/9 e parâmetros inválidos", cen_11),
    ("12. o que levar ao evento e o ponto único", cen_12),
    ("13. conversa inexistente na criação de evento (DEVE falhar)", cen_13),
    ("14. lembrar amanhã às 9h e o aviso vencido uma vez", cen_14),
    ("15. régua 2/5/9: degrau atual, uma vez, nada à noite", cen_15),
    ("16. lembrete e régua não escrevem na conversa", cen_16),
    ("17. Casting nas rotas da venda (DEVE falhar)", cen_17),
]


def main() -> int:
    so = None
    manter = "--manter" in sys.argv[1:]
    for arg in sys.argv[1:]:
        if arg.startswith("--so="):
            so = {int(n) for n in arg.split("=", 1)[1].split(",") if n.strip()}
    banco = os.environ["DATABASE_URL"].rsplit("/", 1)[-1]
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        limpar()  # sobra de uma rodada interrompida
        preparar()
        estado["funil_antes"] = {}
    print(f"Feature 349 — o comercial mede e fecha, contra {banco}")
    try:
        try:
            estado["funil_antes"] = _funil(estado["ana"])
        except Exception as exc:  # noqa: BLE001 — antes do núcleo o funil ainda não tem os campos novos
            print(f"  (funil de antes indisponível: {exc})")
        # Fora de `app.app_context()`: o test client dentro dele vaza a sessão entre requisições.
        for indice, (nome, fn) in enumerate(CENARIOS, start=1):
            if so is None or indice in so:
                cenario(nome, fn)
    finally:
        if manter:
            print(f"  --manter: dados {PREFIX} ficam para conferir a tela (senha: {SENHA})")
        else:
            with app.app_context():
                cenario("18. limpeza", limpar)
        for _nome, _fn in _REAIS.items():
            setattr(_wc, _nome, _fn)
        _rotas.insert_event = _INSERT_EVENT_REAL

    ok = sum(1 for _, passou, _ in resultados if passou)
    print(
        f"\n{ok}/{len(resultados)} OK · escapes de rede: {len(_ESCAPES)} · consultas da lista: "
        f"{estado.get('consultas_da_lista', '—')}"
    )
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) and not _ESCAPES else 1


if __name__ == "__main__":
    sys.exit(main())
