"""marketing posts com multiplos temas do catalogo

Revision ID: b7d4f81a6e0c
Revises: a3c7e1d59f42
Create Date: 2026-07-29

Migração escrita à mão (padrão do repo). Troca o vínculo 1:N de `marketing_posts.catalog_item_id`
por N:N via a nova tabela `marketing_post_temas` — um post pode falar de vários Temas ao mesmo
tempo (ex.: Reels que junta "15 Anos" e "Debutante" no mesmo vídeo).

1. Cria `marketing_post_temas` (post_id, catalog_item_id), FKs `ON DELETE CASCADE` dos dois lados
   (a linha de associação não faz sentido sem o post nem sem o Tema).
2. Copia todo `catalog_item_id` já preenchido de `marketing_posts` para a tabela nova — nenhum
   vínculo existente se perde.
3. Remove a coluna antiga (`catalog_item_id`, sua FK e seu índice) de `marketing_posts` — a partir
   daqui o vínculo vive só na tabela de associação.

`marketing_frequency_goals.catalog_item_id` não muda: a meta continua mirando em **um** Tema; o
casamento com posts multi-Tema passa a ser "qualquer um dos Temas do post bate com o da meta"
(mudança só em `app/marketing/marketing_ops.py`, sem impacto de schema).
"""
import sqlalchemy as sa
from alembic import op

revision = "b7d4f81a6e0c"
down_revision = "a3c7e1d59f42"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "marketing_post_temas",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["post_id"], ["marketing_posts.id"],
            name="fk_marketing_post_temas_post_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"], ["catalog_items.id"],
            name="fk_marketing_post_temas_catalog_item_id", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("post_id", "catalog_item_id"),
    )
    op.create_index(
        "ix_marketing_post_temas_catalog_item_id",
        "marketing_post_temas",
        ["catalog_item_id"],
    )

    op.execute(
        """
        INSERT INTO marketing_post_temas (post_id, catalog_item_id)
        SELECT id, catalog_item_id FROM marketing_posts WHERE catalog_item_id IS NOT NULL
        """
    )

    op.drop_index("ix_marketing_posts_catalog_item_id", table_name="marketing_posts")
    op.drop_constraint(
        "fk_marketing_posts_catalog_item_id", "marketing_posts", type_="foreignkey"
    )
    op.drop_column("marketing_posts", "catalog_item_id")


def downgrade():
    op.add_column("marketing_posts", sa.Column("catalog_item_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_marketing_posts_catalog_item_id", "marketing_posts", "catalog_items",
        ["catalog_item_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index(
        "ix_marketing_posts_catalog_item_id", "marketing_posts", ["catalog_item_id"]
    )

    # Downgrade tem perda: com >1 Tema por post, só o primeiro (menor catalog_item_id) volta.
    op.execute(
        """
        UPDATE marketing_posts
        SET catalog_item_id = sub.catalog_item_id
        FROM (
            SELECT DISTINCT ON (post_id) post_id, catalog_item_id
            FROM marketing_post_temas
            ORDER BY post_id, catalog_item_id
        ) AS sub
        WHERE marketing_posts.id = sub.post_id
        """
    )

    op.drop_index("ix_marketing_post_temas_catalog_item_id", table_name="marketing_post_temas")
    op.drop_table("marketing_post_temas")
