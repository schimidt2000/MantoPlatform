"""Endpoints de LEITURA de Financeiro/Vendas (feature 156, abre a US4; 157, dashboard DRE;
158, comissões; 159, planilha de pagamentos — fecha a leitura da US4; 196, pivot do pipeline de
vendas para Dashboard Comercial).

Reusa os cálculos já existentes em `app/financeiro/routes.py` (`_group_cost`/`_event_cost`/
`_event_commission`/`_resolve_period`/`_compute_drg`/etc.) e o núcleo comercial de
`app/financeiro/vendas_ops.py` — não duplica lógica de negócio, só serializa. Gates
(`require_vendas`/`require_financeiro`) reimplementados aqui como funções simples porque os
decorators originais são específicos de view Flask.
"""

from collections import defaultdict
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required
from app.constants import RoleName
from app.models import (
    CalendarEvent,
    EventInstallment,
    EventInvoice,
    Role,
    SiteSetting,
    User,
)

TZ_SP = ZoneInfo("America/Sao_Paulo")

PERIOD_LABELS = {
    "este_mes": "Este mês",
    "30d": "Últimos 30 dias",
    "mes_anterior": "Mês anterior",
    "custom": "Período personalizado",
}


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _is_educamanto_responsavel(settings: SiteSetting | None) -> bool:
    return bool(settings and settings.educamanto_seller_id == current_user.id)


def _can_view_vendas(settings: SiteSetting | None) -> bool:
    return _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN) or (
        _is_educamanto_responsavel(settings)
    )


class _VendasScope:
    """Escopo de leitura do Dashboard Comercial, decidido no servidor (feature 196).

    Attributes:
        can_filter_seller: Gestor (Financeiro/Superadmin) — vê a empresa toda e pode filtrar.
        seller_id: Vendedor ao qual a lista está restrita (``None`` = sem restrição).
        educamanto_only: Responsável EducaManto sem papel comercial — só eventos "(EDU…".
        commission_target_id: De quem é a comissão projetada (``None`` = comissão da empresa).
    """

    def __init__(
        self,
        *,
        can_filter_seller: bool,
        seller_id: int | None,
        educamanto_only: bool,
        commission_target_id: int | None,
    ) -> None:
        self.can_filter_seller = can_filter_seller
        self.seller_id = seller_id
        self.educamanto_only = educamanto_only
        self.commission_target_id = commission_target_id


def _resolve_vendas_scope() -> _VendasScope:
    """Decide no servidor o que o usuário logado enxerga no Dashboard Comercial.

    Nunca confia no cliente: um `COMERCIAL` sem papel de gestão recebe as próprias vendas
    independentemente do ``seller_id`` que vier na query string (mesma política já usada em
    ``api_financeiro_comissoes``).
    """
    can_filter_seller = _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN)
    is_comercial = _has_role(RoleName.COMERCIAL)
    educamanto_only = not (is_comercial or can_filter_seller)
    requested_seller_id = request.args.get("seller_id", type=int)

    if can_filter_seller:
        seller_id = requested_seller_id
    elif educamanto_only:
        seller_id = None  # o recorte já é o dos eventos EducaManto
    else:
        seller_id = current_user.id

    return _VendasScope(
        can_filter_seller=can_filter_seller,
        seller_id=seller_id,
        educamanto_only=educamanto_only,
        commission_target_id=requested_seller_id if can_filter_seller else current_user.id,
    )


def _comercial_sellers() -> list[dict[str, Any]]:
    """Vendedores selecionáveis no filtro de gestor — mesma lista de `api_financeiro_comissoes`."""
    sellers = (
        User.query.join(User.roles)
        .filter(Role.name == RoleName.COMERCIAL)
        .order_by(User.name)
        .all()
    )
    return [{"id": u.id, "name": u.name} for u in sellers]


