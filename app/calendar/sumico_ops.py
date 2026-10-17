"""Evento que some do Google Agenda: conferir, apagar o vazio, manter e marcar o que tem dinheiro
(feature 303).

Existe porque a limpeza do sync apagava do banco todo evento do mês que não vinha na lista do
Google — com venda, comprovantes, contrato e escala junto. Foi assim que o `(R&I) GABBY + PANDY +
GATUNO` (evento 1244) perdeu a venda em 17/09/2026, e o `(SHOW) PETER PAN...` antes dele (224):
alguém apagou a linha no calendário, e o sistema apagou a prova de que o dinheiro entrou. E nem
precisava apagar: o 1275, só MOVIDO de setembro para outubro no Google, foi apagado pela limpeza
de setembro e reimportado como o 1287, sem venda.

A regra daqui em diante, por evento que falta na lista do mês:

- a falta na lista não basta: o evento é **conferido no próprio Google** (`gcal.consultar_evento`).
  Só a ausência confirmada (404, 410 ou `status: cancelled`) tem efeito; na dúvida, ele fica;
- **vazio** (sem venda, comprovante, contrato, escala nem grupo) é apagado, como sempre foi;
- **com dinheiro** fica e ganha a marca `google_missing_since`, com aviso no sino e histórico.

Puro no sentido da constituição: sem `flask.request` nem `current_user`. O Google é chamado sempre
por atributo do módulo (`gcal.consultar_evento`), para o dublê do verify e o espião do verify_205
interceptarem. Os helpers de `routes.py` entram por import tardio (o `routes` importa este módulo
dentro das funções).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, NoReturn

from flask import current_app
from sqlalchemy import ColumnElement, and_, update

from app import db
from app.calendar import service as gcal
from app.calendar.cancel_ops import total_recebido
from app.constants import EVENT_TYPE_SHOW, now_sp
from app.models import AuditLog, CalendarEvent, EventContract, EventLog, EventPayment, EventRole
from app.money import format_brl
from app.notificacoes import notificacoes_ops

if TYPE_CHECKING:
    from app.models import User

logger = logging.getLogger(__name__)

#: Quantos eventos a faixa lista; `total` é sempre a contagem exata.
FAIXA_LIMITE = 100

GRUPO_PRINCIPAL = "principal"
GRUPO_SATELITE = "satelite"
_GRUPO_TEXTO = {
    GRUPO_PRINCIPAL: "principal de grupo comercial",
    GRUPO_SATELITE: "satélite de grupo comercial",
}

# Por que a marca saiu — fechado. Só o reaparecimento grava rastro próprio em `desmarcar`; na
# devolução, o rastro é o que a própria devolução grava antes de chamar o Google.
MOTIVO_REAPARECEU = "reapareceu"
MOTIVO_DEVOLVIDO = "devolvido"
_MOTIVOS_DE_DESMARCAR = frozenset({MOTIVO_REAPARECEU, MOTIVO_DEVOLVIDO})

# O que `_decidir_candidato` fez com um evento — só para `limpar_mes` registrar depois do commit.
_VIRTUAL = "virtual"
_JA_MARCADO = "ja_marcado"
_INCONCLUSIVO = "inconclusivo"
_PRESENTE = "presente"
_MOVIDO = "movido"
_REMOVIDO = "removido"
_MARCADO = "marcado"
_OUTRO_MARCOU = "outro_marcou"

# Inconclusivo sem consulta: o disjuntor da rodada já tinha aberto.
_MOTIVO_DISJUNTOR = "disjuntor"


@dataclass(frozen=True)
class PresoAoEvento:
    """O que prende um evento ao sistema — decide se ele pode ser apagado, escreve o histórico e
    alimenta o aviso. Uma fonte só: os três não podem divergir sobre o mesmo evento.

    Comissão já paga não entra (decisão do dono, 30/09): o evento sem mais nada é apagado e o
    estorno sai contra o vendedor, como hoje (`cancel_ops.aplicar_estorno_comissao`).
    """

    venda: Decimal
    recebido: Decimal
    n_comprovantes: int
    tem_contrato: bool
    n_escalados: int  # sem a vaga automática do técnico de som em SHOW
    grupo: str | None  # GRUPO_PRINCIPAL, GRUPO_SATELITE ou None
    tecnico_automatico: bool  # SHOW com a vaga automática ocupada pelo técnico padrão

    @property
    def vazio(self) -> bool:
        """True se apagar o evento não perde nada que importe."""
        return (
            self.venda <= 0
            and self.n_comprovantes == 0
            and not self.tem_contrato
            and self.n_escalados == 0
            and self.grupo is None
        )

    def descricao(self) -> str:
        """O retrato em uma linha: "venda R$ 0,00 · 0 comprovantes · sem contrato · 0 escalados ·
        sem grupo". Vai no histórico do evento marcado e na auditoria do evento apagado — é o que
        torna conferível, depois, que o apagado estava mesmo vazio."""
        return " · ".join(
            (
                f"venda {format_brl(self.venda, prefix=True)}",
                self._comprovantes(),
                "com contrato" if self.tem_contrato else "sem contrato",
                self._escalados(),
                _GRUPO_TEXTO.get(self.grupo or "", "sem grupo"),
            )
        )

    def _comprovantes(self) -> str:
        if self.n_comprovantes == 0:
            return "0 comprovantes"
        rotulo = "comprovante" if self.n_comprovantes == 1 else "comprovantes"
        recebido = format_brl(self.recebido, prefix=True)
        return f"{self.n_comprovantes} {rotulo} (recebido {recebido})"

    def _escalados(self) -> str:
        base = "1 escalado" if self.n_escalados == 1 else f"{self.n_escalados} escalados"
        if not self.tecnico_automatico:
            return base
        if self.n_escalados == 0:
            return f"{base} (só o técnico de som automático)"
        return f"{base} (fora o técnico de som automático)"


@dataclass
class ResultadoLimpeza:
    """O que a limpeza de um mês fez — os dois chamadores (ciclo e "Limpar eventos fantasma")
    somam e mostram os números."""

    removidos: list[str] = field(default_factory=list)  # títulos
    marcados: list[int] = field(default_factory=list)
    movidos: list[int] = field(default_factory=list)
    desmarcados: list[int] = field(default_factory=list)
    presentes_fora_da_lista: list[int] = field(default_factory=list)
    inconclusivos: list[int] = field(default_factory=list)
    falhas: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class _Decisao:
    acao: str
    motivo: str = ""
    titulo: str = ""


def filtro_marcados() -> ColumnElement[bool]:
    """Predicado SQL de "marcado": marca preenchida E não cancelado (fonte única da consulta;
    `CalendarEvent.is_google_missing` é o mesmo teste para objeto já carregado)."""
    return and_(
        CalendarEvent.google_missing_since.isnot(None),
        CalendarEvent.cancelled_at.is_(None),
    )


def _grupo_do_evento(event: CalendarEvent) -> str | None:
    if event.group_leader_id is not None:
        return GRUPO_SATELITE
    tem_satelite = (
        db.session.query(CalendarEvent.id).filter(CalendarEvent.group_leader_id == event.id).first()
    )
    return GRUPO_PRINCIPAL if tem_satelite else None


def preso_ao_evento(event: CalendarEvent) -> PresoAoEvento:
    """Retrato do que prende o evento ao sistema (R2 da 303).

    Não usa `cancel_ops.pode_excluir`: aquela conta qualquer vaga com talento e daria "não vazio"
    para todo SHOW, por causa da vaga do técnico de som que o sistema cria sozinho. O comprovante
    conta por existência, mesmo sem valor — a exclusão apagaria a linha do mesmo jeito.
    """
    from app.calendar.routes import SOUND_TECH_CHARACTER, SOUND_TECH_TALENT_ID

    escalados = EventRole.query.filter(
        EventRole.event_id == event.id, EventRole.talent_id.isnot(None)
    )
    n_tecnico = 0
    if event.event_type == EVENT_TYPE_SHOW:
        # Só em SHOW: o orçamento cria a mesma vaga em evento de outro tipo, e ali o técnico 42 é
        # escalação feita pela equipe. Com ou sem cachê — "se foi pago é porque foi realizado".
        n_tecnico = escalados.filter(
            EventRole.role_type == "extra",
            EventRole.character_name == SOUND_TECH_CHARACTER,
            EventRole.talent_id == SOUND_TECH_TALENT_ID,
        ).count()
    return PresoAoEvento(
        venda=Decimal(str(event.sale_value or 0)),
        recebido=total_recebido(event),
        n_comprovantes=EventPayment.query.filter_by(event_id=event.id).count(),
        tem_contrato=EventContract.query.filter_by(event_id=event.id).first() is not None,
        n_escalados=escalados.count() - n_tecnico,
        grupo=_grupo_do_evento(event),
        tecnico_automatico=n_tecnico > 0,
    )


def marcar(event: CalendarEvent, preso: PresoAoEvento, *, contexto: str) -> datetime | None:
    """Marca o evento "Sumiu do Google Agenda" e avisa, na transação de quem chama (NÃO comita).

    O `UPDATE` é condicional: o ciclo automático e o "Limpar eventos fantasma" não passam pelo
    mesmo claim, e a transição sem marca → marcado não pode render dois avisos nem dois históricos.
    Quem não pega a linha devolve `None` e não escreve nada.

    Args:
        contexto: o mês limpo, `AAAA-MM`, gravado na auditoria.

    Returns:
        O carimbo gravado, ou `None` quando outro processo marcou primeiro.
    """
    from app.calendar.routes import _log_sync

    carimbo = now_sp()
    linhas = db.session.execute(
        update(CalendarEvent)
        .where(
            CalendarEvent.id == event.id,
            CalendarEvent.google_missing_since.is_(None),
            CalendarEvent.cancelled_at.is_(None),
        )
        .values(google_missing_since=carimbo)
        .execution_options(synchronize_session=False)
    ).rowcount
    if not linhas:
        return None
    db.session.refresh(event)
    # O aviso sai antes do histórico porque o texto do histórico diz quantas pessoas foram
    # avisadas; e recebe o carimbo do próprio UPDATE, que é a identidade do aviso (um por sumiço).
    n = notificacoes_ops.notificar_evento_sumiu_google(event, marcado_em=carimbo, preso=preso)
    # Sem `created_at`: vale o default UTC do modelo, que o histórico da tela converte.
    db.session.add(
        EventLog(
            event_id=event.id,
            actor_name="Sistema",
            actor_role="Sistema",
            message=(
                "Sumiu do Google Agenda — mantido no sistema. "
                f"Preso: {preso.descricao()}. Aviso enviado a {n} pessoa(s)."
            ),
        )
    )
    _log_sync(
        "sumiu_do_google",
        event,
        details=(
            f"Sumiu do Google Agenda ({contexto}) — mantido no sistema. "
            f"Preso: {preso.descricao()}. Aviso a {n} pessoa(s)."
        ),
    )
    return carimbo


def desmarcar(
    event: CalendarEvent,
    *,
    motivo: str,
    actor_name: str = "Sistema",
    actor_role: str = "Sistema",
) -> bool:
    """Retira a marca — a única função que faz isso. NÃO comita.

    Zera a coluna e dá como lido o aviso do sino (para todos: o fato deixou de valer). No
    reaparecimento grava também o rastro — histórico com o ator recebido (quem clicou em
    "Sincronizar", ou Sistema) e auditoria `google_reapareceu`; na devolução, o rastro é o que a
    própria devolução já gravou.

    Returns:
        `False`, sem escrever nada, quando o evento não está marcado.
    """
    if motivo not in _MOTIVOS_DE_DESMARCAR:
        raise ValueError(f"motivo de desmarcar fora da lista: {motivo!r}")
    if not event.is_google_missing:
        return False
    desde = event.google_missing_since
    event.google_missing_since = None
    notificacoes_ops.marcar_lidas_por_entidade(
        "calendar_event", event.id, notificacoes_ops.KIND_EVENTO_SUMIU_GOOGLE
    )
    if motivo == MOTIVO_REAPARECEU:
        _rastro_do_reaparecimento(event, desde, actor_name, actor_role)
    return True


def _rastro_do_reaparecimento(
    event: CalendarEvent, desde: datetime, actor_name: str, actor_role: str
) -> None:
    from app.calendar.routes import _log_sync

    # `actor_role` é String(60) nas duas tabelas: o par de papéis juntado por vírgula de quem tem
    # vários passa disso, e o Postgres recusaria o histórico inteiro.
    papel = (actor_role or "")[:60] or None
    texto = (
        f'Reapareceu no Google Agenda — a marca "Sumiu do Google Agenda" de {desde:%d/%m/%Y} '
        "foi retirada."
    )
    # Sem `created_at`: vale o default UTC do modelo, que o histórico da tela converte.
    db.session.add(
        EventLog(event_id=event.id, actor_name=actor_name[:120], actor_role=papel, message=texto)
    )
    _log_sync("google_reapareceu", event, details=texto, actor=actor_name[:120], actor_role=papel)


def _texto(valor: str | None) -> str:
    return (valor or "").strip()


def mesmos_dados(event: CalendarEvent, item: dict) -> bool:
    """O item do Google traz os mesmos título, datas, local e descrição que o banco?

    Compara pelos valores que `sync_events` GRAVARIA, não pelo item cru: o título sem os
    segmentos de equipe ("+ Coordenador"), as datas por `parse_event_datetime` (São Paulo sem
    fuso; dia inteiro à meia-noite, com o fim exclusivo do Google), local e descrição com nulo
    igual a vazio e sem espaços nas pontas.

    Invariante: logo depois de `sync_events([item])`, `mesmos_dados(event, item)` é `True`. Sem
    isso, um evento que nunca vem na lista (série recorrente-mãe, página cortada) seria
    ressincronizado — com `UPDATE` e aviso ao elenco — a cada 10 minutos.
    """
    from app.calendar.routes import _strip_reserved_title_segments

    titulo = _strip_reserved_title_segments(item.get("summary") or "Sem título")
    inicio, fim = gcal.parse_event_datetime(item)
    return (
        _texto(titulo) == _texto(event.title)
        and inicio == event.start_at
        and fim == event.end_at
        and _texto(item.get("location")) == _texto(event.location)
        and _texto(item.get("description")) == _texto(event.description)
    )


def _apagar_vazio(event: CalendarEvent, preso: PresoAoEvento, motivo: str, ym: str) -> _Decisao:
    from app.calendar.routes import _delete_event, _log_sync

    # Feature 306 (FR-036): trava o evento e relê antes de apagar (o molde de `_delete_event_flow`).
    db.session.flush()
    db.session.refresh(event, with_for_update=True)
    titulo = event.title
    _log_sync(
        "auto_deleted",
        event,
        details=(
            # "Não está mais", nunca "foi apagado": 404/410 também é evento movido para outro
            # calendário — o motivo cru do Google vai junto.
            f"Não está mais no Google Agenda ({ym}; o Google respondeu {motivo}) — removido do "
            f"sistema porque estava vazio: {preso.descricao()}"
        ),
    )
    _delete_event(event)
    return _Decisao(_REMOVIDO, motivo, titulo)


def _registrado_hoje(event_id: int, acao: str) -> bool:
    """Já existe auditoria desta ação para o evento hoje? O dia é o da coluna, que é UTC."""
    hoje = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.session.query(AuditLog.id)
        .filter(
            AuditLog.entity_type == "agenda",
            AuditLog.entity_id == event_id,
            AuditLog.action == acao,
            AuditLog.created_at >= hoje,
        )
        .first()
        is not None
    )


def _aplicar_presente(event: CalendarEvent, consulta: gcal.ConsultaEvento) -> _Decisao:
    """O evento está no Google, só não veio na lista do mês: não é sumiço.

    Mudou (de data, quase sempre) → `sync_events` com o item — a mesma função do ciclo, que acha
    pelo id, grava a data nova e avisa o elenco aceito; ela comita sozinha e expira o objeto.
    Não mudou → nada é regravado, e a auditoria registra uma vez por dia.
    """
    from app.calendar.routes import _log_sync, sync_events

    if not mesmos_dados(event, consulta.item):
        sync_events([consulta.item])
        return _Decisao(_MOVIDO, consulta.motivo)
    if not _registrado_hoje(event.id, "presente_fora_da_lista"):
        recorrente = consulta.motivo == gcal.MOTIVO_SERIE_RECORRENTE
        _log_sync(
            "presente_fora_da_lista",
            event,
            details="Está no Google Agenda, mas não veio na lista do mês"
            + (" (série recorrente)" if recorrente else "")
            + " — nada alterado.",
        )
    return _Decisao(_PRESENTE, consulta.motivo)


def _decidir_candidato(event: CalendarEvent, ym: str, *, disjuntor_aberto: bool) -> _Decisao:
    """Decide UM evento que faltou na lista do mês. Não comita — `limpar_mes` comita por evento.

    Ordem: venda virtual (nunca consulta) → já marcado (pula) → disjuntor aberto (inconclusivo sem
    consultar) → consulta ao Google. Só a ausência confirmada apaga (vazio) ou marca (com dinheiro).
    """
    from app.calendar.routes import CALENDAR_ID, _is_virtual_event, _log_sync

    if _is_virtual_event(event):
        # Venda virtual nunca é apagada por sumiço no Google (FR-029b da 205): a venda é a fonte
        # de verdade dela. A equipe é sinalizada e decide.
        _log_sync(
            "virtual_divergente",
            event,
            details=f"Evento de venda virtual sumiu do Google Calendar "
            f"({ym}) — NÃO removido do sistema, pedido segue válido.",
        )
        return _Decisao(_VIRTUAL)
    if event.is_google_missing:
        return _Decisao(_JA_MARCADO)
    if disjuntor_aberto:
        return _Decisao(_INCONCLUSIVO, _MOTIVO_DISJUNTOR)
    consulta = gcal.consultar_evento(CALENDAR_ID, event.google_event_id)
    if consulta.desfecho == gcal.DESFECHO_INCONCLUSIVO:
        return _Decisao(_INCONCLUSIVO, consulta.motivo)
    if consulta.desfecho == gcal.DESFECHO_PRESENTE:
        return _aplicar_presente(event, consulta)
    preso = preso_ao_evento(event)
    if preso.vazio:
        return _apagar_vazio(event, preso, consulta.motivo, ym)
    if marcar(event, preso, contexto=ym) is None:
        return _Decisao(_OUTRO_MARCOU)
    return _Decisao(_MARCADO, consulta.motivo)


def _candidatos(vivos: set[str], year: int, month: int) -> list[int]:
    """Ids dos eventos do mês (com id do Google, não cancelados) que não vieram na lista.

    Ids, não objetos: a unidade de trabalho é o evento e cada commit expira o que foi carregado; o
    ensaio-filho apagado junto com o pai vazio chegaria à sua vez fora da sessão.
    """
    inicio = datetime(year, month, 1)
    fim = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    linhas = (
        db.session.query(CalendarEvent.id, CalendarEvent.google_event_id)
        .filter(
            CalendarEvent.google_event_id.isnot(None),
            # Cancelado JÁ foi tirado do Google de propósito (224): faltar é o esperado.
            CalendarEvent.cancelled_at.is_(None),
            CalendarEvent.start_at >= inicio,
            CalendarEvent.start_at < fim,
        )
        .order_by(CalendarEvent.start_at, CalendarEvent.id)
        .all()
    )
    return [event_id for event_id, gid in linhas if gid not in vivos]


def _registrar(resultado: ResultadoLimpeza, event_id: int, decisao: _Decisao) -> None:
    if decisao.acao == _REMOVIDO:
        resultado.removidos.append(decisao.titulo)
    elif decisao.acao == _MARCADO:
        resultado.marcados.append(event_id)
    elif decisao.acao == _MOVIDO:
        resultado.movidos.append(event_id)
    elif decisao.acao == _PRESENTE:
        resultado.presentes_fora_da_lista.append(event_id)
    elif decisao.acao == _INCONCLUSIVO:
        resultado.inconclusivos.append(event_id)


def _desmarcar_os_que_voltaram(vivos: set[str], ym: str, resultado: ResultadoLimpeza) -> None:
    """O marcado cujo id voltou à lista do mês perde a marca — vale o Google.

    Pelo id, sem faixa de mês: o evento que atravessa a virada vem na lista de um mês com início
    no outro. Sem consulta nem `sync_events`: a lista (`showDeleted=False`) já prova a presença, e
    os três chamadores rodam `sync_events(items)` antes da limpeza — os dados já estão gravados.
    """
    if not vivos:
        return
    ids = [
        event_id
        for (event_id,) in db.session.query(CalendarEvent.id)
        .filter(filtro_marcados(), CalendarEvent.google_event_id.in_(vivos))
        .order_by(CalendarEvent.id)
    ]
    for event_id in ids:
        event = db.session.get(CalendarEvent, event_id)
        if event is None:
            continue
        try:
            desmarcou = desmarcar(event, motivo=MOTIVO_REAPARECEU)
            db.session.commit()
        except Exception:  # noqa: BLE001 — um evento com erro não pode parar a limpeza do mês
            db.session.rollback()
            logger.exception("[sumico] falha ao desmarcar o evento %s (%s)", event_id, ym)
            resultado.falhas.append(event_id)
            continue
        if desmarcou:
            resultado.desmarcados.append(event_id)


def limpar_mes(items: list[dict], year: int, month: int) -> ResultadoLimpeza:
    """Limpa um mês cuja lista o Google acabou de devolver (o chamador garante que respondeu).

    Primeiro, o marcado que voltou à lista perde a marca. Depois, cada candidato é decidido e
    comitado sozinho: um evento que falha (banco, aviso) volta atrás inteiro — marca sem aviso
    não existe —, entra em `falhas` e os outros seguem. O disjuntor é desta chamada: a primeira
    consulta sem resposta por rede, 5xx ou credencial encerra as consultas do mês (cada uma pode
    esperar 60 s); recusa pontual (403, 429) não segura as outras.
    """
    resultado = ResultadoLimpeza()
    ym = f"{year:04d}-{month:02d}"
    vivos = {item["id"] for item in items if item.get("id")}
    _desmarcar_os_que_voltaram(vivos, ym, resultado)
    disjuntor_aberto = False
    for event_id in _candidatos(vivos, year, month):
        event = db.session.get(CalendarEvent, event_id)
        if event is None:
            continue  # saiu por cascade (ensaio do pai apagado) ou por outro processo
        try:
            decisao = _decidir_candidato(event, ym, disjuntor_aberto=disjuntor_aberto)
            db.session.commit()
        except Exception:  # noqa: BLE001 — um evento com erro não pode parar a limpeza do mês
            db.session.rollback()
            logger.exception("[sumico] falha ao conferir o evento %s (%s)", event_id, ym)
            resultado.falhas.append(event_id)
            continue
        if decisao.motivo in gcal.MOTIVOS_QUE_ABREM_DISJUNTOR:
            disjuntor_aberto = True
        _registrar(resultado, event_id, decisao)
    return resultado


def faixa_sumidos(limite: int = FAIXA_LIMITE) -> dict[str, Any]:
    """Os eventos marcados, para a faixa do topo: contagem exata e a lista por urgência.

    Futuros (o evento ainda não terminou) por data crescente; depois os passados, do mais recente
    ao mais antigo; sem data por último. "Passado" é o fim (ou o início, sem fim) antes de agora
    em São Paulo — `now_sp()`, nunca `utcnow`, que erraria 3 h. Sem dinheiro, motivo nem autor:
    a faixa vai a todo Comercial.
    """
    linhas = (
        db.session.query(
            CalendarEvent.id, CalendarEvent.title, CalendarEvent.start_at, CalendarEvent.end_at
        )
        .filter(filtro_marcados())
        .all()
    )
    agora = now_sp()
    com_data = [linha for linha in linhas if linha.start_at is not None]
    futuros = sorted(
        (linha for linha in com_data if (linha.end_at or linha.start_at) >= agora),
        key=lambda linha: (linha.start_at, linha.id),
    )
    passados = sorted(
        (linha for linha in com_data if (linha.end_at or linha.start_at) < agora),
        key=lambda linha: (linha.start_at, linha.id),
        reverse=True,
    )
    sem_data = sorted((linha for linha in linhas if linha.start_at is None), key=lambda x: x.id)
    return {
        "total": len(linhas),
        "limit": limite,
        "items": [
            {
                "id": linha.id,
                "title": linha.title,
                "start_at": linha.start_at.isoformat() if linha.start_at else None,
            }
            for linha in (futuros + passados + sem_data)[:limite]
        ],
    }


def _reconferir_um(event: CalendarEvent) -> tuple[str, str]:
    """Consulta um marcado pelo próprio id. Presente → a marca sai e vale o Google; ausente e
    inconclusivo → nada (aqui "ausente" nunca apaga nem marca de novo)."""
    from app.calendar.routes import CALENDAR_ID, sync_events

    consulta = gcal.consultar_evento(CALENDAR_ID, event.google_event_id)
    if consulta.desfecho == gcal.DESFECHO_PRESENTE:
        desmarcar(event, motivo=MOTIVO_REAPARECEU)
        # Um commit só, o do próprio `sync_events`: marca retirada e dados do Google juntos.
        sync_events([consulta.item])
        return "reapareceram", consulta.motivo
    if consulta.desfecho == gcal.DESFECHO_AUSENTE:
        return "seguem_ausentes", consulta.motivo
    return "inconclusivos", consulta.motivo


def reconferir_marcados() -> dict[str, list[int]]:
    """Confere cada evento marcado no Google pelo próprio id, no começo de cada ciclo.

    Existe porque a lista do mês não alcança todo marcado: o de mês passado nunca é listado, e o
    que voltou com outra data aparece num mês que pode estar fora do horizonte. Disjuntor desta
    chamada, como o de `limpar_mes`; cada evento em transação própria.

    Returns:
        Ids por desfecho: `reapareceram`, `seguem_ausentes`, `inconclusivos` e `falhas`.
    """
    saida: dict[str, list[int]] = {
        "reapareceram": [],
        "seguem_ausentes": [],
        "inconclusivos": [],
        "falhas": [],
    }
    ids = [
        event_id
        for (event_id,) in db.session.query(CalendarEvent.id)
        .filter(filtro_marcados())
        .order_by(CalendarEvent.id)
    ]
    disjuntor_aberto = False
    for event_id in ids:
        event = db.session.get(CalendarEvent, event_id)
        if event is None or not event.is_google_missing:
            continue
        if disjuntor_aberto:
            saida["inconclusivos"].append(event_id)
            continue
        try:
            chave, motivo = _reconferir_um(event)
            db.session.commit()
        except Exception:  # noqa: BLE001 — um evento com erro não pode parar a reconferência
            db.session.rollback()
            logger.exception("[sumico] falha ao reconferir o evento marcado %s", event_id)
            saida["falhas"].append(event_id)
            continue
        if motivo in gcal.MOTIVOS_QUE_ABREM_DISJUNTOR:
            disjuntor_aberto = True
        saida[chave].append(event_id)
    return saida


# ── Devolver ao Google (o Superadmin, pela tela do evento) ─────────────────────────────────────

RESULTADO_RECRIADO = "recriado"
RESULTADO_REAPARECEU = "reapareceu"

# Código interno: o evento sumiu entre a view e o bloqueio — a view responde o 404 de sempre.
CODIGO_INEXISTENTE = "inexistente"
CODIGO_CANCELADO = "cancelado"
CODIGO_NAO_MARCADO = "nao_marcado"
CODIGO_VENDA_VIRTUAL = "venda_virtual"
CODIGO_SEM_DATA = "sem_data"
CODIGO_GOOGLE_TRAVADO = "google_travado"
CODIGO_GOOGLE_INCONCLUSIVO = "google_inconclusivo"
CODIGO_GOOGLE_DESCONECTADO = "google_desconectado"
CODIGO_GOOGLE_RECUSOU = "google_recusou"

# Os textos do contrato, letra por letra. Nenhum leva o erro bruto do Google: o tipo do erro vai
# só para a auditoria.
_MENSAGENS_DEVOLVER = {
    CODIGO_INEXISTENTE: "Evento não encontrado",
    CODIGO_CANCELADO: "Este evento está cancelado e não pode ser devolvido ao Google Agenda.",
    CODIGO_NAO_MARCADO: (
        "Este evento não está mais marcado — já foi devolvido ou voltou ao Google Agenda."
    ),
    CODIGO_VENDA_VIRTUAL: "Venda virtual não é devolvida ao Google Agenda por aqui.",
    CODIGO_SEM_DATA: ("Acerte a data e o horário do evento antes de devolvê-lo ao Google Agenda."),
    CODIGO_GOOGLE_TRAVADO: "Este ambiente não escreve no Google Agenda. Nada foi alterado.",
    CODIGO_GOOGLE_INCONCLUSIVO: (
        "O Google Agenda não respondeu à conferência. Nada foi alterado — tente de novo em alguns "
        "minutos."
    ),
    CODIGO_GOOGLE_DESCONECTADO: "O sistema está sem acesso ao Google Agenda. Nada foi alterado.",
}
MSG_RECUSOU_CRIACAO = (
    "O Google Agenda não confirmou a criação. A marca continua. Antes de tentar de novo, confira "
    "na Agenda se o evento apareceu — se apareceu, apague-o lá e devolva de novo."
)
MSG_RECUSOU_ATUALIZACAO = (
    "O evento já está no Google Agenda, mas o Google não aceitou a atualização. A marca continua "
    "— tente de novo."
)
_FRASE_ELENCO = (
    " O elenco deste evento passa a ser mantido pelo sistema: personagem acrescentado no título "
    "pelo Google não cria vaga."
)


class DevolverAoGoogleError(Exception):
    """A devolução não aconteceu. Sem status HTTP: quem traduz o `codigo` é a view."""

    def __init__(self, codigo: str, message: str | None = None) -> None:
        self.codigo = codigo
        self.message = message or _MENSAGENS_DEVOLVER.get(codigo, "")
        super().__init__(self.message)


def _validar(event: CalendarEvent | None) -> CalendarEvent:
    """Pode devolver? Não chama o Google nem escreve — vale antes e depois do bloqueio."""
    from app.calendar.routes import _is_virtual_event

    if event is None:
        raise DevolverAoGoogleError(CODIGO_INEXISTENTE)
    if event.is_cancelled:
        raise DevolverAoGoogleError(CODIGO_CANCELADO)
    if not event.is_google_missing:
        raise DevolverAoGoogleError(CODIGO_NAO_MARCADO)
    if _is_virtual_event(event):
        raise DevolverAoGoogleError(CODIGO_VENDA_VIRTUAL)
    if not event.start_at or not event.end_at or event.end_at < event.start_at:
        raise DevolverAoGoogleError(CODIGO_SEM_DATA)
    return event


def _exigir_ambiente_liberado() -> None:
    """Fora da produção a devolução não escreve no Google (Princípio XIV).

    Lida a cada chamada — o verify liga e desliga a chave no mesmo processo —, e chave ausente é
    travado: o `manto_local` traz o token de verdade do calendário da empresa.
    """
    if current_app.config.get("CALENDAR_SUPPRESS_EVENT_WRITES", True):
        raise DevolverAoGoogleError(CODIGO_GOOGLE_TRAVADO)


def _bloquear_e_revalidar(event_id: int, google_id_consultado: str) -> CalendarEvent:
    """Trava a linha até o commit e confere tudo de novo.

    Sem o bloqueio, dois cliques (ou o clique e o ciclo) criariam dois eventos no Google. Entre a
    consulta e aqui, outro clique, o ciclo ou o "Sincronizar" podem ter desmarcado, cancelado ou
    trocado o id do evento. Sem `joinedload`: o FOR UPDATE não aceita outer join.
    """
    event = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.id == event_id)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )
    event = _validar(event)
    if event.google_event_id != google_id_consultado:
        raise DevolverAoGoogleError(CODIGO_NAO_MARCADO)
    return event


def _papeis(actor: User) -> str | None:
    # `actor_role` é String(60) no histórico e na auditoria: o par de papéis de quem tem vários
    # passaria disso — e o estouro depois do insert deixaria um evento órfão no Google.
    return ", ".join(r.name for r in actor.roles)[:60] or None


def _tem_vaga_fora_do_titulo(event: CalendarEvent) -> bool:
    """A mesma conta da reconciliação do sync: vaga de personagem cujo nome não está no título."""
    from app.calendar.routes import _is_reserved_title_name, parse_characters, strip_role_prefix

    personagens = set(parse_characters(event.title))
    for role in event.roles:
        if role.role_type == "extra":
            continue
        nome = strip_role_prefix(role.character_name)
        if nome not in personagens and not _is_reserved_title_name(nome):
            return True
    return False


def _registrar_devolucao_google(event: CalendarEvent, *, actor: User, resultado: str) -> None:
    """Prepara o rastro ANTES de qualquer escrita no Google, e dá `flush`: a falha previsível de
    banco acontece antes da escrita externa. Não comita.

    Vaga fora do título: a origem passa a ser o sistema (nos dois ramos — nos dois o Google fica
    com o título do sistema), senão o sync seguinte apagaria a vaga com e-mail de remoção.
    """
    mudou_origem = event.source != "platform" and _tem_vaga_fora_do_titulo(event)
    if mudou_origem:
        event.source = "platform"
    desde = f"{event.google_missing_since:%d/%m/%Y}"
    marca = f'(estava marcado "Sumiu do Google Agenda" desde {desde}).'
    if resultado == RESULTADO_RECRIADO:
        texto = f"Devolveu o evento ao Google Agenda {marca}"
    else:
        texto = (
            f"Devolveu o evento ao Google Agenda: ele já estava de volta e nada foi criado {marca}"
        )
    # Sem `created_at`: vale o default UTC do modelo, que o histórico da tela converte.
    db.session.add(
        EventLog(
            event_id=event.id,
            actor_name=actor.name[:120],
            actor_role=_papeis(actor),
            message=texto + (_FRASE_ELENCO if mudou_origem else ""),
        )
    )
    db.session.flush()


def _falha_no_google(event_id: int, actor: User, exc: Exception, mensagem: str) -> NoReturn:
    """Desfaz tudo o que a devolução preparou, audita o tipo do erro e levanta `google_recusou`.

    Sem delete compensatório no Google: sem cenário que o exercite, seria código não verificado;
    o órfão fica no log, como na criação de evento.
    """
    from app.calendar.routes import _log_sync

    db.session.rollback()
    event = db.session.get(CalendarEvent, event_id)
    _log_sync(
        "google_return_failed",
        event,
        details=f"O Google recusou a devolução: {type(exc).__name__}",
        actor=actor.name[:120],
        actor_role=_papeis(actor),
    )
    db.session.commit()
    raise DevolverAoGoogleError(CODIGO_GOOGLE_RECUSOU, mensagem) from exc


def _dia_inteiro(event: CalendarEvent) -> bool:
    inicio, fim = event.start_at, event.end_at
    return inicio.time() == fim.time() == datetime.min.time() and fim > inicio


def _recriar_no_google(event: CalendarEvent, *, actor: User) -> dict:
    """Cria o evento de novo no Google com os dados ATUAIS do sistema — sem convidados, sem Meet."""
    from app.calendar.routes import CALENDAR_ID

    try:
        criado = gcal.insert_event(
            CALENDAR_ID,
            event.title,
            event.start_at,
            event.end_at,
            description=event.description or "",
            location=event.location or "",
            all_day=_dia_inteiro(event),
        )
        if not criado or not criado.get("id"):
            raise ValueError("o Google respondeu sem id")
    except Exception as exc:  # noqa: BLE001 — toda recusa do Google vira a mesma mensagem fixa
        _falha_no_google(event.id, actor, exc, MSG_RECUSOU_CRIACAO)
    return criado


def _devolver_recriando(event: CalendarEvent, *, actor: User) -> dict[str, Any]:
    from app.calendar.routes import _log_sync

    _registrar_devolucao_google(event, actor=actor, resultado=RESULTADO_RECRIADO)
    criado = _recriar_no_google(event, actor=actor)
    # Antes de trocar o id: `_log_sync` grava `gcal:<id>` na hora, e a auditoria guarda o velho.
    _log_sync(
        "google_returned",
        event,
        details=f"Devolvido ao Google Agenda — recriado com o id {criado['id']}",
        actor=actor.name[:120],
        actor_role=_papeis(actor),
    )
    event.google_event_id = criado["id"]
    event.google_html_link = criado.get("htmlLink")
    desmarcar(event, motivo=MOTIVO_DEVOLVIDO)
    # Entre o insert e o commit, só gravação local já preparada: a guarda da 254 em `sync_events`
    # cobre o evento recém-criado por 5 minutos, nada mais.
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception(
            "[sumico] devolução do evento %s não gravou; evento Google %s órfão",
            event.id,
            criado["id"],
        )
        raise DevolverAoGoogleError(CODIGO_GOOGLE_RECUSOU, MSG_RECUSOU_CRIACAO) from exc
    return {"event": event, "resultado": RESULTADO_RECRIADO}


def _devolver_ja_voltou(event: CalendarEvent, item: dict, *, actor: User) -> dict[str, Any]:
    """O id velho está de volta no Google (alguém restaurou da lixeira): nada é criado.

    O Google recebe os dados do sistema — o que foi editado enquanto marcado — pelo mesmo push da
    edição. Nunca `sync_events` aqui: ele gravaria o Google por cima do sistema e reconciliaria o
    elenco pelo título antigo.
    """
    from app.calendar.event_ops import _push_cabecalho_ao_google
    from app.calendar.routes import _log_sync

    _registrar_devolucao_google(event, actor=actor, resultado=RESULTADO_REAPARECEU)
    if not mesmos_dados(event, item):
        try:
            _push_cabecalho_ao_google(event)
        except Exception as exc:  # noqa: BLE001 — toda recusa do Google vira a mesma mensagem
            _falha_no_google(event.id, actor, exc, MSG_RECUSOU_ATUALIZACAO)
    _log_sync(
        "google_returned",
        event,
        details="Devolvido ao Google Agenda — já estava de volta, nada foi criado",
        actor=actor.name[:120],
        actor_role=_papeis(actor),
    )
    desmarcar(event, motivo=MOTIVO_DEVOLVIDO)
    db.session.commit()
    return {"event": event, "resultado": RESULTADO_REAPARECEU}


def devolver_ao_google(event_id: int, *, actor: User) -> dict[str, Any]:
    """Devolve ao Google Agenda um evento marcado — a única saída do evento marcado nesta entrega.

    Ordem: valida sem bloqueio → trava de ambiente → consulta o id velho (sem confirmar a
    ausência, nada é criado: um evento restaurado da lixeira ganharia um gêmeo) → bloqueia a linha
    e revalida → rastro → Google → troca o id → desmarca → commit.

    Returns:
        `{"event": CalendarEvent, "resultado": "recriado" | "reapareceu"}`; comita.

    Raises:
        DevolverAoGoogleError: com o `codigo` do contrato; a marca e o id ficam como estavam.
    """
    from app.calendar.routes import CALENDAR_ID

    event = _validar(db.session.get(CalendarEvent, event_id))
    _exigir_ambiente_liberado()
    id_velho = event.google_event_id
    consulta = gcal.consultar_evento(CALENDAR_ID, id_velho)
    if consulta.desfecho == gcal.DESFECHO_INCONCLUSIVO:
        sem_acesso = consulta.motivo == gcal.MOTIVO_SEM_CREDENCIAL
        raise DevolverAoGoogleError(
            CODIGO_GOOGLE_DESCONECTADO if sem_acesso else CODIGO_GOOGLE_INCONCLUSIVO
        )
    event = _bloquear_e_revalidar(event_id, id_velho)
    if consulta.desfecho == gcal.DESFECHO_PRESENTE:
        return _devolver_ja_voltou(event, consulta.item, actor=actor)
    return _devolver_recriando(event, actor=actor)
