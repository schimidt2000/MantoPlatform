import os
import re
import unicodedata
from datetime import datetime, timedelta
from flask import Blueprint, redirect, url_for, render_template, request, flash, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.models import Talent, EventRole, CalendarEvent, ImportState, EventRating, EventSubRating
from .. import db
from app.constants import RoleName
from . import rating_ops
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
    pending_count = Talent.query.filter_by(status="pending").count()
    return render_template(
        "talents_list.html",
        people=people,
        pagination=pagination,
        status=status,
        pending_count=pending_count,
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


# Reexportada — app/clientes/client_ops.py importa `_parse_period` diretamente deste módulo.
_parse_period = rating_ops.parse_period


@talents_bp.route("/talents/avaliacoes")
@login_required
def avaliacoes():
    """Resumo das avaliações — filtros combináveis de período, categoria e evento.

    Visível a todos os usuários autenticados; a autoria fica anônima para todos,
    exceto super admin (salvo modo anônimo total) — ver feature 056.
    """
    is_sa = rating_ops.is_superadmin(current_user)
    overview = rating_ops.build_overview(request.args, is_sa)
    return render_template("talents/avaliacoes.html", is_superadmin=is_sa, **overview)


@talents_bp.route("/talents/avaliacoes/modo-anonimo", methods=["POST"])
@login_required
def toggle_modo_anonimo():
    """Liga/desliga o modo anônimo total das avaliações (só super admin) — feature 056."""
    if not rating_ops.is_superadmin(current_user):
        abort(403)
    enabled = request.form.get("enabled") == "1"
    rating_ops.set_anonymous_mode(enabled, current_user)
    flash(
        "Modo anônimo total ativado — nem o super admin vê a autoria."
        if enabled else
        "Modo anônimo total desativado — o super admin volta a ver a autoria.",
        "success",
    )
    return redirect(url_for("talents.avaliacoes"))


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


@talents_bp.route("/talents/<int:talent_id>/notes", methods=["POST"])
@login_required
def save_talent_notes(talent_id: int):
    """Salva anotações internas e o nível de alerta do talento (uso interno)."""
    if not _can_edit_talent():
        abort(403)
    talent = Talent.query.get_or_404(talent_id)
    from app.talents.talent_ops import save_notes

    save_notes(
        talent, notes=request.form.get("notes", ""), warning_level=request.form.get("warning_level", "")
    )
    db.session.commit()
    flash("Anotações salvas.", "success")
    return redirect(url_for("talents.talent_detail", talent_id=talent.id))


@talents_bp.route("/talents/<int:talent_id>/edit", methods=["GET", "POST"])
@login_required
def edit_talent(talent_id: int):
    if not _can_edit_talent():
        abort(403)
    talent = Talent.query.get_or_404(talent_id)
    is_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)

    if request.method == "POST":
        f = request.form
        from app.talents.talent_ops import update_talent_fields

        data = {
            "cpf": f.get("cpf", ""),
            "full_name": f.get("full_name", ""),
            "artistic_name": f.get("artistic_name", ""),
            "phone": f.get("phone", ""),
            "email_contact": f.get("email_contact", ""),
            "gender": f.get("gender", ""),
            "race": f.get("race", ""),
            "languages": f.get("languages", ""),
            "skills": f.get("skills", ""),
            "tags": f.get("tags", ""),
            "pix_key": f.get("pix_key", ""),
            "pix_key_secondary": f.get("pix_key_secondary", ""),
            "pix_key_type": f.get("pix_key_type", ""),
            "rg": f.get("rg", ""),
            "passport_status": f.get("passport_status", ""),
            "how_found_us": f.get("how_found_us", ""),
            "worked_before": f.get("worked_before"),
            "car_brand": f.get("car_brand", ""),
            "car_model": f.get("car_model", ""),
            "car_year": f.get("car_year", ""),
            "car_plate": f.get("car_plate", ""),
            "height_cm": f.get("height_cm", ""),
            "clothing_size_top": f.get("clothing_size_top", ""),
            "clothing_size_bottom": f.get("clothing_size_bottom", ""),
            "shoe_size": f.get("shoe_size", ""),
            "birth_date": f.get("birth_date", ""),
            "cnh_expiration": f.get("cnh_expiration", ""),
        }
        cpf_before = talent.cpf
        errors = update_talent_fields(talent, data, is_superadmin=is_superadmin)
        if errors:
            flash(next(iter(errors.values())), "error")
            return render_template("talent_edit.html", talent=talent, is_superadmin=is_superadmin)

        from app.utils import audit
        audit("edit", "talent", talent.id, talent.full_name,
              "Perfil editado" + ("; CPF alterado" if talent.cpf != cpf_before else ""))
        db.session.commit()
        flash("Talento atualizado com sucesso.", "success")
        return redirect(url_for("talents.talent_detail", talent_id=talent.id))

    return render_template("talent_edit.html", talent=talent, is_superadmin=is_superadmin)


