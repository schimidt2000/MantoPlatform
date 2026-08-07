"""Núcleo de negócio do Dashboard Comercial (`/vendas`) — feature 196.

Fonte única dos KPIs comerciais do período e da lista de vendas fechadas consumida por
``GET /api/vendas/pipeline``. Módulo **puro**: nunca importa ``flask.request``/``render_template``
— quem chama resolve o período e o escopo de vendedor e passa tudo como argumento.

Reusa (não duplica) os cálculos já existentes em ``app/financeiro/routes.py``
(``_event_commission``/``_commission_beneficiary``/``_is_permuta``) via import local, mesmo padrão
já adotado por ``app/api/financeiro_read.py``.
"""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app import db
from app.constants import EDUCAMANTO_TITLE_PREFIX, EVENT_TYPE_VIRTUAL
from app.models import CalendarEvent, EventContract, EventPayment

# ── Status do contrato do evento (derivado de EventContract) ──────────────────
CONTRACT_ASSINADO = "assinado"
CONTRACT_PENDENTE = "pendente"
CONTRACT_SEM_CONTRATO = "sem_contrato"

CONTRACT_STATUS_LABELS: dict[str, str] = {
    CONTRACT_ASSINADO: "Assinado",
    CONTRACT_PENDENTE: "Pendente",
    CONTRACT_SEM_CONTRATO: "Sem contrato",
}

# ── Status de recebimento do evento (derivado de EventPayment) ────────────────
PAYMENT_STATUS_LABELS: dict[str, str] = {
    "permuta": "Permuta/Cortesia",
    "sem_valor": "Sem valor",
    "pago_total": "Pago total",
    "parcial": "Parcial",
    "pendente": "Pendente",
}

# Tipo de evento que nunca é uma venda (ensaio interno).
NON_SALE_EVENT_TYPE = "ENSAIO"


def event_payment_status(sale_value: float, received: float, is_permuta: bool) -> str:
    """Status de recebimento de um evento a partir do valor de venda e do já recebido.

    Fonte única da regra que antes vivia inline no dashboard financeiro
    (``app/api/financeiro_read.py``) — as duas telas mostram exatamente o mesmo rótulo.

    Args:
        sale_value: Valor de venda do evento, em R$.
        received: Soma dos ``EventPayment`` do evento, em R$.
        is_permuta: Se o evento é cortesia/permuta (venda tratada como 0).

    Returns:
        Uma das chaves de :data:`PAYMENT_STATUS_LABELS`.
    """
    if is_permuta:
        return "permuta"
    if sale_value <= 0:
        return "sem_valor"
    if received >= sale_value:
        return "pago_total"
    if received > 0:
        return "parcial"
    return "pendente"


def closing_date(event: CalendarEvent) -> date | None:
    """Data de fechamento comercial do evento.

    ``sale_date`` quando preenchida; senão, a data do próprio evento (``start_at``). É o eixo do
    período no Dashboard Comercial: nenhuma venda some por falta de ``sale_date`` e nenhuma é
    contada em dois períodos.
    """
    if event.sale_date:
        return event.sale_date
    return event.start_at.date() if event.start_at else None


def contratante_name(event: CalendarEvent) -> str | None:
    """Nome do contratante do evento (feature 100).

    Prefere o ``EventClient`` com relação "Contratante"; cai para o primeiro cliente vinculado e,
    por fim, para o ``client_id`` denormalizado. ``None`` quando o evento não tem cliente.
    """
    linked = [ec for ec in event.event_clients if ec.client]
    for event_client in linked:
        if (event_client.relationship_type or "").strip().lower() == "contratante":
            return event_client.client.name
    if linked:
        return linked[0].client.name
    return event.client.name if event.client else None


def contract_status_map(event_ids: list[int]) -> dict[int, str]:
    """Status do contrato de cada evento, em uma consulta só.

    Um evento com pelo menos um contrato assinado é "assinado"; com contrato só enviado é
    "pendente"; sem nenhum contrato é "sem_contrato".
    """
    status = {event_id: CONTRACT_SEM_CONTRATO for event_id in event_ids}
    if not event_ids:
        return status
    rows = (
        db.session.query(EventContract.event_id, EventContract.is_signed)
        .filter(EventContract.event_id.in_(event_ids))
        .all()
    )
    for event_id, is_signed in rows:
        if is_signed:
            status[event_id] = CONTRACT_ASSINADO
        elif status[event_id] == CONTRACT_SEM_CONTRATO:
            status[event_id] = CONTRACT_PENDENTE
    return status


def received_map(event_ids: list[int]) -> dict[int, float]:
    """Total já recebido (``EventPayment``) por evento, em uma consulta só."""
    if not event_ids:
        return {}
    rows = (
        db.session.query(
            EventPayment.event_id,
            db.func.coalesce(db.func.sum(EventPayment.amount), 0),
        )
        .filter(EventPayment.event_id.in_(event_ids))
        .group_by(EventPayment.event_id)
        .all()
    )
    return {event_id: float(total or 0) for event_id, total in rows}