@api_bp.route("/vendas/pipeline")
@api_login_required
def api_vendas_pipeline() -> Any:
    """Dashboard Comercial: KPIs de venda do período + funil fechado (feature 196).

    Substitui o pipeline plano da feature 156. Custo e lucro saíram do payload de propósito —
    são informação do Painel Financeiro, e o papel `COMERCIAL` não acessa aquele painel.
    """
    from app.financeiro import vendas_ops
    from app.financeiro.routes import _resolve_period

    settings = SiteSetting.query.get(1)
    if not _can_view_vendas(settings):
        return jsonify({"error": {"message": "Sem permissão"}}), 403

    scope = _resolve_vendas_scope()
    today = datetime.now(TZ_SP).date()
    period, start_date, end_date, _is_full_month = _resolve_period(today)

    sales = vendas_ops.list_closed_sales(
        start_date,
        end_date,
        seller_id=scope.seller_id,
        educamanto_only=scope.educamanto_only,
    )

    # Venda da Loja Virtual não tem vendedor: ela se fecha sozinha. Deixá-la no funil do time
    # comercial inflaria metas que ninguém bateu e afundaria a taxa de conversão de quem vende de
    # verdade (FR-054). Some da tela do vendedor; para o gestor, aparece **separada**, com o total
    # do canal — esconder receita de quem consolida seria o erro oposto (FR-055).
    presenciais, virtuais = vendas_ops.split_por_canal(sales)
    # FR-055: gestor pode pedir o funil consolidado com o canal dentro; o vendedor comum não —
    # para ele a loja simplesmente não existe nesta tela.
    incluir_virtual = (
        scope.can_filter_seller
        and request.args.get("incluir_loja_virtual") in ("1", "true", "sim")
    )
    funil = sales if incluir_virtual else presenciais

    payload: dict[str, Any] = {
        "period": period,
        "period_label": PERIOD_LABELS.get(period, "Este mês"),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "can_filter_seller": scope.can_filter_seller,
        "seller_id": scope.seller_id,
        "scope_label": "Empresa toda" if scope.commission_target_id is None else "Minhas vendas",
        "kpis": vendas_ops.build_kpis(funil, settings, scope.commission_target_id),
        "eventos": vendas_ops.serialize_sales(funil, settings),
    }
    if scope.can_filter_seller:
        payload["sellers"] = _comercial_sellers()
        payload["loja_virtual"] = vendas_ops.resumo_loja_virtual(virtuais)
        payload["incluir_loja_virtual"] = incluir_virtual

    return jsonify(payload)


def _floatify(d: dict) -> dict:
    """Converte todo valor `Decimal` de um dict raso para `float` (JSON-safe)."""
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in d.items()}


