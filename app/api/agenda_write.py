"""Endpoints de ESCRITA da Agenda/Eventos (feature 146). Fatia US1: escalar casting.

Cada ação reusa o núcleo em `app/calendar/casting_ops.py` (mesma lógica do handler Jinja) e
devolve o evento no formato de leitura da feature 145. As ações Jinja seguem intactas.
"""

from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from flask import jsonify, request, session
from flask_login import current_user

from app.api import api_bp
from app.api.agenda_read import serialize_event_detail
from app.api_utils import api_login_required, json_error
from app.constants import CLIENT_RELATION_TIPOS, RoleName
from app.models import CalendarEvent, Client, EventObservation, EventRole, db

_TZ_SP = ZoneInfo("America/Sao_Paulo")


def _can_edit_event() -> bool:
    """Mesmo gate do POST de /events/<id> (`_CAN_EDIT_EVENT`) — paridade com o Jinja."""
    from app.calendar.routes import _CAN_EDIT_EVENT

    return any(r.name.upper() in _CAN_EDIT_EVENT for r in current_user.roles)


def _can_casting() -> bool:
    """Gate específico das ações de casting que o exigem (ex.: remover cargo)."""
    return any(
        r.name.upper() in (RoleName.CASTING, RoleName.SUPERADMIN) for r in current_user.roles
    )


def _is_superadmin() -> bool:
    """Só superadmin (dispensar/restaurar cargo)."""
    return any(r.name == RoleName.SUPERADMIN for r in current_user.roles)


def _can_confirm() -> bool:
    """Gate de confirmar/desconfirmar o evento: Comercial ou Superadmin (paridade com o Jinja)."""
    return any(
        r.name.upper() in (RoleName.COMERCIAL, RoleName.SUPERADMIN) for r in current_user.roles
    )


def _can_delete() -> bool:
    """Gate de excluir o evento (`_CAN_DELETE` = Comercial ou Superadmin) — paridade com o Jinja."""
    from app.calendar.routes import _CAN_DELETE

    return any(r.name.upper() in _CAN_DELETE for r in current_user.roles)


def _can_create_event() -> bool:
    """Gate de criar evento (`_CAN_CREATE` = Comercial ou Superadmin) — paridade com o Jinja."""
    from app.calendar.routes import _CAN_CREATE

    return any(r.name.upper() in _CAN_CREATE for r in current_user.roles)


def _event_detail_json(event: Any) -> Any:
    """Serializa o evento atualizado com o RBAC do usuário atual (resposta padrão das escritas)."""
    impersonate = session.get("impersonate_role")
    return jsonify(serialize_event_detail(event, current_user, impersonate))


@api_bp.route("/roles/<int:role_id>/assign", methods=["POST"])
@api_login_required
def api_assign_role(role_id: int) -> Any:
    """Escala/atualiza/desescala o talento de um cargo (data-model.md)."""
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)

    event = CalendarEvent.query.get(role.event_id)
    data = request.get_json(silent=True) or {}
    is_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)

    from app.calendar.casting_ops import assign_role

    assign_role(
        event,
        role,
        talent_id=data.get("talent_id"),
        cache_value=data.get("cache_value"),
        travel_cache=data.get("travel_cache"),
        actor_name=current_user.name,
        is_superadmin=is_superadmin,
        tz=_TZ_SP,
    )
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/roles", methods=["POST"])
@api_login_required
def api_add_role(event_id: int) -> Any:
    """Adiciona um cargo ao evento (feature 147)."""
    if not _can_edit_event():
        return json_error("Sem permissão", 403)
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    data = request.get_json(silent=True) or {}
    character_name = (data.get("character_name") or "").strip()
    if not character_name:
        return json_error("Informe o nome do personagem", 400, {"character_name": "Obrigatório"})

    from app.calendar.casting_ops import add_role

    add_role(
        event,
        character_name=character_name,
        talent_id=data.get("talent_id"),
        cache_value=data.get("cache_value"),
        role_type=data.get("role_type", "character"),
        actor_name=current_user.name,
        tz=_TZ_SP,
    )
    return _event_detail_json(event)


