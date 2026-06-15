"""painel financeiro mensal: flag de permuta + constantes fiscais

Revision ID: p2e3f4a5b6c7
Revises: o1d2e3f4a5b6
Create Date: 2026-06-15

Adiciona:
- calendar_events.is_cortesia_permuta (Boolean): evento de cortesia/permuta.
  Quando true, a venda é tratada como 0 e o cachê dos talentos vira "Custo de
  Marketing" (não entra no CPV, não distorce a margem bruta).
- site_settings.tax_rate (Float, default 16.0): taxa de provisionamento de
  imposto aplicada sobre o sale_value de eventos com nota (with_invoice).
- site_settings.fator_r_threshold (Float, default 28.0): corte do Fator R
  (folha ÷ faturamento) para o alerta fiscal do painel.

Migration escrita à mão (autogenerate quebrado por drift pré-existente).
"""
from alembic import op
import sqlalchemy as sa

revision = "p2e3f4a5b6c7"
down_revision = "o1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("calendar_events") as batch_op:
        batch_op.add_column(sa.Column(
            "is_cortesia_permuta", sa.Boolean(),
            nullable=False, server_default=sa.false(),
        ))
    with op.batch_alter_table("site_settings") as batch_op:
        batch_op.add_column(sa.Column("tax_rate", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("fator_r_threshold", sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table("site_settings") as batch_op:
        batch_op.drop_column("fator_r_threshold")
        batch_op.drop_column("tax_rate")
    with op.batch_alter_table("calendar_events") as batch_op:
        batch_op.drop_column("is_cortesia_permuta")
