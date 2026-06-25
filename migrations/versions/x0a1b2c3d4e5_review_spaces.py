"""espaco de revisao de midia estilo Vimeo (feature 088)

Revision ID: x0a1b2c3d4e5
Revises: w9f0a1b2c3d4
Create Date: 2026-06-25

Cria as tabelas do modulo de revisao de midia: review_spaces (espacos), review_assets (materiais:
video/audio/imagem/pdf), review_reviewers (usuarios autorizados a revisar) e review_comments
(comentarios ancorados: timecode em video/audio, page em pdf, pos_x/pos_y em imagem).

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "x0a1b2c3d4e5"
down_revision = "w9f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "review_spaces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "review_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("space_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=400), nullable=False),
        sa.Column("original_name", sa.String(length=300), nullable=True),
        sa.Column("media_type", sa.String(length=10), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["space_id"], ["review_spaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_assets_space_id", "review_assets", ["space_id"], unique=False)
    op.create_table(
        "review_reviewers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("space_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["space_id"], ["review_spaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("space_id", "user_id", name="uq_review_reviewer"),
    )
    op.create_index("ix_review_reviewers_space_id", "review_reviewers", ["space_id"], unique=False)
    op.create_table(
        "review_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("timecode", sa.Float(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("pos_x", sa.Float(), nullable=True),
        sa.Column("pos_y", sa.Float(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["review_assets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_comments_asset_id", "review_comments", ["asset_id"], unique=False)


def downgrade():
    op.drop_index("ix_review_comments_asset_id", table_name="review_comments")
    op.drop_table("review_comments")
    op.drop_index("ix_review_reviewers_space_id", table_name="review_reviewers")
    op.drop_table("review_reviewers")
    op.drop_index("ix_review_assets_space_id", table_name="review_assets")
    op.drop_table("review_assets")
    op.drop_table("review_spaces")
