"""acervo 3d com multiplos arquivos

Revision ID: d9e3a5b7c124
Revises: c8d2f4a6b013
Create Date: 2026-07-29

Migração escrita à mão (padrão do repo) para a feature 201: um mesmo presente 3D pode ter mais de
um arquivo (o modelo costuma vir fatiado em partes — corpo, argola, base). Cria
`acervo_3d_files` (1:N com `acervo_3d_items`), **migra os arquivos já cadastrados** para a tabela
nova e só então remove `acervo_3d_items.file_path`.

A ordem importa: o INSERT ... SELECT roda ANTES do DROP COLUMN, senão os arquivos das peças já
existentes seriam perdidos (o `file_path` era NOT NULL desde a c8d2f4a6b013, então toda peça
cadastrada vira exatamente uma linha em `acervo_3d_files`, na posição 0).
"""
import sqlalchemy as sa
from alembic import op

revision = "d9e3a5b7c124"
down_revision = "c8d2f4a6b013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "acervo_3d_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_id"], ["acervo_3d_items.id"],
            name="fk_acervo_3d_files_item_id", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_acervo_3d_files_item_id", "acervo_3d_files", ["item_id"])

    # Preserva o arquivo das peças já cadastradas antes de a coluna sumir.
    op.execute(
        """
        INSERT INTO acervo_3d_files (item_id, file_path, position, created_at)
        SELECT id, file_path, 0, created_at FROM acervo_3d_items
        """
    )

    with op.batch_alter_table("acervo_3d_items", schema=None) as batch_op:
        batch_op.drop_column("file_path")


def downgrade():
    """Volta ao arquivo único, ficando com o PRIMEIRO arquivo de cada peça (os demais somem).

    O NOT NULL só é restaurado se nenhuma peça ficou sem arquivo — a regra de negócio garante
    ≥1, mas um banco em estado inesperado não deve **apagar peças** só para satisfazer a
    constraint. Nesse caso a coluna fica nullable e o log avisa.
    """
    with op.batch_alter_table("acervo_3d_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("file_path", sa.String(500), nullable=True))

    op.execute(
        """
        UPDATE acervo_3d_items AS i
           SET file_path = f.file_path
        FROM (
            SELECT DISTINCT ON (item_id) item_id, file_path
            FROM acervo_3d_files ORDER BY item_id, position, id
        ) AS f
        WHERE f.item_id = i.id
        """
    )

    connection = op.get_bind()
    orphans = connection.execute(
        sa.text("SELECT COUNT(*) FROM acervo_3d_items WHERE file_path IS NULL")
    ).scalar()
    if orphans:
        print(f"[d9e3a5b7c124] {orphans} peça(s) sem arquivo — file_path fica nullable.")
    else:
        with op.batch_alter_table("acervo_3d_items", schema=None) as batch_op:
            batch_op.alter_column("file_path", nullable=False)

    op.drop_index("ix_acervo_3d_files_item_id", table_name="acervo_3d_files")
    op.drop_table("acervo_3d_files")
