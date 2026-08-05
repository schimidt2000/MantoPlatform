"""Serialização de leitura da Agenda/Eventos (feature 145, US1).

Fonte única do formato JSON de leitura consumido pela SPA React. Nesta fatia cobre apenas o
RESUMO do evento (agenda); o detalhe do evento (com RBAC financeiro) entra no Incremento B.
Reaproveita os parsers e a query de mês da view Jinja (Princípio I) — não duplica lógica.
"""

from datetime import UTC, date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.constants import EVENT_TYPE_SHOW, EVENT_TYPE_VIRTUAL, RoleName
from app.models import (
    CalendarEvent,
    ClientFeedback,
    EventContract,
    EventInvoice,
    EventLog,
    EventPayment,
    EventRating,
    EventReimbursement,
    SiteSetting,
    SpecialExpense,
)


def _money(value: Any) -> float | None:
    """Converte Decimal/None em float (JSON não serializa Decimal)."""
    return float(value) if value is not None else None


def _event_type_serializado(event) -> str:
    """Tipo do evento como o frontend o lê.

    `parse_event_type` extrai o tipo do prefixo `(TIPO)` do título — convenção dos eventos que vêm
    do Google Calendar. Vendas da Loja de Interações Virtuais (feature 205) nascem na plataforma e
    **não** carregam esse prefixo: o tipo está na coluna. Sem este fallback, a seção da venda nunca
    renderizaria, porque o payload diria `event_type: ""`.

    O fallback é deliberadamente estreito (só `VIRTUAL`) para não mudar o que a agenda já devolve
    para os demais tipos — Princípio IV.
    """
    from app.calendar.routes import parse_event_type

    if event.event_type == EVENT_TYPE_VIRTUAL:
        return EVENT_TYPE_VIRTUAL
    return parse_event_type(event.title)


def serialize_event_summary(event: CalendarEvent) -> dict[str, Any]:
    """Resumo de um evento para a lista/calendário da agenda (data-model.md: EventoResumo).

    Sem nenhum dado financeiro — a agenda não expõe valores.
    """
    # Import tardio: parsers vivem no blueprint calendar (evita import circular no boot).
    from app.calendar.routes import parse_characters

    return {
        "id": event.id,
        "title": event.title,
        "event_type": _event_type_serializado(event),
        "start_at": event.start_at.isoformat() if event.start_at else None,
        "end_at": event.end_at.isoformat() if event.end_at else None,
        "location": event.location or None,
        "characters": parse_characters(event.title),
        "is_satellite": event.is_satellite,
        "group_name": event.group_name or None,
        "confirmed": event.confirmed_at is not None,
    }


def client_of_event(event: CalendarEvent) -> tuple[str | None, str | None]:
    """(nome, telefone exibível) da cliente principal do evento, para a busca da agenda.

    Preferência: EventClient "Contratante" → primeiro EventClient → `event.client`
    (denormalizado, eventos pré-feature 100). `(None, None)` quando não há cliente.
    """
    chosen = None
    for event_client in event.event_clients:
        if event_client.client is None:
            continue
        if (event_client.relationship_type or "").lower() == "contratante":
            chosen = event_client.client
            break
        if chosen is None:
            chosen = event_client.client
    if chosen is None:
        chosen = event.client
    if chosen is None:
        return None, None
    return chosen.name, chosen.phone_display or chosen.phone


def build_agenda_month(year: int, month: int) -> dict[str, Any]:
    """Monta a resposta da agenda de um mês: eventos + índice por dia (para o calendário).

    Usa a mesma query da view (`_query_month_events`), então o conjunto de eventos é idêntico
    ao que o sistema atual mostra. `by_day` espalha eventos de vários dias por todos os dias
    que eles cobrem dentro do mês (como o calendário Jinja).
    """
    from app.calendar.routes import _query_month_events

    events = _query_month_events(year, month)
    summaries = [serialize_event_summary(e) for e in events]

    by_day: dict[str, list[int]] = {}
    for event in events:
        if not event.start_at:
            continue
        start_day = event.start_at.date()
        end_day = event.end_at.date() if event.end_at else start_day
        cursor = start_day
        while cursor <= end_day:
            if cursor.year == year and cursor.month == month:
                by_day.setdefault(cursor.isoformat(), []).append(event.id)
            cursor = cursor.fromordinal(cursor.toordinal() + 1)

    return {"ym": f"{year:04d}-{month:02d}", "events": summaries, "by_day": by_day}


