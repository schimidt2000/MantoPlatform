"""Núcleo do cancelamento de evento e da solicitação de exclusão (feature 224).

Existe porque apagar um evento que já recebeu dinheiro destrói a única prova de que o dinheiro
entrou: `_clear_event_side_tables` (`app/calendar/routes.py`) remove os `EventPayment` junto, e
depois disso não há a que a devolução se referir. Foi exatamente o que aconteceu com o
`(SHOW) PETER PAN...` em 07/08/2026, apagado pelo sync depois de sumir do Google Agenda.

A regra: evento **vazio** (sem venda, sem pagamento, sem contrato e sem elenco escalado) continua
sendo excluído de verdade — é o caso do evento criado por engano. Evento com qualquer uma dessas
coisas presa vira **cancelado**: o registro fica, some de toda métrica (via `cancelled_at`), e a
devolução ao cliente nasce vinculada a ele.

Funções puras no sentido do projeto: sem `flask.request`/`render_template`/`flash`. Os
adaptadores (`app/api/agenda_write.py`) é que traduzem em resposta HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app import db
from app.models import (
    CalendarEvent,
    CommissionPayment,
    EventContract,
    EventLog,
    EventPayment,
    EventRole,
    SpecialExpense,
    User,
)

TZ = ZoneInfo("America/Sao_Paulo")


class CancelValidationError(Exception):
    """Recusa de negócio do cancelamento e das correções do cancelado (features 224 e 306).

    A view a traduz numa linha só: `json_error(exc.message, exc.status, fields=exc.fields,
    codigo=exc.codigo, **exc.extras)`.

    Args:
        message: a frase da recusa.
        fields: todos os campos recusados de uma vez (`{campo: mensagem}`).
        field: atalho para `{field: message}`.
        status: 400 (forma) ou 409 (estado; vem com `codigo`).
        codigo: um `CODIGO_*` de `app.constants` (P18).
        **extras: os extras do envelope (`max_devolucao`, `dias`, `piso`, `teto`…); nunca `fields`.
    """

    def __init__(
        self,
        message: str,
        *,
        fields: dict[str, str] | None = None,
        field: str | None = None,
        status: int = 400,
        codigo: str | None = None,
        **extras: Any,
    ) -> None:
        super().__init__(message)
        if "fields" in extras:
            raise TypeError("`fields` vai no argumento próprio, não nos extras")
        self.message = message
        self.fields = fields if fields is not None else ({field: message} if field else None)
        self.status = status
        self.codigo = codigo
        self.extras = extras


class EventoCanceladoError(CancelValidationError):
    """A regra única do cancelado (FR-047): só o Superadmin real corrige dados de venda.

    Irmã de `EventoMarcadoError`. Sai como 409 `cancelado`; a exclusão de um cancelado também a
    levanta (o cancelado não se exclui, FR-021).
    """

    MENSAGEM = "Este evento está cancelado: só o Superadmin corrige os dados de venda."

    def __init__(self, message: str = MENSAGEM) -> None:
        from app.constants import CODIGO_EVENTO_CANCELADO

        super().__init__(message, status=409, codigo=CODIGO_EVENTO_CANCELADO)


class EventoMarcadoError(CancelValidationError):
    """Excluir um evento marcado "Sumiu do Google Agenda" (features 303 e 306).

    A feature 306 abriu o cancelamento do marcado (o ato desmarca antes de `cancelled_at`); a
    exclusão continua recusada, porque apagar destruiria o lastro do dinheiro. O texto mora aqui,
    uma vez: a API e o wrapper Jinja leem `exc.message`.
    """

    MENSAGEM = (
        "Este evento sumiu do Google Agenda e não se exclui: devolva-o ao Google Agenda ou "
        "cancele o evento."
    )

    def __init__(self, message: str = MENSAGEM) -> None:
        super().__init__(message)


def total_recebido(event: CalendarEvent) -> Decimal:
    """Soma dos comprovantes de pagamento da cliente nesse evento."""
    total = (
        db.session.query(db.func.coalesce(db.func.sum(EventPayment.amount), 0))
        .filter(EventPayment.event_id == event.id)
        .scalar()
    )
    return Decimal(str(total or 0))


# ── Feature 306: a regra única, o BV do retido, o resumo e o período ─────────────────────────


def pode_editar_venda_do_cancelado(user: User | None) -> bool:
    """A regra única do cancelado (FR-047): só o papel REAL de Superadmin corrige dados de venda.

    A mesma régua de `_can_delete()` (`agenda_write.py`): o "Ver como" não conta, porque o papel
    vem de `user.roles`, não da sessão.
    """
    from app.constants import RoleName

    return bool(user) and any(r.name.upper() == RoleName.SUPERADMIN for r in user.roles)


_CENTAVO = Decimal("0.01")


def _dinheiro(valor: Any) -> Decimal:
    return Decimal(str(valor or 0)).quantize(_CENTAVO)


def bv_do_retido(cheio: Any, retido: Any, venda: Any) -> Decimal:
    """O BV na proporção do que a Manto reteve: `bv_que_acompanha(cheio, retido, venda)`, teto no cheio.

    A mesma conta da comissão do retido (`comissoes_ops.comissao_do_retido`), para as duas
    proporções não divergirem na tolerância de R$ 0,01 (FR-028).
    """
    from app.orcamento.quote_ops import bv_que_acompanha

    cheio_d, retido_d, venda_d = (_dinheiro(x) for x in (cheio, retido, venda))
    if cheio_d <= 0 or retido_d <= 0 or venda_d <= 0:
        return Decimal("0.00")
    return min(cheio_d, bv_que_acompanha(cheio_d, retido_d, venda_d))


def filtro_devolucao():
    """A devolução à cliente: categoria, evento e aprovação — nunca pelo tipo de desembolso.

    `disbursement_type` a tela edita (e o "Salvar" de Gastos Extras chegou a apagá-lo), então ele
    não serve para reconhecer a devolução (substitui o `.first()` da 224 em `listar_cancelamentos`).
    """
    return db.and_(
        SpecialExpense.category == SpecialExpense.CATEGORY_DEVOLUCAO,
        SpecialExpense.event_id.isnot(None),
        SpecialExpense.status == "aprovado",
    )


def devolucoes_por_evento(ids: list[int]) -> dict[int, list[SpecialExpense]]:
    """Todas as devoluções (categoria + evento) dos ids, numa consulta só, por id do evento."""
    if not ids:
        return {}
    out: dict[int, list[SpecialExpense]] = {}
    linhas = (
        SpecialExpense.query.filter(
            SpecialExpense.category == SpecialExpense.CATEGORY_DEVOLUCAO,
            SpecialExpense.event_id.in_(ids),
        )
        .order_by(SpecialExpense.id)
        .all()
    )
    for gasto in linhas:
        out.setdefault(gasto.event_id, []).append(gasto)
    return out


def ids_do_grupo(principal_ids: list[int]) -> dict[int, list[int]]:
    """Os ids de cada grupo, por consulta: o principal e os dias com `group_leader_id` = ele.

    Nunca pela coleção (`leader.satellites`, `group_ops.group_events`): é a mesma consulta que
    `travar_grupo` trava em T1, e o resumo e o período a leem sem `FOR UPDATE` (data-model §5).
    Os dias cancelados entram: é dinheiro (FR-004).
    """
    if not principal_ids:
        return {}
    out: dict[int, list[int]] = {pid: [pid] for pid in principal_ids}
    for eid, lider in (
        db.session.query(CalendarEvent.id, CalendarEvent.group_leader_id)
        .filter(CalendarEvent.group_leader_id.in_(principal_ids))
        .order_by(CalendarEvent.id)
        .all()
    ):
        out[lider].append(eid)
    return out


def _pago_por_evento(ids: list[int]) -> dict[int, Decimal]:
    """Σ coalesce(comprovante, 0) por evento, numa consulta (o molde de `total_recebido`)."""
    if not ids:
        return {}
    return {
        eid: Decimal(str(total or 0))
        for eid, total in (
            db.session.query(EventPayment.event_id, db.func.coalesce(db.func.sum(EventPayment.amount), 0))
            .filter(EventPayment.event_id.in_(ids))
            .group_by(EventPayment.event_id)
            .all()
        )
    }


@dataclass
class ResumoCancelado:
    """O resumo único de um cancelado (FR-005): o que a tela, a DRE e o Comercial leem.

    Pago e devolvido são do grupo por consulta, ao vivo; o resto vem do congelado. `legado` é o
    cancelado sem linha congelada (o de antes do deploy): retido = pago − devolvido, comissão 0,
    imposto 0, BV só o pago.
    """

    event: CalendarEvent
    regime: str
    modo: str | None
    modo_corrente: str
    venda: Decimal | None
    pago: Decimal
    devolvido: Decimal
    devolucoes: list[SpecialExpense]
    retido: Decimal
    com_nota: bool
    cancelado_em: datetime | None
    principal: CalendarEvent | None
    venda_passou_para: CalendarEvent | None
    corte: dict[str, Decimal | None] | None
    imposto: Decimal | None
    taxa: Decimal | None
    comissao_cheia: Decimal
    comissao_retido: Decimal
    beneficiario: User | None
    seller_id: int | None
    linhas: list[CommissionPayment]
    bvs: list[dict[str, Any]] = field(default_factory=list)

    @property
    def bv_retido(self) -> Decimal:
        """O BV que conta (pago pelo pago; a pagar pela proporção), somado."""
        return sum((b["conta"] or Decimal("0") for b in self.bvs), Decimal("0.00"))

    @property
    def imposto_que_conta(self) -> Decimal:
        return _dinheiro(self.imposto) if self.imposto is not None else Decimal("0.00")

    @property
    def efeito_resultado(self) -> Decimal:
        """O que o cancelado soma ao resultado: retido − comissão − BV − imposto."""
        return self.retido - self.comissao_retido - self.bv_retido - self.imposto_que_conta

    @property
    def tem_dinheiro(self) -> bool:
        """Sem pago nem devolvido, o cancelado não entra em DRE nem no Comercial (P-24)."""
        return self.pago > 0 or self.devolvido > 0


def _modo_corrente(pago: Decimal, devolvido: Decimal) -> str:
    from app.constants import MODO_NADA, MODO_PARTE, MODO_TUDO

    if devolvido <= 0:
        return MODO_NADA
    if devolvido >= pago:
        return MODO_TUDO
    return MODO_PARTE


def _bv_que_conta(linha, acr, *, regime: str, retido: Decimal, venda: Decimal | None) -> Decimal | None:
    """O BV de um acréscimo no cancelado (decisão (a), data-model §7.4); `None` = some da Planilha.

    - `venda`, pago ou no banco: `paid_amount` (o `amount_brl`, só na janela do deploy);
    - `venda`, a pagar: o proporcional do retido; zero vira `None`;
    - sem linha congelada (`legado`, `satelite`, `dia`, `virtual`): o `amount_brl` se pago ou no
      banco; senão `None`.
    """
    from app.constants import REGIME_VENDA

    pago = (acr.bv_payment_status or "nao_pago") in ("pago", "no_banco")
    if regime == REGIME_VENDA and linha is not None:
        if pago:
            return _dinheiro(linha.paid_amount if linha.paid_amount is not None else acr.amount_brl)
        conta = bv_do_retido(linha.original_amount, retido, venda)
        return conta if conta > 0 else None
    return _dinheiro(acr.amount_brl) if pago else None


def resumos_cancelados(ids: list[int]) -> dict[int, ResumoCancelado]:
    """O resumo de cada cancelado dos ids, em lote (consultas fixas, sem N+1)."""
    from sqlalchemy.orm import selectinload

    from app.constants import REGIME_DIA, REGIME_LEGADO, REGIME_SATELITE, REGIME_VENDA
    from app.models import EventAcrescimo, EventCancellation

    if not ids:
        return {}
    # O backref `cancelamento` só existe depois do `configure_mappers`: o selectinload nasce aqui.
    eventos = (
        CalendarEvent.query.filter(CalendarEvent.id.in_(ids), CalendarEvent.cancelled_at.isnot(None))
        .options(selectinload(CalendarEvent.cancelamento).selectinload(EventCancellation.bvs))
        .all()
    )
    # O grupo do dinheiro: o do principal no `satelite` e no `dia`; o próprio nos demais (`legado`
    # incluído: sem congelado, não se sabe a que ato o dia pertenceu).
    principais: dict[int, int] = {}
    for ev in eventos:
        canc = ev.cancelamento
        if canc is not None and canc.regime in (REGIME_SATELITE, REGIME_DIA) and canc.group_leader_id:
            principais[ev.id] = canc.group_leader_id
        else:
            principais[ev.id] = ev.id
    grupos = ids_do_grupo(sorted(set(principais.values())))
    todos = sorted({i for g in grupos.values() for i in g} | {ev.id for ev in eventos})
    pago_por = _pago_por_evento(todos)
    devolucoes = devolucoes_por_evento(todos)
    linhas_por: dict[int, list[CommissionPayment]] = {}
    for cp in (
        CommissionPayment.query.filter(CommissionPayment.event_id.in_([ev.id for ev in eventos]))
        .order_by(CommissionPayment.id)
        .all()
    ):
        linhas_por.setdefault(cp.event_id, []).append(cp)
    acrescimos: dict[int, list] = {}
    for a in (
        EventAcrescimo.query.filter(EventAcrescimo.event_id.in_([ev.id for ev in eventos]), EventAcrescimo.is_bv.is_(True))
        .order_by(EventAcrescimo.id)
        .all()
    ):
        acrescimos.setdefault(a.event_id, []).append(a)
    beneficiarios = {
        ev.cancelamento.commission_seller_id
        for ev in eventos
        if ev.cancelamento is not None and ev.cancelamento.commission_seller_id
    }
    pessoas = {u.id: u for u in User.query.filter(User.id.in_(beneficiarios)).all()} if beneficiarios else {}
    de_fora = set(principais.values()) - {ev.id for ev in eventos}
    lideres = {e.id: e for e in CalendarEvent.query.filter(CalendarEvent.id.in_(de_fora)).all()} if de_fora else {}
    lideres.update({ev.id: ev for ev in eventos})

    out: dict[int, ResumoCancelado] = {}
    for ev in eventos:
        canc = ev.cancelamento
        regime = canc.regime if canc is not None else REGIME_LEGADO
        grupo = grupos.get(principais[ev.id], [ev.id])
        pago = sum((pago_por.get(i, Decimal("0")) for i in grupo), Decimal("0"))
        do_grupo = [g for i in grupo for g in devolucoes.get(i, [])]
        devolvido = sum((_dinheiro(g.amount) for g in do_grupo if g.status == "aprovado"), Decimal("0"))
        pago, devolvido = _dinheiro(pago), _dinheiro(devolvido)
        venda = _dinheiro(canc.sale_value) if canc is not None and canc.sale_value is not None else None
        retido = max(Decimal("0.00"), pago - devolvido) if regime in (REGIME_VENDA, REGIME_LEGADO) else Decimal("0.00")
        if regime == REGIME_VENDA and canc is not None:
            from app.financeiro.comissoes_ops import comissao_do_retido

            cheia = _dinheiro(canc.commission_full)
            comissao_retido = comissao_do_retido(cheia, retido, venda)
        else:
            cheia, comissao_retido = Decimal("0.00"), Decimal("0.00")
        congeladas = {b.acrescimo_id: b for b in (canc.bvs if canc is not None else []) if b.acrescimo_id is not None}
        bvs = []
        for a in acrescimos.get(ev.id, []):
            linha = congeladas.get(a.id)
            bvs.append({
                "acrescimo": a,
                "linha": linha,
                "cheio": _dinheiro(linha.original_amount if linha is not None else a.amount_brl),
                "conta": _bv_que_conta(linha, a, regime=regime, retido=retido, venda=venda),
                "estado": a.bv_payment_status or "nao_pago",
                "pago_no_ato": bool(linha.paid_at_cancellation) if linha is not None else False,
            })
        principal = lideres.get(canc.group_leader_id) if canc is not None and canc.group_leader_id else None
        corte = None
        if regime == REGIME_DIA and canc is not None:
            corte = {
                "venda_antes": canc.sale_value_before,
                "venda_depois": canc.sale_value_after,
                "cheio_antes": canc.sale_value_gross_before,
                "cheio_depois": canc.sale_value_gross_after,
            }
        com_nota = bool(canc.with_invoice) if canc is not None and regime == REGIME_VENDA else bool(ev.with_invoice)
        out[ev.id] = ResumoCancelado(
            event=ev,
            regime=regime,
            modo=canc.refund_mode if canc is not None else None,
            modo_corrente=_modo_corrente(pago, devolvido),
            venda=venda,
            pago=pago,
            devolvido=devolvido,
            devolucoes=list(devolucoes.get(ev.id, [])) if regime == REGIME_DIA else do_grupo,
            retido=retido,
            com_nota=com_nota,
            cancelado_em=ev.cancelled_at,
            principal=principal if regime in (REGIME_SATELITE, REGIME_DIA) else None,
            venda_passou_para=principal if canc is not None and canc.sale_handed_over else None,
            corte=corte,
            imposto=canc.retained_tax if canc is not None and regime == REGIME_VENDA else None,
            taxa=canc.commission_rate if canc is not None and regime == REGIME_VENDA else None,
            comissao_cheia=cheia,
            comissao_retido=comissao_retido,
            beneficiario=pessoas.get(canc.commission_seller_id) if canc is not None else None,
            seller_id=(canc.seller_id if canc is not None and canc.seller_id else ev.seller_id),
            linhas=linhas_por.get(ev.id, []),
            bvs=bvs,
        )
    return out


def resumo_cancelado(event: CalendarEvent) -> ResumoCancelado | None:
    """O resumo de um cancelado; `None` se o evento não está cancelado."""
    return resumos_cancelados([event.id]).get(event.id)


def _evento_curto(ev: CalendarEvent | None) -> dict[str, Any] | None:
    if ev is None:
        return None
    return {"id": ev.id, "titulo": ev.title, "data": ev.start_at.date().isoformat() if ev.start_at else None}


def _f(valor: Any) -> float | None:
    return None if valor is None else float(valor)


def serializar_resumo_cancelado(resumo: ResumoCancelado, flags: dict[str, Any]) -> dict[str, Any]:
    """O `ResumoCancelado` do contrato (contracts §0). PIX, comissão, BV, imposto e taxa só com
    `show_financeiro`; os limites do "Alterar devolução" só com `can_edit_venda_cancelado`."""
    from app.financeiro.comissoes_ops import ciclo_de_pagamento_da_linha, tipo_da_linha

    financeiro = bool(flags.get("show_financeiro"))
    out: dict[str, Any] = {
        "regime": resumo.regime,
        "modo": resumo.modo,
        "modo_corrente": resumo.modo_corrente,
        "venda": _f(resumo.venda),
        "pago": float(resumo.pago),
        "devolvido": float(resumo.devolvido),
        "devolucoes": [
            {
                "id": g.id,
                "valor": float(g.amount or 0),
                "nome": g.supplier_name,
                **({"pix": g.supplier_pix} if financeiro else {}),
                "estado": g.payment_status or "nao_pago",
                "data": g.expense_date.isoformat() if g.expense_date else None,
                "evento_id": g.event_id,
                "observacao": g.notes,
            }
            for g in resumo.devolucoes
        ],
        "retido": float(resumo.retido),
        "com_nota": resumo.com_nota,
        "cancelado_em": resumo.cancelado_em.isoformat() if resumo.cancelado_em else None,
        "principal": _evento_curto(resumo.principal),
        "venda_passou_para": _evento_curto(resumo.venda_passou_para),
        "corte": {k: _f(v) for k, v in resumo.corte.items()} if resumo.corte else None,
    }
    if financeiro:
        out["imposto"] = _f(resumo.imposto)
        out["taxa"] = _f(resumo.taxa)
        out["comissao"] = {
            "cheia": float(resumo.comissao_cheia),
            "retido": float(resumo.comissao_retido),
            "beneficiario": {"id": resumo.beneficiario.id, "nome": resumo.beneficiario.name} if resumo.beneficiario else None,
            "liquidada": float(sum((Decimal(c.amount or 0) for c in resumo.linhas if c.status in ("pago", "no_banco")), Decimal("0"))),
            "linhas": [
                {
                    "id": c.id,
                    "seller_id": c.seller_id,
                    "seller_nome": c.seller.name if c.seller else None,
                    "valor": float(c.amount or 0),
                    "status": c.status,
                    "tipo": tipo_da_linha(c)[0],
                    "ciclo": (lambda d: d.strftime("%Y-%m") if d else None)(ciclo_de_pagamento_da_linha(c)),
                    "motivo": tipo_da_linha(c)[1],
                }
                for c in resumo.linhas
            ],
        }
        out["bvs"] = [
            {
                "acrescimo_id": b["acrescimo"].id,
                "recebedor": (b["linha"].recipient if b["linha"] is not None else None) or b["acrescimo"].bv_recipient,
                "pix": (b["linha"].pix if b["linha"] is not None else None) or b["acrescimo"].bv_pix,
                "cheio": float(b["cheio"]),
                "conta": _f(b["conta"]),
                "estado": b["estado"],
                "pago_no_ato": b["pago_no_ato"],
            }
            for b in resumo.bvs
        ]
    return out


def cancelados_do_periodo(
    inicio: date, fim: date, *, seller_id: int | None = None, educamanto_only: bool = False
) -> list[ResumoCancelado]:
    """Os cancelados cujo dinheiro conta no período, pelo mês do `cancelled_at` (FR-044).

    Fonte única da DRE, do Comercial e do desempenho. Só `venda` e `legado` com dinheiro (P-24);
    `satelite`, `dia` e `virtual` não contam. O vendedor é o congelado (o de hoje no `legado`).
    """
    from app.constants import (
        EDUCAMANTO_TITLE_PREFIX,
        EVENT_TYPE_VIRTUAL,
        REGIME_LEGADO,
        REGIME_VENDA,
    )
    from app.models import EventCancellation

    comeco = datetime.combine(inicio, datetime.min.time())
    termino = datetime.combine(fim, datetime.max.time())
    consulta = (
        db.session.query(CalendarEvent.id)
        .outerjoin(EventCancellation, EventCancellation.event_id == CalendarEvent.id)
        .filter(
            CalendarEvent.cancelled_at >= comeco,
            CalendarEvent.cancelled_at <= termino,
            db.func.coalesce(CalendarEvent.event_type, "") != EVENT_TYPE_VIRTUAL,
            db.or_(EventCancellation.id.is_(None), EventCancellation.regime == REGIME_VENDA),
        )
    )
    if seller_id is not None:
        consulta = consulta.filter(db.func.coalesce(EventCancellation.seller_id, CalendarEvent.seller_id) == seller_id)
    if educamanto_only:
        consulta = consulta.filter(CalendarEvent.title.ilike(EDUCAMANTO_TITLE_PREFIX + "%"))
    ids = [r[0] for r in consulta.order_by(CalendarEvent.cancelled_at, CalendarEvent.id).all()]
    resumos = resumos_cancelados(ids)
    return [
        resumos[i]
        for i in ids
        if i in resumos and resumos[i].regime in (REGIME_VENDA, REGIME_LEGADO) and resumos[i].tem_dinheiro
    ]


def totais_cancelamentos(resumos: list[ResumoCancelado]) -> dict[str, Any]:
    """Os totais do painel de cancelamentos (`paineis.cancelamentos`, contracts §19)."""
    def soma(campo) -> Decimal:
        return sum((campo(r) for r in resumos), Decimal("0.00"))

    a_pagar = soma(lambda r: sum(
        (_dinheiro(g.amount) for g in r.devolucoes if g.status == "aprovado" and (g.payment_status or "nao_pago") != "pago"),
        Decimal("0.00"),
    ))
    return {
        "quantidade": len(resumos),
        "pago": soma(lambda r: r.pago),
        "devolvido": soma(lambda r: r.devolvido),
        "devolucao_a_pagar": a_pagar,
        "retido": soma(lambda r: r.retido),
        "comissao_retido": soma(lambda r: r.comissao_retido),
        "bv_retido": soma(lambda r: r.bv_retido),
        "imposto": soma(lambda r: r.imposto_que_conta),
        "efeito_resultado": soma(lambda r: r.efeito_resultado),
        "itens": [
            {
                "event_id": r.event.id,
                "titulo": r.event.title,
                "cancelado_em": r.cancelado_em.isoformat() if r.cancelado_em else None,
                "retido": r.retido,
            }
            for r in resumos
        ],
    }


def retido_por_vendedor(resumos: list[ResumoCancelado]) -> dict[int, Decimal]:
    """O retido de cada vendedor (o congelado), para o Comercial e o desempenho (FR-046)."""
    out: dict[int, Decimal] = {}
    for r in resumos:
        if r.seller_id is not None:
            out[r.seller_id] = out.get(r.seller_id, Decimal("0.00")) + r.retido
    return out


def bv_da_planilha(acr, *, resumos: dict[int, ResumoCancelado] | None = None) -> Decimal | None:
    """O BV que conta na Planilha, no resumo e no custo da DRE (decisão (a), data-model §7.4).

    - Evento vivo: `amount_brl`;
    - `venda` pago ou no banco: `paid_amount` (o `amount_brl` só na janela do deploy);
    - `venda` não pago: o proporcional do retido (`bv_do_retido`); `None` quando dá zero;
    - sem linha congelada (`legado`, `satelite`, `dia`, `virtual`): o `amount_brl` se pago ou no
      banco; senão `None`.

    `None` = o BV some da Planilha. `resumos` (de `resumos_cancelados`) evita uma consulta por BV
    quando quem chama monta uma lista.
    """
    ev = acr.event
    if ev is None or not ev.is_cancelled:
        return _dinheiro(acr.amount_brl)
    resumo = resumos.get(ev.id) if resumos is not None else None
    if resumo is None:
        resumo = resumo_cancelado(ev)
    if resumo is None:
        return _dinheiro(acr.amount_brl)
    for b in resumo.bvs:
        if b["acrescimo"].id == acr.id:
            return b["conta"]
    return _bv_que_conta(None, acr, regime=resumo.regime, retido=resumo.retido, venda=resumo.venda)


def marcar_status_do_bv(acrescimo_id: int, status: str, valor_esperado: Any, actor_name: str) -> str:
    """A função única que muda o status de um BV na Planilha (as duas portas, R9). Não faz commit.

    Ordem: `valor_esperado` não numérico → 400 antes de travar; o evento (`travar_evento`) e depois
    o acréscimo (`FOR UPDATE populate_existing`), a ordem de `substituir_acrescimos`; relê o
    congelado; `atual = bv_da_planilha`. Ao marcar pago ou no banco: `atual is None` → 409
    `bv_nao_esta_a_pagar`; `valor_esperado` diferente de `atual` → 409 `valor_mudou` (a frase da
    305). `paid_amount` segue o data-model §7.4: nasce no "pago", fica entre pago e no banco, volta
    a `None` no desfazer (o BV volta ao proporcional, FR-039).

    Returns:
        O status gravado.

    Raises:
        CancelValidationError: 400 "Item não encontrado." / "Valor esperado inválido.", 409.
    """
    from app.calendar.orcamento_evento_ops import travar_evento
    from app.constants import CODIGO_BV_NAO_ESTA_A_PAGAR, CODIGO_VALOR_MUDOU
    from app.models import EventAcrescimo, EventCancellationBv
    from app.money import format_brl
    from app.utils import audit

    esperado = None
    if valor_esperado is not None and not isinstance(valor_esperado, bool):
        try:
            esperado = Decimal(str(valor_esperado)).quantize(_CENTAVO)
        except (ArithmeticError, ValueError) as exc:
            raise CancelValidationError("Valor esperado inválido.") from exc
    acr = db.session.get(EventAcrescimo, acrescimo_id) if acrescimo_id is not None else None
    if acr is None or not acr.is_bv:
        raise CancelValidationError("Item não encontrado")
    if acr.event is not None:
        travar_evento(acr.event)
    acr = (
        EventAcrescimo.query.filter(EventAcrescimo.id == acrescimo_id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    linha = (
        EventCancellationBv.query.filter(EventCancellationBv.acrescimo_id == acr.id)
        .populate_existing()
        .one_or_none()
    )
    if linha is not None:
        db.session.refresh(linha.cancelamento)
    antes = acr.bv_payment_status or "nao_pago"
    marca_pago = status in ("pago", "no_banco")
    atual = bv_da_planilha(acr)
    if marca_pago:
        if atual is None:
            raise CancelValidationError(
                "Este BV não está a pagar: recarregue a Planilha.", status=409, codigo=CODIGO_BV_NAO_ESTA_A_PAGAR
            )
        if esperado is not None and esperado != atual:
            raise CancelValidationError(
                f"O BV mudou para {format_brl(float(atual), prefix=True)} desde que a Planilha abriu: "
                "recarregue e confira antes de marcar.",
                status=409,
                codigo=CODIGO_VALOR_MUDOU,
                atual=float(atual),
            )
    if linha is not None:
        if marca_pago and antes not in ("pago", "no_banco"):
            linha.paid_amount = atual
        elif not marca_pago:
            linha.paid_amount = None
    acr.bv_payment_status = status
    valor = linha.paid_amount if linha is not None and linha.paid_amount is not None else atual
    audit(
        "payment",
        "event_bv",
        acr.id,
        acr.bv_recipient or "—",
        f"BV (repasse): {antes} → {status}"
        + (f", {format_brl(float(valor), prefix=True)}" if valor is not None else "")
        + (f" (por {actor_name})" if actor_name else ""),
    )
    return status


# ── Feature 306: as travas do ato e das correções (data-model §8.10, R24) ─────────────────────


def travar_grupo(event: CalendarEvent) -> list[CalendarEvent]:
    """T1: trava o grupo inteiro (o principal e os dias), por id, e relê todas as colunas.

    Os ids saem de `ids_do_grupo`, por consulta, nunca de `event.satellites`. Depois da trava a
    composição é relida: se outro ato agrupou, desagrupou ou passou a venda no meio, 409
    `grupo_mudou`. Avulso = uma linha. Regime, vendedor, taxa e `is_cancelled` só se leem depois
    daqui. Não faz commit.
    """
    from app.constants import CODIGO_GRUPO_MUDOU

    db.session.flush()
    principal_id = event.group_leader_id or event.id
    ids = sorted({*ids_do_grupo([principal_id])[principal_id], event.id})
    eventos = (
        CalendarEvent.query.filter(CalendarEvent.id.in_(ids))
        .order_by(CalendarEvent.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    relido = event.group_leader_id or event.id
    if relido != principal_id or sorted({*ids_do_grupo([relido])[relido], event.id}) != ids:
        raise CancelValidationError(
            "O grupo deste evento mudou enquanto você decidia: recarregue e confira.",
            status=409,
            codigo=CODIGO_GRUPO_MUDOU,
        )
    # As coleções lidas antes da trava podem estar velhas (R25).
    for ev in eventos:
        db.session.expire(ev, ["satellites", "group_leader", "acrescimos", "cancelamento"])
    return eventos


def _ler_congelados(ids: list[int]) -> dict[int, Any]:
    """T2: as linhas congeladas do grupo, relidas (`populate_existing`), sem `FOR UPDATE`."""
    from sqlalchemy.orm import selectinload

    from app.models import EventCancellation

    if not ids:
        return {}
    linhas = (
        EventCancellation.query.filter(EventCancellation.event_id.in_(ids))
        .options(selectinload(EventCancellation.bvs), selectinload(EventCancellation.elenco))
        .populate_existing()
        .all()
    )
    return {c.event_id: c for c in linhas}


def _travar_acrescimos(event_id: int) -> list:
    """T3: os acréscimos do evento, `ORDER BY id FOR UPDATE`, relidos."""
    from app.models import EventAcrescimo

    return (
        EventAcrescimo.query.filter(EventAcrescimo.event_id == event_id)
        .order_by(EventAcrescimo.id)
        .with_for_update()
        .populate_existing()
        .all()
    )


def _travar_linhas_de_comissao(ids: list[int], beneficiarios) -> None:
    """T4: um SELECT só — as linhas do grupo e as abertas dos beneficiários, `ORDER BY id`."""
    condicao = CommissionPayment.event_id.in_(ids)
    quem = sorted({b for b in beneficiarios if b is not None})
    if quem:
        condicao = db.or_(
            condicao,
            db.and_(
                CommissionPayment.seller_id.in_(quem),
                CommissionPayment.status.in_(("a_pagar", "no_banco")),
            ),
        )
    (
        CommissionPayment.query.filter(condicao)
        .order_by(CommissionPayment.id)
        .with_for_update()
        .populate_existing()
        .all()
    )


def _travar_devolucoes(ids: list[int]) -> list[SpecialExpense]:
    """T5: todas as devoluções do grupo, pendentes inclusive, `ORDER BY id FOR UPDATE`."""
    return (
        SpecialExpense.query.filter(
            SpecialExpense.category == SpecialExpense.CATEGORY_DEVOLUCAO,
            SpecialExpense.event_id.in_(ids),
        )
        .order_by(SpecialExpense.id)
        .with_for_update()
        .populate_existing()
        .all()
    )


def _beneficiarios_das_linhas(ids: list[int]) -> set[int]:
    return {
        sid
        for (sid,) in db.session.query(CommissionPayment.seller_id)
        .filter(CommissionPayment.event_id.in_(ids), CommissionPayment.status != "cancelado")
        .distinct()
        .all()
    }


def traduzir_erro_de_banco(exc: Exception) -> CancelValidationError | None:
    """O deadlock (40P01) vira 409 `tente_de_novo`; o UNIQUE do cancelamento, 409 `ja_cancelado`.

    As views da 306 chamam isto no `except` do erro de banco, depois do rollback.
    """
    from sqlalchemy.exc import DBAPIError, IntegrityError

    from app.constants import CODIGO_JA_CANCELADO, CODIGO_TENTE_DE_NOVO

    if not isinstance(exc, DBAPIError):
        return None
    codigo_pg = getattr(getattr(exc, "orig", None), "pgcode", None) or getattr(
        getattr(getattr(exc, "orig", None), "diag", None), "sqlstate", None
    )
    if codigo_pg == "40P01":
        return CancelValidationError(
            "Outra pessoa mexeu neste evento ao mesmo tempo: tente de novo.",
            status=409,
            codigo=CODIGO_TENTE_DE_NOVO,
        )
    if isinstance(exc, IntegrityError) and "uq_event_cancellations_event_id" in str(exc):
        return CancelValidationError(
            "Este evento já está cancelado.", status=409, codigo=CODIGO_JA_CANCELADO
        )
    return None


# ── O pedido de cancelamento (o corpo do POST) ─────────────────────────────────────────────


def _decimal(valor: Any) -> tuple[Decimal | None, bool]:
    """`(valor, inválido)`: ausente → `(None, False)`; não numérico → `(None, True)`."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None, False
    if isinstance(valor, bool):
        return None, True
    try:
        numero = Decimal(str(valor).strip().replace(",", ".") if isinstance(valor, str) else str(valor))
    except (ArithmeticError, ValueError):
        return None, True
    if not numero.is_finite():
        return None, True
    return numero.quantize(_CENTAVO), False


