"""talento estrangeiro (cpf opcional) + telefone com codigo de pais (feature 092)

Revision ID: a3d4e5f6a7b8
Revises: z2c3d4e5f6a7
Create Date: 2026-06-29

- Adiciona talents.is_foreigner (default false) para marcar talentos estrangeiros sem CPF.
- Torna talents.cpf nullable (estrangeiros gravam cpf = NULL; UNIQUE permite multiplos NULL no Postgres).
- Prefixa '+55 ' a todos os telefones existentes que ainda nao tenham codigo de pais (nao comecam com '+'),
  pois foram preenchidos so com DDD. Nao duplica para os que ja tenham '+'.

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "a3d4e5f6a7b8"
down_revision = "z2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "talents",
        sa.Column("is_foreigner", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.alter_column("talents", "cpf", existing_type=sa.String(length=20), nullable=True)
    # Telefones existentes vieram so com DDD: prefixa o codigo do Brasil. Nao duplica para quem ja tem '+'.
    op.execute(
        "UPDATE talents SET phone = '+55 ' || phone "
        "WHERE phone IS NOT NULL AND btrim(phone) <> '' AND phone NOT LIKE '+%'"
    )


def downgrade():
    # Remove o prefixo '+55 ' inserido no upgrade (apenas quando exatamente nesse formato).
    op.execute(
        "UPDATE talents SET phone = substring(phone from 5) "
        "WHERE phone LIKE '+55 %'"
    )
    op.alter_column("talents", "cpf", existing_type=sa.String(length=20), nullable=False)
    op.drop_column("talents", "is_foreigner")
