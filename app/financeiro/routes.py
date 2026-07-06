import csv
import io
from collections import defaultdict
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Blueprint, render_template, request, redirect, url_for, abort, make_response, jsonify, flash
from flask_login import login_required, current_user

from app import db, _safe_next
from app.models import CalendarEvent, EventRole, EventPayment, EventInstallment, EventInvoice, SiteSetting, User, Role, SalaryHistory, CommissionPayment, SalaryPayment, SalaryAdvance, SpecialExpense, EventAcrescimo
from app.money import format_brl
from app.constants import RoleName, EDUCAMANTO_TITLE_PREFIX

financeiro_bp = Blueprint("financeiro", __name__)

# Fuso padrão do sistema: tudo é exibido/comparado em horário de Brasília.
TZ_SP = ZoneInfo("America/Sao_Paulo")

DEFAULT_COMMISSION = Decimal("2.5")
# Comissão EducaManto (feature 109): % sobre o LUCRO do evento (venda − BV − cachês),
# diferente da comissão comum (% sobre a venda). Override por evento continua valendo.
EDUCAMANTO_COMMISSION_RATE = Decimal("5")


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


def _is_educamanto_responsavel() -> bool:
    """True se o usuário logado é o responsável EducaManto configurado (feature 109)."""
    if not current_user.is_authenticated:
        return False
    settings = SiteSetting.query.get(1)
    return bool(settings and settings.educamanto_seller_id == current_user.id)


