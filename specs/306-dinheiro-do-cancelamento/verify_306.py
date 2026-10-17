"""Verificação da feature 306 — o dinheiro do cancelamento.

A tabela de cenários está na `spec.md` (seção "Verificação", 59 cenários: os 57 do plano mais 37b e
38c). Escrito ANTES do núcleo (Princípio VIII): a primeira rodada fica em
`verify_306_primeira_falha.txt`. Os blocos acompanham as fases do `tasks.md`:

  B0  Fundação     1, 23, 26 e a regressão do 41; com `--nucleo`, a variante 16b cheia 0.
  B1  História 1   7–14b, 17, 30 (no `--nucleo`, semeando o congelado por ORM).
  B2  História 2   2–6, 15, 16, 18, 19, 25, 28, 31, 32, 34, 36 (e o resto da B1 pela API).
  B3  História 3   20, 21, 22, 24.
  B4  História 4   16b, 16c, 16d, 16e.
  B5  História 5   29, 35, 37, 37b, 38, 38c, 39, 41, 42, 42b, 42c, 42d e as partes de grupo.
  B6  História 6   33, 40, 42e, 43, 44, 45, 45b, 45c.
  B9  limpeza      27 (roda sempre).

O GOOGLE É UM DUBLÊ QUE FALHA FECHADO (o da 303): `service.build` e `service.load_credentials` são
trocados, todo id desconhecido responde 503 e um disjuntor recusa qualquer conexão que não seja
local. O e-mail sai por um `_send` falso e o `send_removal_email` tem espião. O `manto_local` traz o
token REAL da agenda e as credenciais REAIS de e-mail: nenhum cenário fala com o mundo.

EVENTOS DE TESTE: os de dinheiro nascem pelo ORM em meses isolados (2047 a 2049, longe da faixa do
`verify_303`), com `google_event_id` prefixado `v306-` e registrados no dublê; os que precisam de
elenco nascem pelo caminho real (`sync_events`), que cria Coordenador, personagens do título e, no
SHOW, as vagas de som. O talento descartável entra em vaga que o SISTEMA criou — nunca `EventRole`
inventada — e o técnico de som pré-atribuído a um talento real é solto nos eventos do verify.

ESCRITA SE CONFERE POR CONEXÃO SEPARADA (`_no_banco`): o autoflush da sessão do app mostra o que
ainda não foi commitado (hotfix 257). Requisições HTTP ficam FORA de `app.app_context()`. Login só
por `POST /api/auth/login`.

O BACKEND LOCAL TEM DE ESTAR PARADO: a thread de sync falaria com o Google real. Se
`calendar_auto_sync_at` for recente, o verify sai com código 2.

Rodar contra o manto_local (PowerShell, na raiz do worktree; quickstart, Pré-requisitos)::

    $py specs\\306-dinheiro-do-cancelamento\\verify_306.py              # o portão: 59/59 OK
    $py specs\\306-dinheiro-do-cancelamento\\verify_306.py --so=2,2b,8  # iteração (o 27 roda sempre)
    $py specs\\306-dinheiro-do-cancelamento\\verify_306.py --nucleo     # Fundação e História 1
    $py specs\\306-dinheiro-do-cancelamento\\verify_306.py --regressao  # + os verifies antigos
    $py specs\\306-dinheiro-do-cancelamento\\verify_306.py --semear-tela / --limpar-tela

`--regressao` roda os verifies antigos do quickstart §5 em subprocesso, ANTES de semear qualquer
coisa (o `verify_303` recusa rodar com evento marcado de outro verify no banco), e compara com a
base gravada na primeira rodada (`verify_306_regressao_base.json`).

Saída: 0 = tudo OK; 1 = algum cenário falhou; 2 = ambiente impróprio.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import traceback
import uuid
from collections.abc import Callable, Iterator
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
REPO_ROOT = AQUI.parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")  # cinto, além do `_send` falso
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

import httplib2  # noqa: E402
from googleapiclient.errors import HttpError  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter, maps  # noqa: E402
from app import email_service as es  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.formularios import formularios_ops  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    CommissionPayment,
    EventAcrescimo,
    EventPayment,
    EventRole,
    Role,
    SiteSetting,
    SpecialExpense,
    Talent,
    User,
)

# ── nomes fixados no contrato (o verify depende deles) ─────────────────────────────────────────
PREFIX = "__v306_"
GID = "v306"
SENHA = "verify-306-senha"
PIX = "verify306-pix@exemplo.test"
MARCADOR = "[TESTE verify 306] pode apagar"
CENTAVO = Decimal("0.01")
TRAVA = "CALENDAR_SUPPRESS_EVENT_WRITES"
CATEGORIA_DEVOLUCAO = "Devolução a cliente"
CATEGORIA_MULTA = "Multa de cancelamento"
FAIXA_ISOLADA = (datetime(2047, 1, 1), datetime(2050, 1, 1))
FAIXA_ISOLADA_MES = "2047-01"  # month_ref de folha e fixos gerados pela Planilha dos meses isolados
ROTAS = {
    "cancelar": "/api/events/{id}/cancelar",
    "impacto": "/api/events/{id}/impacto-exclusao",
    "devolucao": "/api/events/{id}/devolucao",
    "multas": "/api/events/{id}/multas",
    "detalhe": "/api/events/{id}",
    "excluir": "/api/events/{id}",
    "comercial": "/api/events/{id}/comercial",
    "acrescimos": "/api/events/{id}/acrescimos",
    "orcamento": "/api/events/{id}/orcamento",
    "comprovante": "/api/events/{id}/payments",
    "comprovante_um": "/api/payments/{id}",
    "reembolso": "/api/events/{id}/reimbursements",
    "parcelas": "/api/events/{id}/parcelas",
    "notas": "/api/events/{id}/invoices",
    "grupo": "/api/events/{id}/grupo",
    "sync": "/api/events/{id}/sync",
    "cancelamentos": "/api/events/cancelamentos",
    "gastos": "/api/gastos",
    "gasto": "/api/gastos/{id}",
    "gasto_aprovar": "/api/gastos/{id}/aprovar",
    "gasto_rejeitar": "/api/gastos/{id}/rejeitar",
    "gasto_vincular": "/api/gastos/{id}/vincular-evento",
    "planilha": "/api/financeiro/pagamentos?month={m}",
    "planilha_status": "/api/financeiro/pagamentos/set-status",
    "comissoes": "/api/financeiro/comissoes?month={m}&seller_id={s}",
    "dre": "/api/financeiro/dashboard?period=custom&start={a}&end={b}",
    "pipeline": "/api/vendas/pipeline?period=custom&start={a}&end={b}",
    "desempenho": "/api/admin/desempenho?month={m}",
    "dre_jinja": "/financeiro/?period=custom&start={a}&end={b}",
    "vendas_jinja": "/vendas/?period=custom&start={a}&end={b}",
    "cliente": "/api/clientes/{id}",
    "home": "/api/dashboard",
    "impersonate": "/api/auth/impersonate",
}

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False  # muitos logins: o "10 per minute" estoura

_externo = create_engine(os.environ["DATABASE_URL"], future=True)
INICIO_UTC = datetime.utcnow()

resultados: list[tuple[str, str, str, str]] = []  # (bloco, nome, estado, detalhe)
estado: dict = {"eventos": {}, "talentos": [], "usuarios": {}, "clientes": [], "orcamentos": []}
OPCOES: dict = {"so": None, "nucleo": False}


class Bloqueado(Exception):
    """O cenário depende de algo que só existe numa fase posterior."""


# ── disjuntor de rede: nada sai desta máquina ──────────────────────────────────────────────────
rede_bloqueada: list[str] = []
_LOCAIS = {"127.0.0.1", "::1", "localhost"}
_connect_real = socket.socket.connect
_connect_ex_real = socket.socket.connect_ex


def _host(endereco) -> str:
    return str(endereco[0]) if isinstance(endereco, tuple) else str(endereco)


def _connect_vigiado(self, endereco):
    if self.family in (socket.AF_INET, socket.AF_INET6) and _host(endereco) not in _LOCAIS:
        rede_bloqueada.append(_host(endereco))
        raise OSError(f"verify_306: conexão externa bloqueada ({_host(endereco)})")
    return _connect_real(self, endereco)


def _connect_ex_vigiado(self, endereco):
    if self.family in (socket.AF_INET, socket.AF_INET6) and _host(endereco) not in _LOCAIS:
        rede_bloqueada.append(_host(endereco))
        return 111  # ECONNREFUSED
    return _connect_ex_real(self, endereco)


socket.socket.connect = _connect_vigiado
socket.socket.connect_ex = _connect_ex_vigiado


# ── o dublê do Google (o da 303, enxuto) ───────────────────────────────────────────────────────
def _http(status: int) -> HttpError:
    return HttpError(
        httplib2.Response({"status": str(status)}), b'{"error": {"message": "duble 306"}}'
    )


class _CredFalsa:
    valid = True
    expired = False
    token = "verify-306"


class _Pedido:
    def __init__(self, fn: Callable[[], object]):
        self._fn = fn

    def execute(self, **_kw):
        return self._fn()


class _Eventos:
    def __init__(self, g: GoogleFalso):
        self.g = g

    def list(self, **kw):
        return _Pedido(lambda: self.g._list(kw))

    def list_next(self, *_a, **_k):
        return None

    def get(self, calendarId=None, eventId=None, **_kw):  # noqa: N803 — nomes da API do Google
        return _Pedido(lambda: self.g._get(eventId))

    def insert(self, calendarId=None, body=None, **_kw):  # noqa: N803
        return _Pedido(lambda: self.g._insert(body or {}))

    def patch(self, calendarId=None, eventId=None, body=None, **_kw):  # noqa: N803
        return _Pedido(lambda: self.g._patch(eventId, body or {}))

    def update(self, calendarId=None, eventId=None, body=None, **_kw):  # noqa: N803
        return _Pedido(lambda: self.g._patch(eventId, body or {}))

    def delete(self, calendarId=None, eventId=None, **_kw):  # noqa: N803
        return _Pedido(lambda: self.g._delete(eventId))


class _Servico:
    def __init__(self, g: GoogleFalso):
        self.g = g

    def events(self):
        return _Eventos(self.g)


class GoogleFalso:
    """Agenda falsa que falha fechado: só responde a id que ela conhece."""

    def __init__(self) -> None:
        self.itens: dict[str, dict] = {}
        self.apagados: set[str] = set()
        self.chamadas: list[tuple[str, str | None]] = []
        self.falhar_delete: set[str] = set()

    def build(self, *_a, **_k) -> _Servico:
        return _Servico(self)

    def load_credentials(self):
        self.chamadas.append(("credencial", None))
        return _CredFalsa()

    def registrar(self, item: dict) -> None:
        self.itens[item["id"]] = item

    def marco(self) -> int:
        return len(self.chamadas)

    def deletes(self, desde: int = 0) -> list[str]:
        return [alvo for verbo, alvo in self.chamadas[desde:] if verbo == "delete"]

    def _list(self, kw: dict) -> dict:
        self.chamadas.append(("list", kw.get("timeMin")))
        raise _http(503)  # nenhum cenário lista meses: falha fechado

    def _get(self, gid: str):
        self.chamadas.append(("get", gid))
        if gid not in self.itens:
            raise _http(503)
        if gid in self.apagados:
            raise _http(404)
        return copy.deepcopy(self.itens[gid])

    def _insert(self, body: dict) -> dict:
        self.chamadas.append(("insert", body.get("summary")))
        gid = f"{GID}g-{uuid.uuid4().hex[:10]}"
        item = {**copy.deepcopy(body), "id": gid, "status": "confirmed"}
        self.registrar(item)
        return copy.deepcopy(item)

    def _patch(self, gid: str, body: dict) -> dict:
        self.chamadas.append(("patch", gid))
        if gid not in self.itens:
            raise _http(503)
        self.itens[gid].update(copy.deepcopy(body))
        return copy.deepcopy(self.itens[gid])

    def _delete(self, gid: str) -> str:
        self.chamadas.append(("delete", gid))
        # "Depois do commit" (FR-065): pela conexão separada, o show já está cancelado e o ensaio já
        # saiu do banco no instante da remoção.
        with contextlib.suppress(Exception):
            linha = _no_banco("SELECT cancelled_at FROM calendar_events WHERE google_event_id = :g", g=gid)
            _commit_antes_do_google.append(not linha or linha[0][0] is not None)
        if gid in self.falhar_delete:
            raise _http(500)
        if gid not in self.itens:
            raise _http(503)
        self.apagados.add(gid)
        return ""


_commit_antes_do_google: list[bool] = []
google = GoogleFalso()
cal_service.build = google.build
cal_service.load_credentials = google.load_credentials
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: None
cal_routes._lookup_sp_status = lambda _loc: False
# `sync_events` termina em `_mark_talents_worked`, que liga `worked_before` em talento real do espelho.
cal_routes._mark_talents_worked = lambda *a, **k: None
formularios_ops.retry_auto_link_pending = lambda: 0


def _item_google(gid: str, titulo: str, inicio: datetime, fim: datetime) -> dict:
    """Item do Google como a API devolve — SEM `created` (senão a guarda da 254 o pularia)."""
    return {
        "id": gid,
        "status": "confirmed",
        "summary": titulo,
        "location": "Rua V306, 1",
        "description": MARCADOR,
        "start": {"dateTime": inicio.strftime("%Y-%m-%dT%H:%M:%S") + "-03:00"},
        "end": {"dateTime": fim.strftime("%Y-%m-%dT%H:%M:%S") + "-03:00"},
        "htmlLink": f"https://calendar.google.com/v306/{gid}",
    }


# ── e-mail e espiões ───────────────────────────────────────────────────────────────────────────
_emails: list[dict] = []
_remocoes: list[dict] = []


def _send_falso(to: str, subject: str = "", body: str = "", html: str = "") -> bool:
    _emails.append({"to": to, "subject": subject})
    return True


es._send = _send_falso
_send_removal_real = getattr(es, "send_removal_email", None)


def _espiao_remocao(*args, **kwargs):
    """Conta cada e-mail de remoção (o `_send` falso já impede o envio de verdade)."""
    _remocoes.append({"args": args, "kwargs": kwargs})
    if _send_removal_real is not None:
        return _send_removal_real(*args, **kwargs)
    return True


es.send_removal_email = _espiao_remocao


def _instalar_espiao_de_remocao() -> None:
    """`casting_ops` e `calendar/routes` importam `send_removal_email` pelo nome: trocar só o atributo
    de `email_service` não alcança essas chamadas. Varre todo módulo do app já carregado (o núcleo
    novo inclusive) e troca o nome onde ele ainda aponta para o original. Roda antes de cada cenário."""
    for nome, mod in list(sys.modules.items()):
        if mod is None or not (nome == "app" or nome.startswith("app.")):
            continue
        if getattr(mod, "send_removal_email", None) is _send_removal_real:
            mod.send_removal_email = _espiao_remocao
_ao_cancelar: list[tuple[int, str, int | None]] = []
_ao_cancelar_estado: list[dict] = []


def _instalar_espiao_ao_cancelar() -> None:
    """Espião do ponto da 2a (`cancel_ops.ao_cancelar`), se ele já existir (nasce na H2)."""
    from app.calendar import cancel_ops

    real = getattr(cancel_ops, "ao_cancelar", None)
    if real is None or getattr(real, "_espiao_306", False):
        return

    def espiao(event, *, alcance, novo_principal=None):
        _ao_cancelar.append(
            (event.id, alcance, getattr(novo_principal, "id", novo_principal))
        )
        # O estado no instante da chamada, pela própria sessão: na passagem, o ponto da 2a só
        # pode ser chamado depois de `passar_venda` (a venda e as linhas já no novo principal).
        novo = novo_principal if hasattr(novo_principal, "id") else None
        _ao_cancelar_estado.append({
            "evento": event.id,
            "venda_do_evento": event.sale_value,
            "venda_do_novo": getattr(novo, "sale_value", None),
            "linhas_no_evento": CommissionPayment.query.filter_by(event_id=event.id).count(),
        })
        return real(event, alcance=alcance, novo_principal=novo_principal)

    espiao._espiao_306 = True
    cancel_ops.ao_cancelar = espiao


def _esperar_threads() -> None:
    """E-mail sai por thread (`send_async`): esperar antes de afirmar."""
    for t in threading.enumerate():
        if t is not threading.main_thread() and t.is_alive():
            t.join(timeout=20)


# ── harness ────────────────────────────────────────────────────────────────────────────────────
def q(x) -> Decimal:
    return Decimal(str(x)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _no_banco(sql: str, **params):
    """Conexão separada — a única testemunha confiável de que algo foi commitado."""
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _no_banco_escrever(sql: str, **params) -> None:
    with _externo.begin() as conn:
        conn.execute(text(sql), params)


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _igual(obtido, esperado, msg: str) -> None:
    """Compara dinheiro ao centavo (aceita float, Decimal ou texto)."""
    if esperado is None or obtido is None:
        _garante(obtido == esperado, f"{msg}: esperado {esperado}, veio {obtido}")
        return
    _garante(q(obtido) == q(esperado), f"{msg}: esperado {q(esperado)}, veio {q(obtido)}")


def _deve_quebrar(fn: Callable[[], None], rotulo: str) -> None:
    """Prova por mutação: com a regra errada ligada, o cenário TEM de falhar."""
    try:
        fn()
    except AssertionError:
        return
    raise AssertionError(f"mutação '{rotulo}' passou despercebida — o cenário não protege a regra")


def _selecionado(num: str) -> bool:
    return OPCOES["so"] is None or num in OPCOES["so"] or num == "27"


def cenario(bloco: str, num: str, nome: str, fn: Callable[[], None]) -> None:
    """Roda um cenário; registra OK, FALHA ou BLOQUEADO e segue."""
    if not _selecionado(num):
        return
    rotulo = f"{num} · {nome}"
    marco_google = google.marco()
    _instalar_espiao_de_remocao()
    # No manto_local a trava nasce ligada (banco local): o dublê é o Google, então ela começa
    # desligada em todo cenário — só o 31 e o 43 a ligam de propósito.
    app.config[TRAVA] = False
    try:
        fn()
        resultados.append((bloco, rotulo, "OK", ""))
        print(f"  OK         {rotulo}")
    except Bloqueado as exc:
        resultados.append((bloco, rotulo, "BLOQUEADO", str(exc)))
        print(f"  BLOQUEADO  {rotulo}: {exc}")
    except Exception as exc:  # noqa: BLE001 — harness: registra e segue
        ultima = traceback.format_exc().strip().splitlines()[-1]
        resultados.append((bloco, rotulo, "FALHA", ultima))
        print(f"  FALHA      {rotulo}: {str(exc)[:500]}")
    finally:
        with app.app_context():
            db.session.rollback()
        # Taxa padrão e EducaManto mexidos por um cenário (11, 16b, 16e, 42c) voltam já aqui, com
        # o resync: o seguinte não pode ressincronizar o espelho com a configuração do verify.
        _restaurar_config()
        google.falhar_delete.clear()
        app.config[TRAVA] = False  # o dublê é o Google: a trava só liga no cenário 31
        estado.setdefault("chamadas_google", []).append((rotulo, google.chamadas[marco_google:]))


@contextlib.contextmanager
def _com_hoje(dia: date) -> Iterator[None]:
    """Fixa o "hoje" de São Paulo em todo módulo do app que tem `now_sp`."""
    import app.constants as constantes

    real = constantes.now_sp
    hora = datetime.combine(dia, datetime.min.time()).replace(hour=11)

    def falso():
        return hora

    for nome, mod in list(sys.modules.items()):
        if (nome == "app" or nome.startswith("app.")) and getattr(mod, "now_sp", None) is real:
            mod.now_sp = falso
    try:
        yield
    finally:
        # Todo módulo com o falso volta ao real — também o importado pela primeira vez DENTRO da
        # janela com `from app.constants import now_sp` (ele copiou o falso já trocado).
        for nome, mod in list(sys.modules.items()):
            if (nome == "app" or nome.startswith("app.")) and getattr(mod, "now_sp", None) is falso:
                mod.now_sp = real


def _hoje_sp() -> date:
    from app.constants import now_sp

    return now_sp().date()


def _mes(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _mes_seguinte(d: date) -> date:
    return date(d.year + (d.month // 12), d.month % 12 + 1, 1)


def _mes_anterior(d: date) -> date:
    return date(d.year - (1 if d.month == 1 else 0), 12 if d.month == 1 else d.month - 1, 1)


_PROXIMO_DIA = [datetime(2047, 1, 5)]


def _data_isolada_no_mes(*, dias: int = 3, folga: int = 4) -> datetime:
    """Um dia isolado com `folga` dias do mesmo mês à frente (o grupo do 42 fica num mês só)."""
    d = _data_isolada(dias=dias)
    while (d + timedelta(days=folga)).month != d.month:
        d = _data_isolada(dias=dias)
    return d


def _data_isolada(*, dias: int = 3) -> datetime:
    """Um dia só do cenário, nos meses isolados (2047+), com folga entre um e outro."""
    atual = _PROXIMO_DIA[0]
    _PROXIMO_DIA[0] = atual + timedelta(days=dias)
    return atual.replace(hour=19)


# ── pessoas ────────────────────────────────────────────────────────────────────────────────────
def _usuario(apelido: str, *papeis: str, comissiona: bool = True) -> dict:
    email = f"{PREFIX}{apelido}@manto.local"
    with app.app_context():
        user = User(
            name=f"{PREFIX}{apelido}",
            email=email,
            is_active=True,
            has_access=True,
            receives_commission=comissiona,
        )
        user.set_password(SENHA)
        for p in papeis:
            user.roles.append(Role.query.filter_by(name=p).one())
        db.session.add(user)
        db.session.commit()
        info = {"id": user.id, "email": email}
    estado["usuarios"][apelido] = info
    return info


def _talento(sufixo: str, *, pix: str | None = PIX) -> int:
    with app.app_context():
        t = Talent(
            full_name=f"{PREFIX}{sufixo}",
            artistic_name=f"{PREFIX}{sufixo}",
            email_contact=f"{PREFIX}{sufixo}@manto.local",
            status="active",
            must_change_password=False,
            terms_accepted_at=datetime.utcnow(),
            pix_key=pix,
        )
        t.set_password(SENHA)
        db.session.add(t)
        db.session.commit()
        estado["talentos"].append(t.id)
        return t.id


def _cliente(apelido: str):
    """Sessão logada pela API, como o navegador."""
    info = estado["usuarios"][apelido]
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": info["email"], "password": SENHA})
    _garante(r.status_code == 200, f"login de {apelido} → {r.status_code}")
    return c


def _erro(r) -> dict:
    return (r.get_json(silent=True) or {}).get("error") or {}


def _codigo(r) -> str | None:
    return _erro(r).get("codigo")


# ── eventos ────────────────────────────────────────────────────────────────────────────────────
def _evento(
    rotulo: str,
    *,
    venda: float | None = 2000,
    taxa: float | None = 5,
    bruto: float | None = None,
    vendedor: str | None = "vend",
    inicio: datetime | None = None,
    tipo: str = "CORP",
    nota: bool = False,
    cortesia: bool = False,
    titulo: str | None = None,
    venda_em: date | None = None,
) -> int:
    """Evento de dinheiro, pelo ORM, num dia isolado (ou no `inicio` dado)."""
    inicio = inicio or _data_isolada()
    gid = f"{GID}-{uuid.uuid4().hex[:10]}"
    titulo = titulo or f"({tipo}) V306 {rotulo.upper()}"
    google.registrar(_item_google(gid, titulo, inicio, inicio + timedelta(hours=3)))
    with app.app_context():
        ev = CalendarEvent(
            title=titulo,
            event_type=tipo,
            start_at=inicio,
            end_at=inicio + timedelta(hours=3),
            google_event_id=gid,
            source="google_calendar",
            location="Rua V306, 1",
            description=MARCADOR,
            sale_value=Decimal(str(venda)) if venda is not None else None,
            sale_value_gross=Decimal(str(bruto if bruto is not None else venda))
            if venda is not None
            else None,
            with_invoice=nota,
            is_cortesia_permuta=cortesia,
            commission_rate=taxa,
            seller_id=estado["usuarios"][vendedor]["id"] if vendedor else None,
            sale_date=venda_em or _hoje_sp() if venda is not None else None,
        )
        db.session.add(ev)
        db.session.commit()
        estado["eventos"][ev.id] = gid
        return ev.id


def _evento_com_elenco(
    rotulo: str, personagens: list[str], *, inicio: datetime | None = None, tipo: str = "SHOW"
) -> int:
    """Evento pelo caminho real (`sync_events`): as vagas nascem do sistema."""
    inicio = inicio or _data_isolada()
    gid = f"{GID}-{uuid.uuid4().hex[:10]}"
    nomes = " + ".join(f"V306 {p.upper()}" for p in personagens)
    titulo = f"({tipo}) {nomes}"
    item = _item_google(gid, titulo, inicio, inicio + timedelta(hours=3))
    google.registrar(item)
    with app.app_context():
        cal_routes.sync_events([item])
        ev = CalendarEvent.query.filter_by(google_event_id=gid).one()
        # O técnico de som do SHOW nasce atribuído a um talento real: solto no evento do verify.
        for r in EventRole.query.filter(
            EventRole.event_id == ev.id, EventRole.talent_id.isnot(None)
        ).all():
            r.talent_id = None
        db.session.commit()
        estado["eventos"][ev.id] = gid
        return ev.id


def _escalar(
    event_id: int, talento_id: int, *, vaga: str | None = None, convite: str = "accepted"
) -> int:
    """Preenche uma vaga que o SISTEMA criou. Nunca cria `EventRole`."""
    with app.app_context():
        q_ = EventRole.query.filter(
            EventRole.event_id == event_id, EventRole.talent_id.is_(None)
        )
        q_ = (
            q_.filter(EventRole.character_name == vaga)
            if vaga
            else q_.filter(EventRole.role_type != "extra")
        )
        role = q_.order_by(EventRole.id).first()
        _garante(role is not None, f"evento {event_id} sem vaga livre ({vaga or 'personagem'})")
        role.talent_id = talento_id
        role.invite_status = convite
        role.assigned_at = datetime.utcnow()
        role.cache_value = Decimal("300")
        db.session.commit()
        return role.id


def _comprovante(event_id: int, valor: float | None) -> int:
    with app.app_context():
        p = EventPayment(
            event_id=event_id,
            file_path=f"{PREFIX}comprovante.pdf",
            amount=Decimal(str(valor)) if valor is not None else None,
        )
        db.session.add(p)
        db.session.commit()
        return p.id


def _bv(
    event_id: int,
    valor: float = 200,
    *,
    status: str = "nao_pago",
    recebedor: str | None = f"{PREFIX}Parceiro",
    pix: str | None = PIX,
) -> int:
    with app.app_context():
        a = EventAcrescimo(
            event_id=event_id,
            tipo="BV",
            descricao=None,
            is_percent=False,
            value=Decimal(str(valor)),
            amount_brl=Decimal(str(valor)),
            is_bv=True,
            bv_recipient=recebedor,
            bv_pix=pix,
            bv_payment_status=status,
        )
        db.session.add(a)
        db.session.commit()
        return a.id


def _acrescimo(event_id: int, tipo: str, valor: float) -> int:
    with app.app_context():
        a = EventAcrescimo(
            event_id=event_id,
            tipo=tipo,
            is_percent=False,
            value=Decimal(str(valor)),
            amount_brl=Decimal(str(valor)),
            is_bv=False,
        )
        db.session.add(a)
        db.session.commit()
        return a.id


def _linha_comissao(
    event_id: int | None,
    valor: float,
    *,
    status: str = "a_pagar",
    vendedor: str = "vend",
    venda_em: date | None = None,
    liberacao: date | None = None,
    original_id: int | None = None,
    nota: str | None = None,
) -> int:
    with app.app_context():
        ev = db.session.get(CalendarEvent, event_id) if event_id else None
        cp = CommissionPayment(
            event_id=event_id,
            event_title=ev.title if ev else f"{PREFIX}órfão",
            seller_id=estado["usuarios"][vendedor]["id"],
            sale_date=venda_em or _hoje_sp(),
            payable_from=liberacao,
            amount=Decimal(str(valor)),
            status=status,
            paid_at=datetime.utcnow() if status in ("pago", "no_banco") else None,
            original_id=original_id,
            notes=nota,
        )
        db.session.add(cp)
        db.session.commit()
        return cp.id


def _sincronizar_comissao(event_id: int) -> None:
    """A comissão do evento vivo pela regra de hoje (o mesmo gancho das escritas)."""
    from app.financeiro import comissoes_ops

    with app.app_context():
        comissoes_ops._sync_commission_payment(db.session.get(CalendarEvent, event_id))
        db.session.commit()


def _devolucao_avulsa(
    event_id: int, valor: float, *, status: str = "aprovado", pagamento: str = "nao_pago"
) -> int:
    """Devolução lançada à mão em Gastos Extras (pendente ou aprovada), sem passar pelo ato."""
    with app.app_context():
        sa = estado["usuarios"]["sa"]["id"]
        g = SpecialExpense(
            description=f"{PREFIX}devolução avulsa",
            category=CATEGORIA_DEVOLUCAO,
            amount=Decimal(str(valor)),
            expense_date=_hoje_sp(),
            status=status,
            created_by_id=sa,
            approved_by_id=sa if status == "aprovado" else None,
            approved_at=datetime.utcnow() if status == "aprovado" else None,
            disbursement_type="cliente",
            supplier_name=f"{PREFIX}Cliente",
            supplier_pix=PIX,
            payment_status=pagamento,
            paid_at_creation=False,
            event_id=event_id,
        )
        db.session.add(g)
        db.session.commit()
        return g.id


def _gasto_comum(event_id: int | None, valor: float, *, categoria: str = "Outros") -> int:
    with app.app_context():
        sa = estado["usuarios"]["sa"]["id"]
        g = SpecialExpense(
            description=f"{PREFIX}gasto comum",
            category=categoria,
            amount=Decimal(str(valor)),
            expense_date=_hoje_sp(),
            status="aprovado",
            created_by_id=sa,
            approved_by_id=sa,
            approved_at=datetime.utcnow(),
            disbursement_type="fornecedor",
            supplier_name=f"{PREFIX}Fornecedor",
            supplier_pix=PIX,
            payment_status="nao_pago",
            paid_at_creation=False,
            event_id=event_id,
        )
        db.session.add(g)
        db.session.commit()
        return g.id


def _agrupar(principal_id: int, *satelites: int) -> None:
    with app.app_context():
        for s in satelites:
            db.session.get(CalendarEvent, s).group_leader_id = principal_id
        db.session.commit()


def _marcar_sumido(event_id: int) -> None:
    """Marca "Sumiu do Google Agenda" (303) direto: o ciclo da 303 não é o assunto aqui."""
    _no_banco_escrever(
        "UPDATE calendar_events SET google_missing_since = :t WHERE id = :i",
        t=datetime.utcnow(),
        i=event_id,
    )


# ── leituras ───────────────────────────────────────────────────────────────────────────────────
def _linhas_comissao(event_id: int, *, vivas: bool = True) -> list[dict]:
    sql = (
        "SELECT id, seller_id, amount, status, sale_date, payable_from, original_id, notes "
        "FROM commission_payments WHERE event_id = :i"
    )
    if vivas:
        sql += " AND status <> 'cancelado'"
    chaves = ("id", "seller", "valor", "status", "venda_em", "liberacao", "original_id", "nota")
    return [dict(zip(chaves, r, strict=True)) for r in _no_banco(sql + " ORDER BY id", i=event_id)]


def _soma_vivas(event_id: int, vendedor: str | None = None) -> Decimal:
    linhas = _linhas_comissao(event_id)
    if vendedor:
        linhas = [x for x in linhas if x["seller"] == estado["usuarios"][vendedor]["id"]]
    return sum((Decimal(x["valor"]) for x in linhas), Decimal("0"))


def _cancelamento(event_id: int) -> dict | None:
    linhas = _no_banco(
        "SELECT regime, refund_mode, sale_value, commission_full, commission_rate, "
        "commission_seller_id, seller_id, with_invoice, retained_tax, group_leader_id, "
        "sale_handed_over, sale_value_before, sale_value_after, sale_value_gross_before, "
        "sale_value_gross_after FROM event_cancellations WHERE event_id = :i",
        i=event_id,
    )
    if not linhas:
        return None
    chaves = (
        "regime", "modo", "venda", "cheia", "taxa", "beneficiario", "vendedor", "nota",
        "imposto", "principal", "passou", "venda_antes", "venda_depois", "cheio_antes",
        "cheio_depois",
    )  # fmt: skip
    return dict(zip(chaves, linhas[0], strict=True))


def _devolucoes(event_id: int) -> list[dict]:
    rows = _no_banco(
        "SELECT id, amount, status, payment_status, disbursement_type, supplier_name, "
        "supplier_pix, expense_date FROM special_expenses WHERE event_id = :i AND category = :c "
        "ORDER BY id",
        i=event_id,
        c=CATEGORIA_DEVOLUCAO,
    )
    chaves = ("id", "valor", "status", "pagamento", "tipo", "nome", "pix", "data")
    return [dict(zip(chaves, r, strict=True)) for r in rows]


def _historico(event_id: int) -> list[tuple[str, datetime]]:
    return [
        (r[0], r[1])
        for r in _no_banco(
            "SELECT message, created_at FROM event_logs WHERE event_id = :i ORDER BY id",
            i=event_id,
        )
    ]


def _cancelado_em(event_id: int):
    return _no_banco("SELECT cancelled_at FROM calendar_events WHERE id = :i", i=event_id)[0][0]


def _detalhe(apelido: str, event_id: int) -> dict:
    r = _cliente(apelido).get(ROTAS["detalhe"].format(id=event_id))
    _garante(r.status_code == 200, f"GET do evento {event_id} → {r.status_code}")
    return r.get_json()


def _resumo_api(event_id: int, apelido: str = "sa") -> dict:
    corpo = _detalhe(apelido, event_id)
    resumo = (corpo.get("event") or {}).get("cancelamento")
    _garante(resumo is not None, f"evento {event_id} sem `event.cancelamento` no detalhe")
    return resumo


def _retrato_tabelas(event_ids: list[int]) -> dict:
    """Retrato das tabelas que o ato toca (para a prévia que não grava e a passagem)."""
    ids = list(event_ids) or [0]
    consultas = {
        "comissoes": "SELECT id, event_id, seller_id, amount, status, sale_date, payable_from, "
        "original_id, notes FROM commission_payments WHERE event_id = ANY(:ids) OR seller_id IN "
        "(SELECT seller_id FROM commission_payments WHERE event_id = ANY(:ids)) ORDER BY id",
        "gastos": "SELECT id, event_id, amount, status, payment_status, category FROM "
        "special_expenses WHERE event_id = ANY(:ids) ORDER BY id",
        "eventos": "SELECT id, cancelled_at, sale_value, sale_value_gross, group_leader_id, "
        "google_missing_since FROM calendar_events WHERE id = ANY(:ids) ORDER BY id",
        "acrescimos": "SELECT id, event_id, amount_brl, bv_payment_status, bv_recipient, bv_pix "
        "FROM event_acrescimos WHERE event_id = ANY(:ids) ORDER BY id",
        "comprovantes": "SELECT id, event_id, amount FROM event_payments WHERE "
        "event_id = ANY(:ids) ORDER BY id",
        "logs": "SELECT count(*) FROM event_logs WHERE event_id = ANY(:ids)",
        "notificacoes": "SELECT count(*) FROM notifications WHERE entity_type = 'calendar_event' "
        "AND entity_id = ANY(:ids)",
        # contagem global: o verify roda sozinho, e a auditoria de comissão/gasto/BV não traz o id do evento
        "auditoria": "SELECT count(*) FROM audit_logs WHERE :ids IS NOT NULL",
        "parcelas": "SELECT id, event_id, due_date, amount, received FROM event_installments WHERE "
        "event_id = ANY(:ids) ORDER BY id",
        "notas": "SELECT id, event_id, amount, status FROM event_invoices WHERE event_id = ANY(:ids) ORDER BY id",
    }
    out = {k: [tuple(r) for r in _no_banco(sql, ids=ids)] for k, sql in consultas.items()}
    # As tabelas da 306 só existem depois da migration: antes dela, a chave fica de fora.
    congeladas = {
        "cancelamentos": "SELECT * FROM event_cancellations WHERE event_id = ANY(:ids) ORDER BY id",
        "cancelamento_bvs": "SELECT b.* FROM event_cancellation_bvs b JOIN event_cancellations c ON "
        "c.id = b.cancellation_id WHERE c.event_id = ANY(:ids) ORDER BY b.id",
        "cancelamento_elenco": "SELECT x.* FROM event_cancellation_elenco x JOIN event_cancellations c ON "
        "c.id = x.cancellation_id WHERE c.event_id = ANY(:ids) OR x.day_event_id = ANY(:ids) ORDER BY x.id",
    }
    for chave, sql in congeladas.items():
        with contextlib.suppress(Exception):
            out[chave] = [tuple(r) for r in _no_banco(sql, ids=ids)]
    return out


# ── o ato pela API ─────────────────────────────────────────────────────────────────────────────
def _corpo_cancelar(
    modo: str = "parte",
    valor: float | None = 600,
    *,
    nome: str | None = f"{PREFIX}Cliente",
    pix: str | None = PIX,
    motivo: str = "Cliente desistiu (verify 306)",
    **extra,
) -> dict:
    devolucao = {"modo": modo}
    if valor is not None:
        devolucao["valor"] = valor
    if nome is not None:
        devolucao["nome"] = nome
    if pix is not None:
        devolucao["pix"] = pix
    corpo = {"motivo": motivo, "devolucao": devolucao}
    corpo.update(extra)
    return corpo


def _cancelar(event_id: int, corpo: dict | None = None, *, apelido: str = "sa"):
    _instalar_espiao_ao_cancelar()
    # o retrato das devoluções antes do POST, de todo dia do grupo, para o `_nada_gravado` de uma recusa
    lider = _no_banco("SELECT coalesce(group_leader_id, id) FROM calendar_events WHERE id = :i", i=event_id)
    raiz = lider[0][0] if lider else event_id
    dias = [r[0] for r in _no_banco("SELECT id FROM calendar_events WHERE id = :r OR group_leader_id = :r", r=raiz)]
    for dia in {event_id, *dias}:
        _ESTADO_DEVOLUCOES[dia] = [(d["id"], q(d["valor"]), d["status"]) for d in _devolucoes(dia)]
    return _cliente(apelido).post(
        ROTAS["cancelar"].format(id=event_id), json=corpo or _corpo_cancelar()
    )


def _cancelar_ok(event_id: int, corpo: dict | None = None) -> dict:
    r = _cancelar(event_id, corpo)
    _garante(
        r.status_code == 200, f"cancelar {event_id} → {r.status_code} {r.get_data(as_text=True)[:400]}"
    )
    _esperar_threads()
    return r.get_json()


def _previa(event_id: int, devolucao: float, *, venda_nova: float | None = None, apelido="sa"):
    url = ROTAS["impacto"].format(id=event_id) + f"?devolucao={devolucao}"
    if venda_nova is not None:
        url += f"&venda_nova={venda_nova}"
    return _cliente(apelido).get(url)


def _alterar_devolucao(event_id: int, total: float, *, apelido: str = "sa", **extra):
    corpo = {"devolucao_total": total, **extra}
    return _cliente(apelido).patch(ROTAS["devolucao"].format(id=event_id), json=corpo)


def _planilha(mes: str) -> list[dict]:
    r = _cliente("fin").get(ROTAS["planilha"].format(m=mes))
    _garante(r.status_code == 200, f"Planilha {mes} → {r.status_code}")
    return r.get_json().get("items") or []


def _comissoes(mes: str, vendedor: str = "vend") -> dict:
    r = _cliente("fin").get(
        ROTAS["comissoes"].format(m=mes, s=estado["usuarios"][vendedor]["id"])
    )
    _garante(r.status_code == 200, f"Comissões {mes} → {r.status_code}")
    return r.get_json()


def _dre(inicio: date, fim: date) -> dict:
    r = _cliente("fin").get(ROTAS["dre"].format(a=inicio.isoformat(), b=fim.isoformat()))
    _garante(r.status_code == 200, f"DRE {inicio}..{fim} → {r.status_code}")
    return r.get_json()


def _exemplo_padrao(
    rotulo: str, *, bv: bool = True, nota: bool = False, comissao=None, vendedor: str = "vend", venda_em: date | None = None
) -> dict:
    """Venda 2.000 a 5% e BV 200 (cheia 90), pagos 1.000. `comissao` = estado da linha de 100/90."""
    ev = _evento(rotulo, nota=nota, vendedor=vendedor, venda_em=venda_em)
    acr = _bv(ev, 200) if bv else None
    _comprovante(ev, 1000)
    linha = None
    if comissao is not None:
        linha = _linha_comissao(ev, 90 if bv else 100, status=comissao, vendedor=vendedor, venda_em=venda_em)
    return {"ev": ev, "bv": acr, "linha": linha}


# ── guarda de ambiente, preparo e limpeza ──────────────────────────────────────────────────────
def _sair(msg: str) -> None:
    print(f"\nAMBIENTE IMPRÓPRIO — {msg}")
    sys.exit(2)


def guarda_de_ambiente() -> None:
    url = os.environ["DATABASE_URL"]
    if not ("localhost" in url or "127.0.0.1" in url):
        _sair("DATABASE_URL não é o manto_local (localhost).")
    ultimo = _no_banco("SELECT calendar_auto_sync_at FROM site_settings WHERE id = 1")[0][0]
    if ultimo and datetime.utcnow() - ultimo < timedelta(minutes=15):
        _sair(
            "houve sincronização automática há menos de 15 minutos — o backend local está ligado, "
            "e a thread dele falaria com o Google real. Pare-o."
        )
    estranhos = _no_banco(
        "SELECT COUNT(*) FROM calendar_events WHERE start_at >= :a AND start_at < :b "
        "AND coalesce(google_event_id, '') NOT LIKE 'v306%'",
        a=FAIXA_ISOLADA[0],
        b=FAIXA_ISOLADA[1],
    )[0][0]
    if estranhos:
        _sair(f"{estranhos} evento(s) que não são do verify nos meses isolados (2047–2049).")


def _papeis_existem() -> None:
    nomes = {r[0] for r in _no_banco("SELECT name FROM roles")}
    for p in (
        RoleName.SUPERADMIN,
        RoleName.COMERCIAL,
        RoleName.FINANCEIRO,
        RoleName.CASTING,
        RoleName.FIGURINO,
        RoleName.ENSAIO,
        RoleName.MARKETING,
        RoleName.ARTISTA_3D,
    ):
        _garante(p in nomes, f"papel {p} não existe no espelho")


def preparar() -> None:
    limpar()
    _papeis_existem()
    _usuario("sa", RoleName.SUPERADMIN)
    _usuario("com", RoleName.COMERCIAL)
    _usuario("fin", RoleName.FINANCEIRO)
    _usuario("cast", RoleName.CASTING)
    _usuario("fig", RoleName.FIGURINO)
    _usuario("ens", RoleName.ENSAIO)
    _usuario("mkt", RoleName.MARKETING)
    _usuario("a3d", RoleName.ARTISTA_3D)
    _usuario("vend", RoleName.COMERCIAL)
    _usuario("vend2", RoleName.COMERCIAL)
    _usuario("semcom", RoleName.COMERCIAL, comissiona=False)
    estado["t"] = _talento("t1")
    estado["t2"] = _talento("t2")
    estado["t_sem_pix"] = _talento("t3", pix=None)
    _aquecer_planilha_e_comissoes()
    estado["linhas_espelho"] = _retrato_comissoes_do_espelho()
    with app.app_context():
        s = db.session.get(SiteSetting, 1)
        estado["config"] = {
            "taxa_padrao": s.default_commission_rate,
            "edu_responsavel": s.educamanto_seller_id,
            "edu_taxa": s.educamanto_commission_rate,
            "tax_rate": getattr(s, "tax_rate", None),
        }


_CONTAGEM_DO_AQUECIMENTO = (
    ("salários", "SELECT count(*) FROM salary_payments"),
    ("lançamentos de fixos", "SELECT count(*) FROM recurring_expense_entries"),
    ("linhas de comissão", "SELECT count(*) FROM commission_payments"),
)


def _aquecer_planilha_e_comissoes() -> None:
    """Abre a Planilha de M−1 a M+2 e Comissões (todos os vendedores) antes do retrato do 26.

    O GET das duas telas grava (resync das comissões, salários e lançamentos de fixos do mês): é o
    que o app faria na primeira abertura, com ou sem o verify. Sem aquecer, a primeira abertura por
    um cenário qualquer mudaria o espelho e o 26 acusaria algo que não é da feature. O que o
    aquecimento grava fica no espelho e é listado aqui.
    """
    antes = {rotulo: _no_banco(sql)[0][0] for rotulo, sql in _CONTAGEM_DO_AQUECIMENTO}
    hoje = _hoje_sp()
    meses = [_mes_anterior(hoje), date(hoje.year, hoje.month, 1)]
    meses += [_mes_seguinte(meses[-1]), _mes_seguinte(_mes_seguinte(meses[-1]))]
    for m in meses:
        _planilha(_mes(m))
    for m in meses[:2]:
        r = _cliente("fin").get(f"/api/financeiro/comissoes?month={_mes(m)}")
        _garante(r.status_code == 200, f"aquecimento: Comissões {_mes(m)} → {r.status_code}")
    depois = {rotulo: _no_banco(sql)[0][0] for rotulo, sql in _CONTAGEM_DO_AQUECIMENTO}
    novos = {k: depois[k] - antes[k] for k in antes if depois[k] != antes[k]}
    estado["aquecimento"] = novos
    print(f"  (aquecimento de {_mes(meses[0])} a {_mes(meses[-1])}: fica no espelho {novos or 'nada novo'})")


def _retrato_comissoes_do_espelho() -> list[tuple]:
    """Todas as linhas de comissão fora do verify (o passado quieto, cenário 26)."""
    return [
        tuple(r)
        for r in _no_banco(
            "SELECT cp.id, cp.event_id, cp.seller_id, cp.amount, cp.status, cp.sale_date, "
            "cp.payable_from, cp.original_id, cp.notes FROM commission_payments cp "
            "LEFT JOIN users u ON u.id = cp.seller_id "
            "LEFT JOIN calendar_events e ON e.id = cp.event_id "
            # Linha de evento do verify não é do espelho, mesmo com um vendedor do espelho: o resync
            # da restauração passa a EducaManto dos eventos do verify ao responsável do espelho.
            "WHERE coalesce(u.email, '') NOT LIKE :p "
            "AND NOT (coalesce(e.google_event_id, '') LIKE :g OR coalesce(e.title, '') LIKE :t) ORDER BY cp.id",
            p=f"{PREFIX}%",
            g=f"{GID}%",
            t=f"%{PREFIX}%",
        )
    ]


def _restaurar_config() -> None:
    """Volta a taxa padrão e o EducaManto do espelho e ressincroniza as comissões a pagar.

    Enquanto a configuração do verify vale, qualquer abertura de Comissões ou da Planilha
    ressincroniza também as linhas do espelho: a EducaManto passa para o responsável do verify e a
    comum é recalculada pela taxa do verify. A 1ª rodada (16/10) apagou assim duas linhas
    EducaManto do espelho na limpeza. O resync aqui, com a configuração de volta, devolve cada
    linha a pagar do espelho ao que o app calcularia sem o verify.
    """
    cfg = estado.get("config")
    if not cfg:
        return
    with app.app_context():
        s = db.session.get(SiteSetting, 1)
        mudou = (
            s.default_commission_rate != cfg["taxa_padrao"]
            or s.educamanto_seller_id != cfg["edu_responsavel"]
            or s.educamanto_commission_rate != cfg["edu_taxa"]
        )
        s.default_commission_rate = cfg["taxa_padrao"]
        s.educamanto_seller_id = cfg["edu_responsavel"]
        s.educamanto_commission_rate = cfg["edu_taxa"]
        db.session.commit()
        if mudou:
            from app.financeiro.routes import _resync_pending_commissions

            _resync_pending_commissions()
            db.session.commit()


def _sobras_do_verify() -> dict:
    """O que sobrou com o prefixo ou o id do Google do verify (cenário 27): tem de ser nada."""
    consultas = {
        "eventos": ("SELECT count(*) FROM calendar_events WHERE google_event_id LIKE :g OR title LIKE :t", {}),
        "ensaios": ("SELECT count(*) FROM calendar_events WHERE event_type = 'ENSAIO' AND location LIKE :p", {}),
        "usuários": ("SELECT count(*) FROM users WHERE email LIKE :p", {}),
        "talentos": ("SELECT count(*) FROM talents WHERE full_name LIKE :p", {}),
        "comissões": (
            "SELECT count(*) FROM commission_payments cp JOIN users u ON u.id = cp.seller_id WHERE u.email LIKE :p",
            {},
        ),
        "gastos": ("SELECT count(*) FROM special_expenses WHERE description LIKE :p OR supplier_name LIKE :p", {}),
        "orçamentos": ("SELECT count(*) FROM orcamento_history WHERE event_location LIKE :p", {}),
        "clientes": ("SELECT count(*) FROM clients WHERE name LIKE :p", {}),
        "folha nos meses isolados": (f"SELECT count(*) FROM salary_payments WHERE month_ref >= '{FAIXA_ISOLADA_MES}'", {}),
        "fixos nos meses isolados": (f"SELECT count(*) FROM recurring_expense_entries WHERE month_ref >= '{FAIXA_ISOLADA_MES}'", {}),
        "formulários": ("SELECT count(*) FROM form_responses WHERE contact_name LIKE :p", {}),
        "notificações": (
            "SELECT count(*) FROM notifications n JOIN users u ON u.id = n.user_id WHERE u.email LIKE :p",
            {},
        ),
        "sinos dos atos": (
            "SELECT count(*) FROM notifications n WHERE n.kind IN ('evento.cancelado', 'evento.cancelado_escala') "
            "AND NOT EXISTS (SELECT 1 FROM calendar_events e WHERE e.id::text = split_part(n.dedupe_key, ':', 2))",
            {},
        ),
    }
    out = {}
    valores = {"g": f"{GID}%", "t": f"%{PREFIX}%", "p": f"{PREFIX}%"}
    for rotulo, (sql, _extra) in consultas.items():
        n = _no_banco(sql, **{k: v for k, v in valores.items() if f":{k}" in sql})[0][0]
        if n:
            out[rotulo] = n
    with contextlib.suppress(Exception):
        n = _no_banco(
            "SELECT count(*) FROM event_cancellations c LEFT JOIN calendar_events e ON e.id = c.event_id "
            "WHERE e.id IS NULL"
        )[0][0]
        if n:
            out["congelamentos órfãos"] = n
    return out


def limpar() -> None:
    """Apaga tudo o que o verify criou, pelo prefixo e pelo id do Google — nunca pelo título."""
    _restaurar_config()
    with app.app_context():
        db.session.rollback()
        ids = [
            r[0]
            for r in _no_banco(
                "SELECT id FROM calendar_events WHERE google_event_id LIKE :g OR title LIKE :t "
                "OR (parent_event_id IN (SELECT id FROM calendar_events WHERE google_event_id "
                "LIKE :g))",
                g=f"{GID}%",
                t=f"%{PREFIX}%",
            )
        ] + list(estado["eventos"].keys())
        ids = sorted(set(ids))
        usuarios = [
            r[0]
            for r in _no_banco("SELECT id FROM users WHERE email LIKE :p", p=f"{PREFIX}%")
        ]
        talentos = [
            r[0]
            for r in _no_banco("SELECT id FROM talents WHERE full_name LIKE :p", p=f"{PREFIX}%")
        ]
        alvo = ids or [0]
        conta = usuarios or [0]
        comandos = [
            # filhas do cancelamento (se as tabelas existem) antes dos eventos
            "DELETE FROM event_cancellation_elenco WHERE day_event_id = ANY(:e) OR cancellation_id "
            "IN (SELECT id FROM event_cancellations WHERE event_id = ANY(:e))",
            "DELETE FROM event_cancellation_bvs WHERE cancellation_id IN (SELECT id FROM "
            "event_cancellations WHERE event_id = ANY(:e))",
            "DELETE FROM event_cancellations WHERE event_id = ANY(:e) OR updated_by_id = ANY(:u) "
            "OR seller_id = ANY(:u) OR commission_seller_id = ANY(:u)",
        ]
        for sql in comandos:
            with contextlib.suppress(Exception):
                db.session.execute(text(sql), {"e": alvo, "u": conta})
                db.session.commit()
            db.session.rollback()
        db.session.execute(
            text(
                "DELETE FROM notifications WHERE (entity_type = 'calendar_event' AND entity_id = "
                "ANY(:e)) OR user_id = ANY(:u) OR (kind IN ('evento.cancelado', 'evento.cancelado_escala') "
                "AND split_part(dedupe_key, ':', 2) ~ '^[0-9]+$' AND split_part(dedupe_key, ':', 2)::int = ANY(:e))"
            ),
            {"e": alvo, "u": conta},
        )
        # Nunca pelo vendedor sozinho: uma linha do espelho que o resync passou a um usuário do
        # verify continua sendo do espelho (o `_restaurar_config` a devolve). Do verify são as
        # linhas dos eventos dele e as sem evento (estorno da exclusão) dos usuários dele.
        db.session.execute(
            text(
                "DELETE FROM commission_payments WHERE event_id = ANY(:e) "
                "OR (event_id IS NULL AND seller_id = ANY(:u)) "
                "OR original_id IN (SELECT id FROM commission_payments WHERE event_id = ANY(:e) "
                "OR (event_id IS NULL AND seller_id = ANY(:u)))"
            ),
            {"e": alvo, "u": conta},
        )
        db.session.execute(
            text("UPDATE calendar_events SET orcamento_history_id = NULL, client_id = NULL WHERE id = ANY(:e)"),
            {"e": alvo},
        )
        db.session.execute(text("DELETE FROM event_clients WHERE event_id = ANY(:e)"), {"e": alvo})
        db.session.execute(
            text("DELETE FROM form_responses WHERE contact_name LIKE :p OR event_id = ANY(:e)"),
            {"p": f"{PREFIX}%", "e": alvo},
        )
        db.session.execute(
            text(
                "DELETE FROM orcamento_history WHERE id = ANY(:o) OR user_id = ANY(:u) "
                "OR event_location LIKE :p"
            ),
            {"o": estado["orcamentos"] or [0], "u": conta, "p": f"{PREFIX}%"},
        )
        db.session.execute(
            text(
                "DELETE FROM special_expenses WHERE event_id = ANY(:e) OR description LIKE :p "
                "OR created_by_id = ANY(:u)"
            ),
            {"e": alvo, "p": f"{PREFIX}%", "u": conta},
        )
        db.session.commit()
        eventos = CalendarEvent.query.filter(CalendarEvent.id.in_(alvo)).all()
        # Ensaios antes dos pais; satélites antes dos líderes.
        for ev in sorted(
            eventos, key=lambda e: (e.parent_event_id is None, e.group_leader_id is None)
        ):
            cal_routes._clear_event_side_tables(ev.id)
            db.session.delete(ev)
            db.session.flush()
        db.session.execute(
            text(
                # Só a do verify: `entity_id` de comissão é vendedor ou linha, não evento.
                "DELETE FROM audit_logs WHERE (entity_type = 'agenda' AND entity_id = ANY(:e)) "
                "OR entity_name LIKE :p OR entity_name LIKE '%V306%' OR detail LIKE :g OR actor_name LIKE :p"
            ),
            {"e": alvo, "p": f"%{PREFIX}%", "g": f"%{GID}%"},
        )
        db.session.commit()
        for tid in talentos:
            db.session.execute(text("DELETE FROM event_ratings WHERE talent_id = :t"), {"t": tid})
            t = db.session.get(Talent, tid)
            if t is not None:
                db.session.delete(t)
        db.session.execute(
            text(
                "DELETE FROM event_clients WHERE client_id IN (SELECT id FROM clients WHERE name LIKE :p)"
            ),
            {"p": f"{PREFIX}%"},
        )
        db.session.execute(text("DELETE FROM clients WHERE name LIKE :p"), {"p": f"{PREFIX}%"})
        # A Planilha aberta nos meses isolados (2047+) gera folha e lançamentos de fixos ali: são do verify.
        db.session.execute(text("DELETE FROM salary_payments WHERE month_ref >= :m"), {"m": FAIXA_ISOLADA_MES})
        db.session.execute(text("DELETE FROM recurring_expense_entries WHERE month_ref >= :m"), {"m": FAIXA_ISOLADA_MES})
        for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
            u.roles.clear()
            db.session.delete(u)
        db.session.commit()
        # Os arquivos que o próprio verify subiu (comprovante, reembolso, nota): o `secure_filename`
        # tira os sublinhados da frente, então o nome gravado leva `_v306_` depois do carimbo.
        pasta = Path(app.config["UPLOAD_FOLDER"])
        for arquivo in pasta.rglob(f"*_{PREFIX.strip('_')}_*"):
            if arquivo.is_file():
                arquivo.unlink()
    estado["eventos"].clear()
    estado["usuarios"].clear()
    estado["talentos"].clear()
    estado["orcamentos"].clear()
    estado["clientes"].clear()


# ── harness `main` × branch ────────────────────────────────────────────────────────────────────
_ARVORE_MAIN: dict = {}


def _arvore_da_main() -> Path:
    """`git archive` da base (`git merge-base HEAD main`) numa pasta do %TEMP%, uma vez por rodada."""
    if "dir" in _ARVORE_MAIN:
        return _ARVORE_MAIN["dir"]
    base = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "merge-base", "HEAD", "main"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    destino = Path(tempfile.mkdtemp(prefix="v306_main_"))
    arquivo = destino / "base.tar"
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "archive", "--format=tar", "-o", str(arquivo), base, "app"],
        check=True,
    )
    subprocess.run(["tar", "-xf", str(arquivo), "-C", str(destino)], check=True)
    _ARVORE_MAIN["dir"] = destino
    _ARVORE_MAIN["base"] = base
    return destino


def _sonda(codigo: str, *, lado: str, env_extra: dict | None = None) -> dict:
    """Roda `codigo` (que imprime um JSON na última linha) com o `app` da `main` ou da branch."""
    raiz = _arvore_da_main() if lado == "main" else REPO_ROOT
    script = Path(tempfile.mkdtemp(prefix="v306_sonda_")) / "sonda.py"
    script.write_text(codigo, encoding="utf-8")
    env = {
        **os.environ,
        "PYTHONPATH": str(raiz),
        "MANTO_SEM_THREADS": "1",
        "FLASK_ENV": "development",
        "PYTHONUTF8": "1",
        **(env_extra or {}),
    }
    r = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(raiz),
        timeout=1800,
    )
    linhas = [x for x in r.stdout.strip().splitlines() if x.strip()]
    _garante(r.returncode == 0 and linhas, f"sonda ({lado}) falhou: {r.stderr.strip()[-800:]}")
    return json.loads(linhas[-1])


_SONDA_COMISSAO = r"""
import json, os
from app import create_app, db
from app.models import CalendarEvent, SiteSetting
app = create_app()
with app.app_context():
    from app.financeiro import comissoes_ops
    s = db.session.get(SiteSetting, 1)
    out = {}
    # A casca e a comissão exibida no detalhe (que cai na estimativa quando não há linha): as 8
    # chamadas de hoje passam por uma das duas — o /vendas/ Jinja e a DRE pela casca, a ficha do
    # evento pela exibida.
    for e in CalendarEvent.query.order_by(CalendarEvent.id).all():
        valor, origem = comissoes_ops.comissao_exibida_do_evento(e, s)
        out[str(e.id)] = [str(comissoes_ops._event_commission(e, s)), str(valor), origem]
    print(json.dumps(out))
"""

_SONDA_GRUPOS_E_COBRANCAS = r"""
import json
from app import create_app, db
from app.models import CalendarEvent, SiteSetting
app = create_app()
with app.app_context():
    from app.financeiro import comissoes_ops, cobranca_ops
    s = db.session.get(SiteSetting, 1)
    lideres = CalendarEvent.query.filter(
        CalendarEvent.id.in_(db.session.query(CalendarEvent.group_leader_id).filter(
            CalendarEvent.group_leader_id.isnot(None)))).order_by(CalendarEvent.id).all()
    grupos = {str(e.id): [str(comissoes_ops._event_commission(e, s)),
                          str(comissoes_ops._group_cost(e))] for e in lideres}
    vendas = CalendarEvent.query.filter(CalendarEvent.sale_value.isnot(None),
                                        CalendarEvent.group_leader_id.is_(None),
                                        CalendarEvent.cancelled_at.is_(None)).order_by(
        CalendarEvent.id).all()
    # So venda sem devolucao lancada: o "ja devolvido" e o que a branch muda de proposito (FR-061).
    from sqlalchemy import text
    com_devolucao = {r[0] for r in db.session.execute(text(
        "SELECT DISTINCT event_id FROM special_expenses WHERE category = 'Devolução a cliente' "
        "AND event_id IS NOT NULL")).fetchall()}
    cobrancas = {}
    for e in vendas:
        if e.id in com_devolucao:
            continue
        r = cobranca_ops.resumo_da_venda_do_evento(e)
        cobrancas[str(e.id)] = {k: str(getattr(r, k)) for k in (
            "valor", "recebido", "saldo", "quitada", "sinal_pendente", "vencimento",
            "vencimento_origem", "data_do_grupo", "situacao")}
    print(json.dumps({"grupos": grupos, "cobrancas": cobrancas}))
"""


def _comparar_lados(sonda: str, rotulo: str) -> None:
    main = _sonda(sonda, lado="main")
    branch = _sonda(sonda, lado="branch")
    diferencas = _diferencas(main, branch)
    _garante(not diferencas, f"{rotulo}: main × branch diferem: {diferencas[:8]}")


def _diferencas(a, b, caminho: str = "") -> list[str]:
    """Diferenças entre dois JSON, olhando só as chaves que `a` (a main) tem."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k, v in a.items():
            if k not in b:
                out.append(f"{caminho}/{k}: some na branch")
            else:
                out.extend(_diferencas(v, b[k], f"{caminho}/{k}"))
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{caminho}: {len(a)} itens na main, {len(b)} na branch"]
        out = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            out.extend(_diferencas(x, y, f"{caminho}[{i}]"))
        return out
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return [] if round(float(a), 2) == round(float(b), 2) else [f"{caminho}: {a} × {b}"]
    return [] if a == b else [f"{caminho}: {a!r} × {b!r}"]


# ── o ato no modo núcleo (Fundação e História 1, antes de a API existir) ───────────────────────
def _ato_nucleo(event_id: int, modo: str, valor: float, *, hoje: date | None = None) -> None:
    """Semeia o congelado pelo ORM e chama a reconciliação direto (quickstart §1, `--nucleo`).

    Usa só o que a Fundação e a História 1 constroem: `comissao_cheia_do_evento`, o modelo,
    `resumo_cancelado` e `reconciliar_comissao_do_cancelado`. A devolução nasce aprovada, como no ato.
    """
    from app.calendar import cancel_ops
    from app.constants import MOTIVO_AJUSTE_RETIDO, REGIME_VENDA, now_sp
    from app.financeiro import comissoes_ops
    from app.models import EventCancellation, EventCancellationBv

    with app.app_context():
        ev = db.session.get(CalendarEvent, event_id)
        s = db.session.get(SiteSetting, 1)
        pago = cancel_ops.total_recebido(ev)
        devolve = pago if modo == "tudo" else (Decimal("0") if modo == "nada" else Decimal(str(valor)))
        if devolve > 0:
            db.session.add(
                SpecialExpense(
                    description=f"Devolução à cliente — {ev.title}"[:200],
                    category=CATEGORIA_DEVOLUCAO,
                    amount=devolve,
                    expense_date=now_sp().date(),
                    status="aprovado",
                    created_by_id=estado["usuarios"]["sa"]["id"],
                    approved_by_id=estado["usuarios"]["sa"]["id"],
                    approved_at=datetime.utcnow(),
                    disbursement_type="cliente",
                    supplier_name=f"{PREFIX}Cliente",
                    supplier_pix=PIX,
                    payment_status="nao_pago",
                    paid_at_creation=False,
                    event_id=ev.id,
                )
            )
        cheia, beneficiario, taxa = comissoes_ops.comissao_cheia_do_evento(ev, s)
        canc = EventCancellation(
            event=ev,
            regime=REGIME_VENDA,
            refund_mode=modo,
            sale_value=Decimal(ev.sale_value or 0),
            commission_full=cheia,
            commission_rate=taxa,
            commission_seller_id=beneficiario,
            seller_id=ev.seller_id,
            with_invoice=bool(ev.with_invoice),
        )
        for a in ev.acrescimos:
            if a.is_bv and a.amount_brl:
                pago_bv = a.bv_payment_status in ("pago", "no_banco")
                canc.bvs.append(
                    EventCancellationBv(
                        acrescimo_id=a.id,
                        recipient=a.bv_recipient,
                        pix=a.bv_pix,
                        original_amount=a.amount_brl,
                        paid_at_cancellation=pago_bv,
                        paid_amount=a.amount_brl if pago_bv else None,
                    )
                )
        db.session.add(canc)
        ev.cancelled_at = now_sp()
        ev.cancelled_by_id = estado["usuarios"]["sa"]["id"]
        ev.cancellation_reason = "verify 306 (núcleo)"
        db.session.flush()
        resumo = cancel_ops.resumo_cancelado(ev)
        alvos = {beneficiario: comissoes_ops.comissao_do_retido(cheia, resumo.retido, canc.sale_value)}
        if beneficiario is None:
            alvos = {}
        comissoes_ops.reconciliar_comissao_do_cancelado(
            ev, alvos, motivo=MOTIVO_AJUSTE_RETIDO, hoje=hoje
        )
        db.session.commit()


def _ato(event_id: int, modo: str = "parte", valor: float = 600, *, hoje: date | None = None) -> None:
    """O cancelamento do jeito da fase: pelo núcleo (`--nucleo`) ou pela API."""
    if OPCOES["nucleo"]:
        _ato_nucleo(event_id, modo, valor, hoje=hoje)
        return
    if hoje is None:
        _cancelar_ok(event_id, _corpo_cancelar(modo, valor if modo != "nada" else None))
        return
    with _com_hoje(hoje):
        _cancelar_ok(event_id, _corpo_cancelar(modo, valor if modo != "nada" else None))


def _dia(n: int) -> date:
    """O dia `n` do mês corrente (para a matriz de "hoje": dias 1–5 × depois do dia 5)."""
    h = _hoje_sp()
    return date(h.year, h.month, n)


# ── B0 · Fundação ──────────────────────────────────────────────────────────────────────────────
def c1_chao_e_casca() -> None:
    _garante(es._send is _send_falso, "o `_send` falso não está instalado")
    _garante(cal_service.build == google.build, "o dublê do Google não está em service.build")
    _garante(not rede_bloqueada, f"conexão externa tentada antes do 1: {rede_bloqueada}")
    _comparar_lados(_SONDA_COMISSAO, "comissão do evento vivo (casca de _event_commission)")


def c16b_cheia_zero_nucleo() -> None:
    """Variante 16b "cheia 0" no modo núcleo: o portão do beneficiário fica só na camada nova."""
    from app.financeiro import comissoes_ops

    cortesia = _evento("16b cortesia", cortesia=True)
    sem_vendedor = _evento("16b sem vendedor", vendedor=None)
    with app.app_context():
        s = db.session.get(SiteSetting, 1)
        for eid, rotulo in ((cortesia, "cortesia com valor"), (sem_vendedor, "sem vendedor")):
            ev = db.session.get(CalendarEvent, eid)
            cheia, beneficiario, _taxa = comissoes_ops.comissao_cheia_do_evento(ev, s)
            _igual(cheia, 0, f"cheia de {rotulo}")
            _garante(beneficiario is None, f"{rotulo}: beneficiário {beneficiario}, esperado None")
        # A casca continua a regra de hoje: a cortesia com valor e o vendedor comissionado dão 100.
        for eid, rotulo in ((cortesia, "cortesia com valor"), (sem_vendedor, "sem vendedor")):
            _igual(
                comissoes_ops._event_commission(db.session.get(CalendarEvent, eid), s),
                100,
                f"casca de {rotulo} (regra de hoje: segue com comissão na DRE)",
            )


def c26_passado_quieto() -> None:
    """Roda no fim: nenhuma linha de comissão fora do verify nasceu, mudou ou foi cancelada."""
    r = subprocess.run(
        [sys.executable, str(AQUI / "contagem_pre_deploy.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=600,
    )
    _garante(r.returncode == 0, f"contagem_pre_deploy.py → {r.returncode}: {r.stderr[-400:]}")
    _garante("alembic_version" in r.stdout and "event_cancellations" in r.stdout, f"a contagem não terminou: {r.stdout[-300:]}")
    # Reabre Comissões (todos os vendedores) e a Planilha de M−1 a M+2 antes do retrato "depois": o
    # resync de agora, com todos os cancelados do verify no banco, não pode mexer no espelho.
    _aquecer_planilha_e_comissoes()
    depois = _retrato_comissoes_do_espelho()
    antes = estado.get("linhas_espelho") or []
    _garante(
        antes == depois,
        f"linhas de comissão fora do verify mudaram: {len(antes)} → {len(depois)} "
        f"(primeira diferença: {next((a for a, b in zip(antes, depois, strict=False) if a != b), None)})",
    )


def c41_regressao_grupos_e_cobrancas() -> None:
    _comparar_lados(_SONDA_GRUPOS_E_COBRANCAS, "comissões dos grupos e cobranças da Home")


_RETRATO: dict = {}


def _retrato() -> dict:
    """O `retrato_main_branch.py` uma vez por rodada (cenários 17 e 23)."""
    if "saida" not in _RETRATO:
        r = subprocess.run(
            [sys.executable, str(AQUI / "retrato_main_branch.py"), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            timeout=3600,
        )
        _RETRATO["codigo"] = r.returncode
        _RETRATO["saida"] = r.stdout
        _RETRATO["erro"] = r.stderr
    return _RETRATO


def c23_retrato_main_branch() -> None:
    r = _retrato()
    _garante(
        r["codigo"] == 0,
        f"retrato_main_branch.py → {r['codigo']}: {(r['saida'] or r['erro'])[-1200:]}",
    )


# ── B1 · História 1 ────────────────────────────────────────────────────────────────────────────
def c7_a_pagar_no_lugar() -> None:
    for bv, cheia, esperado in ((False, 100, 20), (True, 90, 18)):
        ex = _exemplo_padrao(f"7 bv={bv}", bv=bv, comissao="a_pagar")
        antes = _linhas_comissao(ex["ev"])[0]
        _igual(antes["valor"], cheia, "linha antes do ato")
        _ato(ex["ev"])
        linhas = _linhas_comissao(ex["ev"])
        _garante(len(linhas) == 1, f"7: esperada uma linha viva, vieram {linhas}")
        depois = linhas[0]
        _garante(depois["id"] == antes["id"], "7: a linha não foi ajustada no lugar (id mudou)")
        _igual(depois["valor"], esperado, "comissão do retido")
        _garante(depois["venda_em"] == antes["venda_em"], "7: a data da linha mudou")
        _garante(depois["status"] == "a_pagar", f"7: status {depois['status']}")


def _seed_mes_anterior(*, aberto: bool, vendedor: str = "vend") -> int:
    """Uma linha do vendedor no ciclo M−1: a pagar (abre ciclo) ou só paga (liquidado)."""
    outro = _evento("8 outro evento do vendedor", vendedor=vendedor)
    m1 = _mes_anterior(_hoje_sp())
    return _linha_comissao(
        outro, 50, status="a_pagar" if aberto else "pago", vendedor=vendedor, venda_em=date(m1.year, m1.month, 20)
    )


def _ajuste_negativo(event_id: int) -> dict:
    novos = [x for x in _linhas_comissao(event_id) if x["original_id"] is not None]
    _garante(len(novos) == 1, f"esperado um ajuste ligado à paga, vieram {novos}")
    return novos[0]


def c8_paga_no_primeiro_repasse_aberto() -> None:
    for volta, (dia, m1_aberto, ciclo_esperado) in enumerate(((10, None, "M"), (2, True, "M-1"), (2, False, "M"))):
        hoje = _dia(dia)
        vendedor = f"vend8_{volta}"
        _vendedor_proprio(vendedor)
        extra = None
        if m1_aberto is not None:
            extra = _seed_mes_anterior(aberto=m1_aberto, vendedor=vendedor)
        ex = _exemplo_padrao(f"8 dia={dia} m1={m1_aberto}", bv=False, comissao="pago", vendedor=vendedor)
        paga = _linhas_comissao(ex["ev"])[0]
        _ato(ex["ev"], hoje=hoje)
        _igual(_linhas_comissao(ex["ev"])[0]["valor"], 100, "8: a paga ficou intacta")
        aj = _ajuste_negativo(ex["ev"])
        _igual(aj["valor"], -80, "8: ajuste")
        _garante(aj["original_id"] == paga["id"], "8: o ajuste não aponta a paga")
        _garante(aj["status"] == "a_pagar", f"8: ajuste em {aj['status']}")
        _garante(aj["venda_em"] == aj["liberacao"], "8: sale_date ≠ payable_from no ajuste")
        mes_aj = date(aj["venda_em"].year, aj["venda_em"].month, 1)
        alvo = _mes_anterior(hoje) if ciclo_esperado == "M-1" else date(hoje.year, hoje.month, 1)
        _garante(mes_aj == alvo, f"8 dia {dia}: ajuste no ciclo {mes_aj}, esperado {alvo}")
        if extra is not None:
            _no_banco_escrever("DELETE FROM commission_payments WHERE id = :i", i=extra)


def c8_variante_previa_igual_execucao() -> None:
    """Variante 2/8 prévia = execução (no 8): mesma conta, sem gravar nada."""
    for dia in (2, 10):
        hoje = _dia(dia)
        ex = _exemplo_padrao(f"8 prévia dia={dia}", bv=False, comissao="pago")
        if OPCOES["nucleo"]:
            _previa_nucleo(ex["ev"], hoje)
            continue
        with _com_hoje(hoje):
            antes = _retrato_tabelas([ex["ev"]])
            r = _previa(ex["ev"], 600)
            depois = _retrato_tabelas([ex["ev"]])
            _garante(r.status_code == 200, f"prévia → {r.status_code} {r.get_data(as_text=True)[:300]}")
            _garante(antes == depois, "a prévia gravou algo (simular escreve)")
            efeito = r.get_json()["efeito"]
            _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
        aj = _ajuste_negativo(ex["ev"])
        _igual(efeito["retido"], 400, "prévia: retido")
        _igual(efeito["comissao_retido"], 20, "prévia: comissão do retido")
        _igual(efeito["ajuste"], aj["valor"], "prévia: ajuste × gravado")
        _garante(efeito["ciclo"] == _mes(aj["venda_em"]), f"prévia: ciclo {efeito['ciclo']} × {aj['venda_em']}")
        repasse = _mes_seguinte(aj["venda_em"]).replace(day=5).isoformat()
        _garante(efeito["repasse_em"] == repasse, f"prévia: repasse {efeito['repasse_em']} × {repasse}")
    if not OPCOES["nucleo"]:
        # Mutação "simular escreve": a prévia que grava (e commita) tem de ser acusada pelo retrato.
        from app.financeiro import comissoes_ops

        def grava(original):
            def mutante(*a, **k):
                k["simular"] = False
                out = original(*a, **k)
                db.session.commit()
                return out

            return mutante

        def previa_quieta() -> None:
            ex = _exemplo_padrao("8 prévia mutação", bv=False, comissao="pago")
            with _com_hoje(_dia(10)):
                antes = _retrato_tabelas([ex["ev"]])
                r = _previa(ex["ev"], 600)
                _garante(r.status_code == 200, f"prévia mutação → {r.status_code}")
                _garante(_retrato_tabelas([ex["ev"]]) == antes, "a prévia gravou algo (simular escreve)")

        _sob_mutacao(comissoes_ops, "reconciliar_comissao_do_cancelado", grava, previa_quieta, "simular escreve")


def _previa_nucleo(event_id: int, hoje: date) -> None:
    """No núcleo, a prévia é `reconciliar(simular=True)`: o plano tem de ser o que `False` grava."""
    from app.constants import MOTIVO_AJUSTE_RETIDO
    from app.financeiro import comissoes_ops

    with app.app_context():
        ev = db.session.get(CalendarEvent, event_id)
        alvos = {estado["usuarios"]["vend"]["id"]: Decimal("20")}
        consulta = text(
            "SELECT id, amount, status, sale_date, payable_from, original_id, notes "
            "FROM commission_payments WHERE event_id = :i ORDER BY id"
        )
        antes = db.session.execute(consulta, {"i": event_id}).fetchall()
        plano = comissoes_ops.reconciliar_comissao_do_cancelado(
            ev, alvos, motivo=MOTIVO_AJUSTE_RETIDO, hoje=hoje, simular=True
        )
        # A conexão separada só vê o commitado: a prova é a própria sessão (o ORM sujo e, depois do
        # flush, a mesma transação).
        sujos = [o for o in db.session.dirty if db.session.is_modified(o)]
        _garante(
            not db.session.new and not sujos and not db.session.deleted,
            f"simular=True mexeu no ORM: novos {list(db.session.new)}, sujos {sujos}, apagados {list(db.session.deleted)}",
        )
        db.session.flush()
        _garante(db.session.execute(consulta, {"i": event_id}).fetchall() == antes, "simular=True gravou na transação")
        db.session.rollback()
        ev = db.session.get(CalendarEvent, event_id)
        feito = comissoes_ops.reconciliar_comissao_do_cancelado(
            ev, alvos, motivo=MOTIVO_AJUSTE_RETIDO, hoje=hoje, simular=False
        )
        db.session.commit()
    _garante(isinstance(plano, list) and plano, f"simular=True não devolveu o plano (lista de linhas): {plano!r}")
    _garante(
        _normalizar_plano(plano) == _normalizar_plano(feito),
        f"plano simulado ≠ executado: {plano} × {feito}",
    )


def _normalizar_plano(plano) -> list:
    return sorted(
        json.dumps({k: str(v) for k, v in sorted(p.items()) if k != "linha_id"}) for p in plano or []
    )


def c9_no_banco_e_desfazer() -> None:
    ex = _exemplo_padrao("9 no banco", bv=False, comissao="no_banco")
    _ato(ex["ev"], hoje=_dia(10))
    aj = _ajuste_negativo(ex["ev"])
    _igual(aj["valor"], -80, "9: no banco tratada como paga")
    no_banco = next(x for x in _linhas_comissao(ex["ev"]) if x["id"] == ex["linha"])
    _garante(no_banco["status"] == "no_banco" and q(no_banco["valor"]) == q(100), f"9: a no banco mudou {no_banco}")
    _garante(aj["original_id"] == ex["linha"] and aj["venda_em"] == aj["liberacao"], f"9: ajuste {aj}")
    _garante((aj["venda_em"].year, aj["venda_em"].month) == (_dia(10).year, _dia(10).month), f"9: −80 fora do primeiro repasse aberto {aj}")
    _desfazer_e_conferir(ex["ev"], alvo=Decimal("20"), alvo_com_mais_100=Decimal("25"))


def _desfazer_e_conferir(event_id: int, *, alvo: Decimal, alvo_com_mais_100: Decimal) -> None:
    """Variante 9/10-desfazer: desfazer o pago pela Planilha (267c), abrir as telas e corrigir um
    comprovante — a Σ das linhas vivas é o alvo em cada momento (data-model §7.3)."""
    liquidada = next(
        x for x in _linhas_comissao(event_id) if x["status"] in ("pago", "no_banco")
    )
    ciclo = liquidada["liberacao"] or liquidada["venda_em"]
    item = f"{liquidada['seller']}:{_mes(ciclo)}" + (":pago" if liquidada["status"] == "pago" else "")
    r = _cliente("sa").post(
        ROTAS["planilha_status"],
        json={"item_type": "commission", "item_id": item, "status": "nao_pago", "motivo": "verify 306"},
    )
    _garante(r.status_code == 200, f"desfazer {item} → {r.status_code} {r.get_data(as_text=True)[:300]}")
    voltou = next(x for x in _linhas_comissao(event_id) if x["id"] == liquidada["id"])
    _garante(voltou["status"] == "a_pagar", f"desfazer: a linha ficou {voltou['status']}")
    _igual(voltou["valor"], liquidada["valor"], "desfazer: o valor mudou")
    _igual(_soma_vivas(event_id), alvo, "Σ depois do desfazer")
    _planilha(_mes(_mes_seguinte(ciclo)))  # abre a Planilha (resync)
    _comissoes(_mes(ciclo))  # e Comissões
    _igual(_soma_vivas(event_id), alvo, "Σ depois do resync")
    _garante(
        next(x for x in _linhas_comissao(event_id) if x["id"] == liquidada["id"])["valor"]
        == liquidada["valor"],
        "o resync regravou a linha desfeita",
    )
    if OPCOES["nucleo"]:
        return  # a correção do comprovante no cancelado nasce na H2 (reaplicar_por_dinheiro)
    antes = {x["id"]: x for x in _linhas_comissao(event_id)}
    r = _post_comprovante("sa", event_id, 100)
    _garante(r.status_code == 201, f"comprovante depois do desfazer → {r.status_code} {_erro(r)}")
    _igual(_soma_vivas(event_id), alvo_com_mais_100, "Σ depois de corrigir o comprovante")
    vivas = _linhas_comissao(event_id)
    _garante(
        all(x["id"] in antes and (x["venda_em"], x["liberacao"]) == (antes[x["id"]]["venda_em"], antes[x["id"]]["liberacao"]) for x in vivas),
        f"a correção não absorveu no lugar com a data intacta: {antes} → {vivas}",
    )


def c10_tudo_e_sem_linha() -> None:
    a_pagar = _exemplo_padrao("10 tudo a pagar", bv=False, comissao="a_pagar")
    _ato(a_pagar["ev"], "tudo", 1000)
    _garante(not _linhas_comissao(a_pagar["ev"]), "10: a a_pagar não foi cancelada no Tudo")
    mantida = [x for x in _linhas_comissao(a_pagar["ev"], vivas=False) if x["id"] == a_pagar["linha"]]
    _garante(mantida and mantida[0]["status"] == "cancelado", f"10: a a_pagar não ficou cancelada (sumiu?): {mantida}")
    paga = _exemplo_padrao("10 tudo paga", bv=False, comissao="pago")
    _ato(paga["ev"], "tudo", 1000, hoje=_dia(10))
    _igual(_ajuste_negativo(paga["ev"])["valor"], -100, "10: −100 da paga no Tudo")
    _desfazer_e_conferir(paga["ev"], alvo=Decimal("0"), alvo_com_mais_100=Decimal("5"))
    sem_linha = _exemplo_padrao("10 sem linha", bv=False)
    _ato(sem_linha["ev"])
    linhas = _linhas_comissao(sem_linha["ev"])
    _garante(len(linhas) == 1, f"10: a linha não nasceu no cancelamento: {linhas}")
    _igual(linhas[0]["valor"], 20, "10: linha nascida")
    nao_comissionado = _evento("10 vendedor sem comissão", vendedor="semcom")
    _comprovante(nao_comissionado, 1000)
    _ato(nao_comissionado)
    _garante(not _linhas_comissao(nao_comissionado), "10: vendedor sem comissão ganhou linha")
    _igual(_cancelamento(nao_comissionado)["cheia"], 0, "10: cheia do não comissionado")


def _configurar_educamanto() -> None:
    with app.app_context():
        s = db.session.get(SiteSetting, 1)
        s.educamanto_seller_id = estado["usuarios"]["vend2"]["id"]
        s.educamanto_commission_rate = 5
        db.session.commit()


def c11_educamanto() -> None:
    _configurar_educamanto()
    try:
        _c11_educamanto()
    finally:
        _restaurar_config()


def _c11_educamanto() -> None:
    inicio = datetime.combine(_hoje_sp() + timedelta(days=40), datetime.min.time()).replace(hour=19)
    vend2 = estado["usuarios"]["vend2"]["id"]
    ev = _evento("11 edu", titulo="(EDU) V306 11 EDUCAMANTO", inicio=inicio, vendedor="vend")
    _bv(ev, 200)
    _comprovante(ev, 1000)
    linha = _linha_comissao(ev, 90, vendedor="vend2", liberacao=inicio.date())
    _ato(ev)
    linhas = _linhas_comissao(ev)
    _garante(len(linhas) == 1 and linhas[0]["id"] == linha, f"11: reduzida no lugar (mesma linha): {linhas}")
    _igual(linhas[0]["valor"], 18, "11: EducaManto reduzida no lugar")
    _garante(linhas[0]["liberacao"] == inicio.date(), "11: a data de liberação mudou")
    _garante(linhas[0]["seller"] == vend2, "11: beneficiário errado")
    variante = _evento("11 edu sem linha", titulo="(EDU) V306 11 SEM LINHA", inicio=inicio + timedelta(days=1))
    _bv(variante, 200)
    _comprovante(variante, 1000)
    _ato(variante)
    nova = _linhas_comissao(variante)
    _garante(len(nova) == 1, f"11 variante: {nova}")
    _igual(nova[0]["valor"], 18, "11 variante: valor da linha nova")
    _garante(nova[0]["seller"] == vend2, f"11 variante: beneficiário {nova[0]['seller']} (esperado o responsável)")
    _garante(
        nova[0]["liberacao"] == (inicio + timedelta(days=1)).date(),
        f"11 variante: a linha nova não nasceu com a data do evento ({nova[0]['liberacao']})",
    )
    # EducaManto já paga: o ajuste vai ao primeiro repasse aberto do responsável
    paga = _evento("11 edu paga", titulo="(EDU) V306 11 PAGA", inicio=inicio + timedelta(days=2))
    _bv(paga, 200)
    _comprovante(paga, 1000)
    base = _linha_comissao(paga, 90, vendedor="vend2", status="pago", liberacao=(inicio + timedelta(days=2)).date())
    _ato(paga, hoje=_dia(10))
    aj = _ajuste_negativo(paga)
    _igual(aj["valor"], -72, "11 paga: ajuste")
    _garante(aj["original_id"] == base and aj["seller"] == vend2 and aj["venda_em"] == aj["liberacao"], f"11 paga: ajuste {aj}")
    _garante((aj["venda_em"].year, aj["venda_em"].month) == (_dia(10).year, _dia(10).month), f"11 paga: fora do primeiro repasse aberto {aj}")


def c12_reabrir_telas() -> None:
    ex = _exemplo_padrao("12 reabrir", comissao="a_pagar")
    _ato(ex["ev"])
    mes = _mes(_hoje_sp())
    _comissoes(mes)
    _planilha(_mes(_mes_seguinte(_hoje_sp())))
    _igual(_soma_vivas(ex["ev"]), 18, "12: depois de reabrir Comissões e Planilha")
    if not OPCOES["nucleo"]:
        resumo = _resumo_api(ex["ev"])
        _igual(resumo["comissao"]["retido"], 18, "12: comissão do retido no detalhe")
    # Σ linhas vivas = alvo em todo cancelado com congelamento.
    from app.calendar import cancel_ops
    from app.financeiro import comissoes_ops

    for (eid,) in _no_banco("SELECT event_id FROM event_cancellations WHERE regime = 'venda'"):
        with app.app_context():
            ev = db.session.get(CalendarEvent, eid)
            resumo = cancel_ops.resumo_cancelado(ev)
            alvo = comissoes_ops.comissao_do_retido(
                resumo.comissao_cheia, resumo.retido, resumo.venda or 0
            )
        _igual(_soma_vivas(eid), alvo, f"12: Σ das linhas vivas do cancelado {eid}")


def _vendedor_proprio(apelido: str) -> int:
    """Vendedor descartável só do cenário: as somas por vendedor e ciclo não misturam outros cenários."""
    if apelido not in estado["usuarios"]:
        _usuario(apelido, RoleName.COMERCIAL)
    return estado["usuarios"][apelido]["id"]


def c13_planilha_igual_comissoes() -> None:
    vend = _vendedor_proprio("vend13")
    m2 = _mes_anterior(_mes_anterior(_hoje_sp()))
    venda_em = date(m2.year, m2.month, 12)
    ex = _exemplo_padrao("13 identidade", bv=False, comissao="pago", vendedor="vend13", venda_em=venda_em)
    no_banco = _evento("13 no banco", vendedor="vend13", venda_em=venda_em)
    _linha_comissao(no_banco, 50, status="no_banco", vendedor="vend13", venda_em=venda_em)
    _ato(ex["ev"], hoje=_dia(10))
    aj = _ajuste_negativo(ex["ev"])
    ciclos = sorted({_mes(venda_em), _mes(aj["venda_em"])})
    _garante(len(ciclos) == 2, f"13: a venda e o ajuste no mesmo ciclo {ciclos}")
    for ciclo in ciclos:
        dados = _comissoes(ciclo, vendedor="vend13")
        k = dados["kpis"]
        soma = sum(Decimal(str(k.get(c) or 0)) for c in ("total_paid", "total_no_banco", "total_pending"))
        _igual(k.get("total_month"), soma, f"13 {ciclo}: total_month = pago + no banco + a pagar")
        ano, mes_ = (int(x) for x in ciclo.split("-"))
        itens = [
            i for i in _planilha(_mes(_mes_seguinte(date(ano, mes_, 1))))
            if i["type"] == "commission" and str(i["id"]).startswith(f"{vend}:{ciclo}")
        ]
        linhas = sorted((x["id"], q(x["amount"])) for i in itens for x in (i.get("commission_lines") or []))
        entradas = sorted(
            (e["id"], q(e.get("amount") or 0)) for e in dados.get("entries", [])
            if e.get("status") in ("a_pagar", "no_banco", "pago")
        )
        _garante(linhas == entradas, f"13 {ciclo}: Planilha {linhas} × Comissões {entradas} (mesmas linhas)")
        _igual(sum(Decimal(str(i["amount"])) for i in itens), sum(x[1] for x in entradas), f"13 {ciclo}: mesmo desconto")


def c14_soma_zero_e_orfao() -> None:
    from app.financeiro import comissoes_ops

    vend = _vendedor_proprio("vend14")
    ex = _exemplo_padrao("14 soma zero", bv=False, comissao="pago", vendedor="vend14")
    _ato(ex["ev"], "tudo", 1000, hoje=_dia(10))  # −100 no ciclo corrente
    outro = _evento("14 outro", vendedor="vend14")
    _linha_comissao(outro, 100, vendedor="vend14", venda_em=_dia(10))  # +100 a pagar no mesmo ciclo
    abertos = [
        i for i in _planilha(_mes(_mes_seguinte(_hoje_sp())))
        if i["type"] == "commission" and i["id"] == f"{vend}:{_mes(_hoje_sp())}"
    ]
    _garante(abertos, "14: o item aberto de soma zero com linhas de valor sumiu da Planilha")
    _igual(abertos[0]["amount"], 0, "14: soma do item aberto")
    _garante(len(abertos[0].get("commission_lines") or []) >= 2, f"14: o item não traz as linhas: {abertos[0]}")
    # Órfão (sem evento, ligado a uma paga) no ciclo M−1: não abre ciclo para o primeiro repasse aberto.
    m1 = _mes_anterior(_hoje_sp())
    antigo = _evento("14 antigo", venda=None, vendedor="vend14")
    paga = _linha_comissao(antigo, 30, status="pago", vendedor="vend14", venda_em=date(m1.year, m1.month, 15))
    orfao = _linha_comissao(None, -30, vendedor="vend14", venda_em=date(m1.year, m1.month, 15), original_id=paga)
    with app.app_context():
        cp = db.session.get(CommissionPayment, orfao)
        _garante(cp.event_id is None and cp.original_id == paga, f"14: o órfão não tem o formato {cp.event_id} {cp.original_id}")
        _garante(not comissoes_ops.linha_abre_ciclo(cp), "14: estorno órfão abre ciclo")
        primeiro = comissoes_ops.primeiro_repasse_aberto(vend, _dia(2))
        _garante((primeiro.year, primeiro.month) == (_hoje_sp().year, _hoje_sp().month), f"14: o órfão abriu o ciclo M−1 ({primeiro})")
    # um ajuste de verdade no dia 2, com o órfão no M−1: vai ao corrente
    real = _exemplo_padrao("14 ajuste", bv=False, comissao="pago", vendedor="vend14")
    _ato(real["ev"], hoje=_dia(2))
    aj = _ajuste_negativo(real["ev"])
    _garante((aj["venda_em"].year, aj["venda_em"].month) == (_hoje_sp().year, _hoje_sp().month), f"14: ajuste no ciclo do órfão {aj}")


_SONDA_ESTORNO = r"""
import json, os
from datetime import date
from app import create_app, db
from app.models import CalendarEvent, CommissionPayment
app = create_app()
with app.app_context():
    from app.calendar import cancel_ops
    ev = db.session.get(CalendarEvent, int(os.environ["V306_EVENTO"]))
    cancel_ops.aplicar_estorno_comissao(ev)
    db.session.flush()
    novas = CommissionPayment.query.filter(CommissionPayment.original_id.isnot(None),
        CommissionPayment.seller_id == int(os.environ["V306_VENDEDOR"]),
        CommissionPayment.event_id.is_(None)).all()
    out = [{"venda_em": str(c.sale_date), "liberacao": str(c.payable_from), "valor": str(c.amount)}
           for c in novas]
    db.session.rollback()
    print(json.dumps(out))
"""


def c14b_exclusao_no_primeiro_repasse() -> None:
    for dia in (2, 10):
        for status in ("pago", "no_banco"):
            m2 = _mes_anterior(_mes_anterior(_hoje_sp()))
            apelido = f"vend14b_{dia}_{status}"
            vend = _vendedor_proprio(apelido)
            ev = _evento(f"14b {status} dia={dia}", venda=None, vendedor=apelido)
            _linha_comissao(ev, 100, status=status, vendedor=apelido, venda_em=date(m2.year, m2.month, 10))

            def item_do_ciclo_da_venda(vend: int = vend, m2: date = m2) -> list:
                return sorted(
                    (str(i["id"]), round(float(i["amount"] or 0), 2), i["status"])
                    for i in _planilha(_mes(_mes_seguinte(m2)))
                    if i["type"] == "commission" and str(i["id"]).startswith(f"{vend}:{_mes(m2)}")
                )

            ciclo_da_venda = item_do_ciclo_da_venda()
            if dia == 10:
                # mutação contra a main: a main põe o estorno na data da venda (o 211)
                main = _sonda(
                    _SONDA_ESTORNO,
                    lado="main",
                    env_extra={"V306_EVENTO": str(ev), "V306_VENDEDOR": str(vend)},
                )
                if status == "pago":
                    _garante(
                        main and main[0]["venda_em"] == str(date(m2.year, m2.month, 10)),
                        f"14b mutação: a main não pôs o estorno na data da venda ({main})",
                    )
                else:
                    # A main só estorna a paga (`cancel_ops.py:158-171`): o ramo `no_banco` é da 306.
                    _garante(not main, f"14b mutação: a main estornou o no_banco ({main})")
            with _com_hoje(_dia(dia)):
                r = _cliente("sa").delete(ROTAS["excluir"].format(id=ev))
            _garante(r.status_code == 200, f"14b excluir → {r.status_code} {r.get_data(as_text=True)[:300]}")
            estornos = _no_banco(
                "SELECT sale_date, payable_from, amount FROM commission_payments WHERE "
                "event_id IS NULL AND original_id IS NOT NULL AND seller_id = :s AND amount < 0 "
                "ORDER BY id DESC LIMIT 1",
                s=vend,
            )
            _garante(estornos, "14b: o estorno órfão não nasceu")
            venda_em, liberacao, valor = estornos[0]
            _igual(valor, -100, "14b: estorno")
            _garante(venda_em == liberacao, "14b: sale_date ≠ payable_from no estorno")
            esperado = date(_hoje_sp().year, _hoje_sp().month, 1)
            _garante(
                date(venda_em.year, venda_em.month, 1) == esperado,
                f"14b dia {dia} {status}: estorno no ciclo {venda_em}, esperado o corrente",
            )
            # A Planilha do ciclo da venda (paga no mês seguinte a ele) não muda: o estorno não cai lá.
            _garante(item_do_ciclo_da_venda() == ciclo_da_venda, f"14b: a Planilha do ciclo da venda mudou {ciclo_da_venda} → {item_do_ciclo_da_venda()}")


def _bv_planilha(event_id: int, mes: str) -> list[dict]:
    ids = {r[0] for r in _no_banco("SELECT id FROM event_acrescimos WHERE event_id = :i", i=event_id)}
    return [i for i in _planilha(mes) if i["type"] == "bv" and int(i["id"]) in ids]


def _bv_planilha_jinja(event_id: int, mes: str) -> list[dict]:
    """Os itens de BV da Planilha Jinja (`/financeiro/pagamentos`), pelo `template_rendered`."""
    from flask import template_rendered

    ids = {r[0] for r in _no_banco("SELECT id FROM event_acrescimos WHERE event_id = :i", i=event_id)}
    capturado: dict = {}

    def gravar(_sender, template, context, **_k):
        if template.name == "financeiro/pagamentos.html":
            capturado["items"] = context.get("items") or []

    template_rendered.connect(gravar, app)
    try:
        r = _cliente("fin").get(f"/financeiro/pagamentos?month={mes}")
    finally:
        template_rendered.disconnect(gravar, app)
    _garante(r.status_code == 200, f"Planilha Jinja {mes} → {r.status_code}")
    return [i for i in capturado.get("items", []) if i.get("type") == "bv" and int(i.get("id")) in ids]


def _mes_evento(event_id: int) -> str:
    return _mes(_no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=event_id)[0][0])


def _conta_do_bv(acr_id: int):
    """No núcleo, `bv_da_planilha` direto; senão, a Planilha."""
    from app.calendar import cancel_ops
    from app.models import EventAcrescimo

    with app.app_context():
        return cancel_ops.bv_da_planilha(db.session.get(EventAcrescimo, acr_id))


def c17_bv_na_planilha() -> None:
    nada = _exemplo_padrao("17 nada")
    _ato(nada["ev"], "nada", 0)
    _igual(_conta_do_bv(nada["bv"]), 100, "17: bv_da_planilha com Nada (retido 1.000)")
    if not OPCOES["nucleo"]:
        itens = _bv_planilha(nada["ev"], _mes_evento(nada["ev"]))
        _garante(len(itens) == 1, f"17 Nada: {itens}")
        _igual(itens[0]["amount"], 100, "17: BV do retido com Nada (retido 1.000)")
        jinja = _bv_planilha_jinja(nada["ev"], _mes_evento(nada["ev"]))
        _garante(len(jinja) == 1 and q(jinja[0]["amount"]) == q(100), f"17: Planilha Jinja {jinja}")
    tudo = _exemplo_padrao("17 tudo")
    _ato(tudo["ev"], "tudo", 1000)
    _garante(_conta_do_bv(tudo["bv"]) is None, "17 Tudo: bv_da_planilha não deu None")
    if not OPCOES["nucleo"]:
        _garante(not _bv_planilha(tudo["ev"], _mes_evento(tudo["ev"])), "17 Tudo: o BV não sumiu")
        _garante(not _bv_planilha_jinja(tudo["ev"], _mes_evento(tudo["ev"])), "17 Tudo: o BV não sumiu do Jinja")
    pago = _exemplo_padrao("17 pago antes")
    _no_banco_escrever("UPDATE event_acrescimos SET bv_payment_status = 'pago' WHERE id = :i", i=pago["bv"])
    _ato(pago["ev"], "nada", 0)
    _igual(_conta_do_bv(pago["bv"]), 200, "17: BV pago antes fica pelo pago")
    if not OPCOES["nucleo"]:
        itens = _bv_planilha(pago["ev"], _mes_evento(pago["ev"]))
        _garante(len(itens) == 1 and itens[0]["status"] == "pago", f"17 pago antes: {itens}")
        _igual(itens[0]["amount"], 200, "17: BV pago antes fica pelo pago")
    # variante 16/17-paid_amount: desfeito o pago depois do ato, volta ao proporcional
    if OPCOES["nucleo"]:
        from app.calendar import cancel_ops

        with app.app_context():
            cancel_ops.marcar_status_do_bv(pago["bv"], "nao_pago", None, "verify 306")
            db.session.commit()
    else:
        r = _cliente("fin").post(
            ROTAS["planilha_status"],
            json={"item_type": "bv", "item_id": pago["bv"], "status": "nao_pago"},
        )
        _garante(r.status_code == 200, f"17 desfazer BV → {r.status_code} {r.get_data(as_text=True)[:300]}")
    _igual(_conta_do_bv(pago["bv"]), 100, "17 variante: desfeito, volta ao proporcional")
    _garante(
        _no_banco("SELECT b.paid_amount FROM event_cancellation_bvs b WHERE b.acrescimo_id = :i", i=pago["bv"])[0][0] is None,
        "17 variante: paid_amount não voltou a NULL",
    )


def c17_satelite() -> None:
    """17, a parte do grupo (H5): no satélite cancelado, BV pago fica pelo pago e o não pago some."""
    g = _grupo("17 satélite", dias=2)
    pago = _bv(g["dias"][0], 120, status="pago")
    nao_pago = _bv(g["dias"][1], 80)
    _cancelar_ok(g["principal"], _corpo_cancelar("parte", 900, alcance="todos"))
    itens = _bv_planilha(g["dias"][0], _mes_evento(g["dias"][0]))
    _garante(len(itens) == 1 and q(itens[0]["amount"]) == q(120) and itens[0]["status"] == "pago", f"17 satélite: BV pago {itens}")
    _garante(not _bv_planilha(g["dias"][1], _mes_evento(g["dias"][1])), "17 satélite: BV não pago ficou na Planilha")
    _ = (pago, nao_pago)


def c30_corrida_com_a_planilha() -> None:
    from app.calendar import cancel_ops

    ex = _exemplo_padrao("30 corrida", bv=False, comissao="a_pagar")
    linha = ex["linha"]
    real = None if OPCOES["nucleo"] else cancel_ops.travar_grupo  # sem o gancho: vermelho

    def injeta(*a, **k):
        # outra sessão marca "pago" entre a leitura do endpoint e a trava das linhas
        _no_banco_escrever(
            "UPDATE commission_payments SET status = 'pago', paid_at = now() WHERE id = :i", i=linha
        )
        return real(*a, **k)

    if OPCOES["nucleo"]:
        _no_banco_escrever(
            "UPDATE commission_payments SET status = 'pago', paid_at = now() WHERE id = :i", i=linha
        )
        _ato(ex["ev"], hoje=_dia(10))
    else:
        cancel_ops.travar_grupo = injeta
        try:
            _ato(ex["ev"], hoje=_dia(10))
        finally:
            cancel_ops.travar_grupo = real
    paga = next(x for x in _linhas_comissao(ex["ev"]) if x["id"] == linha)
    _garante(paga["status"] == "pago", "30: a linha não ficou paga")
    _igual(paga["valor"], 100, "30: a paga virou 'paga de 20'")
    _igual(_ajuste_negativo(ex["ev"])["valor"], -80, "30: o −80 não nasceu")
    # sincronização com o evento lido antes do ato: não regrava a linha do retido
    from app.financeiro import comissoes_ops

    ex2 = _exemplo_padrao("30 sync velho", bv=False, comissao="a_pagar")
    # O evento é lido vivo numa sessão, desligado dela, e volta numa sessão nova sem reler o banco
    # (`merge(load=False)`): é o "evento lido antes do ato", sem aninhar a requisição do ato num
    # `app_context` (o que esconderia commits).
    with app.app_context():
        velho = db.session.get(CalendarEvent, ex2["ev"])
        _garante(velho.cancelled_at is None, "30: o evento já nasceu cancelado")
        db.session.expunge(velho)
    _ato(ex2["ev"])
    with app.app_context():
        velho = db.session.merge(velho, load=False)
        _garante(velho.cancelled_at is None, "30: o evento velho não ficou velho")
        comissoes_ops._sync_commission_payment(velho)
        db.session.commit()
    _igual(_soma_vivas(ex2["ev"]), 20, "30: o sync com o evento velho regravou a linha do retido")


# ── B2 · História 2 ────────────────────────────────────────────────────────────────────────────
def _nada_gravado(event_id: int, rotulo: str) -> None:
    """Depois de uma recusa: o evento vivo, sem congelamento e sem devolução nova.

    A devolução que o próprio cenário semeou antes (a avulsa do 3, a pendente do 5) não conta: só
    a que nasceu depois de `_ESTADO_DEVOLUCOES[event_id]` (gravado por `_cancelar`).
    """
    _garante(_cancelado_em(event_id) is None, f"{rotulo}: o evento ficou cancelado")
    _garante(_cancelamento(event_id) is None, f"{rotulo}: nasceu linha em event_cancellations")
    antes = _ESTADO_DEVOLUCOES.get(event_id, [])
    agora = [(d["id"], q(d["valor"]), d["status"]) for d in _devolucoes(event_id)]
    _garante(agora == antes, f"{rotulo}: as devoluções mudaram {antes} → {agora}")


_ESTADO_DEVOLUCOES: dict[int, list] = {}


def _arquivo(nome: str = "c.pdf"):
    import io

    return (io.BytesIO(b"%PDF-1.4 verify 306"), f"{PREFIX}{nome}")


def _post_comprovante(apelido: str, event_id: int, valor: float):
    return _cliente(apelido).post(
        ROTAS["comprovante"].format(id=event_id),
        data={"amount": str(valor), "file": _arquivo()},
        content_type="multipart/form-data",
    )


def c2_parte_600() -> None:
    _ao_cancelar.clear()
    ex = _exemplo_padrao("2 parte", comissao="a_pagar")
    gid = _no_banco("SELECT google_event_id FROM calendar_events WHERE id = :i", i=ex["ev"])[0][0]
    antes_utc = datetime.utcnow()
    marco = google.marco()
    _commit_antes_do_google.clear()
    corpo = _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    _garante(_cancelado_em(ex["ev"]) is not None, "2: não ficou cancelado")
    _garante(google.deletes(marco) == [gid] and all(_commit_antes_do_google), f"2: remoção do Google depois do commit {google.deletes(marco)}")
    devs = _devolucoes(ex["ev"])
    _garante(len(devs) == 1, f"2: devoluções {devs}")
    d = devs[0]
    _igual(d["valor"], 600, "2: devolução")
    _garante(d["status"] == "aprovado" and d["pagamento"] == "nao_pago", f"2: devolução {d}")
    _garante(d["tipo"] == "cliente" and d["nome"] and d["pix"] == PIX, f"2: destinatário {d}")
    c = _cancelamento(ex["ev"])
    _garante(c and c["regime"] == "venda" and c["modo"] == "parte", f"2: congelado {c}")
    _igual(c["venda"], 2000, "2: venda congelada")
    _igual(c["cheia"], 90, "2: cheia congelada")
    resumo = _resumo_api(ex["ev"])
    _igual(resumo["retido"], 400, "2: retido")
    _garante(corpo.get("resumo") == resumo, "2: o `resumo` da resposta ≠ `event.cancelamento` do GET")
    logs = [m for m, quando in _historico(ex["ev"]) if "cancel" in m.lower()]
    _garante(logs, "2: sem EventLog do cancelamento")
    texto = logs[-1].lower()
    for palavra in ("parte", "600", "400", f"{PREFIX}parceiro".lower()):
        _garante(palavra in texto, f"2: o histórico não diz '{palavra}': {logs[-1]}")
    # o BV do retido (40) como número próprio, não como pedaço do 400
    _garante(re.search(r"(?<![\d.,])40(?:[.,]00)?(?![\d])", texto), f"2: o histórico não traz o BV do retido 40: {logs[-1]}")
    quando = [q_ for m, q_ in _historico(ex["ev"]) if "cancel" in m.lower()][-1]
    _garante(abs((quando - antes_utc).total_seconds()) < 300, f"2: hora do histórico {quando} (UTC)")
    _garante(_ao_cancelar.count((ex["ev"], "todos", None)) == 1, f"2: ao_cancelar não viu ('todos', None) uma vez: {_ao_cancelar}")
    # com nota: o imposto entra no histórico
    nota = _exemplo_padrao("2 nota", nota=True)
    _cancelar_ok(nota["ev"], _corpo_cancelar("parte", 600, imposto_retido=64))
    texto = " ".join(m for m, _ in _historico(nota["ev"]) if "cancel" in m.lower())
    _garante(re.search(r"(?<![\d.,])64(?:[.,]00)?(?![\d])", texto), f"2: o histórico não traz o imposto: {texto}")


def c2_variante_previa() -> None:
    for dia in (2, 10):
        ex = _exemplo_padrao(f"2 prévia dia={dia}", comissao="pago")
        with _com_hoje(_dia(dia)):
            antes = _retrato_tabelas([ex["ev"]])
            r = _previa(ex["ev"], 600)
            _garante(r.status_code == 200, f"2 prévia → {r.status_code} {r.get_data(as_text=True)[:300]}")
            _garante(_retrato_tabelas([ex["ev"]]) == antes, "2: o GET da prévia gravou")
            efeito = r.get_json()["efeito"]
            _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
        resumo = _resumo_api(ex["ev"])
        aj = _ajuste_negativo(ex["ev"])
        _igual(efeito["retido"], resumo["retido"], "2 prévia: retido")
        _igual(efeito["comissao_retido"], resumo["comissao"]["retido"], "2 prévia: comissão do retido")
        _igual(efeito["ajuste"], aj["valor"], "2 prévia: ajuste")
        _garante(efeito["ciclo"] == _mes(aj["venda_em"]), "2 prévia: ciclo")
        repasse = _mes_seguinte(aj["venda_em"]).replace(day=5).isoformat()
        _garante(efeito["repasse_em"] == repasse, f"2 prévia: repasse {efeito['repasse_em']} × {repasse}")
        _igual(efeito["bv_retido"], 40, "2 prévia: BV do retido")


def c2b_marcado() -> None:
    from app.notificacoes import notificacoes_ops

    ex = _exemplo_padrao("2b marcado")
    _marcar_sumido(ex["ev"])
    sa = estado["usuarios"]["sa"]["id"]
    _no_banco_escrever(
        "INSERT INTO notifications (user_id, kind, severity, title, entity_type, entity_id, dedupe_key, created_at) "
        "VALUES (:u, :k, 'info', 'verify 306', 'calendar_event', :e, :d, now())",
        u=sa,
        k=notificacoes_ops.KIND_EVENTO_SUMIU_GOOGLE,
        e=ex["ev"],
        d=f"v306-sumiu:{ex['ev']}",
    )
    marco = google.marco()
    corpo = _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    _garante(not google.chamadas[marco:], f"2b: o Google foi chamado: {google.chamadas[marco:]}")
    _garante(not corpo.get("aviso"), f"2b: aviso do Google no marcado: {corpo.get('aviso')}")
    marca = _no_banco("SELECT google_missing_since FROM calendar_events WHERE id = :i", i=ex["ev"])
    _garante(marca[0][0] is None, "2b: a marca não saiu")
    # motivo `cancelado`: o sino do sumiço fica lido, sem o rastro do reaparecimento
    lida = _no_banco("SELECT read_at FROM notifications WHERE dedupe_key = :d", d=f"v306-sumiu:{ex['ev']}")
    _garante(lida and lida[0][0] is not None, "2b: o sino do sumiço não ficou lido")
    _garante(not any("Reapareceu" in m for m, _ in _historico(ex["ev"])), "2b: rastro de reaparecimento no histórico")
    _garante(
        not _no_banco("SELECT 1 FROM audit_logs WHERE action = 'google_reapareceu' AND entity_id = :i", i=ex["ev"]),
        "2b: auditoria google_reapareceu",
    )


def c2b_avisos() -> None:
    """2b, a parte da H6: o marcado avisa elenco e equipe de Ensaio como todo cancelamento."""
    show = _evento_com_elenco("2b avisos", ["A"])
    _escalar(show, estado["t"])
    ensaio = _ensaio(show, _data_isolada())
    _marcar_sumido(show)
    _remocoes.clear()
    marco = google.marco()
    _cancelar_ok(show, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    _esperar_threads()
    _garante(set(_remocoes_por_talento()) == {estado["t"]}, f"2b: elenco não avisado {_remocoes_por_talento()}")
    _garante(
        estado["usuarios"]["ens"]["id"] in {a[0] for a in _avisos_do_ato("evento.cancelado", show)},
        "2b: a equipe de Ensaio não foi avisada",
    )
    _garante(estado["eventos"][show] not in google.deletes(marco), "2b: o show marcado foi ao Google")
    _garante(estado["eventos"][ensaio] in google.deletes(marco), "2b: o ensaio do marcado não saiu do Google")


def c3_tudo_nada_divergente() -> None:
    tudo = _exemplo_padrao("3 tudo")
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=tudo["ev"])).get_json()
    _igual(imp.get("max_devolucao"), 1000, "3: max_devolucao")
    _cancelar_ok(tudo["ev"], _corpo_cancelar("tudo", imp["max_devolucao"]))
    _igual(_devolucoes(tudo["ev"])[0]["valor"], 1000, "3: Tudo preenche o total")
    nada = _exemplo_padrao("3 nada")
    _cancelar_ok(nada["ev"], _corpo_cancelar("nada", None, nome=None, pix=None))
    _garante(not _devolucoes(nada["ev"]), "3: Nada gerou gasto")
    _igual(_resumo_api(nada["ev"])["retido"], 1000, "3: Nada → retido = pago")
    div = _exemplo_padrao("3 divergente")
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=div["ev"])).get_json()
    avulsa = _devolucao_avulsa(div["ev"], 200)
    r = _cancelar(div["ev"], _corpo_cancelar("tudo", imp.get("max_devolucao", 1000)))
    _garante(r.status_code == 409 and _codigo(r) == "max_devolucao_mudou", f"3 divergente → {r.status_code} {_erro(r)}")
    _igual(_erro(r).get("max_devolucao"), 800, "3: max_devolucao recalculado")
    _nada_gravado(div["ev"], "3 divergente")
    _garante([d["id"] for d in _devolucoes(div["ev"])] == [avulsa], f"3 divergente: devoluções {_devolucoes(div['ev'])}")


def _deve_400(event_id: int, corpo: dict, campo: str, rotulo: str) -> None:
    r = _cancelar(event_id, corpo)
    _garante(r.status_code == 400, f"4 {rotulo} → {r.status_code} {_erro(r)}")
    _garante(campo in (_erro(r).get("fields") or {}), f"4 {rotulo}: sem fields.{campo}: {_erro(r)}")
    _nada_gravado(event_id, f"4 {rotulo}")


def c4_recusas_de_forma() -> None:
    ex = _exemplo_padrao("4 forma")
    ev = ex["ev"]
    corpo = _corpo_cancelar("parte", 600)
    corpo["devolucao"].pop("modo")
    _deve_400(ev, corpo, "devolucao_modo", "sem modo")
    _deve_400(ev, _corpo_cancelar("parte", 1500), "devolucao_valor", "acima do pago")
    _deve_400(ev, _corpo_cancelar("parte", 600, nome=None), "devolucao_nome", "Parte sem nome")
    _deve_400(ev, _corpo_cancelar("parte", 600, pix=None), "devolucao_pix", "Parte sem PIX")
    _deve_400(ev, _corpo_cancelar("parte", 600, imposto_retido=10), "imposto_retido", "imposto sem nota")
    com_nota = _exemplo_padrao("4 nota", nota=True)
    _deve_400(com_nota["ev"], _corpo_cancelar("parte", 600), "imposto_retido", "nota sem imposto")
    _deve_400(com_nota["ev"], _corpo_cancelar("parte", 600, imposto_retido=-1), "imposto_retido", "imposto negativo")
    r = _cliente("sa").get(ROTAS["impacto"].format(id=ev) + "?devolucao=abc")
    _garante(r.status_code == 400 and "devolucao" in (_erro(r).get("fields") or {}), f"4 prévia inválida → {r.status_code}")
    sem_pix = _evento("4 bv sem pix")
    acr = _bv(sem_pix, 200, recebedor=None, pix=None)
    _comprovante(sem_pix, 1000)
    _deve_400(sem_pix, _corpo_cancelar("parte", 600), f"bv_pix_{acr}", "BV sem PIX e sem bvs")
    # variante: com `bvs`, cancela, e o PIX vai ao acréscimo e à Planilha
    _cancelar_ok(sem_pix, _corpo_cancelar("parte", 600, bvs=[{"acrescimo_id": acr, "recebedor": f"{PREFIX}Parceiro", "pix": PIX}]))
    linha = _no_banco("SELECT bv_recipient, bv_pix FROM event_acrescimos WHERE id = :i", i=acr)[0]
    _garante(linha[1] == PIX and linha[0], f"4 variante: o PIX não foi ao acréscimo: {linha}")
    itens = _bv_planilha(sem_pix, _mes_evento(sem_pix))
    _garante(itens and itens[0]["pix_key"] == PIX, f"4 variante: Planilha sem o PIX: {itens}")
    _igual(itens[0]["amount"], 40, "4 variante: BV proporcional")


def c4_multas_recusadas() -> None:
    """4, a parte da H6: multa negativa e multa de vaga de outro evento no POST …/cancelar → 400."""
    show = _evento_com_elenco("4 multa", ["A"])
    papel = _escalar(show, estado["t"])
    outro = _evento_com_elenco("4 multa outro", ["A"])
    alheio = _escalar(outro, estado["t2"])
    for rotulo, multa, campo in (
        ("multa negativa", {"role_id": papel, "valor": -10}, f"multa_{papel}"),
        ("multa de outro evento", {"role_id": alheio, "valor": 10}, f"multa_{alheio}"),
    ):
        _deve_400(show, {"motivo": "verify 306", "devolucao": {"modo": "nada"}, "multas": [multa]}, campo, rotulo)
        _garante(not _multas_do_evento(show) and not _multas_do_evento(outro), f"4 {rotulo}: multa gravada")


def c5_pendente_ja_cancelado_duplo() -> None:
    pend = _exemplo_padrao("5 pendente")
    _devolucao_avulsa(pend["ev"], 100, status="pendente")
    r = _cancelar(pend["ev"])
    _garante(r.status_code == 409 and _codigo(r) == "devolucao_pendente", f"5 pendente → {r.status_code} {_erro(r)}")
    _nada_gravado(pend["ev"], "5 pendente")
    ja = _exemplo_padrao("5 já cancelado")
    _cancelar_ok(ja["ev"])
    devolucoes = [d["id"] for d in _devolucoes(ja["ev"])]
    r = _cancelar(ja["ev"])
    _garante(r.status_code == 409 and _codigo(r) == "ja_cancelado", f"5 já cancelado → {r.status_code} {_erro(r)}")
    _garante(_no_banco("SELECT count(*) FROM event_cancellations WHERE event_id = :i", i=ja["ev"])[0][0] == 1, "5: duas linhas congeladas")
    _garante([d["id"] for d in _devolucoes(ja["ev"])] == devolucoes, "5: o 2º POST mexeu nas devoluções")
    duplo = _exemplo_padrao("5 duplo")
    respostas: list = []

    def disparo():
        c = _cliente("sa")
        respostas.append(c.post(ROTAS["cancelar"].format(id=duplo["ev"]), json=_corpo_cancelar()))

    fios = [threading.Thread(target=disparo) for _ in range(2)]
    for f in fios:
        f.start()
    for f in fios:
        f.join(timeout=120)
    codigos = sorted(r.status_code for r in respostas)
    _garante(codigos == [200, 409], f"5 duplo: {codigos}")
    recusa = next(r for r in respostas if r.status_code == 409)
    _garante(_codigo(recusa) in ("ja_cancelado", "tente_de_novo"), f"5 duplo: código {_erro(recusa)}")
    n = _no_banco("SELECT count(*) FROM event_cancellations WHERE event_id = :i", i=duplo["ev"])[0][0]
    _garante(n == 1, f"5 duplo: {n} linhas em event_cancellations")
    _garante(len(_devolucoes(duplo["ev"])) == 1, "5 duplo: duas devoluções")


def c6_papeis() -> None:
    ex = _exemplo_padrao("6 papéis")
    cancelado = _exemplo_padrao("6 cancelado")
    _cancelar_ok(cancelado["ev"])
    devolucao = [(d["id"], q(d["valor"])) for d in _devolucoes(cancelado["ev"])]
    for apelido in ("com", "fig"):
        c = _cliente(apelido)
        r1 = c.post(ROTAS["cancelar"].format(id=ex["ev"]), json=_corpo_cancelar())
        r2 = c.patch(ROTAS["devolucao"].format(id=cancelado["ev"]), json={"devolucao_total": 700})
        r3 = c.get(ROTAS["impacto"].format(id=ex["ev"]) + "?devolucao=600")
        _garante(
            (r1.status_code, r2.status_code, r3.status_code) == (403, 403, 403),
            f"6 {apelido}: {(r1.status_code, r2.status_code, r3.status_code)}",
        )
    r = _cliente("fin").patch(ROTAS["devolucao"].format(id=cancelado["ev"]), json={"devolucao_total": 700})
    _garante(r.status_code == 403, f"6 FINANCEIRO no PATCH → {r.status_code}")
    _nada_gravado(ex["ev"], "6")
    _garante([(d["id"], q(d["valor"])) for d in _devolucoes(cancelado["ev"])] == devolucao, "6: a recusa mexeu na devolução do cancelado")


def c15_alterar_devolucao() -> None:
    a = _exemplo_padrao("15 a pagar", bv=False, comissao="a_pagar")
    _cancelar_ok(a["ev"], _corpo_cancelar("parte", 600))
    r = _alterar_devolucao(a["ev"], 800)
    _garante(r.status_code == 200, f"15 600→800 → {r.status_code} {_erro(r)}")
    _igual(_soma_vivas(a["ev"]), 10, "15: comissão 20 → 10")
    _igual(_resumo_api(a["ev"])["retido"], 200, "15: recalcula na hora")
    p = _exemplo_padrao("15 paga", bv=False, comissao="pago")
    with _com_hoje(_dia(10)):
        _cancelar_ok(p["ev"], _corpo_cancelar("parte", 600))
        _alterar_devolucao(p["ev"], 800)
        ajuste = _ajuste_negativo(p["ev"])
        _igual(ajuste["valor"], -90, "15: −80 → −90 no lugar")
        r = _alterar_devolucao(p["ev"], 500)
    _garante(r.status_code == 200, f"15 800→500 → {r.status_code} {_erro(r)}")
    depois = _ajuste_negativo(p["ev"])
    _garante(depois["id"] == ajuste["id"], "15: o ajuste não foi refeito no lugar")
    _igual(depois["valor"], -75, "15: −90 → −75 no lugar (Σ 25)")
    _igual(_soma_vivas(p["ev"]), 25, "15: Σ")
    # diminuir devolução paga → 409 abaixo do piso, nada gravado
    _no_banco_escrever(
        "UPDATE special_expenses SET payment_status = 'pago' WHERE event_id = :i AND category = :c",
        i=p["ev"],
        c=CATEGORIA_DEVOLUCAO,
    )
    antes = ([(d["id"], q(d["valor"]), d["pagamento"]) for d in _devolucoes(p["ev"])], _linhas_comissao(p["ev"]))
    r = _alterar_devolucao(p["ev"], 300)
    _garante(r.status_code == 409 and _codigo(r) == "abaixo_do_piso", f"15 diminuir paga → {r.status_code} {_erro(r)}")
    _garante(([(d["id"], q(d["valor"]), d["pagamento"]) for d in _devolucoes(p["ev"])], _linhas_comissao(p["ev"])) == antes, "15: o 409 gravou")
    # o −90 já liquidado: 800 → 500 faz nascer +15 ligado à liquidada, no primeiro repasse aberto
    lq = _exemplo_padrao("15 liquidado", bv=False, comissao="pago")
    with _com_hoje(_dia(10)):
        _cancelar_ok(lq["ev"], _corpo_cancelar("parte", 600))
        _alterar_devolucao(lq["ev"], 800)
        menos90 = _ajuste_negativo(lq["ev"])
        _no_banco_escrever("UPDATE commission_payments SET status = 'pago', paid_at = now() WHERE id = :i", i=menos90["id"])
        r = _alterar_devolucao(lq["ev"], 500)
    _garante(r.status_code == 200, f"15 liquidado 800→500 → {r.status_code} {_erro(r)}")
    linhas = _linhas_comissao(lq["ev"])
    m90 = next(x for x in linhas if x["id"] == menos90["id"])
    _garante(m90["status"] == "pago" and q(m90["valor"]) == q(-90), f"15: o −90 liquidado mudou {m90}")
    novos = [x for x in linhas if x["id"] not in (lq["linha"], menos90["id"])]
    _garante(len(novos) == 1 and q(novos[0]["valor"]) == q(15) and novos[0]["original_id"] is not None, f"15: o +15 não nasceu {novos}")
    _garante(
        novos[0]["venda_em"] == novos[0]["liberacao"] and (novos[0]["venda_em"].year, novos[0]["venda_em"].month) == (_dia(10).year, _dia(10).month),
        f"15: +15 fora do primeiro repasse aberto {novos[0]}",
    )
    # "Nada" → 300 em duas chamadas simultâneas → um complemento só
    n = _exemplo_padrao("15 nada", bv=False)
    _cancelar_ok(n["ev"], _corpo_cancelar("nada", None, nome=None, pix=None))
    respostas: list = []

    def disparo():
        respostas.append(
            _cliente("sa").patch(
                ROTAS["devolucao"].format(id=n["ev"]),
                json={"devolucao_total": 300, "nome": f"{PREFIX}Cliente", "pix": PIX},
            )
        )

    fios = [threading.Thread(target=disparo) for _ in range(2)]
    for f in fios:
        f.start()
    for f in fios:
        f.join(timeout=120)
    codigos = sorted(x.status_code for x in respostas)
    _garante(codigos in ([200, 200], [200, 409]), f"15 simultâneo: {codigos} {[_erro(x) for x in respostas]}")
    for x in respostas:
        if x.status_code == 409:
            _garante(_codigo(x) == "tente_de_novo", f"15 simultâneo: código {_erro(x)}")
    devs = _devolucoes(n["ev"])
    _garante(len(devs) == 1, f"15 simultâneo: {devs}")
    _igual(devs[0]["valor"], 300, "15 simultâneo: complemento")


def c16_comprovante_no_cancelado() -> None:
    ex = _exemplo_padrao("16 comprovante", comissao="a_pagar")
    _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    r = _post_comprovante("sa", ex["ev"], 200)
    _garante(r.status_code == 201, f"16 Superadmin → {r.status_code} {_erro(r)}")
    resumo = _resumo_api(ex["ev"])
    _igual(resumo["retido"], 600, "16: retido")
    _igual(_soma_vivas(ex["ev"]), 27, "16: comissão do retido")
    _igual(_bv_planilha(ex["ev"], _mes_evento(ex["ev"]))[0]["amount"], 60, "16: BV do retido")
    r = _post_comprovante("cast", ex["ev"], 50)
    _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"16 CASTING comprovante → {r.status_code} {_erro(r)}")
    r = _alterar_devolucao(ex["ev"], 700, apelido="cast")
    _garante(r.status_code == 403, f"16 CASTING no PATCH → {r.status_code}")
    # pago abaixo do devolvido
    pagamentos = _no_banco("SELECT id FROM event_payments WHERE event_id = :i ORDER BY id", i=ex["ev"])
    r = _cliente("sa").delete(ROTAS["comprovante_um"].format(id=pagamentos[0][0]))
    _garante(r.status_code == 409 and _codigo(r) == "pago_abaixo_do_devolvido", f"16 abaixo do devolvido → {r.status_code} {_erro(r)}")
    _garante(len(_no_banco("SELECT id FROM event_payments WHERE event_id = :i", i=ex["ev"])) == 2, "16: excluiu o comprovante")


def c16_variante_paid_amount() -> None:
    ex = _exemplo_padrao("16 paid_amount")
    _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    item = _bv_planilha(ex["ev"], _mes_evento(ex["ev"]))[0]
    r = _cliente("fin").post(
        ROTAS["planilha_status"],
        json={"item_type": "bv", "item_id": item["id"], "status": "pago", "valor_esperado": 99},
    )
    _garante(r.status_code == 409 and _codigo(r) == "valor_mudou", f"16 divergente → {r.status_code} {_erro(r)}")
    _garante(re.search(r"(?<![\d.,])40(?:,00)?(?![\d])", _erro(r).get("message") or ""), f"16 divergente: sem o valor atual: {_erro(r)}")
    _garante(_no_banco("SELECT bv_payment_status FROM event_acrescimos WHERE id = :i", i=ex["bv"])[0][0] in (None, "nao_pago"), "16: o divergente gravou")
    r = _cliente("fin").post(
        ROTAS["planilha_status"],
        json={"item_type": "bv", "item_id": item["id"], "status": "pago", "valor_esperado": 40},
    )
    _garante(r.status_code == 200, f"16 marcar pago → {r.status_code} {_erro(r)}")
    _post_comprovante("sa", ex["ev"], 200)
    itens = _bv_planilha(ex["ev"], _mes_evento(ex["ev"]))
    _garante(len(itens) == 1, f"16 variante: acerto ao parceiro {itens}")
    _igual(itens[0]["amount"], 40, "16 variante: BV pago fica em 40")
    r = _cliente("fin").post(ROTAS["planilha_status"], json={"item_type": "bv", "item_id": item["id"], "status": "nao_pago"})
    _garante(r.status_code == 200, f"16 desfazer → {r.status_code}")
    _igual(_bv_planilha(ex["ev"], _mes_evento(ex["ev"]))[0]["amount"], 60, "16 variante: desfeito volta a 60")
    tudo = _exemplo_padrao("16 não a pagar")
    _cancelar_ok(tudo["ev"], _corpo_cancelar("tudo", 1000))
    r = _cliente("fin").post(
        ROTAS["planilha_status"], json={"item_type": "bv", "item_id": tudo["bv"], "status": "pago"}
    )
    _garante(r.status_code == 409 and _codigo(r) == "bv_nao_esta_a_pagar", f"16 não a pagar → {r.status_code} {_erro(r)}")
    _garante(_no_banco("SELECT bv_payment_status FROM event_acrescimos WHERE id = :i", i=tudo["bv"])[0][0] in (None, "nao_pago"), "16: o não a pagar gravou")


def c16_vivo() -> None:
    from app.financeiro import comissoes_ops

    avulso = _exemplo_padrao("16 vivo avulso", bv=False, comissao="a_pagar")
    principal = _exemplo_padrao("16 vivo principal", bv=False, comissao="a_pagar")
    dia = _evento("16 vivo dia", venda=None)
    _agrupar(principal["ev"], dia)
    for ev in (avulso["ev"], dia):
        r = _post_comprovante("com", ev, 100)
        _garante(r.status_code == 201 and not _codigo(r), f"16-vivo comprovante {ev} → {r.status_code} {_erro(r)}")
        r = _cliente("com").post(
            ROTAS["reembolso"].format(id=ev),
            data={"description": f"{PREFIX}reembolso", "amount": "50", "file": _arquivo("nf.pdf")},
            content_type="multipart/form-data",
        )
        _garante(r.status_code == 201 and not _codigo(r), f"16-vivo reembolso {ev} → {r.status_code} {_erro(r)}")
    for ev, valor in ((avulso["ev"], 500), (principal["ev"], 200)):
        r = _cliente("com").put(
            ROTAS["parcelas"].format(id=ev),
            json={"items": [{"due_date": (_hoje_sp() + timedelta(days=10)).isoformat(), "amount": valor}]},
        )
        _garante(r.status_code == 200 and not _codigo(r), f"16-vivo parcela {ev} → {r.status_code} {_erro(r)}")
    # Sem abrir Comissões nem a Planilha (o resync regravaria a linha e esconderia o erro): a linha
    # semeada (2.000 × 5% = 100) fica, e é também a `_event_commission` de hoje.
    with app.app_context():
        s = db.session.get(SiteSetting, 1)
        esperado = {
            ev: comissoes_ops._event_commission(db.session.get(CalendarEvent, ev), s)
            for ev in (avulso["ev"], principal["ev"])
        }
    for ev, valor in esperado.items():
        _igual(valor, 100, f"16-vivo: _event_commission de {ev}")
        linhas = _linhas_comissao(ev)
        _garante(len(linhas) == 1, f"16-vivo: linhas de {ev} {linhas}")
        _igual(linhas[0]["valor"], 100, f"16-vivo: as portas mexeram na comissão a pagar de {ev}")


def _patch_gasto(gasto_id: int, apelido: str = "fin", **mudar):
    g = _no_banco(
        "SELECT description, category, amount, expense_date, disbursement_type, supplier_name, "
        "supplier_pix, event_id FROM special_expenses WHERE id = :i",
        i=gasto_id,
    )[0]
    corpo = {
        "description": g[0],
        "category": g[1],
        "amount": float(g[2]),
        "expense_date": g[3].isoformat(),
        "disbursement_type": g[4] or "",
        "supplier_name": g[5] or "",
        "supplier_pix": g[6] or "",
        "event_id": g[7],
    }
    corpo.update(mudar)
    return _cliente(apelido).patch(ROTAS["gasto"].format(id=gasto_id), json=corpo)


def c18_gastos_extras() -> None:
    ex = _exemplo_padrao("18 gastos")
    _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    dev = _devolucoes(ex["ev"])[0]["id"]
    r = _patch_gasto(dev)
    _garante(r.status_code == 200, f"18 Salvar sem mexer → {r.status_code} {_erro(r)}")
    linha = _no_banco(
        "SELECT disbursement_type, supplier_name, supplier_pix, approved_with_edits FROM special_expenses WHERE id = :i",
        i=dev,
    )[0]
    _garante(linha[0] == "cliente" and linha[1] and linha[2] == PIX and not linha[3], f"18 Salvar: {linha}")
    r = _patch_gasto(dev, supplier_pix="novo-pix@exemplo.test")
    _garante(r.status_code == 200, f"18 corrigir PIX → {r.status_code}")
    _garante(
        _no_banco("SELECT supplier_pix FROM special_expenses WHERE id = :i", i=dev)[0][0] == "novo-pix@exemplo.test",
        "18: o PIX não foi trocado",
    )
    intacta = _no_banco("SELECT amount, expense_date, category, event_id, status FROM special_expenses WHERE id = :i", i=dev)[0]
    outro = _evento("18 outro", venda=None)
    for campo, valor in (
        ("amount", 500),
        ("expense_date", (_hoje_sp() - timedelta(days=3)).isoformat()),
        ("category", "Outros"),
        ("event_id", outro),
    ):
        r = _patch_gasto(dev, **{campo: valor})
        _garante(
            r.status_code == 409 and _codigo(r) == "devolucao_travada" and _erro(r).get("event_id") == ex["ev"],
            f"18 mudar {campo} → {r.status_code} {_erro(r)}",
        )
    for rota in ("gasto_aprovar", "gasto_rejeitar"):
        r = _cliente("fin").post(ROTAS[rota].format(id=dev), json={"motivo": "verify"})
        _garante(
            r.status_code == 409 and _codigo(r) == "devolucao_travada" and _erro(r).get("event_id") == ex["ev"],
            f"18 {rota} → {r.status_code} {_erro(r)}",
        )
    r = _cliente("fin").delete(ROTAS["gasto"].format(id=dev))
    _garante(
        r.status_code == 409 and _codigo(r) == "devolucao_travada" and _erro(r).get("event_id") == ex["ev"],
        f"18 excluir → {r.status_code} {_erro(r)}",
    )
    r = _cliente("fin").post(ROTAS["gasto_vincular"].format(id=dev), json={"event_id": outro})
    _garante(r.status_code == 409 and _codigo(r) == "devolucao_travada", f"18 vincular → {r.status_code} {_erro(r)}")
    _garante(
        _no_banco("SELECT amount, expense_date, category, event_id, status FROM special_expenses WHERE id = :i", i=dev)[0] == intacta,
        "18: um 409 travado gravou na devolução",
    )
    r = _cliente("fin").post(
        ROTAS["gastos"],
        data={
            "description": f"{PREFIX}tentativa",
            "category": "Outros",
            "amount": "10",
            "expense_date": _hoje_sp().isoformat(),
            "disbursement_type": "cliente",
            "supplier_name": "x",
            "supplier_pix": "y",
            "receipt": _arquivo("r.pdf"),
        },
        content_type="multipart/form-data",
    )
    _garante(r.status_code == 400 and "disbursement_type" in (_erro(r).get("fields") or {}), f"18 POST cliente → {r.status_code} {_erro(r)}")
    comum = _gasto_comum(None, 30)
    r = _patch_gasto(comum, disbursement_type="cliente")
    _garante(r.status_code == 400, f"18 PATCH fornecedor → cliente → {r.status_code} {_erro(r)}")
    vivo = _evento("18 vivo", venda=None)
    viva = _devolucao_avulsa(vivo, 80)
    r = _patch_gasto(viva, amount=90)
    _garante(r.status_code == 200, f"18 devolução de evento vivo editável → {r.status_code} {_erro(r)}")
    # 18-inverso
    retido = _resumo_api(ex["ev"])["retido"]
    comum_ligado = _gasto_comum(ex["ev"], 40)
    multa = _gasto_comum(ex["ev"], 60, categoria=CATEGORIA_MULTA)
    for gid in (comum_ligado, multa):
        r = _patch_gasto(gid, category=CATEGORIA_DEVOLUCAO)
        _garante(
            r.status_code == 409 and _codigo(r) == "devolucao_travada" and "category" in (_erro(r).get("fields") or {}),
            f"18-inverso categoria {gid} → {r.status_code} {_erro(r)}",
        )
    r = _patch_gasto(viva, event_id=ex["ev"])
    _garante(
        r.status_code == 409 and _codigo(r) == "devolucao_travada" and "event_id" in (_erro(r).get("fields") or {}),
        f"18-inverso vínculo → {r.status_code} {_erro(r)}",
    )
    _igual(_resumo_api(ex["ev"])["retido"], retido, "18-inverso: o retido mudou")


def _orcamento_de(dono: str) -> int:
    from app.models import OrcamentoHistory

    with app.app_context():
        e = OrcamentoHistory(
            user_id=estado["usuarios"][dono]["id"],
            client_name=f"{PREFIX}orçamento",
            event_location=f"{PREFIX}Salão",
            event_date=(_hoje_sp() + timedelta(days=60)).isoformat(),
            total_1h=Decimal("1000"),
            total_2h=Decimal("1500"),
            total_3h=Decimal("2000"),
            total_4h=Decimal("2500"),
            has_show=False,
            form_snapshot=json.dumps({"acrescimos": [], "nota_fiscal": False, "performers": []}),
        )
        db.session.add(e)
        db.session.commit()
        estado["orcamentos"].append(e.id)
        return e.id


def c19_orcamento_excluir_acrescimos() -> None:
    ex = _exemplo_padrao("19 portas")
    _cancelar_ok(ex["ev"])
    antes = _retrato_tabelas([ex["ev"]])
    orc_outro = _orcamento_de("vend2")  # de outro autor: prova que o 409 vem antes da autoria
    for apelido in ("sa", "com", "fin"):
        r = _cliente(apelido).patch(ROTAS["orcamento"].format(id=ex["ev"]), json={"orcamento_history_id": orc_outro})
        _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"19 orçamento {apelido} → {r.status_code} {_erro(r)}")
    r = _cliente("sa").delete(ROTAS["excluir"].format(id=ex["ev"]))
    _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"19 DELETE Superadmin → {r.status_code} {_erro(r)}")
    r = _cliente("com").delete(ROTAS["excluir"].format(id=ex["ev"]))
    _garante(r.status_code == 403, f"19 DELETE COMERCIAL → {r.status_code}")
    for apelido in ("com", "fin"):
        r = _cliente(apelido).put(ROTAS["acrescimos"].format(id=ex["ev"]), json={"items": []})
        _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"19 acréscimos {apelido} → {r.status_code} {_erro(r)}")
    _garante(_retrato_tabelas([ex["ev"]]) == antes, "19: algo mudou")


def c25_payload() -> None:
    ex = _exemplo_padrao("25 payload", comissao="a_pagar", nota=True)
    _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600, imposto_retido=64))
    sa = _detalhe("sa", ex["ev"])
    res = sa["event"]["cancelamento"]
    _igual(res["pago"], 1000, "25: pago")
    _igual(res["devolvido"], 600, "25: devolvido")
    _igual(res["retido"], 400, "25: retido")
    _igual(res["comissao"]["retido"], 18, "25: comissão do retido")
    _igual(res["bvs"][0]["conta"], 40, "25: BV do retido")
    _igual(res.get("imposto"), 64, "25: imposto para quem tem show_financeiro")
    _garante(res["devolucoes"][0].get("pix") == PIX and res["bvs"][0].get("pix") == PIX, f"25: PIX ausente para quem tem show_financeiro {res}")
    _garante("kpi" not in sa or sa.get("kpi") is None, "25: `kpi` presente no cancelado")
    _garante(sa["flags"].get("can_edit_pagamentos") is True, "25: can_edit_pagamentos do Superadmin")
    com = _detalhe("com", ex["ev"])
    res_c = com["event"].get("cancelamento")
    _garante(res_c is not None, "25: COMERCIAL sem o bloco (show_comercial)")
    _garante(not any(d.get("pix") for d in res_c.get("devolucoes", [])), "25: PIX para quem não tem show_financeiro")
    for chave in ("comissao", "bvs", "imposto", "taxa"):
        _garante(res_c.get(chave) is None, f"25: `{chave}` para quem não tem show_financeiro: {res_c.get(chave)}")
    cast = _detalhe("cast", ex["ev"])
    _garante(not cast["event"].get("cancelamento"), "25: CASTING viu o bloco")
    vivo = _exemplo_padrao("25 vivo")
    sa_v = _detalhe("sa", vivo["ev"]).get("venda") or {}
    com_v = _detalhe("com", vivo["ev"]).get("venda") or {}
    _garante(sa_v.get("pode_mudar_taxa") is True, "25 vivo: Superadmin sem pode_mudar_taxa")
    _garante(com_v.get("pode_mudar_taxa") is False, "25 vivo: COMERCIAL com pode_mudar_taxa")
    _garante(sa_v.get("pode_trocar_vendedor") is True, "25 vivo: Superadmin sem pode_trocar_vendedor")
    _garante(com_v.get("pode_trocar_vendedor") is False, "25 vivo: COMERCIAL troca vendedor já gravado")


def c28_rbac() -> None:
    ex = _exemplo_padrao("28 rbac")
    cancelado = _exemplo_padrao("28 cancelado")
    _cancelar_ok(cancelado["ev"])
    anon = app.test_client()
    for metodo, url in (
        ("post", ROTAS["cancelar"].format(id=ex["ev"])),
        ("patch", ROTAS["devolucao"].format(id=cancelado["ev"])),
        ("get", ROTAS["impacto"].format(id=ex["ev"]) + "?devolucao=600"),
        ("get", ROTAS["cancelamentos"]),
    ):
        r = getattr(anon, metodo)(url, json={})
        _garante(r.status_code == 401, f"28 sem sessão {metodo} {url} → {r.status_code}")
    r = _cliente("com").patch(ROTAS["devolucao"].format(id=999999999), json={"devolucao_total": 1})
    _garante(r.status_code == 404, f"28 inexistente → {r.status_code} (404 antes do 403)")
    r = _cliente("fin").post(ROTAS["cancelar"].format(id=ex["ev"]), json=_corpo_cancelar())
    _garante(r.status_code == 403, f"28 FINANCEIRO cancela → {r.status_code}")
    r = _post_comprovante("fin", cancelado["ev"], 10)
    _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"28 FINANCEIRO comprovante → {r.status_code} {_erro(r)}")
    for apelido in ("mkt", "ens", "a3d"):
        r = _cliente(apelido).get(ROTAS["cancelamentos"])
        _garante(r.status_code == 403, f"28 {apelido} na página → {r.status_code}")
    c = _cliente("sa")
    c.post(ROTAS["impersonate"], json={"role": RoleName.COMERCIAL})
    corpo = c.get(ROTAS["detalhe"].format(id=cancelado["ev"])).get_json()
    _garante(not corpo["flags"].get("can_delete"), "28 Ver como: can_delete verdadeiro")
    _garante(not corpo["flags"].get("can_edit_pagamentos"), "28 Ver como: can_edit_pagamentos verdadeiro no cancelado")
    r = c.post(ROTAS["cancelar"].format(id=ex["ev"]), json=_corpo_cancelar())
    _garante(r.status_code == 200, f"28 Ver como: a API recusou o papel real → {r.status_code} {_erro(r)}")


def c31_google() -> None:
    falha = _exemplo_padrao("31 falha")
    google.falhar_delete.add(estado["eventos"][falha["ev"]])
    corpo = _cancelar_ok(falha["ev"])
    _garante(corpo.get("aviso"), "31: falha do Google sem aviso")
    _garante("duble" not in (corpo.get("aviso") or "").lower(), "31: o aviso traz o texto cru do erro")
    _igual(corpo["resumo"]["retido"], 400, "31: resumo certo apesar da falha")
    travado = _exemplo_padrao("31 trava")
    app.config[TRAVA] = True
    marco = google.marco()
    corpo = _cancelar_ok(travado["ev"])
    _garante(not google.chamadas[marco:], f"31: com a trava, o Google foi chamado: {google.chamadas[marco:]}")
    _garante(corpo.get("aviso"), "31: com a trava, sem aviso")
    app.config[TRAVA] = False
    gid = estado["eventos"][falha["ev"]]
    antes = _no_banco("SELECT title, start_at, end_at, location FROM calendar_events WHERE id = :i", i=falha["ev"])
    google.itens[gid]["summary"] = "(CORP) V306 31 MUDOU NO GOOGLE"
    google.itens[gid]["location"] = "Outro lugar, 2"
    _remocoes.clear()
    marco = google.marco()
    r = _cliente("sa").post(ROTAS["sync"].format(id=falha["ev"]))
    _esperar_threads()
    _garante(r.status_code < 500, f"31 Sincronizar → {r.status_code}")
    _garante(
        _no_banco("SELECT title, start_at, end_at, location FROM calendar_events WHERE id = :i", i=falha["ev"]) == antes,
        "31: o Sincronizar regravou o cancelado com o que veio do Google",
    )
    _garante(not _remocoes, "31: o Sincronizar mandou e-mail de remoção do cancelado")
    _garante(
        not [c for c in google.chamadas[marco:] if c[0] in ("patch", "insert", "delete")],
        f"31: o Sincronizar mexeu no Google do cancelado: {google.chamadas[marco:]} ({r.status_code})",
    )
    _garante(_cancelado_em(falha["ev"]) is not None, "31: o Sincronizar descancelou")


def c32_pago_maior_e_sem_valor() -> None:
    ev = _evento("32 pago maior")
    _bv(ev, 200)
    _comprovante(ev, 2500)
    _linha_comissao(ev, 90)
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=ev)).get_json()
    _igual(imp.get("max_devolucao"), 2500, "32: Tudo devolve o pago")
    _cancelar_ok(ev, _corpo_cancelar("nada", None, nome=None, pix=None))
    _igual(_soma_vivas(ev), 90, "32: comissão = cheia com pago maior que a venda")
    sem_valor = _evento("32 sem valor")
    _comprovante(sem_valor, None)
    _comprovante(sem_valor, 500)
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=sem_valor)).get_json()
    _garante(imp.get("comprovantes_sem_valor") == 1, f"32: comprovantes_sem_valor {imp.get('comprovantes_sem_valor')}")
    _igual(imp.get("pago"), 500, "32: comprovante sem valor conta zero")


def c34_excluir_usuario() -> None:
    ex = _exemplo_padrao("34 vendedor", bv=False)
    _cancelar_ok(ex["ev"])
    novo = _usuario("vend34", RoleName.COMERCIAL)
    _no_banco_escrever("UPDATE event_cancellations SET seller_id = :u WHERE event_id = :e", u=novo["id"], e=ex["ev"])
    r = _cliente("sa").delete(f"/api/admin/users/{novo['id']}")
    _garante(r.status_code in (400, 409) and "cancelamento" in (_erro(r).get("message") or "").lower(), f"34 → {r.status_code} {_erro(r)}")
    _garante(_no_banco("SELECT 1 FROM users WHERE id = :i", i=novo["id"]), "34: o vendedor congelado foi apagado")
    benef = _usuario("benef34", RoleName.COMERCIAL)
    _no_banco_escrever(
        "UPDATE event_cancellations SET seller_id = :v, commission_seller_id = :b WHERE event_id = :e",
        v=estado["usuarios"]["vend"]["id"],
        b=benef["id"],
        e=ex["ev"],
    )
    r = _cliente("sa").delete(f"/api/admin/users/{benef['id']}")
    _garante(r.status_code in (400, 409) and "cancelamento" in (_erro(r).get("message") or "").lower(), f"34 variante → {r.status_code} {_erro(r)}")
    _garante(_no_banco("SELECT 1 FROM users WHERE id = :i", i=benef["id"]), "34: o beneficiário congelado foi apagado")


def c36_devolucao_na_planilha() -> None:
    ex = _exemplo_padrao("36 planilha")
    _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    dev = _devolucoes(ex["ev"])[0]
    mes = _mes(dev["data"])
    _garante(mes == _mes(_hoje_sp()), f"36: devolução no mês {mes}")
    itens = [i for i in _planilha(mes) if i["type"] == "expense" and int(i["id"]) == dev["id"]]
    _garante(itens, "36: a devolução não aparece na Planilha do mês do cancelamento")
    for status in ("no_banco", "pago", "nao_pago"):
        r = _cliente("fin").post(
            ROTAS["planilha_status"],
            json={"item_type": "expense", "item_id": dev["id"], "status": status, "valor_esperado": 600},
        )
        _garante(r.status_code == 200, f"36 marcar {status} → {r.status_code} {_erro(r)}")
        _garante(
            _no_banco("SELECT payment_status FROM special_expenses WHERE id = :i", i=dev["id"])[0][0] == status,
            f"36: a trava alcançou o status de pagamento ({status})",
        )
    # paga, a primeira não absorve: o "Alterar devolução" para 900 faz nascer um complemento de 300,
    # no mês em que nasce (o dia 10 do mês seguinte)
    r = _cliente("fin").post(
        ROTAS["planilha_status"],
        json={"item_type": "expense", "item_id": dev["id"], "status": "pago", "valor_esperado": 600},
    )
    _garante(r.status_code == 200, f"36 marcar pago → {r.status_code} {_erro(r)}")
    seguinte = _mes_seguinte(_hoje_sp())
    with _com_hoje(date(seguinte.year, seguinte.month, 10)):
        r = _alterar_devolucao(ex["ev"], 900)
    _garante(r.status_code == 200, f"36 complemento → {r.status_code} {_erro(r)}")
    devs = _devolucoes(ex["ev"])
    _garante(sum(Decimal(d["valor"]) for d in devs) == 900, f"36: total {devs}")
    novas = [d for d in devs if d["id"] != dev["id"]]
    _garante(len(novas) == 1 and q(novas[0]["valor"]) == q(300) and novas[0]["pagamento"] == "nao_pago", f"36: complemento {novas}")
    _garante(_mes(novas[0]["data"]) == _mes(seguinte), f"36: complemento fora do mês em que nasce ({novas[0]['data']})")
    itens = [i for i in _planilha(_mes(seguinte)) if i["type"] == "expense" and int(i["id"]) == novas[0]["id"]]
    _garante(itens, "36: o complemento não aparece na Planilha do mês em que nasce")


def c_codigos_uniao_ts() -> None:
    """Os 18 códigos: o conjunto Python e a união TS têm os mesmos membros (data-model §6.2)."""
    from app import constants

    py = getattr(constants, "CODIGOS_RECUSA_DO_CANCELAMENTO", None)
    _garante(py is not None and len(py) == 18, f"CODIGOS_RECUSA_DO_CANCELAMENTO: {py}")
    ts = (REPO_ROOT / "frontend/apps/internal/src/lib/eventOps.ts").read_text(encoding="utf-8")
    m = re.search(r"export type CodigoRecusaCancelamento\s*=([^;]+);", ts)
    if not m:
        raise Bloqueado("a união CodigoRecusaCancelamento nasce na T048")
    membros = set(re.findall(r'"([a-z_]+)"', m.group(1)))
    _garante(membros == set(py), f"união TS × Python: {sorted(membros ^ set(py))}")


# ── B3 · História 3 ────────────────────────────────────────────────────────────────────────────
def c32_dre_retido_inteiro() -> None:
    """32, a parte da DRE: pago maior que a venda, Nada → o retido inteiro (2.500) entra na DRE."""
    inicio, fim = _mes_corrente()
    antes = _dre(inicio, fim)["dre"]["total"]
    ev = _evento("32 dre")
    _comprovante(ev, 2500)
    _cancelar_ok(ev, _corpo_cancelar("nada", None, nome=None, pix=None))
    _igual(_delta(antes, _dre(inicio, fim)["dre"]["total"], "receita_bruta"), 2500, "32: DRE com o retido inteiro")

def _mes_corrente() -> tuple[date, date]:
    h = _hoje_sp()
    inicio = date(h.year, h.month, 1)
    return inicio, _mes_seguinte(inicio) - timedelta(days=1)


def _dre_jinja(inicio: date, fim: date) -> dict:
    """A DRE antiga pelo `template_rendered` (o Jinja ainda está vivo)."""
    from flask import template_rendered

    capturado: dict = {}

    def gravar(_sender, template, context, **_k):
        if template.name == "financeiro/dashboard.html":
            capturado.update(context)

    template_rendered.connect(gravar, app)
    try:
        r = _cliente("fin").get(ROTAS["dre_jinja"].format(a=inicio.isoformat(), b=fim.isoformat()))
    finally:
        template_rendered.disconnect(gravar, app)
    _garante(r.status_code == 200 and capturado, f"DRE Jinja → {r.status_code}")
    return capturado


def _delta(antes: dict, depois: dict, chave: str) -> Decimal:
    return q(Decimal(str(depois[chave])) - Decimal(str(antes[chave])))


_SONDA_DRE = r"""
import json, os
import datetime as _dt
from datetime import timedelta

_DATETIME, _DATE = _dt.datetime, _dt.date
FIXO = _DATETIME.fromisoformat(os.environ["V306_RELOGIO"])


class _MetaDatetime(type):
    def __instancecheck__(cls, obj):
        return isinstance(obj, _DATETIME)


class _MetaDate(type):
    def __instancecheck__(cls, obj):
        return isinstance(obj, _DATE)


class _Relogio(_DATETIME, metaclass=_MetaDatetime):
    @classmethod
    def now(cls, tz=None):
        return FIXO if tz is None else FIXO.replace(tzinfo=tz)

    @classmethod
    def utcnow(cls):
        return FIXO + timedelta(hours=3)


class _Data(_DATE, metaclass=_MetaDate):
    @classmethod
    def today(cls):
        return FIXO.date()


from app import create_app
app = create_app()
app.config["TESTING"] = True
import sys
import app.constants as constants
import app.financeiro.routes as fin_routes
import app.api.financeiro_read as fin_read
import app.gastos.gastos_ops as gastos_ops
gastos_ops.ensure_recurring_entries = lambda *a, **k: None
_NOW = constants.now_sp
for nome, mod in list(sys.modules.items()):
    if mod is None or not (nome == "app" or nome.startswith("app.")):
        continue
    if getattr(mod, "datetime", None) is _DATETIME:
        mod.datetime = _Relogio
    if getattr(mod, "date", None) is _DATE:
        mod.date = _Data
    if getattr(mod, "now_sp", None) is _NOW:
        mod.now_sp = lambda: FIXO
c = app.test_client()
c.post("/api/auth/login", json={"email": os.environ["V306_EMAIL"], "password": os.environ["V306_SENHA"]})
r = c.get(os.environ["V306_URL"])
print(json.dumps(r.get_json()["dre"]))
"""


def _dre_main(inicio: date, fim: date) -> dict:
    """A DRE da `main` (subprocesso, mesmo banco) com o relógio fixo no "agora" desta rodada."""
    return _sonda(
        _SONDA_DRE,
        lado="main",
        env_extra={
            "V306_EMAIL": estado["usuarios"]["fin"]["email"],
            "V306_SENHA": SENHA,
            "V306_URL": ROTAS["dre"].format(a=inicio.isoformat(), b=fim.isoformat()),
            "V306_RELOGIO": datetime.now().replace(microsecond=0).isoformat(),
        },
    )


_CHAVES_DRE = ("receita_bruta", "impostos", "cpv", "comissoes", "gastos_extras", "resultado_liquido", "retido_cancelamentos")


def c20_dre_do_mes_do_cancelamento() -> None:
    inicio, fim = _mes_corrente()
    antes = _dre(inicio, fim)["dre"]
    antes_main = _dre_main(inicio, fim)
    ex = _exemplo_padrao("20 dre", comissao="a_pagar")
    _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    depois_corpo = _dre(inicio, fim)
    depois = depois_corpo["dre"]
    for visao in ("realizado", "total"):
        a, d = antes[visao], depois[visao]
        _igual(_delta(a, d, "receita_bruta"), 400, f"20 {visao}: receita bruta")
        _igual(_delta(a, d, "cpv"), 40, f"20 {visao}: custo (BV do retido)")
        _igual(_delta(a, d, "comissoes"), 18, f"20 {visao}: comissões")
        _igual(_delta(a, d, "gastos_extras"), 0, f"20 {visao}: gastos extras sem a devolução")
        _igual(_delta(a, d, "resultado_liquido"), 342, f"20 {visao}: resultado")
        _igual(d.get("retido_cancelamentos"), Decimal(str(a.get("retido_cancelamentos") or 0)) + 400, f"20 {visao}: linha do retido")
    _igual(_delta(antes["projetado"], depois["projetado"], "resultado_liquido"), 0, "20: Projetado mudou")
    jinja = _dre_jinja(inicio, fim)
    for visao, chave in (("realizado", "drg_realizado"), ("projetado", "drg_projetado"), ("total", "drg_total")):
        for k in _CHAVES_DRE:
            _garante(k in jinja[chave], f"20: o Jinja ({visao}) não tem {k}")
            _igual(jinja[chave][k], depois[visao][k], f"20: API × Jinja ({visao}.{k})")
    depois_main = _dre_main(inicio, fim)
    _igual(
        Decimal(str(depois_main["total"]["resultado_liquido"])) - Decimal(str(antes_main["total"]["resultado_liquido"])),
        -600,
        "20 mutação: a main tem de dar −600",
    )
    # num mês sem cancelado, as chaves estão presentes e o painel vem com quantidade 0
    vazio = _dre(date(2047, 1, 1), date(2047, 1, 31))
    for visao in ("realizado", "projetado", "total"):
        _garante("retido_cancelamentos" in vazio["dre"][visao] and "n_cancelados" in vazio["dre"][visao], f"20: chaves ausentes em {visao}")
    _garante((vazio["paineis"].get("cancelamentos") or {}).get("quantidade") == 0, "20: paineis.cancelamentos sem quantidade 0")


def _tendencia(corpo: dict) -> dict:
    return {m["label"]: m for m in corpo["paineis"]["monthly_trend"]}


def _dia_do_mes_corrente() -> datetime:
    """Um dia do mês corrente para o evento que precisa estar na Tendência (6 meses até hoje)."""
    hoje = _hoje_sp()
    dia = hoje + timedelta(days=1) if hoje.day < 27 else hoje - timedelta(days=1)
    return datetime.combine(dia, datetime.min.time()).replace(hour=19)


def c21_mes_do_evento_tendencia_e_variantes() -> None:
    inicio, fim = _mes_corrente()
    # mês do evento: antes do ato a venda viva está lá; depois, nada do evento fica (−2.000, −BV, −comissão)
    ex = _exemplo_padrao("21 nota", nota=True)
    mes_ev = _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=ex["ev"])[0][0].date()
    ini_ev = date(mes_ev.year, mes_ev.month, 1)
    fim_ev = _mes_seguinte(ini_ev) - timedelta(days=1)
    antes_ev = _dre(ini_ev, fim_ev)["dre"]["total"]
    antes = _dre(inicio, fim)["dre"]["total"]
    _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600, imposto_retido=64))
    depois = _dre(inicio, fim)
    _igual(_delta(antes, depois["dre"]["total"], "impostos"), 64, "21: imposto gravado")
    _igual(_delta(antes, depois["dre"]["total"], "resultado_liquido"), 278, "21: com nota")
    depois_ev = _dre(ini_ev, fim_ev)["dre"]["total"]
    _igual(_delta(antes_ev, depois_ev, "receita_bruta"), -2000, "21: a venda do cancelado ficou no mês do evento")
    _igual(_delta(antes_ev, depois_ev, "cpv"), -200, "21: o BV do cancelado ficou no mês do evento")
    _igual(_delta(antes_ev, depois_ev, "comissoes"), -90, "21: a comissão do cancelado ficou no mês do evento")
    # Tendência: sem os 2.000 no mês do evento e com +400 no do cancelamento (aqui, o mesmo mês)
    rotulo = f"{inicio.month:02d}/{str(inicio.year)[2:]}"
    tend = _evento("21 tendência", inicio=_dia_do_mes_corrente())
    _bv(tend, 200)
    _comprovante(tend, 1000)
    t_antes = _tendencia(_dre(inicio, fim))[rotulo]
    _cancelar_ok(tend, _corpo_cancelar("parte", 600))
    t_depois = _tendencia(_dre(inicio, fim))[rotulo]
    _igual(Decimal(str(t_depois["receita"])) - Decimal(str(t_antes["receita"])), -1600, "21: Tendência sem os 2.000 e com +400")
    _igual(Decimal(str(t_depois.get("retido") or 0)) - Decimal(str(t_antes.get("retido") or 0)), 400, "21: Tendência sem o retido")
    # devolução alterada para 800 (sem imposto): retido 200, BV 20, comissão 9, resultado +171 no mesmo mês
    alt = _exemplo_padrao("21 alterar")
    antes = _dre(inicio, fim)["dre"]["total"]
    _cancelar_ok(alt["ev"], _corpo_cancelar("parte", 600))
    r = _alterar_devolucao(alt["ev"], 800)
    _garante(r.status_code == 200, f"21 alterar → {r.status_code} {_erro(r)}")
    _igual(_resumo_api(alt["ev"])["retido"], 200, "21: retido depois de alterar")
    d = _dre(inicio, fim)["dre"]["total"]
    _igual(_delta(antes, d, "receita_bruta"), 200, "21 alterar: retido 200 na DRE")
    _igual(_delta(antes, d, "cpv"), 20, "21 alterar: BV 20")
    _igual(_delta(antes, d, "comissoes"), 9, "21 alterar: comissão 9")
    _igual(_delta(antes, d, "resultado_liquido"), 171, "21 alterar: resultado +171")
    _igual(_delta(antes, d, "gastos_extras"), 0, "21 alterar: devolução nos gastos extras")
    # multa ligada ao cancelado e devolução ligada a evento vivo seguem nos gastos extras
    antes = _dre(inicio, fim)["dre"]["total"]
    _gasto_comum(ex["ev"], 150, categoria=CATEGORIA_MULTA)
    vivo = _evento("21 vivo", venda=None)
    _devolucao_avulsa(vivo, 70)
    _igual(_delta(antes, _dre(inicio, fim)["dre"]["total"], "gastos_extras"), 220, "21: multa e devolução viva nos gastos")
    # Tudo com BV 200 pago: retido 0, comissão 0, custo +200
    antes = _dre(inicio, fim)["dre"]["total"]
    tudo = _exemplo_padrao("21 tudo bv pago")
    _no_banco_escrever("UPDATE event_acrescimos SET bv_payment_status = 'pago' WHERE id = :i", i=tudo["bv"])
    _cancelar_ok(tudo["ev"], _corpo_cancelar("tudo", 1000))
    d = _dre(inicio, fim)["dre"]["total"]
    _igual(_delta(antes, d, "receita_bruta"), 0, "21 Tudo: retido")
    _igual(_delta(antes, d, "comissoes"), 0, "21 Tudo: comissão")
    _igual(_delta(antes, d, "cpv"), 200, "21 Tudo: custo +BV pago")
    # virtual cancelado: sem retido
    antes = _dre(inicio, fim)["dre"]["total"]
    virtual = _evento("21 virtual", tipo="VIRTUAL", vendedor=None, taxa=None)
    _comprovante(virtual, 300)
    _cancelar_ok(virtual, {"motivo": "verify 306 virtual"})
    _igual(_delta(antes, _dre(inicio, fim)["dre"]["total"], "receita_bruta"), 0, "21: virtual sem retido")


def c21_satelite() -> None:
    """21, a parte do grupo (H5): o satélite cancelado não traz retido próprio — só o principal conta."""
    inicio, fim = _mes_corrente()
    antes = _dre(inicio, fim)["dre"]["total"]
    g = _grupo("21 satélite", dias=2)
    _cancelar_ok(g["principal"], _corpo_cancelar("parte", 900, alcance="todos"))
    d = _dre(inicio, fim)["dre"]["total"]
    _igual(_delta(antes, d, "receita_bruta"), 600, "21 satélite: retido contado mais de uma vez (ou o satélite trouxe retido)")
    _igual(Decimal(str(d.get("n_cancelados") or 0)) - Decimal(str(antes.get("n_cancelados") or 0)), 1, "21 satélite: n_cancelados conta o satélite")


def _vendedor_no_top(lista, apelido: str) -> Decimal:
    for s in lista or []:
        nome = s.get("user_name") or s.get("name") or getattr(s.get("user"), "name", None)
        if nome == f"{PREFIX}{apelido}":
            return Decimal(str(s.get("receita") or 0))
    return Decimal("0")


def c22_paineis() -> None:
    from app.models import EventInstallment, EventInvoice

    inicio, fim = _mes_corrente()
    _vendedor_proprio("vend22")
    antes, antes_j = _dre(inicio, fim), _dre_jinja(inicio, fim)
    ex = _exemplo_padrao("22 painéis", nota=True, comissao="a_pagar", vendedor="vend22")
    with app.app_context():
        db.session.add(EventInstallment(event_id=ex["ev"], due_date=_dia_do_mes_corrente().date(), amount=Decimal("500"), received=False))
        db.session.add(EventInvoice(event_id=ex["ev"], amount=Decimal("2000"), status="a_emitir"))
        db.session.commit()
    _garante([p for p in _dre(inicio, fim)["pendencias"]["recebimentos_previstos"] if p.get("event_id") == ex["ev"]], "22: a parcela do vivo não aparece (controle)")
    # Nada: retido 1.000 (o pago inteiro), para o vendedor entrar no Top 5 do mês (três reais + os do verify)
    _cancelar_ok(ex["ev"], _corpo_cancelar("nada", None, nome=None, pix=None, imposto_retido=160))
    depois, depois_j = _dre(inicio, fim), _dre_jinja(inicio, fim)
    _igual(depois["kpis"]["ticket_medio"], antes["kpis"]["ticket_medio"], "22: ticket médio mudou (API)")
    _igual(depois_j["ticket_medio"], antes_j["ticket_medio"], "22: ticket médio mudou (Jinja)")
    _igual(depois["paineis"]["a_receber_clientes"], antes["paineis"]["a_receber_clientes"], "22: a receber mudou (API)")
    _igual(depois_j["a_receber_clientes"], antes_j["a_receber_clientes"], "22: a receber mudou (Jinja)")
    rotulo = "Retido de cancelamentos"
    for tela, a, d in (("API", antes["paineis"]["receita_por_tipo"], depois["paineis"]["receita_por_tipo"]), ("Jinja", antes_j["receita_por_tipo"], depois_j["receita_por_tipo"])):
        _igual(Decimal(str((d or {}).get(rotulo, 0))) - Decimal(str((a or {}).get(rotulo, 0))), 1000, f"22: barra do retido ({tela})")
    # Fator R e break-even saem do total da DRE, que já tem o retido na receita: a conta tem de bater
    # com o total de agora (o retido de 1.000 move o Fator R menos que o arredondamento a 0,1).
    def pct(num, den) -> Decimal:
        return Decimal("0") if not den else (Decimal(str(num)) / Decimal(str(den)) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    tot = depois["dre"]["total"]
    _igual(_delta(antes["dre"]["total"], tot, "receita_bruta"), 1000, "22: o retido na receita da DRE")
    _garante(Decimal(str(depois["kpis"]["fator_r_pct"])) == pct(tot["pessoal"], tot["receita_bruta"]), "22: Fator R sem o retido (API)")
    _garante(
        Decimal(str(depois["kpis"]["breakeven_pct"])) == pct(tot["lucro_bruto"], Decimal(str(tot["pessoal"])) + Decimal(str(tot["comissoes"]))),
        "22: break-even sem o retido (API)",
    )
    for k in ("fator_r_pct", "breakeven_pct"):
        _igual(depois_j[k], depois["kpis"][k], f"22: {k} API × Jinja")
    previstos = [p for p in depois["pendencias"]["recebimentos_previstos"] if p.get("event_id") == ex["ev"]]
    _garante(not previstos, "22: a parcela do cancelado aparece nos Recebimentos Previstos (API)")
    _garante(not [p for p in depois_j["recebimentos_previstos"] if p.get("event_id") == ex["ev"]], "22: a parcela do cancelado nos Recebimentos Previstos (Jinja)")
    notas = [n for n in depois["pendencias"]["nf_a_emitir"] if n.get("event_id") == ex["ev"]]
    _garante(notas and notas[0].get("cancelado"), f"22: nota a emitir sem o selo do cancelado: {notas}")
    _garante([n for n in depois_j["nf_a_emitir"] if n.get("event_id") == ex["ev"]], "22: a nota a emitir sumiu do Jinja")
    _igual(_vendedor_no_top(depois["paineis"]["top_sellers"], "vend22") - _vendedor_no_top(antes["paineis"]["top_sellers"], "vend22"), 1000, "22: vendedor + retido (API)")
    _igual(_vendedor_no_top(depois_j["top_sellers"], "vend22") - _vendedor_no_top(antes_j["top_sellers"], "vend22"), 1000, "22: vendedor + retido (Jinja)")


def _retrato_rodado(*extra: str) -> tuple[int, dict, str]:
    r = subprocess.run(
        [sys.executable, str(AQUI / "retrato_main_branch.py"), "--json", *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=3600,
    )
    linhas = [x for x in (r.stdout or "").strip().splitlines() if x.strip().startswith("{")]
    return r.returncode, (json.loads(linhas[-1]) if linhas else {}), (r.stdout or "")[-800:] + (r.stderr or "")[-400:]


def c23_mutacao() -> None:
    """A mutação do 23: o retido somado sem a condição da quantidade de cancelados acusa a diferença.

    Roda na B3, com cancelados do verify no banco: os dois lados só leem (`--sem-resync`; o resync
    da `main` cancelaria as linhas deles), os meses com cancelado saem da comparação, e a base limpa,
    no mesmo estado, tem de sair idêntica antes de a mutação contar.
    """
    codigo, resumo, saida = _retrato_rodado("--sem-resync")
    _garante(codigo == 0 and resumo.get("diferencas") == 0, f"23 mutação: a base não sai idêntica ({codigo}, {resumo}): {saida}")
    # 1 = diferença acusada; 3 = o gancho da mutação ainda não existe na branch (antes da H3). Saída 1
    # também é a de uma exceção do Python: só vale com o resumo JSON dizendo que houve diferença.
    codigo, resumo, saida = _retrato_rodado("--sem-resync", "--mutacao")
    _garante(codigo == 1, f"23 mutação: o retrato saiu {codigo}, não acusou o retido somado sem a condição: {saida}")
    _garante((resumo.get("diferencas") or 0) >= 1, f"23 mutação: saída 1 sem diferença no resumo ({resumo}; {saida})")


def c24_comercial() -> None:
    from app.models import EventClient

    inicio, fim = _mes_corrente()
    uid = _vendedor_proprio("vend24")
    quando = _data_isolada()
    ini_ev = date(quando.year, quando.month, 1)
    fim_ev = _mes_seguinte(ini_ev) - timedelta(days=1)

    def kpis(ini: date, fi: date) -> dict:
        url = ROTAS["pipeline"].format(a=ini.isoformat(), b=fi.isoformat()) + f"&seller_id={uid}"
        return _cliente("fin").get(url).get_json()["kpis"]

    def desempenho(mes: str) -> dict:
        corpo = _cliente("sa").get(ROTAS["desempenho"].format(m=mes)).get_json()
        meu = [v for v in corpo.get("vendas", []) if v.get("name") == f"{PREFIX}vend24"]
        return meu[0] if meu else {}

    def d(a: dict, b: dict, k: str) -> Decimal:
        return Decimal(str(b.get(k) or 0)) - Decimal(str(a.get(k) or 0))

    cliente = _cliente_descartavel("24 cliente")
    metricas_antes = _cliente("sa").get("/api/clientes/metricas").get_json()
    antes, antes_ev = kpis(inicio, fim), kpis(ini_ev, fim_ev)
    des_antes, des_antes_ev = desempenho(_mes(_hoje_sp())), desempenho(_mes(ini_ev))
    ev = _evento("24 comercial", vendedor="vend24", inicio=quando, venda_em=quando.date())
    # sem venda: só faz da cliente uma recorrente, sem entrar no Comercial do mês
    outro_da_cliente = _evento("24 outro da cliente", venda=None, vendedor=None)
    _bv(ev, 200)
    _comprovante(ev, 1000)
    _linha_comissao(ev, 90, vendedor="vend24")
    _no_banco_escrever("UPDATE calendar_events SET client_id = :c WHERE id = :i", c=cliente, i=ev)
    with app.app_context():
        db.session.add(EventClient(event_id=ev, client_id=cliente, relationship_type="Contratante"))
        db.session.add(EventClient(event_id=outro_da_cliente, client_id=cliente, relationship_type="Contratante"))
        db.session.commit()
    metricas_vivo = _cliente("sa").get("/api/clientes/metricas").get_json()
    _garante(metricas_vivo.get("recurring_clients") == (metricas_antes.get("recurring_clients") or 0) + 1, "24: a cliente com 2 eventos não é recorrente (controle)")
    vendas_jinja = _cliente("sa").get(ROTAS["vendas_jinja"].format(a=ini_ev.isoformat(), b=fim_ev.isoformat()))
    _garante(b"V306 24 COMERCIAL" in vendas_jinja.data, "24: /vendas/ não lista o evento vivo (controle)")
    _cancelar_ok(ev, _corpo_cancelar("parte", 600))
    depois, depois_ev = kpis(inicio, fim), kpis(ini_ev, fim_ev)
    _igual(d(antes, depois, "total_vendido"), 400, "24: total vendido + retido no mês do cancelamento")
    _igual(d(antes, depois, "retido_cancelamentos"), 400, "24: retido_cancelamentos")
    _igual(d(antes, depois, "n_cancelados"), 1, "24: n_cancelados")
    _igual(d(antes, depois, "comissao_retido"), 18, "24: comissão do retido")
    _igual(d(antes, depois, "comissao_prevista"), 18, "24: comissão prevista com a do retido")
    _igual(d(antes_ev, depois_ev, "total_vendido"), 0, "24: a venda do cancelado ficou no mês dela (Comercial)")
    des, des_ev = desempenho(_mes(_hoje_sp())), desempenho(_mes(ini_ev))
    _igual(d(des_antes, des, "retido"), 400, f"24: desempenho sem o retido: {des}")
    _igual(d(des_antes, des, "cancelados"), 1, f"24: desempenho sem o cancelado: {des}")
    _igual(d(des_antes_ev, des_ev, "total"), 0, f"24: algo no mês do evento (desempenho): {des_ev}")
    ficha = _cliente("sa").get(ROTAS["cliente"].format(id=cliente)).get_json()
    _igual((ficha.get("client") or ficha).get("total_sales"), 400, f"24: ficha da cliente {ficha}")
    metricas = _cliente("sa").get("/api/clientes/metricas").get_json()
    _garante(
        metricas.get("clients_with_event") == (metricas_antes.get("clients_with_event") or 0) + 1
        and metricas.get("recurring_clients") == metricas_antes.get("recurring_clients"),
        f"24: 'Com evento' ou 'Recorrentes' contaram o cancelado {metricas_antes} → {metricas}",
    )
    painel = _dre(inicio, fim)["paineis"]["cancelamentos"]
    itens = [i for i in painel.get("itens", []) if i.get("id") == ev or i.get("event_id") == ev]
    _garante(itens and itens[0].get("status") == "cancelado", f"24: status de pagamento 'cancelado': {itens}")
    r = _cliente("sa").get(ROTAS["vendas_jinja"].format(a=ini_ev.isoformat(), b=fim_ev.isoformat()))
    _garante(r.status_code == 200 and b"V306 24 COMERCIAL" not in r.data, "24: /vendas/ mostra o cancelado")
    # Performance da Home: sem cargo nem cachê do cancelado
    show = _evento_com_elenco("24 performance", ["A"])
    _escalar(show, estado["t"])
    dia = _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=show)[0][0].date().isoformat()
    url = f"{ROTAS['home']}?perf_range=custom&perf_start={dia}&perf_end={dia}"
    perf_antes = _cliente("sa").get(url).get_json().get("performance") or {}
    _cancelar_ok(show, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    perf = _cliente("sa").get(url).get_json().get("performance") or {}
    _garante(Decimal(str(perf.get("casting_total") or 0)) < Decimal(str(perf_antes.get("casting_total") or 0)), f"24: Performance com o cargo do cancelado {perf_antes} → {perf}")
    _igual(d(perf, perf_antes, "money_total"), 300, f"24: Performance com o cachê do cancelado {perf_antes} → {perf}")


# ── B4 · História 4 ────────────────────────────────────────────────────────────────────────────
def _patch_comercial(event_id: int, apelido: str = "sa", **mudar):
    ev = _no_banco(
        "SELECT sale_value, sale_value_gross, with_invoice, is_cortesia_permuta, seller_id, commission_rate, sale_date "
        "FROM calendar_events WHERE id = :i",
        i=event_id,
    )[0]
    corpo = {
        "sale_value": float(ev[0]) if ev[0] is not None else None,
        "sale_value_gross": float(ev[1]) if ev[1] is not None else None,
        "transport_value": 0,
        "with_invoice": bool(ev[2]),
        "is_cortesia_permuta": bool(ev[3]),
        "seller_id": ev[4],
        "sale_date": (ev[6] or _hoje_sp()).isoformat(),
        "commission_rate": ev[5],
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
    }
    corpo.update(mudar)
    return _cliente(apelido).patch(ROTAS["comercial"].format(id=event_id), json=corpo)


def _taxa_padrao(valor: float) -> None:
    with app.app_context():
        db.session.get(SiteSetting, 1).default_commission_rate = valor
        db.session.commit()


def c16b_dados_de_venda() -> None:
    ex = _exemplo_padrao("16b venda", comissao="pago")
    with _com_hoje(_dia(10)):
        _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
        r = _patch_comercial(ex["ev"], sale_value=2400, sale_value_gross=2400)
    _garante(r.status_code == 200, f"16b venda → {r.status_code} {_erro(r)}")
    c = _cancelamento(ex["ev"])
    _igual(c["venda"], 2400, "16b: venda recongelada")
    _igual(c["cheia"], 110, "16b: cheia recongelada")
    _igual(_soma_vivas(ex["ev"]), q(Decimal("110") * 400 / 2400), "16b: comissão do retido")
    _igual(_linhas_comissao(ex["ev"])[0]["valor"], 90, "16b: a paga ficou intacta")
    # A diferença da recongelação fica no ajuste a pagar, no primeiro repasse aberto do dia 10 (o
    # mês corrente), com venda e liberação iguais — nunca na data da venda, ciclo já fechado.
    aj = _ajuste_negativo(ex["ev"])
    _garante(aj["venda_em"] is not None and aj["venda_em"] == aj["liberacao"], f"16b: datas do ajuste {aj}")
    _garante(
        (aj["venda_em"].year, aj["venda_em"].month) == (_dia(10).year, _dia(10).month),
        f"16b: diferença fora do primeiro repasse aberto ({aj['venda_em']})",
    )
    _igual(_resumo_api(ex["ev"])["bvs"][0]["conta"], q(Decimal("200") * 400 / 2400), "16b: BV do retido")
    # taxa sem própria (padrão 2,5) → 3,0 e → 2,0
    _taxa_padrao(2.5)
    t = _exemplo_padrao("16b taxa", comissao=None)
    _no_banco_escrever("UPDATE calendar_events SET commission_rate = NULL WHERE id = :i", i=t["ev"])
    _linha_comissao(t["ev"], 45, status="pago")
    with _com_hoje(_dia(10)):
        _cancelar_ok(t["ev"], _corpo_cancelar("parte", 600))
        r = _patch_comercial(t["ev"], commission_rate=3.0)
    _garante(r.status_code == 200, f"16b taxa → {r.status_code} {_erro(r)}")
    _igual(_cancelamento(t["ev"])["taxa"], 3, "16b: taxa congelada 3,0")
    aj = _ajuste_negativo(t["ev"])
    _garante((aj["nota"] or "").startswith("Cancelamento: taxa corrigida"), f"16b: motivo {aj['nota']}")
    _igual(_soma_vivas(t["ev"]), q(Decimal("54") * 400 / 2000), "16b: comissão do retido a 3%")
    with _com_hoje(_dia(10)):
        _patch_comercial(t["ev"], commission_rate=2.0)
    _igual(_soma_vivas(t["ev"]), q(Decimal("36") * 400 / 2000), "16b: comissão do retido a 2% (desconto)")
    # cortesia → cheia 0 e desconto do pago
    cort = _exemplo_padrao("16b cortesia", comissao="pago")
    with _com_hoje(_dia(10)):
        _cancelar_ok(cort["ev"], _corpo_cancelar("parte", 600))
        _patch_comercial(cort["ev"], is_cortesia_permuta=True)
    _igual(_cancelamento(cort["ev"])["cheia"], 0, "16b: cortesia → cheia 0")
    _igual(_soma_vivas(cort["ev"]), 0, "16b: desconto do pago na cortesia")
    # nota e parcela pelo Superadmin; congelado intacto
    antes = _cancelamento(ex["ev"])
    r = _cliente("sa").put(ROTAS["parcelas"].format(id=ex["ev"]), json={"items": [{"due_date": _hoje_sp().isoformat(), "amount": 100}]})
    _garante(r.status_code == 200, f"16b parcela → {r.status_code} {_erro(r)}")
    r = _cliente("sa").post(
        ROTAS["notas"].format(id=ex["ev"]),
        data={"amount": "400", "issue_date": _hoje_sp().isoformat()},
        content_type="multipart/form-data",
    )
    _garante(r.status_code in (200, 201), f"16b nota → {r.status_code} {_erro(r)}")
    _garante(
        _no_banco("SELECT 1 FROM event_installments WHERE event_id = :i AND amount = 100", i=ex["ev"]),
        "16b: a parcela não foi gravada",
    )
    _garante(
        _no_banco("SELECT 1 FROM event_invoices WHERE event_id = :i AND amount = 400", i=ex["ev"]),
        "16b: a nota não foi gravada",
    )
    _garante(_cancelamento(ex["ev"]) == antes, "16b: nota/parcela mexeram no congelado")
    notas_antes = _no_banco("SELECT count(*) FROM event_invoices WHERE event_id = :i", i=ex["ev"])[0][0]
    r = _patch_comercial(ex["ev"], apelido="com", sale_value=2500)
    _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"16b COMERCIAL → {r.status_code} {_erro(r)}")
    r = _cliente("fin").post(
        ROTAS["notas"].format(id=ex["ev"]),
        data={"amount": "10", "issue_date": _hoje_sp().isoformat()},
        content_type="multipart/form-data",
    )
    _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"16b FINANCEIRO nota → {r.status_code} {_erro(r)}")
    _igual(_no_banco("SELECT sale_value FROM calendar_events WHERE id = :i", i=ex["ev"])[0][0], 2400, "16b: a recusa mudou a venda")
    _garante(_no_banco("SELECT count(*) FROM event_invoices WHERE event_id = :i", i=ex["ev"])[0][0] == notas_antes, "16b: a recusa lançou nota")
    _garante(_cancelamento(ex["ev"]) == antes, "16b: a recusa mexeu no congelado")
    # variante "cheia 0" pela API: cortesia com valor e evento sem vendedor, cancelados
    for rotulo, kw in (("cortesia", {"cortesia": True}), ("sem vendedor", {"vendedor": None})):
        ev = _evento(f"16b cheia0 {rotulo}", **kw)
        _comprovante(ev, 1000)
        from app.financeiro import comissoes_ops

        with app.app_context():
            vivo = comissoes_ops._event_commission(db.session.get(CalendarEvent, ev), db.session.get(SiteSetting, 1))
        _igual(vivo, 100, f"16b cheia 0 ({rotulo}): a comissão do vivo antes do ato não é a de hoje")
        _cancelar_ok(ev, _corpo_cancelar("parte", 600))
        _igual(_cancelamento(ev)["cheia"], 0, f"16b cheia 0 ({rotulo})")
        _garante(not _linhas_comissao(ev), f"16b cheia 0 ({rotulo}): nasceu linha")


def _retido_comercial(apelido: str) -> tuple[Decimal, Decimal]:
    """O retido do vendedor no Dashboard Comercial e no `/admin/desempenho` do mês corrente."""
    inicio, fim = _mes_corrente()
    uid = estado["usuarios"][apelido]["id"]
    url = ROTAS["pipeline"].format(a=inicio.isoformat(), b=fim.isoformat()) + f"&seller_id={uid}"
    kpis = _cliente("fin").get(url).get_json()["kpis"]
    des = _cliente("sa").get(ROTAS["desempenho"].format(m=_mes(_hoje_sp()))).get_json()
    meu = [v for v in des.get("vendas", []) if v.get("name") == f"{PREFIX}{apelido}"]
    return (
        Decimal(str(kpis.get("retido_cancelamentos") or 0)),
        Decimal(str((meu[0].get("retido") if meu else 0) or 0)),
    )


def c16c_troca_de_vendedor() -> None:
    a = _exemplo_padrao("16c paga", comissao="pago")
    with _com_hoje(_dia(10)):
        _cancelar_ok(a["ev"], _corpo_cancelar("parte", 600))
        menos72 = _ajuste_negativo(a["ev"])
        _igual(menos72["valor"], -72, "16c: −72 antes da troca")
        antes_a, antes_b = _retido_comercial("vend"), _retido_comercial("vend2")
        r = _patch_comercial(a["ev"], seller_id=estado["usuarios"]["vend2"]["id"])
        depois_a, depois_b = _retido_comercial("vend"), _retido_comercial("vend2")
    _garante(r.status_code == 200, f"16c troca → {r.status_code} {_erro(r)}")
    paga = next(x for x in _linhas_comissao(a["ev"]) if x["id"] == a["linha"])
    _garante(paga["status"] == "pago" and q(paga["valor"]) == q(90), f"16c: a paga de 90 mudou {paga}")
    for i, tela in enumerate(("Dashboard Comercial", "/admin/desempenho")):
        _igual(antes_a[i] - depois_a[i], 400, f"16c: o retido não saiu de A no {tela}")
        _igual(depois_b[i] - antes_b[i], 400, f"16c: o retido não foi a B no {tela}")
    da = [x for x in _linhas_comissao(a["ev"]) if x["seller"] == estado["usuarios"]["vend"]["id"]]
    db_ = [x for x in _linhas_comissao(a["ev"]) if x["seller"] == estado["usuarios"]["vend2"]["id"]]
    _igual(sum(Decimal(x["valor"]) for x in da), 0, "16c: A devolve o recebido (90 − 90)")
    _igual(sum(Decimal(x["valor"]) for x in db_), 18, "16c: B recebe a comissão do retido")
    neg = [x for x in da if x["original_id"]]
    _garante(neg and (neg[0]["nota"] or "").startswith("Cancelamento: vendedor trocado — devolve o já recebido"), f"16c: motivo de A {neg}")
    _garante(neg[0]["id"] == menos72["id"] and q(neg[0]["valor"]) == q(-90), f"16c: o −72 não virou −90 na mesma linha {menos72} → {neg[0]}")
    _garante(db_ and (db_[0]["nota"] or "").startswith("Cancelamento: vendedor trocado — comissão do retido"), f"16c: motivo de B {db_}")
    _garante(
        db_[0]["venda_em"] == db_[0]["liberacao"] and (db_[0]["venda_em"].year, db_[0]["venda_em"].month) == (_dia(10).year, _dia(10).month),
        f"16c: +18 de B fora do primeiro repasse aberto {db_[0]}",
    )
    c = _cancelamento(a["ev"])
    _garante(c["vendedor"] == estado["usuarios"]["vend2"]["id"] and c["beneficiario"] == estado["usuarios"]["vend2"]["id"], f"16c: congelado {c}")
    so = _exemplo_padrao("16c a pagar", comissao="a_pagar")
    _cancelar_ok(so["ev"], _corpo_cancelar("parte", 600))
    _patch_comercial(so["ev"], seller_id=estado["usuarios"]["vend2"]["id"])
    _igual(_soma_vivas(so["ev"], "vend"), 0, "16c (ii): a de A cancelada")
    _igual(_soma_vivas(so["ev"], "vend2"), 18, "16c (ii): B com 18")
    sem = _exemplo_padrao("16c sem comissão", comissao="a_pagar")
    _cancelar_ok(sem["ev"], _corpo_cancelar("parte", 600))
    _patch_comercial(sem["ev"], seller_id=estado["usuarios"]["semcom"]["id"])
    _igual(_soma_vivas(sem["ev"]), 0, "16c (iii): ninguém recebe")
    antes_v = (_cancelamento(so["ev"]), _linhas_comissao(so["ev"]))
    r = _patch_comercial(so["ev"], apelido="com", seller_id=estado["usuarios"]["vend"]["id"])
    _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"16c (v) COMERCIAL → {r.status_code} {_erro(r)}")
    _garante((_cancelamento(so["ev"]), _linhas_comissao(so["ev"])) == antes_v, "16c (v): a recusa gravou")
    from app.constants import MOTIVOS_AJUSTE_COMISSAO

    soltas = _no_banco(
        "SELECT cp.id, cp.event_id, cp.notes FROM commission_payments cp JOIN commission_payments o ON o.id = cp.original_id "
        "WHERE cp.original_id IS NOT NULL AND cp.seller_id = ANY(:u) AND (cp.event_id IS NOT NULL OR o.event_id = ANY(:e))",
        u=[estado["usuarios"][k]["id"] for k in ("vend", "vend2")],
        e=[a["ev"], so["ev"], sem["ev"]],
    )
    for lid, eid, nota in soltas:
        _garante(eid is not None and any((nota or "").startswith(m) for m in MOTIVOS_AJUSTE_COMISSAO), f"16c varredura: ajuste {lid} sem evento ou motivo ({nota})")


def c16c_corrida() -> None:
    """16c-corrida (molde do 30): outra sessão marca "pago" o −72 de A entre a porta e a trava (T1 → T2 → T4).

    A linha de A nunca vira "paga" de um valor que a troca já reescreveu: o −72 fica −72 pago, e o
    acerto de A ao alvo 0 nasce à parte.
    """
    from app.calendar import cancel_ops

    a = _exemplo_padrao("16c corrida", comissao="pago")
    with _com_hoje(_dia(10)):
        _cancelar_ok(a["ev"], _corpo_cancelar("parte", 600))
        menos72 = _ajuste_negativo(a["ev"])
        real = cancel_ops.travar_grupo  # sem o gancho: vermelho

        def injeta(*args, **kw):
            _no_banco_escrever(
                "UPDATE commission_payments SET status = 'pago', paid_at = now() WHERE id = :i", i=menos72["id"]
            )
            return real(*args, **kw)

        cancel_ops.travar_grupo = injeta
        try:
            r = _patch_comercial(a["ev"], seller_id=estado["usuarios"]["vend2"]["id"])
        finally:
            cancel_ops.travar_grupo = real
    _garante(r.status_code == 200, f"16c corrida → {r.status_code} {_erro(r)}")
    linha = next(x for x in _linhas_comissao(a["ev"]) if x["id"] == menos72["id"])
    _garante(linha["status"] == "pago" and q(linha["valor"]) == q(-72), f"16c corrida: a linha paga foi reescrita {linha}")
    _igual(_soma_vivas(a["ev"], "vend"), 0, "16c corrida: A não ficou no alvo 0")
    _igual(_soma_vivas(a["ev"], "vend2"), 18, "16c corrida: B sem a comissão do retido")


def _put_acrescimos(event_id: int, itens: list[dict], apelido: str = "sa"):
    return _cliente(apelido).put(ROTAS["acrescimos"].format(id=event_id), json={"items": itens})


def _itens_atuais(event_id: int) -> list[dict]:
    rows = _no_banco(
        "SELECT id, tipo, is_percent, value, bv_recipient, bv_pix FROM event_acrescimos WHERE event_id = :i ORDER BY id",
        i=event_id,
    )
    return [
        {"id": r[0], "tipo": r[1], "is_percent": r[2], "value": float(r[3]), "bv_recipient": r[4], "bv_pix": r[5]}
        for r in rows
    ]


def c16d_acrescimos() -> None:
    ex = _exemplo_padrao("16d acréscimos")
    transporte = _acrescimo(ex["ev"], "Transporte", 100)
    comum = _acrescimo(ex["ev"], "Outro", 50)
    pago = _bv(ex["ev"], 100, status="pago")
    _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    cheia_antes = _cancelamento(ex["ev"])["cheia"]
    itens = _itens_atuais(ex["ev"])
    for i in itens:
        if i["id"] == ex["bv"]:
            i.update(value=300, bv_pix="pix-novo@exemplo.test", bv_recipient=f"{PREFIX}Parceiro Novo")
        if i["id"] == transporte:
            i["value"] = 150
        if i["id"] == pago:
            i["value"] = 999  # BV pago com outro valor: mantém o gravado
    itens = [i for i in itens if i["id"] != comum]
    itens.append({"tipo": "Outro", "is_percent": False, "value": 20})
    congelado_antes = {k: v for k, v in (_cancelamento(ex["ev"]) or {}).items() if k not in ("cheia",)}
    retido_antes = _resumo_api(ex["ev"])["retido"]
    aud_comum = _no_banco("SELECT count(*) FROM audit_logs WHERE entity_id IN (:i, :c)", i=ex["ev"], c=comum)[0][0]
    r = _put_acrescimos(ex["ev"], itens)
    _garante(r.status_code == 200, f"16d PUT → {r.status_code} {_erro(r)}")
    _garante(
        _no_banco("SELECT bv_recipient FROM event_acrescimos WHERE id = :i", i=ex["bv"])[0][0] == f"{PREFIX}Parceiro Novo",
        "16d: o recebedor corrigido não gravou",
    )
    _igual(_no_banco("SELECT amount_brl FROM event_acrescimos WHERE id = :i", i=transporte)[0][0], 150, "16d: transporte mudado")
    _garante(
        _no_banco("SELECT 1 FROM event_acrescimos WHERE event_id = :i AND tipo = 'Outro' AND value = 20", i=ex["ev"]),
        "16d: o acréscimo novo não nasceu",
    )
    _garante(
        _no_banco("SELECT count(*) FROM audit_logs WHERE entity_id IN (:i, :c)", i=ex["ev"], c=comum)[0][0] > aud_comum,
        "16d: a remoção do acréscimo comum sem audit",
    )
    congelado = {k: v for k, v in (_cancelamento(ex["ev"]) or {}).items() if k not in ("cheia",)}
    _garante(congelado == congelado_antes, f"16d: o congelado mudou além da cheia {congelado_antes} → {congelado}")
    _igual(_resumo_api(ex["ev"])["retido"], retido_antes, "16d: o retido mudou")
    linha_bv = _no_banco("SELECT id, amount_brl, bv_pix FROM event_acrescimos WHERE id = :i", i=ex["bv"])
    _garante(linha_bv, "16d: o BV foi apagado e recriado (mesmo id)")
    _igual(linha_bv[0][1], 300, "16d: BV cheio")
    _igual(_no_banco("SELECT amount_brl FROM event_acrescimos WHERE id = :i", i=pago)[0][0], 100, "16d: BV pago intacto")
    _garante(not _no_banco("SELECT 1 FROM event_acrescimos WHERE id = :i", i=comum), "16d: o acréscimo comum não saiu")
    c = _cancelamento(ex["ev"])
    _igual(c["cheia"], q((Decimal("2000") - 300 - 100) * 5 / 100), "16d: cheia sobre a venda − BV cheios")
    _garante(cheia_antes is not None, "16d: sem cheia antes")
    planilha = _bv_planilha(ex["ev"], _mes_evento(ex["ev"]))
    nao_pago = [i for i in planilha if int(i["id"]) == ex["bv"]]
    _garante(nao_pago and nao_pago[0]["pix_key"] == "pix-novo@exemplo.test", "16d: PIX novo fora da Planilha")
    _igual(nao_pago[0]["amount"], 60, "16d: BV do retido")
    sem_pago = [i for i in _itens_atuais(ex["ev"]) if i["id"] != pago]
    retrato = _itens_atuais(ex["ev"])
    r = _put_acrescimos(ex["ev"], sem_pago)
    _garante(r.status_code == 400 and "items" in (_erro(r).get("fields") or {}), f"16d BV pago ausente → {r.status_code} {_erro(r)}")
    _garante(_itens_atuais(ex["ev"]) == retrato, "16d: o PUT recusado gravou")
    _igual(_no_banco("SELECT amount_brl FROM event_acrescimos WHERE id = :i", i=pago)[0][0], 100, "16d: o BV pago mudou na recusa")
    r = _put_acrescimos(ex["ev"], _itens_atuais(ex["ev"]), apelido="com")
    _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"16d COMERCIAL → {r.status_code} {_erro(r)}")
    _garante(_itens_atuais(ex["ev"]) == retrato, "16d: o COMERCIAL gravou")
    # reembolso lançado e cobrado no cancelado: gravado, retido intacto
    retido = _resumo_api(ex["ev"])["retido"]
    r = _cliente("sa").post(
        ROTAS["reembolso"].format(id=ex["ev"]),
        data={"description": f"{PREFIX}reembolso 16d", "amount": "70", "file": _arquivo("nf.pdf")},
        content_type="multipart/form-data",
    )
    _garante(r.status_code == 201, f"16d reembolso → {r.status_code} {_erro(r)}")
    reembolso = _no_banco("SELECT id FROM event_reimbursements WHERE event_id = :i AND amount = 70", i=ex["ev"])
    _garante(reembolso, "16d: o reembolso não gravou")
    r = _cliente("sa").post(f"/api/reimbursements/{reembolso[0][0]}/collect")
    _garante(r.status_code in (200, 201), f"16d cobrar o reembolso → {r.status_code} {_erro(r)}")
    _igual(_resumo_api(ex["ev"])["retido"], retido, "16d: o reembolso mexeu no retido")


def c16e_taxa_congelada() -> None:
    _taxa_padrao(2.5)
    try:
        ex = _exemplo_padrao("16e taxa", comissao="pago")
        _no_banco_escrever("UPDATE calendar_events SET commission_rate = NULL WHERE id = :i", i=ex["ev"])
        with _com_hoje(_dia(10)):
            _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
        _igual(_cancelamento(ex["ev"])["taxa"], 2.5, "16e: taxa congelada no ato")
        _taxa_padrao(3.0)
        with _com_hoje(_dia(10)):
            for rotulo, acao in (
                ("venda", lambda: _patch_comercial(ex["ev"], sale_value=2200, sale_value_gross=2200)),
                ("vendedor", lambda: _patch_comercial(ex["ev"], seller_id=estado["usuarios"]["vend2"]["id"])),
                ("comprovante", lambda: _post_comprovante("sa", ex["ev"], 100)),
            ):
                r = acao()
                _garante(r.status_code in (200, 201), f"16e {rotulo} → {r.status_code} {_erro(r)}")
                _igual(_cancelamento(ex["ev"])["taxa"], 2.5, f"16e: a padrão alcançou o cancelado na correção da {rotulo}")
            _comissoes(_mes(_hoje_sp()))
            _planilha(_mes(_mes_seguinte(_hoje_sp())))
        _igual(_cancelamento(ex["ev"])["taxa"], 2.5, "16e: a padrão alcançou o cancelado")
        soma_antes = _soma_vivas(ex["ev"])
        with _com_hoje(_dia(10)):
            r = _patch_comercial(ex["ev"], commission_rate=3.0)
        _garante(r.status_code == 200, f"16e taxa à mão → {r.status_code} {_erro(r)}")
        _igual(_cancelamento(ex["ev"])["taxa"], 3, "16e: a correção à mão leva a 3")
        _garante(_soma_vivas(ex["ev"]) > soma_antes, f"16e: a correção para 3% não refez para mais ({soma_antes} → {_soma_vivas(ex['ev'])})")
    finally:
        _restaurar_config()


# ── B5 · História 5 ────────────────────────────────────────────────────────────────────────────
def _grupo(
    rotulo: str,
    *,
    venda: float = 3000,
    taxa: float = 2.5,
    dias: int = 2,
    pagos: tuple = (1000, 500),
    comissao: str | None = "a_pagar",
    bruto: float | None = None,
    inicio: datetime | None = None,
    passo: timedelta = timedelta(days=1),
) -> dict:
    """Grupo semeado: o principal (mais cedo) com a venda e `dias` satélites sem venda."""
    inicio = inicio or _data_isolada(dias=dias + 3)
    principal = _evento(f"{rotulo} principal", venda=venda, taxa=taxa, bruto=bruto, inicio=inicio)
    sats = [
        _evento(f"{rotulo} dia {i + 2}", venda=None, taxa=None, vendedor=None, inicio=inicio + passo * (i + 1))
        for i in range(dias)
    ]
    _agrupar(principal, *sats)
    if pagos and pagos[0]:
        _comprovante(principal, pagos[0])
    if len(pagos) > 1 and pagos[1] and sats:
        _comprovante(sats[0], pagos[1])
    linha = None
    if comissao:
        linha = _linha_comissao(principal, q(Decimal(str(venda)) * Decimal(str(taxa)) / 100), status=comissao)
    return {"principal": principal, "dias": sats, "linha": linha}


def _corte(dia_id: int, venda_nova: float, modo: str = "parte", valor: float | None = 300, **extra):
    corpo = _corpo_cancelar(modo, valor, **({"nome": None, "pix": None} if modo == "nada" else {}))
    corpo.update({"venda_nova": venda_nova, **extra})
    return _cancelar(dia_id, corpo)


def c5_grupo_pendente() -> None:
    g = _grupo("5 grupo")
    _devolucao_avulsa(g["dias"][0], 50, status="pendente")
    r = _cancelar(g["principal"], _corpo_cancelar("parte", 600, alcance="todos"))
    _garante(r.status_code == 409 and _codigo(r) == "devolucao_pendente", f"5-grupo todos → {r.status_code} {_erro(r)}")
    _garante([d.get("id") for d in _erro(r).get("dias") or []] == [g["dias"][0]], f"5-grupo: `dias` no todos: {_erro(r)}")
    r = _corte(g["dias"][1], 2000)
    _garante(r.status_code == 409 and _codigo(r) == "devolucao_pendente", f"5-grupo corte → {r.status_code} {_erro(r)}")
    _garante([d.get("id") for d in _erro(r).get("dias") or []] == [g["dias"][0]], f"5-grupo: `dias` no corte: {_erro(r)}")
    for ev in (g["principal"], *g["dias"]):
        _nada_gravado(ev, f"5-grupo {ev}")
    _garante(
        [d["status"] for d in _devolucoes(g["dias"][0])] == ["pendente"] and not _devolucoes(g["principal"]),
        "5-grupo: a recusa mexeu nas devoluções",
    )


def c4_corte_recusas() -> None:
    g = _grupo("4 corte")
    dia = g["dias"][1]
    for corpo_extra, campo, rotulo in (
        ({}, "venda_nova", "sem venda nova"),
        ({"venda_nova": 0}, "venda_nova", "venda nova zero"),
        ({"venda_nova": 4000}, "venda_nova", "acima da venda"),
        ({"venda_nova": 2000, "imposto_retido": 10}, "imposto_retido", "com imposto"),
    ):
        corpo = _corpo_cancelar("parte", 300)
        corpo.update(corpo_extra)
        _deve_400(dia, corpo, campo, f"corte {rotulo}")
    corpo = _corpo_cancelar("tudo", 1500)
    corpo["venda_nova"] = 2000
    _deve_400(dia, corpo, "devolucao_modo", "corte com tudo")
    quitado = _grupo("4 corte quitado", pagos=(3000,))
    _deve_400(quitado["dias"][0], {**_corpo_cancelar("nada", None, nome=None, pix=None), "venda_nova": 2000}, "devolucao_modo", "Nada abaixo do mínimo")
    _deve_400(quitado["dias"][0], {**_corpo_cancelar("parte", 500), "venda_nova": 2000}, "devolucao_valor", "Parte abaixo do mínimo")
    r = _previa(quitado["dias"][0], 1000, venda_nova=2000)
    _garante(r.status_code == 200 and q(r.get_json()["efeito"].get("devolucao_minima")) == q(1000), f"4: devolucao_minima na prévia {r.get_data(as_text=True)[:300]}")


def _vendas(*ids: int) -> dict:
    return {
        r[0]: (r[1], r[2])
        for r in _no_banco("SELECT id, sale_value, group_leader_id FROM calendar_events WHERE id = ANY(:i)", i=list(ids))
    }


def _recusa_cancelado(r, rotulo: str) -> None:
    _garante(
        r.status_code == 409 and _codigo(r) == "cancelado" and "cancelad" in (_erro(r).get("message") or "").lower(),
        f"{rotulo} → {r.status_code} {_erro(r)}",
    )


def c29_agrupar_cancelado() -> None:
    a = _exemplo_padrao("29 cancelado")
    _cancelar_ok(a["ev"])
    vivo = _evento("29 vivo", venda=1000)
    antes = _vendas(a["ev"], vivo)
    for lider, alvo in ((vivo, a["ev"]), (a["ev"], vivo)):
        r = _cliente("sa").post(
            ROTAS["grupo"].format(id=lider),
            json={"leader_event_id": lider, "target_event_ids": [alvo], "confirm_clear_financials": True},
        )
        _recusa_cancelado(r, f"29 agrupar (líder {lider})")
        _garante(_vendas(a["ev"], vivo) == antes, f"29: o agrupamento recusado mexeu: {_vendas(a['ev'], vivo)}")
        jinja = _cliente("sa").post(
            f"/events/{lider}",
            data={"action": "group_events", "leader_event_id": str(lider), "target_event_ids": [str(alvo)], "confirm_clear_financials": "1"},
        )
        _garante(jinja.status_code in (200, 302), f"29 Jinja (líder {lider}) → {jinja.status_code}")
        _garante(_vendas(a["ev"], vivo) == antes, f"29: o Jinja agrupou ou zerou (líder {lider}): {_vendas(a['ev'], vivo)}")
    g = _grupo("29 desagrupar")
    _cancelar_ok(g["dias"][0], {**_corpo_cancelar("parte", 100), "venda_nova": 2500})
    r = _cliente("sa").delete(ROTAS["grupo"].format(id=g["dias"][0]))
    _recusa_cancelado(r, "29 desagrupar cancelado")
    r = _cliente("sa").delete(f"/api/events/{g['principal']}/grupo/satelites/{g['dias'][0]}")
    _recusa_cancelado(r, "29 soltar o satélite cancelado pelo principal")
    _garante(_vendas(g["dias"][0])[g["dias"][0]][1] == g["principal"], "29: o dia cancelado saiu do grupo")
    r = _cliente("sa").delete(ROTAS["grupo"].format(id=g["dias"][1]))
    _garante(r.status_code == 200, f"29 desagrupar vivo → {r.status_code} {_erro(r)}")
    _garante(_vendas(g["dias"][1])[g["dias"][1]][1] is None, "29: o dia vivo não saiu do grupo")


def c35_marcado_no_grupo() -> None:
    g = _grupo("35 principal marcado")
    for ev in (g["principal"], *g["dias"]):
        _marcar_sumido(ev)
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=g["principal"])).get_json()
    _garante(imp.get("acao") == "cancelar", f"35: acao {imp.get('acao')}")
    vazio = _evento("35 marcado vazio", venda=None, vendedor=None)
    _marcar_sumido(vazio)
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=vazio)).get_json()
    _garante(imp.get("acao") == "cancelar", f"35: o marcado vazio ainda sai 'excluir': {imp.get('acao')}")
    _cancelar_ok(g["principal"], _corpo_cancelar("parte", 600, alcance="todos"))
    for ev in (g["principal"], *g["dias"]):
        _garante(_cancelado_em(ev) is not None, f"35: dia {ev} não cancelou")
        _garante(_no_banco("SELECT google_missing_since FROM calendar_events WHERE id = :i", i=ev)[0][0] is None, f"35: a marca ficou em {ev}")
    s = _grupo("35 satélite marcado")
    _marcar_sumido(s["dias"][0])
    r = _corte(s["dias"][0], 2500, valor=100)
    _garante(r.status_code == 200, f"35 satélite → {r.status_code} {_erro(r)}")
    _garante(_cancelado_em(s["dias"][0]) is not None, "35: o satélite marcado não cancelou")
    _garante(
        _no_banco("SELECT google_missing_since FROM calendar_events WHERE id = :i", i=s["dias"][0])[0][0] is None,
        "35: a marca ficou no satélite",
    )
    _garante(_cancelado_em(s["principal"]) is None and _cancelado_em(s["dias"][1]) is None, "35: o corte levou outro dia")


def c37_cancelar_todos() -> None:
    _ao_cancelar.clear()
    g = _grupo("37 todos", dias=3)
    ja = g["dias"][2]
    _cancelar_ok(ja, {**_corpo_cancelar("nada", None, nome=None, pix=None), "venda_nova": 3000})
    ja_em, ja_linha = _cancelado_em(ja), _cancelamento(ja)
    propria = _linha_comissao(g["dias"][0], 30, status="pago", vendedor="vend2")
    base = _linhas_comissao(g["principal"])[0]
    logs_antes = {ev: len(_historico(ev)) for ev in (g["principal"], *g["dias"])}
    marco = google.marco()
    _commit_antes_do_google.clear()
    corpo = _cancelar_ok(g["principal"], _corpo_cancelar("parte", 900, alcance="todos"))
    vivos = [g["principal"], g["dias"][0], g["dias"][1]]
    for ev in vivos:
        _garante(_cancelado_em(ev) is not None, f"37: {ev} não cancelou")
        _garante(len(_historico(ev)) == logs_antes[ev] + 1, f"37: EventLog do dia {ev}")
    for ev in g["dias"][:2]:
        _garante(_no_banco("SELECT group_leader_id FROM calendar_events WHERE id = :i", i=ev)[0][0] == g["principal"], f"37: desagrupou {ev}")
    _garante(_cancelado_em(ja) == ja_em and _cancelamento(ja) == ja_linha and len(_historico(ja)) == logs_antes[ja], "37: o dia já cancelado foi tocado")
    resumo = _resumo_api(g["principal"])
    _igual(resumo["pago"], 1500, "37: pago do grupo")
    _igual(resumo["retido"], 600, "37: retido")
    vivas = _linhas_comissao(g["principal"])
    _garante(
        len(vivas) == 1 and vivas[0]["id"] == base["id"] and q(vivas[0]["valor"]) == q(15) and vivas[0]["venda_em"] == base["venda_em"],
        f"37: comissão 15 no lugar (mesma linha e data): {vivas} × {base}",
    )
    _garante(_cancelamento(g["principal"])["regime"] == "venda", "37: principal sem regime venda")
    for ev in g["dias"][:2]:
        c = _cancelamento(ev)
        _garante(c and c["regime"] == "satelite" and c["principal"] == g["principal"], f"37: dia {ev} {c}")
    _garante(len(google.deletes(marco)) == 3 and all(_commit_antes_do_google), f"37: remoções no Google {google.deletes(marco)}")
    _garante(sorted(corpo.get("dias_cancelados") or []) == sorted(vivos), f"37: dias_cancelados {corpo.get('dias_cancelados')}")
    for ev in vivos:
        _garante(_ao_cancelar.count((ev, "todos", None)) == 1, f"37: ao_cancelar não viu {ev} uma vez")
    p = next(x for x in _linhas_comissao(g["dias"][0]) if x["id"] == propria)
    _garante(p["status"] == "pago" and q(p["valor"]) == q(30), f"37: a comissão própria do satélite mudou: {p}")
    # variante 37-devolução
    v = _grupo("37 devolução", dias=2)
    _devolucao_avulsa(v["dias"][0], 200)
    _cancelar_ok(v["principal"], _corpo_cancelar("parte", 900, alcance="todos"))
    _igual(_resumo_api(v["principal"])["devolvido"], 1100, "37-devolução: total devolvido")
    dev_p = _devolucoes(v["principal"])[0]["id"]
    dev_s = _devolucoes(v["dias"][0])[0]["id"]
    aud_antes = _auditoria_de_gastos(dev_p, dev_s)
    r = _alterar_devolucao(v["principal"], 100)
    _garante(r.status_code == 200, f"37-devolução → {r.status_code} {_erro(r)}")
    _garante(not _devolucoes(v["principal"]), f"37-devolução: a do principal não foi excluída: {_devolucoes(v['principal'])}")
    _igual(_devolucoes(v["dias"][0])[0]["valor"], 100, "37-devolução: a do satélite")
    aud = _auditoria_de_gastos(dev_p, dev_s)
    _garante(aud[dev_p] > aud_antes[dev_p] and aud[dev_s] > aud_antes[dev_s], f"37-devolução: auditoria {aud_antes} → {aud}")


def _auditoria_de_gastos(*ids: int) -> dict[int, int]:
    return {
        i: _no_banco(
            "SELECT count(*) FROM audit_logs WHERE entity_type IN ('gasto', 'special_expense', 'expense') AND entity_id = :i",
            i=i,
        )[0][0]
        for i in ids
    }


def c37b_comprovante_no_satelite() -> None:
    g = _grupo("37b", dias=2)
    _cancelar_ok(g["principal"], _corpo_cancelar("parte", 900, alcance="todos"))
    base = _linhas_comissao(g["principal"])[0]
    logs = (len(_historico(g["dias"][1])), len(_historico(g["principal"])))
    r = _post_comprovante("sa", g["dias"][1], 200)
    _garante(r.status_code == 201, f"37b → {r.status_code} {_erro(r)}")
    _garante((r.get_json().get("event") or {}).get("id") == g["dias"][1], "37b: a resposta não é o detalhe do dia")
    resumo = _resumo_api(g["principal"])
    _igual(resumo["pago"], 1700, "37b: pago do grupo")
    _igual(resumo["retido"], 800, "37b: retido")
    vivas = _linhas_comissao(g["principal"])
    _garante(len(vivas) == 1 and vivas[0]["id"] == base["id"] and q(vivas[0]["valor"]) == q(20), f"37b: comissão 15 → 20 no lugar: {vivas}")
    c = _cancelamento(g["dias"][1])
    _garante(
        c["regime"] == "satelite" and c["venda"] is None and c["cheia"] is None,
        f"37b: a linha satelite ganhou dinheiro próprio: {c}",
    )
    _garante(
        len(_historico(g["dias"][1])) >= logs[0] + 2 and len(_historico(g["principal"])) > logs[1],
        "37b: sem EventLog no dia e no principal",
    )


def _cobranca(principal: int) -> dict:
    from app.financeiro import cobranca_ops

    with app.app_context():
        r = cobranca_ops.resumo_da_venda_do_evento(db.session.get(CalendarEvent, principal))
        return {k: getattr(r, k) for k in ("valor", "recebido", "saldo", "quitada", "sinal_pendente", "vencimento", "data_do_grupo")}


def c38_so_este_dia() -> None:
    _ao_cancelar.clear()
    for variante in ("a_pagar", "pago"):
        g = _grupo(f"38 {variante}", comissao=variante, bruto=3300)
        dia = g["dias"][0]
        inicio, fim = _mes_corrente()
        mes_ev = _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=g["principal"])[0][0].date()
        ini_ev = date(mes_ev.year, mes_ev.month, 1)
        fim_ev = _mes_seguinte(ini_ev) - timedelta(days=1)
        dre_antes, dre_ev_antes = _dre(inicio, fim)["dre"]["total"], _dre(ini_ev, fim_ev)["dre"]["total"]
        logs = len(_historico(g["principal"]))
        with _com_hoje(_dia(10)):
            r = _corte(dia, 2000)
        _garante(r.status_code == 200, f"38 {variante} → {r.status_code} {_erro(r)}")
        c = _cancelamento(dia)
        _garante(c["regime"] == "dia", f"38: regime {c['regime']}")
        _igual(c["venda_antes"], 3000, "38: venda antes")
        _igual(c["venda_depois"], 2000, "38: venda depois")
        _igual(c["cheio_antes"], 3300, "38: cheio antes")
        _igual(c["cheio_depois"], 2200, "38: cheio depois")
        pr = _no_banco("SELECT sale_value, sale_value_gross, cancelled_at, group_leader_id FROM calendar_events WHERE id = :i", i=g["principal"])[0]
        _igual(pr[0], 2000, "38: venda do principal")
        _igual(pr[1], 2200, "38: cheio do principal")
        _igual(Decimal(str(pr[1])) - Decimal(str(pr[0])), 200, "38: desconto 300 → 200")
        _garante(pr[2] is None, "38: o principal cancelou")
        _garante(len(_historico(g["principal"])) > logs, "38: sem EventLog no principal")
        _garante(_no_banco("SELECT group_leader_id FROM calendar_events WHERE id = :i", i=dia)[0][0] == g["principal"], "38: o dia saiu do grupo")
        if variante == "a_pagar":
            _igual(_soma_vivas(g["principal"]), 50, "38: a pagar vira 50")
        else:
            paga = _linhas_comissao(g["principal"])[0]
            _garante(paga["status"] == "pago" and q(paga["valor"]) == q(75), f"38: a paga ficou: {paga}")
            aj = _ajuste_negativo(g["principal"])
            _igual(aj["valor"], -25, "38: −25")
            _garante(aj["original_id"] == paga["id"] and aj["venda_em"] == aj["liberacao"], f"38: ajuste {aj}")
            _garante((aj["venda_em"].year, aj["venda_em"].month) == (_dia(10).year, _dia(10).month), f"38: −25 fora do primeiro repasse aberto {aj}")
        _igual(_devolucoes(dia)[0]["valor"], 300, "38: devolução ligada ao dia")
        _igual(_delta(dre_antes, _dre(inicio, fim)["dre"]["total"], "gastos_extras"), 0, "38: a devolução entrou nos gastos extras da DRE")
        _igual(_delta(dre_ev_antes, _dre(ini_ev, fim_ev)["dre"]["total"], "receita_bruta"), -1000, "38: DRE do mês do evento com 2.000")
        _igual(_cobranca(g["principal"]).get("saldo"), 800, "38: Home com 800 a receber")
        _garante(_ao_cancelar.count((dia, "so_este_dia", None)) == 1, f"38: ao_cancelar {_ao_cancelar}")
        # "Alterar devolução" do dia: 300 → 30; acima do teto → 409
        comissao_antes, linha_dia = _linhas_comissao(g["principal"]), _cancelamento(dia)
        dev = _devolucoes(dia)[0]["id"]
        aud = _auditoria_de_gastos(dev)[dev]
        r = _alterar_devolucao(dia, 30)
        _garante(r.status_code == 200, f"38 alterar → {r.status_code} {_erro(r)}")
        _igual(_devolucoes(dia)[0]["valor"], 30, "38: devolução do dia")
        _garante(_linhas_comissao(g["principal"]) == comissao_antes and _cancelamento(dia) == linha_dia, "38: a comissão do principal ou a linha dia mexeu")
        _igual(_cobranca(g["principal"]).get("saldo"), 530, "38: cobrança refeita")
        _garante(_auditoria_de_gastos(dev)[dev] > aud, "38: alterar devolução sem auditoria")
        r = _alterar_devolucao(dia, 5000)
        _garante(r.status_code == 409 and _codigo(r) == "acima_do_teto", f"38 teto → {r.status_code} {_erro(r)}")
        _igual(_devolucoes(dia)[0]["valor"], 30, "38: o 409 do teto gravou")
    # BV não pago na proporção da venda nova (num grupo à parte: com BV a cheia não é a dos 50/−25)
    gbv = _grupo("38 bv", comissao=None, bruto=3300)
    bv = _bv(gbv["principal"], 200)
    with _com_hoje(_dia(10)):
        rc = _corte(gbv["dias"][0], 2000)
    _garante(rc.status_code == 200, f"38 bv corte → {rc.status_code} {_erro(rc)}")
    _igual(_no_banco("SELECT amount_brl FROM event_acrescimos WHERE id = :i", i=bv)[0][0], q(Decimal("200") * 2000 / 3000), "38: BV não pago na proporção")
    # piso do dia cortado (P-52): venda 3.000 quitada, venda nova 2.000 → mínimo 1.000
    quitado = _grupo("38 piso", pagos=(3000,), comissao=None)
    r = _corte(quitado["dias"][0], 2000, valor=1000)
    _garante(r.status_code == 200, f"38 piso corte → {r.status_code} {_erro(r)}")
    r = _alterar_devolucao(quitado["dias"][0], 500)
    _garante(r.status_code == 409 and _codigo(r) == "abaixo_do_piso", f"38 P-52 → {r.status_code} {_erro(r)}")
    _igual(_devolucoes(quitado["dias"][0])[0]["valor"], 1000, "38: o 409 do piso gravou")
    # variante 38-comprovante: acrescentar no dia cortado não refaz nada; a cobrança relê o pago
    v = _grupo("38 comprovante")
    _corte(v["dias"][0], 2000)
    antes = (_linhas_comissao(v["principal"]), _cancelamento(v["dias"][0]))
    saldo = _cobranca(v["principal"]).get("saldo")
    r = _post_comprovante("sa", v["dias"][0], 100)
    _garante(r.status_code == 201, f"38-comprovante → {r.status_code} {_erro(r)}")
    _garante((_linhas_comissao(v["principal"]), _cancelamento(v["dias"][0])) == antes, "38-comprovante: algo se refez")
    _igual(Decimal(str(saldo)) - Decimal(str(_cobranca(v["principal"]).get("saldo"))), 100, "38-comprovante: a cobrança não releu o pago")
    # grupo semeado para o abaixo do devolvido: pago 1.500, devolução do dia 1.200; corrigir 500 → 100
    w = _grupo("38 abaixo do devolvido")
    rc = _corte(w["dias"][0], 2000, valor=1200)
    _garante(rc.status_code == 200, f"38 abaixo do devolvido, corte → {rc.status_code} {_erro(rc)}")
    pid = _no_banco("SELECT id FROM event_payments WHERE event_id = :i ORDER BY id LIMIT 1", i=w["dias"][0])[0][0]
    r = _cliente("sa").patch(ROTAS["comprovante_um"].format(id=pid), json={"amount": 100})
    _garante(r.status_code == 409 and _codigo(r) == "pago_abaixo_do_devolvido", f"38-comprovante abaixo → {r.status_code} {_erro(r)}")
    _igual(_no_banco("SELECT amount FROM event_payments WHERE id = :i", i=pid)[0][0], 500, "38: o 409 gravou o comprovante")


def _c38c(rotulo: str) -> None:
    """38c: corte com a base paga, desfazer o "pago" (267c) e resync — Σ 75 em todo momento."""
    g = _grupo(rotulo, venda=4000, comissao="pago", pagos=(1000,))
    with _com_hoje(_dia(10)):
        r = _corte(g["dias"][0], 3000, "nada", None)
    _garante(r.status_code == 200, f"38c corte → {r.status_code} {_erro(r)}")

    def composicao() -> list[tuple]:
        return sorted((x["id"], q(x["valor"]), x["status"]) for x in _linhas_comissao(g["principal"]))

    base = g["linha"]
    depois_corte = composicao()
    aj = [x for x in depois_corte if x[0] != base]
    _garante(
        (base, q(100), "pago") in depois_corte and len(aj) == 1 and aj[0][1:] == (q(-25), "a_pagar"),
        f"38c: depois do corte, esperado 100 paga + −25 a pagar: {depois_corte}",
    )
    _comissoes(_mes(_hoje_sp()))
    _planilha(_mes(_mes_seguinte(_hoje_sp())))
    _garante(composicao() == depois_corte, f"38c: com a base ainda paga, o resync mexeu: {composicao()}")
    ciclo = _linhas_comissao(g["principal"])[0]["venda_em"]
    vend = estado["usuarios"]["vend"]["id"]
    r = _cliente("sa").post(
        ROTAS["planilha_status"],
        json={"item_type": "commission", "item_id": f"{vend}:{_mes(ciclo)}:pago", "status": "nao_pago", "motivo": "verify 306"},
    )
    _garante(r.status_code == 200, f"38c desfazer → {r.status_code} {_erro(r)}")
    depois_desfazer = composicao()
    _garante(
        (base, q(100), "a_pagar") in depois_desfazer and (aj[0][0], q(-25), "a_pagar") in depois_desfazer,
        f"38c: depois do desfazer, esperado 100 a pagar + −25 a pagar: {depois_desfazer}",
    )
    _comissoes(_mes(_hoje_sp()))
    _planilha(_mes(_mes_seguinte(_hoje_sp())))
    vivas = _linhas_comissao(g["principal"])
    _garante(
        len(vivas) == 1 and vivas[0]["id"] == base and q(vivas[0]["valor"]) == q(75),
        f"38c: depois do resync, esperada a base 75 no lugar (nunca 75 − 25 = 50): {vivas}",
    )
    canceladas = [x for x in _linhas_comissao(g["principal"], vivas=False) if x["id"] == aj[0][0]]
    _garante(canceladas and canceladas[0]["status"] == "cancelado", f"38c: o −25 não foi cancelado: {canceladas}")


def c38c_desfazer_no_principal_vivo() -> None:
    from app.financeiro import comissoes_ops

    _c38c("38c")
    # A regra nova (b) da sincronização: com ajuste vivo e a base de volta a `a_pagar`, reconcilia
    # com alvo = cheia. O gancho é `comissoes_ops._reconciliar_ajuste_vivo`; sem ele, Σ 50.
    _sob_mutacao(
        comissoes_ops, "_reconciliar_ajuste_vivo", lambda _o: (lambda *a, **k: None),
        lambda: _c38c("38c mutação"), "sincronização sem a regra nova (b)", base_ja_rodou=True,
    )


def c39_depois_do_38() -> None:
    g = _grupo("39", comissao="pago")
    with _com_hoje(_dia(10)):
        rc = _corte(g["dias"][0], 2000)
        _garante(rc.status_code == 200, f"39 corte → {rc.status_code} {_erro(rc)}")
        aj = _ajuste_negativo(g["principal"])
        r = _patch_comercial(g["principal"])
        _garante(r.status_code == 200, f"39 gravar comercial → {r.status_code} {_erro(r)}")
        _comissoes(_mes(_hoje_sp()))
        _planilha(_mes(_mes_seguinte(_hoje_sp())))
    depois = _ajuste_negativo(g["principal"])
    _garante(
        (depois["id"], q(depois["valor"]), depois["venda_em"], depois["liberacao"]) == (aj["id"], q(aj["valor"]), aj["venda_em"], aj["liberacao"]),
        f"39: o −25 foi sobrescrito: {aj} → {depois}",
    )
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=g["principal"])).get_json()
    _igual(imp.get("ja_devolvido"), 300, "39: já devolvido com os 300 do dia")
    _igual(imp.get("max_devolucao"), 1200, "39: teto do Tudo desconta os 300")
    with _com_hoje(_dia(10)):
        _cancelar_ok(g["principal"], _corpo_cancelar("parte", 200, alcance="todos"))
    resumo = _resumo_api(g["principal"])
    _igual(resumo["devolvido"], 500, "39: já devolvido 300 + 200")
    _igual(resumo["retido"], 1000, "39: retido do resto")
    # cheia sobre a venda de 2.000 a 2,5% = 50; comissão do retido = 50 × 1.000 / 2.000 = 25, no −25
    _igual(_soma_vivas(g["principal"]), 25, "39: comissão do retido depois do resto")
    _garante(_ajuste_negativo(g["principal"])["id"] == aj["id"], "39: o ajuste não absorveu no lugar")
    with _com_hoje(_dia(10)):
        r = _alterar_devolucao(g["dias"][0], 100)
    _garante(r.status_code == 200, f"39 variante → {r.status_code} {_erro(r)}")
    resumo = _resumo_api(g["principal"])
    _igual(resumo["devolvido"], 300, "39 variante: já devolvido pela diferença (500 − 200)")
    _igual(resumo["retido"], 1200, "39 variante: retido refeito (D28)")
    _igual(_soma_vivas(g["principal"]), 30, "39 variante: comissão do retido refeita (50 × 1.200 / 2.000)")
    aj2 = _ajuste_negativo(g["principal"])
    _garante(
        aj2["id"] == aj["id"] and aj2["venda_em"] == aj["venda_em"] and aj2["liberacao"] == aj["liberacao"],
        f"39 variante: o ajuste da paga saiu do lugar: {aj} → {aj2}",
    )


def c40_soltar_e_cache_pago() -> None:
    g = _grupo("40")
    rc = _corte(g["dias"][0], 2500, valor=100)
    _garante(rc.status_code == 200, f"40 corte → {rc.status_code} {_erro(rc)}")
    r = _cliente("sa").delete(ROTAS["grupo"].format(id=g["dias"][0]))
    _recusa_cancelado(r, "40 soltar")
    jinja = _cliente("sa").post(f"/events/{g['dias'][0]}", data={"action": "ungroup_event"})
    _garante(jinja.status_code in (200, 302), f"40 soltar Jinja → {jinja.status_code}")
    _garante(
        _no_banco("SELECT group_leader_id FROM calendar_events WHERE id = :i", i=g["dias"][0])[0][0] == g["principal"],
        "40: o Jinja soltou o dia cancelado",
    )
    outro = _evento("40 outro", venda=500)
    solto = _exemplo_padrao("40 cancelado solto")
    _cancelar_ok(solto["ev"])
    r = _cliente("sa").post(
        ROTAS["grupo"].format(id=g["principal"]),
        json={"leader_event_id": g["principal"], "target_event_ids": [outro, solto["ev"]], "confirm_clear_financials": True},
    )
    _recusa_cancelado(r, "40 agrupar com o cancelado")
    _garante(_no_banco("SELECT group_leader_id FROM calendar_events WHERE id = :i", i=solto["ev"])[0][0] is None, "40: o cancelado entrou no grupo")
    _garante(
        _no_banco("SELECT group_leader_id, sale_value FROM calendar_events WHERE id = :i", i=outro)[0] == (None, Decimal("500.00")),
        "40: o agrupamento recusado mexeu no outro",
    )
    show = _evento_com_elenco("40 show", ["A", "B"])
    sat = _evento_com_elenco("40 show dia 2", ["C"], inicio=_data_isolada())
    _no_banco_escrever("UPDATE calendar_events SET sale_value = 2000, seller_id = :v, sale_date = :d WHERE id = :i", v=estado["usuarios"]["vend"]["id"], d=_hoje_sp(), i=show)
    _agrupar(show, sat)
    role = _escalar(sat, estado["t"])
    _no_banco_escrever("UPDATE event_roles SET payment_status = 'pago' WHERE id = :i", i=role)
    r = _cancelar(show, _corpo_cancelar("nada", None, nome=None, pix=None, alcance="todos"))
    _garante(r.status_code == 409 and _codigo(r) == "cache_pago", f"40 cachê pago → {r.status_code} {_erro(r)}")
    _garante(any(d.get("id") == sat for d in _erro(r).get("dias") or []), "40: a recusa não diz qual dia")
    for ev in (show, sat):
        _nada_gravado(ev, "40")
    ensaio = _evento("40 ensaio", venda=None, tipo="ENSAIO", titulo="🟧 ENSAIO V306 40")
    r = _cancelar(ensaio, {"motivo": "verify"})
    _garante(r.status_code == 409 and _codigo(r) == "ensaio", f"40 ENSAIO → {r.status_code} {_erro(r)}")
    _nada_gravado(ensaio, "40 ENSAIO")


def c41_custo_do_grupo() -> None:
    from app.financeiro import comissoes_ops

    g = _grupo("41 custo")
    inicio_principal = _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=g["principal"])[0][0]
    show_dia = _evento_com_elenco("41 dia com elenco", ["X"], inicio=inicio_principal - timedelta(days=1))
    _agrupar(g["principal"], show_dia)
    _escalar(show_dia, estado["t"])
    _comprovante(show_dia, 200)
    data_grupo = _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=g["principal"])[0][0].date()
    kpi_antes = _detalhe("sa", g["principal"]).get("kpi") or {}
    cobranca_antes = _cobranca(g["principal"])
    _garante(cobranca_antes["data_do_grupo"] == inicio_principal.date() - timedelta(days=1), f"41: o dia mais cedo não abre o grupo (controle) {cobranca_antes}")
    rc = _corte(show_dia, 2800, modo="nada", valor=None)
    _garante(rc.status_code == 200, f"41 corte → {rc.status_code} {_erro(rc)}")
    kpi = _detalhe("sa", g["principal"]).get("kpi") or {}
    _igual(Decimal(str(kpi_antes.get("cost") or 0)) - Decimal(str(kpi.get("cost") or 0)), 300, "41: o cachê do dia cancelado não saiu do custo")
    cobranca = _cobranca(g["principal"])
    _igual(cobranca["recebido"], cobranca_antes["recebido"], "41: o comprovante do dia cancelado saiu da cobrança")
    _igual(cobranca["recebido"], 1700, "41: recebido do grupo com o dia cancelado")
    _garante(cobranca["data_do_grupo"] == data_grupo, f"41: data do grupo na cobrança {cobranca['data_do_grupo']} × {data_grupo}")
    # EducaManto principal: o cachê do dia cancelado sai da base (5% × 300 = +15)
    _configurar_educamanto()
    e = _grupo("41 edu", comissao=None)
    _no_banco_escrever("UPDATE calendar_events SET title = :t, commission_rate = NULL WHERE id = :i", t="(EDU) V306 41 PRINCIPAL", i=e["principal"])
    dia_edu = _evento_com_elenco("41 edu dia", ["X"], inicio=_data_isolada())
    _agrupar(e["principal"], dia_edu)
    _escalar(dia_edu, estado["t"])

    def base_edu() -> Decimal:
        with app.app_context():
            s = db.session.get(SiteSetting, 1)
            return comissoes_ops._event_commission(db.session.get(CalendarEvent, e["principal"]), s)

    antes = base_edu()
    rc = _corte(dia_edu, 3000, modo="nada", valor=None)
    _garante(rc.status_code == 200, f"41 corte EducaManto → {rc.status_code} {_erro(rc)}")
    _igual(base_edu() - antes, 15, "41: o cachê do dia cancelado não saiu da base EducaManto")


def _cliente_descartavel(rotulo: str) -> int:
    from app.models import Client

    with app.app_context():
        c = Client(name=f"{PREFIX}{rotulo}", phone=f"5511{uuid.uuid4().int % 10**9:09d}")
        db.session.add(c)
        db.session.commit()
        estado["clientes"].append(c.id)
        return c.id


def _grupo_42(rotulo: str, *, comissao_paga: bool = True, bv_pago: bool = False, inicio: datetime | None = None) -> dict:
    """O grupo do 42: tudo o que a passagem leva, num grupo de 3 dias com um já cancelado."""
    from app.models import (
        EventClient,
        EventContract,
        EventInstallment,
        EventInvoice,
        EventReimbursement,
        FormResponse,
    )

    inicio = inicio or _data_isolada_no_mes(dias=6)
    g = _grupo(rotulo, dias=2, pagos=(1000,), comissao=None, bruto=3300, inicio=inicio)
    principal, vivo, cancelar_antes = g["principal"], g["dias"][0], g["dias"][1]
    _comprovante(principal, 500)
    _comprovante(vivo, 200)
    bv = _bv(principal, 200)
    bv_pago_id = _bv(principal, 50, status="pago") if bv_pago else None
    _acrescimo(principal, "Transporte", 100)
    cliente = _cliente_descartavel(f"{rotulo} cliente")
    orcamento = _orcamento_de("vend")
    with app.app_context():
        db.session.add(EventInstallment(event_id=principal, due_date=inicio.date(), amount=Decimal("1000"), received=False))
        db.session.add(EventInvoice(event_id=principal, amount=Decimal("3000"), status="pendente"))
        db.session.add(EventContract(event_id=principal, file_path=f"{PREFIX}contrato.pdf", amount=3000))
        db.session.add(EventReimbursement(event_id=principal, description=f"{PREFIX}reembolso", amount=Decimal("80")))
        db.session.add(EventClient(event_id=principal, client_id=cliente, relationship_type="Contratante"))
        db.session.add(FormResponse(form_type="comum", data="{}", contact_name=f"{PREFIX}{rotulo}", event_id=principal, client_id=cliente))
        db.session.commit()
    base = _linha_comissao(principal, 75, status="pago" if comissao_paga else "a_pagar")
    ajuste = _linha_comissao(principal, -25, original_id=base) if comissao_paga else None
    _devolucao_avulsa(principal, 100)
    _no_banco_escrever(
        "UPDATE calendar_events SET group_name = :n, invoice_due_date = :d, orcamento_history_id = :o, client_id = :c "
        "WHERE id = :i",
        n=f"{PREFIX}grupo 42",
        d=inicio.date(),
        o=orcamento,
        c=cliente,
        i=principal,
    )
    _cancelar_ok(cancelar_antes, {**_corpo_cancelar("nada", None, nome=None, pix=None), "venda_nova": 3000})
    return {
        "principal": principal, "novo": vivo, "ja_cancelado": cancelar_antes, "bv": bv, "bv_pago": bv_pago_id,
        "base": base, "ajuste": ajuste, "cliente": cliente, "orcamento": orcamento,
    }


def _retrato_passagem(ids: list[int]) -> dict:
    """Toda tabela pendurada no evento que a passagem leva (TABELAS_DA_PASSAGEM), com o event_id no fim."""
    tabelas = {
        "event_payments": "id, amount",
        "event_installments": "id, due_date, amount, received",
        "event_invoices": "id, amount, status",
        "event_contracts": "id, amount",
        "event_reimbursements": "id, description, amount",
        "event_clients": "id, client_id, relationship_type",
        "form_responses": "id, client_id",
        "event_acrescimos": "id, tipo, amount_brl, bv_payment_status, bv_recipient, bv_pix",
        "commission_payments": "id, amount, status, sale_date, payable_from, seller_id, original_id",
    }
    out = {}
    for tabela, cols in tabelas.items():
        out[tabela] = sorted(
            tuple(r) for r in _no_banco(f"SELECT {cols}, event_id FROM {tabela} WHERE event_id = ANY(:ids)", ids=ids)
        )
    out["devolucoes"] = sorted(
        tuple(r)
        for r in _no_banco(
            "SELECT id, amount, status, event_id FROM special_expenses WHERE event_id = ANY(:ids) AND category = :c",
            ids=ids,
            c=CATEGORIA_DEVOLUCAO,
        )
    )
    return out


_CAMPOS_VISTOS = (
    "sale_value", "sale_value_gross", "seller_id", "sale_date", "commission_rate", "orcamento_history_id",
    "group_name", "invoice_due_date", "group_leader_id",
)


def _campos(event_id: int) -> dict:
    linha = _no_banco(f"SELECT {', '.join(_CAMPOS_VISTOS)} FROM calendar_events WHERE id = :i", i=event_id)[0]
    return dict(zip(_CAMPOS_VISTOS, linha, strict=True))


def _telas_da_venda(g: dict) -> dict:
    """DRE do mês do evento, Comissões e Planilha do ciclo, Dashboard e cobrança: o que a passagem não muda."""
    inicio = _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=g["principal"])[0][0].date()
    ini, fim = date(inicio.year, inicio.month, 1), _mes_seguinte(date(inicio.year, inicio.month, 1)) - timedelta(days=1)
    dre = _dre(ini, fim)["dre"]["total"]
    ini_v, fim_v = _mes_corrente()  # o Comercial recorta pela data da venda, que é hoje
    kpis = _cliente("fin").get(ROTAS["pipeline"].format(a=ini_v.isoformat(), b=fim_v.isoformat())).get_json()["kpis"]
    mes = _mes(_hoje_sp())
    comissoes = _comissoes(mes)
    planilha = sorted(
        (str(i["id"]), round(float(i["amount"] or 0), 2), i["status"])
        for i in _planilha(_mes(_mes_seguinte(_hoje_sp())))
        if i["type"] in ("commission", "bv")
    )
    cobranca = _cobranca(g["novo"])
    return {
        "dre": {k: dre.get(k) for k in ("receita_bruta", "cpv", "comissoes", "gastos_extras", "resultado_liquido")},
        "kpis": {k: kpis.get(k) for k in ("total_vendido", "comissao_prevista")},
        "comissoes": comissoes.get("kpis"),
        "planilha": planilha,
        "cobranca": {k: str(cobranca[k]) for k in ("valor", "recebido", "saldo")},
    }


def c42_passagem() -> None:
    _ao_cancelar.clear()
    _ao_cancelar_estado.clear()
    g = _grupo_42("42")
    antes = _retrato_passagem([g["principal"], g["novo"]])
    campos_antes = _campos(g["principal"])
    telas_antes = _telas_da_venda(g)
    logs = (len(_historico(g["principal"])), len(_historico(g["novo"])))
    corpo = _cancelar_ok(
        g["principal"],
        {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": g["novo"], "venda_nova": 3000},
    )
    depois = _retrato_passagem([g["principal"], g["novo"]])
    for tabela, linhas in antes.items():
        _garante(sorted(x[:-1] for x in linhas) == sorted(x[:-1] for x in depois[tabela]), f"42: {tabela} mudou além do vínculo")
        _garante({x[-1] for x in depois[tabela]} <= {g["novo"]}, f"42: {tabela} ainda no antigo: {depois[tabela]}")
    soma = {t: sum(Decimal(str(x[1])) for x in depois[t]) for t in ("event_payments", "devolucoes")}
    _igual(soma["event_payments"], 1700, "42: comprovantes 1.700")
    _igual(soma["devolucoes"], 100, "42: devolução 100")
    _igual(sum(Decimal(str(x[2] or 0)) for x in depois["event_acrescimos"]), 300, "42: acréscimos 300")
    novo = _campos(g["novo"])
    for k in ("seller_id", "sale_date", "commission_rate", "orcamento_history_id", "group_name", "invoice_due_date"):
        _garante(novo[k] == campos_antes[k], f"42: {k} não passou ao novo ({campos_antes[k]} → {novo[k]})")
    _igual(novo["sale_value"], 3000, "42: venda no novo")
    _igual(novo["sale_value_gross"], 3300, "42: cheio no novo")
    _garante(novo["group_leader_id"] is None, "42: o novo principal ainda aponta a alguém")
    velho = _campos(g["principal"])
    _garante(
        all(velho[k] in (None, False) for k in ("sale_value", "sale_value_gross", "seller_id", "orcamento_history_id", "group_name", "invoice_due_date")),
        f"42: campos não zerados no antigo: {velho}",
    )
    for dia in (g["principal"], g["ja_cancelado"]):
        _garante(_campos(dia)["group_leader_id"] == g["novo"], f"42: o dia {dia} não aponta ao novo")
    _garante(len(_historico(g["principal"])) >= logs[0] + 2 and len(_historico(g["novo"])) > logs[1], "42: sem retrato no histórico dos dois")
    _garante((corpo.get("venda_passou_para") or {}).get("id") == g["novo"], f"42: venda_passou_para {corpo.get('venda_passou_para')}")
    c = _cancelamento(g["principal"])
    _garante(c["regime"] == "dia" and c["passou"], f"42: antigo 1º dia {c}")
    _igual(c["venda_antes"], 3000, "42: venda antes")
    _igual(c["venda_depois"], 3000, "42: venda depois")
    _garante(_telas_da_venda(g) == telas_antes, f"42: as telas mudaram: {telas_antes} → {_telas_da_venda(g)}")
    _garante(_ao_cancelar.count((g["principal"], "so_este_dia", g["novo"])) == 1, f"42: ao_cancelar {_ao_cancelar}")
    momento = [x for x in _ao_cancelar_estado if x["evento"] == g["principal"]]
    _garante(
        momento and momento[0]["venda_do_evento"] is None and q(momento[0]["venda_do_novo"]) == q(3000) and momento[0]["linhas_no_evento"] == 0,
        f"42: ao_cancelar antes da passagem: {momento}",
    )


def c42_aviso_e_ensaio() -> None:
    """42, a parte da H6: na passagem, o elenco do antigo 1º dia é avisado e o ensaio dele sai."""
    g = _grupo_42("42 aviso")
    show = _evento_com_elenco("42 aviso elenco", ["A"], inicio=_data_isolada())
    papel = _escalar(show, estado["t"])
    # o elenco precisa estar no antigo 1º dia: a vaga do show vai a ele
    _no_banco_escrever("UPDATE event_roles SET event_id = :p WHERE id = :r", p=g["principal"], r=papel)
    ensaio = _ensaio(g["principal"], _data_isolada())
    _remocoes.clear()
    _cancelar_ok(
        g["principal"],
        {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": g["novo"], "venda_nova": 3000},
    )
    _esperar_threads()
    _garante(set(_remocoes_por_talento()) == {estado["t"]}, f"42 aviso: elenco do antigo 1º dia {_remocoes_por_talento()}")
    _garante(not _no_banco("SELECT 1 FROM calendar_events WHERE id = :i", i=ensaio), "42 aviso: o ensaio do antigo 1º dia ficou")


def c42b_passagem_com_corte() -> None:
    for paga in (True, False):
        g = _grupo_42(f"42b {'paga' if paga else 'a pagar'}", comissao_paga=paga)
        antes = _retrato_passagem([g["principal"], g["novo"]])
        inicio, fim = _mes_corrente()
        dre_antes = _dre(inicio, fim)["dre"]["total"]
        with _com_hoje(_dia(10)):
            r = _cancelar(
                g["principal"],
                {**_corpo_cancelar("parte", 300), "alcance": "so_este_dia", "novo_principal_id": g["novo"], "venda_nova": 2400},
            )
        _garante(r.status_code == 200, f"42b → {r.status_code} {_erro(r)}")
        _garante(((r.get_json() or {}).get("venda_passou_para") or {}).get("id") == g["novo"], "42b: venda_passou_para")
        depois = _retrato_passagem([g["principal"], g["novo"]])
        for tabela in ("event_payments", "event_installments", "event_invoices", "event_contracts", "event_reimbursements", "event_clients", "form_responses"):
            _garante(sorted(x[:-1] for x in antes[tabela]) == sorted(x[:-1] for x in depois[tabela]), f"42b: {tabela} mudou além do vínculo")
            _garante({x[-1] for x in depois[tabela]} <= {g["novo"]}, f"42b: {tabela} ainda no antigo")
        novo = _no_banco("SELECT sale_value, sale_value_gross FROM calendar_events WHERE id = :i", i=g["novo"])[0]
        _igual(novo[0], 2400, "42b: venda nova no novo principal")
        _igual(novo[1], 2640, "42b: cheio na proporção (sem aumentar o desconto)")
        _igual(_no_banco("SELECT amount_brl FROM event_acrescimos WHERE id = :i", i=g["bv"])[0][0], 160, "42b: BV a pagar acompanhou")
        c = _cancelamento(g["principal"])
        _garante(c["regime"] == "dia" and c["passou"], f"42b: antigo 1º dia {c}")
        _igual(c["venda_antes"], 3000, "42b: venda antes")
        _igual(c["venda_depois"], 2400, "42b: venda depois")
        _igual(c["cheio_antes"], 3300, "42b: cheio antes")
        _igual(c["cheio_depois"], 2640, "42b: cheio depois")
        dev = [d for d in _devolucoes(g["principal"]) if q(d["valor"]) == q(300)]
        _garante(dev, f"42b: devolução de 300 ligada ao antigo 1º dia: {_devolucoes(g['principal'])}")
        _igual(_delta(dre_antes, _dre(inicio, fim)["dre"]["total"], "gastos_extras"), 0, "42b: a devolução entrou nos gastos da DRE")
        imp = _cliente("sa").get(ROTAS["impacto"].format(id=g["novo"])).get_json()
        _igual(imp.get("ja_devolvido"), 400, "42b: já devolvido (100 + 300)")
        # corte como no 38, contra o novo principal: cheia (2.400 − BV 160) × 2,5% = 56
        if paga:
            linhas = _linhas_comissao(g["novo"])
            base = next(x for x in linhas if x["id"] == g["base"])
            _garante(base["status"] == "pago" and q(base["valor"]) == q(75), f"42b: a paga mudou {base}")
            _igual(_soma_vivas(g["novo"]), 56, "42b: Σ = cheia nova (75 paga − 19)")
        else:
            _igual(_soma_vivas(g["novo"]), 56, "42b: a pagar 75 → 56")


def c42b_multa_do_antigo() -> None:
    """42b, a parte da H6: a multa por escalação do antigo 1º dia sai na passagem."""
    g = _grupo_42("42b multa", comissao_paga=False)
    show = _evento_com_elenco("42b multa elenco", ["A"], inicio=_data_isolada())
    papel = _escalar(show, estado["t"])
    _no_banco_escrever("UPDATE event_roles SET event_id = :p WHERE id = :r", p=g["principal"], r=papel)
    _cancelar_ok(
        g["principal"],
        {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": g["novo"],
         "venda_nova": 3000, "multas": [{"role_id": papel, "valor": 90}]},
    )
    multas = _multas_do_evento(g["principal"])
    _garante(len(multas) == 1 and q(multas[0][1]) == q(90), f"42b: multa do antigo 1º dia {multas}")


def c42c_outro_mes() -> None:
    _configurar_educamanto()
    outubro = datetime(2047, 10, 31, 19)
    g = _grupo("42c", dias=1, inicio=outubro, passo=timedelta(days=1), comissao=None, pagos=(1000,))
    _no_banco_escrever("UPDATE calendar_events SET title = :t, with_invoice = true WHERE id = :i", t="(EDU) V306 42C PRINCIPAL", i=g["principal"])
    _no_banco_escrever("UPDATE calendar_events SET title = :t WHERE id = :i", t="(EDU) V306 42C DIA 2", i=g["dias"][0])
    _bv(g["principal"], 200)
    elenco = _evento_com_elenco("42c elenco", ["A"], inicio=_data_isolada())
    papel = _escalar(elenco, estado["t"])
    _no_banco_escrever("UPDATE event_roles SET event_id = :p WHERE id = :r", p=g["dias"][0], r=papel)
    _linha_comissao(g["principal"], 50, vendedor="vend2", liberacao=outubro.date())
    propria = _linha_comissao(g["dias"][0], 40, status="pago")
    # a comissão comum de outro grupo que cruza o mês: data de venda e ciclo ficam
    h = _grupo("42c comum", dias=1, inicio=datetime(2047, 10, 30, 19), passo=timedelta(days=3), comissao="a_pagar", pagos=(1000,))
    linha_comum = _linhas_comissao(h["principal"])[0]
    out_antes = _dre(date(2047, 10, 1), date(2047, 10, 31))["dre"]["total"]
    nov_antes = _dre(date(2047, 11, 1), date(2047, 11, 30))["dre"]["total"]
    _cancelar_ok(g["principal"], {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": g["dias"][0], "venda_nova": 3000})
    _comissoes(_mes(_hoje_sp()))
    edu = [x for x in _linhas_comissao(g["dias"][0]) if x["seller"] == estado["usuarios"]["vend2"]["id"]]
    _garante(edu and edu[0]["liberacao"] == date(2047, 11, 1), f"42c: EducaManto não foi a 01/11: {edu}")
    _cancelar_ok(h["principal"], {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": h["dias"][0], "venda_nova": 3000})
    _comissoes(_mes(_hoje_sp()))
    c2 = next((x for x in _linhas_comissao(h["dias"][0]) if x["id"] == linha_comum["id"]), None)
    _garante(
        c2 and (c2["venda_em"], c2["liberacao"]) == (linha_comum["venda_em"], linha_comum["liberacao"]),
        f"42c: data de venda ou ciclo da comissão comum mudou {linha_comum} → {c2}",
    )
    p = next(x for x in _linhas_comissao(g["dias"][0]) if x["id"] == propria)
    _garante(p["status"] == "pago" and q(p["valor"]) == q(40), "42c: a comissão própria entrou na conta")
    _garante(not [x for x in _linhas_comissao(g["dias"][0]) if x["original_id"] == propria], "42c: nasceu ajuste contra a comissão própria")
    _igual(_soma_vivas(g["dias"][0], "vend"), 40, "42c: a comissão própria entrou na conta (Σ do vendedor)")
    out = _dre(date(2047, 10, 1), date(2047, 10, 31))["dre"]["total"]
    nov = _dre(date(2047, 11, 1), date(2047, 11, 30))["dre"]["total"]
    for k in ("receita_bruta", "impostos", "cpv", "comissoes"):
        if k not in out:
            continue
        _garante(Decimal(str(out[k])) - Decimal(str(out_antes[k])) <= 0 and Decimal(str(nov[k])) - Decimal(str(nov_antes[k])) >= 0, f"42c: {k} não foi de outubro a novembro")
    # as duas passagens (g, de 31/10 a 01/11, e h, de 30/10 a 02/11) levam 3.000 cada a novembro
    _igual(_delta(nov_antes, nov, "receita_bruta"), 6000, "42c: receita em novembro")
    _igual(_delta(out_antes, out, "receita_bruta"), -6000, "42c: outubro ainda com a receita")
    bv_nov = [i for i in _planilha("2047-11") if i["type"] == "bv"]
    _garante(any(int(i["id"]) in {r[0] for r in _no_banco("SELECT id FROM event_acrescimos WHERE event_id = :i", i=g["dias"][0])} for i in bv_nov), "42c: BV fora da Planilha de novembro")
    jinja_out = _dre_jinja(date(2047, 10, 1), date(2047, 10, 31))
    _garante(Decimal(str(jinja_out["drg_total"]["receita_bruta"])) == Decimal(str(out["receita_bruta"])), "42c: Jinja de outubro diverge da API")


def c42d_recusas_da_passagem() -> None:
    from app.calendar import group_ops

    g = _grupo_42("42d")
    antes = _retrato_passagem([g["principal"], g["novo"], g["ja_cancelado"]])
    campos = {x: _campos(x) for x in (g["principal"], g["novo"], g["ja_cancelado"])}

    def nada_mudou(rotulo: str) -> None:
        _garante(_retrato_passagem([g["principal"], g["novo"], g["ja_cancelado"]]) == antes, f"42d {rotulo}: alguma linha mudou de vínculo ou valor")
        _garante({x: _campos(x) for x in campos} == campos, f"42d {rotulo}: campos do grupo mudaram")
        _garante(_cancelado_em(g["principal"]) is None and _cancelamento(g["principal"]) is None, f"42d {rotulo}: o antigo cancelou")

    corpo_ok = {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": g["novo"], "venda_nova": 3000}
    r = _cancelar(g["principal"], {**_corpo_cancelar("nada", None, nome=None, pix=None), "venda_nova": 3000})
    _garante(r.status_code == 400 and "alcance" in (_erro(r).get("fields") or {}), f"42d alcance → {r.status_code} {_erro(r)}")
    nada_mudou("alcance")
    # um dia vivo do grupo que não é o mais cedo
    tarde = _evento("42d dia tarde", venda=None, inicio=_data_isolada(dias=30))
    _agrupar(g["principal"], tarde)
    r = _cancelar(g["principal"], {**corpo_ok, "novo_principal_id": tarde})
    _garante(r.status_code == 409 and _codigo(r) == "grupo_mudou", f"42d não é o mais cedo → {r.status_code} {_erro(r)}")
    nada_mudou("não é o mais cedo")
    _no_banco_escrever("UPDATE calendar_events SET group_leader_id = NULL WHERE id = :i", i=tarde)
    # principal de grupo sem outro dia vivo
    s = _grupo("42d sozinho", dias=1, pagos=(), comissao=None)
    _cancelar_ok(s["dias"][0], {**_corpo_cancelar("nada", None, nome=None, pix=None), "venda_nova": 3000})
    r = _cancelar(s["principal"], {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "venda_nova": 3000})
    _garante(r.status_code == 409 and _codigo(r) == "sem_outro_dia_vivo", f"42d sem outro dia vivo → {r.status_code} {_erro(r)}")
    _garante(_cancelado_em(s["principal"]) is None, "42d: o principal sem outro dia vivo cancelou")
    pend = _devolucao_avulsa(g["principal"], 10, status="pendente")
    r = _cancelar(g["principal"], corpo_ok)
    _garante(r.status_code == 409 and _codigo(r) == "devolucao_pendente", f"42d pendente → {r.status_code} {_erro(r)}")
    _no_banco_escrever("DELETE FROM special_expenses WHERE id = :i", i=pend)
    nada_mudou("pendente")
    r = _cliente("com").post(ROTAS["cancelar"].format(id=g["principal"]), json=corpo_ok)
    _garante(r.status_code == 403, f"42d COMERCIAL → {r.status_code}")
    nada_mudou("COMERCIAL")
    real = group_ops.passar_venda  # sem o gancho, vermelho (AttributeError)

    def explode(*a, **k):
        real(*a, **k)
        raise RuntimeError("falha injetada no meio da passagem (verify 306)")

    group_ops.passar_venda = explode
    try:
        try:
            r = _cancelar(g["principal"], corpo_ok)
        except RuntimeError:
            r = None  # com TESTING a exceção sobe pelo test client
    finally:
        group_ops.passar_venda = real
    _garante(r is None or r.status_code >= 500, f"42d exceção injetada → {r.status_code if r else None}")
    nada_mudou("exceção injetada")
    # duas confirmações simultâneas: uma vence, a outra recebe 409
    respostas: list = []

    def confirmar() -> None:
        respostas.append(_cancelar(g["principal"], corpo_ok))

    fios = [threading.Thread(target=confirmar) for _ in range(2)]
    for f in fios:
        f.start()
    for f in fios:
        f.join(timeout=120)
    codigos = sorted(x.status_code for x in respostas)
    _garante(codigos == [200, 409], f"42d simultâneas → {codigos} {[_erro(x) for x in respostas]}")
    _garante(len(_no_banco("SELECT id FROM event_cancellations WHERE event_id = :i", i=g["principal"])) == 1, "42d: dois congelamentos")


def c42d_cache_pago() -> None:
    """42d, a parte da H6: cachê pago no antigo 1º dia → 409 cache_pago, nada muda."""
    g = _grupo_42("42d cachê")
    show = _evento_com_elenco("42d cachê elenco", ["A"], inicio=_data_isolada())
    papel = _escalar(show, estado["t"])
    _no_banco_escrever("UPDATE event_roles SET event_id = :p, payment_status = 'pago' WHERE id = :r", p=g["principal"], r=papel)
    antes = _retrato_passagem([g["principal"], g["novo"]])
    r = _cancelar(
        g["principal"],
        {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": g["novo"], "venda_nova": 3000},
    )
    _garante(r.status_code == 409 and _codigo(r) == "cache_pago", f"42d cachê pago → {r.status_code} {_erro(r)}")
    _garante(_retrato_passagem([g["principal"], g["novo"]]) == antes, "42d cachê: alguma linha mudou")
    _nada_gravado(g["principal"], "42d cachê")


# ── B6 · História 6 ────────────────────────────────────────────────────────────────────────────
FRASE_CACHE_PAGO = (
    "Este evento tem cachê pago ao elenco e não pode ser cancelado. Para devolver dinheiro à cliente, "
    "lance uma Devolução em Gastos Extras."
)


def _nada_avisado(event_id: int, marco: int, rotulo: str) -> None:
    """Depois de uma recusa: nenhum sino, nenhum e-mail, nenhuma chamada de remoção ao Google."""
    _esperar_threads()
    for kind in ("evento.cancelado", "evento.cancelado_escala"):
        _garante(not _avisos_do_ato(kind, event_id), f"{rotulo}: sino {kind} depois da recusa")
    _garante(not _remocoes, f"{rotulo}: e-mail de remoção depois da recusa")
    _garante(not google.deletes(marco), f"{rotulo}: remoção no Google depois da recusa {google.deletes(marco)}")


def c33_cache_pago() -> None:
    passado = datetime.combine(_hoje_sp() - timedelta(days=20), datetime.min.time()).replace(hour=19)
    for estado_pag in ("pago", "no_banco"):
        show = _evento_com_elenco(f"33 {estado_pag}", ["A"], inicio=passado)
        _no_banco_escrever("UPDATE calendar_events SET sale_value = 2000, seller_id = :v WHERE id = :i", v=estado["usuarios"]["vend"]["id"], i=show)
        role = _escalar(show, estado["t"])
        _no_banco_escrever("UPDATE event_roles SET payment_status = :s WHERE id = :i", s=estado_pag, i=role)
        ensaio = _ensaio(show, _data_isolada())
        imp = _cliente("sa").get(ROTAS["impacto"].format(id=show)).get_json()
        _garante((imp.get("cache_pago") or 0) > 0, f"33: impacto sem cache_pago ({estado_pag})")
        _remocoes.clear()
        marco = google.marco()
        r = _cancelar(show, _corpo_cancelar("nada", None, nome=None, pix=None))
        _garante(r.status_code == 409 and _codigo(r) == "cache_pago", f"33 {estado_pag} → {r.status_code} {_erro(r)}")
        _garante(_erro(r).get("message") == FRASE_CACHE_PAGO, f"33: frase do cache_pago {_erro(r).get('message')!r}")
        _nada_gravado(show, "33")
        _garante(_no_banco("SELECT 1 FROM calendar_events WHERE id = :i", i=ensaio), "33: o ensaio saiu do banco")
        _nada_avisado(show, marco, f"33 {estado_pag}")
    marcado = _evento_com_elenco("33 marcado", ["A"], inicio=passado)
    role = _escalar(marcado, estado["t"])
    _no_banco_escrever("UPDATE event_roles SET payment_status = 'pago' WHERE id = :i", i=role)
    _marcar_sumido(marcado)
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=marcado)).get_json()
    _garante((imp.get("cache_pago") or 0) > 0, "33: impacto do marcado sem cache_pago")
    _remocoes.clear()
    marco = google.marco()
    r = _cancelar(marcado, _corpo_cancelar("nada", None, nome=None, pix=None))
    _garante(r.status_code == 409 and _codigo(r) == "cache_pago", f"33 marcado → {r.status_code} {_erro(r)}")
    _nada_gravado(marcado, "33 marcado")
    _garante(
        _no_banco("SELECT google_missing_since FROM calendar_events WHERE id = :i", i=marcado)[0][0] is not None,
        "33: o marcado perdeu a marca (só lhe resta 'Devolver ao Google')",
    )
    _nada_avisado(marcado, marco, "33 marcado")
    presenca = _evento_com_elenco("33 presença", ["A"], inicio=passado)
    role = _escalar(presenca, estado["t"], vaga="Técnico de Som (Presença)")
    _no_banco_escrever("UPDATE event_roles SET payment_status = 'pago' WHERE id = :i", i=role)
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=presenca)).get_json()
    _garante(not imp.get("cache_pago"), "33: a vaga de presença contou como cachê pago")
    r = _cancelar(presenca, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    _garante(r.status_code == 200, f"33: a recusa contou a vaga de presença → {r.status_code} {_erro(r)}")


def _ensaio(show: int, quando: datetime) -> int:
    gid = f"{GID}-ens-{uuid.uuid4().hex[:8]}"
    google.registrar(_item_google(gid, f"🟧 ENSAIO V306 {show}", quando, quando + timedelta(hours=2)))
    with app.app_context():
        e = CalendarEvent(
            title=f"🟧 ENSAIO V306 {show}",
            event_type="ENSAIO",
            start_at=quando,
            end_at=quando + timedelta(hours=2),
            google_event_id=gid,
            parent_event_id=show,
            location=f"{PREFIX}Sala de ensaio",
            description=MARCADOR,
        )
        db.session.add(e)
        db.session.commit()
        estado["eventos"][e.id] = gid
        return e.id


def c43_ensaios() -> None:
    show = _evento_com_elenco("43 show", ["A"])
    inicio = _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=show)[0][0]
    ensaios = [_ensaio(show, inicio - timedelta(days=d)) for d in (3, 2)]
    alvos = {
        _no_banco("SELECT google_event_id FROM calendar_events WHERE id = :i", i=x)[0][0]: x
        for x in [show, *ensaios]
    }
    datas = {x: _no_banco("SELECT start_at, location FROM calendar_events WHERE id = :i", i=x)[0] for x in ensaios}
    marco = google.marco()
    _commit_antes_do_google.clear()
    corpo = _cancelar_ok(show, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    for e in ensaios:
        _garante(not _no_banco("SELECT 1 FROM calendar_events WHERE id = :i", i=e), f"43: ensaio {e} ficou no banco")
    _garante(sorted(google.deletes(marco)) == sorted(alvos), f"43: remoções {google.deletes(marco)} × {sorted(alvos)}")
    # O dublê anota, a cada remoção, se o cancelamento já estava commitado (conexão separada).
    _garante(_commit_antes_do_google and all(_commit_antes_do_google), f"43: Google antes do commit {_commit_antes_do_google}")
    itens = corpo.get("ensaios_cancelados") or []
    _garante(sorted(i.get("id") for i in itens) == sorted(ensaios), f"43: ensaios_cancelados {itens}")
    for i in itens:
        quando, local = datas[i["id"]]
        _garante(
            (i.get("data") or "")[:10] == quando.date().isoformat() and i.get("local") == local,
            f"43: ensaio {i} × {quando} {local}",
        )
    hist = [m for m, _ in _historico(show)]
    for e in ensaios:
        quando, local = datas[e]
        _garante(
            any(quando.strftime("%d/%m") in m and local in m for m in hist),
            f"43: o histórico não traz data e local do ensaio {e}: {hist}",
        )
    travado = _evento_com_elenco("43 trava", ["A"])
    _ensaio(travado, _data_isolada())
    app.config[TRAVA] = True
    marco = google.marco()
    corpo = _cancelar_ok(travado, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    _garante(not google.deletes(marco) and corpo.get("aviso"), "43: com a trava, chamou o Google ou sem aviso")
    app.config[TRAVA] = False
    falha = _evento_com_elenco("43 falha", ["A"])
    e1 = _ensaio(falha, _data_isolada())
    e2 = _ensaio(falha, _data_isolada())
    google.falhar_delete.add(estado["eventos"][e2])
    corpo = _cancelar_ok(falha, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    _garante(corpo.get("aviso") and _cancelado_em(falha) is not None, "43: a falha desfez o cancelamento ou não avisou")
    for e in (e1, e2):
        _garante(not _no_banco("SELECT 1 FROM calendar_events WHERE id = :i", i=e), f"43: com a falha, o ensaio {e} ficou no banco")
    # grupo com ensaio em 2 dias: os dois saem no mesmo ato
    d1 = _evento_com_elenco("43 dia 1", ["A"])
    d2 = _evento_com_elenco("43 dia 2", ["A"])
    _agrupar(d1, d2)
    g1, g2 = _ensaio(d1, _data_isolada()), _ensaio(d2, _data_isolada())
    _cancelar_ok(d1, {"motivo": "verify 306", "devolucao": {"modo": "nada"}, "alcance": "todos"})
    for e in (g1, g2):
        _garante(not _no_banco("SELECT 1 FROM calendar_events WHERE id = :i", i=e), f"43 grupo: o ensaio {e} ficou")
    # regressão: o botão "Cancelar ensaio" e a troca SHOW → outro seguem apagando pelo mesmo caminho
    vivo = _evento_com_elenco("43 vivo", ["A"])
    ens = _ensaio(vivo, _data_isolada())
    gid = estado["eventos"][ens]
    marco = google.marco()
    r = _cliente("sa").delete(f"/api/ensaios/{ens}")
    _garante(r.status_code == 200, f"43 Cancelar ensaio → {r.status_code} {_erro(r)}")
    _garante(not _no_banco("SELECT 1 FROM calendar_events WHERE id = :i", i=ens), "43: o Cancelar ensaio não apagou")
    _garante(google.deletes(marco) == [gid], f"43: o Cancelar ensaio no Google {google.deletes(marco)}")
    _garante(_cancelado_em(vivo) is None, "43: o Cancelar ensaio cancelou o show")
    troca = _evento_com_elenco("43 troca", ["A"])
    ens2 = _ensaio(troca, _data_isolada())
    marco = google.marco()
    from app.calendar import event_ops

    with app.app_context():
        ev = db.session.get(CalendarEvent, troca)
        ev.event_type = "R&I"
        db.session.flush()
        event_ops.aplicar_troca_de_tipo(ev, "SHOW", "R&I", actor_name="verify 306", tz=ZoneInfo("America/Sao_Paulo"))
        db.session.commit()
    _garante(not _no_banco("SELECT 1 FROM calendar_events WHERE id = :i", i=ens2), "43: a troca SHOW → R&I não apagou o ensaio")
    _garante(google.deletes(marco) == [estado["eventos"][ens2]], f"43: a troca no Google {google.deletes(marco)}")


def _avisos(kind: str, event_id: int) -> list:
    return _no_banco(
        "SELECT user_id, severity, link_path, dedupe_key FROM notifications WHERE kind = :k AND entity_id = :i",
        k=kind,
        i=event_id,
    )


def _avisos_do_ato(kind: str, url_id: int) -> list:
    """Os sinos de um ato, pela chave do ato (data-model §6.3): o id do evento da URL."""
    if kind == "evento.cancelado":
        sql, chave = "dedupe_key = :c", f"evento.cancelado:{url_id}"
    else:
        sql, chave = "dedupe_key LIKE :c", f"evento.cancelado_escala:{url_id}:%"
    return _no_banco(
        f"SELECT user_id, severity, link_path, dedupe_key, entity_id FROM notifications WHERE kind = :k AND {sql}",
        k=kind,
        c=chave,
    )


def _ativos_do_papel(papel: str) -> set[int]:
    return {
        r[0]
        for r in _no_banco(
            "SELECT u.id FROM users u JOIN user_roles ur ON ur.user_id = u.id JOIN roles r ON r.id = ur.role_id "
            "WHERE r.name = :n AND u.is_active AND u.has_access",
            n=papel,
        )
    }


def _remocoes_por_talento() -> dict[int, list[tuple[int, str]]]:
    """E-mails de remoção do espião: talento → [(id do dia, personagem)]."""
    out: dict[int, list[tuple[int, str]]] = {}
    for chamada in _remocoes:
        talento, evento, personagem = chamada["args"][:3]
        out.setdefault(getattr(talento, "id", talento), []).append((getattr(evento, "id", evento), personagem))
    return out


def _personagem(role_id: int) -> str:
    return _no_banco("SELECT character_name FROM event_roles WHERE id = :i", i=role_id)[0][0]


def c44_avisos() -> None:
    ensaio_users, casting_users = _ativos_do_papel(RoleName.ENSAIO), _ativos_do_papel(RoleName.CASTING)
    d1 = _evento_com_elenco("44 dia 1", ["A", "B", "C"], inicio=_dias_a_frente(2))
    d2 = _evento_com_elenco("44 dia 2", ["A"], inicio=_dias_a_frente(3))
    _agrupar(d1, d2)
    _ensaio(d1, _data_isolada())
    t_d1 = _escalar(d1, estado["t"])
    _escalar(d2, estado["t"])
    t2_d1 = _escalar(d1, estado["t2"])
    _escalar(d1, estado["t_sem_pix"], convite="rejected")
    _remocoes.clear()
    corpo = _cancelar_ok(d1, {"motivo": "verify 306", "devolucao": {"modo": "nada"}, "alcance": "todos"})
    _esperar_threads()
    avisos = _avisos_do_ato("evento.cancelado", d1)
    por_usuario: dict[int, int] = {}
    for a in avisos:
        por_usuario[a[0]] = por_usuario.get(a[0], 0) + 1
    _garante(set(por_usuario) == ensaio_users and set(por_usuario.values()) == {1}, f"44: evento.cancelado {por_usuario} × ENSAIO {ensaio_users}")
    emails = _remocoes_por_talento()
    _garante(set(emails) == {estado["t"], estado["t2"]}, f"44: e-mails {emails} (uma vez por pessoa; quem recusou fora)")
    _garante(all(len(v) == 1 for v in emails.values()), f"44: e-mail repetido {emails}")
    _garante(emails[estado["t"]] == [(d1, _personagem(t_d1))], f"44: e-mail do dia mais cedo {emails[estado['t']]}")
    _garante(emails[estado["t2"]] == [(d1, _personagem(t2_d1))], f"44: e-mail de t2 {emails[estado['t2']]}")
    escala = _avisos_do_ato("evento.cancelado_escala", d1)
    dias_avisados = {(a[0], int(a[3].rsplit(":", 1)[1])) for a in escala}
    _garante(dias_avisados == {(u, d) for u in casting_users for d in (d1, d2)}, f"44: evento.cancelado_escala {sorted(dias_avisados)}")
    _garante(all("aba=producao" in (a[2] or "") for a in escala), f"44: link da escala {escala}")
    _garante(all(a[1] == "urgent" for a in escala), "44: a 2 dias o sino não é urgent")
    _garante(
        corpo.get("avisados") == {"email": 2, "ensaio": len(ensaio_users), "casting": len(escala)},
        f"44: avisados {corpo.get('avisados')}",
    )
    elenco = _resumo_api(d1).get("elenco") or []
    _garante(
        sorted((e.get("talent_id"), e.get("dia", {}).get("id")) for e in elenco)
        == sorted([(estado["t"], d1), (estado["t"], d2), (estado["t2"], d1)]),
        f"44: lista do ato {elenco}",
    )
    # sem ensaio: avisa os escalados e não a equipe de Ensaio; a 60 dias o sino é info
    sem_ensaio = _evento_com_elenco("44 sem ensaio", ["A"], inicio=_dias_a_frente(60))
    _escalar(sem_ensaio, estado["t"])
    _remocoes.clear()
    _cancelar_ok(sem_ensaio, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    _esperar_threads()
    _garante(not _avisos_do_ato("evento.cancelado", sem_ensaio), "44: sem ensaio avisou a equipe de Ensaio")
    _garante(set(_remocoes_por_talento()) == {estado["t"]}, "44: sem ensaio não avisou o escalado")
    a60 = _avisos_do_ato("evento.cancelado_escala", sem_ensaio)
    _garante(a60 and all(a[1] == "info" for a in a60), f"44: a 60 dias o sino não é info (ou não veio): {a60}")
    # sem elenco: nenhum sino ao Casting
    vazio = _evento_com_elenco("44 sem elenco", ["A"])
    _cancelar_ok(vazio, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    _garante(not _avisos_do_ato("evento.cancelado_escala", vazio), "44: sem elenco, sino ao Casting")
    # corte: só o elenco do dia cortado, com a data dele
    c1 = _evento_com_elenco("44 corte 1", ["A"], inicio=_dias_a_frente(20))
    c2 = _evento_com_elenco("44 corte 2", ["A", "B"], inicio=_dias_a_frente(21))
    _agrupar(c1, c2)
    _no_banco_escrever("UPDATE calendar_events SET sale_value = 2000, sale_value_gross = 2000 WHERE id = :i", i=c1)
    _escalar(c1, estado["t"])
    v_c2 = _escalar(c2, estado["t"])
    _escalar(c1, estado["t2"])
    _remocoes.clear()
    r = _corte(c2, 1500, modo="nada", valor=None)
    _garante(r.status_code == 200, f"44 corte → {r.status_code} {_erro(r)}")
    _esperar_threads()
    _garante(_remocoes_por_talento() == {estado["t"]: [(c2, _personagem(v_c2))]}, f"44: no corte, e-mails {_remocoes_por_talento()}")
    _garante({int(a[3].rsplit(":", 1)[1]) for a in _avisos_do_ato("evento.cancelado_escala", c2)} == {c2}, "44: no corte, sino de outro dia")
    # passagem: o elenco do antigo 1º dia é avisado
    p1 = _evento_com_elenco("44 passagem 1", ["A"], inicio=_dias_a_frente(30))
    p2 = _evento_com_elenco("44 passagem 2", ["A"], inicio=_dias_a_frente(31))
    _agrupar(p1, p2)
    _no_banco_escrever("UPDATE calendar_events SET sale_value = 2000, sale_value_gross = 2000 WHERE id = :i", i=p1)
    v_p1 = _escalar(p1, estado["t2"])
    _remocoes.clear()
    _cancelar_ok(p1, {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": p2, "venda_nova": 2000})
    _esperar_threads()
    _garante(_remocoes_por_talento() == {estado["t2"]: [(p1, _personagem(v_p1))]}, f"44: na passagem, e-mails {_remocoes_por_talento()}")
    # 409 não avisa
    recusado = _evento_com_elenco("44 recusado", ["A"])
    _escalar(recusado, estado["t"])
    _devolucao_avulsa(recusado, 10, status="pendente")
    _ensaio(recusado, _data_isolada())
    _remocoes.clear()
    marco = google.marco()
    r = _cancelar(recusado, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    _garante(r.status_code == 409, f"44 recusado → {r.status_code} {_erro(r)}")
    _nada_avisado(recusado, marco, "44 recusado")


def _multas_do_evento(event_id: int) -> list[tuple]:
    return _no_banco(
        "SELECT id, amount, status, payment_status, supplier_name, supplier_pix, expense_date, disbursement_type "
        "FROM special_expenses WHERE event_id = :i AND category = :c ORDER BY id",
        i=event_id,
        c=CATEGORIA_MULTA,
    )


def _nome_do_talento(talento_id: int) -> str:
    return _no_banco("SELECT full_name FROM talents WHERE id = :i", i=talento_id)[0][0]


def _dias_a_frente(n: int) -> datetime:
    return datetime.combine(_hoje_sp() + timedelta(days=n), datetime.min.time()).replace(hour=19)


def _show_com_dinheiro(rotulo: str, personagens: list[str], dias: int) -> int:
    """Show do caminho real com a venda do exemplo padrão: 2.000 a 5%, BV 200, pago 1.000."""
    show = _evento_com_elenco(rotulo, personagens, inicio=_dias_a_frente(dias))
    _no_banco_escrever(
        "UPDATE calendar_events SET sale_value = 2000, sale_value_gross = 2000, seller_id = :v, sale_date = :d, "
        "commission_rate = 5 WHERE id = :i",
        v=estado["usuarios"]["vend"]["id"],
        d=_hoje_sp(),
        i=show,
    )
    _bv(show, 200)
    _comprovante(show, 1000)
    return show


def c45_multa_no_ato() -> None:
    inicio, fim = _mes_corrente()
    show = _show_com_dinheiro("45 multa", ["A", "B", "C"], 60)
    r1 = _escalar(show, estado["t"])
    r2 = _escalar(show, estado["t_sem_pix"])
    recusou = _escalar(show, estado["t2"], convite="rejected")
    imp = _cliente("sa").get(ROTAS["impacto"].format(id=show)).get_json()
    _garante(imp.get("faltam_dias") in (59, 60, 61), f"45: faltam_dias {imp.get('faltam_dias')}")
    bloco = imp.get("elenco") or []
    vagas = {e.get("role_id") for e in bloco}
    _garante({r1, r2} <= vagas and recusou not in vagas, f"45: bloco do elenco {vagas} (quem recusou fica fora)")
    _garante(not any(k.startswith("multa") and e[k] for e in bloco for k in e), f"45: o bloco sugeriu multa: {bloco}")
    antes = _dre(inicio, fim)["dre"]["total"]
    corpo = _corpo_cancelar("parte", 600, multas=[{"role_id": r1, "valor": 150}, {"role_id": r2, "valor": 0}])
    _cancelar_ok(show, corpo)
    multas = _multas_do_evento(show)
    _garante(len(multas) == 1, f"45: multas {multas}")
    gid, valor, status, pagamento, nome, pix, data, tipo = multas[0]
    _igual(valor, 150, "45: multa")
    _garante(status == "aprovado" and pagamento == "nao_pago" and tipo == "fornecedor", f"45: gasto {multas[0]}")
    _garante(nome == _nome_do_talento(estado["t"]) and pix == PIX, f"45: nome e PIX do talento: {nome!r} {pix!r}")
    _garante(data == _cancelado_em(show).date(), f"45: data da multa {data} × cancelamento {_cancelado_em(show)}")
    resumo = _resumo_api(show)
    _igual(resumo["retido"], 400, "45: retido")
    _igual(resumo["comissao"]["retido"], 18, "45: comissão do retido")
    _igual(resumo["bvs"][0]["conta"], 40, "45: BV do retido")
    elenco = resumo.get("elenco") or []
    _garante(len(elenco) == 2, f"45: lista do ato com quem recusou ou sem um escalado: {elenco}")
    depois = _dre(inicio, fim)["dre"]["total"]
    _igual(_delta(antes, depois, "gastos_extras"), 150, "45: DRE do mês do cancelamento, gastos +150")
    _igual(_delta(antes, depois, "resultado_liquido"), 342 - 150, "45: resultado +342 − 150")
    item = [i for i in _planilha(_mes(_hoje_sp())) if i["type"] == "expense" and int(i["id"]) == gid]
    _garante(item and abs(float(item[0]["amount"]) - 150) < 0.005, f"45: multa fora da Planilha do mês: {item}")
    r = _patch_gasto(gid, "fin", description=f"{PREFIX}multa editada")
    _garante(r.status_code == 200, f"45: multa não editável em Gastos Extras → {r.status_code} {_erro(r)}")
    # a 2 dias, talento sem PIX
    sem = _evento_com_elenco("45 sem pix", ["A"], inicio=_dias_a_frente(2))
    rs = _escalar(sem, estado["t_sem_pix"])
    imp2 = _cliente("sa").get(ROTAS["impacto"].format(id=sem)).get_json()
    _garante(imp2.get("faltam_dias") in (1, 2, 3), f"45: faltam_dias a 2 dias {imp2.get('faltam_dias')}")
    _garante(rs in {e.get("role_id") for e in imp2.get("elenco") or []}, "45: o bloco não veio a 2 dias")
    _cancelar_ok(sem, {"motivo": "verify 306", "devolucao": {"modo": "nada"}, "multas": [{"role_id": rs, "valor": 80}]})
    m2 = _multas_do_evento(sem)
    _garante(len(m2) == 1 and m2[0][5] in (None, ""), f"45: sem PIX ganhou PIX ou não nasceu: {m2}")
    item = [i for i in _planilha(_mes(_hoje_sp())) if i["type"] == "expense" and int(i["id"]) == m2[0][0]]
    _garante(item and not item[0].get("pix_key"), f"45: a Planilha não mostra 'sem PIX': {item}")
    # escalado em 2 dias de um grupo: 2 linhas no bloco e 2 gastos
    d1 = _evento_com_elenco("45 dia 1", ["A"], inicio=_dias_a_frente(70))
    d2 = _evento_com_elenco("45 dia 2", ["A"], inicio=_dias_a_frente(71))
    _agrupar(d1, d2)
    v1, v2 = _escalar(d1, estado["t"]), _escalar(d2, estado["t"])
    imp3 = _cliente("sa").get(ROTAS["impacto"].format(id=d1)).get_json()
    linhas = [e for e in imp3.get("elenco") or [] if e.get("role_id") in (v1, v2)]
    _garante(len(linhas) == 2 and {e.get("day_event_id") for e in linhas} == {d1, d2}, f"45: escalado em 2 dias {linhas}")
    _cancelar_ok(
        d1,
        {
            "motivo": "verify 306",
            "devolucao": {"modo": "nada"},
            "alcance": "todos",
            "multas": [{"role_id": v1, "valor": 100}, {"role_id": v2, "valor": 120}],
        },
    )
    gastos = _multas_do_evento(d1) + _multas_do_evento(d2)
    _garante(sorted(q(g[1]) for g in gastos) == [q(100), q(120)], f"45: uma multa por escalação: {gastos}")


def c45b_multa_depois() -> None:
    inicio, fim = _mes_corrente()
    show = _show_com_dinheiro("45b", ["A"], 60)
    _escalar(show, estado["t"])
    with _com_hoje(_dia(1)):
        _cancelar_ok(show, _corpo_cancelar("parte", 600))
    resumo = _resumo_api(show)
    elenco = resumo.get("elenco") or []
    _garante(elenco, "45b: cancelamento.elenco vazio")
    eid = elenco[0]["elenco_id"]
    antes_dre = _dre(inicio, fim)["dre"]["total"]
    with _com_hoje(_dia(10)):
        r = _cliente("sa").post(ROTAS["multas"].format(id=show), json={"multas": [{"elenco_id": eid, "valor": 150}]})
    _garante(r.status_code == 200, f"45b → {r.status_code} {_erro(r)}")
    multas = _multas_do_evento(show)
    _garante(len(multas) == 1 and (r.get_json() or {}).get("gastos") == [multas[0][0]], f"45b: gastos {multas} × {r.get_json()}")
    gid, valor, status, pagamento, nome, pix, data, tipo = multas[0]
    _igual(valor, 150, "45b: multa")
    _garante(status == "aprovado" and pagamento == "nao_pago" and tipo == "fornecedor", f"45b: gasto {multas[0]}")
    _garante(nome == _nome_do_talento(estado["t"]) and pix == PIX, f"45b: nome e PIX {nome!r} {pix!r}")
    _garante(data == _dia(10), f"45b: data do lançamento {data}, esperado {_dia(10)} (não a do cancelamento)")
    depois = _resumo_api(show)
    _igual(depois["retido"], resumo["retido"], "45b: retido mudou")
    _igual(depois["comissao"]["retido"], resumo["comissao"]["retido"], "45b: comissão mudou")
    _igual(depois["bvs"][0]["conta"], resumo["bvs"][0]["conta"], "45b: BV mudou")
    _igual(_delta(antes_dre, _dre(inicio, fim)["dre"]["total"], "gastos_extras"), 150, "45b: DRE do mês do lançamento +150")
    item = [i for i in _planilha(_mes(_dia(10))) if i["type"] == "expense" and int(i["id"]) == gid]
    _garante(item, "45b: multa fora da Planilha do mês do lançamento")
    vivo = _evento_com_elenco("45b vivo", ["A"])
    r = _cliente("sa").post(ROTAS["multas"].format(id=vivo), json={"multas": [{"elenco_id": eid, "valor": 1}]})
    _garante(r.status_code == 409 and _codigo(r) == "nao_cancelado", f"45b vivo → {r.status_code} {_erro(r)}")
    _garante(not _multas_do_evento(vivo), "45b: o vivo ganhou multa")
    for apelido in ("cast", "com"):
        r = _cliente(apelido).post(ROTAS["multas"].format(id=show), json={"multas": [{"elenco_id": eid, "valor": 1}]})
        _garante(r.status_code == 403, f"45b {apelido} → {r.status_code}")
    _garante(len(_multas_do_evento(show)) == 1, "45b: a recusa gravou multa")
    r = _cliente("sa").post(ROTAS["multas"].format(id=show), json={"multas": [{"elenco_id": eid, "valor": 0}]})
    _garante(r.status_code == 400 and "multas" in (_erro(r).get("fields") or {}), f"45b nada a lançar → {r.status_code} {_erro(r)}")


def c45c_tirado_da_vaga() -> None:
    show = _evento_com_elenco("45c", ["A", "B"])
    r1 = _escalar(show, estado["t"])
    _escalar(show, estado["t2"])
    _cancelar_ok(show, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    _remocoes.clear()
    r = _cliente("cast").post(f"/api/roles/{r1}/assign", json={"talent_id": None, "cache_value": None})
    _garante(r.status_code == 200, f"45c tirar → {r.status_code} {_erro(r)}")
    _esperar_threads()
    _garante(not _remocoes, "45c: e-mail de remoção no cancelado")
    _garante(_no_banco("SELECT talent_id FROM event_roles WHERE id = :i", i=r1)[0][0] is None, "45c: a vaga não ficou sem talento")
    elenco = _resumo_api(show).get("elenco") or []
    _garante(len(elenco) == 2, f"45c: a lista do ato perdeu a linha: {elenco}")
    tirado = next(e for e in elenco if not e.get("na_vaga"))
    _garante(tirado.get("talent_id") == estado["t"], f"45c: a linha do tirado mudou: {tirado}")
    r = _cliente("sa").post(ROTAS["multas"].format(id=show), json={"multas": [{"elenco_id": tirado["elenco_id"], "valor": 100}]})
    _garante(r.status_code == 200, f"45c multa ao tirado → {r.status_code} {_erro(r)}")
    m = _multas_do_evento(show)
    _garante(len(m) == 1 and m[0][4] == _nome_do_talento(estado["t"]) and m[0][5] == PIX, f"45c: multa com nome e PIX do cadastro {m}")
    _garante((r.get_json() or {}).get("gastos") == [m[0][0]], f"45c: gastos da resposta {r.get_json()}")
    outro = _evento_com_elenco("45c outro", ["A"])
    _escalar(outro, estado["t2"])
    _cancelar_ok(outro, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    alheio = (_resumo_api(outro).get("elenco") or [{}])[0].get("elenco_id")
    for rotulo, eid in (("de outro evento", alheio), ("fora da lista", 999_999_999)):
        r = _cliente("sa").post(ROTAS["multas"].format(id=show), json={"multas": [{"elenco_id": eid, "valor": 10}]})
        _garante(r.status_code == 400 and f"multa_{eid}" in (_erro(r).get("fields") or {}), f"45c {rotulo} → {r.status_code} {_erro(r)}")
    _garante(len(_multas_do_evento(show)) == 1 and not _multas_do_evento(outro), "45c: a recusa gravou multa")
    vivo = _evento_com_elenco("45c vivo", ["A"])
    rv = _escalar(vivo, estado["t"])
    _remocoes.clear()
    _cliente("cast").post(f"/api/roles/{rv}/assign", json={"talent_id": None, "cache_value": None})
    _esperar_threads()
    _garante(len(_remocoes) == 1, f"45c: evento vivo sem o e-mail de remoção ({len(_remocoes)})")


def c16b_satelite() -> None:
    """16b, a parte do grupo (H5): dado de venda num satélite ou num dia cortado → o 409 do satélite."""
    g = _grupo("16b satélite", dias=2)
    _cancelar_ok(g["principal"], _corpo_cancelar("parte", 900, alcance="todos"))
    r = _patch_comercial(g["dias"][0], sale_value=500)
    _garante(
        r.status_code == 409 and _erro(r).get("leader_id") == g["principal"],
        f"16b satélite cancelado → {r.status_code} {_erro(r)}",
    )
    g2 = _grupo("16b dia cortado", dias=2)
    with _com_hoje(_dia(10)):
        rc = _corte(g2["dias"][1], 2000)
    _garante(rc.status_code == 200, f"16b corte → {rc.status_code} {_erro(rc)}")
    r = _patch_comercial(g2["dias"][1], sale_value=500)
    _garante(
        r.status_code == 409 and _erro(r).get("leader_id") == g2["principal"],
        f"16b dia cortado → {r.status_code} {_erro(r)}",
    )


def c42e_ensaios_na_passagem() -> None:
    """42e: na passagem, o ensaio do antigo 1º dia sai; o do dia que fica não muda (H6, aceite 8)."""
    g = _grupo_42("42e")
    velho = _ensaio(g["principal"], _data_isolada())
    fica = _ensaio(g["novo"], _data_isolada())
    _no_banco_escrever("UPDATE calendar_events SET needs_rehearsal = true WHERE id = :i", i=g["novo"])
    gid_velho = _no_banco("SELECT google_event_id FROM calendar_events WHERE id = :i", i=velho)[0][0]
    antes_fica = _no_banco(
        "SELECT parent_event_id, title, start_at, end_at, location, google_event_id FROM calendar_events WHERE id = :i",
        i=fica,
    )
    marco = google.marco()
    _cancelar_ok(
        g["principal"],
        {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": g["novo"], "venda_nova": 3000},
    )
    _garante(not _no_banco("SELECT 1 FROM calendar_events WHERE id = :i", i=velho), "42e: o ensaio do antigo 1º dia ficou no banco")
    _garante(gid_velho in google.deletes(marco), f"42e: o ensaio do antigo 1º dia não saiu do Google {google.deletes(marco)}")
    depois_fica = _no_banco(
        "SELECT parent_event_id, title, start_at, end_at, location, google_event_id FROM calendar_events WHERE id = :i",
        i=fica,
    )
    _garante(depois_fica == antes_fica, f"42e: o ensaio do dia que fica foi tocado: {antes_fica} → {depois_fica}")
    _garante(antes_fica[0][5] not in google.deletes(marco), "42e: o ensaio do dia que fica saiu do Google")
    _garante(
        _no_banco("SELECT needs_rehearsal FROM calendar_events WHERE id = :i", i=g["novo"])[0][0] is True,
        "42e: o 'precisa ensaio' do novo principal mudou",
    )
    _garante(
        estado["usuarios"]["ens"]["id"] in {r[0] for r in _avisos_do_ato("evento.cancelado", g["principal"])},
        "42e: sem o sino à equipe de Ensaio",
    )


# ── provas por mutação (T007/T008) ─────────────────────────────────────────────────────────────
# Cada uma liga a regra errada num gancho do núcleo e roda a parte do cenário que a protege: o
# cenário TEM de falhar. Os ganchos são atributos de módulo, chamados pelo módulo (nunca por
# `from … import`), para a troca alcançar a chamada:
#   comissoes_ops._beneficiarios_com_linha_viva(event_ids) -> set[int]   (16c: alvo 0 aos outros)
#   comissoes_ops._nota_do_ajuste(motivo, detalhe=None) -> str           (16c: prefixo do motivo)
#   comercial_ops.alterar_acrescimos_do_cancelado(event, itens, …)        (16d: no lugar)
#   comissoes_ops.comissao_cheia_do_evento(event, settings, *, taxa, …)   (16e: taxa congelada)
#   group_ops.passar_venda(antigo, novo, …)                               (42: move, não recria)
#   comissoes_ops._sync_commission_payment(event)                        (42c: data do novo dia)
#   cancel_ops._chave_do_sino(kind, evento_id, dia_id=None) -> str        (44: chave do ato)
#   cancel_ops._elenco_do_resumo(cancelamento) -> list[dict]              (45c: lista do ato)
#   casting_ops._manda_email_de_remocao(event) -> bool                    (45c: sem e-mail no cancelado)
#   comissoes_ops._reconciliar_ajuste_vivo(event, …)                      (38c: regra nova (b) do sync)
# `AttributeError` na troca = o núcleo ainda não tem o gancho: o cenário fica vermelho, como deve.
@contextlib.contextmanager
def _mutando(modulo, nome: str, fabrica: Callable) -> Iterator[None]:
    original = getattr(modulo, nome)
    setattr(modulo, nome, fabrica(original))
    try:
        yield
    finally:
        setattr(modulo, nome, original)


def _sob_mutacao(
    modulo, nome: str, fabrica: Callable, fn: Callable[[], None], rotulo: str, *, base_ja_rodou: bool = False
) -> None:
    """A prova por mutação: a sonda passa com a regra certa e quebra com a errada.

    Sem rodar a sonda limpa antes, qualquer falha (o núcleo ainda não existe, um 400 do caminho)
    contaria como "mutação acusada" — foi o que deixou o 42c verde na rodada vermelha de 16/10.
    """
    if not base_ja_rodou:
        fn()  # a sonda limpa tem de passar; senão a prova não prova nada

    def rodar() -> None:
        with _mutando(modulo, nome, fabrica):
            fn()

    _deve_quebrar(rodar, rotulo)


def _c16c_troca(rotulo: str) -> None:
    a = _exemplo_padrao(rotulo, comissao="pago")
    with _com_hoje(_dia(10)):
        _cancelar_ok(a["ev"], _corpo_cancelar("parte", 600))
        r = _patch_comercial(a["ev"], seller_id=estado["usuarios"]["vend2"]["id"])
    _garante(r.status_code == 200, f"16c troca → {r.status_code} {_erro(r)}")
    linhas = _linhas_comissao(a["ev"])
    da = [x for x in linhas if x["seller"] == estado["usuarios"]["vend"]["id"]]
    db_ = [x for x in linhas if x["seller"] == estado["usuarios"]["vend2"]["id"]]
    _igual(sum(Decimal(x["valor"]) for x in da), 0, "16c: A devolve o recebido")
    _igual(sum(Decimal(x["valor"]) for x in db_), 18, "16c: B recebe a comissão do retido")
    neg = [x for x in da if x["original_id"]]
    _garante(neg and (neg[0]["nota"] or "").startswith("Cancelamento: vendedor trocado — devolve o já recebido"), f"16c: motivo de A {neg}")
    _garante(db_ and (db_[0]["nota"] or "").startswith("Cancelamento: vendedor trocado — comissão do retido"), f"16c: motivo de B {db_}")


def c16c_mutacoes() -> None:
    from app.financeiro import comissoes_ops

    _sob_mutacao(
        comissoes_ops, "_beneficiarios_com_linha_viva", lambda _o: (lambda *a, **k: set()),
        lambda: _c16c_troca("16c mutação um só"), "um beneficiário só",
    )
    _sob_mutacao(
        comissoes_ops, "_nota_do_ajuste", lambda _o: (lambda motivo, detalhe=None, **k: detalhe or ""),
        lambda: _c16c_troca("16c mutação nota"), "nota sem prefixo",
    )


def _c16d_no_lugar(rotulo: str) -> None:
    ex = _exemplo_padrao(rotulo)
    _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    itens = _itens_atuais(ex["ev"])
    for i in itens:
        if i["id"] == ex["bv"]:
            i.update(value=300)
    r = _put_acrescimos(ex["ev"], itens)
    _garante(r.status_code == 200, f"16d PUT → {r.status_code} {_erro(r)}")
    linha = _no_banco("SELECT amount_brl FROM event_acrescimos WHERE id = :i", i=ex["bv"])
    _garante(linha, "16d: o BV foi apagado e recriado")
    _igual(linha[0][0], 300, "16d: o BV no lugar com o valor novo")


def c16d_mutacao() -> None:
    from app.calendar import comercial_ops
    from app.models import EventAcrescimo

    def recria(_original):
        def mutante(event, itens, *a, **k):
            for velho in EventAcrescimo.query.filter_by(event_id=event.id).all():
                db.session.delete(velho)
            db.session.flush()
            for i in itens or []:
                valor = Decimal(str(i.get("value") or 0))
                db.session.add(EventAcrescimo(
                    event_id=event.id, tipo=i.get("tipo") or "Outro", is_percent=bool(i.get("is_percent")),
                    value=valor, amount_brl=valor, is_bv=(i.get("tipo") == "BV"),
                    bv_recipient=i.get("bv_recipient"), bv_pix=i.get("bv_pix"),
                ))
            db.session.flush()
            return []

        return mutante

    _sob_mutacao(comercial_ops, "alterar_acrescimos_do_cancelado", recria, lambda: _c16d_no_lugar("16d mutação"), "apagar e recriar")


def _c16e_taxa(rotulo: str) -> None:
    _taxa_padrao(2.5)
    ex = _exemplo_padrao(rotulo, comissao="pago")
    _no_banco_escrever("UPDATE calendar_events SET commission_rate = NULL WHERE id = :i", i=ex["ev"])
    with _com_hoje(_dia(10)):
        _cancelar_ok(ex["ev"], _corpo_cancelar("parte", 600))
    _taxa_padrao(3.0)
    with _com_hoje(_dia(10)):
        _patch_comercial(ex["ev"], sale_value=2200, sale_value_gross=2200)
    _igual(_cancelamento(ex["ev"])["taxa"], 2.5, "16e: a padrão alcançou o cancelado")
    # (2.200 − BV 200) × 2,5% = 50; com a taxa de hoje (3%), 60
    _igual(_cancelamento(ex["ev"])["cheia"], 50, "16e: a cheia recongelada com a taxa de hoje")


def c16e_mutacao() -> None:
    from app.financeiro import comissoes_ops

    def sem_taxa(original):
        def mutante(event, settings, **k):
            k.pop("taxa", None)
            return original(event, settings, **k)

        return mutante

    _sob_mutacao(comissoes_ops, "comissao_cheia_do_evento", sem_taxa, lambda: _c16e_taxa("16e mutação"), "taxa de hoje")


def _c42_move(rotulo: str) -> None:
    g = _grupo_42(rotulo, bv_pago=True)
    antes = _retrato_passagem([g["principal"], g["novo"]])
    _cancelar_ok(
        g["principal"],
        {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": g["novo"], "venda_nova": 3000},
    )
    depois = _retrato_passagem([g["principal"], g["novo"]])
    for tabela, linhas in antes.items():
        _garante(sorted(x[:-1] for x in linhas) == sorted(x[:-1] for x in depois[tabela]), f"42: {tabela} mudou além do vínculo")


def c42_mutacao() -> None:
    from app.calendar import group_ops
    from app.models import EventAcrescimo, EventPayment

    def recria(original):
        def mutante(antigo, novo, *a, **k):
            out = original(antigo, novo, *a, **k)
            nid = getattr(novo, "id", novo)
            for p in EventPayment.query.filter_by(event_id=nid).all():
                db.session.add(EventPayment(event_id=nid, file_path=p.file_path, amount=p.amount, created_at=p.created_at))
                db.session.delete(p)
            # o acréscimo recriado perde o id e o estado do BV pago
            for a in EventAcrescimo.query.filter_by(event_id=nid).all():
                db.session.add(EventAcrescimo(event_id=nid, tipo=a.tipo, is_percent=a.is_percent, value=a.value,
                                              amount_brl=a.amount_brl, is_bv=a.is_bv, bv_recipient=a.bv_recipient, bv_pix=a.bv_pix))
                db.session.delete(a)
            db.session.flush()
            return out

        return mutante

    _sob_mutacao(group_ops, "passar_venda", recria, lambda: _c42_move("42 mutação"), "apagar e recriar")


def _c42c_data(rotulo: str) -> None:
    _configurar_educamanto()
    novembro_menos_um = datetime(2047, 10, 31, 19)
    g = _grupo(rotulo, dias=1, inicio=novembro_menos_um, passo=timedelta(days=1), comissao=None, pagos=(1000,))
    _no_banco_escrever("UPDATE calendar_events SET title = :t WHERE id = :i", t=f"(EDU) V306 {rotulo.upper()}", i=g["principal"])
    _no_banco_escrever("UPDATE calendar_events SET title = :t WHERE id = :i", t=f"(EDU) V306 {rotulo.upper()} DIA 2", i=g["dias"][0])
    _linha_comissao(g["principal"], 50, vendedor="vend2", liberacao=novembro_menos_um.date())
    _cancelar_ok(g["principal"], {**_corpo_cancelar("nada", None, nome=None, pix=None), "alcance": "so_este_dia", "novo_principal_id": g["dias"][0], "venda_nova": 3000})
    _comissoes(_mes(_hoje_sp()))
    edu = [x for x in _linhas_comissao(g["dias"][0]) if x["seller"] == estado["usuarios"]["vend2"]["id"]]
    _garante(edu and edu[0]["liberacao"] == date(2047, 11, 1), f"42c: EducaManto não foi a 01/11: {edu}")


def c42c_mutacao() -> None:
    from app.financeiro import comissoes_ops
    from app.models import CommissionPayment

    def guarda_a_data(original):
        def mutante(event):
            antes = {
                cp.id: cp.payable_from
                for cp in CommissionPayment.query.filter_by(event_id=event.id, status="a_pagar").all()
            }
            original(event)
            for cp in CommissionPayment.query.filter(CommissionPayment.id.in_(list(antes) or [0])).all():
                cp.payable_from = antes[cp.id]

        return mutante

    _sob_mutacao(comissoes_ops, "_sync_commission_payment", guarda_a_data, lambda: _c42c_data("42c mutação"), "data antiga")


def _c44_dois_atos(rotulo: str, *, chave_do_principal: bool = False) -> None:
    """Corte de um dia com ensaio e, depois, "Cancelar todos os dias" com ensaio: 2 sinos por pessoa."""
    from app.calendar import cancel_ops

    g = _grupo(rotulo, dias=2, comissao=None, pagos=())
    dia = g["dias"][1]
    _ensaio(dia, _data_isolada())
    _ensaio(g["principal"], _data_isolada())

    def atos() -> None:
        r = _corte(dia, 2500, modo="nada", valor=None)
        _garante(r.status_code == 200, f"44 corte → {r.status_code} {_erro(r)}")
        _cancelar_ok(g["principal"], {"motivo": "verify 306", "devolucao": {"modo": "nada"}, "alcance": "todos"})

    if chave_do_principal:
        with _mutando(cancel_ops, "_chave_do_sino", lambda o: (lambda kind, evento_id, dia_id=None: o(kind, g["principal"], dia_id))):
            atos()
    else:
        atos()
    ens = estado["usuarios"]["ens"]["id"]
    _garante(ens in {r[0] for r in _avisos_do_ato("evento.cancelado", dia)}, "44 dois atos: sem o sino do corte")
    _garante(ens in {r[0] for r in _avisos_do_ato("evento.cancelado", g["principal"])}, "44 dois atos: o 2º sino foi engolido")


def c44_dois_sinos() -> None:
    _c44_dois_atos("44 dois atos")
    _deve_quebrar(lambda: _c44_dois_atos("44 mutação", chave_do_principal=True), "dedupe_key do principal")


def _c45c_tirar(rotulo: str) -> None:
    show = _evento_com_elenco(rotulo, ["A", "B"])
    r1 = _escalar(show, estado["t"])
    _escalar(show, estado["t2"])
    _cancelar_ok(show, {"motivo": "verify 306", "devolucao": {"modo": "nada"}})
    _remocoes.clear()
    r = _cliente("cast").post(f"/api/roles/{r1}/assign", json={"talent_id": None, "cache_value": None})
    _garante(r.status_code == 200, f"45c tirar → {r.status_code} {_erro(r)}")
    _esperar_threads()
    _garante(not _remocoes, "45c: e-mail de remoção no cancelado")
    _garante(len(_resumo_api(show).get("elenco") or []) == 2, "45c: a lista do ato perdeu a linha")


def c45c_mutacoes() -> None:
    from app.calendar import cancel_ops, casting_ops

    _sob_mutacao(
        cancel_ops, "_elenco_do_resumo",
        lambda o: (lambda cancelamento, *a, **k: [x for x in o(cancelamento, *a, **k) if x.get("na_vaga")]),
        lambda: _c45c_tirar("45c mutação lista"), "lista lida da escala de hoje",
    )
    _sob_mutacao(
        casting_ops, "_manda_email_de_remocao", lambda _o: (lambda *a, **k: True),
        lambda: _c45c_tirar("45c mutação e-mail"), "remoção sem a condição",
    )


# ── registro dos cenários, regressão e main ────────────────────────────────────────────────────
CENARIOS: list[tuple[str, str, str, Callable[[], None]]] = [
    ("B0", "1", "chão e a casca da comissão (main × branch)", c1_chao_e_casca),
    ("B0", "16b", "cheia 0 no núcleo (cortesia e sem vendedor)", c16b_cheia_zero_nucleo),
    ("B0", "41", "regressão das comissões dos grupos e das cobranças (main × branch)", c41_regressao_grupos_e_cobrancas),
    ("B0", "23", "retrato main × branch dos meses sem cancelamento", c23_retrato_main_branch),
    ("B1", "7", "a pagar ajustada no lugar", c7_a_pagar_no_lugar),
    ("B1", "8", "paga: −80 no primeiro repasse aberto (dias 2 e 10)", c8_paga_no_primeiro_repasse_aberto),
    ("B1", "8", "variante prévia = execução", c8_variante_previa_igual_execucao),
    ("B1", "9", "no banco como paga + desfazer", c9_no_banco_e_desfazer),
    ("B1", "10", "Tudo, linha que nasce, vendedor sem comissão", c10_tudo_e_sem_linha),
    ("B1", "11", "EducaManto", c11_educamanto),
    ("B1", "12", "reabrir Comissões e Planilha", c12_reabrir_telas),
    ("B1", "13", "Planilha × Comissões", c13_planilha_igual_comissoes),
    ("B1", "14", "soma zero e órfão", c14_soma_zero_e_orfao),
    ("B1", "14b", "exclusão no primeiro repasse aberto", c14b_exclusao_no_primeiro_repasse),
    ("B1", "17", "BV na Planilha", c17_bv_na_planilha),
    ("B1", "30", "corrida com a Planilha e sync velho", c30_corrida_com_a_planilha),
    ("B2", "2", "Parte de 600", c2_parte_600),
    ("B2", "2", "variante prévia = execução", c2_variante_previa),
    ("B2", "2b", "marcado pela 303", c2b_marcado),
    ("B2", "3", "Tudo, Nada e divergente", c3_tudo_nada_divergente),
    ("B2", "4", "recusas de forma", c4_recusas_de_forma),
    ("B2", "5", "pendente, já cancelado, clique duplo", c5_pendente_ja_cancelado_duplo),
    ("B2", "6", "papéis", c6_papeis),
    ("B2", "15", "Alterar devolução", c15_alterar_devolucao),
    ("B2", "16", "comprovante no cancelado", c16_comprovante_no_cancelado),
    ("B2", "16", "variante paid_amount e valor esperado", c16_variante_paid_amount),
    ("B2", "16", "variante 16-vivo", c16_vivo),
    ("B2", "18", "Gastos Extras (+ 18-inverso)", c18_gastos_extras),
    ("B2", "19", "orçamento, excluir e acréscimos no cancelado", c19_orcamento_excluir_acrescimos),
    ("B2", "25", "payload do cancelado e flags do vivo", c25_payload),
    ("B2", "28", "RBAC", c28_rbac),
    ("B2", "28", "união TS dos códigos", c_codigos_uniao_ts),
    ("B2", "31", "Google: falha, trava e Sincronizar", c31_google),
    ("B2", "32", "pago maior que a venda e comprovante sem valor", c32_pago_maior_e_sem_valor),
    ("B2", "34", "excluir usuário congelado", c34_excluir_usuario),
    ("B2", "36", "devolução na Planilha", c36_devolucao_na_planilha),
    ("B3", "20", "DRE do mês do cancelamento", c20_dre_do_mes_do_cancelamento),
    ("B3", "21", "mês do evento, Tendência e variantes", c21_mes_do_evento_tendencia_e_variantes),
    ("B3", "22", "painéis", c22_paineis),
    ("B3", "23", "mutação do retrato", c23_mutacao),
    ("B3", "32", "DRE com o retido inteiro (pago maior que a venda)", c32_dre_retido_inteiro),
    ("B3", "24", "relatórios comerciais", c24_comercial),
    ("B4", "16b", "dados de venda do cancelado", c16b_dados_de_venda),
    ("B4", "16c", "troca de vendedor", c16c_troca_de_vendedor),
    ("B4", "16c", "mutações: um beneficiário só, nota sem prefixo", c16c_mutacoes),
    ("B4", "16c", "variante 16c-corrida", c16c_corrida),
    ("B4", "16d", "acréscimos no lugar", c16d_acrescimos),
    ("B4", "16d", "mutação apagar e recriar", c16d_mutacao),
    ("B4", "16e", "taxa congelada", c16e_taxa_congelada),
    ("B4", "16e", "mutação taxa de hoje", c16e_mutacao),
    ("B5", "5", "variante 5-grupo", c5_grupo_pendente),
    ("B5", "4", "recusas do corte e piso", c4_corte_recusas),
    ("B5", "29", "agrupar e desagrupar cancelado", c29_agrupar_cancelado),
    ("B5", "35", "marcado no grupo", c35_marcado_no_grupo),
    ("B5", "37", "Cancelar todos os dias (+ 37-devolução)", c37_cancelar_todos),
    ("B5", "37b", "comprovante num satélite do grupo cancelado", c37b_comprovante_no_satelite),
    ("B5", "38", "só este dia (+ comprovante e P-52)", c38_so_este_dia),
    ("B5", "38c", "desfazer no principal vivo", c38c_desfazer_no_principal_vivo),
    ("B5", "39", "depois do 38", c39_depois_do_38),
    ("B5", "41", "custo do grupo com dia cancelado", c41_custo_do_grupo),
    ("B5", "16b", "satélite e dia cortado → 409 do satélite", c16b_satelite),
    ("B5", "17", "BV do satélite cancelado na Planilha", c17_satelite),
    ("B5", "21", "satélite cancelado sem retido na DRE", c21_satelite),
    ("B5", "42", "passagem da venda", c42_passagem),
    ("B5", "42", "mutação apagar e recriar", c42_mutacao),
    ("B5", "42b", "passagem com corte", c42b_passagem_com_corte),
    ("B5", "42c", "novo 1º dia noutro mês", c42c_outro_mes),
    ("B5", "42c", "mutação data antiga", c42c_mutacao),
    ("B5", "42d", "recusas da passagem", c42d_recusas_da_passagem),
    ("B6", "33", "cachê pago", c33_cache_pago),
    ("B6", "40", "soltar, agrupar, cachê pago no grupo e ENSAIO", c40_soltar_e_cache_pago),
    ("B6", "43", "ensaios", c43_ensaios),
    ("B6", "2b", "marcado: elenco e equipe de Ensaio avisados", c2b_avisos),
    ("B6", "4", "multas recusadas no cancelar", c4_multas_recusadas),
    ("B6", "42", "passagem: elenco avisado e ensaio apagado", c42_aviso_e_ensaio),
    ("B6", "42b", "passagem: multa por escalação do antigo 1º dia", c42b_multa_do_antigo),
    ("B6", "42d", "passagem: cachê pago no antigo 1º dia", c42d_cache_pago),
    ("B6", "42e", "ensaios na passagem da venda", c42e_ensaios_na_passagem),
    ("B6", "44", "avisos", c44_avisos),
    ("B6", "44", "dois atos, dois sinos (+ mutação da chave do principal)", c44_dois_sinos),
    ("B6", "45", "multa no ato", c45_multa_no_ato),
    ("B6", "45b", "multa depois do ato", c45b_multa_depois),
    ("B6", "45c", "multa a quem saiu da escala", c45c_tirado_da_vaga),
    ("B6", "45c", "mutações: lista da escala de hoje, remoção sem a condição", c45c_mutacoes),
]
# O 26 roda por último (antes da limpeza): "antes e depois do verify inteiro".
FINAIS = [("B0", "26", "passado quieto e contagem só leitura", c26_passado_quieto)]
NUCLEO = {"B0", "B1"}  # Fundação e História 1 (o 26 final é B0); quickstart §1, modo núcleo

VERIFIES_ANTIGOS = [
    "303-sync-nao-apaga-venda/verify_303.py",
    "267-integridade-comissao/verify_267.py",
    "267b-hotfix-data-da-venda/verify_267b.py",
    "267c-hotfix-trava-do-lote/verify_267c.py",
    "299-sem-valor-cobrancas/verify_299.py",
    "215b-hotfix-taxa-e-vendedor/verify_215b.py",
    "305-bv-do-orcamento-no-evento/verify_305.py",
    "205-loja-interacoes-virtuais/verify_205.py",
    "266-costuras-funil/verify_266.py",
    "258-cliente-manual/verify_258.py",
    "256-auditor-marketing/verify_256.py",
    "273-orcamento-para-evento/verify_273.py",
    "301-orcamentos-visiveis-comercial/verify_301.py",
    "272-notificacoes-internas/verify_272.py",
    "238-teto-autorizado/verify_238.py",
    "271-hotfix-corrida-lancamentos/verify_271.py",
    "307-natal-papai-noel-calculadora/verify_307.py",
]
BASE_REGRESSAO = AQUI / "verify_306_regressao_base.json"


def _placar(saida: str) -> str:
    m = re.findall(r"(\d+)\s*/\s*(\d+)\s*(?:OK|cenários|ok)", saida)
    return f"{m[-1][0]}/{m[-1][1]}" if m else "?"


def _limpar_laboratorio_do_238() -> None:
    """O `verify_238` cria o evento `fake-verify-238` e nunca o apaga: na segunda rodada ele
    quebra no UNIQUE do `google_event_id`. Apagar o laboratório dele antes de cada rodada mantém a
    regressão idempotente sem tocar no verify antigo."""
    with app.app_context():
        for ev in CalendarEvent.query.filter_by(google_event_id="fake-verify-238").all():
            cal_routes._clear_event_side_tables(ev.id)
            db.session.delete(ev)
        db.session.commit()


def regressao() -> bool:
    """Os verifies antigos em subprocesso, antes de semear qualquer coisa (quickstart §5)."""
    print("\n── regressão: verifies antigos ──")
    atual: dict = {}
    for rel in VERIFIES_ANTIGOS:
        caminho = REPO_ROOT / "specs" / rel
        if not caminho.exists():
            atual[rel] = {"codigo": None, "placar": "ausente"}
            continue
        if "verify_238" in rel:
            _limpar_laboratorio_do_238()
        env = {**os.environ, "PYTHONUTF8": "1"}
        tok = Path(r"C:\Users\schim\Desktop\Manto_Platform\.marketing-agent-token")
        if "256" in rel and tok.exists():
            env["MARKETING_AGENT_TOKEN"] = tok.read_text(encoding="utf-8").strip()
        r = subprocess.run(
            [sys.executable, str(caminho)], capture_output=True, text=True, encoding="utf-8",
            env=env, cwd=str(REPO_ROOT), timeout=3600,
        )
        atual[rel] = {"codigo": r.returncode, "placar": _placar(r.stdout)}
        print(f"  {rel}: saída {r.returncode}, placar {atual[rel]['placar']}")
    if not BASE_REGRESSAO.exists():
        BASE_REGRESSAO.write_text(json.dumps(atual, indent=1, ensure_ascii=False), encoding="utf-8")
        print("  (base gravada nesta rodada)")
        return True
    base = json.loads(BASE_REGRESSAO.read_text(encoding="utf-8"))
    pior = []
    for rel, v in atual.items():
        b = base.get(rel) or {}
        if b.get("codigo") == 0 and v["codigo"] != 0:
            pior.append(rel)
        elif re.fullmatch(r"\d+/\d+", v["placar"] or "") and re.fullmatch(r"\d+/\d+", b.get("placar") or ""):
            ok_a, tot_a = (int(x) for x in v["placar"].split("/"))
            ok_b, _tot_b = (int(x) for x in b["placar"].split("/"))
            if ok_a < ok_b:
                pior.append(rel)
    if pior:
        print(f"  PIOR que a base: {pior}")
    return not pior


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--so", default=None)
    parser.add_argument("--nucleo", action="store_true")
    parser.add_argument("--regressao", action="store_true")
    parser.add_argument("--semear-tela", action="store_true")
    parser.add_argument("--limpar-tela", action="store_true")
    args = parser.parse_args()
    if args.so:
        OPCOES["so"] = {s.strip() for s in args.so.split(",") if s.strip()}
    OPCOES["nucleo"] = args.nucleo
    guarda_de_ambiente()
    if args.limpar_tela:
        limpar()
        print("dados da conferência de tela apagados")
        return 0
    regressao_ok = True
    if args.regressao:
        regressao_ok = regressao()
    print("\n── verify 306 ──")
    try:
        preparar()
        if args.semear_tela:
            return semear_tela()
        for bloco, num, nome, fn in CENARIOS + FINAIS:
            # Pelo bloco, não pelo número: o 16b, o 41 e o 23 têm partes fora do núcleo (B3–B5).
            if OPCOES["nucleo"] and bloco not in NUCLEO:
                continue
            cenario(bloco, num, nome, fn)
    finally:
        if not args.semear_tela:
            try:
                limpar()
                sobras = _sobras_do_verify()
                _garante(not sobras, f"a limpeza deixou: {sobras}")
                _garante(not rede_bloqueada, f"conexões externas tentadas: {rede_bloqueada}")
                resultados.append(("B9", "27 · limpeza e nenhuma rede", "OK", ""))
                print("  OK         27 · limpeza e nenhuma rede")
            except Exception as exc:  # noqa: BLE001
                resultados.append(("B9", "27 · limpeza e nenhuma rede", "FALHA", str(exc)))
                print(f"  FALHA      27 · limpeza: {exc}")
    total = len(resultados)
    oks = sum(1 for r in resultados if r[2] == "OK")
    # O placar é por cenário (quickstart §1): as variantes rodam como linhas próprias, mas um número
    # só fica verde quando todas as linhas dele ficam.
    por_numero: dict[str, bool] = {}
    for _bloco, rotulo, status, _msg in resultados:
        numero = rotulo.split(" · ")[0]
        por_numero[numero] = por_numero.get(numero, True) and status == "OK"
    cenarios_ok = sum(1 for v in por_numero.values() if v)
    print(
        f"\n{cenarios_ok}/{len(por_numero)} cenários OK ({oks}/{total} linhas)"
        + ("" if regressao_ok else " — regressão PIOR que a base")
    )
    for bloco in sorted({r[0] for r in resultados}):
        linhas = [r for r in resultados if r[0] == bloco]
        print(f"  {bloco}: {sum(1 for r in linhas if r[2] == 'OK')}/{len(linhas)}")
    return 0 if oks == total and regressao_ok else 1


def semear_tela() -> int:
    """Dados da conferência de tela (quickstart §8): eventos que sobrevivem ao verify."""
    ex = _exemplo_padrao("tela exemplo", nota=True, comissao="pago")
    g = _grupo("tela grupo", dias=2)
    show = _evento_com_elenco("tela show", ["A", "B"])
    _escalar(show, estado["t"])
    _escalar(show, estado["t2"])
    print(json.dumps({
        "usuarios": {k: v["email"] for k, v in estado["usuarios"].items()},
        "senha": "(a do verify, no código)",
        "eventos": {"exemplo": ex["ev"], "grupo_principal": g["principal"], "grupo_dias": g["dias"], "show": show},
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
