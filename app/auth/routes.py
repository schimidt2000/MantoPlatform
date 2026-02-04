from flask import Blueprint, request, render_template, redirect, url_for
from flask_login import login_user, logout_user, login_required
from ..models import User, db
from flask_login import current_user

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
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
