"""Núcleo do cancelamento de evento e da solicitação de exclusão (feature 224).

Existe porque apagar um evento que já recebeu dinheiro destrói a única prova de que o dinheiro
entrou: `_clear_event_side_tables` (`app/calendar/routes.py`) remove os `EventPayment` junto, e
depois disso não há a que a devolução se referir. Foi exatamente o que aconteceu com o
`(SHOW) PETER PAN...` em 07/08/2026, apagado pelo sync depois de sumir do Google Agenda.

A regra: evento **vazio** (sem venda, sem pagamento, sem contrato e sem elenco escalado) continua
sendo excluído de verdade — é o caso do evento criado por engano. Evento com qualquer uma dessas
coisas presa, ou marcado "Sumiu do Google Agenda", vira **cancelado**: o registro fica e sai da
agenda e das métricas do evento (via `cancelled_at`). O que a Manto reteve (pago − devolvido)
entra na DRE, no Comercial e na comissão pelo mês do cancelamento (feature 306), e a devolução à
cliente nasce vinculada a ele.

Funções puras no sentido do projeto: sem `flask.request`/`render_template`/`flash`. Os
adaptadores (`app/api/agenda_write.py`) é que traduzem em resposta HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
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


def pode_editar_motivo_do_cancelado(user: User | None) -> bool:
    """Feature 306b: o texto do motivo, Superadmin ou Comercial pelo papel REAL ("Ver como" não conta)."""
    from app.constants import RoleName

    papeis = {RoleName.SUPERADMIN, RoleName.COMERCIAL}
    return bool(user) and any(r.name.upper() in papeis for r in user.roles)


# Os prefixos que o ato grava antes do motivo no `EventLog` e no `AuditLog` (224, 306: o ato, o dia
# satélite do "todos os dias" e o corte de um dia). O motivo só é trocado logo depois de um deles e
# seguido de " | " ou do fim da linha — nunca solto no meio de outro texto.
_PREFIXOS_DO_MOTIVO = (r"Evento cancelado: ", r"Dia cancelado: ", r'Evento cancelado com todos os dias do grupo de "[^"\n]*": ')


def _trocar_motivo_no_texto(texto: str, antigo: str, novo: str) -> str:
    """O texto com `antigo` trocado por `novo` onde ele é o motivo de uma linha do ato."""
    import re

    for prefixo in _PREFIXOS_DO_MOTIVO:
        padrao = re.compile(f"({prefixo}){re.escape(antigo)}(?= \\| |$)")
        texto = padrao.sub(lambda m: m.group(1) + novo, texto)
    return texto


def editar_motivo_do_cancelado(event: CalendarEvent, *, corpo: dict[str, Any] | None, actor: User) -> list[int]:
    """Troca o motivo do cancelamento (feature 306b). Sem commit.

    O motivo é do ato: vale para o evento e para os dias do mesmo grupo cancelados com o mesmo
    texto. Nas linhas do histórico desses dias (`EventLog` e o `event_cancelled` do `AuditLog`), o
    motivo antigo vira o novo; cada dia ganha "Editou o motivo do cancelamento", sem o texto antigo
    (o dono, 20/10: o motivo antigo some de toda tela). Dinheiro, avisos e Google não mudam.
    T1 → 409 `nao_cancelado` → 400 `fields.motivo`.

    Returns:
        Os ids dos dias que receberam o motivo novo, em ordem.
    """
    from app.calendar.routes import _log_sync
    from app.constants import CODIGO_NAO_CANCELADO
    from app.models import AuditLog

    corpo = corpo if isinstance(corpo, dict) else {}
    eventos = travar_grupo(event)  # T1
    if not event.is_cancelled:
        raise CancelValidationError("Este evento não está cancelado.", status=409, codigo=CODIGO_NAO_CANCELADO)
    novo = _texto(corpo.get("motivo"))
    if not novo:
        raise CancelValidationError("Informe o motivo do cancelamento.", field="motivo")
    antigo = event.cancellation_reason or ""
    dias = [
        e for e in eventos if e.id == event.id or (antigo and e.is_cancelled and e.cancellation_reason == antigo)
    ]
    if novo == antigo:
        return sorted(e.id for e in dias)

    ids = sorted(e.id for e in dias)
    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    if antigo:
        for linha in EventLog.query.filter(EventLog.event_id.in_(ids)).all():
            trocado = _trocar_motivo_no_texto(linha.message, antigo, novo)
            if trocado != linha.message:
                linha.message = trocado
        auditoria = AuditLog.query.filter(
            AuditLog.entity_type == "agenda",
            AuditLog.entity_id.in_(ids),
            AuditLog.action == "event_cancelled",
        ).all()
        for linha in auditoria:
            trocado = _trocar_motivo_no_texto(linha.detail or "", antigo, novo)
            if trocado != (linha.detail or ""):
                linha.detail = trocado
    for dia in dias:
        dia.cancellation_reason = novo
        db.session.add(
            EventLog(event_id=dia.id, actor_name=actor.name, actor_role=papel, message="Editou o motivo do cancelamento")
        )
        _log_sync("event_cancel_reason_edited", dia, details="Editou o motivo do cancelamento", actor=actor.name, actor_role=papel)
    return ids


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
    """As devoluções aprovadas (`filtro_devolucao`) dos ids, numa consulta só, por id do evento.

    Só as aprovadas (data-model §5): a rejeitada antes do ato aparecia "a pagar" na tela do cancelado
    e na página de Cancelamentos, sem ser dinheiro devido (converge, T109).
    """
    if not ids:
        return {}
    out: dict[int, list[SpecialExpense]] = {}
    linhas = (
        SpecialExpense.query.filter(filtro_devolucao(), SpecialExpense.event_id.in_(ids))
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
        """Sem venda, sem pago e sem devolvido, o cancelado não entra em DRE nem no Comercial (P-24;
        FR-044). O de venda sem pagamento conta: na contagem, no painel e no BV pago do custo."""
        return (self.venda or Decimal("0")) > 0 or self.pago > 0 or self.devolvido > 0


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


def painel_de_cancelamentos(
    resumos: list[ResumoCancelado],
    *,
    totais: dict[str, Any] | None = None,
    commission_target_id: int | None = None,
    com_imposto: bool = True,
) -> dict[str, Any]:
    """O card "Cancelamentos do período" (feature 312): a mesma forma na DRE e no Comercial.

    Os totais são os de `totais_cancelamentos` (a DRE passa os que já somou na cascata, para o card
    e a linha "Retido de cancelamentos" serem o mesmo número). A comissão do retido segue a régua
    do KPI do Comercial (`vendas_ops.build_kpis`): com `commission_target_id`, só a do beneficiário
    alvo. `imposto` e `efeito_resultado` só com `com_imposto` (Q1 do dono: Superadmin e Financeiro).
    JSON-safe (floats).
    """
    from app.financeiro.vendas_ops import event_payment_status

    totais = totais if totais is not None else totais_cancelamentos(resumos)
    status = event_payment_status(0, 0, False, cancelado=True)  # o rótulo do cancelado (306)

    def _do_alvo(r: ResumoCancelado) -> bool:
        return commission_target_id is None or (
            r.beneficiario is not None and r.beneficiario.id == commission_target_id
        )

    comissao = (
        totais["comissao_retido"]
        if commission_target_id is None
        else sum((r.comissao_retido for r in resumos if _do_alvo(r)), Decimal("0.00"))
    )
    nomes = {
        u.id: u.name
        for u in User.query.filter(User.id.in_({r.seller_id for r in resumos if r.seller_id} or {-1})).all()
    }
    painel: dict[str, Any] = {
        "quantidade": totais["quantidade"],
        "pago": float(totais["pago"]),
        "devolvido": float(totais["devolvido"]),
        "devolucao_a_pagar": float(totais["devolucao_a_pagar"]),
        "retido": float(totais["retido"]),
        "comissao_retido": float(comissao),
        "bv_retido": float(totais["bv_retido"]),
        "itens": [
            {
                "event_id": r.event.id,
                "titulo": r.event.title,
                "event_date": r.event.start_at.isoformat() if r.event.start_at else None,
                "cancelado_em": r.cancelado_em.isoformat() if r.cancelado_em else None,
                "seller_name": nomes.get(r.seller_id),
                "pago": float(r.pago),
                "devolvido": float(r.devolvido),
                "devolucao_a_pagar": float(sum(
                    (_dinheiro(g.amount) for g in r.devolucoes
                     if g.status == "aprovado" and (g.payment_status or "nao_pago") != "pago"),
                    Decimal("0.00"),
                )),
                "retido": float(r.retido),
                "comissao_retido": float(r.comissao_retido if _do_alvo(r) else Decimal("0.00")),
                "status": status,
            }
            for r in resumos
        ],
    }
    if com_imposto:
        painel["imposto"] = float(totais["imposto"])
        painel["efeito_resultado"] = float(totais["efeito_resultado"])
    return painel


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
            "Outra pessoa alterou este evento ao mesmo tempo: tente novamente.",
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
    try:
        # `1e26` passa no `Decimal` e estoura no `quantize` (precisão 28): é inválido, não 500.
        return numero.quantize(_CENTAVO), False
    except ArithmeticError:
        return None, True


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
    # Feature 306, H5 (contracts §1, itens 5–7 e 10): o grupo.
    alcance: str | None = None
    alcance_enviado: bool = False
    novo_principal_id: int | None = None
    venda_nova: Decimal | None = None
    venda_nova_invalida: bool = False
    # A venda do grupo que o diálogo mostrou: outro corte (ou a aba Comercial) no meio dá 409.
    venda_esperada: Decimal | None = None
    # H6 (contracts §1): a multa por escalação no ato, `{role_id: (valor, inválido, talent_id visto)}`.
    multas: dict[int, tuple[Decimal | None, bool, int | None]] = field(default_factory=dict)
    multas_malformadas: bool = False

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
        venda_nova, venda_nova_invalida = _decimal(corpo.get("venda_nova"))
        multas: dict[int, tuple[Decimal | None, bool, int | None]] = {}
        brutas = corpo.get("multas")
        multas_malformadas = brutas is not None and not isinstance(brutas, list)
        for item in brutas if isinstance(brutas, list) else []:
            rid = item.get("role_id") if isinstance(item, dict) else None
            if not isinstance(rid, int) or isinstance(rid, bool):
                multas_malformadas = True
                continue
            visto = item.get("talent_id")
            visto = visto if isinstance(visto, int) and not isinstance(visto, bool) else None
            multas[rid] = (*_decimal(item.get("valor")), visto)
        alcance = corpo.get("alcance")
        novo = corpo.get("novo_principal_id")
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
            alcance=alcance if isinstance(alcance, str) else None,
            alcance_enviado=corpo.get("alcance") is not None,
            novo_principal_id=novo if isinstance(novo, int) and not isinstance(novo, bool) else None,
            venda_nova=venda_nova,
            venda_nova_invalida=venda_nova_invalida,
            venda_esperada=_decimal(corpo.get("venda_esperada"))[0],
            multas=multas,
            multas_malformadas=multas_malformadas,
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


# ── O grupo: a forma do ato e a conta do corte (H5; FR-054–FR-058) ──────────────────────────


@dataclass
class FormaDoAto:
    """Quem o ato cancela e onde a venda fica (contracts §1, itens 5–7).

    - `avulso`: o evento sem outro dia vivo (o principal de um grupo já todo cortado inclusive);
    - `todos`: o principal e todos os dias vivos (o principal em `venda`; os outros em `satelite`);
    - `corte`: um dia do grupo que não é o principal (`dia`); a venda fica no principal, menor;
    - `passagem`: só o 1º dia (`dia`); a venda passa ao novo 1º dia, o dia vivo mais cedo.
    """

    tipo: str
    principal: CalendarEvent  # o dono da venda no momento do ato
    dias: list[CalendarEvent]  # os que o ato cancela, o da URL primeiro
    vivo: CalendarEvent | None = None  # o principal que continua vivo (corte e passagem)

    @property
    def corta(self) -> bool:
        return self.tipo in ("corte", "passagem")


def _grupo_mudou(**extras: Any) -> CancelValidationError:
    from app.constants import CODIGO_GRUPO_MUDOU

    return CancelValidationError(
        "O grupo deste evento mudou enquanto você decidia: recarregue e confira.",
        status=409,
        codigo=CODIGO_GRUPO_MUDOU,
        **extras,
    )


def _dias_vivos_ordenados(event: CalendarEvent, eventos: list[CalendarEvent]) -> list[CalendarEvent]:
    """Os outros dias vivos do grupo (já travados em T1), o mais cedo primeiro (início, depois id)."""
    return sorted(
        (e for e in eventos if e.id != event.id and not e.is_cancelled),
        key=lambda e: (e.start_at or datetime.max, e.id),
    )


def _quem_recebe_a_venda(outros: list[CalendarEvent]) -> CalendarEvent | None:
    """O dia vivo mais cedo que pode guardar a venda: nunca um compromisso interno (🟧/🟠), que a
    cobrança da Home tira da lista (regra da 299; converge, T108). O "todos" segue cancelando-o."""
    from app.financeiro.cobranca_ops import compromisso_interno

    return next((e for e in outros if not compromisso_interno(e)), None)


def _forma_do_ato(event: CalendarEvent, eventos: list[CalendarEvent], pedido: PedidoDeCancelamento) -> FormaDoAto:
    """400 `alcance` → 409 `sem_outro_dia_vivo` → 409 `grupo_mudou`, nesta ordem (contracts §1).

    Conta os dias vivos de verdade: `is_group_leader` segue verdadeiro com os outros dias já
    cancelados (eles ficam no grupo).
    """
    from app.constants import ALCANCE_SO_ESTE_DIA, ALCANCE_TODOS, CODIGO_SEM_OUTRO_DIA_VIVO

    if event.group_leader_id is not None:
        if pedido.alcance_enviado:
            raise CancelValidationError(
                "Este dia se cancela sozinho: escolher o alcance só vale no 1º dia do grupo.", field="alcance"
            )
        principal = next((e for e in eventos if e.id == event.group_leader_id), None)
        if principal is None or principal.is_cancelled:
            raise _grupo_mudou()
        _recusa_da_venda_que_mudou(principal, pedido)
        return FormaDoAto("corte", principal=principal, dias=[event], vivo=principal)
    if pedido.alcance_enviado and pedido.alcance not in (ALCANCE_TODOS, ALCANCE_SO_ESTE_DIA):
        raise CancelValidationError("Escolha se cancela todos os dias do grupo ou só este.", field="alcance")
    outros = _dias_vivos_ordenados(event, eventos)
    if not outros:
        if pedido.alcance == ALCANCE_SO_ESTE_DIA:
            raise CancelValidationError(
                "Não há outro dia vivo no grupo para receber a venda: cancele todos os dias.",
                status=409,
                codigo=CODIGO_SEM_OUTRO_DIA_VIVO,
            )
        return FormaDoAto("avulso", principal=event, dias=[event])
    if not pedido.alcance_enviado:
        raise CancelValidationError(
            "Este evento tem outros dias no grupo: escolha se cancela todos ou só este.", field="alcance"
        )
    if pedido.alcance == ALCANCE_TODOS:
        return FormaDoAto("todos", principal=event, dias=[event, *outros])
    novo = _quem_recebe_a_venda(outros)
    if novo is None:
        raise CancelValidationError(
            "Não há outro dia vivo no grupo para receber a venda (só compromisso interno): cancele todos os dias.",
            status=409,
            codigo=CODIGO_SEM_OUTRO_DIA_VIVO,
        )
    if pedido.novo_principal_id != novo.id:
        raise _grupo_mudou(novo_principal=_evento_curto(novo))
    _recusa_da_venda_que_mudou(event, pedido)
    return FormaDoAto("passagem", principal=event, dias=[event], vivo=novo)


def _recusa_da_venda_que_mudou(principal: CalendarEvent, pedido: PedidoDeCancelamento) -> None:
    """A venda do grupo mudou desde que o diálogo abriu (outro corte, ou a aba Comercial): o novo
    valor foi pensado sobre a de antes — 409 `grupo_mudou`, com a venda de agora."""
    if pedido.venda_esperada is not None and pedido.venda_esperada != _dinheiro(principal.sale_value):
        raise _grupo_mudou(venda_do_grupo=float(_dinheiro(principal.sale_value)))


def _regime_do_ato(forma: FormaDoAto) -> str:
    from app.constants import REGIME_DIA, REGIME_VENDA, REGIME_VIRTUAL
    from app.financeiro.vendas_ops import is_loja_virtual

    if forma.corta:
        return REGIME_DIA
    return REGIME_VIRTUAL if is_loja_virtual(forma.principal) else REGIME_VENDA


@dataclass
class ContaDoCorte:
    """O dinheiro do corte de um dia (FR-056): a venda do grupo diminui; ninguém fica com retido."""

    pago: Decimal
    ja_devolvido: Decimal
    max_devolucao: Decimal  # o teto: pago do grupo − já devolvido
    devolucao: Decimal
    venda: Decimal
    venda_nova: Decimal | None  # `None` = inválida (o 400 de `venda_nova`)
    cheio: Decimal | None
    cheio_novo: Decimal | None
    minima: Decimal


def _devolucao_minima(pago: Decimal, ja_devolvido: Decimal, venda_nova: Decimal, venda: Decimal) -> Decimal:
    """O mínimo a devolver no corte (FR-056): o que a cliente pagou acima da venda nova, menos o que
    já passava da venda de antes (esse excedente não nasce do corte)."""
    livre = pago - ja_devolvido
    return _dinheiro(max(Decimal("0"), (livre - venda_nova) - max(Decimal("0"), livre - venda)))


def _conta_do_corte(principal: CalendarEvent, ids: list[int], devolucao: Decimal, venda_nova: Any) -> ContaDoCorte:
    """A mesma na prévia e no ato. O cheio novo é o de antes na proporção da venda (meio centavo
    para cima)."""
    from decimal import ROUND_HALF_UP

    pago, ja_devolvido = _dinheiro_do_grupo(ids)
    venda = _dinheiro(principal.sale_value)
    nova, invalida = _decimal(venda_nova)
    if invalida or nova is None or nova <= 0 or nova > venda:
        nova = None
    cheio = _dinheiro(principal.sale_value_gross) if principal.sale_value_gross is not None else None
    cheio_novo = None
    if nova is not None and cheio is not None and venda > 0:
        cheio_novo = (cheio * nova / venda).quantize(_CENTAVO, rounding=ROUND_HALF_UP)
    return ContaDoCorte(
        pago=pago,
        ja_devolvido=ja_devolvido,
        max_devolucao=max(Decimal("0.00"), pago - ja_devolvido),
        devolucao=_dinheiro(devolucao),
        venda=venda,
        venda_nova=nova,
        cheio=cheio,
        cheio_novo=cheio_novo,
        minima=_devolucao_minima(pago, ja_devolvido, nova, venda) if nova is not None else Decimal("0.00"),
    )


def _frase_da_minima(conta: ContaDoCorte) -> str:
    return (
        f"A cliente pagou {_brl(conta.pago)}: devolva pelo menos {_brl(conta.minima)} "
        "ou aumente o novo valor da venda."
    )


def _erros_do_corte(pedido: PedidoDeCancelamento, conta: ContaDoCorte) -> dict[str, str]:
    """Todos os campos recusados do corte de uma vez: só Parte ou Nada, sem imposto e sem PIX de BV."""
    from app.constants import MODO_NADA, MODO_PARTE, MODO_TUDO

    erros: dict[str, str] = {}
    if not pedido.motivo:
        erros["motivo"] = "Informe o motivo do cancelamento."
    if conta.venda_nova is None:
        erros["venda_nova"] = f"Informe o novo valor da venda do grupo: maior que zero e até {_brl(conta.venda)}."
    if pedido.imposto_enviado:
        erros["imposto_retido"] = "Ao cancelar só um dia não há imposto a reter: a venda continua no grupo."
    modo = pedido.modo
    if modo == MODO_TUDO:
        erros["devolucao_modo"] = "Ao cancelar só um dia, devolva parte ou nada: a venda continua no grupo."
    elif modo not in (MODO_PARTE, MODO_NADA):
        erros["devolucao_modo"] = "Escolha se devolve parte ou nada à cliente."
    elif modo == MODO_PARTE and conta.pago <= 0:
        erros["devolucao_modo"] = "A cliente não pagou nada (nenhum comprovante com valor): só cabe Nada."
    elif modo == MODO_PARTE:
        if pedido.valor_invalido or pedido.valor is None or pedido.valor <= 0:
            erros["devolucao_valor"] = "Informe quanto devolve à cliente."
        elif pedido.valor > conta.max_devolucao:
            erros["devolucao_valor"] = f"Acima do que é possível devolver ({_brl(conta.max_devolucao)})."
        elif pedido.valor < conta.minima:
            erros["devolucao_valor"] = _frase_da_minima(conta)
    elif conta.minima > 0:
        erros["devolucao_modo"] = _frase_da_minima(conta)
    if modo == MODO_PARTE and "devolucao_modo" not in erros:
        _erros_de_quem_recebe(pedido, erros)
    return erros


def _bvs_depois_do_corte(principal: CalendarEvent, conta: ContaDoCorte) -> list[tuple[Any, Decimal, bool]]:
    """O BV do principal depois de acompanhar a venda nova, pela MESMA conta da gravação
    (`comercial_ops.bvs_que_acompanham`, FR-011): o pago fica; o a pagar acompanha. `(acréscimo, BV,
    pago)`."""
    from app.calendar.comercial_ops import bvs_que_acompanham
    from app.models import EventAcrescimo

    linhas = [
        a
        for a in EventAcrescimo.query.filter(EventAcrescimo.event_id == principal.id).order_by(EventAcrescimo.id).all()
        if a.is_bv
    ]
    antes = (principal.sale_value, bool(principal.with_invoice), bool(principal.is_cortesia_permuta))
    novos: dict[int, Decimal] = {}
    if conta.venda_nova is not None:
        novos, _ficou = bvs_que_acompanham(
            linhas, antes, conta.venda_nova, bool(principal.with_invoice), bool(principal.is_cortesia_permuta)
        )
    saida = []
    for a in linhas:
        if not a.amount_brl:
            continue
        pago = (a.bv_payment_status or "nao_pago") in ("pago", "no_banco")
        saida.append((a, _dinheiro(novos.get(a.id, a.amount_brl)), pago))
    return saida


def _custo_sem_o_dia(vivo: CalendarEvent, dia: CalendarEvent, settings) -> Decimal | None:
    """O custo da comissão EducaManto do principal que fica, sem o dia cortado (que ainda não tem
    `cancelled_at` quando a comissão é refeita). Fora da EducaManto, `None`."""
    from app.calendar.group_ops import dias_vivos
    from app.financeiro import comissoes_ops

    if not (vivo.is_educamanto and comissoes_ops._educamanto_responsavel(settings) is not None):
        return None
    return _dinheiro(sum((comissoes_ops._event_cost(e) for e in dias_vivos(vivo) if e.id != dia.id), 0))


def _previa_do_corte(event: CalendarEvent, devolucao: Any, venda_nova: Any) -> dict[str, Any]:
    """A prévia do corte (contracts §2): sem retido nem comissão do retido; a cheia nova do
    principal, o BV dele depois de acompanhar a venda e a devolução mínima. Sem trava."""
    from app.constants import CODIGO_SEM_OUTRO_DIA_VIVO, MOTIVO_AJUSTE_CORTE_DE_DIA, now_sp
    from app.financeiro import comissoes_ops
    from app.models import SiteSetting

    principal_id = event.group_leader_id or event.id
    ids = ids_do_grupo([principal_id])[principal_id]
    principal = event if event.group_leader_id is None else db.session.get(CalendarEvent, event.group_leader_id)
    if event.group_leader_id is None and _quem_recebe_a_venda(
        _dias_vivos_ordenados(event, CalendarEvent.query.filter(CalendarEvent.id.in_(ids)).all())
    ) is None:
        raise CancelValidationError(
            "Não há outro dia vivo no grupo para receber a venda: cancele todos os dias.",
            status=409,
            codigo=CODIGO_SEM_OUTRO_DIA_VIVO,
        )
    valor, invalido = _decimal(devolucao)
    conta = _conta_do_corte(principal, ids, valor or Decimal("0"), venda_nova)
    if conta.venda_nova is None:
        raise CancelValidationError(
            f"Informe o novo valor da venda do grupo: maior que zero e até {_brl(conta.venda)}.", field="venda_nova"
        )
    if invalido or valor is None or valor < 0 or valor > conta.max_devolucao:
        raise CancelValidationError(f"Informe um valor de 0 a {_brl(conta.max_devolucao)}.", field="devolucao")
    settings = SiteSetting.query.get(1)
    bvs = _bvs_depois_do_corte(principal, conta)
    bv_total = _dinheiro(sum((b for _a, b, _p in bvs), Decimal("0")))
    bv_a_pagar = _dinheiro(sum((b for _a, b, pago in bvs if not pago), Decimal("0")))
    cheia_antes, _b, _t = comissoes_ops.comissao_cheia_do_evento(principal, settings)
    cheia, beneficiario, _taxa = comissoes_ops.comissao_cheia_do_evento(
        principal, settings, venda=conta.venda_nova, bv_total=bv_total, custo=_custo_sem_o_dia(principal, event, settings)
    )  # fmt: skip
    plano: list[dict] = []
    if _dinheiro(cheia) != _dinheiro(cheia_antes):
        alvos = {beneficiario: cheia} if beneficiario else {}
        plano = comissoes_ops.reconciliar_comissao_do_cancelado(
            principal, alvos, motivo=MOTIVO_AJUSTE_CORTE_DE_DIA, hoje=now_sp().date(), simular=True
        )
    nova, ciclo, repasse = _ajuste_do_plano(plano, beneficiario)
    return {
        "devolucao": float(conta.devolucao),
        "retido": None,
        "comissao_cheia": float(cheia),
        "comissao_retido": None,
        # No corte, o BV a pagar do principal depois de acompanhar (contracts §2); o pago não conta.
        "bv_retido": float(bv_a_pagar),
        "bvs": [{"acrescimo_id": a.id, "bv_retido": float(b)} for a, b, pago in bvs if not pago],
        "ja_liquidada": float(_liquidada(principal, beneficiario)),
        "ajuste": float(nova["valor"]) if nova else None,
        "ciclo": ciclo.strftime("%Y-%m") if ciclo else None,
        "repasse_em": repasse.isoformat() if repasse else None,
        "imposto_referencia": None,
        "devolucao_minima": float(conta.minima),
    }


def _aliquota(settings) -> Decimal:
    from app.financeiro.routes import _get_tax_rate

    return Decimal(str(_get_tax_rate(settings)))


def _ajuste_do_plano(plano: list[dict], beneficiario_id: int | None) -> tuple[dict | None, date | None, date | None]:
    """A linha nova do plano (a do beneficiário primeiro), o ciclo dela e o dia do repasse."""
    from app.constants import DIA_DO_REPASSE

    novas = [p for p in plano if p["linha_id"] is None and p["seller_id"] == beneficiario_id]
    nova = novas[0] if novas else (next((p for p in plano if p["linha_id"] is None), None))
    ciclo = (nova["payable_from"] or nova["sale_date"]) if nova else None
    repasse = None
    if ciclo is not None:
        seguinte = date(ciclo.year + 1, 1, 1) if ciclo.month == 12 else date(ciclo.year, ciclo.month + 1, 1)
        repasse = seguinte.replace(day=DIA_DO_REPASSE)
    return nova, ciclo, repasse


def _liquidada(event: CalendarEvent, beneficiario_id: int | None) -> Decimal:
    from app.financeiro import comissoes_ops

    if not beneficiario_id:
        return Decimal("0.00")
    soma = (
        db.session.query(db.func.coalesce(db.func.sum(CommissionPayment.amount), 0))
        .filter(
            CommissionPayment.event_id == event.id,
            CommissionPayment.seller_id == beneficiario_id,
            CommissionPayment.status.in_(("pago", "no_banco")),
            comissoes_ops._sem_marca_propria(),
        )
        .scalar()
    )
    return _dinheiro(soma)


def _efeito(event: CalendarEvent, conta: ContaDoAto, plano: list[dict], settings) -> dict[str, Any]:
    """O `EfeitoCancelamento` (contracts §2) a partir da conta e do plano da reconciliação."""
    nova, ciclo, repasse = _ajuste_do_plano(plano, conta.beneficiario_id)
    liquidada = _liquidada(event, conta.beneficiario_id)
    referencia = None
    if event.with_invoice:
        referencia = (_aliquota(settings) * conta.retido / Decimal("100")).quantize(
            _CENTAVO, rounding=ROUND_HALF_UP
        )
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

    Com `venda_nova`, é a prévia do corte (o dia do grupo, ou o 1º dia com a passagem da venda):
    `_previa_do_corte`.

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
    if venda_nova not in (None, ""):
        return _previa_do_corte(event, devolucao, venda_nova)
    if event.group_leader_id is not None:
        raise CancelValidationError(
            "Informe o novo valor da venda do grupo para cancelar só este dia.", field="venda_nova"
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
    """O que o cancelamento faz além do dinheiro em cada dia que encerra (data-model §6.4, FR-062).

    Roda em **todo** cancelamento, na transação, logo depois de `cancelled_at`: o avulso e cada
    dia do "todos" com `(ALCANCE_TODOS, None)`; o corte de um dia que não é o principal com
    `(ALCANCE_SO_ESTE_DIA, None)`; o antigo 1º dia, **depois** de `passar_venda`, com
    `(ALCANCE_SO_ESTE_DIA, novo_principal)`. O verify o chama pelo módulo (o espião da 306 envolve
    esta função: a assinatura não muda).

    Feature 315: fecha o pedido de cancelamento do dia, se havia, e responde a quem pediu.
    """
    from app.calendar import solicitacao_ops  # tardio: solicitacao_ops importa este módulo

    solicitacao_ops.fechar_no_cancelamento(event, alcance=alcance, novo_principal=novo_principal)


def _recusas_de_estado(event: CalendarEvent) -> None:
    """As recusas que não dependem do corpo, depois de T1: já cancelado e ensaio. O grupo se resolve
    em `_forma_do_ato` (alcance, dia vivo, novo principal)."""
    from app.constants import CODIGO_ENSAIO, CODIGO_JA_CANCELADO

    if event.is_cancelled:
        raise CancelValidationError("Este evento já está cancelado.", status=409, codigo=CODIGO_JA_CANCELADO)
    if event.event_type == "ENSAIO":
        raise CancelValidationError(
            "Ensaio não se cancela sozinho: ele sai junto com o cancelamento do evento.",
            status=409,
            codigo=CODIGO_ENSAIO,
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
        erros["motivo"] = "Informe o motivo do cancelamento."
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
            erros["devolucao_valor"] = f"Acima do que é possível devolver ({_brl(conta.max_devolucao)})."
    elif modo == MODO_TUDO and (pedido.valor_invalido or pedido.valor is None):
        erros["devolucao_valor"] = "Recarregue a página: falta o total a devolver."
    if modo in (MODO_TUDO, MODO_PARTE) and "devolucao_modo" not in erros:
        _erros_de_quem_recebe(pedido, erros)
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


def _erros_de_quem_recebe(pedido: PedidoDeCancelamento, erros: dict[str, str]) -> None:
    if not pedido.nome:
        erros["devolucao_nome"] = "Informe quem recebe a devolução."
    elif len(pedido.nome) > 200:
        erros["devolucao_nome"] = "Quem recebe: até 200 caracteres."
    if not pedido.pix:
        erros["devolucao_pix"] = "Informe o PIX da devolução."
    elif len(pedido.pix) > 120:
        erros["devolucao_pix"] = "PIX: até 120 caracteres."


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
    mesma pessoa só atrasaria o repasse. Aprovado, ele entra sozinho na Planilha de Pagamentos. Na
    DRE, não: a devolução de cancelado sai dos gastos extras (`dre_ops.gastos_extras_do_periodo`),
    porque já está descontada no retido. Direto no ORM, nunca por `create_expense` (que nasce
    pendente e avisa o Financeiro). A data é a de São Paulo do ato.
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


def _congelar_satelite(dia: CalendarEvent, *, principal: CalendarEvent, actor: User) -> None:
    """A linha `satelite` de um dia do "todos": sem dinheiro próprio, ligada ao principal."""
    from app.constants import REGIME_SATELITE
    from app.models import EventCancellation

    db.session.add(EventCancellation(
        event=dia, regime=REGIME_SATELITE, seller_id=dia.seller_id, with_invoice=False,
        group_leader_id=principal.id, updated_by_id=actor.id,
    ))  # fmt: skip


def _congelar_dia(
    dia: CalendarEvent, *, principal: CalendarEvent, pedido: PedidoDeCancelamento, conta: ContaDoCorte, actor: User
):
    """A linha `dia` do corte: a venda do grupo antes e depois (e o cheio), ligada ao principal
    que fica vivo — na passagem, o novo (`passar_venda` marca `sale_handed_over`)."""
    from app.constants import REGIME_DIA
    from app.models import EventCancellation

    canc = EventCancellation(
        event=dia, regime=REGIME_DIA, refund_mode=pedido.modo, seller_id=dia.seller_id, with_invoice=False,
        group_leader_id=principal.id, sale_value_before=conta.venda, sale_value_after=conta.venda_nova,
        sale_value_gross_before=conta.cheio, sale_value_gross_after=conta.cheio_novo, updated_by_id=actor.id,
    )  # fmt: skip
    db.session.add(canc)
    return canc


def _marcar_comissao_propria(novo: CalendarEvent) -> None:
    """Antes de `passar_venda`, pelo `event_id` de antes: a comissão que o novo 1º dia já tinha de
    quando era venda avulsa fica fora da reconciliação da venda do grupo (P-29, P-51)."""
    from app.constants import NOTA_COMISSAO_PROPRIA_DO_DIA
    from app.utils import audit

    linhas = (
        CommissionPayment.query.filter(CommissionPayment.event_id == novo.id, CommissionPayment.status != "cancelado")
        .order_by(CommissionPayment.id)
        .all()
    )
    for cp in linhas:
        if NOTA_COMISSAO_PROPRIA_DO_DIA in (cp.notes or ""):
            continue
        cp.notes = f"{NOTA_COMISSAO_PROPRIA_DO_DIA} | {cp.notes}" if cp.notes else NOTA_COMISSAO_PROPRIA_DO_DIA
        audit("edit", "commission", cp.id, novo.title, "Comissão própria do dia: fica fora da venda do grupo")


def _seguir_o_corte(vivo: CalendarEvent, conta: ContaDoCorte, *, dia: CalendarEvent, actor: User, settings) -> None:
    """A venda do principal que fica diminui, o BV a pagar acompanha UMA vez e a comissão se refaz.

    Pela 305: `estado_da_venda` (trava e relê o "antes"), a venda nova, `acompanhar_bv_da_venda`
    e só então a comissão — com a cheia nova sobre a venda nova, o BV acompanhado e o custo sem o
    dia cortado. Só refaz quando o corte muda a cheia (a venda que diminuiu, ou o cachê do dia que
    sai da base da EducaManto): com a mesma cheia, refazer acertaria diferenças que não são do corte.
    """
    from app.calendar.comercial_ops import acompanhar_bv_da_venda, estado_da_venda
    from app.constants import MOTIVO_AJUSTE_CORTE_DE_DIA
    from app.financeiro import comissoes_ops

    antes = estado_da_venda(vivo)
    cheia_antes, _b, _t = comissoes_ops.comissao_cheia_do_evento(vivo, settings)
    vivo.sale_value = conta.venda_nova
    if conta.cheio_novo is not None:
        vivo.sale_value_gross = conta.cheio_novo
    acompanhar_bv_da_venda(vivo, antes, actor_name=actor.name, tz=TZ)
    db.session.flush()
    cheia, beneficiario, _taxa = comissoes_ops.comissao_cheia_do_evento(
        vivo, settings, custo=_custo_sem_o_dia(vivo, dia, settings)
    )
    if _dinheiro(cheia) != _dinheiro(cheia_antes):
        alvos = {beneficiario: cheia} if beneficiario else {}
        comissoes_ops.reconciliar_comissao_do_cancelado(vivo, alvos, motivo=MOTIVO_AJUSTE_CORTE_DE_DIA)
    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    texto = f'Dia "{dia.title}" cancelado: venda do grupo {_brl(conta.venda)} → {_brl(conta.venda_nova)}'
    if conta.cheio_novo is not None:
        texto += f" (antes do desconto {_brl(conta.cheio)} → {_brl(conta.cheio_novo)})"
    db.session.add(EventLog(event_id=vivo.id, actor_name=actor.name, actor_role=papel, message=texto))


def _conta_validada(forma: FormaDoAto, regime: str, ids: list[int], acrescimos: list, pedido, settings):
    """A conta da forma do ato e as recusas de campo (400) e do máximo (409)."""
    from app.constants import CODIGO_MAX_DEVOLUCAO_MUDOU, MODO_TUDO, REGIME_VENDA, REGIME_VIRTUAL

    if forma.corta:
        conta = _conta_do_corte(forma.principal, ids, pedido.devolve(Decimal("0.00")), pedido.venda_nova)
        erros = _erros_do_corte(pedido, conta)
    else:
        pago, ja_devolvido = _dinheiro_do_grupo(ids)
        maximo = max(Decimal("0.00"), pago - ja_devolvido)
        devolve = pedido.devolve(maximo) if regime == REGIME_VENDA else Decimal("0.00")
        conta = _conta_do_ato(forma.principal, ids, acrescimos, devolve, settings)
        erros = _erros_do_pedido(forma.principal, pedido, regime=regime, conta=conta)
    papeis_do_ato = (
        {r.id: r.talent_id for r in elenco_do_ato(forma.dias[0], dias=[d.id for d in forma.dias])}
        if regime != REGIME_VIRTUAL
        else {}
    )
    erros.update(_erros_das_multas_do_ato(pedido, papeis_do_ato))
    if erros:
        raise CancelValidationError("Corrija os campos destacados.", fields=erros)
    if not forma.corta and regime == REGIME_VENDA and pedido.modo == MODO_TUDO and pedido.valor != conta.max_devolucao:
        raise CancelValidationError(
            f"O valor a devolver mudou para {_brl(conta.max_devolucao)}: confira antes de cancelar.",
            status=409,
            codigo=CODIGO_MAX_DEVOLUCAO_MUDOU,
            max_devolucao=float(conta.max_devolucao),
        )
    return conta


def _gravar_o_ato(forma: FormaDoAto, regime: str, pedido, conta, actor: User, settings) -> tuple:
    """Congela (a linha, os BVs e o elenco), devolve e refaz a comissão, na ordem do plan §Travas.

    Returns:
        `(gasto da devolução, linha congelada que guarda o elenco)` — no `venda`, a do principal com
        todos os dias do "todos"; no corte e na passagem, a do dia; na Loja Virtual, nenhuma.
    """
    from app.calendar import group_ops
    from app.constants import MOTIVO_AJUSTE_RETIDO, REGIME_VENDA
    from app.financeiro import comissoes_ops

    if not forma.corta:
        canc = _congelar(forma.principal, regime=regime, pedido=pedido, conta=conta, actor=actor)
        if regime == REGIME_VENDA:
            _congelar_elenco(canc, forma.dias)
        else:
            canc = None
        for dia in forma.dias[1:]:
            _congelar_satelite(dia, principal=forma.principal, actor=actor)
        gasto = None
        if regime == REGIME_VENDA:
            gasto = _registrar_devolucao(forma.principal, valor=conta.devolucao, nome=pedido.nome, pix=pedido.pix,
                                         observacao=pedido.observacao, actor=actor)  # fmt: skip
        db.session.flush()
        if regime == REGIME_VENDA:
            comissoes_ops.reconciliar_comissao_do_cancelado(forma.principal, conta.alvos, motivo=MOTIVO_AJUSTE_RETIDO)
        return gasto, canc
    dia = forma.dias[0]
    canc = _congelar_dia(dia, principal=forma.vivo, pedido=pedido, conta=conta, actor=actor)
    _congelar_elenco(canc, [dia])
    if forma.tipo == "passagem":
        db.session.flush()
        _marcar_comissao_propria(forma.vivo)
        # Pelo nome do módulo: a mutação do 42 a troca por um "apaga e recria".
        group_ops.passar_venda(dia, forma.vivo, actor_name=actor.name)
    # Ligada ao dia da URL: a devolução do ato não viaja com a venda (fica no antigo 1º dia).
    gasto = _registrar_devolucao(dia, valor=conta.devolucao, nome=pedido.nome, pix=pedido.pix,
                                 observacao=pedido.observacao, actor=actor)  # fmt: skip
    db.session.flush()
    _seguir_o_corte(forma.vivo, conta, dia=dia, actor=actor, settings=settings)
    return gasto, canc


def _texto_do_corte(forma: FormaDoAto, pedido: PedidoDeCancelamento, conta: ContaDoCorte) -> str:
    partes = [f"Dia cancelado: {pedido.motivo}", f"venda do grupo {_brl(conta.venda)} → {_brl(conta.venda_nova)}"]
    if conta.devolucao > 0:
        partes.append(f"devolução de {_brl(conta.devolucao)} a {pedido.nome}")
    else:
        partes.append("não devolve nada")
    if forma.tipo == "passagem":
        partes.append(f'a venda passou para "{forma.vivo.title}"')
    return " | ".join(partes)


def _texto_das_multas(canc, gastos: list[SpecialExpense]) -> str:
    """A multa de cada escalação no histórico (FR-016): artista, vaga e dia, pelas linhas congeladas."""
    por_gasto = {x.special_expense_id: x for x in canc.elenco if x.special_expense_id} if canc is not None else {}
    partes = []
    for g in gastos:
        x = por_gasto.get(g.id)
        if x is None:
            partes.append(f"{g.supplier_name or '?'} {_brl(g.amount)}")
            continue
        nome = (x.talent.full_name if x.talent else None) or g.supplier_name or "?"
        dia = x.day_event or db.session.get(CalendarEvent, x.day_event_id)
        quando = dia.start_at.strftime("%d/%m") if dia is not None and dia.start_at else "sem data"
        partes.append(f"{nome} ({x.character_name}, {quando}) {_brl(g.amount)}")
    return "; ".join(partes)


def _encerrar_os_dias(
    forma: FormaDoAto, regime: str, pedido, conta, actor: User, *, url_id: int, ensaios: list, canc
) -> dict[str, Any]:
    """O fim do ato, na ordem única (data-model §7.1): `cancelled_at` e `ao_cancelar` de cada dia;
    depois os ensaios saem do banco, os sinos e as multas nascem (H6); por fim o histórico, um por
    dia (FR-016), com os ensaios do dia e, no da URL, as multas e quem foi avisado.

    Returns:
        `{"ensaios", "avisados", "emails"}` — os e-mails saem depois do commit (`_mandar_os_emails`).
    """
    from app.calendar.routes import _log_sync
    from app.constants import ALCANCE_SO_ESTE_DIA, ALCANCE_TODOS, now_sp

    for dia in forma.dias:
        dia.cancelled_at = now_sp()
        dia.cancelled_by_id = actor.id
        dia.cancellation_reason = pedido.motivo
        # O pedido de cancelamento do dia fecha em `ao_cancelar` (feature 315), que lê o autor antes.
        if forma.corta:
            novo = forma.vivo if forma.tipo == "passagem" else None
            ao_cancelar(dia, alcance=ALCANCE_SO_ESTE_DIA, novo_principal=novo)
        else:
            ao_cancelar(dia, alcance=ALCANCE_TODOS, novo_principal=None)

    feitos = _apagar_os_ensaios(ensaios)
    for dia in forma.dias:
        db.session.expire(dia, ["ensaios"])
    escalados = _escalados_do_ato(forma, canc)
    sinos = _avisar_no_sino(forma, url_id, feitos, escalados)
    multas = _multas_do_ato(canc, pedido, actor)
    emails = _alvos_do_email(escalados)
    avisados = {"email": len(emails), **sinos}

    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    for dia in forma.dias:
        if forma.corta:
            partes = [_texto_do_corte(forma, pedido, conta)]
        elif dia is forma.principal:
            partes = [_texto_do_historico(pedido.motivo, regime, pedido, conta)]
        else:
            partes = [f'Evento cancelado com todos os dias do grupo de "{forma.principal.title}": {pedido.motivo}']
        do_dia = [e["texto"] for e in feitos if e["pai"] == dia.id]
        if do_dia:
            partes.append("ensaios cancelados: " + "; ".join(do_dia))
        if dia.id == url_id:
            if multas:
                partes.append("multa ao elenco: " + _texto_das_multas(canc, multas))
            partes.append(
                f"avisados: {avisados['email']} por e-mail, {avisados['ensaio']} da equipe de Ensaio, "
                f"{avisados['casting']} do Casting"
            )
        detalhe = " | ".join(partes)
        # Sem `created_at`: vale o default UTC do modelo, que o histórico da tela converte (FR-016).
        db.session.add(EventLog(event_id=dia.id, actor_name=actor.name, actor_role=papel, message=detalhe))
        _log_sync("event_cancelled", dia, details=detalhe, actor=actor.name, actor_role=papel)
    return {"ensaios": feitos, "avisados": avisados, "emails": emails}


def cancelar_evento(event: CalendarEvent, *, corpo: dict[str, Any] | None, actor: User) -> dict[str, Any]:
    """Cancela o evento: congela, devolve, reconcilia a comissão e tira do Google. Commita.

    A ordem é a única do ato (data-model §7.1; contracts §1): travas → recusas (o grupo em
    `_forma_do_ato`) → validação de todos os campos → (marcado: desmarcar) → congelar → (passagem:
    a comissão própria do novo e `passar_venda`) → devolução → comissão (ou o corte: a venda do
    principal que fica, o BV e a comissão dele) → `cancelled_at` → `ao_cancelar` → `EventLog`
    (UTC) → commit → Google, fora da trava. As quatro formas estão em `FormaDoAto`. H6: T6 e a recusa
    do cachê pago antes da pendente; o elenco congela com a linha; depois de `ao_cancelar`, os
    ensaios saem do banco, os sinos e as multas nascem; depois do commit, o Google (dias e ensaios)
    e os e-mails ao elenco.

    Returns:
        `{"event", "gasto_id", "google_removido", "aviso", "dias_cancelados", "venda_passou_para",
        "ensaios_cancelados", "avisados"}`;
        a view monta o `resumo`.

    Raises:
        CancelValidationError: as recusas do contrato (400 com `fields`, 409 com `codigo`).
    """
    from app.calendar import sumico_ops
    from app.constants import REGIME_VENDA, REGIME_VIRTUAL
    from app.financeiro import comissoes_ops
    from app.models import SiteSetting

    pedido = PedidoDeCancelamento.ler(corpo)
    eventos = travar_grupo(event)  # T1
    ids = [e.id for e in eventos]
    _ler_congelados(ids)  # T2
    _recusas_de_estado(event)
    forma = _forma_do_ato(event, eventos, pedido)
    regime = _regime_do_ato(forma)
    settings = SiteSetting.query.get(1)
    acrescimos = _travar_acrescimos(forma.principal.id) if regime != REGIME_VIRTUAL else []  # T3
    beneficiario = comissoes_ops._beneficiario_comissionado(forma.principal, settings)
    _travar_linhas_de_comissao(ids, {getattr(beneficiario, "id", None), *_beneficiarios_das_linhas(ids)})  # T4
    devolucoes = _travar_devolucoes(ids)  # T5
    _travar_elenco([d.id for d in forma.dias])  # T6
    _recusa_do_cache_pago(forma.dias)
    _recusa_da_pendente(devolucoes)
    conta = _conta_validada(forma, regime, ids, acrescimos, pedido, settings)

    # ── grava ──
    ensaios = _ensaios_dos_dias(forma.dias)
    # Antes do `desmarcar`: o marcado já não está no Google; os ensaios estão (FR-014, FR-065).
    alvos_google = _alvos_do_google(forma.dias) + _alvos_do_google(ensaios)
    for dia in forma.dias:
        if dia.is_google_missing:
            sumico_ops.desmarcar(dia, motivo=sumico_ops.MOTIVO_CANCELADO)
    if regime == REGIME_VENDA:
        _gravar_pix_dos_bvs(acrescimos, pedido)
    db.session.flush()
    gasto, canc = _gravar_o_ato(forma, regime, pedido, conta, actor, settings)
    efeitos = _encerrar_os_dias(forma, regime, pedido, conta, actor, url_id=event.id, ensaios=ensaios, canc=canc)
    db.session.flush()
    gasto_id = gasto.id if gasto is not None else None
    for dia in {*forma.dias, forma.principal, *([forma.vivo] if forma.vivo else [])}:
        db.session.expire(dia, ["commission_payments"])
    db.session.commit()

    google_removido, aviso = _remover_do_google(alvos_google)
    if aviso and efeitos["ensaios"]:
        aviso += " Confira também os ensaios: " + "; ".join(e["texto"] for e in efeitos["ensaios"]) + "."
    _mandar_os_emails(efeitos["emails"])
    return {
        "event": event,
        "gasto_id": gasto_id,
        "google_removido": google_removido,
        "aviso": aviso,
        "dias_cancelados": [d.id for d in forma.dias],
        "venda_passou_para": _evento_curto(forma.vivo) if forma.tipo == "passagem" else None,
        "ensaios_cancelados": [{"id": e["id"], "data": e["data"], "local": e["local"]} for e in efeitos["ensaios"]],
        "avisados": efeitos["avisados"],
    }


def elenco_do_ato(event: CalendarEvent, dias: list[int] | None = None) -> list[EventRole]:
    """A régua única das escalações do ato (R18): com talento, sem quem recusou o convite e sem
    a vaga de presença do som. O impacto mostra esta lista; a H6 a grava no congelado."""
    return elenco_dos_dias(dias or [event.id])


def elenco_dos_dias(ids: list[int]) -> list[EventRole]:
    """A régua de `elenco_do_ato` para uma lista de dias, em uma consulta (feature 312).

    É também a de "quem o Casting ainda tem de tirar e avisar" num cancelado: as vagas de HOJE —
    quem já saiu da escala sai daqui. Lista vazia devolve vazio (em `elenco_do_ato` ela caía no
    próprio evento).
    """
    from app.calendar.casting_ops import e_vaga_de_presenca

    if not ids:
        return []
    papeis = (
        EventRole.query.filter(EventRole.event_id.in_(ids), EventRole.talent_id.isnot(None))
        .order_by(EventRole.event_id, EventRole.id)
        .all()
    )
    return [r for r in papeis if r.invite_status != "rejected" and not e_vaga_de_presenca(r)]


def _papeis_com_cache_pago(ids: list[int]) -> list[EventRole]:
    """As escalações com talento em "pago" ou "no banco" dos dias, fora a vaga de presença (FR-063)."""
    from app.calendar.casting_ops import e_vaga_de_presenca

    if not ids:
        return []
    papeis = (
        EventRole.query.filter(
            EventRole.event_id.in_(ids),
            EventRole.talent_id.isnot(None),
            EventRole.payment_status.in_(("pago", "no_banco")),
        )
        .order_by(EventRole.id)
        .all()
    )
    return [r for r in papeis if not e_vaga_de_presenca(r)]


# ── História 6: cachê pago, elenco congelado, ensaios, sinos, multas e e-mails ─────────────────

#: FR-063: a frase da recusa do cachê pago (o diálogo a mostra sem botão, apontando Gastos Extras).
FRASE_CACHE_PAGO = (
    "Este evento tem cachê pago ao elenco e não pode ser cancelado. Para devolver dinheiro à "
    "cliente, lance uma Devolução em Gastos Extras."
)


def cache_pago_do_evento(event: CalendarEvent) -> Decimal:
    """O cachê já pago (ou no banco) do elenco do evento — a régua única do FR-063 (exportada à 2a).

    Escalação com talento em "pago" ou "no banco", fora a vaga de presença (que nunca tem cachê).
    Soma os valores; uma escalação paga de valor vazio conta R$ 0,01, para nunca sair "sem cachê pago".
    """
    papeis = _papeis_com_cache_pago([event.id])
    total = _dinheiro(sum((_dinheiro(r.cache_value) for r in papeis), Decimal("0")))
    return max(total, _CENTAVO) if papeis else Decimal("0.00")


def _travar_elenco(ids: list[int]) -> None:
    """T6: as escalações com talento dos dias que o ato alcança, `ORDER BY id FOR UPDATE` (só no ato)."""
    if ids:
        (
            EventRole.query.filter(EventRole.event_id.in_(ids), EventRole.talent_id.isnot(None))
            .order_by(EventRole.id)
            .with_for_update()
            .populate_existing()
            .all()
        )


def _recusa_do_cache_pago(dias: list[CalendarEvent]) -> None:
    """409 `cache_pago` com os dias (FR-063): nada se grava, ninguém é avisado."""
    from app.constants import CODIGO_CACHE_PAGO

    pagos = {r.event_id for r in _papeis_com_cache_pago([d.id for d in dias])}
    if pagos:
        raise CancelValidationError(
            FRASE_CACHE_PAGO,
            status=409,
            codigo=CODIGO_CACHE_PAGO,
            dias=[_evento_curto(d) for d in dias if d.id in pagos],
        )


def _congelar_elenco(canc, dias: list[CalendarEvent]) -> None:
    """As linhas do elenco do ato (FR-070; data-model §3), uma por escalação (vaga × dia), pela
    `elenco_do_ato`: é delas que saem a multa, o e-mail e a lista do resumo — nunca da escala de hoje."""
    from app.models import EventCancellationElenco

    for r in elenco_do_ato(dias[0], dias=[d.id for d in dias]):
        canc.elenco.append(EventCancellationElenco(
            talent_id=r.talent_id, role_id=r.id, day_event_id=r.event_id,
            character_name=(r.character_name or "")[:120], cache_reference=r.cache_value,
        ))  # fmt: skip


def _chave_do_sino(kind: str, evento_id: int, dia_id: int | None = None) -> str:
    """A `dedupe_key` dos sinos do ato: sempre pelo evento da URL (data-model §6.5) — pelo principal,
    o corte de um dia e o "todos" depois engoliriam um ao outro. Gancho da mutação do 44."""
    return f"{kind}:{evento_id}" + (f":{dia_id}" if dia_id is not None else "")


def _ensaios_dos_dias(dias: list[CalendarEvent]) -> list[CalendarEvent]:
    """Os ensaios (filhos) dos dias que o ato cancela — no "só este dia", só os do antigo 1º dia."""
    ids = [d.id for d in dias]
    return (
        CalendarEvent.query.filter(CalendarEvent.parent_event_id.in_(ids), CalendarEvent.event_type == "ENSAIO")
        .order_by(CalendarEvent.start_at, CalendarEvent.id)
        .all()
    )


def _descrever_ensaio(ensaio: CalendarEvent) -> str:
    quando = ensaio.start_at.strftime("%d/%m %H:%M") if ensaio.start_at else "sem data"
    return f"{quando}" + (f" ({ensaio.location})" if ensaio.location else "")


def _apagar_os_ensaios(ensaios: list[CalendarEvent]) -> list[dict[str, Any]]:
    """FR-065: os ensaios saem do banco na transação do ato (o Google, depois do commit)."""
    from app.calendar.event_ops import _apagar_ensaio_no_banco

    saida = []
    for ensaio in ensaios:
        saida.append({
            "id": ensaio.id,
            "data": ensaio.start_at.isoformat() if ensaio.start_at else None,
            "local": ensaio.location,
            "pai": ensaio.parent_event_id,
            "texto": _descrever_ensaio(ensaio),
        })  # fmt: skip
        _apagar_ensaio_no_banco(ensaio)
    return saida


def _avisar_no_sino(forma: FormaDoAto, url_id: int, ensaios: list[dict], escalados: list) -> dict[str, int]:
    """Os dois sinos do ato (FR-067), na transação: a equipe de Ensaio (só com ensaio cancelado) e
    o Casting (um por dia cancelado com escalados). As chaves saem de `_chave_do_sino`, pelo módulo."""
    from app.notificacoes import notificacoes_ops as nops

    ensaio = 0
    if ensaios:
        ensaio = nops.notificar_evento_cancelado(
            forma.dias[0], [e["texto"] for e in ensaios],
            dedupe_key=_chave_do_sino(nops.KIND_EVENTO_CANCELADO, url_id),
        )  # fmt: skip
    # Pessoas, não vagas: o artista em duas vagas do mesmo dia é um a tirar da escala.
    pessoas: dict[int, set[int]] = {}
    for e in escalados:
        pessoas.setdefault(e.day_event_id, set()).add(e.talent_id)
    por_dia = {dia_id: len(quem) for dia_id, quem in pessoas.items()}
    casting = 0
    for dia in forma.dias:
        if por_dia.get(dia.id):
            casting += nops.notificar_cancelamento_na_escala(
                dia, por_dia[dia.id], dedupe_key=_chave_do_sino(nops.KIND_EVENTO_CANCELADO_ESCALA, url_id, dia.id)
            )
    return {"ensaio": ensaio, "casting": casting}


@dataclass(frozen=True)
class Escalado:
    """Uma escalação que o ato alcança: o artista, o dia, a vaga (e a ordem de desempate)."""

    talent_id: int
    day_event_id: int
    character_name: str
    ordem: int


def _escalados_do_ato(forma: FormaDoAto, canc) -> list[Escalado]:
    """Quem o ato avisa (FR-066, FR-068): as linhas congeladas do elenco; na Loja Virtual, que não
    congela elenco (não tem multa), as escalações dos dias pela mesma `elenco_do_ato` — o artista
    pré-escalado da campanha também recebe o e-mail e entra no sino do Casting."""
    if canc is not None:
        return [Escalado(x.talent_id, x.day_event_id, x.character_name, x.id) for x in canc.elenco]
    papeis = elenco_do_ato(forma.dias[0], dias=[d.id for d in forma.dias])
    return [Escalado(r.talent_id, r.event_id, r.character_name or "", r.id) for r in papeis]


def _alvos_do_email(escalados: list[Escalado]) -> list[tuple[int, int, str]]:
    """Um e-mail por talento com e-mail cadastrado (R17): o dia mais cedo em que ele estava entre os
    dias do ato e o personagem dessa vaga. `(talent_id, day_event_id, character_name)`."""
    from app.models import Talent

    com_email = {
        t.id
        for t in Talent.query.filter(Talent.id.in_({e.talent_id for e in escalados} or {-1})).all()
        if (t.email_contact or "").strip()
    }
    dias = {d.id: d for d in CalendarEvent.query.filter(CalendarEvent.id.in_({e.day_event_id for e in escalados} or {-1}))}
    por_talento: dict[int, tuple] = {}
    for e in escalados:
        if e.talent_id not in com_email:
            continue
        dia = dias.get(e.day_event_id)
        chave = ((dia.start_at if dia is not None else None) or datetime.max, e.day_event_id, e.ordem)
        atual = por_talento.get(e.talent_id)
        if atual is None or chave < atual[0]:
            por_talento[e.talent_id] = (chave, e.day_event_id, e.character_name)
    return [(tid, dia_id, nome) for tid, (_c, dia_id, nome) in sorted(por_talento.items())]


def _mandar_os_emails(alvos: list[tuple[int, int, str]]) -> None:
    """Depois do commit: "você foi removido do evento" a cada talento do ato (FR-066)."""
    from app.email_service import send_async, send_removal_email
    from app.models import Talent

    for talent_id, dia_id, personagem in alvos:
        talento = db.session.get(Talent, talent_id)
        dia = db.session.get(CalendarEvent, dia_id)
        if talento is not None and dia is not None:
            send_async(send_removal_email, talento, dia, personagem)


# ── Multa ao elenco (FR-070–FR-072; data-model §7.5) ─────────────────────────────────────────


def _registrar_multa(linha, valor: Decimal, actor: User) -> SpecialExpense:
    """O Gasto Extra da multa de uma escalação: aprovado, a pagar ao artista, ligado ao dia. Sem
    commit. Pelo ORM, no molde de `_registrar_devolucao` (nunca `create_expense`, que nasce pendente)."""
    from app.constants import now_sp
    from app.gastos.gastos_ops import _log

    agora = now_sp()
    talento = linha.talent
    dia = linha.day_event or db.session.get(CalendarEvent, linha.day_event_id)
    nome = (talento.full_name if talento else "") or ""
    gasto = SpecialExpense(
        description=f"Multa de cancelamento — {nome} ({linha.character_name}) — {dia.title if dia else ''}"[:200],
        category=SpecialExpense.CATEGORY_MULTA_CANCELAMENTO,
        amount=valor,
        expense_date=agora.date(),
        status="aprovado",
        created_by_id=actor.id,
        approved_by_id=actor.id,
        approved_at=agora,
        disbursement_type="fornecedor",
        supplier_name=nome[:200] or None,
        supplier_pix=((talento.pix_key or "").strip()[:120] or None) if talento else None,
        payment_status="nao_pago",
        paid_at_creation=False,
        event_id=linha.day_event_id,
    )
    db.session.add(gasto)
    db.session.flush()
    linha.special_expense_id = gasto.id
    _log(actor, "gasto", gasto.id, gasto.description, "criou", f"Multa de cancelamento {_brl(valor)}")
    return gasto


#: O teto da coluna do gasto (`Numeric(10,2)`): acima disso o flush estoura com 500.
_TETO_DA_MULTA = Decimal("100000000")


def _erro_do_valor_da_multa(valor: Decimal | None, invalido: bool) -> str | None:
    if invalido or (valor is not None and valor < 0):
        return "Informe a multa em reais (0 ou mais)."
    if valor is not None and valor >= _TETO_DA_MULTA:
        return "Valor alto demais para uma multa: confira."
    return None


def _erros_das_multas_do_ato(pedido: PedidoDeCancelamento, papeis_do_ato: dict[int, int]) -> dict[str, str]:
    """`fields.multa_<role_id>` (contracts §1): valor negativo, inválido ou acima do teto; vaga fora do
    ato; o artista da vaga mudou desde que a tela abriu (a multa iria para outra pessoa). Vazio e 0 não
    são erro — são "sem multa". `papeis_do_ato` = `{role_id: talent_id}`, lido sob a T6."""
    erros: dict[str, str] = {}
    if pedido.multas_malformadas:
        erros["multas"] = "Envie as multas como uma lista de {role_id, valor}."
    for role_id, (valor, invalido, visto) in pedido.multas.items():
        erro = _erro_do_valor_da_multa(valor, invalido)
        if erro:
            erros[f"multa_{role_id}"] = erro
        elif valor and valor > 0 and role_id not in papeis_do_ato:
            erros[f"multa_{role_id}"] = "Esta escalação não está no cancelamento: confira o artista e o dia."
        elif valor and valor > 0 and visto is not None and papeis_do_ato[role_id] != visto:
            erros[f"multa_{role_id}"] = "O artista desta vaga mudou desde que a tela abriu: recarregue e confira."
    return erros


def _multas_do_ato(canc, pedido: PedidoDeCancelamento, actor: User) -> list[SpecialExpense]:
    """As multas do corpo do ato, nas linhas do elenco recém-congeladas (pela vaga)."""
    if canc is None or not pedido.multas:
        return []
    db.session.flush()
    gastos = []
    for linha in canc.elenco:
        valor = pedido.multas.get(linha.role_id, (None, False, None))[0]
        if valor and valor > 0 and linha.special_expense_id is None:
            gastos.append(_registrar_multa(linha, valor, actor))
    return gastos


def lancar_multas_do_cancelado(event: CalendarEvent, *, corpo: dict[str, Any] | None, actor: User) -> list[int]:
    """`POST /api/events/<id>/multas` (contracts §4): a multa depois do ato, por linha do elenco. Sem commit.

    T1 → T2 → 409 `nao_cancelado` → 400. A linha vale quando é do cancelamento deste evento ou do
    dia dele; a multa já lançada se corrige em Gastos Extras. A data do gasto é a do lançamento (P-34).
    """
    from app.constants import CODIGO_NAO_CANCELADO
    from app.models import EventCancellationElenco

    corpo = corpo if isinstance(corpo, dict) else {}
    itens = corpo.get("multas")
    travar_grupo(event)  # T1
    _ler_congelados([event.id])  # T2
    if not event.is_cancelled:
        raise CancelValidationError("Este evento não está cancelado.", status=409, codigo=CODIGO_NAO_CANCELADO)
    if not isinstance(itens, list):
        raise CancelValidationError("Informe a multa de ao menos um artista", field="multas")
    pedidos: dict[int, tuple[Decimal | None, bool]] = {}
    for item in itens:
        eid = item.get("elenco_id") if isinstance(item, dict) else None
        if not isinstance(eid, int) or isinstance(eid, bool):
            raise CancelValidationError("Envie as multas como uma lista de {elenco_id, valor}.", field="multas")
        pedidos[eid] = _decimal(item.get("valor"))
    ids = list(pedidos)
    linhas = {
        x.id: x
        for x in EventCancellationElenco.query.filter(EventCancellationElenco.id.in_(ids or [-1]))
        .order_by(EventCancellationElenco.id)
        .with_for_update()
        .populate_existing()
        .all()
    }
    erros: dict[str, str] = {}
    lancar: list[tuple[Any, Decimal]] = []
    for eid, (valor, invalido) in pedidos.items():
        erro = _erro_do_valor_da_multa(valor, invalido)
        if erro:
            erros[f"multa_{eid}"] = erro
            continue
        if not valor:
            continue
        linha = linhas.get(eid)
        if linha is None or event.id not in (linha.cancelamento.event_id, linha.day_event_id):
            erros[f"multa_{eid}"] = "Esta escalação não é do cancelamento deste evento."
        elif linha.special_expense_id is not None:
            erros[f"multa_{eid}"] = "Já há multa lançada para esta escalação: corrija em Gastos Extras."
        else:
            lancar.append((linha, valor))
    if erros:
        raise CancelValidationError("Corrija os campos destacados.", fields=erros)
    if not lancar:
        raise CancelValidationError("Informe a multa de ao menos um artista", field="multas")
    gastos = [_registrar_multa(linha, valor, actor) for linha, valor in lancar]
    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    texto = "Multa ao elenco lançada: " + "; ".join(
        f"{(linha.talent.full_name if linha.talent else '?')} ({linha.character_name}) {_brl(valor)}"
        for linha, valor in lancar
    )
    db.session.add(EventLog(event_id=event.id, actor_name=actor.name, actor_role=papel, message=texto[:2000]))
    return [g.id for g in gastos]


def _elenco_do_resumo(cancelamento, dia_id: int | None = None) -> list[dict[str, Any]]:
    """O `elenco[]` do resumo (contracts §0): das linhas congeladas no ato, nunca da escala de hoje.

    `na_vaga` diz se o artista ainda está na vaga (o Casting pode tê-lo tirado depois). `dia_id`
    recorta um dia (o satélite do "todos" mostra as linhas dele, que moram no principal). Gancho da
    mutação do 45c: o detalhe o chama pelo módulo.
    """
    if cancelamento is None:
        return []
    saida = []
    linhas = [x for x in cancelamento.elenco if dia_id is None or x.day_event_id == dia_id]
    for linha in sorted(linhas, key=lambda x: x.id):
        talento = linha.talent
        dia = linha.day_event
        gasto = linha.special_expense
        saida.append({
            "elenco_id": linha.id,
            "talent_id": linha.talent_id,
            "artista": (talento.artistic_name or talento.full_name) if talento else None,
            "vaga": linha.character_name,
            "dia": {"id": linha.day_event_id, "data": dia.start_at.date().isoformat() if dia and dia.start_at else None},
            "cache_referencia": _f(linha.cache_reference),
            "na_vaga": bool(linha.role_id is not None and linha.role is not None and linha.role.talent_id == linha.talent_id),
            "talent_pix_informado": bool(talento and (talento.pix_key or "").strip()),
            "multa": {"gasto_id": gasto.id, "valor": _f(gasto.amount)} if gasto is not None else None,
        })  # fmt: skip
    return saida


def dias_dos_gastos(event: CalendarEvent) -> list[int]:
    """De que dias o painel de gastos lê (data-model §5): o principal vivo, pelos dias vivos; o
    cancelado em `venda` (o "todos"), com os dias `satelite` dele; os outros cancelados (`satelite`,
    `dia`, `virtual`, `legado`), só o próprio dia. A API e o Jinja usam esta mesma régua."""
    from app.calendar.group_ops import dias_vivos
    from app.constants import REGIME_SATELITE, REGIME_VENDA
    from app.models import EventCancellation

    if not event.is_cancelled:
        return [ge.id for ge in dias_vivos(event)] or [event.id]
    canc = event.cancelamento
    if canc is not None and canc.regime == REGIME_VENDA:
        satelites = EventCancellation.query.filter(
            EventCancellation.group_leader_id == event.id, EventCancellation.regime == REGIME_SATELITE
        ).all()
        return [event.id, *(x.event_id for x in satelites)]
    return [event.id]


def _dias_com_cache_pago(ids: list[int]) -> set[int]:
    """Os dias com escalação de cachê já pago ou no banco (o diálogo explica; a recusa é da H6)."""
    return {r.event_id for r in _papeis_com_cache_pago(ids)}


def _vivos_por_id(ids: list[int]) -> dict[int, bool]:
    """`{id: vivo}` dos dias, por consulta."""
    return {i: c is None for i, c in db.session.query(CalendarEvent.id, CalendarEvent.cancelled_at).filter(CalendarEvent.id.in_(ids))}


def _grupo_do_impacto(event: CalendarEvent, ids: list[int]) -> dict[str, Any] | None:
    """O bloco `grupo` do impacto (contracts §2): os dias, e no 1º dia o próximo principal."""
    from app.constants import now_sp

    if len(ids) <= 1:
        return None
    dias = sorted(CalendarEvent.query.filter(CalendarEvent.id.in_(ids)).all(), key=lambda e: (e.start_at or datetime.max, e.id))
    pagos = _dias_com_cache_pago(ids)
    hoje = now_sp().date()
    proximo_vivo = _quem_recebe_a_venda(_dias_vivos_ordenados(event, dias)) if event.group_leader_id is None else None
    return {
        "principal_id": event.group_leader_id or event.id,
        "dias": [
            {
                **_evento_curto(d),
                "cancelado": d.is_cancelled,
                "cache_pago": d.id in pagos,
                "faltam_dias": (d.start_at.date() - hoje).days if d.start_at else None,
            }
            for d in dias
        ],
        "proximo_principal": _evento_curto(proximo_vivo) if proximo_vivo is not None else None,
    }


def resumo_impacto(event: CalendarEvent, *, show_financeiro: bool = True) -> dict[str, Any]:
    """O que será perdido/afetado — a tela mostra isso ANTES de confirmar. No grupo (H5), o bloco
    `grupo` e o elenco dos dias vivos (o "todos" leva todos; a tela filtra por `day_event_id`).

    Foi a falta disso que deixou a exclusão ser uma decisão às cegas: o diálogo antigo só
    perguntava "tem certeza?", sem dizer que havia pagamento recebido e comissão paga em jogo.

    Feature 306 (contracts §2): o regime que o ato daria, o pago e o já devolvido **do grupo**
    (`ids_do_grupo`; `total_recebido` continua o do próprio evento), o máximo a devolver, a nota
    e a alíquota de referência, os BVs, a comissão em jogo e os comprovantes sem valor.
    """
    from app.constants import REGIME_DIA, REGIME_VENDA, REGIME_VIRTUAL, now_sp
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
    vivos = [i for i, c in _vivos_por_id(ids).items() if c] if event.group_leader_id is None else [event.id]
    if event.group_leader_id is not None:
        regime = REGIME_DIA
    else:
        regime = REGIME_VIRTUAL if is_loja_virtual(event) else REGIME_VENDA

    return {
        "acao": "cancelar" if event.is_google_missing or not pode_excluir(event) else "excluir",
        "sale_value": float(event.sale_value or 0),
        "total_recebido": float(recebido),
        "devolucao_sugerida": float(recebido),
        "cliente_nome": event.client.name if event.client else None,
        "elenco": [
            {
                # O artista que a tela viu: a multa no ato confere que a vaga ainda é dele.
                "talent_id": r.talent_id,
                "character_name": r.character_name,
                "talent_name": r.talent.full_name if r.talent else None,
                "cache_value": float(r.cache_value or 0),
                "payment_status": r.payment_status or "nao_pago",
                "role_id": r.id,
                "day_event_id": r.event_id,
                "talent_pix_informado": bool(r.talent and (r.talent.pix_key or "").strip()),
                "talent_email_informado": bool(r.talent and (r.talent.email_contact or "").strip()),
                **({"talent_pix": r.talent.pix_key if r.talent else None} if show_financeiro else {}),
            }
            for r in elenco_do_ato(event, dias=vivos or [event.id])
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
        "regime": regime,
        "grupo": _grupo_do_impacto(event, ids),
        # A venda do grupo hoje (a do principal): de onde parte o "Novo valor da venda" do corte.
        "venda_do_grupo": float(
            (db.session.get(CalendarEvent, principal_id).sale_value if principal_id != event.id else event.sale_value)
            or 0
        ),
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
        # H6 (contracts §2): os ensaios que cairiam (dos dias vivos que o "todos" alcança) e o
        # cachê pago (> 0 → o diálogo explica e não oferece cancelar).
        "ensaios": [
            {"id": e.id, "data": e.start_at.isoformat() if e.start_at else None, "local": e.location,
             "day_event_id": e.parent_event_id}
            for e in _ensaios_dos_dias(CalendarEvent.query.filter(CalendarEvent.id.in_(vivos or [event.id])).all())
        ],  # fmt: skip
        "cache_pago": float(
            sum((cache_pago_do_evento(d) for d in CalendarEvent.query.filter(CalendarEvent.id.in_(vivos or [event.id]))), Decimal("0"))
        ),
    }


# ── As correções do cancelado: devolução, dinheiro e a regra única das portas ─────────────────


def limites_da_devolucao(event: CalendarEvent) -> dict[str, Any] | None:
    """Piso e teto do "Alterar devolução" no `venda`, no `dia` e no `legado` (data-model §7.2).

    A mesma régua da gravação (`_regua_da_devolucao`). `None` nos regimes sem devolução própria
    (`satelite`, `virtual`).
    """
    from app.constants import REGIME_DIA, REGIME_LEGADO, REGIME_VENDA
    from app.models import EventCancellation

    canc = event.cancelamento
    regime = canc.regime if canc is not None else REGIME_LEGADO
    if not event.is_cancelled or regime not in (REGIME_VENDA, REGIME_LEGADO, REGIME_DIA):
        return None
    principal_id = event.group_leader_id or event.id
    ids = ids_do_grupo([principal_id])[principal_id]
    congelados = {c.event_id: c for c in EventCancellation.query.filter(EventCancellation.event_id.in_(ids)).all()}
    regua = _regua_da_devolucao(event, canc, congelados, ids)
    atual = _dinheiro(sum((_dinheiro(d.amount) for d in regua.ajustaveis), Decimal("0"))) + regua.fixas
    # `refaz_retido`: o novo total mexe num retido — o próprio (`venda`) ou, no `dia`, o do 1º dia
    # já cancelado em `venda`; com o principal vivo, a venda do grupo não muda.
    if regime == REGIME_DIA:
        do_principal = congelados.get(event.group_leader_id)
        refaz = do_principal is not None and do_principal.regime == REGIME_VENDA
    else:
        refaz = regime == REGIME_VENDA
    # `atual`: o total que o Alterar parte — no `dia`, o daquele dia (não o devolvido do grupo).
    return {"piso": float(regua.piso), "teto": float(regua.teto), "atual": float(atual), "refaz_retido": refaz}


def _piso_da_devolucao(aprovadas: list[SpecialExpense]) -> Decimal:
    """O que já saiu (pago ou no banco) não volta: é o piso do novo total."""
    return _dinheiro(
        sum(
            (_dinheiro(d.amount) for d in aprovadas if (d.payment_status or "nao_pago") in ("pago", "no_banco")),
            Decimal("0"),
        )
    )


def reaplicar_cancelado(
    event: CalendarEvent, *, motivo: str, motivos: dict[int, str] | None = None
) -> list[dict]:
    """Refaz a comissão do retido de um cancelado `venda` pelo dinheiro de agora. Não faz commit.

    A cheia, a venda e o beneficiário são os congelados; o retido é o do grupo, ao vivo; o BV do
    retido é lido na hora (`bv_da_planilha`), então não há o que gravar nele. Supõe a T4 tomada.
    A cheia não se recalcula aqui (o comprovante não a mexe): quem corrige a venda recongela antes
    (`recongelar_do_comercial`) e passa os `motivos` por beneficiário da troca de vendedor.
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
    plano = comissoes_ops.reconciliar_comissao_do_cancelado(event, alvos, motivo=motivo, motivos=motivos)
    db.session.expire(event, ["commission_payments"])
    return plano


