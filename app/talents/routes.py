import os
import re
import unicodedata
from datetime import datetime, timedelta
from flask import Blueprint, redirect, url_for, render_template, request, flash, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, not_

from app.models import Talent, EventRole, CalendarEvent, ImportState, EventRating, EventSubRating
from .. import db
from app.constants import RoleName
from .importer import import_new_talents_from_sheet


def _can_edit_talent():
    return any(r.name in (RoleName.SUPERADMIN, RoleName.CASTING) for r in current_user.roles)

talents_bp = Blueprint("talents", __name__)

GOOGLE_FORM_URL = "https://forms.gle/iaZWqNpvtG5FUU3E7"
SERVICE_ACCOUNT_JSON = os.path.abspath(os.path.join("instance", "credentials", "sheets_service_account.json"))


def _get_sheet_config():
    from flask import current_app
    return (
        current_app.config.get("TALENTS_SPREADSHEET_ID", "1A_bXqUP21HR1RWS8AVBmj1oPgjhIWBaFfYxeqX17Ric"),
        current_app.config.get("TALENTS_SHEET_NAME", "Respostas"),
    )

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
    q = request.args.get("q", "").strip()
    ja_trabalhou = request.args.get("ja_trabalhou", "0" if filtrou else ("1" if status == "active" else "0"))
    query = Talent.query.filter_by(status=status)
    if q:
        query = query.filter(or_(
            Talent.full_name.ilike(f"%{q}%"),
            Talent.artistic_name.ilike(f"%{q}%"),
        ))
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
            for pv in passport:
                passport_filters.append(Talent.passport_status == pv)
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
            ("visa",     "passaporte + visto americano"),
            ("passport", "passaporte sem visto"),
            ("none",     "sem passaporte"),
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
    from datetime import datetime as _now_dt
    import_state = ImportState.query.filter_by(key="talents_form").first()
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
        q=q,
        character=character,
        character_matches=character_matches,
        import_state=import_state,
        now=_now_dt.utcnow(),
    )


# Ordem de exibição das categorias de sub-avaliação + rótulos pt-BR.
_RATING_CATEGORIES = [
    ("artista", "Artista"),
    ("som", "Som"),
    ("figurino", "Figurino"),
    ("texto", "Texto"),
    ("coordenacao", "Coordenação"),
    ("maquiagem", "Maquiagem"),
]


@talents_bp.route("/talents/avaliacoes")
@login_required
def avaliacoes():
    """Resumo das avaliações dos eventos — visão geral ou por evento."""
    if not _can_edit_talent():
        abort(403)

    event_id_raw = request.args.get("event_id", "").strip()
    event_id = int(event_id_raw) if event_id_raw.isdigit() else None

    # Eventos com ao menos uma avaliação (para o seletor).
    rated_event_rows = (
        db.session.query(CalendarEvent.id, CalendarEvent.title, CalendarEvent.start_at)
        .join(EventRating, EventRating.event_id == CalendarEvent.id)
        .group_by(CalendarEvent.id, CalendarEvent.title, CalendarEvent.start_at)
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )
    rated_events = [{"id": r.id, "title": r.title, "start_at": r.start_at} for r in rated_event_rows]

    selected_event = None
    ratings_q = EventRating.query
    subs_q = EventSubRating.query.join(EventRating, EventSubRating.rating_id == EventRating.id)
    if event_id:
        selected_event = CalendarEvent.query.get(event_id)
        ratings_q = ratings_q.filter(EventRating.event_id == event_id)
        subs_q = subs_q.filter(EventRating.event_id == event_id)

    ratings = ratings_q.order_by(EventRating.submitted_at.desc()).all()
    subs = subs_q.all()

    scores = [r.score for r in ratings if r.score]
    total = len(ratings)
    avg_overall = round(sum(scores) / len(scores), 1) if scores else 0.0
    events_rated = len({r.event_id for r in ratings})
    dist = {s: 0 for s in range(1, 6)}
    for s in scores:
        if 1 <= s <= 5:
            dist[s] += 1
    dist_max = max(dist.values()) if dist else 0

    by_category = []
    for key, label in _RATING_CATEGORIES:
        cat_scores = [s.score for s in subs if s.category == key and s.score]
        if cat_scores:
            by_category.append({
                "key": key,
                "label": label,
                "avg": round(sum(cat_scores) / len(cat_scores), 1),
                "count": len(cat_scores),
            })

    comments = []
    for r in ratings:
        if r.comment and r.comment.strip():
            comments.append({
                "score": r.score,
                "comment": r.comment.strip(),
                "author": r.talent.full_name if r.talent else "—",
                "event_title": r.event.title if r.event else "—",
                "event_id": r.event_id,
                "submitted_at": r.submitted_at,
            })
    if not event_id:
        comments = comments[:30]   # geral: limita para não poluir

    return render_template(
        "talents/avaliacoes.html",
        rated_events=rated_events,
        selected_event=selected_event,
        event_id=event_id,
        total=total,
        avg_overall=avg_overall,
        events_rated=events_rated,
        dist=dist,
        dist_max=dist_max,
        by_category=by_category,
        comments=comments,
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

    # Notas: avaliações recebidas POR este talento (como sujeito de sub-avaliação)
    received_sub_ratings = (
        EventSubRating.query
        .filter_by(subject_talent_id=talent.id)
        .join(EventRating, EventSubRating.rating_id == EventRating.id)
        .order_by(EventRating.submitted_at.desc())
        .all()
    )
    # Avaliações gerais feitas por este talento (como avaliador)
    given_ratings = (
        EventRating.query
        .filter_by(talent_id=talent.id)
        .order_by(EventRating.submitted_at.desc())
        .all()
    )

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
        received_sub_ratings=received_sub_ratings,
        given_ratings=given_ratings,
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
        ps = f.get("passport_status", "").strip()
        talent.passport_status      = ps if ps in ("visa", "passport", "none") else None
        talent.has_visa             = talent.passport_status == "visa"  # manter sincronizado
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
    from datetime import datetime as _dt
    spreadsheet_id, sheet_name = _get_sheet_config()
    try:
        result = import_new_talents_from_sheet(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            credentials_path=SERVICE_ACCOUNT_JSON,
        )
        imported = result.get("imported", 0)
        # Atualiza registro de sync manual
        state = ImportState.query.filter_by(key="talents_form").first()
        if state:
            state.last_checked_at = _dt.utcnow()
            state.last_import_count = imported
            db.session.commit()
        flash(f"Import finalizado: {imported} novo(s), {result.get('skipped', 0)} ignorado(s).")
        for item in result.get("skipped_details", []):
            flash(f"Ignorado (linha {item['linha']}): {item['nome']} — {item['motivo']}", "warning")
    except FileNotFoundError:
        flash("Credenciais do Google Sheets não encontradas.", "error")
    except Exception as e:
        flash(f"Erro ao importar: {e}", "error")
    return redirect(url_for("talents.list_talents", status="active"))
