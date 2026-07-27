"""Gastos especiais/extras da empresa.

Registro aberto a qualquer colaborador autenticado; o gasto só impacta o balanço
financeiro quando aprovado por um super admin. Valores em R$ (formato brasileiro).

Núcleo de negócio em `gastos_ops.py` (reusado pela API em `app/api/gastos_read.py`/
`gastos_write.py`) — este módulo só parseia `request`/`flash`/`redirect` e chama `gastos_ops`.
"""
from __future__ import annotations

from datetime import date

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.gastos import gastos_ops
from app.gastos.gastos_ops import (  # noqa: F401 — reexportados p/ callers existentes
    ensure_recurring_entries,
    recurring_alerts,
)
from app.models import RecurringExpense, RecurringExpenseEntry, SpecialExpense, User
from app.money import format_brl, parse_brl

gastos_bp = Blueprint("gastos", __name__, url_prefix="/gastos")


def _fmt_brl(value) -> str:
    """Formata número/Decimal como moeda brasileira: R$ 1.000,00 (fonte única)."""
    return format_brl(value, prefix=True)


def _resolve_event_id(raw: str | None) -> int | None:
    """Converte um event_id de formulário em int válido (evento existe) ou None."""
    from app.models import CalendarEvent

    if not raw or not str(raw).strip().isdigit():
        return None
    eid = int(raw)
    return eid if CalendarEvent.query.get(eid) else None


@gastos_bp.route("/")
@login_required
def index():
    """Página de gastos extras.

    Qualquer usuário autenticado registra e vê os próprios gastos. O super admin vê
    todos os gastos e o balanço (totais aprovados/pendentes); o usuário comum não vê
    o balanço nem gastos de terceiros.
    """
    from decimal import Decimal

    is_sa = gastos_ops.is_superadmin(current_user)
    expenses = gastos_ops.list_expenses(current_user)

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
    date_raw = request.form.get("expense_date", "").strip()
    try:
        expense_date = date.fromisoformat(date_raw) if date_raw else date.today()
    except ValueError:
        expense_date = date.today()

    nota_fiscal_file = request.files.get("receipt")
    if not nota_fiscal_file or not nota_fiscal_file.filename:
        flash("Anexe a Nota Fiscal (foto ou PDF que mostre o valor dos produtos).", "error")
        return redirect(url_for("gastos.index"))
    receipt_path = gastos_ops.save_receipt(
        nota_fiscal_file, current_app.config["UPLOAD_EXPENSES"]
    )
    if receipt_path is None:
        flash("Não foi possível salvar a Nota Fiscal. Tente outro arquivo.", "error")
        return redirect(url_for("gastos.index"))

    raw_uid = request.form.get("reimburse_user_id", "").strip()
    data = {
        "description": request.form.get("description", "").strip(),
        "category": request.form.get("category", "Outros").strip(),
        "amount": parse_brl(request.form.get("amount", "")),
        "expense_date": expense_date,
        "notes": request.form.get("notes", "").strip(),
        "disbursement_type": request.form.get("disbursement_type", "").strip(),
        "reimburse_user_id": int(raw_uid) if raw_uid.isdigit() else None,
        "supplier_name": request.form.get("supplier_name", "").strip(),
        "supplier_pix": request.form.get("supplier_pix", "").strip(),
        "paid_at_creation": request.form.get("paid_at_creation") == "on",
    }
    if data["amount"] is not None and data["amount"] <= 0:
        data["amount"] = None
    event_id = _resolve_event_id(request.form.get("event_id"))

    try:
        gastos_ops.create_expense(current_user, data, receipt_path, event_id)
    except gastos_ops.GastoValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("gastos.index"))
    flash("Gasto registrado. Aguardando aprovação de um super admin.", "success")
    return redirect(url_for("gastos.index"))


@gastos_bp.route("/<int:expense_id>/aprovar", methods=["POST"])
@login_required
def aprovar(expense_id: int):
    """Aprova um gasto — passa a contar no balanço. Apenas super admin."""
    if not gastos_ops.is_superadmin(current_user):
        abort(403)
    expense = SpecialExpense.query.get_or_404(expense_id)
    try:
        gastos_ops.approve_expense(expense, current_user)
    except gastos_ops.GastoStateError as exc:
        flash(str(exc), "error")
        return redirect(url_for("gastos.index"))
    flash("Gasto aprovado — agora entra no balanço.", "success")
    return redirect(url_for("gastos.index"))