def travar_para_corrigir_venda(event: CalendarEvent, *, novo_vendedor_id: Any = None) -> None:
    """T1 → T2 → T4 da correção comercial do cancelado (plan §Travas), antes de gravar. Sem commit.

    O grupo (pelo nome do módulo: o 16c-corrida troca `travar_grupo` para injetar a corrida), os
    congelados e, num SELECT só, as linhas do evento e as abertas dos beneficiários antigo e novo —
    o primeiro repasse aberto de cada um não pode mudar entre a leitura e a escrita. É a trava de
    `primeiro_repasse_aberto(…, travar=True)` para os dois de uma vez, em ordem de id.
    """
    from app.financeiro import comissoes_ops
    from app.models import SiteSetting

    ids = [e.id for e in travar_grupo(event)]
    canc = _ler_congelados(ids).get(event.id)
    try:
        novo = int(novo_vendedor_id) if novo_vendedor_id not in (None, "") else None
    except (TypeError, ValueError):
        novo = None
    responsavel = (
        comissoes_ops._educamanto_responsavel(SiteSetting.query.get(1)) if event.is_educamanto else None
    )
    antigo = canc.commission_seller_id if canc is not None else None
    _travar_linhas_de_comissao(
        ids, {antigo, novo, getattr(responsavel, "id", None), *_beneficiarios_das_linhas(ids)}
    )