@talents_bp.route("/talents/character-suggestions")
@login_required
def character_suggestions():
    from app.talents.talent_ops import suggest_characters

    return jsonify(suggest_characters(request.args.get("q", "")))


@talents_bp.route("/talents/<int:talent_id>/upload-photo", methods=["POST"])
@login_required
def upload_talent_photo(talent_id: int):
    if not _can_edit_talent():
        abort(403)
    from app.talents.talent_ops import save_talent_photo

    talent = Talent.query.get_or_404(talent_id)
    photo_type = request.form.get("photo_type", "face")  # 'face' | 'full' | 'doc' | 'cnh'
    file = request.files.get("photo")
    error = save_talent_photo(talent, photo_type=photo_type, file_storage=file)
    if error:
        flash(error, "error")
        return redirect(url_for("talents.talent_detail", talent_id=talent_id))
    db.session.commit()
    is_doc = photo_type in ("doc", "cnh")
    flash("Documento atualizado." if is_doc else "Foto atualizada.", "success")
    return redirect(url_for("talents.talent_detail", talent_id=talent_id))


@talents_bp.route("/talents/<int:talent_id>/remove-photo", methods=["POST"])
@login_required
def remove_talent_photo_route(talent_id: int):
    if not _can_edit_talent():
        abort(403)
    from app.talents.talent_ops import remove_talent_photo

    talent = Talent.query.get_or_404(talent_id)
    photo_type = request.form.get("photo_type", "face")
    error = remove_talent_photo(talent, photo_type=photo_type)
    if error:
        flash(error, "error")
    else:
        db.session.commit()
        flash("Removido.", "success")
    return redirect(url_for("talents.talent_detail", talent_id=talent_id))


@talents_bp.route("/talents/<int:talent_id>/approve", methods=["POST"])
@login_required
def approve_talent(talent_id: int):
    """Aprova um cadastro pendente (do formulário público), tornando-o ativo no banco."""
    if not _can_edit_talent():
        abort(403)
    talent = Talent.query.get_or_404(talent_id)
    from app.talents.talent_ops import approve_talent_status

    approve_talent_status(talent)
    db.session.commit()
    flash(f"{talent.full_name} aprovado(a) e adicionado(a) ao banco.", "success")
    return redirect(request.referrer or url_for("talents.list_talents", status="pending"))


@talents_bp.route("/talents/<int:talent_id>/reject", methods=["POST"])
@login_required
def reject_talent(talent_id: int):
    """Rejeita/exclui um cadastro pendente."""
    if not _can_edit_talent():
        abort(403)
    talent = Talent.query.get_or_404(talent_id)
    name = talent.full_name
    from app.talents.talent_ops import reject_talent_record

    if not reject_talent_record(talent):
        flash("Só é possível rejeitar cadastros pendentes.", "error")
        return redirect(url_for("talents.talent_detail", talent_id=talent_id))
    db.session.commit()
    flash(f"Cadastro de {name} rejeitado e removido.", "success")
    return redirect(url_for("talents.list_talents", status="pending"))


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