def _texto(valor: Any) -> str:
    return valor.strip() if isinstance(valor, str) else ""


@dataclass
class PedidoDeCancelamento:
    """O corpo do `POST …/cancelar` lido uma vez (contracts §1). A validação é de `_erros_do_pedido`."""

    motivo: str
    modo: str | None
    valor: Decimal | None
    valor_invalido: bool
    nome: str
    pix: str
    observacao: str
    imposto: Decimal | None
    imposto_enviado: bool
    imposto_invalido: bool
    bvs: dict[int, tuple[str, str]]
    venda_nova_enviada: bool

    @classmethod
    def ler(cls, corpo: dict[str, Any] | None) -> PedidoDeCancelamento:
        corpo = corpo if isinstance(corpo, dict) else {}
        devolucao = corpo.get("devolucao") if isinstance(corpo.get("devolucao"), dict) else {}
        valor, valor_invalido = _decimal(devolucao.get("valor"))
        imposto, imposto_invalido = _decimal(corpo.get("imposto_retido"))
        bvs: dict[int, tuple[str, str]] = {}
        for item in corpo.get("bvs") or []:
            if isinstance(item, dict) and isinstance(item.get("acrescimo_id"), int):
                bvs[item["acrescimo_id"]] = (_texto(item.get("recebedor")), _texto(item.get("pix")))
        modo = devolucao.get("modo")
        return cls(
            motivo=_texto(corpo.get("motivo")),
            modo=modo if isinstance(modo, str) else None,
            valor=valor,
            valor_invalido=valor_invalido,
            nome=_texto(devolucao.get("nome")),
            pix=_texto(devolucao.get("pix")),
            observacao=_texto(devolucao.get("observacao")),
            imposto=imposto,
            imposto_enviado="imposto_retido" in corpo and corpo.get("imposto_retido") is not None,
            imposto_invalido=imposto_invalido,
            bvs=bvs,
            venda_nova_enviada=corpo.get("venda_nova") is not None,
        )

    def devolve(self, max_devolucao: Decimal) -> Decimal:
        """Quanto este pedido devolve: Tudo = o máximo; Parte = o valor; Nada = 0."""
        from app.constants import MODO_PARTE, MODO_TUDO

        if self.modo == MODO_TUDO:
            return max_devolucao
        if self.modo == MODO_PARTE and self.valor is not None and self.valor > 0:
            return self.valor
        return Decimal("0.00")


