import os
import re as _re_mod
import secrets
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, current_app, send_from_directory, abort
)
from werkzeug.utils import secure_filename

from app import db, limiter
from app.models import Talent, EventRole, CalendarEvent, TalentMedia
from app.talents.importer import parse_date
from app.email_service import send_password_reset_email

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")

_ALLOWED_PHOTO = {".jpg", ".jpeg", ".png", ".webp"}


# ── Servir uploads de fotos do portal (sem Flask-Login) ────────

@portal_bp.route("/photo/<path:filename>")
def portal_photo(filename: str):
    if not session.get("talent_id"):
        abort(403)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_dir, filename)


# ── Auth helpers ───────────────────────────────────────────────

def _current_talent():
    tid = session.get("talent_id")
    if not tid:
        return None
    return Talent.query.get(tid)


def portal_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("talent_id"):
            return redirect(url_for("portal.login"))
        talent = _current_talent()
        if talent and not talent.terms_accepted_at:
            return redirect(url_for("portal.terms"))
        return fn(*args, **kwargs)
    return wrapper


# ── Login / Logout ─────────────────────────────────────────────

@portal_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if session.get("talent_id"):
        return redirect(url_for("portal.home"))

    error = None
    if request.method == "POST":
        cpf_raw = request.form.get("cpf", "")
        password = request.form.get("password", "")
        cpf = "".join(c for c in cpf_raw if c.isdigit())

        talent = Talent.query.filter_by(cpf=cpf).first()
        if not talent or not talent.check_password(password):
            error = "CPF ou senha incorretos."
        else:
            session.clear()
            session["talent_id"] = talent.id
            session.permanent = True
            if talent.must_change_password:
                return redirect(url_for("portal.change_password"))
            if not talent.terms_accepted_at:
                return redirect(url_for("portal.terms"))
            return redirect(url_for("portal.home"))

    return render_template("portal/login.html", error=error)


@portal_bp.route("/terms", methods=["GET", "POST"])
def terms():
    if not session.get("talent_id"):
        return redirect(url_for("portal.login"))
    talent = _current_talent()
    if talent and talent.terms_accepted_at:
        return redirect(url_for("portal.home"))
    if request.method == "POST" and talent:
        talent.terms_accepted_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("portal.home"))
    return render_template("portal/terms.html", talent=talent)


@portal_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("talent_id", None)
    return redirect(url_for("portal.login"))


# ── Primeiro acesso ────────────────────────────────────────────

import re as _re_pw

def _validate_new_password(pw: str):
    if len(pw) < 8:
        return "A senha deve ter pelo menos 8 caracteres."
    if not _re_pw.search(r'[A-Z]', pw):
        return "A senha deve ter pelo menos 1 letra maiúscula."
    if not _re_pw.search(r'[a-z]', pw):
        return "A senha deve ter pelo menos 1 letra minúscula."
    if not _re_pw.search(r'\d', pw):
        return "A senha deve ter pelo menos 1 número."
    if not _re_pw.search(r'[^A-Za-z0-9]', pw):
        return "A senha deve ter pelo menos 1 símbolo (ex: @, #, !, %)."
    return None


@portal_bp.route("/first-access", methods=["GET", "POST"])
def first_access():
    if session.get("talent_id"):
        return redirect(url_for("portal.home"))

    step = request.form.get("step", "1")
    error = None
    talent = None

    if request.method == "POST":
        cpf = "".join(c for c in request.form.get("cpf", "") if c.isdigit())
        talent = Talent.query.filter_by(cpf=cpf).first()

        if step == "1":
            if not talent:
                error = "CPF não encontrado. Verifique se você está cadastrado."
            elif talent.password_hash:
                error = "Este CPF já possui senha. Use a tela de login ou fale com o casting para resetar."
            else:
                # CPF válido sem senha → avança para criação de senha
                return render_template("portal/first_access.html", step="2", cpf=cpf, error=None)

        elif step == "2":
            if not talent:
                error = "CPF inválido."
            else:
                new_pw = request.form.get("new_password", "")
                confirm = request.form.get("confirm_password", "")
                error = _validate_new_password(new_pw)
                if not error and new_pw != confirm:
                    error = "As senhas não coincidem."
                if not error:
                    talent.set_password(new_pw)
                    talent.must_change_password = False
                    db.session.commit()
                    flash("Senha criada com sucesso! Faça login.", "success")
                    return redirect(url_for("portal.login"))
                return render_template("portal/first_access.html", step="2", cpf=cpf, error=error)

    return render_template("portal/first_access.html", step="1", cpf="", error=error)


