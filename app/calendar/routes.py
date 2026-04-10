from datetime import datetime, timezone, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
import calendar as cal
import os
import re
import urllib.parse
from zoneinfo import ZoneInfo

from flask import Blueprint, redirect, request, session, url_for, render_template, current_app, abort, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from .service import (
    get_authorization_url,
    build_flow,
    save_token,
    fetch_events_for_month,
    fetch_single_event,
    parse_event_datetime,
    insert_event,
)
from .. import db
from app.constants import RoleName
from app.models import CalendarEvent, EventRole, EventLog, Talent, EventContract, EventPayment, SiteSetting, User, Role, FigurinoSheet, EnsaioMaterial
from app.email_service import send_invite_email, send_event_changed_email, send_ensaio_alert_email, send_removal_email

calendar_bp = Blueprint("calendar", __name__)

CALENDAR_ID = "eventos@mantoproducoes.com.br"
TZ = ZoneInfo("America/Sao_Paulo")
_CAN_ENSAIO      = {RoleName.ENSAIO, RoleName.CASTING, RoleName.SUPERADMIN}
_CAN_CREATE      = {RoleName.COMERCIAL, RoleName.SUPERADMIN}
_CAN_EDIT_EVENT  = {RoleName.CASTING, RoleName.FIGURINO, RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN}


@calendar_bp.route("/google/connect")
@login_required
def google_connect():
    redirect_uri = url_for("calendar.google_callback", _external=True)
    auth_url, state = get_authorization_url(redirect_uri)
    session["google_oauth_state"] = state
    return redirect(auth_url)


@calendar_bp.route("/google/callback")
@login_required
def google_callback():
    state = session.get("google_oauth_state")
    redirect_uri = url_for("calendar.google_callback", _external=True)

    flow = build_flow(redirect_uri)
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    save_token(creds)

    return redirect(url_for("calendar.agenda"))


@calendar_bp.route("/agenda")
@login_required
def agenda():
    ym = request.args.get("ym", "").strip()
    view = request.args.get("view", "calendar").strip()
    now = datetime.now()

    if ym:
        year, month = ym.split("-")
        year = int(year)
        month = int(month)
    else:
        year = now.year
        month = now.month
        ym = f"{year:04d}-{month:02d}"

    try:
        items = fetch_events_for_month(CALENDAR_ID, year, month)
        sync_events(items)
    except RuntimeError:
        items = []
        flash("Google Calendar não conectado. Acesse Admin → Configurações para conectar.", "warning")

    ids = [i.get("id") for i in items if i.get("id")]
    event_map = {}
    if ids:
        for ev in CalendarEvent.query.filter(CalendarEvent.google_event_id.in_(ids)).all():
            event_map[ev.google_event_id] = ev.id

    events_by_day = {}
    for item in items:
        start_dt, end_dt = parse_event_datetime(item)
        if start_dt and start_dt.month == month:
            day = start_dt.day
            when = start_dt.strftime("%H:%M") if start_dt else ""
            if end_dt and end_dt.strftime("%H:%M") != "00:00":
                when += f"–{end_dt.strftime('%H:%M')}"
            events_by_day.setdefault(day, []).append(
                {
                    "title": item.get("summary") or "Sem título",
                    "when": when,
                    "event_id": event_map.get(item.get("id")),
                }
            )

    first_weekday, days_in_month = cal.monthrange(year, month)
    first_weekday = (first_weekday + 1) % 7
    weeks = []
    week = []
    for _ in range(first_weekday):
        week.append(None)
    for d in range(1, days_in_month + 1):
        week.append(d)
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        while len(week) < 7:
            week.append(None)
        weeks.append(week)

    if month == 1:
        prev_ym = f"{year-1:04d}-12"
    else:
        prev_ym = f"{year:04d}-{month-1:02d}"

    if month == 12:
        next_ym = f"{year+1:04d}-01"
    else:
        next_ym = f"{year:04d}-{month+1:02d}"

    # Na view de lista, no mês atual, mostra apenas eventos de hoje em diante
    is_current_month = (year == now.year and month == now.month)
    if view == "list" and is_current_month:
        today_str = now.date().isoformat()  # "YYYY-MM-DD"
        def _event_date(item) -> str:
            start = item.get("start", {})
            return (start.get("dateTime") or start.get("date") or "")[:10]
        list_events = [i for i in items if _event_date(i) >= today_str]
    else:
        list_events = items

    return render_template(
        "calendar_list.html",
        ym=ym,
        prev_ym=prev_ym,
        next_ym=next_ym,
        events=list_events,
        event_map=event_map,
        view=view,
        month_weeks=weeks,
        events_by_day=events_by_day,
        today=now.date(),
    )


# ─── Event Detail — action handlers ──────────────────────────────────────────

