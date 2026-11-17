"""Conversas: o WhatsApp da Manto dentro da Plataforma (feature 325).

Quatro tabelas novas: ``whatsapp_avisos`` (o POST cru da Meta, gravado antes de processar),
``conversas`` (um contato num canal), ``conversa_mensagens`` e ``conversa_midias``. Nenhuma coluna
existente muda; ``clients`` só ganha FKs apontando para ela (SET NULL).

Aditiva: o código anterior não enxerga as tabelas. Rollback = reverter o merge; o ``downgrade``
derruba as quatro tabelas (e as conversas guardadas nelas).

Revision ID: e325a7c1d9f2
Revises: f345c0a1b2d3
Create Date: 2026-10-30
"""

import sqlalchemy as sa
from alembic import op

revision = "e325a7c1d9f2"
down_revision = "f345c0a1b2d3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "whatsapp_avisos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("erro", sa.String(500), nullable=True),
        sa.Column("recebido_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("tentado_em", sa.DateTime(), nullable=True),
        sa.Column("processado_em", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_whatsapp_avisos_estado", "whatsapp_avisos", ["estado"])

    op.create_table(
        "conversas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canal", sa.String(20), nullable=False),
        sa.Column("contato_id", sa.String(64), nullable=False),
        sa.Column("contato_bsuid", sa.String(64), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("nome_perfil", sa.String(255), nullable=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", name="fk_conversas_client_id_clients", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ultima_recebida_em", sa.DateTime(), nullable=True),
        sa.Column("ultima_mensagem_em", sa.DateTime(), nullable=True),
        sa.Column("ultima_previa", sa.String(200), nullable=True),
        sa.Column("nao_lidas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("canal", "contato_id", name="uq_conversas_canal_contato"),
    )
    op.create_index("ix_conversas_telefone", "conversas", ["telefone"])
    op.create_index("ix_conversas_client_id", "conversas", ["client_id"])
    op.create_index("ix_conversas_ultima_mensagem_em", "conversas", ["ultima_mensagem_em"])

    op.create_table(
        "conversa_mensagens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversa_id",
            sa.Integer(),
            sa.ForeignKey(
                "conversas.id",
                name="fk_conversa_mensagens_conversa_id_conversas",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("direcao", sa.String(10), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("externo_id", sa.String(128), nullable=True),
        sa.Column("chave_envio", sa.String(64), nullable=True),
        sa.Column("situacao", sa.String(12), nullable=False),
        sa.Column("erro_codigo", sa.Integer(), nullable=True),
        sa.Column("erro_motivo", sa.String(500), nullable=True),
        sa.Column(
            "autor_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id", name="fk_conversa_mensagens_autor_id_users", ondelete="SET NULL"
            ),
            nullable=True,
        ),
        sa.Column("origem", sa.String(12), nullable=False),
        sa.Column("modelo_nome", sa.String(255), nullable=True),
        sa.Column("resposta_a", sa.String(128), nullable=True),
        sa.Column("dados", sa.Text(), nullable=True),
        sa.Column("momento", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("externo_id", name="uq_conversa_mensagens_externo_id"),
        sa.UniqueConstraint("chave_envio", name="uq_conversa_mensagens_chave_envio"),
    )
    op.create_index(
        "ix_conversa_mensagens_conversa_momento", "conversa_mensagens", ["conversa_id", "momento"]
    )

    op.create_table(
        "conversa_midias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "mensagem_id",
            sa.Integer(),
            sa.ForeignKey(
                "conversa_mensagens.id",
                name="fk_conversa_midias_mensagem_id_conversa_mensagens",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("externo_id", sa.String(128), nullable=True),
        sa.Column("mime", sa.String(120), nullable=True),
        sa.Column("tamanho", sa.Integer(), nullable=True),
        sa.Column("nome_original", sa.String(255), nullable=True),
        sa.Column("caminho", sa.String(500), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="pendente"),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("erro", sa.String(500), nullable=True),
        sa.Column("tentado_em", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("mensagem_id", name="uq_conversa_midias_mensagem_id"),
    )
    op.create_index("ix_conversa_midias_estado", "conversa_midias", ["estado"])


def downgrade():
    op.drop_index("ix_conversa_midias_estado", table_name="conversa_midias")
    op.drop_table("conversa_midias")
    op.drop_index("ix_conversa_mensagens_conversa_momento", table_name="conversa_mensagens")
    op.drop_table("conversa_mensagens")
    op.drop_index("ix_conversas_ultima_mensagem_em", table_name="conversas")
    op.drop_index("ix_conversas_client_id", table_name="conversas")
    op.drop_index("ix_conversas_telefone", table_name="conversas")
    op.drop_table("conversas")
    op.drop_index("ix_whatsapp_avisos_estado", table_name="whatsapp_avisos")
    op.drop_table("whatsapp_avisos")
