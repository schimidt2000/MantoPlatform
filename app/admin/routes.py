import os
from collections import defaultdict
from datetime import datetime, date
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import User, SiteSetting, Role, EventLog, CalendarEvent, AuditLog
from app.constants import RoleName

admin_bp = Blueprint("admin", __name__)


def require_superadmin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not any(r.name == RoleName.SUPERADMIN for r in current_user.roles):
            return {"ok": False, "error": "Acesso apenas para SuperAdmin"}, 403
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
@require_superadmin
def list_users():
    users = User.query.order_by(User.id.asc()).all()
    return render_template(
        "admin_users.html",
        users=users,
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
@require_superadmin
def edit_user(user_id: int):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        is_active = request.form.get("is_active") == "1"
        role_ids = [int(r) for r in request.form.getlist("roles")]

        if not name or not email:
            return render_template(
                "admin_user_edit.html",
                user=user,
                error="Preencha tudo.",
                settings=get_settings(),
                active="users",
                title="Admin - Editar Usuário",
            )

        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            return render_template(
                "admin_user_edit.html",
                user=user,
                error="Esse email já existe.",
                settings=get_settings(),
                active="users",
                title="Admin - Editar Usuário",
            )

        user.name = name
        user.email = email
        user.is_active = is_active
        user.roles = Role.query.filter(Role.id.in_(role_ids)).all() if role_ids else []
        from app.utils import audit
        audit("edit", "user", user.id, user.name, f"Usuário editado: {user.email}")
        db.session.commit()
        return redirect(url_for("admin.list_users"))

    return render_template(
        "admin_user_edit.html",
        user=user,
        settings=get_settings(),
        active="users",
        title="Admin - Editar Usuário",
        roles=Role.query.order_by(Role.name.asc()).all(),
    )


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

        # ClickSign
        cs_token = request.form.get("clicksign_token", "").strip()
        if cs_token:
            settings.clicksign_token = cs_token
        settings.clicksign_sandbox = request.form.get("clicksign_sandbox", "0") == "1"
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

    return render_template(
        "admin_logs.html",
        logs=logs,
        entity_type=entity_type,
        actor=actor,
        entity_types=[r[0] for r in entity_types],
    )


# ─── PAINEL DE DESEMPENHO ─────────────────────────────────────────────────────

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
