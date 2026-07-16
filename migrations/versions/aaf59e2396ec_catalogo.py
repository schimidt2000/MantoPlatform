"""catalogo publico (feature 133)

Revision ID: aaf59e2396ec
Revises: 4e2bdfa8b106
Create Date: 2026-07-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "aaf59e2396ec"
down_revision = "4e2bdfa8b106"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "catalog_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "catalog_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wp_product_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("short_description_html", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wp_product_id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "catalog_item_categories",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["catalog_categories.id"]),
        sa.PrimaryKeyConstraint("item_id", "category_id"),
    )

    op.create_table(
        "catalog_item_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("original_url", sa.String(length=500), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["catalog_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_catalog_item_images_item_id", "catalog_item_images", ["item_id"]
    )


def downgrade():
    op.drop_index("ix_catalog_item_images_item_id", table_name="catalog_item_images")
    op.drop_table("catalog_item_images")
    op.drop_table("catalog_item_categories")
    op.drop_table("catalog_items")
    op.drop_table("catalog_categories")
