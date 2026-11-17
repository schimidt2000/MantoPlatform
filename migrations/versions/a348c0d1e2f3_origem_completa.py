"""Origem completa: de qual anúncio, clique ou conversa veio cada venda (feature 348).

Aditiva:
- ``origem_codigos`` (nova): o clique de campanha que chegou ao site e o código curto da mensagem pronta;
- ``conversa_anuncios``: ``ctwa_clid`` (preenchido aqui a partir da mensagem crua) e ``codigo_id``;
- ``anuncios_meta``: o conjunto de anúncios (os já consultados voltam à fila uma vez para ganhá-lo);
- ``orcamento_history`` e ``calendar_events``: a conversa e o contato de origem congelado; no evento,
  também a frente (FK para ``marketing_frentes``);
- ``clients``: o id da campanha de origem (preenchido aqui para as fichas atribuídas pela 334).

O preenchimento do ``ctwa_clid`` roda em Python, linha a linha: a mensagem crua é texto e pode estar
corrompida — o ``dados::json`` do SQL derrubaria a migration inteira na primeira linha ruim. Em produção
as tabelas do CRM estão vazias (CRM desligado): é garantia, não carga.

O ``downgrade`` derruba as colunas e a tabela; os dados novos se perdem.

Revision ID: a348c0d1e2f3
Revises: d334b2c4e6f8
Create Date: 2026-11-17
"""

import json

import sqlalchemy as sa
from alembic import op

revision = "a348c0d1e2f3"
down_revision = "d334b2c4e6f8"
branch_labels = None
depends_on = None

_MARCADORES = ("gclid", "gbraid", "wbraid", "fbclid")
_UTM = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
# (tabela, coluna, tabela alvo, nome da FK) — a conversa e o contato de origem da venda.
_LIGACOES_DA_VENDA = (
    ("orcamento_history", "conversa_id", "conversas", "fk_orcamento_history_conversa_id"),
    ("orcamento_history", "origem_contato_id", "conversa_anuncios", "fk_orcamento_history_origem_contato_id"),
    ("calendar_events", "conversa_id", "conversas", "fk_calendar_events_conversa_id"),
    ("calendar_events", "origem_contato_id", "conversa_anuncios", "fk_calendar_events_origem_contato_id"),
)


def _preencher_ctwa_clid(bind) -> int:
    """O ``ctwa_clid`` dos contatos do WhatsApp que chegaram antes desta feature.

    A chave do contato do WhatsApp é o wamid, o mesmo ``externo_id`` da mensagem crua. Pula a mensagem
    corrompida, sem ``referral`` ou com o campo vazio. Devolve quantos ganharam o valor.
    """
    linhas = bind.execute(
        sa.text(
            "SELECT ca.id, cm.dados FROM conversa_anuncios ca "
            "JOIN conversa_mensagens cm ON cm.externo_id = ca.chave "
            "WHERE ca.canal = 'whatsapp' AND ca.ctwa_clid IS NULL AND cm.dados IS NOT NULL"
        )
    ).fetchall()
    preenchidos = 0
    for contato_id, dados in linhas:
        try:
            mensagem = json.loads(dados)
        except (TypeError, ValueError):
            continue
        referral = mensagem.get("referral") if isinstance(mensagem, dict) else None
        valor = referral.get("ctwa_clid") if isinstance(referral, dict) else None
        if not isinstance(valor, str) or not valor.strip():
            continue
        bind.execute(
            sa.text("UPDATE conversa_anuncios SET ctwa_clid = :v WHERE id = :i"),
            {"v": valor.strip()[:512], "i": contato_id},
        )
        preenchidos += 1
    return preenchidos


