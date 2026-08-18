"""Explicação do teto do cachê: `event_roles.cache_cap_note` (feature 239).

Texto pronto com a conta do `cache_cap` EM VALORES — tipo/subtipo do papel, a régua de duração
aplicada e cada adicional que entrou ("Ator cara-limpa: base 2h R$ 300 + noturno R$ 50 +
fora-SP R$ 67 = R$ 417"). Preenchida na criação do evento a partir do orçamento vinculado; fica
NULL quando o papel nasceu sem orçamento (a tela mostra "definido manualmente, sem orçamento
vinculado" nesse caso).

A coluna é só explicação: nenhuma regra de negócio lê esse texto, e ele só sai pela API para o
superadmin (`app/api/agenda_read.py::_serialize_role`).

Revision ID: e2d8ca4b3071
Revises: d1c7b93a2f60
Create Date: 2026-08-18
"""

import sqlalchemy as sa
from alembic import op

revision = "e2d8ca4b3071"
down_revision = "d1c7b93a2f60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("event_roles", sa.Column("cache_cap_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("event_roles", "cache_cap_note")
