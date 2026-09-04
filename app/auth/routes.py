from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required
from werkzeug.utils import secure_filename
from ..models import User, db
from flask_login import current_user
from app import limiter
from app.storage import (
    ALLOWED_IMAGE_EXTENSIONS,
    ImagemNaoConvertida,
    delete_file,
    formatos_aceitos,
    is_allowed_extension,
    save_file,
)

#: Teto do avatar. Antes o único limite era o `MAX_CONTENT_LENGTH` global de 512 MB.
AVATAR_MAX_BYTES = 5 * 1024 * 1024


def _tamanho(file_storage) -> int:
    """Bytes do upload, sem consumir o stream."""
    file_storage.stream.seek(0, 2)
    tamanho = file_storage.stream.tell()
    file_storage.stream.seek(0)
    return tamanho


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

    user = User.query.filter_by(email=email).first() if email else None
    if not user or not user.has_access or not user.check_password(password):
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

    p1 = request.form.get("password", "")
    p2 = request.form.get("confirm", "")

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
            if not is_allowed_extension(photo.filename, ALLOWED_IMAGE_EXTENSIONS):
                errors.append(f"Formato inválido. Use {formatos_aceitos(ALLOWED_IMAGE_EXTENSIONS)}.")
            elif _tamanho(photo) > AVATAR_MAX_BYTES:
                errors.append("Foto muito grande. O limite é 5 MB.")
            else:
                # `save_file` (e não `photo.save`) por três motivos: comprime como todo o resto do
                # sistema, gera nome novo — o `user_<id>.<ext>` fixo deixava o navegador com o
                # avatar antigo em cache e sobrava um `user_5.heic` órfão quando a conversão
                # mudava a extensão — e **devolve** o caminho, em vez de montá-lo à mão.
                anterior = current_user.profile_photo
                try:
                    url = save_file(photo, "profiles")
                except ImagemNaoConvertida:
                    url = None
                    errors.append("Não conseguimos ler esta foto. Envie em JPG ou PNG.")
                if url:
                    # A coluna guarda `profiles/<arquivo>` sem o `/uploads/` (ver base.html).
                    current_user.profile_photo = url[len("/uploads/"):]
                    if anterior:
                        delete_file(f"/uploads/{anterior}")

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
