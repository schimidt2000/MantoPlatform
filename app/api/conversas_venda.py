"""A venda na conversa (feature 349): painel, perda, qualificação e lembrete.

RBAC: COMERCIAL e SUPERADMIN pelo papel real (``conversas.acesso.pode_conversas``, função chamada no início de cada
view — Princípio XIII), o mesmo acesso das Conversas. Nada aqui fala com a Meta: o lembrete só vira aviso no sino da
equipe, pela varredura. Os endpoints validam, chamam ``app/conversas/venda_ops.py`` e devolvem o painel.

Recusas do núcleo saem no envelope de ``json_error`` com ``codigo``: 422 ``invalido`` com ``fields`` (``motivo``,
``frase``, ``decisao``) e 404 ``nao_encontrada``.
"""

from __future__ import annotations

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.conversas import venda_ops
from app.conversas.acesso import pode_conversas
from app.conversas.recusa import Recusa


def _negado() -> Any:
    if not pode_conversas(current_user):
        return json_error("Sem permissão", 403)
    return None


def _recusa(exc: Recusa) -> Any:
    return json_error(exc.mensagem, exc.status, fields=exc.fields or None, codigo=exc.codigo)


def _corpo() -> dict[str, Any]:
    corpo = request.get_json(silent=True)
    return corpo if isinstance(corpo, dict) else {}


def _venda(conversa: Any) -> Any:
    return jsonify({"venda": venda_ops.painel(conversa)})


@api_bp.route("/conversas/<int:conversa_id>/venda")
@api_login_required
def api_conversas_venda(conversa_id: int) -> Any:
    """O painel da venda: etapa, pontuação, primeira resposta, perda, lembrete e o que levar ao evento."""
    negado = _negado()
    if negado:
        return negado
    try:
        conversa = venda_ops.conversa_ou_404(conversa_id)
    except Recusa as exc:
        return _recusa(exc)
    return jsonify(venda_ops.painel(conversa))


@api_bp.route("/conversas/<int:conversa_id>/perdida", methods=["POST"])
@api_login_required
def api_conversas_perdida(conversa_id: int) -> Any:
    """Marca a conversa como perdida, com o motivo da lista fechada (e a frase no "Outro")."""
    negado = _negado()
    if negado:
        return negado
    corpo = _corpo()
    try:
        conversa = venda_ops.marcar_perdida(
            conversa_id, corpo.get("motivo"), corpo.get("frase"), current_user
        )
    except Recusa as exc:
        return _recusa(exc)
    return _venda(conversa)


@api_bp.route("/conversas/<int:conversa_id>/perdida", methods=["DELETE"])
@api_login_required
def api_conversas_reabrir(conversa_id: int) -> Any:
    """Reabre a conversa perdida (idempotente)."""
    negado = _negado()
    if negado:
        return negado
    try:
        conversa = venda_ops.reabrir(conversa_id)
    except Recusa as exc:
        return _recusa(exc)
    return _venda(conversa)


@api_bp.route("/conversas/<int:conversa_id>/qualificacao", methods=["POST"])
@api_login_required
def api_conversas_qualificacao(conversa_id: int) -> Any:
    """``decisao``: ``qualificada``, ``nao_qualificada`` ou ``null`` (usar a regra)."""
    negado = _negado()
    if negado:
        return negado
    try:
        conversa = venda_ops.decidir_qualificacao(
            conversa_id, _corpo().get("decisao"), current_user
        )
    except Recusa as exc:
        return _recusa(exc)
    return _venda(conversa)


@api_bp.route("/conversas/<int:conversa_id>/lembrete", methods=["POST"])
@api_login_required
def api_conversas_lembrete(conversa_id: int) -> Any:
    """ "Lembrar amanhã": às 9h de São Paulo do próximo dia, no sino de quem tocou."""
    negado = _negado()
    if negado:
        return negado
    try:
        conversa = venda_ops.lembrar_amanha(conversa_id, current_user)
    except Recusa as exc:
        return _recusa(exc)
    return _venda(conversa)


@api_bp.route("/conversas/<int:conversa_id>/lembrete", methods=["DELETE"])
@api_login_required
def api_conversas_lembrete_cancelar(conversa_id: int) -> Any:
    """Cancela o lembrete (idempotente)."""
    negado = _negado()
    if negado:
        return negado
    try:
        conversa = venda_ops.cancelar_lembrete(conversa_id)
    except Recusa as exc:
        return _recusa(exc)
    return _venda(conversa)
