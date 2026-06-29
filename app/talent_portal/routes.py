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
from sqlalchemy import func, or_

from app import db, limiter
from app.models import Talent, EventRole, CalendarEvent, TalentMedia, EventRating, EventSubRating
from app.talents.importer import parse_date
from app.email_service import send_password_reset_email, send_async

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")

_ALLOWED_PHOTO = {".jpg", ".jpeg", ".png", ".webp"}

_PW_RULES = [
    (_re_mod.compile(r'.{8,}'),        "Mínimo 8 caracteres"),
    (_re_mod.compile(r'[A-Z]'),        "Pelo menos uma letra maiúscula"),
    (_re_mod.compile(r'[a-z]'),        "Pelo menos uma letra minúscula"),
    (_re_mod.compile(r'[0-9]'),        "Pelo menos um número"),
    (_re_mod.compile(r'[^A-Za-z0-9]'), "Pelo menos um símbolo (!@#$%...)"),
]


def _validate_password_strength(pw: str) -> str | None:
    for pattern, msg in _PW_RULES:
        if not pattern.search(pw):
            return msg
    return None


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
        if talent and talent.must_change_password:
            return redirect(url_for("portal.change_password"))
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
    if talent and talent.must_change_password:
        return redirect(url_for("portal.change_password"))
    # Já aceitou: mostra o termo em modo leitura (feature 091), em vez de redirecionar.
    if request.method == "GET" and talent and talent.terms_accepted_at:
        return render_template("portal/terms.html", talent=talent, view_only=True)
    if request.method == "POST" and talent:
        talent.terms_accepted_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("portal.home"))
    return render_template("portal/terms.html", talent=talent, view_only=False)


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

    sent = False
    error = None
    email_hint = None

    if request.method == "POST":
        import secrets as _sec, string as _str
        from app.email_service import send_welcome_email as _send_welcome

        cpf = "".join(c for c in request.form.get("cpf", "") if c.isdigit())
        talent = Talent.query.filter_by(cpf=cpf).first()

        if not talent:
            error = "CPF não encontrado. Verifique se você está cadastrado ou fale com nossa equipe."
        elif talent.password_hash:
            error = "Este CPF já possui senha. Use a opção 'Esqueci minha senha' abaixo para recuperar o acesso."
        elif not talent.email_contact:
            error = "Seu email não está cadastrado. Entre em contato com nossa equipe de casting."
        else:
            alphabet = _str.ascii_letters + _str.digits
            temp_pw = "".join(_sec.choice(alphabet) for _ in range(10))
            # Lê atributos antes do commit
            talent_email = talent.email_contact
            talent_name  = talent.artistic_name or talent.full_name
            talent_cpf   = talent.cpf
            parts = talent_email.split("@")
            email_hint = (parts[0][:2] + "***@" + parts[1]) if len(parts) == 2 else "***"
            talent.set_password(temp_pw)
            talent.must_change_password = True
            db.session.commit()
            from types import SimpleNamespace
            _t = SimpleNamespace(email_contact=talent_email, artistic_name=None,
                                 full_name=talent_name, cpf=talent_cpf)
            send_async(_send_welcome, _t, temp_pw)
            sent = True

    return render_template("portal/first_access.html", sent=sent, error=error, email_hint=email_hint)


# ── Trocar senha (primeiro acesso) ────────────────────────────

@portal_bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    if not session.get("talent_id"):
        return redirect(url_for("portal.login"))
    talent = _current_talent()
    if not talent or not talent.must_change_password:
        return redirect(url_for("portal.home"))
    error = None
    if request.method == "POST":
        new_pw = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        error = _validate_password_strength(new_pw) or (
            "As senhas não coincidem." if new_pw != confirm else None
        )
        if not error:
            talent.set_password(new_pw)
            talent.must_change_password = False
            db.session.commit()
            if not talent.terms_accepted_at:
                return redirect(url_for("portal.terms"))
            return redirect(url_for("portal.home"))
    return render_template("portal/change_password.html", talent=talent, error=error)


