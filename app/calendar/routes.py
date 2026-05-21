from datetime import datetime, timezone, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
import calendar as cal
import json
import os
import re
import urllib.parse
import urllib.request
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
    update_event,
    delete_event,
)
from .. import db
from app.constants import RoleName
from app.models import CalendarEvent, EventRole, EventLog, Talent, EventContract, EventPayment, SiteSetting, User, Role, FigurinoSheet, EnsaioMaterial, EventObservation, OrcamentoHistory, EventRating
from app.email_service import send_invite_email, send_event_changed_email, send_ensaio_alert_email, send_removal_email, send_async

calendar_bp = Blueprint("calendar", __name__)

CALENDAR_ID = "eventos@mantoproducoes.com.br"
TZ = ZoneInfo("America/Sao_Paulo")
_CAN_ENSAIO      = {RoleName.ENSAIO, RoleName.CASTING, RoleName.SUPERADMIN}
_CAN_CREATE      = {RoleName.COMERCIAL, RoleName.SUPERADMIN}
_CAN_EDIT_EVENT  = {RoleName.CASTING, RoleName.FIGURINO, RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN}

_SYNC_TTL_SECONDS = 900  # 15 min — cron job sincroniza a cada 10 min, este é o fallback


def _is_month_fresh(ym: str) -> bool:
    settings = SiteSetting.query.get(1)
    if not settings or not settings.calendar_sync_cache:
        return False
    cache = json.loads(settings.calendar_sync_cache)
    ts_str = cache.get(ym)
    if not ts_str:
        return False
    age = (datetime.utcnow() - datetime.fromisoformat(ts_str)).total_seconds()
    return age < _SYNC_TTL_SECONDS


def _mark_month_synced(ym: str) -> None:
    settings = SiteSetting.query.get(1)
    if not settings:
        return
    cache = json.loads(settings.calendar_sync_cache) if settings.calendar_sync_cache else {}
    cache[ym] = datetime.utcnow().isoformat()
    if len(cache) > 24:
        for k in sorted(cache.keys())[:-24]:
            del cache[k]
    settings.calendar_sync_cache = json.dumps(cache)
    db.session.commit()


def _build_events_from_db(
    year: int, month: int, month_start: date, month_end: date
) -> tuple[dict, dict, list]:
    """Constrói event_map, events_by_day e list_items a partir do banco (sem chamar Google)."""
    month_start_dt = datetime(year, month, 1)
    if month == 12:
        month_end_dt = datetime(year + 1, 1, 1)
    else:
        month_end_dt = datetime(year, month + 1, 1)

    db_events = (
        CalendarEvent.query
        .filter(
            CalendarEvent.start_at < month_end_dt,
            db.or_(
                CalendarEvent.end_at >= month_start_dt,
                db.and_(CalendarEvent.end_at.is_(None), CalendarEvent.start_at >= month_start_dt),
            ),
        )
        .order_by(CalendarEvent.start_at)
        .all()
    )

    event_map = {ev.google_event_id: ev.id for ev in db_events}
    events_by_day: dict[int, list] = {}

    for ev in db_events:
        if not ev.start_at:
            continue
        ev_start = ev.start_at.date()
        ev_end = ev.end_at.date() if ev.end_at else ev_start
        is_ensaio = ev.event_type == "ENSAIO" or "ensaio" in ev.title.lower()
        cur = max(ev_start, month_start)
        stop = min(ev_end, month_end)
        while cur <= stop:
            is_start_day = (cur == ev_start)
            if is_start_day:
                when = ev.start_at.strftime("%H:%M") if (ev.start_at.hour or ev.start_at.minute) else ""
                if ev.end_at and (ev.end_at.hour or ev.end_at.minute) and ev_end > ev_start:
                    when += f"–{ev.end_at.strftime('%d/%m %H:%M')}"
                elif ev.end_at and ev.end_at.strftime("%H:%M") != "00:00":
                    when += f"–{ev.end_at.strftime('%H:%M')}"
            else:
                when = "↪"
            events_by_day.setdefault(cur.day, []).append({
                "title": ev.title,
                "when": when,
                "event_id": ev.id,
                "is_ensaio": is_ensaio,
            })
            cur += timedelta(days=1)

    list_items = [
        {
            "id": ev.google_event_id,
            "summary": ev.title,
            "start": {"dateTime": ev.start_at.strftime("%Y-%m-%dT%H:%M:%S")} if ev.start_at else {},
            "location": ev.location or "",
        }
        for ev in db_events
    ]
    return event_map, events_by_day, list_items


def _oauth_redirect_uri() -> str:
    """Retorna o redirect_uri do OAuth — usa env var em produção para garantir HTTPS correto."""
    override = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")
    if override:
        return override
    return url_for("calendar.google_callback", _external=True)


@calendar_bp.route("/google/connect")
@login_required
def google_connect():
    redirect_uri = _oauth_redirect_uri()
    auth_url, state = get_authorization_url(redirect_uri)
    session["google_oauth_state"] = state
    return redirect(auth_url)


