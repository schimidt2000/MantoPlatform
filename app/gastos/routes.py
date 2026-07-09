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
from app.models import (
    AuditLog, CalendarEvent, RecurringExpense, RecurringExpenseEntry, SpecialExpense, User,
)
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


# ══════════════════════════════════════════════════════════════════
#  Gastos recorrentes (feature 110) — FINANCEIRO/SUPERADMIN
# ══════════════════════════════════════════════════════════════════

def _is_financeiro() -> bool:
    """True se o usuário atual tem papel FINANCEIRO ou SUPERADMIN."""
    return any(
        r.name.upper() in (RoleName.FINANCEIRO, RoleName.SUPERADMIN)
        for r in current_user.roles
    )


def _require_financeiro_recorrentes() -> None:
    """Aborta 403 fora de FINANCEIRO/SUPERADMIN (guard das rotas de recorrentes)."""
    if not _is_financeiro():
        abort(403)


def _month_ref(year: int, month: int) -> str:
    """Formata a referência mensal: '2026-07'."""
    return f"{year:04d}-{month:02d}"


def _clamp_day(year: int, month: int, day: int) -> date:
    """Data no mês com o dia clampado no último dia (dia 31 num mês de 30 vira dia 30)."""
    import calendar as cal_mod
    _, last_day = cal_mod.monthrange(year, month)
    return date(year, month, min(max(day, 1), last_day))


def _weekly_first_date(conta: RecurringExpense, year: int, month: int) -> date | None:
    """Primeira ocorrência do dia da semana da conta no mês∩vigência (feature 113)."""
    import calendar as cal_mod
    from datetime import timedelta
    _, last_day = cal_mod.monthrange(year, month)
    lo = max(date(year, month, 1), conta.start_date or date(year, month, 1))
    hi = min(date(year, month, last_day), conta.end_date or date(year, month, last_day))
    d = lo
    while d <= hi:
        if d.weekday() == conta.anchor_weekday:
            return d
        d += timedelta(days=1)
    return None


def _conta_due_date(conta: RecurringExpense, year: int, month: int) -> date:
    """Vencimento exibido no mês: 1ª ocorrência (semanal) ou o dia do mês clampado."""
    if conta.frequency == "semanal":
        first = _weekly_first_date(conta, year, month)
        if first is not None:
            return first
    return _clamp_day(year, month, conta.due_day)


def ensure_recurring_entries(year: int, month: int) -> None:
    """Cria os lançamentos 'registrado' do mês para os fixos ativos (idempotente).

    Padrão de geração preguiçosa (mesmo dos salários): chamada pelas telas que consomem os
    dados; a unique (recurring_id, month_ref) garante 1 lançamento por conta/mês. Faz commit.
    """
    ref = _month_ref(year, month)
    fixed = RecurringExpense.query.filter(
        RecurringExpense.is_active.is_(True),
        RecurringExpense.expense_type.in_(["debito_automatico", "assinatura"]),
    ).all()
    if not fixed:
        return
    existing_ids = {
        e.recurring_id
        for e in RecurringExpenseEntry.query.filter_by(month_ref=ref).all()
    }
    created = False
    for r in fixed:
        if r.id in existing_ids or r.amount is None:
            continue
        # Feature 112: frequência/vigência — 0 ocorrências = sem lançamento no mês;
        # semanal/quinzenal multiplicam o valor pelas ocorrências do mês.
        occurrences = r.occurrences_in_month(year, month)
        if occurrences == 0:
            continue
        db.session.add(RecurringExpenseEntry(
            recurring_id=r.id,
            month_ref=ref,
            amount=r.amount * occurrences,
            due_date=_conta_due_date(r, year, month),
            status="registrado",
        ))
        created = True
    if created:
        db.session.commit()


