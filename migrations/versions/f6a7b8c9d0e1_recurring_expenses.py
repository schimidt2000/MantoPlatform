"""Gastos recorrentes (feature 110).

Duas tabelas novas: recurring_expenses (cadastro: conta variável, débito automático,
assinatura) e recurring_expense_entries (lançamento mensal — um por conta/mês).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-06
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recurring_expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("expense_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("amount_min", sa.Numeric(10, 2), nullable=True),
        sa.Column("amount_max", sa.Numeric(10, 2), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=False),
        sa.Column("default_pix", sa.String(120), nullable=True),
        sa.Column("card_name", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "recurring_expense_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recurring_id", sa.Integer(), sa.ForeignKey("recurring_expenses.id"), nullable=False),
        sa.Column("month_ref", sa.String(7), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("pix", sa.String(120), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("filled_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("filled_at", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("recurring_id", "month_ref", name="uq_recurring_entry_month"),
    )
    op.create_index("ix_recurring_entries_month_ref", "recurring_expense_entries", ["month_ref"])
    op.create_index("ix_recurring_entries_status", "recurring_expense_entries", ["status"])


def downgrade():
    op.drop_index("ix_recurring_entries_status", table_name="recurring_expense_entries")
    op.drop_index("ix_recurring_entries_month_ref", table_name="recurring_expense_entries")
    op.drop_table("recurring_expense_entries")
    op.drop_table("recurring_expenses")
