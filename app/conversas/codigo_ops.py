"""O código do site (feature 348): o clique de campanha que chega à conversa pela mensagem pronta."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class SemMarcador(ValueError):
    """O pedido de código não trouxe nenhum marcador de campanha."""


def criar_codigo(marcadores: dict[str, Any]) -> Any:
    raise NotImplementedError


def anexar_a_mensagem(mensagem: str, codigo: Any, form_response_id: int | None = None) -> str:
    raise NotImplementedError


def ler_na_mensagem(conversa: Any, texto: str | None, momento: datetime) -> list[int]:
    raise NotImplementedError
