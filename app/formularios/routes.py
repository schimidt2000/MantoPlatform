"""Formulários públicos de pré-contrato + banco de respostas (feature 118).

Substitui o WhatsForm: dois formulários públicos (comum e corporativo) hospedados no
Manto. No envio válido, a resposta é salva em ``FormResponse`` ANTES de abrir o WhatsApp
da cliente com a mensagem formatada para o número da Manto (``SiteSetting.
whatsapp_form_number``). A área interna lista as respostas, permite associar a cliente
(sugestão por telefone normalizado), excluir (só SUPERADMIN) e buscar respostas para
vincular a um evento em ``/events/new``.

A estrutura dos dois formulários (seções, campos, tipos, obrigatoriedade, ordem) é
editável pelo painel (SUPERADMIN) via ``FormFieldDefinition`` — feature 123.

O vínculo com um evento da agenda pode ser automático (por data e, em caso de empate/
ausência, por cliente já associada a um evento — feature 126) ou manual, sempre que a
automação não tiver certeza suficiente para decidir sozinha.
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import date, datetime
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import not_

from app import db, limiter
from app.clientes.importer import normalize_phone
from app.constants import RoleName
from app.models import (
    CalendarEvent,
    Client,
    EventClient,
    FormFieldDefinition,
    FormResponse,
    SiteSetting,
)

from . import formularios_ops

formularios_bp = Blueprint("formularios", __name__)

from app.formularios.formularios_ops import (
    CEP_TARGET_KEYS,
    DEFAULT_WHATSAPP_NUMBER,
    FIELD_TYPE_LABELS,
    FORM_META,
    _attempt_auto_link,
    _build_message,
    _build_phone_display,
    _build_sections_dynamic,
    _fmt_date_br,
    _grouped_sections,
    _load_fields,
    _only_digits,
    _parse_event_date,
    _save_response,
    _validate_dynamic,
    _whatsapp_link,
    _whatsapp_target,
    retry_auto_link_pending,
)


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def require_vendas(fn):
    """Restringe o acesso aos papéis comerciais (COMERCIAL/FINANCEIRO/SUPERADMIN)."""

    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


def require_superadmin(fn):
    """Restringe o acesso ao SUPERADMIN — edição de estrutura dos formulários (feature 123)."""

    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not _has_role(RoleName.SUPERADMIN):
            abort(403)
        return fn(*args, **kwargs)

    return wrapper



def _render_public_form(form_type: str, form, errors: dict, status: int = 200):
    """Renderiza o formulário público a partir da definição de campos vigente, preservando os
    valores digitados quando há erro (FR-004)."""
    fields = _load_fields(form_type)
    meta = FORM_META[form_type]
    return render_template(
        "formularios/public_form.html", form=form, errors=errors, meta=meta,
        sections=_grouped_sections(fields),
        submit_url=url_for(f"formularios.submit_{form_type}"),
        has_cep=any(fld.field_type == "cep" for fld in fields),
    ), status


def _submit_public_form(form_type: str):
    """Valida, salva e devolve a página que abre o WhatsApp com a resposta."""
    f = request.form
    # Honeypot anti-bot: campo oculto que humanos não preenchem.
    if (f.get("website") or "").strip():
        return render_template("formularios/enviado.html", wa_link="", contact_name="")
    fields = _load_fields(form_type)
    errors = _validate_dynamic(f, fields)
    if errors:
        return _render_public_form(form_type, f, errors, 400)
    sections = _build_sections_dynamic(f, fields)
    meta = FORM_META[form_type]
    contact_name = (f.get(meta["name_key"]) or "").strip()
    response = _save_response(
        form_type, contact_name, _build_phone_display(f, "whatsapp"),
        _parse_event_date(f.get("data_evento")), sections)
    # Vínculo automático a um evento já existente na agenda (feature 126) — best-effort,
    # nunca pode impedir a resposta de ser salva/enviada mesmo se algo aqui falhar.
    try:
        result = _attempt_auto_link(response)
        if result in ("auto_date", "auto_client"):
            response.event_link_source = result
        elif result == "ambiguous":
            response.event_link_ambiguous = True
        if result:
            db.session.commit()
    except Exception:  # noqa: BLE001 — best-effort, a resposta já foi salva antes disso
        db.session.rollback()
        current_app.logger.exception(
            "[formularios] falha ao tentar vínculo automático de evento (resposta %s)",
            response.id)
    message = _build_message(meta["message_title"], sections)
    return render_template(
        "formularios/enviado.html", wa_link=_whatsapp_link(message), contact_name=contact_name)


@formularios_bp.route("/f/pre-contrato", methods=["GET"])
def form_comum():
    """Formulário público de pré-contrato (pessoa física)."""
    return _render_public_form("comum", request.form, {})


@formularios_bp.route("/f/pre-contrato", methods=["POST"])
@limiter.limit("10 per hour")
def submit_comum():
    return _submit_public_form("comum")


@formularios_bp.route("/f/corporativo", methods=["GET"])
def form_corporativo():
    """Formulário público de contrato corporativo (pessoa jurídica)."""
    return _render_public_form("corporativo", request.form, {})


@formularios_bp.route("/f/corporativo", methods=["POST"])
@limiter.limit("10 per hour")
def submit_corporativo():
    return _submit_public_form("corporativo")


# ── Área interna: banco de respostas ─────────────────────────────────


@formularios_bp.route("/formularios/")
@require_vendas
def index():
    """Seção de formulários: links copiáveis + listagem das respostas."""
    responses = formularios_ops.list_responses()
    return render_template(
        "formularios/index.html", responses=responses,
        can_edit_structure=_has_role(RoleName.SUPERADMIN))


@formularios_bp.route("/formularios/respostas/<int:response_id>")
@require_vendas
def detail(response_id: int):
    """Detalhe completo da resposta + associação a cliente."""
    response = FormResponse.query.get_or_404(response_id)
    suggested = None
    if response.client_id is None and response.contact_phone:
        suggested = Client.query.filter_by(phone=response.contact_phone).first()
    return render_template(
        "formularios/detail.html", response=response, suggested=suggested)


@formularios_bp.route("/formularios/respostas/<int:response_id>/associar", methods=["POST"])
@require_vendas
def associar(response_id: int):
    """Associa a resposta a um cliente existente ou cria um a partir dos dados dela."""
    response = FormResponse.query.get_or_404(response_id)
    try:
        client = formularios_ops.associate_client(response, request.form.get("client_id"))
    except formularios_ops.FormValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("formularios.detail", response_id=response.id))
    flash(f"Resposta associada ao cliente {client.name}.", "success")
    return redirect(url_for("formularios.detail", response_id=response.id))


@formularios_bp.route("/formularios/respostas/<int:response_id>/desassociar", methods=["POST"])
@require_vendas
def desassociar(response_id: int):
    """Remove a associação da resposta com o cliente."""
    response = FormResponse.query.get_or_404(response_id)
    formularios_ops.dissociate_client(response)
    flash("Associação removida.", "success")
    return redirect(url_for("formularios.detail", response_id=response.id))


@formularios_bp.route("/formularios/respostas/<int:response_id>/vincular-evento", methods=["POST"])
@require_vendas
def vincular_evento(response_id: int):
    """Associa manualmente a resposta a um evento existente da agenda (feature 126).

    Marca ``event_link_locked`` — a partir daqui, a automação nunca mais tenta decidir
    sozinha por essa resposta (respeita a decisão humana).
    """
    response = FormResponse.query.get_or_404(response_id)
    raw = request.form.get("event_id", "").strip()
    if not raw.isdigit():
        flash("Selecione um evento válido.", "error")
        return redirect(url_for("formularios.detail", response_id=response.id))
    try:
        event = formularios_ops.link_event(response, int(raw))
    except formularios_ops.FormValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("formularios.detail", response_id=response.id))
    flash(f'Resposta vinculada ao evento "{event.title}".', "success")
    return redirect(url_for("formularios.detail", response_id=response.id))


@formularios_bp.route("/formularios/respostas/<int:response_id>/desvincular-evento", methods=["POST"])
@require_vendas
def desvincular_evento(response_id: int):
    """Desfaz o vínculo de evento — automático ou manual (feature 126, FR-008).

    Também marca ``event_link_locked``: uma vez que um humano decide desfazer, a
    automação não pode religar sozinha ao mesmo evento no próximo ciclo de sincronização.
    """
    response = FormResponse.query.get_or_404(response_id)
    formularios_ops.unlink_event(response)
    flash("Vínculo de evento removido.", "success")
    return redirect(url_for("formularios.detail", response_id=response.id))


@formularios_bp.route("/formularios/respostas/<int:response_id>/delete", methods=["POST"])
@require_vendas
def delete(response_id: int):
    """Exclui uma resposta — apenas SUPERADMIN (FR-009)."""
    if not _has_role(RoleName.SUPERADMIN):
        abort(403)
    response = FormResponse.query.get_or_404(response_id)
    formularios_ops.delete_response(response)
    flash("Resposta excluída.", "success")
    return redirect(url_for("formularios.index"))


@formularios_bp.route("/formularios/respostas/search")
@require_vendas
def search():
    """Busca respostas (JSON) para o buscador de ``/events/new`` — sem acento (FR-010)."""
    results = formularios_ops.search_responses(request.args.get("q") or "")
    return jsonify([
        {
            "id": r.id,
            "name": r.contact_name,
            "phone_display": r.contact_phone_display or "",
            "form_type": r.form_type_label,
            "event_date": _fmt_date_br(r.event_date),
            "created_at": r.created_at.strftime("%d/%m/%Y"),
        }
        for r in results
    ])


# ── Editor de estrutura dos formulários (feature 123, SUPERADMIN) ────


@formularios_bp.route("/formularios/editor/<form_type>")
@require_superadmin
def editor(form_type: str):
    """Tela de edição da estrutura de um dos formulários públicos (feature 123)."""
    if form_type not in FORM_META:
        abort(404)
    fields = _load_fields(form_type)
    return render_template(
        "formularios/editor.html", form_type=form_type, meta=FORM_META[form_type],
        sections=_grouped_sections(fields), field_types=FIELD_TYPE_LABELS)


@formularios_bp.route("/formularios/editor/<form_type>/campo/novo", methods=["POST"])
@require_superadmin
def editor_novo_campo(form_type: str):
    """Adiciona um campo personalizado ao fim de uma seção (US2 — feature 123)."""
    if form_type not in FORM_META:
        abort(404)
    try:
        field = formularios_ops.create_field(form_type, {
            "label": request.form.get("label"),
            "section_name": request.form.get("section_name"),
            "field_type": request.form.get("field_type"),
            "help_text": request.form.get("help_text"),
            "required": request.form.get("required") == "on",
            "options": request.form.get("options"),
        })
    except formularios_ops.FormValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("formularios.editor", form_type=form_type))
    flash(f'Campo "{field.label}" adicionado.', "success")
    return redirect(url_for("formularios.editor", form_type=form_type))


@formularios_bp.route("/formularios/editor/campo/<int:field_id>/editar", methods=["POST"])
@require_superadmin
def editor_editar_campo(field_id: int):
    """Edita rótulo/texto de ajuda/obrigatoriedade/opções de um campo (US1 — feature 123).

    ``field_type`` e ``field_key`` são imutáveis após criação — evita inconsistência de
    formato em respostas já salvas e preserva a busca por chave da feature 119.
    """
    field = FormFieldDefinition.query.get_or_404(field_id)
    try:
        formularios_ops.update_field(field, {
            "label": request.form.get("label"),
            "help_text": request.form.get("help_text"),
            "placeholder": request.form.get("placeholder"),
            "required": request.form.get("required") == "on",
            "options": request.form.get("options"),
        })
    except formularios_ops.FormValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("formularios.editor", form_type=field.form_type))
    flash(f'Campo "{field.label}" atualizado.', "success")
    return redirect(url_for("formularios.editor", form_type=field.form_type))


@formularios_bp.route("/formularios/editor/campo/<int:field_id>/mover", methods=["POST"])
@require_superadmin
def editor_mover_campo(field_id: int):
    """Reordena um campo dentro da própria seção (US3 — feature 123)."""
    field = FormFieldDefinition.query.get_or_404(field_id)
    formularios_ops.move_field(field, request.form.get("direction", ""))
    return redirect(url_for("formularios.editor", form_type=field.form_type))


@formularios_bp.route("/formularios/editor/campo/<int:field_id>/excluir", methods=["POST"])
@require_superadmin
def editor_excluir_campo(field_id: int):
    """Remove um campo personalizado (US3 — feature 123). Campos de sistema são protegidos."""
    field = FormFieldDefinition.query.get_or_404(field_id)
    form_type = field.form_type
    try:
        formularios_ops.delete_field(field)
    except formularios_ops.FormValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("formularios.editor", form_type=form_type))
    flash("Campo removido.", "success")
    return redirect(url_for("formularios.editor", form_type=form_type))
