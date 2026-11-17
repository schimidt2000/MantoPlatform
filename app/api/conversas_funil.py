"""O funil das conversas (feature 335): leitura do núcleo ``app/conversas/funil_ops.py``.

RBAC: COMERCIAL e SUPERADMIN pelo papel real (``pode_conversas``, função no início de cada view — Princípio XIII),
o mesmo acesso das Conversas. Recusas do núcleo saem no envelope de ``json_error`` (422 com ``fields``).
"""

from __future__ import annotations

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.conversas import funil_ops
from app.conversas.acesso import pode_conversas
from app.conversas.recusa import Recusa


def _negado() -> Any:
    if not pode_conversas(current_user):
        return json_error("Sem permissão", 403)
    return None


def _recusa(exc: Recusa) -> Any:
    return json_error(exc.mensagem, exc.status, fields=exc.fields or None, codigo=exc.codigo)


def _filtros() -> dict[str, str | None]:
    return {
        "inicio": request.args.get("inicio") or None,
        "fim": request.args.get("fim") or None,
        "canal": request.args.get("canal") or None,
        "campanha": request.args.get("campanha") or None,
    }


@api_bp.route("/conversas/funil")
@api_login_required
def api_conversas_funil() -> Any:
    """As etapas do período, os filtros de campanha e a divisão por vendedor, campanha ou canal."""
    negado = _negado()
    if negado:
        return negado
    try:
        return jsonify(funil_ops.funil(**_filtros(), dividir=request.args.get("dividir") or None))
    except Recusa as exc:
        return _recusa(exc)


@api_bp.route("/conversas/funil/parados")
@api_login_required
def api_conversas_funil_parados() -> Any:
    """As conversas que pararam numa etapa (até 200, com o total)."""
    negado = _negado()
    if negado:
        return negado
    try:
        return jsonify(funil_ops.parados(**_filtros(), etapa=request.args.get("etapa") or None))
    except Recusa as exc:
        return _recusa(exc)