def _now_sp() -> datetime:
    """Agora em horário de Brasília, naïve — mesma convenção dos horários de evento no banco."""
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)


def _event_ended(event) -> bool:
    """True se o evento já terminou (término efetivo: end_at, senão start_at) em Brasília."""
    if not event:
        return False
    event_end = event.end_at or event.start_at
    return bool(event_end and event_end < _now_sp())


def _rated_event_ids(talent) -> set[int]:
    """IDs de eventos que o talento já avaliou (independe de janela de tempo)."""
    return {r.event_id for r in EventRating.query.filter_by(talent_id=talent.id).all()}


def _not_rejected():
    """Cláusula: talento escalado cujo convite NÃO foi recusado (aceito, pendente ou sem status).

    Em SQL ``NULL != 'rejected'`` resulta em NULL (não True), então NULL é tratado explicitamente.
    """
    return or_(EventRole.invite_status.is_(None), EventRole.invite_status != "rejected")


def _rateable_event_ids(talent) -> set[int]:
    """IDs de eventos que o talento pode avaliar e ainda não avaliou.

    Elegível: escalado (convite não recusado) num evento já terminado, dentro de 7 dias contados do
    MAIS RECENTE entre o término do evento e a inclusão do talento (``assigned_at``). Assim, quem é
    adicionado tardiamente ganha a janela a partir da inclusão (feature 085).
    """
    now = _now_sp()
    window = now - timedelta(days=7)
    event_end = func.coalesce(CalendarEvent.end_at, CalendarEvent.start_at)
    rated = _rated_event_ids(talent)
    rows = (
        EventRole.query
        .filter(EventRole.talent_id == talent.id, _not_rejected())
        .join(CalendarEvent)
        .filter(
            event_end < now,
            or_(event_end >= window, EventRole.assigned_at >= window),
        )
        .all()
    )
    return {r.event_id for r in rows if r.event_id and r.event_id not in rated}


def _editable_rating_event_ids(talent) -> set[int]:
    """IDs de eventos já avaliados pelo talento, na janela de edição (30 dias).

    Janela contada do mais recente entre o término do evento e a inclusão do talento (feature 085).
    """
    rated = _rated_event_ids(talent)
    if not rated:
        return set()
    now = _now_sp()
    window = now - timedelta(days=30)
    event_end = func.coalesce(CalendarEvent.end_at, CalendarEvent.start_at)
    rows = (
        EventRole.query
        .filter(EventRole.talent_id == talent.id, _not_rejected())
        .join(CalendarEvent)
        .filter(
            CalendarEvent.id.in_(rated),
            event_end < now,
            or_(event_end >= window, EventRole.assigned_at >= window),
        )
        .all()
    )
    return {r.event_id for r in rows if r.event_id}


def _snapshot_rating(rating) -> dict:
    """Fotografia do estado atual de uma avaliação (nota geral + comentário + sub-avaliações)."""
    return {
        "score": rating.score,
        "comment": rating.comment,
        "subs": sorted(
            [
                {
                    "category": s.category,
                    "subject_talent_id": s.subject_talent_id,
                    "score": s.score,
                    "comment": s.comment,
                }
                for s in rating.sub_ratings
            ],
            key=lambda d: (d["category"], d["subject_talent_id"] or 0),
        ),
    }


