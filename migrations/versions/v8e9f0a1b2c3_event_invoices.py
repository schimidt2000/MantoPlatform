"""notas fiscais por evento (feature 069)

Revision ID: v8e9f0a1b2c3
Revises: u7d8e9f0a1b2
Create Date: 2026-06-22

Cria a tabela event_invoices: cada evento "com nota" pode ter varias notas, cada uma com valor,
data de emissao, estado (a_emitir|emitida), arquivo e data de emissao real.

Migra a nota unica pre-existente (feature 065): para cada evento com invoice_file ou
invoice_due_date e sem nota, cria 1 event_invoice (amount=sale_value, issue_date=invoice_due_date,
file=invoice_file, status='emitida' se tinha arquivo senao 'a_emitir'). Idempotente.

As colunas calendar_events.invoice_file / invoice_due_date sao mantidas (nao removidas).

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "v8e9f0a1b2c3"
down_revision = "u7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "event_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="a_emitir", nullable=False),
        sa.Column("file", sa.String(length=300), nullable=True),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["calendar_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_invoices_event_id", "event_invoices", ["event_id"], unique=False
    )

    # Migra a nota unica existente (feature 065) para o novo formato.
    op.execute(
        """
        INSERT INTO event_invoices (event_id, amount, issue_date, status, file, issued_at, created_at)
        SELECT e.id, e.sale_value, e.invoice_due_date,
               CASE WHEN e.invoice_file IS NOT NULL THEN 'emitida' ELSE 'a_emitir' END,
               e.invoice_file,
               CASE WHEN e.invoice_file IS NOT NULL THEN CURRENT_TIMESTAMP ELSE NULL END,
               CURRENT_TIMESTAMP
        FROM calendar_events e
        WHERE (e.invoice_file IS NOT NULL OR e.invoice_due_date IS NOT NULL)
          AND NOT EXISTS (SELECT 1 FROM event_invoices ei WHERE ei.event_id = e.id)
        """
    )


def downgrade():
    op.drop_index("ix_event_invoices_event_id", table_name="event_invoices")
    op.drop_table("event_invoices")
