"""Endpoints de LEITURA de Financeiro/Vendas (feature 156, abre a US4).

Reusa os cálculos já existentes em `app/financeiro/routes.py` (`_group_cost`/`_event_cost`/
`_event_commission`) — não duplica lógica de negócio, só serializa. Gate: paridade com
`require_vendas`/`_is_educamanto_responsavel` (Jinja), reimplementado aqui como função simples
porque o decorator original é específico de view Flask.
"""

from typing import Any

from flask import jsonify
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required
from app.constants import EDUCAMANTO_TITLE_PREFIX, RoleName
from app.models import CalendarEvent, SiteSetting


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _is_educamanto_responsavel(settings: SiteSetting | None) -> bool:
    return bool(settings and settings.educamanto_seller_id == current_user.id)


def _can_view_vendas(settings: SiteSetting | None) -> bool:
    return _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN) or (
        _is_educamanto_responsavel(settings)
    )


@api_bp.route("/vendas/pipeline")
@api_login_required
def api_vendas_pipeline() -> Any:
    """Pipeline de vendas: eventos com venda/custo/comissão (feature 156)."""
    from app.financeiro.routes import _event_commission, _event_cost, _group_cost

    settings = SiteSetting.query.get(1)
    if not _can_view_vendas(settings):
        return jsonify({"error": {"message": "Sem permissão"}}), 403

    is_financeiro = _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN)

    events_q = CalendarEvent.query.filter(CalendarEvent.event_type != "ENSAIO")
    if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        events_q = events_q.filter(CalendarEvent.title.ilike(EDUCAMANTO_TITLE_PREFIX + "%"))
    events = events_q.order_by(CalendarEvent.start_at.desc()).all()

    items = []
    for e in events:
        if e.is_satellite:
            continue
        custo = float(_group_cost(e) if e.is_group_leader else _event_cost(e))
        comissao = float(_event_commission(e, settings))
        sale_value = float(e.sale_value or 0)
        item = {
            "event_id": e.id,
            "title": e.title,
            "group_label": (
                f"{e.group_display_name} ({len(e.satellites) + 1} eventos)"
                if e.is_group_leader
                else None
            ),
            "location": e.location,
            "sale_date": e.sale_date.isoformat() if e.sale_date else None,
            "sale_value": sale_value,
            "custo": custo,
            "comissao": comissao,
            "with_invoice": bool(e.with_invoice),
        }
        if is_financeiro:
            item["lucro"] = sale_value - custo
        items.append(item)

    return jsonify({"items": items, "is_financeiro": is_financeiro})
