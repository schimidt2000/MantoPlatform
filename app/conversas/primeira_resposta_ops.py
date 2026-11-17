"""O tempo da primeira resposta de cada conversa (feature 349, FR-001 a FR-005).

A conversa guarda a primeira mensagem da cliente (sem contar reação) e a primeira resposta da equipe depois dela:
a hora, quem respondeu e por onde (``plataforma``, ``celular``, ``outro``). O eco do app do celular e o de outro app
do Instagram chegam SEM autor (limite da coexistência): ficam gravados assim, e a tela mostra o caso.

As gravações são UPDATEs condicionais no banco (como a espera da 328): dois workers processando avisos ao mesmo
tempo não fazem "último ganha". A resposta que a Meta recusar depois do aceite, e a primeira mensagem que andar para
trás (aviso reprocessado atrasado), recalculam pelas mensagens com a régua de resposta válida da espera.

Camada de baixo do domínio, como ``equipe_ops`` (que a chama): importa só modelos, constantes e ``db``. Não comita:
roda dentro da transação de quem gravou a mensagem.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, text

from app import db
from app.conversas import constantes as K
from app.models import Conversa, ConversaMensagem

# A primeira mensagem só anda para trás (a mensagem atrasada pela varredura pode ser a mais antiga).
_GRAVAR_PRIMEIRA_MENSAGEM = text(
    "UPDATE conversas SET primeira_recebida_em = :momento "
    "WHERE id = :id AND (primeira_recebida_em IS NULL OR primeira_recebida_em > :momento)"
)
# A primeira resposta só se grava uma vez e nunca antes da primeira mensagem dela.
_GRAVAR_PRIMEIRA_RESPOSTA = text(
    "UPDATE conversas SET primeira_resposta_em = :momento, primeira_resposta_por_id = :autor, "
    "primeira_resposta_origem = :origem "
    "WHERE id = :id AND primeira_resposta_em IS NULL "
    "AND primeira_recebida_em IS NOT NULL AND primeira_recebida_em <= :momento"
)
_CAMPOS = (
    "primeira_recebida_em",
    "primeira_resposta_em",
    "primeira_resposta_por_id",
    "primeira_resposta_origem",
    "primeira_resposta_por",
)
# Só o envio que a Meta aceitou conta (o `pendente` ainda pode falhar).
_SITUACOES_QUE_VALEM = (K.SITUACAO_ENVIADA, K.SITUACAO_ENTREGUE, K.SITUACAO_LIDA)


def registrar_contato(conversa: Conversa, momento: datetime) -> None:
    """A cliente escreveu (não é reação): a primeira mensagem é a mais antiga. Não comita.

    Se a primeira mensagem andou para trás e já havia primeira resposta, recalcula: a resposta gravada pode ter
    sido dada antes da mensagem que acabou de chegar atrasada.
    """
    if conversa.primeira_recebida_em is not None and conversa.primeira_recebida_em <= momento:
        return
    resultado = db.session.execute(
        _GRAVAR_PRIMEIRA_MENSAGEM, {"momento": momento, "id": conversa.id}
    )
    db.session.expire(conversa, list(_CAMPOS))
    if resultado.rowcount and conversa.primeira_resposta_em is not None:
        recalcular(conversa)


def registrar_resposta(
    conversa: Conversa, momento: datetime, autor_id: int | None, origem: str
) -> None:
    """A equipe respondeu (envio aceito, eco do celular ou de outro app). Grava se for a primeira. Não comita."""
    if conversa.primeira_resposta_em is not None:
        return
    db.session.execute(
        _GRAVAR_PRIMEIRA_RESPOSTA,
        {"momento": momento, "autor": autor_id, "origem": origem, "id": conversa.id},
    )
    db.session.expire(conversa, list(_CAMPOS))


def _resposta_valida():
    """A régua da espera (328) restrita ao que a Meta aceitou: sem falha, sem reação, sem "apagada/editada"."""
    falsas = (K.TEXTO_APAGADA_NO_CELULAR, K.TEXTO_EDITADA_NO_CELULAR)
    return and_(
        ConversaMensagem.direcao == K.ENVIADA,
        ConversaMensagem.situacao.in_(_SITUACOES_QUE_VALEM),
        ConversaMensagem.tipo != K.TIPO_REACAO,
        or_(
            ConversaMensagem.origem != K.ORIGEM_CELULAR,
            ConversaMensagem.texto.is_(None),
            ConversaMensagem.texto.notin_(falsas),
        ),
    )


def recalcular(conversa: Conversa) -> None:
    """Refaz a primeira resposta pelas mensagens (falha depois do aceite, mensagem atrasada). Não comita."""
    db.session.flush()
    inicio = conversa.primeira_recebida_em
    primeira = None
    if inicio is not None:
        primeira = (
            ConversaMensagem.query.filter(
                ConversaMensagem.conversa_id == conversa.id,
                ConversaMensagem.momento >= inicio,
                _resposta_valida(),
            )
            .order_by(ConversaMensagem.momento, ConversaMensagem.id)
            .first()
        )
    conversa.primeira_resposta_em = primeira.momento if primeira else None
    conversa.primeira_resposta_por_id = primeira.autor_id if primeira else None
    conversa.primeira_resposta_origem = primeira.origem if primeira else None


def minutos(conversa: Conversa) -> int | None:
    """Os minutos inteiros entre a primeira mensagem e a primeira resposta, ou ``None``."""
    if conversa.primeira_recebida_em is None or conversa.primeira_resposta_em is None:
        return None
    return max(
        0,
        int((conversa.primeira_resposta_em - conversa.primeira_recebida_em).total_seconds() // 60),
    )
