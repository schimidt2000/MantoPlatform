"""Tabela `notifications`: notificações internas por destinatário (feature 272).

O dono não quer e-mail quando a cliente preenche formulário — quer o aviso dentro do ERP. Esta
tabela é a fundação: **uma linha por destinatário** (o estado "lida" é por pessoa; com uma tabela
só, o sino é um COUNT indexado e o dedupe é uma constraint), texto pronto na escrita
(`title`/`body`/`link_path`) e referência **fraca** ao objeto (`entity_type`/`entity_id`, sem FK —
a tabela é transversal e uma FK por domínio a acoplaria a todos).

`dedupe_key` (`<kind>:<entity_id>[:<marcador>]`) é a identidade do aviso; a `UNIQUE(user_id,
dedupe_key)` é a trava de idempotência entre os 3 workers do gunicorn — por restrição de banco, não
por confiança no fluxo (docs/00 §6 item 10; mesmo molde de `virtual_order_notifications`).

O índice **parcial** `(user_id, id) WHERE read_at IS NULL` serve a contagem de não lidas — a
consulta mais frequente do sistema depois desta feature (polling a cada 60 s por aba aberta) — e
não cresce com o histórico lido. Declarado aqui **e** em `models.py` (`postgresql_where` +
`sqlite_where`): um `flask db migrate` futuro que não o veja no modelo proporia `drop_index` e
derrubaria o `startCommand`.

`created_at` é relógio de São Paulo (`now_sp`), não UTC como `audit_logs` — comparar as duas
tabelas erra 3 h de propósito documentado.

Revision ID: b7d2e4f1a9c3
Revises: a1c7d3e59b02
Create Date: 2026-09-02
"""

import sqlalchemy as sa
from alembic import op

revision = "b7d2e4f1a9c3"
down_revision = "a1c7d3e59b02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False, server_default="info"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=True),
        sa.Column("link_path", sa.String(length=300), nullable=True),
        sa.Column("entity_type", sa.String(length=30), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id", "id"])
    op.create_index(
        "ix_notifications_user_unread", "notifications", ["user_id", "id"],
        postgresql_where=sa.text("read_at IS NULL"),
        sqlite_where=sa.text("read_at IS NULL"),
    )
    op.create_index("ix_notifications_entity", "notifications", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_entity", table_name="notifications")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
