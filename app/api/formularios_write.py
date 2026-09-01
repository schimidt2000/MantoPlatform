"""Endpoints dos formulários públicos dinâmicos em React (feature 163, 3ª fatia da US5).

Reaproveita por import direto o motor dinâmico já existente em `app/formularios/routes.py`
(feature 118/123/126) — este módulo só traduz o resultado em JSON. Público (sem
`@login_required`/RBAC), mesma acessibilidade das rotas `/f/pre-contrato` e `/f/corporativo`
hoje. As rotas Jinja seguem no ar em paralelo; a área interna autenticada (`/formularios/*`) não
é tocada (ver `specs/163-formularios-dinamicos-react/plan.md`).
"""

from typing import Any

from flask import current_app, jsonify, request

from app import db, limiter
from app.api import api_bp
from app.api_utils import json_error
from app.constants import RoleName
from app.email_service import send_async, send_form_response_email
from app.formularios.formularios_ops import (
    FORM_META,
    _attempt_auto_link,
    _build_message,
    _build_phone_display,
    _build_sections_dynamic,
    _grouped_sections,
    _load_fields,
    _parse_event_date,
    _save_response,
    _validate_dynamic,
    _whatsapp_link,
    attempt_auto_link_client,
    ensure_event_client,
)
from app.models import FormFieldDefinition, FormResponse, Role, User

_INVALID_FIELDS_MESSAGE = (
    "Alguns campos precisam de atenção. Corrija os campos destacados e envie novamente."
)


def _field_schema(field: FormFieldDefinition) -> dict[str, Any]:
    """Serializa um `FormFieldDefinition` para o schema JSON consumido pelo `DynamicForm`."""
    return {
        "key": field.field_key,
        "type": field.field_type,
        "label": field.label,
        "help_text": field.help_text,
        "placeholder": field.placeholder,
        "required": field.required,
        "options": field.options_list if field.field_type == "selecao" else None,
    }


@api_bp.route("/formularios/<form_type>/schema")
def api_formularios_schema(form_type: str) -> Any:
    """Estrutura vigente de um dos dois formulários públicos (paridade com `_render_public_form`)."""
    if form_type not in FORM_META:
        return json_error("Formulário não encontrado", 404)

    fields = _load_fields(form_type)
    meta = FORM_META[form_type]
    return jsonify(
        {
            "title": meta["title"],
            "header": meta["header"],
            "sections": [
                {"secao": section["secao"], "campos": [_field_schema(f) for f in section["campos"]]}
                for section in _grouped_sections(fields)
            ],
        }
    )


def _avisar_comercial(response: FormResponse) -> None:
    """Dispara o aviso de resposta nova para quem pode agir nela (feature 266).

    Best-effort por decisão: a resposta da cliente já está gravada, e perder um lead porque o
    SMTP caiu seria pior que não ter o aviso. O envio é assíncrono e o POST responde 201
    independentemente do resultado.
    """
    try:
        destinatarios = (
            User.query.join(User.roles)
            .filter(
                Role.name.in_([RoleName.COMERCIAL, RoleName.SUPERADMIN]),
                User.is_active.is_(True),
                User.has_access.is_(True),
            )
            .all()
        )
        if destinatarios:
            send_async(send_form_response_email, response, destinatarios)
    except Exception:  # noqa: BLE001 — aviso nunca derruba a submissão pública
        current_app.logger.exception(
            "[formularios_write] falha ao avisar o comercial da resposta %s", response.id)


@api_bp.route("/formularios/<form_type>", methods=["POST"])
@limiter.limit("10 per hour")
def api_formularios_submit(form_type: str) -> Any:
    """Recebe a submissão de um formulário público dinâmico e salva a resposta.

    Honeypot preenchido responde 201 com `wa_link`/`contact_name` nulos (mesmo comportamento
    silencioso do Jinja) — não revela ao remetente automatizado que foi bloqueado.
    """
    if form_type not in FORM_META:
        return json_error("Formulário não encontrado", 404)

    f = request.form
    if (f.get("website") or "").strip():
        return jsonify({"wa_link": None, "contact_name": None}), 201

    fields = _load_fields(form_type)
    errors = _validate_dynamic(f, fields)
    if errors:
        return json_error(_INVALID_FIELDS_MESSAGE, 400, fields=errors)

    sections = _build_sections_dynamic(f, fields)
    meta = FORM_META[form_type]
    contact_name = (f.get(meta["name_key"]) or "").strip()
    response = _save_response(
        form_type, contact_name, _build_phone_display(f, "whatsapp"),
        _parse_event_date(f.get("data_evento")), sections)

    try:
        result = _attempt_auto_link(response)
        if result in ("auto_date", "auto_client"):
            response.event_link_source = result
        elif result == "ambiguous":
            response.event_link_ambiguous = True
        client_result = attempt_auto_link_client(response)
        if client_result:
            response.client_link_source = client_result
            # Só quando o evento também foi identificado nesta passada: é o que o caminho
            # manual (`link_event`) já faz, e é o que faz o evento aparecer na ficha dela.
            if response.event_id is not None and response.event is not None:
                ensure_event_client(response.event, response.client_id)
        if result or client_result:
            db.session.commit()
    except Exception:  # noqa: BLE001 — best-effort, a resposta já foi salva antes disso
        db.session.rollback()
        current_app.logger.exception(
            "[formularios_write] falha ao tentar vínculo automático de evento/cliente "
            "(resposta %s)",
            response.id)

    _avisar_comercial(response)

    message = _build_message(meta["message_title"], sections)
    return jsonify({"wa_link": _whatsapp_link(message), "contact_name": contact_name}), 201
