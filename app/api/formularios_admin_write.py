"""Endpoints de ESCRITA do lado staff/admin de Formulários (migração 177, US7).

Não confundir com `app/api/formularios_write.py` (fluxo público `/f/*`, intocado nesta
feature). Reusa, sem duplicar, o núcleo já extraído em `app/formularios/formularios_ops.py`.
"""

from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.api.formularios_admin_read import _require_superadmin, _require_vendas
from app.api_utils import api_login_required, json_error
from app.formularios import formularios_ops
from app.models import FormFieldDefinition, FormResponse


@api_bp.route("/formularios/respostas/<int:response_id>/associar", methods=["POST"])
@api_login_required
def api_formularios_associar(response_id: int) -> Any:
    """Associa a resposta a um cliente existente ou cria um a partir dos dados dela."""
    denied = _require_vendas()
    if denied:
        return denied
    response = FormResponse.query.get(response_id)
    if response is None:
        return json_error("Resposta não encontrada", 404)
    body = request.get_json(silent=True) or {}
    try:
        client = formularios_ops.associate_client(response, body.get("client_id"))
    except formularios_ops.FormValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"client_id": client.id, "client_name": client.name})


@api_bp.route("/formularios/respostas/<int:response_id>/desassociar", methods=["POST"])
@api_login_required
def api_formularios_desassociar(response_id: int) -> Any:
    """Remove a associação da resposta com o cliente."""
    denied = _require_vendas()
    if denied:
        return denied
    response = FormResponse.query.get(response_id)
    if response is None:
        return json_error("Resposta não encontrada", 404)
    formularios_ops.dissociate_client(response)
    return jsonify({"ok": True})


@api_bp.route("/formularios/respostas/<int:response_id>/vincular-evento", methods=["POST"])
@api_login_required
def api_formularios_vincular_evento(response_id: int) -> Any:
    """Associa manualmente a resposta a um evento existente da agenda (feature 126)."""
    denied = _require_vendas()
    if denied:
        return denied
    response = FormResponse.query.get(response_id)
    if response is None:
        return json_error("Resposta não encontrada", 404)
    body = request.get_json(silent=True) or {}
    event_id = body.get("event_id")
    if not event_id:
        return json_error("Selecione um evento válido.", 400, fields={"event_id": "obrigatório"})
    try:
        event = formularios_ops.link_event(response, int(event_id))
    except formularios_ops.FormValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"event_id": event.id, "event_title": event.title})


@api_bp.route("/formularios/respostas/<int:response_id>/desvincular-evento", methods=["POST"])
@api_login_required
def api_formularios_desvincular_evento(response_id: int) -> Any:
    """Desfaz o vínculo de evento — automático ou manual (feature 126, FR-008)."""
    denied = _require_vendas()
    if denied:
        return denied
    response = FormResponse.query.get(response_id)
    if response is None:
        return json_error("Resposta não encontrada", 404)
    formularios_ops.unlink_event(response)
    return jsonify({"ok": True})


@api_bp.route("/formularios/respostas/<int:response_id>", methods=["DELETE"])
@api_login_required
def api_formularios_delete(response_id: int) -> Any:
    """Exclui uma resposta — apenas SUPERADMIN."""
    denied = _require_superadmin()
    if denied:
        return denied
    response = FormResponse.query.get(response_id)
    if response is None:
        return json_error("Resposta não encontrada", 404)
    formularios_ops.delete_response(response)
    return "", 204


# ══════════════════════════════════════════════════════════════════
#  Editor de estrutura dos formulários (SUPERADMIN)
# ══════════════════════════════════════════════════════════════════


def _field_dict(f: FormFieldDefinition) -> dict:
    return {
        "id": f.id,
        "section_name": f.section_name,
        "field_key": f.field_key,
        "field_type": f.field_type,
        "label": f.label,
        "help_text": f.help_text,
        "placeholder": f.placeholder,
        "required": f.required,
        "options": f.options,
        "order": f.order,
        "is_system": f.is_system,
    }


@api_bp.route("/formularios/editor/<form_type>/campo", methods=["POST"])
@api_login_required
def api_formularios_criar_campo(form_type: str) -> Any:
    """Adiciona um campo personalizado ao fim de uma seção."""
    denied = _require_superadmin()
    if denied:
        return denied
    if form_type not in ("comum", "corporativo"):
        return json_error("Tipo de formulário inválido", 404)
    body = request.get_json(silent=True) or {}
    try:
        field = formularios_ops.create_field(form_type, body)
    except formularios_ops.FormValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_field_dict(field)), 201


@api_bp.route("/formularios/editor/campo/<int:field_id>", methods=["PATCH"])
@api_login_required
def api_formularios_editar_campo(field_id: int) -> Any:
    """Edita rótulo/texto de ajuda/obrigatoriedade/opções de um campo."""
    denied = _require_superadmin()
    if denied:
        return denied
    field = FormFieldDefinition.query.get(field_id)
    if field is None:
        return json_error("Campo não encontrado", 404)
    body = request.get_json(silent=True) or {}
    try:
        formularios_ops.update_field(field, body)
    except formularios_ops.FormValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_field_dict(field))


@api_bp.route("/formularios/editor/campo/<int:field_id>/mover", methods=["POST"])
@api_login_required
def api_formularios_mover_campo(field_id: int) -> Any:
    """Reordena um campo dentro da própria seção."""
    denied = _require_superadmin()
    if denied:
        return denied
    field = FormFieldDefinition.query.get(field_id)
    if field is None:
        return json_error("Campo não encontrado", 404)
    body = request.get_json(silent=True) or {}
    formularios_ops.move_field(field, body.get("direction", ""))
    return jsonify(_field_dict(field))


@api_bp.route("/formularios/editor/campo/<int:field_id>", methods=["DELETE"])
@api_login_required
def api_formularios_excluir_campo(field_id: int) -> Any:
    """Remove um campo personalizado — campos de sistema são protegidos."""
    denied = _require_superadmin()
    if denied:
        return denied
    field = FormFieldDefinition.query.get(field_id)
    if field is None:
        return json_error("Campo não encontrado", 404)
    try:
        formularios_ops.delete_field(field)
    except formularios_ops.FormValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return "", 204