def _bv_congelado_total(canc) -> Decimal:
    """O BV da cheia recongelada: Σ `original_amount` das linhas com acréscimo (a órfã não conta),
    nunca `_event_bv_total` do evento vivo (data-model §8, invariante 3)."""
    return _dinheiro(
        sum((_dinheiro(b.original_amount) for b in canc.bvs if b.acrescimo_id is not None), Decimal("0"))
    )


def recongelar_do_comercial(
    event: CalendarEvent, *, actor: User, motivo: str | None = None, cortesia_antes: bool | None = None
) -> list[dict]:
    """A correção da venda do cancelado `venda` pelo Superadmin (FR-049–FR-051; R20). Sem commit.

    O evento já está gravado; compara-o com o congelado e recongela na mesma transação:

    - **taxa**: só a taxa explícita nova troca a congelada (`_mesma_taxa`); a padrão das
      Configurações não alcança o cancelado. Motivo "taxa corrigida", para mais e para menos;
    - **venda**: a nova vira a congelada. A cortesia zera a venda viva, não a congelada: a cheia vai
      a 0 pelo portão do beneficiário, e a volta da cortesia a restaura;
    - **vendedor** (`_mesmo_vendedor`): o congelado passa ao novo; o antigo vai ao alvo 0 ("vendedor
      trocado — devolve o já recebido") e o novo leva o alvo inteiro ("— comissão do retido"), numa
      chamada só da reconciliação;
    - a cheia sai sempre dos insumos congelados (taxa, BV das linhas, custo do ato), pelo nome do
      módulo: a mutação do 16e tira a taxa e a conta cai na de hoje;
    - **o portão vivo não é relido** (converge, T106): sem troca de vendedor, quem recebe é o
      beneficiário congelado e a fórmula EducaManto é a do ato (`commission_cost`); o vendedor que
      deixou de comissionar e o responsável trocado em Configurações não alcançam o cancelado. Só a
      troca de vendedor, ou a cortesia desfeita num cancelado que congelou sem beneficiário
      (`cortesia_antes`), relê `_beneficiario_comissionado`.

    Venda nova abaixo do retido não é recusada: a comissão do retido tem teto na cheia. Os outros
    regimes não têm o que recongelar (devolve `[]`).
    """
    from app.calendar.event_ops import _mesma_taxa, _mesmo_valor, _mesmo_vendedor
    from app.constants import (
        MOTIVO_AJUSTE_CORRECAO_VENDA,
        MOTIVO_AJUSTE_TAXA,
        MOTIVO_AJUSTE_TROCA_DEVOLVE,
        MOTIVO_AJUSTE_TROCA_RETIDO,
        REGIME_VENDA,
        now_sp,
    )
    from app.financeiro import comissoes_ops
    from app.models import SiteSetting

    canc = event.cancelamento
    if not event.is_cancelled or canc is None or canc.regime != REGIME_VENDA:
        return []
    mudou: list[str] = []
    motivo = motivo or MOTIVO_AJUSTE_CORRECAO_VENDA
    if event.commission_rate is not None and not _mesma_taxa(canc.commission_rate, event.commission_rate):
        mudou.append(f"taxa {canc.commission_rate}% → {event.commission_rate}%")
        canc.commission_rate = Decimal(str(event.commission_rate))
        motivo = MOTIVO_AJUSTE_TAXA
    if not event.is_cortesia_permuta and not _mesmo_valor(event.sale_value, canc.sale_value):
        mudou.append(f"venda {_brl(canc.sale_value)} → {_brl(event.sale_value)}")
        canc.sale_value = _dinheiro(event.sale_value)
    vendedor_mudou = not _mesmo_vendedor(canc.seller_id, event.seller_id)
    if vendedor_mudou:
        mudou.append("vendedor trocado")
        canc.seller_id = event.seller_id
    antigo = canc.commission_seller_id
    cortesia_mudou = cortesia_antes is not None and bool(cortesia_antes) != bool(event.is_cortesia_permuta)
    if vendedor_mudou or (antigo is None and cortesia_mudou):
        cheia, beneficiario, _taxa = comissoes_ops.comissao_cheia_do_evento(
            event, SiteSetting.query.get(1), venda=canc.sale_value, taxa=canc.commission_rate,
            bv_total=_bv_congelado_total(canc), custo=canc.commission_cost,
        )  # fmt: skip
    else:
        beneficiario = antigo
        cheia = (
            Decimal("0.00")
            if beneficiario is None or event.is_cortesia_permuta
            else comissoes_ops.cheia_do_congelado(
                event, venda=canc.sale_value, taxa=canc.commission_rate,
                bv_total=_bv_congelado_total(canc), custo=canc.commission_cost,
            )  # fmt: skip
        )
    if cheia != _dinheiro(canc.commission_full):
        mudou.append(f"comissão cheia {_brl(canc.commission_full)} → {_brl(cheia)}")
    canc.commission_full = cheia
    canc.commission_seller_id = beneficiario
    canc.updated_at = now_sp()
    canc.updated_by_id = actor.id
    principal_id = event.group_leader_id or event.id
    ids = ids_do_grupo([principal_id])[principal_id]
    motivos: dict[int, str] = {}
    if vendedor_mudou and antigo != beneficiario:
        devolvem = {antigo, *_beneficiarios_das_linhas(ids)} - {beneficiario, None}
        motivos = dict.fromkeys(devolvem, MOTIVO_AJUSTE_TROCA_DEVOLVE)
        if beneficiario is not None:
            motivos[beneficiario] = MOTIVO_AJUSTE_TROCA_RETIDO
    db.session.flush()
    # T4 de novo, já com o beneficiário resolvido (as linhas já travadas não esperam).
    _travar_linhas_de_comissao(ids, {antigo, beneficiario, *_beneficiarios_das_linhas(ids)})
    plano = reaplicar_cancelado(event, motivo=motivo, motivos=motivos)
    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    texto = "Venda do cancelado corrigida" + (f" ({'; '.join(mudou)})" if mudou else "")
    db.session.add(
        EventLog(event_id=event.id, actor_name=actor.name, actor_role=papel, message=texto[:500])
    )
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
                "Informe o valor e insira o comprovante para registrar o pagamento.",
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


