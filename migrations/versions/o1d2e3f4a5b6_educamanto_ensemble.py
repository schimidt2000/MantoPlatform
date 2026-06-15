"""EducaManto: ensemble + catering por pessoa

Revision ID: o1d2e3f4a5b6
Revises: n0c1d2e3f4a5
Create Date: 2026-06-15

- Pacote ganha cachê do ensemble por cenário (350/600/300/550).
- Item ganha ensemble_add (quanto a qtd cresce por ensemble).
- Converte o catering de valor fixo para POR PESSOA, padronizado:
  ensaio R$28/pessoa; apresentação R$55/pessoa (1s) e R$73/pessoa (2s).
  A quantidade vira o headcount do pacote (qtd da "Ajuda de custo ensaio", ou 11).
  Os 3 itens (ajuda de custo, catering ensaio, catering apresentação) recebem ensemble_add=1.
"""
import sqlalchemy as sa
from alembic import op

revision = "o1d2e3f4a5b6"
down_revision = "n0c1d2e3f4a5"
branch_labels = None
depends_on = None

CATER_ENSAIO = "Catering ensaio"
CATER_APRES = "Catering apresentação"
AJUDA = "Ajuda de custo ensaio"

# Catering padronizado por pessoa (1s, 2s, 1s/dia, 2s/dia)
ENSAIO_PP = (28, 28, 28, 28)
APRES_PP = (55, 73, 55, 73)


def upgrade():
    with op.batch_alter_table("educamanto_packages") as b:
        b.add_column(sa.Column("ensemble_1s", sa.Float(), nullable=False, server_default="350"))
        b.add_column(sa.Column("ensemble_2s", sa.Float(), nullable=False, server_default="600"))
        b.add_column(sa.Column("ensemble_1s_days", sa.Float(), nullable=False, server_default="300"))
        b.add_column(sa.Column("ensemble_2s_days", sa.Float(), nullable=False, server_default="550"))
    with op.batch_alter_table("educamanto_items") as b:
        b.add_column(sa.Column("ensemble_add", sa.Integer(), nullable=False, server_default="0"))

    conn = op.get_bind()
    pkgs = conn.execute(sa.text("SELECT id FROM educamanto_packages")).fetchall()
    for (pkg_id,) in pkgs:
        # Headcount do pacote = qtd da "Ajuda de custo ensaio" (fallback 11).
        row = conn.execute(
            sa.text("SELECT qty FROM educamanto_items WHERE package_id=:p AND name=:n"),
            {"p": pkg_id, "n": AJUDA},
        ).fetchone()
        headcount = int(row[0]) if row and row[0] else 11

        conn.execute(
            sa.text("UPDATE educamanto_items SET ensemble_add=1 WHERE package_id=:p AND name=:n"),
            {"p": pkg_id, "n": AJUDA},
        )
        conn.execute(
            sa.text(
                "UPDATE educamanto_items SET qty=:q, cost_1s=:a, cost_2s=:b, "
                "cost_1s_days=:c, cost_2s_days=:d, ensemble_add=1 "
                "WHERE package_id=:p AND name=:n"
            ),
            {"q": headcount, "a": ENSAIO_PP[0], "b": ENSAIO_PP[1],
             "c": ENSAIO_PP[2], "d": ENSAIO_PP[3], "p": pkg_id, "n": CATER_ENSAIO},
        )
        conn.execute(
            sa.text(
                "UPDATE educamanto_items SET qty=:q, cost_1s=:a, cost_2s=:b, "
                "cost_1s_days=:c, cost_2s_days=:d, ensemble_add=1 "
                "WHERE package_id=:p AND name=:n"
            ),
            {"q": headcount, "a": APRES_PP[0], "b": APRES_PP[1],
             "c": APRES_PP[2], "d": APRES_PP[3], "p": pkg_id, "n": CATER_APRES},
        )


def downgrade():
    with op.batch_alter_table("educamanto_items") as b:
        b.drop_column("ensemble_add")
    with op.batch_alter_table("educamanto_packages") as b:
        b.drop_column("ensemble_2s_days")
        b.drop_column("ensemble_1s_days")
        b.drop_column("ensemble_2s")
        b.drop_column("ensemble_1s")
