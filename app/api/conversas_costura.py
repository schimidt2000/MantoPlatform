"""Endpoints da costura das Conversas com a Plataforma (feature 333): orçamento, ficha e formulário.

RBAC: COMERCIAL e SUPERADMIN (``conversas.acesso.pode_conversas``, no início de cada view —
Princípio XIII), papel real. O orçamento sai pelo envio da conversa (``envio_ops``), com a trava do
ambiente, a janela e a chave idempotente de sempre; o histórico do orçamento continua do time inteiro
(feature 301), então qualquer pessoa do comercial manda o orçamento de qualquer colega, e o registro
do envio guarda quem mandou.

Recusas do núcleo saem no envelope de ``json_error`` com ``codigo``: 404 ``nao_encontrada``, 422
``invalido`` com ``fields`` (``orcamento``, ``cliente``, ``nome``, ``telefone``, ``chave_envio``) e as do
envio comum (409 ``janela_fechada`` / ``envio_travado``, 503 ``nao_configurado``).
"""

from __future__ import annotations

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.conversas import costura_ops, ficha_ops, leitura_ops
from app.conversas.acesso import pode_conversas
from app.conversas.configuracao import cfg_whatsapp
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


@api_bp.route("/conversas/<int:conversa_id>/orcamento", methods=["POST"])
@api_login_required
def api_conversas_enviar_orcamento(conversa_id: int) -> Any:
    """A mensagem pronta e o PDF do orçamento pela conversa: 201 (novo) ou 200 (a mesma chave)."""
    negado = _negado()
    if negado:
        return negado
    corpo = _corpo()
    try:
        envio = costura_ops.enviar_orcamento(
            conversa_id,
            corpo.get("orcamento_id"),
            corpo.get("chave_envio"),
            current_user.id,
            cfg_whatsapp(),
            corpo.get("cliente"),
        )
    except Recusa as exc:
        return _recusa(exc)
    return jsonify(
        {
            "envio": costura_ops.serializar_envio(envio.registro),
            "mensagens": [leitura_ops.serializar_mensagem(m) for m in envio.mensagens],
            "conversa": leitura_ops.serializar_conversa(envio.conversa),
        }
    ), (201 if envio.novo else 200)


@api_bp.route("/conversas/<int:conversa_id>/ficha", methods=["POST"])
@api_login_required
def api_conversas_ligar_ficha(conversa_id: int) -> Any:
    """Liga a conversa a uma ficha existente (``client_id``) ou nova (``nome`` e ``telefone``)."""
    negado = _negado()
    if negado:
        return negado
    try:
        ligacao = ficha_ops.ligar(conversa_id, _corpo())
    except Recusa as exc:
        return _recusa(exc)
    return jsonify(
        {
            "conversa": leitura_ops.serializar_conversa(ligacao.conversa),
            "reaproveitada": ligacao.reaproveitada,
        }
    )


@api_bp.route("/conversas/<int:conversa_id>/ficha", methods=["DELETE"])
@api_login_required
def api_conversas_remover_ficha(conversa_id: int) -> Any:
    """Remove o vínculo com a ficha (sem apagá-la); a ligação automática não volta a agir."""
    negado = _negado()
    if negado:
        return negado
    try:
        conversa = ficha_ops.remover(conversa_id)
    except Recusa as exc:
        return _recusa(exc)
    return jsonify({"conversa": leitura_ops.serializar_conversa(conversa)})


@api_bp.route("/conversas/<int:conversa_id>/formularios")
@api_login_required
def api_conversas_formularios(conversa_id: int) -> Any:
    """Os formulários públicos com o link curto e o texto pronto para esta conversa."""
    negado = _negado()
    if negado:
        return negado
    try:
        formularios = costura_ops.formularios_da_conversa(conversa_id)
    except Recusa as exc:
        return _recusa(exc)
    return jsonify({"formularios": formularios})
