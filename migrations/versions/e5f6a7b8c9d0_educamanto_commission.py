"""Comissão EducaManto (feature 109).

- site_settings.educamanto_seller_id: responsável EducaManto (beneficiário das comissões
  de eventos "(EDU…"); backfill para o usuário gabriel@mantoproducoes.com.br se existir.
- commission_payments.payable_from: data da realização do evento — comissões EducaManto só
  entram no ciclo de pagamento a partir dela (NULL = comissão comum, ciclo pela sale_date).

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-07-06
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "site_settings",
        sa.Column("educamanto_seller_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("commission_payments", sa.Column("payable_from", sa.Date(), nullable=True))
    # Backfill idempotente: aponta para o Gabriel Lara se o usuário existir (senão fica NULL).
    op.execute(
        "UPDATE site_settings SET educamanto_seller_id = "
        "(SELECT id FROM users WHERE email = 'gabriel@mantoproducoes.com.br' LIMIT 1) "
        "WHERE educamanto_seller_id IS NULL"
    )


def downgrade():
    op.drop_column("commission_payments", "payable_from")
    op.drop_column("site_settings", "educamanto_seller_id")
