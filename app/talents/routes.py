import os
import re
import unicodedata
from flask import Blueprint, redirect, url_for, render_template, request, flash
from flask_login import login_required
from sqlalchemy import or_, and_, not_

from app.models import Talent
from .. import db
from .importer import import_new_talents_from_sheet

talents_bp = Blueprint("talents", __name__)

# CONFIG (você vai preencher)
GOOGLE_FORM_URL = "https://forms.gle/iaZWqNpvtG5FUU3E7"
SPREADSHEET_ID = "1A_bXqUP21HR1RWS8AVBmj1oPgjhIWBaFfYxeqX17Ric"
SHEET_NAME = "Respostas" 
SERVICE_ACCOUNT_JSON = os.path.abspath(os.path.join("instance", "credentials", "sheets_service_account.json"))

@talents_bp.route("/talents/add")
@login_required
def add_talent():
    # ÚNICA forma de adicionar: abre o Google Form
    return redirect(GOOGLE_FORM_URL)

@talents_bp.route("/talents")
@login_required
def list_talents():
    status = request.args.get("status", "active")
    query = Talent.query.filter_by(status=status)

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
        # filters
        languages = request.args.getlist("language")
        races = request.args.getlist("race")
        tops = request.args.getlist("top")
        bottoms = request.args.getlist("bottom")
        shoes = request.args.getlist("shoe")
        passport = request.args.getlist("passport")
        tags = request.args.getlist("tag")

        height_op = request.args.get("height_op")
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
                if height_op == "gt":
                    query = query.filter(Talent.height_cm >= height_num)
                elif height_op == "lt":
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

        # options for filters
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

    people = query.order_by(Talent.full_name.asc()).all()
    return render_template(
        "talents_list.html",
        people=people,
        status=status,
        language_options=language_options,
        race_options=race_options,
        tag_options=tag_options,
        size_options=size_options,
        shoe_options=shoe_options,
        passport_options=passport_options,
    )

@talents_bp.route("/talents/<int:talent_id>")
@login_required
def talent_detail(talent_id: int):
    person = Talent.query.get_or_404(talent_id)
    return render_template("talent_detail.html", person=person)

@talents_bp.route("/talents/import", methods=["POST"])
@login_required
def import_talents():
    result = import_new_talents_from_sheet(
        spreadsheet_id=SPREADSHEET_ID,
        sheet_name=SHEET_NAME,
        credentials_path=SERVICE_ACCOUNT_JSON,
    )

    flash(f"Import finalizado: {result.get('imported', 0)} novos, {result.get('skipped', 0)} ignorados.")
    return redirect(url_for("talents.list_talents", status="pending"))

@talents_bp.route("/talents/<int:talent_id>/approve", methods=["POST"])
@login_required
def approve_talent(talent_id: int):
    t = Talent.query.get_or_404(talent_id)
    t.status = "active"
    db.session.commit()
    return redirect(url_for("talents.list_talents", status="active"))
