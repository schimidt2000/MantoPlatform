"""Núcleo de negócio do lado staff/admin de Formulários (migração 177, US7).

Extraído de `app/formularios/routes.py` (rotas `/formularios/*`, exceto o fluxo público
`/f/*` — já coberto por `app/api/formularios_write.py` desde a feature 163) — funções puras
(sem `flask.request`/`render_template`/`flash`), reusadas tanto pela view Jinja quanto pelos
endpoints de API (`app/api/formularios_admin_read.py`, `app/api/formularios_admin_write.py`).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime

from sqlalchemy.orm import joinedload

from app import db
from app.models import CalendarEvent, Client, FormFieldDefinition, FormResponse
from app.utils import strip_accents_lower, unaccent_lower_sql

# Chaves de campos-sistema usadas pela automação de CPF/CNPJ/endereço do cliente (feature 119)
# — busca por chave estável, sobrevive a renomeação do rótulo pelo editor (FR-009 da 123).
SYSTEM_KEY_CPF = "cpf"
SYSTEM_KEY_CNPJ = "cnpj"
SYSTEM_KEY_ADDRESS_COMUM = "endereco_contratante"
SYSTEM_KEY_ADDRESS_CORPORATIVO = "endereco_empresa"


class FormValidationError(Exception):
    """Erro de validação de negócio (campo obrigatório/inválido, ação bloqueada)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


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


def fill_client_from_response(client: Client, response: FormResponse) -> None:
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


def _data_do_termo(q: str) -> date | None:
    """Interpreta o termo como data do evento: `dd/mm/aaaa`, `dd/mm/aa`, `dd-mm-aaaa` ou ISO.

    O buscador de pré-contrato oferece "nome, telefone ou data" — sem isto, digitar a data do
    evento (o jeito mais natural de achar a resposta de uma cliente cujo nome não se lembra)
    devolvia lista vazia.
    """
    termo = q.strip()
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(termo, formato).date()
        except ValueError:
            continue
    return None


def search_responses(q: str) -> list[FormResponse]:
    """Busca respostas por nome, telefone ou data do evento (sem acentos).

    Usado pelo buscador de pré-contrato de `/events/new` e `/events/<id>/edit`.
    """
    q = (q or "").strip()
    if len(q) < 2:
        return []
    like = f"%{strip_accents_lower(q)}%"
    # Só conta como telefone o que tem dígito suficiente para não casar com tudo: "12" (de uma
    # data digitada pela metade) traria meio banco.
    digits = "".join(c for c in q if c.isdigit())
    conditions = [unaccent_lower_sql(FormResponse.contact_name).like(like)]
    if len(digits) >= 4:
        conditions.append(FormResponse.contact_phone.ilike(f"%{digits}%"))
    data = _data_do_termo(q)
    if data is not None:
        conditions.append(FormResponse.event_date == data)
    from sqlalchemy import or_

    return (
        FormResponse.query.options(joinedload(FormResponse.client))
        .filter(or_(*conditions))
        .order_by(FormResponse.created_at.desc())
        .limit(10)
        .all()
    )


def list_responses(limit: int = 200) -> list[FormResponse]:
    """Lista as respostas mais recentes (tela de índice).

    O cliente vinculado vem em ``joinedload``: a listagem exibe o nome dele em cada linha
    (badge "Cliente: <nome>"), e sem isso seriam até ``limit`` queries extras (N+1).
    """
    return (
        FormResponse.query.options(joinedload(FormResponse.client))
        .order_by(FormResponse.created_at.desc())
        .limit(limit)
        .all()
    )


def associate_client(response: FormResponse, client_id: int | None) -> Client:
    """Associa a resposta a um cliente existente ou cria um a partir dos dados dela.

    Raises:
        FormValidationError: cliente informado não encontrado, ou resposta sem telefone
            válido para criar um cliente novo.
    """
    if client_id:
        client = Client.query.get(client_id)
        if not client:
            raise FormValidationError("client_id", "Cliente não encontrado.")
    else:
        phone = response.contact_phone
        if not phone:
            raise FormValidationError(
                "client_id", "A resposta não tem telefone válido para criar o cliente."
            )
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
    fill_client_from_response(client, response)
    response.client_id = client.id
    db.session.commit()
    return client


def dissociate_client(response: FormResponse) -> None:
    """Remove a associação da resposta com o cliente."""
    response.client_id = None
    db.session.commit()


def link_event(response: FormResponse, event_id: int) -> CalendarEvent:
    """Associa manualmente a resposta a um evento existente da agenda (feature 126).

    Marca `event_link_locked` — a partir daqui, a automação nunca mais tenta decidir
    sozinha por essa resposta (respeita a decisão humana).

    Raises:
        FormValidationError: evento não encontrado.
    """
    event = CalendarEvent.query.get(event_id)
    if not event:
        raise FormValidationError("event_id", "Evento não encontrado.")
    response.event_id = event.id
    response.event_link_source = "manual"
    response.event_link_ambiguous = False
    response.event_link_locked = True
    db.session.commit()
    return event


def unlink_event(response: FormResponse) -> None:
    """Desfaz o vínculo de evento — automático ou manual (feature 126, FR-008).

    Também marca `event_link_locked`: uma vez que um humano decide desfazer, a automação
    não pode religar sozinha ao mesmo evento no próximo ciclo de sincronização.
    """
    response.event_id = None
    response.event_link_source = None
    response.event_link_ambiguous = False
    response.event_link_locked = True
    db.session.commit()


