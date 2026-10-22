"""O pedido de cancelamento ganha o alcance e a devolução combinada (feature 315).

O pedido continua morando no evento, nas três colunas da 224 (`deletion_requested_at`, `_by_id`,
`deletion_request_reason`). A 315 acrescenta duas, nulas:
- `deletion_request_scope` — o alcance numa venda de vários dias, no vocabulário do cancelar da 306
  (`todos` | `so_este_dia`; "so_este_dia" tem 11 caracteres). Nulo = sem pedido, pedido de antes do
  deploy ou feito pelo caminho velho — lido como "todos".
- `deletion_request_refund` — a devolução combinada com a cliente (Q2 = B), JSON em texto como o
  resto da casa (`{"devolucao": {modo, valor, nome, pix}, "venda_nova"}`, valores em texto decimal).

Aditiva: nenhuma coluna existente muda, e o código anterior lê e grava no banco migrado (ignora as
duas). Sem backfill: o pedido pendente de hoje fica "sem devolução informada".

Rollback: reverter o merge basta; o pedido feito no meio-tempo continua pendente pelas três colunas
da 224. O `downgrade` apaga o alcance e a devolução combinada de pedidos pendentes (inclusive nome e
PIX) — nunca dinheiro.

Revision ID: d8b4e15f2c31
Revises: c5d2f7a9e306
Create Date: 2026-10-22
"""

import sqlalchemy as sa
from alembic import op

revision = "d8b4e15f2c31"
down_revision = "c5d2f7a9e306"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calendar_events", sa.Column("deletion_request_scope", sa.String(length=16), nullable=True))
    op.add_column("calendar_events", sa.Column("deletion_request_refund", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("calendar_events", "deletion_request_refund")
    op.drop_column("calendar_events", "deletion_request_scope")
