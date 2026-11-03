"""Endpoints dos avisos no celular (feature 332): a chave pública e o registro do aparelho.

RBAC: COMERCIAL e SUPERADMIN (``conversas.acesso.pode_conversas``, no início de cada view —
Princípio XIII), papel real: só quem atende as Conversas recebe aviso delas. Nada aqui manda aviso;
a entrega é do ``push_ops.despachar``, chamado pelas Conversas depois do commit.
"""

from __future__ import annotations

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.conversas.acesso import pode_conversas
from app.conversas.recusa import Recusa
from app.push import push_ops


def _negado() -> Any:
    if not pode_conversas(current_user):
        return json_error("Sem permissão", 403)
    return None


def _corpo() -> dict[str, Any]:
    corpo = request.get_json(silent=True)
    return corpo if isinstance(corpo, dict) else {}


@api_bp.route("/push/chave")
@api_login_required
def api_push_chave() -> Any:
    """Se os avisos estão ligados e a chave pública para o navegador assinar (FR-009)."""
    negado = _negado()
    if negado:
        return negado
    return jsonify(push_ops.situacao())


@api_bp.route("/push/aparelhos", methods=["POST"])
@api_login_required
def api_push_registrar() -> Any:
    """Registra este aparelho para a pessoa logada (FR-002): 201, 422 ou 503."""
    negado = _negado()
    if negado:
        return negado
    try:
        push_ops.registrar(current_user.id, _corpo(), request.headers.get("User-Agent"))
    except Recusa as exc:
        return json_error(exc.mensagem, exc.status, fields=exc.fields or None, codigo=exc.codigo)
    return jsonify({"ok": True}), 201


@api_bp.route("/push/aparelhos", methods=["DELETE"])
@api_login_required
def api_push_remover() -> Any:
    """Desativa este aparelho (só o da própria pessoa): 204."""
    negado = _negado()
    if negado:
        return negado
    push_ops.remover(current_user.id, _corpo().get("endpoint"))
    return "", 204
