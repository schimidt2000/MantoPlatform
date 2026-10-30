"""Mídia das conversas: baixar a recebida e guardar a enviada (feature 325, FR-007, research R6/R7).

A mídia mora em ``CONVERSAS_MEDIA_FOLDER`` (irmã de ``uploads``, nunca bucket público) e só sai por
``GET /api/conversas/midia/<id>``. O id da Meta vale 7 dias; a url de download, 5 minutos — por isso
cada tentativa pede uma url nova. A gravação da mensagem nunca depende do download: a mídia nasce
``pendente`` e a varredura retenta.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import timedelta

from sqlalchemy import text

from app import db
from app.conversas import constantes as K
from app.conversas.aviso_ops import agora_utc
from app.conversas.configuracao import CfgWhatsapp
from app.integracoes import whatsapp_client as wc
from app.models import ConversaMidia

logger = logging.getLogger(__name__)

# Espaçamento entre tentativas de download: 1, 2, 4, 8… minutos, até 60. Com a Meta fora do ar
# ou o token vencido por algumas horas, a mídia continua pendente (o id da Meta vale 7 dias) em
# vez de esgotar 10 tentativas em minutos; só a IDADE (48 h) a dá por perdida (research R6).
TETO_DO_ESPACAMENTO_MIN = 60
IDADE_MAXIMA = timedelta(hours=48)
# Condição SQL "já pode tentar de novo" (usada no claim e na varredura — uma regra só).
PRONTA_PARA_TENTAR = (
    "(tentado_em IS NULL OR tentado_em < :agora - make_interval("
    "mins => LEAST(power(2, GREATEST(tentativas - 1, 0))::int, :teto_min)))"
)


def _reivindicar(midia_id: int) -> bool:
    """Claim atômico da mídia: uma tentativa por vez, e não antes do espaçamento."""
    resultado = db.session.execute(
        text(
            "UPDATE conversa_midias SET tentativas = tentativas + 1, tentado_em = :agora "
            f"WHERE id = :id AND estado = :pend AND {PRONTA_PARA_TENTAR}"
        ),
        {
            "agora": agora_utc(),
            "teto_min": TETO_DO_ESPACAMENTO_MIN,
            "pend": K.MIDIA_PENDENTE,
            "id": midia_id,
        },
    )
    db.session.commit()
    return bool(resultado.rowcount)


def guardar_bytes(dados: bytes, mime: str | None, cfg: CfgWhatsapp) -> str:
    """Grava os bytes em ``AAAA/MM/<uuid>.<ext>`` dentro da pasta da mídia e devolve o relativo."""
    agora = agora_utc()
    extensao = K.EXTENSAO_DO_MIME.get((mime or "").split(";")[0].strip(), ".bin")
    relativo = f"{agora:%Y}/{agora:%m}/{uuid.uuid4().hex}{extensao}"
    destino = os.path.join(cfg.pasta_midia, *relativo.split("/"))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "wb") as arquivo:
        arquivo.write(dados)
    return relativo


def caminho_absoluto(midia: ConversaMidia, cfg: CfgWhatsapp) -> str | None:
    """O arquivo da mídia no disco, ou ``None`` se não está guardado (ou o caminho escapa da pasta)."""
    if midia.estado != K.MIDIA_GUARDADA or not midia.caminho or not cfg.pasta_midia:
        return None
    raiz = os.path.realpath(cfg.pasta_midia)
    destino = os.path.realpath(os.path.join(raiz, *midia.caminho.split("/")))
    if not destino.startswith(raiz + os.sep) or not os.path.isfile(destino):
        return None
    return destino


def _falhar(midia: ConversaMidia, erro: str, definitivo: bool) -> str:
    velha = midia.created_at < agora_utc() - IDADE_MAXIMA
    midia.erro = erro[: K.ERRO_MAXIMO]
    midia.estado = K.MIDIA_FALHOU if (definitivo or velha) else K.MIDIA_PENDENTE
    db.session.commit()
    return midia.estado


def baixar_e_guardar(midia_id: int, cfg: CfgWhatsapp) -> str:
    """Baixa a mídia recebida e a guarda. Nunca levanta; devolve o estado em que a mídia ficou."""
    if not _reivindicar(midia_id):
        return "ignorada"
    midia = db.session.get(ConversaMidia, midia_id)
    try:
        info = wc.consultar_midia(cfg.conexao, midia.externo_id)
        dados = wc.baixar_midia(cfg.conexao, info["url"], K.MIDIA_TETO_BYTES)
        mime = info.get("mime_type") or midia.mime
        midia.caminho = guardar_bytes(dados, mime, cfg)
    except wc.WhatsappArquivoGrande:
        return _falhar(midia, K.MOTIVO_ARQUIVO_GRANDE, definitivo=True)
    except (wc.WhatsappErro, OSError) as exc:
        logger.info(
            "[whatsapp] mídia %s não baixou (tentativa %s): %s", midia_id, midia.tentativas, exc
        )
        return _falhar(midia, f"{type(exc).__name__}: {exc}", definitivo=False)
    midia.mime = mime
    midia.tamanho = len(dados)
    midia.estado = K.MIDIA_GUARDADA
    midia.erro = None
    db.session.commit()
    return K.MIDIA_GUARDADA
