from datetime import datetime
import re
from flask import Blueprint, redirect, request, session, url_for, render_template
from flask_login import login_required
from .service import (
    get_authorization_url,
    build_flow,
    save_token,
    fetch_events_for_month,
    parse_event_datetime,
)
from .. import db
from app.models import CalendarEvent, EventRole, Talent

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
    # ym = "YYYY-MM"
    ym = request.args.get("ym", "").strip()
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

    # anterior e próximo mês (para botões)
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
    )


@calendar_bp.route("/events/<int:event_id>", methods=["GET", "POST"])
@login_required
def event_detail(event_id: int):
    event = CalendarEvent.query.get_or_404(event_id)

    if request.method == "POST":
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
            role.assigned_at = datetime.utcnow() if role.talent_id else None
            db.session.commit()
        return redirect(url_for("calendar.event_detail", event_id=event.id))

    talents = Talent.query.filter_by(status="active").order_by(Talent.full_name.asc()).all()
    return render_template("event_detail.html", event=event, talents=talents)


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

        title = item.get("summary") or "Sem titulo"
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
        else:
            event.title = title
            event.description = description
            event.location = location
            event.start_at = start_at
            event.end_at = end_at

        # update roles based on title
        characters = parse_characters(title)
        existing = {r.character_name: r for r in event.roles}

        # remove roles no longer in title
        for name, role in list(existing.items()):
            if name not in characters:
                db.session.delete(role)

        # add missing roles
        for name in characters:
            if name not in existing:
                db.session.add(EventRole(event_id=event.id, character_name=name))

    db.session.commit()