def recusar_se_cancelado(event: CalendarEvent, user: User, *, grupo: bool = False) -> None:
    """A regra única das portas (a)–(h) (FR-047): trava o evento, relê e recusa o cancelado.

    Quem não é Superadmin real leva 409 `cancelado`. No vivo, o caminho de hoje segue sob a trava.
    Com `grupo=True` (a aba Comercial, que depois trava o grupo inteiro para recongelar), a trava
    já é a T1 do grupo, em ordem de id — travar só o principal antes subiria um degrau (plan
    §Travas; converge, T116).
    """
    from app.calendar.orcamento_evento_ops import travar_evento

    if grupo:
        travar_grupo(event)
    else:
        travar_evento(event)
    if event.is_cancelled and not pode_editar_venda_do_cancelado(user):
        raise EventoCanceladoError()


# ── Feature 312: a tela do cancelado só para consulta, e nada novo se liga a ele ─────────────


class EventoSomenteConsultaError(CancelValidationError):
    """A trava geral do cancelado (feature 312, FR-011; Q7 = A do dono).

    Vale para TODO papel, o Superadmin inclusive: o que o Superadmin corrige no cancelado são os
    dados de venda, e essas portas não passam por aqui (têm a regra própria da 306,
    `recusar_se_cancelado`; o motivo tem a da 306b). Sai como 409 `cancelado`, o mesmo código das
    outras recusas do cancelado, para a tela recarregar o evento ao recebê-lo.
    """

    MENSAGEM = "Este evento foi cancelado — a tela fica só para consulta."

    def __init__(self, message: str = MENSAGEM) -> None:
        from app.constants import CODIGO_EVENTO_CANCELADO

        super().__init__(message, status=409, codigo=CODIGO_EVENTO_CANCELADO)


