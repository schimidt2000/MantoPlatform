"""A base autorizada (feature 350).

Aditiva:
- ``parceiros``: buffet, assessoria, agência ou outro, com a comissão declarada;
- ``clients``: versão do texto aceito, última retirada, indicado por e parceiro;
- ``cliente_consentimentos``: o histórico de aceites e retiradas (append-only);
- ``cliente_criancas``: o aniversário das crianças com aceite da responsável;
- ``pos_eventos``: o pós-evento único de cada evento (copiado ou enviado pela conversa).

O ``downgrade`` derruba as tabelas e as colunas (o histórico, as crianças, os parceiros e os registros
do pós-evento se perdem; o aceite atual em ``marketing_opt_in_*`` fica).

Nasceu encadeada em ``d334b2c4e6f8``, como a 348, a 349 e a 351; no lote de 17/11 foi reencadeada na
fila 348 → 349 → 350 → 351.

Revision ID: a350b1c2d3e4
Revises: a349c0e1f2a3
Create Date: 2026-11-17
"""

import sqlalchemy as sa
from alembic import op

revision = "a350b1c2d3e4"
down_revision = "a349c0e1f2a3"
branch_labels = None
depends_on = None

COLUNAS_SIMPLES_DA_FICHA = (
    ("marketing_opt_in_version", sa.String(20)),
    ("marketing_opt_out_at", sa.DateTime()),
    ("marketing_opt_out_source", sa.String(160)),
)


def _criar_parceiros() -> None:
    op.create_table(
        "parceiros",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("contato", sa.String(120), nullable=True),
        sa.Column("telefone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("comissao_percentual", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_parceiros_nome", "parceiros", ["nome"])


def _colunas_da_ficha() -> None:
    for nome, tipo in COLUNAS_SIMPLES_DA_FICHA:
        op.add_column("clients", sa.Column(nome, tipo, nullable=True))
    op.add_column("clients", sa.Column("indicado_por_id", sa.Integer(), nullable=True))
    op.add_column("clients", sa.Column("parceiro_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_clients_indicado_por_id",
        "clients",
        "clients",
        ["indicado_por_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_clients_parceiro_id",
        "clients",
        "parceiros",
        ["parceiro_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_clients_indicado_por_id", "clients", ["indicado_por_id"])
    op.create_index("ix_clients_parceiro_id", "clients", ["parceiro_id"])


def _criar_consentimentos() -> None:
    op.create_table(
        "cliente_consentimentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("acao", sa.String(10), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("versao", sa.String(20), nullable=False),
        sa.Column("origem", sa.String(160), nullable=False),
        sa.Column("referencia", sa.String(80), nullable=True),
        sa.Column(
            "registrado_por_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("registrado_em", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_cliente_consentimentos_client", "cliente_consentimentos", ["client_id", "registrado_em"]
    )


def _criar_criancas() -> None:
    op.create_table(
        "cliente_criancas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("primeiro_nome", sa.String(60), nullable=False),
        sa.Column("nascimento", sa.Date(), nullable=False),
        sa.Column("aceite_em", sa.DateTime(), nullable=False),
        sa.Column("aceite_versao", sa.String(20), nullable=False),
        sa.Column("aceite_origem", sa.String(160), nullable=False),
        sa.Column(
            "registrado_por_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_cliente_criancas_client", "cliente_criancas", ["client_id"])


def _criar_pos_eventos() -> None:
    op.create_table(
        "pos_eventos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("calendar_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fotos_url", sa.String(500), nullable=True),
        sa.Column("canal", sa.String(12), nullable=False),
        sa.Column(
            "mensagem_id",
            sa.Integer(),
            sa.ForeignKey("conversa_mensagens.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "registrado_por_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("registrado_em", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_pos_eventos_event_id"),
    )


def upgrade() -> None:
    _criar_parceiros()
    _colunas_da_ficha()
    _criar_consentimentos()
    _criar_criancas()
    _criar_pos_eventos()


def downgrade() -> None:
    op.drop_table("pos_eventos")
    op.drop_index("ix_cliente_criancas_client", table_name="cliente_criancas")
    op.drop_table("cliente_criancas")
    op.drop_index("ix_cliente_consentimentos_client", table_name="cliente_consentimentos")
    op.drop_table("cliente_consentimentos")
    op.drop_index("ix_clients_parceiro_id", table_name="clients")
    op.drop_index("ix_clients_indicado_por_id", table_name="clients")
    op.drop_constraint("fk_clients_parceiro_id", "clients", type_="foreignkey")
    op.drop_constraint("fk_clients_indicado_por_id", "clients", type_="foreignkey")
    op.drop_column("clients", "parceiro_id")
    op.drop_column("clients", "indicado_por_id")
    for nome, _tipo in reversed(COLUNAS_SIMPLES_DA_FICHA):
        op.drop_column("clients", nome)
    op.drop_index("ix_parceiros_nome", table_name="parceiros")
    op.drop_table("parceiros")
