"""Editor de formulários: tabela form_field_definitions + seed dos campos atuais (feature 123).

Revision ID: a51ce3dc4f3c
Revises: d5e6f7a8b9c0
Create Date: 2026-07-09
"""

import json
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "a51ce3dc4f3c"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


TIPOS_CONTRATACAO = ["Receptivo e Interativo", "Receptivo, Interativo e Show", "Social"]
ESPACOS_EVENTO = ["Residência", "Buffet", "Salão de Festas", "Outro"]
PAGAMENTO_COMUM = [
    "À vista",
    "Em 2x no PIX (50% no ato + 50% em até 2 dias antes do evento)",
    "Cartão de Crédito (em até 3x com acréscimo de 15%)",
    "Outros",
]
PAGAMENTO_CORPORATIVO = ["À vista antecipado", "Em 2x", "Faturado", "Boleto", "Outros"]

# (section_name, field_key, field_type, label, help_text, placeholder, required, options, is_system)
COMUM_FIELDS = [
    ("Dados do Contratante", "nome_contratante", "texto_curto", "Nome Completo Contratante", None, None, True, None, True),
    ("Dados do Contratante", "endereco_contratante", "texto_curto", "Endereço completo da contratante", None, "ENDEREÇO DA CONTRATANTE", True, None, True),
    ("Dados do Contratante", "cpf", "cpf", "CPF", None, None, True, None, True),
    ("Dados do Contratante", "email", "email", "E-mail", None, None, True, None, False),
    ("Dados do Contratante", "whatsapp", "telefone", "Número de WhatsApp", "Esse número será usado para assinar o contrato", None, True, None, True),
    ("Dados do Contratante", "assessoria", "telefone", "Gostaria que a confirmação do evento seja com assessoria? Se sim, digite o telefone", None, None, False, None, False),
    ("Dados do Evento", "nome_aniversariante", "texto_curto", "Nome do Aniversariante", None, None, False, None, False),
    ("Dados do Evento", "idade_aniversariante", "texto_curto", "Idade a Completar do Aniversariante", None, None, False, None, False),
    ("Dados do Evento", "tipo_contratacao", "selecao", "Tipo de Contratação", None, None, True, TIPOS_CONTRATACAO, False),
    ("Dados do Evento", "qtd_personagens", "texto_curto", "Quantidade de Personagens", None, None, True, None, False),
    ("Dados do Evento", "quais_personagens", "texto_curto", "Quais personagens?", None, None, True, None, False),
    ("Dados do Evento", "tema_evento", "texto_curto", "Tema do Evento", None, None, True, None, False),
    ("Dados do Evento", "data_evento", "data", "Data do Evento", None, None, True, None, True),
    ("Dados do Evento", "hora_evento", "hora", "Hora do Evento", None, None, True, None, True),
    ("Dados do Evento", "periodo_contratacao", "texto_curto", "Período De Contratação", None, "Ex.: das 15h às 19h", True, None, False),
    ("Endereço do Evento", "espaco_evento", "selecao", "Espaço Escolhido para o Evento", None, None, True, ESPACOS_EVENTO, False),
    ("Endereço do Evento", "cep", "cep", "CEP", None, None, True, None, True),
    ("Endereço do Evento", "logradouro", "texto_curto", "Logradouro", None, "Nome da Rua ou Avenida", True, None, True),
    ("Endereço do Evento", "numero", "texto_curto", "Número", None, None, True, None, False),
    ("Endereço do Evento", "complemento", "texto_curto", "Complemento", None, None, False, None, False),
    ("Endereço do Evento", "bairro", "texto_curto", "Bairro", None, None, True, None, True),
    ("Endereço do Evento", "cidade", "texto_curto", "Cidade", None, None, True, None, True),
    ("Endereço do Evento", "estado", "texto_curto", "Estado", None, "SP", True, None, True),
    ("Pagamento e Observações", "forma_pagamento", "selecao", "Forma de Pagamento", None, None, True, PAGAMENTO_COMUM, False),
    ("Pagamento e Observações", "descreva_outros", "texto_curto", "Descreva Outros", None, None, False, None, False),
    ("Pagamento e Observações", "observacoes", "texto_longo", "Observações Contratuais", None, None, False, None, False),
]

CORPORATIVO_FIELDS = [
    ("Informações da Empresa", "razao_social", "texto_curto", "Razão Social", None, None, True, None, True),
    ("Informações da Empresa", "cnpj", "cnpj", "CNPJ", None, None, True, None, True),
    ("Informações da Empresa", "representante_legal", "texto_curto", "Representante Legal", None, None, True, None, False),
    ("Informações da Empresa", "email", "email", "E-mail", None, None, True, None, False),
    ("Informações da Empresa", "telefone", "telefone", "Telefone", None, None, True, None, False),
    ("Informações da Empresa", "endereco_empresa", "texto_curto", "Endereço", None, None, True, None, True),
    ("Responsável pelo Preenchimento", "nome_responsavel", "texto_curto", "Nome Completo", None, None, True, None, False),
    ("Responsável pelo Preenchimento", "cpf_responsavel", "cpf", "CPF", None, None, True, None, False),
    ("Responsável pelo Preenchimento", "whatsapp", "telefone", "Número de WhatsApp", None, None, True, None, True),
    ("Dados do Evento Corporativo", "data_evento", "data", "Data do Evento", None, None, True, None, True),
    ("Dados do Evento Corporativo", "hora_evento", "hora", "Hora do Evento", None, None, True, None, True),
    ("Dados do Evento Corporativo", "endereco_evento", "texto_curto", "Endereço completo do evento", None, None, True, None, False),
    ("Dados do Evento Corporativo", "periodo_contratacao", "texto_curto", "Período de Contratação", None, None, True, None, False),
    ("Dados do Evento Corporativo", "briefing", "texto_longo", "Briefing do Evento", None, None, True, None, False),
    ("Condições de Pagamento", "forma_pagamento", "selecao", "Forma de Pagamento", None, None, True, PAGAMENTO_CORPORATIVO, False),
    ("Condições de Pagamento", "descreva_outros", "texto_curto", "Descreva Outros", None, None, False, None, False),
]


def _rows(form_type: str, fields: list[tuple]) -> list[dict]:
    rows = []
    for order, (section, key, ftype, label, help_text, placeholder, required, options, is_system) in enumerate(fields):
        rows.append({
            "form_type": form_type,
            "section_name": section,
            "field_key": key,
            "field_type": ftype,
            "label": label,
            "help_text": help_text,
            "placeholder": placeholder,
            "required": required,
            "options": json.dumps(options, ensure_ascii=False) if options else None,
            "order": order,
            "is_system": is_system,
        })
    return rows


def upgrade():
    op.create_table(
        "form_field_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("form_type", sa.String(length=20), nullable=False),
        sa.Column("section_name", sa.String(length=100), nullable=False),
        sa.Column("field_key", sa.String(length=60), nullable=False),
        sa.Column("field_type", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("help_text", sa.String(length=300), nullable=True),
        sa.Column("placeholder", sa.String(length=200), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("options", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("form_type", "field_key", name="uq_form_field_key"),
    )

    table = sa.table(
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
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.utcnow()
    seed_rows = _rows("comum", COMUM_FIELDS) + _rows("corporativo", CORPORATIVO_FIELDS)
    for row in seed_rows:
        row["created_at"] = now
        row["updated_at"] = now
    op.bulk_insert(table, seed_rows)


def downgrade():
    op.drop_table("form_field_definitions")
