"""clicksign_fields

Revision ID: 6cb2d9e5757f
Revises: 6ef8bc59b9bc
Create Date: 2026-03-16 19:23:48.353710

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6cb2d9e5757f'
down_revision = '6ef8bc59b9bc'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('crm_deals', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clicksign_envelope_key', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('contract_sent_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('contract_signed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('payment_proof_path', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('payment_proof_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('calendar_event_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clicksign_token', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('clicksign_sandbox', sa.Boolean(), nullable=True, server_default='0'))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('clicksign_sandbox')
        batch_op.drop_column('clicksign_token')

    with op.batch_alter_table('crm_deals', schema=None) as batch_op:
        batch_op.drop_column('calendar_event_id')
        batch_op.drop_column('payment_proof_at')
        batch_op.drop_column('payment_proof_path')
        batch_op.drop_column('contract_signed_at')
        batch_op.drop_column('contract_sent_at')
        batch_op.drop_column('clicksign_envelope_key')