# ── A conta do ato: a mesma na prévia e na execução (FR-011, R2) ───────────────────────────


@dataclass
class ContaDoAto:
    """O que o ato faz com o dinheiro, antes de gravar. A prévia mostra; a execução grava."""

    pago: Decimal
    ja_devolvido: Decimal
    max_devolucao: Decimal
    devolucao: Decimal
    retido: Decimal
    venda: Decimal
    cheia: Decimal
    beneficiario_id: int | None
    taxa: Decimal
    custo: Decimal | None
    bvs: list[dict[str, Any]]
    comissao_retido: Decimal

    @property
    def alvos(self) -> dict[int, Decimal]:
        return {self.beneficiario_id: self.comissao_retido} if self.beneficiario_id else {}

    @property
    def bv_retido(self) -> Decimal:
        return sum((b["conta"] for b in self.bvs), Decimal("0.00"))


def _dinheiro_do_grupo(ids: list[int]) -> tuple[Decimal, Decimal]:
    """`(pago, já devolvido)` do grupo, por consulta: comprovantes e devoluções aprovadas."""
    pago = _dinheiro(sum(_pago_por_evento(ids).values(), Decimal("0")))
    devolvido = (
        db.session.query(db.func.coalesce(db.func.sum(SpecialExpense.amount), 0))
        .filter(filtro_devolucao(), SpecialExpense.event_id.in_(ids))
        .scalar()
    )
    return pago, _dinheiro(devolvido)


