"""Escrita na caixa de notificações do usuário (feature 272): marcar lida / marcar todas.

RBAC: só `@api_login_required`; escopo por dono (`user_id == current_user.id`) no servidor.
Notificação de outro usuário ou inexistente → **404, não 403**, para não confirmar existência
(convenção do RBAC de arquivo, docs/00 §4). Sem `DELETE` e sem "marcar como não lida" na v1: a
notificação é registro do fato; "sumir da lista" é lida, e a retenção limpa o resto.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.notificacoes import notificacoes_ops


@api_bp.route("/notificacoes/<int:notification_id>/lida", methods=["POST"])
@api_login_required
def api_notificacao_marcar_lida(notification_id: int) -> Any:
    """Marca uma notificação como lida (idempotente). Devolve `unread_count` já recalculado."""
    n = notificacoes_ops.marcar_lida(current_user.id, notification_id)
    if n is None:
        return json_error("Notificação não encontrada", 404)
    db.session.commit()
    return jsonify({
        "id": n.id,
        "read_at": n.read_at.isoformat(timespec="seconds") if n.read_at else None,
        "unread_count": notificacoes_ops.contar_nao_lidas(current_user.id),
    })


@api_bp.route("/notificacoes/lidas", methods=["POST"])
@api_login_required
def api_notificacoes_marcar_todas() -> Any:
    """Marca lidas as do usuário com `id <= ate_id`. `ate_id` é **obrigatório**: sem teto, "marcar
    todas" clicado sobre uma lista de 40 s atrás engoliria o lead que chegou depois e ninguém viu."""
    body = request.get_json(silent=True) or {}
    ate_id = body.get("ate_id")
    if not isinstance(ate_id, int) or ate_id <= 0:
        return json_error("Informe até qual notificação marcar.", 400, fields={"ate_id": "Obrigatório"})
    marcadas = notificacoes_ops.marcar_lidas_ate(current_user.id, ate_id)
    db.session.commit()
    return jsonify({
        "marcadas": marcadas,
        "unread_count": notificacoes_ops.contar_nao_lidas(current_user.id),
    })