# ── Trocar senha (primeiro acesso) ────────────────────────────

@portal_bp.route("/change-password", methods=["GET", "POST"])
@portal_login_required
def change_password():
    talent = _current_talent()
    error = None
    if request.method == "POST":
        new_pw = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if len(new_pw) < 6:
            error = "A senha deve ter pelo menos 6 caracteres."
        elif new_pw != confirm:
            error = "As senhas não coincidem."
        else:
            talent.set_password(new_pw)
            talent.must_change_password = False
            db.session.commit()
            return redirect(url_for("portal.home"))
    return render_template("portal/change_password.html", talent=talent, error=error)


# ── Home ───────────────────────────────────────────────────────

@portal_bp.route("/")
@portal_login_required
def home():
    talent = _current_talent()
    today = datetime.utcnow().date()

    # Convites pendentes (invite_status = 'pending')
    pending_invites = (
        EventRole.query
        .filter_by(talent_id=talent.id, invite_status="pending")
        .join(CalendarEvent)
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )

    # Eventos confirmados futuros (invite_status = 'accepted', data >= hoje)
    upcoming = (
        EventRole.query
        .filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.start_at >= datetime.utcnow())
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )

    # Histórico de eventos passados confirmados (home: últimos 10)
    history = (
        EventRole.query
        .filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.start_at < datetime.utcnow())
        .order_by(CalendarEvent.start_at.desc())
        .limit(10)
        .all()
    )

    # Resumo financeiro — todos os passados
    all_past = (
        EventRole.query
        .filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.start_at < datetime.utcnow())
        .all()
    )
    total_pago    = sum((r.cache_value or 0) + (r.travel_cache or 0) for r in all_past if r.payment_status == "pago")
    total_pendente = sum((r.cache_value or 0) + (r.travel_cache or 0) for r in all_past if r.payment_status != "pago")
    history_total = len(all_past)

    return render_template(
        "portal/home.html",
        talent=talent,
        pending_invites=pending_invites,
        upcoming=upcoming,
        history=history,
        history_total=history_total,
        total_pago=total_pago,
        total_pendente=total_pendente,
        today=today,
    )


# ── Aceitar convite ────────────────────────────────────────────

@portal_bp.route("/invites/<int:role_id>/accept", methods=["POST"])
@portal_login_required
def accept_invite(role_id: int):
    talent = _current_talent()
    role = EventRole.query.filter_by(id=role_id, talent_id=talent.id).first_or_404()
    role.invite_status = "accepted"
    db.session.commit()
    flash("Presença confirmada!", "success")
    return redirect(url_for("portal.home"))


# ── Recusar convite ────────────────────────────────────────────

@portal_bp.route("/invites/<int:role_id>/reject", methods=["POST"])
@portal_login_required
def reject_invite(role_id: int):
    talent = _current_talent()
    role = EventRole.query.filter_by(id=role_id, talent_id=talent.id).first_or_404()
    # Volta para fila do casting
    role.talent_id = None
    role.invite_status = None
    role.assigned_at = None
    role.figurino_done_at = None
    db.session.commit()
    flash("Convite recusado. O casting será notificado.", "info")
    return redirect(url_for("portal.home"))


# ── Perfil ─────────────────────────────────────────────────────

