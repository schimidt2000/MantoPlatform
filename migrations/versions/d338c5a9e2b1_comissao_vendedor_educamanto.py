"""A comissão do vendedor EducaManto (feature 338).

Uma coluna em ``calendar_events`` (o valor que o vendedor pôs no preço pela calculadora), uma em
``commission_payments`` (a fonte da linha: NULL = a comissão do evento, a de sempre) e duas em
``event_cancellations`` (o vendedor e o valor congelados no ato). Todas nulas e sem backfill: toda
linha de comissão que já existe fica na trilha de sempre (``source`` NULL).

Aditiva: o código anterior lê e grava no banco migrado. Rollback = reverter o merge; o ``downgrade``
só derruba as colunas.

Revision ID: d338c5a9e2b1
Revises: d323b5a1c0e7
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op

revision = "d338c5a9e2b1"
down_revision = "d323b5a1c0e7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("calendar_events") as batch:
        batch.add_column(
            sa.Column("educamanto_seller_commission", sa.Numeric(12, 2), nullable=True)
        )

    with op.batch_alter_table("commission_payments") as batch:
        batch.add_column(sa.Column("source", sa.String(30), nullable=True))

    with op.batch_alter_table("event_cancellations") as batch:
        batch.add_column(sa.Column("educamanto_seller_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("educamanto_seller_commission", sa.Numeric(12, 2), nullable=True)
        )
        # Sem `ondelete`, como `commission_seller_id`: quem recebeu no ato bloqueia a exclusão do
        # usuário (FR-073 da 306).
        batch.create_foreign_key(
            "fk_event_cancellations_educamanto_seller_id_users",
            "users",
            ["educamanto_seller_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("event_cancellations") as batch:
        batch.drop_constraint(
            "fk_event_cancellations_educamanto_seller_id_users", type_="foreignkey"
        )
        batch.drop_column("educamanto_seller_commission")
        batch.drop_column("educamanto_seller_id")

    with op.batch_alter_table("commission_payments") as batch:
        batch.drop_column("source")

    with op.batch_alter_table("calendar_events") as batch:
        batch.drop_column("educamanto_seller_commission")
