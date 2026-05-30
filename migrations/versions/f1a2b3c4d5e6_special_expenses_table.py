"""special_expenses table

Revision ID: f1a2b3c4d5e6
Revises: 7cea4da9e282
Create Date: 2026-05-30

Migration escrita à mão (o autogenerate captura divergências pré-existentes do schema
— FKs sem nome em crm_deals/talent_media/password_reset_token — que quebram o batch no
SQLite). Esta migration cria APENAS a tabela special_expenses.
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "4511fd62d394"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "special_expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("receipt_path", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pendente", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name="fk_special_expenses_created_by"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], name="fk_special_expenses_approved_by"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_special_expenses_status", "special_expenses", ["status"], unique=False)
    op.create_index("ix_special_expenses_expense_date", "special_expenses", ["expense_date"], unique=False)


def downgrade():
    op.drop_index("ix_special_expenses_expense_date", table_name="special_expenses")
    op.drop_index("ix_special_expenses_status", table_name="special_expenses")
    op.drop_table("special_expenses")
