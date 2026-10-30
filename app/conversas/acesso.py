"""Quem usa Conversas (feature 325): COMERCIAL e SUPERADMIN — Princípio XIII.

Uma fonte só para o gate dos endpoints e para a flag ``conversas_ligadas`` do ``/api/auth/me``.
Lê os papéis REAIS (``user.roles``), como as cópias de ``_has_role`` de ``app/api/``: o "Ver como"
não abre a caixa de conversas de ninguém.
"""

from __future__ import annotations

from typing import Any

from app.constants import RoleName

PAPEIS_DE_CONVERSAS = (RoleName.COMERCIAL, RoleName.SUPERADMIN)


def pode_conversas(user: Any) -> bool:
    """O usuário tem papel para ler e responder as conversas?"""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    permitidos = {papel.upper() for papel in PAPEIS_DE_CONVERSAS}
    return any((papel.name or "").upper() in permitidos for papel in user.roles)
