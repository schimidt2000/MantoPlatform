"""A DRE única da API e do Jinja: os gastos extras do período e a tendência mensal (feature 306).

As duas telas da DRE (`app/financeiro/routes.py:dashboard` e `app/api/financeiro_read.py:
api_financeiro_dashboard`) montavam essas duas contas em duas cópias linha a linha. O cancelamento
mexe nas duas — a devolução do cancelado sai dos gastos (ela já está no retido, que é pago menos
devolvido) e o retido entra na tendência pelo mês do cancelamento —, e duas cópias divergiriam.

Os helpers da DRE (`_is_permuta`, `_month_range`, `_prev_month`, `_pct`, `_group_cost`) continuam
em `financeiro/routes.py` (remoção do Jinja PAUSADA: nada se move de lá) e entram por import tardio.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app import db
from app.models import CalendarEvent, SpecialExpense

#: O rótulo do retido na receita por tipo e na linha da DRE (contracts §19).
ROTULO_RETIDO = "Retido de cancelamentos"


def gastos_extras_do_periodo(start: date, end: date) -> Decimal:
    """Os gastos extras aprovados do período, **menos** a devolução de evento cancelado.

    A devolução do cancelado, de qualquer regime (o dia cortado inclusive), já está descontada no
    retido (pago − devolvido): somá-la aqui contaria a devolução duas vezes. A multa ao elenco e a
    devolução ligada a evento vivo ficam.
    """
    from app.calendar.cancel_ops import filtro_devolucao

    cancelados = db.session.query(CalendarEvent.id).filter(CalendarEvent.cancelled_at.isnot(None))
    linhas = (
        SpecialExpense.query.filter(
            SpecialExpense.status == "aprovado",
            SpecialExpense.expense_date >= start,
            SpecialExpense.expense_date <= end,
        )
        .filter(db.not_(db.and_(filtro_devolucao(), SpecialExpense.event_id.in_(cancelados))))
        .all()
    )
    return sum((Decimal(g.amount) for g in linhas), Decimal("0"))


def tendencia_mensal(today: date, meses: int = 6) -> list[dict]:
    """A tendência dos últimos meses (visão operacional: receita − cachês), do mais antigo ao atual.

    O cancelado sai do mês do evento (antes ele ficava, com a venda inteira) e o retido entra no
    mês do cancelamento, só quando ≠ 0, com a chave `retido` ao lado. Os valores saem crus
    (`Decimal`); a API os converte.
    """
    from app.calendar import cancel_ops
    from app.financeiro.routes import _group_cost, _is_permuta, _month_range, _pct, _prev_month

    tendencia: list[dict] = []
    y, m = today.year, today.month
    for _ in range(meses):
        s_dt, e_dt = _month_range(y, m)
        evs = CalendarEvent.query.filter(
            CalendarEvent.start_at >= s_dt,
            CalendarEvent.start_at < e_dt,
            CalendarEvent.event_type != "ENSAIO",
            CalendarEvent.cancelled_at.is_(None),
        ).all()
        normais = [e for e in evs if not _is_permuta(e) and not e.is_satellite]
        rec = sum(e.sale_value or 0 for e in normais)
        cst = sum(_group_cost(e) for e in normais)
        retido = sum(
            (
                r.retido
                for r in cancel_ops.cancelados_do_periodo(
                    s_dt.date(), (e_dt - timedelta(days=1)).date()
                )
            ),
            Decimal("0"),
        )
        item: dict = {"label": f"{m:02d}/{str(y)[2:]}"}
        if retido != 0:
            rec = rec + retido
            item["retido"] = retido
        item.update(
            {
                "receita": rec,
                "custo": cst,
                "lucro": rec - cst,
                "margem": _pct(rec - cst, rec),
                "n_eventos": len(evs),
            }
        )
        tendencia.insert(0, item)
        y, m = _prev_month(y, m)
    return tendencia
