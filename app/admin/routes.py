import os
from collections import defaultdict
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import User, SiteSetting, Role, EventLog, CalendarEvent, AuditLog, SalaryHistory
from app.constants import RoleName
from app.money import parse_brl_int

admin_bp = Blueprint("admin", __name__)


def _is_superadmin() -> bool:
    return any(r.name == RoleName.SUPERADMIN for r in current_user.roles)


def require_superadmin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _is_superadmin():
            return {"ok": False, "error": "Acesso apenas para SuperAdmin"}, 403
        return fn(*args, **kwargs)
    return wrapper


def require_users_access(fn):
    """Acesso à seção de Usuários: SUPERADMIN (tudo) ou FINANCEIRO (PIX + salário)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        roles = {r.name.upper() for r in current_user.roles}
        if not ({RoleName.SUPERADMIN, RoleName.FINANCEIRO} & roles):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def get_settings():
    return SiteSetting.query.get(1)


@admin_bp.route("/", methods=["GET"])
@login_required
@require_superadmin
def admin_home():
    return render_template(
        "admin_dashboard.html",
        settings=get_settings(),
        active="home",
        title="Admin - Painel",
    )


@admin_bp.route("/users", methods=["GET"])
@login_required
@require_users_access
def list_users():
    users = User.query.order_by(User.id.asc()).all()
    salaries = {
        s.user_id: s for s in SalaryHistory.query.filter_by(end_date=None).all()
    }
    users_data = [{"user": u, "salary": salaries.get(u.id)} for u in users]
    return render_template(
        "admin_users.html",
        users_data=users_data,
        is_superadmin=_is_superadmin(),
        settings=get_settings(),
        active="users",
        title="Admin - Usuários",
    )


@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
@require_superadmin
def create_user():
    if request.method == "GET":
        return render_template(
            "admin_create_user.html",
            settings=get_settings(),
            active="users",
            title="Admin - Criar Usuário",
            roles=Role.query.order_by(Role.name.asc()).all(),
        )

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    temp_password = request.form.get("temp_password", "")

    if not name or not email or not temp_password:
        return render_template(
            "admin_create_user.html",
            error="Preencha tudo.",
            settings=get_settings(),
            active="users",
            title="Admin - Criar Usuario",
        )

    if User.query.filter_by(email=email).first():
        return render_template(
            "admin_create_user.html",
            error="Esse email já existe.",
            settings=get_settings(),
            active="users",
            title="Admin - Criar Usuario",
        )

    user = User(email=email, name=name, is_active=True, must_change_password=True)
    user.set_password(temp_password)
    role_ids = [int(r) for r in request.form.getlist("roles")]
    if role_ids:
        user.roles = Role.query.filter(Role.id.in_(role_ids)).all()

    # (Importante) Não damos role nenhuma automaticamente.
    db.session.add(user)
    from app.utils import audit
    audit("create", "user", None, user.name, f"Usuário criado: {user.email}")
    db.session.commit()

    return render_template(
        "admin_create_user.html",
        msg="Usuário criado com sucesso!",
        settings=get_settings(),
        active="users",
        title="Admin - Criar Usuario",
        roles=Role.query.order_by(Role.name.asc()).all(),
    )


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@require_users_access
def edit_user(user_id: int):
    """Página unificada do usuário. Identidade/papéis = superadmin; PIX/salário = também financeiro."""
    user = User.query.get_or_404(user_id)

    def _render(error=None):
        return render_template(
            "admin_user_edit.html",
            user=user,
            error=error,
            is_superadmin=_is_superadmin(),
            history=user.salary_histories.order_by(SalaryHistory.start_date.desc()).all(),
            settings=get_settings(),
            active="users",
            title="Admin - Editar Usuário",
            roles=Role.query.order_by(Role.name.asc()).all(),
        )

    if request.method == "POST":
        # Edição de identidade/papéis é exclusiva do Superadmin (PIX e salário têm rotas próprias).
        if not _is_superadmin():
            abort(403)
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        is_active = request.form.get("is_active") == "1"
        role_ids = [int(r) for r in request.form.getlist("roles")]

        if not name or not email:
            return _render(error="Preencha tudo.")
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            return _render(error="Esse email já existe.")

        user.name = name
        user.email = email
        user.is_active = is_active
        user.receives_commission = request.form.get("receives_commission") == "1"
        user.roles = Role.query.filter(Role.id.in_(role_ids)).all() if role_ids else []
        from app.utils import audit
        audit("edit", "user", user.id, user.name, f"Usuário editado: {user.email}")
        db.session.commit()
        flash("Dados do usuário atualizados.", "success")
        return redirect(url_for("admin.edit_user", user_id=user.id))

    return _render()


@admin_bp.route("/users/<int:user_id>/pix", methods=["POST"])
@login_required
@require_users_access
def update_pix(user_id: int):
    """Atualiza dados de pagamento (PIX). Superadmin ou Financeiro."""
    user = User.query.get_or_404(user_id)
    user.pix_key = request.form.get("pix_key", "").strip() or None
    user.pix_key_type = request.form.get("pix_key_type", "").strip() or None
    from app.utils import audit
    audit("edit", "user", user.id, user.name, "PIX atualizado")
    db.session.commit()
    flash("Dados de PIX atualizados.", "success")
    return redirect(url_for("admin.edit_user", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/salario", methods=["POST"])
@login_required
@require_users_access
def add_salary(user_id: int):
    """Registra novo salário (encerra o vigente). Superadmin ou Financeiro."""
    user = User.query.get_or_404(user_id)
    salary_raw = request.form.get("salary", "").strip()
    payment_type = request.form.get("payment_type", "").strip()
    start_str = request.form.get("start_date", "").strip()
    notes = request.form.get("notes", "").strip()

    salary_value = parse_brl_int(salary_raw)

    errors = []
    if salary_value is None or salary_value <= 0:
        errors.append("Salário inválido.")
    if payment_type not in ("semanal", "quinzenal", "comissao"):
        errors.append("Tipo de pagamento inválido.")
    try:
        start_date = date.fromisoformat(start_str) if start_str else date.today()
    except ValueError:
        errors.append("Data de início inválida.")
        start_date = date.today()

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("admin.edit_user", user_id=user.id))

    current = user.salary_histories.filter_by(end_date=None).first()
    if current:
        current.end_date = start_date
    db.session.add(SalaryHistory(
        user_id=user.id,
        salary=salary_value,
        payment_type=payment_type,
        start_date=start_date,
        notes=notes or None,
    ))
    from app.utils import audit
    audit("create", "salary", user.id, user.name,
          f"Salário registrado: R${salary_value} ({payment_type}) a partir de {start_date}")
    db.session.commit()
    flash("Salário registrado.", "success")
    return redirect(url_for("admin.edit_user", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@require_superadmin
def reset_password(user_id: int):
    user = User.query.get_or_404(user_id)
    temp_password = request.form.get("temp_password", "")
    if not temp_password:
        flash("Senha temporária obrigatória.", "error")
        return redirect(url_for("admin.edit_user", user_id=user.id))

    user.set_password(temp_password)
    user.must_change_password = True
    from app.utils import audit
    audit("reset_password", "user", user.id, user.name, "Senha resetada pelo admin")
    db.session.commit()
    flash("Senha resetada com sucesso.", "success")
    return redirect(url_for("admin.edit_user", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@require_superadmin
def delete_user(user_id: int):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Você não pode excluir seu próprio usuário.", "error")
        return redirect(url_for("admin.list_users"))
    from app.utils import audit
    audit("delete", "user", user.id, user.name, f"Usuário excluído: {user.email}")
    db.session.delete(user)
    db.session.commit()
    flash("Usuário excluído.", "success")
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@require_superadmin
def admin_settings():
    settings = SiteSetting.query.get(1)
    if not settings:
        settings = SiteSetting(id=1)
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        commission_raw = request.form.get("default_commission_rate", "").strip()
        try:
            settings.default_commission_rate = float(commission_raw) if commission_raw else settings.default_commission_rate
        except ValueError:
            pass

        file = request.files.get("logo")
        if file and file.filename:
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext in [".png", ".jpg", ".jpeg", ".webp", ".svg"]:
                from app.storage import save_file as _save_file
                settings.logo_path = _save_file(file, "logos", f"logo{ext}")

        # logística
        manto_addr = request.form.get("manto_address", "").strip()
        if manto_addr:
            settings.manto_address = manto_addr
        margin_raw = request.form.get("departure_margin_minutes", "").strip()
        try:
            settings.departure_margin_minutes = int(margin_raw) if margin_raw else settings.departure_margin_minutes
        except ValueError:
            pass
        maps_key = request.form.get("google_maps_api_key", "").strip()
        if maps_key:
            settings.google_maps_api_key = maps_key

        settings.email_notifications_enabled = request.form.get("email_notifications_enabled") == "1"

        # Data de início do sistema
        release_raw = request.form.get("release_date", "").strip()
        if release_raw:
            from datetime import date as _date
            try:
                settings.release_date = _date.fromisoformat(release_raw)
            except ValueError:
                pass
        else:
            settings.release_date = None

        settings.updated_at = datetime.utcnow()
        from app.utils import audit
        audit("edit", "settings", 1, "Configurações", "Configurações do sistema atualizadas")
        db.session.commit()
        flash("Configurações salvas.", "success")
        return redirect(url_for("admin.admin_settings"))

    return render_template(
        "admin_settings.html",
        settings=settings,
        active="settings",
        title="Admin - Configurações",
    )


# ─── LOGS DE AUDITORIA ────────────────────────────────────────────────────────

@admin_bp.route("/logs")
@login_required
@require_superadmin
def audit_logs():
    entity_type = request.args.get("entity_type", "")
    actor = request.args.get("actor", "").strip()
    page = request.args.get("page", 1, type=int)

    q = AuditLog.query.order_by(AuditLog.created_at.desc())
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if actor:
        q = q.filter(AuditLog.actor_name.ilike(f"%{actor}%"))

    logs = q.paginate(page=page, per_page=50, error_out=False)

    entity_types = (
        db.session.query(AuditLog.entity_type)
        .filter(AuditLog.entity_type.isnot(None))
        .distinct()
        .order_by(AuditLog.entity_type)
        .all()
    )

    # Seção "Eventos no banco" — estado atual da agenda
    all_events = (
        CalendarEvent.query
        .filter(CalendarEvent.event_type != "ENSAIO")
        .order_by(CalendarEvent.start_at.desc())
        .limit(200)
        .all()
    )

    return render_template(
        "admin_logs.html",
        logs=logs,
        entity_type=entity_type,
        actor=actor,
        entity_types=[r[0] for r in entity_types],
        all_events=all_events,
    )


# ─── ANÚNCIO DO PORTAL ───────────────────────────────────────────────────────

@admin_bp.route("/portal-announcement", methods=["GET", "POST"])
@login_required
@require_superadmin
def portal_announcement():
    from app.models import Talent
    from app.email_service import send_portal_announcement_email

    talents_with_email    = Talent.query.filter(Talent.email_contact.isnot(None), Talent.email_contact != "").all()
    talents_without_email = Talent.query.filter(
        (Talent.email_contact.is_(None)) | (Talent.email_contact == "")
    ).count()

    if request.method == "POST":
        sent = 0
        failed = 0
        for talent in talents_with_email:
            if send_portal_announcement_email(talent):
                sent += 1
            else:
                failed += 1
        flash(
            f"Anúncio enviado: {sent} email(s) entregue(s)"
            + (f", {failed} falha(s)." if failed else "."),
            "success" if not failed else "info",
        )
        return redirect(url_for("admin.portal_announcement"))

    return render_template(
        "admin_portal_announcement.html",
        total=len(talents_with_email),
        without_email=talents_without_email,
    )


# ─── PAINEL DE DESEMPENHO ─────────────────────────────────────────────────────

@admin_bp.route("/sync", methods=["GET", "POST"])
@login_required
@require_superadmin
def sync_status():
    """Painel de status do sync Google Calendar → banco."""
    import json as _json
    from datetime import date as _date
    from app.models import SiteSetting, CalendarEvent

    settings = SiteSetting.query.get(1)
    raw_cache = _json.loads(settings.calendar_sync_cache) if settings and settings.calendar_sync_cache else {}

    # Meses com eventos no banco (todos, inclusive passados)
    all_events = CalendarEvent.query.with_entities(CalendarEvent.start_at).all()
    months_in_db: set[str] = set()
    for ev in all_events:
        if ev.start_at:
            months_in_db.add(f"{ev.start_at.year:04d}-{ev.start_at.month:02d}")

    now = datetime.utcnow()
    months_info = []
    for ym in sorted(months_in_db, reverse=True):
        ts_str = raw_cache.get(ym)
        if ts_str:
            age_min = int((now - datetime.fromisoformat(ts_str)).total_seconds() // 60)
            fresh = age_min < 20
        else:
            age_min = None
            fresh = False
        y_int, m_int = int(ym[:4]), int(ym[5:7])
        m_start = datetime(y_int, m_int, 1)
        m_end = datetime(y_int + 1, 1, 1) if m_int == 12 else datetime(y_int, m_int + 1, 1)
        count = CalendarEvent.query.filter(
            CalendarEvent.start_at >= m_start,
            CalendarEvent.start_at < m_end,
        ).count()
        months_info.append({"ym": ym, "age_min": age_min, "fresh": fresh, "count": count})

    msg = None
    error = None
    cleanup_result = None
    sync_result = None
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "sync_now":
            from app.calendar.routes import sync_events as _sync_events, _mark_month_synced, CALENDAR_ID as _CAL_ID
            from app.calendar.service import fetch_events_for_month as _fetch
            from datetime import date as _date_cls

            today = _date_cls.today()
            future_months = []
            for i in range(7):  # mês atual + 6 meses à frente
                total_m = today.month - 1 + i
                y = today.year + total_m // 12
                m = total_m % 12 + 1
                future_months.append((y, m, f"{y:04d}-{m:02d}"))

            results = []
            for y, m, ym in future_months:
                try:
                    items = _fetch(_CAL_ID, y, m)
                    _sync_events(items)
                    _mark_month_synced(ym)
                    results.append({"ym": ym, "ok": True, "count": len(items)})
                except Exception as exc:
                    results.append({"ym": ym, "ok": False, "err": str(exc), "count": 0})

            sync_result = results
            errors_count = sum(1 for r in results if not r["ok"])
            total_events = sum(r["count"] for r in results)
            if errors_count:
                error = f"Sync concluído com {errors_count} erro(s). Verifique o resultado abaixo."
            else:
                msg = f"Sync concluído: {len(results)} meses futuros sincronizados ({total_events} eventos processados)."

        elif action == "cleanup_past":
            # Importa só quando necessário para não poluir o namespace global
            from app.calendar.routes import sync_events as _sync_events, _cleanup_stale_events, _mark_month_synced, CALENDAR_ID as _CAL_ID
            from app.calendar.service import fetch_events_for_month as _fetch

            # Limpa TODOS os meses com eventos no banco — incluindo mês atual e futuros.
            # Isso garante que eventos fantasma de qualquer mês sejam removidos.
            all_months = sorted(months_in_db)
            results = []
            for ym in all_months:
                y, m = int(ym[:4]), int(ym[5:7])
                try:
                    items = _fetch(_CAL_ID, y, m)
                    _sync_events(items)
                    removed_titles = _cleanup_stale_events(items, y, m)
                    _mark_month_synced(ym)
                    results.append({"ym": ym, "removed": len(removed_titles), "titles": removed_titles, "ok": True})
                except Exception as exc:
                    results.append({"ym": ym, "removed": 0, "titles": [], "ok": False, "err": str(exc)})
            cleanup_result = results
            total_removed = sum(r["removed"] for r in results)
            errors_count = sum(1 for r in results if not r["ok"])
            if errors_count:
                error = f"Limpeza concluída com {errors_count} erro(s). {total_removed} evento(s) fantasma(s) removido(s)."
            else:
                msg = f"Limpeza concluída: {total_removed} evento(s) fantasma(s) removido(s) em {len(all_months)} mês(es)."

    from app.models import AuditLog
    agenda_logs = (
        AuditLog.query
        .filter(AuditLog.entity_type == "agenda")
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "admin_sync.html",
        months_info=months_info,
        agenda_logs=agenda_logs,
        msg=msg,
        error=error,
        cleanup_result=cleanup_result,
        sync_result=sync_result,
        active="sync",
        title="Admin - Sync Agenda",
    )


@admin_bp.route("/desempenho")
@login_required
@require_superadmin
def desempenho():
    month_str = request.args.get("month", "")
    try:
        year, month = int(month_str[:4]), int(month_str[5:7])
    except (ValueError, IndexError):
        today = date.today()
        year, month = today.year, today.month

    ym = f"{year:04d}-{month:02d}"
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

    # ── Casting ───────────────────────────────────────────────
    casting_logs = EventLog.query.filter(
        EventLog.actor_role == "Casting",
        EventLog.created_at >= start,
        EventLog.created_at < end,
    ).all()
    casting_raw = defaultdict(int)
    for log in casting_logs:
        casting_raw[log.actor_name] += 1
    casting_stats = sorted(casting_raw.items(), key=lambda x: -x[1])

    # ── Figurino ──────────────────────────────────────────────
    figurino_logs = EventLog.query.filter(
        EventLog.actor_role == "Figurino",
        EventLog.created_at >= start,
        EventLog.created_at < end,
    ).all()
    figurino_raw = defaultdict(int)
    for log in figurino_logs:
        figurino_raw[log.actor_name] += 1
    figurino_stats = sorted(figurino_raw.items(), key=lambda x: -x[1])

    # ── Vendas ────────────────────────────────────────────────
    eventos_vendidos = (
        CalendarEvent.query
        .filter(
            CalendarEvent.seller_id.isnot(None),
            CalendarEvent.start_at >= start,
            CalendarEvent.start_at < end,
        )
        .all()
    )
    vendas_raw = defaultdict(lambda: {"count": 0, "total": 0})
    for ev in eventos_vendidos:
        nome = ev.seller.name if ev.seller else "Desconhecido"
        vendas_raw[nome]["count"] += 1
        vendas_raw[nome]["total"] += ev.sale_value or 0
    vendas_stats = sorted(vendas_raw.items(), key=lambda x: -x[1]["total"])

    return render_template(
        "desempenho.html",
        ym=ym,
        casting_stats=casting_stats,
        figurino_stats=figurino_stats,
        vendas_stats=vendas_stats,
        total_casting=sum(casting_raw.values()),
        total_figurino=sum(figurino_raw.values()),
        total_vendas=sum(v["count"] for v in vendas_raw.values()),
        total_valor=sum(v["total"] for v in vendas_raw.values()),
    )
