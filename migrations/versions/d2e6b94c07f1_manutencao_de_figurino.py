"""Manutenção de figurino: tipo e gravidade no pedido (feature 225b).

O pedido deixa de ser só "produzir algo novo" e passa a cobrir também "mexer no que já existe":
conserto de defeito relatado num evento, ajuste para uma data, adaptação. A maior parte disso não
tem compra nenhuma — é trabalho manual que hoje se combina por voz e some.

`kind` nasce `producao` em todo pedido existente, então nenhum muda de comportamento.
`severity` é nulo fora da manutenção.

Revision ID: d2e6b94c07f1
Revises: c1d5a83b64e7
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op

revision = "d2e6b94c07f1"
down_revision = "c1d5a83b64e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "figurino_producoes",
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="producao"),
    )
    op.add_column(
        "figurino_producoes", sa.Column("severity", sa.String(length=20), nullable=True)
    )
    op.create_index("ix_figurino_producoes_kind", "figurino_producoes", ["kind"])
    # A pergunta quente é "esta ficha tem manutenção aberta que impede o uso?", feita para cada
    # ficha da lista e para cada cargo do elenco de um evento. O índice parcial mantém isso barato
    # sem inchar com as fichas que estão bem — que são a maioria.
    op.create_index(
        "ix_figurino_producoes_sheet_aberto",
        "figurino_producoes",
        ["figurino_sheet_id", "status"],
        postgresql_where=sa.text("figurino_sheet_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_figurino_producoes_sheet_aberto", table_name="figurino_producoes")
    op.drop_index("ix_figurino_producoes_kind", table_name="figurino_producoes")
    op.drop_column("figurino_producoes", "severity")
    op.drop_column("figurino_producoes", "kind")
