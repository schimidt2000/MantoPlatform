"""figurino_missing_dismissals

Revision ID: 7c2d9e4f1a3b
Revises: aa1bb2cc3dd4
Create Date: 2026-07-24

Migração escrita à mão (padrão do repo). Cria a tabela `figurino_missing_dismissals` para a
feature 183 (Reestruturação do Banco de Figurinos): registra o descarte do alerta de
"personagem sem ficha" pelos `EventRole.id` cobertos no momento do descarte — um cargo de
evento novo (id fora do JSON salvo) faz o personagem reaparecer na lista de faltantes.
"""
import sqlalchemy as sa
from alembic import op

revision = "7c2d9e4f1a3b"
down_revision = "aa1bb2cc3dd4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "figurino_missing_dismissals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("character_name_norm", sa.String(length=200), nullable=False),
        sa.Column("event_role_ids", sa.Text(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(), nullable=False),
        sa.Column("dismissed_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["dismissed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_figurino_missing_dismissals_norm",
        "figurino_missing_dismissals",
        ["character_name_norm"],
    )


def downgrade():
    op.drop_index("ix_figurino_missing_dismissals_norm", table_name="figurino_missing_dismissals")
    op.drop_table("figurino_missing_dismissals")
