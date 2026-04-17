"""event_create_extended_fields

Revision ID: c2d3e4f5a6b7
Revises: 3427e062d799
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'c2d3e4f5a6b7'
down_revision = '3427e062d799'
branch_labels = None
depends_on = None


def upgrade():
    # ── calendar_events: campos financeiros e de pagamento ──────────────────
    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_method',       sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('payment_installments', sa.Integer(),          nullable=True))
        batch_op.add_column(sa.Column('payment_due_date',     sa.Date(),             nullable=True))
        batch_op.add_column(sa.Column('transport_value',      sa.Integer(),          nullable=True))
        batch_op.add_column(sa.Column('acrescimo_value',      sa.Integer(),          nullable=True))
        batch_op.add_column(sa.Column('orcamento_history_id', sa.Integer(),          nullable=True))
        batch_op.create_foreign_key(
            'fk_calendar_events_orcamento_history_id',
            'orcamento_history', ['orcamento_history_id'], ['id']
        )

    # ── event_contracts: campo assinatura ───────────────────────────────────
    with op.batch_alter_table('event_contracts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_signed', sa.Boolean(), nullable=False, server_default='0'))

    # ── event_roles: campos de figurino/casting pré-preenchidos ─────────────
    with op.batch_alter_table('event_roles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('needs_makeup', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('is_singer',    sa.Boolean(), nullable=True))

    # ── nova tabela: event_observations ──────────────────────────────────────
    op.create_table(
        'event_observations',
        sa.Column('id',         sa.Integer(),      nullable=False),
        sa.Column('event_id',   sa.Integer(),      nullable=False),
        sa.Column('obs_type',   sa.String(10),     nullable=False),
        sa.Column('content',    sa.Text(),         nullable=True),
        sa.Column('file_path',  sa.String(500),    nullable=True),
        sa.Column('label',      sa.String(200),    nullable=True),
        sa.Column('created_at', sa.DateTime(),     nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['calendar_events.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('event_observations', schema=None) as batch_op:
        batch_op.create_index('ix_event_observations_event_id', ['event_id'], unique=False)


def downgrade():
    with op.batch_alter_table('event_observations', schema=None) as batch_op:
        batch_op.drop_index('ix_event_observations_event_id')
    op.drop_table('event_observations')

    with op.batch_alter_table('event_roles', schema=None) as batch_op:
        batch_op.drop_column('is_singer')
        batch_op.drop_column('needs_makeup')

    with op.batch_alter_table('event_contracts', schema=None) as batch_op:
        batch_op.drop_column('is_signed')

    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.drop_constraint('fk_calendar_events_orcamento_history_id', type_='foreignkey')
        batch_op.drop_column('orcamento_history_id')
        batch_op.drop_column('acrescimo_value')
        batch_op.drop_column('transport_value')
        batch_op.drop_column('payment_due_date')
        batch_op.drop_column('payment_installments')
        batch_op.drop_column('payment_method')
