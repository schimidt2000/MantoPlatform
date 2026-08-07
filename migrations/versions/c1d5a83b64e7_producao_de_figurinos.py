"""Produção de figurinos: pedido, anexos, histórico e vínculo com gasto (feature 225).

Cria a entidade que faltava entre o catálogo de fichas (`figurino_sheets`, que descreve o
figurino pronto) e o caixa (`special_expenses`, que registra o dinheiro depois que saiu): o
trabalho de produzir, com responsável, prazo, custo previsto e evolução.

`special_expenses.figurino_producao_id` nasce nulo em todos os 40 lançamentos de figurino
existentes — nenhum número muda com esta migração. Vincular os antigos é trabalho de tela, feito
quando alguém quiser organizar o passado (FR-032).

Revision ID: c1d5a83b64e7
Revises: b8e4d27a91f5
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op

revision = "c1d5a83b64e7"
down_revision = "b8e4d27a91f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "figurino_producoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="solicitado"
        ),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        # SET NULL nos dois: excluir o evento ou a ficha não pode apagar o pedido — o trabalho
        # existiu e o dinheiro saiu (mesma lição que a feature 224 aprendeu com o event_id do
        # gasto extra, que era NO ACTION e quebrava a exclusão do evento).
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("figurino_sheet_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_id", sa.Integer(), nullable=False),
        sa.Column("responsible_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("done_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("google_event_id", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"], ["calendar_events.id"], ondelete="SET NULL",
            name="fk_figurino_producoes_event",
        ),
        sa.ForeignKeyConstraint(
            ["figurino_sheet_id"], ["figurino_sheets.id"], ondelete="SET NULL",
            name="fk_figurino_producoes_sheet",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_id"], ["users.id"], name="fk_figurino_producoes_requested_by",
        ),
        sa.ForeignKeyConstraint(
            ["responsible_id"], ["users.id"], ondelete="SET NULL",
            name="fk_figurino_producoes_responsible",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"], ["users.id"], ondelete="SET NULL",
            name="fk_figurino_producoes_approved_by",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_figurino_producoes_status", "figurino_producoes", ["status"])
    op.create_index(
        "ix_figurino_producoes_responsible_id", "figurino_producoes", ["responsible_id"]
    )
    op.create_index("ix_figurino_producoes_event_id", "figurino_producoes", ["event_id"])
    op.create_index("ix_figurino_producoes_due_date", "figurino_producoes", ["due_date"])

    op.create_table(
        "figurino_producao_anexos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("producao_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="foto"),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=True),
        sa.Column("caption", sa.String(length=300), nullable=True),
        sa.Column("supplier_name", sa.String(length=200), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["producao_id"], ["figurino_producoes.id"], ondelete="CASCADE",
            name="fk_figurino_producao_anexos_producao",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"], ["users.id"], ondelete="SET NULL",
            name="fk_figurino_producao_anexos_uploaded_by",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_figurino_producao_anexos_producao_id", "figurino_producao_anexos", ["producao_id"]
    )

    op.create_table(
        "figurino_producao_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("producao_id", sa.Integer(), nullable=False),
        sa.Column("actor_name", sa.String(length=120), nullable=False, server_default="Sistema"),
        sa.Column("actor_role", sa.String(length=120), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("photo_path", sa.String(length=500), nullable=True),
        sa.Column("status_from", sa.String(length=20), nullable=True),
        sa.Column("status_to", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["producao_id"], ["figurino_producoes.id"], ondelete="CASCADE",
            name="fk_figurino_producao_logs_producao",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_figurino_producao_logs_producao_id", "figurino_producao_logs", ["producao_id"]
    )

    op.add_column(
        "special_expenses", sa.Column("figurino_producao_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_special_expenses_figurino_producao", "special_expenses", "figurino_producoes",
        ["figurino_producao_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index(
        "ix_special_expenses_figurino_producao_id",
        "special_expenses",
        ["figurino_producao_id"],
        postgresql_where=sa.text("figurino_producao_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_special_expenses_figurino_producao_id", table_name="special_expenses")
    op.drop_constraint(
        "fk_special_expenses_figurino_producao", "special_expenses", type_="foreignkey"
    )
    op.drop_column("special_expenses", "figurino_producao_id")

    op.drop_index("ix_figurino_producao_logs_producao_id", table_name="figurino_producao_logs")
    op.drop_table("figurino_producao_logs")
    op.drop_index(
        "ix_figurino_producao_anexos_producao_id", table_name="figurino_producao_anexos"
    )
    op.drop_table("figurino_producao_anexos")

    op.drop_index("ix_figurino_producoes_due_date", table_name="figurino_producoes")
    op.drop_index("ix_figurino_producoes_event_id", table_name="figurino_producoes")
    op.drop_index("ix_figurino_producoes_responsible_id", table_name="figurino_producoes")
    op.drop_index("ix_figurino_producoes_status", table_name="figurino_producoes")
    op.drop_table("figurino_producoes")
