"""client feedback (feature 130)

Revision ID: d969149662f5
Revises: 9ae0a236db40
Create Date: 2026-07-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d969149662f5"
down_revision = "9ae0a236db40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "calendar_events",
        sa.Column("feedback_token", sa.String(length=43), nullable=True),
    )
    op.create_unique_constraint(
        "uq_calendar_events_feedback_token", "calendar_events", ["feedback_token"]
    )

    op.create_table(
        "client_feedbacks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["calendar_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_client_feedbacks_event_id", "client_feedbacks", ["event_id"]
    )


def downgrade():
    op.drop_index("ix_client_feedbacks_event_id", table_name="client_feedbacks")
    op.drop_table("client_feedbacks")
    op.drop_constraint(
        "uq_calendar_events_feedback_token", "calendar_events", type_="unique"
    )
    op.drop_column("calendar_events", "feedback_token")