@api_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@api_login_required
def api_delete_role(role_id: int) -> Any:
    """Remove um cargo (feature 147). Cargo com convite aceito só sai por superadmin."""
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _can_casting():
        return json_error("Sem permissão", 403)
    event = CalendarEvent.query.get(role.event_id)
    is_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)

    from app.calendar.casting_ops import delete_role

    removed = delete_role(
        event, role, is_superadmin=is_superadmin, actor_name=current_user.name, tz=_TZ_SP
    )
    if not removed:
        return json_error("Cargo com convite aceito só pode ser removido por um superadmin", 403)
    return _event_detail_json(event)


@api_bp.route("/roles/<int:role_id>/invite", methods=["POST"])
@api_login_required
def api_send_invite(role_id: int) -> Any:
    """Reenvia o convite de um cargo com talento (feature 148). No-op se não há talento."""
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)
    event = CalendarEvent.query.get(role.event_id)

    from app.calendar.casting_ops import send_invite

    send_invite(event, role, actor_name=current_user.name, tz=_TZ_SP)
    return _event_detail_json(event)


@api_bp.route("/roles/<int:role_id>/figurino-done", methods=["POST"])
@api_login_required
def api_figurino_done(role_id: int) -> Any:
    """Marca o figurino de um cargo como separado (feature 148).

    RBAC = `_CAN_EDIT_EVENT` (paridade exata: no Jinja o `figurino_done` é despachado pelo POST
    de `/events/<id>`, gateado por quem pode editar o evento — não só Figurino).
    """
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)
    event = CalendarEvent.query.get(role.event_id)

    from app.calendar.casting_ops import set_figurino_done

    set_figurino_done(event, role, actor_name=current_user.name, tz=_TZ_SP)
    return _event_detail_json(event)


@api_bp.route("/roles/<int:role_id>/dismiss", methods=["POST"])
@api_login_required
def api_dismiss_role(role_id: int) -> Any:
    """Dispensa um cargo sem talento (feature 108/148). RBAC: só superadmin."""
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _is_superadmin():
        return json_error("Sem permissão", 403)

    from app.calendar.casting_ops import dismiss_role

    ok = dismiss_role(role, actor_name=current_user.name, dismissed_by=current_user.id)
    if not ok:
        return json_error("Só é possível dispensar cargos sem talento atribuído", 400)
    event = CalendarEvent.query.get(role.event_id)
    return _event_detail_json(event)


@api_bp.route("/roles/<int:role_id>/restore", methods=["POST"])
@api_login_required
def api_restore_role(role_id: int) -> Any:
    """Restaura um cargo dispensado (feature 108/148). RBAC: só superadmin."""
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _is_superadmin():
        return json_error("Sem permissão", 403)

    from app.calendar.casting_ops import restore_role

    restore_role(role, actor_name=current_user.name)
    event = CalendarEvent.query.get(role.event_id)
    return _event_detail_json(event)


# ── Ações de nível-evento (feature 149) ──────────────────────────────────────


@api_bp.route("/events/<int:event_id>/confirm", methods=["POST"])
@api_login_required
def api_toggle_confirm(event_id: int) -> Any:
    """Confirma/desconfirma o evento (feature 149, toggle). RBAC: Comercial ou Superadmin."""
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_confirm():
        return json_error("Sem permissão", 403)

    from app.calendar.event_ops import toggle_confirmed

    toggle_confirmed(event, actor_name=current_user.name, actor_id=current_user.id, tz=_TZ_SP)
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/logistics", methods=["PATCH"])
@api_login_required
def api_save_logistics(event_id: int) -> Any:
    """Salva a logística do evento (feature 149). RBAC: `_CAN_EDIT_EVENT` (como o POST Jinja)."""
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)
    data = request.get_json(silent=True) or {}

    from app.calendar.event_ops import resolve_makeup_location, save_logistics

    save_logistics(
        event,
        makeup_time=data.get("makeup_time", ""),
        makeup_location=resolve_makeup_location(
            data.get("makeup_location"), data.get("makeup_location_custom")
        ),
        departure_time=data.get("departure_time", ""),
        departure_location=data.get("departure_location", ""),
        needs_rehearsal=bool(data.get("needs_rehearsal")),
        actor_name=current_user.name,
        tz=_TZ_SP,
    )
    return _event_detail_json(event)


# ── Observações do evento (feature 150) ──────────────────────────────────────


