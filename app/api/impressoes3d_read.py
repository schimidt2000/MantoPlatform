"""Endpoints de LEITURA do módulo de Impressões 3D (feature 200).

`/api/3d/acervo` (catálogo de peças) e `/api/3d/fila` (painel operacional do Artista 3D).
Reusa, sem duplicar, `app.impressoes3d.impressoes3d_ops`. Gate: `ARTISTA_3D` ou `SUPERADMIN`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.impressoes3d import impressoes3d_ops as ops
from app.models import CalendarEvent, EventRole


def has_3d_access(user: Any) -> bool:
    """True se o usuário pode ver/gerir o módulo 3D (Artista 3D ou Superadmin)."""
    allowed = {RoleName.ARTISTA_3D, RoleName.SUPERADMIN}
    return any(r.name.upper() in allowed for r in user.roles)


def require_3d_access() -> Any:
    """Devolve a resposta 403 quando o usuário não tem acesso ao módulo, ou `None`."""
    if not has_3d_access(current_user):
        return json_error("Sem permissão", 403)
    return None


def _serialize_role(role: EventRole) -> dict[str, Any]:
    """Personagem contratado do evento, com o talento escalado (se já houver)."""
    talent = role.talent
    return {
        "id": role.id,
        "character_name": role.character_name,
        "role_type": role.role_type,
        "talent_name": (talent.artistic_name or talent.full_name) if talent else None,
        "talent_photo_url": talent.photo_face_path if talent else None,
    }


def _serialize_event(event: CalendarEvent) -> dict[str, Any]:
    """Dados do evento pai exibidos no card/linha da Fila de Impressão."""
    return {
        "id": event.id,
        "title": event.title,
        "event_type": event.event_type or "",
        "start_at": event.start_at.isoformat() if event.start_at else None,
        "location": event.location or None,
    }


def serialize_queue_entry(gift: Any) -> dict[str, Any]:
    """Linha da Fila de Impressão: presente + evento + elenco + formulário de pré-contrato.

    Os `roles` e o `form_response` vêm aninhados de propósito (spec da feature 200): é lendo o
    formulário preenchido pela cliente que o Artista 3D descobre a idade e a quantidade de
    aniversariantes, e é pelo elenco que ele sabe quais personagens foram contratados — sem isso
    a Fila obrigaria a abrir o evento item por item.
    """
    event = gift.event
    form_response = event.form_responses[0] if event.form_responses else None
    entry = ops.serialize_gift(gift)
    entry["event"] = _serialize_event(event)
    entry["roles"] = [_serialize_role(r) for r in sorted(event.roles, key=lambda r: r.id)]
    entry["form_response"] = ops.serialize_form_response(form_response)
    return entry


@api_bp.route("/3d/acervo")
@api_login_required
def api_3d_acervo_list() -> Any:
    """Catálogo de peças do Acervo 3D (`?ativos=1` esconde as inativas)."""
    denied = require_3d_access()
    if denied:
        return denied
    only_active = request.args.get("ativos", "").strip() in ("1", "true")
    rows = ops.list_acervo(include_inactive=not only_active)
    return jsonify({"items": [ops.serialize_acervo_item(item, count) for item, count in rows]})


def serialize_pending_event(event: CalendarEvent) -> dict[str, Any]:
    """Evento SHOW futuro sem presente vinculado — uma tarefa aberta para o Artista 3D."""
    entry = _serialize_event(event)
    dismissal = event.dispensa_3d
    entry["dismissed"] = dismissal is not None
    entry["dismissed_by"] = (
        dismissal.dismisser.name if dismissal and dismissal.dismisser else None
    )
    entry["characters"] = [
        r.character_name for r in sorted(event.roles, key=lambda r: r.id)
        if r.role_type == "character"
    ]
    return entry


@api_bp.route("/3d/fila")
@api_login_required
def api_3d_fila() -> Any:
    """Fila de Impressão do Artista 3D — dois blocos de trabalho.

    `items`: presentes já vinculados e ainda não entregues (o que imprimir).
    `sem_presente`: eventos SHOW futuros que **ainda não têm presente vinculado** — a pendência
    nasce do evento, não do presente (feature 202). `?dispensados=1` inclui os já marcados como
    "não leva presente", para a tela poder oferecer o "Reativar".
    """
    denied = require_3d_access()
    if denied:
        return denied
    include_dismissed = request.args.get("dispensados", "").strip() in ("1", "true")
    pending = ops.list_pending_events(include_dismissed=include_dismissed)
    return jsonify(
        {
            "items": [serialize_queue_entry(g) for g in ops.list_print_queue()],
            "sem_presente": [serialize_pending_event(e) for e in pending],
        }
    )
