"""Cadastro de fornecedores dos gastos extras (feature 352).

Aditiva, com reescrita de dados:
- ``fornecedores``: o cadastro, com ``nome_normalizado`` único;
- ``special_expenses.fornecedor_id``: o vínculo do gasto (``ON DELETE SET NULL``);
- importação: os gastos a fornecedor já lançados viram fornecedores, juntando as grafias do mesmo
  fornecedor (mesma chave PIX normalizada OU mesmo nome normalizado), e cada gasto passa a apontar
  para o seu e a exibir o nome arrumado. A chave PIX gravada nos gastos NÃO muda.

O ``downgrade`` derruba a coluna e a tabela; os nomes reescritos nos gastos antigos ficam como estão
(a grafia original sobrevive só nos dumps noturnos).

Revision ID: f352a1b2c3d4
Revises: d334b2c4e6f8
Create Date: 2026-11-17
"""

import logging
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "f352a1b2c3d4"
down_revision = "d334b2c4e6f8"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

# As cinco categorias que a pessoa escolhe no gasto; devolução e multa nascem só pelo cancelamento.
CATEGORIAS_DO_FORNECEDOR = {"Figurino", "Escritório", "Marketing", "Manutenção", "Outros"}

# Nome arrumado de cada grupo, decidido sobre as 65 grafias de produção em 17/11 (plan.md §7).
# A chave é o nome normalizado de UMA das grafias do grupo. Só nomes: chave PIX e documento nunca
# entram no repositório. Grafia fora desta tabela cai na regra geral (`_nome_do_grupo`).
NOMES_ARRUMADOS = {
    "adao lima da silva": "Adão Lima da Silva",
    "real producoes ramon rossi": "Real Produções (Ramon Rossi)",
    "andressa carvalho lages do vale": "Andressa Carvalho Lages do Vale",
    "beatriz hornink boneti": "Beatriz Hornink Boneti",
    "sara castelo": "Sara Castelo (Castelo das Iludidos)",
    "studio de art diego motta": "Studio de Art Diego Motta",
    "do motoboy fatima": "Motoboy da Fátima",
    "karen madureira": "Karen Madureira",
    "marcelo lima": "Marcelo Lima",
    "meta": "Meta (Sheila e David)",
    "peterson caminhao": "Peterson (caminhão)",
    "rosangela": "Rosângela",
    "thunder print 3d": "Thunder Print 3D",
    "william castro": "William Castro",
    "jose carlos c daudt": "Jose Carlos C. Daudt",
    "kelvem jhonata almeida da cruz": "Kelvem Jhonata Almeida da Cruz",
    "mercado livre": "Mercado Livre",
    "talita stefani de castro will castro": "Talita Stefani de Castro (Will Castro)",
    "victor santos de santana": "Victor Santos de Santana",
    "certificado digital": "Certificado Digital",
}


def _normalizar_nome(texto: str | None) -> str:
    """Cópia de `app.gastos.fornecedor_ops.normalizar_nome` — a migration não importa `app/` (o
    código muda; a migration fica congelada). O verify_352 confere que as duas dão o mesmo."""
    decomposto = unicodedata.normalize("NFD", (texto or "").lower())
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sem_acento).strip()


def _normalizar_pix(pix: str | None) -> str | None:
    """E-mail e chave aleatória: minúsculas sem espaço. CPF, CNPJ e telefone: só os dígitos."""
    bruto = (pix or "").strip().lower()
    if bruto in ("", "-"):
        return None
    if re.search(r"[a-z]", bruto):
        return re.sub(r"\s+", "", bruto)
    return re.sub(r"\D", "", bruto) or None


def _limpar(texto: str | None) -> str:
    return " ".join((texto or "").split())[:200]


def _recencia(linha) -> tuple:
    return (linha["expense_date"], linha["id"])


def _agrupar(linhas: list) -> list[list]:
    """União de grupos: mesma chave PIX normalizada OU mesmo nome normalizado = mesmo fornecedor."""
    pai = list(range(len(linhas)))

    def raiz(i: int) -> int:
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i

    primeiro_por_chave: dict[tuple, int] = {}
    for i, linha in enumerate(linhas):
        chaves = [
            ("nome", _normalizar_nome(linha["supplier_name"])),
            ("pix", _normalizar_pix(linha["supplier_pix"])),
        ]
        for chave in (c for c in chaves if c[1]):
            j = primeiro_por_chave.setdefault(chave, i)
            pai[raiz(i)] = raiz(j)
    grupos: dict[int, list] = defaultdict(list)
    for i, linha in enumerate(linhas):
        grupos[raiz(i)].append(linha)
    return sorted(grupos.values(), key=lambda membros: min(m["id"] for m in membros))