def _custo_congelado(event: CalendarEvent, settings) -> Decimal | None:
    """O custo de cachês que a comissão EducaManto usa (sobre o lucro); fora dela, `None`."""
    from app.financeiro import comissoes_ops

    if not (event.is_educamanto and comissoes_ops._educamanto_responsavel(settings) is not None):
        return None
    custo = comissoes_ops._group_cost(event) if event.is_group_leader else comissoes_ops._event_cost(event)
    return _dinheiro(custo)


def _conta_do_ato(
    event: CalendarEvent, ids: list[int], acrescimos: list, devolucao: Decimal, settings
) -> ContaDoAto:
    from app.financeiro import comissoes_ops

    pago, ja_devolvido = _dinheiro_do_grupo(ids)
    maximo = max(Decimal("0.00"), pago - ja_devolvido)
    retido = max(Decimal("0.00"), pago - ja_devolvido - devolucao)
    venda = _dinheiro(event.sale_value)
    custo = _custo_congelado(event, settings)
    cheia, beneficiario, taxa = comissoes_ops.comissao_cheia_do_evento(event, settings, custo=custo)
    bvs = []
    for a in acrescimos:
        if not a.is_bv or not a.amount_brl:
            continue
        ja_pago = (a.bv_payment_status or "nao_pago") in ("pago", "no_banco")
        conta = _dinheiro(a.amount_brl) if ja_pago else bv_do_retido(a.amount_brl, retido, venda)
        bvs.append({"acrescimo": a, "cheio": _dinheiro(a.amount_brl), "conta": conta, "pago": ja_pago})
    return ContaDoAto(
        pago=pago,
        ja_devolvido=ja_devolvido,
        max_devolucao=maximo,
        devolucao=devolucao,
        retido=retido,
        venda=venda,
        cheia=_dinheiro(cheia),
        beneficiario_id=beneficiario,
        taxa=Decimal(str(taxa)),
        custo=custo,
        bvs=bvs,
        comissao_retido=comissoes_ops.comissao_do_retido(cheia, retido, venda),
    )


def _aliquota(settings) -> Decimal:
    from app.financeiro.routes import _get_tax_rate

    return Decimal(str(_get_tax_rate(settings)))


def _efeito(event: CalendarEvent, conta: ContaDoAto, plano: list[dict], settings) -> dict[str, Any]:
    """O `EfeitoCancelamento` (contracts §2) a partir da conta e do plano da reconciliação."""
    from app.constants import DIA_DO_REPASSE

    novas = [p for p in plano if p["linha_id"] is None and p["seller_id"] == conta.beneficiario_id]
    nova = novas[0] if novas else (next((p for p in plano if p["linha_id"] is None), None))
    ciclo = (nova["payable_from"] or nova["sale_date"]) if nova else None
    repasse = None
    if ciclo is not None:
        seguinte = date(ciclo.year + 1, 1, 1) if ciclo.month == 12 else date(ciclo.year, ciclo.month + 1, 1)
        repasse = seguinte.replace(day=DIA_DO_REPASSE)
    liquidada = (
        db.session.query(db.func.coalesce(db.func.sum(CommissionPayment.amount), 0))
        .filter(
            CommissionPayment.event_id == event.id,
            CommissionPayment.seller_id == conta.beneficiario_id,
            CommissionPayment.status.in_(("pago", "no_banco")),
        )
        .scalar()
        if conta.beneficiario_id
        else 0
    )
    referencia = None
    if event.with_invoice:
        referencia = (_aliquota(settings) * conta.retido / Decimal("100")).quantize(_CENTAVO)
    return {
        "devolucao": float(conta.devolucao),
        "retido": float(conta.retido),
        "comissao_cheia": float(conta.cheia),
        "comissao_retido": float(conta.comissao_retido),
        "bv_retido": float(conta.bv_retido),
        "bvs": [{"acrescimo_id": b["acrescimo"].id, "bv_retido": float(b["conta"])} for b in conta.bvs],
        "ja_liquidada": float(_dinheiro(liquidada)),
        "ajuste": float(nova["valor"]) if nova else None,
        "ciclo": ciclo.strftime("%Y-%m") if ciclo else None,
        "repasse_em": repasse.isoformat() if repasse else None,
        "imposto_referencia": float(referencia) if referencia is not None else None,
    }


def previa_cancelamento(event: CalendarEvent, devolucao: Any, venda_nova: Any = None) -> dict[str, Any]:
    """A prévia do ato (`GET …/impacto-exclusao?devolucao=`): a mesma conta, sem trava e sem gravar.

    `reconciliar_comissao_do_cancelado(simular=True)` não toca o ORM, e `primeiro_repasse_aberto`
    exclui as linhas do próprio evento: a prévia sai igual à execução (FR-011).

    Raises:
        CancelValidationError: 400 `fields.devolucao` / `fields.venda_nova`; 409 `ja_cancelado`.
    """
    from app.constants import CODIGO_JA_CANCELADO, MOTIVO_AJUSTE_RETIDO, now_sp
    from app.financeiro import comissoes_ops
    from app.financeiro.vendas_ops import is_loja_virtual
    from app.models import EventAcrescimo, SiteSetting

    valor, invalido = _decimal(devolucao)
    if event.is_cancelled:
        raise CancelValidationError("Este evento já está cancelado.", status=409, codigo=CODIGO_JA_CANCELADO)
    if venda_nova is not None:
        raise CancelValidationError(
            "O novo valor da venda só vale ao cancelar um dia do grupo.", field="venda_nova"
        )
    principal_id = event.group_leader_id or event.id
    ids = ids_do_grupo([principal_id])[principal_id]
    pago, ja_devolvido = _dinheiro_do_grupo(ids)
    maximo = max(Decimal("0.00"), pago - ja_devolvido)
    if invalido or valor is None or valor < 0 or valor > maximo:
        raise CancelValidationError(
            f"Informe um valor de 0 a {_brl(maximo)}.", field="devolucao"
        )
    settings = SiteSetting.query.get(1)
    acrescimos = (
        EventAcrescimo.query.filter(EventAcrescimo.event_id == event.id).order_by(EventAcrescimo.id).all()
    )
    conta = _conta_do_ato(event, ids, acrescimos, valor, settings)
    plano: list[dict] = []
    if not is_loja_virtual(event):
        plano = comissoes_ops.reconciliar_comissao_do_cancelado(
            event, conta.alvos, motivo=MOTIVO_AJUSTE_RETIDO, hoje=now_sp().date(), simular=True
        )
    return _efeito(event, conta, plano, settings)


def _brl(valor: Any) -> str:
    from app.money import format_brl

    return format_brl(float(valor or 0), prefix=True)


# ── O ato ─────────────────────────────────────────────────────────────────────────────────────


