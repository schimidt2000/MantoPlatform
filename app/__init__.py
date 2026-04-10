import os
from flask import Flask, render_template, request, send_from_directory, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, not_, func
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_login import login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta, date
from .config import Config  # se seu config.py está na raiz
from .constants import RoleName

from .email_service import mail

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = None  # suprime mensagem automática de "faça login"
limiter = Limiter(key_func=get_remote_address, default_limits=[])

def _start_talent_sync(app):
    """Inicia thread de background que importa novos talentos da planilha a cada 5 minutos."""
    import threading
    import os as _os

    # Evita duplicar a thread no modo debug (Werkzeug spawna 2 processos)
    if _os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        return

    credentials_path = _os.path.abspath(
        _os.path.join("instance", "credentials", "sheets_service_account.json")
    )
    if not _os.path.exists(credentials_path):
        return  # sem credenciais, não inicia

    SPREADSHEET_ID = app.config.get("TALENTS_SPREADSHEET_ID", "")
    SHEET_NAME     = app.config.get("TALENTS_SHEET_NAME", "Respostas")
    INTERVAL       = 5 * 60  # segundos

    if not SPREADSHEET_ID:
        app.logger.warning("[talent-sync] TALENTS_SPREADSHEET_ID não configurado — sync desativado")
        return

    def _sync_loop():
        import time
        # Aguarda o app estar pronto antes da primeira execução
        time.sleep(10)
        while True:
            try:
                from app.talents.importer import import_new_talents_from_sheet
                with app.app_context():
                    result = import_new_talents_from_sheet(
                        spreadsheet_id=SPREADSHEET_ID,
                        sheet_name=SHEET_NAME,
                        credentials_path=credentials_path,
                    )
                    if result.get("imported", 0) > 0:
                        app.logger.info(
                            f"[talent-sync] {result['imported']} novo(s) talento(s) importado(s)"
                        )
            except Exception as exc:
                app.logger.warning(f"[talent-sync] erro: {exc}")
            time.sleep(INTERVAL)

    t = threading.Thread(target=_sync_loop, daemon=True, name="talent-sync")
    t.start()
    app.logger.info("[talent-sync] thread iniciada (intervalo: 5 min)")


def create_app():
    from urllib.parse import quote as _url_quote
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.filters['urlencode'] = _url_quote

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
    mail.init_app(app)
    limiter.init_app(app)

    @app.context_processor
    def inject_settings():
        from app.models import SiteSetting
        return {"settings": SiteSetting.query.get(1)}

    @app.context_processor
    def inject_roles():
        def is_real_superadmin() -> bool:
            return current_user.is_authenticated and any(
                r.name == RoleName.SUPERADMIN for r in current_user.roles
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
    from .talent_portal.routes import portal_bp
    from .crm.routes import crm_bp
    from .orcamento.routes import orcamento_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(rh_bp, url_prefix="/rh")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(calendar_bp)
    app.register_blueprint(talents_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(figurino_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(orcamento_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"500 error: {e}")
        return render_template("500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("404.html"), 403

    @app.route("/")
    @login_required
    def home():
        from app.models import CalendarEvent, EventRole

        # to-do list — filtra a partir do release_date (ou hoje se não configurado)
        from app.models import SiteSetting
        _settings = SiteSetting.query.get(1)
        _release = _settings.release_date if _settings and _settings.release_date else date.today()
        task_cutoff = datetime(_release.year, _release.month, _release.day)

        exclude_ensaios = not_(CalendarEvent.title.like("🟧 ENSAIO%"))
        future_events = CalendarEvent.start_at >= task_cutoff

        pending_casting = (
            EventRole.query.filter(EventRole.talent_id.is_(None))
            .join(CalendarEvent)
            .filter(exclude_ensaios, future_events)
            .order_by(CalendarEvent.start_at.asc())
            .all()
        )

        total_casting = EventRole.query.join(CalendarEvent).filter(exclude_ensaios, future_events).count()
        done_casting = total_casting - len(pending_casting)

        # Figurino: roles COM talento atribuído mas SEM figurino confirmado
        pending_figurino = (
            EventRole.query.filter(
                EventRole.talent_id.isnot(None),
                EventRole.figurino_done_at.is_(None),
            )
            .join(CalendarEvent)
            .filter(exclude_ensaios, future_events)
            .order_by(CalendarEvent.start_at.asc())
            .all()
        )
        total_figurino = (
            EventRole.query.filter(EventRole.talent_id.isnot(None))
            .join(CalendarEvent)
            .filter(exclude_ensaios, future_events)
            .count()
        )
        done_figurino = total_figurino - len(pending_figurino)

        _is_real_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)
        _impersonate = session.get("impersonate_role") if _is_real_superadmin else None

        def has_role(name: str) -> bool:
            if _impersonate:
                return _impersonate.upper() == name.upper()
            return any(r.name.upper() == name.upper() for r in current_user.roles)

        is_superadmin = _is_real_superadmin and not _impersonate

        show_casting = has_role(RoleName.CASTING) or is_superadmin
        show_figurino = has_role(RoleName.FIGURINO) or is_superadmin
        show_ensaio = has_role(RoleName.ENSAIO) or is_superadmin

        # Ensaio: eventos que precisam de ensaio mas ainda não têm nenhum agendado
        pending_ensaio = []
        if show_ensaio:
            future_shows = (
                CalendarEvent.query
                .filter(
                    CalendarEvent.needs_rehearsal == True,
                    CalendarEvent.start_at >= datetime.utcnow(),
                )
                .order_by(CalendarEvent.start_at.asc())
                .all()
            )
            pending_ensaio = [e for e in future_shows if not e.ensaios]

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
            today=date.today(),
            pending_casting=pending_casting,
            pending_figurino=pending_figurino,
            pending_ensaio=pending_ensaio,
            show_casting=show_casting,
            show_figurino=show_figurino,
            show_ensaio=show_ensaio,
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

    # ── Auto-import de talentos da planilha ────────────────────────
    _start_talent_sync(app)

    @app.route("/uploads/<path:filename>")
    @login_required
    def uploaded_file(filename: str):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # ── Impersonação de role (somente SUPERADMIN) ──────────────────
    _IMPERSONABLE_ROLES = [
        RoleName.CASTING, RoleName.FIGURINO, RoleName.COMERCIAL,
        RoleName.FINANCEIRO, RoleName.ENSAIO,
    ]

    @app.route("/impersonate/<role_name>", methods=["POST"])
    @login_required
    def impersonate_role(role_name: str):
        if not any(r.name == RoleName.SUPERADMIN for r in current_user.roles):
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

    @app.route("/health")
    def health():
        return "ok", 200

    return app
