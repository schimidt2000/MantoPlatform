"""Formulários públicos de pré-contrato + banco de respostas (feature 118).

Substitui o WhatsForm: dois formulários públicos (comum e corporativo) hospedados no
Manto. No envio válido, a resposta é salva em ``FormResponse`` ANTES de abrir o WhatsApp
da cliente com a mensagem formatada para o número da Manto (``SiteSetting.
whatsapp_form_number``). A área interna lista as respostas, permite associar a cliente
(sugestão por telefone normalizado), excluir (só SUPERADMIN) e buscar respostas para
vincular a um evento em ``/events/new``.

A estrutura dos dois formulários (seções, campos, tipos, obrigatoriedade, ordem) é
editável pelo painel (SUPERADMIN) via ``FormFieldDefinition`` — feature 123. As rotas
públicas renderizam e validam dinamicamente a partir dessa tabela em vez de campos
hardcoded no código.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from datetime import date, datetime
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from app import db, limiter
from app.clientes.importer import normalize_phone
from app.constants import RoleName
from app.models import Client, FormFieldDefinition, FormResponse, SiteSetting
from app.utils import strip_accents_lower

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

# Chaves de campos-sistema usadas pela automação de CPF/CNPJ/endereço do cliente (feature 119)
# — busca por chave estável, sobrevive a renomeação do rótulo pelo editor (FR-009 da 123).
SYSTEM_KEY_CPF = "cpf"
SYSTEM_KEY_CNPJ = "cnpj"
SYSTEM_KEY_ADDRESS_COMUM = "endereco_contratante"
SYSTEM_KEY_ADDRESS_CORPORATIVO = "endereco_empresa"

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


def _field_value_by_key(sections: list[dict], field_key: str) -> str:
    """Busca o valor de um campo pela chave estável (feature 123 — sobrevive a renomeação de
    rótulo). Respostas anteriores à feature 123 têm campos com só ``[rótulo, valor]``, sem
    chave — nesse caso a busca simplesmente não encontra nada (mesmo comportamento best-effort
    que a automação já tinha antes)."""
    for section in sections:
        for campo in section["campos"]:
            if len(campo) == 3 and campo[0] == field_key:
                return (campo[2] or "").strip()
    return ""


def _fill_client_from_response(client: Client, response: FormResponse) -> None:
    """Completa CPF/CNPJ e endereço do cliente com dados da resposta (feature 119).

    Só preenche campos que estiverem vazios no cliente — nunca sobrescreve um valor já
    existente (manual ou de uma associação anterior).
    """
    sections = response.data_sections
    if response.form_type == "corporativo":
        cnpj = _field_value_by_key(sections, SYSTEM_KEY_CNPJ)
        address = _field_value_by_key(sections, SYSTEM_KEY_ADDRESS_CORPORATIVO)
        if cnpj and not client.cnpj:
            client.cnpj = cnpj
        if address and not client.address:
            client.address = address
    else:
        cpf = _field_value_by_key(sections, SYSTEM_KEY_CPF)
        address = _field_value_by_key(sections, SYSTEM_KEY_ADDRESS_COMUM)
        if cpf and not client.cpf:
            client.cpf = cpf
        if address and not client.address:
            client.address = address


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


# ── Motor dinâmico dos formulários públicos (feature 123) ────────────


def _load_fields(form_type: str) -> list[FormFieldDefinition]:
    """Campos de um formulário, na ordem de exibição vigente."""
    return (
        FormFieldDefinition.query.filter_by(form_type=form_type)
        .order_by(FormFieldDefinition.order)
        .all()
    )


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
    _save_response(
        form_type, contact_name, _build_phone_display(f, "whatsapp"),
        _parse_event_date(f.get("data_evento")), sections)
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
    responses = FormResponse.query.order_by(FormResponse.created_at.desc()).limit(200).all()
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
    client_id = request.form.get("client_id")
    if client_id:
        client = Client.query.get(client_id)
        if not client:
            flash("Cliente não encontrado.", "error")
            return redirect(url_for("formularios.detail", response_id=response.id))
    else:
        # Criar a partir da resposta (dedup por telefone normalizado — FR-008)
        phone = response.contact_phone
        if not phone:
            flash("A resposta não tem telefone válido para criar o cliente.", "error")
            return redirect(url_for("formularios.detail", response_id=response.id))
        client = Client.query.filter_by(phone=phone).first()
        if not client:
            client = Client(
                name=response.contact_name,
                phone=phone,
                phone_display=response.contact_phone_display,
                source="manual",
            )
            db.session.add(client)
            db.session.flush()
    _fill_client_from_response(client, response)
    response.client_id = client.id
    db.session.commit()
    flash(f"Resposta associada ao cliente {client.name}.", "success")
    return redirect(url_for("formularios.detail", response_id=response.id))


@formularios_bp.route("/formularios/respostas/<int:response_id>/desassociar", methods=["POST"])
@require_vendas
def desassociar(response_id: int):
    """Remove a associação da resposta com o cliente."""
    response = FormResponse.query.get_or_404(response_id)
    response.client_id = None
    db.session.commit()
    flash("Associação removida.", "success")
    return redirect(url_for("formularios.detail", response_id=response.id))


@formularios_bp.route("/formularios/respostas/<int:response_id>/delete", methods=["POST"])
@require_vendas
def delete(response_id: int):
    """Exclui uma resposta — apenas SUPERADMIN (FR-009)."""
    if not _has_role(RoleName.SUPERADMIN):
        abort(403)
    response = FormResponse.query.get_or_404(response_id)
    db.session.delete(response)
    db.session.commit()
    flash("Resposta excluída.", "success")
    return redirect(url_for("formularios.index"))


@formularios_bp.route("/formularios/respostas/search")
@require_vendas
def search():
    """Busca respostas (JSON) para o buscador de ``/events/new`` — sem acento (FR-010)."""
    from app.utils import unaccent_lower_sql

    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    like = f"%{strip_accents_lower(q)}%"
    digits = _only_digits(q)
    conditions = [unaccent_lower_sql(FormResponse.contact_name).like(like)]
    if digits:
        conditions.append(FormResponse.contact_phone.ilike(f"%{digits}%"))
    results = (
        FormResponse.query.filter(or_(*conditions))
        .order_by(FormResponse.created_at.desc())
        .limit(10)
        .all()
    )
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


def _unique_field_key(form_type: str, label: str) -> str:
    """Gera uma chave estável (slug) a partir do rótulo, única dentro do formulário."""
    base = re.sub(r"[^a-z0-9]+", "_", strip_accents_lower(label)).strip("_") or "campo"
    existing = {
        row[0] for row in
        db.session.query(FormFieldDefinition.field_key).filter_by(form_type=form_type).all()
    }
    key = base
    suffix = 2
    while key in existing:
        key = f"{base}_{suffix}"
        suffix += 1
    return key


def _next_order(form_type: str) -> int:
    """Posição no fim da lista global — o agrupamento por seção não depende de contiguidade em
    ``order`` (ver ``_grouped_sections``), então um campo novo sempre cai no fim da sua seção."""
    last = (
        FormFieldDefinition.query.filter_by(form_type=form_type)
        .order_by(FormFieldDefinition.order.desc())
        .first()
    )
    return (last.order + 1) if last else 0


def _parse_options(raw: str) -> list[str]:
    return [line.strip() for line in (raw or "").splitlines() if line.strip()]


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
    label = (request.form.get("label") or "").strip()
    section_name = (request.form.get("section_name") or "").strip()
    field_type = request.form.get("field_type") or ""
    if not label or not section_name:
        flash("Informe o rótulo e a seção do campo.", "error")
        return redirect(url_for("formularios.editor", form_type=form_type))
    if field_type not in FormFieldDefinition.FIELD_TYPES:
        flash("Tipo de campo inválido.", "error")
        return redirect(url_for("formularios.editor", form_type=form_type))
    options = None
    if field_type == "selecao":
        opts = _parse_options(request.form.get("options"))
        if not opts:
            flash("Um campo de seleção precisa de pelo menos uma opção.", "error")
            return redirect(url_for("formularios.editor", form_type=form_type))
        options = json.dumps(opts, ensure_ascii=False)
    field = FormFieldDefinition(
        form_type=form_type, section_name=section_name,
        field_key=_unique_field_key(form_type, label), field_type=field_type, label=label,
        help_text=(request.form.get("help_text") or "").strip() or None,
        required=request.form.get("required") == "on", options=options,
        order=_next_order(form_type), is_system=False,
    )
    db.session.add(field)
    db.session.commit()
    flash(f'Campo "{label}" adicionado.', "success")
    return redirect(url_for("formularios.editor", form_type=form_type))


@formularios_bp.route("/formularios/editor/campo/<int:field_id>/editar", methods=["POST"])
@require_superadmin
def editor_editar_campo(field_id: int):
    """Edita rótulo/texto de ajuda/obrigatoriedade/opções de um campo (US1 — feature 123).

    ``field_type`` e ``field_key`` são imutáveis após criação — evita inconsistência de
    formato em respostas já salvas e preserva a busca por chave da feature 119.
    """
    field = FormFieldDefinition.query.get_or_404(field_id)
    label = (request.form.get("label") or "").strip()
    if not label:
        flash("O rótulo não pode ficar vazio.", "error")
        return redirect(url_for("formularios.editor", form_type=field.form_type))
    if field.field_type == "selecao":
        opts = _parse_options(request.form.get("options"))
        if not opts:
            flash("Um campo de seleção precisa de pelo menos uma opção.", "error")
            return redirect(url_for("formularios.editor", form_type=field.form_type))
        field.options = json.dumps(opts, ensure_ascii=False)
    field.label = label
    field.help_text = (request.form.get("help_text") or "").strip() or None
    field.placeholder = (request.form.get("placeholder") or "").strip() or None
    field.required = request.form.get("required") == "on"
    db.session.commit()
    flash(f'Campo "{field.label}" atualizado.', "success")
    return redirect(url_for("formularios.editor", form_type=field.form_type))


@formularios_bp.route("/formularios/editor/campo/<int:field_id>/mover", methods=["POST"])
@require_superadmin
def editor_mover_campo(field_id: int):
    """Reordena um campo dentro da própria seção (US3 — feature 123)."""
    field = FormFieldDefinition.query.get_or_404(field_id)
    direction = request.form.get("direction")
    siblings = (
        FormFieldDefinition.query
        .filter_by(form_type=field.form_type, section_name=field.section_name)
        .order_by(FormFieldDefinition.order)
        .all()
    )
    idx = siblings.index(field)
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(siblings):
        other = siblings[swap_idx]
        field.order, other.order = other.order, field.order
        db.session.commit()
    return redirect(url_for("formularios.editor", form_type=field.form_type))


@formularios_bp.route("/formularios/editor/campo/<int:field_id>/excluir", methods=["POST"])
@require_superadmin
def editor_excluir_campo(field_id: int):
    """Remove um campo personalizado (US3 — feature 123). Campos de sistema são protegidos."""
    field = FormFieldDefinition.query.get_or_404(field_id)
    if field.is_system:
        flash(
            f'"{field.label}" é um campo do sistema (usado por outras telas) e não pode ser '
            "removido — só o texto e a obrigatoriedade podem ser ajustados.", "error")
        return redirect(url_for("formularios.editor", form_type=field.form_type))
    form_type = field.form_type
    db.session.delete(field)
    db.session.commit()
    flash("Campo removido.", "success")
    return redirect(url_for("formularios.editor", form_type=form_type))
