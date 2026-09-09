"""Recados que as clientes escrevem na página da tag NFC (feature 297).

Núcleo puro, sem `flask.request`. Fica separado de `nfc_ops.py` de propósito: aquele arquivo já
passa de 500 linhas e trata de outro assunto (a tag, o código eterno, a entrega de vídeo). Aqui só
mora a via de volta — a primeira vez que o presente deixa de ser um monólogo.

DECISÃO DE PRIVACIDADE: guarda-se o texto e um nome opcional. Nada de e-mail, telefone, IP ou
impressão do navegador. É a menor superfície de dado pessoal que ainda cumpre o pedido; o controle
de abuso é o limite de taxa da rota pública, que o flask-limiter faz em memória sem persistir nada.

DECISÃO DE SEGURANÇA: recado enviado a código inexistente ou a tag desativada **não é gravado, e
mesmo assim a resposta é de sucesso**. É a mesma indistinguibilidade que a leitura garante desde a
feature 255 (SC-006): se um código errado respondesse diferente, a rota viraria um oráculo que diz
quais códigos existem — e o sufixo de seis caracteres é, na prática, um token de acesso.
"""

import logging
from typing import Any

from sqlalchemy import func

from app import db
from app.constants import NFC_MENSAGEM_AUTOR_MAX_CHARS, NFC_MENSAGEM_MAX_CHARS
from app.impressoes3d.nfc_ops import NfcValidationError
from app.models import NfcTag, NfcTagMessage

logger = logging.getLogger(__name__)


def registrar_recado(
    raw_code: str, *, message: str, author_name: str | None = None
) -> NfcTagMessage | None:
    """Grava o recado de uma visitante, se a tag existir e estiver ativa.

    Args:
        raw_code: o código lido da URL, como veio.
        message: o texto do recado.
        author_name: como a pessoa quis se identificar; opcional.

    Returns:
        O recado gravado, ou `None` quando o código não corresponde a uma tag ativa — caso em que
        nada é gravado e quem chama ainda assim responde sucesso (ver a decisão no topo do módulo).

    Raises:
        NfcValidationError: texto vazio ou acima do limite. A validação vem ANTES da resolução do
            código de propósito: um recado vazio é erro de preenchimento em qualquer caso, e
            responder 400 aqui não revela nada sobre a existência do código.
    """
    texto = (message or "").strip()
    if not texto:
        raise NfcValidationError("message", "Escreva sua mensagem antes de enviar.")
    if len(texto) > NFC_MENSAGEM_MAX_CHARS:
        raise NfcValidationError(
            "message",
            f"Sua mensagem passou de {NFC_MENSAGEM_MAX_CHARS} caracteres. "
            f"Conte em menos palavras, por favor.",
        )
    autor = (author_name or "").strip()[:NFC_MENSAGEM_AUTOR_MAX_CHARS] or None

    code = (raw_code or "").strip().upper()
    tag = NfcTag.query.filter_by(code=code).first() if code else None
    if tag is None or not tag.is_active:
        return None

    recado = NfcTagMessage(
        tag_id=tag.id,
        # Fotografia do vínculo AGORA: a tag pode ser reassociada amanhã, e o recado pertence a
        # quem o recebeu hoje.
        client_id=tag.client_id,
        author_name=autor,
        message=texto,
    )
    db.session.add(recado)
    db.session.commit()
    return recado


def listar_recados(tag_id: int) -> list[NfcTagMessage]:
    """Recados de uma tag, do mais novo para o mais antigo."""
    return (
        NfcTagMessage.query.filter_by(tag_id=tag_id)
        .order_by(NfcTagMessage.created_at.desc(), NfcTagMessage.id.desc())
        .all()
    )


def marcar_lidos(tag_id: int) -> int:
    """Marca como lidos os recados ainda não lidos de uma tag. Devolve quantos mudaram."""
    from datetime import datetime

    quantidade = (
        NfcTagMessage.query.filter(
            NfcTagMessage.tag_id == tag_id, NfcTagMessage.read_at.is_(None)
        ).update({"read_at": datetime.utcnow()}, synchronize_session=False)
    )
    db.session.commit()
    return quantidade or 0


def contagens_por_tag() -> dict[int, dict[str, int]]:
    """Total e não lidos de recados, por tag, numa consulta só.

    A lista de gestão mostra o selo de recados em cada card; sem isto seriam 35 requisições para
    desenhar uma tela.
    """
    linhas = (
        db.session.query(
            NfcTagMessage.tag_id,
            func.count(NfcTagMessage.id),
            func.count(NfcTagMessage.id).filter(NfcTagMessage.read_at.is_(None)),
        )
        .group_by(NfcTagMessage.tag_id)
        .all()
    )
    return {tag_id: {"total": total, "nao_lidos": nao_lidos} for tag_id, total, nao_lidos in linhas}


def serializar(recado: NfcTagMessage) -> dict[str, Any]:
    """Recado no formato que o ERP consome."""
    return {
        "id": recado.id,
        "message": recado.message,
        "author_name": recado.author_name,
        "created_at": recado.created_at.isoformat() if recado.created_at else None,
        "read_at": recado.read_at.isoformat() if recado.read_at else None,
    }
