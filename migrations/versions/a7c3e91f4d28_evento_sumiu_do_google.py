"""Marca "Sumiu do Google Agenda" no evento (feature 303).

Até aqui, a limpeza do sync apagava do banco todo evento que não aparecia no Google Agenda no mês
sincronizado — com venda, comprovantes, contrato e escala junto. A 303 mantém o evento que tem
dinheiro preso e o marca com a data e a hora (horário de parede de São Paulo, como
`cancelled_at`) em que o sistema percebeu o sumiço.

Coluna própria, e não os campos da solicitação de exclusão (feature 224): o Comercial
sobrescreveria a marca ao pedir exclusão, e o "Recusar" a zeraria.

Aditiva e nullable: nenhum evento existente muda de comportamento, e o código anterior lê e grava
no banco migrado — um `git revert` é seguro para o schema (os eventos marcados têm de ser
devolvidos ao Google antes; ver o quickstart da 303).

Revision ID: a7c3e91f4d28
Revises: e5a1c7d93b20
Create Date: 2026-09-30
"""

import sqlalchemy as sa
from alembic import op

revision = "a7c3e91f4d28"
down_revision = "e5a1c7d93b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calendar_events", sa.Column("google_missing_since", sa.DateTime(), nullable=True)
    )
    # A faixa e a reconferência do ciclo procuram os marcados a cada minuto e a cada 10 minutos;
    # o índice parcial mantém isso barato sem incluir as milhares de linhas não marcadas.
    op.create_index(
        "ix_calendar_events_google_missing_since",
        "calendar_events",
        ["google_missing_since"],
        postgresql_where=sa.text("google_missing_since IS NOT NULL"),
        sqlite_where=sa.text("google_missing_since IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_calendar_events_google_missing_since", table_name="calendar_events")
    op.drop_column("calendar_events", "google_missing_since")
