from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
import calendar as cal
from .config import Config  # se seu config.py está na raiz

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # ✅ Importa blueprints AQUI (depois do db existir)
    from .auth.routes import auth_bp
    from .rh.routes import rh_bp
    from .admin.routes import admin_bp
    from .calendar.routes import calendar_bp
    from .talents.routes import talents_bp
    from .tools.routes import tools_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(rh_bp, url_prefix="/rh")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(calendar_bp)
    app.register_blueprint(talents_bp)
    app.register_blueprint(tools_bp)
    print(app.url_map)
    @app.route("/")
    @login_required
    def home():
        from app.calendar.service import fetch_events_for_month, fetch_events_for_range, TZ, parse_event_datetime
        from app.calendar.routes import CALENDAR_ID, sync_events
        from app.models import CalendarEvent, EventRole

        now = datetime.now(tz=TZ)
        event_map = {}
        try:
            items = fetch_events_for_month(CALENDAR_ID, now.year, now.month)
            upcoming_raw = fetch_events_for_range(CALENDAR_ID, now, now + timedelta(days=7))
            sync_events(items)
            sync_events(upcoming_raw)
        except RuntimeError:
            items = []
            upcoming_raw = []

        days_with_events = set()
        events_by_day = {}
        for item in items:
            start_dt, _ = parse_event_datetime(item)
            if start_dt and start_dt.month == now.month:
                day = start_dt.day
                days_with_events.add(day)
                events_by_day.setdefault(day, []).append(
                    {
                        "title": item.get("summary") or "Sem titulo",
                        "when": start_dt.strftime("%H:%M") if start_dt.time() else "",
                        "event_id": event_map.get(item.get("id")),
                    }
                )

        # build month grid (weeks)
        first_weekday, days_in_month = cal.monthrange(now.year, now.month)
        # monthrange: Monday=0..Sunday=6, we want Sunday=0
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

        # map google id to event id
        ids = [i.get("id") for i in items if i.get("id")]
        ids += [i.get("id") for i in upcoming_raw if i.get("id")]
        if ids:
            for ev in CalendarEvent.query.filter(CalendarEvent.google_event_id.in_(ids)).all():
                event_map[ev.google_event_id] = ev.id

        upcoming = []
        for item in upcoming_raw:
            start_dt, _ = parse_event_datetime(item)
            upcoming.append(
                {
                    "title": item.get("summary") or "Sem titulo",
                    "when": start_dt.strftime("%d/%m %H:%M") if start_dt else "",
                    "location": item.get("location") or "",
                    "event_id": event_map.get(item.get("id")),
                }
            )

        # todo list
        pending_casting = (
            EventRole.query.filter(EventRole.talent_id.is_(None))
            .join(CalendarEvent)
            .order_by(CalendarEvent.start_at.asc())
            .all()
        )

        pending_figurino = (
            EventRole.query.join(CalendarEvent)
            .order_by(CalendarEvent.start_at.asc())
            .limit(10)
            .all()
        )

        role_view = request.args.get("role_view")
        if role_view and not any(r.name == "SUPERADMIN" for r in current_user.roles):
            role_view = None

        def has_role(name: str) -> bool:
            return any(r.name.upper() == name.upper() for r in current_user.roles)

        is_superadmin = has_role("SUPERADMIN")

        if role_view == "casting":
            show_casting = True
            show_figurino = False
        elif role_view == "figurino":
            show_casting = False
            show_figurino = True
        elif role_view == "todos":
            show_casting = True
            show_figurino = True
        else:
            show_casting = has_role("CASTING") or is_superadmin
            show_figurino = has_role("FIGURINO") or is_superadmin

        return render_template(
            "home.html",
            month_events=items,
            days_with_events=sorted(days_with_events),
            events_by_day=events_by_day,
            month_weeks=weeks,
            upcoming_events=upcoming,
            pending_casting=pending_casting,
            pending_figurino=pending_figurino,
            role_view=role_view,
            show_casting=show_casting,
            show_figurino=show_figurino,
            is_superadmin=is_superadmin,
            month_label=now.strftime("%B %Y"),
        )

    @app.route("/figurinos")
    @login_required
    def figurinos():
        return render_template("figurinos.html")

    return app
