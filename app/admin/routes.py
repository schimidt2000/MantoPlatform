from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app import db
from app.models import User
from functools import wraps


admin_bp = Blueprint("admin", __name__)

def require_superadmin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not any(r.name == "SUPERADMIN" for r in current_user.roles):
            return {"ok": False, "error": "Acesso apenas para SuperAdmin"}, 403
        return fn(*args, **kwargs)
    return wrapper

@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
@require_superadmin
def create_user():
    if request.method == "GET":
        return render_template("admin_create_user.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    temp_password = request.form.get("temp_password", "")

    if not name or not email or not temp_password:
        return render_template("admin_create_user.html", error="Preencha tudo.")

    if User.query.filter_by(email=email).first():
        return render_template("admin_create_user.html", error="Esse email já existe.")

    user = User(email=email, name=name, is_active=True, must_change_password=True)
    user.set_password(temp_password)

    # (Importante) Não damos role nenhuma automaticamente.
    db.session.add(user)
    db.session.commit()

    return render_template("admin_create_user.html", msg="Usuário criado com sucesso!")
