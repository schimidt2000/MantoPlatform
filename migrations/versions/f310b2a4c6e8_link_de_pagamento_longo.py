"""Link de pagamento sem teto de tamanho (hotfix 310b).

``virtual_orders.payment_url`` passa de ``VARCHAR(500)`` para ``TEXT``. O link da InfinitePay carrega
a cobrança inteira codificada num parâmetro só e passou de 500 caracteres em 11/11/2026: a gravação
falhava, a reserva respondia 500 e a família ficava sem botão de pagar.

No PostgreSQL, ``VARCHAR(n)`` → ``TEXT`` é só metadado (sem reescrever a tabela nem travá-la além do
instante da troca). O código anterior grava e lê a coluna do mesmo jeito.

Rollback = reverter o merge. O ``downgrade`` volta a ``VARCHAR(500)`` e anula os links mais longos
(um link cortado não abre; anulado, a página do pedido mostra "Gerando o pagamento…" até a reserva
vencer, como antes).

Revision ID: f310b2a4c6e8
Revises: d342a7c1e9f3
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "f310b2a4c6e8"
down_revision = "d342a7c1e9f3"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "virtual_orders",
        "payment_url",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "virtual_orders",
        "payment_url",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True,
        postgresql_using="CASE WHEN length(payment_url) > 500 THEN NULL ELSE payment_url END",
    )
