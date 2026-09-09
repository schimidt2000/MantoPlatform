"""Conversão de vídeo, moldura e recados nas tags NFC (feature 297).

POR QUE ESTA MIGRATION EXISTE. Em 09/09/2026 descobriu-se que os dez vídeos anexados a tags NFC em
produção eram os arquivos crus da câmera: 1080x1920 e 2160x3840, de 23 a 76 Mbps, pesando de 42 a
147 MB para 14 a 42 segundos. Nenhum deles estava corrompido — todos eram H.264 válidos, servidos
corretamente com `206`. Eles simplesmente não cabem numa rede móvel, e dez deles na mesma tela
esgotam os decodificadores do navegador, que é o "arquivo está corrompido" que a equipe via.

A tabela `nfc_tag_deliveries` não guardava nada sobre o arquivo (nem peso, nem duração, nem tipo),
e por isso o problema ficou invisível por meses. As colunas novas servem às duas coisas: conduzir a
conversão e deixar o peso à vista na tela.

DECISÃO REGISTRADA: guarda-se um MESTRE 1080p sem moldura (`master_file_path`), não o arquivo cru.
O cru custaria de 42 a 147 MB por vídeo e estouraria a cota do backup de mídia no Drive, que já usa
6,5 GB dos 15 GB da conta de serviço. O mestre entrega a mesma reversibilidade por ~15 MB.

ARMADILHA EVITADA: `processing_status` nasce com server_default `'pronto'`. As dez entregas que já
existem continuam visíveis para a cliente sem NENHUM `UPDATE` de linha neste `upgrade` — elas são
vídeos que funcionam mal, não vídeos ausentes, e tirá-las do ar durante o deploy seria pior que o
defeito. Quem as converte é `flask nfc reprocessar`, rodado à mão depois, um vídeo por vez.

Revision ID: c9f4a2b71e60
Revises: b7d2e4f1a9c3
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from alembic import op

revision = "c9f4a2b71e60"
down_revision = "b7d2e4f1a9c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── nfc_tag_deliveries: o que se sabe do arquivo e em que pé está a conversão ──
    with op.batch_alter_table("nfc_tag_deliveries") as batch:
        batch.add_column(sa.Column("source_file_path", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("master_file_path", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("mime_type", sa.String(length=60), nullable=True))
        batch.add_column(sa.Column("file_size_bytes", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("duration_seconds", sa.Numeric(7, 2), nullable=True))
        batch.add_column(sa.Column("width", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("height", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "has_frame", sa.Boolean(), nullable=False, server_default=sa.text("false")
            )
        )
        batch.add_column(
            sa.Column(
                "processing_status", sa.String(length=20), nullable=False,
                server_default="pronto",
            )
        )
        batch.add_column(sa.Column("processing_error", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("processed_at", sa.DateTime(), nullable=True))

    # Índice PARCIAL: a fila é sempre minúscula perto da tabela, e o claim atômico roda a cada 20
    # segundos em cada um dos 3 workers. Espelha `app/models.py` (NfcTagDelivery.__table_args__).
    op.create_index(
        "ix_nfc_tag_deliveries_fila",
        "nfc_tag_deliveries",
        ["processing_status"],
        unique=False,
        postgresql_where=sa.text("processing_status <> 'pronto'"),
        sqlite_where=sa.text("processing_status <> 'pronto'"),
    )

    # ── nfc_tag_messages: o recado da cliente ──
    op.create_table(
        "nfc_tag_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("author_name", sa.String(length=120), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tag_id"], ["nfc_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nfc_tag_messages_tag", "nfc_tag_messages", ["tag_id", "created_at"])
    op.create_index("ix_nfc_tag_messages_client", "nfc_tag_messages", ["client_id"])

    # ── site_settings: os dois arquivos únicos do sistema (molde de `logo_path`) ──
    with op.batch_alter_table("site_settings") as batch:
        batch.add_column(sa.Column("nfc_frame_path", sa.String(length=300), nullable=True))
        batch.add_column(sa.Column("nfc_intro_video_path", sa.String(length=300), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("site_settings") as batch:
        batch.drop_column("nfc_intro_video_path")
        batch.drop_column("nfc_frame_path")

    op.drop_index("ix_nfc_tag_messages_client", table_name="nfc_tag_messages")
    op.drop_index("ix_nfc_tag_messages_tag", table_name="nfc_tag_messages")
    op.drop_table("nfc_tag_messages")

    op.drop_index("ix_nfc_tag_deliveries_fila", table_name="nfc_tag_deliveries")
    with op.batch_alter_table("nfc_tag_deliveries") as batch:
        batch.drop_column("processed_at")
        batch.drop_column("processing_error")
        batch.drop_column("processing_status")
        batch.drop_column("has_frame")
        batch.drop_column("height")
        batch.drop_column("width")
        batch.drop_column("duration_seconds")
        batch.drop_column("file_size_bytes")
        batch.drop_column("mime_type")
        batch.drop_column("master_file_path")
        batch.drop_column("source_file_path")
