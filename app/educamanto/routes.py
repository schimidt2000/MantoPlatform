"""EducaManto — Motor de orçamentos por pacote musical."""
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.constants import RoleName
from app.educamanto import package_ops, quote_ops
from app.educamanto.package_ops import PackageValidationError
from app.models import EducaMantoItem, EducaMantoPackage
from app.money import parse_brl
from app.utils import json_for_script

educamanto_bp = Blueprint("educamanto", __name__, url_prefix="/educamanto")


def _money(value, default: float) -> float:
    """Lê um valor em R$ (mascarado ou cru) como float; usa o default só se vazio/inválido.

    Diferente de ``parse_brl(x) or default``, preserva o zero explícito (R$ 0,00).
    """
    parsed = parse_brl(value)
    return float(parsed) if parsed is not None else float(default)

_CAN_USE      = {RoleName.COMERCIAL, RoleName.SUPERADMIN, RoleName.ENSAIO, RoleName.REVENDEDOR_EDUCAMANTO}
# ENSAIO/Revendedor usam só a calculadora — não veem a aba de pacotes.
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
    copy = package_ops.duplicate_package(original)
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
    data = request.get_json(silent=True) or {}
    try:
        quote, snapshot = quote_ops.generate_quote(current_user.id, data)
    except quote_ops.QuoteValidationError as exc:
        return jsonify({"error": exc.message}), 400
    return _pdf_response(snapshot, quote.id)


@educamanto_bp.route("/orcamento/<int:quote_id>/pdf")
@login_required
@_require_use
def orcamento_pdf(quote_id: int):
    """Re-renderiza o PDF de um orçamento do histórico (valores congelados)."""
    from app.models import EducaMantoQuote
    q = EducaMantoQuote.query.get_or_404(quote_id)
    snapshot = quote_ops.load_quote_snapshot(q)
    return _pdf_response(snapshot, q.id, inline=True)


@educamanto_bp.route("/historico")
@login_required
@_require_use
def historico():
    """Histórico dos orçamentos gerados — mesmo padrão da calculadora (feature 109).

    Busca por texto para todos; filtros de período de geração para todos; coluna e filtro
    "Gerado por" apenas para o super admin (regra idêntica ao histórico da calculadora).
    """
    is_superadmin = bool({r.name.upper() for r in current_user.roles} & {RoleName.SUPERADMIN})

    q         = request.args.get("q", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to   = request.args.get("date_to", "").strip()
    user_id_f = request.args.get("user_id", "").strip()

    entries, users = quote_ops.search_history(
        query=q,
        date_from=date_from,
        date_to=date_to,
        user_id_filter=user_id_f,
        is_superadmin=is_superadmin,
    )

    return render_template(
        "educamanto/historico.html",
        entries=entries,
        q=q,
        date_from=date_from,
        date_to=date_to,
        users=users,
        is_superadmin=is_superadmin,
    )


def _package_form_data() -> dict:
    """Monta o dict de entrada de `package_ops` a partir do form Jinja (percentuais em 0-100)."""
    return {
        "name": request.form["name"].strip(),
        "margin_1s": float(request.form["margin_1s"]),
        "margin_2s": float(request.form["margin_2s"]),
        "margin_1s_days": float(request.form["margin_1s_days"]),
        "margin_2s_days": float(request.form["margin_2s_days"]),
        "discount_days": int(request.form["discount_days"]),
        "discount_pct": float(request.form["discount_pct"]) / 100,
        "commission_rate": float(request.form["commission_rate"]) / 100,
        "ensemble_1s": _money(request.form.get("ensemble_1s"), 350),
        "ensemble_2s": _money(request.form.get("ensemble_2s"), 600),
        "ensemble_1s_days": _money(request.form.get("ensemble_1s_days"), 300),
        "ensemble_2s_days": _money(request.form.get("ensemble_2s_days"), 550),
        "items": _parse_items_from_form(),
    }


@educamanto_bp.route("/packages/create", methods=["GET", "POST"])
@login_required
@_require_manage
def create_package():
    if request.method == "POST":
        try:
            pkg = package_ops.create_package(_package_form_data())
        except PackageValidationError as exc:
            flash(exc.message, "danger")
            return render_template("educamanto/package_form.html", package=None)
        flash("Pacote criado com sucesso.", "success")
        return redirect(url_for("educamanto.index", pkg=pkg.id))
    return render_template("educamanto/package_form.html", package=None)


@educamanto_bp.route("/packages/<int:pkg_id>/edit", methods=["GET", "POST"])
@login_required
@_require_manage
def edit_package(pkg_id: int):
    pkg = EducaMantoPackage.query.get_or_404(pkg_id)
    if request.method == "POST":
        try:
            package_ops.update_package(pkg, _package_form_data())
        except PackageValidationError as exc:
            flash(exc.message, "danger")
            return render_template("educamanto/package_form.html", package=pkg)
        flash("Pacote atualizado com sucesso.", "success")
        return redirect(url_for("educamanto.index", pkg=pkg.id))
    return render_template("educamanto/package_form.html", package=pkg)


@educamanto_bp.route("/packages/<int:pkg_id>/delete", methods=["POST"])
@login_required
@_require_manage
def delete_package(pkg_id: int):
    pkg = EducaMantoPackage.query.get_or_404(pkg_id)
    name = pkg.name
    package_ops.delete_package(pkg)
    flash(f'Pacote "{name}" removido.', "success")
    return redirect(url_for("educamanto.index"))
