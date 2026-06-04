"""comissao padrao 2% -> 2,5% (correcao do valor salvo)

Revision ID: h4b5c6d7e8f9
Revises: g3a4b5c6d7e8
Create Date: 2026-06-04

Migration de DADOS (autogenerate quebrado): corrige a taxa padrao de comissao no
SiteSetting de 2.0 (valor errado) / NULL para 2.5. Não altera taxas próprias de
eventos (essas ficam intactas).
"""
from alembic import op

revision = "h4b5c6d7e8f9"
down_revision = "g3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE site_settings SET default_commission_rate = 2.5 "
        "WHERE default_commission_rate IS NULL OR default_commission_rate = 2.0"
    )


def downgrade():
    op.execute(
        "UPDATE site_settings SET default_commission_rate = 2.0 "
        "WHERE default_commission_rate = 2.5"
    )
