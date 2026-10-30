"""Varredura do WhatsApp: refaz avisos e mídias que ficaram pelo caminho (feature 325, research R3/R5).

Roda pela thread ``_start_whatsapp_sweep`` (``app/__init__.py``, atrás de ``MANTO_SEM_THREADS``) e
pelo comando ``flask whatsapp-reprocessar``. Sem lock de ciclo: o claim é por linha, então os 3
workers podem varrer juntos sem processar a mesma linha duas vezes.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app import db
from app.conversas import aviso_ops, midia_ops
from app.conversas import constantes as K
from app.conversas.aviso_ops import agora_utc
from app.conversas.configuracao import cfg_whatsapp

logger = logging.getLogger(__name__)


def avisos_a_refazer(limite: int = K.VARREDURA_LOTE) -> list[int]:
    """Pendentes há mais de 30 s (o processamento da hora não pegou) e processando parados."""
    agora = agora_utc()
    linhas = db.session.execute(
        text(
            "SELECT id FROM whatsapp_avisos "
            "WHERE (estado = :pend AND recebido_em < :espera) "
            "OR (estado = :proc AND tentado_em < :preso) "
            "ORDER BY id LIMIT :limite"
        ),
        {
            "pend": K.AVISO_PENDENTE,
            "proc": K.AVISO_PROCESSANDO,
            "espera": agora - K.VARREDURA_ESPERA,
            "preso": agora - K.PROCESSANDO_PRESO,
            "limite": limite,
        },
    ).fetchall()
    return [linha[0] for linha in linhas]


def reprocessar_avisos(limite: int = K.VARREDURA_LOTE) -> dict[str, int]:
    """Refaz os avisos parados. Devolve a contagem por estado final."""
    cfg = cfg_whatsapp()
    resumo = {"processados": 0, "pendentes": 0, "descartados": 0}
    for aviso_id in avisos_a_refazer(limite):
        estado = aviso_ops.processar_aviso(aviso_id, cfg)
        if estado == K.AVISO_PROCESSADO:
            resumo["processados"] += 1
        elif estado == K.AVISO_PENDENTE:
            resumo["pendentes"] += 1
        elif estado == K.AVISO_DESCARTADO:
            resumo["descartados"] += 1
    return resumo


def reprocessar_midias(limite: int = K.VARREDURA_LOTE) -> dict[str, int]:
    """Retenta as mídias pendentes. Devolve a contagem por estado final."""
    cfg = cfg_whatsapp()
    ids = [
        linha[0]
        for linha in db.session.execute(
            text(
                "SELECT id FROM conversa_midias WHERE estado = :pend "
                f"AND {midia_ops.PRONTA_PARA_TENTAR} ORDER BY id LIMIT :limite"
            ),
            {
                "pend": K.MIDIA_PENDENTE,
                "agora": agora_utc(),
                "teto_min": midia_ops.TETO_DO_ESPACAMENTO_MIN,
                "limite": limite,
            },
        ).fetchall()
    ]
    resumo = {"guardadas": 0, "pendentes": 0, "falharam": 0}
    for midia_id in ids:
        estado = midia_ops.baixar_e_guardar(midia_id, cfg)
        if estado == K.MIDIA_GUARDADA:
            resumo["guardadas"] += 1
        elif estado == K.MIDIA_PENDENTE:
            resumo["pendentes"] += 1
        elif estado == K.MIDIA_FALHOU:
            resumo["falharam"] += 1
    return resumo


def ciclo_de_varredura() -> dict[str, int]:
    """Uma passada completa; cada rotina isolada (a falha de uma não impede a outra)."""
    resumo: dict[str, int] = {}
    for rotina in (reprocessar_avisos, reprocessar_midias):
        try:
            resumo.update(rotina())
        except Exception as exc:  # noqa: BLE001 — a próxima passada tenta de novo
            db.session.rollback()
            logger.warning("[whatsapp-sweep] %s falhou: %s", rotina.__name__, exc)
    return resumo
