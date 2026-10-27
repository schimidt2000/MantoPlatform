"""Sincronização com a ClickSign e as escritas do vínculo e da cobrança (feature 317).

A ClickSign é a fonte da verdade. Toda passada pergunta "o que mudou desde o último marco"
(`filter[modified]`), grava cada envelope em `ClicksignDocumento` (idempotente pelo id do envelope),
liga o de cliente à venda quando há um candidato só e anexa o PDF assinado. A mesma função serve ao
aviso da ClickSign (que só dispara — o conteúdo dele nunca é lido), à conferência periódica e ao
comando retroativo (research R-01).

Sem `flask.request`. Lê a trava e o token de `current_app.config` a cada chamada: o verify troca os
dois no mesmo processo. Comita por conta própria só a sincronização (é um job, não um endpoint); as
escritas chamadas pela API (`ligar`, `desligar`, `descartar`, `registrar_cobranca`) não comitam.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from flask import current_app
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage

from app import db
from app.constants import (
    CLICKSIGN_AUTOR,
    CLICKSIGN_AUTOR_PAPEL,
    CLICKSIGN_CURSOR_FOLGA_MINUTOS,
    CLICKSIGN_TIPO_ARTISTA,
    CLICKSIGN_TIPO_CLIENTE,
    CONFERIR_DESLIGADO,
    CONFERIR_SEM_TELEFONE,
    CONFERIR_TELEFONE_DIVERGE,
    FORM_SUGESTAO_JANELA_DIAS,
    TZ_SP,
    VINCULO_A_CONFERIR,
    VINCULO_DESCARTADO,
    VINCULO_FORA,
    VINCULO_LIGADO,
    VINCULO_ORIGEM_AUTO,
    VINCULO_ORIGEM_MANUAL,
    now_sp,
)
from app.contratos import contratos_ops as nucleo
from app.integracoes import clicksign_client as cliente
from app.models import (
    CalendarEvent,
    ClicksignCobranca,
    ClicksignDesvinculo,
    ClicksignDocumento,
    EventClient,
    EventLog,
    FormResponse,
)

logger = logging.getLogger(__name__)

# Uma passada presa (worker morto no meio) libera o lock depois disto.
LOCK_PRESO_MINUTOS = 10
# Sem marco (primeira passada automática), olha só a última semana: o passivo desde junho entra
# pelo comando retroativo, com simulação antes (quickstart §3).
JANELA_SEM_MARCO_DIAS = 7
# Quantas vezes a passada repete por causa de aviso que chegou no meio dela.
REPETICOES_MAXIMAS = 3


ALTERADO = "Este contrato acabou de ser alterado. A tela foi atualizada."


class ContratoIndisponivel(Exception):
    """O documento ou a venda não está em condição para a ação pedida (vira 409 na API).

    Attributes:
        codigo: `ja_ligado`, `nao_ligado`, `tipo_fora`, `cancelado`, `nao_cobravel`, `sem_venda`.
        motivo: Frase em pt-BR para a tela.
    """

    def __init__(self, codigo: str, motivo: str) -> None:
        super().__init__(motivo)
        self.codigo = codigo
        self.motivo = motivo


# ── Configuração ─────────────────────────────────────────────────────────────────────────────


def integracao_ligada() -> bool:
    """Há token configurado (FR-018)."""
    return bool(current_app.config.get("CLICKSIGN_ACCESS_TOKEN"))


def _conexao() -> dict[str, Any]:
    """Os três argumentos que toda função do cliente recebe; chave ausente = travado (XIV)."""
    return {
        "base": current_app.config.get("CLICKSIGN_API_BASE", "https://app.clicksign.com/api/v3"),
        "token": current_app.config.get("CLICKSIGN_ACCESS_TOKEN", ""),
        "travada": current_app.config.get("CLICKSIGN_SUPPRESS_CALLS", True),
    }


def _para_sp(valor: str | None) -> datetime | None:
    """ISO com fuso da ClickSign (`-03:00`) → horário de parede de SP sem fuso (como o resto)."""
    if not valor:
        return None
    try:
        momento = datetime.fromisoformat(valor)
    except ValueError:
        return None
    if momento.tzinfo is not None:
        momento = momento.astimezone(TZ_SP).replace(tzinfo=None)
    return momento


# ── Lock da passada ──────────────────────────────────────────────────────────────────────────


def _no_lock(sql: str, **params: Any) -> int:
    """Executa uma escrita do lock numa conexão PRÓPRIA, fora da sessão do app.

    A sessão da passada não pode ser comitada pelo lock: na simulação ela é desfeita inteira, e
    renovar o lock no meio comitaria o que a simulação gravou (analyze C-09).
    """
    with db.engine.begin() as conexao:
        return conexao.execute(text(sql), params).rowcount


def _reivindicar() -> bool:
    """Lock de execução única entre os 3 workers (molde `invite_reminders._claim_rodada`)."""
    agora = now_sp()
    return (
        _no_lock(
            "UPDATE site_settings SET clicksign_sync_at = :agora "
            "WHERE id = 1 AND (clicksign_sync_at IS NULL OR clicksign_sync_at < :preso)",
            agora=agora,
            preso=agora - timedelta(minutes=LOCK_PRESO_MINUTOS),
        )
        == 1
    )


def _renovar() -> None:
    """Mantém o lock vivo numa passada longa (o retroativo passa de 10 min)."""
    _no_lock("UPDATE site_settings SET clicksign_sync_at = :agora WHERE id = 1", agora=now_sp())


def _soltar(*, terminou: bool) -> None:
    if terminou:
        _no_lock(
            "UPDATE site_settings SET clicksign_sync_at = NULL, clicksign_sync_fim = :agora "
            "WHERE id = 1",
            agora=now_sp(),
        )
    else:
        _no_lock("UPDATE site_settings SET clicksign_sync_at = NULL WHERE id = 1")


def marcar_pendente() -> None:
    """O aviso que chegou com uma passada em curso pede para ela repetir antes de soltar."""
    _no_lock("UPDATE site_settings SET clicksign_sync_pendente = true WHERE id = 1")


def _consumir_pendente() -> bool:
    return (
        _no_lock(
            "UPDATE site_settings SET clicksign_sync_pendente = false "
            "WHERE id = 1 AND clicksign_sync_pendente = true"
        )
        == 1
    )


def _passada_recente(intervalo_segundos: int) -> bool:
    """A periódica de outro worker acabou há pouco (os 3 acordam juntos — analyze C-15)."""
    fim = db.session.execute(
        text("SELECT clicksign_sync_fim FROM site_settings WHERE id = 1")
    ).scalar()
    return fim is not None and fim > now_sp() - timedelta(seconds=intervalo_segundos * 0.9)


def _cursor() -> datetime | None:
    return db.session.execute(
        text("SELECT clicksign_sync_cursor FROM site_settings WHERE id = 1")
    ).scalar()


def _gravar_cursor(marco: datetime) -> None:
    _no_lock(
        "UPDATE site_settings SET clicksign_sync_cursor = :c "
        "WHERE id = 1 AND (clicksign_sync_cursor IS NULL OR clicksign_sync_cursor < :c)",
        c=marco,
    )


# ── Candidatos (venda viva na data do documento) ─────────────────────────────────────────────


@dataclass
class _Venda:
    principal: CalendarEvent
    eventos: list[CalendarEvent]
    chaves: set[str]
    temas: tuple[str, ...]


def _principal(evento: CalendarEvent) -> CalendarEvent:
    from app.financeiro.cobranca_ops import principal_da_venda

    return principal_da_venda(evento)


def _vendas_na_data(inicio: date, fim: date | None = None) -> list[_Venda]:
    """Vendas com algum dia (principal ou satélite) no intervalo; ensaio, 🟧 e loja ficam fora.

    Em lote (analyze C-04): uma consulta de eventos na janela, uma de principais com os satélites
    e a ficha, e uma por fonte de telefone (contratantes, fichas, formulários) para todos os dias de
    todas as vendas — nunca uma consulta por venda.
    """
    from sqlalchemy.orm import joinedload, selectinload

    from app.formularios.pre_evento_ops import _campos, _valor
    from app.models import Client

    fim = fim or inicio
    eventos = CalendarEvent.query.filter(
        func.date(CalendarEvent.start_at) >= inicio, func.date(CalendarEvent.start_at) <= fim
    ).all()
    principais_ids = {e.group_leader_id or e.id for e in eventos}
    if not principais_ids:
        return []
    principais = (
        CalendarEvent.query.options(
            selectinload(CalendarEvent.satellites), joinedload(CalendarEvent.client)
        )
        .filter(CalendarEvent.id.in_(principais_ids))
        .all()
    )
    # A venda cancelada continua candidata (para dizer "cancelada"); as outras exclusões não.
    principais = [p for p in principais if p.cancelled_at or nucleo.venda_entra(p)]
    grupos = {p.id: [p, *p.satellites] for p in principais}
    dono = {e.id: pid for pid, evs in grupos.items() for e in evs}
    telefones: dict[int, set[str]] = {pid: set() for pid in grupos}
    temas: dict[int, list[str]] = {p.id: [p.title or ""] for p in principais}
    client_ids = {e.client_id: dono[e.id] for evs in grupos.values() for e in evs if e.client_id}
    for event_id, phone in (
        db.session.query(EventClient.event_id, Client.phone)
        .join(Client, Client.id == EventClient.client_id)
        .filter(EventClient.event_id.in_(dono))
    ):
        telefones[dono[event_id]].add(phone)
    for client_id, phone in db.session.query(Client.id, Client.phone).filter(
        Client.id.in_(client_ids)
    ):
        telefones[client_ids[client_id]].add(phone)
    for resposta in FormResponse.query.filter(FormResponse.event_id.in_(dono)):
        pid = dono[resposta.event_id]
        if resposta.contact_phone:
            telefones[pid].add(resposta.contact_phone)
        tema = _valor(_campos(resposta), "tema")
        if tema:
            temas[pid].append(tema)
    return [
        _Venda(
            p,
            grupos[p.id],
            {c for c in (nucleo.chave_telefone(t) for t in telefones[p.id]) if c},
            tuple(temas[p.id]),
        )
        for p in principais
    ]


def _desvinculados(documento: ClicksignDocumento) -> set[int]:
    if documento.id is None:
        return set()
    return {
        event_id
        for (event_id,) in db.session.query(ClicksignDesvinculo.event_id).filter_by(
            documento_id=documento.id
        )
    }


def candidatos(documento: ClicksignDocumento) -> list[nucleo.Candidato]:
    """Vendas com a data e o telefone do documento (sem as de onde ele foi desligado)."""
    chave = nucleo.chave_telefone(documento.telefone_lido)
    if documento.data_lida is None or chave is None:
        return []
    fora = _desvinculados(documento)
    return [
        nucleo.Candidato(v.principal.id, v.temas, bool(v.principal.cancelled_at))
        for v in _vendas_na_data(documento.data_lida)
        if chave in v.chaves and v.principal.id not in fora
    ]


def sugestoes(documento: ClicksignDocumento) -> list[dict[str, Any]]:
    """Vendas vivas parecidas para a conferência: mesmo telefone em ±3 dias, ou mesma data."""
    if documento.data_lida is None:
        return []
    chave = nucleo.chave_telefone(documento.telefone_lido)
    janela = timedelta(days=FORM_SUGESTAO_JANELA_DIAS)
    fora = _desvinculados(documento)
    achadas = []
    for venda in _vendas_na_data(documento.data_lida - janela, documento.data_lida + janela):
        principal = venda.principal
        if principal.cancelled_at or principal.id in fora:
            continue
        mesma_data = any(
            e.start_at and e.start_at.date() == documento.data_lida for e in venda.eventos
        )
        if (chave and chave in venda.chaves) or mesma_data:
            achadas.append(
                {
                    "event_id": principal.id,
                    "titulo": principal.title,
                    "data_evento": principal.start_at.date().isoformat()
                    if principal.start_at
                    else None,
                    "cliente": _cliente_da_venda(principal),
                    "mesmo_telefone": bool(chave and chave in venda.chaves),
                }
            )
    achadas.sort(key=lambda s: (not s["mesmo_telefone"], s["data_evento"] or ""))
    return achadas[:5]


def _cliente_da_venda(principal: CalendarEvent) -> str | None:
    from app.financeiro.vendas_ops import contratante_name

    return contratante_name(principal)


# ── Aplicar um envelope ──────────────────────────────────────────────────────────────────────


def _vincular(documento: ClicksignDocumento) -> None:
    """Classifica e decide o vínculo automático (FR-002/FR-004/FR-005)."""
    if documento.tipo == CLICKSIGN_TIPO_ARTISTA or (
        documento.tipo != CLICKSIGN_TIPO_CLIENTE and documento.data_lida is None
    ):
        documento.vinculo, documento.vinculo_motivo, documento.event_id = VINCULO_FORA, None, None
        return
    if documento.tipo != CLICKSIGN_TIPO_CLIENTE:
        documento.vinculo, documento.vinculo_motivo = VINCULO_A_CONFERIR, CONFERIR_SEM_TELEFONE
        return
    chave_nome = nucleo.chave_telefone(documento.telefone_lido)
    chave_signatario = nucleo.chave_telefone(documento.signatario_telefone)
    if chave_nome and chave_signatario and chave_nome != chave_signatario:
        documento.vinculo, documento.vinculo_motivo = VINCULO_A_CONFERIR, CONFERIR_TELEFONE_DIVERGE
        return
    lido = nucleo.NomeLido(
        documento.data_lida,
        None,
        documento.telefone_lido,
        documento.signatario_email,
        documento.tema_lido,
    )
    event_id, motivo = nucleo.escolher_candidato(lido, candidatos(documento))
    if event_id is None:
        documento.vinculo, documento.vinculo_motivo, documento.event_id = (
            VINCULO_A_CONFERIR,
            motivo,
            None,
        )
        return
    documento.vinculo = VINCULO_LIGADO
    documento.vinculo_origem = VINCULO_ORIGEM_AUTO
    documento.vinculo_motivo = None
    documento.event_id = event_id
    documento.vinculado_em = now_sp()


def _ler_signatario(documento: ClicksignDocumento, conexao: dict[str, Any]) -> None:
    from app.clientes.importer import normalize_phone

    signers = cliente.signatarios(documento.envelope_id, **conexao)
    if not signers:
        return
    atributos = signers[0].get("attributes") or {}
    documento.signatario_nome = (atributos.get("name") or "")[:200] or None
    documento.signatario_telefone = normalize_phone(atributos.get("phone_number"))
    documento.signatario_email = (atributos.get("email") or "")[:200] or None
    documento.canal = nucleo.canal_do_signatario(atributos.get("communicate_events"))


def _ler_eventos(documento: ClicksignDocumento, conexao: dict[str, Any]) -> None:
    nomes = [(e.get("attributes") or {}) for e in cliente.eventos(documento.envelope_id, **conexao)]
    assinaturas = [
        _para_sp(a.get("created")) for a in nomes if a.get("name") in ("sign", "auto_close")
    ]
    assinaturas = [m for m in assinaturas if m]
    if documento.status == nucleo.STATUS_FECHADO:
        documento.assinado_em = max(assinaturas) if assinaturas else documento.modificado_em
    documento.recusado = any(a.get("name") == "refusal" for a in nomes)


def aplicar_envelope(
    envelope: dict[str, Any], conexao: dict[str, Any]
) -> tuple[ClicksignDocumento, bool]:
    """Grava um envelope (idempotente pelo id) e devolve (documento, mudou)."""
    atributos = envelope.get("attributes") or {}
    # FOR UPDATE: a periódica de outro worker (lock vencido) ou a comercial ligando à mão não
    # escrevem a mesma linha ao mesmo tempo (analyze C-10).
    documento = (
        ClicksignDocumento.query.filter_by(envelope_id=envelope["id"])
        .with_for_update()
        .populate_existing()
        .first()
    )
    novo = documento is None
    modificado = _para_sp(atributos.get("modified"))
    status = atributos.get("status") or nucleo.STATUS_RASCUNHO
    if novo:
        documento = ClicksignDocumento(
            envelope_id=envelope["id"], vinculo=VINCULO_A_CONFERIR, tipo="outro", status=status
        )
        db.session.add(documento)
    mudou = novo or documento.status != status or documento.modificado_em != modificado
    status_anterior = None if novo else documento.status

    documento.nome = atributos.get("name")
    documento.status = status
    documento.prazo = _para_sp(atributos.get("deadline_at"))
    documento.criado_em = _para_sp(atributos.get("created"))
    documento.modificado_em = modificado
    documento.sincronizado_em = now_sp()
    if documento.status == nucleo.STATUS_CANCELADO:
        documento.cancelado_em = documento.cancelado_em or modificado

    lido = nucleo.ler_nome(documento.nome)
    documento.data_lida = lido.data
    documento.telefone_lido = lido.telefone
    documento.tema_lido = lido.tema
    # O "outro" que a comercial ligou à mão vira de cliente e não é reclassificado (analyze C-02).
    if not (
        documento.vinculo == VINCULO_LIGADO and documento.vinculo_origem == VINCULO_ORIGEM_MANUAL
    ):
        documento.tipo = nucleo.classificar(documento.nome, lido)

    # Relê o signatário quando o envelope ainda em processo mudou: a troca de signatário muda o
    # canal da cobrança (analyze C-19).
    em_processo = documento.status in (nucleo.STATUS_EM_PROCESSO, nucleo.STATUS_RASCUNHO)
    if (
        novo
        or (mudou and em_processo)
        or (documento.canal is None and documento.signatario_telefone is None)
    ):
        _ler_signatario(documento, conexao)
    if mudou and documento.status in (nucleo.STATUS_FECHADO, nucleo.STATUS_CANCELADO):
        _ler_eventos(documento, conexao)

    db.session.flush()
    # Só documento novo ou ainda "a conferir" por decisão automática é reavaliado: ligado à mão,
    # descartado e desligado nunca mudam sozinhos (FR-005).
    if novo or (
        documento.vinculo == VINCULO_A_CONFERIR
        and documento.vinculo_origem is None
        and documento.vinculo_motivo != CONFERIR_DESLIGADO
    ):
        _vincular(documento)
    if (
        documento.status == nucleo.STATUS_FECHADO
        and status_anterior != nucleo.STATUS_FECHADO
        and documento.vinculo == VINCULO_LIGADO
        and documento.contrato_anexo_id is None
    ):
        documento.anexo_pendente = True
    return documento, mudou


def anexo_manual_do_mesmo_documento(documento: ClicksignDocumento) -> Any | None:
    """O `EventContract` que alguém já anexou à mão com o PDF baixado deste documento, se houver.

    A ClickSign nomeia o download `<nome do envelope> - Clicksign.pdf`; o upload passa por
    `secure_filename` e ganha um prefixo de data. Procura nos dias da venda ligada.
    """
    from werkzeug.utils import secure_filename

    from app.calendar.group_ops import group_events
    from app.models import EventContract

    if documento.event_id is None or not documento.nome:
        return None
    evento = db.session.get(CalendarEvent, documento.event_id)
    if evento is None:
        return None
    alvo = secure_filename(f"{nucleo.normalizar_nome(documento.nome)} - Clicksign.pdf").lower()
    if not alvo:
        return None
    usados = db.session.query(ClicksignDocumento.contrato_anexo_id).filter(
        ClicksignDocumento.contrato_anexo_id.isnot(None)
    )
    for contrato in EventContract.query.filter(
        EventContract.event_id.in_([e.id for e in group_events(evento)]),
        EventContract.id.notin_(usados),
    ):
        if (contrato.file_path or "").lower().endswith(alvo):
            return contrato
    return None


def anexar_assinado(documento: ClicksignDocumento, conexao: dict[str, Any]) -> bool:
    """Baixa o PDF assinado e o anexa ao evento ligado, marcado como assinado (FR-009).

    Falha de rede mantém `anexo_pendente` para a próxima passada; arquivo recusado (grande ou
    inválido) desiste com log. Excluir o anexo depois não o traz de volta (`anexo_pendente` falso).
    """
    from app.calendar.routes import _add_contract_record

    if not documento.anexo_pendente or documento.event_id is None:
        return False
    evento = db.session.get(CalendarEvent, documento.event_id)
    if evento is None:
        return False
    if evento.cancelled_at:
        # A tela do cancelado é só consulta (312): o PDF fica pendente e entra se a venda voltar.
        logger.info("[clicksign] anexo de %s adiado: venda cancelada", documento.envelope_id)
        return False
    manual = anexo_manual_do_mesmo_documento(documento)
    if manual is not None:
        # O PDF já foi baixado e anexado à mão (o "… - Clicksign.pdf" de antes da 317): vira o anexo
        # do documento, marcado — sem baixar de novo nem duplicar (analyze C-08).
        manual.is_signed = True
        documento.contrato_anexo_id = manual.id
        documento.anexo_pendente = False
        return True
    try:
        if documento.document_id is None:
            docs = cliente.documentos(documento.envelope_id, **conexao)
            if not docs:
                return False
            documento.document_id = docs[0]["id"]
        detalhe = cliente.documento(documento.envelope_id, documento.document_id, **conexao)
        url = ((detalhe.get("links") or {}).get("files") or {}).get("signed")
        if not url:
            return False
        dados = cliente.baixar(url, travada=conexao["travada"])
    except cliente.ClicksignError as exc:
        # Indisponível ou recusado: fica pendente para a varredura da próxima passada.
        logger.warning("[clicksign] anexo de %s adiado: %s", documento.envelope_id, exc)
        return False
    nome_arquivo = (
        f"{nucleo.normalizar_nome(documento.nome) or documento.envelope_id} - Clicksign.pdf"
    )
    arquivo = FileStorage(io.BytesIO(dados), filename=nome_arquivo, content_type="application/pdf")
    contrato = _add_contract_record(evento, file_storage=arquivo, is_signed=True)
    documento.anexo_pendente = False
    if contrato is None:
        logger.warning(
            "[clicksign] PDF de %s recusado pelo upload (tamanho ou tipo)", documento.envelope_id
        )
        return False
    db.session.flush()
    documento.contrato_anexo_id = contrato.id
    db.session.add(
        EventLog(
            event_id=evento.id,
            actor_name=CLICKSIGN_AUTOR,
            actor_role=CLICKSIGN_AUTOR_PAPEL,
            message=f"Anexou o contrato assinado na ClickSign: {nucleo.normalizar_nome(documento.nome)}",
            created_at=datetime.utcnow(),
        )
    )
    return True


# ── A passada ────────────────────────────────────────────────────────────────────────────────


def _uma_passada(
    desde: date, ate: date | None, aplicar: bool, conexao: dict[str, Any]
) -> dict[str, int]:
    contagem = {
        "envelopes": 0,
        "novos": 0,
        "ligados": 0,
        "a_conferir": 0,
        "artista": 0,
        "outro": 0,
        "anexados": 0,
        "anexar": 0,
        "anexos_antigos": 0,
        "erros": 0,
    }
    maior: datetime | None = None
    menor_falha: datetime | None = None
    pagina = 1
    while True:
        resposta = cliente.listar_envelopes(
            modificado_desde=desde, modificado_ate=ate, pagina=pagina, **conexao
        )
        envelopes = list(resposta.get("data") or [])
        for envelope in envelopes:
            modificado = _para_sp((envelope.get("attributes") or {}).get("modified"))
            existia = (
                ClicksignDocumento.query.filter_by(envelope_id=envelope["id"]).first() is not None
            )
            # Um envelope que falha (4xx da ClickSign, conflito no banco) não derruba a passada nem
            # trava o marco para sempre: desfaz só ele, registra e segue (analyze C-03).
            try:
                with db.session.begin_nested():
                    documento, _mudou = aplicar_envelope(envelope, conexao)
            except (cliente.ClicksignError, IntegrityError) as exc:
                contagem["erros"] += 1
                logger.warning("[clicksign] envelope %s pulado: %s", envelope.get("id"), exc)
                if modificado and (menor_falha is None or modificado < menor_falha):
                    menor_falha = modificado
                continue
            contagem["envelopes"] += 1
            contagem["novos"] += 0 if existia else 1
            if documento.vinculo == VINCULO_LIGADO:
                contagem["ligados"] += 1
            elif documento.vinculo == VINCULO_A_CONFERIR:
                contagem["a_conferir"] += 1
            elif documento.tipo == CLICKSIGN_TIPO_ARTISTA:
                contagem["artista"] += 1
            else:
                contagem["outro"] += 1
            if modificado and (maior is None or modificado > maior):
                maior = modificado
        if aplicar:
            db.session.commit()
            _renovar()
        if len(envelopes) < cliente.TAMANHO_DA_PAGINA:
            break
        pagina += 1

    # Varredura de TODO anexo pendente, não só dos envelopes que voltaram na listagem: o
    # documento antigo ligado à mão e o download que falhou com o marco já passado (analyze C-01).
    pendentes = ClicksignDocumento.query.filter(
        ClicksignDocumento.anexo_pendente.is_(True),
        ClicksignDocumento.vinculo == VINCULO_LIGADO,
    ).all()
    for documento in pendentes:
        if not aplicar:
            contagem["anexar"] += 1
            if anexo_manual_do_mesmo_documento(documento) is not None:
                contagem["anexos_antigos"] += 1
            continue
        manual = anexo_manual_do_mesmo_documento(documento) is not None
        try:
            with db.session.begin_nested():
                anexou = anexar_assinado(documento, conexao)
        except (cliente.ClicksignError, IntegrityError) as exc:
            contagem["erros"] += 1
            logger.warning("[clicksign] anexo de %s pulado: %s", documento.envelope_id, exc)
            continue
        if anexou:
            contagem["anexos_antigos" if manual else "anexados"] += 1
        db.session.commit()

    if aplicar:
        db.session.commit()
        marco = min(m for m in (maior, menor_falha) if m) if (maior or menor_falha) else None
        if marco is not None:
            _gravar_cursor(marco)
    else:
        db.session.rollback()
    return contagem


def sincronizar(
    *,
    desde: date | None = None,
    ate: date | None = None,
    aplicar: bool = True,
    motivo: str = "aviso",
) -> dict[str, Any]:
    """Uma passada incremental (e as repetições pedidas por aviso no meio dela).

    Args:
        desde: Início do `filter[modified]`; sem ele, o marco menos a folga (ou a última semana).
        ate: Fim do intervalo (o comando usa; a passada automática não).
        aplicar: Falso = simulação: lê tudo, conta e desfaz (o comando sem `--aplicar`).
        motivo: `aviso`, `periodica` ou `comando` — só para o log.

    Returns:
        Contagens; ou `{"desligada": True}` sem token, `{"travada": True}` com a trava,
        `{"ocupada": True}` quando outra passada segura o lock (e fica pedida a repetição).
    """
    if not integracao_ligada():
        return {"desligada": True}
    conexao = _conexao()
    if conexao["travada"]:
        try:
            cliente.listar_envelopes(pagina=1, **conexao)
        except cliente.ClicksignTravada:
            return {"travada": True}
    periodica = motivo == "periodica"
    if periodica and _passada_recente(current_app.config.get("CLICKSIGN_SYNC_INTERVAL", 1800)):
        return {"recente": True}
    total: dict[str, Any] = {"motivo": motivo, "passadas": 0}
    for _ in range(REPETICOES_MAXIMAS):
        if not _reivindicar():
            # Só o aviso pede repetição: a periódica e a simulação não escrevem nada aqui.
            if aplicar and not periodica:
                marcar_pendente()
            return {**total, "ocupada": True} if total["passadas"] else {"ocupada": True}
        terminou = False
        try:
            inicio = desde
            if inicio is None:
                marco = _cursor()
                inicio = (
                    (marco - timedelta(minutes=CLICKSIGN_CURSOR_FOLGA_MINUTOS)).date()
                    if marco
                    else now_sp().date() - timedelta(days=JANELA_SEM_MARCO_DIAS)
                )
            contagem = _uma_passada(inicio, ate, aplicar, conexao)
            total["passadas"] += 1
            for chave, valor in contagem.items():
                total[chave] = total.get(chave, 0) + valor
            terminou = aplicar
        except Exception as exc:  # noqa: BLE001 — a passada nunca deixa o lock preso
            db.session.rollback()
            logger.warning("[clicksign] passada (%s) interrompida: %s", motivo, exc)
            total["erro"] = str(exc)
        finally:
            _soltar(terminou=terminou)
        # O aviso que chegou durante a passada (ou entre o fim dela e o soltar) pede outra.
        if not aplicar or total.get("erro") or not _consumir_pendente():
            break
    return total


# ── Escritas da comercial (sem commit; a rota comita) ────────────────────────────────────────


def _documento_travado(documento_id: int) -> ClicksignDocumento | None:
    return (
        ClicksignDocumento.query.filter_by(id=documento_id)
        .with_for_update()
        .populate_existing()
        .first()
    )


def ligar(documento_id: int, event_id: int, usuario: Any) -> ClicksignDocumento:
    """Liga o documento à venda do evento (sempre o principal). FR-006."""
    from app.calendar.cancel_ops import EventoSomenteConsultaError, exigir_evento_vivo

    documento = _documento_travado(documento_id)
    if documento is None:
        raise LookupError("documento")
    if documento.vinculo == VINCULO_LIGADO:
        raise ContratoIndisponivel("ja_ligado", "Este contrato já está ligado a uma venda.")
    if documento.tipo == CLICKSIGN_TIPO_ARTISTA:
        raise ContratoIndisponivel("tipo_fora", "Contrato de artista não se liga a venda.")
    if documento.vinculo != VINCULO_A_CONFERIR:
        # Outra pessoa acabou de descartar (borda "duas pessoas…" da spec).
        raise ContratoIndisponivel("alterado", ALTERADO)
    evento = db.session.get(CalendarEvent, event_id, with_for_update=True)
    if evento is None:
        raise LookupError("evento")
    principal = _principal(evento)
    try:
        exigir_evento_vivo(principal)
    except EventoSomenteConsultaError as exc:
        raise ContratoIndisponivel("cancelado", str(exc)) from exc
    documento.vinculo = VINCULO_LIGADO
    documento.vinculo_origem = VINCULO_ORIGEM_MANUAL
    documento.vinculo_motivo = None
    # O "outro" (corporativo só com razão social) que a comercial reconheceu passa a contar como
    # contrato de cliente da venda — senão sumia da conferência e não aparecia na situação (C-02).
    documento.tipo = CLICKSIGN_TIPO_CLIENTE
    documento.event_id = principal.id
    documento.vinculado_por_id = getattr(usuario, "id", None)
    documento.vinculado_em = now_sp()
    if documento.status == nucleo.STATUS_FECHADO and documento.contrato_anexo_id is None:
        documento.anexo_pendente = True
    return documento


def desligar(documento_id: int, usuario: Any) -> ClicksignDocumento:
    """Desliga e lembra o par: a sincronização não religa sozinha nessa venda (FR-005)."""
    documento = _documento_travado(documento_id)
    if documento is None:
        raise LookupError("documento")
    if documento.vinculo != VINCULO_LIGADO or documento.event_id is None:
        raise ContratoIndisponivel("nao_ligado", "Este contrato não está ligado a uma venda.")
    existe = ClicksignDesvinculo.query.filter_by(
        documento_id=documento.id, event_id=documento.event_id
    ).first()
    if existe is None:
        db.session.add(
            ClicksignDesvinculo(
                documento_id=documento.id,
                event_id=documento.event_id,
                por_id=getattr(usuario, "id", None),
            )
        )
    _tirar_anexo_automatico(documento)
    documento.vinculo = VINCULO_A_CONFERIR
    documento.vinculo_origem = VINCULO_ORIGEM_MANUAL
    documento.vinculo_motivo = CONFERIR_DESLIGADO
    documento.event_id = None
    documento.vinculado_por_id = getattr(usuario, "id", None)
    documento.vinculado_em = now_sp()
    documento.anexo_pendente = False
    return documento


def _tirar_anexo_automatico(documento: ClicksignDocumento) -> None:
    """O PDF assinado que a sincronização anexou na venda errada sai dela (analyze C-06).

    Só o registro sai: o arquivo fica no disco, como em toda exclusão de contrato. Fica no histórico
    do evento quem tirou e por quê. Ao ligar à venda certa, o PDF é anexado de novo lá.
    """
    from app.models import EventContract

    if documento.contrato_anexo_id is None:
        return
    contrato = db.session.get(EventContract, documento.contrato_anexo_id)
    documento.contrato_anexo_id = None
    if contrato is None:
        return
    db.session.add(
        EventLog(
            event_id=contrato.event_id,
            actor_name=CLICKSIGN_AUTOR,
            actor_role=CLICKSIGN_AUTOR_PAPEL,
            message=(
                "Retirou o contrato assinado da ClickSign desligado desta venda: "
                f"{nucleo.normalizar_nome(documento.nome)}"
            ),
            created_at=datetime.utcnow(),
        )
    )
    db.session.delete(contrato)


def descartar(documento_id: int, usuario: Any) -> ClicksignDocumento:
    """ "Não é de nenhuma venda": sai da conferência para sempre."""
    documento = _documento_travado(documento_id)
    if documento is None:
        raise LookupError("documento")
    if documento.vinculo == VINCULO_LIGADO:
        raise ContratoIndisponivel("ja_ligado", "Desligue o contrato da venda antes de descartar.")
    if documento.vinculo != VINCULO_A_CONFERIR:
        raise ContratoIndisponivel("alterado", ALTERADO)
    documento.vinculo = VINCULO_DESCARTADO
    documento.vinculo_origem = VINCULO_ORIGEM_MANUAL
    documento.vinculado_por_id = getattr(usuario, "id", None)
    documento.vinculado_em = now_sp()
    return documento


def registrar_cobranca(documento_id: int, usuario: Any) -> ClicksignCobranca:
    """Registra o "Cobrar contrato" (FR-011); só o contrato aguardando, no principal vivo."""
    documento = db.session.get(ClicksignDocumento, documento_id)
    if documento is None:
        raise LookupError("documento")
    if documento.vinculo != VINCULO_LIGADO or documento.event_id is None:
        raise ContratoIndisponivel("sem_venda", "Este contrato não está ligado a uma venda.")
    from app.contratos.situacao_ops import situacao_da_venda

    principal = db.session.get(CalendarEvent, documento.event_id)
    principal = _principal(principal)
    situacao = situacao_da_venda(principal)
    bloqueio = nucleo.bloqueio_da_cobranca(
        situacao["situacao"], eh_principal=True, venda_viva=principal.cancelled_at is None
    )
    if bloqueio or (situacao["documento"] is None or situacao["documento"].id != documento.id):
        raise ContratoIndisponivel(
            "nao_cobravel", bloqueio or "Este não é o contrato vigente da venda."
        )
    cobranca = ClicksignCobranca(
        documento_id=documento.id,
        event_id=principal.id,
        usuario_id=getattr(usuario, "id", None),
        usuario_nome=(getattr(usuario, "name", None) or getattr(usuario, "email", None) or "—")[
            :120
        ],
        em=now_sp(),
    )
    db.session.add(cobranca)
    return cobranca
