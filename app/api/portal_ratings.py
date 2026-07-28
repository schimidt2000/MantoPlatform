"""Endpoints de Avaliação de eventos do Portal do Artista (feature 191).

Só orquestra e serializa — janelas de prazo, validação de nota e versionamento moram em
`app/talent_portal/portal_rating_ops.py`, fonte única reusada pela tela Jinja legada.

RBAC = "é o dono do recurso": toda consulta parte do talento da sessão e da sua escalação no
evento; um talento nunca alcança a avaliação de outro.

O baseline de versionamento (estado pré-edição) é capturado no GET do formulário e devolvido ao
cliente, que o reenvia no POST. A tela Jinja guarda o mesmo baseline na sessão — aqui não dá,
porque um cliente REST pode ter várias abas abertas e o slot único de sessão já estourou o
tamanho do cookie uma vez (ver `portal_rating_ops`). O baseline é apenas um detector de
mudança: se vier adulterado, o pior efeito é registrar (ou deixar de registrar) uma versão no
histórico — nunca alterar a nota gravada.
"""

from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.api.portal_auth import current_talent, portal_api_login_required
from app.api_utils import json_error
from app.talent_portal import portal_rating_ops
from app.talent_portal.portal_rating_ops import PortalRatingError


def _rating_error(exc: PortalRatingError) -> Any:
    """Traduz um `PortalRatingError` no envelope de erro padrão da API."""
    fields = {exc.field: exc.message} if exc.field else None
    return json_error(exc.message, exc.status, fields=fields)


@api_bp.route("/portal/ratings/pending")
@portal_api_login_required
def api_portal_pending_ratings() -> Any:
    """IDs de eventos que o talento pode avaliar agora e os que ainda pode editar."""
    talent = current_talent()
    return jsonify(
        {
            "rateable_event_ids": sorted(portal_rating_ops.rateable_event_ids(talent)),
            "rated_event_ids": sorted(portal_rating_ops.rated_event_ids(talent)),
            "editable_event_ids": sorted(portal_rating_ops.editable_rating_event_ids(talent)),
        }
    )


@api_bp.route("/portal/events/<int:event_id>/rate")
@portal_api_login_required
def api_portal_get_rating(event_id: int) -> Any:
    """Formulário de avaliação de um evento: nota atual, categorias e pessoas avaliáveis."""
    talent = current_talent()
    try:
        return jsonify(portal_rating_ops.serialize_rating_form(talent, event_id))
    except PortalRatingError as exc:
        return _rating_error(exc)


@api_bp.route("/portal/events/<int:event_id>/rate", methods=["POST"])
@portal_api_login_required
def api_portal_submit_rating(event_id: int) -> Any:
    """Envia (ou atualiza) a nota geral do evento — etapa 1 da avaliação."""
    talent = current_talent()
    data = request.get_json(silent=True) or {}
    try:
        portal_rating_ops.submit_rating(
            talent,
            event_id,
            data.get("score"),
            data.get("comment"),
            baseline=data.get("baseline"),
        )
        return jsonify(portal_rating_ops.serialize_rating_form(talent, event_id))
    except PortalRatingError as exc:
        return _rating_error(exc)


@api_bp.route("/portal/events/<int:event_id>/rate/detail", methods=["POST"])
@portal_api_login_required
def api_portal_submit_rating_detail(event_id: int) -> Any:
    """Envia as sub-avaliações (figurino/som/texto e pessoas) — etapa 2, opcional."""
    talent = current_talent()
    data = request.get_json(silent=True) or {}
    try:
        portal_rating_ops.submit_rating_detail(
            talent,
            event_id,
            data.get("general") or {},
            data.get("people") or [],
            baseline=data.get("baseline"),
        )
        return jsonify(portal_rating_ops.serialize_rating_form(talent, event_id))
    except PortalRatingError as exc:
        return _rating_error(exc)
