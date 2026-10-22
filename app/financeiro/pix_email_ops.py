"""A rodada da leitura dos avisos de PIX do Inter (feature 318).

Thread `pix-email` (`app/__init__.py`), a cada `PIX_EMAIL_SWEEP_INTERVAL`, uma rodada só entre os
workers (`claim_sweep`, molde do bounce da 219):

1. interruptor da tela desligado → não lê nada;
2. lê a caixa (IMAP, só leitura) — `fetch_messages` dos últimos `PIX_EMAIL_LOOKBACK_DAYS`;
3. cada e-mail novo (pelo `Message-ID`) vira um `PixRecebido` e passa pela regra (`pix_ops.vincular`);
4. PIX sem venda dos últimos 7 dias é comparado de novo (a cliente paga o sinal antes de a venda ser
   cadastrada);
5. erro de acesso à caixa fica em `site_settings.pix_email_ultimo_erro` — a tela mostra.

Cada aviso é commitado sozinho: um aviso que quebra não desfaz os outros.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError

from app import db
from app.constants import (
    PIX_ESTADO_IGNORADO,
    PIX_ESTADO_NAO_ENTENDIDO,
    PIX_ESTADO_NOVO,
    PIX_ESTADO_SEM_VENDA,
    PIX_ORIGEM_EMAIL_INTER,
    PIX_REAVALIAR_DIAS,
    PIX_SAUDE_JANELA_DIAS,
    PIX_SAUDE_PARADA_MIN,
    PIX_TIPO_DEVOLUCAO,
    PIX_TIPO_PIX,
    now_sp,
)
from app.financeiro import pix_ops
from app.financeiro.pix_aviso import AvisoDesconhecido, AvisoPix, ler_aviso_inter
from app.models import ContaRecebimento, ImportState, PixRecebido, SiteSetting

log = logging.getLogger(__name__)

CHAVE_RODADA = "pix_email"
REMETENTE = "no-reply@inter.co"
ASSUNTO = "Pix recebido"


def claim_sweep(interval_seconds: int) -> bool:
    """Reivindica a rodada de forma atômica entre os workers (cópia do `bounce_ops.claim_sweep`,
    para não mexer no que a 219 roda)."""
    agora = datetime.utcnow()
    limiar = agora - timedelta(seconds=interval_seconds)
    if not ImportState.query.filter_by(key=CHAVE_RODADA).first():
        try:
            db.session.add(ImportState(key=CHAVE_RODADA, last_row=0))
            db.session.commit()
        except IntegrityError:  # outro worker criou a linha primeiro
            db.session.rollback()
    resultado = db.session.execute(
        text(
            "UPDATE import_state SET last_checked_at = :agora "
            "WHERE key = :chave AND (last_checked_at IS NULL OR last_checked_at < :limiar)"
        ),
        {"agora": agora, "limiar": limiar, "chave": CHAVE_RODADA},
    )
    db.session.commit()
    return resultado.rowcount == 1


def _ingerir(aviso: AvisoPix | AvisoDesconhecido, ativo_desde: datetime | None) -> PixRecebido:
    pix = PixRecebido(
        origem=PIX_ORIGEM_EMAIL_INTER,
        message_id=aviso.message_id[:300],
        tipo=aviso.tipo,
        recebido_em=aviso.recebido_em,
        autenticado=aviso.autenticado,
        estado=PIX_ESTADO_NOVO,
        descartados=[],
        pagamentos_extra=[],
    )
    if isinstance(aviso, AvisoDesconhecido):
        pix.estado = PIX_ESTADO_NAO_ENTENDIDO
        pix.assunto = aviso.assunto
        pix.remetente = aviso.remetente
        return pix
    pix.valor = aviso.valor
    pix.pagador_nome = aviso.pagador_nome
    pix.pagador_norm = pix_ops.normalizar_nome(aviso.pagador_nome) or None
    pix.numero_conta_lido = aviso.numero_conta
    pix.titular_lido = aviso.titular
    conta = pix_ops.conta_por_numero(aviso.numero_conta)
    pix.conta_id = conta.id if conta else None
    if aviso.tipo == PIX_TIPO_DEVOLUCAO:
        pix.estado = PIX_ESTADO_IGNORADO
        pix.motivo = "devolução de um PIX enviado"
    elif ativo_desde is not None and aviso.recebido_em < ativo_desde:
        pix.estado = PIX_ESTADO_IGNORADO
        pix.motivo = "anterior ao início da leitura"
    return pix


def processar_brutos(brutos: list[bytes]) -> dict:
    """Guarda e decide cada e-mail ainda não visto. Commita aviso a aviso."""
    contagem = {"lidos": 0, "novos": 0, "nao_entendidos": 0, "erros": 0}
    s = db.session.get(SiteSetting, 1)
    ativo_desde = s.pix_email_ativo_desde if s else None
    vendas: list | None = None
    for bruto in brutos:
        contagem["lidos"] += 1
        aviso = ler_aviso_inter(bruto)
        if aviso is None:
            contagem["nao_entendidos"] += 1
            continue
        if PixRecebido.query.filter_by(message_id=aviso.message_id[:300]).first() is not None:
            continue
        # 1º o aviso fica guardado (commit próprio): se a decisão quebrar, ele não some — fica
        # "novo", é tentado de novo na próxima rodada e o erro aparece na saúde.
        try:
            pix = _ingerir(aviso, ativo_desde)
            db.session.add(pix)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()  # outro processo guardou o mesmo e-mail primeiro
            continue
        contagem["novos"] += 1
        if pix.estado == PIX_ESTADO_NAO_ENTENDIDO:
            contagem["nao_entendidos"] += 1
        if pix.estado != PIX_ESTADO_NOVO:
            continue
        pix_id = pix.id
        try:
            pix = PixRecebido.query.filter_by(id=pix_id).with_for_update().first()
            if vendas is None:
                vendas = pix_ops.vendas_abertas()
            pix_ops.vincular(pix, vendas=vendas)
            if pix.event_payment_id:
                vendas = None  # o saldo mudou: a próxima decisão relê as vendas
            db.session.commit()
        except Exception as exc:  # noqa: BLE001 — um aviso que quebra não para a rodada
            db.session.rollback()
            vendas = None
            contagem["erros"] += 1
            _registrar_erro(f"falha ao decidir o PIX {pix_id}: {exc}")
            log.exception("[pix-email] falha ao decidir o PIX %s", pix_id)
    return contagem


def _registrar_erro(texto: str) -> None:
    s = db.session.get(SiteSetting, 1)
    if s is not None:
        s.pix_email_ultimo_erro = texto[:500]
        s.pix_email_ultimo_erro_em = now_sp()
        db.session.commit()


def reavaliar_pendentes() -> int:
    """PIX sem venda (que ninguém decidiu) dos últimos 7 dias, comparado de novo. Commita cada um."""
    desde = now_sp() - timedelta(days=PIX_REAVALIAR_DIAS)
    ids = [
        pid
        for (pid,) in db.session.query(PixRecebido.id).filter(
            # `novo` = aviso guardado cuja decisão quebrou numa rodada anterior.
            PixRecebido.estado.in_((PIX_ESTADO_SEM_VENDA, PIX_ESTADO_NOVO)),
            PixRecebido.decidido_por_id.is_(None),
            PixRecebido.tipo == PIX_TIPO_PIX,
            PixRecebido.recebido_em >= desde,
        )
    ]
    if not ids:
        return 0
    mudaram = 0
    vendas = pix_ops.vendas_abertas()
    for pid in ids:
        try:
            pix = PixRecebido.query.filter_by(id=pid).with_for_update().first()
            if pix is None or pix.estado not in (PIX_ESTADO_SEM_VENDA, PIX_ESTADO_NOVO) or pix.decidido_por_id:
                db.session.rollback()
                continue
            pix.estado = PIX_ESTADO_NOVO
            pix_ops.vincular(pix, vendas=vendas)
            if pix.estado != PIX_ESTADO_SEM_VENDA:
                mudaram += 1
                if pix.event_payment_id:
                    vendas = pix_ops.vendas_abertas()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            log.exception("[pix-email] falha ao reavaliar o PIX %s", pid)
    return mudaram


def _buscar_padrao(**kwargs) -> list[bytes]:
    from app.integracoes.imap_client import fetch_messages

    return fetch_messages(**kwargs)


def rodada(*, buscar: Callable[..., list[bytes]] | None = None) -> dict:
    """Uma rodada completa (sem o claim — quem chama reivindica). `buscar` é injetável (verify)."""
    from flask import current_app

    from app.integracoes.imap_client import ImapUnavailableError

    s = db.session.get(SiteSetting, 1)
    if s is None or not s.pix_email_ativo:
        return {"ativo": False}
    buscar = buscar or _buscar_padrao
    try:
        brutos = buscar(
            username=current_app.config.get("MAIL_USERNAME"),
            password=current_app.config.get("MAIL_PASSWORD"),
            sender=REMETENTE,
            subject=ASSUNTO,
            since_days=current_app.config.get("PIX_EMAIL_LOOKBACK_DAYS", 3),
        )
    except ImapUnavailableError as exc:
        s.pix_email_ultimo_erro = str(exc)[:500]
        s.pix_email_ultimo_erro_em = now_sp()
        db.session.commit()
        log.warning("[pix-email] caixa indisponível: %s", exc)
        return {"ativo": True, "erro": str(exc)}
    if s.pix_email_ultimo_erro:
        s.pix_email_ultimo_erro = None
        s.pix_email_ultimo_erro_em = None
        db.session.commit()
    contagem = processar_brutos(brutos)
    contagem["religados"] = reavaliar_pendentes()
    estado = ImportState.query.filter_by(key=CHAVE_RODADA).first()
    if estado is not None:
        estado.last_import_count = contagem["novos"]
        db.session.commit()
    contagem["ativo"] = True
    return contagem


def saude() -> dict:
    """Para a faixa da tela: a leitura está viva? (contrato `GET /api/pix/saude`)."""
    s = db.session.get(SiteSetting, 1)
    estado = ImportState.query.filter_by(key=CHAVE_RODADA).first()
    ultima = estado.last_checked_at if estado else None  # UTC
    desde = now_sp() - timedelta(days=PIX_SAUDE_JANELA_DIAS)
    janela = PixRecebido.query.filter(PixRecebido.recebido_em >= desde)
    lidos = janela.count()
    nao_entendidos = janela.filter(PixRecebido.estado == PIX_ESTADO_NAO_ENTENDIDO).count()
    sem_conta = janela.filter(
        PixRecebido.conta_id.is_(None), PixRecebido.numero_conta_lido.isnot(None)
    ).count()
    contas = [
        apelido
        for (apelido,) in db.session.query(ContaRecebimento.apelido)
        .join(PixRecebido, PixRecebido.conta_id == ContaRecebimento.id)
        .filter(PixRecebido.recebido_em >= desde)
        .group_by(ContaRecebimento.apelido)
        .order_by(func.min(ContaRecebimento.id))
    ]
    ativo = bool(s and s.pix_email_ativo)
    alerta = None
    if ativo and s.pix_email_ultimo_erro:
        alerta = "erro"
    elif ativo and (ultima is None or datetime.utcnow() - ultima > timedelta(minutes=PIX_SAUDE_PARADA_MIN)):
        alerta = "parada"
    return {
        "ativo": ativo,
        "ativo_desde": s.pix_email_ativo_desde.isoformat(timespec="seconds")
        if s and s.pix_email_ativo_desde
        else None,
        "ultima_leitura": (ultima.isoformat(timespec="seconds") + "Z") if ultima else None,
        "lidos_7d": lidos,
        "nao_entendidos_7d": nao_entendidos,
        "conta_nao_cadastrada_7d": sem_conta,
        "contas_vistas_7d": contas,
        "ultimo_erro": s.pix_email_ultimo_erro if s else None,
        "alerta": alerta,
    }
