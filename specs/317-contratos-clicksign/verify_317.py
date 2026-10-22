"""Verificação da feature 317 — contrato da ClickSign ligado à venda e "Cobrar contrato".

Os 26 cenários da tabela da spec (seção "Verificação"). A ClickSign NUNCA é chamada: as funções de
`app.integracoes.clicksign_client` viram um dublê com envelopes em memória (`ContaClickSign`), e um
disjuntor de rede derruba qualquer conexão de saída que não seja o Postgres local — instalado ANTES
de importar o app, em `socket.socket.connect` E em `socket.create_connection` (o disjuntor da 310
só pegava o segundo, e o `requests` passa pelo primeiro via urllib3).

Todo evento de teste tem "[TESTE verify 317] pode apagar" no título e `v317-` no `google_event_id`;
todo envelope do dublê começa com `v317-`. As colunas `clicksign_*` do `site_settings` são
salvas no início e devolvidas no fim (o `manto_local` é compartilhado com outros worktrees).

Escrita conferida por **conexão separada** e requisições HTTP **fora** de `app.app_context()`.

Rodar contra o manto_local (PowerShell, a partir de C:\\tmp\\mp317)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    C:/Users/schim/Desktop/Manto_Platform/.venv/Scripts/python.exe specs/317-contratos-clicksign/verify_317.py [--so=1,2]
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import sys
import traceback
import unicodedata
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
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
        raise OSError(f"verify 317: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 317: conexão de saída bloqueada para {_host_de(endereco)}")
    return _create_connection_original(endereco, *args, **kwargs)


socket.socket.connect = _connect_local
socket.create_connection = _create_connection_local

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ["CLICKSIGN_AVISO_SINCRONO"] = "true"
os.environ.pop("CLICKSIGN_ALLOW_LOCAL_CALLS", None)
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    Client,
    EventClient,
    EventContract,
    FormResponse,
    Role,
    SiteSetting,
    User,
)

PREFIX = "v317-"
SENHA = "verify-317-senha"
TITULO_TESTE = "[TESTE verify 317] pode apagar"
SEGREDO = "segredo-do-verify-317"
TOKEN_FALSO = "token-falso-do-verify-317"

app = create_app()
app.config["TESTING"] = True
app.config["CLICKSIGN_ACCESS_TOKEN"] = TOKEN_FALSO
app.config["CLICKSIGN_AVISO_SINCRONO"] = True
limiter.enabled = False

# ── O Google fica de fora ────────────────────────────────────────────────────────────────────────
import app.calendar.event_ops as _event_ops  # noqa: E402
import app.calendar.routes as _rotas  # noqa: E402
import app.calendar.service as _servico  # noqa: E402


def _google_real(*_args, **_kwargs):
    raise RuntimeError("verify 317: Google real")


_rotas.insert_event = lambda *a, **k: {"id": f"{PREFIX}gc"}
for _modulo in (_rotas, _servico, _event_ops):
    if hasattr(_modulo, "update_event"):
        _modulo.update_event = lambda *a, **k: {}
_servico.insert_event = _google_real
_servico.load_credentials = _google_real

# ── O dublê da ClickSign ─────────────────────────────────────────────────────────────────────────
import app.integracoes.clicksign_client as _cliente_cs  # noqa: E402

_REAIS = {
    nome: getattr(_cliente_cs, nome)
    for nome in (
        "listar_envelopes",
        "signatarios",
        "eventos",
        "documentos",
        "documento",
        "baixar",
        "listar_webhooks",
        "criar_webhook",
        "remover_webhook",
    )
}
PDF_FALSO = b"%PDF-1.4\n% verify 317\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _iso(momento: datetime) -> str:
    return momento.strftime("%Y-%m-%dT%H:%M:%S.000-03:00")


class ContaClickSign:
    """A conta da ClickSign em memória: envelopes, signatários, eventos e o PDF assinado."""

    def __init__(self) -> None:
        self.envelopes: dict[str, dict] = {}
        self.chamadas = {"listar": 0, "baixar": 0}

    def envelope(
        self,
        chave: str,
        nome: str,
        *,
        status: str = "running",
        criado: datetime | None = None,
        prazo_dias: int = 5,
        telefone: str | None = "do_nome",
        email: str | None = None,
        canal: str = "whatsapp",
        recusado: bool = False,
    ) -> str:
        criado = criado or datetime.combine(estado["hoje"], time(10, 0))
        if telefone == "do_nome":
            # Na conta real o signatário é o WhatsApp que o fluxo põe no nome (sem o 55).
            from app.contratos.contratos_ops import ler_nome

            lido = ler_nome(nome).telefone
            telefone = lido[2:] if lido else None
        eid = f"{PREFIX}{chave}"
        self.envelopes[eid] = {
            "id": eid,
            "attributes": {
                "name": nome,
                "status": status,
                "created": _iso(criado),
                "modified": _iso(criado),
                "deadline_at": _iso(criado + timedelta(days=prazo_dias)),
            },
            "signers": [
                {
                    "id": f"{eid}-s",
                    "attributes": {
                        "name": "Signatária de teste",
                        "phone_number": telefone,
                        "email": email,
                        "communicate_events": {
                            "signature_request": canal,
                            "signature_reminder": "none",
                        },
                    },
                }
            ],
            "events": [{"attributes": {"name": "refusal", "created": _iso(criado)}}]
            if recusado
            else [],
            "documents": [{"id": f"{eid}-d", "attributes": {"filename": f"{nome}.pdf"}}],
        }
        return eid

    def mudar(self, eid: str, *, status: str, quando: datetime | None = None) -> None:
        env = self.envelopes[eid]
        quando = quando or datetime.combine(estado["hoje"], time(12, 0))
        env["attributes"]["status"] = status
        env["attributes"]["modified"] = _iso(quando)
        if status == "closed":
            env["events"].insert(0, {"attributes": {"name": "sign", "created": _iso(quando)}})

    # As funções do cliente, com a mesma assinatura (a trava é ignorada pelo dublê).
    def listar_envelopes(
        self,
        *,
        pagina: int = 1,
        modificado_desde=None,
        modificado_ate=None,
        criado_desde=None,
        criado_ate=None,
        status=None,
        **_kw,
    ) -> dict:
        self.chamadas["listar"] += 1
        itens = []
        for env in self.envelopes.values():
            a = env["attributes"]
            mod = datetime.fromisoformat(a["modified"]).date()
            cri = datetime.fromisoformat(a["created"]).date()
            if modificado_desde and mod < modificado_desde:
                continue
            if modificado_ate and mod > modificado_ate:
                continue
            if criado_desde and cri < criado_desde:
                continue
            if criado_ate and cri > criado_ate:
                continue
            if status and a["status"] != status:
                continue
            itens.append({"id": env["id"], "type": "envelopes", "attributes": dict(a)})
        inicio = (pagina - 1) * 50
        return {"data": itens[inicio : inicio + 50], "meta": {"record_count": len(itens)}}

    def signatarios(self, envelope_id: str, **_kw) -> list:
        return self.envelopes[envelope_id]["signers"]

    def eventos(self, envelope_id: str, **_kw) -> list:
        return self.envelopes[envelope_id]["events"]

    def documentos(self, envelope_id: str, **_kw) -> list:
        return self.envelopes[envelope_id]["documents"]

    def documento(self, envelope_id: str, document_id: str, **_kw) -> dict:
        doc = dict(self.envelopes[envelope_id]["documents"][0])
        status = self.envelopes[envelope_id]["attributes"]["status"]
        arquivos = {"original": f"https://s3.falso/{document_id}/original"}
        if status == "closed":
            arquivos["signed"] = f"https://s3.falso/{document_id}/signed"
        doc["links"] = {"files": arquivos}
        return doc

    def baixar(self, url: str, **_kw) -> bytes:
        self.chamadas["baixar"] += 1
        return PDF_FALSO

    def listar_webhooks(self, **_kw) -> list:
        return []

    def criar_webhook(self, url_destino, nomes_de_eventos, **_kw) -> dict:
        return {"id": f"{PREFIX}wh", "attributes": {"secret": "a" * 32, "endpoint": url_destino}}

    def remover_webhook(self, webhook_id, **_kw) -> None:
        return None


conta = ContaClickSign()


def _instalar_duble() -> None:
    for nome in _REAIS:
        setattr(_cliente_cs, nome, getattr(conta, nome))


def _restaurar_cliente_real() -> None:
    for nome, funcao in _REAIS.items():
        setattr(_cliente_cs, nome, funcao)


_instalar_duble()

resultados: list[tuple[str, bool, str]] = []
estado: dict = {"ids": {}, "env": {}}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    """Lê pelo banco, por fora da sessão do app (o autoflush esconde falta de commit)."""
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchone()


def _no_banco_todas(sql: str, **params):
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


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


def _chamar(email: str, metodo: str, url: str, corpo: dict | None = None):
    """Uma requisição autenticada, fora de qualquer contexto de aplicação."""
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
        _garante(r.status_code == 200, f"login {email} → {r.status_code}")
        return getattr(c, metodo)(url, json=corpo) if corpo is not None else getattr(c, metodo)(url)


def _aviso(corpo: dict, segredo: str | None = SEGREDO):
    """POST do aviso da ClickSign, com o HMAC do corpo bruto (ou sem/errado)."""
    bruto = json.dumps(corpo).encode()
    cabecalhos = {"Content-Type": "application/json"}
    if segredo is not None:
        cabecalhos["Content-Hmac"] = (
            "sha256=" + hmac.new(segredo.encode(), bruto, hashlib.sha256).hexdigest()
        )
    with app.test_client() as c:
        return c.post("/api/webhooks/clicksign", data=bruto, headers=cabecalhos)


# ── Semeadura ────────────────────────────────────────────────────────────────────────────────────


def _d(dias: int) -> date:
    return estado["hoje"] + timedelta(days=dias)


def _nome_festa(dia: date, telefone: str, tema: str) -> str:
    """Nome no formato do fluxo "Contratos Monta": DDMMAAAA + (DD) NNNNN-NNNN + Tema."""
    fone = f"({telefone[2:4]}) {telefone[4:9]}-{telefone[9:]}"
    return f"{dia:%d%m%Y} + {fone} + {tema}"


def _evento(
    nome: str,
    dia: date,
    *,
    telefone: str | None = None,
    lider: int | None = None,
    cancelado: bool = False,
    cortesia: bool = False,
    titulo: str | None = None,
    valor: int = 3000,
) -> int:
    inicio = datetime.combine(dia, time(15, 0))
    ev = CalendarEvent(
        title=f"{titulo or nome} {TITULO_TESTE}",
        start_at=inicio,
        end_at=inicio + timedelta(hours=3),
        google_event_id=f"{PREFIX}{nome}",
        source="platform",
        sale_value=None if lider else valor,
        sale_value_gross=None if lider else valor,
        is_cortesia_permuta=cortesia,
        group_leader_id=lider,
        is_outside_sp=False,
        cancelled_at=datetime.utcnow() if cancelado else None,
    )
    db.session.add(ev)
    db.session.flush()
    if telefone:
        # O telefone é UNIQUE na ficha: a mesma cliente com duas festas é uma ficha só.
        cl = Client.query.filter_by(phone=telefone).first()
        if cl is None:
            cl = Client(
                name=f"{PREFIX}{nome}",
                phone=telefone,
                phone_display=f"+{telefone}",
                source="manual",
            )
            db.session.add(cl)
            db.session.flush()
        db.session.add(
            EventClient(event_id=ev.id, client_id=cl.id, relationship_type="Contratante")
        )
        ev.client_id = cl.id
    estado["ids"][nome] = ev.id
    return ev.id


def _formulario(event_id: int, telefone: str, tema: str) -> None:
    db.session.add(
        FormResponse(
            form_type="comum",
            data=json.dumps([{"secao": "Evento", "campos": [["tema_evento", "Tema", tema]]}]),
            contact_name=f"{PREFIX}formulario",
            contact_phone=telefone,
            event_id=event_id,
            event_link_source="manual",
        )
    )


def preparar() -> None:
    estado["hoje"] = now_sp().date()
    estado["comercial"] = _usuario("comercial", RoleName.COMERCIAL)
    estado["financeiro"] = _usuario("financeiro", RoleName.FINANCEIRO)
    estado["casting"] = _usuario("casting", RoleName.CASTING)

    s = SiteSetting.query.get(1)
    estado["site_original"] = {
        c: getattr(s, c)
        for c in (
            "clicksign_webhook_id",
            "clicksign_webhook_secret",
            "clicksign_webhook_secret_anterior",
            "clicksign_webhook_secret_anterior_ate",
            "clicksign_sync_at",
            "clicksign_sync_cursor",
            "clicksign_sync_pendente",
        )
    }
    s.clicksign_webhook_secret = SEGREDO
    s.clicksign_sync_at = None
    s.clicksign_sync_cursor = None
    s.clicksign_sync_pendente = False

    fones = {n: f"551190000{n:04d}" for n in range(1, 20)}
    estado["fones"] = fones
    ev = estado["ids"]
    # Venda A: aguardando, prazo amanhã → vermelho; cobrável.
    _evento("a", _d(10), telefone=fones[1], titulo="Festa Hot Wheels")
    # Venda B em grupo: principal + dia 2; o contrato leva a data do dia 2.
    _evento("b", _d(20), telefone=fones[2], titulo="Festa Galaxy")
    _evento("b2", _d(21), lider=ev["b"])
    # Empate: duas vendas no mesmo dia com o mesmo telefone.
    _evento("e1", _d(15), telefone=fones[3], titulo="Festa Frozen")
    _evento("e2", _d(15), telefone=fones[3], titulo="Festa Patrulha Canina")
    # Cancelada.
    _evento("c", _d(12), telefone=fones[4], cancelado=True)
    # Vigente: reenvio assinado × original cancelado; remarcação em processo.
    _evento("v", _d(25), telefone=fones[5])
    _evento("r", _d(30), telefone=fones[6])
    # Vencido e recusado.
    _evento("x", _d(5), telefone=fones[7])
    _evento("y", _d(6), telefone=fones[8])
    # Sem contrato: dentro e fora da janela de 30 dias.
    _evento("z", _d(7), telefone=fones[10])
    _evento("zz", _d(45), telefone=fones[11])
    # Cortesia entra (clarify).
    _evento("k", _d(9), telefone=fones[12], cortesia=True)
    # Canal e-mail.
    _evento("m", _d(11), telefone=fones[13])
    # Já aconteceu, sem contrato.
    _evento("p", _d(-3), telefone=fones[14])
    # Telefone só no formulário ligado.
    _evento("f", _d(13))
    _formulario(ev["f"], fones[15], "Bluey")
    # Avulso que vai virar dia de um grupo (cenário 25).
    _evento("g", _d(16), telefone=fones[16])
    _evento("g0", _d(16), telefone=fones[17])
    db.session.commit()

    agora = datetime.combine(estado["hoje"], time(9, 0))
    env = estado["env"]
    env["a"] = conta.envelope("a", _nome_festa(_d(10), fones[1], "Hot Wheels"), prazo_dias=1)
    env["b"] = conta.envelope("b", _nome_festa(_d(21), fones[2], "Galaxy"), status="closed")
    env["e1"] = conta.envelope("e1", _nome_festa(_d(15), fones[3], "Frozen"))
    env["e2"] = conta.envelope("e2", _nome_festa(_d(15), fones[3], "Bluey"))
    env["c"] = conta.envelope("c", _nome_festa(_d(12), fones[4], "Cancelada"))
    env["s"] = conta.envelope("s", _nome_festa(_d(40), fones[9], "Sem venda"))
    env["v_orig"] = conta.envelope(
        "v_orig",
        _nome_festa(_d(25), fones[5], "Sereia"),
        status="canceled",
        criado=agora - timedelta(days=3),
    )
    env["v_reenvio"] = conta.envelope(
        "v_reenvio",
        _nome_festa(_d(25), fones[5], "Sereia") + " (1)",
        status="closed",
        criado=agora - timedelta(days=2),
    )
    env["r1"] = conta.envelope(
        "r1",
        _nome_festa(_d(30), fones[6], "Lego"),
        status="closed",
        criado=agora - timedelta(days=5),
    )
    env["r2"] = conta.envelope(
        "r2", _nome_festa(_d(30), fones[6], "Lego"), criado=agora - timedelta(days=1)
    )
    env["x"] = conta.envelope("x", _nome_festa(_d(5), fones[7], "Circo"), status="canceled")
    env["y"] = conta.envelope(
        "y", _nome_festa(_d(6), fones[8], "Mickey"), status="canceled", recusado=True
    )
    env["k"] = conta.envelope("k", _nome_festa(_d(9), fones[12], "Natal"))
    env["m"] = conta.envelope(
        "m",
        _nome_festa(_d(11), fones[13], "Princesas"),
        canal="email",
        telefone=None,
        email="cliente@exemplo.com",
    )
    env["f"] = conta.envelope("f", _nome_festa(_d(13), fones[15], "Bluey"))
    env["g"] = conta.envelope("g", _nome_festa(_d(16), fones[16], "Astronauta"))
    env["art"] = conta.envelope(
        "art",
        unicodedata.normalize(
            "NFD", "Fulana de Tal_CONTRATO DE PRESTAÇÃO DE SERVIÇOS ARTÍSTICOS_Belém"
        ),
    )
    env["outro"] = conta.envelope("outro", "Declaração Estágio Supervisionado")
    env["data_ruim"] = conta.envelope("data_ruim", "31022026 + (11) 90000-0018 + Data impossível")
    env["mail"] = conta.envelope(
        "mail",
        f"{_d(11):%d-%m-%Y} + cliente@exemplo.com + Sereia",
        telefone=None,
        email="cliente@exemplo.com",
        canal="email",
    )


def _sincronizar(**kw) -> dict:
    from app.contratos import sincronizar_ops

    with app.app_context():
        return sincronizar_ops.sincronizar(**kw)


def _doc(chave: str):
    return _no_banco(
        "SELECT id, tipo, status, event_id, vinculo, vinculo_origem, vinculo_motivo, contrato_anexo_id, "
        "canal, data_lida, telefone_lido, tema_lido, anexo_pendente "
        "FROM clicksign_documentos WHERE envelope_id = :e",
        e=estado["env"][chave],
    )


def _contrato(email: str, nome: str) -> dict:
    r = _chamar(email, "get", f"/api/events/{estado['ids'][nome]}")
    _garante(r.status_code == 200, f"detalhe de {nome} → {r.status_code}")
    corpo = r.get_json()
    _garante("contrato" in corpo, f"detalhe de {nome} sem a chave `contrato`")
    return corpo


def _painel(email: str) -> dict:
    r = _chamar(email, "get", "/api/dashboard")
    _garante(r.status_code == 200, f"/api/dashboard → {r.status_code}")
    bloco = (r.get_json().get("comercial") or {}).get("contratos")
    _garante(isinstance(bloco, dict), f"painel sem `comercial.contratos`: {bloco!r}")
    return bloco


def _ids(linhas: list[dict]) -> set[int]:
    return {linha.get("event_id") for linha in linhas}


# ── Cenários ─────────────────────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    """Leitura do nome com as variações reais."""
    from app.contratos.contratos_ops import ler_nome

    casos = {
        "25102026 + (11) 98492-5407 + Hot Wheels Monster Trunck (1)": (
            date(2026, 10, 25),
            "5511984925407",
            "Hot Wheels Monster Trunck",
        ),
        "4122026 + (11) 98235-3711 + Natal.pdf": (date(2026, 12, 4), "5511982353711", "Natal"),
        "04-10-2025 + (11) 91234-5678 + Ursinhos": (date(2025, 10, 4), "5511912345678", "Ursinhos"),
        "07112026 + Clube Atlético São Paulo + (11) 94370-4338.pdf": (
            date(2026, 11, 7),
            "5511943704338",
            "Clube Atlético São Paulo",
        ),
        "31022026 + (11) 90000-0018 + Data impossível": (None, "5511900000018", "Data impossível"),
    }
    for nome, (dia, fone, tema) in casos.items():
        lido = ler_nome(nome)
        _garante((lido.data, lido.telefone, lido.tema) == (dia, fone, tema), f"{nome!r} → {lido}")
    lido = ler_nome("02-08-2025 + amanda@uol.com.br + Sereia")
    _garante(
        lido.email == "amanda@uol.com.br" and lido.telefone is None, f"e-mail no nome → {lido}"
    )


def cen_02() -> None:
    """Classificação cliente × artista × outro (artista com acento decomposto)."""
    _sincronizar(desde=_d(-30))
    _garante(_doc("art")[1] == "artista" and _doc("art")[4] == "fora", f"artista → {_doc('art')}")
    _garante(_doc("outro")[1] == "outro" and _doc("outro")[4] == "fora", f"outro → {_doc('outro')}")
    _garante(_doc("a")[1] == "cliente", f"cliente → {_doc('a')}")


def cen_03() -> None:
    """Vínculo único por data + telefone (cliente, contratante e formulário)."""
    ev = estado["ids"]
    for chave in ("a", "x", "y", "k", "f", "g", "m"):
        d = _doc(chave)
        _garante(
            d[4] == "ligado" and d[5] == "auto" and d[3] == ev[chave],
            f"{chave} não ligou sozinho: {d}",
        )
    # O contrato com e-mail NO NOME, no lugar do telefone (fluxo antigo), nunca liga sozinho.
    d = _doc("mail")
    _garante(d[4] == "a_conferir" and d[6] == "sem_telefone", f"e-mail no nome → {d}")


def cen_04() -> None:
    """Empate resolvido pelo tema; empate sem tema → a conferir."""
    _garante(
        _doc("e1")[4] == "ligado" and _doc("e1")[3] == estado["ids"]["e1"], f"e1 → {_doc('e1')}"
    )
    d = _doc("e2")
    _garante(d[4] == "a_conferir" and d[6] == "empate" and d[3] is None, f"e2 → {d}")


def cen_05() -> None:
    """Sem candidato e data ilegível → a conferir; nunca liga."""
    d = _doc("s")
    _garante(d[4] == "a_conferir" and d[6] == "sem_candidato" and d[3] is None, f"s → {d}")
    d = _doc("data_ruim")
    _garante(d[4] == "a_conferir" and d[6] == "data_ilegivel", f"data ruim → {d}")


def cen_06() -> None:
    """Venda cancelada não liga."""
    d = _doc("c")
    _garante(d[4] == "a_conferir" and d[6] == "cancelada" and d[3] is None, f"c → {d}")


def cen_07() -> None:
    """Grupo: contrato com a data do dia 2 liga no principal; situação igual nos dois dias."""
    d = _doc("b")
    _garante(d[4] == "ligado" and d[3] == estado["ids"]["b"], f"b → {d}")
    for dia in ("b", "b2"):
        sit = _contrato(estado["comercial"], dia)["contrato"]["situacao"]
        _garante(sit == "assinado", f"{dia} → {sit}")


def cen_08() -> None:
    """Vigente: reenvio assinado vence o original cancelado; remarcação em processo vence o antigo."""
    _garante(
        _contrato(estado["comercial"], "v")["contrato"]["situacao"] == "assinado",
        "v deveria estar assinado",
    )
    _garante(
        _contrato(estado["comercial"], "r")["contrato"]["situacao"] == "aguardando",
        "r deveria aguardar",
    )


def cen_09() -> None:
    """Situação no evento, nas listas da Home (grupos, cor, fronteira de data) e em /vendas."""
    ev = estado["ids"]
    c = _contrato(estado["comercial"], "a")["contrato"]
    _garante(c["situacao"] == "aguardando" and c["cor"] == "vermelho", f"a → {c}")
    _garante(c["documento"]["canal"] == "whatsapp", f"canal de a → {c['documento']}")
    p = _painel(estado["comercial"])
    _garante(
        {ev["a"], ev["k"], ev["r"]} <= _ids(p["para_cobrar"]),
        f"para_cobrar → {_ids(p['para_cobrar'])}",
    )
    _garante({ev["x"], ev["y"]} <= _ids(p["vencidos"]), f"vencidos → {_ids(p['vencidos'])}")
    _garante(
        ev["z"] in _ids(p["sem_contrato"]) and ev["zz"] not in _ids(p["sem_contrato"]),
        "sem_contrato errado",
    )
    _garante(ev["p"] in _ids(p["ja_aconteceu"]), "p deveria estar em ja_aconteceu")
    _garante(
        ev["b"] not in _ids(p["para_cobrar"]) | _ids(p["sem_contrato"]),
        "b assinado apareceu para cobrar",
    )
    _garante(
        ev["c"] not in _ids(p["para_cobrar"]) | _ids(p["vencidos"]) | _ids(p["sem_contrato"]),
        "cancelada nas listas",
    )
    linha_a = next(linha for linha in p["para_cobrar"] if linha["event_id"] == ev["a"])
    _garante(
        linha_a["severidade"] == "vermelho" and linha_a["documento_id"], f"linha a → {linha_a}"
    )
    conferir = {linha["documento_id"] for linha in p["a_conferir"]}
    _garante({_doc("e2")[0], _doc("s")[0], _doc("c")[0]} <= conferir, f"a_conferir → {conferir}")
    with app.app_context():
        from app.financeiro.vendas_ops import contract_status_map

        mapa = contract_status_map([ev["a"], ev["b"], ev["x"], ev["z"]])
    _garante(mapa[ev["b"]] == "assinado" and mapa[ev["a"]] == "aguardando", f"/vendas → {mapa}")
    _garante(mapa[ev["x"]] == "vencido" and mapa[ev["z"]] == "sem_contrato", f"/vendas → {mapa}")


def cen_10() -> None:
    """Mensagem pelo canal (WhatsApp × e-mail) e registro da cobrança."""
    corpo = _contrato(estado["comercial"], "a")
    _garante(
        corpo["mensagens"].get("contrato_canal") == "whatsapp",
        f"mensagens de a → {corpo['mensagens']}",
    )
    doc_a = corpo["contrato"]["documento"]["id"]
    r = _chamar(estado["comercial"], "post", f"/api/contratos/{doc_a}/cobranca")
    _garante(r.status_code == 201, f"cobrar a → {r.status_code} {r.get_data(as_text=True)[:200]}")
    linha = _no_banco(
        "SELECT usuario_nome, event_id FROM clicksign_cobrancas WHERE documento_id = :d", d=doc_a
    )
    _garante(linha is not None and linha[1] == estado["ids"]["a"], f"cobrança não gravada: {linha}")
    ultima = _contrato(estado["comercial"], "a")["contrato"]["ultima_cobranca"]
    _garante(ultima and ultima["por"], f"última cobrança → {ultima}")
    # O contrato por e-mail, depois de ligado à mão (cenário 18 liga outro): canal vem do signatário.
    _garante(_doc("m")[8] == "email", f"canal de m → {_doc('m')}")


def cen_11() -> None:
    """Botão desativado com o motivo certo."""
    casos = {
        "b": "Contrato já assinado",
        "b2": "A cobrança deste grupo está no evento principal",
        "x": "O contrato venceu sem assinatura. Gere um novo na ClickSign.",
        "z": "Nenhum contrato na ClickSign para esta venda",
    }
    for nome, motivo in casos.items():
        c = _contrato(estado["comercial"], nome)["contrato"]
        _garante(
            c["pode_cobrar"] is False and c["motivo_bloqueio"] == motivo,
            f"{nome} → {c['pode_cobrar']} {c['motivo_bloqueio']!r}",
        )
    r = _chamar(estado["comercial"], "post", f"/api/contratos/{_doc('b')[0]}/cobranca")
    _garante(r.status_code == 409, f"cobrar assinado → {r.status_code}")


def cen_12() -> None:
    """Assinado → PDF anexado ao principal, marcado, autor automático, sem duplicar; excluir não volta."""
    d = _doc("b")
    _garante(d[7] is not None and d[12] is False, f"b sem anexo: {d}")
    linha = _no_banco("SELECT event_id, is_signed FROM event_contracts WHERE id = :i", i=d[7])
    _garante(linha == (estado["ids"]["b"], True), f"anexo de b → {linha}")
    log = _no_banco(
        "SELECT count(*) FROM event_logs WHERE event_id = :e AND actor_name = 'ClickSign (automático)'",
        e=estado["ids"]["b"],
    )[0]
    _garante(log >= 1, "sem EventLog automático")
    baixados = conta.chamadas["baixar"]
    _sincronizar(desde=_d(-30))
    _garante(conta.chamadas["baixar"] == baixados, "baixou de novo")
    _garante(
        _no_banco("SELECT count(*) FROM event_contracts WHERE event_id = :e", e=estado["ids"]["b"])[
            0
        ]
        == 1,
        "duplicou",
    )
    with app.app_context():
        EventContract.query.filter_by(id=d[7]).delete()
        db.session.commit()
    _sincronizar(desde=_d(-30))
    _garante(
        _no_banco("SELECT count(*) FROM event_contracts WHERE event_id = :e", e=estado["ids"]["b"])[
            0
        ]
        == 0,
        "o PDF excluído voltou sozinho",
    )


def cen_13() -> None:
    """Aviso com HMAC errado ou ausente: 404 e nenhuma consulta (DEVE falhar)."""
    antes = conta.chamadas["listar"]
    _garante(
        _aviso({"event": {"name": "sign"}}, segredo="errado").status_code == 404,
        "HMAC errado aceito",
    )
    _garante(
        _aviso({"event": {"name": "sign"}}, segredo=None).status_code == 404, "sem HMAC aceito"
    )
    _garante(conta.chamadas["listar"] == antes, "aviso inválido disparou consulta")


def cen_14() -> None:
    """Aviso repetido: processado uma vez; a reconsulta decide."""
    conta.mudar(estado["env"]["k"], status="closed")
    for _ in range(2):
        r = _aviso({"event": {"name": "sign"}, "document": {"key": "qualquer"}})
        _garante(r.status_code == 200, f"aviso válido → {r.status_code}")
    _garante(
        _contrato(estado["comercial"], "k")["contrato"]["situacao"] == "assinado",
        "k não assinou pelo aviso",
    )
    n = _no_banco("SELECT count(*) FROM event_contracts WHERE event_id = :e", e=estado["ids"]["k"])[
        0
    ]
    _garante(n == 1, f"k com {n} anexos")


def cen_15() -> None:
    """Aviso diz "assinado", a ClickSign diz "em processo": nada muda (DEVE falhar se interpretar)."""
    r = _aviso(
        {
            "event": {"name": "auto_close"},
            "document": {"key": estado["env"]["a"], "status": "closed"},
        }
    )
    _garante(r.status_code == 200, f"aviso → {r.status_code}")
    sit = _contrato(estado["comercial"], "a")["contrato"]["situacao"]
    _garante(sit == "aguardando", f"o aviso decidiu sozinho: {sit}")


def cen_16() -> None:
    """FINANCEIRO vê mas não cobra nem liga (DEVE falhar com 403)."""
    fin = estado["financeiro"]
    c = _contrato(fin, "a")["contrato"]
    _garante(c["pode_cobrar"] is False and c["pode_conferir"] is False, f"financeiro → {c}")
    _garante(
        _chamar(fin, "post", f"/api/contratos/{_doc('a')[0]}/cobranca").status_code == 403,
        "financeiro cobrou",
    )
    r = _chamar(
        fin, "post", f"/api/contratos/{_doc('e2')[0]}/ligar", {"event_id": estado["ids"]["e2"]}
    )
    _garante(r.status_code == 403, f"financeiro ligou → {r.status_code}")
    _garante(_painel(fin)["pode_cobrar"] is False, "painel do financeiro com pode_cobrar")


def cen_17() -> None:
    """CASTING não vê o contrato (DEVE falhar com 403)."""
    r = _chamar(estado["casting"], "get", f"/api/events/{estado['ids']['a']}")
    _garante(
        r.status_code == 200 and "contrato" not in r.get_json(), "casting viu o bloco do contrato"
    )
    _garante(
        _chamar(estado["casting"], "get", "/api/contratos/a-conferir").status_code == 403,
        "casting leu a conferir",
    )


def cen_18() -> None:
    """Ligar à mão a partir de "A conferir"."""
    r = _chamar(
        estado["comercial"],
        "post",
        f"/api/contratos/{_doc('e2')[0]}/ligar",
        {"event_id": estado["ids"]["e2"]},
    )
    _garante(r.status_code == 200, f"ligar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    d = _doc("e2")
    _garante(d[4] == "ligado" and d[5] == "manual" and d[3] == estado["ids"]["e2"], f"e2 → {d}")
    # Ligar a venda cancelada é recusado (trava da 312, no núcleo).
    r = _chamar(
        estado["comercial"],
        "post",
        f"/api/contratos/{_doc('c')[0]}/ligar",
        {"event_id": estado["ids"]["c"]},
    )
    _garante(r.status_code == 409, f"ligar a cancelada → {r.status_code}")


def cen_19() -> None:
    """Desligar e não religar sozinho."""
    r = _chamar(estado["comercial"], "post", f"/api/contratos/{_doc('e1')[0]}/desligar")
    _garante(r.status_code == 200, f"desligar → {r.status_code}")
    _garante(_doc("e1")[4] == "a_conferir" and _doc("e1")[6] == "desligado", f"e1 → {_doc('e1')}")
    conta.mudar(
        estado["env"]["e1"], status="running", quando=datetime.combine(estado["hoje"], time(13, 0))
    )
    _sincronizar(desde=_d(-1))
    _garante(_doc("e1")[4] == "a_conferir", f"religou sozinho: {_doc('e1')}")


def cen_20() -> None:
    """Descartar: some para sempre."""
    r = _chamar(estado["comercial"], "post", f"/api/contratos/{_doc('s')[0]}/descartar")
    _garante(r.status_code == 200, f"descartar → {r.status_code}")
    _garante(_doc("s")[4] == "descartado", f"s → {_doc('s')}")
    conferir = {linha["documento_id"] for linha in _painel(estado["comercial"])["a_conferir"]}
    _garante(_doc("s")[0] not in conferir, "descartado continua a conferir")


def cen_21() -> None:
    """Comando retroativo: simulação não grava; --aplicar duas vezes = idempotente."""
    novo = conta.envelope(
        "retro",
        _nome_festa(_d(14), estado["fones"][19], "Retro"),
        criado=datetime.combine(_d(-20), time(10, 0)),
    )
    estado["env"]["retro"] = novo
    runner = app.test_cli_runner()
    r = runner.invoke(args=["clicksign-sincronizar", "--desde", _d(-60).isoformat()])
    _garante(r.exit_code == 0, f"dry-run → {r.exit_code} {r.output[-300:]}")
    _garante(_doc("retro") is None, "o dry-run gravou")
    for _ in range(2):
        r = runner.invoke(
            args=["clicksign-sincronizar", "--desde", _d(-60).isoformat(), "--aplicar"]
        )
        _garante(r.exit_code == 0, f"--aplicar → {r.exit_code} {r.output[-300:]}")
    n = _no_banco("SELECT count(*) FROM clicksign_documentos WHERE envelope_id = :e", e=novo)[0]
    _garante(n == 1, f"retro gravado {n} vezes")


def cen_22() -> None:
    """Conferência periódica acerta aviso perdido."""
    conta.mudar(estado["env"]["f"], status="closed")
    from app.contratos import sincronizar_ops

    with app.app_context():
        sincronizar_ops.sincronizar(motivo="periodica")
    _garante(
        _contrato(estado["comercial"], "f")["contrato"]["situacao"] == "assinado",
        "f não assinou na periódica",
    )


def cen_23() -> None:
    """Trava: com o cliente real, nada sai da máquina."""
    _restaurar_cliente_real()
    try:
        from app.integracoes.clicksign_client import ClicksignTravada

        with app.app_context():
            _garante(
                app.config["CLICKSIGN_SUPPRESS_CALLS"] is True,
                "CLICKSIGN_SUPPRESS_CALLS desligado no local",
            )
            from app.contratos import sincronizar_ops

            resultado = sincronizar_ops.sincronizar(motivo="periodica")
        _garante(resultado.get("travada") is True, f"sincronizar sem trava: {resultado}")
        try:
            _cliente_cs.listar_envelopes(
                base="https://app.clicksign.com/api/v3", token="x", travada=True
            )
            raise AssertionError("o cliente real não travou")
        except ClicksignTravada:
            pass
        _garante(not _ESCAPES, f"conexões de saída: {_ESCAPES}")
    finally:
        _instalar_duble()


def cen_24() -> None:
    """Sem credencial: integração desligada, telas respondem."""
    app.config["CLICKSIGN_ACCESS_TOKEN"] = ""
    try:
        c = _contrato(estado["comercial"], "a")["contrato"]
        _garante(c["integracao_ligada"] is False, f"integração ligada sem token: {c}")
        _garante(
            _painel(estado["comercial"])["integracao_ligada"] is False,
            "painel sem a marca de desligada",
        )
        with app.app_context():
            from app.contratos import sincronizar_ops

            _garante(
                sincronizar_ops.sincronizar().get("desligada") is True, "sincronizou sem token"
            )
    finally:
        app.config["CLICKSIGN_ACCESS_TOKEN"] = TOKEN_FALSO


def cen_25() -> None:
    """Agrupar não tira o contrato da venda; o sumiço do Google não apaga evento com contrato ligado."""
    ev = estado["ids"]
    with app.app_context():
        g = db.session.get(CalendarEvent, ev["g"])
        g.group_leader_id = ev["g0"]
        g.sale_value = None
        db.session.commit()
    sit = _contrato(estado["comercial"], "g0")["contrato"]["situacao"]
    _garante(sit == "aguardando", f"venda g0 depois de agrupar → {sit}")
    with app.app_context():
        g = db.session.get(CalendarEvent, ev["g"])
        g.group_leader_id = None
        db.session.commit()
        from app.calendar.sumico_ops import preso_ao_evento

        _garante(
            preso_ao_evento(db.session.get(CalendarEvent, ev["g"])).tem_contrato,
            "evento com contrato ligado não está preso",
        )


# ── Limpeza ──────────────────────────────────────────────────────────────────────────────────────


def _tabelas_filhas() -> list[tuple[str, str]]:
    linhas = db.session.execute(
        text(
            "SELECT DISTINCT tc.table_name, kcu.column_name "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema "
            "JOIN information_schema.constraint_column_usage ccu "
            "  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema "
            "WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'calendar_events' "
            "  AND tc.table_name <> 'calendar_events'"
        )
    ).fetchall()
    return [(tabela, coluna) for tabela, coluna in linhas]


def limpar() -> None:
    db.session.rollback()
    padrao = f"{PREFIX}%"
    # Os PDFs que a sincronização gravou no disco local.
    from app.storage import delete_file

    for (caminho,) in db.session.execute(
        text(
            "SELECT ec.file_path FROM event_contracts ec JOIN calendar_events ce ON ce.id = ec.event_id "
            "WHERE ce.google_event_id LIKE :p"
        ),
        {"p": padrao},
    ):
        delete_file(caminho)
    db.session.execute(
        text("DELETE FROM clicksign_documentos WHERE envelope_id LIKE :p"), {"p": padrao}
    )
    ids = [
        i
        for (i,) in db.session.execute(
            text("SELECT id FROM calendar_events WHERE google_event_id LIKE :p"), {"p": padrao}
        )
    ]
    if ids:
        db.session.execute(
            text(
                "UPDATE calendar_events SET group_leader_id = NULL, parent_event_id = NULL "
                "WHERE id = ANY(:ids)"
            ),
            {"ids": ids},
        )
        for tabela, coluna in _tabelas_filhas():
            db.session.execute(
                text(f"DELETE FROM {tabela} WHERE {coluna} = ANY(:ids)"), {"ids": ids}
            )
        db.session.execute(text("DELETE FROM calendar_events WHERE id = ANY(:ids)"), {"ids": ids})
    db.session.execute(text("DELETE FROM form_responses WHERE contact_name LIKE :p"), {"p": padrao})
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
    if estado.get("site_original"):
        s = SiteSetting.query.get(1)
        for coluna, valor in estado["site_original"].items():
            setattr(s, coluna, valor)
    db.session.commit()
    sobras = _no_banco(
        "SELECT count(*) FROM calendar_events WHERE google_event_id LIKE :p", p=padrao
    )[0]
    _garante(sobras == 0, f"sobraram {sobras} eventos de teste")


CENARIOS = [
    ("1. leitura do nome com as variações reais", cen_01),
    ("2. classificação cliente × artista × outro", cen_02),
    ("3. vínculo único por data + telefone", cen_03),
    ("4. empate: tema resolve; sem tema, a conferir", cen_04),
    ("5. sem candidato e data ilegível, a conferir", cen_05),
    ("6. venda cancelada não liga", cen_06),
    ("7. grupo: situação pelo principal", cen_07),
    ("8. documento vigente", cen_08),
    ("9. situação no evento, na Home e em /vendas", cen_09),
    ("10. mensagem pelo canal e registro da cobrança", cen_10),
    ("11. botão desativado com o motivo certo", cen_11),
    ("12. PDF assinado anexado, sem duplicar, sem voltar", cen_12),
    ("13. aviso com HMAC errado (DEVE falhar)", cen_13),
    ("14. aviso repetido: uma vez, a reconsulta decide", cen_14),
    ("15. aviso que mente não decide (DEVE falhar se interpretar)", cen_15),
    ("16. FINANCEIRO não cobra nem liga (DEVE falhar)", cen_16),
    ("17. CASTING não vê o contrato (DEVE falhar)", cen_17),
    ("18. ligar à mão", cen_18),
    ("19. desligar e não religar sozinho", cen_19),
    ("20. descartar", cen_20),
    ("21. comando retroativo idempotente", cen_21),
    ("22. conferência periódica", cen_22),
    ("23. trava: nada sai da máquina", cen_23),
    ("24. sem credencial: desligada", cen_24),
    ("25. agrupar e sumiço do Google", cen_25),
]


def main() -> int:
    so = None
    for arg in sys.argv[1:]:
        if arg.startswith("--so="):
            so = {int(n) for n in arg.split("=", 1)[1].split(",") if n.strip()}
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        limpar()  # sobra de uma rodada interrompida
        preparar()

    print("Feature 317 — contratos da ClickSign, contra manto_local")
    try:
        for indice, (nome, fn) in enumerate(CENARIOS, start=1):
            if so is None or indice in so:
                cenario(nome, fn)
    finally:
        with app.app_context():
            cenario("26. limpeza", limpar)

    ok = sum(1 for _, passou, _ in resultados if passou)
    print(
        f"\n{ok}/{len(resultados)} OK · escapes de rede: {len(_ESCAPES)} · listar: {conta.chamadas['listar']}"
    )
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
