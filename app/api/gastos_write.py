"""Endpoints de ESCRITA de Gastos Extras e Gastos Recorrentes (migração 177, US1/US3).

Reusa, sem duplicar, o núcleo já extraído em `app/gastos/gastos_ops.py` — os endpoints aqui só
validam RBAC, parseiam o corpo JSON/multipart e serializam. RBAC replicado como função,
paridade com `app/gastos/routes.py`.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from flask import current_app, jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api.gastos_read import _entry_dict, _expense_dict, _recurring_dict
from app.api_utils import api_login_required, json_error
from app.gastos import gastos_ops
from app.models import CalendarEvent, RecurringExpense, RecurringExpenseEntry, SpecialExpense


def _require_financeiro() -> Any:
    if not gastos_ops.is_financeiro(current_user):
        return json_error("Sem permissão", 403)
    return None


def _to_decimal(raw: Any) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        value = Decimal(str(raw))
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _to_date(raw: Any) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return None


@api_bp.route("/gastos", methods=["POST"])
@api_login_required
def api_gastos_create() -> Any:
    """Registra um novo gasto extra (multipart — comprovante obrigatório)."""
    form = request.form
    receipt_file = request.files.get("receipt")
    receipt_path = (
        gastos_ops.save_receipt(receipt_file, current_app.config["UPLOAD_EXPENSES"])
        if receipt_file
        else None
    )
    reimburse_raw = (form.get("reimburse_user_id") or "").strip()
    data = {
        "description": form.get("description", ""),
        "category": form.get("category", "Outros"),
        "amount": _to_decimal(form.get("amount")),
        "expense_date": _to_date(form.get("expense_date")) or date.today(),
        "notes": form.get("notes", ""),
        "disbursement_type": form.get("disbursement_type", ""),
        "reimburse_user_id": int(reimburse_raw) if reimburse_raw.isdigit() else None,
        "supplier_name": form.get("supplier_name", ""),
        "supplier_pix": form.get("supplier_pix", ""),
        "paid_at_creation": form.get("paid_at_creation") in ("true", "1", "on"),
    }
    event_raw = (form.get("event_id") or "").strip()
    event_id = int(event_raw) if event_raw.isdigit() and CalendarEvent.query.get(int(event_raw)) else None
    try:
        expense = gastos_ops.create_expense(current_user, data, receipt_path, event_id)
    except gastos_ops.GastoValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_expense_dict(expense)), 201


@api_bp.route("/gastos/<int:expense_id>/aprovar", methods=["POST"])
@api_login_required
def api_gastos_aprovar(expense_id: int) -> Any:
    """Aprova um gasto pendente. Apenas SUPERADMIN."""
    if not gastos_ops.is_superadmin(current_user):
        return json_error("Sem permissão", 403)
    expense = SpecialExpense.query.get(expense_id)
    if expense is None:
        return json_error("Gasto não encontrado", 404)
    try:
        gastos_ops.approve_expense(expense, current_user)
    except gastos_ops.GastoStateError as exc:
        return json_error(str(exc), 409)
    return jsonify(_expense_dict(expense))


@api_bp.route("/gastos/<int:expense_id>/rejeitar", methods=["POST"])
@api_login_required
def api_gastos_rejeitar(expense_id: int) -> Any:
    """Rejeita um gasto pendente. Apenas SUPERADMIN."""
    if not gastos_ops.is_superadmin(current_user):
        return json_error("Sem permissão", 403)
    expense = SpecialExpense.query.get(expense_id)
    if expense is None:
        return json_error("Gasto não encontrado", 404)
    body = request.get_json(silent=True) or {}
    try:
        gastos_ops.reject_expense(expense, current_user, body.get("motivo", ""))
    except gastos_ops.GastoStateError as exc:
        return json_error(str(exc), 409)
    return jsonify(_expense_dict(expense))


@api_bp.route("/gastos/<int:expense_id>", methods=["DELETE"])
@api_login_required
def api_gastos_delete(expense_id: int) -> Any:
    """Exclui um gasto. Autor pode excluir o próprio enquanto pendente; SUPERADMIN sempre."""
    expense = SpecialExpense.query.get(expense_id)
    if expense is None:
        return json_error("Gasto não encontrado", 404)
    if not gastos_ops.can_delete_expense(expense, current_user):
        return json_error("Sem permissão", 403)
    gastos_ops.delete_expense(expense, current_user)
    return "", 204


@api_bp.route("/gastos/<int:expense_id>/vincular-evento", methods=["POST"])
@api_login_required
def api_gastos_vincular_evento(expense_id: int) -> Any:
    """Vincula/remove o evento de um gasto existente. Apenas SUPERADMIN."""
    if not gastos_ops.is_superadmin(current_user):
        return json_error("Sem permissão", 403)
    expense = SpecialExpense.query.get(expense_id)
    if expense is None:
        return json_error("Gasto não encontrado", 404)
    body = request.get_json(silent=True) or {}
    try:
        expense = gastos_ops.link_expense_to_event(expense, body.get("event_id"), current_user)
    except gastos_ops.GastoValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_expense_dict(expense))


# ══════════════════════════════════════════════════════════════════
#  Gastos recorrentes
# ══════════════════════════════════════════════════════════════════


def _conta_body_to_data(body: dict) -> dict:
    ref_mode = body.get("ref_mode") or "faixa"
    return {
        "name": body.get("name", ""),
        "expense_type": body.get("expense_type", ""),
        "frequency": body.get("frequency", "mensal"),
        "weekday": body.get("weekday"),
        "due_day": body.get("due_day"),
        "amount": _to_decimal(body.get("amount")),
        "ref_mode": ref_mode,
        "amount_min": _to_decimal(body.get("amount_min")) if ref_mode != "exato" else None,
        "amount_max": _to_decimal(body.get("amount_max")) if ref_mode != "exato" else None,
        "start_date": _to_date(body.get("start_date")) or date.today(),
        "end_date": _to_date(body.get("end_date")),
        "default_pix": body.get("default_pix", ""),
        "card_name": body.get("card_name", ""),
        "notes": body.get("notes", ""),
    }


@api_bp.route("/gastos/recorrentes", methods=["POST"])
@api_login_required
def api_gastos_recorrentes_create() -> Any:
    """Cadastra uma conta recorrente (variável/débito automático/assinatura) ou programada."""
    denied = _require_financeiro()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    try:
        if body.get("expense_type") == "programado":
            data = {
                "name": body.get("name", ""),
                "default_pix": body.get("default_pix", ""),
                "notes": body.get("notes", ""),
                "parcelas": [
                    {"date": _to_date(p.get("date")), "amount": _to_decimal(p.get("amount"))}
                    for p in body.get("parcelas", [])
                ],
            }
            conta = gastos_ops.create_programado(current_user, data)
        else:
            conta = gastos_ops.create_recurring(current_user, _conta_body_to_data(body))
    except gastos_ops.GastoValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_recurring_dict(conta, None)), 201


@api_bp.route("/gastos/recorrentes/<int:conta_id>", methods=["PATCH"])
@api_login_required
def api_gastos_recorrentes_update(conta_id: int) -> Any:
    """Edita uma conta recorrente comum (não aplica a pagamentos programados)."""
    denied = _require_financeiro()
    if denied:
        return denied
    conta = RecurringExpense.query.get(conta_id)
    if conta is None:
        return json_error("Conta não encontrada", 404)
    body = request.get_json(silent=True) or {}
    try:
        gastos_ops.update_recurring(conta, current_user, _conta_body_to_data(body))
    except gastos_ops.GastoValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_recurring_dict(conta, None))


@api_bp.route("/gastos/recorrentes/<int:conta_id>/toggle", methods=["POST"])
@api_login_required
def api_gastos_recorrentes_toggle(conta_id: int) -> Any:
    """Ativa/desativa uma conta recorrente."""
    denied = _require_financeiro()
    if denied:
        return denied
    conta = RecurringExpense.query.get(conta_id)
    if conta is None:
        return json_error("Conta não encontrada", 404)
    gastos_ops.toggle_recurring(conta, current_user)
    return jsonify(_recurring_dict(conta, None))


@api_bp.route("/gastos/recorrentes/<int:conta_id>", methods=["DELETE"])
@api_login_required
def api_gastos_recorrentes_delete(conta_id: int) -> Any:
    """Exclui uma conta recorrente sem lançamentos (com histórico, o caminho é desativar)."""
    denied = _require_financeiro()
    if denied:
        return denied
    conta = RecurringExpense.query.get(conta_id)
    if conta is None:
        return json_error("Conta não encontrada", 404)
    try:
        gastos_ops.delete_recurring(conta, current_user)
    except gastos_ops.GastoStateError as exc:
        return json_error(str(exc), 409)
    return "", 204


def _entry_or_404(entry_id: int) -> RecurringExpenseEntry | None:
    return RecurringExpenseEntry.query.get(entry_id)


def _month_ref_or_current(raw: Any) -> str:
    """`month_ref` do corpo (`"YYYY-MM"`) se válido, senão o mês corrente."""
    if isinstance(raw, str) and len(raw) == 7 and raw[4] == "-":
        return raw
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


@api_bp.route("/gastos/recorrentes/<int:conta_id>/preencher", methods=["POST"])
@api_login_required
def api_gastos_conta_preencher(conta_id: int) -> Any:
    """Preenche a conta variável do mês (valor + PIX + vencimento): lançamento a pagar.

    A conta pode ainda não ter lançamento no mês (estado "aguardando") — este endpoint cria o
    lançamento se necessário, mesma semântica de `gastos_ops.fill_entry`.
    """
    denied = _require_financeiro()
    if denied:
        return denied
    conta = RecurringExpense.query.get(conta_id)
    if conta is None:
        return json_error("Conta não encontrada", 404)
    body = request.get_json(silent=True) or {}
    amount = _to_decimal(body.get("amount"))
    if amount is None:
        return json_error("Informe o valor exato da conta (ex.: 512,30).", 400, fields={"amount": "obrigatório"})
    try:
        entry = gastos_ops.fill_entry(
            conta, current_user, _month_ref_or_current(body.get("month_ref")), amount,
            body.get("pix"), _to_date(body.get("due_date")),
        )
    except gastos_ops.GastoStateError as exc:
        return json_error(str(exc), 409)
    return jsonify(_entry_dict(entry))


@api_bp.route("/gastos/recorrentes/<int:conta_id>/pular", methods=["POST"])
@api_login_required
def api_gastos_conta_pular(conta_id: int) -> Any:
    """Pula o mês de uma conta variável (boleto não veio) — cria o lançamento se necessário."""
    denied = _require_financeiro()
    if denied:
        return denied
    conta = RecurringExpense.query.get(conta_id)
    if conta is None:
        return json_error("Conta não encontrada", 404)
    body = request.get_json(silent=True) or {}
    try:
        entry = gastos_ops.skip_entry(conta, current_user, _month_ref_or_current(body.get("month_ref")))
    except gastos_ops.GastoStateError as exc:
        return json_error(str(exc), 409)
    return jsonify(_entry_dict(entry))


@api_bp.route("/gastos/recorrentes/entry/<int:entry_id>/pagar", methods=["POST"])
@api_login_required
def api_gastos_entry_pagar(entry_id: int) -> Any:
    """Marca um lançamento a pagar como pago."""
    denied = _require_financeiro()
    if denied:
        return denied
    entry = _entry_or_404(entry_id)
    if entry is None:
        return json_error("Lançamento não encontrado", 404)
    try:
        gastos_ops.pay_entry(entry, current_user)
    except gastos_ops.GastoStateError as exc:
        return json_error(str(exc), 409)
    return jsonify(_entry_dict(entry))


@api_bp.route("/gastos/recorrentes/entry/<int:entry_id>/reabrir", methods=["POST"])
@api_login_required
def api_gastos_entry_reabrir(entry_id: int) -> Any:
    """Reabre um lançamento (pago volta a 'a pagar'; pulado é removido)."""
    denied = _require_financeiro()
    if denied:
        return denied
    entry = _entry_or_404(entry_id)
    if entry is None:
        return json_error("Lançamento não encontrado", 404)
    try:
        entry = gastos_ops.reopen_entry(entry, current_user)
    except gastos_ops.GastoStateError as exc:
        return json_error(str(exc), 409)
    return jsonify(_entry_dict(entry)) if entry else ("", 204)


@api_bp.route("/gastos/recorrentes/entry/<int:entry_id>", methods=["DELETE"])
@api_login_required
def api_gastos_entry_delete(entry_id: int) -> Any:
    """Exclui uma parcela avulsa de pagamento programado ainda não paga."""
    denied = _require_financeiro()
    if denied:
        return denied
    entry = _entry_or_404(entry_id)
    if entry is None:
        return json_error("Lançamento não encontrado", 404)
    try:
        gastos_ops.delete_parcela(entry, current_user)
    except gastos_ops.GastoStateError as exc:
        return json_error(str(exc), 409)
    return "", 204
