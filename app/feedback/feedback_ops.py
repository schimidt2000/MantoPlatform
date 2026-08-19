"""Núcleo do feedback da cliente: as etiquetas e a regra de qual conjunto aparece por nota.

Funções puras — não importam `flask.request`, `render_template` nem `flash`.

Estes símbolos viviam em `app/feedback/routes.py` (o blueprint Jinja) e eram importados de lá pela
API React (`app/api/feedback_write.py`) e pelo CRM de clientes (`app/clientes/client_ops.py`).
Enquanto ficassem naquele arquivo, **apagar a superfície Jinja derrubaria a API viva** — a mesma
armadilha dos imports tardios de `calendar/routes.py`. Ficam aqui para que a remoção do Jinja seja
uma mudança de superfície, e não de regra de negócio.
"""

from __future__ import annotations

POSITIVE_TAGS = [
    "🎭 Atuação Impecável",
    "👗 Figurino Perfeito",
    "🤝 Interação com Convidados",
    "⏰ Pontualidade",
    "✨ Pura Magia",
]

ATTENTION_TAGS = [
    "⏰ Atraso",
    "👗 Figurino",
    "🎭 Atuação / Energia",
    "🗣️ Comunicação",
]

MAX_COMMENT_LENGTH = 2000


def tags_for_score(score: int) -> list[str]:
    """Etiquetas oferecidas para a nota dada: elogio em nota cheia, atenção no resto.

    Args:
        score: Nota de 1 a 5 dada pela cliente.

    Returns:
        A lista de etiquetas que a interface deve mostrar.
    """
    return POSITIVE_TAGS if score == 5 else ATTENTION_TAGS
