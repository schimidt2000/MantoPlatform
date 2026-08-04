"""Endpoints de LEITURA da Loja de Interações Virtuais (feature 205).

Listagem e detalhe administrativo das campanhas. Reusa, sem duplicar,
``app.marketing.virtuais_ops``. Gate: ``COMERCIAL`` ou ``SUPERADMIN`` (FR-010).

A superfície pública (landing, horários, página do pedido) vive em ``virtuais_public.py``, sem
autenticação — são coisas diferentes de propósito.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import VIRTUAIS_ADMIN_ROLES, VIRTUAL_REFUND_STATUS_PENDENTE, RoleName
from app.marketing import virtuais_ops as ops
from app.models import VirtualCampaign, VirtualRefundRequest


def has_virtuais_access(user: Any) -> bool:
    """True se o usuário pode gerir campanhas virtuais (Comercial ou Superadmin)."""
    allowed = {role.upper() for role in VIRTUAIS_ADMIN_ROLES}
    return any(r.name.upper() in allowed for r in user.roles)


def require_virtuais_access() -> Any:
    """Devolve a resposta 403 quando o usuário não pode gerir campanhas, ou ``None``."""
    if not has_virtuais_access(current_user):
        return json_error("Sem permissão", 403)
    return None


@api_bp.route("/virtuais/campanhas", methods=["GET"])
@api_login_required
def api_virtuais_campanhas_list() -> Any:
    """Lista as campanhas virtuais com vendidos, faturado e horários restantes (FR-009)."""
    denied = require_virtuais_access()
    if denied:
        return denied
    campaigns = VirtualCampaign.query.order_by(VirtualCampaign.created_at.desc()).all()
    return jsonify({"campaigns": [ops.serialize_campaign_admin(c) for c in campaigns]})


def has_producao_access(user: Any) -> bool:
    """True se o usuário pode ver a Fila de Produção de Mídia (FR-051).

    Além de quem gere as campanhas, entra o `CASTING` — é o time que acompanha a execução — e o
    próprio talento, que precisa ver e atualizar o que lhe cabe.
    """
    allowed = {r.upper() for r in VIRTUAIS_ADMIN_ROLES} | {RoleName.CASTING}
    return any(r.name.upper() in allowed for r in user.roles)


def require_producao_access() -> Any:
    """403 quando o usuário não pode operar a Fila de Produção, ou ``None``."""
    if not has_producao_access(current_user):
        return json_error("Sem permissão", 403)
    return None


@api_bp.route("/virtuais/producao", methods=["GET"])
@api_login_required
def api_virtuais_producao() -> Any:
    """Fila de Produção de Mídia — uma linha por entrega (FR-045, FR-046, FR-050).

    Filtros por campanha, data e status; a lista já vem ordenada por urgência.
    """
    denied = require_producao_access()
    if denied:
        return denied
    entregas = ops.listar_fila_producao(
        campaign_id=request.args.get("campaign_id"),
        day=request.args.get("date"),
        status=request.args.get("status"),
    )
    return jsonify({"deliveries": [ops.serialize_delivery(d) for d in entregas]})


@api_bp.route("/virtuais/devolucoes", methods=["GET"])
@api_login_required
def api_virtuais_devolucoes() -> Any:
    """Devoluções a executar no painel da operadora (FR-043).

    Padrão `?status=pendente` — o que a equipe precisa ver é o que ainda deve dinheiro à família.
    A InfinitePay não publica API de estorno, então esta lista é a garantia de que nenhuma
    devolução se perde.
    """
    denied = require_virtuais_access()
    if denied:
        return denied
    status = request.args.get("status", VIRTUAL_REFUND_STATUS_PENDENTE)
    query = VirtualRefundRequest.query
    if status:
        query = query.filter(VirtualRefundRequest.status == status)
    refunds = query.order_by(VirtualRefundRequest.created_at.desc()).all()
    return jsonify({"refunds": [ops.serialize_refund(r) for r in refunds]})


@api_bp.route("/virtuais/campanhas/<int:campaign_id>/admin", methods=["GET"])
@api_login_required
def api_virtuais_campanha_detail(campaign_id: int) -> Any:
    """Detalhe administrativo de uma campanha, com seus horários."""
    denied = require_virtuais_access()
    if denied:
        return denied
    campaign = VirtualCampaign.query.get(campaign_id)
    if campaign is None:
        return json_error("Campanha não encontrada", 404)
    return jsonify(
        {
            **ops.serialize_campaign_admin(campaign),
            "slots": [ops.serialize_slot(s) for s in campaign.slots],
        }
    )
