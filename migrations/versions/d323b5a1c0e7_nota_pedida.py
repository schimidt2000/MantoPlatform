"""A nota pedida chega ao Superadmin (feature 323).

Cinco colunas em ``calendar_events`` (os dados da nota, que são da venda) e três em
``event_invoices`` (quem pediu cada nota, quando, e quando o aviso saiu). Todas nulas e sem
backfill: nota do legado fica sem "pedida por" e nunca dispara e-mail.

Aditiva: o código anterior lê e grava no banco migrado. Rollback = reverter o merge; o ``downgrade``
só derruba as colunas.

Revision ID: d323b5a1c0e7
Revises: c322a7e1b9d4
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "d323b5a1c0e7"
down_revision = "c322a7e1b9d4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("calendar_events") as batch:
        batch.add_column(sa.Column("nota_tomador_doc", sa.String(14), nullable=True))
        batch.add_column(sa.Column("nota_iss_retido", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("nota_municipio", sa.String(120), nullable=True))
        batch.add_column(sa.Column("nota_referencia", sa.String(120), nullable=True))
        batch.add_column(sa.Column("nota_observacoes", sa.Text(), nullable=True))

    with op.batch_alter_table("event_invoices") as batch:
        batch.add_column(sa.Column("pedida_por_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("pedida_em", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("aviso_enviado_em", sa.DateTime(), nullable=True))
        batch.create_foreign_key(
            "fk_event_invoices_pedida_por_id_users",
            "users",
            ["pedida_por_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("event_invoices") as batch:
        batch.drop_constraint("fk_event_invoices_pedida_por_id_users", type_="foreignkey")
        batch.drop_column("aviso_enviado_em")
        batch.drop_column("pedida_em")
        batch.drop_column("pedida_por_id")

    with op.batch_alter_table("calendar_events") as batch:
        batch.drop_column("nota_observacoes")
        batch.drop_column("nota_referencia")
        batch.drop_column("nota_municipio")
        batch.drop_column("nota_iss_retido")
        batch.drop_column("nota_tomador_doc")
