"""Endpoints de ESCRITA da Agenda/Eventos (feature 146). Fatia US1: escalar casting.

Cada ação reusa o núcleo em `app/calendar/casting_ops.py` (mesma lógica do handler Jinja) e
devolve o evento no formato de leitura da feature 145. As ações Jinja seguem intactas.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from flask import current_app, jsonify, request, session
from flask_login import current_user

from app.api import api_bp
from app.api.agenda_read import serialize_event_detail
from app.api_utils import api_login_required, json_error
from app.constants import CLIENT_RELATION_TIPOS, RoleName
from app.models import (
    CalendarEvent,
    Client,
    EventContract,
    EventObservation,
    EventPayment,
    EventReimbursement,
    EventRole,
    db,
)

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


def _can_manage_sale() -> bool:
    """Gate de nota fiscal: mesmo `can_vendas` de `_handle_update_comercial` (Jinja) — a nota
    fiscal hoje só é criada dentro daquele formulário, gateado a Comercial/Financeiro/Superadmin.
    """
    return any(
        r.name.upper() in (RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN)
        for r in current_user.roles
    )


def _can_confirm() -> bool:
    """Gate de confirmar/desconfirmar o evento: Comercial ou Superadmin (paridade com o Jinja)."""
    return any(
        r.name.upper() in (RoleName.COMERCIAL, RoleName.SUPERADMIN) for r in current_user.roles
    )


def _can_delete() -> bool:
    """Gate de excluir/cancelar o evento (`_CAN_DELETE` = só Superadmin, feature 224)."""
    from app.calendar.routes import _CAN_DELETE

    return any(r.name.upper() in _CAN_DELETE for r in current_user.roles)


def _can_request_delete() -> bool:
    """Gate de SOLICITAR a exclusão (`_CAN_REQUEST_DELETE` = Comercial ou Superadmin)."""
    from app.calendar.routes import _CAN_REQUEST_DELETE

    return any(r.name.upper() in _CAN_REQUEST_DELETE for r in current_user.roles)


def _can_create_event() -> bool:
    """Gate de criar evento (`_CAN_CREATE` = Comercial ou Superadmin) — paridade com o Jinja."""
    from app.calendar.routes import _CAN_CREATE

    return any(r.name.upper() in _CAN_CREATE for r in current_user.roles)


def _event_detail_json(event: Any) -> Any:
    """Serializa o evento atualizado com o RBAC do usuário atual (resposta padrão das escritas)."""
    impersonate = session.get("impersonate_role")
    return jsonify(serialize_event_detail(event, current_user, impersonate))


def _decimal_from_form(raw: str | None) -> Decimal | None:
    """Converte um campo de valor vindo de `multipart/form-data` (feature 153).

    O React envia o número puro (mesma convenção do corpo JSON — Princípio VII: o valor
    formatado em BRL é só de exibição), então o parsing aqui é direto, sem `parse_brl`
    (que espera o formato BRL "1.234,56" usado pelo Jinja).

    Args:
        raw: valor do campo de formulário, ou None.

    Returns:
        O `Decimal` correspondente, ou None se ausente/vazio/inválido.
    """
    if raw is None or not raw.strip():
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


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

    from app.calendar.casting_ops import _UNSET, assign_role

    assign_role(
        event,
        role,
        talent_id=data.get("talent_id"),
        cache_value=data.get("cache_value"),
        # Repasse CONDICIONAL (feature 239): esta tela não edita o adicional de transporte e
        # nunca manda a chave. Passar `data.get(...)` = None fazia o `assign_role` gravar NULL
        # por cima do valor existente a cada "Salvar" — o `_UNSET` é o "não mexe nisso".
        travel_cache=data["travel_cache"] if "travel_cache" in data else _UNSET,
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


@api_bp.route("/roles/<int:role_id>/transporte", methods=["POST"])
@api_login_required
def api_marcar_transporte(role_id: int) -> Any:
    """Marca o integrante como responsável pelo transporte fora de SP (feature 239).

    RBAC = `_CAN_EDIT_EVENT` — mesmo gate de quem escala o casting (decisão 4). O marcador só
    existe em evento fora de SP: dentro de SP não há veículo a ratear, então a marcação é
    recusada em vez de virar um teto inflado sem lastro.
    """
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)
    event = CalendarEvent.query.get(role.event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not event.is_outside_sp:
        return json_error("O transporte só vale para evento fora de São Paulo.", 400)

    from app.calendar.casting_ops import set_transporte

    set_transporte(
        event, role, faz_transporte=True, actor_name=current_user.name, tz=_TZ_SP
    )
    return _event_detail_json(event)


@api_bp.route("/roles/<int:role_id>/transporte", methods=["DELETE"])
@api_login_required
def api_desmarcar_transporte(role_id: int) -> Any:
    """Desmarca o responsável pelo transporte (feature 239) — volta do `POST` de mesma rota.

    Sem a guarda de fora-SP do POST: um evento que deixou de ser fora de SP precisa poder
    limpar a marcação que já estava lá.
    """
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)
    event = CalendarEvent.query.get(role.event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)

    from app.calendar.casting_ops import set_transporte

    set_transporte(
        event, role, faz_transporte=False, actor_name=current_user.name, tz=_TZ_SP
    )
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
    """Adiciona uma observação (texto/link/imagem) ao evento (features 150/153).

    Sem gate de papel (paridade com o `@login_required` do Jinja). Aceita dois content-types:
    JSON para texto/link (inalterado desde a feature 150) e `multipart/form-data` para imagem
    (feature 153, exige arquivo) — endpoint único, sem duplicar rota (Princípio I).
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)

    is_multipart = bool(request.content_type) and request.content_type.startswith("multipart/")
    file_storage = None
    if is_multipart:
        data = request.form
        obs_type = data.get("obs_type")
        file_storage = request.files.get("image")
    else:
        data = request.get_json(silent=True) or {}
        obs_type = data.get("obs_type")

    if obs_type not in ("text", "link", "image"):
        return json_error("Tipo de observação inválido", 400, {"obs_type": "Use texto, link ou imagem"})
    if obs_type == "image" and not (file_storage and file_storage.filename):
        return json_error("Anexe uma imagem para a observação", 400, {"image": "Obrigatório"})

    from app.calendar.observation_ops import add_observation
    from app.calendar.routes import _save_file_upload
    from app.storage import ALLOWED_IMAGE_EXTENSIONS

    # Allowlist estrita de imagem: este endpoint não tem gate de papel, então é o caminho mais
    # barato para plantar um arquivo executável em `/uploads` (mesmo origin das SPAs).
    file_path = (
        _save_file_upload(
            file_storage,
            current_app.config["UPLOAD_EVENT_OBS"],
            "event_obs",
            allowed=ALLOWED_IMAGE_EXTENSIONS,
        )
        if obs_type == "image"
        else None
    )
    if obs_type == "image" and not file_path:
        return json_error(
            "Imagem inválida: envie JPG, PNG, WEBP ou GIF de até 20 MB",
            400,
            {"image": "Formato ou tamanho não aceito"},
        )

    obs = add_observation(
        event,
        obs_type=obs_type,
        content=data.get("content"),
        label=data.get("label"),
        file_path=file_path,
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


@api_bp.route("/events/<int:event_id>/impacto-exclusao")
@api_login_required
def api_impacto_exclusao(event_id: int) -> Any:
    """O que será perdido/afetado ao excluir ou cancelar (feature 224). RBAC: `_CAN_DELETE`.

    A tela abre o diálogo com isso: qual das duas ações vai acontecer, quanto a cliente já
    pagou, que comissão está em jogo e quem está escalado. Antes o diálogo só perguntava
    "tem certeza?", e foi assim que um evento com pagamento recebido foi parar no lixo.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_delete():
        return json_error("Sem permissão", 403)

    from app.calendar.cancel_ops import resumo_impacto

    return jsonify(resumo_impacto(event))


@api_bp.route("/events/<int:event_id>", methods=["DELETE"])
@api_login_required
def api_delete_event(event_id: int) -> Any:
    """Exclui o evento do banco **e do Google Agenda** (feature 151). RBAC: só Superadmin (224).

    Recusa com 409 o evento líder de grupo (desagrupar antes) e o evento que tem dinheiro preso
    — esse é caso de cancelamento, não de exclusão: apagar destruiria o pagamento recebido e a
    comissão, que são justamente o lastro da devolução.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_delete():
        return json_error("Sem permissão", 403)

    from app.calendar.cancel_ops import pode_excluir
    from app.calendar.routes import _delete_event_flow

    if not pode_excluir(event):
        return json_error(
            "Este evento tem venda, pagamento, contrato ou elenco escalado — use o "
            "cancelamento, que preserva o registro e trata a devolução.",
            409,
        )

    deleted, aviso = _delete_event_flow(
        event,
        actor_name=current_user.name,
        actor_role=", ".join(r.name for r in current_user.roles),
    )
    if not deleted:
        return json_error(
            "Desagrupe os eventos satélites antes de excluir este evento", 409
        )
    return jsonify({"ok": True, "aviso": aviso})


@api_bp.route("/events/<int:event_id>/cancelar", methods=["POST"])
@api_login_required
def api_cancelar_evento(event_id: int) -> Any:
    """Cancela o evento, resolve a comissão e registra a devolução (feature 224).

    RBAC: só Superadmin. Corpo: `{motivo, devolucao: {valor, nome, pix, observacao}}`.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_delete():
        return json_error("Sem permissão", 403)

    from app.calendar.cancel_ops import CancelValidationError, cancelar_evento

    body = request.get_json(silent=True) or {}
    try:
        resultado = cancelar_evento(
            event,
            motivo=body.get("motivo") or "",
            devolucao=body.get("devolucao") or {},
            actor=current_user,
        )
    except CancelValidationError as exc:
        return json_error(exc.message, 400, fields={"motivo": exc.message})
    return jsonify({"ok": True, **resultado})


@api_bp.route("/events/<int:event_id>/solicitar-exclusao", methods=["POST"])
@api_login_required
def api_solicitar_exclusao(event_id: int) -> Any:
    """Comercial pede a exclusão; o Superadmin decide (feature 224). Corpo: `{motivo}`."""
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_request_delete():
        return json_error("Sem permissão", 403)

    from app.calendar.cancel_ops import CancelValidationError, solicitar_exclusao

    body = request.get_json(silent=True) or {}
    try:
        solicitar_exclusao(event, motivo=body.get("motivo") or "", actor=current_user)
    except CancelValidationError as exc:
        return json_error(exc.message, 400, fields={"motivo": exc.message})
    return jsonify({"ok": True})


@api_bp.route("/events/<int:event_id>/solicitar-exclusao", methods=["DELETE"])
@api_login_required
def api_recusar_solicitacao(event_id: int) -> Any:
    """Superadmin recusa a solicitação de exclusão (feature 224)."""
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_delete():
        return json_error("Sem permissão", 403)

    from app.calendar.cancel_ops import CancelValidationError, recusar_solicitacao

    body = request.get_json(silent=True) or {}
    try:
        recusar_solicitacao(event, actor=current_user, motivo=body.get("motivo") or "")
    except CancelValidationError as exc:
        return json_error(exc.message, 400)
    return jsonify({"ok": True})


@api_bp.route("/events/cancelamentos")
@api_login_required
def api_listar_cancelamentos() -> Any:
    """Fila do Superadmin: solicitações pendentes + eventos cancelados (feature 224)."""
    if not _can_delete():
        return json_error("Sem permissão", 403)

    from app.calendar.cancel_ops import listar_cancelamentos

    return jsonify(listar_cancelamentos())


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

    # Prefixo "(TIPO)" do título: a normalização virou `build_gc_title` em `event_ops`
    # (feature 239), para a criação e as duas telas de edição usarem a MESMA regra — o sync do
    # Google deriva o tipo desse prefixo.
    from app.calendar.event_ops import build_gc_title

    gc_title = build_gc_title(data["title"], data["event_type"])
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


def _build_update_event_data(body: dict) -> dict:
    """Converte o corpo JSON de `PATCH /api/events/<id>` no `data` esperado por
    `event_ops.update_event_core()` (feature 184). Mesmo formato de `_build_create_event_data`,
    sem os campos exclusivos de criação (`orcamento_history_id`, `duracao`, `orc_caches`,
    `acrescimos`, reembolso, observações) e com `role_id` por personagem, usado para reconciliar
    o elenco em vez de substituí-lo.
    """
    characters = [
        {
            "role_id": c.get("role_id"),
            "name": (c.get("name") or "").strip(),
            "figurino_sheet_id": c.get("figurino_sheet_id"),
            "cache_value": c.get("cache_value"),
            "needs_makeup": bool(c.get("needs_makeup")),
            "is_singer": bool(c.get("is_singer")),
            "talent_id": c.get("talent_id"),
        }
        for c in body.get("characters") or []
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
        "is_cortesia_permuta": bool(body.get("is_cortesia_permuta")),
        "seller_id": body.get("seller_id"),
        "sale_date": date.fromisoformat(sale_date_raw) if sale_date_raw else None,
        "payment_method": body.get("payment_method") or None,
        "payment_installments": body.get("payment_installments"),
        "payment_due_date": date.fromisoformat(payment_due_raw) if payment_due_raw else None,
        "characters": characters,
        "coordinator_talent_id": body.get("coordinator_talent_id"),
        "client_pairs": _client_pairs_from_json(body.get("clients") or []),
        "form_response_id": body.get("form_response_id"),
    }


@api_bp.route("/events/<int:event_id>", methods=["PATCH"])
@api_login_required
def api_update_event(event_id: int) -> Any:
    """Atualiza em bloco os campos centrais de um evento existente (feature 184). RBAC: mesmo
    nível de `_can_create_event()` (Comercial/Superadmin) — o corpo cobre os mesmos campos
    financeiros sensíveis da criação. Núcleo em `event_ops.update_event_core()`.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_create_event():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    data = _build_update_event_data(body)

    from app.calendar.routes import _validate_event_core

    errors = _validate_event_core(data)
    if errors:
        return json_error("Corrija os campos destacados", 400, fields=errors)

    from app.calendar.event_ops import (
        EventCoreUpdateBlocked,
        EventTypeChangeBlocked,
        update_event_core,
    )

    try:
        warnings = update_event_core(
            event,
            data,
            is_superadmin=_is_superadmin(),
            actor_name=current_user.name,
            tz=_TZ_SP,
        )
    except EventCoreUpdateBlocked as exc:
        return json_error(exc.message, 409)
    # Troca de tipo desfeita porque o título novo não chegou à Agenda (feature 239): o resto do
    # salvamento ficou gravado, mas o usuário precisa saber que o tipo continua o de antes —
    # sair de SHOW apaga ensaio e vaga de som para sempre e não pode rodar "no escuro".
    except EventTypeChangeBlocked as exc:
        return json_error(exc.message, 409)

    result = _event_detail_json(event).get_json()
    result["warnings"] = warnings
    return jsonify(result)


# ── Edição pontual por bloco da tela de detalhe (feature 215) ────────────────
# A tela de abas edita cada bloco onde ele é exibido. Estes endpoints são o recorte estreito
# do PATCH em bloco acima: cada um valida e grava SÓ o seu conjunto de campos, então salvar o
# cabeçalho nunca mexe no elenco e salvar os valores nunca mexe nos clientes.


@api_bp.route("/events/<int:event_id>/basico", methods=["PATCH"])
@api_login_required
def api_update_event_basics(event_id: int) -> Any:
    """Título, tipo, data/horário, local e descrição (feature 215).

    RBAC igual ao PATCH em bloco (`_can_create_event`): mudar a data de um evento tem o mesmo
    peso comercial de criá-lo. Reusa `_validate_event_core` para o mesmo mapa de erros por
    campo que o formulário grande devolve.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_create_event():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    data = {
        "title": (body.get("title") or "").strip(),
        "event_type": (body.get("event_type") or "").strip(),
        "date_str": body.get("date") or "",
        "start_str": body.get("start") or "",
        "end_str": body.get("end") or "",
        "location": (body.get("location") or "").strip(),
        # Chave ausente = "não mexa na descrição". Ela é o HTML que também vive no Google
        # Agenda: um corpo sem o campo (ou de um cliente que não edita descrição) não pode
        # apagá-la de raspão — mesma cautela que a tela de edição em bloco já documenta.
        "description": (
            (body.get("description") or "").strip()
            if "description" in body
            else (event.description or "")
        ),
    }

    from app.calendar.routes import _validate_event_core

    errors = _validate_event_core(data)
    # `_validate_event_core` também cobre campos financeiros que este endpoint não recebe —
    # só os erros do recorte de cabeçalho importam aqui.
    errors = {k: v for k, v in errors.items() if k in ("title", "event_date", "event_time")}
    if errors:
        return json_error("Corrija os campos destacados", 400, fields=errors)

    from app.calendar.event_ops import EventTypeChangeBlocked, update_event_basics

    try:
        warnings = update_event_basics(event, data, actor_name=current_user.name, tz=_TZ_SP)
    # Mesma trava do PATCH em bloco: sem o título novo no Google, a troca de tipo é desfeita e
    # devolvida como erro em vez de rodar a parte irreversível às cegas (feature 239).
    except EventTypeChangeBlocked as exc:
        return json_error(exc.message, 409)
    result = _event_detail_json(event).get_json()
    result["warnings"] = warnings
    return jsonify(result)


@api_bp.route("/events/<int:event_id>/comercial", methods=["PATCH"])
@api_login_required
def api_update_event_comercial(event_id: int) -> Any:
    """Valores da venda, forma de pagamento, vendedor e comissão (feature 215).

    RBAC `_can_create_event()` — mesmos campos financeiros sensíveis do PATCH em bloco.

    Recusa satélite de grupo. Isto era um buraco real: o Jinja escondia o formulário de venda para
    satélite, mas a API aceitava gravar. O valor entrava no banco e **sumia de todos os relatórios**
    — o financeiro pula satélites de propósito, porque o dinheiro do contrato mora no principal.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_create_event():
        return json_error("Sem permissão", 403)
    if event.is_satellite:
        return json_error(
            "Este evento é satélite de um grupo: os dados comerciais são do evento principal.",
            409,
            leader_id=event.group_leader_id,
        )

    body = request.get_json(silent=True) or {}
    sale_date_raw = body.get("sale_date")
    payment_due_raw = body.get("payment_due_date")
    try:
        data = {
            "sale_value": body.get("sale_value"),
            "sale_value_gross": body.get("sale_value_gross"),
            "transport_value": body.get("transport_value"),
            "with_invoice": bool(body.get("with_invoice")),
            "is_cortesia_permuta": bool(body.get("is_cortesia_permuta")),
            "seller_id": body.get("seller_id"),
            "sale_date": date.fromisoformat(sale_date_raw) if sale_date_raw else None,
            "commission_rate": body.get("commission_rate"),
            "payment_method": body.get("payment_method") or None,
            "payment_installments": body.get("payment_installments"),
            "payment_due_date": (
                date.fromisoformat(payment_due_raw) if payment_due_raw else None
            ),
        }
    except ValueError:
        return json_error("Data inválida (use AAAA-MM-DD)", 400)

    from app.calendar.event_ops import update_event_comercial
    from app.financeiro.routes import _sync_commission_payment

    update_event_comercial(
        event,
        data,
        actor_name=current_user.name,
        tz=_TZ_SP,
        sincronizar_comissao=_sync_commission_payment,
    )
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/clients", methods=["PUT"])
@api_login_required
def api_set_event_clients(event_id: int) -> Any:
    """Substitui os clientes vinculados ao evento (feature 215).

    `PUT` porque o corpo é a lista inteira, não um delta: `{"clients": []}` desvincula todos.
    Mesma normalização de `_client_pairs_from_json` (dedup, relação fora da lista vira "Outros").
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_create_event():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    pairs = _client_pairs_from_json(body.get("clients") or [])

    from app.calendar.event_ops import set_event_clients

    set_event_clients(event, pairs)
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/form-response", methods=["PATCH"])
@api_login_required
def api_set_event_form_response(event_id: int) -> Any:
    """Vincula ou desvincula o pré-contrato do evento (feature 215).

    `{"form_response_id": null}` desvincula. Uma resposta já presa a outro evento é recusada
    com 409 — nunca roubamos o pré-contrato de outra venda.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_create_event():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    raw = body.get("form_response_id")
    if raw is not None and not isinstance(raw, int):
        return json_error("form_response_id inválido", 400)

    from app.calendar.event_ops import set_event_form_response

    if not set_event_form_response(event, raw) and raw is not None:
        return json_error("Esse pré-contrato já está vinculado a outro evento", 409)
    return _event_detail_json(event)


# ── Upload e gestão de anexos do evento (feature 153) ────────────────────────
# Convenção multipart: specs/144-migracao-react-spa/contracts/api-conventions.md.


@api_bp.route("/events/<int:event_id>/invoices", methods=["POST"])
@api_login_required
def api_add_invoice(event_id: int) -> Any:
    """Adiciona uma nota fiscal ao evento (feature 153). RBAC: Comercial/Financeiro/Superadmin
    (mesmo gate de `_handle_update_comercial`, único lugar onde a nota fiscal é criada hoje).
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_manage_sale():
        return json_error("Sem permissão", 403)

    amount = _decimal_from_form(request.form.get("amount"))
    issue_date_raw = (request.form.get("issue_date") or "").strip()
    try:
        issue_date = date.fromisoformat(issue_date_raw) if issue_date_raw else None
    except ValueError:
        issue_date = None
    file_storage = request.files.get("file")

    from app.calendar.routes import _add_invoice_record

    invoice = _add_invoice_record(event, amount=amount, issue_date=issue_date, file_storage=file_storage)
    if invoice is None:
        return json_error(
            "Informe ao menos o valor, a data ou o arquivo da nota.", 400,
            {"amount": "Preencha ao menos um campo"},
        )
    return _event_detail_json(event), 201


@api_bp.route("/events/<int:event_id>/invoices/<int:invoice_id>", methods=["PATCH"])
@api_login_required
def api_update_invoice(event_id: int, invoice_id: int) -> Any:
    """Edita uma nota fiscal do evento (feature 251). Corpo `multipart`, como o POST irmão.

    Campos: `amount`, `issue_date` e o arquivo opcional em `file`. Anexar arquivo **emite** a
    nota; reenviar o mesmo não reescreve a data de emissão. Sem `file`, o anexo atual é
    preservado — um PATCH sem upload é edição de valor ou data, não remoção do anexo.

    Até aqui a API só sabia **adicionar** nota (`POST /invoices`): editar a lista era exclusivo do
    formulário Jinja, que a fase 6 apaga.
    """
    from app.models import EventInvoice

    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_manage_sale():
        return json_error("Sem permissão", 403)

    nota = EventInvoice.query.filter_by(id=invoice_id, event_id=event_id).first()
    if nota is None:
        return json_error("Nota fiscal não encontrada", 404)

    from app.calendar import comercial_ops
    from app.calendar.routes import _save_nf_file

    comercial_ops.atualizar_nota(
        nota,
        amount=_decimal_from_form(request.form.get("amount")),
        issue_date=(request.form.get("issue_date") or "").strip(),
        arquivo=_save_nf_file(request.files.get("file")),
        agora=datetime.now(tz=_TZ_SP),
    )
    db.session.commit()
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/invoices/<int:invoice_id>", methods=["DELETE"])
@api_login_required
def api_delete_invoice(event_id: int, invoice_id: int) -> Any:
    """Remove uma nota fiscal do evento (feature 251).

    O arquivo em disco não é apagado — nota fiscal é documento contábil.
    """
    from app.models import EventInvoice

    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_manage_sale():
        return json_error("Sem permissão", 403)

    nota = EventInvoice.query.filter_by(id=invoice_id, event_id=event_id).first()
    if nota is None:
        return json_error("Nota fiscal não encontrada", 404)

    from app.calendar import comercial_ops

    comercial_ops.remover_nota(nota)
    db.session.commit()
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/acrescimos", methods=["PUT"])
@api_login_required
def api_set_acrescimos(event_id: int) -> Any:
    """Substitui os acréscimos do evento (features 099/100). Corpo: `{"items": [...]}`.

    `PUT` porque o corpo é a lista inteira, não um delta — mesma escolha de
    `PUT /events/<id>/clients`. Mandar `{"items": []}` apaga todos.

    Cada item aceita `tipo`, `descricao`, `is_percent`, `value`, `bv_recipient` e `bv_pix`.
    Acréscimo percentual é congelado em reais sobre a venda **do momento do save**.

    RBAC `_can_manage_sale()`: acréscimo mexe na base da comissão e o BV é repasse a terceiro —
    mesmo gate da nota fiscal, não o de editar evento.

    Até aqui essas linhas só podiam ser escritas pelo formulário Jinja, que a fase 6 apaga.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_manage_sale():
        return json_error("Sem permissão", 403)
    if event.is_satellite:
        return json_error(
            "Este evento é satélite de um grupo: os dados comerciais são do evento principal.",
            409,
            leader_id=event.group_leader_id,
        )

    body = request.get_json(silent=True) or {}
    itens = body.get("items")
    if not isinstance(itens, list):
        return json_error("Envie a lista completa em `items`.", 400, fields={"items": "Obrigatório"})

    from app.calendar import comercial_ops

    comercial_ops.substituir_acrescimos(event, itens)
    db.session.commit()
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/parcelas", methods=["PUT"])
@api_login_required
def api_set_parcelas(event_id: int) -> Any:
    """Substitui o cronograma de parcelas do evento (feature 065). Corpo: `{"items": [...]}`.

    Cada item aceita `due_date` (ISO) e `amount`; parcela sem um dos dois é ignorada, como no
    editor antigo. `{"items": []}` apaga o cronograma.

    Não valida a soma contra o valor da venda de propósito — o Jinja também não valida, e a
    planilha de pagamentos existe justamente para mostrar a diferença.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_manage_sale():
        return json_error("Sem permissão", 403)
    if event.is_satellite:
        return json_error(
            "Este evento é satélite de um grupo: os dados comerciais são do evento principal.",
            409,
            leader_id=event.group_leader_id,
        )

    body = request.get_json(silent=True) or {}
    itens = body.get("items")
    if not isinstance(itens, list):
        return json_error("Envie a lista completa em `items`.", 400, fields={"items": "Obrigatório"})

    from app.calendar import comercial_ops

    comercial_ops.substituir_parcelas(event, itens)
    db.session.commit()
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/contracts", methods=["POST"])
@api_login_required
def api_add_contract(event_id: int) -> Any:
    """Adiciona um contrato ao evento (feature 153). RBAC: `_CAN_EDIT_EVENT` — o handler
    `_handle_add_contract` não checa papel por dentro, mas todo POST de `/events/<id>` no
    Jinja já é gateado por `_CAN_EDIT_EVENT` no dispatcher (`event_detail`), então esse é o
    gate efetivo hoje."""
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)

    file_storage = request.files.get("file")
    is_signed = request.form.get("is_signed", "false").lower() == "true"

    from app.calendar.routes import _add_contract_record

    contract = _add_contract_record(event, file_storage=file_storage, is_signed=is_signed)
    if contract is None:
        return json_error(
            "Selecione o arquivo do contrato (até 10 MB).", 400, {"file": "Obrigatório"}
        )
    return _event_detail_json(event), 201


@api_bp.route("/contracts/<int:contract_id>", methods=["DELETE"])
@api_login_required
def api_delete_contract(contract_id: int) -> Any:
    """Exclui um contrato (feature 153). RBAC: só superadmin (paridade com `_handle_delete_contract`)."""
    contract = EventContract.query.get(contract_id)
    if contract is None:
        return json_error("Contrato não encontrado", 404)
    if not _is_superadmin():
        return json_error("Apenas o super admin pode excluir contratos", 403)
    event = CalendarEvent.query.get(contract.event_id)

    from app.calendar.routes import _delete_contract_record

    _delete_contract_record(contract)
    db.session.commit()
    return _event_detail_json(event)


@api_bp.route("/contracts/<int:contract_id>/toggle-signed", methods=["POST"])
@api_login_required
def api_toggle_contract_signed(contract_id: int) -> Any:
    """Alterna `is_signed` de um contrato (feature 153). RBAC: só superadmin (paridade com
    `_handle_toggle_contract_signed`)."""
    contract = EventContract.query.get(contract_id)
    if contract is None:
        return json_error("Contrato não encontrado", 404)
    if not _is_superadmin():
        return json_error("Apenas o super admin pode alterar o status do contrato", 403)
    event = CalendarEvent.query.get(contract.event_id)

    from app.calendar.routes import _toggle_contract_signed

    _toggle_contract_signed(contract)
    db.session.commit()
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/payments", methods=["POST"])
@api_login_required
def api_add_payment(event_id: int) -> Any:
    """Registra um pagamento de cachê com comprovante (feature 153). RBAC: `_CAN_EDIT_EVENT`
    (gate efetivo do dispatcher `event_detail` no Jinja — `_handle_add_payment` não checa
    papel por dentro, mas todo POST daquela rota já passa por esse gate antes)."""
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)

    amount = _decimal_from_form(request.form.get("amount"))
    file_storage = request.files.get("file")

    from app.calendar.routes import _add_payment_record

    payment = _add_payment_record(event, amount=amount, file_storage=file_storage)
    if payment is None:
        return json_error(
            "Informe o valor e anexe o comprovante para adicionar o pagamento.", 400,
            {"amount": "Obrigatório", "file": "Obrigatório"},
        )
    return _event_detail_json(event), 201


@api_bp.route("/payments/<int:payment_id>", methods=["PATCH"])
@api_login_required
def api_edit_payment(payment_id: int) -> Any:
    """Corrige o valor de um comprovante de pagamento (feature 153). RBAC: só superadmin
    (paridade com `_handle_edit_payment`)."""
    payment = EventPayment.query.get(payment_id)
    if payment is None:
        return json_error("Comprovante não encontrado", 404)
    if not _is_superadmin():
        return json_error("Apenas o super admin pode editar comprovantes", 403)
    event = CalendarEvent.query.get(payment.event_id)

    body = request.get_json(silent=True) or {}
    amount = Decimal(str(body["amount"])) if body.get("amount") is not None else None

    from app.calendar.routes import _edit_payment_amount

    if not _edit_payment_amount(payment, amount=amount):
        return json_error("Informe um valor válido para o comprovante", 400, {"amount": "Obrigatório"})
    db.session.commit()
    return _event_detail_json(event)


@api_bp.route("/payments/<int:payment_id>", methods=["DELETE"])
@api_login_required
def api_delete_payment(payment_id: int) -> Any:
    """Exclui um comprovante de pagamento (feature 153). RBAC: só superadmin (paridade com
    `_handle_delete_payment`)."""
    payment = EventPayment.query.get(payment_id)
    if payment is None:
        return json_error("Comprovante não encontrado", 404)
    if not _is_superadmin():
        return json_error("Apenas o super admin pode excluir comprovantes", 403)
    event = CalendarEvent.query.get(payment.event_id)

    from app.calendar.routes import _delete_payment_record

    _delete_payment_record(payment)
    db.session.commit()
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/reimbursements", methods=["POST"])
@api_login_required
def api_add_reimbursement(event_id: int) -> Any:
    """Registra um reembolso a cobrar da cliente (feature 153). RBAC: `_CAN_EDIT_EVENT` (gate
    efetivo do dispatcher `event_detail` — `_handle_add_reembolso` não checa papel por dentro)."""
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)

    description = request.form.get("description", "")
    amount = _decimal_from_form(request.form.get("amount"))
    file_storage = request.files.get("file")

    from app.calendar.routes import _add_reimbursement_record

    reimbursement = _add_reimbursement_record(
        event,
        description=description,
        amount=amount,
        file_storage=file_storage,
        created_by_id=current_user.id,
    )
    if reimbursement is None:
        return json_error(
            "Informe a descrição e o valor do reembolso.", 400,
            {"description": "Obrigatório", "amount": "Obrigatório"},
        )
    return _event_detail_json(event), 201


@api_bp.route("/reimbursements/<int:reimbursement_id>/collect", methods=["POST"])
@api_login_required
def api_collect_reimbursement(reimbursement_id: int) -> Any:
    """Marca um reembolso como cobrado (feature 153). RBAC: `_CAN_EDIT_EVENT` (gate efetivo do
    dispatcher `event_detail` — `_handle_collect_reembolso` não checa papel por dentro)."""
    reimbursement = EventReimbursement.query.get(reimbursement_id)
    if reimbursement is None:
        return json_error("Reembolso não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)
    if reimbursement.is_collected:
        return json_error("Esse reembolso já foi marcado como cobrado", 400)
    event = CalendarEvent.query.get(reimbursement.event_id)

    collected_amount = _decimal_from_form(request.form.get("collected_amount"))
    file_storage = request.files.get("file")

    from app.calendar.routes import _collect_reimbursement_record

    ok = _collect_reimbursement_record(
        reimbursement,
        collected_amount=collected_amount,
        file_storage=file_storage,
        collected_by_id=current_user.id,
    )
    if not ok:
        return json_error(
            "Informe o valor recebido e anexe o comprovante para marcar como cobrado.", 400,
            {"collected_amount": "Obrigatório", "file": "Obrigatório"},
        )
    return _event_detail_json(event)


@api_bp.route("/reimbursements/<int:reimbursement_id>", methods=["DELETE"])
@api_login_required
def api_delete_reimbursement(reimbursement_id: int) -> Any:
    """Exclui um reembolso (feature 153). RBAC: só superadmin (paridade com
    `_handle_delete_reembolso`)."""
    reimbursement = EventReimbursement.query.get(reimbursement_id)
    if reimbursement is None:
        return json_error("Reembolso não encontrado", 404)
    if not _is_superadmin():
        return json_error("Apenas o super admin pode excluir reembolsos", 403)
    event = CalendarEvent.query.get(reimbursement.event_id)

    from app.calendar.routes import _delete_reimbursement_record

    _delete_reimbursement_record(reimbursement)
    db.session.commit()
    return _event_detail_json(event)


# ── Detalhe do evento — feature 190 (refatoração da tela /events/:id) ─────────
# As ações que a tela nova precisa e que só existiam como `action=` do POST Jinja de
# `/events/<id>`. Cada uma reusa o núcleo em `app/calendar/event_ops.py` (Princípio I) e
# devolve o evento serializado, como todas as escritas desta camada.


def _can_ensaio_material() -> bool:
    """Gate dos materiais de ensaio (`_CAN_ENSAIO_MATERIAL` = Ensaio/Casting/Superadmin)."""
    from app.calendar.routes import _CAN_ENSAIO_MATERIAL

    return any(r.name.upper() in _CAN_ENSAIO_MATERIAL for r in current_user.roles)


def _role_of_event(role_id: int) -> tuple[Any, Any] | None:
    """Carrega o cargo e o evento dono. Devolve None se o cargo não existe."""
    role = EventRole.query.get(role_id)
    if role is None:
        return None
    return role, CalendarEvent.query.get(role.event_id)


@api_bp.route("/roles/<int:role_id>/payment-status", methods=["POST"])
@api_login_required
def api_set_role_payment_status(role_id: int) -> Any:
    """Grava o status de pagamento do cachê de um cargo (feature 190).

    RBAC = `_CAN_EDIT_EVENT`, o gate efetivo do `action=set_payment_status` no Jinja.
    """
    found = _role_of_event(role_id)
    if found is None:
        return json_error("Cargo não encontrado", 404)
    role, event = found
    if not _can_edit_event():
        return json_error("Sem permissão", 403)

    from app.calendar.event_ops import set_payment_status

    status = (request.get_json(silent=True) or {}).get("payment_status", "")
    if not set_payment_status(event, role, status=status):
        return json_error(
            "Status de pagamento inválido.", 400, {"payment_status": "Valor não aceito"}
        )
    return _event_detail_json(event)


@api_bp.route("/roles/<int:role_id>/figurino-sheet", methods=["POST"])
@api_login_required
def api_link_figurino_sheet(role_id: int) -> Any:
    """Vincula/desvincula a ficha de figurino de um cargo (feature 190).

    Corpo: ``{"sheet_id": <int>}`` para vincular, ``{"sheet_id": null}`` para desvincular.
    RBAC = `_CAN_EDIT_EVENT`, o gate efetivo do `action=link_figurino` no Jinja.
    """
    found = _role_of_event(role_id)
    if found is None:
        return json_error("Cargo não encontrado", 404)
    role, event = found
    if not _can_edit_event():
        return json_error("Sem permissão", 403)

    from app.calendar.event_ops import link_figurino_sheet

    raw = (request.get_json(silent=True) or {}).get("sheet_id")
    sheet_id = int(raw) if raw else None
    ok = link_figurino_sheet(
        event, role, sheet_id=sheet_id, actor_name=current_user.name, tz=_TZ_SP
    )
    if not ok:
        return json_error("Ficha de figurino não encontrada.", 404)
    return _event_detail_json(event)


@api_bp.route("/roles/<int:role_id>/figurino-done", methods=["DELETE"])
@api_login_required
def api_clear_figurino_done(role_id: int) -> Any:
    """Desmarca o figurino separado de um cargo (feature 190) — volta do `POST` de mesma rota.

    A tela nova trata "Separado" como caixa de seleção; o fluxo Jinja só tinha o caminho de ida.
    """
    found = _role_of_event(role_id)
    if found is None:
        return json_error("Cargo não encontrado", 404)
    role, event = found
    if not _can_edit_event():
        return json_error("Sem permissão", 403)

    from app.calendar.event_ops import clear_figurino_done

    clear_figurino_done(event, role, actor_name=current_user.name, tz=_TZ_SP)
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/travel-estimate", methods=["POST"])
@api_login_required
def api_travel_estimate(event_id: int) -> Any:
    """Recalcula a estimativa de trajeto pelo Google Maps e devolve o evento atualizado.

    Reusa `_fetch_travel_data` (fonte única da chamada à Distance Matrix), que grava
    `travel_time_minutes`/`travel_distance_km` no evento. RBAC = `_CAN_EDIT_EVENT`.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)
    if not event.location:
        return json_error("Evento sem endereço de destino.", 400, {"location": "Obrigatório"})

    from app.calendar.routes import _fetch_travel_data
    from app.models import SiteSetting

    if not _fetch_travel_data(event, SiteSetting.query.get(1)):
        return json_error(
            "Não foi possível estimar o trajeto — verifique o endereço do evento.", 400
        )
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/materials", methods=["POST"])
@api_login_required
def api_add_material(event_id: int) -> Any:
    """Adiciona um material de ensaio ao evento (feature 190).

    Aceita dois content-types, como `api_add_observation`: `multipart/form-data` com `file`
    (+ `label` opcional) para arquivo, e JSON `{"url", "label"}` para link.
    RBAC = `_CAN_ENSAIO_MATERIAL` (paridade com as rotas Jinja de ensaio).
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_ensaio_material():
        return json_error("Sem permissão", 403)

    from app.calendar.event_ops import add_ensaio_file, add_ensaio_link

    is_multipart = bool(request.content_type) and request.content_type.startswith("multipart/")
    if is_multipart:
        file_storage = request.files.get("file")
        label = (request.form.get("label") or "").strip()
        material = add_ensaio_file(
            event, file_storage=file_storage, label=label, user_id=current_user.id
        )
        if material is None:
            return json_error(
                "Selecione um arquivo de até 20 MB.", 400, {"file": "Obrigatório"}
            )
        return _event_detail_json(event), 201

    body = request.get_json(silent=True) or {}
    material = add_ensaio_link(
        event,
        url=(body.get("url") or "").strip(),
        label=(body.get("label") or "").strip(),
        user_id=current_user.id,
    )
    if material is None:
        return json_error("Informe a URL do material.", 400, {"url": "Obrigatório"})
    return _event_detail_json(event), 201


@api_bp.route("/materials/<int:material_id>", methods=["DELETE"])
@api_login_required
def api_delete_material(material_id: int) -> Any:
    """Remove um material de ensaio (arquivo físico incluído). RBAC = `_CAN_ENSAIO_MATERIAL`."""
    from app.models import EnsaioMaterial

    material = EnsaioMaterial.query.get(material_id)
    if material is None:
        return json_error("Material não encontrado", 404)
    if not _can_ensaio_material():
        return json_error("Sem permissão", 403)
    event = CalendarEvent.query.get(material.event_id)

    from app.calendar.event_ops import delete_ensaio_material

    delete_ensaio_material(material)
    return _event_detail_json(event)


# ── Ensaios: agendamento, edição, exclusão, vínculo e presença (restaurado na 206) ────────


def _can_ensaio() -> bool:
    """Gate das ações de ensaio (`_CAN_ENSAIO` = Ensaio/Casting/Superadmin) — paridade Jinja."""
    from app.calendar.routes import _CAN_ENSAIO

    return any(r.name.upper() in _CAN_ENSAIO for r in current_user.roles)


@api_bp.route("/events/<int:event_id>/ensaios", methods=["POST"])
@api_login_required
def api_create_ensaio(event_id: int) -> Any:
    """Agenda um ensaio para o show (Google Calendar + banco). RBAC = `_CAN_ENSAIO`.

    Corpo JSON: `{"date": "YYYY-MM-DD", "start": "HH:MM", "end": "HH:MM", "description",
    "location_type": "manto"|"outro", "location"}`.
    """
    from app.calendar.event_ops import (
        EnsaioValidationError,
        create_ensaio,
        resolve_ensaio_location,
    )

    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if event.event_type == "ENSAIO":
        return json_error("Um ensaio não pode ter outro ensaio.", 400)
    if not _can_ensaio():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    try:
        create_ensaio(
            event,
            date_str=body.get("date") or "",
            start_str=body.get("start") or "",
            end_str=body.get("end") or "",
            description=body.get("description") or "",
            location=resolve_ensaio_location(
                body.get("location_type") or "manto", body.get("location") or ""
            ),
        )
    except EnsaioValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    except RuntimeError as exc:
        return json_error(f"Erro ao criar no Google Calendar: {exc}", 502)
    return _event_detail_json(event), 201


@api_bp.route("/ensaios/<int:ensaio_id>", methods=["PATCH"])
@api_login_required
def api_update_ensaio(ensaio_id: int) -> Any:
    """Edita data/hora/descrição/local de um ensaio. RBAC = `_CAN_ENSAIO`."""
    from app.calendar.event_ops import EnsaioValidationError, update_ensaio

    ensaio = CalendarEvent.query.get(ensaio_id)
    if ensaio is None or ensaio.event_type != "ENSAIO":
        return json_error("Ensaio não encontrado", 404)
    if not _can_ensaio():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    try:
        warning = update_ensaio(
            ensaio,
            date_str=body.get("date") or "",
            start_str=body.get("start") or "",
            end_str=body.get("end") or "",
            description=body.get("description") or "",
            location=body.get("location") or "",
        )
    except EnsaioValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})

    # A resposta é o detalhe do SHOW pai quando houver (é a tela que o painel refaz).
    target = ensaio.parent or ensaio
    response = serialize_event_detail(target, current_user, session.get("impersonate_role"))
    if warning:
        response["warning"] = warning
    return jsonify(response)


@api_bp.route("/ensaios/<int:ensaio_id>", methods=["DELETE"])
@api_login_required
def api_delete_ensaio(ensaio_id: int) -> Any:
    """Cancela um ensaio (Google + banco), sem afetar o show pai. RBAC = `_CAN_ENSAIO`."""
    from app.calendar.event_ops import delete_ensaio

    ensaio = CalendarEvent.query.get(ensaio_id)
    if ensaio is None or ensaio.event_type != "ENSAIO":
        return json_error("Ensaio não encontrado", 404)
    if not _can_ensaio():
        return json_error("Sem permissão", 403)

    parent = ensaio.parent
    warning = delete_ensaio(ensaio)
    if parent is not None:
        response = serialize_event_detail(parent, current_user, session.get("impersonate_role"))
        if warning:
            response["warning"] = warning
        return jsonify(response)
    return jsonify({"ok": True, "warning": warning})


@api_bp.route("/ensaios/<int:ensaio_id>/vincular", methods=["POST"])
@api_login_required
def api_link_ensaio(ensaio_id: int) -> Any:
    """Vincula um ensaio órfão a um show (feature 063). Corpo: `{"parent_event_id": int}`."""
    from app.calendar.event_ops import link_ensaio_to_show

    ensaio = CalendarEvent.query.get(ensaio_id)
    if ensaio is None or ensaio.event_type != "ENSAIO":
        return json_error("Ensaio não encontrado", 404)
    if not _can_ensaio():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    parent_id = body.get("parent_event_id")
    parent = CalendarEvent.query.get(parent_id) if parent_id else None
    if parent is None or parent.event_type == "ENSAIO" or parent.id == ensaio.id:
        return json_error(
            "Show inválido para vínculo.", 400, fields={"parent_event_id": "Selecione um show"}
        )

    link_ensaio_to_show(ensaio, parent, actor_name=current_user.name)
    return _event_detail_json(ensaio)


@api_bp.route("/events/<int:event_id>/presenca", methods=["POST"])
@api_login_required
def api_assign_presence(event_id: int) -> Any:
    """Define (ou limpa) o Técnico de Som (Presença) — tarefa da equipe de ensaio.

    Corpo: `{"talent_id": int | null}`. RBAC = `_CAN_ENSAIO` (paridade com
    `_handle_assign_tech_presence` do Jinja).
    """
    from zoneinfo import ZoneInfo

    from app.calendar.event_ops import assign_tech_presence

    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_ensaio():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    raw = body.get("talent_id")
    talent_id = int(raw) if isinstance(raw, int) or (isinstance(raw, str) and raw.isdigit()) else None
    if not assign_tech_presence(event, talent_id, tz=ZoneInfo("America/Sao_Paulo")):
        return json_error("Este evento não tem a vaga de presença.", 400)
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/feedback-link", methods=["POST"])
@api_login_required
def api_feedback_link(event_id: int) -> Any:
    """Gera (na primeira vez) e devolve o link público de avaliação da cliente (feature 130).

    RBAC: Comercial ou Superadmin. Desde a fase 3 da remoção do Jinja este é o **único** gerador
    do link — o gêmeo `feedback.gerar_link` foi apagado junto com a superfície Jinja.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_confirm():
        return json_error("Sem permissão", 403)

    from app.calendar.event_ops import ensure_feedback_token

    token = ensure_feedback_token(event)
    # PUBLIC_BASE_URL, não request.url_root: atrás do proxy reverso (206) o Host que chega
    # aqui é o do serviço backend (changeOrigin) — url_root geraria um link com o domínio
    # interno da Railway em vez do endereço público da plataforma.
    base = (current_app.config.get("PUBLIC_BASE_URL") or request.url_root).rstrip("/")
    # `/catalogo/avaliar/...` e não `/avaliar/...`: este é o endereço da página React (o bundle da
    # vitrine roda com `basename="/catalogo"`). O caminho antigo continua vivo como 302 em
    # `feedback.avaliar`, para os links já enviados às clientes — o token não expira.
    return jsonify({"url": f"{base}/catalogo/avaliar/{token}"})