def delete_response(response: FormResponse) -> None:
    """Exclui uma resposta — chamador já deve ter checado a permissão (SUPERADMIN)."""
    db.session.delete(response)
    db.session.commit()


# ── Editor de estrutura dos formulários (feature 123) ────────────────


def list_field_definitions(form_type: str) -> list[FormFieldDefinition]:
    """Campos de um formulário, na ordem de exibição vigente."""
    return (
        FormFieldDefinition.query.filter_by(form_type=form_type)
        .order_by(FormFieldDefinition.order)
        .all()
    )


def _unique_field_key(form_type: str, label: str) -> str:
    """Gera uma chave estável (slug) a partir do rótulo, única dentro do formulário."""
    base = re.sub(r"[^a-z0-9]+", "_", strip_accents_lower(label)).strip("_") or "campo"
    existing = {
        row[0]
        for row in db.session.query(FormFieldDefinition.field_key).filter_by(form_type=form_type).all()
    }
    key = base
    suffix = 2
    while key in existing:
        key = f"{base}_{suffix}"
        suffix += 1
    return key


def _next_order(form_type: str) -> int:
    """Posição no fim da lista global — o agrupamento por seção não depende de contiguidade em
    `order`, então um campo novo sempre cai no fim da sua seção."""
    last = (
        FormFieldDefinition.query.filter_by(form_type=form_type)
        .order_by(FormFieldDefinition.order.desc())
        .first()
    )
    return (last.order + 1) if last else 0


def _parse_options(raw: str) -> list[str]:
    return [line.strip() for line in (raw or "").splitlines() if line.strip()]


def create_field(form_type: str, data: dict) -> FormFieldDefinition:
    """Adiciona um campo personalizado ao fim de uma seção.

    Args:
        data: `label`, `section_name`, `field_type`, `help_text`, `required` (bool),
            `options` (string com uma opção por linha, só para `field_type == "selecao"`).

    Raises:
        FormValidationError: rótulo/seção ausente, tipo inválido, ou seleção sem opções.
    """
    label = (data.get("label") or "").strip()
    section_name = (data.get("section_name") or "").strip()
    field_type = data.get("field_type") or ""
    if not label or not section_name:
        raise FormValidationError("label", "Informe o rótulo e a seção do campo.")
    if field_type not in FormFieldDefinition.FIELD_TYPES:
        raise FormValidationError("field_type", "Tipo de campo inválido.")
    options = None
    if field_type == "selecao":
        opts = _parse_options(data.get("options", ""))
        if not opts:
            raise FormValidationError(
                "options", "Um campo de seleção precisa de pelo menos uma opção."
            )
        options = json.dumps(opts, ensure_ascii=False)
    field = FormFieldDefinition(
        form_type=form_type,
        section_name=section_name,
        field_key=_unique_field_key(form_type, label),
        field_type=field_type,
        label=label,
        help_text=(data.get("help_text") or "").strip() or None,
        required=bool(data.get("required")),
        options=options,
        order=_next_order(form_type),
        is_system=False,
    )
    db.session.add(field)
    db.session.commit()
    return field


def update_field(field: FormFieldDefinition, data: dict) -> FormFieldDefinition:
    """Edita rótulo/texto de ajuda/obrigatoriedade/opções de um campo.

    `field_type`/`field_key` são imutáveis após criação (nunca alterados aqui) — evita
    inconsistência de formato em respostas já salvas e preserva a busca por chave (feature 119).

    Raises:
        FormValidationError: rótulo vazio, ou seleção sem opções.
    """
    label = (data.get("label") or "").strip()
    if not label:
        raise FormValidationError("label", "O rótulo não pode ficar vazio.")
    if field.field_type == "selecao":
        opts = _parse_options(data.get("options", ""))
        if not opts:
            raise FormValidationError(
                "options", "Um campo de seleção precisa de pelo menos uma opção."
            )
        field.options = json.dumps(opts, ensure_ascii=False)
    field.label = label
    field.help_text = (data.get("help_text") or "").strip() or None
    field.placeholder = (data.get("placeholder") or "").strip() or None
    field.required = bool(data.get("required"))
    db.session.commit()
    return field


def move_field(field: FormFieldDefinition, direction: str) -> None:
    """Reordena um campo dentro da própria seção (`direction`: `"up"`/`"down"`)."""
    siblings = (
        FormFieldDefinition.query.filter_by(form_type=field.form_type, section_name=field.section_name)
        .order_by(FormFieldDefinition.order)
        .all()
    )
    idx = siblings.index(field)
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(siblings):
        other = siblings[swap_idx]
        field.order, other.order = other.order, field.order
        db.session.commit()


def delete_field(field: FormFieldDefinition) -> None:
    """Remove um campo personalizado.

    Raises:
        FormValidationError: campo é `is_system` (usado por outras partes do sistema).
    """
    if field.is_system:
        raise FormValidationError(
            "is_system",
            f'"{field.label}" é um campo do sistema (usado por outras telas) e não pode ser '
            "removido — só o texto e a obrigatoriedade podem ser ajustados.",
        )
    db.session.delete(field)
    db.session.commit()