def list_closed_sales(
    start_date: date,
    end_date: date,
    *,
    seller_id: int | None = None,
    educamanto_only: bool = False,
) -> list[CalendarEvent]:
    """Vendas fechadas no período, da mais recente para a mais antiga.

    Três recortes, nesta ordem:

    1. **É uma venda.** Só entra evento com ``sale_value`` positivo ou marcado como
       cortesia/permuta (negócio fechado a R$ 0). Evento de agenda ainda sem valor não é venda e
       não polui o funil comercial — quem cobra esse preenchimento é a auditoria do Painel
       Financeiro.
    2. **Caiu no período.** Pela **data de fechamento** (ver :func:`closing_date`): ``sale_date``
       quando preenchida, senão a data do evento. A segunda perna resgata as vendas em que
       ninguém preencheu ``sale_date`` — sem ela, some dinheiro real do relatório.
    3. **Não duplica grupo comercial.** Eventos satélite ficam de fora: o principal carrega o
       valor do grupo inteiro (FR-010/FR-011), então incluí-los contaria a venda duas vezes.
    4. **Não é venda cancelada.** Evento cancelado (feature 224) sai do funil e do faturamento:
       o dinheiro está sendo devolvido, e a devolução aparece do outro lado como saída
       (`SpecialExpense` categoria "Devolução a cliente"). Contá-lo aqui somaria uma receita
       que a empresa não tem.

    Args:
        start_date: Primeiro dia do período (inclusive).
        end_date: Último dia do período (inclusive).
        seller_id: Quando informado, restringe às vendas desse vendedor.
        educamanto_only: Quando ``True``, restringe aos eventos EducaManto (título "(EDU…").
    """
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    query = CalendarEvent.query.filter(
        CalendarEvent.event_type != NON_SALE_EVENT_TYPE,
        CalendarEvent.cancelled_at.is_(None),
        CalendarEvent.group_leader_id.is_(None),
        db.or_(
            db.and_(CalendarEvent.sale_value.isnot(None), CalendarEvent.sale_value > 0),
            CalendarEvent.is_cortesia_permuta.is_(True),
        ),
        db.or_(
            db.and_(
                CalendarEvent.sale_date.isnot(None),
                CalendarEvent.sale_date >= start_date,
                CalendarEvent.sale_date <= end_date,
            ),
            db.and_(
                CalendarEvent.sale_date.is_(None),
                CalendarEvent.start_at >= start_dt,
                CalendarEvent.start_at <= end_dt,
            ),
        ),
    )
    if seller_id is not None:
        query = query.filter(CalendarEvent.seller_id == seller_id)
    if educamanto_only:
        query = query.filter(CalendarEvent.title.ilike(EDUCAMANTO_TITLE_PREFIX + "%"))
    events = query.all()
    events.sort(key=lambda e: closing_date(e) or date.min, reverse=True)
    return events


def is_loja_virtual(event: CalendarEvent) -> bool:
    """True se a venda veio da Loja de Interações Virtuais (feature 205, FR-052).

    **Fonte única do recorte de canal.** Todo agregador financeiro que precisa separar a loja usa
    esta função — DRE, KPIs de evento, pipeline comercial e comissões. Espalhar
    ``event_type == "VIRTUAL"`` pelo código seria a forma garantida de esquecer um ponto, e um
    ponto esquecido é exatamente como o ticket médio se distorce ou nasce uma comissão fantasma.
    """
    return event.event_type == EVENT_TYPE_VIRTUAL


def split_por_canal(
    events: list[CalendarEvent],
) -> tuple[list[CalendarEvent], list[CalendarEvent]]:
    """Separa ``(eventos_presenciais, vendas_da_loja_virtual)``.

    A loja é um canal com natureza diferente: dezenas de microvendas de 10 minutos, sem vendedor,
    fechadas sozinhas. Misturá-las com shows nos mesmos indicadores não é só impreciso — muda a
    leitura que a equipe faz do próprio desempenho (FR-054).
    """
    virtuais = [e for e in events if is_loja_virtual(e)]
    presenciais = [e for e in events if not is_loja_virtual(e)]
    return presenciais, virtuais


def resumo_loja_virtual(events: list[CalendarEvent]) -> dict[str, Any]:
    """Consolidado da Loja Virtual para o painel (FR-053).

    A receita **continua** somando no DRE — é dinheiro que entrou. O que muda é que ela aparece
    identificada, e não diluída dentro dos números de show.
    """
    virtuais = [e for e in events if is_loja_virtual(e)]
    receita = sum((Decimal(e.sale_value or 0) for e in virtuais), Decimal("0"))
    return {
        "canal": "Loja Virtual",
        "vendas": len(virtuais),
        "receita": float(receita),
        "ticket_medio": float(receita / len(virtuais)) if virtuais else 0.0,
    }