def _role_flags(user: Any, impersonate: str | None) -> dict[str, bool]:
    """Flags de visibilidade por papel, com a MESMA lógica da view `event_detail`.

    Respeita a impersonação de papel do SUPERADMIN (ver o sistema como outro papel).
    """
    is_real_sa = any(r.name == RoleName.SUPERADMIN for r in user.roles)
    active = impersonate if (impersonate and is_real_sa) else None

    def has(role: str) -> bool:
        if active:
            return active.upper() == role.upper()
        return any(r.name.upper() == role.upper() for r in user.roles)

    is_superadmin = has(RoleName.SUPERADMIN)
    return {
        "show_casting": has(RoleName.CASTING) or is_superadmin,
        "show_figurino": has(RoleName.FIGURINO) or is_superadmin,
        "show_comercial": has(RoleName.COMERCIAL) or has(RoleName.FINANCEIRO) or is_superadmin,
        "show_financeiro": has(RoleName.FINANCEIRO) or is_superadmin,
        "show_ensaio": has(RoleName.ENSAIO) or has(RoleName.CASTING) or is_superadmin,
        "is_superadmin": is_superadmin,
        # Escrita de nível-evento (feature 149): confirmar = Comercial/SA; logística = _CAN_EDIT_EVENT.
        "can_confirm": has(RoleName.COMERCIAL) or is_superadmin,
        "can_edit_event": (
            has(RoleName.CASTING)
            or has(RoleName.FIGURINO)
            or has(RoleName.COMERCIAL)
            or has(RoleName.FINANCEIRO)
            or is_superadmin
        ),
        # Excluir evento (feature 151): _CAN_DELETE = Comercial ou Superadmin.
        "can_delete": has(RoleName.COMERCIAL) or is_superadmin,
        # Editar campos centrais em bloco (feature 184): mesmo nível de _can_create_event —
        # mais restrito que can_edit_event porque cobre os mesmos campos financeiros da criação.
        "can_edit_core": has(RoleName.COMERCIAL) or is_superadmin,
        # Presentes 3D (feature 200): todo mundo que abre o evento SHOW LÊ a lista; só o
        # Artista 3D (e o Superadmin) vincula/edita/remove — mesmo gate dos endpoints
        # `/api/3d/*` e `/api/events/<id>/3d-gifts`.
        "can_manage_3d": has(RoleName.ARTISTA_3D) or is_superadmin,
    }


def _serialize_logs(event_id: int) -> list[dict[str, Any]]:
    """Histórico do evento, mais recente primeiro, horário em São Paulo (como a view)."""
    tz_sp = ZoneInfo("America/Sao_Paulo")
    logs = []
    raw = (
        EventLog.query.filter_by(event_id=event_id)
        .order_by(EventLog.created_at.desc())
        .all()
    )
    for log in raw:
        dt = log.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = dt.astimezone(tz_sp)
        logs.append(
            {
                "ts": dt.strftime("%d/%m/%Y %H:%M"),
                "actor_name": log.actor_name,
                "actor_role": log.actor_role,
                "message": log.message,
            }
        )
    return logs


def _serialize_talent(talent: Any) -> dict[str, Any]:
    """Talento escalado, com o que a tela de detalhe mostra no card (feature 190).

    Inclui o número de WhatsApp já pronto (`Talent.whatsapp_number` — fonte única do formato
    com DDI) e as medidas de figurino, exibidas no card de Figurino do evento.
    """
    return {
        "id": talent.id,
        "name": talent.full_name,
        "artistic_name": talent.artistic_name,
        "first_name": (talent.full_name or "").split(" ")[0],
        "whatsapp": talent.whatsapp_number or None,
        "size_top": talent.clothing_size_top or None,
        "size_bottom": talent.clothing_size_bottom or None,
        "shoe_size": talent.shoe_size or None,
        "height_cm": talent.height_cm,
    }