@api_bp.route("/financeiro/dashboard")
@api_login_required
def api_financeiro_dashboard() -> Any:
    """Dashboard financeiro (DRE): consolidado do período (feature 157).

    Reaproveita, sem duplicar, os mesmos cálculos de `dashboard()`
    (`app/financeiro/routes.py:387`) — só monta a query do período e serializa.
    """
    from app import db
    from app.financeiro import vendas_ops
    from app.financeiro.routes import (
        FATOR_R_RATE_HIGH,
        FATOR_R_RATE_LOW,
        _compute_drg,
        _event_commission,
        _event_cost,
        _get_commission_rate,
        _get_fator_r_threshold,
        _get_tax_rate,
        _group_cost,
        _is_permuta,
        _month_range,
        _month_refs_between,
        _pct,
        _prev_month,
        _resolve_period,
        _salary_cost,
    )
    from app.gastos.routes import ensure_recurring_entries
    from app.models import EventPayment, RecurringExpenseEntry, SpecialExpense

    if not _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return jsonify({"error": {"message": "Sem permissão"}}), 403

    settings = SiteSetting.query.get(1)
    today = datetime.now(TZ_SP).date()
    now_naive = datetime.now(TZ_SP).replace(tzinfo=None)

    period, start_date, end_date, is_full_month = _resolve_period(today)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

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

    realizados = [e for e in events if e.start_at and e.start_at < now_naive]
    projetados = [e for e in events if e.start_at and e.start_at >= now_naive]

    salary_cost = _salary_cost(start_date, end_date, is_full_month)
    gastos_extras = sum(
        (Decimal(g.amount) for g in SpecialExpense.query.filter(
            SpecialExpense.status == "aprovado",
            SpecialExpense.expense_date >= start_date,
            SpecialExpense.expense_date <= end_date,
        ).all()),
        Decimal("0"),
    )

    ensure_recurring_entries(today.year, today.month)
    gastos_recorrentes = sum(
        (Decimal(e.amount) for e in RecurringExpenseEntry.query.filter(
            RecurringExpenseEntry.month_ref.in_(_month_refs_between(start_date, end_date)),
            RecurringExpenseEntry.status != "pulado",
            RecurringExpenseEntry.amount.isnot(None),
        ).all()),
        Decimal("0"),
    )

    drg_realizado = _compute_drg(realizados, settings, salary_cost, gastos_extras, gastos_recorrentes)
    drg_projetado = _compute_drg(projetados, settings, Decimal("0"), Decimal("0"))
    drg_total = _compute_drg(events, settings, salary_cost, gastos_extras, gastos_recorrentes)

    from app.financeiro.vendas_ops import is_loja_virtual, resumo_loja_virtual

    todas_com_venda = [
        e for e in events
        if not _is_permuta(e) and not e.is_satellite and e.sale_value and e.sale_value > 0
    ]
    # A receita da Loja Virtual **continua** dentro da cascata da DRE — Fator R, break-even e
    # resultado líquido seguem exatos, porque é dinheiro que entrou de verdade (FR-053).
    # O que sai são os indicadores **de evento**: ticket médio e "a receber" (FR-054). Dezenas de
    # microvendas de 10 minutos ao lado de shows completos não distorcem só a média — mudam a
    # leitura que a equipe faz do próprio desempenho.
    # FR-055: o gestor pode pedir o consolidado com o canal dentro. É opt-in explícito — o padrão
    # segrega, porque quem abre a tela sem escolher nada quer os números de evento limpos.
    incluir_virtual = request.args.get("incluir_loja_virtual") in ("1", "true", "sim")
    eventos_com_venda = (
        todas_com_venda
        if incluir_virtual
        else [e for e in todas_com_venda if not is_loja_virtual(e)]
    )
    loja_virtual = resumo_loja_virtual(todas_com_venda)

    receita_presencial = sum(
        (Decimal(e.sale_value or 0) for e in eventos_com_venda), Decimal("0")
    )
    ticket_medio = (
        (receita_presencial / Decimal(len(eventos_com_venda))).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        if eventos_com_venda else Decimal("0")
    )
    ratio_custo_talento = _pct(drg_total["cpv"], drg_total["receita_liquida"])

    fixed_cost = drg_total["pessoal"] + drg_total["comissoes"]
    breakeven_pct = _pct(drg_total["lucro_bruto"], fixed_cost)
    breakeven_atingido = bool(fixed_cost > 0 and drg_total["lucro_bruto"] >= fixed_cost)

    fator_r_threshold = _get_fator_r_threshold(settings)
    fator_r_pct = _pct(drg_total["pessoal"], drg_total["receita_bruta"])
    fator_r_protegido = bool(drg_total["receita_bruta"] > 0 and fator_r_pct >= fator_r_threshold)

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

    roles_no_periodo = [r for e in events for r in e.roles if r.talent_id]
    pagamentos_pendentes = sum(
        float(r.cache_value or 0) for r in roles_no_periodo if r.payment_status == "nao_pago"
    )
    pagamentos_realizados = sum(
        float(r.cache_value or 0) for r in roles_no_periodo
        if r.payment_status in ("pago", "no_banco")
    )

    # A receita por tipo é onde a Loja Virtual **deve** aparecer: é a visão por canal, e omiti-la
    # aqui esconderia receita real do gestor. Entra como uma barra própria, identificada
    # (FR-053/FR-055) — o oposto de diluí-la dentro de SHOW.
    receita_por_tipo_dd = defaultdict(int)
    for e in eventos_com_venda:
        receita_por_tipo_dd[e.event_type or "Outros"] += (e.sale_value or 0)
    if loja_virtual["vendas"]:
        receita_por_tipo_dd["Loja Virtual"] += Decimal(str(loja_virtual["receita"]))
    receita_por_tipo = {
        k: float(v) for k, v in sorted(receita_por_tipo_dd.items(), key=lambda x: -x[1])
    }
    receita_tipo_max = max(receita_por_tipo.values()) if receita_por_tipo else 0.0

    seller_revenue = defaultdict(int)
    seller_margin = defaultdict(int)
    for e in eventos_com_venda:
        if e.seller_id:
            seller_revenue[e.seller_id] += (e.sale_value or 0)
            seller_margin[e.seller_id] += (e.sale_value or 0) - _group_cost(e)
    top_sellers = []
    for sid, rev in sorted(seller_revenue.items(), key=lambda x: -x[1])[:5]:
        u = User.query.get(sid)
        if u:
            top_sellers.append({
                "user_id": u.id,
                "user_name": u.name,
                "receita": float(rev),
                "lucro": float(seller_margin[sid]),
            })

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
            "receita": float(rec),
            "custo": float(cst),
            "lucro": float(rec - cst),
            "margem": float(_pct(rec - cst, rec)),
            "n_eventos": len(evs),
        })
        y, m = _prev_month(y, m)

    auditoria = [
        {
            "event_id": e.id,
            "title": e.title,
            "start_at": e.start_at.isoformat() if e.start_at else None,
        }
        for e in events
        if not _is_permuta(e) and not e.is_satellite and not (e.sale_value and e.sale_value > 0)
    ]

    eventos_data = []
    for e in events:
        if e.is_satellite:
            continue
        custo = float(_group_cost(e) if e.is_group_leader else _event_cost(e) or 0)
        comissao = float(_event_commission(e, settings))
        recebido = float(_recebido_por_evento.get(e.id, 0))
        venda = float(e.sale_value or 0)
        # Mesma regra do Dashboard Comercial (feature 196) — fonte única em `vendas_ops`.
        status = vendas_ops.event_payment_status(venda, recebido, _is_permuta(e))
        eventos_data.append({
            "event_id": e.id,
            "title": e.title,
            "group_label": (
                f"{e.group_display_name} ({len(e.satellites) + 1} eventos)"
                if e.is_group_leader else None
            ),
            "start_at": e.start_at.isoformat() if e.start_at else None,
            "event_type": e.event_type or None,
            "receita": venda,
            "custo": custo,
            "lucro": (0 if _is_permuta(e) else venda) - custo,
            "comissao": comissao,
            "rate": float(_get_commission_rate(e, settings)),
            "is_projetado": bool(e.start_at and e.start_at >= now_naive),
            "status": status,
        })

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
        {
            "date": inst.due_date.isoformat() if inst.due_date else None,
            "event_id": ev.id,
            "event_title": ev.title,
            "amount": float(inst.amount or 0),
        }
        for inst, ev in _inst_rows
    ]
    recebimentos_previstos_total = sum(r["amount"] for r in recebimentos_previstos)

    tax_rate_nf = _get_tax_rate(settings)

    _nf_pend = (
        EventInvoice.query
        .filter(EventInvoice.status == "a_emitir")
        .join(CalendarEvent, EventInvoice.event_id == CalendarEvent.id)
        .order_by(EventInvoice.issue_date.is_(None), EventInvoice.issue_date.asc())
        .all()
    )
    nf_a_emitir = [
        {
            "id": inv.id,
            "date": inv.issue_date.isoformat() if inv.issue_date else None,
            "event_id": inv.event_id,
            "event_title": inv.event.title if inv.event else "—",
            "amount": float(inv.amount or 0),
        }
        for inv in _nf_pend
    ]
    nf_a_emitir_total = sum(n["amount"] for n in nf_a_emitir)

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
            "amount": float(_val),
            "date": inv.issue_date.isoformat() if inv.issue_date else None,
            "status": inv.status,
            "custo": float(_custo),
        })
    custo_nota_total = sum(i["custo"] for i in custo_nota_itens)

    return jsonify({
        "period": period,
        "period_label": PERIOD_LABELS.get(period, "Este mês"),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "is_full_month": is_full_month,
        "dre": {
            "realizado": _floatify(drg_realizado),
            "projetado": _floatify(drg_projetado),
            "total": _floatify(drg_total),
        },
        "kpis": {
            "ticket_medio": float(ticket_medio),
            "ratio_custo_talento": float(ratio_custo_talento),
            "margem_bruta": float(drg_total["margem_bruta"]),
            "margem_ebitda": float(drg_total["margem_ebitda"]),
            "breakeven_pct": float(breakeven_pct),
            "breakeven_atingido": breakeven_atingido,
            "fixed_cost": float(fixed_cost),
            "fator_r_pct": float(fator_r_pct),
            "fator_r_threshold": float(fator_r_threshold),
            "fator_r_protegido": fator_r_protegido,
            # Rótulos fiscais (feature 189): alíquota de imposto provisionado sobre eventos com
            # nota e as duas faixas do Fator R — mesma fonte da tela Jinja legada.
            "tax_rate": float(tax_rate_nf),
            "fator_r_rate_low": FATOR_R_RATE_LOW,
            "fator_r_rate_high": FATOR_R_RATE_HIGH,
        },
        "paineis": {
            "a_receber_clientes": a_receber_clientes,
            "pagamentos_pendentes": pagamentos_pendentes,
            "pagamentos_realizados": pagamentos_realizados,
            "receita_por_tipo": receita_por_tipo,
            "receita_tipo_max": receita_tipo_max,
            # Consolidado do canal (feature 205, FR-053): a receita já está somada na cascata da
            # DRE; este bloco existe para o gestor conferir quanto dela veio da loja.
            "loja_virtual": loja_virtual,
            "incluir_loja_virtual": incluir_virtual,
            "top_sellers": top_sellers,
            "monthly_trend": monthly_trend,
            "auditoria": auditoria,
        },
        "eventos": eventos_data,
        "pendencias": {
            "recebimentos_previstos": recebimentos_previstos,
            "recebimentos_previstos_total": recebimentos_previstos_total,
            "nf_a_emitir": nf_a_emitir,
            "nf_a_emitir_total": nf_a_emitir_total,
            "custo_nota_itens": custo_nota_itens,
            "custo_nota_total": custo_nota_total,
        },
    })