def _handle_assign_casting(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    role_id      = request.form.get("role_id")
    talent_id    = request.form.get("talent_id")
    cache_value  = request.form.get("cache_value")
    travel_cache = request.form.get("travel_cache")
    role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
    if not role:
        return
    old_talent_id = role.talent_id
    role.talent_id = int(talent_id) if talent_id else None
    try:
        role.cache_value = int(cache_value) if cache_value else None
    except ValueError:
        role.cache_value = None
    try:
        role.travel_cache = int(travel_cache) if travel_cache else None
    except ValueError:
        role.travel_cache = None
    role.assigned_at = datetime.now(tz=tz_sp) if role.talent_id else None
    if role.talent_id != old_talent_id:
        role.figurino_done_at = None
        role.invite_status = None
    if role.talent_id:
        role.payment_status = "nao_pago"
    if old_talent_id and old_talent_id != role.talent_id:
        old_talent = Talent.query.get(old_talent_id)
        if old_talent:
            send_removal_email(old_talent, event, role.character_name)
    db.session.commit()
    if role.talent_id and role.talent_id != old_talent_id:
        role.invite_status = "pending"
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=current_user.name,
            actor_role="Casting",
            message=f"Adicionou {role.talent.full_name} como {role.character_name} com um cachê de {role.cache_value or 0} reais",
            created_at=datetime.now(tz=tz_sp),
        ))
        db.session.commit()
        send_invite_email(role)
    elif role.talent_id:
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=current_user.name,
            actor_role="Casting",
            message=f"Atualizou cachê de {role.talent.full_name} como {role.character_name} para {role.cache_value or 0} reais",
            created_at=datetime.now(tz=tz_sp),
        ))
        db.session.commit()


