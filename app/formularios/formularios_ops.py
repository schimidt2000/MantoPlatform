"""Núcleo de negócio do lado staff/admin de Formulários (migração 177, US7).

Extraído de `app/formularios/routes.py` (rotas `/formularios/*`, exceto o fluxo público
`/f/*` — já coberto por `app/api/formularios_write.py` desde a feature 163) — funções puras
(sem `flask.request`/`render_template`/`flash`), reusadas tanto pela view Jinja quanto pelos
endpoints de API (`app/api/formularios_admin_read.py`, `app/api/formularios_admin_write.py`).
"""

from __future__ import annotations

import json
import re
import urllib.parse
from datetime import date, datetime

from sqlalchemy import not_
from sqlalchemy.orm import joinedload

from app import db
from app.clientes.importer import normalize_phone
from app.constants import now_sp
from app.models import (
    CalendarEvent,
    Client,
    EventClient,
    FormFieldDefinition,
    FormResponse,
    SiteSetting,
)
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


# Filtros de situação da listagem de respostas — chaves estáveis usadas pela API e pela tela.
STATUS_FILTERS = ("sem_evento", "sem_cliente", "ambiguos", "futuros_sem_evento")


def _status_condition(filtro: str):
    """Condição SQL de um filtro de situação (``None`` para filtro desconhecido/vazio)."""
    if filtro == "sem_evento":
        return FormResponse.event_id.is_(None)
    if filtro == "sem_cliente":
        return FormResponse.client_id.is_(None)
    if filtro == "ambiguos":
        # Ambíguo só interessa enquanto não resolvido — resposta já vinculada sai da fila.
        return db.and_(
            FormResponse.event_link_ambiguous.is_(True), FormResponse.event_id.is_(None)
        )
    if filtro == "futuros_sem_evento":
        # `now_sp()`, nunca `date.today()`: produção roda em UTC, e das 21h à meia-noite de
        # Brasília o "hoje" do processo já é amanhã — a festa de HOJE sairia da fila
        # justamente no horário em que a comercial confere o dia seguinte.
        return db.and_(
            FormResponse.event_id.is_(None), FormResponse.event_date >= now_sp().date()
        )
    return None


def count_status() -> dict[str, int]:
    """Contadores dos cartões-resumo da tela de formulários (1 query, sem N+1)."""
    row = db.session.query(
        db.func.count(FormResponse.id),
        *[
            db.func.count(FormResponse.id).filter(_status_condition(f))
            for f in STATUS_FILTERS
        ],
    ).one()
    return {"total": row[0], **{f: row[i + 1] for i, f in enumerate(STATUS_FILTERS)}}


def list_responses(limit: int = 200, filtro: str = "") -> list[FormResponse]:
    """Lista as respostas mais recentes (tela de índice), com filtro de situação opcional.

    O cliente vinculado vem em ``joinedload``: a listagem exibe o nome dele em cada linha
    (badge "Cliente: <nome>"), e sem isso seriam até ``limit`` queries extras (N+1).
    ``futuros_sem_evento`` ordena pela data do evento (o mais urgente primeiro) — é a fila
    de "festa chegando sem evento na agenda"; os demais mantêm o mais recente primeiro.
    """
    query = FormResponse.query.options(joinedload(FormResponse.client))
    condition = _status_condition(filtro)
    if condition is not None:
        query = query.filter(condition)
    if filtro == "futuros_sem_evento":
        query = query.order_by(FormResponse.event_date.asc())
    else:
        query = query.order_by(FormResponse.created_at.desc())
    return query.limit(limit).all()