@api_bp.route("/financeiro/comissoes")
@api_login_required
def api_financeiro_comissoes() -> Any:
    """Comissões do mês: leitura (feature 158, reestruturada na feature 187).

    RBAC aplicado no servidor: vendedor comum (sem Financeiro/Superadmin) só recebe os
    próprios dados, independente do que for passado em `seller_id` — nunca confia no cliente
    para restringir o escopo. Reaproveita `comissoes_ops` (fonte única com a view Jinja
    legada não tocando este módulo) e `_resync_pending_commissions` (mesma reconciliação de
    `app/financeiro/routes.py`, sem duplicar).
    """
    from app.financeiro import comissoes_ops
    from app.financeiro.routes import _resync_pending_commissions

    settings = SiteSetting.query.get(1)
    if not _can_view_vendas(settings):
        return jsonify({"error": {"message": "Sem permissão"}}), 403

    _resync_pending_commissions()
    can_manage = _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN)

    month_param = request.args.get("month")
    requested_seller_id = request.args.get("seller_id", type=int)
    seller_filter = requested_seller_id if can_manage else current_user.id

    month, _start, _end = comissoes_ops.resolve_month(month_param)
    kpis = comissoes_ops.get_month_kpis(month, seller_filter)
    by_seller = comissoes_ops.get_month_summary_by_seller(month, seller_filter)
    entries = comissoes_ops.get_month_entries(month, seller_filter)

    payload: dict[str, Any] = {
        "month": month,
        "can_manage": can_manage,
        "title": "Comissões" if can_manage else "Minhas Comissões",
        "kpis": kpis.to_dict(),
        "by_seller": [row.to_dict() for row in by_seller],
        "entries": [e.to_dict() for e in entries],
    }
    if can_manage:
        sellers = (
            User.query.join(User.roles)
            .filter(Role.name == RoleName.COMERCIAL)
            .order_by(User.name)
            .all()
        )
        payload["sellers"] = [{"id": u.id, "name": u.name} for u in sellers]

    return jsonify(payload)


