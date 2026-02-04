from datetime import datetime, timezone, timedelta
import calendar as cal
import os
import re
from zoneinfo import ZoneInfo

from flask import Blueprint, redirect, request, session, url_for, render_template, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from .service import (
    get_authorization_url,
    build_flow,
    save_token,
    fetch_events_for_month,
    parse_event_datetime,
)
from .. import db
from app.models import CalendarEvent, EventRole, EventLog, Talent, EventContract, EventPayment

calendar_bp = Blueprint("calendar", __name__)

CALENDAR_ID = "eventos@mantoproducoes.com.br"


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

    items = fetch_events_for_month(CALENDAR_ID, year, month)
    sync_events(items)

    ids = [i.get("id") for i in items if i.get("id")]
    event_map = {}
    if ids:
        for ev in CalendarEvent.query.filter(CalendarEvent.google_event_id.in_(ids)).all():
            event_map[ev.google_event_id] = ev.id

    events_by_day = {}
    for item in items:
        start_dt, _ = parse_event_datetime(item)
        if start_dt and start_dt.month == month:
            day = start_dt.day
            events_by_day.setdefault(day, []).append(
                {
                    "title": item.get("summary") or "Sem título",
                    "when": start_dt.strftime("%H:%M") if start_dt else "",
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

    return render_template(
        "calendar_list.html",
        ym=ym,
        prev_ym=prev_ym,
        next_ym=next_ym,
        events=items,
        event_map=event_map,
        view=view,
        month_weeks=weeks,
        events_by_day=events_by_day,
    )


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
        action = request.form.get("action")

        if action == "assign_casting":
            role_id = request.form.get("role_id")
            talent_id = request.form.get("talent_id")
            cache_value = request.form.get("cache_value")
            role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
            if role:
                role.talent_id = int(talent_id) if talent_id else None
                try:
                    role.cache_value = int(cache_value) if cache_value else None
                except ValueError:
                    role.cache_value = None
                role.assigned_at = datetime.now(tz=tz_sp) if role.talent_id else None
                db.session.commit()
                if role.talent_id:
                    db.session.add(
                        EventLog(
                            event_id=event.id,
                            actor_name=current_user.name,
                            actor_role="Casting",
                            message=f"Adicionou {role.talent.full_name} como {role.character_name} com um cachê de {role.cache_value or 0} reais",
                            created_at=datetime.now(tz=tz_sp),
                        )
                    )
                    db.session.commit()

        if action == "add_role":
            character_name = request.form.get("character_name", "").strip()
            talent_id = request.form.get("talent_id")
            cache_value = request.form.get("cache_value")
            if character_name:
                role = EventRole(event_id=event.id, character_name=character_name)
                if talent_id:
                    role.talent_id = int(talent_id)
                    role.assigned_at = datetime.now(tz=tz_sp)
                try:
                    role.cache_value = int(cache_value) if cache_value else None
                except ValueError:
                    role.cache_value = None
                db.session.add(role)
                db.session.add(
                    EventLog(
                        event_id=event.id,
                        actor_name=current_user.name,
                        actor_role="Casting",
                        message=(
                            f"Adicionou {role.talent.full_name} como {role.character_name} com um cachê de {role.cache_value or 0} reais"
                            if role.talent_id
                            else f"Adicionou personagem extra: {character_name}"
                        ),
                        created_at=datetime.now(tz=tz_sp),
                    )
                )
                db.session.commit()

        if action == "figurino_done":
            role_id = request.form.get("role_id")
            role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
            if role:
                role.figurino_done_at = datetime.now(tz=tz_sp)
                db.session.add(
                    EventLog(
                        event_id=event.id,
                        actor_name=current_user.name,
                        actor_role="Figurino",
                        message=f"Separou figurino de {role.character_name}",
                        created_at=datetime.now(tz=tz_sp),
                    )
                )
                db.session.commit()

        if action == "add_contract":
            amount_raw = request.form.get("contract_amount")
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
                        amount = int(amount_raw) if amount_raw else None
                    except ValueError:
                        amount = None
                    db.session.add(
                        EventContract(
                            event_id=event.id,
                            file_path=f"/uploads/contracts/{name}",
                            amount=amount,
                        )
                    )
                    db.session.add(
                        EventLog(
                            event_id=event.id,
                            actor_name=current_user.name,
                            actor_role="Comercial",
                            message="Adicionou contrato assinado",
                            created_at=datetime.now(tz=tz_sp),
                        )
                    )
                    db.session.commit()

        if action == "add_payment":
            amount_raw = request.form.get("payment_amount")
            file = request.files.get("payment_file")
            if file and file.filename:
                file.stream.seek(0, 2)
                size = file.stream.tell()
                file.stream.seek(0)
                if size <= 10 * 1024 * 1024:
                    name = secure_filename(file.filename)
                    save_path = os.path.join(current_app.config["UPLOAD_PAYMENTS"], name)
                    file.save(save_path)
                    try:
                        amount = int(amount_raw) if amount_raw else None
                    except ValueError:
                        amount = None
                    db.session.add(
                        EventPayment(
                            event_id=event.id,
                            file_path=f"/uploads/payments/{name}",
                            amount=amount,
                        )
                    )
                    db.session.add(
                        EventLog(
                            event_id=event.id,
                            actor_name=current_user.name,
                            actor_role="Comercial",
                            message=f"Adicionou pagamento recebido de {amount or 0} reais",
                            created_at=datetime.now(tz=tz_sp),
                        )
                    )
                    db.session.commit()

        return redirect(url_for("calendar.event_detail", event_id=event.id))

    talents = Talent.query.filter_by(status="active").order_by(Talent.full_name.asc()).all()
    contracts = EventContract.query.filter_by(event_id=event.id).order_by(EventContract.created_at.desc()).all()
    payments = EventPayment.query.filter_by(event_id=event.id).order_by(EventPayment.created_at.desc()).all()

    # disponibilidade por talento (mesmo dia / conflito de horario)
    availability = {}
    if event.start_at:
        event_start = event.start_at
        event_end = event.end_at or (event.start_at + timedelta(hours=2))
        for t in talents:
            conflicts = (
                EventRole.query.join(CalendarEvent)
                .filter(
                    EventRole.talent_id == t.id,
                    CalendarEvent.id != event.id,
                )
                .all()
            )
            status = "free"
            info = ""
            for r in conflicts:
                if not r.event or not r.event.start_at:
                    continue
                other_start = r.event.start_at
                other_end = r.event.end_at or (r.event.start_at + timedelta(hours=2))
                if other_start.date() == event_start.date():
                    status = "same_day"
                    info = f"{r.event.title} ({other_start.strftime('%d/%m/%Y %H:%M')} - {other_end.strftime('%d/%m/%Y %H:%M')})"
                    if max(event_start, other_start) < min(event_end, other_end):
                        status = "conflict"
                        info = f"Conflito: {r.event.title} ({other_start.strftime('%d/%m/%Y %H:%M')} - {other_end.strftime('%d/%m/%Y %H:%M')})"
                        break
            availability[t.id] = {"status": status, "info": info}

    def has_role(name: str) -> bool:
        return any(r.name.upper() == name.upper() for r in current_user.roles)

    return render_template(
        "event_detail.html",
        event=event,
        talents=talents,
        logs=logs,
        contracts=contracts,
        payments=payments,
        availability=availability,
        show_casting=has_role("CASTING") or has_role("SUPERADMIN"),
        show_figurino=has_role("FIGURINO") or has_role("SUPERADMIN"),
        show_comercial=has_role("COMERCIAL") or has_role("SUPERADMIN"),
    )


def parse_characters(title: str) -> list[str]:
    if not title:
        return []
    parts = [p.strip() for p in re.split(r"\s*\+\s*", title) if p.strip()]
    return parts


def sync_events(items: list[dict]) -> None:
    for item in items:
        google_id = item.get("id")
        if not google_id:
            continue

        title = item.get("summary") or "Sem título"
        description = item.get("description")
        location = item.get("location")
        start_at, end_at = parse_event_datetime(item)

        event = CalendarEvent.query.filter_by(google_event_id=google_id).first()
        if not event:
            event = CalendarEvent(
                google_event_id=google_id,
                title=title,
                description=description,
                location=location,
                start_at=start_at,
                end_at=end_at,
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
        else:
            event.title = title
            event.description = description
            event.location = location
            event.start_at = start_at
            event.end_at = end_at

        if title.startswith("🟧 ENSAIO"):
            for role in list(event.roles):
                db.session.delete(role)
            db.session.commit()
            continue

        characters = parse_characters(title)
        existing = {r.character_name: r for r in event.roles}

        for name, role in list(existing.items()):
            if name not in characters:
                db.session.delete(role)

        for name in characters:
            if name not in existing:
                db.session.add(EventRole(event_id=event.id, character_name=name))

    db.session.commit()
