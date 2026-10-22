"""Contratos da ClickSign ligados à venda: três tabelas e sete colunas (feature 317).

A Manto passa a espelhar os envelopes da conta ClickSign (`clicksign_documentos`), a lembrar o par
documento × venda que a comercial desligou (`clicksign_desvinculos`) e cada "Cobrar contrato"
(`clicksign_cobrancas`). Em `site_settings` entram o aviso cadastrado (id e segredo, com o anterior
por 24 h) e o lock, o marco e o "repetir" da sincronização.

Aditiva: nenhuma coluna existente muda; as colunas novas de `site_settings` são nulas ou têm
`server_default`, e o código anterior lê e grava no banco migrado. As colunas antigas
`clicksign_token` e `clicksign_sandbox` continuam como estão (inertes; dívida no `docs/05`).

Rollback: reverter o merge, sem `downgrade`, é limpo — as tabelas novas ficam paradas e nada do
código antigo as lê. O `downgrade` apaga o espelho, os desvínculos e o histórico de cobranças; o
espelho se refaz com `flask clicksign-sincronizar`, os outros dois não voltam. Os PDFs assinados
anexados viram `event_contracts` comuns e ficam.

Revision ID: d3c7a1e5b317
Revises: c5d2f7a9e306
Create Date: 2026-10-22
"""

import sqlalchemy as sa
from alembic import op

revision = "d3c7a1e5b317"
down_revision = "c5d2f7a9e306"
branch_labels = None
depends_on = None

_COLUNAS_DO_SITE_SETTING = (
    sa.Column("clicksign_webhook_id", sa.String(36), nullable=True),
    sa.Column("clicksign_webhook_secret", sa.String(64), nullable=True),
    sa.Column("clicksign_webhook_secret_anterior", sa.String(64), nullable=True),
    sa.Column("clicksign_webhook_secret_anterior_ate", sa.DateTime(), nullable=True),
    sa.Column("clicksign_sync_at", sa.DateTime(), nullable=True),
    sa.Column("clicksign_sync_cursor", sa.DateTime(), nullable=True),
    sa.Column("clicksign_sync_pendente", sa.Boolean(), nullable=False, server_default=sa.false()),
)


def upgrade() -> None:
    op.create_table(
        "clicksign_documentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("envelope_id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=True),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("recusado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("prazo", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=True),
        sa.Column("modificado_em", sa.DateTime(), nullable=True),
        sa.Column("assinado_em", sa.DateTime(), nullable=True),
        sa.Column("cancelado_em", sa.DateTime(), nullable=True),
        sa.Column("signatario_nome", sa.String(200), nullable=True),
        sa.Column("signatario_telefone", sa.String(20), nullable=True),
        sa.Column("signatario_email", sa.String(200), nullable=True),
        sa.Column("canal", sa.String(10), nullable=True),
        sa.Column("data_lida", sa.Date(), nullable=True),
        sa.Column("telefone_lido", sa.String(20), nullable=True),
        sa.Column("tema_lido", sa.String(200), nullable=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("calendar_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("vinculo", sa.String(12), nullable=False),
        sa.Column("vinculo_origem", sa.String(10), nullable=True),
        sa.Column("vinculo_motivo", sa.String(40), nullable=True),
        sa.Column(
            "vinculado_por_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("vinculado_em", sa.DateTime(), nullable=True),
        sa.Column(
            "contrato_anexo_id",
            sa.Integer(),
            sa.ForeignKey("event_contracts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("anexo_pendente", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sincronizado_em", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("envelope_id", name="uq_clicksign_documentos_envelope"),
    )
    op.create_index("ix_clicksign_documentos_event_id", "clicksign_documentos", ["event_id"])
    op.create_index("ix_clicksign_documentos_data_lida", "clicksign_documentos", ["data_lida"])
    op.create_index(
        "ix_clicksign_documentos_a_conferir",
        "clicksign_documentos",
        ["vinculo"],
        postgresql_where=sa.text("vinculo = 'a_conferir'"),
        sqlite_where=sa.text("vinculo = 'a_conferir'"),
    )

    op.create_table(
        "clicksign_desvinculos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "documento_id",
            sa.Integer(),
            sa.ForeignKey("clicksign_documentos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("calendar_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "por_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("em", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("documento_id", "event_id", name="uq_clicksign_desvinculo"),
    )

    op.create_table(
        "clicksign_cobrancas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "documento_id",
            sa.Integer(),
            sa.ForeignKey("clicksign_documentos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("calendar_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("usuario_nome", sa.String(120), nullable=False),
        sa.Column("em", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_clicksign_cobrancas_documento_em", "clicksign_cobrancas", ["documento_id", "em"]
    )

    for coluna in _COLUNAS_DO_SITE_SETTING:
        op.add_column("site_settings", coluna.copy())


def downgrade() -> None:
    for coluna in reversed(_COLUNAS_DO_SITE_SETTING):
        op.drop_column("site_settings", coluna.name)
    op.drop_index("ix_clicksign_cobrancas_documento_em", table_name="clicksign_cobrancas")
    op.drop_table("clicksign_cobrancas")
    op.drop_table("clicksign_desvinculos")
    op.drop_index("ix_clicksign_documentos_a_conferir", table_name="clicksign_documentos")
    op.drop_index("ix_clicksign_documentos_data_lida", table_name="clicksign_documentos")
    op.drop_index("ix_clicksign_documentos_event_id", table_name="clicksign_documentos")
    op.drop_table("clicksign_documentos")
