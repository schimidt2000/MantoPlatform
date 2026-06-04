"""remover CRM: drop das tabelas crm_*

Revision ID: g3a4b5c6d7e8
Revises: f2a3b4c5d6e7
Create Date: 2026-06-04

Migration escrita à mão (autogenerate quebrado por drift pré-existente do schema).
Remoção do módulo de CRM — decisão de produto, IRREVERSÍVEL (downgrade é no-op).
Ordem de drop: filho → pai (respeita as FKs).
"""
from alembic import op

revision = "g3a4b5c6d7e8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None

_TABLES = [
    "crm_reminders",
    "crm_notes",
    "crm_deals",
    "crm_contacts",
    "crm_organizations",
    "crm_stages",
]


def upgrade():
    bind = op.get_bind()
    insp = sa_inspect(bind)
    existing = set(insp.get_table_names())
    for table in _TABLES:
        if table in existing:
            op.drop_table(table)


def downgrade():
    # Remoção do CRM é irreversível por decisão de produto; nada a recriar.
    pass


def sa_inspect(bind):
    from sqlalchemy import inspect
    return inspect(bind)
