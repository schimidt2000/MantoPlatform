"""O casting vê o que está fechando (feature 322).

Três colunas novas em ``event_roles``, todas nulas e sem backfill (o dono decidiu: sem retroativo):

- ``perfil_vendido``: o tipo que o orçamento vendeu, em texto para ler ("Cantor · show · com
  maquiagem").
- ``criada_pelo_sistema``: a vaga nasceu de uma regra do sistema (coordenador/técnico garantidos,
  extras do orçamento, maquiador automático).
- ``escalado_pelo_comercial``: o talento atual entrou pelo formulário do evento.

Aditiva: o código anterior lê e grava no banco migrado. Rollback = reverter o merge; o ``downgrade``
só derruba as colunas.

Revision ID: c322a7e1b9d4
Revises: e8b4a1c7d310
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "c322a7e1b9d4"
down_revision = "e8b4a1c7d310"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("event_roles") as batch:
        batch.add_column(sa.Column("perfil_vendido", sa.String(200), nullable=True))
        batch.add_column(sa.Column("criada_pelo_sistema", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("escalado_pelo_comercial", sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table("event_roles") as batch:
        batch.drop_column("escalado_pelo_comercial")
        batch.drop_column("criada_pelo_sistema")
        batch.drop_column("perfil_vendido")
