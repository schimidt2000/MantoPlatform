"""De qual anúncio veio cada cliente (feature 334).

Aditiva:
- ``conversa_anuncios``: cada contato pelo anúncio (ou publicação) na conversa;
- ``anuncios_meta``: o nome e a campanha de cada anúncio, pela consulta à Meta;
- ``clients``: o primeiro e o mais recente anúncio, com as datas.

O ``downgrade`` derruba as tabelas e as colunas (os contatos e as campanhas se perdem; a origem gravada
em ``lead_origin``/``utm_*`` fica).

Revision ID: d334b2c4e6f8
Revises: c333e1a5b7d9
Create Date: 2026-11-04
"""

import sqlalchemy as sa
from alembic import op

revision = "d334b2c4e6f8"
down_revision = "c333e1a5b7d9"
branch_labels = None
depends_on = None

COLUNAS_DA_FICHA = (
    ("anuncio_origem_id", sa.String(64)),
    ("anuncio_origem_em", sa.DateTime()),
    ("anuncio_recente_id", sa.String(64)),
    ("anuncio_recente_em", sa.DateTime()),
)


def upgrade():
    op.create_table(
        "conversa_anuncios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversa_id",
            sa.Integer(),
            sa.ForeignKey(
                "conversas.id", name="fk_conversa_anuncios_conversa_id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column("canal", sa.String(20), nullable=False),
        sa.Column("chave", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("anuncio_id", sa.String(64), nullable=True),
        sa.Column("titulo", sa.String(255), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("momento", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("chave", name="uq_conversa_anuncios_chave"),
    )
    op.create_index("ix_conversa_anuncios_conversa_id", "conversa_anuncios", ["conversa_id"])
    op.create_index("ix_conversa_anuncios_anuncio_id", "conversa_anuncios", ["anuncio_id"])
    op.create_table(
        "anuncios_meta",
        sa.Column("anuncio_id", sa.String(64), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=True),
        sa.Column("campanha_id", sa.String(64), nullable=True),
        sa.Column("campanha_nome", sa.String(255), nullable=True),
        sa.Column("consultado_em", sa.DateTime(), nullable=True),
        sa.Column("erro", sa.String(255), nullable=True),
        sa.Column("definitivo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    for nome, tipo in COLUNAS_DA_FICHA:
        op.add_column("clients", sa.Column(nome, tipo, nullable=True))


def downgrade():
    for nome, _ in reversed(COLUNAS_DA_FICHA):
        op.drop_column("clients", nome)
    op.drop_table("anuncios_meta")
    op.drop_index("ix_conversa_anuncios_anuncio_id", table_name="conversa_anuncios")
    op.drop_index("ix_conversa_anuncios_conversa_id", table_name="conversa_anuncios")
    op.drop_table("conversa_anuncios")