# ── Agrupamento comercial de eventos (features 053/054/055) ──────────────────────────────────
#
# O núcleo (regras, snapshot, histórico) mora em `app/calendar/group_ops.py`, compartilhado com os
# handlers Jinja enquanto eles existirem. Aqui fica só o HTTP: RBAC, leitura do corpo e resposta.
#
# A busca de candidatos vive neste arquivo, e não em `agenda.py`, porque só serve ao diálogo de
# agrupar — mantê-la junto evita que alguém mude a regra de elegibilidade num lugar só.


def _can_group() -> bool:
    """Gate de mexer em grupo: Comercial, Financeiro ou Superadmin (paridade com o Jinja)."""
    from app.calendar import group_ops

    return group_ops.pode_agrupar(current_user)


def _grupo_detalhe_json(event: Any, leader_id: int | None = None) -> Any:
    """Detalhe do evento com o `leader_id` no topo, para a tela saber se precisa navegar.

    O principal pode NÃO ser o evento de onde a ação partiu — quem agrupa pode eleger outro como
    principal, e aí a página em que a pessoa está acabou de virar satélite.
    """
    payload = serialize_event_detail(event, current_user, session.get("impersonate_role"))
    if leader_id is not None:
        payload["leader_id"] = leader_id
    return jsonify(payload)


