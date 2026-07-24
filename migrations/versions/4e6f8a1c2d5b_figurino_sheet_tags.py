"""figurino_sheet tags

Revision ID: 4e6f8a1c2d5b
Revises: 7c2d9e4f1a3b
Create Date: 2026-07-24

Migração escrita à mão (padrão do repo). Adiciona a coluna `tags` em `figurino_sheets` para a
feature 183 (Reestruturação do Banco de Figurinos): lista livre de tags/categorias por ficha,
serializada como JSON em texto, mesmo padrão já usado pela coluna `pieces`. Fichas existentes
recebem `NULL` (sem tags) — sem UPDATE em massa necessário.
"""
import sqlalchemy as sa
from alembic import op

revision = "4e6f8a1c2d5b"
down_revision = "7c2d9e4f1a3b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("figurino_sheets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tags", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("figurino_sheets", schema=None) as batch_op:
        batch_op.drop_column("tags")
