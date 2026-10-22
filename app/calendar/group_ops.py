"""Agrupamento comercial de eventos: agrupar, desagrupar e nomear (features 053, 054, 055).

Funções puras (sem `flask.request`, `render_template`, `flash` ou `current_user`) — quem lê o
formulário, decide o HTTP e faz o commit é a camada de rota. O núcleo saiu de
`app/calendar/routes.py` para poder ser chamado tanto pela API React quanto pelo Jinja legado
enquanto ele existir, e para sobreviver à remoção dele.

## O que é um grupo

Não existe tabela de grupo: é uma auto-referência em estrela em `calendar_events`. O satélite
aponta para o principal por `group_leader_id`, e `group_name` só é preenchido no principal.
"Ser principal" não é estado gravado — é ter filhos (`CalendarEvent.is_group_leader`). Dissolver
um grupo é, portanto, apenas zerar o `group_leader_id` de cada satélite.

## O que agrupar destrói

Agrupar **apaga os 14 campos comerciais** do satélite (venda, vendedor, comissão, nota fiscal,
parcelas, vínculo com o orçamento): a partir dali o dinheiro do contrato mora no principal.
Desagrupar **não devolve** esses valores. Por isso duas travas que o Jinja não tinha:

1. `snapshot_comercial` grava os valores no histórico do evento ANTES de zerar. Não restaura
   sozinho — serve para consultar e redigitar quando alguém agrupa errado, que era uma perda
   irreversível e silenciosa até aqui.
2. `agrupar` aceita um `sincronizar_comissao` injetado e o chama para cada satélite depois de
   zerar a venda. Sem isso a linha de comissão do satélite ficava órfã: venda zerada e comissão
   ainda a pagar. A função injetada só cancela o que está *a pagar* — comissão já paga é
   histórico e sobrevive, porque dinheiro que saiu não se desfaz por software.

A injeção existe para este módulo não importar de `app/financeiro/`, que puxaria a régua de
comissão inteira (9 ramos) para dentro do domínio da agenda. Mesmo padrão do e-mail em
`portal_account_ops`.

## O dia cancelado (feature 306)

O dia cancelado fica no grupo (é o histórico da venda), mas não entra nem sai dele: agrupar com
um cancelado, desagrupar um dia cancelado ou removê-lo pelo principal é recusado com 409
`cancelado`, também para o Superadmin. As duas portas travam e releem os eventos em ordem de id
antes de decidir, na mesma ordem do ato. `dias_vivos` é a régua única de leitura do grupo sem os
dias cancelados (custo, gastos e KPI do principal vivo). `passar_venda` leva a venda do antigo 1º
dia ao novo quando só o 1º dia é cancelado, e o principal muda: os campos de venda e o nome do grupo
passam ao novo, todo dia passa a apontar para ele e o antigo, cancelado, vira satélite. As linhas
(comprovantes, parcelas, comissão…) são as mesmas, com o mesmo valor e as mesmas datas: só o
`event_id` delas muda.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app import db
from app.models import (
    CalendarEvent,
    CommissionPayment,
    EventAcrescimo,
    EventClient,
    EventContract,
    EventInstallment,
    EventInvoice,
    EventLog,
    EventPayment,
    EventReimbursement,
    FormResponse,
)

# Campos que deixam de ser do satélite ao entrar num grupo. `with_invoice` e
# `is_cortesia_permuta` são booleanos e voltam a False; o resto vira NULL.
SATELLITE_FIELDS_CLEARED = (
    "sale_value", "sale_value_gross", "sale_date", "with_invoice",
    "is_cortesia_permuta", "seller_id", "commission_rate",
    "payment_method", "payment_installments", "payment_due_date",
    "transport_value", "acrescimo_value", "invoice_file", "orcamento_history_id",
)

_BOOLEANOS = ("with_invoice", "is_cortesia_permuta")

#: Feature 306 (FR-059; data-model §6.3): os campos que a passagem da venda leva do antigo 1º dia ao
#: novo — os 14 do satélite, o vencimento da nota e o nome do grupo.
CAMPOS_DA_PASSAGEM = (*SATELLITE_FIELDS_CLEARED, "invoice_due_date", "group_name")

#: As tabelas cujas linhas a passagem MOVE (só o `event_id` muda; nunca apagar e recriar). Além
#: delas: a devolução aprovada ligada ao antigo e os clientes que faltam no novo.
TABELAS_DA_PASSAGEM = (
    EventPayment,
    EventInstallment,
    EventInvoice,
    EventContract,
    EventReimbursement,
    EventAcrescimo,
    CommissionPayment,
    FormResponse,
)

ACTOR_ROLE = "Comercial"


def has_financial_data(event: CalendarEvent) -> bool:
    """True se o evento já tem valor de venda preenchido — gatilho da confirmação (FR-005)."""
    return bool(event.sale_value)


def group_events(event: CalendarEvent) -> list[CalendarEvent]:
    """Todos os eventos do mesmo grupo comercial que `event`, o principal primeiro.

    Se `event` não pertence a nenhum grupo, devolve ``[event]`` — mesmo comportamento de um
    evento avulso, sem agregação (feature 137).
    """
    if event.is_satellite:
        leader = event.group_leader
        return [leader, *leader.satellites]
    if event.is_group_leader:
        return [event, *event.satellites]
    return [event]


def dias_vivos(event: CalendarEvent) -> list[CalendarEvent]:
    """O grupo de `event` sem os dias cancelados, o principal primeiro (feature 306).

    A régua única de leitura do grupo vivo: o custo (cachês e gastos), o BV e o KPI do principal
    vivo não contam o dia cancelado — o dinheiro dele já saiu da venda pelo corte. Sem trava.
    """
    return [e for e in group_events(event) if not e.is_cancelled]


def _travar_em_ordem(eventos: list[CalendarEvent]) -> None:
    """`FOR UPDATE` dos eventos em ordem de id e releitura (a ordem do ato: nada cruza a trava)."""
    db.session.flush()
    ids = sorted({e.id for e in eventos if e is not None and e.id is not None})
    if not ids:
        return
    relidos = (
        CalendarEvent.query.filter(CalendarEvent.id.in_(ids))
        .order_by(CalendarEvent.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    for ev in relidos:
        db.session.expire(ev, ["satellites", "group_leader"])


def recusar_cancelado_no_grupo(eventos: list[CalendarEvent]) -> None:
    """Trava, relê e recusa o evento cancelado numa porta de grupo (feature 306, FR-061).

    Vale para o Superadmin também: o dia cancelado é histórico da venda do grupo — soltá-lo ou
    juntar um cancelado a outro grupo mudaria de quem é o dinheiro que já foi congelado.

    Raises:
        CancelValidationError: 409 `cancelado`; nada foi gravado.
    """
    _travar_em_ordem(eventos)
    _recusar_os_cancelados(eventos)


def _recusar_os_cancelados(eventos: list[CalendarEvent]) -> None:
    """A recusa do cancelado, sobre eventos já travados e relidos."""
    from app.calendar.cancel_ops import CancelValidationError
    from app.constants import CODIGO_EVENTO_CANCELADO

    for ev in eventos:
        if ev is not None and ev.is_cancelled:
            raise CancelValidationError(
                f'"{ev.title}" está cancelado: evento cancelado não entra em grupo nem sai dele.',
                status=409,
                codigo=CODIGO_EVENTO_CANCELADO,
            )


def _json_safe(valor: Any) -> Any:
    """Converte para algo que `json.dumps` aceite, sem perder precisão de dinheiro."""
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


def snapshot_comercial(event: CalendarEvent) -> dict[str, Any]:
    """Os 14 campos comerciais do evento, prontos para JSON.

    `Decimal` vira string em vez de float de propósito: `float(Decimal("1234.56"))` introduz erro
    de representação, e este snapshot existe justamente para alguém redigitar um valor de venda.
    """
    return {campo: _json_safe(getattr(event, campo)) for campo in SATELLITE_FIELDS_CLEARED}


def apply_satellite(event: CalendarEvent) -> None:
    """Zera os campos comerciais do evento ao vinculá-lo como satélite (FR-005)."""
    for campo in SATELLITE_FIELDS_CLEARED:
        setattr(event, campo, False if campo in _BOOLEANOS else None)


def pode_agrupar(user) -> bool:
    """True se o usuário tem papel para mexer em grupo (Comercial, Financeiro ou Superadmin).

    Recebe o usuário por argumento em vez de ler `current_user`: assim a regra vale igual para a
    API, para o Jinja e para um teste.
    """
    from app.constants import RoleName

    return any(
        r.name.upper() in (RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN)
        for r in user.roles
    )


def validar_agrupamento(
    leader: CalendarEvent, satellites: list[CalendarEvent]
) -> str | None:
    """Regras de integridade da feature 053. Devolve a mensagem de erro, ou None se pode seguir.

    O que estas travas impedem, em ordem de gravidade: grupo ANINHADO (A→B→C), que
    `group_events` — que só olha um nível — ignoraria em silêncio, fazendo o financeiro somar
    errado; e ENSAIO dentro de grupo comercial, que não tem venda para agregar.

    Feature 306: antes de tudo, trava e relê os participantes em ordem de id e recusa o cancelado
    (como principal ou como satélite) com 409 `cancelado`.

    Raises:
        CancelValidationError: um dos eventos está cancelado.
    """
    recusar_cancelado_no_grupo([leader, *satellites])
    if leader.is_satellite:
        return f'"{leader.title}" já é satélite de outro grupo e não pode ser principal.'
    # Um principal que já lidera um grupo PODE receber novos satélites (mesma regra da 053).
    if leader.event_type == "ENSAIO":  # FR-003
        return "Eventos do tipo ENSAIO não podem ser agrupados."
    for sat in satellites:
        if sat.id == leader.id:  # FR-004
            return "Não é possível agrupar um evento a ele mesmo."
        if sat.event_type == "ENSAIO":  # FR-003
            return "Eventos do tipo ENSAIO não podem ser agrupados."
        if sat.is_satellite:  # FR-002
            return f'"{sat.title}" já pertence a outro grupo — desagrupe antes de continuar.'
        if sat.is_group_leader:
            return f'"{sat.title}" já é principal de outro grupo — desagrupe os satélites dele antes.'
    return None


def satelites_com_venda(satellites: list[CalendarEvent]) -> list[CalendarEvent]:
    """Os satélites que vão PERDER valor de venda — o que a confirmação precisa mostrar."""
    return [s for s in satellites if has_financial_data(s)]


def agrupar(
    leader: CalendarEvent,
    satellites: list[CalendarEvent],
    group_name: str | None,
    actor_name: str,
    agora: datetime,
    sincronizar_comissao: Callable[[CalendarEvent], None] | None = None,
) -> dict[str, Any]:
    """Vincula os satélites sob o principal, guardando o que será apagado. Commita.

    Args:
        leader: Evento que passa a ser o principal do grupo.
        satellites: Eventos que viram satélites. Já validados por `validar_agrupamento`.
        group_name: Nome do grupo, gravado no principal. Vazio/None mantém o que já havia.
        actor_name: Nome de quem está agrupando, para o histórico.
        agora: Momento do registro (a camada de rota passa o horário de São Paulo).
        sincronizar_comissao: Chamada para cada satélite depois de zerar a venda, para cancelar
            a comissão que ficaria órfã. Opcional só para teste — em produção sempre injetada.

    Returns:
        ``{"leader_id": int, "satellite_ids": list[int]}`` — o `leader_id` importa porque o
        principal pode NÃO ser o evento de onde a ação partiu, e a tela precisa saber para onde ir.
    """
    if group_name:
        leader.group_name = group_name

    for sat in satellites:
        # Snapshot ANTES de zerar: depois de `apply_satellite` os valores não existem mais em
        # lugar nenhum, e desagrupar não os devolve.
        snapshot = snapshot_comercial(sat)
        apply_satellite(sat)
        sat.group_leader_id = leader.id

        if sincronizar_comissao is not None:
            # Com `sale_value` já zerada, a função enxerga o evento como "sem comissão elegível"
            # e cancela a linha que estivesse *a pagar*. Comissão paga é histórico e não muda.
            sincronizar_comissao(sat)

        db.session.add(EventLog(
            event_id=leader.id, actor_name=actor_name, actor_role=ACTOR_ROLE,
            message=f'Agrupou o evento "{sat.title}" como satélite deste contrato',
            created_at=agora,
        ))
        db.session.add(EventLog(
            event_id=sat.id, actor_name=actor_name, actor_role=ACTOR_ROLE,
            message=(
                f'Vinculado ao grupo do evento "{leader.title}" — dados comerciais agora seguem '
                f"o principal. Valores anteriores (para consulta, não são restaurados ao "
                f"desagrupar): {json.dumps(snapshot, ensure_ascii=False)}"
            ),
            created_at=agora,
        ))

    db.session.commit()
    return {"leader_id": leader.id, "satellite_ids": [s.id for s in satellites]}


def desagrupar(
    satelite: CalendarEvent, actor_name: str, agora: datetime, *, lider_esperado: int | None = None
) -> dict[str, Any]:
    """Solta um satélite do grupo. Commita, e NÃO restaura os campos comerciais.

    Returns:
        ``{"event_id": int, "leader_id": int | None}`` — o `leader_id` do ex-principal, para a
        tela invalidar o cache dele também: o KPI do grupo muda no mesmo instante.

    Raises:
        CancelValidationError: 409 `cancelado` — o dia cancelado não sai do grupo (feature 306); 409
            `grupo_mudou` — o principal mudou entre a leitura e a trava (uma passagem da venda).
    """
    from app.calendar.cancel_ops import CancelValidationError
    from app.constants import CODIGO_GRUPO_MUDOU

    lider_id = satelite.group_leader_id
    _travar_em_ordem([satelite, satelite.group_leader])
    if satelite.group_leader_id is None or satelite.group_leader_id != lider_id or (
        lider_esperado is not None and satelite.group_leader_id != lider_esperado
    ):
        raise CancelValidationError(
            "O grupo deste evento mudou enquanto você decidia: recarregue e confira.",
            status=409,
            codigo=CODIGO_GRUPO_MUDOU,
        )
    _recusar_os_cancelados([satelite])
    leader = satelite.group_leader
    satelite.group_leader_id = None

    db.session.add(EventLog(
        event_id=satelite.id, actor_name=actor_name, actor_role=ACTOR_ROLE,
        message=(
            f'Desfez o agrupamento com "{leader.title if leader else "?"}" — os campos '
            "comerciais voltam a ser próprios e editáveis, mas vazios: procure os valores "
            "anteriores no registro de quando foi agrupado."
        ),
        created_at=agora,
    ))
    if leader:
        db.session.add(EventLog(
            event_id=leader.id, actor_name=actor_name, actor_role=ACTOR_ROLE,
            message=f'O evento "{satelite.title}" deixou de ser satélite deste contrato',
            created_at=agora,
        ))

    db.session.commit()
    return {"event_id": satelite.id, "leader_id": leader.id if leader else None}


def renomear_grupo(
    leader: CalendarEvent, novo_nome: str | None, actor_name: str, agora: datetime
) -> None:
    """Define, edita ou limpa o nome do grupo — sempre no principal (feature 055). Commita.

    Nome vazio volta ao fallback: a leitura usa `group_display_name`, que cai no título do evento.
    """
    novo_nome = (novo_nome or "").strip()[:200] or None
    leader.group_name = novo_nome
    rotulo = f'"{novo_nome}"' if novo_nome else "o título do evento (sem nome)"
    db.session.add(EventLog(
        event_id=leader.id, actor_name=actor_name, actor_role=ACTOR_ROLE,
        message=f"Nome do grupo definido para {rotulo}",
        created_at=agora,
    ))
    db.session.commit()


#: O rótulo de cada tabela movida no histórico da passagem.
_ROTULO_DA_PASSAGEM = {
    EventPayment: "comprovantes",
    EventInstallment: "parcelas",
    EventInvoice: "notas fiscais",
    EventContract: "contratos",
    EventReimbursement: "reembolsos",
    EventAcrescimo: "acréscimos",
    CommissionPayment: "linhas de comissão",
    FormResponse: "formulários",
}
_COLECOES_DA_PASSAGEM = ("installments", "invoices", "acrescimos", "event_clients", "form_responses", "commission_payments")


def _valor_da_linha(linha: Any) -> Decimal:
    valor = getattr(linha, "amount_brl", None) if isinstance(linha, EventAcrescimo) else getattr(linha, "amount", None)
    return Decimal(str(valor or 0))


def _mover(modelo: Any, antigo: CalendarEvent, novo: CalendarEvent) -> list:
    """As linhas de `modelo` do antigo passam ao novo, uma a uma e com `audit` (nunca recriadas)."""
    from app.utils import audit

    consulta = modelo.query.filter(modelo.event_id == antigo.id).order_by(modelo.id)
    if modelo is CommissionPayment:
        consulta = consulta.with_for_update()  # T4 antes do UPDATE (plan §Travas)
    linhas = consulta.populate_existing().all()
    for linha in linhas:
        linha.event_id = novo.id
        audit("edit", modelo.__tablename__, linha.id, novo.title,
              f"Passagem da venda: do evento #{antigo.id} para o #{novo.id}")  # fmt: skip
    return linhas


def passar_venda(antigo: CalendarEvent, novo: CalendarEvent, *, actor_name: str) -> dict[str, Any]:
    """Leva a venda do antigo 1º dia (que o ato cancela) ao novo 1º dia (FR-058–FR-060; R16). Sem commit.

    As mesmas linhas, com o mesmo valor e as mesmas datas: só o `event_id` muda (`TABELAS_DA_PASSAGEM`,
    a devolução aprovada do antigo e os clientes que faltam no novo); os `CAMPOS_DA_PASSAGEM` passam
    e o antigo fica sem eles; todo dia do grupo passa a apontar para o novo, que perde o
    `group_leader_id`; o congelado do antigo ganha `sale_handed_over`, e os dias cancelados antes
    passam a ter o novo como principal do dinheiro. Ficam no antigo o elenco, os ensaios, a
    logística, o histórico e os outros gastos.

    O ato chama esta função pelo nome do módulo (a mutação do 42 a troca por um "recria"), depois
    de congelar e de marcar a comissão própria do novo, e antes da devolução do ato.

    Returns:
        `{rótulo: (quantidade, soma)}` do que passou — o histórico dos dois dias o repete.
    """
    from app.calendar.cancel_ops import _brl, filtro_devolucao
    from app.models import EventCancellation, SpecialExpense
    from app.utils import audit

    valores = {campo: getattr(antigo, campo) for campo in CAMPOS_DA_PASSAGEM}
    # O retrato dos dois dias (FR-059): o que passou e o que o novo tinha de próprio, para consulta.
    retrato_antigo = {c: _json_safe(v) for c, v in valores.items()}
    retrato_novo = {c: _json_safe(getattr(novo, c)) for c in CAMPOS_DA_PASSAGEM}
    for campo in CAMPOS_DA_PASSAGEM:
        setattr(antigo, campo, False if campo in _BOOLEANOS else None)
    db.session.flush()
    for campo, valor in valores.items():
        setattr(novo, campo, valor)
    if novo.client_id is None:
        novo.client_id = antigo.client_id

    # O filho muda de pai pela coluna: as coleções do antigo saem da sessão antes de mover.
    db.session.expire(antigo, list(_COLECOES_DA_PASSAGEM))
    passou: dict[str, tuple[int, Decimal]] = {}
    for modelo in TABELAS_DA_PASSAGEM:
        linhas = _mover(modelo, antigo, novo)
        if linhas:
            passou[_ROTULO_DA_PASSAGEM[modelo]] = (len(linhas), sum((_valor_da_linha(x) for x in linhas), Decimal("0")))
    devolucoes = (
        SpecialExpense.query.filter(filtro_devolucao(), SpecialExpense.event_id == antigo.id)
        .order_by(SpecialExpense.id).with_for_update().populate_existing().all()
    )  # fmt: skip
    for gasto in devolucoes:
        gasto.event_id = novo.id
        audit("edit", "gasto", gasto.id, novo.title,
              f"Passagem da venda: devolução do evento #{antigo.id} para o #{novo.id}")  # fmt: skip
    if devolucoes:
        passou["devoluções"] = (len(devolucoes), sum((Decimal(str(g.amount or 0)) for g in devolucoes), Decimal("0")))
    ja_no_novo = {c.client_id for c in EventClient.query.filter(EventClient.event_id == novo.id).all()}
    clientes = [c for c in EventClient.query.filter(EventClient.event_id == antigo.id).order_by(EventClient.id).all()
                if c.client_id not in ja_no_novo]  # fmt: skip
    for c in clientes:
        c.event_id = novo.id
    if clientes:
        passou["clientes"] = (len(clientes), Decimal("0"))

    for dia in CalendarEvent.query.filter(CalendarEvent.group_leader_id == antigo.id).all():
        dia.group_leader_id = None if dia.id == novo.id else novo.id
    novo.group_leader_id = None
    antigo.group_leader_id = novo.id
    for canc in EventCancellation.query.filter(
        db.or_(EventCancellation.group_leader_id == antigo.id, EventCancellation.event_id == antigo.id)
    ).all():
        canc.group_leader_id = novo.id
        if canc.event_id == antigo.id:
            canc.sale_handed_over = True
    db.session.flush()
    for ev in (antigo, novo):
        db.session.expire(ev, ["satellites", "group_leader", *_COLECOES_DA_PASSAGEM])

    resumo = "; ".join(
        f"{n} {rotulo}" + (f" ({_brl(soma)})" if soma else "") for rotulo, (n, soma) in passou.items()
    ) or "nenhuma linha"
    data_novo = novo.start_at.strftime("%d/%m") if novo.start_at else "?"
    # Sem `created_at`: o default UTC do modelo, como no resto do ato (FR-016).
    db.session.add(EventLog(
        event_id=antigo.id, actor_name=actor_name, actor_role=ACTOR_ROLE,
        message=(f'A venda passou para "{novo.title}" ({data_novo}): {resumo}. Campos que passaram: '
                 f"{json.dumps(retrato_antigo, ensure_ascii=False)}"),
    ))  # fmt: skip
    db.session.add(EventLog(
        event_id=novo.id, actor_name=actor_name, actor_role=ACTOR_ROLE,
        message=(f'Este dia passou a ser o principal da venda (veio de "{antigo.title}"): {resumo}. '
                 f"Valores próprios deste dia antes da passagem (para consulta, não restaurados): "
                 f"{json.dumps(retrato_novo, ensure_ascii=False)}"),
    ))  # fmt: skip
    return passou