def recurring_alerts(today: date) -> list[dict]:
    """Alertas do mês corrente para contas variáveis ativas (home, feature 110).

    A partir do dia esperado (clampado no fim do mês): sem lançamento vira "aguardando";
    lançamento a_pagar vira "a_pagar" (com valor). pago/pulado: sem alerta.
    """
    ref = _month_ref(today.year, today.month)
    variaveis = RecurringExpense.query.filter(
        RecurringExpense.is_active.is_(True),
        RecurringExpense.expense_type == "variavel",
    ).order_by(RecurringExpense.due_day.asc(), RecurringExpense.name.asc()).all()
    if not variaveis:
        return []
    entries = {
        e.recurring_id: e
        for e in RecurringExpenseEntry.query.filter(
            RecurringExpenseEntry.month_ref == ref,
            RecurringExpenseEntry.recurring_id.in_([r.id for r in variaveis]),
        ).all()
    }
    alerts = []
    for r in variaveis:
        # Feature 112: fora da vigência ou fora do ciclo (anual) não alerta.
        if r.occurrences_in_month(today.year, today.month) == 0:
            continue
        # Feature 113: semanal alerta a partir da 1ª ocorrência do dia da semana no mês.
        if today < _conta_due_date(r, today.year, today.month):
            continue
        entry = entries.get(r.id)
        if entry is None:
            alerts.append({"conta": r, "estado": "aguardando", "entry": None})
        elif entry.status == "a_pagar":
            alerts.append({"conta": r, "estado": "a_pagar", "entry": entry})
    return alerts


def _log_recorrente(action: str, conta: RecurringExpense, detail: str = "") -> None:
    """Auditoria das ações de gastos recorrentes."""
    db.session.add(AuditLog(
        actor_name=current_user.name,
        actor_role=", ".join(r.name for r in current_user.roles),
        entity_type="gasto_recorrente",
        entity_id=conta.id,
        entity_name=conta.name,
        action=action,
        detail=detail,
    ))


def _parse_conta_form() -> dict | None:
    """Lê e valida o formulário de conta recorrente; None (com flash) se inválido."""
    name = request.form.get("name", "").strip()
    expense_type = request.form.get("expense_type", "").strip()
    if not name or expense_type not in RecurringExpense.TYPES:
        flash("Informe nome e tipo da conta.", "error")
        return None
    frequency = request.form.get("frequency", "mensal").strip()
    if frequency not in RecurringExpense.FREQUENCIES:
        frequency = "mensal"
    # Semanal (feature 113): dia da SEMANA obrigatório; dia do mês fica irrelevante (=1).
    weekday = None
    if frequency == "semanal":
        wd_raw = request.form.get("weekday", "").strip()
        if not wd_raw.isdigit() or not 0 <= int(wd_raw) <= 6:
            flash("Escolha o dia da semana da cobrança semanal.", "error")
            return None
        weekday = int(wd_raw)
        due_day = 1
    else:
        day_raw = request.form.get("due_day", "").strip()
        if not day_raw.isdigit():
            flash("Informe o dia (1 a 31) da conta.", "error")
            return None
        due_day = int(day_raw)
        if not 1 <= due_day <= 31:
            flash("Dia deve estar entre 1 e 31.", "error")
            return None
    amount = parse_brl(request.form.get("amount", ""))
    if expense_type != "variavel" and (amount is None or amount <= 0):
        flash("Informe o valor fixo da conta (ex.: 1.000,00).", "error")
        return None
    # Referência da conta variável (feature 111): faixa (min–max) OU valor exato esperado
    # (reusa o campo "amount"). Salvar um modo zera os campos do outro.
    ref_mode = request.form.get("ref_mode", "faixa")
    if expense_type == "variavel":
        var_amount = amount if ref_mode == "exato" else None
        var_min = parse_brl(request.form.get("amount_min", "")) if ref_mode != "exato" else None
        var_max = parse_brl(request.form.get("amount_max", "")) if ref_mode != "exato" else None
    # Vigência (feature 112).
    try:
        start_raw = request.form.get("start_date", "").strip()
        start_date = date.fromisoformat(start_raw) if start_raw else date.today()
    except ValueError:
        start_date = date.today()
    end_raw = request.form.get("end_date", "").strip()
    try:
        end_date = date.fromisoformat(end_raw) if end_raw else None
    except ValueError:
        end_date = None
    if end_date and end_date < start_date:
        flash("A data de fim não pode ser anterior à data de início.", "error")
        return None
    return {
        "name": name,
        "expense_type": expense_type,
        "due_day": due_day,
        "frequency": frequency,
        "weekday": weekday,
        "start_date": start_date,
        "end_date": end_date,
        "amount": amount if expense_type != "variavel" else var_amount,
        "amount_min": var_min if expense_type == "variavel" else None,
        "amount_max": var_max if expense_type == "variavel" else None,
        "default_pix": request.form.get("default_pix", "").strip() or None,
        "card_name": (request.form.get("card_name", "").strip() or None) if expense_type == "assinatura" else None,
        "notes": request.form.get("notes", "").strip() or None,
    }