def _handle_add_role(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    character_name = request.form.get("character_name", "").strip()
    talent_id      = request.form.get("talent_id")
    cache_value    = request.form.get("cache_value")
    role_type      = request.form.get("role_type", "character")
    if not character_name:
        return
    role = EventRole(event_id=event.id, character_name=character_name, role_type=role_type)
    if talent_id:
        role.talent_id = int(talent_id)
        role.assigned_at = datetime.now(tz=tz_sp)
    try:
        role.cache_value = int(cache_value) if cache_value else None
    except ValueError:
        role.cache_value = None
    db.session.add(role)
    db.session.flush()
    talent_name = role.talent.full_name if role.talent else None
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Casting",
        message=(
            f"Adicionou {talent_name} como {role.character_name} com um cachê de {role.cache_value or 0} reais"
            if talent_name
            else f"Adicionou função: {character_name}"
        ),
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()


def _handle_figurino_done(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    role_id = request.form.get("role_id")
    role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
    if not role:
        return
    role.figurino_done_at = datetime.now(tz=tz_sp)
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Figurino",
        message=f"Separou figurino de {role.character_name}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()


def _handle_add_contract(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    amount_raw = request.form.get("contract_amount")
    file = request.files.get("contract_file")
    if not file or not file.filename:
        return
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > 10 * 1024 * 1024:
        return
    name = secure_filename(file.filename)
    save_path = os.path.join(current_app.config["UPLOAD_CONTRACTS"], name)
    file.save(save_path)
    try:
        amount = int(amount_raw) if amount_raw else None
    except ValueError:
        amount = None
    db.session.add(EventContract(
        event_id=event.id,
        file_path=f"/uploads/contracts/{name}",
        amount=amount,
    ))
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message="Adicionou contrato assinado",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()


def _handle_update_sale(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    can_vendas = any(r.name.upper() in (RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN) for r in current_user.roles)
    if not can_vendas:
        return
    sale_raw     = request.form.get("sale_value", "").strip()
    with_invoice = request.form.get("with_invoice") == "1"
    try:
        event.sale_value = int(sale_raw) if sale_raw else None
    except ValueError:
        event.sale_value = None
    event.with_invoice = with_invoice
    if any(r.name.upper() == RoleName.COMERCIAL for r in current_user.roles):
        if not event.seller_id:
            event.seller_id = current_user.id
    if any(r.name.upper() in (RoleName.FINANCEIRO, RoleName.SUPERADMIN) for r in current_user.roles):
        seller_raw = request.form.get("seller_id", "").strip()
        event.seller_id = int(seller_raw) if seller_raw else None
        rate_raw = request.form.get("commission_rate", "").strip()
        try:
            event.commission_rate = float(Decimal(rate_raw)) if rate_raw else None
        except ValueError:
            event.commission_rate = None
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Vendas",
        message=f"Atualizou valor de venda para R$ {event.sale_value or 0}{'  (com nota)' if event.with_invoice else ''}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()


def _handle_link_figurino(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    role_id  = request.form.get("role_id")
    sheet_id = request.form.get("figurino_sheet_id")
    role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
    if not role:
        return
    role.figurino_sheet_id = int(sheet_id) if sheet_id else None
    if role.figurino_sheet_id:
        sheet = FigurinoSheet.query.get(role.figurino_sheet_id)
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=current_user.name,
            actor_role="Figurino",
            message=f"Vinculou ficha '{sheet.character_name if sheet else sheet_id}' ao personagem {role.character_name}",
            created_at=datetime.now(tz=tz_sp),
        ))
    else:
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=current_user.name,
            actor_role="Figurino",
            message=f"Removeu ficha de figurino do personagem {role.character_name}",
            created_at=datetime.now(tz=tz_sp),
        ))
    db.session.commit()


def _handle_set_payment_status(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    role_id = request.form.get("role_id")
    status  = request.form.get("payment_status")
    _VALID  = {"nao_pago", "pago", "no_banco", "fora_do_banco"}
    role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
    if role and status in _VALID:
        role.payment_status = status
        db.session.commit()


def _handle_add_payment(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    amount_raw = request.form.get("payment_amount")
    file = request.files.get("payment_file")
    if not file or not file.filename:
        return
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > 10 * 1024 * 1024:
        return
    name = secure_filename(file.filename)
    save_path = os.path.join(current_app.config["UPLOAD_PAYMENTS"], name)
    file.save(save_path)
    try:
        amount = int(amount_raw) if amount_raw else None
    except ValueError:
        amount = None
    db.session.add(EventPayment(
        event_id=event.id,
        file_path=f"/uploads/payments/{name}",
        amount=amount,
    ))
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message=f"Adicionou pagamento recebido de {amount or 0} reais",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()


def _handle_send_invite(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    role_id = request.form.get("role_id")
    role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
    if not role or not role.talent_id:
        return
    role.invite_status = "pending"
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Casting",
        message=f"Enviou convite para {role.talent.full_name} ({role.character_name})",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()
    email_sent = send_invite_email(role)
    msg = f"Convite marcado como enviado para {role.talent.full_name}."
    if email_sent:
        msg += " Email enviado."
    elif role.talent.email_contact:
        msg += " (falha no envio do email)"
    flash(msg, "success")


def _handle_save_logistics(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    old_needs_rehearsal   = event.needs_rehearsal
    event.makeup_time     = request.form.get("makeup_time", "").strip() or None
    loc = request.form.get("makeup_location", "").strip()
    if loc == "outro":
        loc = request.form.get("makeup_location_custom", "").strip()
    event.makeup_location = loc or None
    event.departure_time  = request.form.get("departure_time", "").strip() or None
    event.needs_rehearsal = bool(request.form.get("needs_rehearsal"))
    db.session.commit()
    if event.needs_rehearsal and not old_needs_rehearsal:
        ensaio_users = User.query.join(User.roles).filter(Role.name == RoleName.ENSAIO).all()
        send_ensaio_alert_email(event, ensaio_users)
    flash("Logística salva.", "success")


_EVENT_ACTIONS = {
    "assign_casting":     _handle_assign_casting,
    "add_role":           _handle_add_role,
    "figurino_done":      _handle_figurino_done,
    "add_contract":       _handle_add_contract,
    "update_sale":        _handle_update_sale,
    "link_figurino":      _handle_link_figurino,
    "set_payment_status": _handle_set_payment_status,
    "add_payment":        _handle_add_payment,
    "send_invite":        _handle_send_invite,
    "save_logistics":     _handle_save_logistics,
}


@calendar_bp.route("/events/<int:event_id>", methods=["GET", "POST"])
@login_required
def event_detail(event_id: int):
    event = CalendarEvent.query.get_or_404(event_id)
    tz_sp = ZoneInfo("America/Sao_Paulo")
    raw_logs = EventLog.query.filter_by(event_id=event.id).order_by(EventLog.created_at.desc()).all()
    logs = []
    for log in raw_logs:
        dt = log.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(tz_sp)
        logs.append(
            {
                "ts": dt.strftime("%d%m%Y_%H:%M:%S"),
                "actor_name": log.actor_name,
                "actor_role": log.actor_role,
                "message": log.message,
            }
        )

    if request.method == "POST":
        if not any(r.name.upper() in _CAN_EDIT_EVENT for r in current_user.roles):
            abort(403)
        action = request.form.get("action")
        handler = _EVENT_ACTIONS.get(action)
        if handler:
            handler(event, tz_sp)
        return redirect(url_for("calendar.event_detail", event_id=event.id))

    talents = Talent.query.filter_by(status="active").order_by(Talent.full_name.asc()).all()
    contracts = EventContract.query.filter_by(event_id=event.id).order_by(EventContract.created_at.desc()).all()
    payments = EventPayment.query.filter_by(event_id=event.id).order_by(EventPayment.created_at.desc()).all()

    # Figurino: fichas disponíveis + sugestão automática por nome do personagem
    from app.figurino.drive_service import normalize_name as _norm_name
    figurino_sheets = FigurinoSheet.query.order_by(FigurinoSheet.character_name.asc()).all()
    sheet_by_norm = {s.character_name_norm: s for s in figurino_sheets if s.character_name_norm}
    suggested_sheets = {
        r.id: sheet_by_norm.get(_norm_name(r.character_name))
        for r in event.roles
        if not r.figurino_sheet_id
    }

    # disponibilidade por talento (mesmo dia / conflito de horario)
    def _naive(dt):
        """Remove timezone info para comparações seguras."""
        if dt is None:
            return None
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    availability = {}
    if event.start_at:
        event_start = _naive(event.start_at)
        event_end = _naive(event.end_at or (event.start_at + timedelta(hours=2)))
        for t in talents:
            conflicts = (
                EventRole.query.join(CalendarEvent)
                .filter(
                    EventRole.talent_id == t.id,
                    CalendarEvent.id != event.id,
                )
                .all()
            )
            # Já alocado em outro personagem NESTE MESMO evento?
            same_event = EventRole.query.filter(
                EventRole.talent_id == t.id,
                EventRole.event_id == event.id,
            ).first()
            if same_event:
                availability[t.id] = {
                    "status": "conflict",
                    "info": f"{same_event.character_name} · {_naive(event.start_at).strftime('%Hh') if event.start_at else '?'} > {_naive(event.end_at).strftime('%Hh') if event.end_at else '?'}",
                }
                continue

            status = "free"
            info = ""
            for r in conflicts:
                if not r.event or not r.event.start_at:
                    continue
                other_start = _naive(r.event.start_at)
                other_end = _naive(r.event.end_at or (r.event.start_at + timedelta(hours=2)))
                if other_start.date() == event_start.date():
                    status = "same_day"
                    info = f"{r.event.title} ({other_start.strftime('%d/%m/%Y %H:%M')} - {other_end.strftime('%d/%m/%Y %H:%M')})"
                    if max(event_start, other_start) < min(event_end, other_end):
                        status = "conflict"
                        info = f"Conflito: {r.event.title} ({other_start.strftime('%d/%m/%Y %H:%M')} - {other_end.strftime('%d/%m/%Y %H:%M')})"
                        break
            availability[t.id] = {"status": status, "info": info}

    _is_real_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)
    _impersonate = session.get("impersonate_role") if _is_real_superadmin else None

    def has_role(name: str) -> bool:
        if _impersonate:
            return _impersonate.upper() == name.upper()
        return any(r.name.upper() == name.upper() for r in current_user.roles)

    settings = SiteSetting.query.get(1)
    default_commission = Decimal(str(
        settings.default_commission_rate if settings and settings.default_commission_rate is not None else 2
    ))
    event_rate = Decimal(str(event.commission_rate)) if event.commission_rate is not None else default_commission
    event_cost = sum(r.cache_value or 0 for r in event.roles if r.talent_id)
    event_commission = (
        Decimal(event.sale_value or 0) * event_rate / Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sellers = User.query.join(User.roles).filter(Role.name == RoleName.COMERCIAL).order_by(User.name.asc()).all()

    show_comercial = has_role(RoleName.COMERCIAL) or has_role(RoleName.FINANCEIRO) or has_role(RoleName.SUPERADMIN)
    show_financeiro = has_role(RoleName.FINANCEIRO) or has_role(RoleName.SUPERADMIN)
    show_ensaio = has_role(RoleName.ENSAIO) or has_role(RoleName.CASTING) or has_role(RoleName.SUPERADMIN)

    has_makeup_role = any(
        r.character_name and "maquiador" in r.character_name.lower()
        for r in event.roles
    )

    return render_template(
        "event_detail.html",
        event=event,
        event_type=parse_event_type(event.title),
        talents=talents,
        logs=logs,
        contracts=contracts,
        payments=payments,
        availability=availability,
        show_casting=has_role(RoleName.CASTING) or has_role(RoleName.SUPERADMIN),
        show_figurino=has_role(RoleName.FIGURINO) or has_role(RoleName.SUPERADMIN),
        show_comercial=show_comercial,
        show_vendas=show_comercial,
        show_financeiro=show_financeiro,
        show_ensaio=show_ensaio,
        sellers=sellers,
        event_cost=event_cost,
        event_commission=event_commission,
        event_rate=event_rate,
        default_commission=default_commission,
        figurino_sheets=figurino_sheets,
        suggested_sheets=suggested_sheets,
        settings=settings,
        has_makeup_role=has_makeup_role,
    )


def strip_role_prefix(name: str) -> str:
    """Remove prefixo (TIPO) do início do nome do personagem. Ex: '(R&I) HOMEM ARANHA' → 'HOMEM ARANHA'."""
    return re.sub(r'^\s*\([^)]*\)\s*', '', name).strip()


def parse_event_type(title: str) -> str:
    """Extrai o tipo do evento do prefixo entre parênteses. Ex: '(R&I) HOMEM ARANHA + MARIO' → 'R&I'."""
    if not title:
        return ""
    m = re.match(r'^\s*\(([^)]*)\)', title)
    return m.group(1).strip() if m else ""


def parse_characters(title: str) -> list[str]:
    if not title:
        return []
    parts = [p.strip() for p in re.split(r"\s*\+\s*", title) if p.strip()]
    # Remove prefixo (TIPO) de cada personagem
    cleaned = [strip_role_prefix(p) for p in parts]
    return [p for p in cleaned if p]


def _dt_naive(dt):
    """Remove timezone para comparação segura."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _ensure_coordinator(event_id: int) -> None:
    """Garante que o evento tenha ao menos 1 role de Coordenador sem talento."""
    exists = EventRole.query.filter_by(
        event_id=event_id,
        character_name="Coordenador",
        role_type="extra",
    ).first()
    if not exists:
        db.session.add(EventRole(
            event_id=event_id,
            character_name="Coordenador",
            role_type="extra",
        ))


def _detect_changes(event: CalendarEvent, new_start, new_end, new_location) -> list[str]:
    """Retorna lista de strings descrevendo o que mudou (data/hora/local)."""
    changes = []
    tz_sp = ZoneInfo("America/Sao_Paulo")

    old_start = _dt_naive(event.start_at)
    chk_start = _dt_naive(new_start)
    if old_start != chk_start and old_start is not None:
        old_str = event.start_at.astimezone(tz_sp).strftime("%d/%m/%Y %H:%M") if event.start_at else "—"
        new_str = new_start.astimezone(tz_sp).strftime("%d/%m/%Y %H:%M") if new_start else "—"
        changes.append(f"Data/hora: {old_str} → {new_str}")

    old_end = _dt_naive(event.end_at)
    chk_end = _dt_naive(new_end)
    if old_end != chk_end and old_end is not None and chk_start == old_start:
        # só reporta fim se o início não mudou (evita duplicar)
        old_str = event.end_at.astimezone(tz_sp).strftime("%H:%M") if event.end_at else "—"
        new_str = new_end.astimezone(tz_sp).strftime("%H:%M") if new_end else "—"
        changes.append(f"Horário de término: {old_str} → {new_str}")

    old_loc = (event.location or "").strip()
    new_loc = (new_location or "").strip()
    if old_loc != new_loc and old_loc:
        changes.append(f"Local: {old_loc or '—'} → {new_loc or '—'}")

    return changes


def _notify_accepted_roles(event: CalendarEvent, changes: list[str]) -> None:
    """Marca roles aceitos como alterados e envia emails."""
    now = datetime.now(tz=ZoneInfo("America/Sao_Paulo"))
    for role in event.roles:
        if role.invite_status == "accepted":
            role.event_changed_at = now
            send_event_changed_email(role, changes)


def _notify_ensaio_team(event: CalendarEvent) -> None:
    """Envia alerta à equipe ENSAIO quando evento precisa de ensaio."""
    ensaio_users = (
        User.query.join(User.roles)
        .filter(Role.name == RoleName.ENSAIO)
        .all()
    )
    send_ensaio_alert_email(event, ensaio_users)


def sync_events(items: list[dict]) -> None:
    for item in items:
        google_id = item.get("id")
        if not google_id:
            continue

        title = item.get("summary") or "Sem título"
        description = item.get("description")
        location = item.get("location")
        start_at, end_at = parse_event_datetime(item)

        event_type = parse_event_type(title)
        if title.startswith("🟧 ENSAIO"):
            event_type = "ENSAIO"

        # needs_rehearsal: automático para SHOW, ou via tag na descrição
        desc_lower = (description or "").lower()
        is_show = event_type == "SHOW"
        gc_needs_rehearsal = is_show or "#ensaio" in desc_lower or "precisa de ensaio" in desc_lower

        event = CalendarEvent.query.filter_by(google_event_id=google_id).first()
        if not event:
            event = CalendarEvent(
                google_event_id=google_id,
                title=title,
                description=description,
                location=location,
                start_at=start_at,
                end_at=end_at,
                event_type=event_type,
                needs_rehearsal=gc_needs_rehearsal,
            )
            db.session.add(event)
            db.session.flush()
            db.session.add(
                EventLog(
                    event_id=event.id,
                    actor_name="Sistema",
                    actor_role="Sistema",
                    message="Evento criado",
                    created_at=datetime.now(tz=ZoneInfo("America/Sao_Paulo")),
                )
            )
            if not title.startswith("🟧 ENSAIO"):
                _ensure_coordinator(event.id)
            if gc_needs_rehearsal:
                _notify_ensaio_team(event)
            # Auto-estimar distância se fora da cidade de SP
            if location and _is_outside_sp(location):
                settings = SiteSetting.query.get(1)
                _fetch_travel_data(event, settings)
        else:
            # Detecta mudanças relevantes (data, hora, local) antes de sobrescrever
            _changes = _detect_changes(event, start_at, end_at, location)
            old_needs_rehearsal = event.needs_rehearsal
            old_location = event.location

            event.title = title
            event.description = description
            event.location = location
            event.start_at = start_at
            event.end_at = end_at
            event.event_type = event_type
            # parent_event_id NÃO é sobrescrito — gerenciado pela plataforma
            if gc_needs_rehearsal and not old_needs_rehearsal:
                event.needs_rehearsal = True
                _notify_ensaio_team(event)

            # Re-estima se o endereço mudou ou ainda não tem distância, e é fora de SP
            location_changed = (location or "").strip() != (old_location or "").strip()
            if location and _is_outside_sp(location) and (location_changed or not event.travel_distance_km):
                settings = SiteSetting.query.get(1)
                _fetch_travel_data(event, settings)
            elif not location or not _is_outside_sp(location):
                event.travel_distance_km = None

            # Notifica talentos confirmados sobre mudanças
            if _changes:
                _notify_accepted_roles(event, _changes)

        # Eventos criados pela plataforma: atualiza metadados mas preserva roles
        if event.source == "platform":
            db.session.commit()
            continue

        if title.startswith("🟧 ENSAIO"):
            for role in list(event.roles):
                db.session.delete(role)
            db.session.commit()
            continue

        characters = parse_characters(title)
        existing = {r.character_name: r for r in event.roles}

        # Mapa normalizado: nome sem prefixo → (nome_atual, role)
        # Permite renomear roles antigos que ainda têm o prefixo, preservando casting/figurino
        existing_norm: dict[str, tuple[str, object]] = {}
        for name, role in existing.items():
            norm = strip_role_prefix(name)
            existing_norm[norm] = (name, role)

        # Apaga roles que não existem mais (mesmo após normalização)
        for name, role in list(existing.items()):
            if strip_role_prefix(name) not in characters:
                if role.talent_id and role.talent:
                    send_removal_email(role.talent, event, role.character_name)
                db.session.delete(role)

        # Cria novos ou renomeia roles com prefixo antigo
        for char in characters:
            if char in existing:
                # já existe com o nome correto, nada a fazer
                pass
            elif char in existing_norm:
                # existe mas com prefixo antigo → renomeia preservando assignment
                _, role = existing_norm[char]
                role.character_name = char
            else:
                db.session.add(EventRole(event_id=event.id, character_name=char))

    db.session.commit()


# ─── LOGÍSTICA / ESTIMATIVA DE VIAGEM ────────────────────────────────────────

_SP_CITY_TERMS = ("sao paulo", "são paulo")


def _is_outside_sp(location: str) -> bool:
    """Retorna True se o endereço não pertence à cidade de São Paulo.

    Checa apenas termos específicos da cidade para evitar falsos positivos
    com outras cidades do estado (ex: Campinas - SP).
    """
    if not location:
        return False
    loc = location.lower()
    return not any(term in loc for term in _SP_CITY_TERMS)


def _fetch_travel_data(event: CalendarEvent, settings) -> dict:
    """Chama o Google Maps Distance Matrix e salva travel_time_minutes + travel_distance_km no evento.

    Retorna o dict com os dados ou {} em caso de falha/sem API key.
    """
    import urllib.request
    import json as _json

    if not event.location:
        return {}

    origin = (settings.manto_address if settings and settings.manto_address
              else "R. Olga Camelini, 147 - São João Climaco, São Paulo - SP")
    api_key = settings.google_maps_api_key if settings else None
    if not api_key:
        return {}

    url = (
        "https://maps.googleapis.com/maps/api/distancematrix/json"
        f"?origins={urllib.parse.quote(origin)}"
        f"&destinations={urllib.parse.quote(event.location)}"
        f"&language=pt-BR&key={api_key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = _json.loads(resp.read())
        element = data["rows"][0]["elements"][0]
        if element["status"] != "OK":
            return {}

        duration_min = element["duration"]["value"] // 60
        distance_km  = element["distance"]["value"] / 1000.0

        event.travel_time_minutes = duration_min
        event.travel_distance_km  = distance_km
        return {
            "duration_text":  element["duration"]["text"],
            "distance_text":  element["distance"]["text"],
            "duration_minutes": duration_min,
            "distance_km":    distance_km,
        }
    except Exception:
        return {}


def travel_estimate(event_id: int):
    """Retorna estimativa de tempo de viagem via Google Maps Distance Matrix API."""
    from flask import jsonify

    event = CalendarEvent.query.get_or_404(event_id)
    settings = SiteSetting.query.get(1)

    if not event.location:
        return {"error": "Evento sem endereço de destino."}, 400

    origin = (settings.manto_address if settings and settings.manto_address
              else "R. Olga Camelini, 147 - São João Climaco, São Paulo - SP")
    api_key = settings.google_maps_api_key if settings else None

    if not api_key:
        maps_url = (
            "https://www.google.com/maps/dir/"
            + urllib.parse.quote(origin) + "/"
            + urllib.parse.quote(event.location)
        )
        return {"maps_url": maps_url, "no_key": True}

    result = _fetch_travel_data(event, settings)
    if not result:
        return {"error": "Endereço não encontrado pelo Google Maps."}, 400

    db.session.commit()

    suggested = None
    margin = (settings.departure_margin_minutes if settings and settings.departure_margin_minutes is not None else 60)
    if event.start_at:
        depart_dt = event.start_at - timedelta(minutes=margin + result["duration_minutes"])
        suggested = depart_dt.strftime("%H:%M")

    maps_url = (
        "https://www.google.com/maps/dir/"
        + urllib.parse.quote(origin) + "/"
        + urllib.parse.quote(event.location)
    )
    return {
        "duration_text":    result["duration_text"],
        "distance_text":    result["distance_text"],
        "duration_minutes": result["duration_minutes"],
        "suggested_departure": suggested,
        "maps_url": maps_url,
    }


# ─── ENSAIOS ──────────────────────────────────────────────────────────────────

@calendar_bp.route("/events/<int:event_id>/create-ensaio", methods=["POST"])
@login_required
def create_ensaio(event_id: int):
    event = CalendarEvent.query.get_or_404(event_id)

    if not any(r.name.upper() in _CAN_ENSAIO for r in current_user.roles):
        abort(403)

    date_str  = request.form.get("ensaio_date", "").strip()
    start_str = request.form.get("ensaio_start", "").strip()
    end_str   = request.form.get("ensaio_end", "").strip()
    desc      = request.form.get("ensaio_desc", "").strip()

    errors = []
    d = None
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        errors.append("Data inválida.")

    st = et = None
    if d:
        try:
            st = datetime.combine(d, datetime.strptime(start_str, "%H:%M").time()).replace(tzinfo=TZ)
            et = datetime.combine(d, datetime.strptime(end_str,   "%H:%M").time()).replace(tzinfo=TZ)
        except ValueError:
            errors.append("Horário inválido (use HH:MM).")

    if st and et and et <= st:
        errors.append("Horário de fim deve ser após o início.")

    if errors:
        flash(" ".join(errors), "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    title = f"🟧 ENSAIO — {event.title}"
    try:
        created = insert_event(CALENDAR_ID, title, st, et, description=desc)
        ensaio_ev = CalendarEvent(
            google_event_id=created["id"],
            title=title,
            description=desc or None,
            location=event.location,
            start_at=st,
            end_at=et,
            event_type="ENSAIO",
            parent_event_id=event.id,
        )
        db.session.add(ensaio_ev)
        db.session.commit()
        flash(f'Ensaio criado com sucesso para {d.strftime("%d/%m/%Y")}!', "success")
    except RuntimeError as exc:
        flash(str(exc), "error")

    return redirect(url_for("calendar.event_detail", event_id=event_id))


# ─── CRIAR EVENTO (COMERCIAL) ─────────────────────────────────────────────────

@calendar_bp.route("/events/new", methods=["GET", "POST"])
@login_required
def create_event():
    if not any(r.name.upper() in _CAN_CREATE for r in current_user.roles):
        abort(403)

    figurino_sheets = FigurinoSheet.query.order_by(FigurinoSheet.character_name.asc()).all()
    sellers = User.query.join(User.roles).filter(Role.name == RoleName.COMERCIAL).order_by(User.name.asc()).all()

    if request.method == "GET":
        return render_template("event_create.html", figurino_sheets=figurino_sheets, sellers=sellers, errors=[])

    # ── POST ────────────────────────────────────────────────────────────────
    title        = request.form.get("title", "").strip()
    event_type   = request.form.get("event_type", "").strip()
    date_str     = request.form.get("event_date", "").strip()
    start_str    = request.form.get("event_start", "").strip()
    end_str      = request.form.get("event_end", "").strip()
    location     = request.form.get("location", "").strip()
    description  = request.form.get("description", "").strip()
    # SHOW sempre precisa de ensaio; outros tipos só se o vendedor marcar
    needs_rehearsal  = (event_type == "SHOW") or bool(request.form.get("needs_rehearsal"))
    sale_value_raw   = request.form.get("sale_value", "").strip()
    with_invoice     = bool(request.form.get("with_invoice"))
    seller_id_raw    = request.form.get("seller_id", "").strip()
    char_names       = request.form.getlist("character_names[]")
    sheet_ids        = request.form.getlist("figurino_sheet_ids[]")
    contract_amount_raw = request.form.get("contract_amount", "").strip()

    errors = []
    if not title:
        errors.append("Título obrigatório.")

    d = st = et = None
    if date_str:
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            errors.append("Data inválida.")
    else:
        errors.append("Data obrigatória.")

    if d and start_str and end_str:
        try:
            st = datetime.combine(d, datetime.strptime(start_str, "%H:%M").time()).replace(tzinfo=TZ)
            et = datetime.combine(d, datetime.strptime(end_str,   "%H:%M").time()).replace(tzinfo=TZ)
        except ValueError:
            errors.append("Horário inválido (use HH:MM).")

    if st and et and et <= st:
        errors.append("Horário de fim deve ser após o início.")

    if errors:
        return render_template("event_create.html", figurino_sheets=figurino_sheets,
                               sellers=sellers, errors=errors)

    gc_title = f"({event_type}) {title}" if event_type else title
    try:
        created = insert_event(CALENDAR_ID, gc_title, st, et, description=description)
    except RuntimeError as exc:
        return render_template("event_create.html", figurino_sheets=figurino_sheets,
                               sellers=sellers, errors=[str(exc)])

    event = CalendarEvent(
        google_event_id=created["id"],
        title=gc_title,
        description=description or None,
        location=location or None,
        start_at=st,
        end_at=et,
        event_type=event_type or None,
        needs_rehearsal=needs_rehearsal,
        source="platform",
        sale_value=int(sale_value_raw) if sale_value_raw.isdigit() else None,
        with_invoice=with_invoice,
        seller_id=int(seller_id_raw) if seller_id_raw.isdigit() else None,
    )
    db.session.add(event)
    db.session.flush()

    _ensure_coordinator(event.id)

    # Auto-estimar distância se fora de SP
    if location and _is_outside_sp(location):
        settings = SiteSetting.query.get(1)
        _fetch_travel_data(event, settings)

    for char, sheet_id_raw in zip(char_names, sheet_ids):
        char = char.strip()
        if char:
            sheet_id = int(sheet_id_raw) if sheet_id_raw and sheet_id_raw.isdigit() else None
            db.session.add(EventRole(event_id=event.id, character_name=char, figurino_sheet_id=sheet_id))

    file = request.files.get("contract_file")
    if file and file.filename:
        file.stream.seek(0, 2)
        size = file.stream.tell()
        file.stream.seek(0)
        if size <= 10 * 1024 * 1024:
            name = secure_filename(file.filename)
            save_path = os.path.join(current_app.config["UPLOAD_CONTRACTS"], name)
            file.save(save_path)
            try:
                camount = int(contract_amount_raw) if contract_amount_raw else None
            except ValueError:
                camount = None
            db.session.add(EventContract(
                event_id=event.id,
                file_path=f"/uploads/contracts/{name}",
                amount=camount,
            ))

    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="COMERCIAL",
        message="Evento criado pela plataforma",
        created_at=datetime.now(tz=TZ),
    ))
    db.session.commit()
    if needs_rehearsal:
        _notify_ensaio_team(event)
    flash("Evento criado com sucesso!", "success")
    return redirect(url_for("calendar.event_detail", event_id=event.id))


# ─── MATERIAIS DE ENSAIO ──────────────────────────────────────────────────────

_CAN_ENSAIO_MATERIAL = {RoleName.ENSAIO, RoleName.CASTING, RoleName.SUPERADMIN}

def _can_ensaio(user) -> bool:
    return any(r.name.upper() in _CAN_ENSAIO_MATERIAL for r in user.roles)


@calendar_bp.route("/events/<int:event_id>/ensaio/upload", methods=["POST"])
@login_required
def ensaio_upload_material(event_id: int):
    if not _can_ensaio(current_user):
        abort(403)
    event = CalendarEvent.query.get_or_404(event_id)

    file = request.files.get("material_file")
    label = request.form.get("label", "").strip()

    if not file or not file.filename:
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > 20 * 1024 * 1024:
        flash("Arquivo muito grande (máx 20 MB).", "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    filename = secure_filename(file.filename)
    save_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "ensaio_materials")
    os.makedirs(save_dir, exist_ok=True)
    # prefixo com event_id para evitar colisões
    unique_name = f"{event_id}_{int(datetime.utcnow().timestamp())}_{filename}"
    file.save(os.path.join(save_dir, unique_name))

    db.session.add(EnsaioMaterial(
        event_id=event_id,
        user_id=current_user.id,
        material_type="file",
        label=label or filename,
        file_path=f"ensaio_materials/{unique_name}",
    ))
    db.session.commit()
    flash("Arquivo adicionado.", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))


@calendar_bp.route("/events/<int:event_id>/ensaio/link", methods=["POST"])
@login_required
def ensaio_add_link(event_id: int):
    if not _can_ensaio(current_user):
        abort(403)
    event = CalendarEvent.query.get_or_404(event_id)

    url   = request.form.get("link_url", "").strip()
    label = request.form.get("link_label", "").strip()

    if not url:
        flash("URL não pode ser vazio.", "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    db.session.add(EnsaioMaterial(
        event_id=event_id,
        user_id=current_user.id,
        material_type="link",
        label=label or url[:60],
        url=url,
    ))
    db.session.commit()
    flash("Link adicionado.", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))


@calendar_bp.route("/events/<int:event_id>/ensaio/material/<int:material_id>/delete", methods=["POST"])
@login_required
def ensaio_delete_material(event_id: int, material_id: int):
    if not _can_ensaio(current_user):
        abort(403)
    material = EnsaioMaterial.query.get_or_404(material_id)
    if material.event_id != event_id:
        abort(404)
    # remove arquivo físico se existir
    if material.file_path:
        full = os.path.join(current_app.config["UPLOAD_FOLDER"], material.file_path)
        if os.path.exists(full):
            os.remove(full)
    db.session.delete(material)
    db.session.commit()
    flash("Material removido.", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))


@calendar_bp.route("/events/<int:event_id>/sync", methods=["POST"])
@login_required
def sync_single_event(event_id: int):
    """Sincroniza um único evento com o Google Calendar."""
    event = CalendarEvent.query.get_or_404(event_id)
    if not event.google_event_id:
        flash("Evento sem ID do Google Calendar — não é possível sincronizar.", "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    item = fetch_single_event(CALENDAR_ID, event.google_event_id)
    if not item:
        flash("Não foi possível buscar o evento no Google Calendar.", "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    sync_events([item])
    db.session.commit()
    flash("Evento sincronizado com sucesso.", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))
