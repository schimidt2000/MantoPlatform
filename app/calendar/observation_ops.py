"""Operações sobre as observações do evento como fonte única de lógica (feature 150).

Segue o mesmo padrão de `casting_ops.py`/`event_ops.py` (features 146–149): o núcleo de cada
ação mora aqui, com parâmetros explícitos (sem `request.form`, `flash` ou `current_user`), para
ser reusado por DOIS adaptadores finos — o handler Jinja (`app/calendar/routes.py`) e o endpoint
JSON (`app/api/agenda_write.py`). UMA implementação da regra, zero divergência (Princípio I).

Uma observação (`EventObservation`) é um bloco anexado ao evento: texto, link ou imagem. O
upload da imagem (multipart) permanece no adaptador Jinja — o núcleo recebe `file_path` já
resolvido, mantendo a dependência unidirecional `routes → observation_ops` (este módulo só
importa `models`, nunca `routes` — sem ciclo de import).
"""

from typing import Any

from app.models import EventObservation, db


def add_observation(
    event: Any,
    *,
    obs_type: str,
    content: str | None = None,
    label: str | None = None,
    file_path: str | None = None,
) -> EventObservation | None:
    """Cria uma observação do evento a partir de valores já resolvidos.

    Aplica a mesma validação do loop do handler Jinja: observação de imagem exige `file_path`;
    de texto/link exige `content` não-vazio; tipo desconhecido é ignorado. Quando a observação é
    válida, ela é adicionada à sessão (sem commit — o chamador commita, preservando "um commit por
    requisição"); quando deve ser ignorada, retorna `None` sem tocar na sessão.

    Args:
        event: Evento dono da observação.
        obs_type: Tipo da observação (`"text"`, `"link"` ou `"image"`).
        content: Texto ou URL (obrigatório para texto/link; ignorado para imagem).
        label: Rótulo/descrição opcional.
        file_path: Caminho público do arquivo (`/uploads/...`), obrigatório para imagem.

    Returns:
        A observação criada (ainda não commitada), ou `None` se o item deve ser ignorado
        (texto/link sem conteúdo, imagem sem arquivo, tipo desconhecido).
    """
    content = (content or "").strip() or None
    label = (label or "").strip() or None

    if obs_type == "image":
        if not file_path:
            return None
    elif obs_type in ("text", "link"):
        if not content:
            return None
    else:
        return None

    obs = EventObservation(
        event_id=event.id,
        obs_type=obs_type,
        content=content,
        file_path=file_path,
        label=label,
    )
    db.session.add(obs)
    return obs


def delete_observation(event: Any, obs_id: int) -> bool:
    """Remove uma observação escopada ao evento (paridade com o `first_or_404` do Jinja).

    Args:
        event: Evento dono da observação.
        obs_id: Id da observação a remover.

    Returns:
        `True` se a observação existia (foi removida e commitada); `False` se não pertence ao
        evento ou não existe — o adaptador Jinja transforma em `abort(404)`, a API em 404.
    """
    obs = EventObservation.query.filter_by(id=obs_id, event_id=event.id).first()
    if obs is None:
        return False
    db.session.delete(obs)
    db.session.commit()
    return True
