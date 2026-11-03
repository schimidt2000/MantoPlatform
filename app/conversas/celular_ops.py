"""O aviso no celular da mensagem nova da cliente (feature 332, FR-003/FR-004).

``processar_aviso`` chama ``avisar_mensagens`` depois do commit com as conversas que ganharam
mensagem da cliente neste aviso (eco, reação e reenvio não entram). O nome evita a confusão com o
``aviso_ops``, que é o aviso da Meta (webhook); aqui é o aviso que toca no celular da equipe.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from app.conversas.acesso import responsavel_ativo
from app.conversas.equipe_ops import membros_da_equipe
from app.conversas.leitura_ops import nome_da_conversa
from app.models import Conversa
from app.push import constantes as KP
from app.push import push_ops

logger = logging.getLogger(__name__)


def destinos_da_conversa(conversa: Conversa) -> list[int]:
    """O responsável, se ainda é da equipe; senão, a equipe inteira (research R3)."""
    if responsavel_ativo(conversa):
        return [conversa.responsavel_id]
    return [u.id for u in membros_da_equipe()]


def aviso_da_mensagem(conversa: Conversa) -> push_ops.Aviso:
    return push_ops.Aviso(
        titulo=nome_da_conversa(conversa),
        corpo=conversa.ultima_previa or "",
        link=f"/conversas?c={conversa.id}",
        tag=KP.tag_da_conversa(conversa.id),
        urgencia=KP.URGENCIA_MENSAGEM,
    )


def avisar_mensagens(conversa_ids: Iterable[int]) -> None:
    """Um aviso por conversa. Nunca levanta: o aviso da Meta já foi gravado e fechado (FR-006)."""
    ids = sorted(set(conversa_ids))
    if not ids:
        return
    try:
        for conversa in Conversa.query.filter(Conversa.id.in_(ids)).all():
            push_ops.despachar(destinos_da_conversa(conversa), aviso_da_mensagem(conversa))
    except Exception:  # noqa: BLE001
        logger.exception("[push] falha ao montar o aviso das conversas %s", ids)
