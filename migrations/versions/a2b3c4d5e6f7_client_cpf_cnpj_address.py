"""Cliente: CPF, CNPJ e endereço — cadastro mais completo (feature 119).

Revision ID: a2b3c4d5e6f7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-08
"""

import sqlalchemy as sa
from alembic import op

revision = "a2b3c4d5e6f7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clients", sa.Column("cpf", sa.String(length=20), nullable=True))
    op.add_column("clients", sa.Column("cnpj", sa.String(length=20), nullable=True))
    op.add_column("clients", sa.Column("address", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("clients", "address")
    op.drop_column("clients", "cnpj")
    op.drop_column("clients", "cpf")
