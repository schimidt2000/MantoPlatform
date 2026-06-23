"""historico de orcamentos gerados no EducaManto (feature 077)

Revision ID: w9f0a1b2c3d4
Revises: v8e9f0a1b2c3
Create Date: 2026-06-23

Cria a tabela educamanto_quotes: cada linha e um orcamento PDF gerado no EducaManto, com um
snapshot (JSON) da configuracao e dos valores por pacote no momento da geracao, para reproduzir o
mesmo PDF depois.

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "w9f0a1b2c3d4"
down_revision = "v8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "educamanto_quotes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("client_name", sa.String(length=200), nullable=True),
        sa.Column("packages_label", sa.String(length=300), nullable=True),
        sa.Column("snapshot", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_educamanto_quotes_user_id", "educamanto_quotes", ["user_id"], unique=False
    )


def downgrade():
    op.drop_index("ix_educamanto_quotes_user_id", table_name="educamanto_quotes")
    op.drop_table("educamanto_quotes")