@api_bp.route("/events/<int:event_id>/grupo/candidatos", methods=["GET"])
@api_login_required
def api_grupo_candidatos(event_id: int) -> Any:
    """Eventos que podem entrar no grupo, filtrados por `?q=` no SERVIDOR.

    O Jinja carregava TODOS os eventos não-ENSAIO do banco (354 hoje) como checkbox no HTML e
    filtrava no navegador. Aqui a busca é no servidor, limitada — a tela nova não deve herdar
    aquele despejo.

    Cada item traz `blocked_reason` em vez de sumir da lista: um evento que já está em outro grupo
    precisa aparecer explicando por que não pode ser marcado, senão a pessoa procura e não acha.
    """
    from app.calendar import group_ops
    from app.calendar.event_ops import SEARCH_MIN_CHARS, search_events

    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_group():
        return json_error("Sem permissão", 403)

    q = (request.args.get("q") or "").strip()
    if len(q) < SEARCH_MIN_CHARS:
        return jsonify({"items": [], "min_chars": SEARCH_MIN_CHARS})

    itens = []
    for candidato in search_events(q):
        if candidato.id == event_id or candidato.event_type == "ENSAIO":
            continue
        motivo = None
        if candidato.is_satellite:
            motivo = "já pertence a outro grupo"
        elif candidato.is_group_leader:
            motivo = "já é principal de outro grupo"
        itens.append({
            "id": candidato.id,
            "title": candidato.title,
            "start_at": candidato.start_at.isoformat() if candidato.start_at else None,
            "event_type": candidato.event_type,
            "has_sale": group_ops.has_financial_data(candidato),
            "blocked_reason": motivo,
        })
    return jsonify({"items": itens, "min_chars": SEARCH_MIN_CHARS})