def _maybe_record_rating_version(event_id: int, rating) -> None:
    """Registra UMA versão anterior por sessão de edição, se o conteúdo mudou.

    Usa um baseline (estado pré-edição) guardado na sessão no GET de `rate_event`. Como uma
    edição ocorre em até 2 requests (nota geral + sub-avaliações), um flag de sessão garante que
    só uma versão seja criada por sessão de edição. Não faz commit.
    """
    import json as _json
    from app.models import EventRatingVersion

    baseline = session.get(f"rating_baseline_{event_id}")
    if baseline is None:
        return  # não é uma edição iniciada pela tela (ex.: primeira avaliação)

    current = _snapshot_rating(rating)
    if current == baseline:
        return  # ainda não mudou nada nesta etapa

    if session.get(f"rating_versioned_{event_id}"):
        return  # já registramos a versão desta sessão de edição

    db.session.add(EventRatingVersion(
        rating_id=rating.id,
        snapshot=_json.dumps(baseline, ensure_ascii=False),
        replaced_at=datetime.utcnow(),
    ))
    rating.edit_count = (rating.edit_count or 0) + 1
    rating.edited_at = datetime.utcnow()
    session[f"rating_versioned_{event_id}"] = True


# ── Home ───────────────────────────────────────────────────────

@portal_bp.route("/")
@portal_login_required
def home():
    talent = _current_talent()
    now = _now_sp()
    today = now.date()

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
        .filter(CalendarEvent.start_at >= now)
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )

    # Eventos para avaliar: TERMINADOS nos últimos 7 dias, sem avaliação ainda.
    rateable_event_ids = _rateable_event_ids(talent)
    events_to_rate = (
        EventRole.query
        .filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.id.in_(rateable_event_ids) if rateable_event_ids else False)
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    # Histórico de eventos passados confirmados (home: últimos 10)
    history = (
        EventRole.query
        .filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.start_at < now)
        .order_by(CalendarEvent.start_at.desc())
        .limit(10)
        .all()
    )

    # Resumo financeiro — todos os passados
    all_past = (
        EventRole.query
        .filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.start_at < now)
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
        events_to_rate=events_to_rate,
        rateable_event_ids=rateable_event_ids,
        rated_event_ids=_rated_event_ids(talent),
        editable_rating_event_ids=_editable_rating_event_ids(talent),
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
    # Mantém talent_id para o casting saber quem recusou; status marca a rejeição
    role.invite_status = "rejected"
    db.session.commit()
    flash("Convite recusado. Nossa equipe de casting foi notificada.", "info")
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
    role.change_description = None
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
        .filter(CalendarEvent.start_at < _now_sp())
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
        rateable_event_ids=_rateable_event_ids(talent),
        rated_event_ids=_rated_event_ids(talent),
        editable_rating_event_ids=_editable_rating_event_ids(talent),
    )


# ── Visualizador de figurinos do evento ────────────────────────

@portal_bp.route("/events/<int:event_id>/figurino")
@portal_login_required
def event_figurino(event_id: int):
    talent = _current_talent()

    # Garante que o talento tem uma vaga neste evento (pendente ou aceita)
    role = EventRole.query.filter(
        EventRole.event_id == event_id,
        EventRole.talent_id == talent.id,
        EventRole.invite_status.in_(["accepted", "pending"]),
    ).first_or_404()

    event = role.event

    from app.models import FigurinoSheet
    from app.figurino.drive_service import normalize_name

    seen_ids: set[int] = set()
    sheet_items: list[tuple] = []

    for r in [r for r in event.roles if r.talent_id == talent.id]:
        sheet = r.figurino_sheet
        if not sheet:
            norm = normalize_name(r.character_name)
            sheet = FigurinoSheet.query.filter_by(character_name_norm=norm).first()

        if not sheet or sheet.id in seen_ids:
            continue
        seen_ids.add(sheet.id)

        # Converte URL de upload para rota do portal (evita checar Flask-Login)
        photo_url = None
        if sheet.photo_filename:
            if sheet.photo_filename.startswith("/uploads/"):
                photo_url = "/portal/photo/" + sheet.photo_filename[9:]
            else:
                photo_url = sheet.photo_filename

        sheet_items.append((sheet, photo_url))

    return render_template(
        "portal/figurino_viewer.html",
        event=event,
        sheet_items=sheet_items,
        talent=talent,
    )


# ── Avaliação de eventos ───────────────────────────────────────

_SHOW_KEYWORDS = ("SHOW", "APRESENTAÇÃO", "APRESENTACAO", "ESPETÁCULO", "ESPETACULO")