@gastos_bp.route("/recorrentes")
@login_required
def recorrentes():
    """Tela de gastos recorrentes: contas por tipo + status do mês (FINANCEIRO/SUPERADMIN)."""
    _require_financeiro_recorrentes()
    today = date.today()
    month = request.args.get("month", "").strip()
    try:
        year_i, month_i = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        year_i, month_i = today.year, today.month
    ref = _month_ref(year_i, month_i)

    ensure_recurring_entries(year_i, month_i)

    contas = RecurringExpense.query.order_by(
        RecurringExpense.is_active.desc(), RecurringExpense.due_day.asc(),
        RecurringExpense.name.asc(),
    ).all()
    entries = {
        e.recurring_id: e
        for e in RecurringExpenseEntry.query.filter_by(month_ref=ref).all()
    }
    grupos = {t: [c for c in contas if c.expense_type == t] for t in RecurringExpense.TYPES}

    # Histórico expandido de uma conta (?conta=ID)
    hist_conta = None
    raw_conta = request.args.get("conta", "").strip()
    if raw_conta.isdigit():
        hist_conta = RecurringExpense.query.get(int(raw_conta))

    # Soma mensal estimada por tipo (fixos: valor; variáveis: exato esperado ou teto da faixa).
    # Feature 112: ajustada pela frequência (semanal ×4, quinzenal ×2, anual ÷12) —
    # referência visual, não competência.
    def _estimate(c: RecurringExpense):
        # Pagamento programado (feature 121) é um cronograma finito e não regular — não
        # entra na estimativa "R$/mês" das demais contas.
        if c.expense_type == "programado":
            return Decimal("0")
        base = (c.amount or 0) if c.is_fixed else (c.amount or c.amount_max or c.amount_min or 0)
        base = Decimal(str(base))
        freq = c.frequency or "mensal"
        if freq == "semanal":
            return base * 4
        if freq == "quinzenal":
            return base * 2
        if freq == "anual":
            return (base / 12).quantize(Decimal("0.01"))
        return base
    somas = {
        t: sum((Decimal(str(_estimate(c))) for c in grupos[t] if c.is_active), Decimal("0"))
        for t in RecurringExpense.TYPES
    }

    # Pagamentos programados ativos: soma das parcelas ainda "a_pagar" (feature 121).
    programado_pendente_total = sum(
        (e.amount or Decimal("0")
         for c in grupos["programado"] if c.is_active
         for e in c.entries if e.status == "a_pagar"),
        Decimal("0"),
    )

    return render_template(
        "gastos/recorrentes.html",
        grupos=grupos,
        entries=entries,
        somas=somas,
        programado_pendente_total=programado_pendente_total,
        month_ref=ref,
        ref_year=year_i,
        ref_month=month_i,
        is_current_month=(ref == _month_ref(today.year, today.month)),
        type_labels=RecurringExpense.TYPE_LABELS,
        frequency_labels=RecurringExpense.FREQUENCY_LABELS,
        hist_conta=hist_conta,
        today=today,
        fmt_brl=_fmt_brl,
    )


