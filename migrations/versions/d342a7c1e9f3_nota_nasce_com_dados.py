"""O pedido de nota já nasce com os dados que a emissão exige (feature 342).

- ``calendar_events.nota_email``: para onde a nota é enviada.
- ``form_field_definitions.show_if_key`` / ``show_if_value``: campo condicional.
- Cinco campos do sistema na seção "Nota fiscal" de cada formulário público (os campos originais
  também nasceram em migration, ``a51ce3dc4f3c``). Entram no fim da ordem, e só se a chave ainda
  não existir: o ``upgrade`` pode rodar de novo sem duplicar.

Aditiva: o código anterior lê e grava no banco migrado (o formulário antigo mostraria as perguntas
da nota sem a condição durante os minutos do deploy; nenhuma é exigida sem "Preciso de nota fiscal",
porque quem exige é o servidor novo). Rollback = reverter o merge; o ``downgrade`` apaga os dez
campos e as colunas — as respostas já salvas guardam o texto no próprio JSON e não se perdem.

Revision ID: d342a7c1e9f3
Revises: d323b5a1c0e7
Create Date: 2026-11-10
"""

import json
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "d342a7c1e9f3"
down_revision = "d323b5a1c0e7"
branch_labels = None
depends_on = None

SECAO = "Nota fiscal"
FORMULARIOS = ("comum", "corporativo")
CHAVE_MAE = "precisa_nota"

# (chave, tipo, rótulo, ajuda, placeholder, obrigatório, opções, condicional)
CAMPOS = (
    (CHAVE_MAE, "sim_nao", "Preciso de nota fiscal", None, None, False, None, False),
    (
        "nota_doc",
        "cpf_cnpj",
        "CNPJ ou CPF de quem vai receber a nota",
        "Com o CNPJ, a gente já encontra a razão social e o endereço.",
        None,
        True,
        None,
        True,
    ),
    (
        "nota_email",
        "email",
        "E-mail para receber a nota",
        None,
        None,
        True,
        None,
        True,
    ),
    (
        "nota_iss",
        "selecao",
        "A empresa retém o ISS da nota?",
        'Se não tiver certeza, escolha "Não sei" e a gente confirma com você.',
        None,
        True,
        ["Não", "Sim", "Não sei"],
        True,
    ),
    (
        "nota_referencia",
        "texto_curto",
        "Precisa que algo apareça na nota?",
        "Número do pedido ou da ordem de compra, por exemplo. Se não precisar, deixe em branco.",
        "Ex.: Pedido 4411",
        False,
        None,
        True,
    ),
)

_CHAVES = tuple(campo[0] for campo in CAMPOS)


def _tabela() -> sa.Table:
    return sa.table(
        "form_field_definitions",
        sa.column("form_type", sa.String),
        sa.column("section_name", sa.String),
        sa.column("field_key", sa.String),
        sa.column("field_type", sa.String),
        sa.column("label", sa.String),
        sa.column("help_text", sa.String),
        sa.column("placeholder", sa.String),
        sa.column("required", sa.Boolean),
        sa.column("options", sa.Text),
        sa.column("order", sa.Integer),
        sa.column("is_system", sa.Boolean),
        sa.column("show_if_key", sa.String),
        sa.column("show_if_value", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )


def _semear(conn: sa.engine.Connection) -> None:
    tabela = _tabela()
    agora = datetime.utcnow()
    for form_type in FORMULARIOS:
        existentes = {
            linha[0]
            for linha in conn.execute(
                sa.select(tabela.c.field_key).where(tabela.c.form_type == form_type)
            )
        }
        ultimo = conn.execute(
            sa.select(sa.func.max(tabela.c.order)).where(tabela.c.form_type == form_type)
        ).scalar()
        ordem = (ultimo if ultimo is not None else -1) + 1
        for chave, tipo, rotulo, ajuda, placeholder, obrigatorio, opcoes, condicional in CAMPOS:
            if chave in existentes:
                continue
            conn.execute(
                tabela.insert().values(
                    form_type=form_type,
                    section_name=SECAO,
                    field_key=chave,
                    field_type=tipo,
                    label=rotulo,
                    help_text=ajuda,
                    placeholder=placeholder,
                    required=obrigatorio,
                    options=json.dumps(opcoes, ensure_ascii=False) if opcoes else None,
                    order=ordem,
                    is_system=True,
                    show_if_key=CHAVE_MAE if condicional else None,
                    show_if_value="Sim" if condicional else None,
                    created_at=agora,
                    updated_at=agora,
                )
            )
            ordem += 1


def upgrade():
    with op.batch_alter_table("calendar_events") as batch:
        batch.add_column(sa.Column("nota_email", sa.String(200), nullable=True))

    with op.batch_alter_table("form_field_definitions") as batch:
        batch.add_column(sa.Column("show_if_key", sa.String(60), nullable=True))
        batch.add_column(sa.Column("show_if_value", sa.String(200), nullable=True))

    _semear(op.get_bind())


def downgrade():
    tabela = _tabela()
    op.get_bind().execute(
        tabela.delete().where(
            tabela.c.field_key.in_(_CHAVES), tabela.c.section_name == SECAO, tabela.c.is_system
        )
    )

    with op.batch_alter_table("form_field_definitions") as batch:
        batch.drop_column("show_if_value")
        batch.drop_column("show_if_key")

    with op.batch_alter_table("calendar_events") as batch:
        batch.drop_column("nota_email")
