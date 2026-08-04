"""loja de interacoes virtuais

Revision ID: f3a9c72e5d18
Revises: b7d4f81a6e0c
Create Date: 2026-07-30

Migração escrita à mão (padrão do repo), 100% aditiva, para a feature 205 (Loja de Interações
Virtuais). Cria as sete tabelas do canal de venda B2C e acrescenta dois campos de configuração em
`site_settings`. Nenhuma tabela ou coluna existente é alterada ou removida.

Três decisões de schema que carregam regra de negócio:

1. **Dinheiro é `Numeric(12, 2)` em todas as colunas monetárias** (Princípio IX). A InfinitePay
   exige centavos inteiros, mas isso é característica do fornecedor e fica confinado a
   `app/integracoes/infinitepay_client.py`. Nenhuma coluna aqui guarda centavos.

2. **`uq_virtual_slot_campaign_start`** é o que torna a geração de horários idempotente: reexecutar
   a mesma janela não duplica slot (FR-004).

3. **`uq_virtual_order_notification_kind`** e o `UNIQUE` de `transaction_nsu` são as duas travas de
   idempotência da feature. A primeira impede o mesmo aviso sair duas vezes para a família
   (FR-028a); a segunda impede que a reentrega do webhook crie evento, escala, presente 3D e baixa
   de estoque duplicados (FR-028). Sem elas, uma operadora que reenvia o aviso — comportamento
   documentado da InfinitePay — corrompe a operação.

O papel de acesso NÃO é criado aqui: papéis são linhas de `roles` semeadas por `seed.py`, não
schema (mesmo tratamento dado a ARTISTA_3D na feature 200).
"""
import sqlalchemy as sa
from alembic import op

