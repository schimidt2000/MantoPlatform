"""users: has_access + email/password_hash opcionais (pessoa só de pagamento)

Revision ID: n0c1d2e3f4a5
Revises: l8a9b0c1d2e3
Create Date: 2026-06-12

Permite cadastrar pessoas que recebem salário mas não têm login:
- has_access: False = nunca pode logar (default True preserva usuários atuais)
- email/password_hash viram nullable (sem acesso = sem credenciais)
"""
import sqlalchemy as sa
from alembic import op

revision = "n0c1d2e3f4a5"
down_revision = "l8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("has_access", sa.Boolean(), nullable=False, server_default="1")
        )
        batch_op.alter_column(
            "email", existing_type=sa.String(120), nullable=True
        )
        batch_op.alter_column(
            "password_hash", existing_type=sa.String(255), nullable=True
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash", existing_type=sa.String(255), nullable=False
        )
        batch_op.alter_column(
            "email", existing_type=sa.String(120), nullable=False
        )
        batch_op.drop_column("has_access")
