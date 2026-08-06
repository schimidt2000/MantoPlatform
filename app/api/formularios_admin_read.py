"""Endpoints de LEITURA do lado staff/admin de Formulários (migração 177, US7).

Não confundir com `app/api/formularios_write.py` (fluxo público `/f/*`, intocado nesta
feature). Reusa, sem duplicar, o núcleo já extraído em `app/formularios/formularios_ops.py`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.formularios import formularios_ops
from app.models import Client, FormResponse


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_vendas() -> Any:
    if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _require_superadmin() -> Any:
    if not _has_role(RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _response_summary(r: FormResponse) -> dict:
    return {
        "id": r.id,
        "form_type": r.form_type,
        "form_type_label": r.form_type_label,
        "contact_name": r.contact_name,
        "contact_phone_display": r.contact_phone_display or "",
        "event_date": r.event_date.isoformat() if r.event_date else None,
        "client_id": r.client_id,
        # Nome do cliente já na listagem: a coluna "Situação" mostra o badge "Cliente: <nome>"
        # sem exigir que a tela abra o detalhe de cada resposta (`list_responses` faz joinedload).
        "client_name": r.client.name if r.client else None,
        "event_id": r.event_id,
        "event_link_source": r.event_link_source,
        "event_link_ambiguous": r.event_link_ambiguous,
        "event_link_locked": r.event_link_locked,
        "created_at": r.created_at.isoformat(),
    }


def _response_detail(r: FormResponse) -> dict:
    return {
        **_response_summary(r),
        "data_sections": r.data_sections,
        "event_title": r.event.title if r.event else None,
    }


@api_bp.route("/formularios/respostas")
@api_login_required
def api_formularios_respostas_list() -> Any:
    """Lista as respostas mais recentes + contadores de situação (cartões da tela).

    ``?filtro=`` aceita as chaves de `formularios_ops.STATUS_FILTERS`; valor desconhecido
    ou ausente lista tudo. Os contadores vêm sempre no payload — a tela pinta os cartões
    sem uma segunda chamada.
    """
    denied = _require_vendas()
    if denied:
        return denied
    filtro = (request.args.get("filtro") or "").strip()
    responses = formularios_ops.list_responses(filtro=filtro)
    return jsonify({
        "responses": [_response_summary(r) for r in responses],
        "counts": formularios_ops.count_status(),
    })


@api_bp.route("/formularios/respostas/search")
@api_login_required
def api_formularios_respostas_search() -> Any:
    """Busca respostas por nome/telefone (sem acentos)."""
    denied = _require_vendas()
    if denied:
        return denied
    results = formularios_ops.search_responses(request.args.get("q") or "")
    return jsonify({"responses": [_response_summary(r) for r in results]})


@api_bp.route("/formularios/respostas/<int:response_id>")
@api_login_required
def api_formularios_resposta_detail(response_id: int) -> Any:
    """Detalhe completo da resposta + sugestão de cliente por telefone."""
    denied = _require_vendas()
    if denied:
        return denied
    response = FormResponse.query.get(response_id)
    if response is None:
        return json_error("Resposta não encontrada", 404)
    suggested = None
    if response.client_id is None and response.contact_phone:
        suggested = Client.query.filter_by(phone=response.contact_phone).first()
    return jsonify({
        "response": _response_detail(response),
        "suggested_client": (
            {"id": suggested.id, "name": suggested.name} if suggested else None
        ),
        "can_edit_structure": _has_role(RoleName.SUPERADMIN),
    })


@api_bp.route("/formularios/editor/<form_type>")
@api_login_required
def api_formularios_editor_get(form_type: str) -> Any:
    """Definição de campos de um formulário, agrupada por seção (SUPERADMIN)."""
    denied = _require_superadmin()
    if denied:
        return denied
    if form_type not in ("comum", "corporativo"):
        return json_error("Tipo de formulário inválido", 404)
    fields = formularios_ops.list_field_definitions(form_type)
    return jsonify({
        "fields": [
            {
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
            for f in fields
        ]
    })
