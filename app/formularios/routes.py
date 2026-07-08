"""Formulários públicos de pré-contrato + banco de respostas (feature 118).

Substitui o WhatsForm: dois formulários públicos (comum e corporativo) hospedados no
Manto. No envio válido, a resposta é salva em ``FormResponse`` ANTES de abrir o WhatsApp
da cliente com a mensagem formatada para o número da Manto (``SiteSetting.
whatsapp_form_number``). A área interna lista as respostas, permite associar a cliente
(sugestão por telefone normalizado), excluir (só SUPERADMIN) e buscar respostas para
vincular a um evento em ``/events/new``.
"""

from __future__ import annotations

import json
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
from app.models import Client, FormResponse, SiteSetting

formularios_bp = Blueprint("formularios", __name__)

DEFAULT_WHATSAPP_NUMBER = "5511970570577"

PAGAMENTO_COMUM = [
    "À vista",
    "Em 2x no PIX (50% no ato + 50% em até 2 dias antes do evento)",
    "Cartão de Crédito (em até 3x com acréscimo de 15%)",
    "Outros",
]
PAGAMENTO_CORPORATIVO = ["À vista antecipado", "Em 2x", "Faturado", "Boleto", "Outros"]
TIPOS_CONTRATACAO = ["Receptivo e Interativo", "Receptivo, Interativo e Show", "Social"]
ESPACOS_EVENTO = ["Residência", "Buffet", "Salão de Festas", "Outro"]


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
        for label, value in section["campos"]:
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


# ── Formulário comum (pessoa física) ─────────────────────────────────


def _validate_comum(f) -> dict[str, str]:
    """Valida o formulário comum; retorna erros por campo (vazio = ok)."""
    errors: dict[str, str] = {}
    required_text = [
        ("nome_contratante", "Informe o nome completo."),
        ("endereco_contratante", "Informe o endereço completo."),
        ("tipo_contratacao", "Selecione o tipo de contratação."),
        ("qtd_personagens", "Informe a quantidade de personagens."),
        ("quais_personagens", "Informe quais personagens."),
        ("tema_evento", "Informe o tema do evento."),
        ("periodo_contratacao", "Informe o período de contratação."),
        ("espaco_evento", "Selecione o espaço do evento."),
        ("logradouro", "Informe o logradouro."),
        ("numero", "Informe o número."),
        ("bairro", "Informe o bairro."),
        ("cidade", "Informe a cidade."),
        ("estado", "Informe o estado."),
        ("forma_pagamento", "Selecione a forma de pagamento."),
    ]
    for field, msg in required_text:
        if not (f.get(field) or "").strip():
            errors[field] = msg
    if len(_only_digits(f.get("cpf"))) != 11:
        errors["cpf"] = "CPF inválido — confira os 11 dígitos."
    email = (f.get("email") or "").strip()
    if not email or not _valid_email(email):
        errors["email"] = "Informe um e-mail válido."
    if len(_only_digits(f.get("whatsapp_national"))) < 10:
        errors["whatsapp_national"] = "Informe o WhatsApp com DDD."
    if not _parse_event_date(f.get("data_evento")):
        errors["data_evento"] = "Selecione a data do evento."
    if not (f.get("hora_evento") or "").strip():
        errors["hora_evento"] = "Selecione o horário."
    if len(_only_digits(f.get("cep"))) != 8:
        errors["cep"] = "CEP inválido — confira os 8 dígitos."
    if f.get("forma_pagamento") == "Outros" and not (f.get("descreva_outros") or "").strip():
        errors["descreva_outros"] = "Descreva a forma de pagamento."
    return errors


