"""Conferência de personagens do catálogo (feature 360).

Aditiva: duas tabelas novas, vazias. ``catalog_conferencias`` guarda a leitura das fotos de um item e
o que foi decidido; ``catalog_conferencia_personagens``, cada personagem proposto. Nenhuma tabela
existente muda e nenhum dado é carregado aqui: a leitura entra depois, por ação explícita do
Superadmin (``POST /api/admin/catalogo/conferencia/carregar``), para que um problema no dado nunca
derrube o ``flask db upgrade`` do start.

Toda FK tem ``ON DELETE``: excluir item leva a conferência junto (CASCADE); excluir foto, ficha ou
usuário só anula a referência (SET NULL). Nada aqui trava uma exclusão que já funcionava.

O ``downgrade`` derruba as duas tabelas; a conferência feita se perde, a leitura continua no arquivo.

Revision ID: f360a1b2c3d4
Revises: f353a1b2c3d4
Create Date: 2026-11-24
"""

import sqlalchemy as sa
from alembic import op

revision = "f360a1b2c3d4"
down_revision = "f353a1b2c3d4"
branch_labels = None
depends_on = None

TIPOS = "('tema','dupla','avulso','generico')"


def _fk(coluna: str, alvo: str, tabela: str, ondelete: str, nullable: bool = True) -> sa.Column:
    return sa.Column(
        coluna,
        sa.Integer(),
        sa.ForeignKey(alvo, name=f"fk_{tabela}_{coluna}", ondelete=ondelete),
        nullable=nullable,
    )


def upgrade():
    tabela = "catalog_conferencias"
    op.create_table(
        tabela,
        sa.Column("id", sa.Integer(), primary_key=True),
        _fk("catalog_item_id", "catalog_items.id", tabela, "CASCADE", nullable=False),
        sa.Column("tipo_lido", sa.String(10), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("acao", sa.Text(), nullable=True),
        sa.Column("grupo", sa.String(120), nullable=True),
        _fk("ficha_sugerida_id", "figurino_sheets.id", tabela, "SET NULL"),
        _fk("ficha_id", "figurino_sheets.id", tabela, "SET NULL"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("lote", sa.String(10), nullable=True),
        sa.Column("conferido_em", sa.DateTime(), nullable=True),
        _fk("conferido_por_id", "users.id", tabela, "SET NULL"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("catalog_item_id", name="uq_catalog_conferencias_item"),
        sa.CheckConstraint(f"tipo_lido IN {TIPOS}", name="ck_catalog_conferencias_tipo_lido"),
        sa.CheckConstraint(f"tipo IN {TIPOS}", name="ck_catalog_conferencias_tipo"),
    )

    filha = "catalog_conferencia_personagens"
    op.create_table(
        filha,
        sa.Column("id", sa.Integer(), primary_key=True),
        _fk("conferencia_id", "catalog_conferencias.id", filha, "CASCADE", nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("origem", sa.String(10), nullable=False, server_default="leitura"),
        sa.Column("nome_lido", sa.String(200), nullable=True),
        sa.Column("nome", sa.String(200), nullable=False),
        _fk("imagem_id", "catalog_item_images.id", filha, "SET NULL"),
        sa.Column("recorte", sa.Text(), nullable=True),
        sa.Column("foto_largura", sa.Integer(), nullable=True),
        sa.Column("foto_altura", sa.Integer(), nullable=True),
        _fk("ficha_sugerida_id", "figurino_sheets.id", filha, "SET NULL"),
        _fk("ficha_id", "figurino_sheets.id", filha, "SET NULL"),
        sa.Column("aviso", sa.Text(), nullable=True),
        sa.Column("sem_foto_lido", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sem_foto", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("decisao", sa.String(10), nullable=False, server_default="criar"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "origem IN ('leitura','manual')", name="ck_catalog_conf_personagens_origem"
        ),
        sa.CheckConstraint(
            "decisao IN ('criar','nao_criar')", name="ck_catalog_conf_personagens_decisao"
        ),
    )
    op.create_index("ix_catalog_conferencia_personagens_conferencia_id", filha, ["conferencia_id"])


def downgrade():
    op.drop_index(
        "ix_catalog_conferencia_personagens_conferencia_id",
        table_name="catalog_conferencia_personagens",
    )
    op.drop_table("catalog_conferencia_personagens")
    op.drop_table("catalog_conferencias")
