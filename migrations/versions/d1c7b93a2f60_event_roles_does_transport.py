"""Carrinho de transporte no casting: `event_roles.does_transport` (feature 239).

Marcador por integrante — "esta pessoa leva um veículo neste evento fora de SP". Mesma
semântica de `needs_makeup`/`is_singer`: ``True`` ou ``NULL`` (nunca ``False``), coluna
booleana nullable sem default.

A coluna NÃO guarda dinheiro. O valor do transporte é a parcela de UM veículo recalculada do
orçamento do evento (`casting_ops.valor_transporte_papel`) e entra apenas como acréscimo ao
TETO do cachê em `assign_role` — o que se paga continua sendo um número só em `cache_value`,
então planilha de pagamentos, custo do evento, KPI e DRE seguem sem qualquer mudança.

Revision ID: d1c7b93a2f60
Revises: c8f4d92e17ab
Create Date: 2026-08-18
"""

import sqlalchemy as sa
from alembic import op

revision = "d1c7b93a2f60"
down_revision = "c8f4d92e17ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("event_roles", sa.Column("does_transport", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("event_roles", "does_transport")
