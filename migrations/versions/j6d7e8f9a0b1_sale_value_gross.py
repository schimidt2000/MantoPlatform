"""sale_value_gross em calendar_events (valor antes do desconto)

Revision ID: j6d7e8f9a0b1
Revises: i5c6d7e8f9a0
Create Date: 2026-06-09

Adiciona a coluna `sale_value_gross` (Numeric, nullable) em calendar_events:
o valor antes do desconto (preço cheio). O desconto concedido é a diferença
para `sale_value` (valor final). Usado em relatórios financeiros futuros.

Migration escrita à mão (autogenerate quebrado por drift pré-existente).
"""
from alembic import op
import sqlalchemy as sa

revision = "j6d7e8f9a0b1"
down_revision = "i5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("calendar_events") as batch_op:
        batch_op.add_column(sa.Column("sale_value_gross", sa.Numeric(12, 2), nullable=True))


def downgrade():
    with op.batch_alter_table("calendar_events") as batch_op:
        batch_op.drop_column("sale_value_gross")
