"""Quote calculator blueprint — accessible to COMERCIAL and SUPERADMIN."""
import json
import math
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, abort, flash, jsonify, redirect,
    render_template, request, session, url_for,
)
from flask_login import current_user, login_required

from app import db
from app.constants import RoleName
from . import settings as _cfg
from .pricing import (
    aplicar_markup,
    calcular_maquiador,
    get_ator_prices,
    get_cantor_prices,
    get_coordenador_prices,
    get_especial_prices,
    get_tecnico_prices,
)
from .transport import calcular_carro, calcular_van

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
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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
        settings_json=json.dumps(s),
    )


_ADICIONAL_NOTURNO = 50.0  # R$ por artista/coordenador, aplicado pré-markup


def _is_noturno(raw_time: str) -> bool:
    """Retorna True se o horário do evento for a partir das 19h."""
    try:
        from datetime import datetime as _dt
        return _dt.strptime(raw_time, "%H:%M").hour >= 19
    except ValueError:
        return False


def _process_quote():
    try:
        performers = json.loads(request.form.get("performers_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        performers = []

    _coord_raw = int(request.form.get("coordenador_qty", 1) or 0)
    _dj_only   = (len(performers) > 0 and
                  all(p.get("type") == "especial" and p.get("personagem") == "DJ"
                      for p in performers))
    coordenador_qty = max(0 if _dj_only else 1, _coord_raw)

    # Enforce min coordinators for especiais with rules (e.g. Boneco Grande Especial)
    _regras = _cfg.load().get("especiais_regras", {})
    for _p in performers:
        if _p.get("type") == "especial":
            _min = _regras.get(_p.get("personagem", ""), {}).get("min_coordenadores", 1)
            coordenador_qty = max(coordenador_qty, _min)

    fora_sp          = "fora_sp" in request.form
    noturno          = _is_noturno(request.form.get("event_time", ""))
    acrescimo_valor  = float(request.form.get("acrescimo_valor", 0) or 0)
    acrescimo_tipo   = request.form.get("acrescimo_tipo", "valor")
    show_sosia_tipo  = request.form.get("show_sosia_tipo", "predefinido")
    nota_fiscal      = "nota_fiscal" in request.form
    modo_duracao     = request.form.get("modo_duracao", "horas")
    duracao_custom   = int(request.form.get("duracao_custom", 0) or 0)

    event_has_show   = False
    event_has_makeup = False
    num_makes_regular  = 0
    num_makes_especial = 0

    for p in performers:
        ptype      = p.get("type", "")
        show       = bool(p.get("show", False))
        makeup     = bool(p.get("makeup", False))
        makeup_tipo = p.get("makeup_tipo", "comum")
        cantor_flag = bool(p.get("cantor", False))

        # show é ativado pelo ator (qualquer subtipo com show marcado),
        # pelo especial com show/cantor, especiais que sempre têm show (DJ), ou tipo legado "cantor"
        personagem_esp = p.get("personagem", "") if ptype == "especial" else ""
        if ptype == "cantor" or (ptype == "ator" and show) or \
           (ptype == "especial" and (show or cantor_flag or personagem_esp in _cfg.ESPECIAIS_SEMPRE_SHOW)):
            event_has_show = True
        if makeup and ptype in ("ator", "cantor", "especial"):
            event_has_makeup = True
            if makeup_tipo == "especial":
                num_makes_especial += 1
            else:
                num_makes_regular += 1

    cache_totals = [0.0, 0.0, 0.0]
    team_lines   = []
    num_going    = coordenador_qty

    for p in performers:
        ptype  = p.get("type", "")
        show   = bool(p.get("show", False))
        makeup = bool(p.get("makeup", False))
        nome   = p.get("nome", "").strip()

        if ptype == "ator":
            subtipo = p.get("subtipo", "cara_limpa")
            if subtipo == "cantor":
                prices = get_cantor_prices(show, makeup)
                label  = nome or "Cantor"
            else:
                prices = get_ator_prices(subtipo, show, makeup)
                label  = nome or ("Boneco" if subtipo == "boneco" else "Ator")
        elif ptype == "cantor":
            # Suporte legado para histórico antigo (cantor era tipo separado)
            prices = get_cantor_prices(show=True, makeup=makeup)
            label  = nome or "Cantor"
        elif ptype == "especial":
            personagem  = p.get("personagem", "")
            cantor_flag = bool(p.get("cantor", False))
            prices = get_especial_prices(personagem, show, cantor_flag)
            label  = nome or personagem
        else:
            prices = (0, 0, 0)
            label  = nome or "Profissional"

        team_lines.append(label)
        num_going += 1
        for i in range(3):
            cache_totals[i] += prices[i]

    # Show customizado: +R$50 por artista (não conta coord, técnico nem maquiador)
    if show_sosia_tipo == "customizado" and performers:
        custom_add = len(performers) * 50
        for i in range(3):
            cache_totals[i] += custom_add

    coord_prices = get_coordenador_prices(event_has_show, coordenador_qty)
    for i in range(3):
        cache_totals[i] += coord_prices[i]

    brinde = 0.0
    if event_has_show:
        tecnico = get_tecnico_prices()
        for i in range(3):
            cache_totals[i] += tecnico[i]
        num_going += 1
        brinde = float(_cfg.load().get("brinde_show", 100))

    if event_has_makeup:
        maquiador_cost = calcular_maquiador(num_makes_regular, num_makes_especial)
        for i in range(3):
            cache_totals[i] += maquiador_cost

    totals = aplicar_markup(cache_totals, event_has_show)

    if brinde:
        for i in range(3):
            totals[i] = round(totals[i] + brinde, 2)

    if noturno:
        adicional_noturno = (len(performers) + coordenador_qty) * _ADICIONAL_NOTURNO
        for i in range(3):
            totals[i] = round(totals[i] + adicional_noturno, 2)

    transport_total = 0.0  # acumulador para split apresentação / logística na mensagem

    # Transporte especial pós-markup — uma vez por tipo (e.g. Boneco Grande Especial)
    _seen_transport: set = set()
    for p in performers:
        if p.get("type") == "especial":
            personagem = p.get("personagem", "")
            if personagem not in _seen_transport:
                transport_esp = _regras.get(personagem, {}).get("transporte_especial", 0)
                if transport_esp:
                    for i in range(3):
                        totals[i] = round(totals[i] + transport_esp, 2)
                    transport_total += transport_esp
                    _seen_transport.add(personagem)

    transport_breakdown = None
    if fora_sp:
        km_ida           = float(request.form.get("km_ida", 0) or 0)
        transporte_tipo  = request.form.get("transporte_tipo", "van")
        num_colaboradores = int(request.form.get("num_colaboradores", num_going) or num_going)

        if transporte_tipo == "van":
            carretinha = "carretinha" in request.form
            tb = calcular_van(num_colaboradores, km_ida, carretinha, event_has_show)
        else:
            num_carros = int(request.form.get("num_carros", 1) or 1)
            tb = calcular_carro(num_carros, num_colaboradores, km_ida, event_has_show)

        transport_breakdown = tb
        for i in range(3):
            totals[i] = round(totals[i] + tb["total"], 2)
        transport_total += tb["total"]

    if acrescimo_valor > 0:
        if acrescimo_tipo == "percent":
            totals = [round(t * (1 + acrescimo_valor / 100), 2) for t in totals]
        else:
            totals = [round(t + acrescimo_valor, 2) for t in totals]

    if nota_fiscal:
        totals = [round(t / 0.84, 2) for t in totals]

    # Duração personalizada: interpola a partir do preço de 4h
    total_custom = None
    if duracao_custom > 0 and duracao_custom not in (1, 2, 4):
        total_custom = round(totals[2] / 4 * duracao_custom, 2)

    raw_date = request.form.get("event_date", "")
    raw_time = request.form.get("event_time", "")
    try:
        fmt_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        fmt_date = raw_date
    try:
        fmt_time = datetime.strptime(raw_time, "%H:%M").strftime("%Hh%M")
    except ValueError:
        fmt_time = raw_time

    client_name    = request.form.get("client_name", "").strip()
    event_location = request.form.get("event_location", "").strip()

    tipo_evento = "Show com Som" if event_has_show else "Interação / Receptivo"
    saudacao    = f"Olá, *{client_name}*!" if client_name else "Olá!"
    team_text   = "\n".join(f"• {line}" for line in team_lines)

    def _dur_block(label: str, total: float) -> str:
        lines = [label]
        if transport_total > 0:
            apres = round(total - transport_total, 2)
            lines.append(f"  • Valor da Apresentação: {_fmt_brl(apres)}")
            lines.append(f"  • Logística e Transporte: {_fmt_brl(transport_total)}")
        lines.append(f"  • *VALOR TOTAL: {_fmt_brl(total)}*")
        return "\n".join(lines)

    if modo_duracao == "entradas":
        dur_labels = [
            "🎭 *1 entrada de 30 minutos*",
            "🎭 *2 entradas de 30 minutos (2h)*",
            "🎭 *4 entradas de 30 minutos (4h)*",
        ]
    else:
        dur_labels = ["🕐 *1 hora*", "🕑 *2 horas*", "🕓 *4 horas*"]

    investimento = "\n\n".join([
        _dur_block(dur_labels[0], totals[0]),
        _dur_block(dur_labels[1], totals[1]),
        _dur_block(dur_labels[2], totals[2]),
    ])

    if total_custom:
        if modo_duracao == "entradas":
            entradas_custom = duracao_custom * 2
            custom_label = f"🎭 *{entradas_custom} entradas de 30 min ({duracao_custom}h)*"
        else:
            custom_label = f"🕐 *{duracao_custom} horas*"
        investimento += f"\n\n{_dur_block(custom_label, total_custom)}"

    pix_vista = (
        f"  • 1h: *{_fmt_brl(round(totals[0] * 0.95, 2))}*\n"
        f"  • 2h: *{_fmt_brl(round(totals[1] * 0.95, 2))}*\n"
        f"  • 4h: *{_fmt_brl(round(totals[2] * 0.95, 2))}*"
    )
    if total_custom:
        pix_vista += f"\n  • {duracao_custom}h: *{_fmt_brl(round(total_custom * 0.95, 2))}*"

    nf_header = "\n🧾 _Valores com Nota Fiscal inclusa_" if nota_fiscal else ""

    message = (
        f"{saudacao} ✨ É um prazer preparar a proposta para o seu evento.\n\n"
        f"Estamos prontos para levar toda a magia da Manto Produções para o seu dia especial! "
        f"Confira os detalhes abaixo:\n\n"
        f"📍 *DETALHES DO EVENTO*\n"
        f"• Data: {fmt_date}\n"
        f"• Local: {event_location}\n"
        f"• Horário: {fmt_time}\n"
        f"• Modalidade: {tipo_evento}\n\n"
        f"🎭 *PERSONAGENS E EXPERIÊNCIA*\n"
        f"{team_text}\n\n"
        f"💰 *INVESTIMENTO*{nf_header}\n\n"
        f"{investimento}\n\n"
        f"💳 *FORMAS DE PAGAMENTO*\n\n"
        f"1️⃣ *À Vista (PIX):*\n"
        f"{pix_vista}\n"
        f"_(desconto especial de 5% aplicado)_\n\n"
        f"2️⃣ *Reserva Programada (PIX):* 50% no ato do contrato + 50% até 2 dias antes do evento.\n\n"
        f"3️⃣ *Cartão de Crédito:* Parcelamento disponível (taxas da operadora repassadas ao cliente).\n\n"
        f"✨ Podemos seguir com a reserva da sua data? "
        f"Aguardamos sua confirmação para enviarmos o link do contrato digital."
    )

    session["orcamento_quote"] = {
        "message":             message,
        "transport_breakdown": transport_breakdown,
        "fora_sp":             fora_sp,
        "total_1h":            totals[0],
        "total_2h":            totals[1],
        "total_4h":            totals[2],
        "total_custom":        total_custom,
        "duracao_custom":      duracao_custom,
    }

    # Salvar no histórico persistente
    from app.models import OrcamentoHistory
    snapshot = {
        "performers":       performers,
        "coordenador_qty":  coordenador_qty,
        "fora_sp":          fora_sp,
        "km_ida":           request.form.get("km_ida", "0"),
        "transporte_tipo":  request.form.get("transporte_tipo", "van"),
        "carretinha":       "carretinha" in request.form,
        "num_carros":       request.form.get("num_carros", "1"),
        "num_colaboradores": request.form.get("num_colaboradores", ""),
        "event_date":       raw_date,
        "event_time":       raw_time,
        "client_name":      client_name,
        "event_location":   event_location,
        "acrescimo_valor":  str(acrescimo_valor),
        "acrescimo_tipo":   acrescimo_tipo,
        "show_sosia_tipo":  show_sosia_tipo,
        "nota_fiscal":      nota_fiscal,
        "modo_duracao":     modo_duracao,
        "duracao_custom":   str(duracao_custom),
    }
    entry = OrcamentoHistory(
        user_id        = current_user.id,
        client_name    = client_name or None,
        event_location = event_location or None,
        event_date     = raw_date or None,
        total_1h       = totals[0],
        total_2h       = totals[1],
        total_4h       = totals[2],
        has_show       = event_has_show,
        form_snapshot  = json.dumps(snapshot, ensure_ascii=False),
    )
    db.session.add(entry)
    db.session.commit()

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
    if not is_sa:
        query = query.filter_by(user_id=current_user.id)
    elif user_id_f and user_id_f.isdigit():
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
        try:
            query = query.filter(OrcamentoHistory.total_4h >= float(min_val))
        except ValueError:
            pass
    if max_val:
        try:
            query = query.filter(OrcamentoHistory.total_4h <= float(max_val))
        except ValueError:
            pass

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
        "total_4h":       float(e.total_4h) if e.total_4h is not None else 0,
        "has_show":       e.has_show,
    } for e in entries])


