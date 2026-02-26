import os
from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import User, SiteSetting, Role

admin_bp = Blueprint("admin", __name__)


def require_superadmin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not any(r.name == "SUPERADMIN" for r in current_user.roles):
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
        settings.primary_color = request.form.get("primary_color", "") or settings.primary_color
        settings.secondary_color = request.form.get("secondary_color", "") or settings.secondary_color
        settings.accent_color = request.form.get("accent_color", "") or settings.accent_color
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
                save_name = f"logo{ext}"
                save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], save_name)
                file.save(save_path)
                settings.logo_path = f"/uploads/{save_name}"

        settings.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Configurações salvas.", "success")
        return redirect(url_for("admin.admin_settings"))

    return render_template(
        "admin_settings.html",
        settings=settings,
        active="settings",
        title="Admin - Identidade",
    )
