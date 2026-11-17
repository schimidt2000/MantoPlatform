"""marketing integrado: frente, licença do tema, pedido de criativo, propostas e diário (feature 345)

Aditiva:
- colunas novas em `catalog_items`, `marketing_posts`, `marketing_campaign_metrics` e `site_settings`;
- seis tabelas novas (`marketing_frentes`, com as 5 frentes semeadas, `marketing_campanha_frentes`,
  `marketing_ad_metrics`, `marketing_post_anuncios`, `marketing_propostas`, `marketing_diario`).

Nenhum dado existente muda: card antigo vira `tipo='post'`/`origem='pessoa'` e todo tema nasce
`nao_classificado`/`nao_decidido` (fica fora de anúncio até alguém classificar).

Revision ID: f345c0a1b2d3
Revises: e344a1b2c3d4
Create Date: 2026-11-16
"""

import sqlalchemy as sa
from alembic import op

revision = "f345c0a1b2d3"
down_revision = "e344a1b2c3d4"
branch_labels = None
depends_on = None

FRENTES = ("corporativo", "social", "educamanto", "festas", "loja")


def upgrade():
    with op.batch_alter_table("catalog_items") as batch:
        batch.add_column(
            sa.Column(
                "licenca_origem",
                sa.String(length=16),
                nullable=False,
                server_default="nao_classificado",
            )
        )
        batch.add_column(
            sa.Column(
                "liberado_anuncio",
                sa.String(length=12),
                nullable=False,
                server_default="nao_decidido",
            )
        )
        batch.add_column(
            sa.Column(
                "licenca_por_id",
                sa.Integer(),
                sa.ForeignKey("users.id", name="fk_catalog_items_licenca_por", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("licenca_em", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("licenca_sugestao", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("licenca_sugestao_motivo", sa.Text(), nullable=True))

    with op.batch_alter_table("marketing_posts") as batch:
        batch.add_column(
            sa.Column("tipo", sa.String(length=10), nullable=False, server_default="post")
        )
        batch.add_column(sa.Column("frente", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("formato", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("briefing_objetivo", sa.Text(), nullable=True))
        batch.add_column(sa.Column("briefing_mostrar", sa.Text(), nullable=True))
        batch.add_column(sa.Column("briefing_letreiro", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("origem", sa.String(length=10), nullable=False, server_default="pessoa")
        )

    with op.batch_alter_table("marketing_campaign_metrics") as batch:
        batch.add_column(sa.Column("conversations", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("leads", sa.Integer(), nullable=True))

    with op.batch_alter_table("site_settings") as batch:
        batch.add_column(
            sa.Column(
                "marketing_resp_foto_id",
                sa.Integer(),
                sa.ForeignKey(
                    "users.id", name="fk_site_settings_mkt_resp_foto", ondelete="SET NULL"
                ),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "marketing_resp_video_id",
                sa.Integer(),
                sa.ForeignKey(
                    "users.id", name="fk_site_settings_mkt_resp_video", ondelete="SET NULL"
                ),
                nullable=True,
            )
        )

    frentes = op.create_table(
        "marketing_frentes",
        sa.Column("slug", sa.String(length=16), primary_key=True),
        sa.Column("teto_custo_venda", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "updated_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.bulk_insert(frentes, [{"slug": slug} for slug in FRENTES])

    op.create_table(
        "marketing_campanha_frentes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("campaign_id", sa.String(length=80), nullable=False),
        sa.Column("frente", sa.String(length=16), nullable=False),
        sa.Column(
            "updated_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("platform", "campaign_id", name="uq_marketing_campanha_frentes"),
    )

    op.create_table(
        "marketing_ad_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("ad_id", sa.String(length=80), nullable=False),
        sa.Column("ad_name", sa.String(length=300), nullable=True),
        sa.Column("adset_id", sa.String(length=80), nullable=True),
        sa.Column("campaign_id", sa.String(length=80), nullable=True),
        sa.Column("campaign_name", sa.String(length=200), nullable=True),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("spend", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("reach", sa.Integer(), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column("conversations", sa.Integer(), nullable=True),
        sa.Column("leads", sa.Integer(), nullable=True),
        sa.Column("results", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("platform", "ad_id", "metric_date", name="uq_marketing_ad_metrics_day"),
    )
    op.create_index(
        "ix_marketing_ad_metrics_campaign",
        "marketing_ad_metrics",
        ["platform", "campaign_id", "metric_date"],
    )

    op.create_table(
        "marketing_post_anuncios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "post_id",
            sa.Integer(),
            sa.ForeignKey("marketing_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("ad_id", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("platform", "ad_id", name="uq_marketing_post_anuncios_ad"),
    )

    op.create_table(
        "marketing_propostas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(length=12), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("alvo_tipo", sa.String(length=10), nullable=False),
        sa.Column("alvo_id", sa.String(length=80), nullable=False),
        sa.Column("alvo_nome", sa.String(length=300), nullable=True),
        sa.Column("valor_antes", sa.String(length=200), nullable=True),
        sa.Column("valor_depois", sa.String(length=200), nullable=True),
        sa.Column("custo_dia_estimado", sa.Numeric(12, 2), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("evidencia", sa.Text(), nullable=True),
        sa.Column(
            "post_id",
            sa.Integer(),
            sa.ForeignKey("marketing_posts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("situacao", sa.String(length=10), nullable=False, server_default="pendente"),
        sa.Column("criada_em", sa.DateTime(), nullable=False),
        sa.Column(
            "decidida_por_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decidida_em", sa.DateTime(), nullable=True),
        sa.Column("decisao_obs", sa.Text(), nullable=True),
        sa.Column("executada_em", sa.DateTime(), nullable=True),
        sa.Column("resultado_execucao", sa.Text(), nullable=True),
    )
    op.create_index("ix_marketing_propostas_situacao", "marketing_propostas", ["situacao"])

    op.create_table(
        "marketing_diario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("evidencia", sa.Text(), nullable=True),
        sa.Column("resultado_esperado", sa.Text(), nullable=True),
        sa.Column("reavaliar_em", sa.Date(), nullable=False),
        sa.Column("resultado_observado", sa.Text(), nullable=True),
        sa.Column("veredito", sa.String(length=14), nullable=True),
        sa.Column("avaliado_em", sa.DateTime(), nullable=True),
        sa.Column("origem", sa.String(length=10), nullable=False, server_default="pessoa"),
        sa.Column(
            "proposta_id",
            sa.Integer(),
            sa.ForeignKey("marketing_propostas.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "autor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("marketing_diario")
    op.drop_index("ix_marketing_propostas_situacao", table_name="marketing_propostas")
    op.drop_table("marketing_propostas")
    op.drop_table("marketing_post_anuncios")
    op.drop_index("ix_marketing_ad_metrics_campaign", table_name="marketing_ad_metrics")
    op.drop_table("marketing_ad_metrics")
    op.drop_table("marketing_campanha_frentes")
    op.drop_table("marketing_frentes")

    with op.batch_alter_table("site_settings") as batch:
        batch.drop_column("marketing_resp_video_id")
        batch.drop_column("marketing_resp_foto_id")
    with op.batch_alter_table("marketing_campaign_metrics") as batch:
        batch.drop_column("leads")
        batch.drop_column("conversations")
    with op.batch_alter_table("marketing_posts") as batch:
        for col in (
            "origem",
            "briefing_letreiro",
            "briefing_mostrar",
            "briefing_objetivo",
            "formato",
            "frente",
            "tipo",
        ):
            batch.drop_column(col)
    with op.batch_alter_table("catalog_items") as batch:
        for col in (
            "licenca_sugestao_motivo",
            "licenca_sugestao",
            "licenca_em",
            "licenca_por_id",
            "liberado_anuncio",
            "licenca_origem",
        ):
            batch.drop_column(col)
