"""Conversas em equipe: responsável, espera, notas internas e respostas rápidas (feature 328).

Três colunas novas em ``conversas`` (``responsavel_id``, ``assumida_em`` e ``aguardando_desde``,
todas anuláveis) e duas tabelas: ``conversa_notas`` e ``respostas_rapidas``. Os avisos do sino usam a
tabela ``notifications`` da 272, sem coluna nova.

Aditiva: o código da 325 não enxerga as colunas nem as tabelas. Rollback = reverter o merge; o
``downgrade`` derruba as duas tabelas (as notas e as respostas rápidas guardadas nelas) e as colunas.

Revision ID: f328b2d4e6a1
Revises: e325a7c1d9f2
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op

revision = "f328b2d4e6a1"
down_revision = "e325a7c1d9f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "conversas",
        sa.Column(
            "responsavel_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id", name="fk_conversas_responsavel_id_users", ondelete="SET NULL"
            ),
            nullable=True,
        ),
    )
    op.add_column("conversas", sa.Column("assumida_em", sa.DateTime(), nullable=True))
    op.add_column("conversas", sa.Column("aguardando_desde", sa.DateTime(), nullable=True))
    op.create_index("ix_conversas_responsavel_id", "conversas", ["responsavel_id"])
    op.create_index("ix_conversas_aguardando_desde", "conversas", ["aguardando_desde"])

    op.create_table(
        "conversa_notas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversa_id",
            sa.Integer(),
            sa.ForeignKey(
                "conversas.id", name="fk_conversa_notas_conversa_id_conversas", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column(
            "autor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name="fk_conversa_notas_autor_id_users", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversa_notas_conversa_id", "conversa_notas", ["conversa_id"])

    op.create_table(
        "respostas_rapidas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("titulo", sa.String(80), nullable=False),
        sa.Column("atalho", sa.String(30), nullable=True),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column(
            "criado_por_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id", name="fk_respostas_rapidas_criado_por_id_users", ondelete="SET NULL"
            ),
            nullable=True,
        ),
        sa.Column(
            "alterado_por_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id", name="fk_respostas_rapidas_alterado_por_id_users", ondelete="SET NULL"
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    # "Pagamento" e "pagamento" não convivem: a unicidade do título ignora a caixa.
    op.create_index(
        "uq_respostas_rapidas_titulo", "respostas_rapidas", [sa.text("lower(titulo)")], unique=True
    )
    op.create_index("uq_respostas_rapidas_atalho", "respostas_rapidas", ["atalho"], unique=True)


def downgrade():
    op.drop_index("uq_respostas_rapidas_atalho", table_name="respostas_rapidas")
    op.drop_index("uq_respostas_rapidas_titulo", table_name="respostas_rapidas")
    op.drop_table("respostas_rapidas")
    op.drop_index("ix_conversa_notas_conversa_id", table_name="conversa_notas")
    op.drop_table("conversa_notas")
    op.drop_index("ix_conversas_aguardando_desde", table_name="conversas")
    op.drop_index("ix_conversas_responsavel_id", table_name="conversas")
    op.drop_column("conversas", "aguardando_desde")
    op.drop_column("conversas", "assumida_em")
    op.drop_column("conversas", "responsavel_id")
