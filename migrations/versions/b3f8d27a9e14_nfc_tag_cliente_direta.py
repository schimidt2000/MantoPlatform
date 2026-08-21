"""Tag NFC vinculável direto a uma cliente, sem show (feature 255, 2ª rodada).

A luminária não vai só para quem contratou show: campanhas de marketing enviam para clientes
em potencial. Nesses casos não existe evento nenhum — a equipe cria a cliente no módulo
Clientes e vincula a tag direto a ela. `client_id` é independente de `event_id` (podem
coexistir; a cliente direta tem precedência na exibição) e segue a mesma filosofia do evento:
`ondelete=SET NULL` — cliente apagada nunca derruba a tag nem a página pública.

Revision ID: b3f8d27a9e14
Revises: a7e2f94c1d58
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "b3f8d27a9e14"
down_revision = "a7e2f94c1d58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nfc_tags",
        sa.Column(
            "client_id", sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True,
        ),
    )
    op.create_index("ix_nfc_tags_client_id", "nfc_tags", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_nfc_tags_client_id", table_name="nfc_tags")
    op.drop_column("nfc_tags", "client_id")
