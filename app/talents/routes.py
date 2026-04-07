import os
import re
import unicodedata
from datetime import datetime, timedelta
from flask import Blueprint, redirect, url_for, render_template, request, flash, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, not_

from app.models import Talent, EventRole, CalendarEvent
from .. import db
from app.constants import RoleName
from .importer import import_new_talents_from_sheet


def _can_edit_talent():
    return any(r.name in (RoleName.SUPERADMIN, RoleName.CASTING) for r in current_user.roles)

talents_bp = Blueprint("talents", __name__)

# CONFIG (você vai preencher)
GOOGLE_FORM_URL = "https://forms.gle/iaZWqNpvtG5FUU3E7"
SPREADSHEET_ID = "1A_bXqUP21HR1RWS8AVBmj1oPgjhIWBaFfYxeqX17Ric"
SHEET_NAME = "Respostas"
SERVICE_ACCOUNT_JSON = os.path.abspath(os.path.join("instance", "credentials", "sheets_service_account.json"))

@talents_bp.route("/talents/add")
@login_required
def add_talent():
    return redirect(GOOGLE_FORM_URL)

@talents_bp.route("/talents")
@login_required
def list_talents():
    status = request.args.get("status", "active")
    # filtrou=1 indica que o form foi submetido; sem ele é visita fresca (default ativo)
    filtrou = request.args.get("filtrou", "0") == "1"
    ja_trabalhou = request.args.get("ja_trabalhou", "0" if filtrou else ("1" if status == "active" else "0"))
    query = Talent.query.filter_by(status=status)
    if ja_trabalhou == "1":
        query = query.filter(Talent.worked_before.is_(True))

    def normalize_header(value: str) -> str:
        text = (value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def split_values(raw: str) -> list:
        if not raw:
            return []
        parts = re.split(r"[;,/\n]+", raw)
        return [p.strip() for p in parts if p and p.strip()]

    if status == "active":
        languages = request.args.getlist("language")
        races = request.args.getlist("race")
        tops = request.args.getlist("top")
        bottoms = request.args.getlist("bottom")
        shoes = request.args.getlist("shoe")
        passport = request.args.getlist("passport")
        character = request.args.get("character", "").strip()

        # Tag: suporta múltiplos valores OU texto único com vírgulas
        raw_tags = request.args.getlist("tag")
        tags = []
        for t in raw_tags:
            tags.extend(split_values(t))

        height_op = request.args.get("height_op", "gte")
        height_value = request.args.get("height_value")

        if languages:
            lang_filters = [Talent.languages.ilike(f"%{l}%") for l in languages]
            query = query.filter(or_(*lang_filters))

        if races:
            query = query.filter(Talent.race.in_(races))

        if tops:
            query = query.filter(Talent.clothing_size_top.in_(tops))

        if bottoms:
            query = query.filter(Talent.clothing_size_bottom.in_(bottoms))

        if shoes:
            query = query.filter(Talent.shoe_size.in_(shoes))

        if height_value:
            try:
                height_num = int(height_value)
                if height_op == "gte":
                    query = query.filter(Talent.height_cm >= height_num)
                elif height_op == "lte":
                    query = query.filter(Talent.height_cm <= height_num)
            except ValueError:
                pass

        if passport:
            passport_filters = []
            if "visa" in passport:
                passport_filters.append(Talent.has_visa.is_(True))
            if "passaporte" in passport:
                passport_filters.append(
                    and_(
                        or_(Talent.has_visa.is_(False), Talent.has_visa.is_(None)),
                        or_(
                            Talent.passport_visa_text.ilike("%passap%"),
                            Talent.passport_visa_text.ilike("%passport%"),
                        ),
                    )
                )
            if "nenhum" in passport:
                passport_filters.append(
                    and_(
                        or_(Talent.has_visa.is_(False), Talent.has_visa.is_(None)),
                        not_(Talent.passport_visa_text.ilike("%passap%")),
                        not_(Talent.passport_visa_text.ilike("%passport%")),
                    )
                )
            if passport_filters:
                query = query.filter(or_(*passport_filters))

        if tags:
            normalized = [normalize_header(t) for t in tags]
            tag_filters = [Talent.tags.ilike(f"%{t}%") for t in normalized if t]
            if tag_filters:
                query = query.filter(or_(*tag_filters))

        # Filtro por personagem (busca no histórico de EventRole)
        character_matches: dict = {}
        if character:
            matching_roles = (
                EventRole.query
                .filter(
                    EventRole.character_name.ilike(f"%{character}%"),
                    EventRole.assigned_at.isnot(None),
                    EventRole.talent_id.isnot(None),
                )
                .all()
            )
            matching_ids = {r.talent_id for r in matching_roles}
            query = query.filter(Talent.id.in_(matching_ids)) if matching_ids else query.filter(False)
            for r in matching_roles:
                bucket = character_matches.setdefault(r.talent_id, {})
                bucket[r.character_name] = bucket.get(r.character_name, 0) + 1

        all_active = Talent.query.filter_by(status="active").all()
        language_options = sorted({p for t in all_active for p in split_values(t.languages or "")})
        race_options = sorted({t.race for t in all_active if t.race})
        tag_options = sorted({p for t in all_active for p in split_values(t.tags or "")})
        size_options = ["XGG", "GG", "G", "M", "P", "XP"]
        shoe_options = [str(n) for n in range(33, 48)]
        passport_options = [
            ("visa", "com visto e passaporte"),
            ("passaporte", "com passaporte sem visto"),
            ("nenhum", "sem nenhum dos dois"),
        ]
    else:
        language_options = []
        race_options = []
        tag_options = []
        size_options = []
        shoe_options = []
        passport_options = []
        character = ""
        character_matches = {}

    PAGE_SIZE = 60
    page = max(1, request.args.get("page", 1, type=int))
    pagination = query.order_by(Talent.full_name.asc()).paginate(
        page=page, per_page=PAGE_SIZE, error_out=False
    )
    people = pagination.items
    return render_template(
        "talents_list.html",
        people=people,
        pagination=pagination,
        status=status,
        ja_trabalhou=ja_trabalhou,
        language_options=language_options,
        race_options=race_options,
        tag_options=tag_options,
        size_options_top=size_options,
        size_options_bottom=size_options,
        shoe_options=shoe_options,
        passport_options=passport_options,
        character=character,
        character_matches=character_matches,
    )

@talents_bp.route("/talents/<int:talent_id>")
@login_required
def talent_detail(talent_id: int):
    talent = Talent.query.get_or_404(talent_id)

    date_from_str = request.args.get("date_from", "")
    date_to_str   = request.args.get("date_to",   "")

    date_from = None
    date_to   = None
    try:
        if date_from_str:
            date_from = datetime.fromisoformat(date_from_str)
    except ValueError:
        pass
    try:
        if date_to_str:
            date_to = datetime.fromisoformat(date_to_str) + timedelta(days=1)
    except ValueError:
        pass

    hist_q = (
        EventRole.query
        .filter(EventRole.talent_id == talent.id)
        .join(CalendarEvent)
        .filter(EventRole.assigned_at.isnot(None))
        .order_by(CalendarEvent.start_at.desc())
    )
    if date_from:
        hist_q = hist_q.filter(CalendarEvent.start_at >= date_from)
    if date_to:
        hist_q = hist_q.filter(CalendarEvent.start_at < date_to)

    history = hist_q.all()

    total_events    = len({r.event_id for r in history})
    total_earned    = sum(r.cache_value or 0 for r in history)
    characters_done = sorted({r.character_name for r in history})

    return render_template(
        "talent_detail.html",
        talent=talent,
        history=history,
        total_events=total_events,
        total_earned=total_earned,
        characters_done=characters_done,
        date_from=date_from_str,
        date_to=date_to_str,
        can_edit=_can_edit_talent(),
    )

@talents_bp.route("/talents/<int:talent_id>/edit", methods=["GET", "POST"])
@login_required
def edit_talent(talent_id: int):
    if not _can_edit_talent():
        abort(403)
    talent = Talent.query.get_or_404(talent_id)

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
        talent.tags                 = f.get("tags", "").strip() or None
        talent.pix_key              = f.get("pix_key", "").strip() or None
        talent.pix_key_secondary    = f.get("pix_key_secondary", "").strip() or None
        talent.pix_key_type         = f.get("pix_key_type", "").strip() or None
        talent.rg                   = f.get("rg", "").strip() or None
        talent.passport_visa_text   = f.get("passport_visa_text", "").strip() or None
        talent.has_visa             = f.get("has_visa") == "1"
        talent.how_found_us         = f.get("how_found_us", "").strip() or None
        talent.worked_before        = f.get("worked_before") == "1" if f.get("worked_before") != "" else None
        talent.car_brand            = f.get("car_brand", "").strip() or None
        talent.car_model            = f.get("car_model", "").strip() or None
        talent.car_year             = f.get("car_year", "").strip() or None
        talent.car_plate            = f.get("car_plate", "").strip() or None

        try:
            talent.height_cm = int(f.get("height_cm")) if f.get("height_cm") else None
        except ValueError:
            pass

        talent.clothing_size_top    = f.get("clothing_size_top", "").strip() or None
        talent.clothing_size_bottom = f.get("clothing_size_bottom", "").strip() or None
        talent.shoe_size            = f.get("shoe_size", "").strip() or None

        from datetime import date as date_type
        from app.talents.importer import parse_date
        talent.birth_date    = parse_date(f.get("birth_date", ""))
        talent.cnh_expiration = parse_date(f.get("cnh_expiration", ""))

        from app.utils import audit
        audit("edit", "talent", talent.id, talent.full_name, "Perfil editado")
        db.session.commit()
        flash("Talento atualizado com sucesso.", "success")
        return redirect(url_for("talents.talent_detail", talent_id=talent.id))

    return render_template("talent_edit.html", talent=talent)


@talents_bp.route("/talents/character-suggestions")
@login_required
def character_suggestions():
    from sqlalchemy import func as sqlfunc
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])
    rows = (
        db.session.query(EventRole.character_name, sqlfunc.count(EventRole.id).label("cnt"))
        .filter(
            EventRole.character_name.ilike(f"%{q}%"),
            EventRole.assigned_at.isnot(None),
            EventRole.talent_id.isnot(None),
        )
        .group_by(EventRole.character_name)
        .order_by(sqlfunc.count(EventRole.id).desc())
        .limit(10)
        .all()
    )
    return jsonify([{"name": r.character_name, "count": r.cnt} for r in rows])


