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
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app import db
from app.models import CalendarEvent, EventLog

# Campos que deixam de ser do satélite ao entrar num grupo. `with_invoice` e
# `is_cortesia_permuta` são booleanos e voltam a False; o resto vira NULL.
SATELLITE_FIELDS_CLEARED = (
    "sale_value", "sale_value_gross", "sale_date", "with_invoice",
    "is_cortesia_permuta", "seller_id", "commission_rate",
    "payment_method", "payment_installments", "payment_due_date",
    "transport_value", "acrescimo_value", "invoice_file", "orcamento_history_id",
)

_BOOLEANOS = ("with_invoice", "is_cortesia_permuta")

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
    """
    if leader.is_satellite:
        return f'"{leader.title}" já é satélite de outro grupo e não pode ser principal.'
    # Um principal que já lidera um grupo PODE receber novos satélites (mesma regra da 053).
    if leader.event_type == "ENSAIO":  # FR-003
        return "Eventos do tipo ENSAIO não podem ser agrupados por este mecanismo."
    for sat in satellites:
        if sat.id == leader.id:  # FR-004
            return "Não é possível agrupar um evento a ele mesmo."
        if sat.event_type == "ENSAIO":  # FR-003
            return "Eventos do tipo ENSAIO não podem ser agrupados por este mecanismo."
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


def desagrupar(satelite: CalendarEvent, actor_name: str, agora: datetime) -> dict[str, Any]:
    """Solta um satélite do grupo. Commita, e NÃO restaura os campos comerciais.

    Returns:
        ``{"event_id": int, "leader_id": int | None}`` — o `leader_id` do ex-principal, para a
        tela invalidar o cache dele também: o KPI do grupo muda no mesmo instante.
    """
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
