"""orcamento_history.total_3h — duração de 3 horas na calculadora (feature 098)

Revision ID: c5f6a7b8d9e0
Revises: b4e5f6a7c8d9
Create Date: 2026-07-01

Adiciona a coluna orcamento_history.total_3h (nullable) para armazenar o total da duração de 3 horas ao
lado de total_1h/2h/4h. Orçamentos antigos ficam com total_3h = NULL.

Migration escrita a mão (autogenerate quebrado por drift pré-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "c5f6a7b8d9e0"
down_revision = "b4e5f6a7c8d9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "orcamento_history",
        sa.Column("total_3h", sa.Numeric(precision=10, scale=2), nullable=True),
    )


def downgrade():
    op.drop_column("orcamento_history", "total_3h")
