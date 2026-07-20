"""Utilidades compartilhadas pela camada de API JSON (Princípio III — API First).

Fonte única do envelope de erro e do guard de autenticação para os endpoints `/api/*`,
conforme `specs/144-migracao-react-spa/contracts/api-conventions.md`.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify
from flask_login import current_user
from werkzeug.wrappers import Response


def json_error(
    message: str,
    status: int,
    fields: dict[str, str] | None = None,
) -> tuple[Response, int]:
    """Constrói uma resposta de erro JSON no formato padrão da API.

    Args:
        message: Mensagem amigável em pt-BR (nunca stack trace).
        status: Código HTTP (400, 401, 403, 404, 500...).
        fields: Mapa opcional campo → mensagem, para erros de validação (400).

    Returns:
        Tupla ``(resposta_json, status)`` no formato ``{"error": {...}}``.
    """
    body: dict[str, Any] = {"message": message}
    if fields:
        body["fields"] = fields
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
