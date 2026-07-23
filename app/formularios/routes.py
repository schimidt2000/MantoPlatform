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

DEFAULT_WHATSAPP_NUMBER = "5511970570577"

FIELD_TYPE_LABELS = {
    "texto_curto": "Texto curto",
    "texto_longo": "Texto longo (parágrafo)",
    "selecao": "Seleção (lista de opções)",
    "data": "Data",
    "hora": "Hora",
    "telefone": "Telefone/WhatsApp",
    "email": "E-mail",
    "cpf": "CPF",
    "cnpj": "CNPJ",
    "cep": "CEP",
    "sim_nao": "Sim/Não",
}

# Campos de endereço acoplados ao autopreenchimento por CEP (só existem no formulário 'comum').
CEP_TARGET_KEYS = ("logradouro", "bairro", "cidade", "estado")

FORM_META = {
    "comum": {
        "title": "Informações para Pré-Contrato — Manto Produções",
        "header": "INFORMAÇÕES PARA PRÉ-CONTRATO",
        "message_title": "INFORMAÇÕES PARA PRÉ-CONTRATO — MANTO PRODUÇÕES",
        "name_key": "nome_contratante",
    },
    "corporativo": {
        "title": "Contrato Corporativo — Manto Produções",
        "header": "CONTRATO CORPORATIVO",
        "message_title": "CONTRATO CORPORATIVO — MANTO PRODUÇÕES",
        "name_key": "razao_social",
    },
}


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


# ── Helpers de validação/montagem ────────────────────────────────────


def _only_digits(raw: str | None) -> str:
    return "".join(c for c in (raw or "") if c.isdigit())


def _build_phone_display(form, prefix: str) -> str:
    """Telefone como digitado (DDI + nacional), ex.: ``"+55 (11) 99999-9999"``."""
    national = (form.get(f"{prefix}_national") or "").strip()
    if not national:
        return ""
    if national.startswith("+"):
        return national
    ddi = (form.get(f"{prefix}_ddi") or "+55").strip()
    if not ddi.startswith("+"):
        ddi = "+" + ddi.lstrip("+")
    return f"{ddi} {national}".strip()