@api_bp.route("/events/<int:event_id>/observations", methods=["POST"])
@api_login_required
def api_add_observation(event_id: int) -> Any:
    """Adiciona uma observação de texto/link ao evento (feature 150).

    Sem gate de papel (paridade com o `@login_required` do Jinja). Imagem não é suportada por aqui
    (upload adiado) — só `obs_type` "text" ou "link".
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    data = request.get_json(silent=True) or {}
    obs_type = data.get("obs_type")
    if obs_type not in ("text", "link"):
        return json_error("Tipo de observação inválido", 400, {"obs_type": "Use texto ou link"})

    from app.calendar.observation_ops import add_observation

    obs = add_observation(
        event,
        obs_type=obs_type,
        content=data.get("content"),
        label=data.get("label"),
    )
    if obs is None:
        return json_error("Informe o conteúdo da observação", 400, {"content": "Obrigatório"})
    db.session.commit()
    return _event_detail_json(event)


@api_bp.route("/observations/<int:obs_id>", methods=["DELETE"])
@api_login_required
def api_delete_observation(obs_id: int) -> Any:
    """Remove uma observação do evento (feature 150). Sem gate de papel (paridade com o Jinja)."""
    obs = EventObservation.query.get(obs_id)
    if obs is None:
        return json_error("Observação não encontrada", 404)
    event = CalendarEvent.query.get(obs.event_id)

    from app.calendar.observation_ops import delete_observation

    if not delete_observation(event, obs_id):
        return json_error("Observação não encontrada", 404)
    return _event_detail_json(event)


# ── Excluir / sincronizar evento (feature 151) ───────────────────────────────


@api_bp.route("/events/<int:event_id>", methods=["DELETE"])
@api_login_required
def api_delete_event(event_id: int) -> Any:
    """Exclui o evento do banco e do Google (feature 151). RBAC: `_CAN_DELETE` (Comercial/SA).

    Recusa a exclusão de um evento líder de grupo com 409 (desagrupar antes) — paridade com o Jinja.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_delete():
        return json_error("Sem permissão", 403)

    from app.calendar.routes import _delete_event_flow

    deleted = _delete_event_flow(
        event,
        actor_name=current_user.name,
        actor_role=", ".join(r.name for r in current_user.roles),
    )
    if not deleted:
        return json_error(
            "Desagrupe os eventos satélites antes de excluir este evento", 409
        )
    return jsonify({"ok": True})


@api_bp.route("/events/<int:event_id>/sync", methods=["POST"])
@api_login_required
def api_sync_event(event_id: int) -> Any:
    """Sincroniza um evento com o Google Calendar (feature 151). Sem gate de papel (paridade)."""
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)

    from app.calendar.routes import _sync_single_event_flow

    status = _sync_single_event_flow(event)
    if status == "no_google_id":
        return json_error("Evento sem ID do Google Calendar — não é possível sincronizar", 400)
    if status == "not_found":
        return json_error("Não foi possível buscar o evento no Google Calendar", 502)
    return _event_detail_json(event)


# ── Criar evento (feature 152) ───────────────────────────────────────────────


def _client_pairs_from_json(raw: list) -> list[tuple[int, str]]:
    """Normaliza clientes vindos do corpo JSON — mesma regra de `_parse_client_pairs` (routes.py):
    dedup por cliente, ids inexistentes ignorados, relação fora da lista vira "Outros".
    """
    pairs: list[tuple[int, str]] = []
    seen: set[int] = set()
    for item in raw:
        cid = item.get("client_id")
        if not isinstance(cid, int) or cid in seen or Client.query.get(cid) is None:
            continue
        rel = (item.get("relation") or "Contratante").strip()
        if rel not in CLIENT_RELATION_TIPOS:
            rel = "Outros"
        seen.add(cid)
        pairs.append((cid, rel))
    return pairs