@gastos_bp.route("/<int:expense_id>/rejeitar", methods=["POST"])
@login_required
def rejeitar(expense_id: int):
    """Rejeita um gasto com um motivo. Apenas super admin."""
    if not gastos_ops.is_superadmin(current_user):
        abort(403)
    expense = SpecialExpense.query.get_or_404(expense_id)
    try:
        gastos_ops.reject_expense(expense, current_user, request.form.get("motivo", ""))
    except gastos_ops.GastoStateError as exc:
        flash(str(exc), "error")
        return redirect(url_for("gastos.index"))
    flash("Gasto rejeitado.", "success")
    return redirect(url_for("gastos.index"))


@gastos_bp.route("/<int:expense_id>/excluir", methods=["POST"])
@login_required
def excluir(expense_id: int):
    """Exclui um gasto. Autor pode excluir o próprio enquanto pendente; super admin sempre."""
    expense = SpecialExpense.query.get_or_404(expense_id)
    if not gastos_ops.can_delete_expense(expense, current_user):
        abort(403)
    gastos_ops.delete_expense(expense, current_user)
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
    eventos = gastos_ops.search_events_by_date(dia)
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
    if not gastos_ops.is_superadmin(current_user):
        abort(403)
    expense = SpecialExpense.query.get_or_404(expense_id)
    raw = request.form.get("event_id", "").strip()
    if raw == "":
        event_id = None
    else:
        event_id = _resolve_event_id(raw)
        if event_id is None:
            flash("Evento inválido.", "error")
            return redirect(url_for("gastos.index"))
    try:
        gastos_ops.link_expense_to_event(expense, event_id, current_user)
    except gastos_ops.GastoValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("gastos.index"))
    flash("Vínculo de evento atualizado.", "success")
    return redirect(url_for("gastos.index"))


# ══════════════════════════════════════════════════════════════════
#  Gastos recorrentes (feature 110) — FINANCEIRO/SUPERADMIN
# ══════════════════════════════════════════════════════════════════


def _require_financeiro_recorrentes() -> None:
    """Aborta 403 fora de FINANCEIRO/SUPERADMIN (guard das rotas de recorrentes)."""
    if not gastos_ops.is_financeiro(current_user):
        abort(403)


def _parse_conta_form() -> dict | None:
    """Lê o formulário de conta recorrente em dict e delega a validação a `gastos_ops`."""
    weekday_raw = request.form.get("weekday", "").strip()
    due_day_raw = request.form.get("due_day", "").strip()
    ref_mode = request.form.get("ref_mode", "faixa")
    try:
        start_date = (
            date.fromisoformat(request.form.get("start_date", "").strip())
            if request.form.get("start_date", "").strip()
            else date.today()
        )
    except ValueError:
        start_date = date.today()
    try:
        end_date = (
            date.fromisoformat(request.form.get("end_date", "").strip())
            if request.form.get("end_date", "").strip()
            else None
        )
    except ValueError:
        end_date = None
    return {
        "name": request.form.get("name", "").strip(),
        "expense_type": request.form.get("expense_type", "").strip(),
        "frequency": request.form.get("frequency", "mensal").strip(),
        "weekday": int(weekday_raw) if weekday_raw.isdigit() else None,
        "due_day": int(due_day_raw) if due_day_raw.isdigit() else None,
        "amount": parse_brl(request.form.get("amount", "")),
        "ref_mode": ref_mode,
        "amount_min": (
            parse_brl(request.form.get("amount_min", "")) if ref_mode != "exato" else None
        ),
        "amount_max": (
            parse_brl(request.form.get("amount_max", "")) if ref_mode != "exato" else None
        ),
        "start_date": start_date,
        "end_date": end_date,
        "default_pix": request.form.get("default_pix", "").strip(),
        "card_name": request.form.get("card_name", "").strip(),
        "notes": request.form.get("notes", "").strip(),
    }