@calendar_bp.route("/google/callback")
@login_required
def google_callback():
    state = session.get("google_oauth_state")
    redirect_uri = _oauth_redirect_uri()

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
    force_sync = request.args.get("force_sync") == "1"
    now = datetime.now()

    if ym:
        year, month = ym.split("-")
        year = int(year)
        month = int(month)
    else:
        year = now.year
        month = now.month
        ym = f"{year:04d}-{month:02d}"

    first_weekday, days_in_month = cal.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end   = date(year, month, days_in_month)

    if not force_sync and _is_month_fresh(ym):
        # Fast path: serve direto do banco, sem chamada ao Google
        event_map, events_by_day, items = _build_events_from_db(year, month, month_start, month_end)
    else:
        # Slow path: busca no Google Calendar e sincroniza
        try:
            items = fetch_events_for_month(CALENDAR_ID, year, month)
            sync_events(items)
            _mark_month_synced(ym)
        except RuntimeError:
            items = []
            flash("Google Calendar não conectado. Use o botão 'Google' acima para conectar.", "warning")

        ids = [i.get("id") for i in items if i.get("id")]
        event_map = {}
        if ids:
            for ev in CalendarEvent.query.filter(CalendarEvent.google_event_id.in_(ids)).all():
                event_map[ev.google_event_id] = ev.id

        events_by_day: dict[int, list] = {}
        for item in items:
            start_dt, end_dt = parse_event_datetime(item)
            if not start_dt:
                continue

            title    = item.get("summary") or "Sem título"
            event_id = event_map.get(item.get("id"))
            is_ensaio = "ensaio" in title.lower()

            # All-day events: Google Calendar end date is exclusive (day after last day)
            is_all_day = bool(item.get("start", {}).get("date") and not item.get("start", {}).get("dateTime"))
            ev_start = start_dt.date()
            if end_dt:
                ev_end = end_dt.date() - timedelta(days=1) if is_all_day else end_dt.date()
            else:
                ev_end = ev_start

            cur = max(ev_start, month_start)
            stop = min(ev_end, month_end)
            while cur <= stop:
                is_start = (cur == ev_start)
                if is_start:
                    when = start_dt.strftime("%H:%M") if (start_dt.hour or start_dt.minute) else ""
                    if end_dt and (end_dt.hour or end_dt.minute) and ev_end > ev_start:
                        when += f"–{end_dt.strftime('%d/%m %H:%M')}"
                    elif end_dt and end_dt.strftime("%H:%M") != "00:00":
                        when += f"–{end_dt.strftime('%H:%M')}"
                else:
                    when = "↪"
                events_by_day.setdefault(cur.day, []).append({
                    "title":    title,
                    "when":     when,
                    "event_id": event_id,
                    "is_ensaio": is_ensaio,
                })
                cur += timedelta(days=1)

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


@calendar_bp.route("/agenda/day/<date_str>")
@login_required
def agenda_day(date_str: str):
    try:
        day_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for("calendar.agenda"))

    day_start = datetime(day_date.year, day_date.month, day_date.day)
    day_end   = day_start + timedelta(days=1)

    events = (
        CalendarEvent.query
        .filter(CalendarEvent.start_at >= day_start, CalendarEvent.start_at < day_end)
        .order_by(CalendarEvent.start_at)
        .all()
    )

    prev_day = (day_date - timedelta(days=1)).isoformat()
    next_day = (day_date + timedelta(days=1)).isoformat()
    ym       = day_date.strftime("%Y-%m")

    return render_template(
        "calendar_day.html",
        day=day_date,
        events=events,
        ym=ym,
        prev_day=prev_day,
        next_day=next_day,
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
    old_talent_id     = role.talent_id
    old_cache_value   = role.cache_value
    old_travel_cache  = role.travel_cache
    old_invite_status = role.invite_status

    role.talent_id = int(talent_id) if talent_id else None

    _is_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)
    try:
        new_cache = int(cache_value) if cache_value else None
    except ValueError:
        new_cache = None

    # Aplicar teto de cache: casting não pode ultrapassar o cap do orçamento
    if new_cache is not None and role.cache_cap is not None and new_cache > role.cache_cap:
        if not _is_superadmin:
            new_cache = role.cache_cap   # força o limite silenciosamente (JS já avisa)
        # superadmin pode ultrapassar — apenas registra no log depois

    role.cache_value = new_cache
    try:
        new_travel = int(travel_cache) if travel_cache else None
    except ValueError:
        new_travel = None
    role.travel_cache = new_travel
    role.assigned_at = datetime.now(tz=tz_sp) if role.talent_id else None
    if role.talent_id != old_talent_id:
        role.figurino_done_at = None
        role.invite_status = None
    if role.talent_id:
        role.payment_status = "nao_pago"
    # Envia remoção apenas se o talento não tinha recusado voluntariamente
    if old_talent_id and old_talent_id != role.talent_id and old_invite_status != "rejected":
        old_talent = Talent.query.get(old_talent_id)
        if old_talent:
            send_async(send_removal_email, old_talent, event, role.character_name)
    db.session.commit()
    if role.talent_id and role.talent_id != old_talent_id:
        role.invite_status = "pending"
        _cap_note = ""
        if role.cache_cap and role.cache_value and role.cache_value > role.cache_cap:
            _cap_note = f" (acima do cap de {role.cache_cap}R$ — autorizado pelo admin)"
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=current_user.name,
            actor_role="Casting",
            message=f"Adicionou {role.talent.full_name} como {role.character_name} com cachê de {role.cache_value or 0}R${_cap_note}",
            created_at=datetime.now(tz=tz_sp),
        ))
        db.session.commit()
        send_async(send_invite_email, role)
    elif role.talent_id:
        _cap_note = ""
        if role.cache_cap and role.cache_value and role.cache_value > role.cache_cap:
            _cap_note = f" (acima do cap de {role.cache_cap}R$ — autorizado pelo admin)"
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=current_user.name,
            actor_role="Casting",
            message=f"Atualizou cachê de {role.talent.full_name} como {role.character_name} para {role.cache_value or 0}R${_cap_note}",
            created_at=datetime.now(tz=tz_sp),
        ))
        db.session.commit()
        # Notifica talento confirmado se o cachê mudou
        if old_invite_status == "accepted":
            cache_changes = []
            if new_cache != old_cache_value:
                old_fmt = f"R$ {old_cache_value:,.0f}" if old_cache_value else "não definido"
                new_fmt = f"R$ {new_cache:,.0f}" if new_cache else "não definido"
                cache_changes.append(f"Cachê: {old_fmt} → {new_fmt}")
            if new_travel != old_travel_cache:
                old_fmt = f"R$ {old_travel_cache:,.0f}" if old_travel_cache else "não definido"
                new_fmt = f"R$ {new_travel:,.0f}" if new_travel else "não definido"
                cache_changes.append(f"Adicional de transporte: {old_fmt} → {new_fmt}")
            if cache_changes:
                now_sp = datetime.now(tz=tz_sp)
                role.event_changed_at = now_sp
                role.change_description = "\n".join(cache_changes)
                db.session.commit()
                send_async(send_event_changed_email, role, cache_changes)


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
        role.invite_status = "pending"
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
    if role.talent_id:
        send_async(send_invite_email, role)