def ao_cancelar(event: CalendarEvent, *, alcance: str, novo_principal: CalendarEvent | None = None) -> None:
    """Ponto de extensão da 2a (data-model §6.4, FR-062), sem efeito nesta entrega.

    Roda em **todo** cancelamento, na transação, logo depois de `cancelled_at`: o avulso e cada
    dia do "todos" com `(ALCANCE_TODOS, None)`; o corte de um dia que não é o principal com
    `(ALCANCE_SO_ESTE_DIA, None)`; o antigo 1º dia, **depois** de `passar_venda`, com
    `(ALCANCE_SO_ESTE_DIA, novo_principal)`. O verify o chama pelo módulo.
    """
    return None


def _recusas_de_estado(event: CalendarEvent) -> None:
    """As recusas que não dependem do corpo, depois de T1: já cancelado, ensaio, grupo (até a H5)."""
    from app.constants import CODIGO_ENSAIO, CODIGO_JA_CANCELADO

    if event.is_cancelled:
        raise CancelValidationError("Este evento já está cancelado.", status=409, codigo=CODIGO_JA_CANCELADO)
    if event.event_type == "ENSAIO":
        raise CancelValidationError(
            "Ensaio não se cancela sozinho: ele sai junto com o cancelamento do evento.",
            status=409,
            codigo=CODIGO_ENSAIO,
        )
    if event.is_group_leader or event.is_satellite:
        raise CancelValidationError(
            "Desagrupe os eventos satélites antes de cancelar este evento.", field="motivo"
        )


def _recusa_da_pendente(devolucoes: list[SpecialExpense]) -> None:
    from app.constants import CODIGO_DEVOLUCAO_PENDENTE

    pendentes = [d for d in devolucoes if d.status == "pendente"]
    if not pendentes:
        return
    dias = sorted({d.event_id for d in pendentes})
    eventos = {e.id: e for e in CalendarEvent.query.filter(CalendarEvent.id.in_(dias)).all()}
    raise CancelValidationError(
        "Há uma devolução à cliente pendente ligada a este evento: aprove ou rejeite antes de cancelar.",
        status=409,
        codigo=CODIGO_DEVOLUCAO_PENDENTE,
        dias=[_evento_curto(eventos[i]) for i in dias if i in eventos],
    )


def _erros_do_pedido(
    event: CalendarEvent, pedido: PedidoDeCancelamento, *, regime: str, conta: ContaDoAto
) -> dict[str, str]:
    """Todos os campos recusados de uma vez (contracts §1, item 10)."""
    from app.calendar.orcamento_evento_ops import erros_do_bv
    from app.constants import MODO_NADA, MODO_PARTE, MODO_TUDO, REGIME_VENDA

    erros: dict[str, str] = {}
    if not pedido.motivo:
        erros["motivo"] = "Explique o motivo do cancelamento."
    if pedido.venda_nova_enviada:
        erros["venda_nova"] = "O novo valor da venda só vale ao cancelar um dia do grupo."
    if regime != REGIME_VENDA:
        if pedido.imposto_enviado:
            erros["imposto_retido"] = "Esta venda não tem imposto a reter."
        return erros
    modo = pedido.modo
    if modo not in (MODO_TUDO, MODO_PARTE, MODO_NADA):
        erros["devolucao_modo"] = "Escolha se devolve tudo, parte ou nada à cliente."
    elif conta.pago <= 0 and modo != MODO_NADA:
        erros["devolucao_modo"] = "A cliente não pagou nada (nenhum comprovante com valor): só cabe Nada."
    elif modo == MODO_PARTE:
        if pedido.valor_invalido or pedido.valor is None or pedido.valor <= 0:
            erros["devolucao_valor"] = "Informe quanto devolve à cliente."
        elif pedido.valor > conta.max_devolucao:
            erros["devolucao_valor"] = f"Acima do que dá para devolver ({_brl(conta.max_devolucao)})."
    elif modo == MODO_TUDO and (pedido.valor_invalido or pedido.valor is None):
        erros["devolucao_valor"] = "Recarregue a página: falta o total a devolver."
    if modo in (MODO_TUDO, MODO_PARTE) and "devolucao_modo" not in erros:
        if not pedido.nome:
            erros["devolucao_nome"] = "Informe quem recebe a devolução."
        elif len(pedido.nome) > 200:
            erros["devolucao_nome"] = "Quem recebe: até 200 caracteres."
        if not pedido.pix:
            erros["devolucao_pix"] = "Informe o PIX da devolução."
        elif len(pedido.pix) > 120:
            erros["devolucao_pix"] = "PIX: até 120 caracteres."
    if event.with_invoice:
        if pedido.imposto_invalido or pedido.imposto is None:
            erros["imposto_retido"] = "Informe o imposto retido em reais (0 se não houve)."
        elif pedido.imposto < 0:
            erros["imposto_retido"] = "O imposto retido não pode ser negativo."
    elif pedido.imposto_enviado:
        erros["imposto_retido"] = "Este evento não tem nota fiscal: não há imposto a reter."
    for b in conta.bvs:
        a = b["acrescimo"]
        if b["pago"] or b["conta"] <= 0:
            continue
        recebedor, pix = pedido.bvs.get(a.id, ("", ""))
        if erros_do_bv(recebedor or (a.bv_recipient or ""), pix or (a.bv_pix or "")):
            erros[f"bv_pix_{a.id}"] = "Informe quem recebe e o PIX do BV — ele vai à Planilha de Pagamentos."
    return erros


def _gravar_pix_dos_bvs(acrescimos: list, pedido: PedidoDeCancelamento) -> None:
    """Recebedor e PIX do corpo vão ao acréscimo (já travado em T3) antes de congelar (FR-010)."""
    for a in acrescimos:
        if a.is_bv and a.id in pedido.bvs:
            recebedor, pix = pedido.bvs[a.id]
            if recebedor:
                a.bv_recipient = recebedor[:200]
            if pix:
                a.bv_pix = pix[:140]


def _congelar(event: CalendarEvent, *, regime: str, pedido: PedidoDeCancelamento, conta: ContaDoAto, actor: User):
    """A linha congelada do ato e as dos BVs (data-model §1–§2). Pela relação (§8.12)."""
    from app.constants import REGIME_VENDA
    from app.models import EventCancellation, EventCancellationBv

    venda = regime == REGIME_VENDA
    canc = EventCancellation(
        event=event,
        regime=regime,
        refund_mode=pedido.modo if venda else None,
        sale_value=conta.venda if venda else None,
        commission_full=conta.cheia if venda else None,
        commission_rate=conta.taxa if venda else None,
        commission_cost=conta.custo if venda else None,
        commission_seller_id=conta.beneficiario_id if venda else None,
        seller_id=event.seller_id,
        with_invoice=bool(event.with_invoice) if venda else False,
        retained_tax=pedido.imposto if venda and event.with_invoice else None,
        updated_by_id=actor.id,
    )
    if venda:
        for b in conta.bvs:
            a = b["acrescimo"]
            canc.bvs.append(
                EventCancellationBv(
                    acrescimo_id=a.id,
                    recipient=a.bv_recipient,
                    pix=a.bv_pix,
                    original_amount=b["cheio"],
                    paid_at_cancellation=b["pago"],
                    paid_amount=b["cheio"] if b["pago"] else None,
                )
            )
    db.session.add(canc)
    return canc


def _registrar_devolucao(
    event: CalendarEvent,
    *,
    valor: Decimal,
    nome: str,
    pix: str,
    observacao: str,
    actor: User,
) -> SpecialExpense | None:
    """Cria o Gasto Extra da devolução à cliente. Não faz commit.

    Nasce **aprovado** porque quem cancela já é Superadmin — pedir uma segunda aprovação da
    mesma pessoa só atrasaria o repasse. Aprovado, ele entra sozinho na Planilha de Pagamentos e
    na DRE do mês, que já somam `SpecialExpense` do período. Direto no ORM, nunca por
    `create_expense` (que nasce pendente e avisa o Financeiro). A data é a de São Paulo do ato.
    """
    from app.constants import now_sp

    if valor <= 0:
        return None
    agora = now_sp()
    gasto = SpecialExpense(
        description=f"Devolução à cliente — {event.title}"[:200],
        category=SpecialExpense.CATEGORY_DEVOLUCAO,
        amount=valor,
        expense_date=agora.date(),
        status="aprovado",
        notes=observacao or None,
        created_by_id=actor.id,
        approved_by_id=actor.id,
        approved_at=agora,
        disbursement_type="cliente",
        supplier_name=nome[:200] or None,
        supplier_pix=pix[:120] or None,
        payment_status="nao_pago",
        paid_at_creation=False,
        event_id=event.id,
    )
    db.session.add(gasto)
    return gasto


def _texto_do_historico(motivo: str, regime: str, pedido: PedidoDeCancelamento, conta: ContaDoAto) -> str:
    """O histórico do ato (FR-016): o modo, o devolvido, o retido, o BV por recebedor, o imposto."""
    from app.constants import REGIME_VENDA

    partes = [f"Evento cancelado: {motivo}"]
    if regime != REGIME_VENDA:
        return partes[0]
    rotulo = {"tudo": "devolve tudo", "parte": "devolve parte", "nada": "não devolve nada"}.get(pedido.modo or "", "")
    if conta.devolucao > 0:
        partes.append(f"{rotulo}: devolução de {_brl(conta.devolucao)} a {pedido.nome}")
    else:
        partes.append(rotulo)
    partes.append(f"retido {_brl(conta.retido)}")
    if conta.beneficiario_id:
        partes.append(f"comissão do retido {_brl(conta.comissao_retido)}")
    for b in conta.bvs:
        quem = b["acrescimo"].bv_recipient or "(sem recebedor)"
        partes.append(f"BV {'já pago' if b['pago'] else 'do retido'} de {quem}: {_brl(b['conta'])}")
    if pedido.imposto is not None:
        partes.append(f"imposto retido {_brl(pedido.imposto)}")
    return " | ".join(partes)


def _alvos_do_google(eventos: list[CalendarEvent]) -> list[str]:
    """Os ids do Google a remover depois do commit, guardados antes do `desmarcar` (FR-014).

    Pula o marcado "Sumiu do Google Agenda" (já não está lá), a venda virtual sem Google e o
    evento sem id.
    """
    return [
        e.google_event_id
        for e in eventos
        if e.google_event_id
        and not e.is_google_missing
        and not e.google_event_id.startswith("virtual-local-")
    ]


def _remover_do_google(ids_do_google: list[str]) -> tuple[bool, str | None]:
    """Depois do commit, fora da trava (R23). `(removeu algum, aviso)`; o aviso nunca traz o erro cru.

    `CALENDAR_SUPPRESS_EVENT_WRITES` é lida a cada chamada (o verify a liga e desliga), e a chave
    ausente vale como travado: o `manto_local` traz o token de verdade do calendário da empresa.
    404/410 é "já não estava lá".
    """
    from flask import current_app

    if not ids_do_google:
        return False, None
    if current_app.config.get("CALENDAR_SUPPRESS_EVENT_WRITES", True):
        return False, (
            "Cancelado no sistema. Neste ambiente o Google Agenda não é alterado: remova o evento "
            "de lá à mão, se for o caso."
        )
    from app.calendar import service as gcal
    from app.calendar.routes import CALENDAR_ID

    removeu, falhou = False, False
    for gid in ids_do_google:
        try:
            gcal.delete_event(CALENDAR_ID, gid)
            removeu = True
        except Exception as exc:  # noqa: BLE001 — falha do Google não desfaz o cancelamento
            if gcal._status_http(exc) in (404, 410):
                continue
            falhou = True
            import logging

            logging.getLogger(__name__).warning("Cancelamento: o Google não removeu %s (%s)", gid, type(exc).__name__)
    if falhou:
        return removeu, (
            "Cancelado no sistema, mas o Google Agenda não confirmou a remoção: confira lá e "
            "remova o evento à mão."
        )
    return removeu, None


