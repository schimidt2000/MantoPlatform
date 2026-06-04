"""Gastos especiais/extras da empresa.

Registro aberto a qualquer colaborador autenticado; o gasto só impacta o balanço
financeiro quando aprovado por um super admin. Valores em R$ (formato brasileiro).
"""
from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal

from flask import (
    Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app import db
from app.constants import RoleName
from app.models import AuditLog, CalendarEvent, SpecialExpense, User
from app.money import format_brl, parse_brl

gastos_bp = Blueprint("gastos", __name__, url_prefix="/gastos")


def _is_superadmin() -> bool:
    """True se o usuário atual tem o papel SUPERADMIN."""
    return any(r.name.upper() == RoleName.SUPERADMIN for r in current_user.roles)


def _parse_brl(raw: str) -> Decimal | None:
    """Valor do gasto: usa a fonte única e exige valor > 0 (None caso contrário)."""
    value = parse_brl(raw)
    return value if value is not None and value > 0 else None


def _fmt_brl(value) -> str:
    """Formata número/Decimal como moeda brasileira: R$ 1.000,00 (fonte única)."""
    return format_brl(value, prefix=True)


def _save_receipt(file) -> str | None:
    """Salva o comprovante em UPLOAD_EXPENSES; retorna caminho relativo 'expenses/<arquivo>'."""
    if not file or not file.filename:
        return None
    fname = secure_filename(file.filename)
    if not fname:
        return None
    unique = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{fname}"
    dest_dir = current_app.config["UPLOAD_EXPENSES"]
    os.makedirs(dest_dir, exist_ok=True)
    file.save(os.path.join(dest_dir, unique))
    return f"expenses/{unique}"


def _resolve_event_id(raw: str | None) -> int | None:
    """Converte um event_id de formulário em int válido (evento existe) ou None."""
    if not raw or not str(raw).strip().isdigit():
        return None
    eid = int(raw)
    return eid if CalendarEvent.query.get(eid) else None


def _log(action: str, expense: SpecialExpense, detail: str = "") -> None:
    """Registra a ação no log de auditoria do sistema."""
    db.session.add(AuditLog(
        actor_name=current_user.name,
        actor_role=", ".join(r.name for r in current_user.roles),
        entity_type="gasto",
        entity_id=expense.id,
        entity_name=expense.description,
        action=action,
        detail=detail,
    ))


@gastos_bp.route("/")
@login_required
def index():
    """Página de gastos extras.

    Qualquer usuário autenticado registra e vê os próprios gastos. O super admin vê
    todos os gastos e o balanço (totais aprovados/pendentes); o usuário comum não vê
    o balanço nem gastos de terceiros.
    """
    is_sa = _is_superadmin()
    query = SpecialExpense.query
    if not is_sa:
        query = query.filter_by(created_by_id=current_user.id)
    expenses = (
        query
        .order_by(SpecialExpense.expense_date.desc(), SpecialExpense.id.desc())
        .all()
    )

    # Balanço só para super admin.
    total_pendente = None
    total_aprovado = None
    if is_sa:
        total_pendente = sum((e.amount for e in expenses if e.status == "pendente"), Decimal("0"))
        total_aprovado = sum((e.amount for e in expenses if e.status == "aprovado"), Decimal("0"))

    funcionarios = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    return render_template(
        "gastos/index.html",
        expenses=expenses,
        total_pendente=total_pendente,
        total_aprovado=total_aprovado,
        categories=SpecialExpense.CATEGORIES,
        funcionarios=funcionarios,
        is_superadmin=is_sa,
        today=date.today().isoformat(),
        fmt_brl=_fmt_brl,
    )


@gastos_bp.route("/novo", methods=["POST"])
@login_required
def novo():
    """Registra um novo gasto (status 'pendente'). Aberto a qualquer usuário autenticado."""
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "Outros").strip()
    amount = _parse_brl(request.form.get("amount", ""))
    date_raw = request.form.get("expense_date", "").strip()
    notes = request.form.get("notes", "").strip()

    if not description or amount is None:
        flash("Informe uma descrição e um valor válido (ex.: 1.000,00).", "error")
        return redirect(url_for("gastos.index"))

    # Nota Fiscal obrigatória (foto ou PDF que mostre o valor dos produtos).
    nota_fiscal_file = request.files.get("receipt")
    if not nota_fiscal_file or not nota_fiscal_file.filename:
        flash("Anexe a Nota Fiscal (foto ou PDF que mostre o valor dos produtos).", "error")
        return redirect(url_for("gastos.index"))

    # Desembolso: reembolso a funcionário ou pagamento a fornecedor
    disbursement_type = request.form.get("disbursement_type", "").strip()
    reimburse_user_id = None
    supplier_name = None
    supplier_pix = None
    if disbursement_type == "reembolso":
        raw_uid = request.form.get("reimburse_user_id", "").strip()
        if not raw_uid.isdigit():
            flash("Selecione o funcionário a ser reembolsado.", "error")
            return redirect(url_for("gastos.index"))
        reimburse_user_id = int(raw_uid)
    elif disbursement_type == "fornecedor":
        supplier_name = request.form.get("supplier_name", "").strip()
        supplier_pix = request.form.get("supplier_pix", "").strip() or None
        if not supplier_name:
            flash("Informe o nome do fornecedor.", "error")
            return redirect(url_for("gastos.index"))
    else:
        disbursement_type = None

    try:
        expense_date = date.fromisoformat(date_raw) if date_raw else date.today()
    except ValueError:
        expense_date = date.today()

    if category not in SpecialExpense.CATEGORIES:
        category = "Outros"

    receipt_path = _save_receipt(nota_fiscal_file)
    if receipt_path is None:
        flash("Não foi possível salvar a Nota Fiscal. Tente outro arquivo.", "error")
        return redirect(url_for("gastos.index"))

    event_id = _resolve_event_id(request.form.get("event_id"))

    expense = SpecialExpense(
        description=description,
        category=category,
        amount=amount,
        expense_date=expense_date,
        receipt_path=receipt_path,
        notes=notes or None,
        status="pendente",
        created_by_id=current_user.id,
        disbursement_type=disbursement_type,
        reimburse_user_id=reimburse_user_id,
        supplier_name=supplier_name,
        supplier_pix=supplier_pix,
        event_id=event_id,
    )
    db.session.add(expense)
    db.session.flush()
    _log("create", expense, f"Gasto registrado: {_fmt_brl(amount)} ({category})")
    db.session.commit()
    flash("Gasto registrado. Aguardando aprovação de um super admin.", "success")
    return redirect(url_for("gastos.index"))


