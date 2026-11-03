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


def e_da_equipe(user: Any) -> bool:
    """Pode receber conversa (transferência) e aviso: ativo, com acesso e com papel de conversas.

    ``has_access=False`` é a pessoa "só pagamento", sem login: não tem como atender.
    """
    if user is None or not user.is_active or not user.has_access:
        return False
    return pode_conversas(user)


def responsavel_ativo(conversa: Any) -> bool:
    """O responsável da conversa ainda é da equipe? Sem isso, qualquer um assume (FR-003) e o
    alerta da espera vai para a equipe toda."""
    return conversa.responsavel_id is not None and e_da_equipe(conversa.responsavel)
