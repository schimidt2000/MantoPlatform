"""O pedido de cancelamento — "Solicitar cancelamento" do Comercial (feature 315, item 2a do backlog).

O Comercial pede pelo sistema, com o motivo, o alcance numa venda de vários dias e a devolução
combinada com a cliente; cada Superadmin é avisado no sino na mesma transação; só o Superadmin
fecha o pedido — recusando, cancelando (o cancelamento da 306 chama `fechar_no_cancelamento` em
cada dia que encerra) ou excluindo o evento vazio — e quem pediu recebe uma resposta por pedido.

O pedido mora no evento: as três colunas da 224 (`deletion_requested_at`, `_by_id`,
`deletion_request_reason`) e as duas da 315 (`deletion_request_scope`, `deletion_request_refund`).
**Só este módulo escreve as cinco**: pedir e recusar por `UPDATE` condicional (o claim), para dois
pedidos ou duas decisões ao mesmo tempo nunca se sobrescreverem nem avisarem em dobro; o fecho no
cancelamento, sobre o dia que o cancelamento já travou.

O código diz "solicitação" porque `cancel_ops.PedidoDeCancelamento` já é o corpo do POST de
cancelar; a tela e as rotas dizem "pedido de cancelamento".

Puro no sentido da constituição: sem `flask.request` nem `current_user` — quem chama passa o usuário.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, update

from app import db
from app.calendar.cancel_ops import (
    FRASE_CACHE_PAGO,
    CancelValidationError,
    _decimal,
    _dias_vivos_ordenados,
    _papeis_com_cache_pago,
    _quem_recebe_a_venda,
    _texto,
    elenco_dos_dias,
    exigir_evento_vivo,
    ids_do_grupo,
)
from app.constants import (
    ALCANCE_SO_ESTE_DIA,
    ALCANCE_TODOS,
    CODIGO_CACHE_PAGO,
    CODIGO_ENSAIO,
    CODIGO_EVENTO_CANCELADO,
    CODIGO_PEDIDO_PENDENTE,
    CODIGO_SEM_PEDIDO,
    EVENT_TYPE_VIRTUAL,
    MODO_NADA,
    MODO_PARTE,
    MODO_TUDO,
    now_sp,
)
from app.models import CalendarEvent, EventLog, User
from app.money import format_brl
from app.notificacoes import notificacoes_ops as nops

logger = logging.getLogger(__name__)

FRASE_ENSAIO = (
    "O ensaio segue o show: cancelar o show cancela o ensaio junto. Para desmarcar só o ensaio, fale "
    "com a equipe de Ensaio ou o Casting."
)
FRASE_JA_DECIDIDO = "Este pedido já foi decidido — recarregue o evento."
LIMITE_NOME = 200
LIMITE_PIX = 120
LIMITE_FAIXA = 100

#: As cinco colunas do pedido, zeradas juntas por toda saída que grava.
_SEM_PEDIDO = {
    "deletion_requested_at": None,
    "deletion_requested_by_id": None,
    "deletion_request_reason": None,
    "deletion_request_scope": None,
    "deletion_request_refund": None,
}


# ── o evento e a venda ─────────────────────────────────────────────────────────────────────────
def _nome(user_id: int | None) -> str | None:
    if user_id is None:
        return None
    u = db.session.get(User, user_id)
    return u.name if u else None


def _dd_mm(quando: datetime | None) -> str:
    return f"{quando:%d/%m}" if quando else "sem data"


def _dias_vivos_do_grupo(principal: CalendarEvent) -> list[CalendarEvent]:
    """O principal e os outros dias vivos da venda (por consulta, nunca pela coleção)."""
    ids = ids_do_grupo([principal.id]).get(principal.id, [principal.id])
    return (
        CalendarEvent.query.filter(CalendarEvent.id.in_(ids), CalendarEvent.cancelled_at.is_(None))
        .order_by(CalendarEvent.start_at, CalendarEvent.id)
        .all()
    )


def _principal_com_outro_dia_vivo(event: CalendarEvent) -> list[CalendarEvent] | None:
    """No principal com outro dia vivo, os dias vivos da venda; senão `None` (avulso ou satélite).

    Conta os dias vivos de verdade, como o cancelar da 306: `is_group_leader` segue verdadeiro com
    os outros dias já cancelados.
    """
    if event.group_leader_id is not None:
        return None
    dias = _dias_vivos_do_grupo(event)
    return dias if len(dias) > 1 else None


def _texto_do_alcance(event: CalendarEvent, alcance: str | None, dias: list[CalendarEvent] | None) -> str:
    """Como o aviso e o histórico dizem o alcance de um pedido."""
    if event.group_leader_id is not None:
        return "só este dia da venda"
    if not dias:
        return "o evento"
    if alcance == ALCANCE_SO_ESTE_DIA:
        return "só o 1º dia da venda"
    return f"todos os {len(dias)} dias da venda"


def bloqueio_do_proprio_dia(event: CalendarEvent) -> dict[str, str] | None:
    """Por que este dia não recebe pedido (ensaio; cachê pago ao elenco nele), ou `None`.

    É o que o menu mostra desabilitado com a frase. Cachê pago só noutro dia da venda não bloqueia
    o item: "só este dia" vale, e "todos os dias" leva o 409 com os dias na hora de pedir.
    """
    if event.event_type == "ENSAIO":
        return {"codigo": CODIGO_ENSAIO, "frase": FRASE_ENSAIO}
    if _papeis_com_cache_pago([event.id]):
        return {"codigo": CODIGO_CACHE_PAGO, "frase": FRASE_CACHE_PAGO}
    return None


def escolha_do_alcance(event: CalendarEvent) -> dict[str, Any] | None:
    """No principal com outro dia vivo: quantos dias a venda tem e qual dia receberia a venda se só o
    1º caísse — pelo critério da passagem da 306 (pula compromisso interno). A tela não calcula."""
    dias = _principal_com_outro_dia_vivo(event)
    if not dias:
        return None
    proximo = _quem_recebe_a_venda(_dias_vivos_ordenados(event, dias))
    return {
        "dias": len(dias),
        "proximo": (
            {"id": proximo.id, "start_at": proximo.start_at.isoformat() if proximo.start_at else None}
            if proximo
            else None
        ),
    }


# ── a devolução combinada ──────────────────────────────────────────────────────────────────────
def devolucao_gravada(event: CalendarEvent) -> dict[str, Any] | None:
    """A devolução combinada do pedido, lida de forma tolerante (JSON corrompido = sem devolução)."""
    bruto = event.deletion_request_refund
    if not bruto:
        return None
    try:
        dados = json.loads(bruto)
    except (TypeError, ValueError):
        logger.warning("315: devolução do pedido ilegível no evento %s", event.id)
        return None
    return dados if isinstance(dados, dict) else None


def _texto_da_devolucao(registro: dict[str, Any] | None) -> str | None:
    """Modo e valor da devolução combinada, para o histórico e a auditoria — nunca nome nem PIX."""
    if not registro:
        return None
    dev = registro.get("devolucao") or {}
    rotulo = {MODO_TUDO: "tudo", MODO_PARTE: "parte", MODO_NADA: "nada"}.get(dev.get("modo"), "—")
    valor = dev.get("valor")
    texto = f"{rotulo} {format_brl(Decimal(valor), prefix=True)}" if valor else rotulo
    if registro.get("venda_nova"):
        texto += f"; nova venda {format_brl(Decimal(registro['venda_nova']), prefix=True)}"
    return texto


# ── pedir ──────────────────────────────────────────────────────────────────────────────────────
def _ler_corpo(
    event: CalendarEvent, corpo: dict[str, Any] | None, dias: list[CalendarEvent] | None, *, caminho_velho: bool
) -> dict[str, Any]:
    """A forma do pedido (research R4), todos os erros de uma vez. Não confere dinheiro (máximo,
    mínimo, "nada pago"): isso é do cancelar, na hora de cancelar, com o pago daquele momento."""
    corpo = corpo if isinstance(corpo, dict) else {}
    erros: dict[str, str] = {}
    motivo = _texto(corpo.get("motivo"))
    if not motivo:
        erros["motivo"] = "Explique o motivo do pedido de cancelamento."

    satelite = event.group_leader_id is not None
    alcance_bruto = corpo.get("alcance")
    alcance: str | None
    if dias:
        if alcance_bruto is None and caminho_velho:
            alcance = None  # o corpo de antes do deploy: lido como "todos"
        elif alcance_bruto in (ALCANCE_TODOS, ALCANCE_SO_ESTE_DIA):
            alcance = alcance_bruto
        else:
            alcance = None
            erros["alcance"] = "Escolha se o pedido vale para todos os dias da venda ou só para este."
    else:
        alcance = ALCANCE_SO_ESTE_DIA if satelite else ALCANCE_TODOS
        if alcance_bruto is not None:
            erros["alcance"] = (
                "Num outro dia da venda o pedido vale só para ele."
                if satelite
                else "Este evento não faz parte de uma venda de vários dias."
            )
    um_dia_so = satelite or alcance == ALCANCE_SO_ESTE_DIA

    virtual = event.event_type == EVENT_TYPE_VIRTUAL
    devolucao_bruta = corpo.get("devolucao")
    sem_devolucao = virtual or (caminho_velho and devolucao_bruta is None)
    registro: dict[str, Any] | None = None
    if not sem_devolucao:
        dev = devolucao_bruta if isinstance(devolucao_bruta, dict) else {}
        modo = dev.get("modo") if isinstance(dev.get("modo"), str) else None
        valor, valor_invalido = _decimal(dev.get("valor"))
        nome, pix = _texto(dev.get("nome")), _texto(dev.get("pix"))
        if modo not in (MODO_TUDO, MODO_PARTE, MODO_NADA):
            erros["devolucao_modo"] = "Escolha se a cliente recebe tudo, parte ou nada de volta."
        elif modo == MODO_TUDO and um_dia_so:
            erros["devolucao_modo"] = (
                "Num dia só da venda, a devolução é parte ou nada — devolver tudo é cancelar a venda inteira."
            )
        if valor_invalido:
            erros["devolucao_valor"] = "O valor da devolução precisa ser um número."
        elif modo == MODO_PARTE and (valor is None or valor <= 0):
            erros["devolucao_valor"] = "Informe quanto a cliente recebe de volta."
        recebe = modo in (MODO_TUDO, MODO_PARTE)
        if recebe:
            if not nome:
                erros["devolucao_nome"] = "Informe quem recebe a devolução."
            elif len(nome) > LIMITE_NOME:
                erros["devolucao_nome"] = f"Quem recebe: até {LIMITE_NOME} caracteres."
            if not pix:
                erros["devolucao_pix"] = "Informe o PIX de quem recebe a devolução."
            elif len(pix) > LIMITE_PIX:
                erros["devolucao_pix"] = f"PIX: até {LIMITE_PIX} caracteres."
        devolucao: dict[str, Any] = {"modo": modo}
        if recebe:
            if valor is not None and valor > 0:
                devolucao["valor"] = f"{valor:.2f}"
            # Em Nada o registro não guarda nome nem PIX (data-model, "Leitura da devolução").
            devolucao["nome"], devolucao["pix"] = nome, pix
        registro = {"devolucao": devolucao}

    venda_nova, venda_nova_invalida = _decimal(corpo.get("venda_nova"))
    if corpo.get("venda_nova") is not None and not um_dia_so:
        erros["venda_nova"] = "O novo valor da venda só vale no pedido de um dia só."
    elif um_dia_so and not sem_devolucao:
        if venda_nova_invalida or venda_nova is None or venda_nova <= 0:
            erros["venda_nova"] = "Informe o novo valor da venda combinado com a cliente."
        elif registro is not None:
            registro["venda_nova"] = f"{venda_nova:.2f}"

    if erros:
        raise CancelValidationError("Confira os campos do pedido.", fields=erros)
    return {"motivo": motivo, "alcance": alcance, "registro": registro}


def _recusa_do_cache_pago(ids: list[int]) -> None:
    papeis = _papeis_com_cache_pago(ids)
    if papeis:
        dias = sorted({r.event_id for r in papeis})
        raise CancelValidationError(FRASE_CACHE_PAGO, status=409, codigo=CODIGO_CACHE_PAGO, dias=dias)


def solicitar(event: CalendarEvent, corpo: dict[str, Any] | None, actor: User, *, caminho_velho: bool) -> None:
    """Grava o pedido e avisa os Superadmins, na mesma transação. Commita.

    Ordem (a da 306: estado antes da forma): cancelado (409) → ensaio (409) → cachê pago do próprio
    dia (409) → campos (400) → cachê pago dos outros dias que "todos" alcança (409) → claim (409
    `pedido_pendente`). Nenhuma recusa grava coluna, histórico ou aviso.

    Raises:
        CancelValidationError: as recusas acima, com `codigo` e `fields`.
    """
    from app.calendar.routes import _log_sync
    from app.calendar.sumico_ops import preso_ao_evento  # tardio: sumico_ops importa cancel_ops

    exigir_evento_vivo(event)
    bloqueio = bloqueio_do_proprio_dia(event)
    if bloqueio:
        raise CancelValidationError(bloqueio["frase"], status=409, codigo=bloqueio["codigo"])
    dias = _principal_com_outro_dia_vivo(event)
    lido = _ler_corpo(event, corpo, dias, caminho_velho=caminho_velho)
    alcance = lido["alcance"]
    alcancados = [d.id for d in dias] if dias and alcance != ALCANCE_SO_ESTE_DIA else [event.id]
    _recusa_do_cache_pago(alcancados)

    carimbo = now_sp()
    registro = json.dumps(lido["registro"], ensure_ascii=False) if lido["registro"] else None
    linhas = db.session.execute(
        update(CalendarEvent)
        .where(
            CalendarEvent.id == event.id,
            CalendarEvent.deletion_requested_at.is_(None),
            CalendarEvent.cancelled_at.is_(None),
        )
        .values(
            deletion_requested_at=carimbo,
            deletion_requested_by_id=actor.id,
            deletion_request_reason=lido["motivo"],
            deletion_request_scope=alcance,
            deletion_request_refund=registro,
        )
        .execution_options(synchronize_session=False)
    ).rowcount
    # A view carregou o evento antes do UPDATE: sem o refresh, o identity map guardaria o valor
    # velho — no ramo que ganhou (o detalhe da resposta) e no que perdeu (o nome de quem pediu).
    db.session.refresh(event)
    if not linhas:
        db.session.rollback()
        db.session.refresh(event)
        if event.is_cancelled:
            raise CancelValidationError(
                "Este evento foi cancelado — a tela fica só para consulta.",
                status=409,
                codigo=CODIGO_EVENTO_CANCELADO,
            )
        quem = _nome(event.deletion_requested_by_id) or "outra pessoa"
        raise CancelValidationError(
            f"Já existe um pedido de {quem} aguardando o Superadmin.", status=409, codigo=CODIGO_PEDIDO_PENDENTE
        )

    texto_alcance = _texto_do_alcance(event, alcance, dias)
    detalhe = f"Pediu o cancelamento ({texto_alcance}): {lido['motivo']}"
    combinado = _texto_da_devolucao(lido["registro"])
    if combinado:
        detalhe += f" — devolução combinada: {combinado}"
    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    # Sem `created_at`: vale o default UTC do modelo, que o histórico da tela converte (quita a parte
    # da 224 da dívida 76, que gravava em horário de São Paulo).
    db.session.add(EventLog(event_id=event.id, actor_name=actor.name, actor_role=papel, message=detalhe))
    _log_sync("cancel_requested", event, details=detalhe, actor=actor.name, actor_role=papel)
    nops.notificar_pedido_cancelamento(
        event,
        carimbo=carimbo,
        preso=preso_ao_evento(event),
        n_escalados=len(elenco_dos_dias(alcancados)),
        alcance=texto_alcance,
        autor=actor.name,
        motivo=lido["motivo"],
    )
    db.session.commit()


# ── decidir ────────────────────────────────────────────────────────────────────────────────────
def _responder(autor_id: int | None, *, quem_decidiu_id: int | None, decisao: str, carimbo: datetime,
               event_id: int, title: str, body: str | None = None, com_link: bool = True) -> int:
    autor = db.session.get(User, autor_id) if autor_id else None
    return nops.notificar_pedido_decidido(
        autor,
        quem_decidiu_id=quem_decidiu_id,
        decisao=decisao,
        carimbo=carimbo,
        event_id=event_id,
        title=title,
        body=body,
        com_link=com_link,
    )


def recusar(event: CalendarEvent, *, actor: User, motivo: str = "") -> None:
    """O Superadmin recusa o pedido: as cinco colunas voltam a nulo e quem pediu é respondido. Commita.

    O claim é pelo carimbo lido: se outra decisão (recusa, cancelamento) fechou o pedido primeiro, o
    `UPDATE` não acha a linha e a resposta é 409 `sem_pedido` — uma decisão, uma resposta.
    """
    from app.calendar.routes import _log_sync

    carimbo = event.deletion_requested_at
    autor_id = event.deletion_requested_by_id
    linhas = 0
    if carimbo is not None and not event.is_cancelled:
        linhas = db.session.execute(
            update(CalendarEvent)
            .where(CalendarEvent.id == event.id, CalendarEvent.deletion_requested_at == carimbo)
            .values(**_SEM_PEDIDO)
            .execution_options(synchronize_session=False)
        ).rowcount
    db.session.refresh(event)
    if not linhas:
        db.session.rollback()
        raise CancelValidationError(FRASE_JA_DECIDIDO, status=409, codigo=CODIGO_SEM_PEDIDO)

    motivo = _texto(motivo)
    detalhe = f"Recusou o pedido de cancelamento: {motivo}" if motivo else "Recusou o pedido de cancelamento."
    papel = ", ".join(r.name for r in actor.roles)[:60] or None
    db.session.add(EventLog(event_id=event.id, actor_name=actor.name, actor_role=papel, message=detalhe))
    _log_sync("cancel_request_refused", event, details=detalhe, actor=actor.name, actor_role=papel)
    # Sempre com o kind: sem ele, a resposta de uma decisão anterior também ficaria lida.
    nops.marcar_lidas_por_entidade("calendar_event", event.id, nops.KIND_EVENTO_PEDIDO_CANCELAMENTO)
    titulo = f"Pedido recusado — {event.title}"
    _responder(
        autor_id,
        quem_decidiu_id=actor.id,
        decisao="recusado",
        carimbo=carimbo,
        event_id=event.id,
        title=f"{titulo}: {motivo}" if motivo else titulo,
        body=motivo or None,
    )
    db.session.commit()


def fechar_no_cancelamento(dia: CalendarEvent, *, alcance: str, novo_principal: CalendarEvent | None) -> None:
    """O cancelamento da 306 encerrou este dia: o pedido dele, se havia, fecha e quem pediu é respondido.

    Chamado por `cancel_ops.ao_cancelar` em cada dia que o ato encerra, na transação do ato (sem
    commit), com o dia já travado por ela — não precisa de claim: a recusa que chegar depois não acha
    mais o carimbo. Quem cancelou é `dia.cancelled_by_id`, que o ato grava antes.
    """
    carimbo = dia.deletion_requested_at
    if carimbo is None:
        return
    autor_id = dia.deletion_requested_by_id
    for coluna, valor in _SEM_PEDIDO.items():
        setattr(dia, coluna, valor)
    nops.marcar_lidas_por_entidade("calendar_event", dia.id, nops.KIND_EVENTO_PEDIDO_CANCELAMENTO)
    data = _dd_mm(dia.start_at)
    if alcance == ALCANCE_TODOS:
        titulo = f"Evento cancelado — {dia.title} ({data})"
    elif novo_principal is not None:
        titulo = (
            f"Dia {data} cancelado — {dia.title}: a venda passou para o dia "
            f"{_dd_mm(novo_principal.start_at)}; os outros dias seguem"
        )
    else:
        titulo = f"Dia {data} cancelado — {dia.title}: a venda segue nos outros dias"
    _responder(
        autor_id,
        quem_decidiu_id=dia.cancelled_by_id,
        decisao="cancelado",
        carimbo=carimbo,
        event_id=dia.id,
        title=titulo,
    )


def pedido_antes_da_exclusao(event: CalendarEvent) -> dict[str, Any] | None:
    """O que a resposta da exclusão precisa, lido antes: o objeto morre no commit da exclusão."""
    if event.deletion_requested_at is None:
        return None
    return {
        "event_id": event.id,
        "autor_id": event.deletion_requested_by_id,
        "titulo": event.title,
        "carimbo": event.deletion_requested_at,
    }


def responder_na_exclusao(pedido: dict[str, Any] | None, *, quem_excluiu_id: int | None) -> None:
    """Depois que a exclusão commitou: "Evento excluído — <título>" a quem pediu, sem entidade nem
    link (o evento não existe mais). Regime B: transação própria; a falha do aviso não desfaz a
    exclusão. Os avisos do pedido aos Superadmins a exclusão já apagou (`apagar_por_entidade`)."""
    if not pedido:
        return
    try:
        _responder(
            pedido["autor_id"],
            quem_decidiu_id=quem_excluiu_id,
            decisao="excluido",
            carimbo=pedido["carimbo"],
            event_id=pedido["event_id"],
            title=f"Evento excluído — {pedido['titulo']}",
            com_link=False,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("315: a resposta da exclusão do evento %s não saiu", pedido["event_id"])


# ── ler ────────────────────────────────────────────────────────────────────────────────────────
def serializar_para(
    event: CalendarEvent, *, flags: dict[str, Any] | None, usuario: Any, impersonando: bool = False
) -> dict[str, Any] | None:
    """O bloco do pedido com o corte por papel (data-model, "Leitura da devolução"), ou `None`.

    Todos veem que há pedido (data e alcance). Motivo, autor, modo e valor da devolução: `show_comercial`.
    Nome e PIX de quem recebe: `show_comercial` e (`show_financeiro` ou o próprio autor sem "Ver
    como"). Pelo papel em uso — o "Ver como" vale. `flags is None` é chamador interno: libera tudo.
    """
    if not event.has_pending_deletion_request:
        return None
    bloco: dict[str, Any] = {
        "requested_at": event.deletion_requested_at.isoformat(),
        "alcance": event.deletion_request_scope,
    }
    if flags is None:
        ver_motivo = ver_quem_recebe = True
    else:
        ver_motivo = bool(flags.get("show_comercial"))
        autor = (
            not impersonando
            and usuario is not None
            and getattr(usuario, "id", None) == event.deletion_requested_by_id
        )
        ver_quem_recebe = ver_motivo and (bool(flags.get("show_financeiro")) or autor)
    if not ver_motivo:
        return bloco
    bloco["requested_by"] = _nome(event.deletion_requested_by_id)
    bloco["requested_by_id"] = event.deletion_requested_by_id
    bloco["reason"] = event.deletion_request_reason or None
    registro = devolucao_gravada(event)
    if registro:
        dev = dict(registro.get("devolucao") or {})
        if not ver_quem_recebe:
            dev.pop("nome", None)
            dev.pop("pix", None)
        bloco["devolucao"] = dev or None
        bloco["venda_nova"] = registro.get("venda_nova")
    return bloco


def _filtro_pedido_de_todos():
    return (
        CalendarEvent.deletion_requested_at.isnot(None),
        CalendarEvent.cancelled_at.is_(None),
        or_(CalendarEvent.deletion_request_scope.is_(None), CalendarEvent.deletion_request_scope == ALCANCE_TODOS),
    )


def solicitacoes_da_venda(eventos: list[CalendarEvent]) -> dict[int, datetime]:
    """Dia da venda → carimbo do pedido de "todos os dias" feito no principal (research R6).

    Uma consulta pelos principais distintos da lista. Só o dia sem situação própria herda (a
    precedência do modelo: cancelado > sumiu > o próprio pedido > o pedido da venda).
    """
    lideres = {e.group_leader_id for e in eventos if e.group_leader_id is not None and e.situacao is None}
    if not lideres:
        return {}
    carimbos = dict(
        db.session.query(CalendarEvent.id, CalendarEvent.deletion_requested_at)
        .filter(CalendarEvent.id.in_(lideres), *_filtro_pedido_de_todos())
        .all()
    )
    return {
        e.id: carimbos[e.group_leader_id]
        for e in eventos
        if e.group_leader_id in carimbos and e.situacao is None
    }


def pedido_da_venda(event: CalendarEvent) -> dict[str, Any] | None:
    """No detalhe do dia que herda: `{requested_at, principal_id}` (só leitura; o pedido é do principal)."""
    carimbo = solicitacoes_da_venda([event]).get(event.id)
    if carimbo is None:
        return None
    return {"requested_at": carimbo.isoformat(), "principal_id": event.group_leader_id}


def faixa_das_solicitacoes(limite: int = LIMITE_FAIXA) -> dict[str, Any]:
    """Os pedidos pendentes, para a faixa do topo: contagem exata e a lista por urgência (a ordem da
    faixa do sumiço: futuros por data, depois os passados do mais recente, sem data por último).
    Sem dinheiro, motivo nem autor: a faixa vai a todo Comercial."""
    linhas = (
        db.session.query(CalendarEvent.id, CalendarEvent.title, CalendarEvent.start_at, CalendarEvent.end_at)
        .filter(CalendarEvent.deletion_requested_at.isnot(None), CalendarEvent.cancelled_at.is_(None))
        .all()
    )
    agora = now_sp()
    com_data = [x for x in linhas if x.start_at is not None]
    futuros = sorted((x for x in com_data if (x.end_at or x.start_at) >= agora), key=lambda x: (x.start_at, x.id))
    passados = sorted(
        (x for x in com_data if (x.end_at or x.start_at) < agora), key=lambda x: (x.start_at, x.id), reverse=True
    )
    sem_data = sorted((x for x in linhas if x.start_at is None), key=lambda x: x.id)
    return {
        "total": len(linhas),
        "items": [
            {"id": x.id, "title": x.title, "start_at": x.start_at.isoformat() if x.start_at else None}
            for x in (futuros + passados + sem_data)[:limite]
        ],
    }