def _serialize_role(
    role: Any, show_casting: bool, availability: dict[int, dict[str, str]]
) -> dict[str, Any]:
    """Um cargo do elenco. `cache_value` (cachê) só para casting/superadmin (dado do casting)."""
    sheet = role.figurino_sheet
    data: dict[str, Any] = {
        "role_id": role.id,
        "character_name": role.character_name,
        "role_type": role.role_type,
        "talent": _serialize_talent(role.talent) if role.talent else None,
        "figurino_done": role.figurino_done_at is not None,
        "invite_status": role.invite_status,
        "dismissed": role.dismissed_at is not None,
        # feature 184 — necessários para pré-preencher o formulário de edição de evento.
        "figurino_sheet_id": role.figurino_sheet_id,
        "needs_makeup": bool(role.needs_makeup),
        "is_singer": bool(role.is_singer),
        # feature 190 — densidade do card de casting/figurino da tela de detalhe.
        "figurino_sheet_name": sheet.character_name if sheet else None,
        "figurino_done_at": (
            role.figurino_done_at.isoformat() if role.figurino_done_at else None
        ),
        "assigned_at": role.assigned_at.isoformat() if role.assigned_at else None,
        "payment_status": role.payment_status or "nao_pago",
        "availability": (
            availability.get(role.talent_id) if role.talent_id else None
        ),
    }
    if show_casting:
        data["cache_value"] = _money(role.cache_value)
        data["travel_cache"] = _money(role.travel_cache)
        data["cache_cap"] = _money(role.cache_cap)
    return data


