"""Relógio das tabelas de Conversas: UTC naive (features 325 e 328).

Mora num módulo próprio porque `equipe_ops` precisa dele e não pode importar `aviso_ops`: é o
`aviso_ops` que importa `equipe_ops` (abrir e encerrar a espera), e o import de volta fecharia um
ciclo. Os importadores da 325 seguem lendo `aviso_ops.agora_utc`, que é este mesmo objeto.
"""

from __future__ import annotations

from datetime import UTC, datetime


def agora_utc() -> datetime:
    """Relógio destas tabelas: UTC naive (como ``Client.created_at``)."""
    return datetime.now(UTC).replace(tzinfo=None)
