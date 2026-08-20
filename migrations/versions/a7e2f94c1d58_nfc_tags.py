"""Tags NFC das peças 3D: tabela `nfc_tags` + `acervo_3d_items.nfc_prefix` (feature 255).

Cada luminária 3D entregue num show carrega uma tag NFC com URL pública imutável
(`/nfc/<code>`). A linha de `nfc_tags` é a unidade física: nunca é apagada (só desativada) e
`code` nunca muda — todo o conteúdo da página é decidido pelo servidor a cada acesso, o que
permite campanhas futuras sem regravar tags já entregues.

- `code` único: `<prefixo do item>-<sufixo aleatório de 6 chars sem ambiguidade>`.
- `sequence` + constraint única `(item_id, sequence)`: numeração humana por item (nº 1, 2, 3…),
  o rótulo físico que a equipe anota na tagzinha ao gravar em lote.
- `event_id` com `ondelete=SET NULL`: evento apagado deixa a tag sem evento, nunca a derruba.
- `acervo_3d_items.nfc_prefix` não-nulo = item habilitado (presente 3D desse item gera tags
  automaticamente, uma por unidade).

Sem backfill: nenhuma tag física foi gravada ainda; a luminária v1 ganha o prefixo pelo ERP.

Revision ID: a7e2f94c1d58
Revises: f3a9c15d8b42
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "a7e2f94c1d58"
down_revision = "f3a9c15d8b42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "acervo_3d_items",
        sa.Column("nfc_prefix", sa.String(length=10), nullable=True),
    )
    op.create_table(
        "nfc_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "item_id", sa.Integer(),
            sa.ForeignKey("acervo_3d_items.id"), nullable=False,
        ),
        sa.Column(
            "event_id", sa.Integer(),
            sa.ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_accessed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("item_id", "sequence", name="uq_nfc_tags_item_sequence"),
    )
    op.create_index("ix_nfc_tags_code", "nfc_tags", ["code"], unique=True)
    op.create_index("ix_nfc_tags_item_id", "nfc_tags", ["item_id"])
    op.create_index("ix_nfc_tags_event_id", "nfc_tags", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_nfc_tags_event_id", table_name="nfc_tags")
    op.drop_index("ix_nfc_tags_item_id", table_name="nfc_tags")
    op.drop_index("ix_nfc_tags_code", table_name="nfc_tags")
    op.drop_table("nfc_tags")
    op.drop_column("acervo_3d_items", "nfc_prefix")
