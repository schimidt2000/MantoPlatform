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
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from app import db
from app.constants import EVENT_TYPE_VIRTUAL, now_sp
from app.models import CalendarEvent, CommissionPayment, SiteSetting, User

TZ_SP = ZoneInfo("America/Sao_Paulo")

STATUS_LABELS = {
    "a_pagar": "A pagar",
    "no_banco": "No banco",
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
    # Feature 306: o que a linha é (comissão, ajuste ou estorno), a paga que ela acerta, se o evento
    # foi cancelado, o ciclo em que entra no repasse (AAAA-MM) e o motivo do ajuste (FR-033).
    tipo: str = "comissao"
    original_id: int | None = None
    evento_cancelado: bool = False
    ciclo: str | None = None
    motivo: str | None = None

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
            "tipo": self.tipo,
            "original_id": self.original_id,
            "evento_cancelado": self.evento_cancelado,
            "ciclo": self.ciclo,
            "motivo": self.motivo,
        }


@dataclass(frozen=True)
class CommissionKpis:
    """Os cards de KPI do topo da tela (o 4º, "No banco", é da feature 306)."""

    total_month: Decimal
    total_paid: Decimal
    total_pending: Decimal
    total_no_banco: Decimal = Decimal("0")

    def to_dict(self) -> dict:
        """Serializa para o payload JSON da API."""
        return {
            "total_month": float(self.total_month),
            "total_paid": float(self.total_paid),
            "total_pending": float(self.total_pending),
            "total_no_banco": float(self.total_no_banco),
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

    Hotfix 267b: terceiro degrau, `date(created_at)`. Uma comissão sem `sale_date` (a venda foi
    gravada sem data — o formulário React nascia com o campo vazio) caía fora de **todo** mês da
    Planilha de Pagamentos e nunca entrava num lote de pagamento: 38 comissões de agosto de uma
    vendedora, R$ 5.162,26, invisíveis. A data de criação da linha é a melhor aproximação da data
    da venda (a linha nasce quando a venda é gravada), e é o que a tela de Comissões já usava como
    fallback (`_month_scoped_query`) — as duas telas passam a concordar. Ressalva: `created_at` é
    UTC (`utcnow`), então uma venda gravada depois das 21h do último dia do mês pode cair no mês
    seguinte por esse degrau — o degrau é cinto para o legado; venda nova nasce com `sale_date`
    (`event_ops.resolver_data_da_venda`).

    Returns:
        Expressão SQLAlchemy `coalesce(payable_from, sale_date, date(created_at))`.
    """
    return db.func.coalesce(
        CommissionPayment.payable_from,
        CommissionPayment.sale_date,
        db.func.date(CommissionPayment.created_at),
    )



# ── Predicados únicos (feature 306) ───────────────────────────────────────────────────────────


def filtro_estorno_orfao():
    """O estorno órfão: `a_pagar`, negativo, sem evento e ligado a uma paga (`original_id`).

    É o que a exclusão de um evento já pago deixa (`aplicar_estorno_comissao`), e o único que o
    resgate do mês corrente traz: o ajuste do cancelado continua ligado ao evento e entra pelo
    ciclo dele.
    """
    return db.and_(
        CommissionPayment.status == "a_pagar",
        CommissionPayment.amount < 0,
        CommissionPayment.event_id.is_(None),
        CommissionPayment.original_id.isnot(None),
    )


def _e_estorno_orfao(cp: CommissionPayment) -> bool:
    return (
        cp.status == "a_pagar"
        and Decimal(cp.amount or 0) < 0
        and cp.event_id is None
        and cp.original_id is not None
    )


def linha_abre_ciclo(cp: CommissionPayment | None = None):
    """A linha que mantém o ciclo aberto: `a_pagar`, valor ≠ 0 e não órfã (R5).

    Sem argumento, devolve a expressão SQL; com a linha, o mesmo juízo em Python. O verify confere
    os dois em toda linha do espelho. Só `primeiro_repasse_aberto` a usa.
    """
    if cp is None:
        return db.and_(
            CommissionPayment.status == "a_pagar",
            CommissionPayment.amount != 0,
            db.not_(filtro_estorno_orfao()),
        )
    return cp.status == "a_pagar" and Decimal(cp.amount or 0) != 0 and not _e_estorno_orfao(cp)


TIPO_COMISSAO = "comissao"
TIPO_AJUSTE = "ajuste"
TIPO_ESTORNO = "estorno"


def tipo_da_linha(cp: CommissionPayment) -> tuple[str, str | None]:
    """O que a linha é — comissão, ajuste ou estorno — e o motivo pelo prefixo da nota (FR-033).

    Pelo vínculo (data-model §7.3): estorno é a linha sem evento ligada a uma paga, em qualquer
    status e sinal (o resgate do mês é que olha só o órfão a pagar); ajuste é a ligada a uma paga
    que continua no evento; o resto é comissão. O motivo é o código de `MOTIVOS_AJUSTE_COMISSAO`
    cujo prefixo abre a nota.
    """
    from app.constants import MOTIVOS_AJUSTE_COMISSAO

    nota = cp.notes or ""
    motivo = next((cod for pref, cod in MOTIVOS_AJUSTE_COMISSAO.items() if nota.startswith(pref)), None)
    if cp.event_id is None and cp.original_id is not None:
        return TIPO_ESTORNO, motivo
    if cp.original_id is not None:
        return TIPO_AJUSTE, motivo
    return TIPO_COMISSAO, motivo


def ciclo_de_pagamento_da_linha(cp: CommissionPayment) -> date | None:
    """Espelho em Python de `ciclo_de_pagamento_expr()`: `payable_from`, `sale_date`, `created_at`.

    O terceiro degrau é a data de `created_at` em **UTC** (a coluna é `utcnow`), exatamente como o
    `date()` do SQL — converter para São Paulo aqui faria as duas contas divergirem depois das 21h.
    """
    if cp.payable_from is not None:
        return cp.payable_from
    if cp.sale_date is not None:
        return cp.sale_date
    return cp.created_at.date() if cp.created_at is not None else None

def liquidar_periodo(
    seller_id: int, p_start: date, p_end: date, target: str, *, linhas: str = "abertas"
) -> list[CommissionPayment]:
    """Aplica `status`/`paid_at` às comissões de um vendedor no ciclo (feature 267).

    Fonte única das quatro liquidações que existiam duplicadas linha a linha (controle
    individual e em lote, cada um com seu gêmeo Jinja). **Não commita e não audita** — as duas
    coisas dependem do request (`current_user`) e ficam nas rotas.

    Hotfix 267c: o lote mexe só nas linhas **abertas** (`a_pagar`, `no_banco`). Antes pegava
    também as pagas — o "Não pago" de um item misto devolvia a "a pagar" o que já tinha sido
    pago, a ressincronização recalculava pela venda de hoje, e o vendedor aparecia devendo o
    valor cheio. Linha paga só sai de `pago` por `linhas="pagas"`, que é o desfazer do
    Superadmin (`liquidar_item_de_comissao`). As linhas são travadas (`with_for_update`): dois
    cliques simultâneos não se cruzam.

    Args:
        seller_id: vendedor cujo lote está sendo liquidado.
        p_start: primeiro dia do ciclo (inclusive).
        p_end: primeiro dia do mês seguinte (exclusive).
        target: ``"pago"``, ``"no_banco"`` ou ``"a_pagar"``.
        linhas: ``"abertas"`` (o lote) ou ``"pagas"`` (o desfazer de pagamento).

    Returns:
        As linhas afetadas (para a rota montar a mensagem de auditoria).
    """
    ciclo = ciclo_de_pagamento_expr()
    # `no_banco` faz parte do conjunto liquidável aqui, diferente de `_month_scoped_query`
    # (que é leitura do módulo de Comissões). Não unificar sem medir: muda o que o lote pega.
    status = ["pago"] if linhas == "pagas" else ["a_pagar", "no_banco"]
    rows = (
        CommissionPayment.query.filter(
            CommissionPayment.seller_id == seller_id,
            ciclo >= p_start,
            ciclo < p_end,
            CommissionPayment.status.in_(status),
        )
        .order_by(CommissionPayment.id)
        .with_for_update()
        .all()
    )
    for c in rows:
        c.status = target
        # `now_sp()`, nunca `date.today()`: produção roda em UTC e depois das 21h de Brasília o
        # pagamento seria carimbado no dia seguinte.
        c.paid_at = now_sp().date() if target == "pago" else None
    return rows


#: Sufixo do item da Planilha que reúne as linhas JÁ PAGAS de um vendedor no ciclo (hotfix 267c):
#: `"<vendedor>:<AAAA-MM>"` é o aberto; `"<vendedor>:<AAAA-MM>:pago"` é o pago, separado.
SUFIXO_ITEM_PAGO = "pago"


class LiquidacaoRecusada(Exception):
    """O pedido de mudar a situação de um item de comissão não pode ser atendido (hotfix 267c)."""

    def __init__(self, mensagem: str, status: int) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def partir_item_de_comissao(item_id: str) -> tuple[int, date, date, bool] | None:
    """`"12:2026-05"` / `"12:2026-05:pago"` → `(vendedor, início, fim exclusivo, é o item pago)`."""
    partes = str(item_id).split(":")
    if len(partes) not in (2, 3) or (len(partes) == 3 and partes[2] != SUFIXO_ITEM_PAGO):
        return None
    try:
        seller_id = int(partes[0])
        ano, mes = int(partes[1][:4]), int(partes[1][5:7])
        inicio = date(ano, mes, 1)
    except (ValueError, IndexError):
        return None
    fim = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)
    return seller_id, inicio, fim, len(partes) == 3


def liquidar_item_de_comissao(
    item_id: str,
    status: str,
    *,
    eh_superadmin: bool,
    motivo: str = "",
    actor_name: str = "",
) -> tuple[list[CommissionPayment], str]:
    """Muda a situação de um item de comissão da Planilha — as quatro portas chamam esta.

    Hotfix 267c. No item **aberto**, o lote mexe só no que não foi pago (`liquidar_periodo`).
    No item **pago**, só existe uma saída: o Superadmin desfazer um pagamento marcado por engano,
    pelo "Não pago", com o motivo (1e-Q5 = A). O motivo vai ao histórico de cada evento; o
    valor que estava pago e o lote chegam com a 1e (precisam de coluna). Não commita.

    Args:
        item_id: o id do item na Planilha.
        status: ``"pago"``, ``"no_banco"`` ou ``"nao_pago"`` (qualquer outro vira ``a_pagar``).
        eh_superadmin: quem pede é Superadmin (só ele desfaz pagamento).
        motivo: obrigatório para desfazer.
        actor_name: nome de quem pede, para o histórico do evento.

    Returns:
        `(linhas afetadas, situação gravada)`.

    Raises:
        LiquidacaoRecusada: id inválido (400), "No banco" num pago (409), desfazer sem ser
            Superadmin (403) ou sem motivo (400).
    """
    partes = partir_item_de_comissao(item_id)
    if partes is None:
        raise LiquidacaoRecusada("Status inválido para este item", 400)
    seller_id, inicio, fim, eh_pago = partes
    target = status if status in ("pago", "no_banco") else "a_pagar"
    if not eh_pago:
        return liquidar_periodo(seller_id, inicio, fim, target), target
    if target == "pago":
        return [], target
    if target == "no_banco":
        raise LiquidacaoRecusada(
            "Comissão já paga não volta para 'No banco'. Para desfazer um pagamento marcado por "
            "engano, o Superadmin usa 'Não pago' e informa o motivo.",
            409,
        )
    if not eh_superadmin:
        raise LiquidacaoRecusada("Só o Superadmin desfaz um pagamento de comissão.", 403)
    motivo = (motivo or "").strip()
    if not motivo:
        raise LiquidacaoRecusada(
            "Informe o motivo — desfazer é só para pagamento marcado por engano.", 400
        )
    # Feature 306 (Travas): os eventos das linhas primeiro (`ORDER BY id FOR UPDATE`), depois as
    # linhas. Na ordem de antes (linhas, e o `EventLog` pedindo KEY SHARE no evento), o desfazer
    # fechava ciclo com o ato, que trava o evento e depois as linhas.
    ciclo = ciclo_de_pagamento_expr()
    eventos = [
        eid
        for (eid,) in db.session.query(CommissionPayment.event_id)
        .filter(
            CommissionPayment.seller_id == seller_id,
            ciclo >= inicio,
            ciclo < fim,
            CommissionPayment.status == "pago",
            CommissionPayment.event_id.isnot(None),
        )
        .distinct()
        .all()
    ]
    if eventos:
        (
            db.session.query(CalendarEvent.id)
            .filter(CalendarEvent.id.in_(eventos))
            .order_by(CalendarEvent.id)
            .with_for_update()
            .all()
        )
    rows = liquidar_periodo(seller_id, inicio, fim, "a_pagar", linhas="pagas")
    from app.models import EventLog

    for c in rows:
        if c.event_id is not None:
            db.session.add(
                EventLog(
                    event_id=c.event_id,
                    actor_name=actor_name or "—",
                    actor_role="Superadmin",
                    message=f"Desfez o pagamento da comissão (R$ {c.amount}) — motivo: {motivo}",
                    created_at=now_sp(),
                )
            )
    return rows, target


#: Status de comissão que representam dinheiro vivo (o que será ou já foi pago). `cancelado`
#: fica de fora: é linha anulada (sem comissão elegível, excedente da reconciliação ou evento
#: excluído), sem movimentação. A linha do evento cancelado continua viva, com o retido (306).
_STATUS_VIVOS = ("a_pagar", "no_banco", "pago")


def comissao_exibida_do_evento(event, settings) -> tuple[Decimal, str]:
    """Comissão a exibir no detalhe do evento, e de onde ela veio (feature 267).

    Existia em duas cópias divergentes — `_compute_kpi` (API) e a view Jinja `event_detail` —,
    ambas com 2% flat sobre venda−BV. Isso ignora EducaManto (5% sobre o LUCRO), a Loja Virtual
    (que não comissiona) e `receives_commission`: a tela do evento mostrava um número que o
    Financeiro nunca ia pagar.

    Três camadas, nesta ordem:

    1. **Evento cancelado → 0.** A comissão do cancelado é a do retido e mora no resumo
       (`cancel_ops.resumo_cancelado`); as linhas continuam ligadas ao evento e se acertam pela
       reconciliação (feature 306). Sem esta guarda, o fallback inventaria a comissão cheia de
       uma venda que não houve. A regra canônica sozinha NÃO protege: quem checa cancelamento é
       a sincronização, não o cálculo.
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

    from app.constants import NOTA_COMISSAO_PROPRIA_DO_DIA

    # Feature 306 (P-51): a comissão própria do novo 1º dia, marcada na passagem, fica fora da venda.
    linhas = [
        c
        for c in event.commission_payments
        if c.status in _STATUS_VIVOS and NOTA_COMISSAO_PROPRIA_DO_DIA not in (c.notes or "")
    ]
    if linhas:
        total = sum((Decimal(c.amount) for c in linhas), Decimal("0"))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "linha"

    return _event_commission(event, settings), "estimativa"


def _month_scoped_query(start: date, end: date, seller_id: int | None = None):
    """Query base: comissões cujo `sale_date` cai no mês, ou sem `sale_date` mas criadas no
    mês (mesma regra de `api_financeiro_comissoes`).

    Feature 306: `no_banco` entra. É dinheiro já separado para o vendedor, e a tela que o deixava
    de fora não fechava com a Planilha, que sempre o mostrou.
    """
    q = CommissionPayment.query.filter(
        CommissionPayment.status.in_(_STATUS_VIVOS),
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
    """Estornos órfãos pendentes (`filtro_estorno_orfao`), sem filtro de mês.

    O estorno de antes da feature 306 herdou o `sale_date` da venda original, que costuma cair
    num mês já quitado — sem esta consulta ele ficaria invisível e nunca seria descontado
    (feature 187). O de agora já nasce no primeiro repasse aberto (FR-036). Quem chama é que
    decide **onde** exibi-lo: hoje só no mês corrente, via `_estornos_do_mes` — trazê-lo para
    todos os meses fazia o mesmo estorno reaparecer em cada tela e derrubar o total de meses que
    não tinham nada com ele.

    Feature 306: só o **órfão** (sem evento, ligado a uma paga), o que a exclusão deixa. O ajuste
    do cancelado continua ligado ao evento e nasce no primeiro repasse aberto: entra pelo ciclo
    dele, e resgatá-lo aqui o mostraria duas vezes.
    """
    q = CommissionPayment.query.filter(filtro_estorno_orfao())
    if seller_id is not None:
        q = q.filter(CommissionPayment.seller_id == seller_id)
    q = _sem_loja_virtual(q)
    return q.order_by(CommissionPayment.created_at.asc())


def _to_entry(cp: CommissionPayment, cancelados: set[int] | frozenset[int] = frozenset()) -> CommissionEntry:
    tipo, motivo = tipo_da_linha(cp)
    ciclo = ciclo_de_pagamento_da_linha(cp)
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
        tipo=tipo,
        original_id=cp.original_id,
        evento_cancelado=cp.event_id in cancelados,
        ciclo=ciclo.strftime("%Y-%m") if ciclo else None,
        motivo=motivo,
    )


def _eventos_cancelados(cps: list[CommissionPayment]) -> set[int]:
    """Os eventos cancelados entre os das linhas, numa consulta só (sem N+1)."""
    ids = {cp.event_id for cp in cps if cp.event_id is not None}
    if not ids:
        return set()
    return {
        eid
        for (eid,) in db.session.query(CalendarEvent.id)
        .filter(CalendarEvent.id.in_(ids), CalendarEvent.cancelled_at.isnot(None))
        .all()
    }


def _to_entries(cps: list[CommissionPayment]) -> list[CommissionEntry]:
    cancelados = _eventos_cancelados(cps)
    return [_to_entry(cp, cancelados) for cp in cps]


def _estornos_do_mes(month: str, seller_id: int | None) -> list[CommissionPayment]:
    """Estornos pendentes que entram na conta do mês pedido — só no **mês corrente**.

    Um estorno é uma dívida do vendedor com a empresa, e ela é abatida no próximo repasse: o
    lugar dele é o mês que está aberto, não todo mês do histórico. Enquanto ele aparecia em
    todos, um estorno de julho derrubava também o total de abril — meses que não tinham nada a
    ver com ele — e a mesma linha reaparecia em cada tela, parecendo comissão ressuscitada.

    O estorno não se perde: fica no mês corrente até ser liquidado. E o mês do `sale_date` dele
    continua mostrando-o pela via normal (`_month_scoped_query`): no estorno de antes da feature
    306, o mês da venda estornada; no de agora, o do primeiro repasse aberto (FR-036).

    Feature 306: só o estorno **órfão** (`filtro_estorno_orfao`, o da exclusão). O ajuste do
    cancelado nasce no primeiro repasse aberto, ligado ao evento, e entra pelo ciclo dele.
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
    return _to_entries(_com_estornos(rows, month_ref, seller_id))


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
                CommissionPayment.status.in_(_STATUS_VIVOS),
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
            .filter(filtro_estorno_orfao())
            .distinct()
        }
        seller_ids = sorted(month_ids | reversal_ids)

    rows: list[CommissionMonthSummaryRow] = []
    for sid in seller_ids:
        cps = _seller_payable_rows(month, sid)
        if not cps:
            continue
        entries = _to_entries(cps)
        total_amount = sum((e.amount for e in entries), Decimal("0"))
        pending_amount = sum(
            (e.amount for e in entries if e.status == "a_pagar"), Decimal("0")
        )
        # Feature 306: "pendente" é ter linha a pagar com valor, mesmo que o mês some zero (−100 do
        # ajuste e +100 de outra venda): pela soma, o "Pagar Mês" sumia com as duas abertas. O
        # estorno órfão conta. Venda é linha sem `original_id`: o ajuste não é venda nova.
        tem_a_pagar = any(e.status == "a_pagar" and e.amount != 0 for e in entries)
        rows.append(
            CommissionMonthSummaryRow(
                seller_id=sid,
                seller_name=entries[0].seller_name,
                sale_count=sum(1 for e in entries if e.original_id is None),
                total_amount=total_amount,
                pending_amount=pending_amount,
                month_status="pendente" if tem_a_pagar else "pago",
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
    total_no_banco = sum(
        (e.amount for r in rows for e in r.entries if e.status == "no_banco"), Decimal("0")
    )
    total_pending = sum((r.pending_amount for r in rows), Decimal("0"))
    return CommissionKpis(
        total_month=total_paid + total_no_banco + total_pending,
        total_paid=total_paid,
        total_pending=total_pending,
        total_no_banco=total_no_banco,
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
            .order_by(CommissionPayment.id)
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
# cachês) e o resto sobre a venda, BV sempre sai da base, evento cancelado comissiona só o retido
# (`comissao_do_retido`, pela reconciliação do ato — nenhuma sincronização a reescreve), custo
# de líder de grupo agrega os satélites vivos (o dia cancelado fica fora), e comissão já paga
# nunca é reescrita.
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
    """Custo de cachês do evento, somando os satélites quando for principal de grupo (FR-011).

    Feature 306: sem o dia cancelado — o corte já tirou o dia da venda do grupo, e o cachê dele
    não pesa mais na base da comissão EducaManto nem no CPV (a mesma régua de `dias_vivos`).
    """
    total = _event_cost(event)
    for satellite in event.satellites:
        if not satellite.is_cancelled:
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


def _taxa_da_comissao(event, settings) -> Decimal:
    """A taxa que a comissão do evento usa hoje: a do evento; senão a padrão; no EducaManto com
    responsável, a do evento ou a de Configurações (feature 109; FR-029 da 306)."""
    if event.is_educamanto and _educamanto_responsavel(settings) is not None:
        if event.commission_rate is not None:
            return Decimal(str(event.commission_rate))
        return _educamanto_commission_rate(settings)
    return _get_commission_rate(event, settings)


def _base_da_comissao(
    event,
    settings,
    *,
    venda: Decimal | None = None,
    taxa: Decimal | None = None,
    bv_total: Decimal | None = None,
    custo: Decimal | None = None,
) -> Decimal:
    """Camada 1 da comissão cheia (feature 306, P1): o corpo de sempre de `_event_commission`.

    Sem as sobreposições, o número é o de hoje — é o que os oito consumidores de
    `_event_commission` leem, e o cenário 1 confere `main` × branch em todo evento do espelho. As
    sobreposições servem ao cancelado, que congela a venda, a taxa, o BV e o custo no ato e nunca
    relê a venda viva (data-model §8.3).

    Args:
        event: o evento.
        settings: `SiteSetting` (taxa padrão e responsável EducaManto).
        venda: a venda a usar no lugar de `event.sale_value`.
        taxa: a taxa (%) no lugar da do evento ou da padrão.
        bv_total: o BV no lugar de `_event_bv_total(event)`.
        custo: no EducaManto com responsável, o custo de cachês no lugar do lido ao vivo.

    Returns:
        A comissão em `Decimal`, com duas casas (ROUND_HALF_UP), nunca negativa.
    """
    sale_value = event.sale_value if venda is None else venda
    if not sale_value:
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
    bv = _event_bv_total(event) if bv_total is None else Decimal(str(bv_total))
    rate = Decimal(str(taxa)) if taxa is not None else _taxa_da_comissao(event, settings)
    if event.is_educamanto and _educamanto_responsavel(settings) is not None:
        # Comissão EducaManto (feature 109): 5% sobre o LUCRO (venda − BV − cachês).
        if custo is None:
            custo = _group_cost(event) if event.is_group_leader else _event_cost(event)
        base = Decimal(sale_value) - bv - Decimal(custo)
    else:
        # BV sai da base de comissão (repasse, não é receita comissionável) — feature 099.
        base = Decimal(sale_value) - bv
    if base < 0:
        base = Decimal("0")
    return (base * rate / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _event_commission(event, settings) -> Decimal:
    """A comissão do evento como sempre foi: casca da `_base_da_comissao`, sem sobreposição."""
    return _base_da_comissao(event, settings)


def _beneficiario_comissionado(event, settings) -> User | None:
    """Quem recebe a comissão do evento, ou `None` quando ninguém recebe (feature 306).

    Extraído do `should_have` de `_sync_commission_payment`, sem olhar o cancelamento: Loja
    Virtual, evento sem beneficiário, beneficiário que não comissiona (`receives_commission`) e
    cortesia ou permuta recusam. É o portão da comissão cheia do cancelado (P1).
    """
    from app.financeiro.vendas_ops import is_loja_virtual

    if is_loja_virtual(event):
        return None
    if event.is_cortesia_permuta:
        return None
    beneficiary = _commission_beneficiary(event, settings)
    if beneficiary is None or not beneficiary.receives_commission:
        return None
    return beneficiary


def comissao_cheia_do_evento(
    event,
    settings,
    *,
    venda: Decimal | None = None,
    taxa: Decimal | None = None,
    bv_total: Decimal | None = None,
    custo: Decimal | None = None,
) -> tuple[Decimal, int | None, Decimal]:
    """Camada 2 da comissão cheia (feature 306, FR-027): o portão do beneficiário e a base.

    É o que o cancelamento congela em `commission_full`: 0,00 quando ninguém comissiona
    (cortesia com valor, evento sem vendedor, beneficiário sem comissão, Loja Virtual — cenário
    16b), senão a `_base_da_comissao` com as sobreposições do ato.

    Returns:
        `(cheia, beneficiario_id, taxa_usada)`: a cheia ao centavo, o id de quem recebe (ou
        `None`) e a taxa em % que a conta usou.
    """
    taxa_usada = Decimal(str(taxa)) if taxa is not None else _taxa_da_comissao(event, settings)
    beneficiario = _beneficiario_comissionado(event, settings)
    if beneficiario is None:
        return Decimal("0.00"), None, taxa_usada
    cheia = _base_da_comissao(
        event, settings, venda=venda, taxa=taxa_usada, bv_total=bv_total, custo=custo
    )
    return cheia, beneficiario.id, taxa_usada


def cheia_do_congelado(event, *, venda, taxa, bv_total, custo) -> Decimal:
    """A cheia do cancelado pelos insumos congelados, sem reler o portão vivo (feature 306, FR-049).

    É a `_base_da_comissao` com tudo congelado: a venda, a taxa, o BV das linhas e o custo do ato.
    A fórmula EducaManto (sobre o lucro) vale quando o ato congelou o custo (`custo` não nulo, o
    EducaManto com responsável no ato) — nunca pelo responsável de hoje — e o `receives_commission`
    de hoje não é relido: quem recebe é o beneficiário congelado. A cortesia fica com quem chama.
    """
    venda_d = Decimal(str(venda or 0))
    if venda_d <= 0:
        return Decimal("0.00")
    base = venda_d - Decimal(str(bv_total or 0))
    if custo is not None:
        base -= Decimal(str(custo))
    if base < 0:
        base = Decimal("0")
    return (base * Decimal(str(taxa or 0)) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def comissao_do_retido(cheia, retido, venda) -> Decimal:
    """A comissão na proporção do que a Manto reteve: `cheia × retido ÷ venda` (FR-028).

    Pela mesma conta de `bv_que_acompanha` (a do BV do retido), para as duas proporções não
    divergirem na tolerância de R$ 0,01: retido a um centavo da venda conta como a venda inteira.
    Teto na cheia; 0,00 quando venda, retido ou cheia ≤ 0.
    """
    from app.orcamento.quote_ops import bv_que_acompanha

    cheia_d, retido_d, venda_d = (Decimal(str(x or 0)) for x in (cheia, retido, venda))
    if cheia_d <= 0 or retido_d <= 0 or venda_d <= 0:
        return Decimal("0.00")
    return min(cheia_d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
               bv_que_acompanha(cheia_d, retido_d, venda_d))


def _valor_chegou_depois(event: CalendarEvent, hoje: date) -> bool:
    """O valor da venda chegou depois (feature 299, R45, decisão do dono no analyze).

    É o evento cadastrado num mês anterior ao corrente E com a data da venda também num mês
    anterior — o lançado com "Valor a definir" (ou com R$ 0,01) que ganha o valor semanas depois. A
    venda lançada agora com a data de um mês anterior (a virada do mês) NÃO é: o ciclo dela segue a
    data da venda, como sempre. Sem data da venda, nunca.

    `created_at` é UTC ingênuo (`default=datetime.utcnow`): o mês é tirado no fuso de São Paulo.
    """
    from datetime import UTC

    from app.constants import TZ_SP

    if not event.sale_date or not event.created_at:
        return False
    cadastro = event.created_at.replace(tzinfo=UTC).astimezone(TZ_SP).date()
    mes_corrente = (hoje.year, hoje.month)
    return (cadastro.year, cadastro.month) < mes_corrente and (
        event.sale_date.year,
        event.sale_date.month,
    ) < mes_corrente


def _ciclo_marcado_pela_299(existing: CommissionPayment) -> bool:
    """A data de ciclo gravada na linha foi posta pela regra do valor que chegou depois (R45).

    A marca é explícita (`NOTA_CICLO_VALOR_TARDIO` nas notas) porque a data sozinha não diz de onde
    veio: a EducaManto também grava `payable_from` (o dia do evento), e a linha que sai da
    EducaManto cai no ramo comum com essa data. Adivinhar pela data do evento e pelo vendedor
    errava para os dois lados (terceira convergência, T067).

    Args:
        existing: A linha de comissão viva.

    Returns:
        True quando a data é da 299 e deve ficar.
    """
    from app.constants import NOTA_CICLO_VALOR_TARDIO

    return NOTA_CICLO_VALOR_TARDIO in (existing.notes or "")


def _com_marca_do_ciclo(notes: str | None) -> str:
    """As notas da linha com a marca do ciclo da 299, sem repeti-la."""
    from app.constants import NOTA_CICLO_VALOR_TARDIO

    if NOTA_CICLO_VALOR_TARDIO in (notes or ""):
        return notes or ""
    return f"{notes} | {NOTA_CICLO_VALOR_TARDIO}" if notes else NOTA_CICLO_VALOR_TARDIO


def _sem_marca_do_ciclo(notes: str | None) -> str | None:
    """As notas da linha sem a marca do ciclo da 299.

    O ramo EducaManto regrava `payable_from` com o dia do evento: a marca, que diz "esta data é da
    299", deixaria de ser verdade, e na volta ao ramo comum a data da EducaManto ficaria (T071).
    """
    from app.constants import NOTA_CICLO_VALOR_TARDIO

    if not notes or NOTA_CICLO_VALOR_TARDIO not in notes:
        return notes
    partes = [p.strip() for p in notes.split("|")]
    return " | ".join(p for p in partes if p and p != NOTA_CICLO_VALOR_TARDIO) or None


def _ciclo_da_comissao_comum(
    event: CalendarEvent, existing: CommissionPayment | None, amount: Decimal
) -> date | None:
    """`payable_from` da comissão comum (feature 299, R22/R42/R45).

    - Comissão que NASCE agora (linha nova, ou a de R$ 0,00 da venda simbólica ganhando valor real)
      com o valor chegando depois → hoje: entra no ciclo do mês em que o valor foi posto, nunca num
      mês já fechado. A data da venda não muda, e a linha ganha a marca do ciclo.
    - A data marcada nunca volta a `None` nas sincronizações seguintes (antes voltava).
    - Data gravada sem a marca veio da EducaManto: no ramo comum volta a `None`, como antes da 299.
    - Fora isso, `None`: o ciclo segue a data da venda, como sempre.
    """
    from app.constants import now_sp

    if existing is not None and existing.payable_from is not None:
        return existing.payable_from if _ciclo_marcado_pela_299(existing) else None
    nasce_agora = existing is None or (not existing.amount and amount > 0)
    hoje = now_sp().date()
    return hoje if nasce_agora and _valor_chegou_depois(event, hoje) else None


def _comissao_existente(event_id: int, *, ignorar_zero_pago: bool) -> CommissionPayment | None:
    """A linha de comissão viva do evento: a mais recente, fora as canceladas.

    Feature 299 (R42): havendo comissão de verdade a pagar agora, a linha de R$ 0,00 JÁ PAGA de
    uma venda simbólica não conta — pagar zero não é pagar, e a comissão nasce quando o valor real
    entra. Quando a comissão calculada também é zero (taxa 0%), a paga continua valendo: sem isso,
    cada pagamento abriria uma linha nova de R$ 0,00. O corte vai NA CONSULTA, com ordem por id:
    testar depois do `.first()` pegaria a paga de novo a cada sincronização (inclusive a de
    `_resync_pending_commissions`) e criaria uma `a_pagar` por vez.

    Feature 306: o ajuste ligado a uma paga (`original_id`) não é a comissão do evento, e a
    comissão própria do novo principal, marcada na passagem da venda (`NOTA_COMISSAO_PROPRIA_DO_DIA`,
    P-29), também não: sem os dois cortes, a sincronização regravaria o ajuste com a comissão cheia.

    Args:
        event_id: O evento.
        ignorar_zero_pago: A comissão calculada agora é maior que zero.

    Returns:
        A linha, ou ``None`` quando a comissão ainda não existe.
    """
    consulta = CommissionPayment.query.filter_by(event_id=event_id).filter(
        CommissionPayment.status != "cancelado",
        CommissionPayment.original_id.is_(None),
        _sem_marca_propria(),
    )
    if ignorar_zero_pago:
        zero_ja_pago = CommissionPayment.status.in_(("pago", "no_banco")) & (
            CommissionPayment.amount == 0
        )
        consulta = consulta.filter(~zero_ja_pago)
    return consulta.order_by(CommissionPayment.id.desc()).first()


# ── Reconciliação do cancelado por beneficiário (feature 306, R5, data-model §7.3) ────────────

_TETO_DE_CICLOS = 24


def _inicio_do_mes(d: date) -> date:
    return d.replace(day=1)


def _mes_seguinte(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _mes_anterior(d: date) -> date:
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def _linhas_do_ciclo(seller_id: int, inicio: date, *, excluir_event_id: int | None):
    """As linhas do beneficiário cujo ciclo (`ciclo_de_pagamento_expr`) cai no mês de `inicio`."""
    ciclo = ciclo_de_pagamento_expr()
    consulta = CommissionPayment.query.filter(
        CommissionPayment.seller_id == seller_id,
        CommissionPayment.status != "cancelado",
        ciclo >= inicio,
        ciclo < _mes_seguinte(inicio),
    )
    if excluir_event_id is not None:
        consulta = consulta.filter(
            db.or_(CommissionPayment.event_id.is_(None), CommissionPayment.event_id != excluir_event_id)
        )
    return consulta


def _ciclo_tem_linha(seller_id: int, inicio: date, *, excluir_event_id: int | None) -> bool:
    return db.session.query(
        _linhas_do_ciclo(seller_id, inicio, excluir_event_id=excluir_event_id).exists()
    ).scalar()


def _ciclo_aberto(seller_id: int, inicio: date, *, excluir_event_id: int | None) -> bool:
    return db.session.query(
        _linhas_do_ciclo(seller_id, inicio, excluir_event_id=excluir_event_id)
        .filter(linha_abre_ciclo())
        .exists()
    ).scalar()


def _ciclo_liquidado(seller_id: int, inicio: date, *, excluir_event_id: int | None) -> bool:
    """Liquidado = o beneficiário tem linha no ciclo e nenhuma o mantém aberto."""
    return _ciclo_tem_linha(seller_id, inicio, excluir_event_id=excluir_event_id) and not _ciclo_aberto(
        seller_id, inicio, excluir_event_id=excluir_event_id
    )


def primeiro_repasse_aberto(
    seller_id: int, hoje: date, *, excluir_event_id: int | None = None, travar: bool = False
) -> date:
    """A data da linha nova de ajuste: o primeiro repasse ainda aberto do beneficiário (FR-031, R5).

    - Nos dias 1 a `DIA_DO_REPASSE`, o mês anterior, se ali o beneficiário ainda tem linha que
      abre ciclo (o repasse do dia 5 ainda não saiu);
    - senão o mês corrente, se não está liquidado;
    - senão o seguinte, até 24 ciclos; sem achar, o 25º (futuro: nunca reabre um liquidado).

    A data é `hoje` presa ao intervalo do ciclo (o último dia do mês anterior, `hoje` ou o dia 1 de
    um mês futuro): é o único arranjo em que a Planilha (`coalesce`) e Comissões (`sale_date`)
    mostram o mesmo. `excluir_event_id` tira as linhas do próprio evento, para a prévia não
    divergir da execução pelo autoflush; `travar` trava antes as linhas abertas do beneficiário
    (`ORDER BY id FOR UPDATE`), para a correção comercial do cancelado.
    """
    from app.constants import DIA_DO_REPASSE

    if travar:
        (
            CommissionPayment.query.filter(
                CommissionPayment.seller_id == seller_id,
                CommissionPayment.status.in_(("a_pagar", "no_banco")),
            )
            .order_by(CommissionPayment.id)
            .with_for_update()
            .populate_existing()
            .all()
        )
    corrente = _inicio_do_mes(hoje)
    anterior = _mes_anterior(corrente)
    if hoje.day <= DIA_DO_REPASSE and _ciclo_aberto(seller_id, anterior, excluir_event_id=excluir_event_id):
        return _mes_seguinte(anterior) - timedelta(days=1)
    ciclo = corrente
    for _ in range(_TETO_DE_CICLOS):
        if not _ciclo_liquidado(seller_id, ciclo, excluir_event_id=excluir_event_id):
            return hoje if ciclo == corrente else ciclo
        ciclo = _mes_seguinte(ciclo)
    return ciclo


def _sem_marca_propria():
    """Fora a comissão própria do novo principal na passagem (P-29, P-51)."""
    from app.constants import NOTA_COMISSAO_PROPRIA_DO_DIA

    return db.or_(
        CommissionPayment.notes.is_(None),
        db.not_(CommissionPayment.notes.contains(NOTA_COMISSAO_PROPRIA_DO_DIA)),
    )


def _beneficiarios_com_linha_viva(event_ids: list[int]) -> set[int]:
    """Todo beneficiário com linha viva (a pagar, no banco ou paga) dos eventos.

    Gancho das provas por mutação (data-model §6.4): a reconciliação o chama pelo módulo, e é ele
    que dá alvo 0 a quem não está em `alvos` (FR-030).
    """
    if not event_ids:
        return set()
    return {
        sid
        for (sid,) in db.session.query(CommissionPayment.seller_id)
        .filter(
            CommissionPayment.event_id.in_(event_ids),
            CommissionPayment.status.in_(_STATUS_VIVOS),
            _sem_marca_propria(),
        )
        .distinct()
        .all()
        if sid is not None
    }


def _nota_do_ajuste(motivo: str, detalhe: str | None = None) -> str:
    """A nota da linha criada ou ajustada: o motivo como prefixo (FR-033). Gancho do verify."""
    return f"{motivo}: {detalhe}" if detalhe else motivo


def _nota_com_motivo(notas: str | None, motivo: str, detalhe: str | None) -> str:
    """Põe o motivo na frente das notas de uma linha ajustada no lugar, sem empilhar motivos."""
    from app.constants import MOTIVOS_AJUSTE_COMISSAO

    partes = [p.strip() for p in (notas or "").split(" | ") if p.strip()]
    partes = [p for p in partes if not any(p.startswith(pref) for pref in MOTIVOS_AJUSTE_COMISSAO)]
    return " | ".join([_nota_do_ajuste(motivo, detalhe), *partes])


def _reais(valor: Decimal) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


def reconciliar_comissao_do_cancelado(
    event: CalendarEvent,
    alvos: dict[int, Decimal],
    *,
    motivo: str,
    motivos: dict[int, str] | None = None,
    hoje: date | None = None,
    simular: bool = False,
) -> list[dict]:
    """Leva as linhas do evento ao alvo de cada beneficiário: Σ(a pagar + no banco + pago) = alvo.

    `alvos` é o congelado → comissão do retido; todo outro beneficiário com linha viva do evento
    recebe alvo 0 (FR-030). Por beneficiário, `falta = alvo − liquidadas` (pago + no banco):

    - falta 0 → toda `a_pagar` vira `cancelado` (nunca fica linha de R$ 0,00);
    - falta ≠ 0 → a `a_pagar` mais antiga recebe a falta no lugar, com a data intacta (FR-032), e
      as outras são canceladas;
    - sem `a_pagar` → linha nova (±) ligada à liquidada mais recente (`original_id`), datada no
      primeiro repasse aberto; a EducaManto positiva nova só LIBERA no dia do evento, se ele não
      passou (data-model §7.3): a data da venda é a do repasse, nunca herdada da venda (FR-031).

    Só as linhas do próprio evento, fora a comissão própria marcada (P-51). Com `simular=False`
    supõe a T4 tomada e não faz commit; com `simular=True` não toca o ORM. Devolve o plano, uma
    linha por mudança (`linha_id` quando a linha já existe), igual nos dois modos.

    Raises:
        ValueError: um motivo fora de `MOTIVOS_AJUSTE_COMISSAO`.
    """
    from app.constants import MOTIVOS_AJUSTE_COMISSAO, now_sp
    from app.utils import audit

    motivos = dict(motivos or {})
    for m in (motivo, *motivos.values()):
        if m not in MOTIVOS_AJUSTE_COMISSAO:
            raise ValueError(f"motivo de ajuste desconhecido: {m!r}")
    hoje = hoje or now_sp().date()
    settings = SiteSetting.query.get(1)
    edu_responsavel = _educamanto_responsavel(settings) if event.is_educamanto else None
    beneficiarios = sorted(
        {int(b) for b in alvos if b is not None} | _beneficiarios_com_linha_viva([event.id])
    )
    linhas = (
        CommissionPayment.query.filter(
            CommissionPayment.event_id == event.id,
            CommissionPayment.status.in_(_STATUS_VIVOS),
            _sem_marca_propria(),
        )
        .order_by(CommissionPayment.id)
        .all()
    )
    plano: list[dict] = []

    def entrada(cp: CommissionPayment | None, **campos) -> dict:
        base = {
            "linha_id": cp.id if cp is not None else None,
            "seller_id": cp.seller_id if cp is not None else None,
            "valor": Decimal(cp.amount) if cp is not None else None,
            "status": cp.status if cp is not None else None,
            "sale_date": cp.sale_date if cp is not None else None,
            "payable_from": cp.payable_from if cp is not None else None,
            "original_id": cp.original_id if cp is not None else None,
            "nota": cp.notes if cp is not None else None,
        }
        base.update(campos)
        return base

    for sid in beneficiarios:
        alvo = Decimal(str(alvos.get(sid) or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        motivo_b = motivos.get(sid, motivo)
        do_b = [cp for cp in linhas if cp.seller_id == sid]
        liquidadas = [cp for cp in do_b if cp.status in ("pago", "no_banco")]
        a_pagar = [cp for cp in do_b if cp.status == "a_pagar"]
        falta = alvo - sum((Decimal(cp.amount) for cp in liquidadas), Decimal("0.00"))
        canceladas = a_pagar if falta == 0 else a_pagar[1:]
        if falta != 0 and a_pagar:
            alvo_cp = a_pagar[0]
            if Decimal(alvo_cp.amount) != falta:
                detalhe = f"{_reais(Decimal(alvo_cp.amount))} → {_reais(falta)}"
                plano.append(entrada(alvo_cp, valor=falta, nota=_nota_com_motivo(alvo_cp.notes, motivo_b, detalhe)))
        elif falta != 0:
            original = max(liquidadas, key=lambda cp: cp.id) if liquidadas else None
            if (
                edu_responsavel is not None
                and sid == edu_responsavel.id
                and falta > 0
                and event.start_at is not None
                and event.start_at.date() >= hoje
            ):
                venda_em = primeiro_repasse_aberto(sid, hoje, excluir_event_id=event.id)
                liberacao = event.start_at.date()
            else:
                venda_em = liberacao = primeiro_repasse_aberto(sid, hoje, excluir_event_id=event.id)
            detalhe = f"acerta a linha #{original.id}" if original is not None else None
            plano.append(
                entrada(
                    None,
                    seller_id=sid,
                    valor=falta,
                    status="a_pagar",
                    sale_date=venda_em,
                    payable_from=liberacao,
                    original_id=original.id if original is not None else None,
                    nota=_nota_do_ajuste(motivo_b, detalhe),
                )
            )
        for cp in canceladas:
            plano.append(entrada(cp, status="cancelado", nota=_nota_com_motivo(cp.notes, motivo_b, "cancelada")))

    if simular:
        return plano
    for p in plano:
        if p["linha_id"] is None:
            cp = CommissionPayment(
                event_id=event.id,
                event_title=event.title,
                seller_id=p["seller_id"],
                sale_date=p["sale_date"],
                payable_from=p["payable_from"],
                amount=p["valor"],
                status="a_pagar",
                original_id=p["original_id"],
                notes=p["nota"],
            )
            db.session.add(cp)
            db.session.flush()
            p["linha_id"] = cp.id
            acao = f"criou {_reais(p['valor'])}"
        else:
            cp = db.session.get(CommissionPayment, p["linha_id"])
            antes = (Decimal(cp.amount), cp.status)
            cp.amount, cp.status, cp.notes = p["valor"], p["status"], p["nota"]
            acao = (
                f"cancelou {_reais(antes[0])}"
                if p["status"] == "cancelado"
                else f"{_reais(antes[0])} → {_reais(p['valor'])}"
            )
        audit("payment", "commission", cp.id, event.title, f"{p['nota']} ({acao})")
    return plano


def _reler_cancelamento(event: CalendarEvent) -> None:
    """Relê `cancelled_at` do banco, salvo quando a própria sessão acabou de mudá-lo."""
    from sqlalchemy import inspect as sa_inspect

    estado = sa_inspect(event)
    if estado.persistent and not estado.attrs.cancelled_at.history.has_changes():
        db.session.refresh(event, ["cancelled_at"])


def _reconciliar_ajuste_vivo(event: CalendarEvent, beneficiario: User, cheia: Decimal) -> bool:
    """A regra nova (b) da sincronização, no evento vivo; `True` quando reconciliou.

    Gancho das provas por mutação (data-model §6.4): o `_sync` o chama pelo módulo. O motivo é o do
    ajuste vivo (o corte de um dia, hoje), para a nota da base dizer de onde veio a mudança.
    """
    from app.constants import MOTIVO_AJUSTE_CORTE_DE_DIA, MOTIVOS_AJUSTE_COMISSAO

    ajuste = (
        CommissionPayment.query.filter(
            CommissionPayment.event_id == event.id,
            CommissionPayment.original_id.isnot(None),
            CommissionPayment.status.in_(_STATUS_VIVOS),
            _sem_marca_propria(),
        )
        .order_by(CommissionPayment.id)
        .first()
    )
    if ajuste is None:
        return False
    nota = ajuste.notes or ""
    motivo = next((m for m in MOTIVOS_AJUSTE_COMISSAO if nota.startswith(m)), MOTIVO_AJUSTE_CORTE_DE_DIA)
    reconciliar_comissao_do_cancelado(event, {beneficiario.id: cheia}, motivo=motivo)
    return True


def _sync_commission_payment(event: CalendarEvent) -> None:
    """Cria ou atualiza o CommissionPayment de um evento. Não faz commit."""
    # Loja Virtual não gera linha de comissão (feature 205, FR-054). O corte é aqui, na origem:
    # se a linha nunca nasce, nenhum relatório precisa lembrar de escondê-la depois.
    from app.financeiro.vendas_ops import is_loja_virtual

    if is_loja_virtual(event):
        return
    # Feature 306: a comissão do cancelado é a do retido, e só o ato e as correções a reconciliam
    # (`reconciliar_comissao_do_cancelado`); nenhuma sincronização a reescreve. O `cancelled_at` é
    # relido do banco: o evento pode ter sido lido antes do ato (cenário 30, "sync velho").
    _reler_cancelamento(event)
    if event.is_cancelled:
        return

    settings = SiteSetting.query.get(1)
    # O portão único do beneficiário (Loja Virtual, sem beneficiário, `receives_commission` falso,
    # cortesia ou permuta): o mesmo número de hoje no evento vivo.
    beneficiary = _beneficiario_comissionado(event, settings)
    should_have = bool(event.sale_value) and beneficiary is not None
    amount = _event_commission(event, settings) if should_have else 0
    is_edu_com_responsavel = event.is_educamanto and _educamanto_responsavel(settings) is not None
    # A linha de R$ 0,00 paga só deixa de contar na comissão comum: a EducaManto fica como antes da
    # 299 (sem mudança, T024/T061).
    existing = _comissao_existente(
        event.id, ignorar_zero_pago=amount > 0 and not is_edu_com_responsavel
    )

    if not should_have:
        if existing and existing.status == "a_pagar":
            existing.status = "cancelado"
            existing.notes = (existing.notes or "") + " | Cancelado: sem comissão elegível"
        return
    # Regra nova (b) (FR-057, cenário 38c): com um ajuste vivo no evento (o do corte de um dia) e a
    # base de volta a `a_pagar` (o "pago" desfeito pela 267c), regravar a base com a cheia somaria o
    # ajuste duas vezes. Reconcilia com alvo = cheia: a base absorve, e o ajuste é cancelado.
    if existing is not None and existing.status == "a_pagar":
        if _reconciliar_ajuste_vivo(event, beneficiary, Decimal(str(amount))):
            return

    # Comissão EducaManto (feature 109): só entra no ciclo de pagamento após a realização —
    # payable_from = data do evento. Comissão comum: ciclo pela sale_date, salvo o valor que chegou
    # depois (feature 299, `_ciclo_da_comissao_comum`).
    marcar_ciclo = False
    if is_edu_com_responsavel and event.start_at is not None:
        payable_from = event.start_at.date()
    else:
        payable_from = _ciclo_da_comissao_comum(event, existing, amount)
        # No ramo comum, data de ciclo só existe pela regra do valor que chegou depois: a linha leva
        # a marca, que é o que a mantém nas sincronizações seguintes (T067).
        marcar_ciclo = payable_from is not None
    if existing:
        if existing.status == "a_pagar":
            existing.amount = amount
            existing.sale_date = event.sale_date
            existing.event_title = event.title
            existing.seller_id = beneficiary.id
            existing.payable_from = payable_from
            # A marca acompanha a data: some quando a data deixa de ser a da 299 (T071).
            existing.notes = (
                _com_marca_do_ciclo(existing.notes)
                if marcar_ciclo
                else _sem_marca_do_ciclo(existing.notes)
            )
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
            notes=_com_marca_do_ciclo(None) if marcar_ciclo else None,
        ))


def _resync_pending_commissions() -> None:
    """Reconcilia as comissões A PAGAR com o cálculo atual do evento (mesma base da aba comercial).

    Evita divergência quando a taxa muda depois de a comissão ter sido registrada. Não altera
    comissões já pagas (histórico) nem linhas negativas (ajuste ou estorno).

    Feature 306 (Travas, item 4): percorre os eventos por id, cada um sob `FOR NO KEY UPDATE SKIP
    LOCKED`, relê `cancelled_at` e commita por evento. O evento que um ato (ou uma correção) tem
    travado fica para a próxima abertura da tela, em vez de a tela esperar o ato; e a trava dura
    só aquele evento, nunca os ~70 do GET inteiro.
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
    event_ids = sorted({cp.event_id for cp in pendentes})
    if not event_ids:
        return
    for eid in event_ids:
        ev = (
            CalendarEvent.query.filter(CalendarEvent.id == eid)
            .with_for_update(key_share=True, skip_locked=True)
            .populate_existing()
            .one_or_none()
        )
        if ev is not None:
            _sync_commission_payment(ev)
        db.session.commit()
