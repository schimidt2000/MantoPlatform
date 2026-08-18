"""Ficha de figurino direto no item avulso do catálogo (reestruturação, fase 1).

Até aqui, só ``catalog_characters`` podia apontar para uma ficha. Um item SEM elenco — Coringa,
Arlequina, Abóbora Maldita, Beetlejuice… — não tinha onde guardar o figurino dele, e quem
organizava o catálogo contornava criando um "elenco" de UM personagem só, com o mesmo nome do
item, dentro do próprio item. O efeito colateral aparecia na vitrine: a seção "Elenco
Individual" da página abria com um card único repetindo a mesma foto da capa.

Esta migration:

1. Cria ``catalog_items.figurino_sheet_id``.
2. **Achata os auto-temas**: item cujo elenco tem exatamente 1 personagem E o nome desse
   personagem é o mesmo do item (comparação sem acento/caixa) passa a vestir a ficha
   diretamente, e o personagem redundante é apagado. Regra deliberadamente estreita — nomes
   apenas parecidos ("Wandinha Addams" contendo "Wandinha", "Aracnídeo" contendo "Aranha") NÃO
   são tocados: são 11 casos que podem ser um tema legítimo de verdade, e a decisão é de quem
   organiza o catálogo, pela ação "Transformar em item avulso" do gerenciador.

Segurança do passo 2: personagem referenciado por uma campanha virtual
(``virtual_campaigns.catalog_character_id`` é NOT NULL) é PULADO — apagá-lo derrubaria a
campanha. Na base de produção conferida não havia nenhum, mas a guarda fica.

O downgrade recria os personagens achatados a partir do item, para a volta ser simétrica.

Revision ID: c8f4d92e17ab
Revises: b7e3a91d5c24
Create Date: 2026-08-18
"""

import unicodedata

import sqlalchemy as sa
from alembic import op

revision = "c8f4d92e17ab"
down_revision = "b7e3a91d5c24"
branch_labels = None
depends_on = None


def _norm(value: str) -> str:
    """Minúsculas sem acento — mesma normalização de nome usada no resto do catálogo."""
    decomposed = unicodedata.normalize("NFKD", (value or "").lower().strip())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def upgrade() -> None:
    op.add_column(
        "catalog_items", sa.Column("figurino_sheet_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_catalog_items_figurino_sheet_id",
        "catalog_items",
        "figurino_sheets",
        ["figurino_sheet_id"],
        ["id"],
        ondelete="SET NULL",
    )

    conn = op.get_bind()
    # Itens com elenco de exatamente 1 personagem — candidatos a auto-tema.
    candidatos = conn.execute(
        sa.text(
            """
            SELECT i.id AS item_id, i.name AS item_name,
                   c.id AS char_id, c.name AS char_name, c.figurino_sheet_id
              FROM catalog_items i
              JOIN catalog_characters c ON c.catalog_item_id = i.id
             WHERE (SELECT COUNT(*) FROM catalog_characters c2
                     WHERE c2.catalog_item_id = i.id) = 1
            """
        )
    ).fetchall()

    com_campanha = {
        row[0]
        for row in conn.execute(
            sa.text("SELECT DISTINCT catalog_character_id FROM virtual_campaigns")
        ).fetchall()
    }

    achatados = 0
    for row in candidatos:
        if _norm(row.char_name) != _norm(row.item_name):
            continue
        if row.char_id in com_campanha:
            continue
        conn.execute(
            sa.text(
                "UPDATE catalog_items SET figurino_sheet_id = :sheet WHERE id = :item"
            ),
            {"sheet": row.figurino_sheet_id, "item": row.item_id},
        )
        conn.execute(
            sa.text("DELETE FROM catalog_characters WHERE id = :char"),
            {"char": row.char_id},
        )
        achatados += 1
    print(f"[migration c8f4d92e17ab] auto-temas achatados: {achatados}")


def downgrade() -> None:
    conn = op.get_bind()
    # Devolve um personagem para cada item que ganhou ficha direta, restaurando o auto-tema.
    itens = conn.execute(
        sa.text(
            """
            SELECT id, name, slug, figurino_sheet_id
              FROM catalog_items
             WHERE figurino_sheet_id IS NOT NULL
               AND (SELECT COUNT(*) FROM catalog_characters c
                     WHERE c.catalog_item_id = catalog_items.id) = 0
            """
        )
    ).fetchall()
    for item in itens:
        conn.execute(
            sa.text(
                """
                INSERT INTO catalog_characters
                       (catalog_item_id, name, slug, figurino_sheet_id, position, is_active,
                        created_at)
                VALUES (:item, :name, :slug, :sheet, 0, TRUE, NOW())
                """
            ),
            {
                "item": item.id,
                "name": item.name,
                "slug": f"{item.slug}-{item.id}",
                "sheet": item.figurino_sheet_id,
            },
        )

    op.drop_constraint(
        "fk_catalog_items_figurino_sheet_id", "catalog_items", type_="foreignkey"
    )
    op.drop_column("catalog_items", "figurino_sheet_id")
