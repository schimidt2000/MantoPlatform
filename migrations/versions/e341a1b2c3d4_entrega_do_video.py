"""Data de entrega dos vídeos da campanha virtual (feature 341).

Uma coluna nula em ``virtual_campaigns``: ``recorded_delivery_until``. Preenchida, todo vídeo vendido
até ela tem essa data como prazo; nula, vale o prazo em dias de antes. Sem backfill.

Aditiva: o código anterior não lê a coluna. Rollback = reverter o merge; o ``downgrade`` só derruba a
coluna.

Revision ID: e341a1b2c3d4
Revises: e340c1a2b3d4
Create Date: 2026-11-10
"""

import sqlalchemy as sa
from alembic import op

revision = "e341a1b2c3d4"
down_revision = "e340c1a2b3d4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("virtual_campaigns") as batch:
        batch.add_column(sa.Column("recorded_delivery_until", sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table("virtual_campaigns") as batch:
        batch.drop_column("recorded_delivery_until")
