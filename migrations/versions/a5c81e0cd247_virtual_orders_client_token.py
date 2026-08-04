"""client_token do pedido e lock da varredura virtual

Revision ID: a5c81e0cd247
Revises: f3a9c72e5d18
Create Date: 2026-07-31

Migração escrita à mão (padrão do repo), aditiva, complementando a feature 205 (US2).

1. **`virtual_orders.client_token`** — o token que o navegador da família envia ao reservar. É o
   que faz o duplo clique devolver o **mesmo** pedido em vez de travar um segundo horário (FR-026).
   Por que não reaproveitar `origin_hash`: ele identifica a origem (IP + User-Agent com sal), e
   duas famílias atrás do mesmo NAT — prédio, escola, operadora móvel — compartilham origem. Usá-lo
   como chave de idempotência entregaria o pedido de uma família para a outra, com nome e telefone
   de criança junto.

2. **`site_settings.virtual_sweep_at`** — marcador do último ciclo da varredura que expira as
   reservas. Serve de lock de execução única entre os workers do gunicorn, no mesmo modelo de
   `calendar_auto_sync_at` (FR-057a). Sem ele, dois processos expirariam a mesma reserva ao mesmo
   tempo, que é exatamente a corrida que o soft lock existe para evitar.

Migração separada da `f3a9c72e5d18` porque aquela já foi aplicada; reescrevê-la faria bancos que já
rodaram o upgrade divergirem em silêncio.
"""
import sqlalchemy as sa
from alembic import op

revision = "a5c81e0cd247"
down_revision = "f3a9c72e5d18"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("virtual_orders", sa.Column("client_token", sa.String(64), nullable=True))
    op.add_column("site_settings", sa.Column("virtual_sweep_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("site_settings", "virtual_sweep_at")
    op.drop_column("virtual_orders", "client_token")