def _parse_programado_form() -> dict | None:
    """Lê e valida o formulário de pagamento programado (feature 121).

    Retorna ``{"name", "default_pix", "notes", "parcelas": [(date, Decimal), ...]}`` ou
    ``None`` (com flash) se inválido. ``parcelas`` já vem com uma data+valor por linha,
    seja "mesmo valor para todas" ou "valor individual por data".
    """
    name = request.form.get("name", "").strip()
    if not name:
        flash("Informe o nome/descrição do pagamento programado.", "error")
        return None

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
            return None
    if not dates:
        flash("Informe ao menos uma data de parcela.", "error")
        return None

    parcelas: list[tuple[date, Decimal]] = []
    if same_value:
        amount = parse_brl(request.form.get("sched_amount_same", ""))
        if amount is None or amount <= 0:
            flash("Informe o valor das parcelas (ex.: 1.500,00).", "error")
            return None
        parcelas = [(d, amount) for d in dates]
    else:
        amounts_raw = request.form.getlist("sched_amount[]")
        if len(amounts_raw) != len(dates_raw):
            flash("Cada data precisa do seu valor.", "error")
            return None
        # Alinha pelos mesmos índices não vazios usados na coleta de datas.
        idx = 0
        for raw_date, raw_amount in zip(dates_raw, amounts_raw, strict=True):
            if not (raw_date or "").strip():
                continue
            amount = parse_brl(raw_amount)
            if amount is None or amount <= 0:
                flash(f"Valor inválido para a data {dates[idx].strftime('%d/%m/%Y')}.", "error")
                return None
            parcelas.append((dates[idx], amount))
            idx += 1

    return {
        "name": name,
        "default_pix": request.form.get("default_pix", "").strip() or None,
        "notes": request.form.get("notes", "").strip() or None,
        "parcelas": parcelas,
    }


