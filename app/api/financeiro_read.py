"""Endpoints de LEITURA de Financeiro/Vendas (feature 156, abre a US4; 157, dashboard DRE).

Reusa os cálculos já existentes em `app/financeiro/routes.py` (`_group_cost`/`_event_cost`/
`_event_commission`/`_resolve_period`/`_compute_drg`/etc.) — não duplica lógica de negócio, só
serializa. Gates (`require_vendas`/`require_financeiro`) reimplementados aqui como funções
simples porque os decorators originais são específicos de view Flask.
"""

from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from flask import jsonify
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required
from app.constants import EDUCAMANTO_TITLE_PREFIX, RoleName
from app.models import CalendarEvent, EventInstallment, EventInvoice, SiteSetting, User

TZ_SP = ZoneInfo("America/Sao_Paulo")

PERIOD_LABELS = {
    "este_mes": "Este mês",
    "30d": "Últimos 30 dias",
    "mes_anterior": "Mês anterior",
    "custom": "Período personalizado",
}


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


def _floatify(d: dict) -> dict:
    """Converte todo valor `Decimal` de um dict raso para `float` (JSON-safe)."""
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in d.items()}


@api_bp.route("/financeiro/dashboard")
@api_login_required
def api_financeiro_dashboard() -> Any:
    """Dashboard financeiro (DRE): consolidado do período (feature 157).

    Reaproveita, sem duplicar, os mesmos cálculos de `dashboard()`
    (`app/financeiro/routes.py:387`) — só monta a query do período e serializa.
    """
    from app import db
    from app.financeiro.routes import (
        _compute_drg,
        _event_commission,
        _event_cost,
        _get_commission_rate,
        _get_fator_r_threshold,
        _get_tax_rate,
        _group_cost,
        _is_permuta,
        _month_range,
        _month_refs_between,
        _pct,
        _prev_month,
        _resolve_period,
        _salary_cost,
    )
    from app.gastos.routes import ensure_recurring_entries
    from app.models import EventPayment, RecurringExpenseEntry, SpecialExpense

    if not _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return jsonify({"error": {"message": "Sem permissão"}}), 403

    settings = SiteSetting.query.get(1)
    today = datetime.now(TZ_SP).date()
    now_naive = datetime.now(TZ_SP).replace(tzinfo=None)

    period, start_date, end_date, is_full_month = _resolve_period(today)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    events = (
        CalendarEvent.query
        .filter(
            CalendarEvent.start_at >= start_dt,
            CalendarEvent.start_at <= end_dt,
            CalendarEvent.event_type != "ENSAIO",
        )
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    realizados = [e for e in events if e.start_at and e.start_at < now_naive]
    projetados = [e for e in events if e.start_at and e.start_at >= now_naive]

    salary_cost = _salary_cost(start_date, end_date, is_full_month)
    gastos_extras = sum(
        (Decimal(g.amount) for g in SpecialExpense.query.filter(
            SpecialExpense.status == "aprovado",
            SpecialExpense.expense_date >= start_date,
            SpecialExpense.expense_date <= end_date,
        ).all()),
        Decimal("0"),
    )

    ensure_recurring_entries(today.year, today.month)
    gastos_recorrentes = sum(
        (Decimal(e.amount) for e in RecurringExpenseEntry.query.filter(
            RecurringExpenseEntry.month_ref.in_(_month_refs_between(start_date, end_date)),
            RecurringExpenseEntry.status != "pulado",
            RecurringExpenseEntry.amount.isnot(None),
        ).all()),
        Decimal("0"),
    )

    drg_realizado = _compute_drg(realizados, settings, salary_cost, gastos_extras, gastos_recorrentes)
    drg_projetado = _compute_drg(projetados, settings, Decimal("0"), Decimal("0"))
    drg_total = _compute_drg(events, settings, salary_cost, gastos_extras, gastos_recorrentes)

    eventos_com_venda = [
        e for e in events
        if not _is_permuta(e) and not e.is_satellite and e.sale_value and e.sale_value > 0
    ]
    ticket_medio = (
        (drg_total["receita_bruta"] / Decimal(len(eventos_com_venda))).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        if eventos_com_venda else Decimal("0")
    )
    ratio_custo_talento = _pct(drg_total["cpv"], drg_total["receita_liquida"])

    fixed_cost = drg_total["pessoal"] + drg_total["comissoes"]
    breakeven_pct = _pct(drg_total["lucro_bruto"], fixed_cost)
    breakeven_atingido = bool(fixed_cost > 0 and drg_total["lucro_bruto"] >= fixed_cost)

    fator_r_threshold = _get_fator_r_threshold(settings)
    fator_r_pct = _pct(drg_total["pessoal"], drg_total["receita_bruta"])
    fator_r_protegido = bool(drg_total["receita_bruta"] > 0 and fator_r_pct >= fator_r_threshold)

    _recebido_por_evento = dict(
        db.session.query(
            EventPayment.event_id,
            db.func.coalesce(db.func.sum(EventPayment.amount), 0),
        )
        .filter(EventPayment.event_id.in_([e.id for e in eventos_com_venda] or [0]))
        .group_by(EventPayment.event_id)
        .all()
    )
    a_receber_clientes = sum(
        max(float(e.sale_value) - float(_recebido_por_evento.get(e.id, 0)), 0)
        for e in eventos_com_venda
    )

    roles_no_periodo = [r for e in events for r in e.roles if r.talent_id]
    pagamentos_pendentes = sum(
        float(r.cache_value or 0) for r in roles_no_periodo if r.payment_status == "nao_pago"
    )
    pagamentos_realizados = sum(
        float(r.cache_value or 0) for r in roles_no_periodo
        if r.payment_status in ("pago", "no_banco")
    )

    receita_por_tipo_dd = defaultdict(int)
    for e in eventos_com_venda:
        receita_por_tipo_dd[e.event_type or "Outros"] += (e.sale_value or 0)
    receita_por_tipo = {
        k: float(v) for k, v in sorted(receita_por_tipo_dd.items(), key=lambda x: -x[1])
    }
    receita_tipo_max = max(receita_por_tipo.values()) if receita_por_tipo else 0.0

    seller_revenue = defaultdict(int)
    seller_margin = defaultdict(int)
    for e in eventos_com_venda:
        if e.seller_id:
            seller_revenue[e.seller_id] += (e.sale_value or 0)
            seller_margin[e.seller_id] += (e.sale_value or 0) - _group_cost(e)
    top_sellers = []
    for sid, rev in sorted(seller_revenue.items(), key=lambda x: -x[1])[:5]:
        u = User.query.get(sid)
        if u:
            top_sellers.append({
                "user_id": u.id,
                "user_name": u.name,
                "receita": float(rev),
                "lucro": float(seller_margin[sid]),
            })

    monthly_trend = []
    y, m = today.year, today.month
    for _ in range(6):
        s_dt, e_dt = _month_range(y, m)
        evs = CalendarEvent.query.filter(
            CalendarEvent.start_at >= s_dt,
            CalendarEvent.start_at < e_dt,
            CalendarEvent.event_type != "ENSAIO",
        ).all()
        normais = [e for e in evs if not _is_permuta(e) and not e.is_satellite]
        rec = sum(e.sale_value or 0 for e in normais)
        cst = sum(_group_cost(e) for e in normais)
        monthly_trend.insert(0, {
            "label": f"{m:02d}/{str(y)[2:]}",
            "receita": float(rec),
            "custo": float(cst),
            "lucro": float(rec - cst),
            "margem": float(_pct(rec - cst, rec)),
            "n_eventos": len(evs),
        })
        y, m = _prev_month(y, m)

    auditoria = [
        {
            "event_id": e.id,
            "title": e.title,
            "start_at": e.start_at.isoformat() if e.start_at else None,
        }
        for e in events
        if not _is_permuta(e) and not e.is_satellite and not (e.sale_value and e.sale_value > 0)
    ]

    eventos_data = []
    for e in events:
        if e.is_satellite:
            continue
        custo = float(_group_cost(e) if e.is_group_leader else _event_cost(e) or 0)
        comissao = float(_event_commission(e, settings))
        recebido = float(_recebido_por_evento.get(e.id, 0))
        venda = float(e.sale_value or 0)
        if _is_permuta(e):
            status = "permuta"
        elif venda <= 0:
            status = "sem_valor"
        elif recebido >= venda:
            status = "pago_total"
        elif recebido > 0:
            status = "parcial"
        else:
            status = "pendente"
        eventos_data.append({
            "event_id": e.id,
            "title": e.title,
            "group_label": (
                f"{e.group_display_name} ({len(e.satellites) + 1} eventos)"
                if e.is_group_leader else None
            ),
            "start_at": e.start_at.isoformat() if e.start_at else None,
            "custo": custo,
            "lucro": (0 if _is_permuta(e) else venda) - custo,
            "comissao": comissao,
            "rate": float(_get_commission_rate(e, settings)),
            "is_projetado": bool(e.start_at and e.start_at >= now_naive),
            "status": status,
        })

    _inst_rows = (
        db.session.query(EventInstallment, CalendarEvent)
        .join(CalendarEvent, EventInstallment.event_id == CalendarEvent.id)
        .filter(
            EventInstallment.due_date >= start_date,
            EventInstallment.due_date <= end_date,
            EventInstallment.received.is_(False),
        )
        .order_by(EventInstallment.due_date.asc())
        .all()
    )
    recebimentos_previstos = [
        {
            "date": inst.due_date.isoformat() if inst.due_date else None,
            "event_id": ev.id,
            "event_title": ev.title,
            "amount": float(inst.amount or 0),
        }
        for inst, ev in _inst_rows
    ]
    recebimentos_previstos_total = sum(r["amount"] for r in recebimentos_previstos)

    tax_rate_nf = _get_tax_rate(settings)

    _nf_pend = (
        EventInvoice.query
        .filter(EventInvoice.status == "a_emitir")
        .join(CalendarEvent, EventInvoice.event_id == CalendarEvent.id)
        .order_by(EventInvoice.issue_date.is_(None), EventInvoice.issue_date.asc())
        .all()
    )
    nf_a_emitir = [
        {
            "id": inv.id,
            "date": inv.issue_date.isoformat() if inv.issue_date else None,
            "event_id": inv.event_id,
            "event_title": inv.event.title if inv.event else "—",
            "amount": float(inv.amount or 0),
        }
        for inv in _nf_pend
    ]
    nf_a_emitir_total = sum(n["amount"] for n in nf_a_emitir)

    _nf_emit = (
        EventInvoice.query
        .filter(
            EventInvoice.issue_date >= start_date,
            EventInvoice.issue_date <= end_date,
        )
        .join(CalendarEvent, EventInvoice.event_id == CalendarEvent.id)
        .order_by(EventInvoice.issue_date.asc())
        .all()
    )
    custo_nota_itens = []
    for inv in _nf_emit:
        _val = Decimal(inv.amount or 0)
        _custo = (_val * tax_rate_nf / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        custo_nota_itens.append({
            "event_id": inv.event_id,
            "event_title": inv.event.title if inv.event else "—",
            "amount": float(_val),
            "date": inv.issue_date.isoformat() if inv.issue_date else None,
            "status": inv.status,
            "custo": float(_custo),
        })
    custo_nota_total = sum(i["custo"] for i in custo_nota_itens)

    return jsonify({
        "period": period,
        "period_label": PERIOD_LABELS.get(period, "Este mês"),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "is_full_month": is_full_month,
        "dre": {
            "realizado": _floatify(drg_realizado),
            "projetado": _floatify(drg_projetado),
            "total": _floatify(drg_total),
        },
        "kpis": {
            "ticket_medio": float(ticket_medio),
            "ratio_custo_talento": float(ratio_custo_talento),
            "breakeven_pct": float(breakeven_pct),
            "breakeven_atingido": breakeven_atingido,
            "fixed_cost": float(fixed_cost),
            "fator_r_pct": float(fator_r_pct),
            "fator_r_threshold": float(fator_r_threshold),
            "fator_r_protegido": fator_r_protegido,
        },
        "paineis": {
            "a_receber_clientes": a_receber_clientes,
            "pagamentos_pendentes": pagamentos_pendentes,
            "pagamentos_realizados": pagamentos_realizados,
            "receita_por_tipo": receita_por_tipo,
            "receita_tipo_max": receita_tipo_max,
            "top_sellers": top_sellers,
            "monthly_trend": monthly_trend,
            "auditoria": auditoria,
        },
        "eventos": eventos_data,
        "pendencias": {
            "recebimentos_previstos": recebimentos_previstos,
            "recebimentos_previstos_total": recebimentos_previstos_total,
            "nf_a_emitir": nf_a_emitir,
            "nf_a_emitir_total": nf_a_emitir_total,
            "custo_nota_itens": custo_nota_itens,
            "custo_nota_total": custo_nota_total,
        },
    })