def _build_create_event_data(body: dict) -> dict:
    """Converte o corpo JSON de `POST /api/events` no `data` esperado pelo núcleo de criação
    (feature 152, `app/calendar/routes.py`). Sem nenhum campo de arquivo — money/ids já vêm como
    número do React (Princípio VII), sem precisar de `parse_brl`.
    """
    characters = [
        {
            "name": (c.get("name") or "").strip(),
            "figurino_sheet_id": c.get("figurino_sheet_id"),
            "cache_value": c.get("cache_value"),
            "needs_makeup": bool(c.get("needs_makeup")),
            "is_singer": bool(c.get("is_singer")),
            "talent_id": c.get("talent_id"),
        }
        for c in body.get("characters") or []
    ]
    observations = [
        {
            "obs_type": o.get("obs_type"),
            "content": o.get("content") or "",
            "label": o.get("label") or "",
            "file_path": None,
        }
        for o in body.get("observations") or []
        if o.get("obs_type") in ("text", "link")
    ]
    sale_date_raw = body.get("sale_date")
    payment_due_raw = body.get("payment_due_date")

    return {
        "title": (body.get("title") or "").strip(),
        "event_type": (body.get("event_type") or "").strip(),
        "date_str": body.get("date") or "",
        "start_str": body.get("start") or "",
        "end_str": body.get("end") or "",
        "location": (body.get("location") or "").strip(),
        "description": (body.get("description") or "").strip(),
        "needs_rehearsal": bool(body.get("needs_rehearsal")),
        "sale_value": body.get("sale_value"),
        "sale_value_gross": body.get("sale_value_gross"),
        "transport_value": body.get("transport_value"),
        "acrescimo_value": body.get("acrescimo_value"),
        "with_invoice": bool(body.get("with_invoice")),
        "invoice_filename": None,
        "is_cortesia_permuta": bool(body.get("is_cortesia_permuta")),
        "seller_id": body.get("seller_id"),
        "sale_date": date.fromisoformat(sale_date_raw) if sale_date_raw else None,
        "payment_method": body.get("payment_method") or None,
        "payment_installments": body.get("payment_installments"),
        "payment_due_date": date.fromisoformat(payment_due_raw) if payment_due_raw else None,
        "orcamento_history_id": body.get("orcamento_history_id"),
        "duracao": str(body.get("duracao") or "1"),
        "characters": characters,
        "orc_caches": body.get("orc_caches") or [],
        "acrescimos": body.get("acrescimos") or [],
        "coordinator_talent_id": body.get("coordinator_talent_id"),
        "client_pairs": _client_pairs_from_json(body.get("clients") or []),
        "form_response_id": body.get("form_response_id"),
        "has_reembolso": bool(body.get("has_reembolso")),
        "reembolso_description": (body.get("reembolso_description") or "").strip(),
        "reembolso_amount": body.get("reembolso_amount"),
        "reembolso_invoice_file_path": None,
        "observations": observations,
    }


@api_bp.route("/events", methods=["POST"])
@api_login_required
def api_create_event() -> Any:
    """Cria um evento novo (feature 152). RBAC: `_CAN_CREATE` (Comercial/Superadmin).

    Corpo JSON sem nenhum campo de arquivo (nota fiscal/contrato/comprovantes/reembolso/
    observação-imagem ficam fora nesta fatia — só o Jinja lida com upload). Sucesso devolve o
    evento no formato de leitura da 145 + `warnings` (conflitos de agenda de talento
    pré-escalado, se houver).
    """
    if not _can_create_event():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    data = _build_create_event_data(body)

    from app.calendar.routes import _validate_event_core

    errors = _validate_event_core(data)
    if errors:
        return json_error("Corrija os campos destacados", 400, fields=errors)

    from app.calendar.routes import CALENDAR_ID, _build_start_end
    from app.calendar.routes import insert_event as _insert_event

    title = data["title"]
    event_type = data["event_type"]
    import re

    clean_title = re.sub(r"^\s*\([^)]*\)\s*", "", title).strip() if title else title
    gc_title = f"({event_type}) {clean_title}" if event_type else title
    d = date.fromisoformat(data["date_str"])
    st, et = _build_start_end(d, data["start_str"], data["end_str"])

    try:
        created = _insert_event(
            CALENDAR_ID, gc_title, st, et,
            description=data["description"], location=data["location"],
        )
    except Exception:
        return json_error(
            "Não foi possível criar o evento na Agenda do Google agora. "
            "Verifique a conexão e tente novamente.",
            502,
        )

    from app.calendar.routes import _create_event_core

    event, conflicts = _create_event_core(
        data,
        google_event_id=created["id"],
        gc_title=gc_title,
        actor_name=current_user.name,
        actor_id=current_user.id,
        actor_role=", ".join(r.name for r in current_user.roles),
    )

    impersonate = session.get("impersonate_role")
    result = serialize_event_detail(event, current_user, impersonate)
    result["warnings"] = conflicts
    return jsonify(result), 201
