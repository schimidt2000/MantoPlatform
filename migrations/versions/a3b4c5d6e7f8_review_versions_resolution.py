"""historico de versoes e conclusao transparente na revisao (feature 104)

Revision ID: a3b4c5d6e7f8
Revises: e7b8c9d0f1a2
Create Date: 2026-07-02

Cria review_asset_versions (snapshots das versoes anteriores de um material — a atual continua
no proprio review_assets). Adiciona a review_comments: version_number (versao vigente quando o
comentario foi criado), resolved_by e resolved_at (quem concluiu e quando). Adiciona a
review_assets: uploaded_by (quem enviou a versao atual — copiado para o snapshot ao substituir).
Backfill: comentarios existentes recebem a versao atual do seu material.

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "a3b4c5d6e7f8"
down_revision = "e7b8c9d0f1a2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "review_asset_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("review_assets.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=400), nullable=False),
        sa.Column("original_name", sa.String(length=300), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("file_removed", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_review_asset_versions_asset_id", "review_asset_versions", ["asset_id"]
    )

    op.add_column(
        "review_comments",
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "review_comments",
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("review_comments", sa.Column("resolved_at", sa.DateTime(), nullable=True))

    op.add_column(
        "review_assets",
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )

    # Comentarios existentes pertencem a versao atual do seu material (FR-017).
    op.execute(
        "UPDATE review_comments SET version_number = ("
        "SELECT version FROM review_assets "
        "WHERE review_assets.id = review_comments.asset_id)"
    )


def downgrade():
    op.drop_column("review_assets", "uploaded_by")
    op.drop_column("review_comments", "resolved_at")
    op.drop_column("review_comments", "resolved_by")
    op.drop_column("review_comments", "version_number")
    op.drop_index("ix_review_asset_versions_asset_id", table_name="review_asset_versions")
    op.drop_table("review_asset_versions")
