"""painel atribuído: meta e verba por frente, calendário do ano, conceito, proposta e diário (feature 351)

Aditiva:
- `marketing_frentes`: `meta_vendas_mes`, `verba_mes`;
- `marketing_calendario` (nova), com as 60 linhas (5 frentes × 12 meses) e o foco de cada mês tirado do
  calendário de 12 meses da pesquisa de 17/11/2026 (§4.6) — números vazios, o dono preenche;
- `marketing_posts.conceito`;
- `marketing_propostas`: `frente`, `valor_antes_num`, `valor_depois_num`;
- `marketing_diario`: alvo, métrica, dia da mudança, janela, linha de base e controle.

Nenhum dado existente muda. Nasceu na head `d334b2c4e6f8`, como a 348, a 349 e a 350; no lote de 17/11 foi
reencadeada na fila 348 → 349 → 350 → 351.

Revision ID: a351b0c1d2e3
Revises: a350b1c2d3e4
Create Date: 2026-11-17
"""

import sqlalchemy as sa
from alembic import op

revision = "a351b0c1d2e3"
down_revision = "a350b1c2d3e4"
branch_labels = None
depends_on = None

FRENTES = ("corporativo", "social", "educamanto", "festas", "loja")

# Foco de cada mês por frente (pesquisa "Máquina de vendas Manto", §4.6). Texto inicial; editável na tela.
FOCO = {
    "festas": {
        1: "Lembrete dos aniversários de fevereiro e março; férias em condomínio (hipótese)",
        2: "Aniversários de março, o mês com mais nascimentos",
        3: "Aniversários de abril e maio; Páscoa (hipótese)",
        4: "Aniversários de maio",
        5: "Aniversários de junho",
        6: "Aniversários de julho, vendidos antes das férias",
        7: "Férias (hipótese)",
        8: "Dia das Crianças começa a vender",
        9: "Dia das Crianças, últimas datas",
        10: "Pico do ano",
        11: "Natal e encaixes",
        12: "Entregar; pedir avaliação, indicação e opt-in",
    },
    "corporativo": {
        1: "Recompra de quem fez festa em dezembro; convenção pós-Carnaval",
        2: "Convenções",
        3: "Mês de maior conversão de proposta",
        4: "SIPAT e Dia das Mães",
        5: "Festa junina",
        6: "Arraiá de empresa",
        7: "Pacote do 2º semestre",
        8: "Dia das Crianças, Natal e SIPAT",
        9: "Festa de fim de ano",
        10: "Pico de pedidos de proposta; Papai Noel",
        11: "Encaixes de dezembro",
        12: "Entregar",
    },
    "educamanto": {
        1: "Acolhimento e volta às aulas",
        2: "Venda curta para 7/4 (combate ao bullying)",
        3: "7/4 e Dia do Livro Infantil (18/4)",
        4: "Apresentações de abril",
        5: "Bett; abrir a pré-venda do ano seguinte",
        6: "Pré-venda: a escola monta o plano em jun–ago",
        7: "Proposta de open house; plano do ano seguinte",
        8: "Open house e Folclore (22/8)",
        9: "Semana da Criança; a rematrícula abre",
        10: "Semana da Criança; a escola fecha fornecedor (out–dez)",
        11: "Mostra cultural e formatura; fim da pré-venda",
        12: "Formaturas e encerramento",
    },
    "social": {
        2: "Visita a assessorias",
        3: "Parceiros",
        4: "Parceiros",
        5: "Feiras de noivas, só visita",
    },
    "loja": {
        1: "Fechar o aprendizado da loja de Natal",
        8: "Preparar a loja",
        9: "Preparar a loja",
        10: "Loja de Natal abre, com opt-in",
        11: "Loja de Natal",
        12: "Loja de Natal",
    },
}


def _colunas_do_diario() -> list[sa.Column]:
    return [
        sa.Column("alvo_platform", sa.String(length=20), nullable=True),
        sa.Column("alvo_tipo", sa.String(length=10), nullable=True),
        sa.Column("alvo_id", sa.String(length=80), nullable=True),
        sa.Column("alvo_nome", sa.String(length=300), nullable=True),
        sa.Column("metrica", sa.String(length=20), nullable=True),
        sa.Column("mudou_em", sa.Date(), nullable=True),
        sa.Column("janela_dias", sa.SmallInteger(), nullable=True),
        sa.Column("linha_base", sa.Numeric(14, 4), nullable=True),
        sa.Column("controle_tipo", sa.String(length=10), nullable=True),
        sa.Column("controle_id", sa.String(length=80), nullable=True),
        sa.Column("controle_nome", sa.String(length=300), nullable=True),
    ]


def upgrade():
    with op.batch_alter_table("marketing_frentes") as batch:
        batch.add_column(sa.Column("meta_vendas_mes", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("verba_mes", sa.Numeric(12, 2), nullable=True))

    calendario = op.create_table(
        "marketing_calendario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "frente",
            sa.String(length=16),
            sa.ForeignKey("marketing_frentes.slug", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("meta_vendas", sa.Integer(), nullable=True),
        sa.Column("verba", sa.Numeric(12, 2), nullable=True),
        sa.Column("foco", sa.Text(), nullable=True),
        sa.Column(
            "updated_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("frente", "mes", name="uq_marketing_calendario_frente_mes"),
        sa.CheckConstraint("mes BETWEEN 1 AND 12", name="ck_marketing_calendario_mes"),
    )
    op.bulk_insert(
        calendario,
        [
            {"frente": frente, "mes": mes, "foco": FOCO.get(frente, {}).get(mes)}
            for frente in FRENTES
            for mes in range(1, 13)
        ],
    )

    with op.batch_alter_table("marketing_posts") as batch:
        batch.add_column(sa.Column("conceito", sa.String(length=120), nullable=True))

    with op.batch_alter_table("marketing_propostas") as batch:
        batch.add_column(sa.Column("frente", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("valor_antes_num", sa.Numeric(12, 2), nullable=True))
        batch.add_column(sa.Column("valor_depois_num", sa.Numeric(12, 2), nullable=True))

    with op.batch_alter_table("marketing_diario") as batch:
        for coluna in _colunas_do_diario():
            batch.add_column(coluna)


def downgrade():
    with op.batch_alter_table("marketing_diario") as batch:
        for coluna in reversed(_colunas_do_diario()):
            batch.drop_column(coluna.name)

    with op.batch_alter_table("marketing_propostas") as batch:
        batch.drop_column("valor_depois_num")
        batch.drop_column("valor_antes_num")
        batch.drop_column("frente")

    with op.batch_alter_table("marketing_posts") as batch:
        batch.drop_column("conceito")

    op.drop_table("marketing_calendario")

    with op.batch_alter_table("marketing_frentes") as batch:
        batch.drop_column("verba_mes")
        batch.drop_column("meta_vendas_mes")