@portal_bp.route("/profile", methods=["GET", "POST"])
@portal_login_required
def profile():
    talent = _current_talent()

    if request.method == "POST":
        f = request.form
        talent.full_name            = f.get("full_name", "").strip() or talent.full_name
        talent.artistic_name        = f.get("artistic_name", "").strip() or None
        talent.phone                = f.get("phone", "").strip() or None
        talent.email_contact        = f.get("email_contact", "").strip() or None
        talent.gender               = f.get("gender", "").strip() or None
        talent.race                 = f.get("race", "").strip() or None
        talent.languages            = f.get("languages", "").strip() or None
        talent.skills               = f.get("skills", "").strip() or None
        talent.pix_key              = f.get("pix_key", "").strip() or None
        talent.pix_key_type         = f.get("pix_key_type", "").strip() or None
        talent.pix_key_secondary    = f.get("pix_key_secondary", "").strip() or None
        talent.rg                   = f.get("rg", "").strip() or None
        talent.passport_visa_text   = f.get("passport_visa_text", "").strip() or None
        talent.has_visa             = f.get("has_visa") == "1"
        talent.car_brand            = f.get("car_brand", "").strip() or None
        talent.car_model            = f.get("car_model", "").strip() or None
        talent.car_year             = f.get("car_year", "").strip() or None
        talent.car_plate            = f.get("car_plate", "").strip() or None
        talent.birth_date           = parse_date(f.get("birth_date", ""))
        talent.cnh_expiration       = parse_date(f.get("cnh_expiration", ""))

        try:
            talent.height_cm = int(f.get("height_cm")) if f.get("height_cm") else None
        except ValueError:
            pass

        talent.clothing_size_top    = f.get("clothing_size_top", "").strip() or None
        talent.clothing_size_bottom = f.get("clothing_size_bottom", "").strip() or None
        talent.shoe_size            = f.get("shoe_size", "").strip() or None

        # Foto de rosto
        from app.storage import save_file as _save_file

        face_file = request.files.get("photo_face")
        if face_file and face_file.filename:
            ext = os.path.splitext(face_file.filename)[1].lower()
            if ext in _ALLOWED_PHOTO:
                talent.photo_face_path = _save_file(face_file, "talent_photos")

        full_file = request.files.get("photo_full")
        if full_file and full_file.filename:
            ext = os.path.splitext(full_file.filename)[1].lower()
            if ext in _ALLOWED_PHOTO:
                talent.photo_full_path = _save_file(full_file, "talent_photos")

        db.session.commit()
        flash("Perfil atualizado com sucesso!", "success")
        return redirect(url_for("portal.profile"))

    return render_template("portal/profile.html", talent=talent)


# ── Mídia do talento (fotos de atuação + links) ────────────────

MAX_PHOTOS = 3

@portal_bp.route("/media/upload-photo", methods=["POST"])
@portal_login_required
def media_upload_photo():
    talent = _current_talent()
    photo_count = TalentMedia.query.filter_by(talent_id=talent.id, media_type="photo").count()
    if photo_count >= MAX_PHOTOS:
        flash(f"Limite de {MAX_PHOTOS} fotos de atuação atingido.", "error")
        return redirect(url_for("portal.profile"))
    file = request.files.get("photo")
    if not file or not file.filename:
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("portal.profile"))
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in _ALLOWED_PHOTO:
        flash("Formato não suportado.", "error")
        return redirect(url_for("portal.profile"))
    from app.storage import save_file as _save_file
    fname = f"media_{talent.id}_{uuid.uuid4().hex[:8]}{ext}"
    file_url = _save_file(file, "talent_photos", fname)
    label = request.form.get("label", "").strip() or None
    db.session.add(TalentMedia(
        talent_id=talent.id,
        media_type="photo",
        label=label,
        file_path=file_url,
    ))
    db.session.commit()
    flash("Foto adicionada.", "success")
    return redirect(url_for("portal.profile"))