def require_vendas(fn):
    """Permite COMERCIAL/FINANCEIRO/SUPERADMIN e o responsável EducaManto (feature 109)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN) \
                and not _is_educamanto_responsavel():
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


def _group_cost(event) -> int:
    """Custo de cachês do evento, somando os satélites quando for principal de grupo (FR-011)."""
    total = _event_cost(event)
    for satellite in event.satellites:
        total += _event_cost(satellite)
    return total


def _event_bv_total(event) -> Decimal:
    """Soma dos acréscimos BV do evento, em R$ (feature 099).

    BV é um repasse a terceiros: não é lucro da Manto nem entra na comissão da vendedora. Usa o valor
    efetivo já congelado (``amount_brl``) de cada acréscimo marcado como BV.
    """
    total = Decimal("0")
    for a in getattr(event, "acrescimos", []) or []:
        if a.is_bv and a.amount_brl:
            total += Decimal(a.amount_brl)
    return total


def _educamanto_responsavel(settings) -> User | None:
    """Usuário configurado como responsável EducaManto, ou None (feature 109)."""
    if settings and settings.educamanto_seller_id:
        return User.query.get(settings.educamanto_seller_id)
    return None


def _commission_beneficiary(event, settings) -> User | None:
    """Beneficiário da comissão do evento (feature 109).

    Evento EducaManto (título "(EDU…") com responsável configurado → responsável;
    caso contrário → vendedor do evento (regra original).
    """
    if event.is_educamanto:
        responsavel = _educamanto_responsavel(settings)
        if responsavel is not None:
            return responsavel
    return event.seller


def _event_commission(event, settings) -> Decimal:
    if not event.sale_value:
        return Decimal("0")
    beneficiary = _commission_beneficiary(event, settings)
    if beneficiary and not beneficiary.receives_commission:
        return Decimal("0")
    if event.is_educamanto and _educamanto_responsavel(settings) is not None:
        # Comissão EducaManto (feature 109): 5% sobre o LUCRO (venda − BV − cachês).
        rate = (
            Decimal(str(event.commission_rate))
            if event.commission_rate is not None
            else EDUCAMANTO_COMMISSION_RATE
        )
        custo = _group_cost(event) if event.is_group_leader else _event_cost(event)
        base = Decimal(event.sale_value) - _event_bv_total(event) - Decimal(custo)
    else:
        rate = _get_commission_rate(event, settings)
        # BV sai da base de comissão (repasse, não é receita comissionável) — feature 099.
        base = Decimal(event.sale_value) - _event_bv_total(event)
    if base < 0:
        base = Decimal("0")
    return (base * rate / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _sync_commission_payment(event: CalendarEvent) -> None:
    """Cria ou atualiza o CommissionPayment de um evento. Não faz commit."""
    existing = CommissionPayment.query.filter_by(event_id=event.id).filter(
        CommissionPayment.status != "cancelado"
    ).first()

    settings = SiteSetting.query.get(1)
    beneficiary = _commission_beneficiary(event, settings)

    should_have = (
        event.sale_value
        and beneficiary is not None
        and beneficiary.receives_commission
    )

    if not should_have:
        if existing and existing.status == "a_pagar":
            existing.status = "cancelado"
            existing.notes = (existing.notes or "") + " | Cancelado: sem comissão elegível"
        return

    # Comissão EducaManto (feature 109): só entra no ciclo de pagamento após a realização —
    # payable_from = data do evento. Comissão comum fica NULL (ciclo pela sale_date).
    is_edu_com_responsavel = event.is_educamanto and _educamanto_responsavel(settings) is not None
    payable_from = (
        event.start_at.date()
        if is_edu_com_responsavel and event.start_at is not None
        else None
    )

    amount = _event_commission(event, settings)
    if existing:
        if existing.status == "a_pagar":
            existing.amount = amount
            existing.sale_date = event.sale_date
            existing.event_title = event.title
            existing.seller_id = beneficiary.id
            existing.payable_from = payable_from
        # Se já está pago, não alteramos o registro histórico
    else:
        db.session.add(CommissionPayment(
            event_id=event.id,
            event_title=event.title,
            seller_id=beneficiary.id,
            sale_date=event.sale_date,
            payable_from=payable_from,
            amount=amount,
            status="a_pagar",
        ))


def _resync_pending_commissions() -> None:
    """Reconcilia as comissões A PAGAR com o cálculo atual do evento (mesma base da aba comercial).

    Evita divergência quando a taxa muda depois de a comissão ter sido registrada. Não altera
    comissões já pagas (histórico) nem estornos (valores negativos).
    """
    pendentes = (
        CommissionPayment.query
        .filter(
            CommissionPayment.status == "a_pagar",
            CommissionPayment.event_id.isnot(None),
            CommissionPayment.amount >= 0,
        )
        .all()
    )
    event_ids = {cp.event_id for cp in pendentes}
    if not event_ids:
        return
    for eid in event_ids:
        ev = CalendarEvent.query.get(eid)
        if ev:
            _sync_commission_payment(ev)
    db.session.commit()


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


# ── Constantes fiscais (sobrescrevíveis em Settings) ──────────────────────────
DEFAULT_TAX_RATE = Decimal("16")        # % provisionamento de imposto sobre vendas com nota
DEFAULT_FATOR_R = Decimal("28")         # % corte folha/faturamento (Simples Anexo III vs V)
FATOR_R_RATE_LOW = "6"                  # alíquota protegida (rótulo)
FATOR_R_RATE_HIGH = "15,5"             # alíquota de risco (rótulo)


def _pct(num, den) -> Decimal:
    """Percentual seguro: retorna 0 quando o denominador é 0 (sem divisão por zero)."""
    if not den:
        return Decimal("0")
    return (Decimal(num) / Decimal(den) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def _is_permuta(event) -> bool:
    return bool(getattr(event, "is_cortesia_permuta", False))


def _get_tax_rate(settings) -> Decimal:
    if settings and settings.tax_rate is not None:
        return Decimal(str(settings.tax_rate))
    return DEFAULT_TAX_RATE


def _get_fator_r_threshold(settings) -> Decimal:
    if settings and settings.fator_r_threshold is not None:
        return Decimal(str(settings.fator_r_threshold))
    return DEFAULT_FATOR_R


def _is_full_month(start_date: date, end_date: date) -> bool:
    """True se [start, end] cobre exatamente um mês civil (dia 1 ao último dia)."""
    import calendar as _cal
    if start_date.day != 1 or start_date.year != end_date.year or start_date.month != end_date.month:
        return False
    last = _cal.monthrange(start_date.year, start_date.month)[1]
    return end_date.day == last


def _last_day_of_month(d: date) -> date:
    import calendar as _cal
    return date(d.year, d.month, _cal.monthrange(d.year, d.month)[1])


def _resolve_period(today: date):
    """Resolve o filtro de período. Retorna (period, start_date, end_date, is_full_month)."""
    period = request.args.get("period", "este_mes")
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    if period == "30d":
        return "30d", today - timedelta(days=29), today, False
    if period == "mes_anterior":
        py, pm = _prev_month(today.year, today.month)
        start_date = date(py, pm, 1)
        return "mes_anterior", start_date, _last_day_of_month(start_date), True
    if period == "custom" and start_str and end_str:
        try:
            start_date = date.fromisoformat(start_str)
            end_date = date.fromisoformat(end_str)
            if end_date < start_date:
                start_date, end_date = end_date, start_date
            return "custom", start_date, end_date, _is_full_month(start_date, end_date)
        except ValueError:
            pass
    # default: mês corrente
    start_date = date(today.year, today.month, 1)
    return "este_mes", start_date, _last_day_of_month(today), True


def _salary_cost(start_date: date, end_date: date, is_full_month: bool) -> Decimal:
    """Custo de pessoal do período.

    Mês cheio → soma real dos SalaryPayment do mês (se já gerados).
    Período fracionado (ou mês ainda sem lançamentos) → pro-rata do salário vigente.
    """
    if is_full_month:
        month_ref = f"{start_date.year:04d}-{start_date.month:02d}"
        total = db.session.query(
            db.func.coalesce(db.func.sum(SalaryPayment.amount), 0)
        ).filter(SalaryPayment.month_ref == month_ref).scalar()
        if total:
            return Decimal(total)
        # ainda não gerado para o mês → cai no pro-rata abaixo
    period_days = (end_date - start_date).days + 1
    current = SalaryHistory.query.filter(
        SalaryHistory.end_date.is_(None),
        SalaryHistory.payment_type != "comissao",
    ).all()
    return (
        Decimal(sum(s.salary for s in current)) / Decimal("30") * Decimal(period_days)
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _compute_drg(events, settings, salary_cost: Decimal, gastos_extras: Decimal) -> dict:
    """Cascata da DRE Gerencial para um conjunto de eventos.

    Isola permutas/cortesias: o cachê delas não entra no CPV (não distorce a margem),
    entra como Custo de Marketing. Impostos só sobre eventos com nota (with_invoice).
    """
    tax_rate = _get_tax_rate(settings)
    # Satélites não entram como linha própria: seu cachê é somado ao grupo via _group_cost
    # no evento principal (FR-010/FR-011) — evita contar a venda do grupo mais de uma vez.
    normais = [e for e in events if not _is_permuta(e) and not e.is_satellite]
    permutas = [e for e in events if _is_permuta(e)]

    receita_bruta = sum((Decimal(e.sale_value or 0) for e in normais), Decimal("0"))
    impostos = sum(
        (Decimal(e.sale_value or 0) * tax_rate / Decimal("100") for e in normais if e.with_invoice),
        Decimal("0"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    receita_liquida = receita_bruta - impostos

    # BV é repasse a terceiros: entra como custo (não é lucro da Manto) — feature 099.
    bv_total = sum((_event_bv_total(e) for e in normais), Decimal("0"))
    cpv = Decimal(sum(_group_cost(e) for e in normais)) + bv_total
    lucro_bruto = receita_liquida - cpv

    marketing = Decimal(sum(_event_cost(e) for e in permutas))
    comissoes = sum((_event_commission(e, settings) for e in normais), Decimal("0"))
    pessoal = Decimal(salary_cost)
    ebitda = lucro_bruto - marketing - comissoes - pessoal

    gastos = Decimal(gastos_extras)
    resultado_liquido = ebitda - gastos

    return {
        "receita_bruta": receita_bruta,
        "impostos": impostos,
        "receita_liquida": receita_liquida,
        "cpv": cpv,
        "lucro_bruto": lucro_bruto,
        "margem_bruta": _pct(lucro_bruto, receita_liquida),
        "marketing": marketing,
        "comissoes": comissoes,
        "pessoal": pessoal,
        "ebitda": ebitda,
        "margem_ebitda": _pct(ebitda, receita_liquida),
        "gastos_extras": gastos,
        "resultado_liquido": resultado_liquido,
        "n_eventos": len(events),
        "n_normais": len(normais),
        "n_permutas": len(permutas),
    }


@financeiro_bp.route("/financeiro/")
@login_required
@require_financeiro
def dashboard():
    settings = SiteSetting.query.get(1)
    # "Hoje" sempre em horário de Brasília (eventos são guardados naïve em SP).
    today = datetime.now(TZ_SP).date()
    now_naive = datetime.now(TZ_SP).replace(tzinfo=None)

    # ── Filtro de período (regime de competência: data do evento) ─────────────
    period, start_date, end_date, is_full_month = _resolve_period(today)
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

    # Realizado (já ocorrido) × Projetado (futuro), pela data do evento.
    realizados = [e for e in events if e.start_at and e.start_at < now_naive]
    projetados = [e for e in events if e.start_at and e.start_at >= now_naive]

    # ── Custos do período ─────────────────────────────────────────────────────
    salary_cost = _salary_cost(start_date, end_date, is_full_month)
    gastos_extras = sum(
        (Decimal(g.amount) for g in SpecialExpense.query.filter(
            SpecialExpense.status == "aprovado",
            SpecialExpense.expense_date >= start_date,
            SpecialExpense.expense_date <= end_date,
        ).all()),
        Decimal("0"),
    )

    # ── DRE Gerencial: realizado, projetado e total (consolidado do período) ──
    drg_realizado = _compute_drg(realizados, settings, salary_cost, gastos_extras)
    # Projetado mostra só a contribuição operacional dos eventos futuros (sem custo fixo).
    drg_projetado = _compute_drg(projetados, settings, Decimal("0"), Decimal("0"))
    drg_total = _compute_drg(events, settings, salary_cost, gastos_extras)

    # ── KPIs (sobre o consolidado do período) ─────────────────────────────────
    # Apenas eventos normais (não-permuta) com venda contam para indicadores comerciais.
    eventos_com_venda = [
        e for e in events
        if not _is_permuta(e) and not e.is_satellite and e.sale_value and e.sale_value > 0
    ]
    ticket_medio = (
        (drg_total["receita_bruta"] / Decimal(len(eventos_com_venda))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if eventos_com_venda else Decimal("0")
    )
    ratio_custo_talento = _pct(drg_total["cpv"], drg_total["receita_liquida"])

    # Termômetro de break-even: lucro bruto cobrindo o custo fixo (pessoal + comissões).
    fixed_cost = drg_total["pessoal"] + drg_total["comissoes"]
    breakeven_pct = _pct(drg_total["lucro_bruto"], fixed_cost)
    breakeven_atingido = bool(fixed_cost > 0 and drg_total["lucro_bruto"] >= fixed_cost)

    # Alerta fiscal (Fator R): folha ÷ faturamento.
    fator_r_threshold = _get_fator_r_threshold(settings)
    fator_r_pct = _pct(drg_total["pessoal"], drg_total["receita_bruta"])
    fator_r_protegido = bool(drg_total["receita_bruta"] > 0 and fator_r_pct >= fator_r_threshold)

    # A receber de clientes: venda − comprovantes anexados, por evento do período.
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

    # A pagar / pago a talentos no período (exclui permutas? não: cachê é devido mesmo em permuta).
    roles_no_periodo = [r for e in events for r in e.roles if r.talent_id]
    pagamentos_pendentes = sum(
        r.cache_value or 0 for r in roles_no_periodo
        if r.payment_status == "nao_pago"
    )
    pagamentos_realizados = sum(
        r.cache_value or 0 for r in roles_no_periodo
        if r.payment_status in ("pago", "no_banco")
    )

    # ── Receita por tipo de evento ────────────────────────────────────────────
    receita_por_tipo = defaultdict(int)
    for e in eventos_com_venda:
        receita_por_tipo[e.event_type or "Outros"] += (e.sale_value or 0)
    receita_por_tipo = dict(sorted(receita_por_tipo.items(), key=lambda x: -x[1]))
    receita_tipo_max = max(receita_por_tipo.values()) if receita_por_tipo else 0

    # ── Top vendedores por receita ────────────────────────────────────────────
    seller_revenue = defaultdict(int)
    seller_margin  = defaultdict(int)
    for e in eventos_com_venda:
        if e.seller_id:
            seller_revenue[e.seller_id] += (e.sale_value or 0)
            seller_margin[e.seller_id]  += (e.sale_value or 0) - _group_cost(e)
    top_sellers = []
    for sid, rev in sorted(seller_revenue.items(), key=lambda x: -x[1])[:5]:
        u = User.query.get(sid)
        if u:
            top_sellers.append({"user": u, "receita": rev, "lucro": seller_margin[sid]})

    # ── Tendência mensal (últimos 6 meses, visão operacional pura) ───────────
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
            "receita": rec,
            "custo": cst,
            "lucro": rec - cst,
            "margem": _pct(rec - cst, rec),
            "n_eventos": len(evs),
        })
        y, m = _prev_month(y, m)

    # ── Auditoria: eventos com receita zerada SEM flag de cortesia/permuta ────
    auditoria = [
        e for e in events
        if not _is_permuta(e) and not e.is_satellite and not (e.sale_value and e.sale_value > 0)
    ]

    # ── Tabela de eventos do período (com status financeiro) ─────────────────
    events_data = []
    for e in events:
        # Satélites não viram linha própria: o grupo aparece como 1 entrada no principal,
        # com o nome do grupo e os custos somados (feature 055; consolidação da 053).
        if e.is_satellite:
            continue
        # float() normaliza: cache_value é Numeric (Decimal no Postgres), e Decimal não
        # pode ser subtraído de float diretamente (TypeError) — venda/recebido já são float.
        # _group_cost soma os satélites no principal (FR-011); satélite mostra só o próprio cachê.
        custo = float(_group_cost(e) if e.is_group_leader else _event_cost(e) or 0)
        comissao = _event_commission(e, settings)
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
        events_data.append({
            "event": e,
            "custo": custo,
            "lucro": (0 if _is_permuta(e) else venda) - custo,
            "comissao": comissao,
            "rate": _get_commission_rate(e, settings),
            "is_projetado": bool(e.start_at and e.start_at >= now_naive),
            "status": status,
        })

    period_label = {
        "este_mes": "Este mês",
        "30d": "Últimos 30 dias",
        "mes_anterior": "Mês anterior",
        "custom": "Período personalizado",
    }.get(period, "Este mês")

    # Recebimentos previstos (parcelas com vencimento no período, ainda não recebidas) — feature 065.
    # Informativo (fluxo de caixa); NÃO altera a receita reconhecida (que segue pela data do evento).
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
        {"date": inst.due_date, "event_id": ev.id, "event_title": ev.title, "amount": inst.amount or 0}
        for inst, ev in _inst_rows
    ]
    recebimentos_previstos_total = sum(
        (Decimal(r["amount"]) for r in recebimentos_previstos), Decimal("0")
    )

    # ── Notas fiscais (feature 069) ──────────────────────────────────────────
    tax_rate_nf = _get_tax_rate(settings)

    # Tarefas de emissão: TODAS as notas "a emitir" (independem do período) — pendência aberta.
    _nf_pend = (
        EventInvoice.query
        .filter(EventInvoice.status == "a_emitir")
        .join(CalendarEvent, EventInvoice.event_id == CalendarEvent.id)
        .order_by(EventInvoice.issue_date.is_(None), EventInvoice.issue_date.asc())
        .all()
    )
    nf_a_emitir = [
        {
            "id": inv.id, "date": inv.issue_date, "event_id": inv.event_id,
            "event_title": inv.event.title if inv.event else "—",
            "amount": inv.amount or 0,
        }
        for inv in _nf_pend
    ]
    nf_a_emitir_total = sum((Decimal(n["amount"]) for n in nf_a_emitir), Decimal("0"))

    # Custo de nota por mês de EMISSÃO: 16% (tax_rate) de cada nota com issue_date no período.
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
            "amount": _val,
            "date": inv.issue_date,
            "status": inv.status,
            "custo": _custo,
        })
    custo_nota_total = sum((i["custo"] for i in custo_nota_itens), Decimal("0"))

    return render_template(
        "financeiro/dashboard.html",
        recebimentos_previstos=recebimentos_previstos,
        recebimentos_previstos_total=recebimentos_previstos_total,
        nf_a_emitir=nf_a_emitir,
        nf_a_emitir_total=nf_a_emitir_total,
        custo_nota_itens=custo_nota_itens,
        custo_nota_total=custo_nota_total,
        # DRE (3 visões)
        drg_realizado=drg_realizado,
        drg_projetado=drg_projetado,
        drg_total=drg_total,
        # KPIs
        ticket_medio=ticket_medio,
        ratio_custo_talento=ratio_custo_talento,
        breakeven_pct=breakeven_pct,
        breakeven_atingido=breakeven_atingido,
        fixed_cost=fixed_cost,
        fator_r_pct=fator_r_pct,
        fator_r_threshold=fator_r_threshold,
        fator_r_protegido=fator_r_protegido,
        fator_r_rate_low=FATOR_R_RATE_LOW,
        fator_r_rate_high=FATOR_R_RATE_HIGH,
        a_receber_clientes=a_receber_clientes,
        pagamentos_pendentes=pagamentos_pendentes,
        pagamentos_realizados=pagamentos_realizados,
        # Painéis laterais
        receita_por_tipo=receita_por_tipo,
        receita_tipo_max=receita_tipo_max,
        top_sellers=top_sellers,
        # Tendência / Auditoria / Tabela
        monthly_trend=monthly_trend,
        auditoria=auditoria,
        events_data=events_data,
        # Filtros
        settings=settings,
        period=period,
        period_label=period_label,
        is_full_month=is_full_month,
        start_str=start_date.isoformat(),
        end_str=end_date.isoformat(),
        today=today,
    )


@financeiro_bp.route("/financeiro/nf/<int:invoice_id>/emitir", methods=["POST"])
@login_required
@require_financeiro
def nf_emitir(invoice_id: int):
    """Marca uma nota fiscal como emitida (feature 069).

    O super admin/financeiro sobe o arquivo (opcional) e a nota passa a ``emitida``, concluindo a
    tarefa de emissão. Mantém a data de emissão informada na venda; se vier ``issue_date`` no form,
    atualiza.
    """
    import os

    from flask import current_app
    from werkzeug.utils import secure_filename

    from app.utils import audit

    inv = EventInvoice.query.get_or_404(invoice_id)
    back = redirect(request.referrer or url_for("financeiro.dashboard"))

    # data de emissão (opcional) — usa a informada ou mantém a existente
    _draw = (request.form.get("issue_date", "") or "").strip()
    if _draw:
        try:
            inv.issue_date = date.fromisoformat(_draw)
        except ValueError:
            pass

    nf_file = request.files.get("nf_file")
    if nf_file and nf_file.filename:
        nf_file.stream.seek(0, 2)
        size = nf_file.stream.tell()
        nf_file.stream.seek(0)
        if size > 10 * 1024 * 1024:
            flash("Arquivo da nota acima de 10 MB.", "error")
            return back
        fname = f"nf_{inv.id}_{secure_filename(nf_file.filename)}"
        nf_file.save(os.path.join(current_app.config["UPLOAD_INVOICES"], fname))
        inv.file = f"/uploads/invoices/{fname}"

    inv.status = "emitida"
    inv.issued_at = datetime.now(TZ_SP).replace(tzinfo=None)
    _title = inv.event.title if inv.event else "—"
    audit("invoice", "event_invoice", inv.id, _title, f"Nota fiscal emitida (R$ {inv.amount or 0})")
    db.session.commit()
    flash("Nota fiscal marcada como emitida.", "success")
    return back


@financeiro_bp.route("/financeiro/funcionarios")
@login_required
@require_financeiro
def funcionarios():
    # Unificado em Usuários (feature 022). Mantém o link antigo funcionando.
    return redirect(url_for("admin.list_users"))


@financeiro_bp.route("/financeiro/funcionarios/<int:user_id>", methods=["GET", "POST"])
@login_required
@require_financeiro
def funcionario_detail(user_id: int):
    # Unificado em Usuários (feature 022). Mantém o link antigo funcionando.
    return redirect(url_for("admin.edit_user", user_id=user_id))


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

    # Recompõe os lançamentos NÃO pagos do mês a partir do salário vigente:
    # apaga os não pagos (serão recriados com o valor/frequência atuais) e preserva os
    # já pagos / "no banco" (histórico real do que foi efetivamente pago).
    # IMPORTANTE (feature 068/089): também preserva os que têm adiantamento(s) lançado(s), senão a
    # regeneração apagaria os adiantamentos salvos ao recarregar a tela.
    _sp_with_advances = db.session.query(SalaryAdvance.salary_payment_id).distinct()
    SalaryPayment.query.filter(
        SalaryPayment.month_ref == month_ref,
        SalaryPayment.payment_status == "nao_pago",
        SalaryPayment.advance_amount.is_(None),
        ~SalaryPayment.id.in_(_sp_with_advances),
    ).delete(synchronize_session="fetch")

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


def _build_payment_items(roles, salary_payments, today: date, expenses=None, now_dt=None) -> list:
    """Combina cachês, salários e desembolsos de gastos aprovados em lista ordenada por data.

    ``now_dt``: "agora" em horário de Brasília (naïve), usado para classificar um cachê como
    futuro enquanto o evento ainda não terminou (pelo horário de término).
    """
    if now_dt is None:
        now_dt = datetime.now(TZ_SP).replace(tzinfo=None)
    items = []
    for r in roles:
        ev_date = r.event.start_at.date() if r.event and r.event.start_at else date.min
        # Futuro = o evento ainda não terminou (horário de término; reserva: início).
        ev_end = (r.event.end_at or r.event.start_at) if r.event else None
        is_future_event = bool(ev_end and ev_end > now_dt)
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
            "is_future":  is_future_event,
        })
    for sp in salary_payments:
        pix = (sp.user.pix_key or "").strip() if sp.user and sp.user.pix_key else ""
        pix_type = sp.user.pix_key_type if sp.user else ""
        freq = sp.salary_history.payment_type if sp.salary_history else "—"
        copy_label = sp.due_date.strftime("%d/%m/%Y") + " - Salário " + (sp.user.name if sp.user else "")
        _adv = sp.advance_total  # soma de todos os adiantamentos (feature 089)
        _advances = [
            {
                "id": a.id,
                "amount": format_brl(a.amount or 0),
                "date": a.created_at.strftime("%d/%m/%Y") if a.created_at else "",
                "proof": a.proof or "",
            }
            for a in sp.advances
        ]
        items.append({
            "type":        "salary",
            "id":          sp.id,
            "date":        sp.due_date,
            "event_title": "Salário",
            "event_id":    None,
            "copy_label":  copy_label,
            "sublabel":    freq,
            "person_name": sp.user.name if sp.user else "—",
            "amount":      (sp.amount or Decimal("0")) - _adv,  # líquido a pagar (feature 067/089)
            "gross_amount": sp.amount,
            "advance_amount": _adv,
            "advances":    _advances,
            "pix_key":     pix,
            "pix_key_type": pix_type,
            "status":      sp.payment_status,
            "is_future":   sp.due_date > today,
        })
    for g in (expenses or []):
        copy_label = g.expense_date.strftime("%d/%m/%Y") + " - " + (g.description or "Gasto")
        items.append({
            "type":        "expense",
            "id":          g.id,
            "date":        g.expense_date,
            "event_title": f"Gasto: {g.category}",
            "event_id":    None,
            "copy_label":  copy_label,
            "sublabel":    g.description or "—",
            "person_name": g.payee_name,
            "amount":      g.amount,
            "pix_key":     g.payee_pix,
            "pix_key_type": "",
            "status":      g.payment_status or "nao_pago",
            "is_future":   g.expense_date > today,
        })
    items.sort(key=lambda x: x["date"])
    return items


def _build_bv_items(bv_rows, today: date, now_dt=None) -> list:
    """Itens de pagamento de BV (repasse) — feature 099.

    Cada acréscimo BV vira um item a pagar, com recebedor, PIX, valor e status. BV sem PIX é sinalizado
    como pendente de dados (``missing_data``) para não ser esquecido.
    """
    if now_dt is None:
        now_dt = datetime.now(TZ_SP).replace(tzinfo=None)
    items = []
    for a in bv_rows:
        ev = a.event
        ev_date = ev.start_at.date() if ev and ev.start_at else date.min
        ev_end = (ev.end_at or ev.start_at) if ev else None
        copy_label = (ev.start_at.strftime("%d/%m/%Y") if ev and ev.start_at else "") \
                     + " - " + (ev.title if ev else "")
        items.append({
            "type":        "bv",
            "id":          a.id,
            "date":        ev_date,
            "event_title": ev.title if ev else "—",
            "event_id":    ev.id if ev else None,
            "copy_label":  copy_label,
            "sublabel":    "BV (repasse)",
            "person_name": a.bv_recipient or "(sem recebedor)",
            "amount":      a.amount_brl,
            "pix_key":     (a.bv_pix or "").strip(),
            "pix_key_type": "",
            "status":      a.bv_payment_status or "nao_pago",
            "is_future":   bool(ev_end and ev_end > now_dt),
            "missing_data": not (a.bv_pix or "").strip(),
        })
    return items


def _build_commission_items(period_start: date, period_end: date, due_date: date, today: date) -> list:
    """Resumo de comissões por vendedor com ciclo em [period_start, period_end).

    Ciclo = data da venda (comissões comuns) ou data da realização do evento (EducaManto,
    feature 109). Uma linha por vendedor (soma das comissões a_pagar/pago no período;
    estornos reduzem). Datada em due_date (dia 5 do mês visualizado). id = "sellerId:YYYY-MM".
    """
    # Feature 109: comissões EducaManto entram no ciclo pela data da REALIZAÇÃO do evento
    # (payable_from); as demais seguem pela data da venda (payable_from IS NULL).
    cycle_date = db.func.coalesce(CommissionPayment.payable_from, CommissionPayment.sale_date)
    rows = (
        CommissionPayment.query
        .filter(
            CommissionPayment.status.in_(["a_pagar", "pago"]),
            cycle_date >= period_start,
            cycle_date < period_end,
        )
        .all()
    )
    by_seller: dict[int, list] = defaultdict(list)
    for r in rows:
        by_seller[r.seller_id].append(r)

    period_tag = f"{period_start.year:04d}-{period_start.month:02d}"
    items = []
    for seller_id, lst in by_seller.items():
        total = sum((c.amount for c in lst), Decimal("0"))
        if total == 0:
            continue
        seller = User.query.get(seller_id)
        all_paid = all(c.status == "pago" for c in lst)
        pix = (seller.pix_key or "").strip() if seller and seller.pix_key else ""
        items.append({
            "type":        "commission",
            "id":          f"{seller_id}:{period_tag}",
            "date":        due_date,
            "event_title": f"Comissões {period_start.month:02d}/{period_start.year}",
            "event_id":    None,
            "copy_label":  due_date.strftime("%d/%m/%Y") + " - Comissão " + (seller.name if seller else ""),
            "sublabel":    "Comissão",
            "person_name": seller.name if seller else "—",
            "amount":      total,
            "pix_key":     pix,
            "pix_key_type": seller.pix_key_type if seller else "",
            "status":      "pago" if all_paid else "nao_pago",
            "is_future":   due_date > today,
        })
    return items


@financeiro_bp.route("/financeiro/pagamentos")
@login_required
@require_financeiro
def pagamentos():
    _resync_pending_commissions()
    # "Agora" e "hoje" sempre em horário de Brasília (eventos são guardados naïve em SP).
    now_sp = datetime.now(TZ_SP).replace(tzinfo=None)
    today = now_sp.date()
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

    # Desembolsos de gastos aprovados no mês (pela data do gasto), com destino definido
    _m_start = date(year_i, month_i, 1)
    _m_end = date(year_i + 1, 1, 1) if month_i == 12 else date(year_i, month_i + 1, 1)
    expenses = SpecialExpense.query.filter(
        SpecialExpense.status == "aprovado",
        SpecialExpense.disbursement_type.isnot(None),
        SpecialExpense.expense_date >= _m_start,
        SpecialExpense.expense_date < _m_end,
    ).order_by(SpecialExpense.expense_date.asc()).all()

    items = _build_payment_items(roles, salary_payments, today, expenses, now_sp)

    # BV (feature 099): repasses dos eventos do mês (pela data do evento) entram como itens a pagar.
    bv_rows = (
        EventAcrescimo.query.join(CalendarEvent)
        .filter(
            EventAcrescimo.is_bv.is_(True),
            CalendarEvent.start_at >= datetime.combine(_m_start, datetime.min.time()),
            CalendarEvent.start_at < datetime.combine(_m_end, datetime.min.time()),
        )
        .all()
    )
    items += _build_bv_items(bv_rows, today, now_sp)

    # Comissões: soma por vendedor dos eventos vendidos no MÊS ANTERIOR, a pagar no dia 5 do mês visto.
    prev_year, prev_month = (year_i - 1, 12) if month_i == 1 else (year_i, month_i - 1)
    prev_start = date(prev_year, prev_month, 1)
    prev_end = _m_start
    items += _build_commission_items(prev_start, prev_end, date(year_i, month_i, 5), today)
    items.sort(key=lambda x: x["date"])

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
    next_url  = _safe_next(request.form.get("next"), url_for("financeiro.pagamentos"))

    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.form.get("ajax") == "1"
    )

    def _done(effective_status):
        """Resposta de sucesso: JSON em tempo real (AJAX) ou redirect (reserva)."""
        if is_ajax:
            return jsonify({"ok": True, "status": effective_status})
        return redirect(next_url)

    def _bad():
        if is_ajax:
            return jsonify({"ok": False}), 400
        return redirect(next_url)

    if not item_id or status not in _VALID_PAYMENT_STATUS:
        return _bad()

    from app.utils import audit
    if item_type == "commission":
        # item_id = "sellerId:YYYY-MM" (mês de venda). Marca as comissões do vendedor/período.
        try:
            seller_part, period_tag = str(item_id).split(":")
            seller_id = int(seller_part)
            py, pm = int(period_tag[:4]), int(period_tag[5:7])
        except (ValueError, AttributeError):
            return _bad()
        p_start = date(py, pm, 1)
        p_end = date(py + 1, 1, 1) if pm == 12 else date(py, pm + 1, 1)
        target = "pago" if status == "pago" else "a_pagar"
        rows = CommissionPayment.query.filter(
            CommissionPayment.seller_id == seller_id,
            CommissionPayment.sale_date >= p_start,
            CommissionPayment.sale_date < p_end,
            CommissionPayment.status.in_(["a_pagar", "pago"]),
        ).all()
        for c in rows:
            c.status = target
            c.paid_at = date.today() if target == "pago" else None
        audit("payment", "commission", seller_id, "",
              f"Comissões {period_tag}: → {target} ({len(rows)} itens)")
        db.session.commit()
        # Para a UI, comissão só tem "pago" ou "nao_pago".
        return _done("pago" if target == "pago" else "nao_pago")

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
    elif item_type == "expense":
        exp = SpecialExpense.query.get(int(item_id))
        if exp:
            old = exp.payment_status
            exp.payment_status = status
            audit("payment", "special_expense", exp.id, exp.payee_name,
                  f"Desembolso gasto: {old} → {status} | {exp.description}")
            db.session.commit()
    elif item_type == "bv":
        acr = EventAcrescimo.query.get(int(item_id))
        if acr and acr.is_bv:
            old = acr.bv_payment_status
            acr.bv_payment_status = status
            audit("payment", "event_bv", acr.id, acr.bv_recipient or "—",
                  f"BV (repasse): {old} → {status}")
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

    return _done(status)


@financeiro_bp.route("/financeiro/pagamentos/salary/<int:sp_id>/advance", methods=["POST"])
@login_required
@require_financeiro
def salary_advance(sp_id: int):
    """Adiciona um adiantamento de salário (valor + comprovante) à lista — feature 067/089.

    Cada adiantamento é um item próprio (não sobrescreve os anteriores). O valor a pagar passa a ser
    o líquido (salário − soma dos adiantamentos). Comprovante é obrigatório; a soma não pode exceder o
    salário. Não altera o custo de salário do balanço.
    """
    import os

    from flask import current_app
    from werkzeug.utils import secure_filename

    from app.money import parse_brl
    from app.utils import audit

    sp = SalaryPayment.query.get_or_404(sp_id)
    month = request.form.get("month", sp.month_ref)
    back = redirect(url_for("financeiro.pagamentos", month=month))

    adv = parse_brl(request.form.get("advance_amount", ""))
    adv = adv if adv is not None else Decimal("0")
    if adv <= 0:
        flash("Informe um valor de adiantamento maior que zero.", "error")
        return back
    if (sp.advance_total + adv) > (sp.amount or Decimal("0")):
        flash("A soma dos adiantamentos não pode ser maior que o salário.", "error")
        return back

    proof = request.files.get("advance_proof")
    if not (proof and proof.filename):
        flash("Anexe o comprovante do adiantamento.", "error")
        return back

    proof.stream.seek(0, 2)
    size = proof.stream.tell()
    proof.stream.seek(0)
    if size > 10 * 1024 * 1024:
        flash("Comprovante acima de 10 MB.", "error")
        return back

    advance = SalaryAdvance(salary_payment_id=sp.id, amount=adv)
    db.session.add(advance)
    db.session.flush()  # garante advance.id para nomear o arquivo
    fname = f"adv_{sp.id}_{advance.id}_{secure_filename(proof.filename)}"
    proof.save(os.path.join(current_app.config["UPLOAD_PAYMENTS"], fname))
    advance.proof = f"/uploads/payments/{fname}"

    audit("payment", "salary_payment", sp.id, sp.user.name if sp.user else "—",
          f"Adiantamento de salário adicionado: R$ {adv}")
    db.session.commit()
    flash(f"Adiantamento de R$ {adv} adicionado. Valor a pagar atualizado.", "success")
    return back


@financeiro_bp.route("/financeiro/pagamentos/salary/advance/<int:adv_id>/delete", methods=["POST"])
@login_required
@require_financeiro
def salary_advance_delete(adv_id: int):
    """Remove um adiantamento específico da lista (e o comprovante) — feature 089."""
    import os

    from flask import current_app

    from app.utils import audit

    advance = SalaryAdvance.query.get_or_404(adv_id)
    sp = advance.payment
    month = request.form.get("month", sp.month_ref if sp else "")
    back = redirect(url_for("financeiro.pagamentos", month=month))

    if advance.proof and advance.proof.startswith("/uploads/payments/"):
        try:
            os.remove(os.path.join(
                current_app.config["UPLOAD_PAYMENTS"], os.path.basename(advance.proof)))
        except OSError:
            pass

    valor = advance.amount
    db.session.delete(advance)
    audit("payment", "salary_payment", sp.id if sp else 0, sp.user.name if sp and sp.user else "—",
          f"Adiantamento removido: R$ {valor}")
    db.session.commit()
    flash("Adiantamento removido.", "success")
    return back


def _bulk_set_commission_period(commission_id: str, action: str) -> bool:
    """Aplica pago/nao_pago a um item agregado de comissão ("sellerId:YYYY-MM").

    Mesmo efeito do controle individual da planilha. Retorna False se o id é inválido.
    """
    try:
        seller_part, period_tag = str(commission_id).split(":")
        seller_id = int(seller_part)
        py, pm = int(period_tag[:4]), int(period_tag[5:7])
    except (ValueError, AttributeError):
        return False
    p_start = date(py, pm, 1)
    p_end = date(py + 1, 1, 1) if pm == 12 else date(py, pm + 1, 1)
    target = "pago" if action == "pago" else "a_pagar"
    rows = CommissionPayment.query.filter(
        CommissionPayment.seller_id == seller_id,
        CommissionPayment.sale_date >= p_start,
        CommissionPayment.sale_date < p_end,
        CommissionPayment.status.in_(["a_pagar", "pago"]),
    ).all()
    for c in rows:
        c.status = target
        c.paid_at = date.today() if target == "pago" else None
    from app.utils import audit
    audit("payment", "commission", seller_id, "",
          f"Bulk comissões {period_tag}: → {target} ({len(rows)} itens)")
    return True


@financeiro_bp.route("/financeiro/pagamentos/bulk-action", methods=["POST"])
@login_required
@require_financeiro
def bulk_payment_action():
    action         = request.form.get("action")
    role_ids       = request.form.getlist("role_ids")
    salary_ids     = request.form.getlist("salary_ids")
    expense_ids    = request.form.getlist("expense_ids")
    commission_ids = request.form.getlist("commission_ids")
    month          = request.form.get("month", date.today().strftime("%Y-%m"))
    next_url       = url_for("financeiro.pagamentos", month=month)

    if not role_ids and not salary_ids and not expense_ids and not commission_ids:
        return redirect(next_url)

    from app.utils import audit

    r_ids = [int(i) for i in role_ids if i.isdigit()]
    s_ids = [int(i) for i in salary_ids if i.isdigit()]
    g_ids = [int(i) for i in expense_ids if i.isdigit()]

    changed = 0
    skipped: list[str] = []

    if action == "delete":
        # Gastos e comissões pertencem aos seus módulos — não são excluídos por aqui.
        for rid in r_ids:
            role = EventRole.query.get(rid)
            if role:
                db.session.delete(role)
                changed += 1
        for sid in s_ids:
            sp = SalaryPayment.query.get(sid)
            if sp:
                db.session.delete(sp)
                changed += 1
        if g_ids:
            skipped.append(f"{len(g_ids)} gasto(s) — exclua pelo módulo de Gastos")
        if commission_ids:
            skipped.append(f"{len(commission_ids)} comissão(ões) — gerencie na tela de Comissões")
        audit("delete", "payment", None, "bulk",
              f"Excluídos {len(r_ids)} cachês e {len(s_ids)} salários via pagamentos")
        db.session.commit()
        flash(f"{changed} item(ns) excluído(s).", "success")
    elif action in _VALID_PAYMENT_STATUS:
        for rid in r_ids:
            role = EventRole.query.get(rid)
            if role:
                old = role.payment_status
                role.payment_status = action
                changed += 1
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
                changed += 1
                audit("payment", "salary_payment", sp.id,
                      sp.user.name if sp.user else "—",
                      f"Bulk salário: {old} → {action}")
        for gid in g_ids:
            exp = SpecialExpense.query.get(gid)
            if exp:
                old = exp.payment_status
                exp.payment_status = action
                changed += 1
                audit("payment", "special_expense", exp.id, exp.payee_name,
                      f"Bulk desembolso gasto: {old} → {action} | {exp.description}")
        if commission_ids:
            if action == "no_banco":
                skipped.append(f"{len(commission_ids)} comissão(ões) — não têm estado 'no banco'")
            else:
                for cid in commission_ids:
                    if _bulk_set_commission_period(cid, action):
                        changed += 1
        db.session.commit()
        flash(f"{changed} item(ns) atualizado(s).", "success")

    for msg in skipped:
        flash(f"Ignorado: {msg}.", "info")

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

    events_q = CalendarEvent.query.filter(CalendarEvent.event_type != "ENSAIO")
    # Responsável EducaManto sem os papéis plenos vê APENAS os eventos EducaManto (feature 109).
    if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        events_q = events_q.filter(CalendarEvent.title.ilike(EDUCAMANTO_TITLE_PREFIX + "%"))
    events = events_q.order_by(CalendarEvent.start_at.desc()).all()

    events_data = []
    for e in events:
        custo = _group_cost(e) if e.is_group_leader else _event_cost(e)
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
@require_vendas
def comissoes():
    """Comissões: financeiro/superadmin gerenciam; comercial vê só as próprias (leitura)."""
    _resync_pending_commissions()
    can_manage = _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN)
    today = date.today()
    month = request.args.get("month", today.strftime("%Y-%m"))
    try:
        year, mon = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        year, mon = today.year, today.month

    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)

    # Comissões cujo sale_date cai no mês, ou sem sale_date mas criadas no mês
    entries_q = (
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
    )

    # Estornos pendentes (gerados por cancelamentos de meses anteriores)
    estornos_q = (
        CommissionPayment.query
        .filter(
            CommissionPayment.status == "a_pagar",
            CommissionPayment.amount < 0,
        )
        .order_by(CommissionPayment.created_at.asc())
    )

    if not can_manage:
        entries_q = entries_q.filter(CommissionPayment.seller_id == current_user.id)
        estornos_q = estornos_q.filter(CommissionPayment.seller_id == current_user.id)

    entries = entries_q.all()
    estornos = estornos_q.all()

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
        can_manage=can_manage,
        status_labels=_COMMISSION_STATUS_LABELS,
    )


@financeiro_bp.route("/financeiro/comissoes/set-status", methods=["POST"])
@login_required
@require_financeiro
def set_commission_status():
    cp_id  = request.form.get("cp_id")
    status = request.form.get("status")
    next_url = _safe_next(request.form.get("next"), url_for("financeiro.comissoes"))
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
