"""Conversas: o Instagram Direct na mesma caixa (feature 330).

Duas colunas novas em ``conversas`` (``usuario``, o @usuário do Instagram, e ``perfil_em``, a última
busca do perfil) e duas colunas alargadas em ``conversa_mensagens`` (``externo_id`` e ``resposta_a``
de 128 para 255: o ``mid`` do Instagram é mais longo que o ``wamid``). Alargar varchar no Postgres não
reescreve a tabela nem mexe no índice único.

Aditiva. O ``downgrade`` só encurta se nenhum valor passar de 128 (senão falharia no meio): ele
aborta antes, com a mensagem, em vez de truncar ids.

Revision ID: a330c4e8f1b2
Revises: f328b2d4e6a1
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op

revision = "a330c4e8f1b2"
down_revision = "f328b2d4e6a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversas", sa.Column("usuario", sa.String(64), nullable=True))
    op.add_column("conversas", sa.Column("perfil_em", sa.DateTime(), nullable=True))
    op.alter_column(
        "conversa_mensagens",
        "externo_id",
        type_=sa.String(255),
        existing_type=sa.String(128),
        existing_nullable=True,
    )
    op.alter_column(
        "conversa_mensagens",
        "resposta_a",
        type_=sa.String(255),
        existing_type=sa.String(128),
        existing_nullable=True,
    )


def downgrade():
    longos = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM conversa_mensagens "
                "WHERE length(externo_id) > 128 OR length(resposta_a) > 128"
            )
        )
        .scalar()
    )
    if longos:
        raise RuntimeError(
            f"{longos} mensagens do Instagram têm id acima de 128 caracteres: apague-as antes do downgrade."
        )
    op.alter_column(
        "conversa_mensagens",
        "resposta_a",
        type_=sa.String(128),
        existing_type=sa.String(255),
        existing_nullable=True,
    )
    op.alter_column(
        "conversa_mensagens",
        "externo_id",
        type_=sa.String(128),
        existing_type=sa.String(255),
        existing_nullable=True,
    )
    op.drop_column("conversas", "perfil_em")
    op.drop_column("conversas", "usuario")