def _sections_comum(f) -> list[dict]:
    """Monta as seções rótulo→valor do formulário comum (ordem do documento)."""
    endereco = ", ".join(part for part in [
        (f.get("logradouro") or "").strip(),
        (f.get("numero") or "").strip(),
        (f.get("complemento") or "").strip(),
    ] if part)
    return [
        {"secao": "Dados do Contratante", "campos": [
            ["Nome Completo Contratante", (f.get("nome_contratante") or "").strip()],
            ["Endereço completo da contratante", (f.get("endereco_contratante") or "").strip()],
            ["CPF", (f.get("cpf") or "").strip()],
            ["E-mail", (f.get("email") or "").strip()],
            ["Número de WhatsApp", _build_phone_display(f, "whatsapp")],
            ["Telefone da assessoria", _build_phone_display(f, "assessoria")],
        ]},
        {"secao": "Dados do Evento", "campos": [
            ["Nome do Aniversariante", (f.get("nome_aniversariante") or "").strip()],
            ["Idade a Completar", (f.get("idade_aniversariante") or "").strip()],
            ["Tipo de Contratação", (f.get("tipo_contratacao") or "").strip()],
            ["Quantidade de Personagens", (f.get("qtd_personagens") or "").strip()],
            ["Quais personagens", (f.get("quais_personagens") or "").strip()],
            ["Tema do Evento", (f.get("tema_evento") or "").strip()],
            ["Data do Evento", _fmt_date_br(_parse_event_date(f.get("data_evento")))],
            ["Hora do Evento", (f.get("hora_evento") or "").strip()],
            ["Período de Contratação", (f.get("periodo_contratacao") or "").strip()],
        ]},
        {"secao": "Endereço do Evento", "campos": [
            ["Espaço Escolhido", (f.get("espaco_evento") or "").strip()],
            ["CEP", (f.get("cep") or "").strip()],
            ["Endereço", endereco],
            ["Bairro", (f.get("bairro") or "").strip()],
            ["Cidade", (f.get("cidade") or "").strip()],
            ["Estado", (f.get("estado") or "").strip()],
        ]},
        {"secao": "Pagamento e Observações", "campos": [
            ["Forma de Pagamento", (f.get("forma_pagamento") or "").strip()],
            ["Descreva Outros", (f.get("descreva_outros") or "").strip()],
            ["Observações Contratuais", (f.get("observacoes") or "").strip()],
        ]},
    ]


def _render_comum(form, errors: dict, status: int = 200):
    """Renderiza o formulário comum preservando os valores digitados (FR-004)."""
    return render_template(
        "formularios/pre_contrato.html", form=form, errors=errors,
        tipos_contratacao=TIPOS_CONTRATACAO, espacos_evento=ESPACOS_EVENTO,
        pagamento_opcoes=PAGAMENTO_COMUM), status


@formularios_bp.route("/f/pre-contrato", methods=["GET"])
def form_comum():
    """Formulário público de pré-contrato (pessoa física)."""
    return _render_comum(request.form, {})


@formularios_bp.route("/f/pre-contrato", methods=["POST"])
@limiter.limit("10 per hour")
def submit_comum():
    """Valida, salva e devolve a página que abre o WhatsApp com a resposta."""
    f = request.form
    # Honeypot anti-bot: campo oculto que humanos não preenchem.
    if (f.get("website") or "").strip():
        return render_template("formularios/enviado.html", wa_link="", contact_name="")
    errors = _validate_comum(f)
    if errors:
        return _render_comum(f, errors, 400)
    sections = _sections_comum(f)
    contact_name = (f.get("nome_contratante") or "").strip()
    _save_response(
        "comum", contact_name, _build_phone_display(f, "whatsapp"),
        _parse_event_date(f.get("data_evento")), sections)
    message = _build_message("INFORMAÇÕES PARA PRÉ-CONTRATO — MANTO PRODUÇÕES", sections)
    return render_template(
        "formularios/enviado.html", wa_link=_whatsapp_link(message),
        contact_name=contact_name)


# ── Formulário corporativo (pessoa jurídica) ─────────────────────────


def _validate_corporativo(f) -> dict[str, str]:
    """Valida o formulário corporativo; retorna erros por campo (vazio = ok)."""
    errors: dict[str, str] = {}
    required_text = [
        ("razao_social", "Informe a razão social."),
        ("representante_legal", "Informe o representante legal."),
        ("endereco_empresa", "Informe o endereço da empresa."),
        ("nome_responsavel", "Informe o nome do responsável."),
        ("endereco_evento", "Informe o endereço completo do evento."),
        ("periodo_contratacao", "Informe o período de contratação."),
        ("briefing", "Descreva o briefing do evento."),
        ("forma_pagamento", "Selecione a forma de pagamento."),
    ]
    for field, msg in required_text:
        if not (f.get(field) or "").strip():
            errors[field] = msg
    if len(_only_digits(f.get("cnpj"))) != 14:
        errors["cnpj"] = "CNPJ inválido — confira os 14 dígitos."
    email = (f.get("email") or "").strip()
    if not email or not _valid_email(email):
        errors["email"] = "Informe um e-mail válido."
    if len(_only_digits(f.get("telefone_national"))) < 10:
        errors["telefone_national"] = "Informe o telefone da empresa com DDD."
    if len(_only_digits(f.get("cpf_responsavel"))) != 11:
        errors["cpf_responsavel"] = "CPF inválido — confira os 11 dígitos."
    if len(_only_digits(f.get("whatsapp_national"))) < 10:
        errors["whatsapp_national"] = "Informe o WhatsApp com DDD."
    if not _parse_event_date(f.get("data_evento")):
        errors["data_evento"] = "Selecione a data do evento."
    if not (f.get("hora_evento") or "").strip():
        errors["hora_evento"] = "Selecione o horário."
    if f.get("forma_pagamento") == "Outros" and not (f.get("descreva_outros") or "").strip():
        errors["descreva_outros"] = "Descreva a forma de pagamento."
    return errors