def _is_show_event(event: CalendarEvent) -> bool:
    title_upper = (event.title or "").upper()
    return any(kw in title_upper for kw in _SHOW_KEYWORDS)


def _build_rating_context(talent: Talent, event: CalendarEvent) -> dict:
    """Monta as listas de pessoas para avaliação individual."""
    artists, coordinators, makeup = [], [], []
    for role in event.roles:
        if not role.talent_id or role.talent_id == talent.id or not role.talent:
            continue
        if role.role_type == "character":
            artists.append(role)
        elif role.role_type == "extra":
            name_lower = (role.character_name or "").lower()
            if "coordenador" in name_lower or "coord" in name_lower:
                coordinators.append(role)
            elif "maquiador" in name_lower or "maquiagem" in name_lower or "make" in name_lower:
                makeup.append(role)
    return {
        "artists": artists,
        "coordinators": coordinators,
        "makeup": makeup,
        "is_show": _is_show_event(event),
    }


@portal_bp.route("/events/<int:event_id>/rate", methods=["GET"])
@portal_login_required
def rate_event(event_id: int):
    talent = _current_talent()
    role = EventRole.query.filter(
        EventRole.event_id == event_id,
        EventRole.talent_id == talent.id,
        _not_rejected(),
    ).first_or_404()
    event = role.event

    if not _event_ended(event):
        flash("A avaliação abre depois que o evento terminar.", "error")
        return redirect(url_for("portal.home"))

    existing = EventRating.query.filter_by(event_id=event_id, talent_id=talent.id).first()
    ctx = _build_rating_context(talent, event)

    # Início de uma sessão de edição: guarda o baseline (estado atual) e limpa o flag de versão.
    if existing:
        session[f"rating_baseline_{event_id}"] = _snapshot_rating(existing)
        session.pop(f"rating_versioned_{event_id}", None)
    else:
        session.pop(f"rating_baseline_{event_id}", None)
        session.pop(f"rating_versioned_{event_id}", None)

    return render_template(
        "portal/rate.html",
        talent=talent,
        event=event,
        existing_rating=existing,
        **ctx,
    )


@portal_bp.route("/events/<int:event_id>/rate", methods=["POST"])
@portal_login_required
def submit_rating(event_id: int):
    talent = _current_talent()
    role = EventRole.query.filter(
        EventRole.event_id == event_id,
        EventRole.talent_id == talent.id,
        _not_rejected(),
    ).first_or_404()

    if not _event_ended(role.event):
        flash("A avaliação abre depois que o evento terminar.", "error")
        return redirect(url_for("portal.home"))

    score_raw = request.form.get("score", "")
    comment = request.form.get("comment", "").strip() or None
    try:
        score = int(score_raw)
        if not (1 <= score <= 5):
            raise ValueError
    except ValueError:
        flash("Por favor, selecione uma nota de 1 a 5 estrelas.", "error")
        return redirect(url_for("portal.rate_event", event_id=event_id))

    if score < 4 and not comment:
        flash("Para notas abaixo de 4 estrelas, é necessário deixar um comentário explicando o que aconteceu.", "error")
        return redirect(url_for("portal.rate_event", event_id=event_id))

    existing = EventRating.query.filter_by(event_id=event_id, talent_id=talent.id).first()
    if existing:
        existing.score = score
        existing.comment = comment
        _maybe_record_rating_version(event_id, existing)
    else:
        rating = EventRating(event_id=event_id, talent_id=talent.id, score=score, comment=comment)
        db.session.add(rating)

    db.session.commit()

    if request.form.get("skip_detail"):
        session.pop(f"rating_baseline_{event_id}", None)
        session.pop(f"rating_versioned_{event_id}", None)
        flash("Obrigado pela avaliação!", "success")
        return redirect(url_for("portal.home"))

    return redirect(url_for("portal.rate_event_detail", event_id=event_id))