def _compute_kpi(event: CalendarEvent) -> dict[str, Any]:
    """KPIs financeiros agregados pelo grupo comercial — mesma fórmula da view `event_detail`."""
    from app.calendar.routes import _group_events

    settings = SiteSetting.query.get(1)
    default_rate = Decimal(str(
        settings.default_commission_rate
        if settings and settings.default_commission_rate is not None
        else 2
    ))
    group = _group_events(event)
    kpi_event = group[0]
    rate = (
        Decimal(str(kpi_event.commission_rate))
        if kpi_event.commission_rate is not None else default_rate
    )
    cost = sum((r.cache_value or 0 for ge in group for r in ge.roles if r.talent_id), Decimal("0"))
    expenses_total = sum(
        (
            e.amount
            for e in SpecialExpense.query.filter(
                SpecialExpense.event_id.in_([ge.id for ge in group]),
                SpecialExpense.status == "aprovado",
            ).all()
        ),
        Decimal("0"),
    )
    bv_total = sum(
        (
            Decimal(a.amount_brl)
            for ge in group for a in ge.acrescimos if a.is_bv and a.amount_brl
        ),
        Decimal("0"),
    )
    sale = Decimal(kpi_event.sale_value or 0)
    base = sale - bv_total
    if base < 0:
        base = Decimal("0")
    commission = (base * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    lucro = sale - Decimal(cost) - expenses_total - bv_total
    return {
        "sale_value": _money(sale),
        "cost": _money(cost),
        "expenses_total": _money(expenses_total),
        "bv_total": _money(bv_total),
        "commission": _money(commission),
        "lucro": _money(lucro),
        "rate": float(rate),
        "group_size": len(group),
        "seller": kpi_event.seller.name if kpi_event.seller else None,
    }


def _compute_cobranca(
    event: CalendarEvent, payments: list[EventPayment]
) -> dict[str, Any]:
    """Saldo em aberto + data limite da cobrança — mesma política da view."""
    today = date.today()
    policy_due = event.start_at.date() - timedelta(days=2) if event.start_at else None
    unreceived = [i for i in event.installments if not i.received]
    if event.installments:
        outstanding = sum((i.amount or 0 for i in unreceived), Decimal("0"))
        due_dates = [i.due_date for i in unreceived if i.due_date]
        due = min(due_dates) if due_dates else policy_due
    else:
        received = sum((p.amount or 0 for p in payments), Decimal("0"))
        outstanding = Decimal(event.sale_value or 0) - received
        due = event.payment_due_date or policy_due
    enabled = due is not None and due <= today and outstanding > 0
    return {
        "outstanding": _money(outstanding),
        "due": due.isoformat() if due else None,
        "enabled": bool(enabled),
    }


def _serialize_ratings(event_id: int) -> dict[str, Any]:
    """Avaliações dos artistas sobre o evento (portal do talento) + média geral.

    Cada avaliação traz as sub-avaliações por categoria já rotuladas com o nome do avaliado,
    para a tela montar as tags ("Coord. · Matheus ★★★★★") sem uma segunda consulta.
    """
    ratings = (
        EventRating.query.filter_by(event_id=event_id)
        .order_by(EventRating.submitted_at.desc())
        .all()
    )
    items = [
        {
            "id": r.id,
            "talent_name": r.talent.full_name if r.talent else "—",
            "score": r.score,
            "comment": r.comment,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "sub_ratings": [
                {
                    "category": sub.category,
                    "subject_name": (
                        sub.subject_talent.full_name if sub.subject_talent else None
                    ),
                    "score": sub.score,
                    "comment": sub.comment,
                }
                for sub in r.sub_ratings
            ],
        }
        for r in ratings
    ]
    average = round(sum(r.score for r in ratings) / len(ratings), 1) if ratings else None
    return {"items": items, "average": average, "count": len(ratings)}


def _serialize_client_feedbacks(event_id: int) -> list[dict[str, Any]]:
    """Avaliações da cliente (link público `/avaliar/<token>`), mais recente primeiro."""
    return [
        {
            "id": f.id,
            "score": f.score,
            "comment": f.comment,
            "client_name": f.client_name,
            "tags": f.tags_list,
            "submitted_at": f.submitted_at.isoformat() if f.submitted_at else None,
        }
        for f in ClientFeedback.query.filter_by(event_id=event_id)
        .order_by(ClientFeedback.submitted_at.desc())
        .all()
    ]


def _serialize_gastos(group_ids: list[int]) -> list[dict[str, Any]]:
    """Gastos extras APROVADOS vinculados a qualquer evento do grupo comercial.

    São os mesmos gastos que já entram como custo em `_compute_kpi` — aqui detalhados para a
    grade "Gastos extras vinculados" da tela.
    """
    return [
        {
            "id": e.id,
            "description": e.description,
            "category": e.category,
            "amount": _money(e.amount),
            "expense_date": e.expense_date.isoformat() if e.expense_date else None,
            "receipt_path": e.receipt_path,
        }
        for e in SpecialExpense.query.filter(
            SpecialExpense.event_id.in_(group_ids),
            SpecialExpense.status == "aprovado",
        )
        .order_by(SpecialExpense.expense_date.desc(), SpecialExpense.id.desc())
        .all()
    ]


def _serialize_acrescimos(event: CalendarEvent) -> list[dict[str, Any]]:
    """Acréscimos tipados do evento (feature 099) — BV marcado para a tela explicar o repasse."""
    return [
        {
            "id": a.id,
            "label": a.display_label,
            "tipo": a.tipo,
            "is_percent": bool(a.is_percent),
            "value": _money(a.value),
            "amount_brl": _money(a.amount_brl),
            "is_bv": bool(a.is_bv),
            "bv_recipient": a.bv_recipient,
            "bv_payment_status": a.bv_payment_status,
        }
        for a in event.acrescimos
    ]


def _material_url(path: str | None) -> str | None:
    """Normaliza o caminho de um material: registros antigos guardam o caminho relativo a
    `UPLOAD_FOLDER` (`ensaio_materials/x.pdf`); os novos, a URL já pronta de `app.storage`
    (`/uploads/...` local ou `https://...` em S3). O cliente recebe sempre algo servível.
    """
    if not path:
        return None
    if path.startswith(("http://", "https://", "/")):
        return path
    return f"/uploads/{path}"


def _serialize_materials(event: CalendarEvent) -> list[dict[str, Any]]:
    """Materiais de ensaio (arquivos e links) anexados ao evento."""
    return [
        {
            "id": m.id,
            "material_type": m.material_type,
            "label": m.label,
            "url": m.url,
            "file_path": _material_url(m.file_path),
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in event.ensaio_materials
    ]


def _maps_url(origin: str, destination: str) -> str:
    """URL de rota do Google Maps entre dois endereços (mesmo formato de `travel_estimate`)."""
    import urllib.parse

    return (
        "https://www.google.com/maps/dir/"
        + urllib.parse.quote(origin)
        + "/"
        + urllib.parse.quote(destination)
    )


def _serialize_travel(event: CalendarEvent, settings: Any) -> dict[str, Any]:
    """Estimativa de trajeto em cache + horário de saída sugerido + link do Maps."""
    from app.calendar.event_ops import suggested_departure_time

    origin = (
        settings.manto_address
        if settings and settings.manto_address
        else "R. Olga Camelini, 147 - São João Climaco, São Paulo - SP"
    )
    return {
        "time_minutes": event.travel_time_minutes,
        "distance_km": event.travel_distance_km,
        "is_outside_sp": event.is_outside_sp,
        "suggested_departure": suggested_departure_time(event, settings),
        "maps_url": _maps_url(origin, event.location) if event.location else None,
    }


def _serialize_mensagens(
    event: CalendarEvent, cobranca: dict[str, Any], reembolsos: list[Any]
) -> dict[str, Any]:
    """Dados fixos das mensagens de WhatsApp copiadas pela tela (feature 083).

    A saudação por horário continua sendo montada no cliente (depende da hora de quem copia);
    aqui vão só os trechos que dependem do evento.
    """
    from app.calendar.routes import _format_event_date_ptbr, parse_characters
    from app.money import format_brl

    return {
        "characters": " + ".join(parse_characters(event.title)),
        "date_line": _format_event_date_ptbr(event.start_at, event.end_at),
        "location": event.location or "",
        "cobranca_amount": format_brl(cobranca.get("outstanding") or 0, prefix=True),
        "cobranca_due": (
            date.fromisoformat(cobranca["due"]).strftime("%d/%m/%Y")
            if cobranca.get("due")
            else ""
        ),
        "reembolso_lines": [
            f"{r.description} — {format_brl(r.amount or 0, prefix=True)}"
            for r in reembolsos
            if not r.is_collected
        ],
    }


def serialize_event_detail(
    event: CalendarEvent, user: Any, impersonate: str | None
) -> dict[str, Any]:
    """Detalhe do evento para leitura, com RBAC (data-model.md). Blocos financeiros só
    entram no JSON conforme o papel — nunca serializados para quem não os veria (FR-003).
    """
    from app.calendar.routes import parse_characters

    flags = _role_flags(user, impersonate)
    is_ensaio = event.event_type == "ENSAIO"
    settings = SiteSetting.query.get(1)

    data: dict[str, Any] = {
        "event": {
            "id": event.id,
            "title": event.title,
            "event_type": _event_type_serializado(event),
            # feature 190 — cabeçalho e bloco de cópia rápida da tela de detalhe.
            "description": event.description or None,
            "google_html_link": event.google_html_link or None,
            "travel": _serialize_travel(event, settings),
            "start_at": event.start_at.isoformat() if event.start_at else None,
            "end_at": event.end_at.isoformat() if event.end_at else None,
            "location": event.location or None,
            "confirmed": event.confirmed_at is not None,
            "confirmed_by": event.confirmer.name if event.confirmer else None,
            "is_satellite": event.is_satellite,
            "group_name": event.group_name or None,
            "characters": parse_characters(event.title),
            "is_ensaio": is_ensaio,
            # Logística (feature 149) — não-financeiro, sempre presente.
            "makeup_time": event.makeup_time or None,
            "makeup_location": event.makeup_location or None,
            "departure_time": event.departure_time or None,
            "departure_location": event.departure_location or None,
            "needs_rehearsal": bool(event.needs_rehearsal),
        },
        "flags": flags,
    }

    # Histórico do evento — só SUPERADMIN (real e sem impersonação, mesma semântica de
    # flags["is_superadmin"]) recebe; chave ausente = o React não renderiza a seção (mesmo
    # padrão dos blocos financeiros). Precisa vir ANTES do early-return de ENSAIO, senão o
    # superadmin perderia os logs de ensaios.
    if flags["is_superadmin"]:
        data["logs"] = _serialize_logs(event.id)

    # ENSAIO: painel simplificado (sem seções de show).
    if is_ensaio:
        return data

    from app.calendar.event_ops import talent_availability

    # `CalendarEvent.roles` não tem `order_by`, então o Postgres devolve os cargos em ordem
    # arbitrária — e ela muda depois de um UPDATE. Ordenar por id aqui mantém os cards de
    # casting/figurino no mesmo lugar entre uma mutação e outra.
    roles = sorted(event.roles, key=lambda r: r.id)
    availability = talent_availability(event, [r.talent_id for r in roles if r.talent_id])
    data["elenco"] = [_serialize_role(r, flags["show_casting"], availability) for r in roles]
    data["materiais"] = _serialize_materials(event)
    # Presentes 3D (feature 200) — só evento SHOW tem a seção; a chave ausente é o sinal para o
    # React não renderizar nada (mesmo padrão dos blocos financeiros: o servidor decide).
    if event.event_type == EVENT_TYPE_SHOW:
        from app.impressoes3d.impressoes3d_ops import serialize_gift

        data["presentes_3d"] = [serialize_gift(g) for g in event.presentes_3d]

    # Venda da Loja de Interações Virtuais (feature 205) — a ficha que a família preencheu e o
    # acesso à sala. Mesma convenção dos blocos acima: chave ausente = o React não renderiza nada.
    # O talento escalado precisa dos dois para executar a chamada (FR-030, FR-036).
    if event.event_type == EVENT_TYPE_VIRTUAL:
        from app.marketing import virtuais_ops
        from app.models import VirtualOrder

        pedido = VirtualOrder.query.filter_by(event_id=event.id).first()
        if pedido is not None:
            data["pedido_virtual"] = {
                "order_nsu": pedido.order_nsu,
                "modality": pedido.modality,
                "child_name": pedido.child_name,
                "child_age": pedido.child_age,
                "behavior_notes": pedido.behavior_notes,
                "contact_phone_display": pedido.contact_phone_display or pedido.contact_phone,
                "contact_email": pedido.contact_email,
                "delivery_address": pedido.delivery_address,
                "meet_url": pedido.meet_url,
                "meet_pending": bool(pedido.meet_pending),
                "campaign_title": pedido.campaign.title if pedido.campaign else None,
                # Falhas de aviso e desistência da sala (feature 205, FR-039c/FR-056a). O painel do
                # evento é onde a equipe abre quando a família liga perguntando — precisa mostrar
                # que o e-mail não chegou, em vez de deixar a pessoa jurar que enviou.
                "id": pedido.id,
                "avisos_falhos": virtuais_ops.serialize_avisos_falhos(pedido),
                "meet_retry_esgotado": bool(
                    pedido.meet_pending and virtuais_ops.retry_esgotou(pedido.meet_attempts or 0)
                ),
                "meet_attempts": pedido.meet_attempts or 0,
            }
    data["ratings"] = _serialize_ratings(event.id)
    data["client_feedbacks"] = _serialize_client_feedbacks(event.id)
    data["observations"] = [
        {
            "id": o.id,
            "obs_type": o.obs_type,
            "content": o.content,
            "label": o.label,
            # URL pública do arquivo (feature 150) — só para imagem; `file_path` já é `/uploads/...`.
            "image_url": o.file_path if o.obs_type == "image" else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in event.observations
    ]

    payments = (
        EventPayment.query.filter_by(event_id=event.id)
        .order_by(EventPayment.created_at.desc())
        .all()
    )
    reembolsos = (
        EventReimbursement.query.filter_by(event_id=event.id)
        .order_by(EventReimbursement.created_at.desc())
        .all()
    )

    # Bloco comercial (venda, contratos, cobrança) — COMERCIAL/FINANCEIRO/SUPERADMIN.
    if flags["show_comercial"]:
        form_response = event.form_responses[0] if event.form_responses else None
        data["venda"] = {
            "sale_value": _money(event.sale_value),
            "sale_value_gross": _money(event.sale_value_gross),
            "transport_value": _money(event.transport_value),
            "acrescimo_value": _money(event.acrescimo_value),
            "is_cortesia_permuta": bool(event.is_cortesia_permuta),
            "with_invoice": bool(event.with_invoice),
            "seller": event.seller.name if event.seller else None,
            "seller_id": event.seller_id,
            "sale_date": event.sale_date.isoformat() if event.sale_date else None,
            "commission_rate": event.commission_rate,
            "payment_method": event.payment_method,
            "payment_installments": event.payment_installments,
            "payment_due_date": event.payment_due_date.isoformat() if event.payment_due_date else None,
            # feature 184 — necessários para pré-preencher/salvar o formulário de edição de evento.
            "clients": [
                {
                    "client_id": ec.client_id,
                    "name": ec.client.name if ec.client else None,
                    "relation": ec.relationship_type,
                }
                for ec in event.event_clients
            ],
            "form_response": (
                {"id": form_response.id, "name": form_response.contact_name, "form_type": form_response.form_type}
                if form_response
                else None
            ),
        }
        data["contratos"] = [
            {
                "id": c.id,
                "file_path": c.file_path,
                "is_signed": c.is_signed,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in EventContract.query.filter_by(event_id=event.id)
            .order_by(EventContract.created_at.desc())
            .all()
        ]
        data["notas_fiscais"] = [
            {
                "id": inv.id,
                "amount": _money(inv.amount),
                "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                "status": inv.status,
                "file": inv.file,
            }
            for inv in EventInvoice.query.filter_by(event_id=event.id)
            .order_by(EventInvoice.created_at.desc())
            .all()
        ]
        data["cobranca"] = _compute_cobranca(event, payments)
        data["acrescimos"] = _serialize_acrescimos(event)
        data["feedback_link_pendente"] = not data["client_feedbacks"]
        data["reembolsos_pendentes_total"] = _money(
            sum((r.amount or 0 for r in reembolsos if not r.is_collected), Decimal("0"))
        )
        data["mensagens"] = _serialize_mensagens(event, data["cobranca"], reembolsos)

    # KPIs, pagamentos e reembolsos — FINANCEIRO/SUPERADMIN.
    if flags["show_financeiro"]:
        from app.calendar.routes import _group_events

        data["kpi"] = _compute_kpi(event)
        data["gastos"] = _serialize_gastos([ge.id for ge in _group_events(event)])
        data["pagamentos"] = {
            "items": [
                {
                    "id": p.id,
                    "amount": _money(p.amount),
                    "file_path": p.file_path,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in payments
            ],
            "received_total": _money(sum((p.amount or 0 for p in payments), Decimal("0"))),
        }
        data["reembolsos"] = {
            "items": [
                {
                    "id": r.id,
                    "description": r.description,
                    "amount": _money(r.amount),
                    "invoice_file_path": r.invoice_file_path,
                    "is_collected": r.is_collected,
                    "collected_amount": _money(r.collected_amount),
                    "receipt_file_path": r.receipt_file_path,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reembolsos
            ],
            "pendentes_total": _money(
                sum((r.amount or 0 for r in reembolsos if not r.is_collected), Decimal("0"))
            ),
        }

    return data