def cancelar_evento(event: CalendarEvent, *, corpo: dict[str, Any] | None, actor: User) -> dict[str, Any]:
    """Cancela o evento: congela, devolve, reconcilia a comissão e tira do Google. Commita.

    A ordem é a única do ato (data-model §7.1; contracts §1): travas → recusas → validação de
    todos os campos → (marcado: desmarcar) → congelar → devolução → reconciliar → `cancelled_at`
    → `ao_cancelar` → `EventLog` (UTC) → commit → Google, fora da trava.

    Returns:
        `{"event", "gasto_id", "google_removido", "aviso"}`; a view monta o `resumo`.

    Raises:
        CancelValidationError: as recusas do contrato (400 com `fields`, 409 com `codigo`).
    """
    from app.calendar import sumico_ops
    from app.constants import (
        ALCANCE_TODOS,
        CODIGO_MAX_DEVOLUCAO_MUDOU,
        MODO_TUDO,
        MOTIVO_AJUSTE_RETIDO,
        REGIME_VENDA,
        REGIME_VIRTUAL,
        now_sp,
    )
    from app.financeiro import comissoes_ops
    from app.financeiro.vendas_ops import is_loja_virtual
    from app.models import SiteSetting

    pedido = PedidoDeCancelamento.ler(corpo)
    eventos = travar_grupo(event)  # T1
    ids = [e.id for e in eventos]
    _ler_congelados(ids)  # T2
    _recusas_de_estado(event)
    regime = REGIME_VIRTUAL if is_loja_virtual(event) else REGIME_VENDA
    settings = SiteSetting.query.get(1)
    acrescimos = _travar_acrescimos(event.id) if regime == REGIME_VENDA else []  # T3
    beneficiario = comissoes_ops._beneficiario_comissionado(event, settings)
    _travar_linhas_de_comissao(ids, {getattr(beneficiario, "id", None), *_beneficiarios_das_linhas(ids)})  # T4
    _recusa_da_pendente(_travar_devolucoes(ids))  # T5
    pago, ja_devolvido = _dinheiro_do_grupo(ids)
    maximo = max(Decimal("0.00"), pago - ja_devolvido)
    conta = _conta_do_ato(event, ids, acrescimos, pedido.devolve(maximo) if regime == REGIME_VENDA else Decimal("0.00"), settings)
    erros = _erros_do_pedido(event, pedido, regime=regime, conta=conta)
    if erros:
        raise CancelValidationError("Corrija os campos destacados.", fields=erros)
    if regime == REGIME_VENDA and pedido.modo == MODO_TUDO and pedido.valor != conta.max_devolucao:
        raise CancelValidationError(
            f"O valor a devolver mudou para {_brl(conta.max_devolucao)}: confira antes de cancelar.",
            status=409,
            codigo=CODIGO_MAX_DEVOLUCAO_MUDOU,
            max_devolucao=float(conta.max_devolucao),
        )

    # ── grava ──
    alvos_google = _alvos_do_google([event])
    if event.is_google_missing:
        sumico_ops.desmarcar(event, motivo=sumico_ops.MOTIVO_CANCELADO)
    _gravar_pix_dos_bvs(acrescimos, pedido)
    db.session.flush()
    _congelar(event, regime=regime, pedido=pedido, conta=conta, actor=actor)
    gasto = None
    if regime == REGIME_VENDA:
        gasto = _registrar_devolucao(
            event, valor=conta.devolucao, nome=pedido.nome, pix=pedido.pix, observacao=pedido.observacao, actor=actor
        )
    db.session.flush()
    if regime == REGIME_VENDA:
        comissoes_ops.reconciliar_comissao_do_cancelado(event, conta.alvos, motivo=MOTIVO_AJUSTE_RETIDO)
    event.cancelled_at = now_sp()
    event.cancelled_by_id = actor.id
    event.cancellation_reason = pedido.motivo
    # A solicitação foi atendida: limpa para o evento não ficar marcado como pendente.
    event.deletion_requested_at = None
    event.deletion_requested_by_id = None
    event.deletion_request_reason = None
    ao_cancelar(event, alcance=ALCANCE_TODOS, novo_principal=None)
    detalhe = _texto_do_historico(pedido.motivo, regime, pedido, conta)
    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    # Sem `created_at`: vale o default UTC do modelo, que o histórico da tela converte (FR-016).
    db.session.add(EventLog(event_id=event.id, actor_name=actor.name, actor_role=papel, message=detalhe))
    from app.calendar.routes import _log_sync

    _log_sync("event_cancelled", event, details=detalhe, actor=actor.name, actor_role=papel)
    db.session.flush()
    gasto_id = gasto.id if gasto is not None else None
    db.session.expire(event, ["commission_payments"])
    db.session.commit()

    google_removido, aviso = _remover_do_google(alvos_google)
    return {"event": event, "gasto_id": gasto_id, "google_removido": google_removido, "aviso": aviso}


def elenco_do_ato(event: CalendarEvent, dias: list[int] | None = None) -> list[EventRole]:
    """A régua única das escalações do ato (R18): com talento, sem quem recusou o convite e sem
    a vaga de presença do som. O impacto mostra esta lista; a H6 a grava no congelado."""
    from app.calendar.casting_ops import e_vaga_de_presenca

    ids = dias or [event.id]
    papeis = (
        EventRole.query.filter(EventRole.event_id.in_(ids), EventRole.talent_id.isnot(None))
        .order_by(EventRole.event_id, EventRole.id)
        .all()
    )
    return [r for r in papeis if r.invite_status != "rejected" and not e_vaga_de_presenca(r)]


def resumo_impacto(event: CalendarEvent, *, show_financeiro: bool = True) -> dict[str, Any]:
    """O que será perdido/afetado — a tela mostra isso ANTES de confirmar.

    Foi a falta disso que deixou a exclusão ser uma decisão às cegas: o diálogo antigo só
    perguntava "tem certeza?", sem dizer que havia pagamento recebido e comissão paga em jogo.

    Feature 306 (contracts §2): o regime que o ato daria, o pago e o já devolvido **do grupo**
    (`ids_do_grupo`; `total_recebido` continua o do próprio evento), o máximo a devolver, a nota
    e a alíquota de referência, os BVs, a comissão em jogo e os comprovantes sem valor.
    """
    from app.constants import REGIME_VENDA, REGIME_VIRTUAL, now_sp
    from app.financeiro import comissoes_ops
    from app.financeiro.vendas_ops import is_loja_virtual
    from app.models import EventAcrescimo, SiteSetting

    settings = SiteSetting.query.get(1)
    recebido = total_recebido(event)
    principal_id = event.group_leader_id or event.id
    ids = ids_do_grupo([principal_id])[principal_id]
    pago, ja_devolvido = _dinheiro_do_grupo(ids)
    comissoes = CommissionPayment.query.filter(
        CommissionPayment.event_id == event.id,
        CommissionPayment.status != "cancelado",
    ).order_by(CommissionPayment.id).all()
    gastos = SpecialExpense.query.filter_by(event_id=event.id).all()
    acrescimos = (
        EventAcrescimo.query.filter(EventAcrescimo.event_id == event.id, EventAcrescimo.is_bv.is_(True))
        .order_by(EventAcrescimo.id)
        .all()
    )
    cheia, beneficiario_id, _taxa = comissoes_ops.comissao_cheia_do_evento(event, settings)
    beneficiario = db.session.get(User, beneficiario_id) if beneficiario_id else None
    sem_valor = (
        db.session.query(db.func.count(EventPayment.id))
        .filter(EventPayment.event_id.in_(ids), EventPayment.amount.is_(None))
        .scalar()
    )
    faltam = (event.start_at.date() - now_sp().date()).days if event.start_at else None

    return {
        "acao": "cancelar" if event.is_google_missing or not pode_excluir(event) else "excluir",
        "sale_value": float(event.sale_value or 0),
        "total_recebido": float(recebido),
        "devolucao_sugerida": float(recebido),
        "cliente_nome": event.client.name if event.client else None,
        "elenco": [
            {
                "character_name": r.character_name,
                "talent_name": r.talent.full_name if r.talent else None,
                "cache_value": float(r.cache_value or 0),
                "payment_status": r.payment_status or "nao_pago",
                "role_id": r.id,
                "day_event_id": r.event_id,
                "talent_pix_informado": bool(r.talent and (r.talent.pix_key or "").strip()),
                **({"talent_pix": r.talent.pix_key if r.talent else None} if show_financeiro else {}),
            }
            for r in elenco_do_ato(event)
        ],
        "comissoes": [
            {
                "id": c.id,
                "seller_name": c.seller.name if c.seller else None,
                "amount": float(c.amount or 0),
                "status": c.status,
            }
            for c in comissoes
        ],
        "gastos_vinculados": [
            {"id": g.id, "description": g.description, "amount": float(g.amount or 0)}
            for g in gastos
        ],
        "tem_contrato": EventContract.query.filter_by(event_id=event.id).count() > 0,
        "is_group_leader": event.is_group_leader,
        "regime": REGIME_VIRTUAL if is_loja_virtual(event) else REGIME_VENDA,
        "sumiu_do_google": event.is_google_missing,
        "pago": float(pago),
        "ja_devolvido": float(ja_devolvido),
        "max_devolucao": float(max(Decimal("0.00"), pago - ja_devolvido)),
        "com_nota": bool(event.with_invoice),
        "imposto_aliquota": float(_aliquota(settings)),
        "bvs": [
            {
                "acrescimo_id": a.id,
                "recebedor": a.bv_recipient,
                "cheio": float(a.amount_brl or 0),
                "pago": (a.bv_payment_status or "nao_pago") in ("pago", "no_banco"),
                "falta_recebedor": not (a.bv_recipient or "").strip(),
                "falta_pix": not (a.bv_pix or "").strip(),
            }
            for a in acrescimos
            if a.amount_brl
        ],
        "comissao": {
            "beneficiario": {"id": beneficiario.id, "nome": beneficiario.name} if beneficiario else None,
            "cheia": float(cheia),
            "paga": float(
                sum((Decimal(c.amount or 0) for c in comissoes if c.status in ("pago", "no_banco")), Decimal("0"))
            ),
            "a_pagar": float(sum((Decimal(c.amount or 0) for c in comissoes if c.status == "a_pagar"), Decimal("0"))),
        },
        "faltam_dias": faltam,
        "comprovantes_sem_valor": int(sem_valor or 0),
    }


# ── As correções do cancelado: devolução, dinheiro e a regra única das portas ─────────────────


def limites_da_devolucao(event: CalendarEvent) -> dict[str, float] | None:
    """Piso e teto do "Alterar devolução" no `venda` e no `legado` (data-model §7.2).

    Piso = as devoluções do grupo pagas ou no banco; teto = o pago do grupo. `None` nos regimes
    sem devolução própria (`satelite`, `virtual`).
    """
    from app.constants import REGIME_LEGADO, REGIME_VENDA

    canc = event.cancelamento
    regime = canc.regime if canc is not None else REGIME_LEGADO
    if not event.is_cancelled or regime not in (REGIME_VENDA, REGIME_LEGADO):
        return None
    principal_id = event.group_leader_id or event.id
    ids = ids_do_grupo([principal_id])[principal_id]
    pago, _ = _dinheiro_do_grupo(ids)
    piso = _piso_da_devolucao(
        SpecialExpense.query.filter(filtro_devolucao(), SpecialExpense.event_id.in_(ids)).all()
    )
    return {"piso": float(piso), "teto": float(pago)}


