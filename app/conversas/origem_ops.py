"""De qual conversa e de qual contato veio cada venda (feature 348)."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class ConversaNaoEncontrada(ValueError):
    """A conversa informada para a venda não existe."""


def contato_de_origem(conversa_id: int, momento: datetime | None = None) -> Any:
    raise NotImplementedError


def ligar_orcamento(entry: Any, conversa: Any) -> bool:
    raise NotImplementedError


def ligar_evento(event: Any, conversa_id: Any) -> None:
    raise NotImplementedError


def origem_da_venda(event: Any, user: Any = None) -> dict[str, Any] | None:
    raise NotImplementedError
