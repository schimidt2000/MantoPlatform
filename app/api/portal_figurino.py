"""Endpoint de Ficha de Figurino do Portal do Artista (feature 176).

RBAC = "é o dono do recurso": a sessão de talento é conferida por `@portal_api_login_required`
(401 sem ela) e a ficha só sai para quem tem o que ver naquele evento — o intérprete vê os
próprios personagens, o coordenador vê o elenco inteiro. O `event_id` vem do cliente, mas não
manda em nada: quem decide é `portal_ops.get_figurino`, que parte do talento da sessão e devolve
`None` quando ele não está escalado. Não há papéis dentro do portal.

Era o único dos cinco módulos do portal sem esta declaração (feature 302).

**Recusa com 403, e não 404**, o que confirma a um estranho que o evento existe — o Princípio XIII
pede 404. Fica assim por decisão registrada do dono na 302: trocar mudaria a mensagem que o
artista lê ("Você não está escalado neste evento") e não tem relação com o que a feature resolve.
Está em `docs/05`; não "conserte" de passagem.

Só orquestra e serializa — a regra de negócio (resolução da ficha por personagem/evento) mora
em `app/talent_portal/portal_ops.py`.
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
