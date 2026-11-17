"""Endpoints de ESCRITA da equipe nas Conversas (feature 328): responsável, notas e respostas rápidas.

RBAC: COMERCIAL e SUPERADMIN (``conversas.acesso.pode_conversas``, no início de cada view —
Princípio XIII), papel real. Nada aqui fala com a Meta: a nota nunca sai, e a resposta rápida só
preenche o campo na tela (quem envia é o ``POST /mensagens`` da 325, com a trava dela).

Recusas do núcleo saem no envelope de ``json_error`` com ``codigo``: 409 ``ja_assumida`` /
``alterada``, 422 ``invalido`` com ``fields``, 404 ``nao_encontrada``.
"""

from __future__ import annotations

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.conversas import equipe_ops, leitura_ops, respostas_ops
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


@api_bp.route("/conversas/<int:conversa_id>/responsavel", methods=["POST"])
@api_login_required
def api_conversas_responsavel(conversa_id: int) -> Any:
    """Assumir, transferir ou devolver à fila (FR-003/FR-004)."""
    negado = _negado()
    if negado:
        return negado
    corpo = _corpo()
    try:
        conversa = equipe_ops.definir_responsavel(
            conversa_id, corpo.get("acao"), current_user, corpo.get("responsavel_id")
        )
    except Recusa as exc:
        return _recusa(exc)
    return jsonify({"conversa": leitura_ops.serializar_conversa(conversa)})


@api_bp.route("/conversas/<int:conversa_id>/notas", methods=["POST"])
@api_login_required
def api_conversas_nota(conversa_id: int) -> Any:
    """Nota interna: nunca sai para a cliente (FR-009)."""
    negado = _negado()
    if negado:
        return negado
    try:
        nota = equipe_ops.gravar_nota(conversa_id, _corpo().get("texto"), current_user.id)
    except Recusa as exc:
        return _recusa(exc)
    return jsonify({"nota": leitura_ops.serializar_nota(nota)}), 201


@api_bp.route("/conversas/respostas-rapidas")
@api_login_required
def api_respostas_rapidas() -> Any:
    """A lista da equipe, por título (FR-010)."""
    negado = _negado()
    if negado:
        return negado
    return jsonify({"respostas": [respostas_ops.serializar(r) for r in respostas_ops.listar()]})


@api_bp.route("/conversas/respostas-rapidas", methods=["POST"])
@api_login_required
def api_respostas_rapidas_criar() -> Any:
    """Nova resposta rápida da equipe (FR-010): 201, ou 422 apontando o campo."""
    negado = _negado()
    if negado:
        return negado
    try:
        resposta = respostas_ops.criar(_corpo(), current_user.id)
    except Recusa as exc:
        return _recusa(exc)
    return jsonify({"resposta": respostas_ops.serializar(resposta)}), 201


@api_bp.route("/conversas/respostas-rapidas/<int:resposta_id>", methods=["PATCH"])
@api_login_required
def api_respostas_rapidas_alterar(resposta_id: int) -> Any:
    """Altera só os campos enviados: 200, 422 por campo ou 404."""
    negado = _negado()
    if negado:
        return negado
    try:
        resposta = respostas_ops.alterar(resposta_id, _corpo(), current_user.id)
    except Recusa as exc:
        return _recusa(exc)
    return jsonify({"resposta": respostas_ops.serializar(resposta)})


@api_bp.route("/conversas/respostas-rapidas/<int:resposta_id>", methods=["DELETE"])
@api_login_required
def api_respostas_rapidas_excluir(resposta_id: int) -> Any:
    """Exclui de verdade (a tela confirmou antes): 204 ou 404."""
    negado = _negado()
    if negado:
        return negado
    try:
        respostas_ops.excluir(resposta_id)
    except Recusa as exc:
        return _recusa(exc)
    return "", 204
