"""modulo de gestao de marketing e frequencia

Revision ID: a3c7e1d59f42
Revises: e4f7b2c9a350
Create Date: 2026-07-29

Migração escrita à mão (padrão do repo), 100% aditiva, para a feature 204 (Módulo de Gestão de
Marketing e Frequência). Cria:

- `marketing_posts` — o card do Kanban de planejamento. Os três vínculos (`assignee_id`,
  `catalog_item_id`, `review_space_id`) são `ON DELETE SET NULL`: apagar um usuário, um Tema do
  catálogo ou um espaço de revisão **não pode** apagar o planejamento de marketing junto. O
  `review_space_id` é UNIQUE — o vínculo com o módulo de Revisão de Mídia é 1:1 por definição.
- `marketing_frequency_goals` — a regra de frequência ("15 Anos a cada 15 dias"). Não guarda
  estado de cumprimento: `last_posted_date` e o status derivado são calculados na leitura a
  partir dos posts publicados (ver `app/marketing/marketing_ops.py`).

Nenhuma tabela/coluna existente é alterada ou removida. O papel `MARKETING` NÃO é criado aqui:
papéis são linhas de `roles` semeadas por `seed.py` (e o MARKETING já existe desde a feature 088).
"""
import sqlalchemy as sa
from alembic import op

revision = "a3c7e1d59f42"
down_revision = "e4f7b2c9a350"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "marketing_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ideia"),
        sa.Column("deadline_date", sa.Date(), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("platform", sa.String(40), nullable=True),
        sa.Column("drive_folder_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("catalog_item_id", sa.Integer(), nullable=True),
        sa.Column("review_space_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignee_id"], ["users.id"],
            name="fk_marketing_posts_assignee_id", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"], ["catalog_items.id"],
            name="fk_marketing_posts_catalog_item_id", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["review_space_id"], ["review_spaces.id"],
            name="fk_marketing_posts_review_space_id", ondelete="SET NULL",
        ),
        sa.UniqueConstraint("review_space_id", name="uq_marketing_posts_review_space_id"),
    )
    op.create_index("ix_marketing_posts_status", "marketing_posts", ["status"])
    op.create_index("ix_marketing_posts_catalog_item_id", "marketing_posts", ["catalog_item_id"])
    op.create_index("ix_marketing_posts_publish_date", "marketing_posts", ["publish_date"])

    op.create_table(
        "marketing_frequency_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("target_interval_days", sa.Integer(), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"], ["catalog_items.id"],
            name="fk_marketing_frequency_goals_catalog_item_id", ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_marketing_frequency_goals_catalog_item_id",
        "marketing_frequency_goals",
        ["catalog_item_id"],
    )


def downgrade():
    op.drop_index(
        "ix_marketing_frequency_goals_catalog_item_id", table_name="marketing_frequency_goals"
    )
    op.drop_table("marketing_frequency_goals")
    op.drop_index("ix_marketing_posts_publish_date", table_name="marketing_posts")
    op.drop_index("ix_marketing_posts_catalog_item_id", table_name="marketing_posts")
    op.drop_index("ix_marketing_posts_status", table_name="marketing_posts")
    op.drop_table("marketing_posts")