def _serialize_pagamento_item(item: dict) -> dict:
    """Serializa um item da planilha de pagamentos para o payload da API (feature 159).

    Reaproveita os campos já montados por ``_build_payment_items``/``_build_bv_items``/
    ``_build_commission_items``/``_build_recurring_items`` — só converte tipos (data→ISO,
    ``Decimal``→``float``) e re-lê os adiantamentos de ``SalaryAdvance`` como números, em vez
    da string já formatada em BRL que aquelas funções montam para o template Jinja.
    """
    from app.models import SalaryAdvance

    out: dict[str, Any] = {
        "type": item["type"],
        "id": item["id"],
        "date": item["date"].isoformat() if item.get("date") else None,
        "event_title": item.get("event_title"),
        "event_id": item.get("event_id"),
        "copy_label": item.get("copy_label"),
        "sublabel": item.get("sublabel"),
        "person_name": item.get("person_name"),
        "amount": float(item["amount"] or 0),
        "pix_key": item.get("pix_key") or "",
        "pix_key_type": item.get("pix_key_type") or "",
        "status": item["status"],
        "is_future": bool(item.get("is_future")),
    }
    if item["type"] == "salary":
        out["gross_amount"] = float(item.get("gross_amount") or 0)
        out["advance_amount"] = float(item.get("advance_amount") or 0)
        advances = (
            SalaryAdvance.query
            .filter_by(salary_payment_id=item["id"])
            .order_by(SalaryAdvance.advance_date.asc())
            .all()
        )
        out["advances"] = [
            {
                "id": a.id,
                "amount": float(a.amount or 0),
                "date": a.advance_date.isoformat() if a.advance_date else None,
                "proof": a.proof or "",
            }
            for a in advances
        ]
    if item["type"] == "bv":
        out["missing_data"] = bool(item.get("missing_data"))
    return out


