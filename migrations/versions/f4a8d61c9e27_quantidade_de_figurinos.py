"""Quantidade de figurinos iguais por ficha (feature 235).

A ficha descrevia o figurino de um personagem sem dizer **quantos** existem. Na logística isso
é a diferença entre poder ou não atender dois eventos no mesmo dia com o mesmo personagem: hoje
a informação vive na cabeça de quem separa o figurino.

`figurino_sheets.quantity` guarda quantos figurinos IGUAIS a Manto tem daquela ficha. O padrão
é 1 (o acervo atual — 616 fichas — foi cadastrado assumindo uma peça por ficha), e 0 é válido:
ficha cadastrada de um figurino que ainda não foi produzido (o pedido vive em
`figurino_producoes`).

Revision ID: f4a8d61c9e27
Revises: e3f7c25a8b90
Create Date: 2026-08-11
"""

import sqlalchemy as sa
from alembic import op

revision = "f4a8d61c9e27"
down_revision = "e3f7c25a8b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "figurino_sheets",
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("figurino_sheets", "quantity")
