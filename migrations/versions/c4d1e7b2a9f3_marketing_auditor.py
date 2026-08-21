"""Auditor de marketing semanal (feature 256).

Histórico das métricas lidas dos exports da Meta/Google (post = fotografia; campanha e conta =
por período/dia), registro das rodadas e dos arquivos lidos, e o lote de reembolso que liga o
gasto de anúncios de um mês civil ao Gasto Extra gerado para o titular do cartão. Também o link
do post publicado no card de marketing (chave do cruzamento) e a origem/utms do lead no cliente
(atribuição campanha → lead → evento).

Tudo aditivo: nenhuma coluna existente muda; `downgrade()` remove na ordem inversa.

Revision ID: c4d1e7b2a9f3
Revises: b3f8d27a9e14
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "c4d1e7b2a9f3"
down_revision = "b3f8d27a9e14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("marketing_posts", sa.Column("permalink", sa.String(length=500), nullable=True))
    op.add_column("clients", sa.Column("lead_origin", sa.String(length=120), nullable=True))
    op.add_column("clients", sa.Column("utm_source", sa.String(length=200), nullable=True))
    op.add_column("clients", sa.Column("utm_medium", sa.String(length=200), nullable=True))
    op.add_column("clients", sa.Column("utm_campaign", sa.String(length=200), nullable=True))

    op.create_table(
        "marketing_agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=40), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("window_end", sa.DateTime(), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.Column("files_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("posts_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("campaigns_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("account_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_json", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("report_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("run_id", name="uq_marketing_agent_runs_run_id"),
    )

    op.create_table(
        "marketing_import_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id", sa.Integer(),
            sa.ForeignKey("marketing_agent_runs.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("filename", sa.String(length=300), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("sha256", name="uq_marketing_import_files_sha256"),
    )

    op.create_table(
        "marketing_post_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("platform_post_id", sa.String(length=80), nullable=False),
        sa.Column("permalink", sa.String(length=500), nullable=True),
        sa.Column("post_type", sa.String(length=40), nullable=True),
        sa.Column("caption", sa.String(length=300), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("saves", sa.Integer(), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("extra_json", sa.Text(), nullable=True),
        sa.Column(
            "marketing_post_id", sa.Integer(),
            sa.ForeignKey("marketing_posts.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("link_method", sa.String(length=10), nullable=False, server_default="none"),
        sa.Column(
            "run_id", sa.Integer(), sa.ForeignKey("marketing_agent_runs.id"), nullable=False,
        ),
        sa.UniqueConstraint(
            "platform", "platform_post_id", "snapshot_date",
            name="uq_marketing_post_metrics_snapshot",
        ),
    )
    op.create_index(
        "ix_marketing_post_metrics_post", "marketing_post_metrics", ["marketing_post_id"]
    )
    op.create_index(
        "ix_marketing_post_metrics_published", "marketing_post_metrics", ["published_at"]
    )

    op.create_table(
        "marketing_campaign_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("campaign_id", sa.String(length=80), nullable=False),
        sa.Column("campaign_name", sa.String(length=200), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("is_daily", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("spend", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("reach", sa.Integer(), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column("results", sa.Integer(), nullable=True),
        sa.Column("conversions", sa.Integer(), nullable=True),
        sa.Column("result_type", sa.String(length=80), nullable=True),
        sa.Column(
            "run_id", sa.Integer(), sa.ForeignKey("marketing_agent_runs.id"), nullable=False,
        ),
        sa.UniqueConstraint(
            "platform", "campaign_id", "period_start", "period_end",
            name="uq_marketing_campaign_metrics_period",
        ),
    )
    op.create_index(
        "ix_marketing_campaign_metrics_platform_start",
        "marketing_campaign_metrics", ["platform", "period_start"],
    )

    op.create_table(
        "marketing_account_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=True),
        sa.Column("reach", sa.Integer(), nullable=True),
        sa.Column("profile_views", sa.Integer(), nullable=True),
        sa.Column("extra_json", sa.Text(), nullable=True),
        sa.Column(
            "run_id", sa.Integer(), sa.ForeignKey("marketing_agent_runs.id"), nullable=False,
        ),
        sa.UniqueConstraint("platform", "metric_date", name="uq_marketing_account_metrics_day"),
    )

    op.create_table(
        "marketing_ad_spend_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("month_ref", sa.String(length=7), nullable=False),
        sa.Column(
            "special_expense_id", sa.Integer(),
            sa.ForeignKey("special_expenses.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("reported_total", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "last_run_id", sa.Integer(), sa.ForeignKey("marketing_agent_runs.id"), nullable=False,
        ),
        sa.Column("frozen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("platform", "month_ref", name="uq_marketing_ad_spend_batches_month"),
        sa.UniqueConstraint("special_expense_id", name="uq_marketing_ad_spend_batches_expense"),
    )

    op.create_table(
        "marketing_ad_spend_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "batch_id", sa.Integer(),
            sa.ForeignKey("marketing_ad_spend_batches.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("campaign_name", sa.String(length=200), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column("results", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("marketing_ad_spend_lines")
    op.drop_table("marketing_ad_spend_batches")
    op.drop_table("marketing_account_metrics")
    op.drop_index(
        "ix_marketing_campaign_metrics_platform_start", table_name="marketing_campaign_metrics"
    )
    op.drop_table("marketing_campaign_metrics")
    op.drop_index("ix_marketing_post_metrics_published", table_name="marketing_post_metrics")
    op.drop_index("ix_marketing_post_metrics_post", table_name="marketing_post_metrics")
    op.drop_table("marketing_post_metrics")
    op.drop_table("marketing_import_files")
    op.drop_table("marketing_agent_runs")
    op.drop_column("clients", "utm_campaign")
    op.drop_column("clients", "utm_medium")
    op.drop_column("clients", "utm_source")
    op.drop_column("clients", "lead_origin")
    op.drop_column("marketing_posts", "permalink")
