"""modo anônimo total das avaliações: site_settings.ratings_fully_anonymous

Revision ID: s5b6c7d8e9f0
Revises: r4a5b6c7d8e9
Create Date: 2026-06-17

Adiciona:
- site_settings.ratings_fully_anonymous (Boolean, NOT NULL, server_default "0"):
  quando True, a autoria dos comentários na página de avaliações fica oculta até
  para o super admin (feature 056). Nasce desligado, preservando o comportamento
  atual (super admin vê o autor).

Migration escrita à mão (autogenerate quebrado por drift pré-existente).
"""
from alembic import op
import sqlalchemy as sa

revision = "s5b6c7d8e9f0"
down_revision = "r4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "ratings_fully_anonymous",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade():
    with op.batch_alter_table("site_settings", schema=None) as batch_op:
        batch_op.drop_column("ratings_fully_anonymous")
