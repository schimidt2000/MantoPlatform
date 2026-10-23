"""PIX recebido lido do aviso por e-mail e ligado à venda (feature 318).

O "recebido" de uma venda era só a soma dos comprovantes anexados à mão, dias depois do PIX; o
cruzamento de 21/10/2026 achou R$ 209 mil de dinheiro de cliente sem registro e nenhuma informação
de qual conta recebeu (o MEI recebeu R$ 887 mil no período). A 318 lê os avisos "Pix recebido" do
Inter e liga o PIX à venda — sozinho quando é óbvio, "É esta?" quando há dúvida.

- `contas_recebimento` (nova): as contas da empresa, semeadas **sem número** (número de conta não
  vai para o repositório; o Superadmin preenche).
- `pix_recebidos` (nova): um aviso por linha, `message_id` único (idempotência).
- `event_payments`: `file_path` passa a aceitar NULL — só na origem PIX, garantido por CHECK —,
  ganha `conta_id` e `origem` (default `comprovante`, então toda linha existente fica como antes).
- `site_settings`: interruptor (nasce desligado), início da leitura, pagadores próprios e último
  erro.

Aditiva: nenhuma coluna existente muda de tipo; relaxar o NOT NULL não reescreve dado, e a soma do
recebido não muda de fórmula (pagamento de PIX é um `event_payments` como qualquer outro).

Rollback: reverter o merge sem `downgrade` é limpo enquanto a leitura estiver desligada. Depois de
ligada, o código antigo lê pagamentos sem arquivo como `file_path` vazio (link "Ver comprovante"
quebrado no Jinja e no React, sem erro) e a soma do recebido continua certa. O `downgrade` APAGA os
pagamentos de origem PIX sem arquivo (o NOT NULL não volta com eles) — o saldo dessas vendas volta a
subir.

Revision ID: d318a4c9e2b7
Revises: d3c7a1e5b317
Create Date: 2026-10-22
"""

import sqlalchemy as sa
from alembic import op

revision = "d318a4c9e2b7"
down_revision = "d3c7a1e5b317"
branch_labels = None
depends_on = None

_CONTAS = (
    ("Inter MEI", "mei", "inter"),
    ("Inter Prime", "pj", "inter"),
    ("InfinitePay Prime", "pj", "infinitepay"),
    ("Cora Monta", "pj", "cora"),
)


def upgrade() -> None:
    contas = op.create_table(
        "contas_recebimento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("apelido", sa.String(60), nullable=False, unique=True),
        sa.Column("titular_tipo", sa.String(10), nullable=False),
        sa.Column("banco", sa.String(30), nullable=False),
        sa.Column("numero_conta", sa.String(30), nullable=True, unique=True),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.bulk_insert(
        contas,
        [{"apelido": a, "titular_tipo": t, "banco": b} for a, t, b in _CONTAS],
    )

    with op.batch_alter_table("event_payments") as batch:
        batch.alter_column("file_path", existing_type=sa.String(300), nullable=True)
        batch.add_column(
            sa.Column(
                "conta_id",
                sa.Integer(),
                sa.ForeignKey(
                    "contas_recebimento.id",
                    name="fk_event_payments_conta_id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column("origem", sa.String(20), nullable=False, server_default="comprovante")
        )
        batch.create_check_constraint(
            "ck_event_payments_arquivo_ou_pix", "file_path IS NOT NULL OR origem = 'pix_email'"
        )

    op.create_table(
        "pix_recebidos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("message_id", sa.String(300), nullable=False, unique=True),
        sa.Column("e2e_id", sa.String(64), nullable=True, unique=True),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column(
            "conta_id",
            sa.Integer(),
            sa.ForeignKey("contas_recebimento.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("numero_conta_lido", sa.String(30), nullable=True),
        sa.Column("titular_lido", sa.String(30), nullable=True),
        sa.Column("valor", sa.Numeric(12, 2), nullable=True),
        sa.Column("pagador_nome", sa.String(200), nullable=True),
        sa.Column("pagador_norm", sa.String(200), nullable=True),
        sa.Column("recebido_em", sa.DateTime(), nullable=False),
        sa.Column("autenticado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("estado", sa.String(20), nullable=False, server_default="novo"),
        sa.Column("tipo_sugestao", sa.String(25), nullable=True),
        sa.Column("candidatos", sa.JSON(), nullable=True),
        sa.Column("descartados", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "event_payment_id",
            sa.Integer(),
            sa.ForeignKey("event_payments.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column("pagamentos_extra", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "decidido_por_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decidido_em", sa.DateTime(), nullable=True),
        sa.Column("assunto", sa.String(200), nullable=True),
        sa.Column("remetente", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_pix_recebidos_estado", "pix_recebidos", ["estado"])
    op.create_index("ix_pix_recebidos_recebido_em", "pix_recebidos", ["recebido_em"])
    op.create_index("ix_pix_recebidos_pagador_norm", "pix_recebidos", ["pagador_norm"])

    with op.batch_alter_table("site_settings") as batch:
        batch.add_column(
            sa.Column("pix_email_ativo", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(sa.Column("pix_email_ativo_desde", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("pix_pagadores_proprios", sa.Text(), nullable=True))
        batch.add_column(sa.Column("pix_email_ultimo_erro", sa.Text(), nullable=True))
        batch.add_column(sa.Column("pix_email_ultimo_erro_em", sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE site_settings SET pix_pagadores_proprios = 'Prime Dreams' || chr(10) || "
        "'Monta Producoes' WHERE pix_pagadores_proprios IS NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("site_settings") as batch:
        batch.drop_column("pix_email_ultimo_erro_em")
        batch.drop_column("pix_email_ultimo_erro")
        batch.drop_column("pix_pagadores_proprios")
        batch.drop_column("pix_email_ativo_desde")
        batch.drop_column("pix_email_ativo")

    op.drop_index("ix_pix_recebidos_pagador_norm", table_name="pix_recebidos")
    op.drop_index("ix_pix_recebidos_recebido_em", table_name="pix_recebidos")
    op.drop_index("ix_pix_recebidos_estado", table_name="pix_recebidos")
    op.drop_table("pix_recebidos")

    # O NOT NULL só volta sem os pagamentos de PIX sem arquivo (ver o docstring).
    op.execute("DELETE FROM event_payments WHERE file_path IS NULL")
    with op.batch_alter_table("event_payments") as batch:
        batch.drop_constraint("ck_event_payments_arquivo_ou_pix", type_="check")
        batch.drop_constraint("fk_event_payments_conta_id", type_="foreignkey")
        batch.drop_column("origem")
        batch.drop_column("conta_id")
        batch.alter_column("file_path", existing_type=sa.String(300), nullable=False)

    op.drop_table("contas_recebimento")
