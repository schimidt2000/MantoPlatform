"""Núcleo de negócio do módulo de Comissões (feature 187).

Funções puras (sem `flask.request`/`render_template`/`flash`), reusadas apenas pelos endpoints
de API (`app/api/financeiro_read.py`, `app/api/financeiro_write.py`) — fonte única da agregação
por mês/vendedor e da liquidação em lote atômica (Princípio I).

`app/financeiro/routes.py` (view Jinja legada) e sua própria cópia de
`_bulk_set_commission_period` NÃO importam deste módulo — permanecem como estão, por decisão
explícita de não tocar o Jinja legado nesta feature (ver `specs/187-comissoes-modulo-completo/
research.md` §2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app import db
from app.models import CommissionPayment, User

TZ_SP = ZoneInfo("America/Sao_Paulo")

STATUS_LABELS = {
    "a_pagar": "A pagar",
    "pago": "Pago",
    "cancelado": "Cancelado",
}


class InvalidMonthError(ValueError):
    """Formato de mês inválido — esperado `AAAA-MM`."""


class SellerNotFoundError(ValueError):
    """`seller_id` não corresponde a nenhum usuário com papel Comercial."""


@dataclass(frozen=True)
class CommissionEntry:
    """Uma linha de `CommissionPayment` serializada para a API."""

    id: int
    seller_id: int
    seller_name: str
    event_id: int | None
    event_title: str
    sale_date: str | None
    amount: Decimal
    status: str
    status_label: str
    paid_at: str | None

    def to_dict(self) -> dict:
        """Serializa para o payload JSON da API."""
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "seller_name": self.seller_name,
            "event_id": self.event_id,
            "event_title": self.event_title,
            "sale_date": self.sale_date,
            "amount": float(self.amount),
            "status": self.status,
            "status_label": self.status_label,
            "paid_at": self.paid_at,
        }


@dataclass(frozen=True)
class CommissionKpis:
    """Os 3 cards de KPI do topo da tela."""

    total_month: Decimal
    total_paid: Decimal
    total_pending: Decimal

    def to_dict(self) -> dict:
        """Serializa para o payload JSON da API."""
        return {
            "total_month": float(self.total_month),
            "total_paid": float(self.total_paid),
            "total_pending": float(self.total_pending),
        }


@dataclass
class CommissionMonthSummaryRow:
    """Uma linha agregada por vendedor, para a visão "Resumo por Vendedor"."""

    seller_id: int
    seller_name: str
    sale_count: int
    total_amount: Decimal
    pending_amount: Decimal
    month_status: str
    entries: list[CommissionEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serializa para o payload JSON da API."""
        return {
            "seller_id": self.seller_id,
            "seller_name": self.seller_name,
            "sale_count": self.sale_count,
            "total_amount": float(self.total_amount),
            "pending_amount": float(self.pending_amount),
            "month_status": self.month_status,
            "entries": [e.to_dict() for e in self.entries],
        }


