import os
from flask import Flask, render_template, request, send_from_directory, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, not_, func
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from .config import Config  # se seu config.py está na raiz

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = None  # suprime mensagem automática de "faça login"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Absolute paths for uploads (avoids CWD resolution issues)
    _instance = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance'))
    app.config.setdefault("UPLOAD_FOLDER",          os.path.join(_instance, "uploads"))
    app.config.setdefault("UPLOAD_CONTRACTS",        os.path.join(_instance, "uploads", "contracts"))
    app.config.setdefault("UPLOAD_PAYMENTS",         os.path.join(_instance, "uploads", "payments"))
    app.config.setdefault("UPLOAD_FIGURINO_THUMBS",  os.path.join(_instance, "uploads", "figurino_thumbs"))
    app.config.setdefault("UPLOAD_FIGURINO_PHOTOS",  os.path.join(_instance, "uploads", "figurino_photos"))
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_CONTRACTS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_PAYMENTS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FIGURINO_THUMBS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FIGURINO_PHOTOS"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @app.context_processor
    def inject_settings():
        from app.models import SiteSetting
        return {"settings": SiteSetting.query.get(1)}

    @app.context_processor
    def inject_roles():
        def is_real_superadmin() -> bool:
            return current_user.is_authenticated and any(
                r.name == "SUPERADMIN" for r in current_user.roles
            )

        def eff_has_role(*names) -> bool:
            if not current_user.is_authenticated:
                return False
            impersonate = session.get("impersonate_role")
            if impersonate and is_real_superadmin():
                return any(n.upper() == impersonate.upper() for n in names)
            return any(
                r.name.upper() in [n.upper() for n in names]
                for r in current_user.roles
            )

        view_as_role = (
            session.get("impersonate_role")
            if current_user.is_authenticated and is_real_superadmin()
            else None
        )

        return dict(
            eff_has_role=eff_has_role,
            is_real_superadmin=is_real_superadmin,
            view_as_role=view_as_role,
        )

    # ✅ Importa blueprints AQUI (depois do db existir)
    from .auth.routes import auth_bp
    from .rh.routes import rh_bp
    from .admin.routes import admin_bp
    from .calendar.routes import calendar_bp
    from .talents.routes import talents_bp
    from .tools.routes import tools_bp
    from .financeiro.routes import financeiro_bp
    from .figurino.routes import figurino_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(rh_bp, url_prefix="/rh")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(calendar_bp)
    app.register_blueprint(talents_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(figurino_bp)
    print(app.url_map)
    @app.route("/")
    @login_required
    def home():
        from app.models import CalendarEvent, EventRole

        # to-do list (somente eventos ja sincronizados pela agenda)
        exclude_ensaios = not_(CalendarEvent.title.like("🟧 ENSAIO%"))
        pending_casting = (
            EventRole.query.filter(EventRole.talent_id.is_(None))
            .join(CalendarEvent)
            .filter(exclude_ensaios)
            .order_by(CalendarEvent.start_at.asc())
            .all()
        )

        total_casting = EventRole.query.join(CalendarEvent).filter(exclude_ensaios).count()
        done_casting = total_casting - len(pending_casting)

        # Figurino: por enquanto consideramos concluido quando o casting ja escolheu o talento
        pending_figurino = (
            EventRole.query.filter(EventRole.talent_id.is_(None))
            .join(CalendarEvent)
            .filter(exclude_ensaios)
            .order_by(CalendarEvent.start_at.asc())
            .all()
        )
        total_figurino = total_casting
        done_figurino = total_figurino - len(pending_figurino)

        _is_real_superadmin = any(r.name == "SUPERADMIN" for r in current_user.roles)
        _impersonate = session.get("impersonate_role") if _is_real_superadmin else None

        def has_role(name: str) -> bool:
            if _impersonate:
                return _impersonate.upper() == name.upper()
            return any(r.name.upper() == name.upper() for r in current_user.roles)

        is_superadmin = _is_real_superadmin and not _impersonate

        show_casting = has_role("CASTING") or is_superadmin
        show_figurino = has_role("FIGURINO") or is_superadmin

        perf_range = request.args.get("perf_range", "7")
        perf_start = request.args.get("perf_start")
        perf_end = request.args.get("perf_end")

        start_dt = None
        end_dt = None
        if perf_range == "30":
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=30)
        elif perf_range == "custom" and perf_start and perf_end:
            try:
                start_dt = datetime.fromisoformat(perf_start)
                end_dt = datetime.fromisoformat(perf_end) + timedelta(days=1)
            except ValueError:
                start_dt = None
                end_dt = None
        else:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=7)

        perf_casting_total = 0
        perf_casting_done = 0
        perf_figurino_total = 0
        perf_figurino_done = 0
        perf_money = 0
        if is_superadmin and start_dt and end_dt:
            perf_filter = and_(CalendarEvent.start_at >= start_dt, CalendarEvent.start_at < end_dt, exclude_ensaios)
            perf_casting_total = (
                EventRole.query.join(CalendarEvent).filter(perf_filter).count()
            )
            perf_casting_done = (
                EventRole.query.filter(EventRole.assigned_at.isnot(None))
                .join(CalendarEvent)
                .filter(perf_filter)
                .count()
            )
            perf_figurino_total = perf_casting_total
            perf_figurino_done = (
                EventRole.query.filter(EventRole.figurino_done_at.isnot(None))
                .join(CalendarEvent)
                .filter(perf_filter)
                .count()
            )
            perf_money = (
                db.session.query(func.coalesce(func.sum(EventRole.cache_value), 0))
                .join(CalendarEvent)
                .filter(perf_filter, EventRole.assigned_at.isnot(None))
                .scalar()
            )

        return render_template(
            "home.html",
            pending_casting=pending_casting,
            pending_figurino=pending_figurino,
            show_casting=show_casting,
            show_figurino=show_figurino,
            is_superadmin=is_superadmin,
            total_casting=total_casting,
            done_casting=done_casting,
            total_figurino=total_figurino,
            done_figurino=done_figurino,
            perf_range=perf_range,
            perf_start=perf_start,
            perf_end=perf_end,
            perf_casting_total=perf_casting_total,
            perf_casting_done=perf_casting_done,
            perf_figurino_total=perf_figurino_total,
            perf_figurino_done=perf_figurino_done,
            perf_money=perf_money,
        )

    @app.route("/uploads/<path:filename>")
    @login_required
    def uploaded_file(filename: str):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # ── Impersonação de role (somente SUPERADMIN) ──────────────────
    _IMPERSONABLE_ROLES = ["CASTING", "FIGURINO", "COMERCIAL", "RH", "FINANCEIRO", "VENDAS"]

    @app.route("/impersonate/<role_name>", methods=["POST"])
    @login_required
    def impersonate_role(role_name: str):
        if not any(r.name == "SUPERADMIN" for r in current_user.roles):
            return "", 403
        if role_name.upper() not in _IMPERSONABLE_ROLES:
            return "", 400
        session["impersonate_role"] = role_name.upper()
        return redirect(request.referrer or "/")

    @app.route("/impersonate/reset", methods=["POST"])
    @login_required
    def impersonate_reset():
        session.pop("impersonate_role", None)
        return redirect(request.referrer or "/")

    return app