@orcamento_bp.route("/api/historico/<int:entry_id>")
@login_required
@_require_vendas
def api_historico_detail(entry_id: int):
    from app.models import OrcamentoHistory
    is_sa = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)
    if is_sa:
        entry = OrcamentoHistory.query.get_or_404(entry_id)
    else:
        entry = OrcamentoHistory.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    return jsonify(json.loads(entry.form_snapshot or "{}"))


@orcamento_bp.route("/api/historico/<int:entry_id>", methods=["DELETE"])
@login_required
@_require_vendas
def api_historico_delete(entry_id: int):
    from app.models import OrcamentoHistory
    entry = OrcamentoHistory.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"ok": True})


# ── Google Maps distance API ──────────────────────────────────────────────────

@orcamento_bp.route("/api/distancia")
@login_required
@_require_vendas
def api_distancia():
    from app.models import SiteSetting
    setting = SiteSetting.query.get(1)
    import os
    api_key = (setting.google_maps_api_key if setting else "") or os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return jsonify({"error": "Google Maps não configurado. Configure a API Key em Admin → Configurações."}), 503

    origin  = setting.manto_address if setting and setting.manto_address else ""
    if not origin:
        return jsonify({"error": "Endereço da Manto não configurado em Configurações."}), 503

    endereco = request.args.get("endereco", "").strip()
    if not endereco:
        return jsonify({"error": "Endereço não informado."}), 400

    try:
        import googlemaps
        gmaps   = googlemaps.Client(key=api_key)
        result  = gmaps.distance_matrix(origin, endereco, mode="driving")
        element = result["rows"][0]["elements"][0]
        if element["status"] != "OK":
            return jsonify({"error": "Endereço não encontrado pelo Google Maps."}), 400
        km_ida = math.ceil(element["distance"]["value"] / 1000)
        return jsonify({"km_ida": km_ida})
    except ImportError:
        return jsonify({"error": "Biblioteca googlemaps não instalada."}), 503
    except Exception as exc:
        return jsonify({"error": f"Erro ao consultar Google Maps: {exc}"}), 500


