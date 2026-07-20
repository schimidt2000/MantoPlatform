"""event reimbursements (feature 136)

Revision ID: d0fdc94beccc
Revises: aaf59e2396ec
Create Date: 2026-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d0fdc94beccc"
down_revision = "aaf59e2396ec"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "event_reimbursements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("invoice_file_path", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=True),
        sa.Column("collected_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("receipt_file_path", sa.String(length=300), nullable=True),
        sa.Column("collected_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["calendar_events.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["collected_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_reimbursements_event_id", "event_reimbursements", ["event_id"]
    )


def downgrade():
    op.drop_index("ix_event_reimbursements_event_id", table_name="event_reimbursements")
    op.drop_table("event_reimbursements")
