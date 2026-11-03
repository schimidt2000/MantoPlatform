"""Itens em aberto de meses anteriores na Planilha de Pagamentos (correção 331).

A Planilha mostra cada item no mês a que ele pertence: cachê e BV pelo mês do evento, salário e
conta recorrente pelo `month_ref`, gasto pela `expense_date`, comissão pelo mês do repasse (o ciclo
de outubro é o item de 05/11). O que ficava sem pagar ficava para trás, e o Financeiro voltava mês a
mês para achar. Aqui o mês ATUAL ganha também o que está "Não pago" ou "No banco" nas planilhas dos
meses anteriores, desde `PLANILHA_ATRASADOS_DESDE`.

Só a tela traz o item; o banco não muda. A DRE soma cada custo pela data de origem, então mover a
data levaria o custo de um mês para outro. E abrir um mês apaga e regera os salários não pagos dele
(`_ensure_salary_payments`): por isso este módulo só LÊ o que existe e nunca chama os `ensure_*` dos
meses passados.

Os itens saem dos mesmos montadores da planilha (`_build_*` de `app/financeiro/routes.py`, com
import tardio pelo ciclo com `routes`) e mantêm o id: marcar pago no mês atual grava no item de
origem, e a comissão leva o ciclo no id (`vendedor:AAAA-MM`).
"""

from __future__ import annotations

from datetime import date, datetime

from app.constants import DIA_DO_REPASSE, PLANILHA_ATRASADOS_DESDE
from app.models import EventAcrescimo, EventRole, SalaryPayment, SpecialExpense

STATUS_EM_ABERTO = ("nao_pago", "no_banco")


def mes_de(dia: date) -> str:
    """O mês de uma data no formato da planilha ("AAAA-MM")."""
    return f"{dia.year:04d}-{dia.month:02d}"


def _meses_entre(desde: date, ate: date) -> list[date]:
    """O dia 1º de cada mês em [desde, ate)."""
    meses: list[date] = []
    atual = desde.replace(day=1)
    while atual < ate:
        meses.append(atual)
        atual = date(atual.year + (atual.month == 12), atual.month % 12 + 1, 1)
    return meses


def _inicio_do_mes_anterior(inicio: date) -> date:
    return (
        date(inicio.year - 1, 12, 1)
        if inicio.month == 1
        else date(inicio.year, inicio.month - 1, 1)
    )


def _meia_noite(dia: date) -> datetime:
    return datetime.combine(dia, datetime.min.time())


def caches_em_aberto_anteriores(inicio_do_mes: date) -> list[EventRole]:
    """Os cachês em aberto das planilhas de meses anteriores — também alimenta o CSV do mês atual."""
    from app.financeiro.routes import _pagamentos_roles_entre

    if inicio_do_mes <= PLANILHA_ATRASADOS_DESDE:
        return []
    return (
        _pagamentos_roles_entre(_meia_noite(PLANILHA_ATRASADOS_DESDE), _meia_noite(inicio_do_mes))
        .filter(EventRole.payment_status.in_(STATUS_EM_ABERTO))
        .all()
    )


def _do_evento_e_dos_gastos(
    desde: date, ate: date, hoje: date, agora: datetime
) -> list[tuple[str, dict]]:
    """Cachês, gastos e BVs: o mês de origem é o mês da data do item (evento ou gasto)."""
    from app.financeiro.routes import (
        _build_bv_items,
        _build_payment_items,
        _pagamentos_bvs_entre,
        _pagamentos_gastos_entre,
    )

    gastos = (
        _pagamentos_gastos_entre(desde, ate)
        .filter(SpecialExpense.payment_status.in_(STATUS_EM_ABERTO))
        .all()
    )
    bvs = (
        _pagamentos_bvs_entre(desde, ate)
        .filter(EventAcrescimo.bv_payment_status.in_(STATUS_EM_ABERTO))
        .all()
    )
    itens = _build_payment_items(caches_em_aberto_anteriores(ate), [], hoje, gastos, agora)
    itens += _build_bv_items(bvs, hoje, agora)
    return [(mes_de(item["date"]), item) for item in itens]


def _salarios(meses: list[date], hoje: date, agora: datetime) -> list[tuple[str, dict]]:
    """Salários pelo `month_ref` — é ele que põe o salário na planilha (e no custo da DRE)."""
    from app.financeiro.routes import _build_payment_items

    salarios = (
        SalaryPayment.query.filter(
            SalaryPayment.month_ref.in_([mes_de(m) for m in meses]),
            SalaryPayment.payment_status.in_(STATUS_EM_ABERTO),
        )
        .order_by(SalaryPayment.due_date.asc())
        .all()
    )
    mes_por_id = {s.id: s.month_ref for s in salarios}
    return [(mes_por_id[i["id"]], i) for i in _build_payment_items([], salarios, hoje, None, agora)]


def _comissoes_e_contas(meses: list[date], hoje: date) -> list[tuple[str, dict]]:
    """Comissões (o ciclo do mês anterior, no repasse do dia 5) e contas recorrentes, mês a mês."""
    from app.financeiro.routes import _build_commission_items, _build_recurring_items

    pares: list[tuple[str, dict]] = []
    for inicio in meses:
        repasse = inicio.replace(day=DIA_DO_REPASSE)
        itens = _build_commission_items(_inicio_do_mes_anterior(inicio), inicio, repasse, hoje)
        itens += _build_recurring_items(inicio.year, inicio.month, hoje)
        pares += [(mes_de(inicio), item) for item in itens]
    return pares


def itens_em_aberto_anteriores(inicio_do_mes: date, hoje: date, agora: datetime) -> list[dict]:
    """Os itens das planilhas de meses anteriores que ainda esperam pagamento.

    Args:
        inicio_do_mes: dia 1º do mês atual; entra só o que pertence a planilhas anteriores a ele.
        hoje: a data de hoje em São Paulo.
        agora: o "agora" de São Paulo, naïve como `CalendarEvent.start_at`.

    Returns:
        Itens no formato da planilha, do mais antigo ao mais novo, com `de_mes_anterior`,
        `mes_origem` e `dias_em_atraso`. O que ainda vai vencer (`is_future`) não vem: de mês
        anterior, só o vencido.
    """
    meses = _meses_entre(PLANILHA_ATRASADOS_DESDE, inicio_do_mes)
    if not meses:
        return []
    pares = _do_evento_e_dos_gastos(meses[0], inicio_do_mes, hoje, agora)
    pares += _salarios(meses, hoje, agora)
    pares += _comissoes_e_contas(meses, hoje)
    anteriores = []
    for mes_origem, item in pares:
        if item["status"] not in STATUS_EM_ABERTO or item["is_future"]:
            continue
        item.update(
            de_mes_anterior=True,
            mes_origem=mes_origem,
            dias_em_atraso=max(0, (hoje - item["date"]).days),
        )
        anteriores.append(item)
    return sorted(anteriores, key=lambda item: item["date"])
