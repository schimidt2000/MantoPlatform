"""Avisos no celular: os aparelhos registrados (feature 332).

Uma tabela nova, ``push_assinaturas``: o endereço do serviço de avisos de cada aparelho (UNIQUE), as
chaves do aparelho e a pessoa. Aditiva; o ``downgrade`` derruba a tabela (os aparelhos precisam ser
ativados de novo).

Revision ID: b332d5f7a9c1
Revises: a330c4e8f1b2
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op

revision = "b332d5f7a9c1"
down_revision = "a330c4e8f1b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "push_assinaturas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name="fk_push_assinaturas_user_id_users", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(255), nullable=False),
        sa.Column("auth", sa.String(64), nullable=False),
        sa.Column("navegador", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("ultimo_aviso_em", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("endpoint", name="uq_push_assinaturas_endpoint"),
    )
    op.create_index("ix_push_assinaturas_user_id", "push_assinaturas", ["user_id"])


def downgrade():
    op.drop_index("ix_push_assinaturas_user_id", table_name="push_assinaturas")
    op.drop_table("push_assinaturas")
