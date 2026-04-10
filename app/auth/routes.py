import os
from flask import Blueprint, request, render_template, redirect, url_for, current_app, flash, session
from flask_login import login_user, logout_user, login_required
from werkzeug.utils import secure_filename
from ..models import User, db
from flask_login import current_user
from app import limiter

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    # GET: mostra a página
    if request.method == "GET":
        return render_template("login.html")

    # POST: tenta logar (form do navegador OU JSON)
    if request.is_json:
        data = request.get_json()
        email = data.get("email", "")
        password = data.get("password", "")
    else:
        email = request.form.get("email", "")
        password = request.form.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        # Se veio do navegador, renderiza com erro
        if not request.is_json:
            return render_template("login.html", error="Email ou senha inválidos")
        return {"ok": False, "error": "Credenciais inválidas"}, 401

    session.clear()
    login_user(user)

    if user.must_change_password:
        return redirect(url_for("auth.change_password"))

    # Se veio do navegador, redireciona pra home
    if not request.is_json:
        return redirect(url_for("home"))

    return {"ok": True}

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    if not request.is_json:
        return redirect(url_for("auth.login"))
    return {"ok": True}


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "GET":
        return render_template("change_password.html")

    p1 = request.form.get("password1", "")
    p2 = request.form.get("password2", "")

    if not p1 or len(p1) < 6:
        return render_template("change_password.html", error="Senha deve ter pelo menos 6 caracteres.")
    if p1 != p2:
        return render_template("change_password.html", error="As senhas não coincidem.")

    current_user.set_password(p1)
    current_user.must_change_password = False
    db.session.commit()

    return redirect(url_for("home"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    errors = []
    success = None

    if request.method == "POST":
        # Nome
        name = request.form.get("name", "").strip()
        if not name:
            errors.append("O nome não pode ser vazio.")
        else:
            current_user.name = name

        # Data de nascimento
        birth_date_str = request.form.get("birth_date", "").strip()
        if birth_date_str:
            from datetime import date as _date
            try:
                current_user.birth_date = _date.fromisoformat(birth_date_str)
            except ValueError:
                errors.append("Data de nascimento inválida.")
        else:
            current_user.birth_date = None

        # Foto de perfil
        photo = request.files.get("profile_photo")
        if photo and photo.filename:
            ext = os.path.splitext(photo.filename)[1].lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
                errors.append("Formato inválido. Use JPG, PNG, GIF ou WebP.")
            else:
                profiles_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "profiles")
                os.makedirs(profiles_dir, exist_ok=True)
                filename = f"user_{current_user.id}{ext}"
                photo.save(os.path.join(profiles_dir, filename))
                current_user.profile_photo = f"profiles/{filename}"

        # Troca de senha (opcional)
        new_pw = request.form.get("new_password", "").strip()
        if new_pw:
            if len(new_pw) < 6:
                errors.append("A nova senha deve ter pelo menos 6 caracteres.")
            else:
                confirm_pw = request.form.get("confirm_password", "").strip()
                if new_pw != confirm_pw:
                    errors.append("As senhas não coincidem.")
                else:
                    current_user.set_password(new_pw)
                    current_user.must_change_password = False

        if not errors:
            db.session.commit()
            success = "Perfil atualizado com sucesso."

    return render_template("profile.html", errors=errors, success=success)