@dataclass(frozen=True)
class PayoutResult:
    """Retorno da liquidação em lote de um vendedor/mês."""

    seller_id: int
    month: str
    changed_count: int
    paid_total: Decimal
    summary: CommissionMonthSummaryRow | None

    def to_dict(self) -> dict:
        """Serializa para o payload JSON da API."""
        return {
            "seller_id": self.seller_id,
            "month": self.month,
            "changed_count": self.changed_count,
            "paid_total": float(self.paid_total),
            "summary": self.summary.to_dict() if self.summary else None,
        }


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """Retorna `[início, fim)` do mês, como `date`."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def parse_month_strict(month: str) -> tuple[date, date]:
    """Parseia `AAAA-MM` estritamente — levanta `InvalidMonthError` se inválido."""
    try:
        year, mon = int(month[:4]), int(month[5:7])
        if not 1 <= mon <= 12:
            raise ValueError("mês fora do intervalo 1-12")
    except (ValueError, IndexError, TypeError) as exc:
        raise InvalidMonthError(f"Mês inválido: {month!r}") from exc
    return _month_bounds(year, mon)


def resolve_month(month: str | None) -> tuple[str, date, date]:
    """Resolve a string de mês com fallback tolerante ao mês corrente (mesmo padrão da leitura
    já existente em `api_financeiro_comissoes`)."""
    today = datetime.now(TZ_SP).date()
    candidate = month or today.strftime("%Y-%m")
    try:
        start, end = parse_month_strict(candidate)
    except InvalidMonthError:
        candidate = today.strftime("%Y-%m")
        start, end = _month_bounds(today.year, today.month)
    return candidate, start, end


def _month_scoped_query(start: date, end: date, seller_id: int | None = None):
    """Query base: comissões cujo `sale_date` cai no mês, ou sem `sale_date` mas criadas no
    mês (mesma regra de `api_financeiro_comissoes`)."""
    q = CommissionPayment.query.filter(
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
    if seller_id is not None:
        q = q.filter(CommissionPayment.seller_id == seller_id)
    return q.order_by(CommissionPayment.sale_date.asc(), CommissionPayment.seller_id.asc())


def _pending_reversals_query(seller_id: int | None = None):
    """Estornos pendentes (`a_pagar`, valor negativo) — sem filtro de mês: um estorno de um
    evento cancelado herda o `sale_date` da venda original, então precisa continuar visível
    mesmo quando o usuário navega para o mês corrente (ver `research.md` da feature 187)."""
    q = CommissionPayment.query.filter(
        CommissionPayment.status == "a_pagar",
        CommissionPayment.amount < 0,
    )
    if seller_id is not None:
        q = q.filter(CommissionPayment.seller_id == seller_id)
    return q.order_by(CommissionPayment.created_at.asc())


def _to_entry(cp: CommissionPayment) -> CommissionEntry:
    return CommissionEntry(
        id=cp.id,
        seller_id=cp.seller_id,
        seller_name=cp.seller.name if cp.seller else "—",
        event_id=cp.event_id,
        event_title=cp.event_title,
        sale_date=cp.sale_date.isoformat() if cp.sale_date else None,
        amount=cp.amount,
        status=cp.status,
        status_label=STATUS_LABELS.get(cp.status, cp.status),
        paid_at=cp.paid_at.isoformat() if cp.paid_at else None,
    )


def get_month_entries(month: str, seller_id: int | None = None) -> list[CommissionEntry]:
    """Visão analítica ("Detalhamento de Vendas"): uma linha por comissão do mês selecionado."""
    _, start, end = resolve_month(month)
    return [_to_entry(cp) for cp in _month_scoped_query(start, end, seller_id).all()]


def _seller_payable_rows(month: str, seller_id: int) -> list[CommissionPayment]:
    """Registros `CommissionPayment` elegíveis para o resumo/liquidação de UM vendedor no mês:
    as comissões do mês (por `sale_date`/`created_at`) mais os estornos pendentes do vendedor
    (que ficam visíveis em qualquer mês até serem resolvidos). Deduplicado por `id` para não
    contar duas vezes um estorno cujo `sale_date` cai no próprio mês selecionado."""
    _, start, end = resolve_month(month)
    rows = _month_scoped_query(start, end, seller_id).all()
    seen_ids = {cp.id for cp in rows}
    for cp in _pending_reversals_query(seller_id).all():
        if cp.id not in seen_ids:
            rows.append(cp)
            seen_ids.add(cp.id)
    return rows


def get_month_summary_by_seller(
    month: str, seller_id: int | None = None
) -> list[CommissionMonthSummaryRow]:
    """Visão "Resumo por Vendedor": agrupa por vendedor as comissões do mês + estornos
    pendentes de cada vendedor."""
    if seller_id is not None:
        seller_ids = [seller_id]
    else:
        _, start, end = resolve_month(month)
        month_ids = {
            row[0]
            for row in db.session.query(CommissionPayment.seller_id)
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
            .distinct()
        }
        reversal_ids = {
            row[0]
            for row in db.session.query(CommissionPayment.seller_id)
            .filter(CommissionPayment.status == "a_pagar", CommissionPayment.amount < 0)
            .distinct()
        }
        seller_ids = sorted(month_ids | reversal_ids)

    rows: list[CommissionMonthSummaryRow] = []
    for sid in seller_ids:
        cps = _seller_payable_rows(month, sid)
        if not cps:
            continue
        entries = [_to_entry(cp) for cp in cps]
        total_amount = sum((e.amount for e in entries), Decimal("0"))
        pending_amount = sum(
            (e.amount for e in entries if e.status == "a_pagar"), Decimal("0")
        )
        rows.append(
            CommissionMonthSummaryRow(
                seller_id=sid,
                seller_name=entries[0].seller_name,
                sale_count=len(entries),
                total_amount=total_amount,
                pending_amount=pending_amount,
                month_status="pago" if pending_amount == 0 else "pendente",
                entries=entries,
            )
        )
    rows.sort(key=lambda r: r.seller_name)
    return rows


def get_month_kpis(month: str, seller_id: int | None = None) -> CommissionKpis:
    """Os 3 KPIs do topo, somados diretamente a partir do resumo por vendedor (mesma fonte que
    alimenta os botões "Pagar Mês" — garante que os KPIs batem centavo a centavo com o que pode
    ser efetivamente liquidado)."""
    rows = get_month_summary_by_seller(month, seller_id)
    total_paid = sum(
        (e.amount for r in rows for e in r.entries if e.status == "pago"), Decimal("0")
    )
    total_pending = sum((r.pending_amount for r in rows), Decimal("0"))
    return CommissionKpis(
        total_month=total_paid + total_pending,
        total_paid=total_paid,
        total_pending=total_pending,
    )


def pay_seller_month(seller_id: int, month: str, actor: User) -> PayoutResult:
    """Liquida em lote, de forma atômica, todas as comissões `a_pagar` elegíveis de um vendedor
    em um mês (incluindo estornos pendentes do vendedor — ver `_seller_payable_rows`).

    Usa `with_for_update()` para travar os registros elegíveis durante a transação: se duas
    liquidações para o mesmo vendedor/mês forem disparadas quase ao mesmo tempo, a segunda
    espera a primeira commitar e então relê o estado, encontrando 0 registros `a_pagar`
    restantes — idempotente, nunca paga duas vezes (ver `research.md` §4).

    Args:
        seller_id: vendedor a liquidar.
        month: mês no formato `AAAA-MM`.
        actor: usuário que está executando a liquidação (para auditoria).

    Returns:
        PayoutResult com a quantidade de registros alterados nesta chamada e o resumo
        atualizado do vendedor.

    Raises:
        InvalidMonthError: `month` fora do formato `AAAA-MM`.
        SellerNotFoundError: `seller_id` não existe.
    """
    from app.utils import audit

    month_norm, start, end = (month, *parse_month_strict(month))
    seller = User.query.get(seller_id)
    if seller is None:
        raise SellerNotFoundError(f"Vendedor {seller_id} não encontrado")

    today = datetime.now(TZ_SP).date()
    ids_seen = {cp.id for cp in _month_scoped_query(start, end, seller_id).all()}
    ids_seen |= {cp.id for cp in _pending_reversals_query(seller_id).all()}

    if ids_seen:
        payable = (
            CommissionPayment.query.filter(
                CommissionPayment.id.in_(ids_seen),
                CommissionPayment.status == "a_pagar",
            )
            .with_for_update()
            .all()
        )
    else:
        payable = []

    changed_count = 0
    paid_total = Decimal("0")
    for cp in payable:
        cp.status = "pago"
        cp.paid_at = today
        changed_count += 1
        paid_total += cp.amount

    if changed_count:
        audit(
            "payment",
            "commission_month",
            seller_id,
            seller.name,
            f"Liquidação em lote {month_norm}: {changed_count} registro(s), "
            f"R$ {paid_total} (por {actor.name})",
        )
    db.session.commit()

    summary_rows = get_month_summary_by_seller(month_norm, seller_id)
    summary = summary_rows[0] if summary_rows else None
    return PayoutResult(
        seller_id=seller_id,
        month=month_norm,
        changed_count=changed_count,
        paid_total=paid_total,
        summary=summary,
    )
