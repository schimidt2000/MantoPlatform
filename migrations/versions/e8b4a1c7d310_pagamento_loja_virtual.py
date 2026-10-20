"""Pagamento da loja virtual ligado com segurança (feature 310).

Colunas novas, todas com default ou nulas:

- ``site_settings``: interruptor ``virtuais_pagamento_ativo`` (nasce DESLIGADO — R-18) e o segredo
  anterior do aviso aceito por 24 h depois de regerar (R-12).
- ``virtual_orders``: motivo do "liberado sem prova" (``unverified_reason``), código da recusa da
  operadora ao criar o link, recibo e o "a conferir" resolvido (R-07).
- ``virtual_payment_notifications``: ``state``/``attempts``/``last_attempt_at`` para o aviso ser
  processado fora da requisição e reprocessado (R2, R-06), e o "a conferir" resolvido. Backfill:
  linha antiga com ``outcome`` vira ``state='decidido'``, para a varredura não reprocessar o
  histórico da 205.
- ``virtual_campaigns``: ``listada`` (campanha fora da vitrine, R14).

Aditiva: o código anterior lê e grava no banco migrado. Rollback = reverter o merge; o ``downgrade``
só derruba as colunas.

Revision ID: e8b4a1c7d310
Revises: c5d2f7a9e306
Create Date: 2026-10-20
"""

import sqlalchemy as sa
from alembic import op

revision = "e8b4a1c7d310"
down_revision = "c5d2f7a9e306"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_settings") as batch:
        batch.add_column(
            sa.Column("virtuais_pagamento_ativo", sa.Boolean(), nullable=False,
                      server_default=sa.text("false"))
        )
        batch.add_column(sa.Column("infinitepay_webhook_token_anterior", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("infinitepay_webhook_token_anterior_ate", sa.DateTime(), nullable=True)
        )

    with op.batch_alter_table("virtual_orders") as batch:
        batch.add_column(sa.Column("unverified_reason", sa.String(24), nullable=True))
        batch.add_column(sa.Column("payment_link_error", sa.String(200), nullable=True))
        batch.add_column(sa.Column("receipt_url", sa.String(500), nullable=True))
        batch.add_column(sa.Column("conferido_em", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("conferido_por", sa.String(120), nullable=True))

    with op.batch_alter_table("virtual_payment_notifications") as batch:
        batch.add_column(
            sa.Column("state", sa.String(12), nullable=False, server_default="pendente")
        )
        batch.add_column(
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("last_attempt_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("resolvido_em", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("resolvido_por", sa.String(120), nullable=True))

    with op.batch_alter_table("virtual_campaigns") as batch:
        batch.add_column(
            sa.Column("listada", sa.Boolean(), nullable=False, server_default=sa.text("true"))
        )

    # O histórico da 205 já tem desfecho: não é trabalho pendente para a varredura nova.
    op.execute(
        "UPDATE virtual_payment_notifications SET state = 'decidido' WHERE outcome IS NOT NULL"
    )


def downgrade():
    with op.batch_alter_table("virtual_campaigns") as batch:
        batch.drop_column("listada")
    with op.batch_alter_table("virtual_payment_notifications") as batch:
        for coluna in ("resolvido_por", "resolvido_em", "last_attempt_at", "attempts", "state"):
            batch.drop_column(coluna)
    with op.batch_alter_table("virtual_orders") as batch:
        for coluna in ("conferido_por", "conferido_em", "receipt_url", "payment_link_error",
                       "unverified_reason"):
            batch.drop_column(coluna)
    with op.batch_alter_table("site_settings") as batch:
        for coluna in ("infinitepay_webhook_token_anterior_ate",
                       "infinitepay_webhook_token_anterior", "virtuais_pagamento_ativo"):
            batch.drop_column(coluna)