@portal_bp.route("/events/<int:event_id>/rate/detail", methods=["GET", "POST"])
@portal_login_required
def rate_event_detail(event_id: int):
    talent = _current_talent()
    rating = EventRating.query.filter_by(event_id=event_id, talent_id=talent.id).first_or_404()
    event = rating.event

    if not _event_ended(event):
        flash("A avaliação abre depois que o evento terminar.", "error")
        return redirect(url_for("portal.home"))

    ctx = _build_rating_context(talent, event)

    if request.method == "GET":
        return render_template(
            "portal/rate_detail.html",
            talent=talent,
            event=event,
            rating=rating,
            **ctx,
        )

    # POST — salva sub-avaliações
    # Remove sub-ratings anteriores para re-envio limpo
    EventSubRating.query.filter_by(rating_id=rating.id).delete()

    categories = ["figurino"]
    if ctx["is_show"]:
        categories.extend(["som", "texto"])

    for cat in categories:
        score_raw = request.form.get(f"sub_{cat}_score", "")
        comment = request.form.get(f"sub_{cat}_comment", "").strip() or None
        if score_raw:
            try:
                score = int(score_raw)
                if 1 <= score <= 5:
                    db.session.add(EventSubRating(
                        rating_id=rating.id,
                        category=cat,
                        score=score,
                        comment=comment,
                    ))
            except ValueError:
                pass

    person_categories = [
        ("artista", ctx["artists"]),
        ("coordenacao", ctx["coordinators"]),
        ("maquiagem", ctx["makeup"]),
    ]
    for cat, roles in person_categories:
        for role in roles:
            score_raw = request.form.get(f"sub_{cat}_{role.talent_id}_score", "")
            comment = request.form.get(f"sub_{cat}_{role.talent_id}_comment", "").strip() or None
            if score_raw:
                try:
                    score = int(score_raw)
                    if 1 <= score <= 5:
                        db.session.add(EventSubRating(
                            rating_id=rating.id,
                            category=cat,
                            subject_talent_id=role.talent_id,
                            score=score,
                            comment=comment,
                        ))
                except ValueError:
                    pass

    rating.detail_submitted_at = datetime.utcnow()
    # Garante que rating.sub_ratings reflita o novo estado antes de comparar com o baseline.
    db.session.flush()
    db.session.refresh(rating)
    _maybe_record_rating_version(event_id, rating)
    db.session.commit()
    # Encerrou a sessão de edição deste evento — limpa o baseline/flag.
    session.pop(f"rating_baseline_{event_id}", None)
    session.pop(f"rating_versioned_{event_id}", None)
    flash("Obrigado! Sua avaliação completa foi enviada.", "success")
    return redirect(url_for("portal.home"))


# ── Esqueci a senha ────────────────────────────────────────────

@portal_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def forgot_password():
    if session.get("talent_id"):
        return redirect(url_for("portal.home"))

    sent = False
    error = None

    if request.method == "POST":
        cpf_raw = request.form.get("cpf", "")
        email   = request.form.get("email", "").strip().lower()
        cpf     = "".join(c for c in cpf_raw if c.isdigit())

        try:
            talent = Talent.query.filter_by(cpf=cpf).first()
            if (
                talent
                and talent.password_hash
                and talent.email_contact
                and talent.email_contact.strip().lower() == email
            ):
                token = secrets.token_urlsafe(32)
                # Lê atributos antes do commit (evita DetachedInstanceError no thread)
                talent_email = talent.email_contact
                talent_name  = talent.artistic_name or talent.full_name
                talent.password_reset_token = token
                talent.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
                db.session.commit()
                reset_url = url_for("portal.reset_password", token=token, _external=True)
                from types import SimpleNamespace
                _t = SimpleNamespace(email_contact=talent_email,
                                     artistic_name=None, full_name=talent_name)
                send_async(send_password_reset_email, _t, reset_url)
        except Exception:
            import logging as _log
            _log.getLogger(__name__).exception("Erro em forgot_password POST")
            db.session.rollback()

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
