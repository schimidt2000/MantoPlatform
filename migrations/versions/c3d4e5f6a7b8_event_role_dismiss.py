"""dispensar tarefa de casting pendente (feature 108)

Revision ID: c3d4e5f6a7b8
Revises: a3b4c5d6e7f8
Create Date: 2026-07-03

Adiciona a event_roles: dismissed_at (quando o super admin dispensou o cargo pendente) e
dismissed_by (quem dispensou). Cargo dispensado continua existindo (a sincronizacao com o
Google Agenda nunca o apaga nem recria), apenas para de contar como tarefa pendente de
casting. Sem backfill: cargos existentes ficam com dismissed_at NULL (comportamento atual
preservado).

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("event_roles", sa.Column("dismissed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "event_roles",
        sa.Column("dismissed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade():
    op.drop_column("event_roles", "dismissed_by")
    op.drop_column("event_roles", "dismissed_at")
