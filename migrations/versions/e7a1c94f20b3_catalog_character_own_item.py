"""Página própria de personagem do catálogo (feature 209).

`catalog_characters.own_item_id` liga um personagem ao CatalogItem que é a página própria
dele (caso Coelho Branco dentro do tema Alice): o personagem aparece no elenco do tema E
continua com página/busca próprias. UNIQUE — um item só pode ser a página de UM personagem.

Revision ID: e7a1c94f20b3
Revises: d9f2b3a41c07
Create Date: 2026-08-05
"""

import sqlalchemy as sa
from alembic import op

revision = "e7a1c94f20b3"
down_revision = "d9f2b3a41c07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catalog_characters",
        sa.Column("own_item_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_catalog_characters_own_item",
        "catalog_characters",
        "catalog_items",
        ["own_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_catalog_characters_own_item", "catalog_characters", ["own_item_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_catalog_characters_own_item", "catalog_characters", type_="unique")
    op.drop_constraint("fk_catalog_characters_own_item", "catalog_characters", type_="foreignkey")
    op.drop_column("catalog_characters", "own_item_id")