@api_bp.route("/events/<int:event_id>/grupo", methods=["POST"])
@api_login_required
def api_agrupar_eventos(event_id: int) -> Any:
    """Agrupa eventos sob um principal. Corpo: `leader_event_id`, `target_event_ids`,
    `group_name`, `confirm_clear_financials`.

    Devolve **409 com `needs_confirmation`** e a lista de eventos que perderiam venda quando a
    confirmação não veio. É a única trava contra perda irreversível: agrupar apaga os 14 campos
    comerciais do satélite e desagrupar não devolve. O 409 tipado (em vez do checkbox genérico do
    Jinja) é o que deixa a tela mostrar NOMES e VALORES do que será apagado.
    """
    from app.calendar import group_ops
    from app.financeiro.routes import _sync_commission_payment

    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_group():
        return json_error("Sem permissão", 403)

    body = request.get_json(silent=True) or {}
    alvos_raw = body.get("target_event_ids") or []
    alvo_ids = {int(t) for t in alvos_raw if isinstance(t, int) or str(t).isdigit()}
    if not alvo_ids:
        return json_error("Selecione ao menos um evento para agrupar.", 400)

    alvos = CalendarEvent.query.filter(CalendarEvent.id.in_(alvo_ids)).all()
    if len(alvos) != len(alvo_ids):
        return json_error("Selecione eventos válidos para agrupar.", 400)

    participantes = {event.id: event, **{a.id: a for a in alvos}}
    leader_raw = body.get("leader_event_id")
    if leader_raw is None or int(leader_raw) not in participantes:
        return json_error("Selecione qual evento é o principal do grupo.", 400)

    leader = participantes.pop(int(leader_raw))
    satellites = list(participantes.values())

    erro = group_ops.validar_agrupamento(leader, satellites)
    if erro:
        return json_error(erro, 409)

    if not body.get("confirm_clear_financials"):
        com_venda = group_ops.satelites_com_venda(satellites)
        if com_venda:
            return json_error(
                "Estes eventos já têm valor de venda preenchido e vão perdê-lo.",
                409,
                needs_confirmation=True,
                events_with_sale=[
                    {"id": s.id, "title": s.title, "sale_value": str(s.sale_value)}
                    for s in com_venda
                ],
            )

    resultado = group_ops.agrupar(
        leader=leader,
        satellites=satellites,
        group_name=(body.get("group_name") or "").strip(),
        actor_name=current_user.name,
        agora=datetime.now(tz=_TZ_SP),
        sincronizar_comissao=_sync_commission_payment,
    )
    return _grupo_detalhe_json(leader, leader_id=resultado["leader_id"])


