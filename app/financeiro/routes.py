import csv
import io
from collections import defaultdict
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, abort, make_response
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models import CalendarEvent, EventRole, SiteSetting, User, Role, SalaryHistory, CRMDeal, CRMStage, CommissionPayment, SalaryPayment
from app.constants import RoleName

financeiro_bp = Blueprint("financeiro", __name__)

DEFAULT_COMMISSION = Decimal("2")


def _has_role(*names):
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def require_financeiro(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def require_vendas(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def _get_commission_rate(event, settings) -> Decimal:
    """Returns commission rate as Decimal (never float)."""
    if event.commission_rate is not None:
        return Decimal(str(event.commission_rate))
    if settings and settings.default_commission_rate is not None:
        return Decimal(str(settings.default_commission_rate))
    return DEFAULT_COMMISSION


def _event_cost(event) -> int:
    return sum(r.cache_value or 0 for r in event.roles if r.talent_id)


def _event_commission(event, settings) -> Decimal:
    if not event.sale_value:
        return Decimal("0")
    if event.seller and not event.seller.receives_commission:
        return Decimal("0")
    rate = _get_commission_rate(event, settings)
    return (Decimal(event.sale_value) * rate / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _sync_commission_payment(event: CalendarEvent) -> None:
    """Cria ou atualiza o CommissionPayment de um evento. Não faz commit."""
    existing = CommissionPayment.query.filter_by(event_id=event.id).filter(
        CommissionPayment.status != "cancelado"
    ).first()

    should_have = (
        event.sale_value
        and event.seller_id
        and event.seller
        and event.seller.receives_commission
    )

    if not should_have:
        if existing and existing.status == "a_pagar":
            existing.status = "cancelado"
            existing.notes = (existing.notes or "") + " | Cancelado: sem comissão elegível"
        return

    amount = _event_commission(event, SiteSetting.query.get(1))
    if existing:
        if existing.status == "a_pagar":
            existing.amount = amount
            existing.sale_date = event.sale_date
            existing.event_title = event.title
        # Se já está pago, não alteramos o registro histórico
    else:
        db.session.add(CommissionPayment(
            event_id=event.id,
            event_title=event.title,
            seller_id=event.seller_id,
            sale_date=event.sale_date,
            amount=amount,
            status="a_pagar",
        ))


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
        .filter(
            CalendarEvent.start_at >= start_dt,
            CalendarEvent.start_at <= end_dt,
            CalendarEvent.event_type != "ENSAIO",
        )
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
    margem_bruta = (
        (Decimal(lucro_bruto) / Decimal(receita_bruta) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if receita_bruta else Decimal("0")
    )

    # Comissões de vendas
    total_comissoes = sum((_event_commission(e, settings) for e in events), Decimal("0"))

    # Despesas com pessoal (salários fixos vigentes — estimativa pro-rata)
    period_days = (end_date - start_date).days + 1
    current_salaries = SalaryHistory.query.filter_by(end_date=None).all()
    # Custo mensal → diário → pro-rata do período
    custo_pessoal = (
        Decimal(sum(s.salary for s in current_salaries)) / Decimal("30") * Decimal(period_days)
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    # EBITDA / Resultado Operacional = Lucro Bruto - Comissões - Pessoal
    ebitda = Decimal(lucro_bruto) - total_comissoes - custo_pessoal
    margem_ebitda = (
        (ebitda / Decimal(receita_bruta) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if receita_bruta else Decimal("0")
    )

    # ── Indicadores Comerciais ────────────────────────────────────────────────
    eventos_com_venda = [e for e in events if e.sale_value]
    ticket_medio = (
        (Decimal(receita_bruta) / Decimal(len(eventos_com_venda))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if eventos_com_venda else Decimal("0")
    )

    # Custo de talento como % da receita
    ratio_custo_talento = (
        (Decimal(cpv) / Decimal(receita_bruta) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if receita_bruta else Decimal("0")
    )

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
    taxa_conversao = (
        (Decimal(n_won) / Decimal(n_won + n_lost) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if (n_won + n_lost) else Decimal("0")
    )
    pipeline_value = sum(d.value or 0 for d in deals_open)

    # Tempo médio de fechamento (dias entre criação e fechamento dos deals ganhos)
    tempos = [(d.closed_at - d.created_at).days for d in deals_won if d.closed_at and d.created_at]
    tempo_medio_fechamento = (
        (Decimal(sum(tempos)) / Decimal(len(tempos))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if tempos else None
    )

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
            CalendarEvent.event_type != "ENSAIO",
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


def _mondays_in_month(year: int, month: int) -> list:
    import calendar as cal_mod
    _, last_day = cal_mod.monthrange(year, month)
    return [date(year, month, d) for d in range(1, last_day + 1)
            if date(year, month, d).weekday() == 0]


def _ensure_salary_payments(year: int, month: int) -> None:
    """Cria registros de SalaryPayment para o mês se ainda não existirem."""
    import calendar as cal_mod
    _, last_day = cal_mod.monthrange(year, month)
    month_ref = f"{year:04d}-{month:02d}"
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    active_histories = SalaryHistory.query.filter(
        SalaryHistory.payment_type != "comissao",
        SalaryHistory.start_date <= month_end,
        db.or_(SalaryHistory.end_date.is_(None), SalaryHistory.end_date >= month_start),
    ).all()

    # Para cada usuário, pega o histórico mais recente vigente no mês
    user_history: dict = {}
    for h in active_histories:
        if h.user_id not in user_history or h.start_date > user_history[h.user_id].start_date:
            user_history[h.user_id] = h

    for user_id, history in user_history.items():
        if history.payment_type == "semanal":
            due_dates = _mondays_in_month(year, month)
        elif history.payment_type == "quinzenal":
            due_dates = [d for d in [date(year, month, 5), date(year, month, 20)]
                         if d.day <= last_day]
        else:
            continue

        for due in due_dates:
            exists = SalaryPayment.query.filter_by(
                user_id=user_id, due_date=due
            ).first()
            if not exists:
                db.session.add(SalaryPayment(
                    user_id=user_id,
                    salary_history_id=history.id,
                    due_date=due,
                    amount=Decimal(str(history.salary)),
                    payment_status="nao_pago",
                    month_ref=month_ref,
                ))

    db.session.commit()


def _build_payment_items(roles, salary_payments, today: date) -> list:
    """Combina cachês e salários em lista unificada ordenada por data."""
    items = []
    for r in roles:
        ev_date = r.event.start_at.date() if r.event and r.event.start_at else date.min
        pix = (r.talent.pix_key or "").strip() if r.talent else ""
        pix_type = r.talent.pix_key_type if r.talent else ""
        copy_label = (r.event.start_at.strftime("%d/%m/%Y") if r.event and r.event.start_at else "") \
                     + " - " + (r.event.title if r.event else "")
        items.append({
            "type":       "cache",
            "id":         r.id,
            "date":       ev_date,
            "event_title": r.event.title if r.event else "—",
            "event_id":   r.event.id if r.event else None,
            "copy_label": copy_label,
            "sublabel":   r.character_name or "—",
            "person_name": r.talent.full_name if r.talent else "—",
            "amount":     r.cache_value,
            "pix_key":    pix,
            "pix_key_type": pix_type,
            "status":     r.payment_status or "nao_pago",
            "is_future":  ev_date > today,
        })
    for sp in salary_payments:
        pix = (sp.user.pix_key or "").strip() if sp.user and sp.user.pix_key else ""
        pix_type = sp.user.pix_key_type if sp.user else ""
        freq = sp.salary_history.payment_type if sp.salary_history else "—"
        copy_label = sp.due_date.strftime("%d/%m/%Y") + " - Salário " + (sp.user.name if sp.user else "")
        items.append({
            "type":        "salary",
            "id":          sp.id,
            "date":        sp.due_date,
            "event_title": "Salário",
            "event_id":    None,
            "copy_label":  copy_label,
            "sublabel":    freq,
            "person_name": sp.user.name if sp.user else "—",
            "amount":      sp.amount,
            "pix_key":     pix,
            "pix_key_type": pix_type,
            "status":      sp.payment_status,
            "is_future":   sp.due_date > today,
        })
    items.sort(key=lambda x: x["date"])
    return items


@financeiro_bp.route("/financeiro/pagamentos")
@login_required
@require_financeiro
def pagamentos():
    today = date.today()
    month = request.args.get("month", today.strftime("%Y-%m"))
    try:
        year_i, month_i = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        year_i, month_i = today.year, today.month

    _ensure_salary_payments(year_i, month_i)

    roles = _pagamentos_query(month)
    salary_payments = SalaryPayment.query.filter_by(
        month_ref=f"{year_i:04d}-{month_i:02d}"
    ).order_by(SalaryPayment.due_date.asc()).all()

    items = _build_payment_items(roles, salary_payments, today)

    def _amt(item):
        v = item["amount"]
        return Decimal(str(v)) if v else Decimal("0")

    total_val    = sum(_amt(i) for i in items)
    total_pago   = sum(_amt(i) for i in items if i["status"] == "pago")
    total_banco  = sum(_amt(i) for i in items if i["status"] == "no_banco")
    total_pend   = sum(_amt(i) for i in items
                       if i["status"] == "nao_pago" and not i["is_future"])
    total_future = sum(_amt(i) for i in items
                       if i["status"] == "nao_pago" and i["is_future"])

    return render_template(
        "financeiro/pagamentos.html",
        items=items,
        month=month,
        today=today,
        status_labels=_STATUS_LABELS,
        total_val=total_val,
        total_pago=total_pago,
        total_banco=total_banco,
        total_pend=total_pend,
        total_future=total_future,
    )


@financeiro_bp.route("/financeiro/pagamentos/set-status", methods=["POST"])
@login_required
@require_financeiro
def set_payment_status():
    item_type = request.form.get("item_type", "cache")
    item_id   = request.form.get("item_id") or request.form.get("role_id")
    status    = request.form.get("payment_status")
    next_url  = request.form.get("next", url_for("financeiro.pagamentos"))

    if not item_id or status not in _VALID_PAYMENT_STATUS:
        return redirect(next_url)

    from app.utils import audit
    if item_type == "salary":
        sp = SalaryPayment.query.get(int(item_id))
        if sp:
            old = sp.payment_status
            sp.payment_status = status
            if status == "pago":
                sp.paid_at = date.today()
            audit("payment", "salary_payment", sp.id, sp.user.name if sp.user else "—",
                  f"Salário: {old} → {status}")
            db.session.commit()
    else:
        role = EventRole.query.get(int(item_id))
        if role:
            old = role.payment_status
            role.payment_status = status
            talent_name = role.talent.full_name if role.talent else "—"
            audit("payment", "event_role", role.id, talent_name,
                  f"Pagamento: {old} → {status} | {role.character_name}")
            db.session.commit()

    return redirect(next_url)


@financeiro_bp.route("/financeiro/pagamentos/bulk-action", methods=["POST"])
@login_required
@require_financeiro
def bulk_payment_action():
    action       = request.form.get("action")
    role_ids     = request.form.getlist("role_ids")
    salary_ids   = request.form.getlist("salary_ids")
    month        = request.form.get("month", date.today().strftime("%Y-%m"))
    next_url     = url_for("financeiro.pagamentos", month=month)

    if not role_ids and not salary_ids:
        return redirect(next_url)

    from app.utils import audit

    r_ids = [int(i) for i in role_ids if i.isdigit()]
    s_ids = [int(i) for i in salary_ids if i.isdigit()]

    if action == "delete":
        for rid in r_ids:
            role = EventRole.query.get(rid)
            if role:
                db.session.delete(role)
        for sid in s_ids:
            sp = SalaryPayment.query.get(sid)
            if sp:
                db.session.delete(sp)
        audit("delete", "payment", None, "bulk",
              f"Excluídos {len(r_ids)} cachês e {len(s_ids)} salários via pagamentos")
        db.session.commit()
    elif action in _VALID_PAYMENT_STATUS:
        for rid in r_ids:
            role = EventRole.query.get(rid)
            if role:
                old = role.payment_status
                role.payment_status = action
                audit("payment", "event_role", role.id,
                      role.talent.full_name if role.talent else "—",
                      f"Bulk: {old} → {action} | {role.character_name}")
        for sid in s_ids:
            sp = SalaryPayment.query.get(sid)
            if sp:
                old = sp.payment_status
                sp.payment_status = action
                if action == "pago":
                    sp.paid_at = date.today()
                audit("payment", "salary_payment", sp.id,
                      sp.user.name if sp.user else "—",
                      f"Bulk salário: {old} → {action}")
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
    is_financeiro = _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN)

    events = (
        CalendarEvent.query
        .filter(CalendarEvent.event_type != "ENSAIO")
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


# ─── COMISSÕES ROUTES ────────────────────────────────────────────────────────

_COMMISSION_STATUS_LABELS = {
    "a_pagar":  "A pagar",
    "pago":     "Pago",
    "cancelado": "Cancelado",
}


@financeiro_bp.route("/financeiro/comissoes")
@login_required
@require_financeiro
def comissoes():
    today = date.today()
    month = request.args.get("month", today.strftime("%Y-%m"))
    try:
        year, mon = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        year, mon = today.year, today.month

    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)

    # Comissões cujo sale_date cai no mês, ou sem sale_date mas criadas no mês
    entries = (
        CommissionPayment.query
        .filter(
            CommissionPayment.status.in_(["a_pagar", "pago"]),
            db.or_(
                db.and_(
                    CommissionPayment.sale_date >= start,
                    CommissionPayment.sale_date < end,
                ),
                db.and_(
                    CommissionPayment.sale_date.is_(None),
                    db.func.date(CommissionPayment.created_at) >= start,
                    db.func.date(CommissionPayment.created_at) < end,
                ),
            ),
        )
        .order_by(CommissionPayment.sale_date.asc(), CommissionPayment.seller_id.asc())
        .all()
    )

    # Estornos pendentes (gerados por cancelamentos de meses anteriores)
    estornos = (
        CommissionPayment.query
        .filter(
            CommissionPayment.status == "a_pagar",
            CommissionPayment.amount < 0,
        )
        .order_by(CommissionPayment.created_at.asc())
        .all()
    )

    total_a_pagar = sum(e.amount for e in entries if e.status == "a_pagar") + sum(e.amount for e in estornos)

    # Vendedores elegíveis para seleção de mês
    sellers = User.query.join(User.roles).filter(Role.name == RoleName.COMERCIAL).order_by(User.name).all()

    return render_template(
        "financeiro/comissoes.html",
        entries=entries,
        estornos=estornos,
        total_a_pagar=total_a_pagar,
        month=month,
        sellers=sellers,
        status_labels=_COMMISSION_STATUS_LABELS,
    )


@financeiro_bp.route("/financeiro/comissoes/set-status", methods=["POST"])
@login_required
@require_financeiro
def set_commission_status():
    cp_id  = request.form.get("cp_id")
    status = request.form.get("status")
    next_url = request.form.get("next", url_for("financeiro.comissoes"))
    valid = {"a_pagar", "pago", "cancelado"}
    if cp_id and status in valid:
        cp = CommissionPayment.query.get(cp_id)
        if cp:
            old = cp.status
            cp.status = status
            if status == "pago":
                cp.paid_at = date.today()
            from app.utils import audit
            audit("payment", "commission", cp.id, cp.seller.name if cp.seller else "—",
                  f"Comissão: {old} → {status} | {cp.event_title}")
            db.session.commit()
    return redirect(next_url)
