"""EducaManto por responsabilidades: pacotes por nível viram musicais (feature 235).

Os antigos ``educamanto_packages`` (7 espetáculos × 3 níveis + 1 cópia órfã) viram
``educamanto_musicals``: UMA linha por espetáculo, preservando os ids dos pacotes Master
(o "Recalcular" de snapshots antigos mapeia por id). Os níveis morrem — o que era a diferença
entre eles (som, alimentação, gráfica) virou responsabilidade escolhida por orçamento, com os
custos em colunas próprias:

- item "Som"                  → REMOVIDO (som/iluminação viram tabela única por
  combinação em ``pricing_config['educamanto_som_luz']`` — 3ª rodada)
- item "Catering apresentação"→ ``custo_alimentacao_*``   (bloco Alimentação, por pessoa)
- item "Catering ensaio"      → ``custo_catering_ensaio_pp`` (por pessoa POR ENSAIO)
- item "Ajuda de custo ensaio"→ ``custo_ajuda_ensaio_pp``    (por pessoa POR ENSAIO)
- item "Transporte" (R$ 600)  → REMOVIDO (regra nova: caminhão R$ 800 dentro de SP via
  pricing_config; fora de SP, 2 vans — nada no musical)

``num_personagens``/``num_producao`` são derivados dos itens reais, regra do dono
(4ª rodada): personagens = Σ qty de "Cara Limpa" + "Bonecos" + "Papai Noel"; produção =
qty do item "Produção" (fallback 2). Cenógrafo/Maquiador ficam fora das contagens (não
entravam como personagens nem produção; o headcount antigo do catering os incluía).

Downgrade restaura a ESTRUTURA antiga, mas não os níveis podados (Intermediário/Econômica/
cópia) — fazer dump antes do deploy, conforme plano da feature.

Revision ID: b7e3a91d5c24
Revises: f4a8d61c9e27
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "b7e3a91d5c24"
down_revision = "f4a8d61c9e27"
branch_labels = None
depends_on = None

# (coluna, server_default) — todas Float exceto as Integer marcadas.
# Sem custo_cenario_*: cenário saiu das responsabilidades na 4ª rodada (sem custo).
_NOVAS_FLOAT = [
    ("custo_alimentacao_1s", "55"), ("custo_alimentacao_2s", "73"),
    ("custo_catering_ensaio_pp", "28"), ("custo_ajuda_ensaio_pp", "50"),
]
_NOVAS_INT = [("num_personagens", "0"), ("num_producao", "0"), ("num_ensaios", "2")]


def upgrade() -> None:
    # ── Estrutura: renames + colunas novas ────────────────────────────────────────────────
    op.rename_table("educamanto_packages", "educamanto_musicals")
    op.rename_table("educamanto_items", "educamanto_musical_items")
    op.alter_column("educamanto_musical_items", "package_id", new_column_name="musical_id")

    for name, default in _NOVAS_INT:
        op.add_column(
            "educamanto_musicals",
            sa.Column(name, sa.Integer(), nullable=False, server_default=default),
        )
    for name, default in _NOVAS_FLOAT:
        op.add_column(
            "educamanto_musicals",
            sa.Column(name, sa.Float(), nullable=False, server_default=default),
        )
    op.drop_column("educamanto_musicals", "commission_rate")

    # ── Dados: poda dos níveis e realocação dos itens que viraram colunas ────────────────
    bind = op.get_bind()

    # 1. Poda: só os Master ficam (e viram os musicais); a "Cópia de ..." órfã sai junto.
    bind.execute(sa.text(
        "DELETE FROM educamanto_musical_items WHERE musical_id IN ("
        "  SELECT id FROM educamanto_musicals"
        "  WHERE name NOT LIKE '%Master%' OR name LIKE 'Cópia de%')"
    ))
    bind.execute(sa.text(
        "DELETE FROM educamanto_musicals"
        " WHERE name NOT LIKE '%Master%' OR name LIKE 'Cópia de%'"
    ))

    # 2. Equipe declarada, regra do dono (4ª rodada): personagens = Cara Limpa + Bonecos
    #    (+ Papai Noel); produção = item "Produção" (fallback 2). Cenógrafo/Maquiador fora.
    bind.execute(sa.text(
        "UPDATE educamanto_musicals m SET"
        "  num_producao = COALESCE((SELECT i.qty FROM educamanto_musical_items i"
        "    WHERE i.musical_id = m.id AND i.name = 'Produção'), 2),"
        "  num_personagens = COALESCE((SELECT SUM(i.qty) FROM educamanto_musical_items i"
        "    WHERE i.musical_id = m.id"
        "    AND i.name IN ('Cara Limpa', 'Bonecos', 'Papai Noel')), 0),"
        "  num_ensaios = 2"
    ))

    # 3. Itens que viram colunas do musical.
    # O item "Som" NÃO vira coluna (3ª rodada): som/iluminação são a tabela única por
    # combinação em pricing_config — o item é simplesmente removido no passo 4.
    _mover = [
        ("Catering apresentação",
         "custo_alimentacao_1s = i.cost_1s, custo_alimentacao_2s = i.cost_2s"),
        ("Catering ensaio", "custo_catering_ensaio_pp = i.cost_1s"),
        ("Ajuda de custo ensaio", "custo_ajuda_ensaio_pp = i.cost_1s"),
    ]
    for item_name, assignments in _mover:
        bind.execute(sa.text(
            f"UPDATE educamanto_musicals m SET {assignments}"
            "  FROM educamanto_musical_items i"
            "  WHERE i.musical_id = m.id AND i.name = :nome"
        ), {"nome": item_name})

    # 4. Itens absorvidos ou substituídos por regra saem da lista.
    bind.execute(sa.text(
        "DELETE FROM educamanto_musical_items WHERE name IN"
        " ('Som', 'Catering apresentação', 'Catering ensaio',"
        "  'Ajuda de custo ensaio', 'Transporte')"
    ))

    # 5. Nome limpo: "Uma Aventura Animal - Master" → "Uma Aventura Animal".
    bind.execute(sa.text(
        "UPDATE educamanto_musicals SET name = REPLACE(name, ' - Master', '')"
    ))


def downgrade() -> None:
    """Restaura a estrutura antiga. Os níveis podados NÃO retornam (restaurar do dump)."""
    op.add_column(
        "educamanto_musicals",
        sa.Column("commission_rate", sa.Float(), nullable=False, server_default="0.05"),
    )
    for name, _ in [*_NOVAS_FLOAT, *_NOVAS_INT]:
        op.drop_column("educamanto_musicals", name)
    op.alter_column("educamanto_musical_items", "musical_id", new_column_name="package_id")
    op.rename_table("educamanto_musical_items", "educamanto_items")
    op.rename_table("educamanto_musicals", "educamanto_packages")