class EventoCanceladoVinculoError(CancelValidationError):
    """Ligar algo novo a um evento cancelado (feature 312, FR-013–FR-017; Q2 e Q5 do dono).

    Com `campo`, é 400 com o erro no campo (o vizinho de quem escolhe o evento num formulário:
    vínculo de ensaio, tag NFC, pedido de figurino); sem campo, 409 (a ação é sobre o próprio
    evento: agendar ensaio, presente, formulário, escalar, convidar, link de avaliação).
    """

    def __init__(self, message: str, *, campo: str | None = None) -> None:
        from app.constants import CODIGO_EVENTO_CANCELADO

        super().__init__(
            message, field=campo, status=400 if campo else 409, codigo=CODIGO_EVENTO_CANCELADO
        )


def fechar_pedido_ao_casting_se_vazio(dia: CalendarEvent) -> int:
    """Feature 312 (Q10): sem ninguém mais a tirar e avisar no dia cancelado, o sino do pedido ao
    Casting daquele dia fica lido para todos (o "aviso some sozinho" da 298). Sem commit: roda na
    transação da remoção. Devolve quantos avisos ficaram lidos."""
    from app.notificacoes import notificacoes_ops as nops

    db.session.flush()
    if elenco_dos_dias([dia.id]):
        return 0
    return nops.marcar_lidas_por_entidade("calendar_event", dia.id, nops.KIND_EVENTO_CANCELADO_ESCALA)


