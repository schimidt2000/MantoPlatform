"""Tabela `nfc_tag_deliveries`: entregas anexadas a uma tag NFC (feature 261).

A primeira entrega é um vídeo ("Um vídeo especial para você") que o dono sobe pela tela
`/3d/tags` para uma luminária já entregue a uma cliente específica. O modelo nasce como TABELA
(não como coluna solta em `nfc_tags`) porque futuras entregas — foto com link, por exemplo — não
podem exigir migração nova: só uma linha com `kind` diferente.

`kind` hoje só assume `"video"`. `file_path` guarda apenas o NOME do arquivo em
`Config.NFC_MEDIA_FOLDER` (irmão de `UPLOAD_FOLDER`, nunca dentro — a rota `/uploads/<path>`
exige login e a página `/nfc/<code>` é pública). `link_url` já existe para a entrega futura por
link direto, sem arquivo hospedado aqui. `is_active`/`sort_order` preparam múltiplas entregas por
tag; por ora a regra de negócio (`nfc_ops.add_delivery`) mantém só 1 vídeo ativo por tag.

Revision ID: e08e454c4780
Revises: c4d1e7b2a9f3
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op

revision = "e08e454c4780"
down_revision = "c4d1e7b2a9f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nfc_tag_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tag_id", sa.Integer(),
            sa.ForeignKey("nfc_tags.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("link_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_nfc_tag_deliveries_tag_id", "nfc_tag_deliveries", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_nfc_tag_deliveries_tag_id", table_name="nfc_tag_deliveries")
    op.drop_table("nfc_tag_deliveries")
