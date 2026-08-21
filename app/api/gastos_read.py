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
from app.marketing import desempenho_ops
from app.models import RecurringExpense, SpecialExpense, User


def _require_financeiro() -> Any:
    if not gastos_ops.is_financeiro(current_user):
        return json_error("Sem permissão", 403)
    return None


def _num(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _expense_dict(e, batches: dict[int, object] | None = None) -> dict:
    # Lote do auditor de marketing (feature 256): `batches` vem pré-carregado pela lista para
    # não virar uma consulta por gasto; fora da lista cai na busca individual.
    lote = batches.get(e.id) if batches is not None else desempenho_ops.batch_for_expense(e.id)
    return {
        "id": e.id,
        "marketing_batch": desempenho_ops.serialize_batch(lote),
        "description": e.description,
        "category": e.category,
        "amount": _num(e.amount),
        "expense_date": e.expense_date.isoformat(),
        "status": e.status,
        "approved_with_edits": e.approved_with_edits,
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
    """Lista gastos extras: FINANCEIRO/SUPERADMIN vê todos (+ totais), demais só os próprios."""
    can_manage = gastos_ops.is_financeiro(current_user)
    expenses = gastos_ops.list_expenses_for_admin() if can_manage else gastos_ops.list_expenses(current_user)
    lotes = desempenho_ops.batches_for_expenses([e.id for e in expenses])
    payload = {
        "expenses": [_expense_dict(e, lotes) for e in expenses],
        "can_manage": can_manage,
        "categories": SpecialExpense.CATEGORIES,
    }
    if can_manage:
        payload["totals"] = gastos_ops.expense_totals(expenses)
    return jsonify(payload)


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


@api_bp.route("/gastos/funcionarios")
@api_login_required
def api_gastos_funcionarios() -> Any:
    """Colaboradores ativos, para o seletor de reembolso (mesma lista da view Jinja legada)."""
    funcionarios = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    return jsonify({"funcionarios": [{"id": u.id, "name": u.name} for u in funcionarios]})


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


def _recurring_dict(
    conta: RecurringExpense,
    entry,
    *,
    ref_year: int | None = None,
    ref_month: int | None = None,
) -> dict:
    """Serializa uma conta recorrente + o lançamento do mês de referência.

    Args:
        conta: A conta a serializar.
        entry: `RecurringExpenseEntry` do mês de referência (ou `None`).
        ref_year: Ano do mês de referência — habilita `occurrences` (feature 189).
        ref_month: Mês de referência — habilita `occurrences`.

    Returns:
        Dict JSON-safe. `occurrences` é `None` quando o mês de referência não foi informado
        (ex.: resposta de escrita, que devolve só a conta); `0` significa "fora do ciclo".
    """
    occurrences = (
        conta.occurrences_in_month(ref_year, ref_month)
        if ref_year is not None and ref_month is not None
        else None
    )
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
        # Rótulos derivados do model (fonte única com o Jinja legado) — feature 189.
        "expected_label": conta.expected_label,
        "dia_label": conta.dia_label,
        "vigencia_label": conta.vigencia_label,
        "parcelas_summary": conta.parcelas_summary if conta.expense_type == "programado" else None,
        "estimated_monthly": float(gastos_ops.estimate_monthly_cost(conta)),
        "has_entries": bool(conta.entries),
        "occurrences": occurrences,
        "entry": _entry_dict(entry) if entry else None,
        # Só o pagamento programado expõe todas as parcelas na listagem (as demais usam
        # `GET /api/gastos/recorrentes/<id>/historico`).
        "entries": (
            [_entry_dict(e) for e in sorted(conta.entries, key=lambda x: (x.due_date or date.max))]
            if conta.expense_type == "programado"
            else None
        ),
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
    ref_year, ref_month = result["ref_year"], result["ref_month"]
    grupos = {
        t: [
            _recurring_dict(c, entries.get(c.id), ref_year=ref_year, ref_month=ref_month)
            for c in contas
            if c.expense_type == t
        ]
        for t in RecurringExpense.TYPES
    }
    resumo = gastos_ops.recurring_summary(contas)
    alerts = gastos_ops.recurring_alerts(date.today())
    return jsonify({
        "grupos": grupos,
        "month_ref": result["month_ref"],
        "ref_year": ref_year,
        "ref_month": ref_month,
        "is_current_month": result["is_current_month"],
        "type_labels": RecurringExpense.TYPE_LABELS,
        "frequency_labels": RecurringExpense.FREQUENCY_LABELS,
        "weekday_labels": RecurringExpense.WEEKDAY_LABELS,
        "somas": {t: float(v) for t, v in resumo["somas"].items()},
        "programado_pendente_total": float(resumo["programado_pendente_total"]),
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


@api_bp.route("/gastos/recorrentes/<int:conta_id>/historico")
@api_login_required
def api_gastos_recorrentes_historico(conta_id: int) -> Any:
    """Histórico completo de lançamentos de uma conta recorrente (feature 189).

    Equivale ao painel `?conta=<id>` da tela Jinja legada — todos os `RecurringExpenseEntry`
    da conta, do mais recente para o mais antigo.
    """
    denied = _require_financeiro()
    if denied:
        return denied
    conta = RecurringExpense.query.get(conta_id)
    if conta is None:
        return json_error("Conta não encontrada", 404)
    entries = sorted(conta.entries, key=lambda e: e.month_ref, reverse=True)
    return jsonify({
        "conta_id": conta.id,
        "conta_name": conta.name,
        "entries": [_entry_dict(e) for e in entries],
    })
