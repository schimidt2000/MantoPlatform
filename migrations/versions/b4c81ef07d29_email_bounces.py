"""Fila de emails devolvidos (feature 219).

`email_bounces` guarda uma linha por aviso do Mail Delivery Subsystem lido na caixa do remetente,
já casado com o talento/usuário dono do endereço. `message_id` é único: reler a caixa não duplica.

Revision ID: b4c81ef07d29
Revises: e7a1c94f20b3
Create Date: 2026-08-06
"""

import sqlalchemy as sa
from alembic import op

revision = "b4c81ef07d29"
down_revision = "e7a1c94f20b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_bounces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.String(length=300), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("talent_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("is_permanent", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("status_code", sa.String(length=12), nullable=True),
        sa.Column("diagnostic", sa.Text(), nullable=True),
        sa.Column("original_subject", sa.String(length=300), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", name="uq_email_bounces_message_id"),
        sa.ForeignKeyConstraint(
            ["talent_id"], ["talents.id"], name="fk_email_bounces_talent", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_email_bounces_user", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"], ["users.id"],
            name="fk_email_bounces_resolved_by", ondelete="SET NULL",
        ),
    )
    op.create_index("ix_email_bounces_email", "email_bounces", ["email"])
    op.create_index("ix_email_bounces_talent_id", "email_bounces", ["talent_id"])
    op.create_index("ix_email_bounces_resolved_at", "email_bounces", ["resolved_at"])


def downgrade() -> None:
    op.drop_index("ix_email_bounces_resolved_at", table_name="email_bounces")
    op.drop_index("ix_email_bounces_talent_id", table_name="email_bounces")
    op.drop_index("ix_email_bounces_email", table_name="email_bounces")
    op.drop_table("email_bounces")
