"""Utilidades compartilhadas pela camada de API JSON (Princípio III — API First).

Fonte única do envelope de erro e do guard de autenticação para os endpoints `/api/*`,
conforme `specs/144-migracao-react-spa/contracts/api-conventions.md`.
"""

import re
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify, request
from flask_login import current_user
from werkzeug.wrappers import Response


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


def ip_do_cliente() -> str:
    """O IP da família/usuário que fez a requisição (feature 310, FR-027).

    Um lugar só para essa decisão, usado pelo limitador e pela origem anti-abuso da loja. Atrás do
    Node, o ``remote_addr`` é o IP da infraestrutura do Render (o ProxyFix confia em um salto e o
    caminho tem pelo menos dois): o limite valia para todo mundo junto. O Node — único caminho
    público de ``/api`` — informa o IP real em ``X-Manto-Client-Ip``. Quem chamar o backend direto
    e forjar o cabeçalho só escolhe o próprio balde, o que já conseguiria trocando de IP.
    """
    try:
        informado = (request.headers.get(CABECALHO_IP_DO_CLIENTE) or "").strip()
    except RuntimeError:  # fora de requisição
        return "sem-ip"
    return informado[:64] or (request.remote_addr or "sem-ip")


_URL_DO_AVISO = re.compile(r"(/webhooks/infinitepay/)[^/?#\s\"']+")


def mascarar_url_webhook(texto: str) -> str:
    """Troca o segredo do endereço do aviso de pagamento por ``***`` (feature 310, R-13)."""
    return _URL_DO_AVISO.sub(lambda m: m.group(1) + "***", str(texto))