def exigir_evento_vivo(event: CalendarEvent | None) -> None:
    """Recusa toda escrita na tela de um evento cancelado (FR-011). Só olha `cancelled_at`:
    o pedido de exclusão e a marca "Sumiu do Google" não travam nada (FR-010)."""
    if event is not None and event.is_cancelled:
        raise EventoSomenteConsultaError()


def recusar_se_cancelado_para_ligar(
    event: CalendarEvent | None, mensagem: str, *, campo: str | None = None
) -> None:
    """Recusa ligar algo NOVO a um evento cancelado, antes de qualquer escrita, e-mail ou Google.

    Quem chama decide o que é "novo" (reenviar o vínculo que já existe passa): a tag que já era do
    evento, o pedido de figurino que não troca de evento, o formulário que se desliga.
    """
    if event is not None and event.is_cancelled:
        raise EventoCanceladoVinculoError(mensagem, campo=campo)


def _dono_das_aberta(aprovadas: list[SpecialExpense], dono_id: int) -> list[SpecialExpense]:
    """As devoluções ainda não pagas, a do dono primeiro e as outras por id (R12)."""
    abertas = [d for d in aprovadas if (d.payment_status or "nao_pago") == "nao_pago"]
    return sorted(abertas, key=lambda d: (d.event_id != dono_id, d.id))