@api_bp.route("/events/<int:event_id>/grupo", methods=["DELETE"])
@api_login_required
def api_desagrupar_evento(event_id: int) -> Any:
    """Solta ESTE evento do grupo — `event_id` é o satélite (paridade com o Jinja).

    Não restaura os campos comerciais: eles foram apagados no agrupamento. O que existe é a cópia
    gravada no histórico do evento, para consulta.
    """
    from app.calendar import group_ops

    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_group():
        return json_error("Sem permissão", 403)
    if not event.is_satellite:
        return json_error("Este evento não pertence a um grupo.", 409)

    resultado = group_ops.desagrupar(
        event, current_user.name, datetime.now(tz=_TZ_SP)
    )
    return _grupo_detalhe_json(event, leader_id=resultado["leader_id"])


@api_bp.route("/events/<int:leader_id>/grupo/satelites/<int:sat_id>", methods=["DELETE"])
@api_login_required
def api_remover_satelite(leader_id: int, sat_id: int) -> Any:
    """Tira um satélite a partir da tela do PRINCIPAL — o Jinja não tinha isto.

    Sem esta rota, dissolver o grupo de 13 satélites que existe no banco exigiria abrir os 13, um
    por um. E é ela que destrava o cancelamento: um evento principal não pode ser cancelado
    enquanto tiver satélites.
    """
    from app.calendar import group_ops

    satelite = CalendarEvent.query.get(sat_id)
    if satelite is None:
        return json_error("Evento não encontrado", 404)
    if not _can_group():
        return json_error("Sem permissão", 403)
    if satelite.group_leader_id != leader_id:
        return json_error("Este evento não é satélite deste grupo.", 404)

    group_ops.desagrupar(
        satelite, current_user.name, datetime.now(tz=_TZ_SP)
    )
    leader = CalendarEvent.query.get(leader_id)
    return _grupo_detalhe_json(leader, leader_id=leader_id)


@api_bp.route("/events/<int:event_id>/grupo", methods=["PATCH"])
@api_login_required
def api_renomear_grupo(event_id: int) -> Any:
    """Define, edita ou limpa o nome do grupo. Corpo: `{"group_name": str | null}`.

    Só no principal — `group_name` gravado num satélite é ignorado por toda a leitura. Nome vazio
    volta ao fallback (o título do evento).
    """
    from app.calendar import group_ops

    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if not _can_group():
        return json_error("Sem permissão", 403)
    if not event.is_group_leader:
        return json_error("Apenas o evento principal de um grupo pode ser renomeado.", 409)

    body = request.get_json(silent=True) or {}
    group_ops.renomear_grupo(
        event,
        body.get("group_name"),
        current_user.name,
        datetime.now(tz=_TZ_SP),
    )
    return _event_detail_json(event)
