"""pendencia 3d por evento show

Revision ID: e4f7b2c9a350
Revises: d9e3a5b7c124
Create Date: 2026-07-29

Migração escrita à mão (padrão do repo), 100% aditiva, para a feature 202: a Fila de Impressão
passou a ser dirigida pelo EVENTO — todo SHOW futuro sem presente vinculado vira uma tarefa.
Como nem todo show leva presente 3D, `event_3d_dismissals` guarda a dispensa ("este não leva"),
tirando a tarefa da fila sem inventar um presente fantasma.

`event_id` é UNIQUE: uma dispensa por evento. Reverter é apagar a linha (a API expõe DELETE), e
vincular um presente descarta a dispensa automaticamente.
"""
import sqlalchemy as sa
from alembic import op

revision = "e4f7b2c9a350"
down_revision = "d9e3a5b7c124"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "event_3d_dismissals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(), nullable=False),
        sa.Column("dismissed_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["event_id"], ["calendar_events.id"],
            name="fk_event_3d_dismissals_event_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dismissed_by"], ["users.id"], name="fk_event_3d_dismissals_dismissed_by",
        ),
        sa.UniqueConstraint("event_id", name="uq_event_3d_dismissals_event_id"),
    )


def downgrade():
    op.drop_table("event_3d_dismissals")