def _piso_da_devolucao(aprovadas: list[SpecialExpense]) -> Decimal:
    """O que já saiu (pago ou no banco) não volta: é o piso do novo total."""
    return _dinheiro(
        sum(
            (_dinheiro(d.amount) for d in aprovadas if (d.payment_status or "nao_pago") in ("pago", "no_banco")),
            Decimal("0"),
        )
    )


def reaplicar_cancelado(event: CalendarEvent, *, motivo: str) -> list[dict]:
    """Refaz a comissão do retido de um cancelado `venda` pelo dinheiro de agora. Não faz commit.

    A cheia, a venda e o beneficiário são os congelados; o retido é o do grupo, ao vivo; o BV do
    retido é lido na hora (`bv_da_planilha`), então não há o que gravar nele. Supõe a T4 tomada.
    """
    from app.constants import REGIME_VENDA
    from app.financeiro import comissoes_ops

    canc = event.cancelamento
    if not event.is_cancelled or canc is None or canc.regime != REGIME_VENDA:
        return []
    db.session.flush()
    resumo = resumo_cancelado(event)
    alvo = comissoes_ops.comissao_do_retido(canc.commission_full, resumo.retido, canc.sale_value)
    alvos = {canc.commission_seller_id: alvo} if canc.commission_seller_id else {}
    plano = comissoes_ops.reconciliar_comissao_do_cancelado(event, alvos, motivo=motivo)
    db.session.expire(event, ["commission_payments"])
    return plano


def reaplicar_por_dinheiro(event: CalendarEvent, *, actor: User) -> None:
    """Depois de um comprovante gravado (decisão (c)): a guarda e o principal refeito. Não faz commit.

    - pago do grupo abaixo do já devolvido → 409 `pago_abaixo_do_devolvido` (em todo cancelado e
      no grupo com algum dia cancelado);
    - principal `venda` cancelado → T4 e `reaplicar_cancelado`, com `EventLog` no dia e no principal.
    """
    from app.constants import CODIGO_PAGO_ABAIXO_DO_DEVOLVIDO, MOTIVO_AJUSTE_RETIDO, REGIME_VENDA

    principal_id = event.group_leader_id or event.id
    ids = ids_do_grupo([principal_id])[principal_id]
    algum_cancelado = (
        db.session.query(CalendarEvent.id)
        .filter(CalendarEvent.id.in_(ids), CalendarEvent.cancelled_at.isnot(None))
        .first()
        is not None
    )
    if not algum_cancelado:
        return
    db.session.flush()
    pago, devolvido = _dinheiro_do_grupo(ids)
    if pago < devolvido:
        raise CancelValidationError(
            f"O pago do grupo ficaria em {_brl(pago)}, abaixo dos {_brl(devolvido)} já devolvidos.",
            status=409,
            codigo=CODIGO_PAGO_ABAIXO_DO_DEVOLVIDO,
            pago=float(pago),
            devolvido=float(devolvido),
        )
    principal = db.session.get(CalendarEvent, principal_id)
    canc = principal.cancelamento if principal is not None else None
    if principal is None or not principal.is_cancelled or canc is None or canc.regime != REGIME_VENDA:
        return
    _travar_linhas_de_comissao(ids, {canc.commission_seller_id, *_beneficiarios_das_linhas(ids)})
    reaplicar_cancelado(principal, motivo=MOTIVO_AJUSTE_RETIDO)
    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    texto = "Comprovante corrigido no cancelado: retido e comissão refeitos pelo pago do grupo."
    for alvo in {principal.id, event.id}:
        db.session.add(EventLog(event_id=alvo, actor_name=actor.name, actor_role=papel, message=texto))


def gravar_comprovante_no_grupo(
    event: CalendarEvent,
    acao: str,
    *,
    actor: User,
    valor: Decimal | None = None,
    arquivo=None,
    comprovante: EventPayment | None = None,
) -> EventPayment | None:
    """O núcleo das três portas de comprovante (decisão (c); contracts §9). Não faz commit.

    T1 também no evento vivo (o comprovante mexe no pago do grupo), relê `is_cancelled`, recusa o
    POST no cancelado para quem não é Superadmin real **antes** de salvar o arquivo, grava e chama
    `reaplicar_por_dinheiro`. Se algo recusar depois de o POST ter salvo o arquivo, o arquivo novo
    é removido aqui mesmo (a view só faz o rollback).

    Args:
        acao: "adicionar", "editar" ou "excluir".

    Raises:
        CancelValidationError: 409 `cancelado`; 400 com `fields` (valor/arquivo); 409
            `pago_abaixo_do_devolvido`.
    """
    from app.calendar.routes import (
        _add_payment_record,
        _delete_payment_record,
        _edit_payment_amount,
    )

    travar_grupo(event)
    if acao == "adicionar" and event.is_cancelled and not pode_editar_venda_do_cancelado(actor):
        raise EventoCanceladoError()
    if acao == "adicionar":
        comprovante = _add_payment_record(event, amount=valor, file_storage=arquivo)
        if comprovante is None:
            raise CancelValidationError(
                "Informe o valor e anexe o comprovante para adicionar o pagamento.",
                fields={"amount": "Obrigatório", "file": "Obrigatório"},
            )
    elif acao == "editar":
        if not _edit_payment_amount(comprovante, amount=valor):
            raise CancelValidationError(
                "Informe um valor válido para o comprovante", fields={"amount": "Obrigatório"}
            )
    else:
        _delete_payment_record(comprovante)
    try:
        db.session.flush()
        reaplicar_por_dinheiro(event, actor=actor)
    except Exception:
        if acao == "adicionar" and comprovante is not None and comprovante.file_path:
            from app.storage import delete_file

            delete_file(comprovante.file_path)
        raise
    return comprovante if acao != "excluir" else None


def recusar_se_cancelado(event: CalendarEvent, user: User) -> None:
    """A regra única das portas (a)–(h) (FR-047): trava o evento, relê e recusa o cancelado.

    Quem não é Superadmin real leva 409 `cancelado`. No vivo, o caminho de hoje segue sob a trava.
    """
    from app.calendar.orcamento_evento_ops import travar_evento

    travar_evento(event)
    if event.is_cancelled and not pode_editar_venda_do_cancelado(user):
        raise EventoCanceladoError()


def _dono_das_aberta(aprovadas: list[SpecialExpense], dono_id: int) -> list[SpecialExpense]:
    """As devoluções ainda não pagas, a do dono primeiro e as outras por id (R12)."""
    abertas = [d for d in aprovadas if (d.payment_status or "nao_pago") == "nao_pago"]
    return sorted(abertas, key=lambda d: (d.event_id != dono_id, d.id))


def _aplicar_novo_total(
    dono: CalendarEvent,
    aprovadas: list[SpecialExpense],
    total: Decimal,
    *,
    nome: str,
    pix: str,
    observacao: str,
    actor: User,
) -> None:
    """O helper único da gravação (data-model §7.2). Não faz commit.

    A aberta absorve a diferença e fica uma só (a do dono primeiro); zerada, é excluída com
    auditoria; sem aberta e acima do que já está, nasce o complemento. Tocar uma devolução regrava
    `disbursement_type="cliente"` e completa nome e PIX vazios (FR-020).
    """
    from app.gastos.gastos_ops import _log

    atual = _dinheiro(sum((_dinheiro(d.amount) for d in aprovadas), Decimal("0")))
    diferenca = total - atual
    abertas = _dono_das_aberta(aprovadas, dono.id)
    herdado = next((d for d in reversed(aprovadas) if d.supplier_name or d.supplier_pix), None)
    for d in abertas:
        d.disbursement_type = "cliente"
        d.supplier_name = d.supplier_name or (nome[:200] or None)
        d.supplier_pix = d.supplier_pix or (pix[:120] or None)
    if diferenca == 0:
        return
    if abertas:
        fica, *demais = abertas
        novo = _dinheiro(sum((_dinheiro(d.amount) for d in abertas), Decimal("0")) + diferenca)
        for d in demais:
            _log(actor, "SpecialExpense", d.id, d.description, "excluiu", "Devolução juntada no Alterar devolução")
            db.session.delete(d)
        if novo <= 0:
            _log(actor, "SpecialExpense", fica.id, fica.description, "excluiu", "Devolução zerada no Alterar devolução")
            db.session.delete(fica)
            return
        antes = _dinheiro(fica.amount)
        fica.amount = novo
        if observacao:
            fica.notes = observacao
        _log(
            actor, "SpecialExpense", fica.id, fica.description, "editou",
            f"Alterar devolução: {_brl(antes)} → {_brl(novo)}",
        )  # fmt: skip
        return
    if diferenca > 0:
        gasto = _registrar_devolucao(
            dono,
            valor=diferenca,
            nome=nome or (herdado.supplier_name if herdado else "") or "",
            pix=pix or (herdado.supplier_pix if herdado else "") or "",
            observacao=observacao,
            actor=actor,
        )
        db.session.flush()
        _log(actor, "SpecialExpense", gasto.id, gasto.description, "criou", f"Complemento de devolução {_brl(diferenca)}")


