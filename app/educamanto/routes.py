"""EducaManto — Motor de orçamentos por pacote musical."""
import json
from functools import wraps

from flask import (
    Blueprint, abort, flash, redirect,
    render_template, request, url_for,
)
from flask_login import current_user, login_required

from app import db
from app.constants import RoleName
from app.models import EducaMantoItem, EducaMantoPackage

educamanto_bp = Blueprint("educamanto", __name__, url_prefix="/educamanto")

_CAN_USE    = {RoleName.COMERCIAL, RoleName.SUPERADMIN}
_CAN_MANAGE = {RoleName.SUPERADMIN}

_DEFAULT_ITEMS = [
    # (name, qty, cost_1s, cost_2s, cost_1s_days, cost_2s_days)
    ("Cara Limpa",              3, 400,  650,  350,  600),
    ("Bonecos",                 6, 350,  600,  300,  550),
    ("Produção",                2, 350,  600,  300,  550),
    ("Som",                     1, 4000, 4000, 3500, 3500),
    ("Cenógrafo",               1,   0,    0,    0,    0),
    ("Transporte",              1, 600,  600,  600,  600),
    ("Foto e vídeo",            1,   0,    0,    0,    0),
    ("Catering ensaio",         1, 300,  300,  300,  300),
    ("Catering apresentação",   1, 600,  800,  600,  800),
    ("Ajuda de custo ensaio",  11,  50,   50,   50,   50),
    ("Gráfica",                 1, 300,  500,  300,  500),
]


def _require_use(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not {r.name.upper() for r in current_user.roles} & _CAN_USE:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _require_manage(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not {r.name.upper() for r in current_user.roles} & _CAN_MANAGE:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _seed_default_package() -> None:
    """Cria 'Uma Aventura Animal' se ainda não houver nenhum pacote."""
    if EducaMantoPackage.query.count() > 0:
        return
    pkg = EducaMantoPackage(
        name="Uma Aventura Animal",
        margin_1s=1.41, margin_2s=1.70,
        margin_1s_days=1.50, margin_2s_days=1.80,
        discount_days=2, discount_pct=0.05,
        commission_rate=0.05,
    )
    db.session.add(pkg)
    db.session.flush()
    for i, (name, qty, c1s, c2s, c1sd, c2sd) in enumerate(_DEFAULT_ITEMS):
        db.session.add(EducaMantoItem(
            package_id=pkg.id, name=name, qty=qty,
            cost_1s=c1s, cost_2s=c2s,
            cost_1s_days=c1sd, cost_2s_days=c2sd,
            sort_order=i,
        ))
    db.session.commit()


def _parse_items_from_form() -> list[dict]:
    names     = request.form.getlist("item_name[]")
    qtys      = request.form.getlist("item_qty[]")
    c1s_list  = request.form.getlist("item_cost_1s[]")
    c2s_list  = request.form.getlist("item_cost_2s[]")
    c1sd_list = request.form.getlist("item_cost_1s_days[]")
    c2sd_list = request.form.getlist("item_cost_2s_days[]")
    items = []
    for i, name in enumerate(names):
        if not name.strip():
            continue
        items.append({
            "name": name.strip(),
            "qty": int(qtys[i] or 1),
            "cost_1s": float(c1s_list[i] or 0),
            "cost_2s": float(c2s_list[i] or 0),
            "cost_1s_days": float(c1sd_list[i] or 0),
            "cost_2s_days": float(c2sd_list[i] or 0),
            "sort_order": i,
        })
    return items


@educamanto_bp.route("/")
@login_required
@_require_use
def index():
    _seed_default_package()
    packages = EducaMantoPackage.query.order_by(EducaMantoPackage.id).all()
    active_id = request.args.get("pkg", type=int) or (packages[0].id if packages else None)
    packages_json = json.dumps([p.to_dict() for p in packages])
    can_manage = bool({r.name.upper() for r in current_user.roles} & _CAN_MANAGE)
    return render_template(
        "educamanto/index.html",
        packages=packages,
        active_id=active_id,
        packages_json=packages_json,
        can_manage=can_manage,
    )


@educamanto_bp.route("/packages/create", methods=["GET", "POST"])
@login_required
@_require_manage
def create_package():
    if request.method == "POST":
        pkg = EducaMantoPackage(
            name=request.form["name"].strip(),
            margin_1s=float(request.form["margin_1s"]),
            margin_2s=float(request.form["margin_2s"]),
            margin_1s_days=float(request.form["margin_1s_days"]),
            margin_2s_days=float(request.form["margin_2s_days"]),
            discount_days=int(request.form["discount_days"]),
            discount_pct=float(request.form["discount_pct"]) / 100,
            commission_rate=float(request.form["commission_rate"]) / 100,
        )
        db.session.add(pkg)
        db.session.flush()
        for item_data in _parse_items_from_form():
            db.session.add(EducaMantoItem(package_id=pkg.id, **item_data))
        db.session.commit()
        flash("Pacote criado com sucesso.", "success")
        return redirect(url_for("educamanto.index", pkg=pkg.id))
    return render_template("educamanto/package_form.html", package=None)


@educamanto_bp.route("/packages/<int:pkg_id>/edit", methods=["GET", "POST"])
@login_required
@_require_manage
def edit_package(pkg_id: int):
    pkg = EducaMantoPackage.query.get_or_404(pkg_id)
    if request.method == "POST":
        pkg.name = request.form["name"].strip()
        pkg.margin_1s = float(request.form["margin_1s"])
        pkg.margin_2s = float(request.form["margin_2s"])
        pkg.margin_1s_days = float(request.form["margin_1s_days"])
        pkg.margin_2s_days = float(request.form["margin_2s_days"])
        pkg.discount_days = int(request.form["discount_days"])
        pkg.discount_pct = float(request.form["discount_pct"]) / 100
        pkg.commission_rate = float(request.form["commission_rate"]) / 100
        for item in list(pkg.items):
            db.session.delete(item)
        db.session.flush()
        for item_data in _parse_items_from_form():
            db.session.add(EducaMantoItem(package_id=pkg.id, **item_data))
        db.session.commit()
        flash("Pacote atualizado com sucesso.", "success")
        return redirect(url_for("educamanto.index", pkg=pkg.id))
    return render_template("educamanto/package_form.html", package=pkg)


@educamanto_bp.route("/packages/<int:pkg_id>/delete", methods=["POST"])
@login_required
@_require_manage
def delete_package(pkg_id: int):
    pkg = EducaMantoPackage.query.get_or_404(pkg_id)
    db.session.delete(pkg)
    db.session.commit()
    flash(f'Pacote "{pkg.name}" removido.', "success")
    return redirect(url_for("educamanto.index"))
