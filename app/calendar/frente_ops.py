"""A frente de negócio do evento (feature 348): a única leitura, em Python e em SQL."""

from __future__ import annotations

from typing import Any

SOCIAL_REGEX = "(15 anos|debut|casamento|noiv|bodas)"


class FrenteInvalida(ValueError):
    """A frente pedida não é uma das frentes, ou faltou na venda."""


def sugestao(titulo: str | None, event_type: str | None) -> tuple[str, bool]:
    raise NotImplementedError


def frente_do_evento(event: Any) -> dict[str, Any]:
    raise NotImplementedError


def frente_sql() -> Any:
    raise NotImplementedError
