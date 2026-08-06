"""Formulário público de cadastro de talento (feature 086).

Substitui o Google Form: as fotos/documentos vão para o armazenamento da Manto (via ``save_file``),
não dependem do Drive do candidato. Cada envio válido cria um ``Talent`` pendente para revisão.

Toda a validação/parsing e a construção do ``Talent`` vivem em ``cadastro_ops.py`` (feature
162) — reaproveitadas também pelo endpoint API (``app/api/cadastro_write.py``); este módulo só
lida com o transporte HTTP (formulário/redirect) específico do Jinja.
"""

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from app import db, limiter
from app.cadastro import verify_ops
from app.cadastro.cadastro_ops import check_cpf_exists, process_submission

cadastro_bp = Blueprint("cadastro", __name__, url_prefix="/cadastro")


@cadastro_bp.route("/", methods=["GET"])
def form():
    """Renderiza o formulário público de cadastro."""
    # request.form é um MultiDict vazio no GET — dá suporte a form.get/getlist no template.
    return render_template("cadastro/form.html", form=request.form, error=None)


@cadastro_bp.route("/check-cpf")
@limiter.limit("60 per hour")
def check_cpf():
    """Verifica em tempo real se um CPF já existe no banco (avisa antes de enviar tudo)."""
    exists, valid = check_cpf_exists(request.args.get("cpf") or "")
    return jsonify({"exists": exists, "valid": valid})


@cadastro_bp.route("/enviado", methods=["GET"])
def enviado():
    """Página de confirmação após envio bem-sucedido."""
    return render_template("cadastro/success.html")


@cadastro_bp.route("/", methods=["POST"])
@limiter.limit("10 per hour")
def submit():
    """Recebe o cadastro: valida, salva arquivos e cria um talento pendente."""
    outcome = process_submission(request.form, request.files)

    if outcome.honeypot:
        return redirect(url_for("cadastro.enviado"))

    if outcome.error:
        return render_template("cadastro/form.html", form=request.form, error=outcome.error), 400

    # Paridade com o endpoint React (feature 219): o talento também confirma o email por aqui.
    verify_ops.issue_token(outcome.talent)
    db.session.add(outcome.talent)
    db.session.commit()

    from app.api.cadastro_write import _send_confirmation

    _send_confirmation(outcome.talent)
    return redirect(url_for("cadastro.enviado"))
