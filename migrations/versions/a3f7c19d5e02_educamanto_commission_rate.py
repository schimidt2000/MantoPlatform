"""% da comissão EducaManto vira configuração (feature 223).

`site_settings.educamanto_commission_rate`: a taxa do responsável EducaManto sobre o lucro do
evento era a constante `EDUCAMANTO_COMMISSION_RATE = 5` no código. Mudar o acordo exigia deploy.
NULL mantém o padrão de 5%, então a migração não altera nenhum cálculo existente.

Revision ID: a3f7c19d5e02
Revises: c5d92fa16e34
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op

revision = "a3f7c19d5e02"
down_revision = "c5d92fa16e34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_settings",
        sa.Column("educamanto_commission_rate", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("site_settings", "educamanto_commission_rate")
