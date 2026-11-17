"""Verificação da feature 335 — Linha do tempo da ficha e funil das conversas.

Os cenários da tabela da spec, contra o `manto_local`. Só leitura na API: as conversas, as mensagens, os anúncios, os
orçamentos, os formulários, os eventos, os pagamentos e as avaliações são semeados direto no banco (nada fala com a
Meta nem com o Google; um disjuntor de rede derruba qualquer conexão que não seja o Postgres local). As contagens do
funil são conferidas pela DIFERENÇA para a leitura de antes de semear, e as porcentagens no recorte da campanha de
teste: o `manto_local` pode ter outras conversas.

Tudo de teste leva `v335-`. Rodar (PowerShell, na raiz)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
    $env:PYTHONUTF8 = '1'; .venv\\Scripts\\python.exe specs/335-crm-linha-do-tempo/verify_335.py
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
import traceback
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
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
        raise OSError(f"verify 335: conexão de saída bloqueada para {_host_de(endereco)}")
    return _connect_original(self, endereco)


def _create_connection_local(endereco, *args, **kwargs):
    if _host_de(endereco) not in _LOCAIS:
        _ESCAPES.append(_host_de(endereco))
        raise OSError(f"verify 335: conexão de saída bloqueada para {_host_de(endereco)}")
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
    AnuncioMeta,
    CalendarEvent,
    Client,
    ClientFeedback,
    Conversa,
    ConversaAnuncio,
    ConversaMensagem,
    EventClient,
    EventPayment,
    FormResponse,
    OrcamentoEnvio,
    OrcamentoHistory,
    PixRecebido,
    Role,
    User,
)

PREFIX = "v335-"
SENHA = "verify-335-senha"
FESTA = f"{PREFIX}Festa infantil SP"
REPESCAGEM = f"{PREFIX}Repescagem"
AD = {n: f"{PREFIX}ad-{n}" for n in range(1, 4)}
CAMPANHAS = {AD[1]: FESTA, AD[2]: REPESCAGEM, AD[3]: FESTA}
# Conversa: (canal, responsável, etapa mais avançada esperada); contatos e telefones derivados do número.
CONVERSAS = {
    1: (
        "whatsapp",
        "ana",
        "avaliou",
    ),  # anúncio 1; orçamento, formulário, evento, pagamento e avaliação
    2: ("whatsapp", "ana", "orcamento"),  # anúncio 1; só o orçamento
    3: ("instagram", "bia", "orcamento"),  # sem ficha; o orçamento pela conversa
    4: ("whatsapp", "bia", "evento"),  # anúncio 3; evento sem orçamento nem formulário (o celular)
    5: ("whatsapp", None, "chegou"),  # ficha com evento e formulário ANTIGOS
    6: ("instagram", "ana", "formulario"),  # anúncio 2 (repescagem); formulário
    7: ("whatsapp", "bia", "chegou"),  # anúncio 1; nada depois
    8: ("whatsapp", "ana", None),  # fora do período (40 dias), evento de ontem
    9: ("whatsapp", "ana", "chegou"),  # evento cancelado
    10: ("whatsapp", "bia", "pagou"),  # evento satélite; o pagamento no principal do grupo
    11: ("whatsapp", "ana", None),  # só mensagens da Manto: não entra
    12: (
        "whatsapp",
        None,
        None,
    ),  # 23 h de São Paulo da véspera do período (já o 1º dia em UTC): fora
    13: ("whatsapp", None, "chegou"),  # 00h30 de São Paulo do 1º dia do período (03h30 UTC): dentro
}
DIAS = {
    1: 5,
    2: 4.5,
    3: 4,
    4: 3.5,
    5: 3,
    6: 2.5,
    7: 2,
    8: 40,
    9: 1.5,
    10: 1,
    11: 0.5,
}  # dias atrás do 1º contato (12 e 13 são horas de São Paulo, em `semear`)
SEM_FICHA = (3, 7, 12, 13)
CONTATOS = [
    f"55119633500{n:02d}" if CONVERSAS[n][0] == "whatsapp" else f"335335000000{n:04d}"
    for n in CONVERSAS
]
TELEFONES = [f"55119633500{n:02d}" for n in CONVERSAS]

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {"conversas": {}, "fichas": {}, "eventos": {}}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchone()


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


def _hoje_sp() -> date:
    return datetime.now(TZ_SP).date()


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


def _chamar(email: str, url: str):
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
        _garante(r.status_code == 200, f"login {email} → {r.status_code}")
        return c.get(url)


def _periodo() -> str:
    hoje = _hoje_sp()
    return f"inicio={hoje - timedelta(days=10)}&fim={hoje}"


def _funil(email: str, extra: str = "") -> dict:
    inicio = time.perf_counter()
    r = _chamar(email, f"/api/conversas/funil?{_periodo()}{extra}")
    estado.setdefault("tempos", []).append(time.perf_counter() - inicio)
    _garante(r.status_code == 200, f"funil → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()


def _quantidades(resposta: dict) -> dict[str, int]:
    return {e["chave"]: e["quantidade"] for e in resposta["etapas"]}


def _parados(email: str, etapa: str, extra: str = "") -> dict:
    r = _chamar(email, f"/api/conversas/funil/parados?{_periodo()}&etapa={etapa}{extra}")
    _garante(r.status_code == 200, f"parados → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()


# ── Semeadura ──────────────────────────────────────────────────────────────────────────────────


def _ficha(n: int, criada: datetime) -> int:
    ficha = Client(
        name=f"{PREFIX}Cliente {n}", phone=TELEFONES[n - 1], source="conversa", created_at=criada
    )
    if n == 5:
        # Do Kommo: a entrada é o "Criado em" de lá, no horário de São Paulo.
        ficha.source = "kommo_import"
        ficha.kommo_created_at = datetime(2025, 3, 10, 22, 30)
    db.session.add(ficha)
    db.session.flush()
    estado["fichas"][n] = ficha.id
    return ficha.id


def _evento(nome: str, criado: datetime, **campos) -> CalendarEvent:
    evento = CalendarEvent(
        google_event_id=f"{PREFIX}{nome}-{uuid.uuid4().hex[:8]}",
        title=f"{PREFIX}{nome}",
        start_at=datetime.now() + timedelta(days=30),
        source="platform",
        created_at=criado,
        **campos,
    )
    db.session.add(evento)
    db.session.flush()
    estado["eventos"][nome] = evento.id
    return evento


def _orcamento(ficha_id: int | None, criado: datetime) -> int:
    from app.orcamento import quote_ops

    entry = OrcamentoHistory(
        user_id=estado["ana_id"],
        client_name=f"{PREFIX}Orçamento",
        client_id=ficha_id,
        event_location=f"{PREFIX}Buffet Alegria",
        event_date=(_agora() + timedelta(days=30)).date().isoformat(),
        total_1h=Decimal("1800"),
        total_2h=Decimal("2400"),
        total_3h=Decimal("3000"),
        total_4h=Decimal("3500"),
        has_show=False,
        created_at=criado,
    )
    db.session.add(entry)
    db.session.flush()
    quote = quote_ops.legacy_quote(entry)
    quote["message"] = "Olá! Segue o orçamento."
    entry.result_snapshot = json.dumps(quote, ensure_ascii=False)
    return entry.id


def semear() -> None:
    agora = _agora()
    usuarios = {"ana": estado["ana_id"], "bia": estado["bia_id"]}
    primeiro = {n: agora - timedelta(days=d) for n, d in DIAS.items()}
    inicio = _hoje_sp() - timedelta(days=10)
    for n, dia, hora_sp in ((12, inicio - timedelta(days=1), (23, 0)), (13, inicio, (0, 30))):
        local = datetime(dia.year, dia.month, dia.day, *hora_sp, tzinfo=TZ_SP)
        primeiro[n] = local.astimezone(UTC).replace(tzinfo=None)
    estado["primeiro"] = primeiro
    for n, (canal, resp, _) in CONVERSAS.items():
        ficha_id = None if n in SEM_FICHA else _ficha(n, primeiro[n] - timedelta(days=1))
        conversa = Conversa(
            canal=canal,
            contato_id=CONTATOS[n - 1],
            telefone=TELEFONES[n - 1] if canal == "whatsapp" else None,
            nome_perfil=f"{PREFIX}Perfil {n}",
            client_id=ficha_id,
            responsavel_id=usuarios.get(resp) if resp else None,
            ultima_mensagem_em=primeiro[n],
            created_at=agora,
        )
        db.session.add(conversa)
        db.session.flush()
        estado["conversas"][n] = conversa.id
        recebida = n != 11
        db.session.add(
            ConversaMensagem(
                conversa_id=conversa.id,
                direcao="recebida" if recebida else "enviada",
                tipo="texto",
                texto="Quero um orçamento",
                externo_id=f"{PREFIX}m-{n}",
                situacao="recebida" if recebida else "enviada",
                origem="contato" if recebida else "plataforma",
                momento=primeiro[n],
                created_at=agora,
            )
        )
        # Uma segunda mensagem dela, mais nova: o primeiro contato é a primeira.
        if recebida:
            db.session.add(
                ConversaMensagem(
                    conversa_id=conversa.id,
                    direcao="recebida",
                    tipo="texto",
                    texto="Alguém?",
                    externo_id=f"{PREFIX}m-{n}-b",
                    situacao="recebida",
                    origem="contato",
                    momento=primeiro[n] + timedelta(hours=1),
                    created_at=agora,
                )
            )
    for anuncio, campanha in CAMPANHAS.items():
        db.session.add(
            AnuncioMeta(
                anuncio_id=anuncio,
                nome=f"Anúncio {anuncio}",
                campanha_nome=campanha,
                consultado_em=agora,
            )
        )
    for n, anuncio, titulo in ((1, AD[1], "Festa com personagens"), (2, AD[1], "Festa com personagens"),
                               (4, AD[3], "Personagens"), (6, AD[2], "Volte a festejar"),
                               (7, AD[1], "Festa com personagens")):  # fmt: skip
        db.session.add(
            ConversaAnuncio(
                conversa_id=estado["conversas"][n],
                canal=CONVERSAS[n][0],
                chave=f"{PREFIX}ref-{n}",
                tipo="anuncio",
                anuncio_id=anuncio,
                titulo=titulo,
                link=f"https://fb.me/{anuncio}",
                momento=primeiro[n],
                created_at=agora,
            )
        )
    f, c = estado["fichas"], estado["conversas"]
    # 1: tudo, em ordem.
    orc1 = _orcamento(f[1], primeiro[1] + timedelta(days=1))
    db.session.add(
        OrcamentoEnvio(
            orcamento_id=orc1,
            conversa_id=c[1],
            autor_id=estado["ana_id"],
            chave_envio=f"{PREFIX}env-1",
            created_at=primeiro[1] + timedelta(days=1, hours=1),
        )
    )
    db.session.add(
        FormResponse(
            form_type="comum",
            data="[]",
            contact_name=f"{PREFIX}Cliente 1",
            contact_phone=TELEFONES[0],
            client_id=f[1],
            client_link_source="auto_phone",
            created_at=primeiro[1] + timedelta(days=2),
        )
    )
    e1 = _evento("festa-1", primeiro[1] + timedelta(days=3))
    db.session.add(EventClient(event_id=e1.id, client_id=f[1]))
    db.session.add(
        EventPayment(
            event_id=e1.id,
            file_path=f"{PREFIX}comprovante.pdf",
            amount=Decimal("500.00"),
            created_at=primeiro[1] + timedelta(days=4),
        )
    )
    db.session.add(
        ClientFeedback(
            event_id=e1.id, score=5, submitted_at=primeiro[1] + timedelta(days=4, hours=12)
        )
    )
    # 1 também: um evento cancelado, com pagamento e avaliação, que não aparece em lugar nenhum.
    e1c = _evento("cancelado-1", primeiro[1] + timedelta(days=3), cancelled_at=datetime.now())
    db.session.add(EventClient(event_id=e1c.id, client_id=f[1]))
    db.session.add(
        EventPayment(
            event_id=e1c.id, file_path=f"{PREFIX}c.pdf", amount=Decimal("99.00"), created_at=agora
        )
    )
    db.session.add(ClientFeedback(event_id=e1c.id, score=1, submitted_at=agora))
    # 2: só o orçamento enviado pela conversa.
    orc2 = _orcamento(f[2], primeiro[2] + timedelta(hours=2))
    db.session.add(
        OrcamentoEnvio(
            orcamento_id=orc2,
            conversa_id=c[2],
            autor_id=estado["ana_id"],
            chave_envio=f"{PREFIX}env-2",
            created_at=primeiro[2] + timedelta(hours=2),
        )
    )
    # 3: sem ficha; o orçamento pela conversa.
    orc3 = _orcamento(None, primeiro[3] + timedelta(hours=2))
    db.session.add(
        OrcamentoEnvio(
            orcamento_id=orc3,
            conversa_id=c[3],
            autor_id=estado["bia_id"],
            chave_envio=f"{PREFIX}env-3",
            created_at=primeiro[3] + timedelta(hours=2),
        )
    )
    # 4: o evento fechou sem orçamento nem formulário na Plataforma.
    e4 = _evento("festa-4", primeiro[4] + timedelta(days=1))
    db.session.add(EventClient(event_id=e4.id, client_id=f[4]))
    # 5: o evento e o formulário são de antes do primeiro contato (cliente antiga).
    e5 = _evento("antigo-5", primeiro[5] - timedelta(days=60))
    db.session.add(EventClient(event_id=e5.id, client_id=f[5]))
    db.session.add(
        FormResponse(
            form_type="comum",
            data="[]",
            contact_name=f"{PREFIX}Cliente 5",
            client_id=f[5],
            created_at=primeiro[5] - timedelta(days=61),
        )
    )
    # 6: formulário (Instagram).
    db.session.add(
        FormResponse(
            form_type="corporativo",
            data="[]",
            contact_name=f"{PREFIX}Cliente 6",
            client_id=f[6],
            created_at=primeiro[6] + timedelta(hours=5),
        )
    )
    # 8: fora do período, com evento de ontem.
    e8 = _evento("festa-8", agora - timedelta(days=1))
    db.session.add(EventClient(event_id=e8.id, client_id=f[8]))
    # 9: o único evento foi cancelado.
    e9 = _evento("cancelado-9", primeiro[9] + timedelta(hours=3), cancelled_at=datetime.now())
    db.session.add(EventClient(event_id=e9.id, client_id=f[9]))
    # ... com pagamento e avaliação, que também não fazem andar.
    db.session.add(
        EventPayment(
            event_id=e9.id, file_path=f"{PREFIX}c9.pdf", amount=Decimal("50.00"), created_at=agora
        )
    )
    db.session.add(ClientFeedback(event_id=e9.id, score=4, submitted_at=agora))
    # 10: grupo — a ficha está no satélite; o pagamento, por PIX, no principal.
    lider = _evento("lider-10", primeiro[10] + timedelta(hours=2))
    satelite = _evento("satelite-10", primeiro[10] + timedelta(hours=2), group_leader_id=lider.id)
    db.session.add(EventClient(event_id=satelite.id, client_id=f[10]))
    pagamento = EventPayment(
        event_id=lider.id,
        file_path=None,
        origem="pix_email",
        amount=Decimal("800.00"),
        created_at=agora,
    )
    db.session.add(pagamento)
    db.session.flush()
    # A hora real do PIX (São Paulo), anterior ao registro do pagamento: é ela que vai à linha do tempo.
    estado["pix_sp"] = (
        (primeiro[10] + timedelta(hours=6))
        .replace(tzinfo=UTC)
        .astimezone(TZ_SP)
        .replace(tzinfo=None)
    )
    db.session.add(
        PixRecebido(
            origem="email",
            message_id=f"{PREFIX}pix-{uuid.uuid4().hex[:8]}",
            tipo="pix",
            valor=Decimal("800.00"),
            recebido_em=estado["pix_sp"],
            event_payment_id=pagamento.id,
        )
    )
    db.session.commit()


# ── Cenários ───────────────────────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    r = _chamar(estado["ana"], f"/api/clientes/{estado['fichas'][1]}/linha-do-tempo")
    _garante(
        r.status_code == 200, f"linha do tempo → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    marcos = r.get_json()["marcos"]
    tipos = [m["tipo"] for m in marcos]
    for tipo in (
        "entrada",
        "contato",
        "anuncio",
        "orcamento",
        "formulario",
        "evento",
        "pagamento",
        "avaliacao",
    ):
        _garante(
            tipos.count(tipo) == 1, f"o marco {tipo} aparece {tipos.count(tipo)} vez(es): {tipos}"
        )
    quandos = [datetime.fromisoformat(m["quando"]) for m in marcos]
    _garante(
        quandos == sorted(quandos, reverse=True),
        "os marcos não estão do mais novo para o mais antigo",
    )
    por_tipo = {m["tipo"]: m for m in marcos}
    contato = (
        datetime.fromisoformat(por_tipo["contato"]["quando"]).astimezone(UTC).replace(tzinfo=None)
    )
    _garante(
        abs((contato - estado["primeiro"][1]).total_seconds()) < 1, f"primeiro contato {contato}"
    )
    _garante(
        por_tipo["contato"]["link"] == {"tipo": "conversa", "id": estado["conversas"][1]},
        "link da conversa",
    )
    _garante((por_tipo["orcamento"]["link"] or {}).get("tipo") == "orcamento", "link do orçamento")
    _garante(
        por_tipo["evento"]["link"] == {"tipo": "evento", "id": estado["eventos"]["festa-1"]},
        "link do evento",
    )
    _garante(
        "Festa com personagens" in (por_tipo["anuncio"]["detalhe"] or ""),
        f"anúncio {por_tipo['anuncio']}",
    )


def cen_02() -> None:
    r = _chamar(estado["ana"], f"/api/clientes/{estado['fichas'][1]}/linha-do-tempo")
    marcos = r.get_json()["marcos"]
    eventos = [m["link"]["id"] for m in marcos if m["tipo"] == "evento"]
    _garante(estado["eventos"]["cancelado-1"] not in eventos, "o evento cancelado apareceu")
    _garante(
        sum(m["tipo"] == "pagamento" for m in marcos) == 1, "apareceu o pagamento do cancelado"
    )
    _garante(
        sum(m["tipo"] == "avaliacao" for m in marcos) == 1, "apareceu a avaliação do cancelado"
    )
    # O pagamento do principal do grupo, na hora real do PIX (São Paulo), não na do registro.
    marcos = _chamar(
        estado["ana"], f"/api/clientes/{estado['fichas'][10]}/linha-do-tempo"
    ).get_json()["marcos"]
    pagamento = next((m for m in marcos if m["tipo"] == "pagamento"), None)
    _garante(
        pagamento is not None and "PIX" in (pagamento["detalhe"] or ""),
        f"pagamento do grupo {pagamento}",
    )
    _garante(
        datetime.fromisoformat(pagamento["quando"]) == estado["pix_sp"].replace(tzinfo=TZ_SP),
        f"hora do PIX {pagamento['quando']}",
    )
    # A ficha do Kommo entra pelo "Criado em" de lá, no horário de São Paulo.
    marcos = _chamar(
        estado["ana"], f"/api/clientes/{estado['fichas'][5]}/linha-do-tempo"
    ).get_json()["marcos"]
    entrada = next(m for m in marcos if m["tipo"] == "entrada")
    _garante(
        datetime.fromisoformat(entrada["quando"]) == datetime(2025, 3, 10, 22, 30, tzinfo=TZ_SP)
        and "Kommo" in (entrada["detalhe"] or ""),
        f"entrada do Kommo {entrada}",
    )


def cen_03() -> None:
    r = _chamar(estado["fin"], f"/api/clientes/{estado['fichas'][1]}/linha-do-tempo")
    _garante(r.status_code == 200, f"Financeiro → {r.status_code}")
    marcos = {m["tipo"]: m for m in r.get_json()["marcos"]}
    _garante(marcos["contato"]["link"] is None, "o Financeiro ganhou o link da conversa")
    _garante(marcos["orcamento"]["link"] is None, "o Financeiro ganhou o link do orçamento")
    _garante(marcos["evento"]["link"] is not None, "o Financeiro perdeu o link do evento")
    _garante(
        "500" in (marcos["pagamento"]["detalhe"] or ""), f"valor do pagamento {marcos['pagamento']}"
    )
    r = _chamar(estado["cast"], f"/api/clientes/{estado['fichas'][1]}/linha-do-tempo")
    _garante(r.status_code == 403, f"Casting → {r.status_code}")
    r = _chamar(estado["ana"], "/api/clientes/999999999/linha-do-tempo")
    _garante(r.status_code == 404, f"ficha inexistente → {r.status_code}")


def cen_04() -> None:
    depois = _quantidades(_funil(estado["ana"]))
    antes = estado["antes"]
    delta = {k: depois[k] - antes[k] for k in depois}
    # 13 entra (00h30 do 1º dia em São Paulo); 8, 11 e 12 não.
    esperado = {
        "chegou": 10,
        "orcamento": 6,
        "formulario": 4,
        "evento": 3,
        "pagou": 2,
        "avaliou": 1,
    }
    _garante(delta == esperado, f"funil {delta} ≠ {esperado}")
    festa = _funil(estado["ana"], f"&campanha={FESTA}")
    etapas = {e["chave"]: e for e in festa["etapas"]}
    _garante(
        [etapas[k]["quantidade"] for k in esperado] == [4, 3, 2, 2, 1, 1],
        f"funil da Festa {[etapas[k]['quantidade'] for k in esperado]}",
    )
    _garante(
        etapas["chegou"]["sobre_chegou"] == 100.0 and etapas["chegou"]["passagem"] is None, "Chegou"
    )
    _garante(etapas["orcamento"]["sobre_chegou"] == 75.0, f"orçamento {etapas['orcamento']}")
    _garante(
        etapas["formulario"]["passagem"] == 66.7, f"passagem do formulário {etapas['formulario']}"
    )
    _garante(etapas["evento"]["passagem"] == 100.0, f"passagem do evento {etapas['evento']}")


def cen_05() -> None:
    ids = {c["id"] for c in _parados(estado["ana"], "chegou")["conversas"]}
    c = estado["conversas"]
    _garante({c[5], c[7], c[9]} <= ids, f"pararam em Chegou: faltou alguém {ids}")
    _garante(c[8] not in ids, "a conversa de fora do período entrou")
    _garante(c[11] not in ids, "a conversa sem mensagem da cliente entrou")
    _garante(c[13] in ids, "a conversa das 00h30 de São Paulo do 1º dia ficou de fora")
    _garante(c[12] not in ids, "a conversa das 23 h de São Paulo da véspera entrou")
    for etapa in ("orcamento", "formulario", "evento", "pagou", "avaliou"):
        outros = {x["id"] for x in _parados(estado["ana"], etapa)["conversas"]}
        _garante(not ({c[5], c[8], c[9], c[11]} & outros), f"conversa a mais em {etapa}: {outros}")


def cen_06() -> None:
    instagram = _quantidades(_funil(estado["ana"], "&canal=instagram"))
    antes_ig = estado["antes_ig"]
    _garante(
        instagram["chegou"] - antes_ig["chegou"] == 2, f"Instagram {instagram} (antes {antes_ig})"
    )
    repescagem = _quantidades(_funil(estado["ana"], f"&canal=instagram&campanha={REPESCAGEM}"))
    _garante(
        repescagem
        == {"chegou": 1, "orcamento": 1, "formulario": 1, "evento": 0, "pagou": 0, "avaliou": 0},
        f"Instagram + Repescagem {repescagem}",
    )
    for dividir in ("vendedor", "campanha", "canal"):
        resposta = _funil(estado["ana"], f"&dividir={dividir}")
        for etapa in resposta["etapas"]:
            soma = sum(g["quantidades"][etapa["chave"]] for g in resposta["grupos"])
            _garante(
                soma == etapa["quantidade"],
                f"{dividir}: soma de {etapa['chave']} {soma} ≠ {etapa['quantidade']}",
            )
    vendedores = {g["chave"]: g for g in _funil(estado["ana"], "&dividir=vendedor")["grupos"]}
    ana, bia = vendedores.get(str(estado["ana_id"])), vendedores.get(str(estado["bia_id"]))
    _garante(
        ana and ana["quantidades"]["chegou"] == 4 and ana["quantidades"]["evento"] == 1,
        f"Ana {ana}",
    )
    _garante(
        bia and bia["quantidades"]["chegou"] == 4 and bia["quantidades"]["evento"] == 2,
        f"Bia {bia}",
    )
    _garante(bia["conversao"] == 50.0, f"conversão da Bia {bia['conversao']}")
    campanhas = {g["chave"]: g for g in _funil(estado["ana"], "&dividir=campanha")["grupos"]}
    _garante(
        campanhas.get(FESTA, {}).get("quantidades", {}).get("chegou") == 4,
        f"campanhas {list(campanhas)}",
    )
    opcoes = {o["valor"] for o in _funil(estado["ana"])["campanhas"]}
    _garante({FESTA, REPESCAGEM, "__sem_anuncio__"} <= opcoes, f"opções de campanha {opcoes}")
    # "Sem anúncio": 3, 5, 9, 10 e 13 (o 10 pagou; o 9 tem o evento cancelado, com pagamento e avaliação).
    sem = _quantidades(_funil(estado["ana"], "&campanha=__sem_anuncio__"))
    delta = {k: sem[k] - estado["antes_sem"][k] for k in sem}
    _garante(
        delta
        == {"chegou": 5, "orcamento": 2, "formulario": 1, "evento": 1, "pagou": 1, "avaliou": 0},
        f"Sem anúncio {delta}",
    )
    fila = vendedores.get("__sem_responsavel__")
    _garante(
        fila and fila["rotulo"] == "Sem responsável" and fila["quantidades"]["chegou"] >= 2,
        f"Sem responsável {fila}",
    )
    # Sem período: o mês corrente, até hoje (São Paulo).
    r = _chamar(estado["ana"], "/api/conversas/funil")
    periodo = (r.get_json() or {}).get("periodo")
    hoje = _hoje_sp()
    _garante(
        r.status_code == 200
        and periodo == {"inicio": hoje.replace(day=1).isoformat(), "fim": hoje.isoformat()},
        f"período padrão {r.status_code} {periodo}",
    )


def cen_07() -> None:
    c = estado["conversas"]
    orcamento = _parados(estado["ana"], "orcamento")
    ids = [x["id"] for x in orcamento["conversas"]]
    _garante(c[2] in ids and c[3] in ids, f"pararam em Orçamento {ids}")
    _garante(c[1] not in ids and c[4] not in ids and c[6] not in ids, f"a mais em Orçamento {ids}")
    _garante(ids.index(c[3]) < ids.index(c[2]), "a lista não está da mais nova para a mais antiga")
    linha = next(x for x in orcamento["conversas"] if x["id"] == c[3])
    _garante(
        linha["canal"] == "instagram" and linha["vendedor"] == f"{PREFIX}Bia", f"linha {linha}"
    )
    _garante(
        orcamento["rotulo"] == "Orçamento enviado" and orcamento["total"] >= 2,
        f"{orcamento['rotulo']}",
    )
    _garante(c[1] in [x["id"] for x in _parados(estado["ana"], "avaliou")["conversas"]], "Avaliou")
    _garante(
        c[10] in [x["id"] for x in _parados(estado["ana"], "pagou")["conversas"]], "Pagou (grupo)"
    )
    _garante(max(estado["tempos"]) < 2.0, f"o funil levou {max(estado['tempos']):.2f} s")


def cen_08() -> None:
    for quem in ("fin", "cast"):
        r = _chamar(estado[quem], f"/api/conversas/funil?{_periodo()}")
        _garante(r.status_code == 403, f"{quem} no funil → {r.status_code}")
        r = _chamar(estado[quem], f"/api/conversas/funil/parados?{_periodo()}&etapa=chegou")
        _garante(r.status_code == 403, f"{quem} nos parados → {r.status_code}")
    casos = (
        ("inicio=2026-13-01&fim=2026-12-01", "inicio"),
        ("inicio=2026-11-10&fim=2026-11-01", "inicio"),
        ("inicio=2024-01-01&fim=2026-01-01", "inicio"),
        (f"{_periodo()}&dividir=signo", "dividir"),
        (f"{_periodo()}&canal=telegram", "canal"),
    )
    for query, campo in casos:
        r = _chamar(estado["ana"], f"/api/conversas/funil?{query}")
        corpo = r.get_json() or {}
        _garante(
            r.status_code == 422 and campo in ((corpo.get("error") or {}).get("fields") or {}),
            f"{query} → {r.status_code} {corpo}",
        )
    r = _chamar(estado["ana"], f"/api/conversas/funil/parados?{_periodo()}&etapa=sonho")
    _garante(
        r.status_code == 422 and "etapa" in ((r.get_json().get("error") or {}).get("fields") or {}),
        f"etapa → {r.status_code}",
    )


def preparar() -> None:
    estado["ana"], estado["ana_id"] = _usuario("Ana", RoleName.COMERCIAL)
    estado["bia"], estado["bia_id"] = _usuario("Bia", RoleName.COMERCIAL)
    estado["fin"], estado["fin_id"] = _usuario("Fin", RoleName.FINANCEIRO)
    estado["cast"], estado["cast_id"] = _usuario("Cast", RoleName.CASTING)


def limpar() -> None:
    db.session.rollback()
    eventos = "SELECT id FROM calendar_events WHERE google_event_id LIKE :p"
    db.session.execute(
        text("DELETE FROM pix_recebidos WHERE message_id LIKE :p"), {"p": f"{PREFIX}%"}
    )
    for tabela in ("client_feedbacks", "event_payments", "event_clients"):
        db.session.execute(
            text(f"DELETE FROM {tabela} WHERE event_id IN ({eventos})"), {"p": f"{PREFIX}%"}
        )
    db.session.execute(
        text("UPDATE calendar_events SET group_leader_id = NULL WHERE google_event_id LIKE :p"),
        {"p": f"{PREFIX}%"},
    )
    db.session.execute(
        text("DELETE FROM calendar_events WHERE google_event_id LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text("DELETE FROM form_responses WHERE contact_name LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(text("DELETE FROM conversas WHERE contato_id = ANY(:c)"), {"c": CONTATOS})
    db.session.execute(
        text("DELETE FROM orcamento_history WHERE client_name LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text("DELETE FROM anuncios_meta WHERE anuncio_id LIKE :p"), {"p": f"{PREFIX}%"}
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
        "(SELECT count(*) FROM calendar_events WHERE google_event_id LIKE :p) + "
        "(SELECT count(*) FROM form_responses WHERE contact_name LIKE :p)",
        c=CONTATOS,
        t=TELEFONES,
        p=f"{PREFIX}%",
    )[0]
    _garante(sobras == 0, f"sobraram {sobras} registros de teste")


CENARIOS = [
    ("1. a ficha com todos os marcos, em ordem e com os links", cen_01),
    ("2. o evento cancelado some da linha do tempo", cen_02),
    ("3. Financeiro sem os links de conversa e orçamento; Casting 403 (DEVE falhar)", cen_03),
    ("4. o funil: contagens e porcentagens", cen_04),
    ("5. fora do período, fato antigo, cancelado e conversa sem mensagem dela", cen_05),
    ("6. filtros de canal e campanha; divisão por vendedor, campanha e canal", cen_06),
    ("7. quem parou em cada etapa", cen_07),
    ("8. Financeiro e Casting no funil; período e filtros inválidos (DEVE falhar)", cen_08),
]


def main() -> int:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        limpar()
        preparar()
    print("Feature 335 — Linha do tempo da ficha e funil das conversas, contra manto_local")
    try:
        try:
            estado["antes"] = _quantidades(_funil(estado["ana"]))
            estado["antes_ig"] = _quantidades(_funil(estado["ana"], "&canal=instagram"))
            estado["antes_sem"] = _quantidades(_funil(estado["ana"], "&campanha=__sem_anuncio__"))
        except AssertionError as exc:
            print(f"  (leitura de antes falhou: {exc})")
            zero = {
                k: 0 for k in ("chegou", "orcamento", "formulario", "evento", "pagou", "avaliou")
            }
            estado["antes"] = estado["antes_ig"] = estado["antes_sem"] = zero
        with app.app_context():
            semear()
        for nome, fn in CENARIOS:
            cenario(nome, fn)
    finally:
        with app.app_context():
            cenario("9. limpeza", limpar)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK · escapes de rede: {len(_ESCAPES)}")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) and not _ESCAPES else 1


if __name__ == "__main__":
    sys.exit(main())
