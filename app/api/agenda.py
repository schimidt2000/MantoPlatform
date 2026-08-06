"""Endpoints de leitura da Agenda/Eventos (`/api/agenda*`) — feature 145, US1.

Só leitura: lê do banco, nunca dispara sincronização com o Google (sync manual é ação de
escrita, fatia US5). As views Jinja `/agenda` e `/agenda/day/<date>` seguem intactas.
"""

from datetime import datetime
from typing import Any

from flask import jsonify, request, session
from flask_login import current_user

from app.api import api_bp
from app.api.agenda_read import (
    build_agenda_month,
    client_of_event,
    serialize_event_detail,
    serialize_event_summary,
)
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import CalendarEvent, Talent


@api_bp.route("/agenda")
@api_login_required
def api_agenda() -> Any:
    """Agenda de um mês (`?ym=YYYY-MM`; sem parâmetro usa o mês atual)."""
    ym = (request.args.get("ym") or "").strip()
    if ym:
        try:
            year_str, month_str = ym.split("-")
            year, month = int(year_str), int(month_str)
            if not 1 <= month <= 12:
                raise ValueError
        except (ValueError, AttributeError):
            return json_error("Mês inválido (use YYYY-MM)", 400)
    else:
        now = datetime.now()
        year, month = now.year, now.month

    return jsonify(build_agenda_month(year, month))


@api_bp.route("/agenda/search")
@api_login_required
def api_agenda_search() -> Any:
    """Busca textual de eventos (`?q=`) por título, nome ou telefone da cliente.

    Rota separada do `GET /api/agenda` de propósito — o contrato `ym`/`by_day` das três
    visões fica intocado (Princípio IV). Nome/telefone da cliente só saem no JSON para
    papéis de vendas (paridade com `_require_vendas` do CRM): os demais ACHAM o evento
    digitando o telefone, mas recebem os campos como `null`.
    """
    from app.calendar.event_ops import SEARCH_LIMIT, search_events

    q = (request.args.get("q") or "").strip()
    events = search_events(q)

    vendas_roles = {RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN}
    can_see_client = any(r.name.upper() in vendas_roles for r in current_user.roles)

    items = []
    for event in events:
        summary = serialize_event_summary(event)
        client_name, client_phone = client_of_event(event) if can_see_client else (None, None)
        summary["client_name"] = client_name
        summary["client_phone_display"] = client_phone
        items.append(summary)

    return jsonify({"q": q, "items": items, "total": len(items), "limit": SEARCH_LIMIT})


@api_bp.route("/agenda/day/<date_str>")
@api_login_required
def api_agenda_day(date_str: str) -> Any:
    """Eventos de um dia específico (`date_str` = YYYY-MM-DD)."""
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return json_error("Data inválida (use YYYY-MM-DD)", 400)

    day_start = datetime(day.year, day.month, day.day)
    day_end = datetime.fromordinal(day_start.toordinal() + 1)
    events = (
        CalendarEvent.query
        .filter(CalendarEvent.start_at >= day_start, CalendarEvent.start_at < day_end)
        .order_by(CalendarEvent.start_at)
        .all()
    )
    return jsonify(
        {"day": day.isoformat(), "events": [serialize_event_summary(e) for e in events]}
    )


@api_bp.route("/talents")
@api_login_required
def api_talents() -> Any:
    """Talentos ativos para o seletor de casting (id + nome)."""
    talents = (
        Talent.query.filter_by(status="active").order_by(Talent.full_name.asc()).all()
    )
    return jsonify(
        {
            "items": [
                {"id": t.id, "name": t.full_name, "artistic_name": t.artistic_name}
                for t in talents
            ]
        }
    )


@api_bp.route("/events/<int:event_id>/casting-options")
@api_login_required
def api_event_casting_options(event_id: int) -> Any:
    """Talentos escaláveis neste evento, com foto e agenda do dia (feature 215).

    Diferente de `/api/talents` (lista chapada usada por telas sem contexto de data), aqui cada
    talento vem com `photo_url` e `availability` calculados contra a janela DESTE evento — é o
    que a busca de casting mostra antes de escalar, não só depois.
    """
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)

    from app.calendar.event_ops import assignable_talents_for_event

    return jsonify({"items": assignable_talents_for_event(event)})


@api_bp.route("/events/<int:event_id>")
@api_login_required
def api_event_detail(event_id: int) -> Any:
    """Detalhe do evento (leitura), com blocos financeiros conforme o papel do usuário."""
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    impersonate = session.get("impersonate_role")
    return jsonify(serialize_event_detail(event, current_user, impersonate))


@api_bp.route("/events/new/options")
@api_login_required
def api_event_create_options() -> Any:
    """Opções do formulário de criação de evento — fichas, vendedores, talentos, tipos de
    relação de cliente (feature 152). RBAC: `_CAN_CREATE` (Comercial/Superadmin).
    """
    from app.calendar.routes import _CAN_CREATE, _build_event_create_options

    if not any(r.name.upper() in _CAN_CREATE for r in current_user.roles):
        return json_error("Sem permissão", 403)
    return jsonify(_build_event_create_options())


@api_bp.route("/events/new/prefill")
@api_login_required
def api_event_create_prefill() -> Any:
    """Pré-preenchimento a partir de um orçamento salvo (feature 152). RBAC: `_CAN_CREATE`.

    `?orcamento_id=<id>` ausente ou inválido devolve `{}` — nunca erro (paridade com o Jinja).
    """
    from app.calendar.routes import _CAN_CREATE, _build_orcamento_prefill

    if not any(r.name.upper() in _CAN_CREATE for r in current_user.roles):
        return json_error("Sem permissão", 403)
    orc_id = (request.args.get("orcamento_id") or "").strip()
    return jsonify(_build_orcamento_prefill(int(orc_id) if orc_id.isdigit() else None))
