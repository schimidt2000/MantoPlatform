"""rating edit history: event_rating_versions + edited_at/edit_count

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-05-30

Migration escrita à mão (autogenerate quebrado por drift pré-existente do schema).
"""
from alembic import op
import sqlalchemy as sa

revision = "d9e0f1a2b3c4"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("event_ratings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("edited_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("edit_count", sa.Integer(), server_default="0", nullable=False))

    op.create_table(
        "event_rating_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rating_id", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("replaced_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["rating_id"], ["event_ratings.id"],
                                name="fk_event_rating_versions_rating"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_rating_versions_rating_id", "event_rating_versions",
                    ["rating_id"], unique=False)


def downgrade():
    op.drop_index("ix_event_rating_versions_rating_id", table_name="event_rating_versions")
    op.drop_table("event_rating_versions")
    with op.batch_alter_table("event_ratings", schema=None) as batch_op:
        batch_op.drop_column("edit_count")
        batch_op.drop_column("edited_at")
