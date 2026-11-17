"""O comercial mede e fecha pela conversa (feature 349).

Aditiva, só em ``conversas``:
- a primeira mensagem da cliente e a primeira resposta da equipe (hora, autor e origem);
- a perda com motivo; a decisão de qualificação; o lembrete ("Lembrar amanhã").

O ``upgrade`` preenche a primeira mensagem e a primeira resposta das conversas que já existem, pela mesma
régua da gravação viva (`primeira_resposta_ops`): recebida sem reação; enviada aceita, sem reação e sem os
textos "apagada/editada pelo celular", a partir da primeira mensagem. O ``downgrade`` derruba as colunas.

Revision ID: a349c0e1f2a3
Revises: d334b2c4e6f8
Create Date: 2026-11-17
"""

import sqlalchemy as sa
from alembic import op

revision = "a349c0e1f2a3"
down_revision = "d334b2c4e6f8"
branch_labels = None
depends_on = None

# (nome, tipo, FK para users?) na ordem do model.
COLUNAS = (
    ("primeira_recebida_em", sa.DateTime(), False),
    ("primeira_resposta_em", sa.DateTime(), False),
    ("primeira_resposta_por_id", sa.Integer(), True),
    ("primeira_resposta_origem", sa.String(12), False),
    ("perdida_em", sa.DateTime(), False),
    ("perdida_motivo", sa.String(30), False),
    ("perdida_nota", sa.String(300), False),
    ("perdida_por_id", sa.Integer(), True),
    ("qualificacao", sa.String(20), False),
    ("qualificacao_em", sa.DateTime(), False),
    ("qualificacao_por_id", sa.Integer(), True),
    ("lembrar_em", sa.DateTime(), False),
    ("lembrar_para_id", sa.Integer(), True),
)

_PRIMEIRA_RECEBIDA = """
UPDATE conversas c SET primeira_recebida_em = s.em
FROM (
    SELECT conversa_id, MIN(momento) AS em FROM conversa_mensagens
    WHERE direcao = 'recebida' AND tipo <> 'reacao'
    GROUP BY conversa_id
) s
WHERE s.conversa_id = c.id
"""

_PRIMEIRA_RESPOSTA = """
UPDATE conversas c
SET primeira_resposta_em = r.momento,
    primeira_resposta_por_id = r.autor_id,
    primeira_resposta_origem = r.origem
FROM (
    SELECT DISTINCT ON (m.conversa_id) m.conversa_id, m.momento, m.autor_id, m.origem
    FROM conversa_mensagens m
    JOIN conversas c2 ON c2.id = m.conversa_id
    WHERE m.direcao = 'enviada'
      AND m.situacao IN ('enviada', 'entregue', 'lida')
      AND m.tipo <> 'reacao'
      AND (m.origem <> 'celular' OR m.texto IS NULL
           OR m.texto NOT IN ('Mensagem apagada pelo celular.', 'Mensagem editada pelo celular.'))
      AND c2.primeira_recebida_em IS NOT NULL
      AND m.momento >= c2.primeira_recebida_em
    ORDER BY m.conversa_id, m.momento, m.id
) r
WHERE r.conversa_id = c.id
"""


def upgrade():
    for nome, tipo, fk in COLUNAS:
        op.add_column("conversas", sa.Column(nome, tipo, nullable=True))
        if fk:
            op.create_foreign_key(
                f"fk_conversas_{nome}", "conversas", "users", [nome], ["id"], ondelete="SET NULL"
            )
    op.create_index("ix_conversas_lembrar_em", "conversas", ["lembrar_em"])
    op.execute(_PRIMEIRA_RECEBIDA)
    op.execute(_PRIMEIRA_RESPOSTA)


def downgrade():
    op.drop_index("ix_conversas_lembrar_em", table_name="conversas")
    for nome, _, fk in reversed(COLUNAS):
        if fk:
            op.drop_constraint(f"fk_conversas_{nome}", "conversas", type_="foreignkey")
        op.drop_column("conversas", nome)
