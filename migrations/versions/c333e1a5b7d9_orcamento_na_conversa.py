"""Orçamento pela conversa (feature 333).

Aditiva:
- ``orcamento_history.client_id``: a ficha da cliente (FK ``clients``, SET NULL);
- ``conversas.ficha_manual``: a ficha foi escolhida à mão (a ligação automática não age);
- ``orcamento_envios``: cada orçamento mandado pela conversa.

O ``downgrade`` derruba a tabela e as duas colunas (os envios e as ligações se perdem).

Revision ID: c333e1a5b7d9
Revises: b332d5f7a9c1
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op

revision = "c333e1a5b7d9"
down_revision = "b332d5f7a9c1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orcamento_history", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_orcamento_history_client_id_clients",
        "orcamento_history",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orcamento_history_client_id", "orcamento_history", ["client_id"])
    op.add_column(
        "conversas",
        sa.Column("ficha_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "orcamento_envios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "orcamento_id",
            sa.Integer(),
            sa.ForeignKey(
                "orcamento_history.id", name="fk_orcamento_envios_orcamento_id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column(
            "conversa_id",
            sa.Integer(),
            sa.ForeignKey(
                "conversas.id", name="fk_orcamento_envios_conversa_id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column(
            "autor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name="fk_orcamento_envios_autor_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("chave_envio", sa.String(64), nullable=False),
        sa.Column(
            "texto_mensagem_id",
            sa.Integer(),
            sa.ForeignKey(
                "conversa_mensagens.id",
                name="fk_orcamento_envios_texto_mensagem_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column(
            "pdf_mensagem_id",
            sa.Integer(),
            sa.ForeignKey(
                "conversa_mensagens.id",
                name="fk_orcamento_envios_pdf_mensagem_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("chave_envio", name="uq_orcamento_envios_chave"),
    )
    op.create_index("ix_orcamento_envios_orcamento_id", "orcamento_envios", ["orcamento_id"])
    op.create_index("ix_orcamento_envios_conversa_id", "orcamento_envios", ["conversa_id"])


def downgrade():
    op.drop_index("ix_orcamento_envios_conversa_id", table_name="orcamento_envios")
    op.drop_index("ix_orcamento_envios_orcamento_id", table_name="orcamento_envios")
    op.drop_table("orcamento_envios")
    op.drop_column("conversas", "ficha_manual")
    op.drop_index("ix_orcamento_history_client_id", table_name="orcamento_history")
    op.drop_constraint(
        "fk_orcamento_history_client_id_clients", "orcamento_history", type_="foreignkey"
    )
    op.drop_column("orcamento_history", "client_id")