def billable_sales(sales: list[CalendarEvent]) -> list[CalendarEvent]:
    """Subconjunto que entra nos KPIs: venda de verdade, com valor — sem permutas/cortesias.

    Mesma regra de ``eventos_com_venda`` no dashboard financeiro, para os números baterem entre
    as duas telas.
    """
    from app.financeiro.routes import _is_permuta

    return [e for e in sales if not _is_permuta(e) and (e.sale_value or 0) > 0]


def build_kpis(
    sales: list[CalendarEvent],
    settings: Any,
    commission_target_id: int | None,
) -> dict[str, float | int]:
    """KPIs comerciais do período.

    Args:
        sales: Vendas do período já no escopo do usuário (:func:`list_closed_sales`).
        settings: ``SiteSetting`` (alíquotas e responsável EducaManto).
        commission_target_id: Usuário cuja comissão projetar. ``None`` soma a comissão de todas as
            vendas do escopo (visão de gestor — despesa de comissão da empresa).

    Returns:
        ``total_vendido``, ``ticket_medio``, ``eventos_fechados``, ``comissao_prevista`` e
        ``desconto_concedido`` (diferença entre o preço de tabela e o valor fechado).
    """
    from app.financeiro.routes import _commission_beneficiary, _event_commission

    faturaveis = billable_sales(sales)
    total_vendido = sum((Decimal(e.sale_value or 0) for e in faturaveis), Decimal("0"))
    desconto = sum(
        (
            Decimal(e.sale_value_gross) - Decimal(e.sale_value or 0)
            for e in faturaveis
            if e.sale_value_gross and Decimal(e.sale_value_gross) > Decimal(e.sale_value or 0)
        ),
        Decimal("0"),
    )
    ticket_medio = (
        (total_vendido / Decimal(len(faturaveis))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if faturaveis
        else Decimal("0")
    )

    comissao = Decimal("0")
    for event in faturaveis:
        if commission_target_id is not None:
            beneficiary = _commission_beneficiary(event, settings)
            if beneficiary is None or beneficiary.id != commission_target_id:
                continue
        comissao += _event_commission(event, settings)

    return {
        "total_vendido": float(total_vendido),
        "ticket_medio": float(ticket_medio),
        "eventos_fechados": len(faturaveis),
        "comissao_prevista": float(comissao),
        "desconto_concedido": float(desconto),
    }


def serialize_sale(
    event: CalendarEvent,
    settings: Any,
    *,
    contract_status: str,
    received: float,
) -> dict[str, Any]:
    """Serializa uma venda para a tabela de acompanhamento do Dashboard Comercial.

    Sem custo e sem lucro por decisão de negócio (feature 196): essas colunas pertencem ao
    Painel Financeiro. O foco aqui é a relação comercial — cliente, valor, contrato e cobrança.
    """
    from app.financeiro.routes import _event_commission, _is_permuta

    sale_value = float(event.sale_value or 0)
    is_permuta = _is_permuta(event)
    payment_status = event_payment_status(sale_value, received, is_permuta)
    closing = closing_date(event)
    return {
        "event_id": event.id,
        "title": event.title,
        "group_label": (
            f"{event.group_display_name} ({len(event.satellites) + 1} eventos)"
            if event.is_group_leader
            else None
        ),
        "client_name": contratante_name(event),
        "event_date": event.start_at.date().isoformat() if event.start_at else None,
        "sale_date": event.sale_date.isoformat() if event.sale_date else None,
        "closing_date": closing.isoformat() if closing else None,
        "sale_value": sale_value,
        "sale_value_gross": float(event.sale_value_gross) if event.sale_value_gross else None,
        "seller_id": event.seller_id,
        "seller_name": event.seller.name if event.seller else None,
        "contract_status": contract_status,
        "contract_status_label": CONTRACT_STATUS_LABELS[contract_status],
        "payment_status": payment_status,
        "payment_status_label": PAYMENT_STATUS_LABELS[payment_status],
        "comissao": float(_event_commission(event, settings)),
        "is_permuta": is_permuta,
    }


def serialize_sales(sales: list[CalendarEvent], settings: Any) -> list[dict[str, Any]]:
    """Serializa a lista inteira resolvendo contrato e recebimento em duas consultas agregadas."""
    event_ids = [e.id for e in sales]
    contracts = contract_status_map(event_ids)
    received = received_map(event_ids)
    return [
        serialize_sale(
            event,
            settings,
            contract_status=contracts[event.id],
            received=received.get(event.id, 0.0),
        )
        for event in sales
    ]