@portal_bp.route("/media/add-link", methods=["POST"])
@portal_login_required
def media_add_link():
    talent = _current_talent()
    url_val = request.form.get("url", "").strip()
    if not url_val:
        flash("URL não pode ser vazia.", "error")
        return redirect(url_for("portal.profile"))
    label = request.form.get("label", "").strip() or None
    db.session.add(TalentMedia(
        talent_id=talent.id,
        media_type="link",
        label=label or url_val[:60],
        url=url_val,
    ))
    db.session.commit()
    flash("Link adicionado.", "success")
    return redirect(url_for("portal.profile"))


@portal_bp.route("/media/<int:media_id>/delete", methods=["POST"])
@portal_login_required
def media_delete(media_id: int):
    talent = _current_talent()
    item = TalentMedia.query.filter_by(id=media_id, talent_id=talent.id).first_or_404()
    if item.file_path:
        full = os.path.join(current_app.config["UPLOAD_FOLDER"],
                            item.file_path.lstrip("/uploads/").lstrip("uploads/"))
        if os.path.exists(full):
            os.remove(full)
    db.session.delete(item)
    db.session.commit()
    flash("Item removido.", "success")
    return redirect(url_for("portal.profile"))


# ── Ciente de alteração no evento ──────────────────────────────

@portal_bp.route("/roles/<int:role_id>/ack-change", methods=["POST"])
@portal_login_required
def ack_event_change(role_id: int):
    talent = _current_talent()
    role = EventRole.query.filter_by(id=role_id, talent_id=talent.id).first_or_404()
    role.event_changed_at = None
    db.session.commit()
    return redirect(url_for("portal.home"))


# ── Histórico completo ─────────────────────────────────────────

@portal_bp.route("/historico")
@portal_login_required
def historico():
    talent = _current_talent()

    all_past = (
        EventRole.query
        .filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.start_at < datetime.utcnow())
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    total_pago     = sum((r.cache_value or 0) + (r.travel_cache or 0) for r in all_past if r.payment_status == "pago")
    total_pendente = sum((r.cache_value or 0) + (r.travel_cache or 0) for r in all_past if r.payment_status != "pago")
    total_geral    = total_pago + total_pendente

    return render_template(
        "portal/historico.html",
        talent=talent,
        roles=all_past,
        total_pago=total_pago,
        total_pendente=total_pendente,
        total_geral=total_geral,
    )


# ── Esqueci a senha ────────────────────────────────────────────

@portal_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def forgot_password():
    if session.get("talent_id"):
        return redirect(url_for("portal.home"))

    sent = False
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        talent = Talent.query.filter(
            db.func.lower(Talent.email_contact) == email
        ).first()

        # Sempre mostra "enviado" para não revelar quais emails existem
        if talent and talent.password_hash:
            token = secrets.token_urlsafe(32)
            talent.password_reset_token = token
            talent.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            reset_url = url_for("portal.reset_password", token=token, _external=True)
            send_password_reset_email(talent, reset_url)

        sent = True

    return render_template("portal/forgot_password.html", sent=sent, error=error)


# ── Redefinir senha via token ──────────────────────────────────

@portal_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def reset_password(token: str):
    if session.get("talent_id"):
        return redirect(url_for("portal.home"))

    talent = Talent.query.filter_by(password_reset_token=token).first()

    if not talent or (
        talent.password_reset_expires is None
        or talent.password_reset_expires < datetime.utcnow()
    ):
        return render_template("portal/reset_password.html", invalid=True)

    error = None
    if request.method == "POST":
        new_pw = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        error = _validate_new_password(new_pw)
        if not error and new_pw != confirm:
            error = "As senhas não coincidem."
        if not error:
            talent.set_password(new_pw)
            talent.must_change_password = False
            talent.password_reset_token = None
            talent.password_reset_expires = None
            db.session.commit()
            flash("Senha redefinida com sucesso! Faça login.", "success")
            return redirect(url_for("portal.login"))

    return render_template("portal/reset_password.html", invalid=False, error=error, token=token)
