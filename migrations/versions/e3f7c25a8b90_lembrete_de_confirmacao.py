"""Lembrete de confirmação de convite (feature 231).

Mais da metade das escalações futuras está sem confirmação — o convite é enviado e a pessoa não
responde no portal. Duas colunas para o casting cobrar sem spammar:

`event_roles.invite_reminder_at` guarda **quando** o último lembrete daquele convite saiu, e
`invite_reminder_count` **quantos** já saíram. É o que impede o mesmo convite de virar e-mail
todo dia: a regra exige 3 dias de intervalo e para no segundo lembrete.

`site_settings.invite_reminder_run_at` é a trava de execução única — a produção roda 3 workers
do gunicorn, e sem o `UPDATE` condicional os três disparariam a mesma rodada (mesmo padrão de
`calendar_auto_sync_at`, `app/calendar/sync.py:_claim_auto_sync`).

Revision ID: e3f7c25a8b90
Revises: d2e6b94c07f1
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "e3f7c25a8b90"
down_revision = "d2e6b94c07f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("event_roles", sa.Column("invite_reminder_at", sa.DateTime(), nullable=True))
    op.add_column(
        "event_roles",
        sa.Column(
            "invite_reminder_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "site_settings", sa.Column("invite_reminder_run_at", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("site_settings", "invite_reminder_run_at")
    op.drop_column("event_roles", "invite_reminder_count")
    op.drop_column("event_roles", "invite_reminder_at")