def _sections_corporativo(f) -> list[dict]:
    """Monta as seções rótulo→valor do formulário corporativo (ordem do documento)."""
    return [
        {"secao": "Informações da Empresa", "campos": [
            ["Razão Social", (f.get("razao_social") or "").strip()],
            ["CNPJ", (f.get("cnpj") or "").strip()],
            ["Representante Legal", (f.get("representante_legal") or "").strip()],
            ["E-mail", (f.get("email") or "").strip()],
            ["Telefone", _build_phone_display(f, "telefone")],
            ["Endereço", (f.get("endereco_empresa") or "").strip()],
        ]},
        {"secao": "Responsável pelo Preenchimento", "campos": [
            ["Nome Completo", (f.get("nome_responsavel") or "").strip()],
            ["CPF", (f.get("cpf_responsavel") or "").strip()],
            ["Número de WhatsApp", _build_phone_display(f, "whatsapp")],
        ]},
        {"secao": "Dados do Evento Corporativo", "campos": [
            ["Data do Evento", _fmt_date_br(_parse_event_date(f.get("data_evento")))],
            ["Hora do Evento", (f.get("hora_evento") or "").strip()],
            ["Endereço completo do evento", (f.get("endereco_evento") or "").strip()],
            ["Período de Contratação", (f.get("periodo_contratacao") or "").strip()],
            ["Briefing do Evento", (f.get("briefing") or "").strip()],
        ]},
        {"secao": "Condições de Pagamento", "campos": [
            ["Forma de Pagamento", (f.get("forma_pagamento") or "").strip()],
            ["Descreva Outros", (f.get("descreva_outros") or "").strip()],
        ]},
    ]


def _render_corporativo(form, errors: dict, status: int = 200):
    """Renderiza o formulário corporativo preservando os valores digitados (FR-004)."""
    return render_template(
        "formularios/corporativo.html", form=form, errors=errors,
        pagamento_opcoes=PAGAMENTO_CORPORATIVO), status


@formularios_bp.route("/f/corporativo", methods=["GET"])
def form_corporativo():
    """Formulário público de contrato corporativo (pessoa jurídica)."""
    return _render_corporativo(request.form, {})


@formularios_bp.route("/f/corporativo", methods=["POST"])
@limiter.limit("10 per hour")
def submit_corporativo():
    """Valida, salva e devolve a página que abre o WhatsApp com a resposta."""
    f = request.form
    if (f.get("website") or "").strip():
        return render_template("formularios/enviado.html", wa_link="", contact_name="")
    errors = _validate_corporativo(f)
    if errors:
        return _render_corporativo(f, errors, 400)
    sections = _sections_corporativo(f)
    contact_name = (f.get("razao_social") or "").strip()
    _save_response(
        "corporativo", contact_name, _build_phone_display(f, "whatsapp"),
        _parse_event_date(f.get("data_evento")), sections)
    message = _build_message("CONTRATO CORPORATIVO — MANTO PRODUÇÕES", sections)
    return render_template(
        "formularios/enviado.html", wa_link=_whatsapp_link(message),
        contact_name=contact_name)


# ── Área interna: banco de respostas ─────────────────────────────────


@formularios_bp.route("/formularios/")
@require_vendas
def index():
    """Seção de formulários: links copiáveis + listagem das respostas."""
    responses = FormResponse.query.order_by(FormResponse.created_at.desc()).limit(200).all()
    return render_template("formularios/index.html", responses=responses)


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
    from app.utils import strip_accents_lower, unaccent_lower_sql

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