def _parse_event_date(raw: str | None) -> date | None:
    """Converte a data do input HTML (``YYYY-MM-DD``) em ``date``."""
    try:
        return datetime.strptime((raw or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _fmt_date_br(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _valid_email(raw: str) -> bool:
    return "@" in raw and "." in raw.split("@")[-1] and " " not in raw


def _whatsapp_target() -> str:
    """Número destino das mensagens (settings, com fallback para o padrão)."""
    settings = SiteSetting.query.get(1)
    number = _only_digits(getattr(settings, "whatsapp_form_number", None) or "")
    return number or DEFAULT_WHATSAPP_NUMBER


def _build_message(title: str, sections: list[dict]) -> str:
    """Formata a mensagem de WhatsApp: título + seções com ``*Rótulo:* valor`` por linha."""
    lines = [f"*{title}*"]
    for section in sections:
        lines.append("")
        lines.append(f"*— {section['secao']} —*")
        for campo in section["campos"]:
            label, value = campo[-2], campo[-1]
            if (value or "").strip():
                lines.append(f"*{label}:* {value}")
    return "\n".join(lines)


def _whatsapp_link(message: str) -> str:
    return (
        "https://api.whatsapp.com/send?phone="
        f"{_whatsapp_target()}&text={urllib.parse.quote(message)}"
    )


def _save_response(form_type: str, contact_name: str, phone_display: str,
                   event_date: date | None, sections: list[dict]) -> FormResponse:
    """Persiste a resposta (sempre ANTES de abrir o WhatsApp — SC-002)."""
    response = FormResponse(
        form_type=form_type,
        data=json.dumps(sections, ensure_ascii=False),
        contact_name=contact_name[:200],
        contact_phone=normalize_phone(phone_display),
        contact_phone_display=phone_display[:30] or None,
        event_date=event_date,
    )
    db.session.add(response)
    db.session.commit()
    return response


# ── Vínculo automático a evento da agenda (feature 126) ──────────────


def _real_event_candidates(event_date: date) -> list[CalendarEvent]:
    """Eventos "reais" (não ensaio, não satélite) numa data — candidatos a vínculo."""
    return (
        CalendarEvent.query
        .filter(
            db.func.date(CalendarEvent.start_at) == event_date,
            not_(CalendarEvent.title.like("🟧 ENSAIO%")),
            CalendarEvent.group_leader_id.is_(None),
        )
        .all()
    )


def _client_by_phone(phone: str | None) -> Client | None:
    if not phone:
        return None
    return Client.query.filter_by(phone=phone).first()


def _client_real_event_ids(client_id: int, future_only: bool = False) -> set[int]:
    """Ids de eventos reais (não ensaio/satélite) já associados a um cliente."""
    q = (
        db.session.query(CalendarEvent.id)
        .join(EventClient, EventClient.event_id == CalendarEvent.id)
        .filter(
            EventClient.client_id == client_id,
            not_(CalendarEvent.title.like("🟧 ENSAIO%")),
            CalendarEvent.group_leader_id.is_(None),
        )
    )
    if future_only:
        q = q.filter(CalendarEvent.start_at >= datetime.utcnow())
    return {row[0] for row in q.all()}


def _event_client_phones(event_id: int) -> set[str]:
    """Telefones dos clientes já associados a um evento (para checar contradição)."""
    return {
        ec.client.phone for ec in EventClient.query.filter_by(event_id=event_id).all()
        if ec.client and ec.client.phone
    }


def _attempt_auto_link(response: FormResponse) -> str | None:
    """Tenta vincular a resposta a um evento real da agenda (feature 126).

    Critério, do mais para o menos confiável: (1) exatamente um evento real na data
    informada, sem contradição de cliente; (2) telefone da resposta já associado a um
    cliente que resolve o empate entre vários candidatos da mesma data, ou aponta para um
    único evento futuro quando nenhum candidato bate por data. Nunca força um vínculo
    quando os sinais são ambíguos ou se contradizem — nesse caso sinaliza para revisão
    manual em vez de adivinhar.

    Retorna ``"auto_date"``/``"auto_client"`` se vinculou (já persiste ``response.
    event_id`` no objeto, sem commit — quem chama decide quando salvar), ``"ambiguous"``
    se precisa de revisão manual, ou ``None`` se não havia nada a tentar.
    """
    if response.event_id is not None or response.event_link_locked or not response.event_date:
        return None

    candidates = _real_event_candidates(response.event_date)
    client = _client_by_phone(response.contact_phone)

    if len(candidates) == 1:
        event = candidates[0]
        if response.contact_phone:
            existing_phones = _event_client_phones(event.id)
            if existing_phones and response.contact_phone not in existing_phones:
                return "ambiguous"  # evento já tem outra cliente — contradição, não força
        response.event_id = event.id
        return "auto_date"

    if len(candidates) > 1:
        if client:
            client_event_ids = _client_real_event_ids(client.id)
            matched = [e for e in candidates if e.id in client_event_ids]
            if len(matched) == 1:
                response.event_id = matched[0].id
                return "auto_client"
        return "ambiguous"

    # Nenhum candidato na data informada: só resolve se a identidade da cliente apontar
    # para um único evento futuro (a data digitada pode estar errada/desatualizada).
    if client:
        future_ids = _client_real_event_ids(client.id, future_only=True)
        if len(future_ids) == 1:
            response.event_id = next(iter(future_ids))
            return "auto_client"
        if len(future_ids) > 1:
            return "ambiguous"

    return None


def retry_auto_link_pending() -> int:
    """Reprocessa respostas sem evento vinculado (feature 126).

    Chamada pelo ciclo de sincronização da agenda para cobrir o caso do evento ser
    criado/importado DEPOIS da resposta já ter chegado. Nunca reprocessa uma resposta
    que um humano já decidiu manualmente (``event_link_locked``). Retorna quantas
    respostas foram vinculadas nesta chamada.
    """
    pending = FormResponse.query.filter(
        FormResponse.event_id.is_(None),
        FormResponse.event_link_locked.is_(False),
        FormResponse.event_date.isnot(None),
    ).all()
    if not pending:
        return 0
    linked = 0
    for response in pending:
        result = _attempt_auto_link(response)
        if result in ("auto_date", "auto_client"):
            response.event_link_source = result
            response.event_link_ambiguous = False
            linked += 1
        elif result == "ambiguous":
            response.event_link_ambiguous = True
    db.session.commit()
    return linked


# ── Motor dinâmico dos formulários públicos (feature 123) ────────────


def _load_fields(form_type: str) -> list[FormFieldDefinition]:
    """Campos de um formulário, na ordem de exibição vigente."""
    return formularios_ops.list_field_definitions(form_type)


def _grouped_sections(fields: list[FormFieldDefinition]) -> list[dict]:
    """Agrupa campos por seção, preservando a ordem de primeira aparição da seção e a ordem
    interna dos campos dentro dela (não depende de os campos de uma seção serem contíguos em
    ``order`` — um campo novo cai no fim da própria seção onde quer que seja inserido)."""
    by_section: dict[str, list[FormFieldDefinition]] = {}
    section_order: list[str] = []
    for field in fields:
        if field.section_name not in by_section:
            by_section[field.section_name] = []
            section_order.append(field.section_name)
        by_section[field.section_name].append(field)
    return [{"secao": name, "campos": by_section[name]} for name in section_order]


def _validate_dynamic(f, fields: list[FormFieldDefinition]) -> dict[str, str]:
    """Valida um formulário público a partir da definição de campos vigente (feature 123)."""
    errors: dict[str, str] = {}
    for field in fields:
        key = field.field_key
        if field.field_type == "telefone":
            if field.required and len(_only_digits(f.get(f"{key}_national"))) < 10:
                errors[f"{key}_national"] = f'Informe "{field.label}" com DDD.'
            continue
        raw = (f.get(key) or "").strip()
        if not raw:
            if field.required:
                errors[key] = f'Preencha o campo obrigatório: "{field.label}".'
            continue
        if field.field_type == "cpf" and len(_only_digits(raw)) != 11:
            errors[key] = "CPF inválido — confira os 11 dígitos."
        elif field.field_type == "cnpj" and len(_only_digits(raw)) != 14:
            errors[key] = "CNPJ inválido — confira os 14 dígitos."
        elif field.field_type == "cep" and len(_only_digits(raw)) != 8:
            errors[key] = "CEP inválido — confira os 8 dígitos."
        elif field.field_type == "email" and not _valid_email(raw):
            errors[key] = "Informe um e-mail válido."
        elif field.field_type == "data" and not _parse_event_date(raw):
            errors[key] = "Selecione uma data válida."
    # Regra especial preservada da versão hardcoded: "Descreva Outros" é obrigatório quando a
    # forma de pagamento escolhida é "Outros" — acoplada à chave, não generalizável sem lógica
    # condicional entre campos (fora de escopo da feature 123, ver spec/Assumptions).
    if any(fld.field_key == "descreva_outros" for fld in fields):
        if f.get("forma_pagamento") == "Outros" and not (f.get("descreva_outros") or "").strip():
            errors["descreva_outros"] = "Descreva a forma de pagamento."
    return errors


def _build_sections_dynamic(f, fields: list[FormFieldDefinition]) -> list[dict]:
    """Monta as seções ``[chave, rótulo, valor]`` a partir da definição de campos vigente.

    Agrupa pelo mesmo critério de ``_grouped_sections`` (por nome de seção, não por
    contiguidade em ``order``) — um campo personalizado inserido numa seção que já não está
    mais "por último" na ordenação global ainda cai na seção certa, sem duplicar o bloco.
    """
    by_section: dict[str, list[list[str]]] = {}
    section_order: list[str] = []
    for field in fields:
        if field.field_type == "telefone":
            value = _build_phone_display(f, field.field_key)
        elif field.field_type == "data":
            value = _fmt_date_br(_parse_event_date(f.get(field.field_key)))
        else:
            value = (f.get(field.field_key) or "").strip()
        if field.section_name not in by_section:
            by_section[field.section_name] = []
            section_order.append(field.section_name)
        by_section[field.section_name].append([field.field_key, field.label, value])
    return [{"secao": name, "campos": by_section[name]} for name in section_order]


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
