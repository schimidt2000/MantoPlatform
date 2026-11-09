"""Teto autorizado da vaga, vaga sobrando e "Ciente" da faixa do evento (feature 339).

Quatro colunas em ``event_roles``: o teto que o Superadmin autorizou acima do orçamento (valor,
quem, quando) — que passa a ser da VAGA e não do cachê da pessoa — e ``sobrando_desde``, a marca da
vaga que o título deixou de pedir quando todas estavam ocupadas. Uma em ``notifications``:
``ciente_em``, o "Ciente" por pessoa, separado do ``read_at`` que o sino grava ao clicar.

Preenchimento: vaga que hoje já tem cachê acima do teto (regra da 238) ganha esse valor como teto
autorizado, sem autor nem data, para que a próxima troca de artista não o perca. Vaga com carrinho
de transporte fica de fora: a parcela do veículo é calculada em tempo de execução e o cachê dela pode
estar acima do cap só por isso.

Aditiva: o código anterior lê e grava no banco migrado. Rollback = reverter o merge; o ``downgrade``
só derruba as colunas.

Revision ID: e339a7c1b2d4
Revises: d323b5a1c0e7
Create Date: 2026-11-09
"""

import sqlalchemy as sa
from alembic import op

revision = "e339a7c1b2d4"
down_revision = "d323b5a1c0e7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("event_roles") as batch:
        batch.add_column(sa.Column("teto_autorizado", sa.Numeric(10, 2), nullable=True))
        batch.add_column(sa.Column("teto_autorizado_por", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("teto_autorizado_em", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("sobrando_desde", sa.DateTime(), nullable=True))
        batch.create_foreign_key(
            "fk_event_roles_teto_autorizado_por_users",
            "users",
            ["teto_autorizado_por"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("ciente_em", sa.DateTime(), nullable=True))

    op.execute(
        """
        UPDATE event_roles
           SET teto_autorizado = cache_value
         WHERE cache_cap IS NOT NULL
           AND cache_value IS NOT NULL
           AND cache_value > cache_cap
           AND does_transport IS NOT TRUE
        """
    )


def downgrade():
    with op.batch_alter_table("notifications") as batch:
        batch.drop_column("ciente_em")

    with op.batch_alter_table("event_roles") as batch:
        batch.drop_constraint("fk_event_roles_teto_autorizado_por_users", type_="foreignkey")
        batch.drop_column("sobrando_desde")
        batch.drop_column("teto_autorizado_em")
        batch.drop_column("teto_autorizado_por")
        batch.drop_column("teto_autorizado")