@gastos_bp.route("/recorrentes")
@login_required
def recorrentes():
    """Tela de gastos recorrentes: contas por tipo + status do mês (FINANCEIRO/SUPERADMIN)."""
    _require_financeiro_recorrentes()
    result = gastos_ops.list_recurring(request.args.get("month", "").strip() or None)
    contas = result["contas"]
    entries = result["entries"]
    grupos = {t: [c for c in contas if c.expense_type == t] for t in RecurringExpense.TYPES}

    hist_conta = None
    raw_conta = request.args.get("conta", "").strip()
    if raw_conta.isdigit():
        hist_conta = RecurringExpense.query.get(int(raw_conta))

    # Resumo do topo: fonte única em gastos_ops (reusada pelo endpoint da API, feature 189).
    resumo = gastos_ops.recurring_summary(contas)
    somas = resumo["somas"]
    programado_pendente_total = resumo["programado_pendente_total"]

    return render_template(
        "gastos/recorrentes.html",
        grupos=grupos,
        entries=entries,
        somas=somas,
        programado_pendente_total=programado_pendente_total,
        month_ref=result["month_ref"],
        ref_year=result["ref_year"],
        ref_month=result["ref_month"],
        is_current_month=result["is_current_month"],
        type_labels=RecurringExpense.TYPE_LABELS,
        frequency_labels=RecurringExpense.FREQUENCY_LABELS,
        hist_conta=hist_conta,
        today=date.today(),
        fmt_brl=_fmt_brl,
    )


