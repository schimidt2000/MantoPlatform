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
    """Cancelar ou excluir um evento marcado "Sumiu do Google Agenda" (feature 303).

    Nesta entrega nenhum cancelamento de evento marcado sai com a regra velha (decisão do dono,
    30/09): o evento marcado só tem uma saída, devolver ao Google Agenda. A segunda entrega troca
    esta recusa pelo "Cancelar e devolver o dinheiro". O texto mora aqui, uma vez: a API e o
    wrapper Jinja leem `exc.message`.
    """

    MENSAGEM = (
        "Este evento sumiu do Google Agenda. O cancelamento com devolução do dinheiro chega na "
        "próxima entrega — por enquanto, devolva-o ao Google Agenda."
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


def resumo_impacto(event: CalendarEvent) -> dict[str, Any]:
    """O que será perdido/afetado — a tela mostra isso ANTES de confirmar.

    Foi a falta disso que deixou a exclusão ser uma decisão às cegas: o diálogo antigo só
    perguntava "tem certeza?", sem dizer que havia pagamento recebido e comissão paga em jogo.
    """
    recebido = total_recebido(event)
    escalados = (
        EventRole.query.filter(
            EventRole.event_id == event.id, EventRole.talent_id.isnot(None)
        ).all()
    )
    comissoes = CommissionPayment.query.filter(
        CommissionPayment.event_id == event.id,
        CommissionPayment.status != "cancelado",
    ).all()
    gastos = SpecialExpense.query.filter_by(event_id=event.id).all()

    return {
        "acao": "excluir" if pode_excluir(event) else "cancelar",
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
            }
            for r in escalados
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
    }


def aplicar_estorno_comissao(event: CalendarEvent) -> None:
    """Resolve as comissões de um evento que deixou de valer. Não faz commit.

    Extraído de `_delete_event` (`app/calendar/routes.py`) para que exclusão e cancelamento
    usem a MESMA regra — a lógica não pode viver só no caminho que apaga:

    - comissão ainda `a_pagar` é cancelada e desvinculada;
    - comissão já `paga` gera um **estorno negativo** `a_pagar`, que a Planilha de Pagamentos
      desconta do próximo repasse do vendedor (via `_seller_payable_rows`, que junta estornos
      pendentes de qualquer mês).
    """
    for cp in list(CommissionPayment.query.filter_by(event_id=event.id).all()):
        if cp.status == "a_pagar":
            cp.status = "cancelado"
            cp.event_id = None  # desvincula antes do delete do evento
        elif cp.status == "pago":
            db.session.add(CommissionPayment(
                event_id=None,
                event_title=cp.event_title,
                seller_id=cp.seller_id,
                sale_date=cp.sale_date,
                payable_from=cp.payable_from,
                amount=-cp.amount,
                status="a_pagar",
                original_id=cp.id,
                notes="Estorno automático: evento cancelado",
            ))
            cp.event_id = None


def _registrar_devolucao(
    event: CalendarEvent,
    devolucao: dict[str, Any],
    actor: User,
) -> SpecialExpense | None:
    """Cria o Gasto Extra da devolução à cliente. Não faz commit.

    Nasce **aprovado** porque quem cancela já é Superadmin — pedir uma segunda aprovação da
    mesma pessoa só atrasaria o repasse. Aprovado, ele entra sozinho na Planilha de Pagamentos e
    na DRE do mês, que já somam `SpecialExpense` do período.
    """
    valor = Decimal(str(devolucao.get("valor") or 0))
    if valor <= 0:
        return None

    agora = datetime.now(tz=TZ).replace(tzinfo=None)
    gasto = SpecialExpense(
        description=f"Devolução à cliente — {event.title}"[:200],
        category=SpecialExpense.CATEGORY_DEVOLUCAO,
        amount=valor,
        expense_date=agora.date(),
        status="aprovado",
        notes=(devolucao.get("observacao") or "").strip() or None,
        created_by_id=actor.id,
        approved_by_id=actor.id,
        approved_at=agora,
        disbursement_type="cliente",
        supplier_name=(devolucao.get("nome") or "").strip()[:200] or None,
        supplier_pix=(devolucao.get("pix") or "").strip()[:120] or None,
        payment_status="nao_pago",
        event_id=event.id,
    )
    db.session.add(gasto)
    return gasto


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


