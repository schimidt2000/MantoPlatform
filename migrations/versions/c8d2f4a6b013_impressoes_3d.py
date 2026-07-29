"""modulo core de impressoes 3d

Revision ID: c8d2f4a6b013
Revises: 9f1c3a7b5e2d
Create Date: 2026-07-29

Migração escrita à mão (padrão do repo), 100% aditiva, para a feature 200 (Módulo Core de
Impressões 3D). Cria `acervo_3d_items` (catálogo de peças base — foto de preview e arquivo 3D
bruto, ambos NOT NULL: peça sem foto não é selecionável visualmente e peça sem arquivo não é
imprimível) e `event_3d_gifts` (presentes vinculados a um evento, com status, prazo e
quantidade). Nenhuma tabela/coluna existente é alterada ou removida — eventos já existentes
seguem funcionando sem presente 3D vinculado.

O papel `ARTISTA_3D` NÃO é criado aqui: papéis são linhas de `roles` semeadas por `seed.py`
(mesmo tratamento dado a MARKETING/REVENDEDOR_EDUCAMANTO), não schema.
"""
import sqlalchemy as sa
from alembic import op

revision = "c8d2f4a6b013"
down_revision = "9f1c3a7b5e2d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "acervo_3d_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "event_3d_gifts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("deadline_date", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"], ["calendar_events.id"],
            name="fk_event_3d_gifts_event_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"], ["acervo_3d_items.id"],
            name="fk_event_3d_gifts_item_id",
        ),
    )
    op.create_index("ix_event_3d_gifts_event_id", "event_3d_gifts", ["event_id"])
    op.create_index("ix_event_3d_gifts_item_id", "event_3d_gifts", ["item_id"])
    op.create_index("ix_event_3d_gifts_status", "event_3d_gifts", ["status"])


def downgrade():
    op.drop_index("ix_event_3d_gifts_status", table_name="event_3d_gifts")
    op.drop_index("ix_event_3d_gifts_item_id", table_name="event_3d_gifts")
    op.drop_index("ix_event_3d_gifts_event_id", table_name="event_3d_gifts")
    op.drop_table("event_3d_gifts")
    op.drop_table("acervo_3d_items")