@api_bp.route("/financeiro/pagamentos")
@api_login_required
def api_financeiro_pagamentos() -> Any:
    """Planilha de pagamentos do mês: leitura (feature 159).

    Reaproveita, sem duplicar, os mesmos itens de ``pagamentos()``
    (`app/financeiro/routes.py:1088`) — só monta a mesma combinação e serializa.
    """
    from app.financeiro.routes import (
        _STATUS_LABELS,
        _build_bv_items,
        _build_commission_items,
        _build_payment_items,
        _build_recurring_items,
        _ensure_salary_payments,
        _pagamentos_query,
        _resync_pending_commissions,
    )
    from app.gastos.routes import ensure_recurring_entries
    from app.models import EventAcrescimo, SalaryPayment, SpecialExpense

    if not _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return jsonify({"error": {"message": "Sem permissão"}}), 403

    _resync_pending_commissions()
    now_sp = datetime.now(TZ_SP).replace(tzinfo=None)
    today = now_sp.date()
    month = request.args.get("month", today.strftime("%Y-%m"))
    try:
        year, mon = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        month = today.strftime("%Y-%m")
        year, mon = today.year, today.month

    _ensure_salary_payments(year, mon)

    roles = _pagamentos_query(month)
    salary_payments = (
        SalaryPayment.query.filter_by(month_ref=f"{year:04d}-{mon:02d}")
        .order_by(SalaryPayment.due_date.asc())
        .all()
    )

    m_start = date(year, mon, 1)
    m_end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    expenses = (
        SpecialExpense.query
        .filter(
            SpecialExpense.status == "aprovado",
            SpecialExpense.disbursement_type.isnot(None),
            SpecialExpense.paid_at_creation.is_(False),
            SpecialExpense.expense_date >= m_start,
            SpecialExpense.expense_date < m_end,
        )
        .order_by(SpecialExpense.expense_date.asc())
        .all()
    )

    items = _build_payment_items(roles, salary_payments, today, expenses, now_sp)

    bv_rows = (
        EventAcrescimo.query.join(CalendarEvent)
        .filter(
            EventAcrescimo.is_bv.is_(True),
            CalendarEvent.start_at >= datetime.combine(m_start, datetime.min.time()),
            CalendarEvent.start_at < datetime.combine(m_end, datetime.min.time()),
        )
        .all()
    )
    items += _build_bv_items(bv_rows, today, now_sp)

    prev_year, prev_month = (year - 1, 12) if mon == 1 else (year, mon - 1)
    prev_start = date(prev_year, prev_month, 1)
    prev_end = m_start
    items += _build_commission_items(prev_start, prev_end, date(year, mon, 5), today)

    ensure_recurring_entries(year, mon)
    items += _build_recurring_items(year, mon, today)
    items.sort(key=lambda x: x["date"])

    def _amt(item: dict) -> Decimal:
        v = item["amount"]
        return Decimal(str(v)) if v else Decimal("0")

    totals = {
        "total": float(sum(_amt(i) for i in items)),
        "pago": float(sum(_amt(i) for i in items if i["status"] == "pago")),
        "no_banco": float(sum(_amt(i) for i in items if i["status"] == "no_banco")),
        "pendente": float(
            sum(_amt(i) for i in items if i["status"] == "nao_pago" and not i["is_future"])
        ),
        "futuro": float(
            sum(_amt(i) for i in items if i["status"] == "nao_pago" and i["is_future"])
        ),
    }

    return jsonify({
        "month": month,
        "totals": totals,
        "status_labels": _STATUS_LABELS,
        "items": [_serialize_pagamento_item(i) for i in items],
    })