revision = "f3a9c72e5d18"
down_revision = "b7d4f81a6e0c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "virtual_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("catalog_character_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("intro_html", sa.Text(), nullable=True),
        sa.Column("tolerance_terms", sa.Text(), nullable=True),
        sa.Column("faq_json", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column("whatsapp_phone", sa.String(20), nullable=True),
        sa.Column("price_live", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_recorded", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_gift", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("recorded_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recorded_sold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recorded_delivery_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("talent_id", sa.Integer(), nullable=True),
        sa.Column("figurino_sheet_id", sa.Integer(), nullable=True),
        sa.Column(
            "max_reservations_per_origin", sa.Integer(), nullable=False, server_default="5"
        ),
        sa.Column(
            "reservation_window_minutes", sa.Integer(), nullable=False, server_default="60"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalog_character_id"], ["catalog_characters.id"],
            name="fk_virtual_campaigns_character_id",
        ),
        sa.ForeignKeyConstraint(
            ["talent_id"], ["talents.id"], name="fk_virtual_campaigns_talent_id",
        ),
        sa.ForeignKeyConstraint(
            ["figurino_sheet_id"], ["figurino_sheets.id"],
            name="fk_virtual_campaigns_figurino_sheet_id", ondelete="SET NULL",
        ),
        sa.UniqueConstraint("slug", name="uq_virtual_campaigns_slug"),
    )
    op.create_index("ix_virtual_campaigns_status", "virtual_campaigns", ["status"])

    # `virtual_orders` antes de `virtual_campaign_slots`: o slot aponta para o pedido que o ocupa.
    op.create_table(
        "virtual_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=True),
        sa.Column("modality", sa.String(12), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="reservado"),
        sa.Column("order_nsu", sa.String(64), nullable=False),
        sa.Column("public_token", sa.String(43), nullable=False),
        sa.Column("child_name", sa.String(120), nullable=False),
        sa.Column("child_age", sa.Integer(), nullable=False),
        sa.Column("behavior_notes", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.String(20), nullable=False),
        sa.Column("contact_phone_display", sa.String(30), nullable=True),
        sa.Column("contact_email", sa.String(180), nullable=False),
        sa.Column("delivery_address", sa.String(300), nullable=True),
        sa.Column("gift_item_id", sa.Integer(), nullable=True),
        sa.Column("price_interaction", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_gift", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("payment_url", sa.String(500), nullable=True),
        sa.Column("invoice_slug", sa.String(120), nullable=True),
        sa.Column("transaction_nsu", sa.String(120), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("meet_url", sa.String(500), nullable=True),
        sa.Column("meet_pending", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("origin_hash", sa.String(64), nullable=True),
        sa.Column("grace_until", sa.DateTime(), nullable=True),
        sa.Column("recheck_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expired_unverified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("access_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("access_blocked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["virtual_campaigns.id"], name="fk_virtual_orders_campaign_id",
        ),
        sa.ForeignKeyConstraint(
            ["gift_item_id"], ["acervo_3d_items.id"], name="fk_virtual_orders_gift_item_id",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["calendar_events.id"], name="fk_virtual_orders_event_id",
        ),
        sa.UniqueConstraint("order_nsu", name="uq_virtual_orders_order_nsu"),
        sa.UniqueConstraint("public_token", name="uq_virtual_orders_public_token"),
    )
    op.create_index("ix_virtual_orders_status", "virtual_orders", ["status"])
    op.create_index("ix_virtual_orders_campaign_id", "virtual_orders", ["campaign_id"])
    op.create_index("ix_virtual_orders_contact_phone", "virtual_orders", ["contact_phone"])
    op.create_index("ix_virtual_orders_created_at", "virtual_orders", ["created_at"])

    op.create_table(
        "virtual_campaign_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="livre"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["virtual_campaigns.id"],
            name="fk_virtual_campaign_slots_campaign_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["virtual_orders.id"], name="fk_virtual_campaign_slots_order_id",
        ),
        sa.UniqueConstraint("campaign_id", "start_at", name="uq_virtual_slot_campaign_start"),
    )
    op.create_index("ix_virtual_campaign_slots_status", "virtual_campaign_slots", ["status"])
    op.create_index("ix_virtual_campaign_slots_start_at", "virtual_campaign_slots", ["start_at"])

    op.create_foreign_key(
        "fk_virtual_orders_slot_id", "virtual_orders", "virtual_campaign_slots",
        ["slot_id"], ["id"],
    )

    op.create_table(
        "virtual_campaign_acervo",
        sa.Column("campaign_id", sa.Integer(), primary_key=True),
        sa.Column("acervo_3d_item_id", sa.Integer(), primary_key=True),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["virtual_campaigns.id"],
            name="fk_virtual_campaign_acervo_campaign_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["acervo_3d_item_id"], ["acervo_3d_items.id"],
            name="fk_virtual_campaign_acervo_item_id", ondelete="CASCADE",
        ),
    )

    op.create_table(
        "virtual_payment_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("order_nsu", sa.String(64), nullable=True),
        sa.Column("transaction_nsu", sa.String(120), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("secret_ok", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("recheck_result", sa.String(20), nullable=True),
        sa.Column("recheck_payload", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(24), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"], ["virtual_orders.id"],
            name="fk_virtual_payment_notifications_order_id",
        ),
        sa.UniqueConstraint(
            "transaction_nsu", name="uq_virtual_payment_notifications_transaction_nsu"
        ),
    )
    op.create_index(
        "ix_virtual_payment_notifications_order_id", "virtual_payment_notifications", ["order_id"]
    )

    op.create_table(
        "virtual_media_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pendente"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("video_path", sa.String(500), nullable=True),
        sa.Column("video_mime", sa.String(60), nullable=True),
        sa.Column("video_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("video_published_at", sa.DateTime(), nullable=True),
        sa.Column("last_upload_error", sa.Text(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"], ["virtual_orders.id"],
            name="fk_virtual_media_deliveries_order_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"], ["users.id"], name="fk_virtual_media_deliveries_updated_by_id",
        ),
        sa.UniqueConstraint("order_id", name="uq_virtual_media_deliveries_order_id"),
    )
    op.create_index("ix_virtual_media_deliveries_status", "virtual_media_deliveries", ["status"])
    op.create_index(
        "ix_virtual_media_deliveries_due_date", "virtual_media_deliveries", ["due_date"]
    )

    op.create_table(
        "virtual_refund_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False, server_default="conflito_horario"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pendente"),
        sa.Column("invoice_slug", sa.String(120), nullable=True),
        sa.Column("transaction_nsu", sa.String(120), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"], ["virtual_orders.id"], name="fk_virtual_refund_requests_order_id",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"], ["users.id"], name="fk_virtual_refund_requests_resolved_by_id",
        ),
    )
    op.create_index("ix_virtual_refund_requests_status", "virtual_refund_requests", ["status"])

    op.create_table(
        "virtual_order_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("sent_ok", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"], ["virtual_orders.id"],
            name="fk_virtual_order_notifications_order_id", ondelete="CASCADE",
        ),
        sa.UniqueConstraint("order_id", "kind", name="uq_virtual_order_notification_kind"),
    )

    op.add_column(
        "site_settings", sa.Column("infinitepay_handle", sa.String(100), nullable=True)
    )
    op.add_column(
        "site_settings", sa.Column("infinitepay_webhook_token", sa.String(64), nullable=True)
    )


def downgrade():
    op.drop_column("site_settings", "infinitepay_webhook_token")
    op.drop_column("site_settings", "infinitepay_handle")

    op.drop_table("virtual_order_notifications")
    op.drop_index("ix_virtual_refund_requests_status", table_name="virtual_refund_requests")
    op.drop_table("virtual_refund_requests")
    op.drop_index("ix_virtual_media_deliveries_due_date", table_name="virtual_media_deliveries")
    op.drop_index("ix_virtual_media_deliveries_status", table_name="virtual_media_deliveries")
    op.drop_table("virtual_media_deliveries")
    op.drop_index(
        "ix_virtual_payment_notifications_order_id", table_name="virtual_payment_notifications"
    )
    op.drop_table("virtual_payment_notifications")
    op.drop_table("virtual_campaign_acervo")

    # A FK circular precisa cair antes das duas tabelas que ela liga.
    op.drop_constraint("fk_virtual_orders_slot_id", "virtual_orders", type_="foreignkey")
    op.drop_index("ix_virtual_campaign_slots_start_at", table_name="virtual_campaign_slots")
    op.drop_index("ix_virtual_campaign_slots_status", table_name="virtual_campaign_slots")
    op.drop_table("virtual_campaign_slots")

    op.drop_index("ix_virtual_orders_created_at", table_name="virtual_orders")
    op.drop_index("ix_virtual_orders_contact_phone", table_name="virtual_orders")
    op.drop_index("ix_virtual_orders_campaign_id", table_name="virtual_orders")
    op.drop_index("ix_virtual_orders_status", table_name="virtual_orders")
    op.drop_table("virtual_orders")

    op.drop_index("ix_virtual_campaigns_status", table_name="virtual_campaigns")
    op.drop_table("virtual_campaigns")
