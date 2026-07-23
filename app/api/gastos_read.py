"""Endpoints de LEITURA de Gastos Extras e Gastos Recorrentes (migração 177, US1/US3).

Reusa, sem duplicar, o núcleo já extraído em `app/gastos/gastos_ops.py` — os endpoints aqui só
validam RBAC e serializam. RBAC replicado como função, paridade com `app/gastos/routes.py`.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.gastos import gastos_ops
from app.models import RecurringExpense, SpecialExpense


def _require_financeiro() -> Any:
    if not gastos_ops.is_financeiro(current_user):
        return json_error("Sem permissão", 403)
    return None


def _num(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _expense_dict(e) -> dict:
    return {
        "id": e.id,
        "description": e.description,
        "category": e.category,
        "amount": _num(e.amount),
        "expense_date": e.expense_date.isoformat(),
        "status": e.status,
        "notes": e.notes or "",
        "receipt_url": e.receipt_url,
        "disbursement_type": e.disbursement_type,
        "payee_name": e.payee_name,
        "payee_pix": e.payee_pix,
        "payment_status": e.payment_status,
        "paid_at_creation": e.paid_at_creation,
        "event_id": e.event_id,
        "event_title": e.event.title if e.event else None,
        "created_by_name": e.created_by.name if e.created_by else None,
        "created_at": e.created_at.isoformat(),
        "approved_by_name": e.approved_by.name if e.approved_by else None,
        "approved_at": e.approved_at.isoformat() if e.approved_at else None,
    }


@api_bp.route("/gastos")
@api_login_required
def api_gastos_list() -> Any:
    """Lista gastos extras: SUPERADMIN vê todos, demais só os próprios."""
    expenses = gastos_ops.list_expenses(current_user)
    return jsonify({
        "expenses": [_expense_dict(e) for e in expenses],
        "is_superadmin": gastos_ops.is_superadmin(current_user),
        "categories": SpecialExpense.CATEGORIES,
    })


@api_bp.route("/gastos/eventos")
@api_login_required
def api_gastos_eventos() -> Any:
    """Eventos de uma data (`?date=YYYY-MM-DD`), para o seletor de vínculo."""
    raw = request.args.get("date", "").strip()
    try:
        dia = date.fromisoformat(raw)
    except ValueError:
        return jsonify({"events": []})
    eventos = gastos_ops.search_events_by_date(dia)
    out = []
    for e in eventos:
        hora = e.start_at.strftime("%H:%M") if e.start_at else ""
        label = f"{hora} · {e.title}" if hora else (e.title or f"Evento #{e.id}")
        out.append({"id": e.id, "label": label})
    return jsonify({"events": out})


def _entry_dict(entry) -> dict:
    return {
        "id": entry.id,
        "recurring_id": entry.recurring_id,
        "month_ref": entry.month_ref,
        "amount": _num(entry.amount),
        "pix": entry.pix,
        "due_date": entry.due_date.isoformat() if entry.due_date else None,
        "status": entry.status,
        "out_of_range": entry.out_of_range,
        "paid_at": entry.paid_at.isoformat() if entry.paid_at else None,
    }


def _recurring_dict(conta: RecurringExpense, entry) -> dict:
    return {
        "id": conta.id,
        "name": conta.name,
        "expense_type": conta.expense_type,
        "amount": _num(conta.amount),
        "amount_min": _num(conta.amount_min),
        "amount_max": _num(conta.amount_max),
        "due_day": conta.due_day,
        "frequency": conta.frequency,
        "weekday": conta.weekday,
        "start_date": conta.start_date.isoformat(),
        "end_date": conta.end_date.isoformat() if conta.end_date else None,
        "default_pix": conta.default_pix,
        "card_name": conta.card_name,
        "notes": conta.notes,
        "is_active": conta.is_active,
        "entry": _entry_dict(entry) if entry else None,
    }


@api_bp.route("/gastos/recorrentes")
@api_login_required
def api_gastos_recorrentes_list() -> Any:
    """Contas recorrentes por tipo + lançamento do mês + alertas (FINANCEIRO/SUPERADMIN)."""
    denied = _require_financeiro()
    if denied:
        return denied
    result = gastos_ops.list_recurring(request.args.get("month", "").strip() or None)
    contas = result["contas"]
    entries = result["entries"]
    grupos = {
        t: [_recurring_dict(c, entries.get(c.id)) for c in contas if c.expense_type == t]
        for t in RecurringExpense.TYPES
    }
    alerts = gastos_ops.recurring_alerts(date.today())
    return jsonify({
        "grupos": grupos,
        "month_ref": result["month_ref"],
        "is_current_month": result["is_current_month"],
        "type_labels": RecurringExpense.TYPE_LABELS,
        "frequency_labels": RecurringExpense.FREQUENCY_LABELS,
        "alerts": [
            {
                "recurring_id": a["conta"].id,
                "name": a["conta"].name,
                "estado": a["estado"],
                "entry": _entry_dict(a["entry"]) if a["entry"] else None,
            }
            for a in alerts
        ],
    })