def upgrade():
    op.create_table(
        "origem_codigos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(8), nullable=False),
        *(sa.Column(nome, sa.String(512), nullable=True) for nome in _MARCADORES),
        *(sa.Column(nome, sa.String(200), nullable=True) for nome in _UTM),
        sa.Column("campanha_id", sa.String(80), nullable=True),
        sa.Column("pagina", sa.String(500), nullable=True),
        sa.Column("procedencia", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "conversa_id",
            sa.Integer(),
            sa.ForeignKey("conversas.id", name="fk_origem_codigos_conversa_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("usado_em", sa.DateTime(), nullable=True),
        sa.Column(
            "form_response_id",
            sa.Integer(),
            sa.ForeignKey(
                "form_responses.id", name="fk_origem_codigos_form_response_id", ondelete="SET NULL"
            ),
            nullable=True,
        ),
        sa.UniqueConstraint("codigo", name="uq_origem_codigos_codigo"),
    )
    op.create_index("ix_origem_codigos_conversa_id", "origem_codigos", ["conversa_id"])

    op.add_column("conversa_anuncios", sa.Column("ctwa_clid", sa.String(512), nullable=True))
    op.add_column("conversa_anuncios", sa.Column("codigo_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_conversa_anuncios_codigo_id", "conversa_anuncios", "origem_codigos",
        ["codigo_id"], ["id"], ondelete="SET NULL",
    )

    op.add_column("anuncios_meta", sa.Column("conjunto_id", sa.String(64), nullable=True))
    op.add_column("anuncios_meta", sa.Column("conjunto_nome", sa.String(255), nullable=True))

    for tabela, coluna, alvo, fk in _LIGACOES_DA_VENDA:
        op.add_column(tabela, sa.Column(coluna, sa.Integer(), nullable=True))
        op.create_foreign_key(fk, tabela, alvo, [coluna], ["id"], ondelete="SET NULL")
    op.create_index("ix_orcamento_history_conversa_id", "orcamento_history", ["conversa_id"])
    op.create_index("ix_calendar_events_conversa_id", "calendar_events", ["conversa_id"])

    op.add_column("calendar_events", sa.Column("frente", sa.String(16), nullable=True))
    op.create_foreign_key(
        "fk_calendar_events_frente", "calendar_events", "marketing_frentes", ["frente"], ["slug"]
    )

    op.add_column("clients", sa.Column("utm_campaign_id", sa.String(80), nullable=True))

    bind = op.get_bind()
    _preencher_ctwa_clid(bind)
    # O conjunto: os anúncios já consultados com sucesso voltam à fila uma vez (`consultado_em` vazio
    # é a fila da 334). Os que falharam já voltam pela varredura; os definitivos não existem.
    bind.execute(
        sa.text(
            "UPDATE anuncios_meta SET consultado_em = NULL "
            "WHERE erro IS NULL AND NOT definitivo AND consultado_em IS NOT NULL"
        )
    )
    # O id da campanha das fichas que a 334 atribuiu (as mesmas que `_propagar` alcança).
    bind.execute(
        sa.text(
            "UPDATE clients SET utm_campaign_id = anuncios_meta.campanha_id FROM anuncios_meta "
            "WHERE clients.anuncio_origem_id = anuncios_meta.anuncio_id "
            "AND clients.utm_source = 'meta' AND clients.utm_medium = 'anuncio' "
            "AND clients.utm_campaign_id IS NULL AND anuncios_meta.campanha_id IS NOT NULL"
        )
    )


def downgrade():
    op.drop_column("clients", "utm_campaign_id")
    op.drop_constraint("fk_calendar_events_frente", "calendar_events", type_="foreignkey")
    op.drop_column("calendar_events", "frente")
    op.drop_index("ix_calendar_events_conversa_id", table_name="calendar_events")
    op.drop_index("ix_orcamento_history_conversa_id", table_name="orcamento_history")
    for tabela, coluna, _alvo, fk in reversed(_LIGACOES_DA_VENDA):
        op.drop_constraint(fk, tabela, type_="foreignkey")
        op.drop_column(tabela, coluna)
    op.drop_column("anuncios_meta", "conjunto_nome")
    op.drop_column("anuncios_meta", "conjunto_id")
    op.drop_constraint("fk_conversa_anuncios_codigo_id", "conversa_anuncios", type_="foreignkey")
    op.drop_column("conversa_anuncios", "codigo_id")
    op.drop_column("conversa_anuncios", "ctwa_clid")
    op.drop_index("ix_origem_codigos_conversa_id", table_name="origem_codigos")
    op.drop_table("origem_codigos")
