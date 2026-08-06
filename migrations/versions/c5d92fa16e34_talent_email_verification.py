"""Confirmação do email no cadastro público (feature 219).

`talents.email_verified_at` + `email_verify_token` + `email_verify_sent_at`: o talento confirma o
próprio email logo depois de enviar o formulário (com o cadastro já gravado), e o token é a
credencial da tela de sucesso para corrigir o endereço e reenviar sem refazer nada.

Revision ID: c5d92fa16e34
Revises: b4c81ef07d29
Create Date: 2026-08-06
"""

import sqlalchemy as sa
from alembic import op

revision = "c5d92fa16e34"
down_revision = "b4c81ef07d29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("talents", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    op.add_column("talents", sa.Column("email_verify_token", sa.String(length=80), nullable=True))
    op.add_column("talents", sa.Column("email_verify_sent_at", sa.DateTime(), nullable=True))
    op.create_unique_constraint(
        "uq_talents_email_verify_token", "talents", ["email_verify_token"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_talents_email_verify_token", "talents", type_="unique")
    op.drop_column("talents", "email_verify_sent_at")
    op.drop_column("talents", "email_verify_token")
    op.drop_column("talents", "email_verified_at")