def alterar_devolucao(event: CalendarEvent, *, corpo: dict[str, Any] | None, actor: User) -> CalendarEvent:
    """O "Alterar devolução" do cancelado `venda` e `legado` (FR-017; contracts §3). Não faz commit.

    O regime só se lê depois de T1: antes da trava, só a forma de `devolucao_total`. Depois:
    T1 → T2 → T4 (no `venda`) → T5 → 409 `nao_cancelado` → 409 `regime_sem_retido` → 400 com
    todos os campos → 409 `abaixo_do_piso` → grava → `reaplicar_cancelado`.
    """
    from app.constants import (
        CODIGO_ABAIXO_DO_PISO,
        CODIGO_NAO_CANCELADO,
        CODIGO_REGIME_SEM_RETIDO,
        MOTIVO_AJUSTE_RETIDO,
        REGIME_LEGADO,
        REGIME_VENDA,
        now_sp,
    )

    corpo = corpo if isinstance(corpo, dict) else {}
    total, invalido = _decimal(corpo.get("devolucao_total"))
    if total is None or invalido:
        raise CancelValidationError("Informe o novo total devolvido.", field="devolucao_total")
    nome, pix, observacao = _texto(corpo.get("nome")), _texto(corpo.get("pix")), _texto(corpo.get("observacao"))
    imposto, imposto_invalido = _decimal(corpo.get("imposto_retido"))
    imposto_enviado = corpo.get("imposto_retido") is not None

    eventos = travar_grupo(event)  # T1
    ids = [e.id for e in eventos]
    congelados = _ler_congelados(ids)  # T2
    if not event.is_cancelled:
        raise CancelValidationError("Este evento não está cancelado.", status=409, codigo=CODIGO_NAO_CANCELADO)
    canc = congelados.get(event.id)
    regime = canc.regime if canc is not None else REGIME_LEGADO
    if regime not in (REGIME_VENDA, REGIME_LEGADO):
        raise CancelValidationError(
            "Este cancelamento não tem devolução própria para alterar.",
            status=409,
            codigo=CODIGO_REGIME_SEM_RETIDO,
        )
    if regime == REGIME_VENDA:
        _travar_linhas_de_comissao(ids, {canc.commission_seller_id, *_beneficiarios_das_linhas(ids)})  # T4
    devolucoes = _travar_devolucoes(ids)  # T5
    aprovadas = [d for d in devolucoes if d.status == "aprovado"]
    pago, _ = _dinheiro_do_grupo(ids)

    erros: dict[str, str] = {}
    if total < 0:
        erros["devolucao_total"] = "O total devolvido não pode ser negativo."
    elif total > pago:
        erros["devolucao_total"] = f"Acima do que a cliente pagou ({_brl(pago)})."
    atual = _dinheiro(sum((_dinheiro(d.amount) for d in aprovadas), Decimal("0")))
    nasce_complemento = total > atual and not _dono_das_aberta(aprovadas, event.id)
    herdado = next((d for d in reversed(aprovadas) if d.supplier_name or d.supplier_pix), None)
    if len(nome) > 200:
        erros["devolucao_nome"] = "Quem recebe: até 200 caracteres."
    elif nasce_complemento and not (nome or (herdado and herdado.supplier_name)):
        erros["devolucao_nome"] = "Informe quem recebe a devolução."
    if len(pix) > 120:
        erros["devolucao_pix"] = "PIX: até 120 caracteres."
    elif nasce_complemento and not (pix or (herdado and herdado.supplier_pix)):
        erros["devolucao_pix"] = "Informe o PIX da devolução."
    if imposto_enviado:
        if regime != REGIME_VENDA or not canc.with_invoice:
            erros["imposto_retido"] = "Este cancelamento não tem imposto a reter."
        elif imposto_invalido or imposto is None or imposto < 0:
            erros["imposto_retido"] = "Informe o imposto retido em reais (0 se não houve)."
    if erros:
        raise CancelValidationError("Corrija os campos destacados.", fields=erros)
    piso = _piso_da_devolucao(aprovadas)
    if total < piso:
        raise CancelValidationError(
            f"Já saíram {_brl(piso)} de devolução (pagos ou no banco): o novo total não pode ser menor.",
            status=409,
            codigo=CODIGO_ABAIXO_DO_PISO,
            piso=float(piso),
        )

    _aplicar_novo_total(event, aprovadas, total, nome=nome, pix=pix, observacao=observacao, actor=actor)
    if regime == REGIME_VENDA:
        if imposto_enviado:
            canc.retained_tax = imposto
        canc.updated_at = now_sp()
        canc.updated_by_id = actor.id
        reaplicar_cancelado(event, motivo=MOTIVO_AJUSTE_RETIDO)
    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    db.session.add(
        EventLog(
            event_id=event.id,
            actor_name=actor.name,
            actor_role=papel,
            message=f"Alterou a devolução à cliente: {_brl(atual)} → {_brl(total)}",
        )
    )
    return event


def marcar_status_da_devolucao(
    exp_id: int, status: str, *, valor_esperado: Any, actor_name: str
) -> SpecialExpense | None:
    """O status de pagamento da devolução de um cancelado na Planilha, no molde de
    `marcar_status_do_bv` (contracts §17). Não faz commit.

    Trava o evento e relê o gasto; ao marcar pago ou no banco, `valor_esperado` diferente do valor
    de agora → 409 `valor_mudou`. Fora da devolução de cancelado, devolve `None` e a porta segue o
    caminho de hoje.
    """
    from app.calendar.orcamento_evento_ops import travar_evento
    from app.constants import CODIGO_VALOR_MUDOU
    from app.utils import audit

    gasto = db.session.get(SpecialExpense, exp_id) if exp_id is not None else None
    if gasto is None or gasto.category != SpecialExpense.CATEGORY_DEVOLUCAO or gasto.event_id is None:
        return None
    evento = db.session.get(CalendarEvent, gasto.event_id)
    if evento is None or not evento.is_cancelled:
        return None
    esperado = None
    if valor_esperado is not None and not isinstance(valor_esperado, bool):
        esperado, invalido = _decimal(valor_esperado)
        if invalido:
            raise CancelValidationError("Valor esperado inválido.")
    travar_evento(evento)
    gasto = (
        SpecialExpense.query.filter(SpecialExpense.id == exp_id).with_for_update().populate_existing().one()
    )
    if status in ("pago", "no_banco") and esperado is not None and esperado != _dinheiro(gasto.amount):
        raise CancelValidationError(
            f"A devolução mudou para {_brl(gasto.amount)} desde que a Planilha abriu: recarregue e "
            "confira antes de marcar.",
            status=409,
            codigo=CODIGO_VALOR_MUDOU,
            atual=float(gasto.amount or 0),
        )
    antes = gasto.payment_status
    gasto.payment_status = status
    audit(
        "payment",
        "special_expense",
        gasto.id,
        gasto.payee_name,
        f"Devolução de cancelado: {antes} → {status}, {_brl(gasto.amount)}"
        + (f" (por {actor_name})" if actor_name else ""),
    )
    return gasto


def pode_excluir(event: CalendarEvent) -> bool:
    """True se o evento pode ser apagado de verdade, sem perder nada que importe.

    Só é seguro apagar o que está **vazio**: sem valor de venda, sem nenhum pagamento recebido,
    sem contrato e sem ninguém escalado. Qualquer coisa presa ali é histórico que precisa
    sobreviver — nesse caso o caminho é o cancelamento.
    """
    if event.sale_value and Decimal(event.sale_value) > 0:
        return False
    if total_recebido(event) > 0:
        return False
    if EventContract.query.filter_by(event_id=event.id).count() > 0:
        return False
    if EventRole.query.filter(
        EventRole.event_id == event.id, EventRole.talent_id.isnot(None)
    ).count() > 0:
        return False
    return True


def aplicar_estorno_comissao(event: CalendarEvent) -> None:
    """Resolve as comissões de um evento que vai ser excluído. Não faz commit.

    Extraído de `_delete_event` (`app/calendar/routes.py`) na feature 224:

    - comissão ainda `a_pagar` é cancelada e desvinculada;
    - comissão já paga **ou no banco** (feature 306) gera um **estorno órfão** negativo `a_pagar`,
      ligado a ela (`original_id`), que a Planilha desconta do repasse do vendedor.

    Feature 306 (FR-036): o estorno nasce no **primeiro repasse aberto** do vendedor
    (`primeiro_repasse_aberto`), com `sale_date = payable_from` = essa data e o motivo "Exclusão do
    evento". Antes ele copiava as datas da venda e caía num repasse que já tinha saído (o estorno
    211 nasceu em 17/09 com data de 21/08). As datas são calculadas antes de qualquer mudança: o
    autoflush de um estorno recém-criado mudaria a conta do seguinte.
    """
    from app.constants import MOTIVO_AJUSTE_EXCLUSAO, now_sp
    from app.financeiro import comissoes_ops

    hoje = now_sp().date()
    linhas = CommissionPayment.query.filter_by(event_id=event.id).order_by(CommissionPayment.id).all()
    datas = {
        cp.id: comissoes_ops.primeiro_repasse_aberto(cp.seller_id, hoje, excluir_event_id=event.id)
        for cp in linhas
        if cp.status in ("pago", "no_banco")
    }
    for cp in linhas:
        if cp.status == "a_pagar":
            cp.status = "cancelado"
            cp.event_id = None  # desvincula antes do delete do evento
        elif cp.status in ("pago", "no_banco"):
            db.session.add(
                CommissionPayment(
                    event_id=None,
                    event_title=cp.event_title,
                    seller_id=cp.seller_id,
                    sale_date=datas[cp.id],
                    payable_from=datas[cp.id],
                    amount=-cp.amount,
                    status="a_pagar",
                    original_id=cp.id,
                    notes=comissoes_ops._nota_do_ajuste(MOTIVO_AJUSTE_EXCLUSAO, "estorno automático"),
                )
            )
            cp.event_id = None


def solicitar_exclusao(event: CalendarEvent, *, motivo: str, actor: User) -> None:
    """Registra o pedido do Comercial. O Superadmin decide depois. Commita."""
    motivo = (motivo or "").strip()
    if not motivo:
        raise CancelValidationError("Explique o motivo da exclusão.")
    if event.is_cancelled:
        raise CancelValidationError("Este evento já está cancelado.")

    agora = datetime.now(tz=TZ).replace(tzinfo=None)
    event.deletion_requested_at = agora
    event.deletion_requested_by_id = actor.id
    event.deletion_request_reason = motivo
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor.name,
        actor_role=", ".join(r.name for r in actor.roles),
        message=f"Solicitou a exclusão do evento: {motivo}",
        created_at=agora,
    ))
    db.session.commit()


def recusar_solicitacao(event: CalendarEvent, *, actor: User, motivo: str = "") -> None:
    """Superadmin recusa o pedido — os campos da solicitação voltam a nulo. Commita."""
    if event.deletion_requested_at is None:
        raise CancelValidationError("Não há solicitação de exclusão neste evento.")

    agora = datetime.now(tz=TZ).replace(tzinfo=None)
    sufixo = f": {motivo.strip()}" if (motivo or "").strip() else "."
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor.name,
        actor_role=", ".join(r.name for r in actor.roles),
        message=f"Recusou a solicitação de exclusão{sufixo}",
        created_at=agora,
    ))
    event.deletion_requested_at = None
    event.deletion_requested_by_id = None
    event.deletion_request_reason = None
    db.session.commit()


def listar_cancelamentos(*, flags: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Fila do Superadmin: solicitações pendentes + eventos já cancelados.

    Feature 306 (contracts §15): cada cancelado ganha o `resumo`, montado em lote, com todas as
    devoluções e o PIX só com `show_financeiro`. O campo `devolucao` fica por um ciclo.
    """
    pendentes = (
        CalendarEvent.query.filter(
            CalendarEvent.deletion_requested_at.isnot(None),
            CalendarEvent.cancelled_at.is_(None),
        )
        .order_by(CalendarEvent.deletion_requested_at.desc())
        .all()
    )
    cancelados = (
        CalendarEvent.query.filter(CalendarEvent.cancelled_at.isnot(None))
        .order_by(CalendarEvent.cancelled_at.desc())
        .limit(200)
        .all()
    )

    resumos = resumos_cancelados([e.id for e in cancelados])

    def _devolucao(event: CalendarEvent) -> dict[str, Any] | None:
        # O campo fica por um ciclo (contracts §15); o `resumo` em lote é quem traz todas.
        gasto = (
            SpecialExpense.query.filter(filtro_devolucao(), SpecialExpense.event_id == event.id)
            .order_by(SpecialExpense.id)
            .first()
        )
        if gasto is None:
            return None
        return {
            "id": gasto.id,
            "amount": float(gasto.amount or 0),
            "payee_name": gasto.payee_name,
            "payment_status": gasto.payment_status,
        }

    return {
        "pendentes": [
            {
                "id": e.id,
                "title": e.title,
                "start_at": e.start_at.isoformat() if e.start_at else None,
                "sale_value": float(e.sale_value or 0),
                "requested_at": e.deletion_requested_at.isoformat(),
                "requested_by": (
                    db.session.get(User, e.deletion_requested_by_id).name
                    if e.deletion_requested_by_id else None
                ),
                "reason": e.deletion_request_reason,
            }
            for e in pendentes
        ],
        "cancelados": [
            {
                "id": e.id,
                "title": e.title,
                "start_at": e.start_at.isoformat() if e.start_at else None,
                "sale_value": float(e.sale_value or 0),
                "cancelled_at": e.cancelled_at.isoformat(),
                "cancelled_by": (
                    db.session.get(User, e.cancelled_by_id).name if e.cancelled_by_id else None
                ),
                "reason": e.cancellation_reason,
                "devolucao": _devolucao(e),
                "resumo": serializar_resumo_cancelado(resumos[e.id], flags or {}) if e.id in resumos else None,
            }
            for e in cancelados
        ],
    }