def _mais_usado(valores_por_recencia: list[str]) -> str | None:
    """O valor mais frequente; no empate, o que aparece por último (o mais recente)."""
    if not valores_por_recencia:
        return None
    contagem = Counter(valores_por_recencia)
    ultima_posicao = {valor: posicao for posicao, valor in enumerate(valores_por_recencia)}
    return max(contagem, key=lambda valor: (contagem[valor], ultima_posicao[valor]))


def _nome_do_grupo(membros: list) -> str:
    por_recencia = sorted(membros, key=_recencia)
    for linha in reversed(por_recencia):
        arrumado = NOMES_ARRUMADOS.get(_normalizar_nome(linha["supplier_name"]))
        if arrumado:
            return arrumado
    return (
        _mais_usado(
            [_limpar(m["supplier_name"]) for m in por_recencia if _limpar(m["supplier_name"])]
        )
        or ""
    )


def _dados_do_grupo(membros: list) -> dict:
    por_recencia = sorted(membros, key=_recencia)
    com_pix = [
        _limpar(m["supplier_pix"])[:120] for m in por_recencia if _normalizar_pix(m["supplier_pix"])
    ]
    categorias = [m["category"] for m in por_recencia if m["category"] in CATEGORIAS_DO_FORNECEDOR]
    return {
        "nome": _nome_do_grupo(membros),
        "pix": com_pix[-1] if com_pix else None,
        "categoria": _mais_usado(categorias),
        "ids": [m["id"] for m in membros],
    }


def _nome_livre(nome: str, usados: set[str]) -> str:
    """Defensivo: nome arrumado que colida com o de outro grupo ganha " (2)", " (3)"…"""
    candidato, sufixo = nome, 2
    while _normalizar_nome(candidato) in usados:
        candidato, sufixo = f"{nome} ({sufixo})", sufixo + 1
    return candidato


def _importar_historico(conn) -> None:
    # A multa de cancelamento (306) é desembolso "fornecedor", mas paga o artista da escala: fica fora.
    linhas = (
        conn.execute(
            sa.text(
                "SELECT id, supplier_name, supplier_pix, category, expense_date FROM special_expenses "
                "WHERE disbursement_type = 'fornecedor' AND category <> 'Multa de cancelamento' ORDER BY id"
            )
        )
        .mappings()
        .all()
    )
    inserir = sa.text(
        "INSERT INTO fornecedores (nome, nome_normalizado, pix, categoria_padrao, ativo, created_at, updated_at) "
        "VALUES (:nome, :normalizado, :pix, :categoria, true, :agora, :agora) RETURNING id"
    )
    ligar = sa.text(
        "UPDATE special_expenses SET fornecedor_id = :fornecedor_id, supplier_name = :nome WHERE id IN :ids"
    ).bindparams(sa.bindparam("ids", expanding=True))
    agora, usados, ligados = datetime.utcnow(), set(), 0
    for membros in _agrupar(list(linhas)):
        dados = _dados_do_grupo(membros)
        if not _normalizar_nome(dados["nome"]):
            continue
        nome = _nome_livre(dados["nome"], usados)
        usados.add(_normalizar_nome(nome))
        fornecedor_id = conn.execute(
            inserir,
            {
                "nome": nome,
                "normalizado": _normalizar_nome(nome),
                "pix": dados["pix"],
                "categoria": dados["categoria"],
                "agora": agora,
            },
        ).scalar_one()
        conn.execute(ligar, {"fornecedor_id": fornecedor_id, "nome": nome, "ids": dados["ids"]})
        ligados += len(dados["ids"])
    logger.info(
        "352: %d fornecedores importados de %d gastos (%d ligados).",
        len(usados),
        len(linhas),
        ligados,
    )


def upgrade():
    op.create_table(
        "fornecedores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("nome_normalizado", sa.String(200), nullable=False),
        sa.Column("pix", sa.String(120), nullable=True),
        sa.Column("categoria_padrao", sa.String(30), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "criado_por_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name="fk_fornecedores_criado_por_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("nome_normalizado", name="uq_fornecedores_nome_normalizado"),
    )
    op.add_column("special_expenses", sa.Column("fornecedor_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_special_expenses_fornecedor_id",
        "special_expenses",
        "fornecedores",
        ["fornecedor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_special_expenses_fornecedor_id", "special_expenses", ["fornecedor_id"])
    _importar_historico(op.get_bind())


def downgrade():
    op.drop_index("ix_special_expenses_fornecedor_id", table_name="special_expenses")
    op.drop_constraint("fk_special_expenses_fornecedor_id", "special_expenses", type_="foreignkey")
    op.drop_column("special_expenses", "fornecedor_id")
    op.drop_table("fornecedores")
