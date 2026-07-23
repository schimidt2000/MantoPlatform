"""Quote calculator blueprint — accessible to COMERCIAL and SUPERADMIN.

Núcleo de negócio em `quote_ops.py` (reusado pela API em `app/api/orcamento_read.py`/
`orcamento_write.py`) — este módulo só parseia `request`/`flash`/`session`/`redirect` e chama
`quote_ops`.
"""
import json
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, abort, flash, jsonify, redirect,
    render_template, request, Response, session, url_for,
)
from flask_login import current_user, login_required

from app import db
from app.constants import RoleName, ACRESCIMO_TIPO_BV
from app.money import format_brl, parse_brl
from app.utils import json_for_script
from . import settings as _cfg
from . import quote_ops

orcamento_bp = Blueprint("orcamento", __name__, url_prefix="/orcamento")

_CAN_USE = {RoleName.COMERCIAL, RoleName.SUPERADMIN}


def _require_vendas(f):
    """Decorator: allows COMERCIAL, SUPERADMIN."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        roles = {r.name.upper() for r in current_user.roles}
        if not roles & _CAN_USE:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _require_superadmin(f):
    """Decorator: allows SUPERADMIN only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not any(r.name == RoleName.SUPERADMIN for r in current_user.roles):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _fmt_brl(value: float) -> str:
    """Formata moeda BR com prefixo R$ (fonte única)."""
    return format_brl(value, prefix=True)


def _parse_num(raw: str | None) -> float | None:
    """Parse a numeric form field (aceita vírgula decimal). Retorna float ≥ 0 ou None."""
    if raw is None:
        return None
    txt = str(raw).strip().replace(" ", "").replace("R$", "")
    if not txt:
        return None
    # "1.234,56" → "1234.56"; "1234,56" → "1234.56"; "1234.56" mantém
    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    try:
        val = float(txt)
    except ValueError:
        return None
    return val if val >= 0 else None


# ── Quote form ────────────────────────────────────────────────────────────────

@orcamento_bp.route("/", methods=["GET", "POST"])
@login_required
@_require_vendas
def index():
    if request.method == "POST":
        return _process_quote()
    s = _cfg.load()
    return render_template(
        "orcamento/index.html",
        especiais_list=list(s["especiais"].keys()),
        especiais_com_show=list(_cfg.especiais_com_show()),
        especiais_com_cantor=list(_cfg.especiais_com_cantor()),
        especiais_sempre_show=list(_cfg.ESPECIAIS_SEMPRE_SHOW),
        settings_json=json_for_script(s),
        acrescimo_tipos=_cfg.acrescimo_tipos_list(),
        acrescimo_tipo_bv=ACRESCIMO_TIPO_BV,
    )


@orcamento_bp.route("/personagens-no-dia")
@login_required
@_require_vendas
def personagens_no_dia():
    """Personagens já escalados em eventos na data informada (evita venda duplicada — feature 061).

    Retorna JSON ``{date, personagens:[{nome, eventos[]}]}``. Considera apenas papéis de
    personagem (``role_type='character'``) — apoio (Coordenador, Técnico, Presença, Maquiador)
    e ensaios ficam de fora. Vaga sem talento conta (a vaga já compromete o personagem no dia).
    """
    from datetime import date as _date

    raw = (request.args.get("date") or "").strip()
    try:
        dia = _date.fromisoformat(raw)
    except ValueError:
        return jsonify({"date": None, "personagens": []})

    personagens = quote_ops.personagens_no_dia(dia)
    return jsonify({"date": dia.isoformat(), "personagens": personagens})


