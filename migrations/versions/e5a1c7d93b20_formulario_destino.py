"""Destino do formulário: encerramento com motivo e sugestões descartadas (feature 298).

POR QUE ESTA MIGRATION EXISTE. Em 10/09/2026 a Home dizia 1.347 formulários "sem evento", e desde
01/06/2026 eram só 36: o resto era o histórico de 2023 a maio/2026, importado de propósito como
histórico de cliente. Não havia jeito de um formulário sair da fila sem virar evento — a cliente que
desistiu, o que foi preenchido duas vezes ou errado ficavam para sempre como tarefa, e o único
recurso era o superadmin APAGAR, perdendo o histórico.

As quatro colunas de encerramento dão ao formulário o segundo destino possível (o primeiro é o
evento). A tabela de descartes guarda os pares "parece ser este evento — não é" que a comercial
recusou, para a sugestão não voltar (decisão do dono: descarte definitivo).

DECISÃO REGISTRADA: encerramento em colunas da própria `form_responses`, não em tabela de histórico.
O formulário mostra só o estado atual; encerrar e reabrir ficam no `audit_logs` que já existe
(helper `audit()`), sem estrutura nova.

ARMADILHA EVITADA: tudo nullable e sem `server_default` — as 1.548 respostas existentes continuam
exatamente como estão, sem nenhum `UPDATE` de linha neste `upgrade`. "Sem destino" é derivado
(`event_id IS NULL AND closed_at IS NULL AND created_at >= corte`), não uma coluna a preencher.

Revision ID: e5a1c7d93b20
Revises: c9f4a2b71e60
Create Date: 2026-09-11
"""

import sqlalchemy as sa
from alembic import op

revision = "e5a1c7d93b20"
down_revision = "c9f4a2b71e60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── form_responses: o encerramento com motivo ──
    with op.batch_alter_table("form_responses") as batch:
        batch.add_column(sa.Column("closed_reason", sa.String(length=30), nullable=True))
        batch.add_column(sa.Column("closed_note", sa.String(length=300), nullable=True))
        batch.add_column(sa.Column("closed_by_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("closed_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key(
            "fk_form_responses_closed_by_id_users",
            "users",
            ["closed_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Índice PARCIAL da fila "sem destino": a lista da Home lê só essa fatia, que é minúscula
    # perto do histórico. Espelha `app/models.py` (FormResponse.__table_args__).
    op.create_index(
        "ix_form_responses_sem_destino",
        "form_responses",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("event_id IS NULL AND closed_at IS NULL"),
        sqlite_where=sa.text("event_id IS NULL AND closed_at IS NULL"),
    )

    # ── form_response_dismissed_events: "não é este" é definitivo ──
    op.create_table(
        "form_response_dismissed_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("form_response_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("dismissed_by_id", sa.Integer(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["form_response_id"], ["form_responses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["calendar_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dismissed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "form_response_id", "event_id", name="uq_form_response_dismissed_event"
        ),
    )


def downgrade() -> None:
    op.drop_table("form_response_dismissed_events")
    op.drop_index("ix_form_responses_sem_destino", table_name="form_responses")
    with op.batch_alter_table("form_responses") as batch:
        batch.drop_constraint("fk_form_responses_closed_by_id_users", type_="foreignkey")
        batch.drop_column("closed_at")
        batch.drop_column("closed_by_id")
        batch.drop_column("closed_note")
        batch.drop_column("closed_reason")
