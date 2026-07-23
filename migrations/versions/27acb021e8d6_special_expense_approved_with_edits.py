"""special_expense approved_with_edits

Revision ID: 27acb021e8d6
Revises: d0fdc94beccc
Create Date: 2026-07-23

Migração escrita à mão (padrão do repo). Adiciona a coluna `approved_with_edits` em
`special_expenses` para a feature 179 (RBAC/edição em Gastos Extras) — não altera `status`
nem nenhuma outra coluna existente.
"""
import sqlalchemy as sa
from alembic import op

revision = "27acb021e8d6"
down_revision = "d0fdc94beccc"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("special_expenses", schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            "approved_with_edits", sa.Boolean(), server_default=sa.false(), nullable=False
        ))


def downgrade():
    with op.batch_alter_table("special_expenses", schema=None) as batch_op:
        batch_op.drop_column("approved_with_edits")
