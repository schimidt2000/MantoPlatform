"""EducaManto — Motor de orçamentos por pacote musical."""
from functools import wraps

from flask import (
    Blueprint, abort, flash, jsonify, redirect,
    render_template, request, url_for,
)
from flask_login import current_user, login_required

from app import db
from app.constants import RoleName
from app.money import parse_brl
from app.models import EducaMantoItem, EducaMantoPackage
from app.utils import json_for_script

educamanto_bp = Blueprint("educamanto", __name__, url_prefix="/educamanto")


def _money(value, default: float) -> float:
    """Lê um valor em R$ (mascarado ou cru) como float; usa o default só se vazio/inválido.

    Diferente de ``parse_brl(x) or default``, preserva o zero explícito (R$ 0,00).
    """
    parsed = parse_brl(value)
    return float(parsed) if parsed is not None else float(default)

_CAN_USE      = {RoleName.COMERCIAL, RoleName.SUPERADMIN, RoleName.ENSAIO}
# ENSAIO usa só a calculadora — não vê a aba de pacotes.
_CAN_PACKAGES = {RoleName.COMERCIAL, RoleName.SUPERADMIN}
_CAN_MANAGE   = {RoleName.SUPERADMIN}

_DEFAULT_ITEMS = [
    # (name, qty, cost_1s, cost_2s, cost_1s_days, cost_2s_days, ensemble_add)
    # Catering é POR PESSOA (qty = headcount do elenco = 11); cresce com ensemble.
    ("Cara Limpa",              3, 400,  650,  350,  600, 0),
    ("Bonecos",                 6, 350,  600,  300,  550, 0),
    ("Produção",                2, 350,  600,  300,  550, 0),
    ("Som",                     1, 4000, 4000, 3500, 3500, 0),
    ("Cenógrafo",               1,   0,    0,    0,    0, 0),
    ("Transporte",              1, 600,  600,  600,  600, 0),
    ("Foto e vídeo",            1,   0,    0,    0,    0, 0),
    ("Catering ensaio",        11,  28,   28,   28,   28, 1),
    ("Catering apresentação",  11,  55,   73,   55,   73, 1),
    ("Ajuda de custo ensaio",  11,  50,   50,   50,   50, 1),
    ("Gráfica",                 1, 300,  500,  300,  500, 0),
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


def _require_packages(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not {r.name.upper() for r in current_user.roles} & _CAN_PACKAGES:
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
    for i, (name, qty, c1s, c2s, c1sd, c2sd, ens_add) in enumerate(_DEFAULT_ITEMS):
        db.session.add(EducaMantoItem(
            package_id=pkg.id, name=name, qty=qty,
            cost_1s=c1s, cost_2s=c2s,
            cost_1s_days=c1sd, cost_2s_days=c2sd,
            ensemble_add=ens_add,
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
    ens_list  = request.form.getlist("item_ensemble_add[]")
    items = []
    for i, name in enumerate(names):
        if not name.strip():
            continue
        items.append({
            "name": name.strip(),
            "qty": int(qtys[i] or 1),
            "cost_1s": _money(c1s_list[i], 0),
            "cost_2s": _money(c2s_list[i], 0),
            "cost_1s_days": _money(c1sd_list[i], 0),
            "cost_2s_days": _money(c2sd_list[i], 0),
            "ensemble_add": int(ens_list[i] or 0) if i < len(ens_list) else 0,
            "sort_order": i,
        })
    return items


@educamanto_bp.route("/packages")
@login_required
@_require_packages
def packages_list():
    _seed_default_package()
    packages = EducaMantoPackage.query.order_by(EducaMantoPackage.id).all()
    can_manage = bool({r.name.upper() for r in current_user.roles} & _CAN_MANAGE)
    return render_template("educamanto/packages.html", packages=packages, can_manage=can_manage)


@educamanto_bp.route("/packages/<int:pkg_id>/duplicate", methods=["POST"])
@login_required
@_require_manage
def duplicate_package(pkg_id: int):
    original = EducaMantoPackage.query.get_or_404(pkg_id)
    copy = EducaMantoPackage(
        name=f"Cópia de {original.name}",
        margin_1s=original.margin_1s,
        margin_2s=original.margin_2s,
        margin_1s_days=original.margin_1s_days,
        margin_2s_days=original.margin_2s_days,
        discount_days=original.discount_days,
        discount_pct=original.discount_pct,
        commission_rate=original.commission_rate,
    )
    db.session.add(copy)
    db.session.flush()
    for item in original.items:
        db.session.add(EducaMantoItem(
            package_id=copy.id,
            name=item.name,
            qty=item.qty,
            cost_1s=item.cost_1s,
            cost_2s=item.cost_2s,
            cost_1s_days=item.cost_1s_days,
            cost_2s_days=item.cost_2s_days,
            sort_order=item.sort_order,
        ))
    db.session.commit()
    flash(f'Cópia de "{original.name}" criada. Edite o nome e os parâmetros abaixo.', "success")
    return redirect(url_for("educamanto.edit_package", pkg_id=copy.id))


@educamanto_bp.route("/")
@login_required
@_require_use
def index():
    _seed_default_package()
    packages = EducaMantoPackage.query.order_by(EducaMantoPackage.id).all()
    active_id = request.args.get("pkg", type=int) or (packages[0].id if packages else None)
    packages_json = json_for_script([p.to_dict() for p in packages])
    can_manage = bool({r.name.upper() for r in current_user.roles} & _CAN_MANAGE)
    # Config de transporte (fonte única do orçamento) p/ o cálculo no cliente (feature 076).
    from app.orcamento import settings as _orc_settings
    transporte_cfg = _orc_settings.load().get("transporte", {})
    return render_template(
        "educamanto/index.html",
        packages=packages,
        active_id=active_id,
        packages_json=packages_json,
        transporte_json=json_for_script(transporte_cfg),
        can_manage=can_manage,
    )


@educamanto_bp.route("/api/distancia")
@login_required
@_require_use
def api_distancia():
    """Distância até o endereço do evento — mesmo cálculo do orçamento (feature 076).

    Endpoint próprio (em vez de reusar o do orçamento) porque o EducaManto também é usado pelo
    perfil ENSAIO, que não tem acesso às rotas de vendas/orçamento.
    """
    from app.maps import distance_km_ida
    km_ida, error, status = distance_km_ida(request.args.get("endereco", ""))
    if error:
        return jsonify({"error": error}), status
    return jsonify({"km_ida": km_ida})


def _build_snapshot(data: dict) -> tuple[dict, str]:
    """Monta o snapshot do orçamento a partir do JSON do cliente. Retorna (snapshot, label)."""
    clean_pkgs = []
    for p in (data.get("packages") or []):
        clean_pkgs.append({
            "id": p.get("id"),
            "name": str(p.get("name") or "Pacote")[:200],
            "sem_nota": float(p.get("sem_nota") or 0),
            "com_nota": float(p.get("com_nota") or 0),
        })
    try:
        d1 = int(data.get("d1") or 0)
        d2 = int(data.get("d2") or 0)
    except (TypeError, ValueError):
        d1 = d2 = 0
    transporte = data.get("transporte") or {}
    client_name = (data.get("client_name") or "").strip()[:200]
    snapshot = {
        "d1": d1,
        "d2": d2,
        "ensemble": int(data.get("ensemble") or 0),
        "transporte": {
            "total": float(transporte.get("total") or 0),
            "label": str(transporte.get("label") or ""),
            "kmT": transporte.get("kmT"),
            "pessoas": transporte.get("pessoas"),
        },
        "client_name": client_name,
        "packages": clean_pkgs,
    }
    label = ", ".join(p["name"] for p in clean_pkgs)[:300]
    return snapshot, label


def _pdf_response(snapshot: dict, quote_id: int, inline: bool = False):
    from flask import make_response

    from app.educamanto.pdf import gerar_orcamento_pdf
    pdf_bytes = gerar_orcamento_pdf(snapshot)
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    disp = "inline" if inline else "attachment"
    resp.headers["Content-Disposition"] = f'{disp}; filename="orcamento-educamanto-{quote_id}.pdf"'
    return resp


@educamanto_bp.route("/orcamento/gerar", methods=["POST"])
@login_required
@_require_use
def gerar_orcamento():
    """Gera o PDF (1 página por pacote), salva no histórico e devolve para download (feature 077)."""
    import json

    from app.models import EducaMantoQuote
    data = request.get_json(silent=True) or {}
    if not (data.get("packages") or []):
        return jsonify({"error": "Selecione ao menos um pacote."}), 400

    snapshot, label = _build_snapshot(data)
    if snapshot["d1"] + snapshot["d2"] <= 0:
        return jsonify({"error": "Preencha os dias (1 e/ou 2 sessões) antes de gerar."}), 400

    quote = EducaMantoQuote(
        user_id=current_user.id,
        client_name=snapshot["client_name"] or None,
        packages_label=label,
        snapshot=json.dumps(snapshot, ensure_ascii=False),
    )
    db.session.add(quote)
    db.session.commit()
    return _pdf_response(snapshot, quote.id)


@educamanto_bp.route("/orcamento/<int:quote_id>/pdf")
@login_required
@_require_use
def orcamento_pdf(quote_id: int):
    """Re-renderiza o PDF de um orçamento do histórico (valores congelados)."""
    import json

    from app.models import EducaMantoQuote
    q = EducaMantoQuote.query.get_or_404(quote_id)
    snapshot = json.loads(q.snapshot or "{}")
    return _pdf_response(snapshot, q.id, inline=True)


@educamanto_bp.route("/historico")
@login_required
@_require_use
def historico():
    """Histórico dos orçamentos gerados (estilo da calculadora)."""
    from app.models import EducaMantoQuote
    q = request.args.get("q", "").strip()
    query = EducaMantoQuote.query
    if q:
        from sqlalchemy import or_
        like = f"%{q}%"
        query = query.filter(
            or_(EducaMantoQuote.client_name.ilike(like),
                EducaMantoQuote.packages_label.ilike(like))
        )
    entries = query.order_by(EducaMantoQuote.created_at.desc()).limit(300).all()
    return render_template("educamanto/historico.html", entries=entries, q=q)


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
            ensemble_1s=_money(request.form.get("ensemble_1s"), 350),
            ensemble_2s=_money(request.form.get("ensemble_2s"), 600),
            ensemble_1s_days=_money(request.form.get("ensemble_1s_days"), 300),
            ensemble_2s_days=_money(request.form.get("ensemble_2s_days"), 550),
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
        pkg.ensemble_1s = _money(request.form.get("ensemble_1s"), 350)
        pkg.ensemble_2s = _money(request.form.get("ensemble_2s"), 600)
        pkg.ensemble_1s_days = _money(request.form.get("ensemble_1s_days"), 300)
        pkg.ensemble_2s_days = _money(request.form.get("ensemble_2s_days"), 550)
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
