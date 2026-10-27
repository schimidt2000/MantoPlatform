"""Utilidades compartilhadas pela camada de API JSON (Princípio III — API First).

Fonte única do envelope de erro e do guard de autenticação para os endpoints `/api/*`,
conforme `specs/144-migracao-react-spa/contracts/api-conventions.md`.
"""

import hmac
import re
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import current_app, jsonify, request
from flask_login import current_user
from werkzeug.wrappers import Response


def json_recusa_do_cancelado(exc: Any) -> tuple[Response, int]:
    """A tradução única de uma recusa do núcleo do cancelado (`CancelValidationError` da 306 e
    da 312) em `json_error`, com o `codigo` para a tela agir (recarregar o evento)."""
    codigo = {"codigo": exc.codigo} if exc.codigo else {}
    return json_error(exc.message, exc.status, fields=exc.fields, **codigo, **exc.extras)


def trava_do_cancelado(event: Any) -> tuple[Response, int] | None:
    """A trava da tela do cancelado (feature 312, FR-011) na porta da API: 409 `cancelado` ou
    `None` para seguir. Chamada depois do 404 e do 403 de cada rota e antes de qualquer escrita.
    A regra mora no núcleo (`cancel_ops.exigir_evento_vivo`); aqui só se traduz."""
    from app.calendar.cancel_ops import CancelValidationError, exigir_evento_vivo

    try:
        exigir_evento_vivo(event)
    except CancelValidationError as exc:
        return json_recusa_do_cancelado(exc)
    return None


def json_error(
    message: str,
    status: int,
    fields: dict[str, str] | None = None,
    **extra: Any,
) -> tuple[Response, int]:
    """Constrói uma resposta de erro JSON no formato padrão da API.

    Args:
        message: Mensagem amigável em pt-BR (nunca stack trace).
        status: Código HTTP (400, 401, 403, 404, 500...).
        fields: Mapa opcional campo → mensagem, para erros de validação (400).
        **extra: Chaves adicionais dentro do objeto de erro, para o cliente **agir** e não só
            exibir. Existe porque nem todo erro é um beco: um 409 de "isto vai apagar dados"
            precisa dizer *o quê* (`needs_confirmation` + a lista) para a tela abrir a confirmação
            com nomes e valores; um 409 de "este evento é satélite" precisa devolver `leader_id`
            para a tela oferecer o caminho até o principal. Sem isto, sobra a mensagem em prosa e
            o front teria que adivinhar por texto.

    Returns:
        Tupla ``(resposta_json, status)`` no formato ``{"error": {...}}``.
    """
    body: dict[str, Any] = {"message": message}
    if fields:
        body["fields"] = fields
    body.update(extra)
    return jsonify({"error": body}), status


def api_login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Exige sessão autenticada, respondendo 401 JSON em vez de redirecionar.

    Diferente de ``flask_login.login_required`` (que redireciona para a tela de login),
    adequado a um cliente SPA que espera JSON.
    """

    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not current_user.is_authenticated:
            return json_error("Não autenticado", 401)
        return view(*args, **kwargs)

    return wrapped


#: Cabeçalho que o `frontend/server.js` põe com o IP que a borda do Render viu (feature 310, R8).
CABECALHO_IP_DO_CLIENTE = "X-Manto-Client-Ip"
#: Prova de que a requisição passou pelo Node (``MANTO_PROXY_SECRET``) — sem ela o IP informado
#: não vale.
CABECALHO_SEGREDO_DO_PROXY = "X-Manto-Proxy-Secret"


def ip_do_cliente() -> str:
    """O IP da família/usuário que fez a requisição (feature 310, FR-027).

    Um lugar só para essa decisão, usado pelo limitador e pela origem anti-abuso da loja. Atrás do
    Node, o ``remote_addr`` é o IP da infraestrutura do Render (o ProxyFix confia em um salto e o
    caminho tem pelo menos dois): o limite valia para todo mundo junto. O Node — único caminho
    público de ``/api`` — informa o IP real em ``X-Manto-Client-Ip``.

    Mas o backend também tem URL pública: quem chamasse direto trocava o cabeçalho a cada
    requisição e caía num balde novo toda vez, sem limite nenhum. Por isso o IP informado só vale
    junto com ``X-Manto-Proxy-Secret`` igual a ``MANTO_PROXY_SECRET``; sem a prova, vale o
    ``remote_addr``. Sem o segredo configurado (transição do deploy), o cabeçalho é aceito como
    antes e o boot avisa no log.
    """
    try:
        informado = (request.headers.get(CABECALHO_IP_DO_CLIENTE) or "").strip()
        prova = request.headers.get(CABECALHO_SEGREDO_DO_PROXY) or ""
        segredo = current_app.config.get("MANTO_PROXY_SECRET") or ""
    except RuntimeError:  # fora de requisição
        return "sem-ip"
    if segredo and not hmac.compare_digest(prova.encode(), segredo.encode()):
        informado = ""
    return informado[:64] or (request.remote_addr or "sem-ip")


_URL_DO_AVISO = re.compile(r"(/webhooks/infinitepay/)[^/?#\s\"']+")


def mascarar_url_webhook(texto: str) -> str:
    """Troca o segredo do endereço do aviso de pagamento por ``***`` (feature 310, R-13)."""
    return _URL_DO_AVISO.sub(lambda m: m.group(1) + "***", str(texto))
