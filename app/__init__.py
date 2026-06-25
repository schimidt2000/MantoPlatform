import os
from flask import Flask, render_template, request, send_from_directory, session, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, not_, or_, func
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


def _is_revendedor_only(user) -> bool:
    """True se o usuário tem APENAS o perfil Revendedor EducaManto (feature 078).

    Multi-perfil (revendedor + outro) NÃO é restrito — preserva os acessos dos demais perfis.
    Usa os papéis reais (não a impersonação), por ser controle de acesso.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    names = {r.name.upper() for r in user.roles}
    return names == {RoleName.REVENDEDOR_EDUCAMANTO}


# Páginas que o Revendedor EducaManto pode acessar (prefixos). O resto é redirecionado à agenda.
_REVENDEDOR_ALLOWED = ("/agenda", "/events/", "/educamanto", "/auth", "/uploads", "/static", "/health")


def _safe_next(value, default="/"):
    """Retorna ``value`` apenas se for um destino interno seguro; senão, ``default`` (feature 074).

    Bloqueia open redirect: aceita caminho relativo interno (``/algo``) ou URL absoluta do **mesmo
    host**; rejeita esquemas/hosts externos (``http://evil``, ``//evil``).
    """
    from urllib.parse import urlparse
    if not value:
        return default
    parsed = urlparse(value)
    if not parsed.scheme and not parsed.netloc:
        # caminho relativo: precisa começar com '/' e não ser protocol-relative ('//')
        if value.startswith("/") and not value.startswith("//"):
            return value
        return default
    # URL absoluta: só aceita o mesmo host da requisição atual
    try:
        if parsed.netloc == request.host:
            return (parsed.path or "/") + (("?" + parsed.query) if parsed.query else "")
    except RuntimeError:
        pass  # fora de contexto de requisição
    return default

def _start_talent_sync(app):
    """Inicia thread de background que importa novos talentos da planilha periodicamente."""
    import threading
    import os as _os

    # Em modo debug o Werkzeug roda 2 processos: o reloader (pai) e o worker (filho).
    # WERKZEUG_RUN_MAIN="true" só existe no filho. Iniciamos a thread apenas lá.
    # Em produção (gunicorn) a variável nunca é definida, então passa direto.
    flask_env = _os.environ.get("FLASK_ENV", "")
    if flask_env == "development" and _os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    credentials_path = _os.path.abspath(
        _os.path.join("instance", "credentials", "sheets_service_account.json")
    )
    if not _os.path.exists(credentials_path):
        app.logger.info("[talent-sync] credenciais não encontradas — sync desativado")
        return

    SPREADSHEET_ID = app.config.get("TALENTS_SPREADSHEET_ID", "")
    SHEET_NAME     = app.config.get("TALENTS_SHEET_NAME", "Respostas")
    INTERVAL       = app.config.get("TALENTS_SYNC_INTERVAL", 900)

    if not SPREADSHEET_ID:
        app.logger.warning("[talent-sync] TALENTS_SPREADSHEET_ID não configurado — sync desativado")
        return

    def _sync_loop():
        import time
        from datetime import datetime as _dt
        time.sleep(15)  # aguarda o app estar pronto
        while True:
            try:
                from app.talents.importer import import_new_talents_from_sheet
                with app.app_context():
                    result = import_new_talents_from_sheet(
                        spreadsheet_id=SPREADSHEET_ID,
                        sheet_name=SHEET_NAME,
                        credentials_path=credentials_path,
                    )
                    imported = result.get("imported", 0)
                    # Registra o resultado no banco para exibir na UI
                    from app.models import ImportState
                    state = ImportState.query.filter_by(key="talents_form").first()
                    if state:
                        state.last_checked_at = _dt.utcnow()
                        state.last_import_count = imported
                        db.session.commit()
                    if imported > 0:
                        app.logger.info(f"[talent-sync] {imported} novo(s) talento(s) importado(s)")
                    else:
                        app.logger.debug("[talent-sync] nenhum talento novo")
            except Exception as exc:
                app.logger.warning(f"[talent-sync] erro: {exc}")
            time.sleep(INTERVAL)

    t = threading.Thread(target=_sync_loop, daemon=True, name="talent-sync")
    t.start()
    app.logger.info(f"[talent-sync] thread iniciada (intervalo: {INTERVAL}s)")


def _start_calendar_sync(app):
    """Inicia thread de background que sincroniza a agenda com o Google Calendar.

    Substitui a dependência de um serviço Cron externo: roda dentro do próprio app,
    em intervalos regulares, com a mesma lógica do botão "Sincronizar agora".
    Um claim atômico no banco garante execução única entre os workers do gunicorn.
    """
    import threading
    import os as _os

    # Mesma guarda de dev do talent-sync: em modo debug, só roda no processo filho.
    flask_env = _os.environ.get("FLASK_ENV", "")
    if flask_env == "development" and _os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    INTERVAL = app.config.get("CALENDAR_SYNC_INTERVAL", 600)

    def _sync_loop():
        import time
        time.sleep(15)  # aguarda o app estar pronto
        from app.calendar.sync import run_calendar_sync, _claim_auto_sync
        while True:
            try:
                with app.app_context():
                    if _claim_auto_sync(INTERVAL):
                        result = run_calendar_sync()
                        if result["errors"]:
                            app.logger.warning(
                                f"[calendar-sync] ciclo com {result['errors']} erro(s)"
                            )
                        else:
                            app.logger.debug(
                                f"[calendar-sync] {result['months']} mês(es) sincronizado(s)"
                            )
            except Exception as exc:  # noqa: BLE001 — nunca deixar a thread morrer
                app.logger.warning(f"[calendar-sync] erro: {exc}")
            time.sleep(INTERVAL)

    t = threading.Thread(target=_sync_loop, daemon=True, name="calendar-sync")
    t.start()
    app.logger.info(f"[calendar-sync] thread iniciada (intervalo: {INTERVAL}s)")


def create_app():
    from urllib.parse import quote as _url_quote
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.filters['urlencode'] = _url_quote

    from app.money import format_brl
    app.jinja_env.filters['brl'] = format_brl

    # Absolute paths for uploads (avoids CWD resolution issues)
    _instance = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance'))
    app.config.setdefault("UPLOAD_FOLDER",          os.path.join(_instance, "uploads"))
    app.config.setdefault("UPLOAD_CONTRACTS",        os.path.join(_instance, "uploads", "contracts"))
    app.config.setdefault("UPLOAD_PAYMENTS",         os.path.join(_instance, "uploads", "payments"))
    app.config.setdefault("UPLOAD_INVOICES",         os.path.join(_instance, "uploads", "invoices"))
    app.config.setdefault("UPLOAD_FIGURINO_THUMBS",  os.path.join(_instance, "uploads", "figurino_thumbs"))
    app.config.setdefault("UPLOAD_FIGURINO_PHOTOS",  os.path.join(_instance, "uploads", "figurino_photos"))
    app.config.setdefault("UPLOAD_EVENT_OBS",         os.path.join(_instance, "uploads", "event_obs"))
    app.config.setdefault("UPLOAD_EXPENSES",          os.path.join(_instance, "uploads", "expenses"))
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_CONTRACTS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_PAYMENTS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_INVOICES"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FIGURINO_THUMBS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FIGURINO_PHOTOS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_EVENT_OBS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_EXPENSES"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # ── Segurança: cabeçalhos em todas as respostas (feature 074) ──────────────
    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        # CSP mínima: protege clickjacking, base-tag e hijack de <form> sem restringir
        # script/style/img/font/frame-src (não quebra inline nem integrações externas).
        resp.headers.setdefault(
            "Content-Security-Policy",
            "object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'",
        )
        # HSTS só sob HTTPS (atrás do proxy do Railway, confere X-Forwarded-Proto).
        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return resp

    # ── Acesso restrito do Revendedor EducaManto (feature 078) ────────────────
    @app.before_request
    def _revendedor_guard():
        if not _is_revendedor_only(current_user):
            return None
        path = request.path
        if path == "/":
            return redirect("/agenda")
        if any(path == p or path.startswith(p) for p in _REVENDEDOR_ALLOWED):
            return None
        return redirect("/agenda")

    @app.context_processor
    def inject_revendedor_flag():
        return {"is_revendedor_only": _is_revendedor_only(current_user)}

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

    PORTAL_HOSTS = {"portal.mantoproducoes.com.br"}

    @app.before_request
    def portal_domain_routing():
        host = request.host.split(":")[0]
        if host in PORTAL_HOSTS:
            if not request.path.startswith(("/portal", "/cadastro", "/static", "/uploads")):
                return redirect("/portal/")

    # ✅ Importa blueprints AQUI (depois do db existir)
    from .auth.routes import auth_bp
    from .rh.routes import rh_bp
    from .admin.routes import admin_bp
    from .calendar.routes import calendar_bp
    from .talents.routes import talents_bp
    from .financeiro.routes import financeiro_bp
    from .figurino.routes import figurino_bp
    from .talent_portal.routes import portal_bp
    from .orcamento.routes import orcamento_bp
    from .educamanto.routes import educamanto_bp
    from .gastos.routes import gastos_bp
    from .cadastro.routes import cadastro_bp
    from .revisao.routes import revisao_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(rh_bp, url_prefix="/rh")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(calendar_bp)
    app.register_blueprint(talents_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(figurino_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(orcamento_bp)
    app.register_blueprint(educamanto_bp)
    app.register_blueprint(gastos_bp)
    app.register_blueprint(cadastro_bp)
    app.register_blueprint(revisao_bp)

    def _wa_link(code: int) -> str:
        from zoneinfo import ZoneInfo
        import urllib.parse
        now = datetime.now(tz=ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
        url = request.url
        msg = (
            f"🚨 *Erro na Manto Platform*\n"
            f"• Código: {code}\n"
            f"• Página: {url}\n"
            f"• Horário: {now} (SP)"
        )
        number = os.getenv("SUPPORT_WHATSAPP", "")
        return f"https://wa.me/{number}?text={urllib.parse.quote(msg)}" if number else ""

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html", wa_link=_wa_link(404)), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"500 error: {e}")
        return render_template("500.html", wa_link=_wa_link(500)), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html", wa_link=_wa_link(403)), 403

    @app.route("/")
    @login_required
    def home():
        from app.models import CalendarEvent, EventRole

        # to-do list — filtra a partir do release_date (ou hoje se não configurado)
        from app.models import SiteSetting
        _settings = SiteSetting.query.get(1)
        _release = _settings.release_date if _settings and _settings.release_date else date.today()
        task_cutoff = datetime(_release.year, _release.month, _release.day)

        from app.calendar.routes import PRESENCE_CHARACTER
        not_presence = EventRole.character_name != PRESENCE_CHARACTER

        exclude_ensaios = not_(CalendarEvent.title.like("🟧 ENSAIO%"))
        future_events = CalendarEvent.start_at >= task_cutoff

        # Presença (técnico de som que vai ao evento) é tarefa do ensaio — fora do casting.
        pending_casting = (
            EventRole.query.filter(EventRole.talent_id.is_(None), not_presence)
            .join(CalendarEvent)
            .filter(exclude_ensaios, future_events)
            .order_by(CalendarEvent.start_at.asc())
            .all()
        )

        rejected_invites = (
            EventRole.query.filter(EventRole.invite_status == "rejected")
            .join(CalendarEvent)
            .filter(exclude_ensaios, future_events)
            .order_by(CalendarEvent.start_at.asc())
            .all()
        )

        total_casting = (
            EventRole.query.filter(not_presence)
            .join(CalendarEvent).filter(exclude_ensaios, future_events).count()
        )
        done_casting = (
            EventRole.query
            .filter(EventRole.talent_id.isnot(None), EventRole.invite_status != "rejected", not_presence)
            .join(CalendarEvent)
            .filter(exclude_ensaios, future_events)
            .count()
        )

        # Figurino: roles COM talento atribuído, SEM figurino, excluindo rejeitados e equipe técnica
        pending_figurino = (
            EventRole.query.filter(
                EventRole.talent_id.isnot(None),
                EventRole.figurino_done_at.is_(None),
                EventRole.invite_status != "rejected",
                EventRole.role_type != "extra",
            )
            .join(CalendarEvent)
            .filter(exclude_ensaios, future_events)
            .order_by(CalendarEvent.start_at.asc())
            .all()
        )
        total_figurino = (
            EventRole.query.filter(
                EventRole.talent_id.isnot(None),
                EventRole.invite_status != "rejected",
                EventRole.role_type != "extra",
            )
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

        # Ensaio: separa pendentes (sem ensaio) de agendados (com ensaio)
        pending_ensaio   = []
        scheduled_ensaio = []
        orphan_ensaios   = []
        pending_presence = []
        if show_ensaio:
            future_shows = (
                CalendarEvent.query
                .filter(
                    db.or_(
                        CalendarEvent.needs_rehearsal == True,
                        CalendarEvent.event_type == "SHOW",
                    ),
                    CalendarEvent.event_type != "ENSAIO",
                    CalendarEvent.start_at >= datetime.utcnow(),
                )
                .order_by(CalendarEvent.start_at.asc())
                .all()
            )
            pending_ensaio   = [e for e in future_shows if not e.ensaios]
            scheduled_ensaio = [e for e in future_shows if e.ensaios]

            # Ensaios órfãos: do tipo ENSAIO cujo show pai não existe mais (feature 057).
            # parent is None cobre FK nulo e FK apontando para show já removido.
            # Conta apenas a partir da data de início do sistema (mesmo corte das demais
            # tarefas) para não poluir a home com órfãos antigos (feature 060).
            orphan_ensaios = [
                e for e in CalendarEvent.query
                .filter(CalendarEvent.event_type == "ENSAIO",
                        CalendarEvent.start_at >= task_cutoff)
                .order_by(CalendarEvent.start_at.asc())
                .all()
                if e.parent is None
            ]

            # Presença pendente: shows futuros sem o técnico de presença definido.
            pending_presence = (
                EventRole.query
                .filter(EventRole.talent_id.is_(None),
                        EventRole.character_name == PRESENCE_CHARACTER)
                .join(CalendarEvent)
                .filter(exclude_ensaios, CalendarEvent.start_at >= datetime.utcnow())
                .order_by(CalendarEvent.start_at.asc())
                .all()
            )

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

        # ── Comercial: cobranças pendentes ──────────────────────────
        # Política: à vista, ou 50% no ato + 50% até 2 dias antes do evento.
        # 'futuro'/'faturado' têm data combinada própria (payment_due_date).
        show_comercial = (
            has_role(RoleName.COMERCIAL) or has_role(RoleName.FINANCEIRO) or is_superadmin
        )
        pending_payments = []
        if show_comercial:
            from zoneinfo import ZoneInfo

            from app.models import EventPayment
            today_sp = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
            sale_events = (
                CalendarEvent.query
                .filter(
                    CalendarEvent.sale_value.isnot(None),
                    CalendarEvent.sale_value > 0,
                    CalendarEvent.start_at >= task_cutoff,
                    exclude_ensaios,
                )
                .order_by(CalendarEvent.start_at.asc())
                .all()
            )
            received_by_event = dict(
                db.session.query(
                    EventPayment.event_id,
                    func.coalesce(func.sum(EventPayment.amount), 0),
                )
                .filter(EventPayment.event_id.in_([e.id for e in sale_events] or [0]))
                .group_by(EventPayment.event_id)
                .all()
            )
            for ev in sale_events:
                sale = float(ev.sale_value)
                received = float(received_by_event.get(ev.id, 0))
                saldo = sale - received
                if saldo <= 0:
                    continue
                ev_date = ev.start_at.date() if ev.start_at else None
                is_past = bool(ev_date and ev_date < today_sp)
                due_date = None
                if ev.payment_method in ("futuro", "faturado") and ev.payment_due_date:
                    due_date = ev.payment_due_date
                    severity = "vencido" if due_date <= today_sp else "info"
                elif is_past:
                    # Evento já aconteceu e segue com saldo em aberto.
                    severity = "atrasado"
                else:
                    days_left = (ev_date - today_sp).days if ev_date else None
                    if days_left is not None and days_left <= 2:
                        severity = "urgent"
                    elif received < sale * 0.5:
                        severity = "warn"
                    else:
                        continue  # ≥50% recebido e falta >2 dias: dentro da política
                pending_payments.append({
                    "event": ev,
                    "sale": sale,
                    "received": received,
                    "saldo": saldo,
                    "severity": severity,
                    "due_date": due_date,
                    "is_past": is_past,
                })
            _SEVERITY_ORDER = {"atrasado": 0, "vencido": 1, "urgent": 2, "warn": 3, "info": 4}
            pending_payments.sort(
                key=lambda p: (
                    _SEVERITY_ORDER[p["severity"]],
                    p["event"].start_at or datetime.max,
                )
            )

        events_sem_valor: list = []
        if show_comercial:
            events_sem_valor = (
                CalendarEvent.query
                .filter(
                    or_(CalendarEvent.sale_value.is_(None), CalendarEvent.sale_value == 0),
                    CalendarEvent.start_at >= task_cutoff,
                    CalendarEvent.group_leader_id.is_(None),  # satélite herda do principal (055)
                    CalendarEvent.is_cortesia_permuta.is_(False),  # permuta/cortesia não é "sem valor"
                    exclude_ensaios,
                )
                .order_by(CalendarEvent.start_at.asc())
                .all()
            )

        # Nota fiscal pendente: eventos com nota(s) "a emitir" (feature 069)
        pending_invoice = []
        if is_superadmin:
            from app.models import EventInvoice
            pending_invoice = (
                CalendarEvent.query
                .join(EventInvoice, EventInvoice.event_id == CalendarEvent.id)
                .filter(
                    EventInvoice.status == "a_emitir",
                    CalendarEvent.start_at >= task_cutoff,
                )
                .order_by(CalendarEvent.start_at.asc())
                .distinct()
                .all()
            )

        return render_template(
            "home.html",
            today=date.today(),
            pending_casting=pending_casting,
            rejected_invites=rejected_invites,
            pending_figurino=pending_figurino,
            pending_ensaio=pending_ensaio,
            scheduled_ensaio=scheduled_ensaio,
            orphan_ensaios=orphan_ensaios,
            pending_presence=pending_presence,
            pending_invoice=pending_invoice,
            show_comercial=show_comercial,
            events_sem_valor=events_sem_valor,
            pending_payments=pending_payments,
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

    # ── Sincronização automática da agenda (cron interno) ──────────
    _start_calendar_sync(app)

    # ── Comandos CLI de manutenção ─────────────────────────────────
    from app.cli import register_commands
    register_commands(app)

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
        return redirect(_safe_next(request.referrer, "/"))

    @app.route("/impersonate/reset", methods=["POST"])
    @login_required
    def impersonate_reset():
        session.pop("impersonate_role", None)
        return redirect(_safe_next(request.referrer, "/"))

    @app.route("/health")
    def health():
        return "ok", 200

    return app