def ensure_event_client(event: CalendarEvent, client_id: int | None) -> None:
    """Garante o cliente na associação evento↔cliente (``event_clients``), sem commit.

    É o elo que faltava entre o vínculo de formulário e a ficha da cliente: sem uma linha
    em ``event_clients``, o evento não aparece no perfil dela (correção de dados de
    06/08/2026 preencheu o retroativo; daqui em diante todo vínculo passa por aqui).
    Primeiro cliente do evento entra como Contratante (e assume o ``client_id``
    denormalizado); demais entram como Outros — o comercial ajusta a relação na tela do
    evento se for o caso.
    """
    if not client_id:
        return
    already = EventClient.query.filter_by(event_id=event.id, client_id=client_id).first()
    if already:
        return
    has_any = EventClient.query.filter_by(event_id=event.id).first() is not None
    db.session.add(
        EventClient(
            event_id=event.id,
            client_id=client_id,
            relationship_type="Outros" if has_any else "Contratante",
        )
    )
    if not has_any and event.client_id is None:
        event.client_id = client_id


def associate_client(response: FormResponse, client_id: int | None) -> Client:
    """Associa a resposta a um cliente existente ou cria um a partir dos dados dela.

    Se a resposta já estiver vinculada a um evento, o cliente também entra na associação
    evento↔cliente — é isso que faz o evento aparecer na ficha dela.

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
                # A ficha nasceu de uma resposta de formulário, não de digitação na tela —
                # é o que separa a aquisição por formulário do cadastro manual no gráfico
                # de origem (o mapa de `client_ops.client_metrics` traduz esta chave).
                source="formulario",
            )
            db.session.add(client)
            db.session.flush()
    fill_client_from_response(client, response)
    response.client_id = client.id
    response.client_link_source = "manual"
    if response.event_id is not None and response.event is not None:
        ensure_event_client(response.event, client.id)
    db.session.commit()
    return client


def dissociate_client(response: FormResponse) -> None:
    """Remove a associação da resposta com o cliente (e o rastro de como ela foi feita)."""
    response.client_id = None
    response.client_link_source = None
    db.session.commit()


def apply_event_link(
    response: FormResponse, event: CalendarEvent, *, source: str = "manual"
) -> None:
    """Grava o vínculo resposta→evento, **sem commit** (feature 267).

    Núcleo único dos quatro pontos que escreviam esse vínculo à mão. Até a 267, o caminho da
    agenda gravava só o `event_id` — sem `event_link_locked`, então o reprocessamento do próximo
    ciclo de sync (a cada 10 min) religava a resposta e desfazia a decisão humana em silêncio;
    e sem `ensure_event_client`, então o evento não aparecia na ficha da cliente.

    Sem commit de propósito: quem chama pode estar dentro de um laço ou de uma transação maior
    (um `*_ops` que commita dentro de laço quebra a transação única do request).

    Args:
        response: a resposta a vincular.
        event: o evento de destino (objeto, não id — `ensure_event_client` precisa dele).
        source: origem do vínculo, ``"manual"`` por padrão.
    """
    response.event_id = event.id
    response.event_link_source = source
    response.event_link_ambiguous = False
    response.event_link_locked = True
    ensure_event_client(event, response.client_id)


def clear_event_link(response: FormResponse) -> None:
    """Desfaz o vínculo de evento, **sem commit** (feature 267).

    Marca `event_link_locked`: uma vez que um humano decide desfazer, a automação não pode
    religar sozinha ao mesmo evento no próximo ciclo de sincronização.
    """
    response.event_id = None
    response.event_link_source = None
    response.event_link_ambiguous = False
    response.event_link_locked = True


def link_event(response: FormResponse, event_id: int) -> CalendarEvent:
    """Associa manualmente a resposta a um evento existente da agenda (feature 126).

    ⚠️ Este wrapper **sobrescreve** um vínculo existente. O caminho da agenda
    (`event_ops.set_event_form_response`) faz o contrário: **recusa** com 409 uma resposta já
    presa a outro evento. Por isso os dois compartilham o NÚCLEO (`apply_event_link`) e não o
    wrapper — delegar aqui mudaria o contrato da API.

    Raises:
        FormValidationError: evento não encontrado.
    """
    event = CalendarEvent.query.get(event_id)
    if not event:
        raise FormValidationError("event_id", "Evento não encontrado.")
    apply_event_link(response, event)
    db.session.commit()
    return event


def unlink_event(response: FormResponse) -> None:
    """Desfaz o vínculo de evento — automático ou manual (feature 126, FR-008)."""
    clear_event_link(response)
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


# ─────────────────────────────────────────────────────────────────────────────
# Núcleo dos formulários públicos, movido de `routes.py` na fase 3 da remoção do Jinja.
#
# Estes símbolos nunca foram só do Jinja: `app/api/formularios_write.py`,
# `app/api/catalogo_read.py`, `app/calendar/sync.py` e `app/cli.py` importavam-nos de dentro do
# blueprint. Enquanto morassem lá, apagar a superfície Jinja derrubava a API viva.
#
# Continuam puros: não importam `flask.request`, `render_template` nem `flash` — quem monta a
# resposta HTTP é a camada de rota, que passa o dicionário de campos por argumento.
# ─────────────────────────────────────────────────────────────────────────────

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


def _event_client_phones(event_id: int) -> set[str]:
    """Telefones dos clientes já associados a um evento (para checar contradição)."""
    return {
        ec.client.phone for ec in EventClient.query.filter_by(event_id=event_id).all()
        if ec.client and ec.client.phone
    }


def _attempt_auto_link(response: FormResponse) -> str | None:
    """Tenta vincular a resposta a um evento real da agenda (endurecido pós-feature 126).

    Só vincula sozinho quando os DOIS sinais confirmam: existe evento real na data
    informada E o telefone da resposta pertence a um cliente associado a exatamente um
    desses eventos. Qualquer coisa a menos vira revisão manual (``"ambiguous"``) — a
    Manto costuma ter vários eventos no mesmo dia e clientes recorrentes, então data
    sozinha ou identidade sozinha já vincularam resposta errada em evento errado
    (correção de dados de 06/08/2026: 25 vínculos desfeitos).

    Retorna ``"auto_date"`` se vinculou (persiste ``response.event_id`` no objeto, sem
    commit — quem chama decide quando salvar), ``"ambiguous"`` se há candidato na data
    mas sem confirmação pelo telefone, ou ``None`` se não havia evento na data.
    """
    if response.event_id is not None or response.event_link_locked or not response.event_date:
        return None

    candidates = _real_event_candidates(response.event_date)
    if not candidates:
        return None
    if not response.contact_phone:
        return "ambiguous"

    matched = [e for e in candidates if response.contact_phone in _event_client_phones(e.id)]
    if len(matched) == 1:
        response.event_id = matched[0].id
        return "auto_date"
    return "ambiguous"


def attempt_auto_link_client(response: FormResponse) -> str | None:
    """Vincula a resposta à ficha da cliente quando o telefone identifica uma só (feature 266).

    `Client.phone` é UNIQUE, então "bate com exatamente uma" é garantia do banco e não
    heurística: é literalmente a mesma consulta que a comercial dispara hoje clicando em
    "associar" na sugestão da tela. O que se ganha é não precisar do clique em toda resposta
    de cliente recorrente — o que hoje deixa o cartão "sem cliente" cheio de gente conhecida.

    **Nunca cria cliente**: o endpoint de submissão é público e sem autenticação, e deixá-lo
    inserir em ``clients`` seria porta aberta para poluir o CRM. Criar continua sendo ação
    humana, por ``associate_client``.

    Não roda no reprocessamento do sync de propósito (ver ``retry_auto_link_pending``): não
    existe equivalente de ``event_link_locked`` para cliente, então religar em ciclo desfaria
    a decisão de quem desassociou.

    Args:
        response: resposta recém-salva (sem commit — quem chama decide quando salvar).

    Returns:
        ``"auto_phone"`` se vinculou, ``None`` se não havia telefone, já havia vínculo, ou
        nenhuma ficha corresponde.
    """
    if response.client_id is not None or response.client_link_source or not response.contact_phone:
        return None
    client = Client.query.filter_by(phone=response.contact_phone).first()
    if client is None:
        return None
    fill_client_from_response(client, response)
    response.client_id = client.id
    return "auto_phone"


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
    return list_field_definitions(form_type)


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

