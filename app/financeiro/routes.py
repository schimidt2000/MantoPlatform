import csv
import io
from collections import defaultdict
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, abort, make_response
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models import CalendarEvent, EventRole, SiteSetting, User, Role, SalaryHistory, CRMDeal, CRMStage

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
        if not _has_role("COMERCIAL", "FINANCEIRO", "SUPERADMIN"):
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

def _month_range(year: int, month: int):
    """Retorna (start_dt, end_dt) para um mês."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return (
        datetime.combine(start, datetime.min.time()),
        datetime.combine(end, datetime.min.time()),
    )


def _prev_month(year: int, month: int):
    if month == 1:
        return year - 1, 12
    return year, month - 1


@financeiro_bp.route("/financeiro/")
@login_required
@require_financeiro
def dashboard():
    settings = SiteSetting.query.get(1)
    today = date.today()

    # ── Filtro de período ─────────────────────────────────────────────────────
    period = request.args.get("period", "30")
    start_str = request.args.get("start")
    end_str = request.args.get("end")

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
    else:
        period = "30"
        start_date = today - timedelta(days=29)
        end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt   = datetime.combine(end_date, datetime.max.time())

    events = (
        CalendarEvent.query
        .filter(CalendarEvent.start_at >= start_dt, CalendarEvent.start_at <= end_dt)
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    # ── Demonstração de Resultado Gerencial (DRG) ─────────────────────────────
    # Receita Bruta: soma dos sale_values do período
    receita_bruta = sum(e.sale_value or 0 for e in events)

    # CPV — Custo dos Serviços (cachês pagos a talentos)
    cpv = sum(_event_cost(e) for e in events)

    # Lucro Bruto = Receita - CPV
    lucro_bruto = receita_bruta - cpv
    margem_bruta = round(lucro_bruto / receita_bruta * 100, 1) if receita_bruta else 0

    # Comissões de vendas
    total_comissoes = sum(_event_commission(e, settings) for e in events)

    # Despesas com pessoal (salários fixos vigentes — estimativa pro-rata)
    period_days = (end_date - start_date).days + 1
    current_salaries = SalaryHistory.query.filter_by(end_date=None).all()
    # Custo mensal → diário → pro-rata do período
    custo_pessoal = round(
        sum(s.salary for s in current_salaries) / 30 * period_days, 0
    )

    # EBITDA / Resultado Operacional = Lucro Bruto - Comissões - Pessoal
    ebitda = lucro_bruto - total_comissoes - custo_pessoal
    margem_ebitda = round(ebitda / receita_bruta * 100, 1) if receita_bruta else 0

    # ── Indicadores Comerciais ────────────────────────────────────────────────
    eventos_com_venda = [e for e in events if e.sale_value]
    ticket_medio = round(receita_bruta / len(eventos_com_venda), 0) if eventos_com_venda else 0

    # Custo de talento como % da receita
    ratio_custo_talento = round(cpv / receita_bruta * 100, 1) if receita_bruta else 0

    # Receita por tipo de evento
    receita_por_tipo = defaultdict(int)
    for e in eventos_com_venda:
        receita_por_tipo[e.event_type or "Outros"] += (e.sale_value or 0)
    receita_por_tipo = dict(sorted(receita_por_tipo.items(), key=lambda x: -x[1]))

    # Top vendedores por receita
    seller_revenue = defaultdict(int)
    seller_margin  = defaultdict(int)
    for e in eventos_com_venda:
        if e.seller_id:
            seller_revenue[e.seller_id] += (e.sale_value or 0)
            seller_margin[e.seller_id]  += (e.sale_value or 0) - _event_cost(e)
    top_sellers = []
    for sid, rev in sorted(seller_revenue.items(), key=lambda x: -x[1])[:5]:
        u = User.query.get(sid)
        if u:
            top_sellers.append({"user": u, "receita": rev, "lucro": seller_margin[sid]})

    # ── CRM — Pipeline e Conversão ────────────────────────────────────────────
    all_deals = CRMDeal.query.all()
    deals_won  = [d for d in all_deals if d.stage and d.stage.is_won]
    deals_lost = [d for d in all_deals if d.stage and d.stage.is_lost]
    deals_open = [d for d in all_deals if d.stage and not d.stage.is_won and not d.stage.is_lost]

    n_won, n_lost = len(deals_won), len(deals_lost)
    taxa_conversao = round(n_won / (n_won + n_lost) * 100, 1) if (n_won + n_lost) else 0
    pipeline_value = sum(d.value or 0 for d in deals_open)

    # Tempo médio de fechamento (dias entre criação e fechamento dos deals ganhos)
    tempos = [(d.closed_at - d.created_at).days for d in deals_won if d.closed_at and d.created_at]
    tempo_medio_fechamento = round(sum(tempos) / len(tempos), 0) if tempos else None

    # LTV por organização (top 5)
    org_ltv = defaultdict(int)
    for d in deals_won:
        if d.organization_id:
            org_ltv[d.organization_id] += (d.value or 0)
    top_orgs = []
    for oid, ltv in sorted(org_ltv.items(), key=lambda x: -x[1])[:5]:
        from app.models import CRMOrganization
        org = CRMOrganization.query.get(oid)
        if org:
            top_orgs.append({"org": org, "ltv": ltv})

    # ── Caixa / A Receber ─────────────────────────────────────────────────────
    # Pagamentos pendentes a talentos no período
    roles_no_periodo = [r for e in events for r in e.roles if r.talent_id]
    pagamentos_pendentes = sum(
        r.cache_value or 0 for r in roles_no_periodo
        if r.payment_status == "nao_pago"
    )
    pagamentos_realizados = sum(
        r.cache_value or 0 for r in roles_no_periodo
        if r.payment_status in ("pago", "no_banco")
    )

    # ── Tendência mensal (últimos 6 meses) ───────────────────────────────────
    monthly_trend = []
    y, m = today.year, today.month
    for _ in range(6):
        s_dt, e_dt = _month_range(y, m)
        evs = CalendarEvent.query.filter(
            CalendarEvent.start_at >= s_dt,
            CalendarEvent.start_at < e_dt,
        ).all()
        rec = sum(e.sale_value or 0 for e in evs)
        cst = sum(_event_cost(e) for e in evs)
        monthly_trend.insert(0, {
            "label": f"{m:02d}/{str(y)[2:]}",
            "receita": rec,
            "custo": cst,
            "lucro": rec - cst,
            "n_eventos": len(evs),
        })
        y, m = _prev_month(y, m)

    # ── Tabela de eventos do período ─────────────────────────────────────────
    events_data = []
    for e in events:
        custo = _event_cost(e)
        comissao = _event_commission(e, settings)
        events_data.append({
            "event": e,
            "custo": custo,
            "lucro": (e.sale_value or 0) - custo,
            "comissao": comissao,
            "rate": _get_commission_rate(e, settings),
        })

    return render_template(
        "financeiro/dashboard.html",
        # DRG
        receita_bruta=receita_bruta,
        cpv=cpv,
        lucro_bruto=lucro_bruto,
        margem_bruta=margem_bruta,
        total_comissoes=total_comissoes,
        custo_pessoal=custo_pessoal,
        ebitda=ebitda,
        margem_ebitda=margem_ebitda,
        # Comercial
        ticket_medio=ticket_medio,
        ratio_custo_talento=ratio_custo_talento,
        receita_por_tipo=receita_por_tipo,
        top_sellers=top_sellers,
        # CRM
        taxa_conversao=taxa_conversao,
        pipeline_value=pipeline_value,
        tempo_medio_fechamento=tempo_medio_fechamento,
        top_orgs=top_orgs,
        n_won=n_won,
        n_lost=n_lost,
        # Caixa
        pagamentos_pendentes=pagamentos_pendentes,
        pagamentos_realizados=pagamentos_realizados,
        # Tendência
        monthly_trend=monthly_trend,
        # Tabela
        events_data=events_data,
        total_receita=receita_bruta,
        total_custo=cpv,
        total_lucro=lucro_bruto,
        # Filtros
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
            from app.utils import audit
            audit("create", "salary", user.id, user.name,
                  f"Salário registrado: R${salary_raw} ({payment_type}) a partir de {start_date}")
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


# ─── PAGAMENTOS ROUTES ───────────────────────────────────────────────────────

_STATUS_LABELS = {
    "nao_pago": "Não pago",
    "pago":     "Pago",
    "no_banco": "No banco",
}
_VALID_PAYMENT_STATUS = set(_STATUS_LABELS.keys())


def _pagamentos_query(month_str: str):
    """Returns EventRole queryset for roles with talent assigned in the given month (YYYY-MM)."""
    try:
        year, month = int(month_str[:4]), int(month_str[5:7])
    except (ValueError, IndexError):
        today = date.today()
        year, month = today.year, today.month

    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    return (
        EventRole.query
        .join(CalendarEvent)
        .filter(
            EventRole.talent_id.isnot(None),
            CalendarEvent.start_at >= start,
            CalendarEvent.start_at < end,
        )
        .order_by(CalendarEvent.start_at.asc(), CalendarEvent.title.asc())
        .all()
    )


@financeiro_bp.route("/financeiro/pagamentos")
@login_required
@require_financeiro
def pagamentos():
    today = date.today()
    month = request.args.get("month", today.strftime("%Y-%m"))
    roles = _pagamentos_query(month)
    return render_template(
        "financeiro/pagamentos.html",
        roles=roles,
        month=month,
        status_labels=_STATUS_LABELS,
    )


@financeiro_bp.route("/financeiro/pagamentos/set-status", methods=["POST"])
@login_required
@require_financeiro
def set_payment_status():
    role_id = request.form.get("role_id")
    status  = request.form.get("payment_status")
    next_url = request.form.get("next", url_for("financeiro.pagamentos"))
    if role_id and status in _VALID_PAYMENT_STATUS:
        role = EventRole.query.get(role_id)
        if role:
            old_status = role.payment_status
            role.payment_status = status
            from app.utils import audit
            talent_name = role.talent.full_name if role.talent else "—"
            audit("payment", "event_role", role.id, talent_name,
                  f"Pagamento: {old_status} → {status} | {role.character_name}")
            db.session.commit()
    return redirect(next_url)


@financeiro_bp.route("/financeiro/pagamentos/export")
@login_required
@require_financeiro
def export_pagamentos():
    today = date.today()
    month = request.args.get("month", today.strftime("%Y-%m"))
    roles = _pagamentos_query(month)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data", "Evento", "Função", "Nome", "Valor", "Pix", "Situação"])
    for r in roles:
        writer.writerow([
            r.event.start_at.strftime("%d/%m/%Y") if r.event.start_at else "",
            r.event.title,
            r.character_name,
            r.talent.full_name if r.talent else "",
            r.cache_value or "",
            r.talent.pix_key if r.talent else "",
            _STATUS_LABELS.get(r.payment_status, r.payment_status),
        ])

    resp = make_response(output.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f"attachment; filename=pagamentos_{month}.csv"
    return resp


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