def cancelar_evento(
    event: CalendarEvent,
    *,
    motivo: str,
    devolucao: dict[str, Any] | None,
    actor: User,
    remover_do_google: bool = True,
) -> dict[str, Any]:
    """Cancela o evento, resolve a comissão e registra a devolução. Commita.

    O evento **não** é apagado: `cancelled_at` o tira da agenda e de toda métrica, mas elenco,
    pagamentos recebidos e contrato continuam ali para consulta — é o que dá lastro à devolução.

    Args:
        event: Evento a cancelar.
        motivo: Por que está sendo cancelado (obrigatório — vai para o log e para a tela).
        devolucao: `{"valor", "nome", "pix", "observacao"}`; valor 0/ausente = nada a devolver.
        actor: Quem está cancelando (Superadmin).
        remover_do_google: Tira o evento do Google Agenda. Falso quando ele já sumiu de lá.

    Returns:
        `{"gasto_id": int | None, "google_removido": bool, "aviso": str | None}`.

    Raises:
        EventoMarcadoError: evento marcado "Sumiu do Google Agenda" (feature 303), para qualquer
            papel — vem antes de tudo, para a recusa não depender do corpo.
        CancelValidationError: motivo vazio, evento já cancelado, ou evento líder de grupo.
    """
    if event.is_google_missing:
        raise EventoMarcadoError()
    motivo = (motivo or "").strip()
    if not motivo:
        raise CancelValidationError("Explique o motivo do cancelamento.")
    if event.is_cancelled:
        raise CancelValidationError("Este evento já está cancelado.")
    if event.is_group_leader:
        raise CancelValidationError(
            "Desagrupe os eventos satélites antes de cancelar este evento."
        )

    agora = datetime.now(tz=TZ).replace(tzinfo=None)
    aplicar_estorno_comissao(event)
    gasto = _registrar_devolucao(event, devolucao or {}, actor)

    aviso: str | None = None
    google_removido = False
    if remover_do_google and event.google_event_id:
        from app.calendar.routes import CALENDAR_ID
        from app.calendar.service import delete_event as gcal_delete

        try:
            gcal_delete(CALENDAR_ID, event.google_event_id)
            google_removido = True
        except Exception as exc:  # noqa: BLE001 — falha do Google não trava o cancelamento
            aviso = f"Cancelado no sistema, mas não foi possível remover do Google Agenda: {exc}"

    event.cancelled_at = agora
    event.cancelled_by_id = actor.id
    event.cancellation_reason = motivo
    # A solicitação foi atendida: limpa para o evento não ficar marcado como pendente.
    event.deletion_requested_at = None
    event.deletion_requested_by_id = None
    event.deletion_request_reason = None

    detalhe = f"Evento cancelado: {motivo}"
    if gasto is not None:
        detalhe += f" | devolução de R$ {gasto.amount} registrada para {gasto.payee_name}"
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor.name,
        actor_role=", ".join(r.name for r in actor.roles),
        message=detalhe,
        created_at=agora,
    ))

    from app.calendar.routes import _log_sync

    _log_sync(
        "event_cancelled", event, details=detalhe,
        actor=actor.name, actor_role=", ".join(r.name for r in actor.roles),
    )
    db.session.commit()

    return {
        "gasto_id": gasto.id if gasto is not None else None,
        "google_removido": google_removido,
        "aviso": aviso,
    }


def listar_cancelamentos() -> dict[str, list[dict[str, Any]]]:
    """Fila do Superadmin: solicitações pendentes + eventos já cancelados."""
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
            }
            for e in cancelados
        ],
    }
