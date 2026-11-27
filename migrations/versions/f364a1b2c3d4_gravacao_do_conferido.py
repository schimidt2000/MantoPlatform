"""Gravação do conferido no catálogo (feature 364).

Aditiva: duas colunas nas tabelas da conferência (360), ambas nulas. ``gravado_em`` marca o item cujo
resultado já foi para o catálogo; ``catalog_character_id`` liga o personagem proposto ao personagem do
catálogo que ele gerou — é o que torna a gravação idempotente. Nenhum dado existente muda.

O ``downgrade`` derruba as duas colunas: os personagens já criados no catálogo continuam lá, só se perde
o registro de quem veio de onde.

Revision ID: f364a1b2c3d4
Revises: f360a1b2c3d4
Create Date: 2026-11-27
"""

import sqlalchemy as sa
from alembic import op

revision = "f364a1b2c3d4"
down_revision = "f360a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("catalog_conferencias", sa.Column("gravado_em", sa.DateTime(), nullable=True))
    op.add_column(
        "catalog_conferencia_personagens",
        sa.Column(
            "catalog_character_id",
            sa.Integer(),
            sa.ForeignKey(
                "catalog_characters.id",
                name="fk_catalog_conferencia_personagens_catalog_character_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_constraint(
        "fk_catalog_conferencia_personagens_catalog_character_id",
        "catalog_conferencia_personagens",
        type_="foreignkey",
    )
    op.drop_column("catalog_conferencia_personagens", "catalog_character_id")
    op.drop_column("catalog_conferencias", "gravado_em")
