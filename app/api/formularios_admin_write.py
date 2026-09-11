"""Endpoints de ESCRITA do lado staff/admin de Formulários (migração 177, US7).

Não confundir com `app/api/formularios_write.py` (fluxo público `/f/*`, intocado nesta
feature). Reusa, sem duplicar, o núcleo já extraído em `app/formularios/formularios_ops.py`.

RBAC (função no início de cada view — constituição XIII; tabela em `docs/01` §4.3):
  * `_require_vendas` (COMERCIAL, FINANCEIRO, SUPERADMIN): associar/desassociar cliente,
    vincular/desvincular evento e, desde a 298, encerrar, reabrir, manter entre repetidos,
    confirmar/descartar sugestão e usar a cliente do evento.
  * `_require_superadmin`: excluir resposta e o editor de estrutura.
Conflito de destino (feature 298) → 409 "Este formulário já tem destino." em todos os caminhos.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api.formularios_admin_read import (
    _require_superadmin,
    _require_vendas,
    _response_summary,
)
from app.api_utils import api_login_required, json_error
from app.formularios import destino_ops, formularios_ops
from app.models import FormFieldDefinition, FormResponse


def _resumo(response: FormResponse) -> dict:
    return _response_summary(response, formularios_ops.corte_de_chegada())


@api_bp.route("/formularios/respostas/<int:response_id>/encerrar", methods=["POST"])
@api_login_required
def api_formularios_encerrar(response_id: int) -> Any:
    """Encerra com motivo um formulário sem destino (feature 298): sai da Home e fica guardado."""
    denied = _require_vendas()
    if denied:
        return denied
    if FormResponse.query.get(response_id) is None:
        return json_error("Resposta não encontrada", 404)
    body = request.get_json(silent=True) or {}
    try:
        response = destino_ops.encerrar(
            response_id, body.get("motivo"), body.get("frase"), current_user
        )
    except destino_ops.ValidacaoEncerramento as exc:
        return json_error(exc.message, 400, fields={exc.campo: exc.message})
    except destino_ops.FormularioInexistente:
        db.session.rollback()
        return json_error("Resposta não encontrada", 404)
    except destino_ops.FormularioDoHistorico as exc:
        db.session.rollback()
        return json_error(exc.message, 422)
    except formularios_ops.FormularioJaTemDestino as exc:
        db.session.rollback()
        return json_error(exc.message, 409)
    db.session.commit()
    return jsonify({"response": _resumo(response)})


@api_bp.route("/formularios/respostas/<int:response_id>/reabrir", methods=["POST"])
@api_login_required
def api_formularios_reabrir(response_id: int) -> Any:
    """Desfaz o encerramento (feature 298): o formulário volta para a Home, sem reacender aviso."""
    denied = _require_vendas()
    if denied:
        return denied
    if FormResponse.query.get(response_id) is None:
        return json_error("Resposta não encontrada", 404)
    try:
        response = destino_ops.reabrir(response_id)
    except destino_ops.FormularioInexistente:
        db.session.rollback()
        return json_error("Resposta não encontrada", 404)
    except destino_ops.FormularioNaoEncerrado as exc:
        db.session.rollback()
        return json_error(exc.message, 409)
    db.session.commit()
    return jsonify({"response": _resumo(response)})


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
        event, resultado = formularios_ops.link_event(response, int(event_id))
    except formularios_ops.FormValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    except formularios_ops.FormularioJaTemDestino as exc:
        # Até a 298 este caminho SOBRESCREVIA o vínculo; agora recusa como todos os outros.
        db.session.rollback()
        return json_error(exc.message, 409)
    return jsonify({
        "response": _response_summary(response, formularios_ops.corte_de_chegada()),
        "divergencia_cliente": resultado.divergencia_cliente,
        "event_id": event.id,
        "event_title": event.title,
    })


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
