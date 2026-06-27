"""arquivos temporarios na revisao: expiracao/versao/finalizar (feature 090)

Revision ID: z2c3d4e5f6a7
Revises: y1b2c3d4e5f6
Create Date: 2026-06-26

Adiciona a review_assets: expires_at (prazo de validade do arquivo), finalized_at (aprovado/finalizado
pelo criador), file_removed (arquivo removido do armazenamento) e version. Materiais existentes recebem
expires_at = created_at + 7 dias, version = 1 e file_removed = false.

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "z2c3d4e5f6a7"
down_revision = "y1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("review_assets", sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.add_column("review_assets", sa.Column("finalized_at", sa.DateTime(), nullable=True))
    op.add_column(
        "review_assets",
        sa.Column("file_removed", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "review_assets",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    # Materiais existentes: prazo = data de envio + 7 dias.
    op.execute(
        "UPDATE review_assets SET expires_at = created_at + INTERVAL '7 days' WHERE expires_at IS NULL"
    )


def downgrade():
    op.drop_column("review_assets", "version")
    op.drop_column("review_assets", "file_removed")
    op.drop_column("review_assets", "finalized_at")
    op.drop_column("review_assets", "expires_at")