def _handle_delete_role(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    can_casting = any(r.name.upper() in (RoleName.CASTING, RoleName.SUPERADMIN) for r in current_user.roles)
    if not can_casting:
        return
    role_id = request.form.get("role_id")
    role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
    if not role:
        return
    _is_superadmin = any(r.name.upper() == RoleName.SUPERADMIN for r in current_user.roles)
    if role.invite_status == "accepted" and not _is_superadmin:
        return
    name = role.character_name
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Casting",
        message=f"Removeu vaga: {name}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.delete(role)
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


def _handle_update_comercial(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    can_vendas = any(r.name.upper() in (RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN) for r in current_user.roles)
    if not can_vendas:
        return

    def _pf(v: str) -> Decimal | None:
        """Parseia número em formato BR: '1.500,50' → Decimal('1500.50')"""
        if not v or not v.strip():
            return None
        try:
            return Decimal(v.strip().replace('.', '').replace(',', '.'))
        except Exception:
            return None

    event.sale_value      = _pf(request.form.get("sale_value", ""))
    event.transport_value = _pf(request.form.get("transport_value", ""))
    event.acrescimo_value = _pf(request.form.get("acrescimo_value", ""))
    event.with_invoice    = request.form.get("with_invoice") == "1"

    inv_file = request.files.get("invoice_file")
    if inv_file and inv_file.filename:
        inv_file.stream.seek(0, 2)
        inv_size = inv_file.stream.tell()
        inv_file.stream.seek(0)
        if inv_size <= 10 * 1024 * 1024:
            fname = secure_filename(inv_file.filename)
            inv_file.save(os.path.join(current_app.config["UPLOAD_INVOICES"], fname))
            event.invoice_file = f"/uploads/invoices/{fname}"

    _VALID_METHODS = {"avista", "pix_parcelado", "faturado", "cartao"}
    pay_method = request.form.get("payment_method", "").strip()
    event.payment_method = pay_method if pay_method in _VALID_METHODS else None
    if pay_method == "pix_parcelado":
        event.payment_installments = _pi(request.form.get("payment_installments", ""))
    if pay_method == "faturado":
        due_raw = request.form.get("payment_due_date", "").strip()
        try:
            event.payment_due_date = date.fromisoformat(due_raw) if due_raw else None
        except ValueError:
            event.payment_due_date = None

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
        actor_role="Comercial",
        message=f"Atualizou dados comerciais: venda R$ {event.sale_value or 0}{'  (com NF)' if event.with_invoice else ''}",
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
    old_needs_rehearsal  = event.needs_rehearsal
    old_departure        = event.departure_time
    old_makeup_time      = event.makeup_time
    old_makeup_location  = event.makeup_location

    event.makeup_time    = request.form.get("makeup_time", "").strip() or None
    loc = request.form.get("makeup_location", "").strip()
    if loc == "outro":
        loc = request.form.get("makeup_location_custom", "").strip()
    event.makeup_location = loc or None
    event.departure_time  = request.form.get("departure_time", "").strip() or None
    event.needs_rehearsal = bool(request.form.get("needs_rehearsal"))

    logistics_changes = []
    if event.departure_time != old_departure and old_departure is not None:
        logistics_changes.append(
            f"Horário de saída: {old_departure} → {event.departure_time or 'não definido'}"
        )
    if event.makeup_time != old_makeup_time and old_makeup_time is not None:
        logistics_changes.append(
            f"Horário de maquiagem: {old_makeup_time} → {event.makeup_time or 'não definido'}"
        )
    if event.makeup_location != old_makeup_location and old_makeup_location is not None:
        logistics_changes.append(
            f"Local de maquiagem: {old_makeup_location} → {event.makeup_location or 'não definido'}"
        )
    if logistics_changes:
        _notify_accepted_roles(event, logistics_changes)

    db.session.commit()

    if event.needs_rehearsal and not old_needs_rehearsal:
        ensaio_users = User.query.join(User.roles).filter(Role.name == RoleName.ENSAIO).all()
        send_async(send_ensaio_alert_email, event, ensaio_users)
    flash("Logística salva.", "success")


_EVENT_ACTIONS = {
    "assign_casting":     _handle_assign_casting,
    "add_role":           _handle_add_role,
    "delete_role":        _handle_delete_role,
    "figurino_done":      _handle_figurino_done,
    "add_contract":       _handle_add_contract,
    "update_comercial":   _handle_update_comercial,
    "update_sale":        _handle_update_comercial,
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
        eid = event.id  # capture before commit+thread expire the ORM object
        if handler:
            handler(event, tz_sp)
        return redirect(url_for("calendar.event_detail", event_id=eid))

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

    event_ratings = (
        EventRating.query
        .filter_by(event_id=event.id)
        .order_by(EventRating.submitted_at.desc())
        .all()
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
        event_ratings=event_ratings,
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
        old_str = event.start_at.strftime("%d/%m/%Y %H:%M") if event.start_at else "—"
        new_str = new_start.strftime("%d/%m/%Y %H:%M") if new_start else "—"
        changes.append(f"Data/hora: {old_str} → {new_str}")

    old_end = _dt_naive(event.end_at)
    chk_end = _dt_naive(new_end)
    if old_end != chk_end and old_end is not None and chk_start == old_start:
        # só reporta fim se o início não mudou (evita duplicar)
        old_str = event.end_at.strftime("%H:%M") if event.end_at else "—"
        new_str = new_end.strftime("%H:%M") if new_end else "—"
        changes.append(f"Horário de término: {old_str} → {new_str}")

    old_loc = (event.location or "").strip()
    new_loc = (new_location or "").strip()
    if old_loc != new_loc and old_loc:
        changes.append(f"Local: {old_loc or '—'} → {new_loc or '—'}")

    return changes


def _notify_accepted_roles(event: CalendarEvent, changes: list[str]) -> None:
    """Marca roles aceitos como alterados e envia emails.

    O email só é enviado uma vez por rodada de mudanças — enquanto o talento não
    clicar 'Estou ciente' (que zera event_changed_at), notificações adicionais
    atualizam a descrição silenciosamente, sem novo email.
    """
    now = datetime.now(tz=ZoneInfo("America/Sao_Paulo"))
    description = "\n".join(changes)
    for role in event.roles:
        if role.invite_status == "accepted":
            already_pending = role.event_changed_at is not None
            role.event_changed_at = now
            role.change_description = description
            if not already_pending:
                send_async(send_event_changed_email, role, changes)


def _notify_ensaio_team(event: CalendarEvent) -> None:
    """Envia alerta à equipe ENSAIO quando evento precisa de ensaio."""
    ensaio_users = (
        User.query.join(User.roles)
        .filter(Role.name == RoleName.ENSAIO)
        .all()
    )
    send_async(send_ensaio_alert_email, event, ensaio_users)


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
            # Determina se é fora de SP via CEP (ViaCEP) ou string
            event.is_outside_sp = _lookup_sp_status(location)
            # Auto-estima distância via Google Maps se fora de SP
            if event.is_outside_sp:
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

            # Reavalia se é fora de SP quando o endereço mudou
            location_changed = (location or "").strip() != (old_location or "").strip()
            if location_changed or event.is_outside_sp is None:
                event.is_outside_sp = _lookup_sp_status(location)

            if event.is_outside_sp and (location_changed or not event.travel_distance_km):
                settings = SiteSetting.query.get(1)
                _fetch_travel_data(event, settings)
            elif not event.is_outside_sp:
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
        # Only sync character roles — never touch extra roles (Coordenador, Maquiador, etc.)
        existing = {r.character_name: r for r in event.roles if r.role_type != "extra"}

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

_CEP_RE = re.compile(r'\b(\d{5})-?(\d{3})\b')


def _lookup_sp_status(location: str) -> bool | None:
    """Determina se o endereço é fora da cidade de São Paulo.

    Tenta lookup via ViaCEP se encontrar um CEP no endereço.
    Fallback: checagem por string.
    Retorna True=fora de SP | False=dentro de SP | None=desconhecido.
    """
    if not location:
        return None

    m = _CEP_RE.search(location)
    if m:
        cep = m.group(1) + m.group(2)
        import json as _json
        try:
            url = f"https://viacep.com.br/ws/{cep}/json/"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = _json.loads(resp.read())
            if "erro" not in data:
                city = data.get("localidade", "").strip().lower()
                uf   = data.get("uf", "").strip().upper()
                is_sp = city in ("são paulo", "sao paulo") and uf == "SP"
                return not is_sp
        except Exception:
            pass  # fall through to string check

    # Fallback: se "São Paulo" está explicitamente no endereço, é dentro da cidade
    loc_lower = location.lower()
    if any(term in loc_lower for term in _SP_CITY_TERMS):
        return False
    # Sem CEP e sem "São Paulo" no endereço: desconhecido
    return None


def _is_outside_sp(location: str) -> bool:
    """Retorna True se o endereço não pertence à cidade de São Paulo (checagem rápida por string).

    Usado internamente quando só precisamos de bool (ex: decidir se chama Google Maps).
    Para persistir em banco, use _lookup_sp_status.
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
    import os
    api_key = (settings.google_maps_api_key if settings else None) or os.getenv("GOOGLE_MAPS_API_KEY")
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
    import os
    api_key = (settings.google_maps_api_key if settings else None) or os.getenv("GOOGLE_MAPS_API_KEY")

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

    date_str      = request.form.get("ensaio_date", "").strip()
    start_str     = request.form.get("ensaio_start", "").strip()
    end_str       = request.form.get("ensaio_end", "").strip()
    desc          = request.form.get("ensaio_desc", "").strip()
    location_type = request.form.get("ensaio_location_type", "manto")
    custom_loc    = request.form.get("ensaio_location", "").strip()

    if location_type == "outro" and custom_loc:
        ensaio_loc = custom_loc
    else:
        _s = SiteSetting.query.get(1)
        ensaio_loc = (_s.manto_address or "") if _s else ""

    errors = []
    d = None
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        errors.append("Data inválida.")

    st = et = None
    if d:
        try:
            st = datetime.combine(d, datetime.strptime(start_str, "%H:%M").time())
            et = datetime.combine(d, datetime.strptime(end_str,   "%H:%M").time())
        except ValueError:
            errors.append("Horário inválido (use HH:MM).")

    if st and et and et <= st:
        errors.append("Horário de fim deve ser após o início.")

    if errors:
        flash(" ".join(errors), "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    title = f"🟧 ENSAIO — {event.title}"
    try:
        created = insert_event(CALENDAR_ID, title, st, et, description=desc, location=ensaio_loc)
        ensaio_ev = CalendarEvent(
            google_event_id=created["id"],
            title=title,
            description=desc or None,
            location=ensaio_loc or None,
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


@calendar_bp.route("/events/<int:ensaio_id>/edit-ensaio", methods=["POST"])
@login_required
def edit_ensaio(ensaio_id: int):
    """Edita data/hora/descrição de um evento de ensaio já criado."""
    ensaio = CalendarEvent.query.get_or_404(ensaio_id)

    if not any(r.name.upper() in _CAN_ENSAIO for r in current_user.roles):
        abort(403)

    if ensaio.event_type != "ENSAIO":
        abort(400)

    date_str    = request.form.get("ensaio_date", "").strip()
    start_str   = request.form.get("ensaio_start", "").strip()
    end_str     = request.form.get("ensaio_end", "").strip()
    desc        = request.form.get("ensaio_desc", "").strip()
    new_loc     = request.form.get("ensaio_location", "").strip()
    redirect_to = request.form.get("redirect_to", "home")

    errors = []
    d = None
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        errors.append("Data inválida.")

    st = et = None
    if d:
        try:
            st = datetime.combine(d, datetime.strptime(start_str, "%H:%M").time())
            et = datetime.combine(d, datetime.strptime(end_str,   "%H:%M").time())
        except ValueError:
            errors.append("Horário inválido (use HH:MM).")

    if st and et and et <= st:
        errors.append("Horário de fim deve ser após o início.")

    if errors:
        flash(" ".join(errors), "error")
    else:
        ensaio.start_at    = st
        ensaio.end_at      = et
        ensaio.description = desc or None
        if new_loc:
            ensaio.location = new_loc
        db.session.commit()

        if ensaio.google_event_id:
            try:
                update_event(
                    CALENDAR_ID,
                    ensaio.google_event_id,
                    ensaio.title,
                    st,
                    et,
                    description=desc,
                    location=ensaio.location or "",
                )
            except RuntimeError as exc:
                flash(f"Salvo no banco, mas erro ao atualizar Google Calendar: {exc}", "warning")

        flash("Ensaio atualizado com sucesso!", "success")

    if redirect_to == "event" and ensaio.parent_event_id:
        return redirect(url_for("calendar.event_detail", event_id=ensaio.parent_event_id))
    return redirect(url_for("home"))


@calendar_bp.route("/events/<int:ensaio_id>/delete-ensaio", methods=["POST"])
@login_required
def delete_ensaio(ensaio_id: int):
    """Cancela (exclui) um ensaio sem afetar o evento pai."""
    ensaio = CalendarEvent.query.get_or_404(ensaio_id)

    if ensaio.event_type != "ENSAIO":
        abort(400)

    if not any(r.name.upper() in _CAN_ENSAIO for r in current_user.roles):
        abort(403)

    parent_id = ensaio.parent_event_id

    if ensaio.google_event_id:
        try:
            delete_event(CALENDAR_ID, ensaio.google_event_id)
        except RuntimeError as exc:
            flash(f"Salvo no banco, mas erro ao remover do Google Calendar: {exc}", "warning")

    db.session.delete(ensaio)
    db.session.commit()

    flash("Ensaio cancelado com sucesso.", "success")
    if parent_id:
        return redirect(url_for("calendar.event_detail", event_id=parent_id))
    return redirect(url_for("home"))


# ─── CRIAR EVENTO (COMERCIAL) ─────────────────────────────────────────────────

def _compute_performer_caches(snapshot: dict) -> list[dict]:
    """Retorna lista de {label, cache_1h, cache_2h, cache_4h, needs_makeup, is_singer}
    para cada performer + coordenadores + técnico + maquiador do snapshot."""
    from app.orcamento.pricing import (
        get_ator_prices, get_cantor_prices, get_especial_prices,
        get_coordenador_prices, get_tecnico_prices, calcular_maquiador,
    )
    from app.orcamento import settings as _orc_cfg

    performers     = snapshot.get("performers", [])
    coordenador_qty = int(snapshot.get("coordenador_qty", 1) or 1)
    has_show       = any(
        p.get("show") or p.get("cantor") or p.get("type") == "cantor" or
        (p.get("type") == "especial" and p.get("personagem", "") in _orc_cfg.ESPECIAIS_SEMPRE_SHOW)
        for p in performers
    )

    # Adicional noturno (+R$50 por performer/coord se horário >= 19h)
    event_time_str = (snapshot.get("event_time") or "").strip()
    noturno_add = 0
    try:
        if event_time_str and int(event_time_str.split(":")[0]) >= 19:
            noturno_add = 50
    except (ValueError, IndexError):
        pass

    # Adicional fora SP (parcela afsp = km×2 ÷ divisor, por pessoa)
    transport_add: float = 0.0
    if snapshot.get("fora_sp"):
        km_ida = float(snapshot.get("km_ida") or 0)
        if km_ida > 0:
            afsp_divisor = float(_orc_cfg.load().get("transporte", {}).get("afsp_divisor", 3.0))
            transport_add = round(km_ida * 2 / afsp_divisor, 2)

    result = []
    num_makes_regular  = 0
    num_makes_especial = 0

    for p in performers:
        ptype      = p.get("type", "")
        show       = bool(p.get("show", False))
        makeup     = bool(p.get("makeup", False))
        makeup_tipo = p.get("makeup_tipo", "comum")
        cantor_flag = bool(p.get("cantor", False))
        nome       = p.get("nome", "").strip()
        is_singer  = False

        if ptype == "ator":
            subtipo = p.get("subtipo", "cara_limpa")
            if subtipo == "cantor":
                prices = get_cantor_prices(show, makeup)
                label  = nome or "Cantor"
                is_singer = True
            else:
                prices = get_ator_prices(subtipo, show, makeup)
                label  = nome or ("Boneco" if subtipo == "boneco" else "Ator")
        elif ptype == "cantor":
            prices = get_cantor_prices(show=True, makeup=makeup)
            label  = nome or "Cantor"
            is_singer = True
        elif ptype == "especial":
            personagem = p.get("personagem", "")
            prices = get_especial_prices(personagem, show, cantor_flag)
            label  = nome or personagem
            if cantor_flag:
                is_singer = True
        else:
            prices = (0, 0, 0)
            label  = nome or "Profissional"

        if makeup:
            if makeup_tipo == "especial":
                num_makes_especial += 1
            else:
                num_makes_regular += 1

        result.append({
            "label":       label,
            "cache_1h":    round(int(prices[0]) + noturno_add + transport_add),
            "cache_2h":    round(int(prices[1]) + noturno_add + transport_add),
            "cache_4h":    round(int(prices[2]) + noturno_add + transport_add),
            "needs_makeup": makeup,
            "is_singer":    is_singer,
            "role_type":   "character",
        })

    # Coordenadores
    coord_prices = get_coordenador_prices(has_show, coordenador_qty)
    per_coord    = [coord_prices[i] // max(coordenador_qty, 1) for i in range(3)]
    for _ in range(coordenador_qty):
        result.append({
            "label":       "Coordenador",
            "cache_1h":    round(int(per_coord[0]) + noturno_add + transport_add),
            "cache_2h":    round(int(per_coord[1]) + noturno_add + transport_add),
            "cache_4h":    round(int(per_coord[2]) + noturno_add + transport_add),
            "needs_makeup": False,
            "is_singer":    False,
            "role_type":   "extra",
        })

    # Técnico de som (se houver show) — apenas regra do >500km afeta o técnico, não os adicionais por pessoa
    if has_show:
        tp = get_tecnico_prices()
        result.append({
            "label":       "Técnico de Som",
            "cache_1h":    int(tp[0]),
            "cache_2h":    int(tp[1]),
            "cache_4h":    int(tp[2]),
            "needs_makeup": False,
            "is_singer":    False,
            "role_type":   "extra",
        })

    # Maquiador (se necessário)
    if num_makes_regular > 0 or num_makes_especial > 0:
        mq_cost = calcular_maquiador(num_makes_regular, num_makes_especial)
        result.append({
            "label":       "Maquiador",
            "cache_1h":    int(mq_cost),
            "cache_2h":    int(mq_cost),
            "cache_4h":    int(mq_cost),
            "needs_makeup": False,
            "is_singer":    False,
            "role_type":   "extra",
        })

    return result


def _save_file_upload(file, upload_dir: str, subpath: str) -> str | None:
    """Salva um arquivo e retorna o path relativo a /uploads/, ou None."""
    if not file or not file.filename:
        return None
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > 20 * 1024 * 1024:
        return None
    name = secure_filename(file.filename)
    file.save(os.path.join(upload_dir, name))
    return f"/uploads/{subpath}/{name}"


@calendar_bp.route("/events/new", methods=["GET", "POST"])
@login_required
def create_event():
    if not any(r.name.upper() in _CAN_CREATE for r in current_user.roles):
        abort(403)

    import json as _json

    figurino_sheets = FigurinoSheet.query.order_by(FigurinoSheet.character_name.asc()).all()
    # Índice nome→id para auto-match figurino
    sheet_by_name = {s.character_name.lower(): s.id for s in figurino_sheets}
    sellers = User.query.join(User.roles).filter(Role.name == RoleName.COMERCIAL).order_by(User.name.asc()).all()

    # ── GET — pré-fill a partir do orçamento ────────────────────────────────
    if request.method == "GET":
        prefill = {}
        orc_id  = request.args.get("orcamento_id", "").strip()
        if orc_id and orc_id.isdigit():
            entry = OrcamentoHistory.query.get(int(orc_id))
            if entry:
                snap = _json.loads(entry.form_snapshot or "{}")
                # transporte fora SP
                transport_val = 0
                if snap.get("fora_sp"):
                    from app.orcamento.transport import calcular_carro, calcular_van
                    km = float(snap.get("km_ida", 0) or 0)
                    if snap.get("transporte_tipo", "van") == "van":
                        tb = calcular_van(
                            int(snap.get("num_colaboradores", 1) or 1),
                            km,
                            bool(snap.get("carretinha", False)),
                            entry.has_show,
                        )
                    else:
                        tb = calcular_carro(
                            int(snap.get("num_carros", 1) or 1),
                            int(snap.get("num_colaboradores", 1) or 1),
                            km,
                            entry.has_show,
                        )
                    transport_val = int(tb["total"])

                acrescimo = float(snap.get("acrescimo_valor", 0) or 0)
                acrescimo_val = int(acrescimo) if snap.get("acrescimo_tipo", "valor") == "valor" else 0

                caches = _compute_performer_caches(snap)

                duracao_custom = int(snap.get("duracao_custom", 0) or 0)
                total_4h_val   = float(entry.total_4h or 0)
                total_custom   = (
                    round(total_4h_val / 4 * duracao_custom, 2)
                    if duracao_custom > 0 and duracao_custom not in (1, 2, 4)
                    else None
                )

                prefill = {
                    "orcamento_id":   entry.id,
                    "date":           snap.get("event_date", ""),
                    "start_time":     snap.get("event_time", ""),
                    "location":       entry.event_location or "",
                    "client_name":    entry.client_name or "",
                    "total_1h":       float(entry.total_1h or 0),
                    "total_2h":       float(entry.total_2h or 0),
                    "total_4h":       float(entry.total_4h or 0),
                    "total_custom":   total_custom,
                    "duracao_custom": duracao_custom if total_custom else None,
                    "has_show":       entry.has_show,
                    "transport_value": transport_val,
                    "acrescimo_value": acrescimo_val,
                    "with_invoice":   bool(snap.get("nota_fiscal", False)),
                    "caches_json":    _json.dumps(caches, ensure_ascii=False),
                }
        return render_template(
            "event_create.html",
            figurino_sheets=figurino_sheets,
            sellers=sellers,
            errors=[],
            prefill=prefill,
        )

    # ── POST ────────────────────────────────────────────────────────────────
    title        = request.form.get("title", "").strip()
    event_type   = request.form.get("event_type", "").strip()
    date_str     = request.form.get("event_date", "").strip()
    start_str    = request.form.get("event_start", "").strip()
    end_str      = request.form.get("event_end", "").strip()
    location     = request.form.get("location", "").strip()
    description  = request.form.get("description", "").strip()
    needs_rehearsal  = (event_type == "SHOW") or bool(request.form.get("needs_rehearsal"))
    sale_value_raw   = request.form.get("sale_value", "").strip()
    transport_value_raw = request.form.get("transport_value", "").strip()
    acrescimo_value_raw = request.form.get("acrescimo_value", "").strip()
    with_invoice     = bool(request.form.get("with_invoice"))
    seller_id_raw    = request.form.get("seller_id", "").strip()

    # pagamento
    payment_method   = request.form.get("payment_method", "").strip() or None
    payment_inst_raw = request.form.get("payment_installments", "").strip()
    payment_due_raw  = request.form.get("payment_due_date", "").strip()

    # orçamento de origem + duração selecionada
    orcamento_id_raw = request.form.get("orcamento_history_id", "").strip()
    duracao_raw      = request.form.get("duracao", "1").strip()   # '1' | '2' | '4'
    dur_idx          = {"1": 0, "2": 1, "4": 2}.get(duracao_raw, 0)

    # personagens do form
    char_names   = request.form.getlist("character_names[]")
    sheet_ids    = request.form.getlist("figurino_sheet_ids[]")
    char_makeups = request.form.getlist("char_needs_makeup[]")   # '1' ou ''
    char_singers = request.form.getlist("char_is_singer[]")      # '1' ou ''
    char_caches  = request.form.getlist("char_cache[]")          # valor em R$

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
            st = datetime.combine(d, datetime.strptime(start_str, "%H:%M").time())
            et = datetime.combine(d, datetime.strptime(end_str,   "%H:%M").time())
        except ValueError:
            errors.append("Horário inválido (use HH:MM).")

    if st and et and et <= st:
        errors.append("Horário de fim deve ser após o início.")

    if errors:
        return render_template("event_create.html", figurino_sheets=figurino_sheets,
                               sellers=sellers, errors=errors, prefill={})

    # Remove prefixo (TIPO) que o JS já inseriu no título para não duplicar
    clean_title = re.sub(r'^\s*\([^)]*\)\s*', '', title).strip() if title else title
    gc_title = f"({event_type}) {clean_title}" if event_type else title
    try:
        created = insert_event(CALENDAR_ID, gc_title, st, et, description=description, location=location)
    except RuntimeError as exc:
        return render_template("event_create.html", figurino_sheets=figurino_sheets,
                               sellers=sellers, errors=[str(exc)], prefill={})

    def _parse_int(raw: str) -> int | None:
        try:
            v = float(raw.replace(",", "."))
            return int(round(v))
        except (ValueError, AttributeError):
            return None

    def _parse_decimal(raw: str) -> Decimal | None:
        """Parseia número em formato BR: '1.500,50' → Decimal('1500.50')"""
        if not raw or not raw.strip():
            return None
        try:
            return Decimal(raw.strip().replace('.', '').replace(',', '.'))
        except Exception:
            return None

    # ── Nota fiscal file (opcional) ──────────────────────────────────────────
    invoice_filename = None
    invoice_file = request.files.get("invoice_file")
    if invoice_file and invoice_file.filename:
        _inv_size = invoice_file.stream.seek(0, 2)
        invoice_file.stream.seek(0)
        if _inv_size <= 20 * 1024 * 1024:
            invoice_filename = secure_filename(invoice_file.filename)
            invoice_file.save(
                os.path.join(current_app.config["UPLOAD_INVOICES"], invoice_filename)
            )

    event = CalendarEvent(
        google_event_id      = created["id"],
        title                = gc_title,
        description          = description or None,
        location             = location or None,
        start_at             = st,
        end_at               = et,
        event_type           = event_type or None,
        needs_rehearsal      = needs_rehearsal,
        source               = "platform",
        sale_value           = _parse_decimal(sale_value_raw),
        transport_value      = _parse_decimal(transport_value_raw),
        acrescimo_value      = _parse_decimal(acrescimo_value_raw),
        with_invoice         = with_invoice,
        invoice_file         = invoice_filename,
        seller_id            = int(seller_id_raw) if seller_id_raw.isdigit() else None,
        payment_method       = payment_method,
        payment_installments = int(payment_inst_raw) if payment_inst_raw.isdigit() else None,
        payment_due_date     = date.fromisoformat(payment_due_raw) if payment_due_raw else None,
        orcamento_history_id = int(orcamento_id_raw) if orcamento_id_raw.isdigit() else None,
    )
    db.session.add(event)
    db.session.flush()

    # Determina se é fora de SP e auto-estima distância
    event.is_outside_sp = _lookup_sp_status(location)
    if event.is_outside_sp:
        settings = SiteSetting.query.get(1)
        _fetch_travel_data(event, settings)

    # ── Personagens / equipe ─────────────────────────────────────────────────
    # Se veio de orçamento, caches pré-calculados por index de duração
    orc_caches_json = request.form.get("orc_caches_json", "")
    orc_caches: list[dict] = []
    if orc_caches_json:
        try:
            orc_caches = _json.loads(orc_caches_json)
        except _json.JSONDecodeError:
            orc_caches = []

    for i, (char, sheet_id_raw) in enumerate(zip(char_names, sheet_ids)):
        char = char.strip()
        if not char:
            continue

        # figurino: usuário selecionou, ou auto-match por nome
        if sheet_id_raw and sheet_id_raw.isdigit():
            sheet_id = int(sheet_id_raw)
        else:
            sheet_id = sheet_by_name.get(char.lower())

        # cache: preferência manual do form, depois caches do orçamento
        cache_val = _parse_int(char_caches[i]) if i < len(char_caches) else None
        makeup    = (char_makeups[i] == "1") if i < len(char_makeups) else False
        singer    = (char_singers[i] == "1") if i < len(char_singers) else False

        if cache_val is None and i < len(orc_caches):
            key = ["cache_1h", "cache_2h", "cache_4h"][dur_idx]
            cache_val = orc_caches[i].get(key)

        role_type = orc_caches[i].get("role_type", "character") if i < len(orc_caches) else "character"

        # cache_cap guarda o teto definido pelo orçamento (imutável para casting)
        from_orc = bool(orc_caches) and cache_val is not None
        db.session.add(EventRole(
            event_id         = event.id,
            character_name   = char,
            figurino_sheet_id= sheet_id,
            cache_value      = cache_val,
            cache_cap        = cache_val if from_orc else None,
            role_type        = role_type,
            needs_makeup     = makeup or None,
            is_singer        = singer or None,
        ))

    # Se não veio de orçamento, garante coordenador padrão
    if not orc_caches:
        _ensure_coordinator(event.id)

    # ── Comprovantes de pagamento (múltiplos) ────────────────────────────────
    payment_files  = request.files.getlist("payment_files[]")
    payment_amounts = request.form.getlist("payment_amounts[]")
    for pf, pa_raw in zip(payment_files, payment_amounts):
        fpath = _save_file_upload(pf, current_app.config["UPLOAD_PAYMENTS"], "payments")
        if fpath:
            db.session.add(EventPayment(
                event_id  = event.id,
                file_path = fpath,
                amount    = _parse_int(pa_raw),
            ))

    # ── Contrato ─────────────────────────────────────────────────────────────
    contract_file   = request.files.get("contract_file")
    contract_amount = request.form.get("contract_amount", "").strip()
    is_signed       = bool(request.form.get("contract_signed"))
    fpath = _save_file_upload(contract_file, current_app.config["UPLOAD_CONTRACTS"], "contracts")
    if fpath:
        db.session.add(EventContract(
            event_id  = event.id,
            file_path = fpath,
            amount    = _parse_int(contract_amount),
            is_signed = is_signed,
        ))

    # ── Observações (texto / link / imagem) ──────────────────────────────────
    obs_types    = request.form.getlist("obs_type[]")
    obs_contents = request.form.getlist("obs_content[]")
    obs_labels   = request.form.getlist("obs_label[]")
    obs_images   = request.files.getlist("obs_image[]")
    img_idx = 0
    for j, otype in enumerate(obs_types):
        content   = obs_contents[j].strip() if j < len(obs_contents) else ""
        label     = obs_labels[j].strip()   if j < len(obs_labels)   else ""
        file_path = None
        if otype == "image":
            if img_idx < len(obs_images):
                file_path = _save_file_upload(
                    obs_images[img_idx],
                    current_app.config["UPLOAD_EVENT_OBS"],
                    "event_obs",
                )
                img_idx += 1
            if not file_path:
                continue
        elif otype in ("text", "link") and not content:
            continue
        db.session.add(EventObservation(
            event_id   = event.id,
            obs_type   = otype,
            content    = content or None,
            file_path  = file_path,
            label      = label or None,
        ))

    db.session.add(EventLog(
        event_id   = event.id,
        actor_name = current_user.name,
        actor_role = "COMERCIAL",
        message    = "Evento criado pela plataforma",
        created_at = datetime.now(tz=TZ),
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


@calendar_bp.route("/events/<int:event_id>/observations/add", methods=["POST"])
@login_required
def add_observation(event_id: int):
    """Adiciona observações a um evento existente."""
    event = CalendarEvent.query.get_or_404(event_id)

    obs_types    = request.form.getlist("obs_type[]")
    obs_contents = request.form.getlist("obs_content[]")
    obs_labels   = request.form.getlist("obs_label[]")
    obs_images   = request.files.getlist("obs_image[]")
    img_idx = 0
    added = 0
    for j, otype in enumerate(obs_types):
        content   = obs_contents[j].strip() if j < len(obs_contents) else ""
        label     = obs_labels[j].strip()   if j < len(obs_labels)   else ""
        file_path = None
        if otype == "image":
            if img_idx < len(obs_images):
                file_path = _save_file_upload(
                    obs_images[img_idx],
                    current_app.config["UPLOAD_EVENT_OBS"],
                    "event_obs",
                )
                img_idx += 1
            if not file_path:
                continue
        elif otype in ("text", "link") and not content:
            continue
        db.session.add(EventObservation(
            event_id  = event.id,
            obs_type  = otype,
            content   = content or None,
            file_path = file_path,
            label     = label or None,
        ))
        added += 1

    if added:
        db.session.commit()
        flash(f"{added} observação(ões) adicionada(s).", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))


@calendar_bp.route("/events/<int:event_id>/observations/<int:obs_id>/delete", methods=["POST"])
@login_required
def delete_observation(event_id: int, obs_id: int):
    """Remove uma observação de um evento."""
    obs = EventObservation.query.filter_by(id=obs_id, event_id=event_id).first_or_404()
    db.session.delete(obs)
    db.session.commit()
    return redirect(url_for("calendar.event_detail", event_id=event_id))
