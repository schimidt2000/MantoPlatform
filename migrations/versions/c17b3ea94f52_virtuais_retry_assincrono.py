"""progresso persistido das retentativas assíncronas da Loja Virtual

Revision ID: c17b3ea94f52
Revises: a5c81e0cd247
Create Date: 2026-08-04

Migração escrita à mão (padrão do repo), aditiva, fechando a fase de Convergence da feature 205
(T129–T133).

A política de retry da feature (FR-056) é **3 tentativas espaçadas de 1 minuto**. Num caminho
síncrono isso cabe em memória — três chamadas em sequência dentro da mesma requisição. Num caminho
assíncrono, não: a varredura roda a cada ciclo, decide, e volta depois. Se o contador vive só na
memória do processo, um restart do gunicorn zera tudo e a ordem retenta para sempre — ou, pior,
o outro worker recomeça do zero e a "3ª tentativa" nunca chega. Por isso o progresso é coluna.

1. **`virtual_orders.meet_attempts` / `meet_last_attempt_at`** — quantas vezes a varredura já
   tentou gerar a sala deste pedido e quando foi a última. `meet_pending` diz *que* falta sala;
   estas duas dizem *onde a política parou*. Com `meet_attempts >= 3` a falha vira definitiva e
   visível (FR-056a) em vez de silenciosa.

2. **`virtual_order_notifications.attempts` / `last_attempt_at`** — mesmo raciocínio para o e-mail.
   A linha já existia como trava de idempotência (`UNIQUE(order_id, kind)`); agora ela também
   carrega o progresso da entrega. A distinção importa: a **trava** é do aviso (um por pedido e
   tipo), o **retry** é da entrega daquele aviso.

3. **`virtual_media_deliveries.deadline_alert_at`** — quando a equipe foi alertada do prazo de
   vídeo se aproximando. É marcador de idempotência, não de status: sem ele a varredura alertaria
   a cada ciclo, e um alerta que chega de minuto em minuto é um alerta que ninguém lê.

Aditiva e com default no servidor: bancos já migrados sobem sem reescrever linha existente.
"""
import sqlalchemy as sa
from alembic import op

revision = "c17b3ea94f52"
down_revision = "a5c81e0cd247"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "virtual_orders",
        sa.Column("meet_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "virtual_orders",
        sa.Column("meet_last_attempt_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "virtual_order_notifications",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "virtual_order_notifications",
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "virtual_media_deliveries",
        sa.Column("deadline_alert_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("virtual_media_deliveries", "deadline_alert_at")
    op.drop_column("virtual_order_notifications", "last_attempt_at")
    op.drop_column("virtual_order_notifications", "attempts")
    op.drop_column("virtual_orders", "meet_last_attempt_at")
    op.drop_column("virtual_orders", "meet_attempts")
