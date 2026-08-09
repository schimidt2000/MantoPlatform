"""Endpoint de Ficha de Figurino do Portal do Artista (feature 176).

Só orquestra e serializa — a regra de negócio (resolução da ficha por personagem/evento) mora
em `app/talent_portal/portal_ops.py`, sem duplicar lógica com a view Jinja legada.
"""

from typing import Any

from flask import jsonify

from app.api import api_bp
from app.api.portal_auth import current_talent, portal_api_login_required
from app.api_utils import json_error
from app.models import CalendarEvent
from app.talent_portal import portal_ops


@api_bp.route("/portal/events/<int:event_id>/figurino")
@portal_api_login_required
def api_portal_event_figurino(event_id: int) -> Any:
    talent = current_talent()
    sheet_items = portal_ops.get_figurino(talent, event_id)
    if sheet_items is None:
        return json_error("Você não está escalado neste evento.", 403)

    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado.", 404)

    # `is_coordinator` muda o que a tela DIZ, não só o que ela lista: sem isso o coordenador não
    # entenderia por que apareceram personagens que não são dele, e o texto de lista vazia não
    # saberia distinguir "o evento não tem ficha" de "você não tem personagem aqui".
    coordena = portal_ops.is_event_coordinator(talent, event)

    return jsonify(
        {
            "event": {
                "id": event.id,
                "title": event.title,
                "start_at": event.start_at.isoformat() if event.start_at else None,
            },
            "is_coordinator": coordena,
            "sheets": [
                {
                    "character_name": sheet.character_name,
                    "photo_url": photo_url,
                    "talent_name": talent_name,
                    "notes": sheet.notes,
                    "pieces": sheet.pieces_list,
                }
                for sheet, photo_url, talent_name in sheet_items
            ],
        }
    )