@gastos_bp.route("/<int:expense_id>/aprovar", methods=["POST"])
@login_required
def aprovar(expense_id: int):
    """Aprova um gasto — passa a contar no balanço. Apenas super admin."""
    if not _is_superadmin():
        abort(403)
    expense = SpecialExpense.query.get_or_404(expense_id)
    expense.status = "aprovado"
    expense.approved_by_id = current_user.id
    expense.approved_at = datetime.utcnow()
    _log("approve", expense, f"Gasto aprovado: {_fmt_brl(expense.amount)}")
    db.session.commit()
    flash("Gasto aprovado — agora entra no balanço.", "success")
    return redirect(url_for("gastos.index"))


@gastos_bp.route("/<int:expense_id>/rejeitar", methods=["POST"])
@login_required
def rejeitar(expense_id: int):
    """Rejeita um gasto com um motivo. Apenas super admin."""
    if not _is_superadmin():
        abort(403)
    expense = SpecialExpense.query.get_or_404(expense_id)
    motivo = request.form.get("motivo", "").strip()
    expense.status = "rejeitado"
    expense.approved_by_id = current_user.id
    expense.approved_at = datetime.utcnow()
    expense.notes = motivo or expense.notes
    _log("reject", expense, f"Gasto rejeitado: {motivo or 'sem motivo'}")
    db.session.commit()
    flash("Gasto rejeitado.", "success")
    return redirect(url_for("gastos.index"))


@gastos_bp.route("/<int:expense_id>/excluir", methods=["POST"])
@login_required
def excluir(expense_id: int):
    """Exclui um gasto. Autor pode excluir o próprio enquanto pendente; super admin sempre."""
    expense = SpecialExpense.query.get_or_404(expense_id)
    pode = _is_superadmin() or (
        expense.created_by_id == current_user.id and expense.status == "pendente"
    )
    if not pode:
        abort(403)
    _log("delete", expense, f"Gasto excluído: {_fmt_brl(expense.amount)}")
    db.session.delete(expense)
    db.session.commit()
    flash("Gasto excluído.", "success")
    return redirect(url_for("gastos.index"))


@gastos_bp.route("/api/eventos")
@login_required
def api_eventos():
    """Lista eventos de uma data (YYYY-MM-DD) para vincular a um gasto: [{id, label}]."""
    raw = request.args.get("date", "").strip()
    try:
        dia = date.fromisoformat(raw)
    except ValueError:
        return jsonify([])
    eventos = (
        CalendarEvent.query
        .filter(func.date(CalendarEvent.start_at) == dia.isoformat())
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )
    out = []
    for e in eventos:
        hora = e.start_at.strftime("%H:%M") if e.start_at else ""
        label = f"{hora} · {e.title}" if hora else (e.title or f"Evento #{e.id}")
        out.append({"id": e.id, "label": label})
    return jsonify(out)


@gastos_bp.route("/<int:expense_id>/vincular-evento", methods=["POST"])
@login_required
def vincular_evento(expense_id: int):
    """Vincula/altera/remove o evento de um gasto existente. Apenas super admin."""
    if not _is_superadmin():
        abort(403)
    expense = SpecialExpense.query.get_or_404(expense_id)
    raw = request.form.get("event_id", "").strip()
    if raw == "":
        expense.event_id = None
        detail = "Vínculo de evento removido"
    else:
        event_id = _resolve_event_id(raw)
        if event_id is None:
            flash("Evento inválido.", "error")
            return redirect(url_for("gastos.index"))
        expense.event_id = event_id
        ev = CalendarEvent.query.get(event_id)
        detail = f"Gasto vinculado ao evento: {ev.title if ev else event_id}"
    _log("link_event", expense, detail)
    db.session.commit()
    flash("Vínculo de evento atualizado.", "success")
    return redirect(url_for("gastos.index"))
