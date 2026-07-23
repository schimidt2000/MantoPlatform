"""Endpoints de LEITURA da Calculadora de Orçamento, Config. de Preços e Histórico (migração
177, US2/US4/US5).

Reusa, sem duplicar, o núcleo já extraído em `app/orcamento/quote_ops.py` e os módulos puros
`app/orcamento/settings.py`/`pricing.py` — os endpoints aqui só validam RBAC e serializam.
"""

from datetime import date, datetime
from typing import Any

from flask import jsonify, request
from flask_login import current_user
from sqlalchemy import or_

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import ACRESCIMO_TIPO_BV, RoleName
from app.models import OrcamentoHistory, Role, User
from app.money import parse_brl
from app.orcamento import quote_ops
from app.orcamento import settings as _cfg


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_vendas() -> Any:
    if not _has_role(RoleName.COMERCIAL, RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _require_superadmin() -> Any:
    if not _has_role(RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


@api_bp.route("/orcamento/opcoes")
@api_login_required
def api_orcamento_opcoes() -> Any:
    """Opções da calculadora: especiais, acréscimos, config de preços (para o formulário)."""
    denied = _require_vendas()
    if denied:
        return denied
    s = _cfg.load()
    return jsonify({
        "especiais": list(s["especiais"].keys()),
        "especiais_com_show": list(_cfg.especiais_com_show()),
        "especiais_com_cantor": list(_cfg.especiais_com_cantor()),
        "especiais_sempre_show": list(_cfg.ESPECIAIS_SEMPRE_SHOW),
        "acrescimo_tipos": _cfg.acrescimo_tipos_list(),
        "acrescimo_tipo_bv": ACRESCIMO_TIPO_BV,
        "settings": s,
    })


@api_bp.route("/orcamento/personagens-no-dia")
@api_login_required
def api_orcamento_personagens_no_dia() -> Any:
    """Personagens já escalados em eventos na data informada (evita venda duplicada)."""
    denied = _require_vendas()
    if denied:
        return denied
    raw = (request.args.get("date") or "").strip()
    try:
        dia = date.fromisoformat(raw)
    except ValueError:
        return jsonify({"date": None, "personagens": []})
    return jsonify({"date": dia.isoformat(), "personagens": quote_ops.personagens_no_dia(dia)})


@api_bp.route("/orcamento/distancia")
@api_login_required
def api_orcamento_distancia() -> Any:
    """Distância (km, ida) via Google Maps — fonte única (feature 076)."""
    denied = _require_vendas()
    if denied:
        return denied
    from app.maps import distance_km_ida

    km_ida, error, status = distance_km_ida(request.args.get("endereco", ""))
    if error:
        return json_error(error, status)
    return jsonify({"km_ida": km_ida})


# ══════════════════════════════════════════════════════════════════
#  Configuração de Preços (SUPERADMIN)
# ══════════════════════════════════════════════════════════════════


@api_bp.route("/orcamento/settings")
@api_login_required
def api_orcamento_settings_get() -> Any:
    """Configuração de preços vigente (SUPERADMIN)."""
    denied = _require_superadmin()
    if denied:
        return denied
    s = _cfg.load()
    return jsonify({"settings": s, "default_especiais": list(_cfg.DEFAULTS["especiais"].keys())})


# ══════════════════════════════════════════════════════════════════
#  Histórico de orçamentos
# ══════════════════════════════════════════════════════════════════


def _entry_summary(e: OrcamentoHistory) -> dict:
    return {
        "id": e.id,
        "created_at": e.created_at.isoformat(),
        "client_name": e.client_name or "",
        "event_location": e.event_location or "",
        "event_date": e.event_date or "",
        "total_1h": float(e.total_1h) if e.total_1h is not None else 0,
        "total_2h": float(e.total_2h) if e.total_2h is not None else 0,
        "total_3h": float(e.total_3h) if e.total_3h is not None else 0,
        "total_4h": float(e.total_4h) if e.total_4h is not None else 0,
        "has_show": e.has_show,
        "user_name": e.user.name if e.user else None,
    }


@api_bp.route("/orcamento/historico")
@api_login_required
def api_orcamento_historico_list() -> Any:
    """Histórico de orçamentos — SUPERADMIN vê todos, demais só os próprios."""
    denied = _require_vendas()
    if denied:
        return denied
    is_sa = _has_role(RoleName.SUPERADMIN)

    q = (request.args.get("q") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    min_val = (request.args.get("min_val") or "").strip()
    max_val = (request.args.get("max_val") or "").strip()
    user_id_f = (request.args.get("user_id") or "").strip()
    show_f = (request.args.get("has_show") or "").strip()

    query = OrcamentoHistory.query
    if not is_sa:
        query = query.filter_by(user_id=current_user.id)
    elif user_id_f.isdigit():
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

            query = query.filter(
                OrcamentoHistory.created_at < datetime.fromisoformat(date_to) + timedelta(days=1)
            )
        except ValueError:
            pass
    if min_val:
        parsed = parse_brl(min_val)
        if parsed is not None:
            query = query.filter(OrcamentoHistory.total_4h >= float(parsed))
    if max_val:
        parsed = parse_brl(max_val)
        if parsed is not None:
            query = query.filter(OrcamentoHistory.total_4h <= float(parsed))
    if show_f in ("1", "0"):
        query = query.filter(OrcamentoHistory.has_show == (show_f == "1"))

    entries = query.order_by(OrcamentoHistory.created_at.desc()).limit(300).all()

    users = []
    if is_sa:
        users = [
            {"id": u.id, "name": u.name}
            for u in (
                User.query.join(User.roles)
                .filter(Role.name.in_([RoleName.COMERCIAL, RoleName.SUPERADMIN]))
                .order_by(User.name.asc())
                .all()
            )
        ]

    return jsonify({
        "entries": [_entry_summary(e) for e in entries],
        "is_superadmin": is_sa,
        "users": users,
    })


def _get_entry_or_none(entry_id: int, is_sa: bool) -> OrcamentoHistory | None:
    if is_sa:
        return OrcamentoHistory.query.get(entry_id)
    return OrcamentoHistory.query.filter_by(id=entry_id, user_id=current_user.id).first()


@api_bp.route("/orcamento/historico/<int:entry_id>")
@api_login_required
def api_orcamento_historico_detail(entry_id: int) -> Any:
    """Detalhe congelado de um orçamento salvo (com fallback para registros legados)."""
    denied = _require_vendas()
    if denied:
        return denied
    entry = _get_entry_or_none(entry_id, _has_role(RoleName.SUPERADMIN))
    if entry is None:
        return json_error("Orçamento não encontrado", 404)
    return jsonify({"quote": quote_ops.quote_for_entry(entry)})
