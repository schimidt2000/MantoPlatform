"""notes + warning_level em talents (anotações internas e alerta)

Revision ID: k7e8f9a0b1c2
Revises: j6d7e8f9a0b1
Create Date: 2026-06-09

Adiciona em talents:
  - notes (Text, nullable): anotações internas sobre o talento;
  - warning_level (String(20), nullable): nível de alerta (leve|moderado|grave; None/"" = nenhum).

Migration escrita à mão (autogenerate quebrado por drift pré-existente).
"""
from alembic import op
import sqlalchemy as sa

revision = "k7e8f9a0b1c2"
down_revision = "j6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("talents") as batch_op:
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("warning_level", sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table("talents") as batch_op:
        batch_op.drop_column("warning_level")
        batch_op.drop_column("notes")