# ── Pricing settings (SUPERADMIN only) ───────────────────────────────────────

@orcamento_bp.route("/settings", methods=["GET", "POST"])
@login_required
@_require_superadmin
def pricing_settings():
    if request.method == "POST":
        s = _cfg.load()

        for modelo in ("receptivo", "show"):
            s["markup"][modelo] = [
                float(request.form.get(f"markup_{modelo}_{i}", s["markup"][modelo][i]))
                for i in range(3)
            ]

        for key in s["ator"]:
            safe = key.replace("|", "_").replace(" ", "_")
            s["ator"][key] = [
                float(request.form.get(f"ator_{safe}_{i}", s["ator"][key][i]))
                for i in range(3)
            ]

        for key in s["cantor"]:
            s["cantor"][key] = [
                float(request.form.get(f"cantor_{key}_{i}", s["cantor"][key][i]))
                for i in range(3)
            ]

        s["tecnico_som"] = [
            float(request.form.get(f"tecnico_som_{i}", s["tecnico_som"][i]))
            for i in range(3)
        ]

        for key in s["coordenador"]:
            s["coordenador"][key] = [
                float(request.form.get(f"coordenador_{key}_{i}", s["coordenador"][key][i]))
                for i in range(3)
            ]

        for nome, val in s["especiais"].items():
            safe = nome.replace(" ", "_").replace("-", "_")
            if isinstance(val, dict):
                for show_key in val:
                    s["especiais"][nome][show_key] = [
                        float(request.form.get(f"especial_{safe}_{show_key}_{i}", val[show_key][i]))
                        for i in range(3)
                    ]
            else:
                s["especiais"][nome] = [
                    float(request.form.get(f"especial_{safe}_{i}", val[i]))
                    for i in range(3)
                ]

        s["brinde_show"] = float(request.form.get("brinde_show", s.get("brinde_show", 100)))

        for key in s["maquiador"]:
            s["maquiador"][key] = float(request.form.get(f"maquiador_{key}", s["maquiador"][key]))

        for key in s["transporte"]:
            s["transporte"][key] = float(request.form.get(f"transporte_{key}", s["transporte"][key]))

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