def _payload_from_form() -> dict:
    """Monta o payload aceito por `quote_ops.calculate_quote()` a partir de `request.form`."""
    try:
        performers = json.loads(request.form.get("performers_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        performers = []

    acr_tipos = request.form.getlist("acrescimo_tipo[]")
    acr_descr = request.form.getlist("acrescimo_descricao[]")
    acr_values = request.form.getlist("acrescimo_value[]")
    acr_percents = request.form.getlist("acrescimo_is_percent[]")
    acrescimos = []
    for i, tipo in enumerate(acr_tipos):
        acrescimos.append({
            "tipo": tipo,
            "descricao": acr_descr[i] if i < len(acr_descr) else "",
            "value": _parse_num(acr_values[i]) if i < len(acr_values) else 0.0,
            "is_percent": (acr_percents[i] == "1") if i < len(acr_percents) else False,
        })

    return {
        "performers": performers,
        "coordenador_qty": request.form.get("coordenador_qty", 1),
        "fora_sp": "fora_sp" in request.form,
        "event_time": request.form.get("event_time", ""),
        "acrescimos": acrescimos,
        "show_sosia_tipo": request.form.get("show_sosia_tipo", "predefinido"),
        "nota_fiscal": "nota_fiscal" in request.form,
        "modo_duracao": request.form.get("modo_duracao", "horas"),
        "duracao_custom": request.form.get("duracao_custom", 0),
        "km_ida": request.form.get("km_ida", 0),
        "transporte_tipo": request.form.get("transporte_tipo", "van"),
        "num_colaboradores": request.form.get("num_colaboradores", ""),
        "carretinha": "carretinha" in request.form,
        "num_carros": request.form.get("num_carros", 1),
        "personalizado": "personalizado_ativo" in request.form,
        "personalizado_criterio": request.form.get("personalizado_criterio", "valor_final"),
        "cust_mult_1h": request.form.get("cust_mult_1h", ""),
        "cust_mult_2h": request.form.get("cust_mult_2h", ""),
        "cust_mult_3h": request.form.get("cust_mult_3h", ""),
        "cust_mult_4h": request.form.get("cust_mult_4h", ""),
        "cust_valor_1h": request.form.get("cust_valor_1h", ""),
        "cust_valor_2h": request.form.get("cust_valor_2h", ""),
        "cust_valor_3h": request.form.get("cust_valor_3h", ""),
        "cust_valor_4h": request.form.get("cust_valor_4h", ""),
        "incluir_duracao": request.form.getlist("incluir_duracao"),
        "event_date": request.form.get("event_date", ""),
        "client_name": request.form.get("client_name", ""),
        "event_location": request.form.get("event_location", ""),
    }


def _process_quote():
    payload = _payload_from_form()
    try:
        result = quote_ops.calculate_quote(payload)
    except quote_ops.QuoteValidationError as exc:
        flash(exc.message, "warning")
        return redirect(url_for("orcamento.index"))

    quote, snapshot = result["quote"], result["snapshot"]
    session["orcamento_quote"] = quote
    quote_ops.save_quote_history(current_user, quote, snapshot)
    return redirect(url_for("orcamento.resultado"))


# ── Quote result ──────────────────────────────────────────────────────────────

@orcamento_bp.route("/resultado")
@login_required
@_require_vendas
def resultado():
    quote = session.get("orcamento_quote")
    if not quote:
        return redirect(url_for("orcamento.index"))
    return render_template("orcamento/resultado.html", quote=quote, fmt_brl=_fmt_brl)


# ── Ver orçamento congelado (do histórico) ──────────────────────────────────────

@orcamento_bp.route("/historico/<int:entry_id>/ver")
@login_required
@_require_vendas
def ver_historico(entry_id: int):
    """Mostra o orçamento CONGELADO (snapshot do resultado), imune a mudanças de preço.

    Carrega o snapshot salvo na sessão e reusa a tela de resultado (mensagem/PDF/email).
    """
    from app.models import OrcamentoHistory
    entry = OrcamentoHistory.query.get_or_404(entry_id)
    session["orcamento_quote"] = quote_ops.quote_for_entry(entry)
    return redirect(url_for("orcamento.resultado"))


# ── Download PDF ──────────────────────────────────────────────────────────────

@orcamento_bp.route("/pdf")
@login_required
@_require_vendas
def download_pdf():
    quote = session.get("orcamento_quote")
    if not quote:
        flash("Gere um orçamento primeiro.", "warning")
        return redirect(url_for("orcamento.index"))

    from .pdf import gerar_orcamento_pdf
    pdf_bytes = gerar_orcamento_pdf(quote)

    client = (quote.get("client_name") or "orcamento").replace(" ", "_")
    filename = f"Orcamento_Manto_{client}.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Enviar orçamento por email ─────────────────────────────────────────────────

@orcamento_bp.route("/enviar-email", methods=["POST"])
@login_required
@_require_vendas
def enviar_email():
    quote = session.get("orcamento_quote")
    if not quote:
        return jsonify({"error": "Orçamento não encontrado na sessão."}), 400

    recipient = (request.form.get("email") or "").strip().lower()
    if not recipient or "@" not in recipient:
        return jsonify({"error": "E-mail inválido."}), 400

    from .pdf import gerar_orcamento_pdf
    from app.email_service import send_quote_email

    pdf_bytes = gerar_orcamento_pdf(quote)
    ok = send_quote_email(
        to=recipient,
        client_name=quote.get("client_name") or "",
        pdf_bytes=pdf_bytes,
    )

    if ok:
        return jsonify({"ok": True, "msg": f"Orçamento enviado para {recipient}."})
    return jsonify({"error": "Falha ao enviar email. Verifique as configurações de email do sistema."}), 500


# ── Histórico (página) ───────────────────────────────────────────────────────

@orcamento_bp.route("/historico")
@login_required
@_require_vendas
def historico():
    from app.models import OrcamentoHistory, User, Role
    from sqlalchemy import or_

    is_sa = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)

    q          = request.args.get("q", "").strip()
    date_from  = request.args.get("date_from", "").strip()
    date_to    = request.args.get("date_to", "").strip()
    ev_from    = request.args.get("ev_date_from", "").strip()
    ev_to      = request.args.get("ev_date_to", "").strip()
    min_val    = request.args.get("min_val", "").strip()
    max_val    = request.args.get("max_val", "").strip()
    user_id_f  = request.args.get("user_id", "").strip()
    show_f     = request.args.get("has_show", "").strip()

    query = OrcamentoHistory.query
    if user_id_f and user_id_f.isdigit():
        query = query.filter_by(user_id=int(user_id_f))

    if q:
        query = query.filter(
            or_(
                OrcamentoHistory.client_name.ilike(f"%{q}%"),
                OrcamentoHistory.event_location.ilike(f"%{q}%"),
            )
        )

    if date_from:
        try:
            query = query.filter(OrcamentoHistory.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import timedelta
            query = query.filter(OrcamentoHistory.created_at < datetime.fromisoformat(date_to) + timedelta(days=1))
        except ValueError:
            pass

    if ev_from:
        query = query.filter(OrcamentoHistory.event_date >= ev_from)
    if ev_to:
        query = query.filter(OrcamentoHistory.event_date <= ev_to)

    if min_val:
        _min = parse_brl(min_val)
        if _min is not None:
            query = query.filter(OrcamentoHistory.total_4h >= float(_min))
    if max_val:
        _max = parse_brl(max_val)
        if _max is not None:
            query = query.filter(OrcamentoHistory.total_4h <= float(_max))

    if show_f in ("1", "0"):
        query = query.filter(OrcamentoHistory.has_show == (show_f == "1"))

    entries = query.order_by(OrcamentoHistory.created_at.desc()).limit(300).all()

    users = []
    if is_sa:
        users = (
            User.query
            .join(User.roles)
            .filter(Role.name.in_([RoleName.COMERCIAL, RoleName.SUPERADMIN]))
            .order_by(User.name.asc())
            .all()
        )

    return render_template(
        "orcamento/historico.html",
        entries=entries,
        is_superadmin=is_sa,
        users=users,
        fmt_brl=_fmt_brl,
    )


# ── Histórico API ────────────────────────────────────────────────────────────

@orcamento_bp.route("/api/historico")
@login_required
@_require_vendas
def api_historico():
    from app.models import OrcamentoHistory
    entries = (
        OrcamentoHistory.query
        .filter_by(user_id=current_user.id)
        .order_by(OrcamentoHistory.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([{
        "id":             e.id,
        "created_at":     e.created_at.strftime("%d/%m/%Y %H:%M"),
        "client_name":    e.client_name or "",
        "event_location": e.event_location or "",
        "event_date":     e.event_date or "",
        "total_1h":       float(e.total_1h) if e.total_1h is not None else 0,
        "total_2h":       float(e.total_2h) if e.total_2h is not None else 0,
        "total_3h":       float(e.total_3h) if e.total_3h is not None else 0,
        "total_4h":       float(e.total_4h) if e.total_4h is not None else 0,
        "has_show":       e.has_show,
    } for e in entries])


@orcamento_bp.route("/api/historico/<int:entry_id>")
@login_required
@_require_vendas
def api_historico_detail(entry_id: int):
    from app.models import OrcamentoHistory
    entry = OrcamentoHistory.query.get_or_404(entry_id)
    return jsonify(json.loads(entry.form_snapshot or "{}"))


@orcamento_bp.route("/api/historico/<int:entry_id>", methods=["DELETE"])
@login_required
@_require_vendas
def api_historico_delete(entry_id: int):
    from app.models import OrcamentoHistory
    is_sa = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)
    if is_sa:
        entry = OrcamentoHistory.query.get_or_404(entry_id)
    else:
        entry = OrcamentoHistory.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"ok": True})


# ── Google Maps distance API ──────────────────────────────────────────────────

@orcamento_bp.route("/api/distancia")
@login_required
@_require_vendas
def api_distancia():
    # Fonte única do cálculo de distância (feature 076) — compartilhado com o EducaManto.
    from app.maps import distance_km_ida
    km_ida, error, status = distance_km_ida(request.args.get("endereco", ""))
    if error:
        return jsonify({"error": error}), status
    return jsonify({"km_ida": km_ida})


# ── Pricing settings (SUPERADMIN only) ───────────────────────────────────────

@orcamento_bp.route("/settings", methods=["GET", "POST"])
@login_required
@_require_superadmin
def pricing_settings():
    if request.method == "POST":
        s = _cfg.load()

        def _money(field, default):
            """Lê um preço em R$ enviado com a máscara BR; cai no default se vazio/inválido."""
            val = parse_brl(request.form.get(field, ""))
            return float(val) if val is not None else float(default)

        # markup é multiplicador (não é R$) — segue como número cru.
        for modelo in ("receptivo", "show"):
            s["markup"][modelo] = [
                float(request.form.get(f"markup_{modelo}_{i}", s["markup"][modelo][i]))
                for i in range(4)
            ]

        for key in s["ator"]:
            safe = key.replace("|", "_").replace(" ", "_")
            s["ator"][key] = [
                _money(f"ator_{safe}_{i}", s["ator"][key][i])
                for i in range(4)
            ]

        for key in s["cantor"]:
            s["cantor"][key] = [
                _money(f"cantor_{key}_{i}", s["cantor"][key][i])
                for i in range(4)
            ]

        s["tecnico_som"] = [
            _money(f"tecnico_som_{i}", s["tecnico_som"][i])
            for i in range(4)
        ]

        for key in s["coordenador"]:
            s["coordenador"][key] = [
                _money(f"coordenador_{key}_{i}", s["coordenador"][key][i])
                for i in range(4)
            ]

        for nome, val in s["especiais"].items():
            safe = nome.replace(" ", "_").replace("-", "_")
            if isinstance(val, dict):
                for show_key in val:
                    s["especiais"][nome][show_key] = [
                        _money(f"especial_{safe}_{show_key}_{i}", val[show_key][i])
                        for i in range(4)
                    ]
            else:
                s["especiais"][nome] = [
                    _money(f"especial_{safe}_{i}", val[i])
                    for i in range(4)
                ]

        s["brinde_show"] = _money("brinde_show", s.get("brinde_show", 100))

        for key in s["maquiador"]:
            s["maquiador"][key] = _money(f"maquiador_{key}", s["maquiador"][key])

        for key in s["transporte"]:
            s["transporte"][key] = float(request.form.get(f"transporte_{key}", s["transporte"][key]))

        # Feature 100: tipos de acréscimo comuns (BV/Outro nunca entram nesta lista — são fixos).
        _acr_tipos_raw = request.form.getlist("acrescimo_tipo_nome[]")
        _acr_tipos_new: list[str] = []
        for _t in _acr_tipos_raw:
            _t = (_t or "").strip()
            if _t and _t not in ("BV", "Outro") and _t not in _acr_tipos_new:
                _acr_tipos_new.append(_t)
        s["acrescimo_tipos"] = _acr_tipos_new

        _cfg.save(s)
        flash("Configurações de preços salvas com sucesso!", "success")
        return redirect(url_for("orcamento.pricing_settings"))

    s = _cfg.load()
    return render_template(
        "orcamento/settings.html",
        s=s,
        default_especiais=set(_cfg.DEFAULTS["especiais"].keys()),
    )


@orcamento_bp.route("/settings/add-especial", methods=["POST"])
@login_required
@_require_superadmin
def add_especial():
    data  = request.get_json(silent=True) or {}
    nome  = (data.get("nome") or "").strip()
    prices = data.get("prices")
    if not nome or prices is None:
        return jsonify({"error": "Dados inválidos"}), 400
    s = _cfg.load()
    if nome in s["especiais"]:
        return jsonify({"error": f"'{nome}' já existe"}), 400
    s["especiais"][nome] = prices
    excluidos = s.setdefault("especiais_excluidos", [])
    if nome in excluidos:
        excluidos.remove(nome)
    _cfg.save(s)
    return jsonify({"ok": True})


@orcamento_bp.route("/settings/delete-especial", methods=["POST"])
@login_required
@_require_superadmin
def delete_especial():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Nome inválido"}), 400
    s = _cfg.load()
    if nome in s["especiais"]:
        del s["especiais"][nome]
    excluidos = s.setdefault("especiais_excluidos", [])
    if nome not in excluidos:
        excluidos.append(nome)
    _cfg.save(s)
    return jsonify({"ok": True})
