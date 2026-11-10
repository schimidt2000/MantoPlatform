"""manto-avisos — recebe o aviso de pagamento da InfinitePay e só guarda (feature 340).

Todo push na ``main`` troca o ``manto-backend``, e um serviço com disco não troca de container sem
ficar fora (~1 min de 502). A InfinitePay só reenvia o aviso quando recebe 400: o 502 perdia o
pagamento. Este serviço não tem disco, tem healthcheck e só faz deploy quando esta pasta muda — ele
fica no ar enquanto o backend troca. Ele **não decide nada**: confere o segredo, grava o corpo em
``virtual_payment_inbox`` e responde. O backend drena a caixa e decide pela regra da 310
(``app/marketing/virtuais_ops.py``, ``drenar_caixa_de_avisos``).

Não importa ``app/`` de propósito (traria threads, Google e e-mail, e acoplaria este serviço a todo
deploy do backend). Repete três regras curtas do backend, conferidas pelo ``verify_340.py``:

* segredo: o atual, ou o anterior enquanto ``infinitepay_webhook_token_anterior_ate`` não passou
  (``virtuais_ops.token_do_aviso_valido``), em relógio de São Paulo sem fuso;
* teto de 64 KB do corpo, inclusive sem ``Content-Length`` (``app/api/virtuais_webhook.py``);
* IP do cliente = último item do ``X-Forwarded-For`` (``frontend/server.js``, ``ipDoCliente``).

O segredo do endereço nunca vai para o log nem para o banco. Contrato:
``specs/340-caixa-de-avisos/contracts/manto-avisos.md``.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import re
import sys
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg

LOGGER_NOME = "manto_avisos"
logger = logging.getLogger(LOGGER_NOME)
if not logger.handlers:
    # O gunicorn não configura o logging da aplicação: sem isto, o INFO do aviso não sai no log.
    _saida = logging.StreamHandler(sys.stdout)
    _saida.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_saida)
    logger.setLevel(logging.INFO)
    logger.propagate = False

CAMINHO_DO_AVISO = "/api/webhooks/infinitepay/"
#: O mesmo teto da rota do backend: o aviso real tem centenas de bytes.
CORPO_MAXIMO = 64 * 1024
#: Segredo errado guarda só o começo do corpo, como `registrar_aviso_invalido` faz.
RESUMO_RECUSADO = 2000
LIMITE_POR_MINUTO = 60
#: Sem este teto, quem troca o `X-Forwarded-For` a cada chamada encheria a tabela de recusas.
TETO_RECUSAS_HORA = 120
PRAZO_DE_CONEXAO_S = 3
TZ_SP = ZoneInfo("America/Sao_Paulo")

RESPOSTA_OK = {"success": True, "message": None}
RESPOSTA_TENTE_DE_NOVO = {"success": False, "message": "Try again"}
RESPOSTA_NAO_ENCONTRADO = {"success": False, "message": "Not found"}
RESPOSTA_GRANDE_DEMAIS = {"success": False, "message": "Payload too large"}
RESPOSTA_EXCESSO = {"success": False, "message": "Too many requests"}
RESPOSTA_METODO = {"success": False, "message": "Method not allowed"}

STATUS = {
    200: "200 OK", 400: "400 Bad Request", 404: "404 Not Found", 405: "405 Method Not Allowed",
    413: "413 Payload Too Large", 429: "429 Too Many Requests", 503: "503 Service Unavailable",
}

SQL_SEGREDO = (
    "SELECT infinitepay_webhook_token, infinitepay_webhook_token_anterior, "
    "infinitepay_webhook_token_anterior_ate FROM site_settings WHERE id = 1"
)
SQL_GUARDAR = (
    "INSERT INTO virtual_payment_inbox (received_at, body, secret_ok) VALUES (%s, %s, %s) "
    "RETURNING id"
)


def agora_sp() -> datetime:
    """O mesmo relógio de ``app.constants.now_sp``: São Paulo, sem fuso anexado."""
    return datetime.now(TZ_SP).replace(tzinfo=None)


def normalizar_url(url: str | None) -> str:
    """Aceita a URL do Render (``postgres://``) e a do SQLAlchemy (``postgresql+psycopg://``)."""
    return re.sub(r"^postgres(?:ql)?(?:\+\w+)?://", "postgresql://", (url or "").strip())


class JanelaDeContagem:
    """Quantas vezes cada chave apareceu na janela, em memória (um processo, um worker).

    Thread-safe: o gunicorn roda este serviço com várias threads num processo só.
    """

    def __init__(self, limite: int, segundos: int) -> None:
        self.limite = limite
        self.segundos = segundos
        self._marcas: dict[str, deque[float]] = defaultdict(deque)
        self._trava = threading.Lock()

    def permite(self, chave: str) -> bool:
        """Conta mais uma para ``chave``; ``False`` se o limite da janela já foi atingido."""
        agora = time.monotonic()
        with self._trava:
            marcas = self._marcas[chave]
            while marcas and marcas[0] <= agora - self.segundos:
                marcas.popleft()
            if len(marcas) >= self.limite:
                return False
            marcas.append(agora)
            return True


def ip_do_cliente(environ: dict) -> str:
    """O Render acrescenta o IP de quem chamou ao FIM do ``X-Forwarded-For`` (provado na 310)."""
    partes = [p.strip() for p in environ.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
    return (partes[-1] if partes else environ.get("REMOTE_ADDR") or "sem-ip")[:64]


def ler_corpo(environ: dict) -> bytes | None:
    """O corpo, ou ``None`` se passar de ``CORPO_MAXIMO`` (com ou sem ``Content-Length``)."""
    entrada = environ["wsgi.input"]
    try:
        declarado = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        declarado = 0
    if declarado > CORPO_MAXIMO:
        return None
    if declarado:
        return entrada.read(declarado)
    if not environ.get("wsgi.input_terminated"):
        # Sem tamanho e sem garantia de fim (servidor de teste): ler bloquearia.
        return b""
    # Corpo chunked: o gunicorn entrega até o fim; lê um byte a mais para saber se passou do teto.
    dados = entrada.read(CORPO_MAXIMO + 1)
    return None if len(dados) > CORPO_MAXIMO else dados


def _confere(token: str, guardado: str | None) -> bool:
    if not token or not guardado:
        return False
    return hmac.compare_digest(token.encode("utf-8", "replace"), guardado.encode("utf-8"))


def segredo_valido(url: str, token: str) -> bool:
    """Mesmo critério de ``virtuais_ops.token_do_aviso_valido``; levanta se o banco falhar."""
    with psycopg.connect(url, connect_timeout=PRAZO_DE_CONEXAO_S) as conn:
        linha = conn.execute(SQL_SEGREDO).fetchone()
    if linha is None:
        return False
    atual, anterior, anterior_ate = linha
    if _confere(token, atual):
        return True
    return bool(anterior_ate and anterior_ate > agora_sp() and _confere(token, anterior))


def guardar(url: str, texto: str, secret_ok: bool) -> int:
    """Grava a linha na caixa e devolve o id; levanta se o banco falhar."""
    with psycopg.connect(url, connect_timeout=PRAZO_DE_CONEXAO_S, autocommit=True) as conn:
        return conn.execute(SQL_GUARDAR, (agora_sp(), texto, secret_ok)).fetchone()[0]


def banco_responde(url: str) -> bool:
    """``SELECT 1`` em até ``PRAZO_DE_CONEXAO_S`` — a sondagem de ``/health/banco``."""
    try:
        with psycopg.connect(url, connect_timeout=PRAZO_DE_CONEXAO_S) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error as exc:
        logger.warning("[avisos] banco não respondeu: %s", type(exc).__name__)
        return False


class Receptor:
    """A aplicação WSGI: rotas, limites em memória e a URL do banco."""

    def __init__(self, url: str, *, limite_minuto: int, teto_recusas: int) -> None:
        self.url = url
        self.por_cliente = JanelaDeContagem(limite_minuto, 60)
        self.recusas = JanelaDeContagem(teto_recusas, 3600)

    def __call__(self, environ: dict, start_response: Callable) -> Iterable[bytes]:
        inicio = time.monotonic()
        codigo, corpo, linha_id, tamanho = self.atender(environ)
        if environ.get("PATH_INFO", "").startswith(CAMINHO_DO_AVISO):
            # Nunca a URL: o segredo mora no caminho.
            logger.info("[avisos] %s id=%s bytes=%s ms=%d", codigo, linha_id or "-", tamanho,
                        (time.monotonic() - inicio) * 1000)
        dados = json.dumps(corpo).encode("utf-8")
        start_response(STATUS[codigo], [("Content-Type", "application/json"),
                                        ("Content-Length", str(len(dados))),
                                        ("Cache-Control", "no-store")])
        return [dados]

    def atender(self, environ: dict) -> tuple[int, dict, int | None, int]:
        """Roteia: ``(código, corpo da resposta, id da linha guardada, bytes recebidos)``."""
        caminho = environ.get("PATH_INFO", "")
        metodo = environ.get("REQUEST_METHOD", "GET")
        if caminho in ("/health", "/health/banco"):
            if metodo != "GET":
                return 405, RESPOSTA_METODO, None, 0
            if caminho == "/health":
                return 200, {"ok": True}, None, 0
            ok = banco_responde(self.url)
            return (200 if ok else 503), {"ok": ok}, None, 0
        token = caminho[len(CAMINHO_DO_AVISO):] if caminho.startswith(CAMINHO_DO_AVISO) else ""
        if not token or "/" in token:
            return 404, RESPOSTA_NAO_ENCONTRADO, None, 0
        if metodo != "POST":
            return 405, RESPOSTA_METODO, None, 0
        return self.receber(environ, token)

    def receber(self, environ: dict, token: str) -> tuple[int, dict, int | None, int]:
        """Limite → teto do corpo → segredo → guarda. Banco fora em qualquer passo = 400."""
        if not self.por_cliente.permite(ip_do_cliente(environ)):
            return 429, RESPOSTA_EXCESSO, None, 0
        bruto = ler_corpo(environ)
        if bruto is None:
            return 413, RESPOSTA_GRANDE_DEMAIS, None, CORPO_MAXIMO
        # O Postgres recusa NUL em texto; um aviso de verdade nunca traz, e sem isto ele daria 400
        # para sempre.
        texto = bruto.decode("utf-8", "replace").replace("\x00", "")
        try:
            if not segredo_valido(self.url, token):
                return 404, RESPOSTA_NAO_ENCONTRADO, self.guardar_recusa(texto), len(bruto)
            return 200, RESPOSTA_OK, guardar(self.url, texto, True), len(bruto)
        except psycopg.Error as exc:
            logger.warning("[avisos] banco fora ao receber: %s", type(exc).__name__)
            return 400, RESPOSTA_TENTE_DE_NOVO, None, len(bruto)

    def guardar_recusa(self, texto: str) -> int | None:
        """Resumo de 2 KB da chamada com segredo errado, até o teto por hora."""
        if not self.recusas.permite("global"):
            return None
        try:
            return guardar(self.url, texto[:RESUMO_RECUSADO], False)
        except psycopg.Error as exc:  # a recusa é registro de auditoria; o 404 não muda
            logger.warning("[avisos] recusa não guardada: %s", type(exc).__name__)
            return None


def criar_aplicacao(database_url: str | None, *, limite_minuto: int = LIMITE_POR_MINUTO,
                    teto_recusas: int = TETO_RECUSAS_HORA) -> Receptor:
    """Fábrica da aplicação WSGI; o verify cria uma por cenário (limites zerados, banco fora)."""
    url = normalizar_url(database_url)
    if not url:
        logger.error("[avisos] DATABASE_URL ausente — nenhum aviso será guardado")
    return Receptor(url, limite_minuto=limite_minuto, teto_recusas=teto_recusas)


aplicacao = criar_aplicacao(os.environ.get("DATABASE_URL"))


def _servir_local(argumentos: list[str]) -> None:
    """Servidor da biblioteca padrão só para teste manual (o gunicorn não roda no Windows)."""
    from wsgiref.simple_server import make_server

    porta = int(argumentos[0]) if argumentos else 5340
    logger.info("[avisos] ouvindo em http://127.0.0.1:%s", porta)
    make_server("127.0.0.1", porta, aplicacao).serve_forever()


if __name__ == "__main__":
    _servir_local(sys.argv[1:])
