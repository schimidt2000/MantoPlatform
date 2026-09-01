"""Núcleo de negócio do módulo de Comissões (feature 187).

Funções puras (sem `flask.request`/`render_template`/`flash`), reusadas apenas pelos endpoints
de API (`app/api/financeiro_read.py`, `app/api/financeiro_write.py`) — fonte única da agregação
por mês/vendedor e da liquidação em lote atômica (Princípio I).

**Desde a feature 267 o Jinja legado importa daqui** — o inverso do que esta docstring dizia. O
motivo é que a liquidação existia em QUATRO cópias linha a linha (controle individual e em lote,
cada um com seu gêmeo em `app/financeiro/routes.py`), e as quatro filtravam por `sale_date` puro
enquanto o item da planilha era montado por `coalesce(payable_from, sale_date)`. Comissão
EducaManto aparecia num mês e era liquidada por outro: o botão clicava e nada mudava.

`ciclo_de_pagamento_expr()` e `liquidar_periodo()` são a fonte única disso. A decisão de 2026-07
de "não tocar o Jinja legado" (ver `specs/187-comissoes-modulo-completo/research.md` §2) valia
enquanto a duplicação era inerte; deixar de valer foi o preço de o defeito ser P0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from app import db
from app.constants import EVENT_TYPE_VIRTUAL, now_sp
from app.models import CalendarEvent, CommissionPayment, SiteSetting, User

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


def _sem_loja_virtual(q):
    """Remove da query comissões atreladas a vendas da Loja Virtual (feature 205, FR-054).

    `_sync_commission_payment` já impede que essas linhas nasçam; este filtro é a segunda trava,
    para linhas anteriores à feature ou criadas por outro caminho. Estornos (`event_id IS NULL`)
    continuam visíveis — o NOT EXISTS só descarta o que tem evento virtual atrelado.
    """
    return q.filter(
        ~db.session.query(CalendarEvent)
        .filter(
            CalendarEvent.id == CommissionPayment.event_id,
            CalendarEvent.event_type == EVENT_TYPE_VIRTUAL,
        )
        .exists()
    )


def ciclo_de_pagamento_expr():
    """Expressão do mês em que a comissão entra no repasse (feature 267).

    Comissão comum entra pelo mês da **venda**; comissão EducaManto, pelo mês da **realização**
    (feature 109, `payable_from`). É a mesma expressão que monta o item agregado da Planilha de
    Pagamentos — e por isso tem de ser a mesma que o liquida.

    Existir como função é o ponto: as quatro liquidações filtravam por `sale_date` puro enquanto
    o item era montado pelo `coalesce`, então o item de maio procurava a venda em maio, achava
    zero linhas, e a tela mostrava "pago" sobre um lote que continuava `a_pagar` no banco.

    Returns:
        Expressão SQLAlchemy `coalesce(payable_from, sale_date)`.
    """
    return db.func.coalesce(CommissionPayment.payable_from, CommissionPayment.sale_date)


def liquidar_periodo(
    seller_id: int, p_start: date, p_end: date, target: str
) -> list[CommissionPayment]:
    """Aplica `status`/`paid_at` às comissões de um vendedor no ciclo (feature 267).

    Fonte única das quatro liquidações que existiam duplicadas linha a linha (controle
    individual e em lote, cada um com seu gêmeo Jinja). **Não commita e não audita** — as duas
    coisas dependem do request (`current_user`) e ficam nas rotas.

    Args:
        seller_id: vendedor cujo lote está sendo liquidado.
        p_start: primeiro dia do ciclo (inclusive).
        p_end: primeiro dia do mês seguinte (exclusive).
        target: ``"pago"``, ``"no_banco"`` ou ``"a_pagar"``.

    Returns:
        As linhas afetadas (para a rota montar a mensagem de auditoria).
    """
    ciclo = ciclo_de_pagamento_expr()
    rows = CommissionPayment.query.filter(
        CommissionPayment.seller_id == seller_id,
        ciclo >= p_start,
        ciclo < p_end,
        # `no_banco` faz parte do conjunto liquidável aqui, diferente de `_month_scoped_query`
        # (que é leitura do módulo de Comissões). Não unificar sem medir: muda o que o lote pega.
        CommissionPayment.status.in_(["a_pagar", "no_banco", "pago"]),
    ).all()
    for c in rows:
        c.status = target
        # `now_sp()`, nunca `date.today()`: produção roda em UTC e depois das 21h de Brasília o
        # pagamento seria carimbado no dia seguinte.
        c.paid_at = now_sp().date() if target == "pago" else None
    return rows


#: Status de comissão que representam dinheiro vivo (o que será ou já foi pago). `cancelado`
#: fica de fora: é linha de evento cancelado, sem movimentação.
_STATUS_VIVOS = ("a_pagar", "no_banco", "pago")


def comissao_exibida_do_evento(event, settings) -> tuple[Decimal, str]:
    """Comissão a exibir no detalhe do evento, e de onde ela veio (feature 267).

    Existia em duas cópias divergentes — `_compute_kpi` (API) e a view Jinja `event_detail` —,
    ambas com 2% flat sobre venda−BV. Isso ignora EducaManto (5% sobre o LUCRO), a Loja Virtual
    (que não comissiona) e `receives_commission`: a tela do evento mostrava um número que o
    Financeiro nunca ia pagar.

    Três camadas, nesta ordem:

    1. **Evento cancelado → 0.** O cancelamento esvazia o backref (a linha e o estorno ficam com
       `event_id` nulo), então sem esta guarda o fallback voltaria a inventar número exatamente
       onde o financeiro já estornou. A regra canônica sozinha NÃO protege: quem checa
       cancelamento é a sincronização, não o cálculo.
    2. **Linha real**, quando existe: é o que o Financeiro efetivamente vai pagar — e, se já foi
       pago, é histórico congelado que não deve mais acompanhar a venda.
    3. **Regra canônica** como reserva, nunca a fórmula flat: ela já devolve 0 para Loja Virtual
       e para beneficiário sem `receives_commission`, e usa a base de lucro no EducaManto.

    Args:
        event: o evento (num grupo comercial, passe o LÍDER — venda e comissão vivem só nele).
        settings: `SiteSetting` singleton, para a taxa padrão.

    Returns:
        `(valor, origem)`, com origem ``"linha"`` (provisionada) ou ``"estimativa"`` (calculada).
    """
    if getattr(event, "is_cancelled", False):
        return Decimal("0"), "linha"

    linhas = [c for c in event.commission_payments if c.status in _STATUS_VIVOS]
    if linhas:
        total = sum((Decimal(c.amount) for c in linhas), Decimal("0"))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "linha"

    return _event_commission(event, settings), "estimativa"


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
    q = _sem_loja_virtual(q)
    return q.order_by(CommissionPayment.sale_date.asc(), CommissionPayment.seller_id.asc())


def _is_mes_corrente(month: str) -> bool:
    """True se `month` (`AAAA-MM`) é o mês em que estamos, em horário de Brasília."""
    return month == datetime.now(TZ_SP).date().strftime("%Y-%m")


def _pending_reversals_query(seller_id: int | None = None):
    """Estornos pendentes (`a_pagar`, valor negativo), sem filtro de mês.

    Um estorno herda o `sale_date` da venda original, que costuma cair num mês já quitado — sem
    esta consulta ele ficaria invisível e nunca seria descontado (feature 187). Quem chama é que
    decide **onde** exibi-lo: hoje só no mês corrente, via `_estornos_do_mes` — trazê-lo para
    todos os meses fazia o mesmo estorno reaparecer em cada tela e derrubar o total de meses que
    não tinham nada com ele.
    """
    q = CommissionPayment.query.filter(
        CommissionPayment.status == "a_pagar",
        CommissionPayment.amount < 0,
    )
    if seller_id is not None:
        q = q.filter(CommissionPayment.seller_id == seller_id)
    q = _sem_loja_virtual(q)
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


def _estornos_do_mes(month: str, seller_id: int | None) -> list[CommissionPayment]:
    """Estornos pendentes que entram na conta do mês pedido — só no **mês corrente**.

    Um estorno é uma dívida do vendedor com a empresa, e ela é abatida no próximo repasse: o
    lugar dele é o mês que está aberto, não todo mês do histórico. Enquanto ele aparecia em
    todos, um estorno de julho derrubava também o total de abril — meses que não tinham nada a
    ver com ele — e a mesma linha reaparecia em cada tela, parecendo comissão ressuscitada.

    O estorno não se perde: fica no mês corrente até ser liquidado. E o mês da venda original
    continua mostrando-o pela via normal (`_month_scoped_query`), porque a `sale_date` dele é a
    da venda estornada.
    """
    if not _is_mes_corrente(month):
        return []
    return _pending_reversals_query(seller_id).all()


def _com_estornos(
    rows: list[CommissionPayment], month: str, seller_id: int | None
) -> list[CommissionPayment]:
    """Junta os estornos do mês às linhas já selecionadas, sem duplicar por id."""
    seen_ids = {cp.id for cp in rows}
    for cp in _estornos_do_mes(month, seller_id):
        if cp.id not in seen_ids:
            rows.append(cp)
            seen_ids.add(cp.id)
    return rows


def get_month_entries(month: str, seller_id: int | None = None) -> list[CommissionEntry]:
    """Visão analítica ("Detalhamento de Vendas"): uma linha por comissão do mês selecionado.

    Usa a MESMA seleção do resumo por vendedor, incluindo os estornos que entram na conta do
    mês. Sem isso a tabela não fecha com o total do topo nem com o que o "Pagar Mês" liquida —
    era o caso do estorno do `(SHOW) PETER PAN…`, que descontava R$ 170,00 sem aparecer em
    linha nenhuma (a `sale_date` dele é de julho, e o desconto acontece no mês corrente).
    """
    month_ref, start, end = resolve_month(month)
    rows = _month_scoped_query(start, end, seller_id).all()
    return [_to_entry(cp) for cp in _com_estornos(rows, month_ref, seller_id)]


def _seller_payable_rows(month: str, seller_id: int) -> list[CommissionPayment]:
    """Registros `CommissionPayment` elegíveis para o resumo/liquidação de UM vendedor no mês:
    as comissões do mês (por `sale_date`/`created_at`) mais os estornos pendentes que caem no
    mês corrente. Deduplicado por `id` para não contar duas vezes um estorno cujo `sale_date`
    já cai no próprio mês selecionado."""
    month_ref, start, end = resolve_month(month)
    rows = _month_scoped_query(start, end, seller_id).all()
    return _com_estornos(rows, month_ref, seller_id)


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


# ─────────────────────────────────────────────────────────────────────────────
# Motor de cálculo da comissão, movido de `routes.py` na preparação da fase 6 da remoção do Jinja.
#
# Isto nunca foi código de tela: `app/api/financeiro_read.py` — a API que alimenta o DRE, o
# pipeline de vendas e a planilha de pagamentos do React — importava `_event_commission`,
# `_event_cost`, `_group_cost`, `_get_commission_rate` e `_resync_pending_commissions` de dentro
# do blueprint Jinja. Apagar aquele arquivo derrubaria o financeiro inteiro da plataforma nova.
#
# São nove ramos de decisão até o valor final: Loja Virtual não comissiona, beneficiário pode ser
# o responsável EducaManto em vez do vendedor, EducaManto calcula sobre o LUCRO (venda − BV −
# cachês) e o resto sobre a venda, BV sempre sai da base, evento cancelado não comissiona, custo
# de líder de grupo agrega os satélites, e comissão já paga nunca é reescrita.
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_COMMISSION = Decimal("2.5")
# Comissão EducaManto (feature 109): % sobre o LUCRO do evento (venda − BV − cachês),
# diferente da comissão comum (% sobre a venda). Override por evento continua valendo.
# Este é só o piso de fábrica: a taxa vigente é `SiteSetting.educamanto_commission_rate`,
# editável em Configurações — mudar o acordo com o responsável não deve exigir deploy.
EDUCAMANTO_COMMISSION_RATE = Decimal("5")


def _educamanto_commission_rate(settings) -> Decimal:
    """% da comissão EducaManto vigente — configuração, com fallback no padrão de 5%."""
    rate = getattr(settings, "educamanto_commission_rate", None) if settings else None
    return Decimal(str(rate)) if rate is not None else EDUCAMANTO_COMMISSION_RATE


def _get_commission_rate(event, settings) -> Decimal:
    """Returns commission rate as Decimal (never float)."""
    if event.commission_rate is not None:
        return Decimal(str(event.commission_rate))
    if settings and settings.default_commission_rate is not None:
        return Decimal(str(settings.default_commission_rate))
    return DEFAULT_COMMISSION


def _event_cost(event) -> int:
    """Custo de cachês do evento — soma só o que a Manto realmente paga.

    A vaga "Técnico de Som (Presença)" fica fora (feature 239, decisão 10): ela nunca tem
    cachê, e um valor herdado de antes da trava não pode continuar inflando custo, margem e
    base de comissão.
    """
    from app.calendar.casting_ops import e_vaga_de_presenca

    return sum(
        r.cache_value or 0
        for r in event.roles
        if r.talent_id and not e_vaga_de_presenca(r)
    )


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
    # Venda da Loja de Interações Virtuais não comissiona (feature 205, FR-054): ela se fecha
    # sozinha, sem vendedor, e provisionar percentual sobre ela criaria uma despesa que nunca
    # será paga a ninguém — dinheiro reservado no caixa para um beneficiário que não existe.
    from app.financeiro.vendas_ops import is_loja_virtual

    if is_loja_virtual(event):
        return Decimal("0")
    beneficiary = _commission_beneficiary(event, settings)
    if beneficiary and not beneficiary.receives_commission:
        return Decimal("0")
    if event.is_educamanto and _educamanto_responsavel(settings) is not None:
        # Comissão EducaManto (feature 109): 5% sobre o LUCRO (venda − BV − cachês).
        rate = (
            Decimal(str(event.commission_rate))
            if event.commission_rate is not None
            else _educamanto_commission_rate(settings)
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
    # Loja Virtual não gera linha de comissão (feature 205, FR-054). O corte é aqui, na origem:
    # se a linha nunca nasce, nenhum relatório precisa lembrar de escondê-la depois.
    from app.financeiro.vendas_ops import is_loja_virtual

    if is_loja_virtual(event):
        return

    existing = CommissionPayment.query.filter_by(event_id=event.id).filter(
        CommissionPayment.status != "cancelado"
    ).first()

    settings = SiteSetting.query.get(1)
    beneficiary = _commission_beneficiary(event, settings)

    should_have = (
        event.sale_value
        and beneficiary is not None
        and beneficiary.receives_commission
        # Evento cancelado (feature 224) não comissiona. Sem isto, qualquer escrita posterior
        # no evento recriaria a comissão que `aplicar_estorno_comissao` acabou de estornar.
        and not event.is_cancelled
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
