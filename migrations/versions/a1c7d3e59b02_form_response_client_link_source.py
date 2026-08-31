"""Coluna `form_responses.client_link_source`: origem do vínculo resposta↔cliente (feature 266).

Espelha o `event_link_source` que já existe ao lado (feature 126) e nasce pelo mesmo motivo. A 266
passa a associar a cliente sozinha quando o telefone normalizado da resposta bate com uma ficha —
e `Client.phone` é UNIQUE, então "bate com exatamente uma" é garantia do banco, não heurística.

O que a garantia do banco NÃO cobre é o falso-positivo humano: duas pessoas que dividem um número
(a mãe que reserva pela amiga, o telefone da assessora) produzem um match único e **errado**. Sem
registrar que aquele vínculo foi deduzido, a comercial não tem como saber que ele merece
conferência — e o vínculo automático vira irreversível na auditoria.

Valores: ``'auto_phone'`` (deduzido no envio do formulário) e ``'manual'`` (alguém associou pela
tela). ``NULL`` significa "sem vínculo" ou "vínculo anterior à 266" — por isso não há backfill:
não dá para saber, retroativamente, quem decidiu o que.

Revision ID: a1c7d3e59b02
Revises: e08e454c4780
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from alembic import op

revision = "a1c7d3e59b02"
down_revision = "e08e454c4780"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "form_responses",
        sa.Column("client_link_source", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("form_responses", "client_link_source")