@gastos_bp.route("/recorrentes/programado/nova", methods=["POST"])
@login_required
def recorrente_programado_nova():
    """Cadastra um pagamento programado: N parcelas com data e valor próprios (feature 121).

    Diferente das demais contas recorrentes, as parcelas nascem todas de uma vez — já
    aparecem na planilha de pagamentos na data certa, sem geração posterior por mês.
    """
    _require_financeiro_recorrentes()
    data = _parse_programado_form()
    if data is None:
        return redirect(url_for("gastos.recorrentes"))

    parcelas = data.pop("parcelas")
    conta = RecurringExpense(
        created_by_id=current_user.id,
        expense_type="programado",
        due_day=1,
        frequency="mensal",
        start_date=min(d for d, _ in parcelas),
        end_date=max(d for d, _ in parcelas),
        **data,
    )
    db.session.add(conta)
    db.session.flush()
    for due, amount in parcelas:
        db.session.add(RecurringExpenseEntry(
            recurring_id=conta.id,
            month_ref=due.strftime("%Y-%m"),
            amount=amount,
            pix=conta.default_pix,
            due_date=due,
            status="a_pagar",
        ))
    _log_recorrente(
        "create", conta,
        f"Pagamento programado criado: {len(parcelas)} parcela(s)")
    db.session.commit()
    flash(f'Pagamento "{conta.name}" cadastrado com {len(parcelas)} parcela(s).', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/nova", methods=["POST"])
@login_required
def recorrente_nova():
    """Cadastra uma conta recorrente."""
    _require_financeiro_recorrentes()
    data = _parse_conta_form()
    if data is None:
        return redirect(url_for("gastos.recorrentes"))
    conta = RecurringExpense(created_by_id=current_user.id, **data)
    db.session.add(conta)
    db.session.flush()
    _log_recorrente("create", conta, f"Conta recorrente criada ({data['expense_type']})")
    db.session.commit()
    flash(f'Conta "{conta.name}" cadastrada.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/<int:conta_id>/editar", methods=["POST"])
@login_required
def recorrente_editar(conta_id: int):
    """Edita uma conta recorrente (lançamentos já criados não mudam)."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    data = _parse_conta_form()
    if data is None:
        return redirect(url_for("gastos.recorrentes"))
    for key, value in data.items():
        setattr(conta, key, value)
    _log_recorrente("edit", conta, "Conta recorrente editada")
    db.session.commit()
    flash(f'Conta "{conta.name}" atualizada.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/<int:conta_id>/toggle", methods=["POST"])
@login_required
def recorrente_toggle(conta_id: int):
    """Ativa/desativa uma conta (desativada: sem alertas nem lançamentos novos)."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    conta.is_active = not conta.is_active
    _log_recorrente("toggle", conta, "Reativada" if conta.is_active else "Desativada")
    db.session.commit()
    flash(f'Conta "{conta.name}" {"reativada" if conta.is_active else "desativada"}.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/<int:conta_id>/excluir", methods=["POST"])
@login_required
def recorrente_excluir(conta_id: int):
    """Exclui conta SEM lançamentos; com histórico, o caminho é desativar."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    if RecurringExpenseEntry.query.filter_by(recurring_id=conta.id).count():
        flash("Conta com lançamentos não pode ser excluída — desative-a.", "error")
        return redirect(url_for("gastos.recorrentes"))
    _log_recorrente("delete", conta, "Conta recorrente excluída (sem lançamentos)")
    db.session.delete(conta)
    db.session.commit()
    flash(f'Conta "{conta.name}" excluída.', "success")
    return redirect(url_for("gastos.recorrentes"))


def _entry_do_mes(conta: RecurringExpense, ref: str) -> RecurringExpenseEntry | None:
    return RecurringExpenseEntry.query.filter_by(recurring_id=conta.id, month_ref=ref).first()


def _ref_do_form(today: date) -> str:
    """month_ref do formulário (default: mês corrente), validado."""
    raw = request.form.get("month_ref", "").strip()
    if len(raw) == 7 and raw[:4].isdigit() and raw[5:7].isdigit() and raw[4] == "-":
        return raw
    return _month_ref(today.year, today.month)


@gastos_bp.route("/recorrentes/<int:conta_id>/preencher", methods=["POST"])
@login_required
def recorrente_preencher(conta_id: int):
    """Preenche a conta variável do mês (valor + PIX + vencimento): lançamento a pagar."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    if conta.expense_type != "variavel":
        flash("Só contas variáveis são preenchidas manualmente.", "error")
        return redirect(url_for("gastos.recorrentes"))
    amount = _parse_brl(request.form.get("amount", ""))
    if amount is None:
        flash("Informe o valor exato da conta (ex.: 512,30).", "error")
        return redirect(url_for("gastos.recorrentes"))
    today = date.today()
    ref = _ref_do_form(today)
    due_raw = request.form.get("due_date", "").strip()
    try:
        due_date = date.fromisoformat(due_raw) if due_raw else None
    except ValueError:
        due_date = None

    entry = _entry_do_mes(conta, ref)
    if entry and entry.status == "pago":
        flash("Lançamento já pago — não pode ser alterado.", "error")
        return redirect(url_for("gastos.recorrentes"))
    if entry is None:
        entry = RecurringExpenseEntry(recurring_id=conta.id, month_ref=ref)
        db.session.add(entry)
    entry.amount = amount
    entry.pix = request.form.get("pix", "").strip() or conta.default_pix
    entry.due_date = due_date
    entry.status = "a_pagar"
    entry.filled_by_id = current_user.id
    entry.filled_at = datetime.utcnow()
    _log_recorrente("fill", conta, f"Conta de {ref} preenchida: {_fmt_brl(amount)}")
    db.session.commit()
    flash(f'"{conta.name}" ({ref}) preenchida — já aparece na planilha de pagamentos.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/<int:conta_id>/pular", methods=["POST"])
@login_required
def recorrente_pular(conta_id: int):
    """Pula o mês de uma conta variável (boleto não veio) — encerra o alerta sem pagamento."""
    _require_financeiro_recorrentes()
    conta = RecurringExpense.query.get_or_404(conta_id)
    if conta.expense_type != "variavel":
        flash("Só contas variáveis podem pular o mês.", "error")
        return redirect(url_for("gastos.recorrentes"))
    today = date.today()
    ref = _ref_do_form(today)
    entry = _entry_do_mes(conta, ref)
    if entry and entry.status == "pago":
        flash("Lançamento já pago — não pode ser pulado.", "error")
        return redirect(url_for("gastos.recorrentes"))
    if entry is None:
        entry = RecurringExpenseEntry(recurring_id=conta.id, month_ref=ref)
        db.session.add(entry)
    entry.amount = None
    entry.pix = None
    entry.due_date = None
    entry.status = "pulado"
    entry.filled_by_id = current_user.id
    entry.filled_at = datetime.utcnow()
    _log_recorrente("skip", conta, f"Mês {ref} pulado (conta não veio)")
    db.session.commit()
    flash(f'"{conta.name}" ({ref}) marcada como pulada neste mês.', "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/entry/<int:entry_id>/pagar", methods=["POST"])
@login_required
def recorrente_pagar(entry_id: int):
    """Marca um lançamento a pagar como pago (também possível na planilha de pagamentos)."""
    _require_financeiro_recorrentes()
    entry = RecurringExpenseEntry.query.get_or_404(entry_id)
    if entry.status != "a_pagar":
        flash("Só lançamentos a pagar podem ser marcados como pagos.", "error")
        return redirect(url_for("gastos.recorrentes"))
    entry.status = "pago"
    entry.paid_at = date.today()
    _log_recorrente("pay", entry.recurring, f"Conta de {entry.month_ref} paga: {_fmt_brl(entry.amount)}")
    db.session.commit()
    flash("Lançamento marcado como pago.", "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/entry/<int:entry_id>/excluir-parcela", methods=["POST"])
@login_required
def recorrente_excluir_parcela(entry_id: int):
    """Exclui uma parcela avulsa de pagamento programado ainda não paga (feature 121)."""
    _require_financeiro_recorrentes()
    entry = RecurringExpenseEntry.query.get_or_404(entry_id)
    conta = entry.recurring
    if not conta or conta.expense_type != "programado":
        flash("Esta ação só vale para parcelas de pagamento programado.", "error")
        return redirect(url_for("gastos.recorrentes"))
    if entry.status == "pago":
        flash("Parcela já paga não pode ser excluída.", "error")
        return redirect(url_for("gastos.recorrentes"))
    detail = f"Parcela de {entry.due_date.strftime('%d/%m/%Y') if entry.due_date else entry.month_ref} excluída: {_fmt_brl(entry.amount)}"
    db.session.delete(entry)
    _log_recorrente("delete_parcela", conta, detail)
    db.session.commit()
    flash("Parcela excluída.", "success")
    return redirect(url_for("gastos.recorrentes"))


@gastos_bp.route("/recorrentes/entry/<int:entry_id>/reabrir", methods=["POST"])
@login_required
def recorrente_reabrir(entry_id: int):
    """Reabre um lançamento (pago volta a 'a pagar'; pulado é removido e volta a aguardar)."""
    _require_financeiro_recorrentes()
    entry = RecurringExpenseEntry.query.get_or_404(entry_id)
    conta = entry.recurring
    if entry.status == "pago":
        entry.status = "a_pagar"
        entry.paid_at = None
        detail = f"Pagamento de {entry.month_ref} reaberto"
    elif entry.status == "pulado":
        db.session.delete(entry)
        detail = f"Pulo de {entry.month_ref} desfeito (volta a aguardar valor)"
    else:
        flash("Este lançamento não pode ser reaberto.", "error")
        return redirect(url_for("gastos.recorrentes"))
    _log_recorrente("reopen", conta, detail)
    db.session.commit()
    flash("Lançamento reaberto.", "success")
    return redirect(url_for("gastos.recorrentes"))
