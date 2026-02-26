from datetime import datetime, date, timedelta
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models import CalendarEvent, EventRole, SiteSetting, User, Role, SalaryHistory

financeiro_bp = Blueprint("financeiro", __name__)

DEFAULT_COMMISSION = 2.0


def _has_role(*names):
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def require_financeiro(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _has_role("FINANCEIRO", "SUPERADMIN"):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def require_vendas(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _has_role("VENDAS", "FINANCEIRO", "SUPERADMIN"):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def _get_commission_rate(event, settings):
    if event.commission_rate is not None:
        return event.commission_rate
    if settings and settings.default_commission_rate is not None:
        return settings.default_commission_rate
    return DEFAULT_COMMISSION


def _event_cost(event):
    return sum(r.cache_value or 0 for r in event.roles if r.talent_id)


def _event_commission(event, settings):
    if not event.sale_value:
        return 0.0
    rate = _get_commission_rate(event, settings)
    return round(event.sale_value * rate / 100, 2)


# ─── FINANCEIRO ROUTES ──────────────────────────────────────────────────────

@financeiro_bp.route("/financeiro/")
@login_required
@require_financeiro
def dashboard():
    settings = SiteSetting.query.get(1)

    # filtro de período
    period = request.args.get("period", "30")
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    today = date.today()
    if period == "7":
        start_date = today - timedelta(days=6)
        end_date = today
    elif period == "custom" and start_str and end_str:
        try:
            start_date = date.fromisoformat(start_str)
            end_date = date.fromisoformat(end_str)
        except ValueError:
            start_date = today - timedelta(days=29)
            end_date = today
    else:  # default 30
        start_date = today - timedelta(days=29)
        end_date = today

    events = (
        CalendarEvent.query
        .filter(
            CalendarEvent.start_at >= datetime.combine(start_date, datetime.min.time()),
            CalendarEvent.start_at <= datetime.combine(end_date, datetime.max.time()),
        )
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    total_receita = sum(e.sale_value or 0 for e in events)
    total_custo = sum(_event_cost(e) for e in events)
    total_lucro = total_receita - total_custo
    total_comissoes = sum(_event_commission(e, settings) for e in events)

    events_data = []
    for e in events:
        custo = _event_cost(e)
        comissao = _event_commission(e, settings)
        rate = _get_commission_rate(e, settings)
        events_data.append({
            "event": e,
            "custo": custo,
            "lucro": (e.sale_value or 0) - custo,
            "comissao": comissao,
            "rate": rate,
        })

    return render_template(
        "financeiro/dashboard.html",
        events_data=events_data,
        total_receita=total_receita,
        total_custo=total_custo,
        total_lucro=total_lucro,
        total_comissoes=total_comissoes,
        settings=settings,
        period=period,
        start_str=start_str or "",
        end_str=end_str or "",
    )


@financeiro_bp.route("/financeiro/funcionarios")
@login_required
@require_financeiro
def funcionarios():
    settings = SiteSetting.query.get(1)
    users = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    users_data = []
    for u in users:
        current = u.salary_histories.filter_by(end_date=None).order_by(SalaryHistory.start_date.desc()).first()
        users_data.append({"user": u, "current_salary": current})

    return render_template(
        "financeiro/funcionarios.html",
        users_data=users_data,
        settings=settings,
    )


@financeiro_bp.route("/financeiro/funcionarios/<int:user_id>", methods=["GET", "POST"])
@login_required
@require_financeiro
def funcionario_detail(user_id: int):
    settings = SiteSetting.query.get(1)
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        salary_raw = request.form.get("salary", "").strip()
        payment_type = request.form.get("payment_type", "").strip()
        start_str = request.form.get("start_date", "").strip()
        notes = request.form.get("notes", "").strip()

        errors = []
        if not salary_raw or not salary_raw.isdigit():
            errors.append("Salário inválido.")
        if payment_type not in ("semanal", "quinzenal", "comissao"):
            errors.append("Tipo de pagamento inválido.")
        try:
            start_date = date.fromisoformat(start_str) if start_str else date.today()
        except ValueError:
            errors.append("Data de início inválida.")
            start_date = date.today()

        if not errors:
            # encerra o salário vigente
            current = user.salary_histories.filter_by(end_date=None).first()
            if current:
                current.end_date = start_date

            db.session.add(SalaryHistory(
                user_id=user.id,
                salary=int(salary_raw),
                payment_type=payment_type,
                start_date=start_date,
                notes=notes or None,
            ))
            db.session.commit()
            return redirect(url_for("financeiro.funcionario_detail", user_id=user.id))

        history = user.salary_histories.order_by(SalaryHistory.start_date.desc()).all()
        return render_template(
            "financeiro/funcionario_detail.html",
            user=user,
            history=history,
            settings=settings,
            errors=errors,
        )

    history = user.salary_histories.order_by(SalaryHistory.start_date.desc()).all()
    return render_template(
        "financeiro/funcionario_detail.html",
        user=user,
        history=history,
        settings=settings,
        errors=[],
    )


# ─── VENDAS ROUTES ───────────────────────────────────────────────────────────

@financeiro_bp.route("/vendas/")
@login_required
@require_vendas
def pipeline():
    settings = SiteSetting.query.get(1)
    is_financeiro = _has_role("FINANCEIRO", "SUPERADMIN")

    events = (
        CalendarEvent.query
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    events_data = []
    for e in events:
        custo = _event_cost(e)
        comissao = _event_commission(e, settings)
        events_data.append({
            "event": e,
            "custo": custo,
            "comissao": comissao,
        })

    return render_template(
        "vendas/pipeline.html",
        events_data=events_data,
        settings=settings,
        is_financeiro=is_financeiro,
    )
