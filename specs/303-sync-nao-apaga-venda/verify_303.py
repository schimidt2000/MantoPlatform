"""Verificação da feature 303 — o sync não apaga evento com venda.

Cenários (a tabela da seção "Verificação" da spec), por bloco (`--ate Bn` roda até o bloco n; o B9
roda sempre):

  B0  0     Chão: travas de e-mail e de escrita no Google, dublê instalado, guarda de ambiente,
            disjuntor de rede.
      18    A trava de escrita de evento por ambiente (processo filho).
  B1  1     Evento com venda some do Google (nos quatro modos de apagado): fica, marcado, intacto;
            payloads da agenda e do detalhe.
      1b    Evento passado com venda; "Limpar eventos fantasma"; COMERCIAL recusado (deve falhar).
      2     Um aviso por destinatário, nenhum a mais em ciclos seguintes; FIGURINO sem aviso.
      2b    Corrida: outra conexão marca no meio da consulta — uma marca, um aviso.
      3,4   Sem venda, com comprovante (inclusive de valor nulo) / com contrato: ficam e são marcados.
      5,6   Sem venda, com escalado / satélite e líder de grupo: ficam e são marcados.
      7     Vazio (quatro modos) e SHOW só com o técnico automático: apagados; auditoria com a resposta
            do Google e o retrato vazio.
      7a    SHOW com a vaga de Presença designada / com outro técnico no lugar do padrão: ficam.
      7b    Evento vazio com ensaio que tem histórico: apagado sem erro, pelo sync e pelo DELETE.
      13    Consulta inconclusiva (5xx, tempo esgotado, credencial ausente, RefreshError; 403 e 429;
            dois meses seguidos; a lista inteira falha); a frase "Sumiços:" do ciclo.
      13b   O aviso falha uma vez durante a marca: aquele evento fica sem marca e conta como falha.
      13c   Erro de banco no meio da sincronização de um mês: o mês seguinte sincroniza e limpa.
      14    Edição de evento marcado não escreve no Google; "Sincronizar" de evento ausente responde
            409 e não altera nada (resposta completa e mínima).
      15    Evento cancelado e venda virtual ausentes: como hoje, sem marca e sem consulta.
  B2  8     Mudou de data (mês posterior, mês passado, além do horizonte) e presente sem mudança.
      9     A marca sai quando o evento volta (lista do mês, próprio id, outro mês, "Sincronizar");
            some de novo → aviso novo.
      13d   A consulta falha na reconferência dos marcados: o ciclo segue.
  B3  17    A faixa: quem vê, quem não vê (deve falhar), "Ver como", cancelado, resolvido, limite.
  B4  10*   Devolver ao Google (10a: trava ligada, deve falhar; 10b dia inteiro; 10c já tinha
            voltado; 10d/10e falhas do Google; 10f segundo clique; 10g sync seguinte; 10h ensaio;
            10i recusas).
      11    COMERCIAL não devolve (deve falhar); o Superadmin passa o gate.
      12    Cancelar e excluir evento marcado: recusados, pela API e pela rota antiga.
  B5  24    Portal: "em confirmação" nas três listas; quem não está escalado não vê (deve falhar).
      24b   Evento cancelado sai da avaliação; a nota é recusada (deve falhar).
  B9  41    Limpeza; nenhuma chamada de rede escapou do dublê.

O GOOGLE AQUI É UM DUBLÊ QUE FALHA FECHADO. O `manto_local` traz o token REAL da agenda da empresa:
nenhum cenário pode ler nem escrever na agenda de verdade. O dublê entra em `service.build` e
`service.load_credentials` — os dois nomes que toda função do service resolve na hora da chamada —
porque `routes.py` importa as funções do service pelo nome e trocar função por função deixaria
binding esquecido. Mês não liberado e id desconhecido respondem erro 503: um dublê que devolvesse
lista vazia para um mês real faria a limpeza apagar (ou marcar) os eventos do espelho. Um disjuntor
de rede recusa qualquer conexão que não seja local, e o último cenário afirma que nada escapou.

OS EVENTOS DE TESTE VIVEM EM MESES ISOLADOS (2031 em diante, e um mês passado calculado antes do
evento mais antigo do espelho) e nascem pelo caminho real (`sync_events`): Coordenador, personagens
do título e, em SHOW, as vagas de som nascem do sistema. O talento descartável entra em vaga que o
sistema criou — nunca `EventRole` com `character_name` inventado em evento real.

A coluna nova é lida por SQL cru e as rotas ficam num dicionário: o verify não importa, no topo,
nada que a 303 cria (a única exceção é o import tardio de `faixa_sumidos` dentro do cenário 17, que
vira BLOQUEADO em `ImportError`). Três estados por cenário: OK, FALHA, BLOQUEADO (depende de evento
marcado, que só existe depois da História 1).

ESCRITA SE CONFERE POR CONEXÃO SEPARADA (`_no_banco`): o autoflush da sessão do app mostra o que
ainda não foi commitado (hotfix 257). REQUISIÇÕES HTTP FICAM FORA DE `app.app_context()`.

O BACKEND LOCAL TEM DE ESTAR PARADO: a thread de sync falaria com o Google real sobre os eventos de
teste. Se `calendar_auto_sync_at` for recente, o verify sai com código 2.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"; $env:PYTHONUTF8 = "1"
    .venv\\Scripts\\python.exe specs\\303-sync-nao-apaga-venda\\verify_303.py            # o portão: tudo
    .venv\\Scripts\\python.exe specs\\303-sync-nao-apaga-venda\\verify_303.py --ate B1   # por história

Conferência de tela (quickstart §4) — semear eventos marcados que sobrevivem ao verify, conferir com
o backend local ligado, e apagar com o backend parado::

    .venv\\Scripts\\python.exe specs\\303-sync-nao-apaga-venda\\verify_303.py --semear-tela
    .venv\\Scripts\\python.exe specs\\303-sync-nao-apaga-venda\\verify_303.py --limpar-tela

O portão é a execução SEM argumentos, terminando em `N/N OK`.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import socket
import subprocess
import sys
import threading
import traceback
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")  # cinto, além do suspensório do localhost
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

import httplib2  # noqa: E402
from google.auth.exceptions import RefreshError  # noqa: E402
from googleapiclient.errors import HttpError  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter, maps  # noqa: E402
from app import email_service as es  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.formularios import formularios_ops  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    EventContract,
    EventLog,
    EventPayment,
    EventRole,
    Role,
    Talent,
    User,
)
from app.notificacoes import notificacoes_ops  # noqa: E402

# ── nomes fixados no contrato (o verify depende deles) ─────────────────────────────────────────
PREFIX = "__v303_"
GID = "v303"  # todo google_event_id de teste começa assim (inclusive os criados pela devolução)
SENHA = "verify-303-senha"
MARCADOR = "[TESTE verify 303] pode apagar"
COLUNA = "google_missing_since"
TRAVA = "CALENDAR_SUPPRESS_EVENT_WRITES"
KIND = "evento.sumiu_google"
ROTAS = {
    "faixa": "/api/events/sumidos-google",
    "devolver": "/api/events/{id}/devolver-ao-google",
    "sync": "/api/events/{id}/sync",
    "detalhe": "/api/events/{id}",
    "basico": "/api/events/{id}/basico",
    "roles": "/api/events/{id}/roles",
    "cancelar": "/api/events/{id}/cancelar",
    "excluir": "/api/events/{id}",
    "excluir_jinja": "/events/{id}/delete",
    "solicitar": "/api/events/{id}/solicitar-exclusao",
    "agenda": "/api/agenda?ym={ym}",
    "dia": "/api/agenda/day/{dia}",
    "busca": "/api/agenda/search?q={q}",
    "admin_sync": "/api/admin/sync/run",
    "impersonate": "/api/auth/impersonate",
    "portal_agenda": "/api/portal/agenda",
    "portal_historico": "/api/portal/historico",
    "portal_aceitar": "/api/portal/invites/{role_id}/accept",
    "portal_pendentes": "/api/portal/ratings/pending",
    "portal_avaliar": "/api/portal/events/{id}/rate",
}
MSG_SYNC_AUSENTE = "Este evento não está mais no Google Agenda. Nada foi alterado."
MSG_RECUSOU_CRIACAO = (
    "O Google Agenda não confirmou a criação. A marca continua. Antes de tentar de novo, confira na "
    "Agenda se o evento apareceu — se apareceu, apague-o lá e devolva de novo."
)
MSG_MARCADO = (
    "Este evento sumiu do Google Agenda. O cancelamento com devolução do dinheiro chega na próxima "
    "entrega — por enquanto, devolva-o ao Google Agenda."
)
MSG_AVALIACAO_CANCELADO = "Este evento foi cancelado e não recebe avaliação."
MSG_FALHA_SYNC_EDICAO = "Não foi possível sincronizar a mudança com o Google Agenda."
FRASE_ELENCO = "O elenco deste evento passa a ser mantido pelo sistema"
MODOS_APAGADO = ("cancelado_completo", "cancelado_minimo", "404", "410")

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False  # muitos logins: o "10 per minute" estoura

_externo = create_engine(os.environ["DATABASE_URL"], future=True)
INICIO_UTC = datetime.utcnow()

resultados: list[tuple[str, str, str, str]] = []  # (bloco, nome, estado, detalhe)
estado: dict = {"eventos": {}, "apagados": set(), "talentos": [], "usuarios": []}


class Bloqueado(Exception):
    """O cenário depende de algo que ainda não existe (evento marcado, antes da História 1)."""


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
        raise OSError(f"verify_303: conexão externa bloqueada ({_host(endereco)})")
    return _connect_real(self, endereco)


def _connect_ex_vigiado(self, endereco):
    if self.family in (socket.AF_INET, socket.AF_INET6) and _host(endereco) not in _LOCAIS:
        rede_bloqueada.append(_host(endereco))
        return 111  # ECONNREFUSED
    return _connect_ex_real(self, endereco)


socket.socket.connect = _connect_vigiado
socket.socket.connect_ex = _connect_ex_vigiado


# ── o dublê do Google ──────────────────────────────────────────────────────────────────────────
def _http(status: int) -> HttpError:
    return HttpError(
        httplib2.Response({"status": str(status)}), b'{"error": {"message": "duble 303"}}'
    )


class _CredFalsa:
    """Credencial que só o dublê aceita."""

    valid = True
    expired = False
    token = "verify-303"


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

    def delete(self, calendarId=None, eventId=None, **_kw):  # noqa: N803
        return _Pedido(lambda: self.g._delete(eventId))


class _Servico:
    def __init__(self, g: GoogleFalso):
        self.g = g

    def events(self):
        return _Eventos(self.g)


class GoogleFalso:
    """Agenda falsa que falha fechado. Só responde a mês liberado e a id que ela conhece."""

    def __init__(self) -> None:
        self.itens: dict[str, dict] = {}
        self.apagado: dict[str, str | None] = {}
        self.fora_da_lista: set[str] = set()
        self.liberados: set[str] = set()
        self.lista_falha: set[str] = set()
        self.chamadas: list[tuple[str, str | None]] = []
        self.armadas: list[tuple[str, str]] = []  # (mês, tipo): arma ao responder a lista do mês
        self.proxima: str | None = None  # falha do próximo `get`
        self.credencial: str | None = None  # 'ausente' | 'refresh' na próxima carga de credencial
        self.por_id: dict[str, str] = {}  # falha de UM get daquele id
        self.ganchos: dict[str, Callable[[], None]] = {}
        self.falha_insert = False
        self.consumidas: list[tuple[str, str | None, str]] = []
        self.inseridos: list[tuple[str, dict]] = []
        self.patches: list[tuple[str, dict]] = []

    # instalados no service
    def build(self, *_a, **_k) -> _Servico:
        return _Servico(self)

    def load_credentials(self):
        self.chamadas.append(("credencial", None))
        if self.credencial:
            tipo, self.credencial = self.credencial, None
            self.consumidas.append(("credencial", None, tipo))
            if tipo == "ausente":
                return None
            raise RefreshError("token revogado (dublê 303)")
        return _CredFalsa()

    # manipulação pelos cenários
    def registrar(self, item: dict) -> None:
        self.itens[item["id"]] = item
        self.apagado[item["id"]] = None

    def apagar(self, gid: str, modo: str = "cancelado_completo") -> None:
        self.apagado[gid] = modo

    def restaurar(self, gid: str) -> None:
        self.apagado[gid] = None
        self.fora_da_lista.discard(gid)

    def remover(self, gid: str) -> None:
        self.itens.pop(gid, None)
        self.apagado.pop(gid, None)

    def mover(self, gid: str, inicio: datetime, fim: datetime) -> None:
        item = self.itens[gid]
        item["start"] = {"dateTime": _iso_sp(inicio)}
        item["end"] = {"dateTime": _iso_sp(fim)}

    def liberar(self, mes: str) -> None:
        self.liberados.add(mes)

    def armar(self, tipo: str, apos_lista_de: str | None = None) -> None:
        if apos_lista_de:
            self.armadas.append((apos_lista_de, tipo))
        else:
            self._pronta(tipo)

    def _pronta(self, tipo: str) -> None:
        if tipo in ("ausente", "refresh"):
            self.credencial = tipo
        else:
            self.proxima = tipo

    def desarmar(self) -> None:
        """Esquece toda falha armada — chamado ao fim de cada cenário."""
        self.armadas.clear()
        self.proxima = None
        self.credencial = None
        self.por_id.clear()
        self.ganchos.clear()
        self.falha_insert = False
        self.lista_falha.clear()

    def contar(self, verbo: str, ids: set[str] | None = None, desde: int = 0) -> int:
        return sum(
            1 for v, alvo in self.chamadas[desde:] if v == verbo and (ids is None or alvo in ids)
        )

    def marco(self) -> int:
        return len(self.chamadas)

    # a API
    def _list(self, kw: dict) -> dict:
        inicio = datetime.fromisoformat(kw["timeMin"])
        mes = f"{inicio.year:04d}-{inicio.month:02d}"
        self.chamadas.append(("list", mes))
        if mes not in self.liberados or mes in self.lista_falha:
            raise _http(503)
        itens = [
            copy.deepcopy(it)
            for gid, it in self.itens.items()
            if self.apagado.get(gid) is None
            and gid not in self.fora_da_lista
            and _mes_item(it) == mes
        ]
        for armada in list(self.armadas):
            if armada[0] == mes:
                self.armadas.remove(armada)
                self._pronta(armada[1])
        return {"items": itens}

    def _falhar(self, tipo: str):
        if tipo == "timeout":
            return TimeoutError("timed out (dublê 303)")
        if tipo == "refresh_exec":
            return RefreshError("token revogado no execute (dublê 303)")
        return _http({"5xx": 503, "403": 403, "429": 429}[tipo])

    def _get(self, gid: str):
        self.chamadas.append(("get", gid))
        if gid in self.ganchos:
            self.ganchos.pop(gid)()
        if self.proxima:
            tipo, self.proxima = self.proxima, None
            self.consumidas.append(("get", gid, tipo))
            raise self._falhar(tipo)
        if gid in self.por_id:
            tipo = self.por_id.pop(gid)
            self.consumidas.append(("get", gid, tipo))
            raise self._falhar(tipo)
        if gid not in self.itens:
            raise _http(503)  # falha fechado: id que o dublê não conhece
        modo = self.apagado.get(gid)
        item = copy.deepcopy(self.itens[gid])
        if modo is None:
            return item
        if modo == "cancelado_completo":
            item["status"] = "cancelled"
            return item
        if modo == "cancelado_minimo":
            return {"id": gid, "status": "cancelled"}
        raise _http(int(modo))

    def _insert(self, body: dict) -> dict:
        self.chamadas.append(("insert", body.get("summary")))
        if self.falha_insert:
            self.falha_insert = False
            raise _http(500)
        gid = f"{GID}g-{uuid.uuid4().hex[:10]}"
        item = {
            **copy.deepcopy(body),
            "id": gid,
            "status": "confirmed",
            "htmlLink": f"https://calendar.google.com/v303/{gid}",
        }
        self.registrar(item)
        self.inseridos.append((gid, copy.deepcopy(body)))
        return copy.deepcopy(item)

    def _patch(self, gid: str, body: dict) -> dict:
        self.chamadas.append(("patch", gid))
        if gid not in self.itens:
            raise _http(503)
        if self.apagado.get(gid) is not None:
            raise _http(404)
        self.itens[gid].update(copy.deepcopy(body))
        self.patches.append((gid, copy.deepcopy(body)))
        return copy.deepcopy(self.itens[gid])

    def _delete(self, gid: str) -> str:
        self.chamadas.append(("delete", gid))
        if gid not in self.itens:
            raise _http(503)
        self.apagado[gid] = "404"
        return ""


google = GoogleFalso()
cal_service.build = google.build
cal_service.load_credentials = google.load_credentials


def _iso_sp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "-03:00"


def _mes_item(item: dict) -> str:
    inicio = item.get("start") or {}
    valor = inicio.get("dateTime") or inicio.get("date") or ""
    return valor[:7]


def _item(
    gid: str,
    titulo: str,
    inicio: datetime,
    fim: datetime,
    *,
    local: str = "Rua V303, 1",
    descricao: str | None = MARCADOR,
    dia_inteiro: bool = False,
) -> dict:
    """Item do Google como a API devolve — SEM `created` (senão a guarda da 254 o pularia)."""
    item = {
        "id": gid,
        "status": "confirmed",
        "summary": titulo,
        "location": local,
        "htmlLink": f"https://calendar.google.com/v303/{gid}",
    }
    if descricao is not None:
        item["description"] = descricao
    if dia_inteiro:
        item["start"] = {"date": inicio.date().isoformat()}
        item["end"] = {"date": fim.date().isoformat()}
    else:
        item["start"] = {"dateTime": _iso_sp(inicio)}
        item["end"] = {"dateTime": _iso_sp(fim)}
    return item


# ── dublês do que não é Google ─────────────────────────────────────────────────────────────────
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: None
formularios_ops.retry_auto_link_pending = lambda: 0
LOCAL_ERRO_BANCO = "V303 ERRO DE BANCO"


def _sp_status_falso(location):
    """Sem ViaCEP. O local-sentinela do 13c provoca um erro de banco DENTRO de `sync_events`."""
    if location and LOCAL_ERRO_BANCO in location:
        db.session.execute(text("SELECT 1/0"))
    return False


cal_routes._lookup_sp_status = _sp_status_falso

_emails: list[dict] = []


def _send_falso(to: str, subject: str = "", body: str = "", html: str = "") -> bool:
    _emails.append({"to": to, "subject": subject, "html": html})
    return True


es._send = _send_falso


def _esperar_threads() -> None:
    """Os e-mails de mudança de data e de ensaio saem por thread: esperar antes de afirmar."""
    for t in threading.enumerate():
        if t is not threading.main_thread() and t.is_alive():
            t.join(timeout=20)


# ── harness ────────────────────────────────────────────────────────────────────────────────────
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


def cenario(bloco: str, nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((bloco, nome, "OK", ""))
        print(f"  OK         {nome}")
    except Bloqueado as exc:
        resultados.append((bloco, nome, "BLOQUEADO", str(exc)))
        print(f"  BLOQUEADO  {nome}: {exc}")
    except Exception as exc:  # noqa: BLE001 — harness: registra e segue
        ultima = traceback.format_exc().strip().splitlines()[-1]
        resultados.append((bloco, nome, "FALHA", ultima))
        print(f"  FALHA      {nome}: {exc}")
    finally:
        with app.app_context():
            db.session.rollback()
        google.desarmar()  # falha armada e não consumida não pode vazar para o cenário seguinte
        app.config[TRAVA] = True


def _marca(event_id: int):
    linhas = _no_banco(f"SELECT {COLUNA} FROM calendar_events WHERE id = :i", i=event_id)
    _garante(bool(linhas), f"evento {event_id} não existe mais")
    return linhas[0][0]


def _existe(event_id: int) -> bool:
    return bool(_no_banco("SELECT 1 FROM calendar_events WHERE id = :i", i=event_id))


def _precisa_marcado(event_id: int) -> None:
    if not _existe(event_id) or _marca(event_id) is None:
        raise Bloqueado("depende de evento marcado (História 1)")


def _hoje_sp() -> date:
    return now_sp().date()


# ── meses ──────────────────────────────────────────────────────────────────────────────────────
_PROXIMO_MES = [2031, 1]
FAIXA_ISOLADA = (datetime(2031, 1, 1), datetime(2045, 1, 1))
MES_ALEM = (2040, 6)  # além do horizonte do ciclo quando o cenário 8 roda; nunca liberado


def _mes_novo() -> tuple[int, int]:
    """Um mês isolado só do cenário, já liberado no dublê."""
    y, m = _PROXIMO_MES
    _PROXIMO_MES[1] += 1
    if _PROXIMO_MES[1] > 12:
        _PROXIMO_MES[0] += 1
        _PROXIMO_MES[1] = 1
    google.liberar(f"{y:04d}-{m:02d}")
    return y, m


def _ym(mes: tuple[int, int]) -> str:
    return f"{mes[0]:04d}-{mes[1]:02d}"


def _mes_passado() -> tuple[int, int]:
    """O mês anterior ao evento mais antigo do espelho — o ciclo automático nunca chega lá."""
    if "mes_passado" not in estado:
        linha = _no_banco(
            "SELECT MIN(start_at) FROM calendar_events WHERE google_event_id NOT LIKE 'v303%'"
        )[0][0]
        base = linha or datetime(2020, 1, 1)
        y, m = base.year, base.month - 1
        if m == 0:
            y, m = y - 1, 12
        estado["mes_passado"] = (y, m)
        google.liberar(_ym((y, m)))
    return estado["mes_passado"]


# ── pessoas ────────────────────────────────────────────────────────────────────────────────────
def _usuario(sufixo: str, *papeis: str) -> str:
    email = f"{PREFIX}{sufixo}@manto.local"
    with app.app_context():
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        user.set_password(SENHA)
        for p in papeis:
            user.roles.append(Role.query.filter_by(name=p).one())
        db.session.add(user)
        db.session.commit()
        estado["usuarios"].append(user.id)
    return email


def _talento(sufixo: str) -> int:
    with app.app_context():
        t = Talent(
            full_name=f"{PREFIX}{sufixo}",
            artistic_name=f"{PREFIX}{sufixo}",
            email_contact=f"{PREFIX}{sufixo}@manto.local",
            status="active",
            must_change_password=False,
            terms_accepted_at=datetime.utcnow(),
        )
        t.set_password(SENHA)
        db.session.add(t)
        db.session.commit()
        estado["talentos"].append(t.id)
        return t.id


def _cliente(email: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
    _garante(r.status_code == 200, f"login de {email} → {r.status_code}")
    return c


def _cliente_portal(talento_id: int):
    c = app.test_client()
    r = c.post(
        "/api/portal/auth/login",
        json={"login": f"{PREFIX}{_sufixo_talento(talento_id)}@manto.local", "password": SENHA},
    )
    _garante(r.status_code == 200, f"login do talento {talento_id} → {r.status_code}")
    return c


def _sufixo_talento(talento_id: int) -> str:
    return _no_banco("SELECT full_name FROM talents WHERE id = :i", i=talento_id)[0][0][
        len(PREFIX) :
    ]


def _destinatarios() -> int:
    with app.app_context():
        return len(
            notificacoes_ops.resolver_destinatarios((RoleName.COMERCIAL, RoleName.SUPERADMIN))
        )


# ── eventos ────────────────────────────────────────────────────────────────────────────────────
def _evento(
    nome: str,
    mes: tuple[int, int],
    *,
    dia: int = 10,
    hora: int = 19,
    duracao: int = 3,
    tipo: str = "CORP",
    titulo: str | None = None,
    dia_inteiro: bool = False,
    descricao: str | None = MARCADOR,
    local: str = "Rua V303, 1",
) -> int:
    """Registra o item no dublê e o importa pelo caminho real (`sync_events`)."""
    gid = f"{GID}-{nome.lower()}-{uuid.uuid4().hex[:6]}"
    inicio = datetime(mes[0], mes[1], dia, 0 if dia_inteiro else hora)
    fim = inicio + (timedelta(days=1) if dia_inteiro else timedelta(hours=duracao))
    titulo = titulo or f"({tipo}) V303 {nome.upper()}"
    item = _item(
        gid, titulo, inicio, fim, local=local, descricao=descricao, dia_inteiro=dia_inteiro
    )
    google.registrar(item)
    with app.app_context():
        cal_routes.sync_events([item])
        ev = CalendarEvent.query.filter_by(google_event_id=gid).one()
        estado["eventos"][ev.id] = gid
        return ev.id


def _gid(event_id: int) -> str:
    return estado["eventos"][event_id]


def _venda(event_id: int, valor: str = "1500.00") -> None:
    with app.app_context():
        ev = db.session.get(CalendarEvent, event_id)
        ev.sale_value = Decimal(valor)
        ev.sale_date = date.today()
        db.session.commit()


def _comprovante(event_id: int, valor: str | None = "500.00") -> None:
    with app.app_context():
        db.session.add(
            EventPayment(
                event_id=event_id,
                file_path=f"{PREFIX}comprovante.pdf",
                amount=Decimal(valor) if valor is not None else None,
            )
        )
        db.session.commit()


def _contrato(event_id: int) -> None:
    with app.app_context():
        db.session.add(
            EventContract(event_id=event_id, file_path=f"{PREFIX}contrato.pdf", amount=1500)
        )
        db.session.commit()


def _escalar(
    event_id: int,
    talento_id: int,
    *,
    vaga: str | None = None,
    convite: str = "accepted",
    substituir_42: bool = False,
) -> int:
    """Preenche uma vaga que o SISTEMA criou. Nunca cria `EventRole` com nome inventado."""
    with app.app_context():
        q = EventRole.query.filter(EventRole.event_id == event_id)
        q = (
            q.filter(EventRole.character_name == vaga)
            if vaga
            else q.filter(EventRole.role_type != "extra")
        )
        if not substituir_42:
            q = q.filter(EventRole.talent_id.is_(None))
        role = q.first()
        _garante(role is not None, f"evento {event_id} sem vaga livre ({vaga or 'personagem'})")
        role.talent_id = talento_id
        role.invite_status = convite
        role.assigned_at = datetime.utcnow()
        db.session.commit()
        return role.id


def _grupo(lider_id: int, satelite_id: int) -> None:
    with app.app_context():
        db.session.get(CalendarEvent, satelite_id).group_leader_id = lider_id
        db.session.commit()


def _ensaio_filho(pai_id: int, mes: tuple[int, int]) -> int:
    """Ensaio por INSERT (o endpoint de ensaio cria no Google), num mês que nenhum ciclo lista."""
    gid = f"{GID}-ensaio-{uuid.uuid4().hex[:6]}"
    with app.app_context():
        ens = CalendarEvent(
            google_event_id=gid,
            title=f"🟧 ENSAIO V303 {pai_id}",
            start_at=datetime(mes[0], mes[1], 5, 9),
            end_at=datetime(mes[0], mes[1], 5, 12),
            event_type="ENSAIO",
            parent_event_id=pai_id,
            description=MARCADOR,
        )
        db.session.add(ens)
        db.session.flush()
        db.session.add(
            EventLog(
                event_id=ens.id,
                actor_name="verify",
                actor_role="verify",
                message="histórico do ensaio (verify 303)",
            )
        )
        db.session.commit()
        estado["eventos"][ens.id] = gid
        return ens.id


def _ciclo() -> dict:
    from app.calendar.sync import run_calendar_sync

    with app.app_context():
        return run_calendar_sync()


def _limpar_fantasmas(email: str) -> dict:
    c = _cliente(email)
    r = c.post(ROTAS["admin_sync"], json={"action": "cleanup_past"})
    _garante(r.status_code == 200, f"Limpar eventos fantasma → {r.status_code}")
    return r.get_json()


def _linha_mes(resposta: dict, mes: tuple[int, int]) -> dict:
    for linha in resposta.get("results", []):
        if linha.get("ym") == _ym(mes):
            return linha
    raise AssertionError(f"o mês {_ym(mes)} não veio em results[]")


def _marcar_pelo_ciclo(event_id: int, modo: str = "cancelado_completo") -> None:
    google.apagar(_gid(event_id), modo)
    _ciclo()


def _auditoria(acao: str, event_id: int | None = None, gid: str | None = None) -> list:
    if gid is not None:
        return _no_banco(
            "SELECT detail FROM audit_logs WHERE action = :a AND detail LIKE :g",
            a=acao,
            g=f"gcal:{gid}%",
        )
    return _no_banco(
        "SELECT detail FROM audit_logs WHERE action = :a AND entity_type = 'agenda' "
        "AND entity_id = :i",
        a=acao,
        i=event_id,
    )


def _historico(event_id: int) -> list[str]:
    return [
        r[0]
        for r in _no_banco(
            "SELECT message FROM event_logs WHERE event_id = :i ORDER BY id", i=event_id
        )
    ]


def _avisos(event_id: int, *, so_nao_lidos: bool = False) -> list:
    sql = (
        "SELECT user_id, read_at FROM notifications WHERE kind = :k AND entity_type = 'calendar_event' "
        "AND entity_id = :i"
    )
    if so_nao_lidos:
        sql += " AND read_at IS NULL"
    return _no_banco(sql, k=KIND, i=event_id)


def _nao_apagado(event_id: int, regra: str) -> None:
    _garante(_existe(event_id), f"{regra}: o sync apagou o evento {event_id}")


def _foto(event_id: int) -> tuple:
    """Título, datas e escala — o que o "Sincronizar" de evento ausente não pode tocar."""
    ev = _no_banco("SELECT title, start_at, end_at FROM calendar_events WHERE id = :i", i=event_id)[
        0
    ]
    vagas = _no_banco(
        "SELECT character_name, talent_id FROM event_roles WHERE event_id = :i "
        "ORDER BY character_name",
        i=event_id,
    )
    return (tuple(ev), tuple(tuple(v) for v in vagas))


def _payload_basico(event_id: int, **mudancas) -> dict:
    """O corpo completo do `PATCH …/basico` a partir do que está no banco, com as mudanças."""
    t, tipo, ini, fim, loc, desc = _no_banco(
        "SELECT title, event_type, start_at, end_at, location, description FROM calendar_events "
        "WHERE id = :i",
        i=event_id,
    )[0]
    corpo = {
        "title": t,
        "event_type": tipo or "CORP",
        "date": ini.date().isoformat(),
        "start": ini.strftime("%H:%M"),
        "end": fim.strftime("%H:%M"),
        "location": loc or "",
        "description": desc or "",
    }
    corpo.update(mudancas)
    return corpo


def _erro(r) -> dict:
    return (r.get_json(silent=True) or {}).get("error") or {}


def _faixa(email: str) -> dict:
    r = _cliente(email).get(ROTAS["faixa"])
    _garante(r.status_code == 200, f"GET da faixa → {r.status_code}")
    return r.get_json()


# ── guarda de ambiente e limpeza ───────────────────────────────────────────────────────────────
def _sair(msg: str) -> None:
    print(f"\nAMBIENTE IMPRÓPRIO — {msg}")
    sys.exit(2)


def guarda_de_ambiente() -> None:
    url = os.environ["DATABASE_URL"]
    if not ("localhost" in url or "127.0.0.1" in url):
        _sair("DATABASE_URL não é o manto_local (localhost).")
    if not _no_banco(
        "SELECT 1 FROM information_schema.columns WHERE table_name = 'calendar_events' "
        "AND column_name = :c",
        c=COLUNA,
    ):
        _sair(
            f"a coluna {COLUNA} não existe: rode `flask db upgrade` e `python seed.py` "
            "(o refresh do espelho desfaz a migration)."
        )
    ultimo = _no_banco("SELECT calendar_auto_sync_at FROM site_settings WHERE id = 1")[0][0]
    if ultimo and datetime.utcnow() - ultimo < timedelta(minutes=15):
        _sair(
            "houve sincronização automática há menos de 15 minutos — o backend local está ligado, "
            "e a thread dele falaria com o Google real sobre os eventos de teste. Pare-o."
        )
    estranhos = _no_banco(
        "SELECT COUNT(*) FROM calendar_events WHERE start_at >= :a AND start_at < :b "
        "AND google_event_id NOT LIKE 'v303%'",
        a=FAIXA_ISOLADA[0],
        b=FAIXA_ISOLADA[1],
    )[0][0]
    if estranhos:
        _sair(f"{estranhos} evento(s) que não são do verify nos meses isolados (2031–2044).")
    marcados = _no_banco(
        f"SELECT COUNT(*) FROM calendar_events WHERE {COLUNA} IS NOT NULL "
        "AND google_event_id NOT LIKE 'v303%'"
    )[0][0]
    if marcados:
        _sair(
            f"{marcados} evento(s) do espelho estão marcados (uma limpeza local leu o Google real): "
            "refresh do espelho e `flask db upgrade` antes do verify."
        )
    if "cache" not in estado:
        estado["cache"] = _no_banco("SELECT calendar_sync_cache FROM site_settings WHERE id = 1")[
            0
        ][0]


def limpar() -> None:
    """Apaga tudo o que o verify criou, pelo prefixo — nunca pelo título (o "Sincronizar" da
    `main` troca o título de evento apagado por "Sem título")."""
    with app.app_context():
        db.session.rollback()
        eventos = CalendarEvent.query.filter(CalendarEvent.google_event_id.like(f"{GID}%")).all()
        ids_vivos = [e.id for e in eventos]
        todos = set(ids_vivos) | set(estado["eventos"].keys())
        if todos:
            db.session.execute(
                text(
                    "DELETE FROM notifications WHERE entity_type = 'calendar_event' "
                    "AND entity_id = ANY(:ids)"
                ),
                {"ids": list(todos)},
            )
            db.session.execute(
                text("DELETE FROM commission_payments WHERE event_id = ANY(:ids)"),
                {"ids": ids_vivos or [0]},
            )
        # Ensaios antes dos pais; satélites antes dos líderes.
        ordem = sorted(
            eventos, key=lambda e: (e.parent_event_id is None, e.group_leader_id is None)
        )
        for ev in ordem:
            cal_routes._clear_event_side_tables(ev.id)
            db.session.delete(ev)
            db.session.flush()
        db.session.execute(
            text(
                "DELETE FROM audit_logs WHERE (entity_type = 'agenda' AND entity_id = ANY(:ids)) "
                "OR detail LIKE 'gcal:v303%' OR (actor_name = 'auto-sync' AND created_at >= :ini)"
            ),
            {"ids": list(todos) or [0], "ini": INICIO_UTC},
        )
        db.session.commit()

        talentos = Talent.query.filter(Talent.full_name.like(f"{PREFIX}%")).all()
        for t in talentos:
            db.session.execute(text("DELETE FROM event_ratings WHERE talent_id = :t"), {"t": t.id})
            db.session.delete(t)
        usuarios = User.query.filter(User.email.like(f"{PREFIX}%")).all()
        for u in usuarios:
            db.session.execute(text("DELETE FROM notifications WHERE user_id = :u"), {"u": u.id})
            u.roles.clear()
            db.session.delete(u)
        if "cache" in estado:
            db.session.execute(
                text("UPDATE site_settings SET calendar_sync_cache = :c WHERE id = 1"),
                {"c": estado["cache"]},
            )
        db.session.commit()
    app.config[TRAVA] = True


# ── B0 — chão ──────────────────────────────────────────────────────────────────────────────────
def c0_chao() -> None:
    _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "a trava de e-mail não está ligada")
    _garante(
        app.config.get(TRAVA) is True, "a trava de escrita de evento não está ligada neste ambiente"
    )
    _garante(cal_service.build == google.build, "o dublê não está em service.build")
    _garante(
        cal_service.load_credentials == google.load_credentials,
        "o dublê não está em service.load_credentials",
    )
    antes = len(rede_bloqueada)
    try:
        socket.create_connection(("203.0.113.10", 80), timeout=2)  # TEST-NET-3: sem DNS
    except OSError:
        pass
    _garante(len(rede_bloqueada) > antes, "o disjuntor de rede não recusou um host externo")
    del rede_bloqueada[antes:]


_FILHO = """
import importlib.util, json, pathlib, sys
alvo = pathlib.Path(sys.argv[1]) / "app" / "config.py"
spec = importlib.util.spec_from_file_location("cfg_isolada", alvo)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(json.dumps({"trava": bool(getattr(mod.Config, "CALENDAR_SUPPRESS_EVENT_WRITES", None))}))
"""


def _trava_com(**env: str) -> bool:
    ambiente = {k: v for k, v in os.environ.items() if not k.startswith("CALENDAR_")}
    ambiente.update(env)
    ambiente["FLASK_ENV"] = (
        "development"  # com production o config.py gravaria instance/.secret_key
    )
    saida = subprocess.run(
        [sys.executable, "-c", _FILHO, str(REPO_ROOT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=ambiente,
        timeout=120,
    )
    _garante(saida.returncode == 0, f"processo filho falhou: {saida.stderr[-300:]}")
    return json.loads(saida.stdout.strip().splitlines()[-1])["trava"]


def c18_trava() -> None:
    local = os.environ["DATABASE_URL"]
    remoto = "postgresql://u:p@db.exemplo.com:5432/manto"
    _garante(_trava_com(DATABASE_URL=local) is True, "banco local não ficou travado")
    _garante(_trava_com(DATABASE_URL=remoto) is False, "banco remoto ficou travado")
    _garante(
        _trava_com(DATABASE_URL=remoto, CALENDAR_SUPPRESS_EVENT_WRITES="true") is True,
        "CALENDAR_SUPPRESS_EVENT_WRITES=true não travou",
    )
    _garante(
        _trava_com(DATABASE_URL=local, CALENDAR_ALLOW_LOCAL_EVENT_WRITES="true") is False,
        "CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true não liberou o local",
    )


# ── B1 — o evento com dinheiro fica ────────────────────────────────────────────────────────────
def c1_com_venda() -> None:
    mes = _mes_novo()
    t = estado["t"]
    alvos = []
    for i, modo in enumerate(MODOS_APAGADO):
        ev = _evento(f"um-{modo}", mes, dia=10 + i)
        _venda(ev)
        _comprovante(ev)
        _contrato(ev)
        _escalar(ev, t)
        alvos.append((ev, modo))
    controle = _evento("um-controle", mes, dia=20)
    estado["e1"] = alvos[0][0]
    for ev, modo in alvos:
        google.apagar(_gid(ev), modo)
    _esperar_threads()
    n_emails = len(_emails)
    _ciclo()
    _esperar_threads()
    for ev, modo in alvos:
        _nao_apagado(ev, "FR-001: o sync apagou evento com venda")
        marca = _marca(ev)
        _garante(marca is not None, f"evento {ev} ({modo}) não foi marcado")
        _garante(
            marca.date() == _hoje_sp(), f"a marca do evento {ev} não tem a data de hoje: {marca}"
        )
        venda = _no_banco("SELECT sale_value FROM calendar_events WHERE id = :i", i=ev)[0][0]
        _garante(venda == Decimal("1500.00"), f"venda mudou: {venda}")
        _garante(
            _no_banco("SELECT COUNT(*) FROM event_payments WHERE event_id = :i", i=ev)[0][0] == 1,
            "o comprovante sumiu",
        )
        _garante(
            _no_banco("SELECT COUNT(*) FROM event_contracts WHERE event_id = :i", i=ev)[0][0] == 1,
            "o contrato sumiu",
        )
        _garante(
            _no_banco(
                "SELECT COUNT(*) FROM event_roles WHERE event_id = :i AND talent_id = :t", i=ev, t=t
            )[0][0]
            == 1,
            "a escala sumiu",
        )
        _garante(
            any("Sumiu do Google Agenda" in m and "Preso:" in m for m in _historico(ev)),
            f"o histórico do evento {ev} não diz que ele sumiu e o que estava preso",
        )
        _garante(_auditoria("sumiu_do_google", ev), f"sem auditoria `sumiu_do_google` para {ev}")
    _garante(
        len(_emails) == n_emails, f"a marca mandou {len(_emails) - n_emails} e-mail(s) ao elenco"
    )

    alvo = alvos[0][0]
    titulo = _no_banco("SELECT title FROM calendar_events WHERE id = :i", i=alvo)[0][0]
    c = _cliente(estado["superadmin"])
    mes_json = c.get(ROTAS["agenda"].format(ym=_ym(mes))).get_json()
    resumo = next((e for e in mes_json.get("events", []) if e.get("id") == alvo), None)
    _garante(
        resumo is not None and resumo.get("situacao") == "sumiu_do_google",
        f"agenda do mês: situacao = {resumo and resumo.get('situacao')!r}",
    )
    dia_json = c.get(ROTAS["dia"].format(dia=f"{mes[0]:04d}-{mes[1]:02d}-10")).get_json()
    resumo = next((e for e in dia_json.get("events", []) if e.get("id") == alvo), None)
    _garante(
        resumo is not None and resumo.get("situacao") == "sumiu_do_google",
        "visão Dia sem a situação",
    )
    from urllib.parse import quote

    busca = c.get(ROTAS["busca"].format(q=quote(titulo))).get_json()
    resumo = next((e for e in busca.get("items", []) if e.get("id") == alvo), None)
    _garante(
        resumo is not None and resumo.get("situacao") == "sumiu_do_google", "busca sem a situação"
    )
    det = c.get(ROTAS["detalhe"].format(id=alvo)).get_json()["event"]
    _garante((det.get("sumiu_do_google") or {}).get("desde"), "detalhe sem `sumiu_do_google.desde`")
    _garante(det.get("google_html_link") is None, "detalhe do marcado ainda manda o link do Google")
    det_c = c.get(ROTAS["detalhe"].format(id=controle)).get_json()["event"]
    _garante(det_c.get("google_html_link"), "o evento de controle perdeu o link do Google")


def c1b_passado() -> None:
    mp = _mes_passado()
    ev = _evento("umb", mp, dia=12)
    _venda(ev)
    google.apagar(_gid(ev))
    r = _limpar_fantasmas(estado["superadmin"])
    linha = _linha_mes(r, mp)
    _nao_apagado(ev, "FR-001: o 'Limpar eventos fantasma' apagou evento com venda")
    _garante(_marca(ev) is not None, "evento passado com venda não foi marcado")
    for chave in ("marcados", "movidos", "desmarcados", "inconclusivos", "falhas"):
        _garante(chave in linha, f"a linha do mês não traz `{chave}`")
    _garante(linha["marcados"] == 1, f"marcados = {linha['marcados']}")
    _garante(
        "mantido(s) e marcado(s)" in (r.get("message") or ""), f"mensagem: {r.get('message')!r}"
    )
    rc = _cliente(estado["comercial"]).post(ROTAS["admin_sync"], json={"action": "cleanup_past"})
    _garante(
        rc.status_code == 403, f"COMERCIAL chamando a limpeza → {rc.status_code} (deve ser 403)"
    )


def c2_um_aviso() -> None:
    e1 = estado.get("e1")
    _garante(e1 is not None, "o cenário 1 não semeou o evento")
    _precisa_marcado(e1)
    n = _destinatarios()
    _ciclo()
    _ciclo()
    avisos = _avisos(e1)
    usuarios = [a[0] for a in avisos]
    _garante(len(avisos) == n, f"{len(avisos)} aviso(s) para {n} destinatário(s)")
    _garante(len(set(usuarios)) == len(usuarios), "destinatário com aviso repetido")
    _garante(estado["figurino_id"] not in usuarios, "o FIGURINO recebeu o aviso")


def c2b_corrida() -> None:
    mes = _mes_novo()
    ev = _evento("doisb", mes)
    _venda(ev)
    gid = _gid(ev)
    google.apagar(gid)
    carimbo = datetime(2030, 1, 1, 10, 0, 0)
    disparou: list[int] = []

    def gancho() -> None:
        _no_banco_escrever(
            f"UPDATE calendar_events SET {COLUNA} = :c WHERE id = :i", c=carimbo, i=ev
        )
        disparou.append(1)

    google.ganchos[gid] = gancho
    try:
        r = _limpar_fantasmas(estado["superadmin"])
    finally:
        google.ganchos.pop(gid, None)
    _garante(disparou, "FR-002: a limpeza não consultou o evento antes de decidir")
    _nao_apagado(ev, "FR-001")
    _garante(
        _marca(ev) == carimbo, f"a limpeza marcou de novo por cima do outro processo: {_marca(ev)}"
    )
    _garante(
        not any("Sumiu do Google" in m for m in _historico(ev)), "histórico de sumiço duplicado"
    )
    _garante(not _auditoria("sumiu_do_google", ev), "auditoria de sumiço duplicada")
    _garante(not _avisos(ev), "aviso emitido por quem perdeu a corrida")
    _garante(_linha_mes(r, mes).get("falhas", 0) == 0, "a corrida contou como falha")


def _prepara_3456() -> dict:
    if "3456" not in estado:
        mes = _mes_novo()
        casos = {
            "3 (comprovante)": _evento("tres-a", mes, dia=3),
            "3 (comprovante sem valor)": _evento("tres-b", mes, dia=4),
            "4": _evento("quatro", mes, dia=5),
            "5": _evento("cinco", mes, dia=6),
            "6 (líder)": _evento("seis-lider", mes, dia=7),
            "6 (satélite)": _evento("seis-sat", mes, dia=8),
        }
        _comprovante(casos["3 (comprovante)"], "300.00")
        _comprovante(casos["3 (comprovante sem valor)"], None)
        _contrato(casos["4"])
        _escalar(casos["5"], estado["t"])
        _grupo(casos["6 (líder)"], casos["6 (satélite)"])
        for ev in casos.values():
            google.apagar(_gid(ev))
        _ciclo()
        estado["3456"] = casos
    return estado["3456"]


def _fica_marcado(*chaves: str) -> None:
    casos = _prepara_3456()
    for chave in chaves:
        ev = casos[chave]
        _nao_apagado(ev, f"FR-001 ({chave})")
        _garante(_marca(ev) is not None, f"{chave}: não foi marcado")
        _garante(
            _auditoria("sumiu_do_google", ev), f"{chave}: sem auditoria do que segurou o evento"
        )


def c7_vazios() -> None:
    mes = _mes_novo()
    vazios = [
        (_evento(f"sete-{modo}", mes, dia=2 + i), modo) for i, modo in enumerate(MODOS_APAGADO)
    ]
    show = _evento("sete-show", mes, dia=12, tipo="SHOW")
    gids = {ev: _gid(ev) for ev, _ in vazios}
    gids[show] = _gid(show)
    for ev, modo in vazios:
        google.apagar(_gid(ev), modo)
    google.apagar(_gid(show))
    _ciclo()
    estado["sete"] = (vazios, show, gids)
    for ev in gids:
        _garante(not _existe(ev), f"o evento vazio {ev} não foi apagado")
        estado["apagados"].add(ev)


def c7_auditoria() -> None:
    _garante("sete" in estado, "o cenário 7 não rodou")
    vazios, show, gids = estado["sete"]
    esperado = {
        "cancelado_completo": "cancelled",
        "cancelado_minimo": "cancelled",
        "404": "http_404",
        "410": "http_410",
    }
    for ev, modo in vazios:
        linhas = _auditoria("auto_deleted", gid=gids[ev])
        _garante(linhas, f"sem auditoria `auto_deleted` para {gids[ev]}")
        det = linhas[-1][0] or ""
        _garante(
            esperado[modo] in det, f"a auditoria não diz o que o Google respondeu ({modo}): {det!r}"
        )
        _garante(
            "sem contrato" in det and "0 escalados" in det,
            f"a auditoria sem o retrato vazio: {det!r}",
        )
    det = (_auditoria("auto_deleted", gid=gids[show]) or [[""]])[-1][0] or ""
    _garante(
        "só o técnico de som automático" in det, f"SHOW: retrato sem o técnico automático: {det!r}"
    )


def c7a_tecnico() -> None:
    mes = _mes_novo()
    presenca = _evento("setea-presenca", mes, dia=3, tipo="SHOW")
    _escalar(presenca, estado["t"], vaga="Técnico de Som (Presença)")
    outro = _evento("setea-outro", mes, dia=4, tipo="SHOW")
    _escalar(outro, estado["t2"], vaga="Técnico de Som", substituir_42=True)
    google.apagar(_gid(presenca))
    google.apagar(_gid(outro))
    _ciclo()
    for ev, nome in ((presenca, "Presença designada"), (outro, "outro técnico no lugar do padrão")):
        _nao_apagado(ev, f"FR-001 ({nome})")
        _garante(_marca(ev) is not None, f"SHOW com {nome} não foi marcado")


def c7b_ensaio() -> None:
    mes = _mes_novo()
    pai_a = _evento("seteb-a", mes, dia=3)
    ens_a = _ensaio_filho(pai_a, (2044, 1))
    google.apagar(_gid(pai_a))
    m = google.marco()
    _ciclo()
    _garante(
        not _existe(pai_a),
        "o pai vazio com ensaio não foi apagado pelo sync (a exclusão estourou?)",
    )
    _garante(not _existe(ens_a), "o ensaio ficou órfão")
    estado["apagados"].update({pai_a, ens_a})
    _garante(google.contar("get", {_gid(ens_a)}, m) == 0, "o ensaio foi consultado no Google")
    pai_b = _evento("seteb-b", mes, dia=12)
    ens_b = _ensaio_filho(pai_b, (2044, 2))
    r = _cliente(estado["superadmin"]).delete(ROTAS["excluir"].format(id=pai_b))
    _garante(
        r.status_code == 200,
        f"DELETE do pai vazio com ensaio → {r.status_code}: {r.get_data(as_text=True)[:160]}",
    )
    _garante(not _existe(pai_b) and not _existe(ens_b), "o DELETE não apagou pai e ensaio")
    estado["apagados"].update({pai_b, ens_b})


def _tres_candidatos(nome: str) -> tuple[tuple[int, int], list[int]]:
    mes = _mes_novo()
    evs = [_evento(f"{nome}-{i}", mes, dia=3 + i) for i in range(3)]
    for ev in evs:
        _venda(ev)
        google.apagar(_gid(ev))
    return mes, evs


def c13_inconclusivo() -> None:
    for tipo in ("5xx", "timeout", "ausente", "refresh"):
        mes, evs = _tres_candidatos(f"treze-{tipo}")
        gids = {_gid(ev) for ev in evs}
        google.armar(tipo, apos_lista_de=_ym(mes))
        m = google.marco()
        _limpar_fantasmas(estado["superadmin"])
        for ev in evs:
            _nao_apagado(ev, f"FR-003 ({tipo}): evento apagado com resposta inconclusiva")
            _garante(_marca(ev) is None, f"FR-003 ({tipo}): marcado com resposta inconclusiva")
        gets = google.contar("get", gids, m)
        esperado = 1 if tipo in ("5xx", "timeout") else 0  # credencial cai antes do `get`
        _garante(
            gets == esperado, f"{tipo}: {gets} consulta(s) no mês (esperado {esperado}; FR-040)"
        )
        _garante(
            google.proxima is None and google.credencial is None,
            f"{tipo}: a falha não foi consumida",
        )
        _limpar_fantasmas(estado["superadmin"])  # controle: com o Google respondendo, marca
        for ev in evs:
            _garante(
                _marca(ev) is not None, f"{tipo}: controle — com ausência confirmada não marcou"
            )

    for tipo in ("403", "429"):
        mes, evs = _tres_candidatos(f"treze-{tipo}")
        gids = {_gid(ev) for ev in evs}
        google.armar(tipo, apos_lista_de=_ym(mes))
        m = google.marco()
        _limpar_fantasmas(estado["superadmin"])
        marcados = [ev for ev in evs if _marca(ev) is not None]
        _garante(
            len(marcados) == 2,
            f"{tipo}: {len(marcados)} marcado(s) — a recusa de um evento "
            "não pode segurar os outros",
        )
        _garante(google.contar("get", gids, m) == 3, f"{tipo}: os demais não foram consultados")

    ma, mb = _mes_novo(), _mes_novo()
    evs_a = [_evento(f"treze-a{i}", ma, dia=3 + i) for i in range(2)]
    evs_b = [_evento(f"treze-b{i}", mb, dia=3 + i) for i in range(2)]
    for ev in evs_a + evs_b:
        _venda(ev)
        google.apagar(_gid(ev))
    google.armar("5xx", apos_lista_de=_ym(ma))
    _limpar_fantasmas(estado["superadmin"])
    _garante(all(_marca(ev) is None for ev in evs_a), "dois meses: o mês da falha marcou")
    _garante(
        all(_marca(ev) is not None for ev in evs_b),
        "dois meses: o mês seguinte não voltou a consultar",
    )

    mes, evs = _tres_candidatos("treze-ciclo")
    google.armar("5xx", apos_lista_de=_ym(mes))
    _ciclo()
    det = (
        _no_banco(
            "SELECT detail FROM audit_logs WHERE actor_name = 'auto-sync' ORDER BY id DESC LIMIT 1"
        )[0][0]
        or ""
    )
    _garante(
        "Sumiços:" in det, f"o resumo do ciclo não traz a frase 'Sumiços:' (FR-042): {det[:160]!r}"
    )
    import re

    frase = det[det.index("Sumiços:") :]
    _garante("0 com falha" in frase, f"o ciclo contou falha num inconclusivo: {frase[:160]!r}")
    m_sem = re.search(r"(\d+) sem confirmação", frase)
    _garante(
        m_sem and int(m_sem.group(1)) >= 1,
        f"o ciclo não contou os sem confirmação: {frase[:160]!r}",
    )
    primeiro_mes = re.search(r"\d{4}-\d{2}:", det)
    _garante(
        not primeiro_mes or primeiro_mes.start() > det.index("Sumiços:"),
        "os totais vieram depois da lista de meses (que é cortada nos oito primeiros)",
    )


def c13_lista_falha() -> None:
    mes = _mes_novo()
    ev = _evento("treze-lista", mes)
    _venda(ev)
    google.apagar(_gid(ev))
    google.lista_falha.add(_ym(mes))
    try:
        _limpar_fantasmas(estado["superadmin"])
    finally:
        google.lista_falha.discard(_ym(mes))
    _nao_apagado(ev, "a lista do mês falhou e mesmo assim o evento foi apagado")
    _garante(_marca(ev) is None, "a lista do mês falhou e mesmo assim o evento foi marcado")


def c13b_aviso_falha() -> None:
    mes, evs = _tres_candidatos("trezeb")
    n = _destinatarios()
    emitir_real = notificacoes_ops.emitir
    falhou: list[int] = []
    # Só os eventos deste cenário: a limpeza percorre todos os meses, e um evento ausente que
    # sobrou de cenário anterior (o mês do 5xx do 13, que nunca é limpo) consumiria a falha antes.
    alvos = set(evs)

    def emitir_quebrado(kind, **kw):
        if kind == KIND and not falhou and (kw.get("entidade") or (None, None))[1] in alvos:
            falhou.append(1)
            raise RuntimeError("o aviso falhou (verify 303)")
        return emitir_real(kind, **kw)

    notificacoes_ops.emitir = emitir_quebrado
    try:
        r = _limpar_fantasmas(estado["superadmin"])
    finally:
        notificacoes_ops.emitir = emitir_real
    _garante(falhou, "o aviso do sino nem foi tentado")
    sem = [ev for ev in evs if _marca(ev) is None]
    _garante(len(sem) == 1, f"{len(sem)} evento(s) sem marca (esperado 1: o do aviso que falhou)")
    _garante(not _avisos(sem[0]), "marca desfeita mas o aviso ficou")
    linha = _linha_mes(r, mes)
    _garante(linha.get("ok") is False and linha.get("falhas") == 1, f"linha do mês: {linha}")
    for ev in evs:
        if ev != sem[0]:
            _garante(len(_avisos(ev)) == n, f"evento {ev}: {len(_avisos(ev))} aviso(s) para {n}")
    _limpar_fantasmas(estado["superadmin"])
    _garante(_marca(sem[0]) is not None, "na rodada seguinte o evento não foi marcado")
    _garante(len(_avisos(sem[0])) == n, "na rodada seguinte o aviso não saiu para todos")

    mes2 = _mes_novo()
    ev2 = _evento("trezeb-ciclo", mes2)
    _venda(ev2)
    google.apagar(_gid(ev2))
    falhou.clear()
    alvos.clear()
    alvos.add(ev2)
    notificacoes_ops.emitir = emitir_quebrado
    try:
        _ciclo()
    finally:
        notificacoes_ops.emitir = emitir_real
    det = (
        _no_banco(
            "SELECT detail FROM audit_logs WHERE actor_name = 'auto-sync' ORDER BY id DESC LIMIT 1"
        )[0][0]
        or ""
    )
    _garante(
        "Sumiços:" in det and "1 com falha" in det[det.index("Sumiços:") :],
        f"o resumo do ciclo não contou a falha: {det[:200]!r}",
    )


def _sentinela(mes: tuple[int, int]) -> str:
    gid = f"{GID}-sentinela-{uuid.uuid4().hex[:6]}"
    inicio = datetime(mes[0], mes[1], 15, 19)
    google.registrar(
        _item(
            gid,
            "(CORP) V303 SENTINELA",
            inicio,
            inicio + timedelta(hours=2),
            local=LOCAL_ERRO_BANCO,
        )
    )
    return gid


def _novo_no_google(nome: str, mes: tuple[int, int]) -> str:
    gid = f"{GID}-{nome}-{uuid.uuid4().hex[:6]}"
    inicio = datetime(mes[0], mes[1], 16, 19)
    google.registrar(_item(gid, f"(CORP) V303 {nome.upper()}", inicio, inicio + timedelta(hours=2)))
    return gid


def c13c_erro_de_banco() -> None:
    m1, m2 = _mes_novo(), _mes_novo()
    _evento("trezec-base1", m1, dia=2)
    sentinela = _sentinela(m1)
    novo = _novo_no_google("trezec-novo", m2)
    cand = _evento("trezec-cand", m2, dia=3)
    _venda(cand)
    google.apagar(_gid(cand))
    try:
        _ciclo()
    finally:
        google.remover(sentinela)  # senão todo ciclo seguinte bateria no erro
    linhas = _no_banco("SELECT id FROM calendar_events WHERE google_event_id = :g", g=novo)
    _garante(linhas, "o mês seguinte ao erro de banco não importou o item novo")
    estado["eventos"][linhas[0][0]] = novo
    _garante(_marca(cand) is not None, "o mês seguinte ao erro de banco não limpou")
    _garante(len(_avisos(cand)) > 0, "marca sem aviso")

    m3, m4 = _mes_novo(), _mes_novo()
    _evento("trezec-base3", m3, dia=2)  # sem evento no banco o 'Limpar' não visita o mês
    sentinela = _sentinela(m3)
    novo = _novo_no_google("trezec-novo4", m4)
    cand4 = _evento("trezec-cand4", m4, dia=3)
    _venda(cand4)
    google.apagar(_gid(cand4))
    try:
        r = _limpar_fantasmas(estado["superadmin"])
    finally:
        google.remover(sentinela)
    _garante(
        _linha_mes(r, m3).get("ok") is False, "Limpar: o mês do erro de banco não saiu com erro"
    )
    _garante(_linha_mes(r, m4).get("ok") is True, "Limpar: o mês seguinte ao erro de banco falhou")
    linhas = _no_banco("SELECT id FROM calendar_events WHERE google_event_id = :g", g=novo)
    _garante(linhas, "Limpar: o mês seguinte não importou o item novo")
    estado["eventos"][linhas[0][0]] = novo
    _garante(_marca(cand4) is not None, "Limpar: o mês seguinte não marcou o candidato")


def c14_edicao() -> None:
    mes = _mes_novo()
    estado["mes14"] = mes
    ev = _evento("catorze-ed", mes)
    _venda(ev)
    _marcar_pelo_ciclo(ev)
    _precisa_marcado(ev)
    gid = _gid(ev)
    m = google.marco()
    c = _cliente(estado["superadmin"])
    titulo = _no_banco("SELECT title FROM calendar_events WHERE id = :i", i=ev)[0][0]
    r = c.patch(
        ROTAS["basico"].format(id=ev),
        json=_payload_basico(
            ev, title=f"{titulo} EDITADO", date=date(mes[0], mes[1], 18).isoformat()
        ),
    )
    _garante(r.status_code == 200, f"edição do marcado → {r.status_code}: {_erro(r)}")
    _garante(
        MSG_FALHA_SYNC_EDICAO not in (r.get_json().get("warnings") or []),
        "a edição do marcado avisou falha de sincronização",
    )
    for tipo in ("SHOW", "CORP"):
        r = c.patch(ROTAS["basico"].format(id=ev), json=_payload_basico(ev, event_type=tipo))
        _garante(
            r.status_code == 200,
            f"troca de tipo para {tipo} → {r.status_code} (nunca 409): {_erro(r)}",
        )
        _garante(
            MSG_FALHA_SYNC_EDICAO not in (r.get_json().get("warnings") or []),
            f"troca para {tipo}: aviso de falha de sincronização",
        )
    _garante(google.contar("patch", {gid}, m) == 0, "a edição do marcado escreveu no Google")
    _garante(_marca(ev) is not None, "a edição tirou a marca")


def _sync_de_ausente(ev: int, nome: str) -> None:
    antes = _foto(ev)
    _esperar_threads()
    n = len(_emails)
    r = _cliente(estado["superadmin"]).post(ROTAS["sync"].format(id=ev))
    _garante(
        r.status_code == 409,
        f"{nome}: Sincronizar de evento ausente → {r.status_code} (deve ser 409)",
    )
    _garante(
        _erro(r).get("message") == MSG_SYNC_AUSENTE, f"{nome}: mensagem {_erro(r).get('message')!r}"
    )
    _esperar_threads()
    _garante(_foto(ev) == antes, f"{nome}: o Sincronizar alterou título, datas ou escala")
    _garante(len(_emails) == n, f"{nome}: o Sincronizar mandou e-mail")


def c14_sync_marcado() -> None:
    mes = estado.get("mes14") or _mes_novo()
    ev = _evento("catorze-sm", mes, dia=20)
    _venda(ev)
    _escalar(ev, estado["t"])
    _marcar_pelo_ciclo(ev)
    _precisa_marcado(ev)
    _sync_de_ausente(ev, "marcado")
    _garante(_marca(ev) is not None, "o Sincronizar de evento ausente tirou a marca")


def c14_sync_nao_marcado() -> None:
    mes = _mes_novo()
    for modo in ("cancelado_completo", "cancelado_minimo"):
        ev = _evento(f"catorze-nm-{modo}", mes, dia=5 if modo == "cancelado_completo" else 6)
        _escalar(ev, estado["t2"])
        google.apagar(_gid(ev), modo)
        _sync_de_ausente(ev, f"não marcado, resposta {modo}")


def c15_cancelado_virtual() -> None:
    mes = _mes_novo()
    canc = _evento("quinze-canc", mes, dia=3)
    _venda(canc)
    _no_banco_escrever(
        "UPDATE calendar_events SET cancelled_at = :a WHERE id = :i", a=now_sp(), i=canc
    )
    gid_v = f"{GID}-virtual-{uuid.uuid4().hex[:6]}"
    with app.app_context():
        ev = CalendarEvent(
            google_event_id=gid_v,
            title="V303 VIRTUAL",
            event_type="VIRTUAL",
            start_at=datetime(mes[0], mes[1], 4, 19),
            end_at=datetime(mes[0], mes[1], 4, 20),
            description=MARCADOR,
        )
        db.session.add(ev)
        db.session.commit()
        virt = ev.id
        estado["eventos"][virt] = gid_v
    google.registrar(
        _item(
            gid_v, "V303 VIRTUAL", datetime(mes[0], mes[1], 4, 19), datetime(mes[0], mes[1], 4, 20)
        )
    )
    google.apagar(_gid(canc))
    google.apagar(gid_v)
    m = google.marco()
    _ciclo()
    for ev, nome in ((canc, "cancelado"), (virt, "venda virtual")):
        _garante(_existe(ev), f"{nome}: apagado")
        _garante(_marca(ev) is None, f"{nome}: marcado")
    _garante(
        google.contar("get", {_gid(canc), gid_v}, m) == 0, "cancelado ou venda virtual consultados"
    )


# ── B2 — mudou de data não é sumiço ────────────────────────────────────────────────────────────
def c8_mudou_de_data() -> None:
    ma, mb = _mes_novo(), _mes_novo()
    mp = _mes_passado()
    t = estado["t"]
    a = _evento("oito-a", ma, dia=5)
    _venda(a)
    _comprovante(a)
    _escalar(a, t)
    google.mover(_gid(a), datetime(mb[0], mb[1], 14, 19), datetime(mb[0], mb[1], 14, 22))
    b = _evento("oito-b", ma, dia=6)
    _venda(b)
    google.mover(_gid(b), datetime(mp[0], mp[1], 14, 19), datetime(mp[0], mp[1], 14, 22))
    c = _evento("oito-c", ma, dia=7)
    _venda(c)
    google.mover(
        _gid(c),
        datetime(MES_ALEM[0], MES_ALEM[1], 14, 19),
        datetime(MES_ALEM[0], MES_ALEM[1], 14, 22),
    )
    _ciclo()
    for ev, alvo, nome in (
        (a, mb, "mês posterior"),
        (b, mp, "mês passado"),
        (c, MES_ALEM, "fora do horizonte"),
    ):
        _garante(
            _existe(ev),
            f"{nome}: o evento movido foi apagado (na main, apagado e reimportado com outro id)",
        )
        inicio = _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=ev)[0][0]
        _garante((inicio.year, inicio.month) == alvo, f"{nome}: a data nova não chegou ({inicio})")
        _garante(_marca(ev) is None, f"{nome}: mudança de data virou sumiço")
        _garante(not _avisos(ev), f"{nome}: mudança de data avisou no sino")
        venda = _no_banco("SELECT sale_value FROM calendar_events WHERE id = :i", i=ev)[0][0]
        _garante(venda == Decimal("1500.00"), f"{nome}: a venda mudou")

    md = _mes_novo()
    d1 = _evento("oito-d1", md, dia=5, titulo="(CORP) V303 OITO-D1 + Coordenador")
    d2 = _evento("oito-d2", md, dia=12, dia_inteiro=True)
    d3 = _evento("oito-d3", md, dia=13, descricao=None)
    for ev in (d1, d2, d3):
        google.fora_da_lista.add(_gid(ev))
    antes = {ev: _foto(ev) for ev in (d1, d2, d3)}
    _esperar_threads()
    n = len(_emails)
    _ciclo()
    _ciclo()
    r = _limpar_fantasmas(estado["superadmin"])
    _esperar_threads()
    for ev in (d1, d2, d3):
        _garante(_existe(ev), f"presente fora da lista {ev} foi apagado")
        _garante(_marca(ev) is None, f"presente fora da lista {ev} foi marcado")
        _garante(_foto(ev) == antes[ev], f"presente sem mudança {ev} foi alterado")
        linhas = _auditoria("presente_fora_da_lista", ev)
        _garante(
            len(linhas) == 1,
            f"{len(linhas)} linha(s) `presente_fora_da_lista` para {ev} (esperado 1)",
        )
    _garante(len(_emails) == n, "presente sem mudança mandou e-mail")
    _garante(_linha_mes(r, md).get("movidos", 0) == 0, "presente sem mudança contou como movido")


def c9_reaparece() -> None:
    mes = _mes_novo()
    n_dest = _destinatarios()
    a = _evento("nove-a", mes, dia=3)
    _venda(a)
    # Elenco com convite aceito: sem ninguém escalado, "a desmarca não manda e-mail" não teria
    # como falhar (converge da 303).
    _escalar(a, estado["t"])
    _marcar_pelo_ciclo(a)
    _precisa_marcado(a)
    google.restaurar(_gid(a))
    _esperar_threads()
    n = len(_emails)
    r = _limpar_fantasmas(estado["superadmin"])
    _esperar_threads()
    _garante(_marca(a) is None, "(a) a marca não saiu quando o evento voltou à lista do mês")
    _garante(not _avisos(a, so_nao_lidos=True), "(a) o aviso não ficou lido")
    _garante(
        any("Reapareceu no Google Agenda" in m for m in _historico(a)), "(a) histórico sem o motivo"
    )
    _garante(_auditoria("google_reapareceu", a), "(a) sem auditoria `google_reapareceu`")
    _garante(_linha_mes(r, mes).get("desmarcados") == 1, f"(a) desmarcados = {_linha_mes(r, mes)}")
    _garante(len(_emails) == n, "(a) a desmarca sem mudança mandou e-mail")

    mp = _mes_passado()
    b = _evento("nove-b", mp, dia=20)
    _venda(b)
    google.apagar(_gid(b))
    _limpar_fantasmas(estado["superadmin"])
    _precisa_marcado(b)
    google.restaurar(_gid(b))
    _ciclo()
    _garante(_marca(b) is None, "(b) marcado de mês passado não foi achado pelo próprio id")

    c_ev = _evento("nove-c", mes, dia=12)
    _venda(c_ev)
    _marcar_pelo_ciclo(c_ev)
    _precisa_marcado(c_ev)
    titulo_google = google.itens[_gid(c_ev)]["summary"]
    rr = _cliente(estado["superadmin"]).patch(
        ROTAS["basico"].format(id=c_ev),
        json=_payload_basico(c_ev, title=f"{titulo_google} EDITADO"),
    )
    _garante(rr.status_code == 200, f"(c) edição do marcado → {rr.status_code}")
    mc = _mes_novo()
    google.mover(_gid(c_ev), datetime(mc[0], mc[1], 9, 18), datetime(mc[0], mc[1], 9, 21))
    google.restaurar(_gid(c_ev))
    _ciclo()
    _garante(_existe(c_ev), "(c) o evento que voltou em outro mês sumiu")
    titulo, inicio = _no_banco("SELECT title, start_at FROM calendar_events WHERE id = :i", i=c_ev)[
        0
    ]
    _garante(_marca(c_ev) is None, "(c) a marca não saiu")
    _garante((inicio.year, inicio.month) == mc, f"(c) a data do Google não chegou ({inicio})")
    _garante(titulo == titulo_google, f"(c) não valeu o Google: título {titulo!r}")

    d = _evento("nove-d", mes, dia=14)
    _venda(d)
    _escalar(d, estado["t"])
    _marcar_pelo_ciclo(d)
    _precisa_marcado(d)
    google.restaurar(_gid(d))
    _esperar_threads()
    n = len(_emails)
    rs = _cliente(estado["comercial"]).post(ROTAS["sync"].format(id=d))
    _esperar_threads()
    _garante(rs.status_code == 200, f"(d) Sincronizar de marcado que voltou → {rs.status_code}")
    _garante(len(_emails) == n, "(d) o Sincronizar do marcado que voltou sem mudança mandou e-mail")
    _garante(_marca(d) is None, "(d) o Sincronizar não tirou a marca")
    _garante(not _avisos(d, so_nao_lidos=True), "(d) o aviso não ficou lido")
    atores = _no_banco(
        "SELECT actor_name FROM event_logs WHERE event_id = :i AND message LIKE "
        "'Reapareceu no Google Agenda%'",
        i=d,
    )
    _garante(
        any(estado["comercial_nome"] == x[0] for x in atores), "(d) o histórico não diz quem clicou"
    )

    google.apagar(_gid(a))
    _ciclo()
    _garante(_marca(a) is not None, "(e) o segundo sumiço não marcou")
    _garante(
        len(_avisos(a)) == 2 * n_dest,
        f"(e) {len(_avisos(a))} aviso(s) — esperado um novo por destinatário",
    )


def c13d_falha_na_reconferencia() -> None:
    # `x` mora num mês que o ciclo nunca lista: num mês listado, a lista o traria de volta e a
    # limpeza tiraria a marca por ela (cenário 9a) — e o cenário deixaria de medir a reconferência.
    # Por isso é marcado pelo "Limpar eventos fantasma", que visita os meses passados.
    x = _evento("trezed-x", _mes_passado(), dia=6)
    _venda(x)
    google.apagar(_gid(x))
    _limpar_fantasmas(estado["superadmin"])
    _precisa_marcado(x)
    google.restaurar(_gid(x))
    md = _mes_novo()
    y = _evento("trezed-y", md, dia=4)
    _venda(y)
    google.apagar(_gid(y))
    marcados = {
        r[0]
        for r in _no_banco(
            f"SELECT google_event_id FROM calendar_events WHERE {COLUNA} IS "
            "NOT NULL AND cancelled_at IS NULL AND google_event_id LIKE 'v303%'"
        )
    }
    n = len(google.consumidas)
    google.armar("5xx")  # a primeira consulta do ciclo
    _ciclo()
    _garante(len(google.consumidas) > n, "nenhuma consulta consumiu a falha")
    _garante(
        google.consumidas[n][1] in marcados,
        "a primeira consulta do ciclo não foi a da reconferência dos marcados (História 5)",
    )
    _garante(_marca(x) is not None, "a falha na reconferência tirou a marca")
    _garante(_marca(y) is not None, "depois da falha na reconferência os meses não limparam")


# ── B3 — a faixa ───────────────────────────────────────────────────────────────────────────────
def c17_quem_nao_ve() -> None:
    for papel in ("figurino", "financeiro", "revendedor"):
        r = _cliente(estado[papel]).get(ROTAS["faixa"])
        _garante(r.status_code == 200, f"{papel}: faixa → {r.status_code} (nunca 403)")
        corpo = r.get_json()
        _garante(
            corpo == {"pode_ver": False, "total": 0, "limit": 100, "items": []},
            f"{papel} viu a faixa: {corpo}",
        )


def _isolar_faixa() -> None:
    """Os blocos anteriores deixam marcados que a faixa contaria: voltam ao Google e perdem a marca."""
    for (gid,) in _no_banco(
        "SELECT google_event_id FROM calendar_events WHERE google_event_id LIKE 'v303%'"
    ):
        if gid in google.itens:
            google.restaurar(gid)
    _no_banco_escrever(
        f"UPDATE calendar_events SET {COLUNA} = NULL WHERE google_event_id LIKE 'v303%'"
    )


def c17_faixa() -> None:
    _isolar_faixa()
    mes = _mes_novo()
    f1 = _evento("dezessete-f1", mes, dia=5)
    _venda(f1)
    _marcar_pelo_ciclo(f1)
    _precisa_marcado(f1)
    for papel in ("superadmin", "comercial"):
        corpo = _faixa(estado[papel])
        _garante(corpo.get("pode_ver") is True and corpo.get("total") == 1, f"{papel}: {corpo}")
        _garante(
            set(corpo["items"][0]) == {"id", "title", "start_at"},
            f"{papel}: item {corpo['items'][0]}",
        )
        _garante(corpo["items"][0]["id"] == f1, f"{papel}: item errado")
    c = _cliente(estado["superadmin"])
    c.post(ROTAS["impersonate"], json={"role": "FIGURINO"})
    _garante(
        c.get(ROTAS["faixa"]).get_json().get("pode_ver") is False, "Ver como FIGURINO viu a faixa"
    )
    c.delete(ROTAS["impersonate"])
    c.post(ROTAS["impersonate"], json={"role": "COMERCIAL"})
    _garante(
        c.get(ROTAS["faixa"]).get_json().get("pode_ver") is True,
        "Ver como COMERCIAL não viu a faixa",
    )
    c.delete(ROTAS["impersonate"])

    f2 = _evento("dezessete-f2", mes, dia=6)
    _venda(f2)
    _marcar_pelo_ciclo(f2)
    _no_banco_escrever(
        "UPDATE calendar_events SET cancelled_at = :a WHERE id = :i", a=now_sp(), i=f2
    )
    corpo = _faixa(estado["superadmin"])
    _garante(
        corpo["total"] == 1 and all(it["id"] != f2 for it in corpo["items"]),
        "a faixa contou o cancelado",
    )
    det = _cliente(estado["superadmin"]).get(ROTAS["detalhe"].format(id=f2)).get_json()["event"]
    _garante(
        det.get("situacao") == "cancelado", f"marcado e cancelado: situacao {det.get('situacao')!r}"
    )
    _garante(det.get("sumiu_do_google") is None, "a marca apareceu em evento cancelado")
    _garante(det.get("google_html_link") is None, "evento cancelado com link do Google")

    google.restaurar(_gid(f1))
    _ciclo()
    _garante(
        _faixa(estado["superadmin"])["total"] == 0,
        "resolvido por reaparecimento, a faixa continuou",
    )

    f3 = _evento("dezessete-f3", _mes_novo(), dia=8)
    _venda(f3)
    _marcar_pelo_ciclo(f3)
    mp = _mes_passado()
    f4 = _evento("dezessete-f4", mp, dia=25)
    _venda(f4)
    google.apagar(_gid(f4))
    _limpar_fantasmas(estado["superadmin"])
    corpo = _faixa(estado["superadmin"])
    _garante(corpo["total"] == 2, f"dois marcados: total {corpo['total']}")
    _garante(
        [it["id"] for it in corpo["items"]] == [f3, f4], "a ordem não é futuro antes de passado"
    )
    try:
        from app.calendar.sumico_ops import (
            faixa_sumidos,  # noqa: PLC0415 — import tardio de propósito
        )
    except ImportError as exc:
        raise Bloqueado("o núcleo da faixa ainda não existe") from exc
    with app.app_context():
        res = faixa_sumidos(limite=1)
    _garante(
        res["total"] == 2 and len(res["items"]) == 1 and res["items"][0]["id"] == f3,
        f"limite 1: {res}",
    )


# ── B4 — devolver ao Google ────────────────────────────────────────────────────────────────────
class _TravaDesligada:
    """Desliga a trava NO PROCESSO (nunca por variável de ambiente) e a devolve sempre."""

    def __enter__(self):
        app.config[TRAVA] = False

    def __exit__(self, *_exc):
        app.config[TRAVA] = True
        return False


def _marcado_novo(nome: str, mes: tuple[int, int], *, dia: int, **kw) -> int:
    ev = _evento(nome, mes, dia=dia, **kw)
    _venda(ev)
    _marcar_pelo_ciclo(ev)
    _precisa_marcado(ev)
    return ev


def _devolver(email: str, ev: int):
    with _TravaDesligada():
        return _cliente(email).post(ROTAS["devolver"].format(id=ev))


def c10a_travado() -> None:
    mes = estado.setdefault("mes10", _mes_novo())
    ev = _marcado_novo("deza", mes, dia=2)
    gid = _gid(ev)
    m = google.marco()
    r = _cliente(estado["superadmin"]).post(ROTAS["devolver"].format(id=ev))
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "google_travado",
        f"trava ligada: {r.status_code} {_erro(r)} (deve falhar com 409 google_travado)",
    )
    _garante(google.marco() == m, "com a trava ligada a devolução chamou o Google")
    _garante(_marca(ev) is not None, "a marca saiu")
    _garante(
        _no_banco("SELECT google_event_id FROM calendar_events WHERE id = :i", i=ev)[0][0] == gid,
        "o id do Google mudou",
    )


def c10_devolver() -> None:
    mes = estado.setdefault("mes10", _mes_novo())
    t = estado["t"]
    ev = _evento("dez", mes, dia=4)
    _venda(ev)
    _comprovante(ev)
    _contrato(ev)
    _escalar(ev, t)
    _marcar_pelo_ciclo(ev)
    _precisa_marcado(ev)
    estado["e10"] = ev
    c = _cliente(estado["superadmin"])
    titulo = _no_banco("SELECT title FROM calendar_events WHERE id = :i", i=ev)[0][0]
    novo_dia = date(mes[0], mes[1], 21)
    r = c.patch(
        ROTAS["basico"].format(id=ev),
        json=_payload_basico(ev, title=f"{titulo} + V303 EXTRA", date=novo_dia.isoformat()),
    )
    _garante(r.status_code == 200, f"edição antes de devolver → {r.status_code}")
    _esperar_threads()
    n_emails, n_ins = len(_emails), len(google.inseridos)
    r = _devolver(estado["superadmin"], ev)
    _garante(r.status_code == 200, f"devolver → {r.status_code}: {_erro(r)}")
    _garante(
        (r.get_json().get("devolucao_google") or {}).get("resultado") == "recriado",
        "resultado ≠ recriado",
    )
    _garante(
        len(google.inseridos) == n_ins + 1,
        f"{len(google.inseridos) - n_ins} criação(ões) no Google",
    )
    gid_novo, corpo = google.inseridos[-1]
    t_db, ini, loc, desc, gid_db, fonte = _no_banco(
        "SELECT title, start_at, location, description, google_event_id, source FROM calendar_events "
        "WHERE id = :i",
        i=ev,
    )[0]
    _garante(corpo.get("summary") == t_db, f"título no Google {corpo.get('summary')!r} ≠ {t_db!r}")
    _garante(
        (corpo.get("start") or {}).get("dateTime", "").startswith(novo_dia.isoformat()),
        f"data no Google {corpo.get('start')}",
    )
    _garante((corpo.get("location") or "") == (loc or ""), "local diferente")
    _garante((corpo.get("description") or "") == (desc or ""), "descrição diferente")
    _garante("attendees" not in corpo, "a devolução convidou gente")
    _garante(gid_db == gid_novo, "o evento não passou a apontar para o id novo")
    estado["eventos"][ev] = gid_novo
    _garante(_marca(ev) is None, "a marca não saiu")
    autores = _no_banco(
        "SELECT actor_name, message FROM event_logs WHERE event_id = :i AND message LIKE "
        "'Devolveu o evento ao Google Agenda%'",
        i=ev,
    )
    _garante(
        autores and autores[-1][0] == estado["superadmin_nome"], "o histórico não diz quem devolveu"
    )
    _garante(
        FRASE_ELENCO not in autores[-1][1], "sem vaga fora do título, mas o elenco mudou de dono"
    )
    _garante(fonte != "platform", "sem vaga fora do título, mas a origem mudou")
    _garante(_auditoria("google_returned", ev), "sem auditoria `google_returned`")
    _garante(not _avisos(ev, so_nao_lidos=True), "o aviso não ficou lido")
    _garante(
        _no_banco("SELECT sale_value FROM calendar_events WHERE id = :i", i=ev)[0][0]
        == Decimal("1500.00"),
        "a venda mudou",
    )
    _garante(
        _no_banco("SELECT COUNT(*) FROM event_payments WHERE event_id = :i", i=ev)[0][0] == 1,
        "comprovante",
    )
    _garante(
        _no_banco("SELECT COUNT(*) FROM event_contracts WHERE event_id = :i", i=ev)[0][0] == 1,
        "contrato",
    )
    _garante(
        _no_banco(
            "SELECT COUNT(*) FROM event_roles WHERE event_id = :i AND talent_id = :t", i=ev, t=t
        )[0][0]
        == 1,
        "escala",
    )
    _garante(
        all(it["id"] != ev for it in _faixa(estado["superadmin"])["items"]),
        "a faixa ainda conta o evento",
    )
    _esperar_threads()
    _garante(len(_emails) == n_emails, "a devolução mandou e-mail")


def c10b_dia_inteiro() -> None:
    ev = _marcado_novo("dezb", estado.setdefault("mes10", _mes_novo()), dia=6, dia_inteiro=True)
    r = _devolver(estado["superadmin"], ev)
    _garante(r.status_code == 200, f"devolver dia inteiro → {r.status_code}: {_erro(r)}")
    _, corpo = google.inseridos[-1]
    _garante(
        "date" in (corpo.get("start") or {}) and "dateTime" not in (corpo.get("start") or {}),
        f"dia inteiro voltou como bloco de horas: {corpo.get('start')}",
    )
    estado["eventos"][ev] = google.inseridos[-1][0]


def c10c_ja_voltou() -> None:
    mes = estado.setdefault("mes10", _mes_novo())
    ev = _marcado_novo("dezc", mes, dia=8)
    google.restaurar(_gid(ev))
    n_ins = len(google.inseridos)
    r = _devolver(estado["superadmin"], ev)
    _garante(r.status_code == 200, f"devolver o que já voltou → {r.status_code}: {_erro(r)}")
    _garante(
        (r.get_json().get("devolucao_google") or {}).get("resultado") == "reapareceu",
        "resultado ≠ reapareceu",
    )
    _garante(len(google.inseridos) == n_ins, "criou outro evento no Google")
    _garante(_marca(ev) is None, "a marca não saiu")

    ev2 = _marcado_novo("dezc2", mes, dia=9)
    c = _cliente(estado["superadmin"])
    novo_dia = date(mes[0], mes[1], 24)
    rr = c.patch(
        ROTAS["basico"].format(id=ev2), json=_payload_basico(ev2, date=novo_dia.isoformat())
    )
    _garante(rr.status_code == 200, f"edição → {rr.status_code}")
    rr = c.post(
        ROTAS["roles"].format(id=ev2),
        json={"character_name": "V303 FORA C", "talent_id": estado["t2"]},
    )
    _garante(rr.status_code == 200, f"vaga fora do título → {rr.status_code}")
    google.restaurar(_gid(ev2))
    n_patch = len(google.patches)
    r = _devolver(estado["superadmin"], ev2)
    _garante(r.status_code == 200, f"devolver editado que já voltou → {r.status_code}: {_erro(r)}")
    novos = google.patches[n_patch:]
    _garante(
        len(novos) == 1 and novos[0][0] == _gid(ev2), f"{len(novos)} regravação(ões) no id velho"
    )
    _garante(
        (novos[0][1].get("start") or {}).get("dateTime", "").startswith(novo_dia.isoformat()),
        "o Google não recebeu a data do sistema",
    )
    _esperar_threads()
    n = len([e for e in _emails if PREFIX in e["to"]])
    _ciclo()
    _esperar_threads()
    _garante(
        _no_banco(
            "SELECT COUNT(*) FROM event_roles WHERE event_id = :i AND character_name = 'V303 FORA C'",
            i=ev2,
        )[0][0]
        == 1,
        "a vaga fora do título foi apagada depois da devolução",
    )
    _garante(
        len([e for e in _emails if PREFIX in e["to"]]) == n, "e-mail ao elenco depois da devolução"
    )


def c10d_google_recusa() -> None:
    ev = _marcado_novo("dezd", estado.setdefault("mes10", _mes_novo()), dia=10)
    gid = _gid(ev)
    google.falha_insert = True
    r = _devolver(estado["superadmin"], ev)
    google.falha_insert = False
    _garante(
        r.status_code == 502 and _erro(r).get("codigo") == "google_recusou",
        f"{r.status_code} {_erro(r)} (deve falhar com 502 google_recusou)",
    )
    _garante(
        _erro(r).get("message") == MSG_RECUSOU_CRIACAO, f"mensagem {_erro(r).get('message')!r}"
    )
    _garante(_marca(ev) is not None, "a marca saiu")
    _garante(
        _no_banco("SELECT google_event_id FROM calendar_events WHERE id = :i", i=ev)[0][0] == gid,
        "o id mudou",
    )
    _garante(_auditoria("google_return_failed", ev), "sem auditoria `google_return_failed`")


def c10e_inconclusivo() -> None:
    mes = estado.setdefault("mes10", _mes_novo())
    for tipo, codigo, dia in (
        ("5xx", "google_inconclusivo", 11),
        ("refresh_exec", "google_desconectado", 12),
    ):
        ev = _marcado_novo(f"deze-{tipo}", mes, dia=dia)
        gid = _gid(ev)
        google.por_id[gid] = tipo
        m, n_ins = google.marco(), len(google.inseridos)
        r = _devolver(estado["superadmin"], ev)
        google.por_id.pop(gid, None)
        _garante(
            r.status_code == 502 and _erro(r).get("codigo") == codigo,
            f"{tipo}: {r.status_code} {_erro(r)} (deve falhar com 502 {codigo})",
        )
        _garante(google.contar("get", {gid}, m) == 1, f"{tipo}: consultas ao id velho")
        _garante(len(google.inseridos) == n_ins, f"{tipo}: criou mesmo sem confirmar a ausência")
        _garante(_marca(ev) is not None, f"{tipo}: a marca saiu")


def c10f_segundo_clique() -> None:
    ev = estado.get("e10")
    if ev is None or _marca(ev) is not None:
        raise Bloqueado("depende do cenário 10 (a primeira devolução)")
    n_ins = len(google.inseridos)
    r = _devolver(estado["superadmin"], ev)
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "nao_marcado",
        f"segundo clique: {r.status_code} {_erro(r)} (deve falhar com 409 nao_marcado)",
    )
    _garante(len(google.inseridos) == n_ins, "o segundo clique criou outro evento")


def c10g_sync_depois() -> None:
    mes = estado.setdefault("mes10", _mes_novo())
    ev = _marcado_novo("dezg", mes, dia=14)
    gid_velho = _gid(ev)
    rr = _cliente(estado["superadmin"]).post(
        ROTAS["roles"].format(id=ev),
        json={"character_name": "V303 FORA G", "talent_id": estado["t2"]},
    )
    _garante(rr.status_code == 200, f"vaga fora do título → {rr.status_code}")
    r = _devolver(estado["superadmin"], ev)
    _garante(r.status_code == 200, f"devolver → {r.status_code}: {_erro(r)}")
    gid_novo = _no_banco("SELECT google_event_id FROM calendar_events WHERE id = :i", i=ev)[0][0]
    estado["eventos"][ev] = gid_novo
    _esperar_threads()
    n = len([e for e in _emails if PREFIX in e["to"]])
    _ciclo()
    _esperar_threads()
    _garante(
        _no_banco("SELECT COUNT(*) FROM calendar_events WHERE google_event_id = :g", g=gid_novo)[0][
            0
        ]
        == 1,
        "o sync seguinte duplicou o evento",
    )
    _garante(
        not _no_banco("SELECT 1 FROM calendar_events WHERE google_event_id = :g", g=gid_velho),
        "sobrou linha com o id velho",
    )
    _garante(_marca(ev) is None, "o sync seguinte remarcou")
    _garante(
        _no_banco(
            "SELECT COUNT(*) FROM event_roles WHERE event_id = :i AND character_name = 'V303 FORA G'",
            i=ev,
        )[0][0]
        == 1,
        "o sync seguinte apagou a vaga fora do título (FR-044)",
    )
    _garante(
        len([e for e in _emails if PREFIX in e["to"]]) == n, "e-mail de remoção depois da devolução"
    )
    fonte = _no_banco("SELECT source FROM calendar_events WHERE id = :i", i=ev)[0][0]
    _garante(fonte == "platform", f"origem {fonte!r}: o elenco não passou a ser do sistema")
    devolveu = _no_banco(
        "SELECT message FROM event_logs WHERE event_id = :i AND message LIKE "
        "'Devolveu o evento ao Google Agenda%' ORDER BY id DESC LIMIT 1",
        i=ev,
    )
    _garante(
        devolveu and FRASE_ELENCO in devolveu[0][0],
        "o histórico não diz que o elenco passou ao sistema",
    )


def c10h_ensaio() -> None:
    ev = _marcado_novo("dezh", estado.setdefault("mes10", _mes_novo()), dia=16)
    ens = _ensaio_filho(ev, (2044, 3))
    n_ins = len(google.inseridos)
    r = _devolver(estado["superadmin"], ev)
    _garante(r.status_code == 200, f"devolver com ensaio → {r.status_code}: {_erro(r)}")
    _garante(len(google.inseridos) == n_ins + 1, "o ensaio foi recriado junto")
    estado["eventos"][ev] = google.inseridos[-1][0]
    pai = _no_banco("SELECT parent_event_id FROM calendar_events WHERE id = :i", i=ens)
    _garante(pai and pai[0][0] == ev, "o ensaio perdeu o vínculo")


def c10i_recusas() -> None:
    mes = estado.setdefault("mes10", _mes_novo())
    vivo = _evento("dezi-vivo", mes, dia=17)
    canc = _evento("dezi-canc", mes, dia=18)
    _no_banco_escrever(
        "UPDATE calendar_events SET cancelled_at = :a WHERE id = :i", a=now_sp(), i=canc
    )
    m = google.marco()
    for ev, codigo, status in (
        (vivo, "nao_marcado", 409),
        (canc, "cancelado", 409),
        (999_999_999, None, 404),
    ):
        r = _devolver(estado["superadmin"], ev)
        _garante(
            r.status_code == status, f"evento {ev}: {r.status_code} (deve falhar com {status})"
        )
        if codigo:
            _garante(
                _erro(r).get("codigo") == codigo, f"evento {ev}: código {_erro(r).get('codigo')!r}"
            )
    _garante(google.marco() == m, "uma recusa chamou o Google")


def c10i_sem_data() -> None:
    ev = _marcado_novo("dezi-sd", estado.setdefault("mes10", _mes_novo()), dia=19)
    _no_banco_escrever(
        "UPDATE calendar_events SET end_at = start_at - interval '1 hour' WHERE id = :i", i=ev
    )
    m = google.marco()
    r = _devolver(estado["superadmin"], ev)
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "sem_data",
        f"{r.status_code} {_erro(r)} (deve falhar com 409 sem_data)",
    )
    _garante(google.marco() == m, "a recusa chamou o Google")


def c11_comercial() -> None:
    ev = _evento("onze", estado.setdefault("mes10", _mes_novo()), dia=20)
    m = google.marco()
    r = _devolver(estado["comercial"], ev)
    _garante(r.status_code == 403, f"COMERCIAL devolvendo → {r.status_code} (deve falhar com 403)")
    _garante(google.marco() == m, "o COMERCIAL chegou ao Google")


def c11_superadmin_gate() -> None:
    ev = _evento("onze-sa", estado.setdefault("mes10", _mes_novo()), dia=22)
    m = google.marco()
    r = _devolver(estado["superadmin"], ev)
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "nao_marcado",
        f"Superadmin em evento não marcado → {r.status_code} {_erro(r)} (nunca 403)",
    )
    _garante(google.marco() == m, "a recusa chamou o Google")


def c12_nao_cancela() -> None:
    mes = _mes_novo()
    ev = _marcado_novo("doze", mes, dia=3)
    n_dest = _destinatarios()
    c = _cliente(estado["superadmin"])
    m = google.marco()
    r = c.post(ROTAS["cancelar"].format(id=ev), json={"motivo": "verify 303"})
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "sumiu_do_google",
        f"cancelar marcado → {r.status_code} {_erro(r)} (deve falhar com 409)",
    )
    _garante(_erro(r).get("message") == MSG_MARCADO, f"mensagem {_erro(r).get('message')!r}")
    r = c.delete(ROTAS["excluir"].format(id=ev))
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "sumiu_do_google",
        f"excluir marcado → {r.status_code} {_erro(r)} (deve falhar com 409)",
    )
    r = c.post(ROTAS["excluir_jinja"].format(id=ev))
    _garante(r.status_code in (302, 303), f"rota antiga → {r.status_code}")
    _garante(_existe(ev), "a rota antiga de exclusão apagou o evento marcado")
    lider = _evento("doze-lider", mes, dia=5)
    sat = _evento("doze-sat", mes, dia=6)
    _grupo(lider, sat)
    google.apagar(_gid(lider))
    google.apagar(_gid(sat))
    _ciclo()
    _precisa_marcado(sat)
    r = c.delete(ROTAS["excluir"].format(id=sat))
    _garante(
        r.status_code == 409 and _erro(r).get("codigo") == "sumiu_do_google",
        f"excluir satélite marcado → {r.status_code} {_erro(r)}",
    )
    for alvo in (ev, sat):
        _garante(
            _existe(alvo) and _marca(alvo) is not None, f"evento {alvo}: registro ou marca sumiram"
        )
        _garante(len(_avisos(alvo)) == n_dest, f"evento {alvo}: avisos mudaram")
    _garante(google.contar("delete", None, m) == 0, "algo foi apagado no Google")
    rc = _cliente(estado["comercial"]).post(
        ROTAS["solicitar"].format(id=ev), json={"motivo": "a cliente desistiu (verify 303)"}
    )
    _garante(rc.status_code == 200, f"solicitar exclusão de marcado → {rc.status_code}")
    _garante(_marca(ev) is not None, "a solicitação tirou a marca")
    det = c.get(ROTAS["detalhe"].format(id=ev)).get_json()["event"]
    _garante(det.get("situacao") == "sumiu_do_google", f"situacao {det.get('situacao')!r}")
    controle = _evento("doze-controle", mes, dia=25)
    r = c.delete(ROTAS["excluir"].format(id=controle))
    _garante(r.status_code == 200, f"controle: excluir evento vazio não marcado → {r.status_code}")
    estado["apagados"].add(controle)


# ── B5 — portal ────────────────────────────────────────────────────────────────────────────────
def _no_portal(
    corpo: dict, event_id: int, listas=("pending_invites", "upcoming", "history", "items")
):
    for lista in listas:
        for it in corpo.get(lista) or []:
            if it.get("event_id") == event_id:
                return lista, it
    return None, None


def c24_portal() -> None:
    mes = _mes_novo()
    t24 = _talento("t24")
    fora = _talento("t24fora")
    i = _evento("vinteq-i", mes, dia=5)
    ii = _evento("vinteq-ii", mes, dia=6)
    for ev in (i, ii):
        _venda(ev)
    role_i = _escalar(i, t24, convite="pending")
    _escalar(ii, t24)
    google.apagar(_gid(i))
    google.apagar(_gid(ii))
    _ciclo()
    mp = _mes_passado()
    iii = _evento("vinteq-iii", mp, dia=27)
    _venda(iii)
    _escalar(iii, t24)
    google.apagar(_gid(iii))
    _limpar_fantasmas(estado["superadmin"])
    for ev in (i, ii, iii):
        _precisa_marcado(ev)
    c = _cliente_portal(t24)
    agenda = c.get(ROTAS["portal_agenda"]).get_json()
    historico = c.get(ROTAS["portal_historico"]).get_json()
    for ev, lista_esperada in ((i, "pending_invites"), (ii, "upcoming")):
        lista, it = _no_portal(agenda, ev)
        _garante(lista == lista_esperada, f"evento {ev} em {lista!r}, esperado {lista_esperada!r}")
        _garante(it.get("em_confirmacao") is True, f"evento {ev} sem `em_confirmacao`")
    _, it = _no_portal(historico, iii, ("items",))
    _garante(it is not None and it.get("em_confirmacao") is True, "histórico sem o aviso")
    _garante(
        "Google"
        not in json.dumps(agenda, ensure_ascii=False) + json.dumps(historico, ensure_ascii=False),
        "o portal mostrou o motivo (Google)",
    )
    r = c.post(ROTAS["portal_aceitar"].format(role_id=role_i))
    _garante(r.status_code == 200, f"aceitar convite de evento em confirmação → {r.status_code}")
    cf = _cliente_portal(fora)
    ag_f = cf.get(ROTAS["portal_agenda"]).get_json()
    hi_f = cf.get(ROTAS["portal_historico"]).get_json()
    for ev in (i, ii, iii):
        _garante(
            _no_portal(ag_f, ev)[0] is None and _no_portal(hi_f, ev, ("items",))[0] is None,
            f"o talento de fora viu o evento {ev} (deve falhar)",
        )
    r = _devolver(estado["superadmin"], ii)
    _garante(r.status_code == 200, f"devolver → {r.status_code}")
    estado["eventos"][ii] = _no_banco(
        "SELECT google_event_id FROM calendar_events WHERE id = :i", i=ii
    )[0][0]
    _, it = _no_portal(c.get(ROTAS["portal_agenda"]).get_json(), ii)
    _garante(
        it is not None and not it.get("em_confirmacao"), "depois de devolvido o aviso continuou"
    )


def _evento_quando(nome: str, inicio: datetime, horas: int = 3) -> int:
    gid = f"{GID}-{nome}-{uuid.uuid4().hex[:6]}"
    item = _item(gid, f"(CORP) V303 {nome.upper()}", inicio, inicio + timedelta(hours=horas))
    google.registrar(item)
    with app.app_context():
        cal_routes.sync_events([item])
        ev = CalendarEvent.query.filter_by(google_event_id=gid).one()
        estado["eventos"][ev.id] = gid
        return ev.id


def c24b_avaliacao() -> None:
    t = _talento("t24b")
    agora = now_sp().replace(tzinfo=None, microsecond=0)
    e_b = _evento_quando("vinteqb-b", agora - timedelta(days=2, hours=4))
    e_c = _evento_quando("vinteqb-c", agora - timedelta(days=3, hours=4))
    _escalar(e_b, t)
    _escalar(e_c, t)
    c = _cliente_portal(t)
    pend = c.get(ROTAS["portal_pendentes"]).get_json()
    _garante(e_b in pend["rateable_event_ids"], "o evento terminado não estava avaliável (arranjo)")
    r = c.post(ROTAS["portal_avaliar"].format(id=e_c), json={"score": 5})
    _garante(r.status_code == 200, f"avaliar antes do cancelamento → {r.status_code}")
    _garante(
        e_c in c.get(ROTAS["portal_pendentes"]).get_json()["editable_event_ids"],
        "arranjo: não editável",
    )
    for ev in (e_b, e_c):
        _no_banco_escrever(
            "UPDATE calendar_events SET cancelled_at = :a WHERE id = :i", a=now_sp(), i=ev
        )
    pend = c.get(ROTAS["portal_pendentes"]).get_json()
    _garante(
        e_b not in pend["rateable_event_ids"], "evento cancelado continua 'a avaliar' (deve falhar)"
    )
    _garante(e_c not in pend["editable_event_ids"], "evento cancelado continua editável")
    r = c.post(ROTAS["portal_avaliar"].format(id=e_b), json={"score": 5})
    _garante(
        r.status_code == 400 and _erro(r).get("message") == MSG_AVALIACAO_CANCELADO,
        f"nota de cancelado → {r.status_code} {_erro(r)} (deve falhar com 400)",
    )
    _garante(
        _no_banco("SELECT COUNT(*) FROM event_ratings WHERE event_id = :i", i=e_b)[0][0] == 0,
        "a nota do cancelado foi gravada",
    )


# ── B9 — limpeza ───────────────────────────────────────────────────────────────────────────────
def c41_limpeza() -> None:
    _esperar_threads()
    limpar()
    _garante(
        not _no_banco("SELECT 1 FROM calendar_events WHERE google_event_id LIKE 'v303%'"),
        "sobrou evento",
    )
    _garante(
        not _no_banco("SELECT 1 FROM talents WHERE full_name LIKE :p", p=f"{PREFIX}%"),
        "sobrou talento",
    )
    _garante(
        not _no_banco("SELECT 1 FROM users WHERE email LIKE :p", p=f"{PREFIX}%"), "sobrou usuário"
    )
    ids = list(estado["eventos"].keys()) or [0]
    _garante(
        not _no_banco(
            "SELECT 1 FROM notifications WHERE entity_type = 'calendar_event' AND "
            "entity_id = ANY(:ids)",
            ids=ids,
        ),
        "sobrou aviso",
    )
    _garante(
        not _no_banco("SELECT 1 FROM audit_logs WHERE detail LIKE 'gcal:v303%'"), "sobrou auditoria"
    )
    cache = _no_banco("SELECT calendar_sync_cache FROM site_settings WHERE id = 1")[0][0]
    _garante(cache == estado.get("cache"), "o cache de meses sincronizados não voltou ao original")
    _garante(rede_bloqueada == [], f"chamadas de rede escaparam do dublê: {rede_bloqueada}")
    _garante(app.config.get(TRAVA) is True, "a trava não voltou a True")


# ── semeadura para a conferência de tela ───────────────────────────────────────────────────────
def semear_tela() -> int:
    mes = _mes_novo()
    t = estado["t"]
    futuro = _evento("tela-futuro", mes, dia=10)
    _venda(futuro)
    _comprovante(futuro)
    _contrato(futuro)
    _escalar(futuro, t)
    lider = _evento("tela-lider", mes, dia=12)
    _venda(lider)
    sat = _evento("tela-satelite", mes, dia=13)
    _grupo(lider, sat)
    sol = _evento("tela-solicitado", mes, dia=14)
    _venda(sol)
    inteiro = _evento("tela-dia-inteiro", mes, dia=16, dia_inteiro=True)
    _venda(inteiro)
    tp = _talento("tela-portal")
    p1 = _evento("tela-convite", mes, dia=18)
    _venda(p1)
    _escalar(p1, tp, convite="pending")
    p2 = _evento("tela-aceito", mes, dia=19)
    _venda(p2)
    _escalar(p2, tp)
    for ev in (futuro, lider, sat, sol, inteiro, p1, p2):
        google.apagar(_gid(ev))
    _ciclo()
    mp = _mes_passado()
    passado = _evento("tela-passado", mp, dia=20)
    _venda(passado)
    _escalar(passado, tp)
    google.apagar(_gid(passado))
    _limpar_fantasmas(estado["superadmin"])
    semeados = (futuro, lider, sat, sol, inteiro, p1, p2, passado)
    if any(_marca(ev) is None for ev in semeados):
        print("\nA marca ainda não existe (História 1): nada a conferir na tela. Limpando.")
        limpar()
        return 1
    _cliente(estado["comercial"]).post(
        ROTAS["solicitar"].format(id=sol), json={"motivo": "a cliente desistiu (semeadura de tela)"}
    )
    print("\nSemeado para a conferência de tela (a senha é a constante SENHA deste arquivo):")
    for papel in ("superadmin", "comercial", "figurino"):
        print(f"  {papel:<11} {estado[papel]}")
    print(f"  portal      {PREFIX}tela-portal@manto.local")
    for nome, ev in (
        ("futuro, com tudo", futuro),
        ("líder", lider),
        ("satélite", sat),
        ("com exclusão solicitada", sol),
        ("dia inteiro", inteiro),
        ("convite pendente", p1),
        ("convite aceito", p2),
        ("passado", passado),
    ):
        print(f"  evento {ev:<8} {nome}")
    print("Depois da conferência, com o backend parado: verify_303.py --limpar-tela")
    return 0


# ── main ───────────────────────────────────────────────────────────────────────────────────────
BLOCOS = ["B0", "B1", "B2", "B3", "B4", "B5"]


def _preparar_pessoas() -> None:
    papeis = {
        "superadmin": (RoleName.SUPERADMIN,),
        "comercial": (RoleName.COMERCIAL,),
        "figurino": (RoleName.FIGURINO,),
        "financeiro": (RoleName.FINANCEIRO,),
        "revendedor": (RoleName.REVENDEDOR_EDUCAMANTO,),
    }
    for nome, roles in papeis.items():
        estado[nome] = _usuario(nome, *roles)
    estado["superadmin_nome"] = f"{PREFIX}superadmin"
    estado["comercial_nome"] = f"{PREFIX}comercial"
    estado["figurino_id"] = _no_banco(
        "SELECT id FROM users WHERE email = :e", e=estado["figurino"]
    )[0][0]
    estado["t"] = _talento("t")
    estado["t2"] = _talento("t2")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificação da feature 303")
    parser.add_argument("--ate", choices=BLOCOS, default="B5")
    parser.add_argument("--semear-tela", action="store_true")
    parser.add_argument("--limpar-tela", action="store_true")
    args = parser.parse_args()

    guarda_de_ambiente()
    if args.limpar_tela:
        limpar()
        print("Semeadura de tela apagada.")
        return 0
    limpar()  # restos de uma execução quebrada
    _preparar_pessoas()
    if args.semear_tela:
        return semear_tela()

    ate = BLOCOS.index(args.ate)
    plano: list[tuple[str, str, Callable[[], None]]] = [
        ("B0", "0 (chão)", c0_chao),
        ("B0", "18 (trava por ambiente)", c18_trava),
        ("B1", "1 (com venda, quatro modos; payloads)", c1_com_venda),
        ("B1", "1b (passado; COMERCIAL recusado)", c1b_passado),
        ("B1", "2 (um aviso por destinatário)", c2_um_aviso),
        ("B1", "2b (corrida: uma marca, um aviso)", c2b_corrida),
        (
            "B1",
            "3 (comprovante, inclusive sem valor)",
            lambda: _fica_marcado("3 (comprovante)", "3 (comprovante sem valor)"),
        ),
        ("B1", "4 (contrato)", lambda: _fica_marcado("4")),
        ("B1", "5 (escalado)", lambda: _fica_marcado("5")),
        ("B1", "6 (líder e satélite)", lambda: _fica_marcado("6 (líder)", "6 (satélite)")),
        ("B1", "7 (apagado)", c7_vazios),
        ("B1", "7 (auditoria)", c7_auditoria),
        ("B1", "7a (técnico designado)", c7a_tecnico),
        ("B1", "7b (vazio com ensaio: sync e DELETE)", c7b_ensaio),
        ("B1", "13 (consulta inconclusiva)", c13_inconclusivo),
        ("B1", "13 (a lista inteira falha)", c13_lista_falha),
        ("B1", "13b (o aviso falha)", c13b_aviso_falha),
        ("B1", "13c (erro de banco no meio do mês)", c13c_erro_de_banco),
        ("B1", "14 (edição)", c14_edicao),
        ("B1", "14 (Sincronizar, marcado)", c14_sync_marcado),
        ("B1", "14 (Sincronizar, não marcado)", c14_sync_nao_marcado),
        ("B1", "15 (cancelado e venda virtual)", c15_cancelado_virtual),
        ("B2", "8 (mudou de data; presente sem mudança)", c8_mudou_de_data),
        ("B2", "9 (a marca sai quando o evento volta)", c9_reaparece),
        ("B2", "13d (falha na reconferência)", c13d_falha_na_reconferencia),
        ("B3", "17 (quem não vê)", c17_quem_nao_ve),
        ("B3", "17 (faixa)", c17_faixa),
        ("B4", "10a (trava ligada)", c10a_travado),
        ("B4", "10 (devolver)", c10_devolver),
        ("B4", "10b (dia inteiro)", c10b_dia_inteiro),
        ("B4", "10c (já tinha voltado)", c10c_ja_voltou),
        ("B4", "10d (o Google recusa)", c10d_google_recusa),
        ("B4", "10e (consulta inconclusiva)", c10e_inconclusivo),
        ("B4", "10f (segundo clique)", c10f_segundo_clique),
        ("B4", "10g (sync seguinte)", c10g_sync_depois),
        ("B4", "10h (ensaio-filho)", c10h_ensaio),
        ("B4", "10i (recusas)", c10i_recusas),
        ("B4", "10i (sem data)", c10i_sem_data),
        ("B4", "11 (Comercial recusado)", c11_comercial),
        ("B4", "11 (Superadmin passa o gate)", c11_superadmin_gate),
        ("B4", "12 (cancelar e excluir recusados)", c12_nao_cancela),
        ("B5", "24 (portal)", c24_portal),
        ("B5", "24b (avaliação de cancelado)", c24b_avaliacao),
    ]
    try:
        bloco_atual = None
        for bloco, nome, fn in plano:
            if BLOCOS.index(bloco) > ate:
                continue
            if bloco != bloco_atual:
                print(f"\n{bloco}")
                bloco_atual = bloco
            cenario(bloco, nome, fn)
    finally:
        print("\nB9")
        cenario("B9", "41 (limpeza; nada escapou do dublê)", c41_limpeza)

    print("\nResumo por bloco:")
    for bloco in BLOCOS + ["B9"]:
        linhas = [r for r in resultados if r[0] == bloco]
        if linhas:
            ok = sum(1 for r in linhas if r[2] == "OK")
            bloq = sum(1 for r in linhas if r[2] == "BLOQUEADO")
            print(f"  {bloco}  {ok}/{len(linhas)} OK" + (f" · {bloq} bloqueado(s)" if bloq else ""))
    verbos = {}
    for verbo, _ in google.chamadas:
        verbos[verbo] = verbos.get(verbo, 0) + 1
    print(f"  dublê: {verbos}")
    total_ok = sum(1 for r in resultados if r[2] == "OK")
    print(f"\n{total_ok}/{len(resultados)} OK")
    return 0 if total_ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
