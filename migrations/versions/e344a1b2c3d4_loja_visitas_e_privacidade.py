"""loja: contagem de visitas, aceite de novidades e pixel da Meta (feature 344)

Aditiva. Uma tabela nova (`virtual_campaign_visits`, contador anônimo por campanha + dia + origem)
e colunas nulas em `virtual_orders` (origem, nome de quem compra, aceite), `clients` (aceite) e
`site_settings` (ID do pixel). Nenhum dado existente muda.

Revision ID: e344a1b2c3d4
Revises: f310b2a4c6e8
Create Date: 2026-11-16
"""

import sqlalchemy as sa
from alembic import op

revision = "e344a1b2c3d4"
down_revision = "f310b2a4c6e8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "virtual_campaign_visits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey("virtual_campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("origem", sa.String(length=20), nullable=False),
        sa.Column("visits", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "campaign_id", "day", "origem", name="uq_virtual_visit_campaign_day_origem"
        ),
    )

    with op.batch_alter_table("virtual_orders") as batch:
        batch.add_column(sa.Column("buyer_name", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("marketing_opt_in_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("marketing_opt_in_version", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("origem", sa.String(length=20), nullable=True))

    with op.batch_alter_table("clients") as batch:
        batch.add_column(sa.Column("marketing_opt_in_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("marketing_opt_in_source", sa.String(length=160), nullable=True))

    with op.batch_alter_table("site_settings") as batch:
        batch.add_column(sa.Column("meta_pixel_id", sa.String(length=30), nullable=True))


def downgrade():
    with op.batch_alter_table("site_settings") as batch:
        batch.drop_column("meta_pixel_id")
    with op.batch_alter_table("clients") as batch:
        batch.drop_column("marketing_opt_in_source")
        batch.drop_column("marketing_opt_in_at")
    with op.batch_alter_table("virtual_orders") as batch:
        batch.drop_column("origem")
        batch.drop_column("marketing_opt_in_version")
        batch.drop_column("marketing_opt_in_at")
        batch.drop_column("buyer_name")
    op.drop_table("virtual_campaign_visits")