@talents_bp.route("/talents/<int:talent_id>/upload-photo", methods=["POST"])
@login_required
def upload_talent_photo(talent_id: int):
    if not _can_edit_talent():
        abort(403)
    import uuid as _uuid
    from werkzeug.utils import secure_filename
    from app.storage import save_file
    talent = Talent.query.get_or_404(talent_id)
    photo_type = request.form.get("photo_type", "face")  # 'face' ou 'full'
    file = request.files.get("photo")
    if not file or not file.filename:
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("talents.talent_detail", talent_id=talent_id))
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        flash("Formato não suportado. Use JPG, PNG ou WEBP.", "error")
        return redirect(url_for("talents.talent_detail", talent_id=talent_id))
    filename = f"talent_{talent_id}_{photo_type}_{_uuid.uuid4().hex[:8]}{ext}"
    url_path = save_file(file, "talent_photos", filename)
    if photo_type == "full":
        talent.photo_full_path = url_path
    else:
        talent.photo_face_path = url_path
    db.session.commit()
    flash("Foto atualizada.", "success")
    return redirect(url_for("talents.talent_detail", talent_id=talent_id))


@talents_bp.route("/talents/<int:talent_id>/reset-password", methods=["POST"])
@login_required
def reset_talent_password(talent_id: int):
    if not _can_edit_talent():
        abort(403)
    import secrets, string
    from app.email_service import send_welcome_email
    talent = Talent.query.get_or_404(talent_id)
    alphabet = string.ascii_letters + string.digits
    new_pw = "".join(secrets.choice(alphabet) for _ in range(8))
    talent.set_password(new_pw)
    talent.must_change_password = True
    db.session.commit()
    email_sent = send_welcome_email(talent, new_pw)
    msg = f"Senha resetada. Nova senha temporária: {new_pw}"
    if email_sent:
        msg += f" — Email enviado para {talent.email_contact}."
    elif talent.email_contact:
        msg += " (falha no envio do email — anote a senha acima)"
    else:
        msg += " (sem email cadastrado — anote a senha acima)"
    flash(msg, "success")
    return redirect(url_for("talents.talent_detail", talent_id=talent_id))


@talents_bp.route("/talents/import", methods=["POST"])
@login_required
def import_talents():
    result = import_new_talents_from_sheet(
        spreadsheet_id=SPREADSHEET_ID,
        sheet_name=SHEET_NAME,
        credentials_path=SERVICE_ACCOUNT_JSON,
    )
    flash(f"Import finalizado: {result.get('imported', 0)} novos, {result.get('skipped', 0)} ignorados.")
    return redirect(url_for("talents.list_talents", status="active"))
