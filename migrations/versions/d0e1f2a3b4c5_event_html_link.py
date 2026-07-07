"""Link direto do evento no Google Calendar (feature 117).

calendar_events ganha google_html_link — vem pronto no payload da API do Google
("htmlLink"), capturado na sincronização. Usado só pelo botão "Editar no Google Agenda";
nenhuma escrita nova do Manto para o Google.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-07
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("calendar_events", sa.Column("google_html_link", sa.String(500), nullable=True))


def downgrade():
    op.drop_column("calendar_events", "google_html_link")