@gastos_bp.route("/recorrentes/programado/nova", methods=["POST"])
@login_required
def recorrente_programado_nova():
    """Cadastra um pagamento programado: N parcelas com data e valor próprios (feature 121)."""
    _require_financeiro_recorrentes()
    dates_raw = request.form.getlist("sched_date[]")
    same_value = request.form.get("valor_mode", "mesmo") == "mesmo"
    dates: list[date] = []
    for raw in dates_raw:
        raw = (raw or "").strip()
        if not raw:
            continue
        try:
            dates.append(date.fromisoformat(raw))
        except ValueError:
            flash(f"Data inválida: {raw}.", "error")
            return redirect(url_for("gastos.recorrentes"))

    parcelas = []
    if same_value:
        amount = parse_brl(request.form.get("sched_amount_same", ""))
        parcelas = [{"date": d, "amount": amount} for d in dates]
    else:
        amounts_raw = request.form.getlist("sched_amount[]")
        idx = 0
        for raw_date, raw_amount in zip(dates_raw, amounts_raw, strict=True):
            if not (raw_date or "").strip():
                continue
            parcelas.append({"date": dates[idx], "amount": parse_brl(raw_amount)})
            idx += 1

    data = {
        "name": request.form.get("name", "").strip(),
        "default_pix": request.form.get("default_pix", "").strip(),
        "notes": request.form.get("notes", "").strip(),
        "parcelas": parcelas,
    }
    try:
        conta = gastos_ops.create_programado(current_user, data)
    except gastos_ops.GastoValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("gastos.recorrentes"))
    flash(f'Pagamento "{conta.name}" cadastrado com {len(parcelas)} parcela(s).', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/nova", methods=["POST"])
@login_required
def recorrente_nova():
    """Cadastra uma conta recorrente."""
    _require_financeiro_recorrentes()
    data = _parse_conta_form()
    try:
        conta = gastos_ops.create_recurring(current_user, data)
    except gastos_ops.GastoValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("gastos.recorrentes"))
    flash(f'Conta "{conta.name}" cadastrada.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/<int:conta_id>/editar", methods=["POST"])
@login_required
def recorrente_editar(conta_id: int):
    """Edita uma conta recorrente (lançamentos já criados não mudam)."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    data = _parse_conta_form()
    try:
        gastos_ops.update_recurring(conta, current_user, data)
    except gastos_ops.GastoValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("gastos.recorrentes"))
    flash(f'Conta "{conta.name}" atualizada.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/<int:conta_id>/toggle", methods=["POST"])
@login_required
def recorrente_toggle(conta_id: int):
    """Ativa/desativa uma conta (desativada: sem alertas nem lançamentos novos)."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    gastos_ops.toggle_recurring(conta, current_user)
    flash(f'Conta "{conta.name}" {"reativada" if conta.is_active else "desativada"}.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/<int:conta_id>/excluir", methods=["POST"])
@login_required
def recorrente_excluir(conta_id: int):
    """Exclui conta SEM lançamentos; com histórico, o caminho é desativar."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    try:
        gastos_ops.delete_recurring(conta, current_user)
    except gastos_ops.GastoStateError as exc:
        flash(str(exc), "error")
        return redirect(url_for("gastos.recorrentes"))
    flash(f'Conta "{conta.name}" excluída.', "success")
    return redirect(url_for("gastos.recorrentes"))


def _ref_do_form(today: date) -> str:
    """month_ref do formulário (default: mês corrente), validado."""
    raw = request.form.get("month_ref", "").strip()
    if len(raw) == 7 and raw[:4].isdigit() and raw[5:7].isdigit() and raw[4] == "-":
        return raw
    return f"{today.year:04d}-{today.month:02d}"


@gastos_bp.route("/recorrentes/<int:conta_id>/preencher", methods=["POST"])
@login_required
def recorrente_preencher(conta_id: int):
    """Preenche a conta variável do mês (valor + PIX + vencimento): lançamento a pagar."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    amount = parse_brl(request.form.get("amount", ""))
    if amount is None:
        flash("Informe o valor exato da conta (ex.: 512,30).", "error")
        return redirect(url_for("gastos.recorrentes"))
    ref = _ref_do_form(date.today())
    due_raw = request.form.get("due_date", "").strip()
    try:
        due_date = date.fromisoformat(due_raw) if due_raw else None
    except ValueError:
        due_date = None
    try:
        gastos_ops.fill_entry(
            conta, current_user, ref, amount, request.form.get("pix", "").strip(), due_date
        )
    except gastos_ops.GastoStateError as exc:
        flash(str(exc), "error")
        return redirect(url_for("gastos.recorrentes"))
    flash(f'"{conta.name}" ({ref}) preenchida — já aparece na planilha de pagamentos.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/<int:conta_id>/pular", methods=["POST"])
@login_required
def recorrente_pular(conta_id: int):
    """Pula o mês de uma conta variável (boleto não veio) — encerra o alerta sem pagamento."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    ref = _ref_do_form(date.today())
    try:
        gastos_ops.skip_entry(conta, current_user, ref)
    except gastos_ops.GastoStateError as exc:
        flash(str(exc), "error")
        return redirect(url_for("gastos.recorrentes"))
    flash(f'"{conta.name}" ({ref}) marcada como pulada neste mês.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/entry/<int:entry_id>/pagar", methods=["POST"])
@login_required
def recorrente_pagar(entry_id: int):
    """Marca um lançamento a pagar como pago (também possível na planilha de pagamentos)."""
    _require_financeiro_recorrentes()
    entry = RecurringExpenseEntry.query.get_or_404(entry_id)
    try:
        gastos_ops.pay_entry(entry, current_user)
    except gastos_ops.GastoStateError as exc:
        flash(str(exc), "error")
        return redirect(url_for("gastos.recorrentes"))
    flash("Lançamento marcado como pago.", "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/entry/<int:entry_id>/excluir-parcela", methods=["POST"])
@login_required
def recorrente_excluir_parcela(entry_id: int):
    """Exclui uma parcela avulsa de pagamento programado ainda não paga (feature 121)."""
    _require_financeiro_recorrentes()
    entry = RecurringExpenseEntry.query.get_or_404(entry_id)
    try:
        gastos_ops.delete_parcela(entry, current_user)
    except gastos_ops.GastoStateError as exc:
        flash(str(exc), "error")
        return redirect(url_for("gastos.recorrentes"))
    flash("Parcela excluída.", "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/entry/<int:entry_id>/reabrir", methods=["POST"])
@login_required
def recorrente_reabrir(entry_id: int):
    """Reabre um lançamento (pago volta a 'a pagar'; pulado é removido e volta a aguardar)."""
    _require_financeiro_recorrentes()
    entry = RecurringExpenseEntry.query.get_or_404(entry_id)
    try:
        gastos_ops.reopen_entry(entry, current_user)
    except gastos_ops.GastoStateError as exc:
        flash(str(exc), "error")
        return redirect(url_for("gastos.recorrentes"))
    flash("Lançamento reaberto.", "success")
    return redirect(url_for("gastos.recorrentes"))
