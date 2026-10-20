"""Congela o dinheiro do cancelamento: três tabelas novas (feature 306).

O cancelamento da 224 zerava a comissão, escondia o BV e deixava a devolução solta: o que a Manto
retém (pago − devolvido) sumia da DRE, da comissão e do BV. A 306 congela no ato o que a conta
do retido precisa e não pode ser relido ao vivo depois — a venda, a comissão cheia, a taxa, o
custo do EducaManto, o beneficiário, a nota e o imposto (`event_cancellations`), cada BV do ato
com o que já estava pago (`event_cancellation_bvs`) e a lista do elenco de cada dia alcançado,
para a multa (`event_cancellation_elenco`). Pago e devolvido não são gravados: são lidos ao vivo.

Aditiva: nenhuma tabela existente ganha coluna, índice, tipo ou default, e o código anterior lê e
grava no banco migrado. Evento cancelado sem linha é `legado` (o cancelado de antes do deploy).

Rollback: reverter o merge, sem `downgrade`, é limpo até o primeiro cancelamento real. Depois
dele:
- o código antigo zera a comissão do retido na primeira abertura de Comissões ou da Planilha
  (`should_have`);
- o código antigo toma o ajuste do corte de dia (`a_pagar` com `original_id`, ligado ao principal
  vivo) pela comissão do evento e o regrava com a cheia (`_comissao_existente`);
- o código antigo lista pelo cheio o BV não pago do cancelado (`_build_bv_items`), e a Planilha
  da 305 deixa marcá-lo pago por esse valor;
- o código antigo deixa excluir o cancelado vazio, inclusive pelo sync, e o CASCADE leva o
  congelamento junto;
- o `downgrade` apaga o congelamento sem volta;
- ensaios apagados, e-mails enviados e a venda passada de dia não voltam.

A partir daí, defeito se corrige para a frente (306b).

Revision ID: c5d2f7a9e306
Revises: a7c3e91f4d28
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "c5d2f7a9e306"
down_revision = "a7c3e91f4d28"
branch_labels = None
depends_on = None

_INDICES_DO_ELENCO = ("cancellation_id", "talent_id", "role_id", "day_event_id")


def upgrade() -> None:
    op.create_table(
        "event_cancellations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("calendar_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("regime", sa.String(12), nullable=False),
        sa.Column("refund_mode", sa.String(8), nullable=True),
        sa.Column("sale_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("commission_full", sa.Numeric(12, 2), nullable=True),
        sa.Column("commission_rate", sa.Numeric(6, 3), nullable=True),
        sa.Column("commission_cost", sa.Numeric(12, 2), nullable=True),
        # Sem `ondelete`: o beneficiário e o vendedor congelados bloqueiam a exclusão do usuário.
        sa.Column("commission_seller_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("with_invoice", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retained_tax", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "group_leader_id",
            sa.Integer(),
            sa.ForeignKey("calendar_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sale_handed_over", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sale_value_before", sa.Numeric(12, 2), nullable=True),
        sa.Column("sale_value_after", sa.Numeric(12, 2), nullable=True),
        sa.Column("sale_value_gross_before", sa.Numeric(12, 2), nullable=True),
        sa.Column("sale_value_gross_after", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("event_id", name="uq_event_cancellations_event_id"),
    )
    op.create_index(
        "ix_event_cancellations_group_leader_id", "event_cancellations", ["group_leader_id"]
    )

    op.create_table(
        "event_cancellation_bvs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "cancellation_id",
            sa.Integer(),
            sa.ForeignKey("event_cancellations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "acrescimo_id",
            sa.Integer(),
            sa.ForeignKey("event_acrescimos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recipient", sa.String(200), nullable=True),
        sa.Column("pix", sa.String(140), nullable=True),
        sa.Column("original_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_at_cancellation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=True),
        sa.UniqueConstraint("acrescimo_id", name="uq_event_cancellation_bvs_acrescimo_id"),
    )
    op.create_index(
        "ix_event_cancellation_bvs_cancellation_id", "event_cancellation_bvs", ["cancellation_id"]
    )

    op.create_table(
        "event_cancellation_elenco",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "cancellation_id",
            sa.Integer(),
            sa.ForeignKey("event_cancellations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Sem `ondelete`: artista com multa não some.
        sa.Column("talent_id", sa.Integer(), sa.ForeignKey("talents.id"), nullable=False),
        sa.Column(
            "role_id", sa.Integer(), sa.ForeignKey("event_roles.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "day_event_id",
            sa.Integer(),
            sa.ForeignKey("calendar_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("character_name", sa.String(120), nullable=False),
        sa.Column("cache_reference", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "special_expense_id",
            sa.Integer(),
            sa.ForeignKey("special_expenses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "special_expense_id", name="uq_event_cancellation_elenco_special_expense_id"
        ),
    )
    for coluna in _INDICES_DO_ELENCO:
        op.create_index(
            f"ix_event_cancellation_elenco_{coluna}", "event_cancellation_elenco", [coluna]
        )


def downgrade() -> None:
    # Filhas primeiro: elenco → bvs → cancelamentos. Apaga o congelamento sem volta.
    for coluna in reversed(_INDICES_DO_ELENCO):
        op.drop_index(f"ix_event_cancellation_elenco_{coluna}", table_name="event_cancellation_elenco")
    op.drop_table("event_cancellation_elenco")
    op.drop_index("ix_event_cancellation_bvs_cancellation_id", table_name="event_cancellation_bvs")
    op.drop_table("event_cancellation_bvs")
    op.drop_index("ix_event_cancellations_group_leader_id", table_name="event_cancellations")
    op.drop_table("event_cancellations")