def _absorver_nas_outras(outras: list[SpecialExpense], restante: Decimal, actor: User) -> None:
    """A redução que sobrou do dono, nas abertas dos outros dias por id: cada uma até zerar."""
    from app.gastos.gastos_ops import _log

    for d in outras:
        if restante >= 0:
            return
        antes = _dinheiro(d.amount)
        novo = antes + restante
        if novo > 0:
            d.amount = novo
            _log(actor, "gasto", d.id, d.description, "editou", f"Alterar devolução: {_brl(antes)} → {_brl(novo)}")
            return
        _log(actor, "gasto", d.id, d.description, "excluiu", "Devolução zerada no Alterar devolução")
        db.session.delete(d)
        restante = novo


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

    As abertas do dono absorvem a diferença e ficam uma só; zerada, é excluída com auditoria. O que
    a redução ainda pede depois vai às abertas dos outros dias (os `satelite` da venda), por id,
    cada uma até zerar. Sem aberta do dono e acima do que já está, nasce o complemento no dono.
    Tocar uma devolução regrava `disbursement_type="cliente"` e completa nome e PIX vazios (FR-020).
    """
    from app.gastos.gastos_ops import _log

    atual = _dinheiro(sum((_dinheiro(d.amount) for d in aprovadas), Decimal("0")))
    diferenca = total - atual
    abertas = _dono_das_aberta(aprovadas, dono.id)
    do_dono = [d for d in abertas if d.event_id == dono.id]
    outras = [d for d in abertas if d.event_id != dono.id]
    herdado = next((d for d in reversed(aprovadas) if d.supplier_name or d.supplier_pix), None)
    for d in abertas:
        d.disbursement_type = "cliente"
        d.supplier_name = d.supplier_name or (nome[:200] or None)
        d.supplier_pix = d.supplier_pix or (pix[:120] or None)
    if diferenca == 0:
        return
    if do_dono:
        fica, *demais = do_dono
        novo = _dinheiro(sum((_dinheiro(d.amount) for d in do_dono), Decimal("0")) + diferenca)
        for d in demais:
            _log(actor, "gasto", d.id, d.description, "excluiu", "Devolução juntada no Alterar devolução")
            db.session.delete(d)
        if novo > 0:
            antes = _dinheiro(fica.amount)
            fica.amount = novo
            if observacao:
                fica.notes = observacao
            _log(
                actor, "gasto", fica.id, fica.description, "editou",
                f"Alterar devolução: {_brl(antes)} → {_brl(novo)}",
            )  # fmt: skip
            return
        _log(actor, "gasto", fica.id, fica.description, "excluiu", "Devolução zerada no Alterar devolução")
        db.session.delete(fica)
        _absorver_nas_outras(outras, novo, actor)
        return
    if diferenca < 0:
        _absorver_nas_outras(outras, diferenca, actor)
        return
    gasto = _registrar_devolucao(
        dono,
        valor=diferenca,
        nome=nome or (herdado.supplier_name if herdado else "") or "",
        pix=pix or (herdado.supplier_pix if herdado else "") or "",
        observacao=observacao,
        actor=actor,
    )
    db.session.flush()
    _log(actor, "gasto", gasto.id, gasto.description, "criou", f"Complemento de devolução {_brl(diferenca)}")


@dataclass
class ReguaDaDevolucao:
    """Piso, teto e as devoluções que o "Alterar devolução" mexe (data-model §7.2)."""

    piso: Decimal
    teto: Decimal
    ajustaveis: list[SpecialExpense]
    fixas: Decimal  # as devoluções dos dias `dia` na venda do grupo (só o Alterar do dia as muda)
    teto_e_409: bool  # no `dia`, acima do teto é 409 `acima_do_teto`; no resto, 400


def _regua_da_devolucao(event: CalendarEvent, canc, congelados: dict, ids: list[int]) -> ReguaDaDevolucao:
    """A régua do Alterar devolução, a mesma no diálogo (`limites_da_devolucao`) e na gravação."""
    from app.constants import REGIME_DIA, REGIME_VENDA

    pago, _ = _dinheiro_do_grupo(ids)
    aprovadas = (
        SpecialExpense.query.filter(filtro_devolucao(), SpecialExpense.event_id.in_(ids)).order_by(SpecialExpense.id).all()
    )
    soma = lambda xs: _dinheiro(sum((_dinheiro(d.amount) for d in xs), Decimal("0")))  # noqa: E731
    regime = canc.regime if canc is not None else None
    if regime == REGIME_DIA:
        do_dia = [d for d in aprovadas if d.event_id == event.id]
        das_outras = [d for d in aprovadas if d.event_id != event.id]
        outras = soma(das_outras)
        # P-52: o mínimo com o "já devolvido" de quando este dia foi cortado. A devolução de um dia
        # cancelado depois foi pensada contando com a deste, e não o desfaz.
        depois = {eid for eid, c in congelados.items() if c.id is not None and canc.id is not None and c.id > canc.id}
        antes = soma([d for d in das_outras if d.event_id not in depois])
        minima = Decimal("0.00")
        if canc.sale_value_after is not None and canc.sale_value_before is not None:
            minima = _devolucao_minima(pago, antes, _dinheiro(canc.sale_value_after), _dinheiro(canc.sale_value_before))
        return ReguaDaDevolucao(
            piso=max(_piso_da_devolucao(do_dia), minima), teto=max(Decimal("0.00"), pago - outras),
            ajustaveis=do_dia, fixas=Decimal("0.00"), teto_e_409=True,
        )  # fmt: skip
    if regime == REGIME_VENDA:
        dias_dia = {eid for eid, c in congelados.items() if c.regime == REGIME_DIA}
        fixas = [d for d in aprovadas if d.event_id in dias_dia]
        ajustaveis = [d for d in aprovadas if d.event_id not in dias_dia]
        return ReguaDaDevolucao(
            piso=_piso_da_devolucao(ajustaveis) + soma(fixas), teto=pago, ajustaveis=ajustaveis,
            fixas=soma(fixas), teto_e_409=False,
        )  # fmt: skip
    return ReguaDaDevolucao(
        piso=_piso_da_devolucao(aprovadas), teto=pago, ajustaveis=aprovadas, fixas=Decimal("0.00"), teto_e_409=False
    )


def alterar_devolucao(event: CalendarEvent, *, corpo: dict[str, Any] | None, actor: User) -> CalendarEvent:
    """O "Alterar devolução" do cancelado `venda`, `dia` e `legado` (FR-017; contracts §3). Sem commit.

    O regime só se lê depois de T1: antes da trava, só a forma de `devolucao_total`. Depois:
    T1 → T2 → 409 `nao_cancelado` → 409 `regime_sem_retido` → T4 (no `venda`, e no `dia` com o
    principal cancelado em `venda`) → T5 → 400 com todos os campos → 409 `abaixo_do_piso` → 409
    `acima_do_teto` (só no `dia`) → grava → refaz a comissão do retido de quem a tem.

    No `dia`, o total é o daquele dia; com o principal vivo nada se refaz (a venda do grupo não
    muda pela devolução do dia); com o principal cancelado em `venda`, o retido dele muda.
    """
    from app.constants import (
        CODIGO_ABAIXO_DO_PISO,
        CODIGO_ACIMA_DO_TETO,
        CODIGO_NAO_CANCELADO,
        CODIGO_REGIME_SEM_RETIDO,
        MOTIVO_AJUSTE_RETIDO,
        REGIME_DIA,
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
    if regime not in (REGIME_VENDA, REGIME_LEGADO, REGIME_DIA):
        raise CancelValidationError(
            "Este cancelamento não tem devolução própria para alterar.",
            status=409,
            codigo=CODIGO_REGIME_SEM_RETIDO,
        )
    principal = next((e for e in eventos if e.id == event.group_leader_id), None) if regime == REGIME_DIA else event
    canc_principal = congelados.get(principal.id) if principal is not None else None
    refaz = principal if canc_principal is not None and canc_principal.regime == REGIME_VENDA and principal.is_cancelled else None
    if refaz is not None:
        _travar_linhas_de_comissao(ids, {canc_principal.commission_seller_id, *_beneficiarios_das_linhas(ids)})  # T4
    _travar_devolucoes(ids)  # T5
    regua = _regua_da_devolucao(event, canc, congelados, ids)
    atual = _dinheiro(sum((_dinheiro(d.amount) for d in regua.ajustaveis), Decimal("0"))) + regua.fixas

    erros: dict[str, str] = {}
    if total < 0:
        erros["devolucao_total"] = "O total devolvido não pode ser negativo."
    elif total > regua.teto and not regua.teto_e_409:
        erros["devolucao_total"] = f"Acima do que a cliente pagou ({_brl(regua.teto)})."
    nasce_complemento = total > atual and not [d for d in _dono_das_aberta(regua.ajustaveis, event.id) if d.event_id == event.id]
    herdado = next((d for d in reversed(regua.ajustaveis) if d.supplier_name or d.supplier_pix), None)
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
    if total < regua.piso:
        raise CancelValidationError(
            f"Já saíram {_brl(regua.piso)} de devolução (pagos, no banco ou de um dia cortado): "
            "o novo total não pode ser menor.",
            status=409,
            codigo=CODIGO_ABAIXO_DO_PISO,
            piso=float(regua.piso),
        )
    if regua.teto_e_409 and total > regua.teto:
        raise CancelValidationError(
            f"Acima do que é possível devolver neste dia ({_brl(regua.teto)}: o pago do grupo menos as "
            "devoluções dos outros dias).",
            status=409,
            codigo=CODIGO_ACIMA_DO_TETO,
            teto=float(regua.teto),
        )

    _aplicar_novo_total(
        event, regua.ajustaveis, total - regua.fixas, nome=nome, pix=pix, observacao=observacao, actor=actor
    )
    if canc is not None:
        if imposto_enviado:
            canc.retained_tax = imposto
        canc.updated_at = now_sp()
        canc.updated_by_id = actor.id
    if refaz is not None:
        db.session.flush()
        reaplicar_cancelado(refaz, motivo=MOTIVO_AJUSTE_RETIDO)
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


def _tem_devolucao(resumo: ResumoCancelado, estado: str) -> bool:
    """O cancelado entra no filtro `estado` da página (feature 312): `sem` = nenhuma devolução.

    O satélite do "todos" carrega no resumo as devoluções do grupo inteiro (o dinheiro mora no 1º
    dia), mas a tela não as mostra nele: o filtro casa só as do próprio dia — senão "A devolver"
    trazia os N dias de um grupo com uma devolução só (converge da 312).
    """
    from app.constants import REGIME_SATELITE

    devolucoes = resumo.devolucoes
    if resumo.regime == REGIME_SATELITE:
        devolucoes = [g for g in devolucoes if g.event_id == resumo.event.id]
    estados = {(g.payment_status or "nao_pago") for g in devolucoes}
    return not estados if estado == "sem" else estado in estados


FILTROS_DEVOLUCAO = ("nao_pago", "no_banco", "pago", "sem")
LIMITE_SEM_MES = 200


def listar_cancelamentos(
    *,
    flags: dict[str, Any] | None = None,
    mes: date | None = None,
    devolucao: str | None = None,
) -> dict[str, Any]:
    """A página de Cancelamentos: pedidos pendentes + eventos cancelados (features 224, 306, 312).

    Feature 306 (contracts §15): cada cancelado traz o `resumo` em lote, com todas as devoluções e o
    PIX só com `show_financeiro`. Feature 312:
    - `mes` (o 1º dia): só os cancelados naquele mês (horário de São Paulo, como `cancelled_at` é
      gravado), sem limite; sem `mes`, os 200 mais recentes e o total diz "dos listados";
    - `devolucao` ∈ `FILTROS_DEVOLUCAO`: pelo estado das devoluções DO RESUMO (o regime `venda` soma
      as do grupo, e a passagem da venda move a devolução de evento — um EXISTS por `event_id`
      divergiria da coluna que a tela mostra). O evento entra em cada estado que tem; `sem` = nenhuma
      devolução. Aplicado antes do corte de 200;
    - sai o objeto `devolucao` legado (o "ciclo" da 306 passou; o bundle dela só o lia sem `resumo`).
    """
    pendentes = (
        CalendarEvent.query.filter(
            CalendarEvent.deletion_requested_at.isnot(None),
            CalendarEvent.cancelled_at.is_(None),
        )
        .order_by(CalendarEvent.deletion_requested_at.desc())
        .all()
    )
    consulta = CalendarEvent.query.filter(CalendarEvent.cancelled_at.isnot(None))
    if mes is not None:
        inicio = datetime(mes.year, mes.month, 1)
        fim = datetime(mes.year + (mes.month // 12), mes.month % 12 + 1, 1)
        consulta = consulta.filter(CalendarEvent.cancelled_at >= inicio, CalendarEvent.cancelled_at < fim)
    consulta = consulta.order_by(CalendarEvent.cancelled_at.desc(), CalendarEvent.id.desc())
    # Sem mês e sem filtro de devolução, o corte é na consulta; com o filtro, depois dele.
    cancelados = consulta.limit(LIMITE_SEM_MES).all() if mes is None and not devolucao else consulta.all()

    resumos = resumos_cancelados([e.id for e in cancelados])
    if devolucao:
        cancelados = [e for e in cancelados if e.id in resumos and _tem_devolucao(resumos[e.id], devolucao)]
        if mes is None:
            cancelados = cancelados[:LIMITE_SEM_MES]
    total_retido = sum((resumos[e.id].retido for e in cancelados if e.id in resumos), Decimal("0.00"))
    ver_motivo = flags is None or bool(flags.get("show_comercial"))

    return {
        "total_retido": float(total_retido),
        "total_retido_escopo": "periodo" if mes is not None else "listados",
        "filtros": {"mes": mes.strftime("%Y-%m") if mes else None, "devolucao": devolucao or None},
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
                # Q9 (312): motivo e autor seguem `show_comercial`, também no "Ver como" — o
                # acesso à página é pelo papel real, o que se mostra segue a flag.
                "cancelled_by": (
                    db.session.get(User, e.cancelled_by_id).name
                    if e.cancelled_by_id and ver_motivo
                    else None
                ),
                "reason": e.cancellation_reason if ver_motivo else None,
                "resumo": serializar_resumo_cancelado(resumos[e.id], flags or {}) if e.id in resumos else None,
            }
            for e in cancelados
        ],
    }
