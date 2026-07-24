"""catalog characters + video url

Revision ID: 9f1c3a7b5e2d
Revises: 4e6f8a1c2d5b
Create Date: 2026-07-24

Migração escrita à mão (padrão do repo), 100% aditiva, para a feature 185 (Catálogo Vitrine
Completo). Adiciona `catalog_items.video_url` (vídeo externo opcional do Tema) e a tabela nova
`catalog_characters` (Personagem filho de um Tema, com foto/vídeo/vínculo opcional de Ficha de
Figurino). Nenhuma coluna/tabela existente é alterada ou removida — itens do catálogo já
existentes continuam funcionando sem re-cadastro (FR-015 de specs/185-catalogo-vitrine-completo).
"""
import sqlalchemy as sa
from alembic import op

revision = "9f1c3a7b5e2d"
down_revision = "4e6f8a1c2d5b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("catalog_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("video_url", sa.String(500), nullable=True))

    op.create_table(
        "catalog_characters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("catalog_item_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(240), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("figurino_sheet_id", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"], ["catalog_items.id"],
            name="fk_catalog_characters_catalog_item_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["figurino_sheet_id"], ["figurino_sheets.id"],
            name="fk_catalog_characters_figurino_sheet_id", ondelete="SET NULL",
        ),
        sa.UniqueConstraint("slug", name="uq_catalog_characters_slug"),
    )
    op.create_index(
        "ix_catalog_characters_catalog_item_id", "catalog_characters", ["catalog_item_id"],
    )


def downgrade():
    op.drop_index("ix_catalog_characters_catalog_item_id", table_name="catalog_characters")
    op.drop_table("catalog_characters")
    with op.batch_alter_table("catalog_items", schema=None) as batch_op:
        batch_op.drop_column("video_url")
