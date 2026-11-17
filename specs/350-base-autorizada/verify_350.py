"""Verificação da feature 350 — a base autorizada.

Os 20 cenários da tabela da spec (seção "Verificação"). A Meta NUNCA é chamada: as funções de
`app.integracoes.whatsapp_client` viram um dublê em memória (`MetaFalsa`, molde do `verify_325`), e um
disjuntor de rede derruba qualquer conexão de saída que não seja o Postgres local — instalado ANTES de
importar o app.

Tudo de teste leva `v350-`: fichas (pelo telefone 55119873500NN), eventos (`google_event_id`),
parceiros, wamids, usuários. Escrita conferida por **conexão separada**; requisições HTTP **fora** de
`app.app_context()`; login só por `POST /api/auth/login`.

Banco: o espelho próprio `manto_350` (`.local-db-url` da worktree) — o `manto_local` é compartilhado
com as features 348, 349 e 351, que migram sobre a mesma head (plan.md, tabela de complexidade).

Rodar (PowerShell, na raiz da worktree)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
    $env:PYTHONUTF8 = '1'; .venv\\Scripts\\python.exe specs/350-base-autorizada/verify_350.py [--so=1,2] [--manter]

`--manter` deixa as fichas, os eventos e os usuários para conferir a tela; rode de novo sem a flag
para limpar.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
import traceback
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

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
        raise OSError(f"verify 350: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 350: conexão de saída bloqueada para {_host_de(endereco)}")
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
from app.constants import (  # noqa: E402
    CONSENTIMENTO_ANIVERSARIO_TEXTO,
    CONSENTIMENTO_NOVIDADES_TEXTO,
    CONSENTIMENTO_NOVIDADES_VERSAO,
    CONSENTIMENTO_ORIGEM_ERRO_WHATSAPP,
    CONSENTIMENTO_ORIGEM_PEDIU_PARA_PARAR,
    CONSENTIMENTO_ORIGEM_POS_EVENTO,
    VIRTUAL_ACEITE_TEXTO,
    RoleName,
    now_sp,
)
from app.models import CalendarEvent, Client, Role, User  # noqa: E402

PREFIX = "v350-"
SENHA = "verify-350-senha"
SEGREDO = "segredo-do-app-v350"
NUMERO_ID = "v350-phone"
NUMERO_MANTO = "5511900000350"
# Fichas: o telefone é a identidade (e é por ele que a conversa se liga sozinha à ficha).
TEL = {
    "ana": "5511987350001",
    "bia": "5511987350002",
    "cris": "5511987350003",
    "loja": "5511987350004",
    "dani": "5511987350005",
}
NOMES = {
    "ana": "Ana v350-Teste",
    "bia": "Bia v350-Teste",
    "cris": "Cris v350-Teste",
    "loja": "Lu v350-Loja",
    "dani": "Dani v350-Exclui",
}
FOTOS = "https://fotos.exemplo.com/v350-album"
MANTER = "--manter" in sys.argv

app = create_app()
TRAVA_DE_FABRICA = app.config.get("WHATSAPP_SUPPRESS_SEND")
app.config["TESTING"] = True
app.config["WHATSAPP_ACCESS_TOKEN"] = "token-falso-v350"
app.config["WHATSAPP_APP_SECRET"] = SEGREDO
app.config["WHATSAPP_VERIFY_TOKEN"] = "verifica-v350"
app.config["WHATSAPP_PHONE_NUMBER_ID"] = NUMERO_ID
app.config["WHATSAPP_WABA_ID"] = "v350-waba"
app.config["WHATSAPP_AVISO_SINCRONO"] = True
app.config["WHATSAPP_SUPPRESS_SEND"] = False  # o dublê no lugar da Meta (e o disjuntor atrás)
limiter.enabled = False

# ── O dublê da Meta ──────────────────────────────────────────────────────────────────────────────
import app.integracoes.whatsapp_client as _wc  # noqa: E402

_REAIS = {nome: getattr(_wc, nome) for nome in ("enviar", "marcar_lida", "listar_modelos")}


class MetaFalsa:
    """Responde como a Meta, registra cada chamada e nunca sai da máquina."""

    def __init__(self) -> None:
        self.chamadas: dict[str, list] = {nome: [] for nome in _REAIS}
        self.seq = 0
        self.recusar_com: int | None = None  # próximo envio recusado com este código

    def enviar(self, conexao, corpo):
        if conexao.travada:
            raise _wc.WhatsappTravado("travado (dublê)")
        if self.recusar_com is not None:
            codigo, self.recusar_com = self.recusar_com, None
            raise _wc.WhatsappRecusou("recusado (dublê)", status=400, code=codigo)
        self.chamadas["enviar"].append(corpo)
        self.seq += 1
        return {"id": f"wamid.{PREFIX}env-{self.seq}", "wa_id": corpo.get("to")}

    def marcar_lida(self, conexao, wamid):
        self.chamadas["marcar_lida"].append(wamid)

    def listar_modelos(self, conexao):
        self.chamadas["listar_modelos"].append(True)
        return [
            {
                "name": "v350_promo",
                "language": "pt_BR",
                "status": "APPROVED",
                "category": "MARKETING",
                "components": [{"type": "BODY", "text": "Oi, {{1}}! Novidade da Manto."}],
            },
            {
                "name": "v350_aviso",
                "language": "pt_BR",
                "status": "APPROVED",
                "category": "UTILITY",
                "components": [{"type": "BODY", "text": "Oi, {{1}}! Sua festa está confirmada."}],
            },
        ]


meta = MetaFalsa()
for _nome in _REAIS:
    setattr(_wc, _nome, getattr(meta, _nome))

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _um(sql: str, **params):
    """Lê por fora da sessão do app (o autoflush esconderia falta de commit)."""
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchone()


def _todas(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _escrever(sql: str, **params) -> None:
    with _externo.begin() as conn:
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
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
            db.session.add(user)
        user.set_password(SENHA)
        user.roles.clear()
        user.roles.append(Role.query.filter_by(name=papel).one())
        db.session.commit()
        estado[f"uid_{sufixo}"] = user.id
    return email


def _chamar(quem: str, metodo: str, url: str, corpo: dict | None = None):
    """Uma requisição autenticada, fora de qualquer contexto de aplicação."""
    with app.test_client() as c:
        if quem != "anon":
            r = c.post("/api/auth/login", json={"email": estado[quem], "password": SENHA})
            _garante(r.status_code == 200, f"login {quem} → {r.status_code}")
        kwargs = {"json": corpo} if corpo is not None else {}
        return getattr(c, metodo)(url, **kwargs)


def _erro(r) -> dict:
    return (r.get_json(silent=True) or {}).get("error") or {}


def _espera(r, status: int, contexto: str) -> dict:
    _garante(
        r.status_code == status,
        f"{contexto}: esperava {status}, veio {r.status_code} {r.get_data(as_text=True)[:300]}",
    )
    return r.get_json(silent=True) or {}


def _ficha(chave: str):
    return _um(
        "SELECT id, marketing_opt_in_at, marketing_opt_in_source, marketing_opt_in_version, "
        "marketing_opt_out_at, marketing_opt_out_source, indicado_por_id, parceiro_id "
        "FROM clients WHERE id=:i",
        i=estado[f"cli_{chave}"],
    )


def _historico(chave: str):
    return _todas(
        "SELECT tipo, acao, texto, versao, origem, referencia, registrado_por_id "
        "FROM cliente_consentimentos WHERE client_id=:i ORDER BY id",
        i=estado[f"cli_{chave}"],
    )


def _url_cli(chave: str, resto: str = "") -> str:
    return f"/api/clientes/{estado[f'cli_{chave}']}{resto}"


def _aceitar(chave: str, origem: str = "Conversa") -> None:
    r = _chamar("com", "post", _url_cli(chave, "/consentimentos/novidades"), {"origem": origem})
    _espera(r, 200, f"aceite de {chave}")


# ── Avisos do WhatsApp (molde do verify_325) ─────────────────────────────────────────────────────


def _post_aviso(corpo: dict):
    import hashlib
    import hmac

    bruto = json.dumps(corpo).encode()
    assinatura = "sha256=" + hmac.new(SEGREDO.encode(), bruto, hashlib.sha256).hexdigest()
    with app.test_client() as c:
        return c.post(
            "/api/webhooks/whatsapp",
            data=bruto,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": assinatura},
        )


def _valor(contatos: list[dict], **campos) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "v350-waba",
                "changes": [
                    {
                        "field": "messages",
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


def _recebida(chave: str, corpo_texto: str) -> str:
    estado["seq_wamid"] = estado.get("seq_wamid", 0) + 1
    wamid = f"wamid.{PREFIX}in-{estado['seq_wamid']}"
    wa_id = TEL[chave]
    aviso = _valor(
        [{"profile": {"name": NOMES[chave]}, "wa_id": wa_id}],
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
    _espera(_post_aviso(aviso), 200, f"aviso '{corpo_texto}'")
    return wamid


def _status_falhou(wamid: str, wa_id: str, codigo: int) -> None:
    item = {
        "id": wamid,
        "status": "failed",
        "timestamp": str(int(time.time())),
        "recipient_id": wa_id,
        "errors": [{"code": codigo, "title": "x", "message": "x", "error_data": {"details": "x"}}],
    }
    _espera(_post_aviso(_valor([], statuses=[item])), 200, "aviso de status")


def _conversa_de(chave: str) -> int:
    linha = _um(
        "SELECT id, client_id FROM conversas WHERE canal='whatsapp' AND contato_id=:c",
        c=TEL[chave],
    )
    _garante(linha is not None, f"conversa de {chave} não existe")
    _garante(linha.client_id == estado[f"cli_{chave}"], "a conversa não se ligou à ficha")
    return linha.id


# ── Preparação ───────────────────────────────────────────────────────────────────────────────────


def _evento(sufixo: str, inicio, cliente: str | None, **extra) -> int:
    with app.app_context():
        evento = CalendarEvent(
            google_event_id=f"{PREFIX}evt-{sufixo}",
            title=f"{PREFIX}Festa {sufixo}",
            start_at=inicio,
            end_at=inicio + timedelta(hours=3),
            source="platform",
            client_id=estado[f"cli_{cliente}"] if cliente else None,
            **extra,
        )
        db.session.add(evento)
        db.session.commit()
        return evento.id


def preparar() -> None:
    limpar()
    estado["com"] = _usuario("comercial", RoleName.COMERCIAL)
    estado["fin"] = _usuario("financeiro", RoleName.FINANCEIRO)
    estado["cas"] = _usuario("casting", RoleName.CASTING)
    with app.app_context():
        for chave, telefone in TEL.items():
            cliente = Client(name=NOMES[chave], phone=telefone, phone_display=telefone)
            db.session.add(cliente)
            db.session.flush()
            estado[f"cli_{chave}"] = cliente.id
        db.session.commit()
    ontem = now_sp().replace(hour=15, minute=0, second=0, microsecond=0) - timedelta(days=1)
    estado["evt"] = _evento("ontem", ontem, "ana")
    estado["evt_sem_cliente"] = _evento("sem-cliente", ontem, None)
    estado["evt_cancelado"] = _evento("cancelado", ontem, "bia", cancelled_at=now_sp())
    estado["evt_satelite"] = _evento("satelite", ontem, "ana", group_leader_id=estado["evt"])
    estado["evt_velho"] = _evento("velho", ontem - timedelta(days=20), "ana")


def limpar() -> None:
    """Apaga tudo o que leva `v350-` (o histórico, as crianças e o pós-evento vão em cascata)."""
    with app.app_context():
        db.session.rollback()
    telefones = tuple(TEL.values())
    _escrever(
        "DELETE FROM client_feedbacks WHERE event_id IN "
        "(SELECT id FROM calendar_events WHERE google_event_id LIKE :p)",
        p=f"{PREFIX}%",
    )
    _escrever(
        "DELETE FROM event_clients WHERE event_id IN "
        "(SELECT id FROM calendar_events WHERE google_event_id LIKE :p)",
        p=f"{PREFIX}%",
    )
    _escrever(
        "UPDATE calendar_events SET group_leader_id=NULL WHERE google_event_id LIKE :p",
        p=f"{PREFIX}%",
    )
    _escrever("DELETE FROM calendar_events WHERE google_event_id LIKE :p", p=f"{PREFIX}%")
    _escrever(
        "DELETE FROM conversa_mensagens WHERE conversa_id IN "
        "(SELECT id FROM conversas WHERE contato_id IN :t)".replace(":t", str(telefones)),
    )
    _escrever(
        "DELETE FROM conversas WHERE contato_id IN :t".replace(":t", str(telefones)),
    )
    _escrever("DELETE FROM whatsapp_avisos WHERE corpo LIKE :p", p=f"%{NUMERO_ID}%")
    _escrever(
        "UPDATE clients SET indicado_por_id=NULL, parceiro_id=NULL WHERE phone IN " + str(telefones)
    )
    _escrever("DELETE FROM clients WHERE phone IN " + str(telefones))
    _escrever("DELETE FROM parceiros WHERE nome LIKE :p", p=f"{PREFIX}%")
    with app.app_context():
        for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
            user.roles.clear()
            db.session.flush()
            db.session.execute(text("DELETE FROM notifications WHERE user_id=:u"), {"u": user.id})
            db.session.delete(user)
        db.session.commit()


# ── Cenários ─────────────────────────────────────────────────────────────────────────────────────


def cen_01_esquema() -> None:
    versao = _um("SELECT version_num FROM alembic_version")
    # No lote de 17/11 a 351 encadeia depois da 350: a head pode ser a dela.
    _garante(versao.version_num in {"a350b1c2d3e4", "a351b0c1d2e3"}, f"head = {versao.version_num}")
    for tabela in ("parceiros", "cliente_consentimentos", "cliente_criancas", "pos_eventos"):
        _garante(_um("SELECT to_regclass(:t) AS r", t=tabela).r is not None, f"{tabela} não existe")
    colunas = {
        linha.column_name
        for linha in _todas(
            "SELECT column_name FROM information_schema.columns WHERE table_name='clients'"
        )
    }
    for coluna in (
        "marketing_opt_in_version",
        "marketing_opt_out_at",
        "marketing_opt_out_source",
        "indicado_por_id",
        "parceiro_id",
    ):
        _garante(coluna in colunas, f"clients.{coluna} não existe")


def cen_02_aceite_pela_ficha() -> None:
    r = _chamar("com", "post", _url_cli("ana", "/consentimentos/novidades"), {"origem": "Qualquer"})
    _garante("origem" in (_erro(r).get("fields") or {}), f"origem fora da lista: {r.status_code}")
    corpo = _espera(
        _chamar(
            "com",
            "post",
            _url_cli("ana", "/consentimentos/novidades"),
            {"origem": "Resposta ao orçamento"},
        ),
        200,
        "aceite",
    )
    _garante(corpo.get("pode_prospectar") is True, "pode_prospectar não virou true")
    ficha = _ficha("ana")
    _garante(ficha.marketing_opt_in_at is not None, "aceite não gravado (conexão separada)")
    _garante(ficha.marketing_opt_in_source == "Resposta ao orçamento", "origem errada")
    _garante(ficha.marketing_opt_in_version == CONSENTIMENTO_NOVIDADES_VERSAO, "versão errada")
    linhas = _historico("ana")
    _garante(len(linhas) == 1, f"histórico com {len(linhas)} linhas")
    linha = linhas[0]
    _garante((linha.tipo, linha.acao) == ("novidades", "aceite"), "tipo/ação errados")
    _garante(linha.texto == CONSENTIMENTO_NOVIDADES_TEXTO, "o texto completo não foi gravado")
    _garante(linha.registrado_por_id == estado["uid_comercial"], "autor não gravado")
    _espera(
        _chamar(
            "com", "post", _url_cli("ana", "/consentimentos/novidades"), {"origem": "Telefone"}
        ),
        200,
        "aceite repetido",
    )
    _garante(len(_historico("ana")) == 1, "aceite repetido duplicou o histórico")


def cen_03_retirada_pela_ficha() -> None:
    _espera(
        _chamar(
            "com", "delete", _url_cli("ana", "/consentimentos/novidades"), {"origem": "Telefone"}
        ),
        200,
        "retirada",
    )
    ficha = _ficha("ana")
    _garante(ficha.marketing_opt_in_at is None, "aceite continua na ficha")
    _garante(ficha.marketing_opt_out_at is not None, "retirada sem data")
    _garante(ficha.marketing_opt_out_source == "Telefone", "origem da retirada errada")
    linhas = _historico("ana")
    _garante([(x.acao) for x in linhas] == ["aceite", "retirada"], f"histórico: {linhas}")
    _garante(linhas[1].texto == CONSENTIMENTO_NOVIDADES_TEXTO, "retirada sem o texto do aceite")
    _espera(
        _chamar(
            "com", "delete", _url_cli("ana", "/consentimentos/novidades"), {"origem": "Telefone"}
        ),
        200,
        "retirada repetida",
    )
    _garante(len(_historico("ana")) == 2, "retirada repetida duplicou o histórico")


def cen_04_rbac() -> None:
    r = _chamar("cas", "post", _url_cli("bia", "/consentimentos/novidades"), {"origem": "Conversa"})
    _garante(r.status_code == 403, f"Casting registrou aceite: {r.status_code}")
    r = _chamar("fin", "post", _url_cli("bia", "/consentimentos/novidades"), {"origem": "Conversa"})
    _garante(r.status_code == 403, f"Financeiro registrou aceite: {r.status_code}")
    r = _chamar("fin", "get", "/api/clientes/aniversarios")
    _garante(r.status_code == 403, f"Financeiro viu aniversários: {r.status_code}")
    r = _chamar("cas", "get", "/api/pos-evento")
    _garante(r.status_code == 403, f"Casting viu o pós-evento: {r.status_code}")
    corpo = _espera(_chamar("fin", "get", _url_cli("bia")), 200, "detalhe do Financeiro")
    _garante("consentimentos" in corpo, "Financeiro sem o bloco de consentimentos")
    _garante("criancas" not in corpo["consentimentos"], "Financeiro recebeu as crianças")
    _garante((corpo.get("flags") or {}).get("pode_editar_base") is False, "flag errada (Fin)")
    corpo = _espera(_chamar("com", "get", _url_cli("bia")), 200, "detalhe do Comercial")
    _garante("criancas" in corpo["consentimentos"], "Comercial sem as crianças")
    _garante(_ficha("bia").marketing_opt_in_at is None, "o 403 gravou mesmo assim")


def _daqui(dias: int, anos_atras: int) -> str:
    alvo = now_sp().date() + timedelta(days=dias)
    return alvo.replace(year=alvo.year - anos_atras).isoformat()


def cen_05_crianca() -> None:
    url = _url_cli("ana", "/criancas")
    base = {"primeiro_nome": "Lia", "nascimento": _daqui(10, 5), "origem": "Conversa"}
    r = _chamar("com", "post", url, {**base, "aceite": False})
    _garante("aceite" in (_erro(r).get("fields") or {}), f"sem aceite passou: {r.status_code}")
    futuro = (now_sp().date() + timedelta(days=3)).isoformat()
    r = _chamar("com", "post", url, {**base, "nascimento": futuro, "aceite": True})
    _garante("nascimento" in (_erro(r).get("fields") or {}), "data futura passou")
    r = _chamar("com", "post", url, {**base, "nascimento": _daqui(0, 25), "aceite": True})
    _garante("nascimento" in (_erro(r).get("fields") or {}), "adulto passou")
    _garante(
        _um("SELECT count(*) AS n FROM cliente_criancas WHERE client_id=:i", i=estado["cli_ana"]).n
        == 0,
        "recusa gravou criança",
    )
    corpo = _espera(_chamar("com", "post", url, {**base, "aceite": True}), 201, "criança")
    criancas = corpo["consentimentos"]["criancas"]
    _garante([c["primeiro_nome"] for c in criancas] == ["Lia"], f"crianças: {criancas}")
    # Uma segunda, para remover (a Lia fica para o cenário 16).
    corpo = _espera(
        _chamar("com", "post", url, {**base, "primeiro_nome": "Zeca", "aceite": True}),
        201,
        "segunda criança",
    )
    zeca = next(
        c["id"] for c in corpo["consentimentos"]["criancas"] if c["primeiro_nome"] == "Zeca"
    )
    r = _chamar("com", "delete", _url_cli("bia", f"/criancas/{zeca}"))
    _garante(r.status_code == 404, f"removeu criança de outra ficha: {r.status_code}")
    _espera(_chamar("com", "delete", _url_cli("ana", f"/criancas/{zeca}")), 200, "remover")
    _garante(
        _um("SELECT count(*) AS n FROM cliente_criancas WHERE id=:i", i=zeca).n == 0,
        "a criança não foi apagada",
    )
    linhas = [x for x in _historico("ana") if x.tipo == "aniversario"]
    _garante([x.acao for x in linhas] == ["aceite", "aceite", "retirada"], f"histórico: {linhas}")
    _garante(linhas[0].texto == CONSENTIMENTO_ANIVERSARIO_TEXTO, "texto do aniversário errado")
    _garante(
        all("Zeca" not in (x.texto + (x.referencia or "") + x.origem) for x in linhas),
        "o histórico guardou o nome da criança",
    )


def cen_06_aceite_pela_conversa() -> None:
    _recebida("ana", "Oi! Quero receber as novidades")
    conversa = _conversa_de("ana")
    estado["conv_ana"] = conversa
    _espera(
        _chamar(
            "com",
            "post",
            _url_cli("ana", "/consentimentos/novidades"),
            {"origem": "Conversa", "referencia": f"conversa:{conversa}"},
        ),
        200,
        "aceite",
    )
    ultima = _historico("ana")[-1]
    _garante(ultima.origem == "Conversa", "origem errada")
    _garante(ultima.referencia == f"conversa:{conversa}", f"referência: {ultima.referencia}")
    corpo = _espera(_chamar("com", "get", f"/api/conversas/{conversa}"), 200, "conversa")
    _garante(
        corpo["conversa"]["cliente"].get("aceite_novidades") is True,
        "o cabeçalho da conversa não mostra o aceite",
    )


def cen_07_saida_por_palavra() -> None:
    _garante(_ficha("ana").marketing_opt_in_at is not None, "pré-condição: Ana com aceite")
    _recebida("ana", "Vou sair às 15h, te chamo depois")
    _garante(_ficha("ana").marketing_opt_in_at is not None, "'vou sair às 15h' tirou o aceite")
    wamid = _recebida("ana", "  Sair! 🙏 ")
    ficha = _ficha("ana")
    _garante(ficha.marketing_opt_in_at is None, "'Sair!' não tirou o aceite")
    _garante(ficha.marketing_opt_out_source == CONSENTIMENTO_ORIGEM_PEDIU_PARA_PARAR, "origem")
    mensagem = _um("SELECT id FROM conversa_mensagens WHERE externo_id=:w", w=wamid)
    ultima = _historico("ana")[-1]
    _garante(ultima.referencia == f"mensagem:{mensagem.id}", f"referência: {ultima.referencia}")
    _garante(ultima.registrado_por_id is None, "saída automática com autor")


def cen_08_saida_por_131050() -> None:
    conversa = estado["conv_ana"]
    _aceitar("ana")
    corpo = _espera(
        _chamar(
            "com",
            "post",
            f"/api/conversas/{conversa}/mensagens",
            {"texto": "Oi, Ana!", "chave_envio": f"{PREFIX}txt-1"},
        ),
        201,
        "envio",
    )
    wamid = _um(
        "SELECT externo_id FROM conversa_mensagens WHERE id=:i", i=corpo["mensagem"]["id"]
    ).externo_id
    _status_falhou(wamid, TEL["ana"], 131050)
    ficha = _ficha("ana")
    _garante(ficha.marketing_opt_in_at is None, "o 131050 do status não tirou o aceite")
    _garante(ficha.marketing_opt_out_source == CONSENTIMENTO_ORIGEM_ERRO_WHATSAPP, "origem")
    # A recusa síncrona (a Meta responde 400 com o código já no envio).
    _aceitar("ana")
    meta.recusar_com = 131050
    _chamar(
        "com",
        "post",
        f"/api/conversas/{conversa}/mensagens",
        {"texto": "Oi de novo", "chave_envio": f"{PREFIX}txt-2"},
    )
    ficha = _ficha("ana")
    _garante(ficha.marketing_opt_in_at is None, "o 131050 síncrono não tirou o aceite")
    _garante(ficha.marketing_opt_out_source == CONSENTIMENTO_ORIGEM_ERRO_WHATSAPP, "origem sync")
    meta.recusar_com = None


def cen_09_modelo_de_marketing() -> None:
    conversa = estado["conv_ana"]
    _garante(_ficha("ana").marketing_opt_in_at is None, "pré-condição: Ana sem aceite")
    antes = len(meta.chamadas["enviar"])
    r = _chamar(
        "com",
        "post",
        f"/api/conversas/{conversa}/modelo",
        {
            "nome": "v350_promo",
            "idioma": "pt_BR",
            "variaveis": ["Ana"],
            "chave_envio": f"{PREFIX}mod-1",
        },
    )
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "sem_aceite",
        f"marketing sem aceite: {r.status_code} {_erro(r)}",
    )
    _garante(len(meta.chamadas["enviar"]) == antes, "a Meta foi chamada")
    _garante(
        _um(
            "SELECT count(*) AS n FROM conversa_mensagens WHERE chave_envio=:c", c=f"{PREFIX}mod-1"
        ).n
        == 0,
        "a recusa gravou mensagem",
    )
    _espera(
        _chamar(
            "com",
            "post",
            f"/api/conversas/{conversa}/modelo",
            {
                "nome": "v350_aviso",
                "idioma": "pt_BR",
                "variaveis": ["Ana"],
                "chave_envio": f"{PREFIX}mod-2",
            },
        ),
        201,
        "modelo de utilidade",
    )
    _aceitar("ana")
    _espera(
        _chamar(
            "com",
            "post",
            f"/api/conversas/{conversa}/modelo",
            {
                "nome": "v350_promo",
                "idioma": "pt_BR",
                "variaveis": ["Ana"],
                "chave_envio": f"{PREFIX}mod-3",
            },
        ),
        201,
        "marketing com aceite",
    )


def _url_pos(evento: str, resto: str = "") -> str:
    return f"/api/events/{estado[evento]}/pos-evento{resto}"


def cen_10_pos_evento_mensagem() -> None:
    corpo = _espera(_chamar("com", "get", _url_pos("evt")), 200, "pós-evento")
    mensagem = corpo["mensagem"]
    _garante(mensagem.startswith("Oi, Ana!"), f"saudação: {mensagem[:40]}")
    _garante(corpo["link_avaliacao"] in mensagem, "sem o link de avaliação")
    _garante("/catalogo/avaliar/" in corpo["link_avaliacao"], "link de avaliação errado")
    _garante("SAIR" in mensagem, "sem a instrução de saída")
    _garante(FOTOS not in mensagem, "fotos sem link informado")
    corpo = _espera(_chamar("com", "get", _url_pos("evt", f"?fotos_url={FOTOS}")), 200, "com fotos")
    _garante(FOTOS in corpo["mensagem"], "o link das fotos não entrou")
    r = _chamar("com", "get", _url_pos("evt_cancelado"))
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "cancelado",
        f"cancelado: {r.status_code}",
    )
    r = _chamar("com", "post", _url_pos("evt"), {"canal": "copiado", "fotos_url": "ftp://x"})
    _garante("fotos_url" in (_erro(r).get("fields") or {}), "link de fotos inválido passou")
    corpo = _espera(_chamar("com", "get", _url_pos("evt_sem_cliente")), 200, "sem contratante")
    _garante(corpo["mensagem"].startswith("Oi!"), "sem contratante deveria ser 'Oi!'")


def _item_da_lista(evento: str) -> dict | None:
    corpo = _espera(_chamar("com", "get", "/api/pos-evento"), 200, "lista")
    return next((i for i in corpo["items"] if i["event_id"] == estado[evento]), None)


def cen_11_copiar_e_lista() -> None:
    _garante((_item_da_lista("evt") or {}).get("situacao") == "pendente", "evento não pendente")
    for _ in range(2):
        _espera(
            _chamar("com", "post", _url_pos("evt"), {"canal": "copiado", "fotos_url": FOTOS}),
            200,
            "copiar",
        )
    linhas = _todas("SELECT canal, fotos_url FROM pos_eventos WHERE event_id=:e", e=estado["evt"])
    _garante(len(linhas) == 1, f"{len(linhas)} registros de pós-evento")
    _garante(linhas[0].canal == "copiado" and linhas[0].fotos_url == FOTOS, "registro errado")
    item = _item_da_lista("evt")
    _garante(item["situacao"] == "copiado", f"situação: {item['situacao']}")
    _garante(item["avaliacao_recebida"] is False, "avaliação recebida antes de existir")
    for evento in ("evt_cancelado", "evt_satelite", "evt_velho"):
        _garante(_item_da_lista(evento) is None, f"{evento} apareceu na lista")
    _escrever(
        "INSERT INTO client_feedbacks (event_id, score, tags, comment, client_name, submitted_at) "
        "VALUES (:e, 5, '[]', '', 'v350', now())",
        e=estado["evt"],
    )
    _garante(_item_da_lista("evt")["avaliacao_recebida"] is True, "avaliação não apareceu")


def cen_12_pos_evento_conversa() -> None:
    token = app.config["WHATSAPP_ACCESS_TOKEN"]
    app.config["WHATSAPP_ACCESS_TOKEN"] = ""
    try:
        r = _chamar("com", "post", _url_pos("evt"), {"canal": "conversa"})
        _garante(r.status_code == 503, f"CRM desligado: {r.status_code}")
        corpo = _espera(_chamar("com", "get", _url_pos("evt")), 200, "prévia desligado")
        _garante(corpo["conversa"]["pode_enviar"] is False, "pode_enviar com o CRM desligado")
    finally:
        app.config["WHATSAPP_ACCESS_TOKEN"] = token
    _garante(
        _um("SELECT canal FROM pos_eventos WHERE event_id=:e", e=estado["evt"]).canal == "copiado",
        "a recusa mexeu no registro",
    )
    _recebida("ana", "Obrigada pela festa!")  # janela aberta
    corpo = _espera(_chamar("com", "get", _url_pos("evt")), 200, "prévia ligada")
    _garante(corpo["conversa"]["pode_enviar"] is True, f"conversa: {corpo['conversa']}")
    antes = len(meta.chamadas["enviar"])
    _espera(
        _chamar("com", "post", _url_pos("evt"), {"canal": "conversa", "fotos_url": FOTOS}),
        200,
        "enviar",
    )
    _garante(len(meta.chamadas["enviar"]) == antes + 1, "a Meta (dublê) não foi chamada")
    enviado = meta.chamadas["enviar"][-1]
    _garante("/catalogo/avaliar/" in json.dumps(enviado, ensure_ascii=False), "texto sem o link")
    linha = _um("SELECT canal, mensagem_id FROM pos_eventos WHERE event_id=:e", e=estado["evt"])
    _garante(linha.canal == "conversa" and linha.mensagem_id, f"registro: {linha}")
    _espera(_chamar("com", "post", _url_pos("evt"), {"canal": "conversa"}), 200, "reenviar")
    _garante(len(meta.chamadas["enviar"]) == antes + 1, "o segundo clique mandou de novo")
    _espera(_chamar("com", "post", _url_pos("evt"), {"canal": "copiado"}), 200, "copiar depois")
    _garante(
        _um("SELECT canal FROM pos_eventos WHERE event_id=:e", e=estado["evt"]).canal == "conversa",
        "a cópia rebaixou o canal",
    )


def _token(evento: str) -> str:
    with app.app_context():
        from app.calendar.event_ops import ensure_feedback_token

        return ensure_feedback_token(db.session.get(CalendarEvent, estado[evento]))


def cen_13_pagina_publica() -> None:
    _espera(
        _chamar(
            "com", "delete", _url_cli("ana", "/consentimentos/novidades"), {"origem": "Telefone"}
        ),
        200,
        "zera Ana",
    )
    token = _token("evt")
    corpo = _espera(_chamar("anon", "get", f"/api/avaliar/{token}"), 200, "GET público")
    bloco = corpo.get("consentimento") or {}
    _garante(bloco.get("primeiro_nome") == "Ana", f"bloco: {bloco}")
    _garante(bloco.get("recebe_novidades") is False, "recebe_novidades errado")
    versao = bloco["textos"]["novidades"]["versao"]
    url = f"/api/avaliar/{token}/consentimento"
    r = _chamar("anon", "post", url, {"novidades": "aceitar", "versao_novidades": "1999-01-01"})
    _garante(r.status_code == 409 and _erro(r).get("codigo") == "texto_mudou", f"{r.status_code}")
    corpo = _espera(
        _chamar("anon", "post", url, {"novidades": "aceitar", "versao_novidades": versao}),
        200,
        "aceitar",
    )
    _garante(corpo.get("recebe_novidades") is True, "não aceitou")
    ultima = _historico("ana")[-1]
    _garante(ultima.origem == CONSENTIMENTO_ORIGEM_POS_EVENTO, f"origem: {ultima.origem}")
    _garante(ultima.referencia == f"evento:{estado['evt']}", "referência do evento")
    _garante(ultima.registrado_por_id is None, "autor numa ação da própria cliente")
    crianca = {"primeiro_nome": "Theo", "nascimento": _daqui(30, 3), "aceite": False}
    r = _chamar("anon", "post", url, {"crianca": crianca, "versao_aniversario": "2026-11-17"})
    _garante("crianca.aceite" in (_erro(r).get("fields") or {}), f"sem caixa: {r.status_code}")
    _espera(
        _chamar(
            "anon",
            "post",
            url,
            {"crianca": {**crianca, "aceite": True}, "versao_aniversario": "2026-11-17"},
        ),
        200,
        "criança",
    )
    _garante(
        _um(
            "SELECT aceite_origem FROM cliente_criancas WHERE client_id=:i AND "
            "primeiro_nome='Theo'",
            i=estado["cli_ana"],
        ).aceite_origem
        == CONSENTIMENTO_ORIGEM_POS_EVENTO,
        "criança da página sem origem certa",
    )
    corpo = _espera(_chamar("anon", "post", url, {"novidades": "retirar"}), 200, "retirar")
    _garante(corpo.get("recebe_novidades") is False, "não retirou")
    _garante(_ficha("ana").marketing_opt_out_source == CONSENTIMENTO_ORIGEM_POS_EVENTO, "origem")
    sem = _token("evt_sem_cliente")
    corpo = _espera(_chamar("anon", "get", f"/api/avaliar/{sem}"), 200, "sem contratante")
    _garante("consentimento" not in corpo, "bloco num evento sem contratante")
    r = _chamar(
        "anon",
        "post",
        f"/api/avaliar/{sem}/consentimento",
        {"novidades": "aceitar", "versao_novidades": versao},
    )
    _garante(r.status_code == 409 and _erro(r).get("codigo") == "sem_ficha", f"{r.status_code}")


def cen_14_indicacao() -> None:
    url = _url_cli("bia", "/indicacao")
    corpo = _espera(
        _chamar("com", "patch", url, {"indicado_por_id": estado["cli_ana"]}), 200, "ind"
    )
    _garante((corpo.get("indicado_por") or {}).get("id") == estado["cli_ana"], f"{corpo}")
    _garante(_ficha("bia").indicado_por_id == estado["cli_ana"], "não gravou")
    ana = _espera(_chamar("com", "get", _url_cli("ana")), 200, "detalhe da Ana")
    _garante(estado["cli_bia"] in [i["id"] for i in ana.get("indicacoes") or []], "Indicou vazio")
    r = _chamar(
        "com", "patch", _url_cli("ana", "/indicacao"), {"indicado_por_id": estado["cli_ana"]}
    )
    _garante("indicado_por_id" in (_erro(r).get("fields") or {}), "auto-indicação passou")
    r = _chamar("com", "patch", _url_cli("ana", "/indicacao"), {"indicado_por_id": 987654321})
    _garante("indicado_por_id" in (_erro(r).get("fields") or {}), "indicação inexistente passou")
    r = _chamar("fin", "patch", url, {"indicado_por_id": None})
    _garante(r.status_code == 403, f"Financeiro mudou a indicação: {r.status_code}")


def cen_15_parceiros() -> None:
    novo = {"nome": f"{PREFIX}Buffet Alegria", "tipo": "buffet", "comissao_percentual": "10"}
    r = _chamar("fin", "post", "/api/parceiros", novo)
    _garante(r.status_code == 403, f"Financeiro criou parceiro: {r.status_code}")
    r = _chamar("com", "post", "/api/parceiros", {**novo, "comissao_percentual": "120"})
    _garante("comissao_percentual" in (_erro(r).get("fields") or {}), "comissão 120 passou")
    r = _chamar("com", "post", "/api/parceiros", {**novo, "tipo": "padaria"})
    _garante("tipo" in (_erro(r).get("fields") or {}), "tipo inválido passou")
    corpo = _espera(_chamar("com", "post", "/api/parceiros", novo), 201, "criar")
    parceiro = corpo["id"]
    estado["parceiro"] = parceiro
    _espera(
        _chamar("com", "patch", _url_cli("bia", "/indicacao"), {"parceiro_id": parceiro}),
        200,
        "ligar",
    )
    lista = _espera(_chamar("fin", "get", "/api/parceiros"), 200, "lista (Fin)")
    item = next(i for i in lista["items"] if i["id"] == parceiro)
    _garante(item["clientes"] == 1 and item["comissao_percentual"] == "10.00", f"{item}")
    _espera(_chamar("com", "patch", f"/api/parceiros/{parceiro}", {"ativo": False}), 200, "inativo")
    r = _chamar("com", "patch", _url_cli("cris", "/indicacao"), {"parceiro_id": parceiro})
    _garante("parceiro_id" in (_erro(r).get("fields") or {}), "parceiro inativo aceito")
    bia = _espera(_chamar("com", "get", _url_cli("bia")), 200, "detalhe da Bia")
    _garante((bia.get("parceiro") or {}).get("id") == parceiro, "a ficha perdeu o parceiro")
    lista = _espera(_chamar("com", "get", "/api/parceiros"), 200, "lista ativa")
    _garante(all(i["id"] != parceiro for i in lista["items"]), "inativo na lista padrão")


def cen_16_aniversarios() -> None:
    _aceitar("ana")  # Lia (10 dias) e Theo (30 dias) da Ana
    _aceitar("bia")
    _espera(
        _chamar(
            "com",
            "post",
            _url_cli("bia", "/criancas"),
            {
                "primeiro_nome": "Nina",
                "nascimento": _daqui(90, 4),
                "aceite": True,
                "origem": "Conversa",
            },
        ),
        201,
        "Nina",
    )
    _espera(
        _chamar(
            "com",
            "post",
            _url_cli("cris", "/criancas"),
            {
                "primeiro_nome": "Bento",
                "nascimento": _daqui(5, 6),
                "aceite": True,
                "origem": "Conversa",
            },
        ),
        201,
        "Bento",
    )  # a Cris não tem aceite de novidades
    corpo = _espera(_chamar("com", "get", "/api/clientes/aniversarios"), 200, "aniversários")
    nossos = {
        i["primeiro_nome"]: i
        for i in corpo["items"]
        if i["cliente"]["id"] in (estado["cli_ana"], estado["cli_bia"], estado["cli_cris"])
    }
    _garante(set(nossos) == {"Lia", "Theo"}, f"lista: {sorted(nossos)}")
    _garante(nossos["Lia"]["dias"] == 10 and nossos["Lia"]["idade"] == 5, f"Lia: {nossos['Lia']}")
    datas = [i["data"] for i in corpo["items"]]
    _garante(datas == sorted(datas), "lista fora de ordem")
    with app.app_context():
        from app.clientes.aniversario_ops import proximo_aniversario

        _garante(
            proximo_aniversario(date(2020, 2, 29), date(2027, 1, 10)) == date(2027, 2, 28),
            "29/02 em ano comum",
        )
        _garante(
            proximo_aniversario(date(2020, 2, 29), date(2028, 1, 10)) == date(2028, 2, 29),
            "29/02 em ano bissexto",
        )
        _garante(
            proximo_aniversario(date(2020, 5, 1), date(2026, 5, 2)) == date(2027, 5, 1),
            "aniversário que já passou",
        )


def cen_17_orcamento() -> None:
    corpo = _espera(
        _chamar(
            "com",
            "post",
            "/api/orcamento/calcular",
            {
                "performers": [
                    {"type": "ator", "subtipo": "cara_limpa", "nome": "Teste", "makeup": False}
                ],
                "coordenador_qty": 1,
                "event_date": (now_sp().date() + timedelta(days=60)).isoformat(),
                "event_time": "15:00",
                "client_name": f"{PREFIX}Cliente",
                "event_location": f"{PREFIX}Salão",
                "incluir_duracao": ["1h", "2h"],
                "modo_duracao": "horas",
            },
        ),
        200,
        "calcular",
    )
    mensagem = (corpo.get("quote") or {}).get("message") or ""
    _garante("Podemos seguir com a reserva da sua data?" in mensagem, "frase de fecho sumiu")
    _garante("QUERO" in mensagem.rsplit("Podemos seguir", 1)[-1], "sem o convite no fim")


def cen_18_loja() -> None:
    from app.marketing import virtuais_ops

    with app.app_context():
        evento = db.session.get(CalendarEvent, estado["evt_velho"])
        cliente = db.session.get(Client, estado["cli_loja"])
        aceite = now_sp() - timedelta(days=2)
        cliente.marketing_opt_out_at = now_sp() - timedelta(days=1)  # saiu depois do pedido
        db.session.commit()
        pedido = SimpleNamespace(
            id=987350,
            order_nsu=f"{PREFIX}nsu",
            contact_phone=TEL["loja"][2:],
            contact_phone_display=TEL["loja"],
            contact_email="lu@v350.local",
            buyer_name="Lu",
            campaign=SimpleNamespace(title=f"{PREFIX}Natal"),
            origem="instagram",
            marketing_opt_in_at=aceite,
            marketing_opt_in_version="2026-11-16",
        )
        virtuais_ops._cliente_da_venda(pedido, evento)
        db.session.commit()
    _garante(_ficha("loja").marketing_opt_in_at is None, "aceite anterior à retirada voltou")
    with app.app_context():
        pedido.marketing_opt_in_at = now_sp()  # aceite novo, depois da retirada
        virtuais_ops._cliente_da_venda(pedido, db.session.get(CalendarEvent, estado["evt_velho"]))
        db.session.commit()
    ficha = _ficha("loja")
    _garante(ficha.marketing_opt_in_at is not None, "aceite novo da loja não chegou à ficha")
    ultima = _historico("loja")[-1]
    _garante(
        ultima.texto == VIRTUAL_ACEITE_TEXTO and ultima.versao == "2026-11-16", "texto da loja"
    )
    _garante(ultima.referencia == "pedido:987350", f"referência: {ultima.referencia}")
    _garante(ultima.origem == f"Loja: {PREFIX}Natal", f"origem: {ultima.origem}")


def cen_19_exclusao_da_ficha() -> None:
    """LGPD: excluir a ficha leva o histórico e as crianças; quem ela indicou só perde o vínculo."""
    dani = estado["cli_dani"]
    _aceitar("dani")
    _espera(
        _chamar(
            "com",
            "post",
            _url_cli("dani", "/criancas"),
            {
                "primeiro_nome": "Dudu",
                "nascimento": _daqui(40, 2),
                "aceite": True,
                "origem": "Telefone",
            },
        ),
        201,
        "criança da Dani",
    )
    _espera(
        _chamar("com", "patch", _url_cli("cris", "/indicacao"), {"indicado_por_id": dani}),
        200,
        "Cris indicada pela Dani",
    )
    _garante(
        _um("SELECT count(*) AS n FROM cliente_consentimentos WHERE client_id=:i", i=dani).n == 2,
        "pré-condição: aceite e aniversário no histórico",
    )
    r = _chamar("fin", "delete", _url_cli("dani"))
    _garante(r.status_code == 204, f"exclusão: {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(_um("SELECT count(*) AS n FROM clients WHERE id=:i", i=dani).n == 0, "ficha ficou")
    for tabela in ("cliente_consentimentos", "cliente_criancas"):
        sobra = _um(f"SELECT count(*) AS n FROM {tabela} WHERE client_id=:i", i=dani).n
        _garante(sobra == 0, f"{tabela} ficou com {sobra} linha(s) da ficha excluída")
    _garante(_ficha("cris").indicado_por_id is None, "a indicada ficou apontando para a excluída")


CENARIOS = [
    ("1 esquema", cen_01_esquema),
    ("2 aceite pela ficha", cen_02_aceite_pela_ficha),
    ("3 retirada pela ficha", cen_03_retirada_pela_ficha),
    ("4 RBAC (deve falhar)", cen_04_rbac),
    ("5 criança", cen_05_crianca),
    ("6 aceite pela conversa", cen_06_aceite_pela_conversa),
    ("7 saída: SAIR recebido", cen_07_saida_por_palavra),
    ("8 saída: erro 131050", cen_08_saida_por_131050),
    ("9 modelo de marketing sem aceite", cen_09_modelo_de_marketing),
    ("10 pós-evento: mensagem", cen_10_pos_evento_mensagem),
    ("11 pós-evento: copiar e lista", cen_11_copiar_e_lista),
    ("12 pós-evento: conversa", cen_12_pos_evento_conversa),
    ("13 página pública", cen_13_pagina_publica),
    ("14 indicação", cen_14_indicacao),
    ("15 parceiros", cen_15_parceiros),
    ("16 aniversários", cen_16_aniversarios),
    ("17 orçamento", cen_17_orcamento),
    ("18 loja (344)", cen_18_loja),
    ("19 exclusão da ficha", cen_19_exclusao_da_ficha),
]


def main() -> int:
    so = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--so=")), None)
    escolhidos = {s.strip() for s in so.split(",")} if so else None
    _garante(TRAVA_DE_FABRICA is True, "a trava do WhatsApp não nasceu ligada contra o banco local")
    print("verify 350 — base autorizada")
    try:
        preparar()
        for nome, fn in CENARIOS:
            if escolhidos is None or nome.split()[0] in escolhidos:
                cenario(nome, fn)
    finally:
        if not MANTER:
            try:
                limpar()
                sobra = _um(
                    "SELECT count(*) AS n FROM clients WHERE phone IN " + str(tuple(TEL.values()))
                )
                resultados.append(("20 limpeza", sobra.n == 0, f"{sobra.n} fichas sobraram"))
                print(f"  {'OK   ' if sobra.n == 0 else 'FALHA'}  20 limpeza")
            except Exception as exc:  # noqa: BLE001 — a limpeza não pode esconder o resultado
                resultados.append(("20 limpeza", False, str(exc)))
                print(f"  FALHA  20 limpeza: {exc}")
    _garante_sem_escape()
    falhas = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} cenários OK")
    for nome, _ok, motivo in falhas:
        print(f"  ✗ {nome}: {motivo}")
    return 1 if falhas else 0


def _garante_sem_escape() -> None:
    if _ESCAPES:
        resultados.append(("disjuntor", False, f"conexões de saída: {sorted(set(_ESCAPES))}"))


if __name__ == "__main__":
    sys.exit(main())
