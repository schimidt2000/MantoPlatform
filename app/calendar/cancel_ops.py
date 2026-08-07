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

from datetime import datetime
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
    """Erro de negócio no cancelamento (ex.: cancelar evento líder de grupo)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def total_recebido(event: CalendarEvent) -> Decimal:
    """Soma dos comprovantes de pagamento da cliente nesse evento."""
    total = (
        db.session.query(db.func.coalesce(db.func.sum(EventPayment.amount), 0))
        .filter(EventPayment.event_id == event.id)
        .scalar()
    )
    return Decimal(str(total or 0))


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
        CancelValidationError: motivo vazio, evento já cancelado, ou evento líder de grupo.
    """
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
        gasto = SpecialExpense.query.filter_by(
            event_id=event.id, disbursement_type="cliente"
        ).first()
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
