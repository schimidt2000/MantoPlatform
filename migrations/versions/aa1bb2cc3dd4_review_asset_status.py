"""review_asset status de aprovacao

Revision ID: aa1bb2cc3dd4
Revises: 27acb021e8d6
Create Date: 2026-07-24

Migração escrita à mão (padrão do repo). Adiciona a coluna `status` em `review_assets`
para a feature 182 (Revisão de Mídia estilo Vimeo): status de aprovação persistente
('em_revisao' | 'aprovado' | 'precisa_ajustes' | 'rejeitado'). Materiais existentes
recebem 'em_revisao' via server_default — sem UPDATE em massa necessário.
"""
import sqlalchemy as sa
from alembic import op

revision = "aa1bb2cc3dd4"
down_revision = "27acb021e8d6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("review_assets", schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            "status", sa.String(length=20), server_default="em_revisao", nullable=False
        ))


def downgrade():
    with op.batch_alter_table("review_assets", schema=None) as batch_op:
        batch_op.drop_column("status")
