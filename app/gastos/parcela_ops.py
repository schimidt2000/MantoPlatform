"""Parcelas do pagamento de um gasto extra (feature 353).

Núcleo puro (sem `flask.request`). Regras:

- parcelado = 2 a 24 parcelas, cada uma com data e valor > 0; o `amount` do gasto é a soma;
- a "Data do gasto" segue a competência (DRE, custo do evento); a parcela só diz quando o pagamento
  sai na Planilha de Pagamentos, onde vira um item próprio (`TIPO_ITEM_PLANILHA`);
- parcela paga ou "no banco" não muda nem sai pela edição do gasto (desmarca-se na Planilha);
- o `payment_status` do gasto parcelado é derivado das parcelas (`situacao_derivada`), para quem já
  lê o campo (situação em Gastos Extras, auditor, relatórios) continuar certo;
- não parcelam: gasto sem desembolso, devolução e multa de cancelamento (o `cancel_ops` reescreve o
  valor delas), "já pago no cadastro" e o reembolso do auditor de marketing (ele reescreve o valor
  do pendente) — com eles a soma deixaria de bater.

`gastos_ops` importa este módulo (criar e editar); a Planilha (`financeiro_read`/`_write`,
`atrasados_ops`) usa a leitura e a marcação.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from sqlalchemy.orm import Query

from app import db
from app.models import GastoParcela, MarketingAdSpendBatch, SpecialExpense

MIN_PARCELAS = 2
MAX_PARCELAS = 24
STATUS_TRAVADOS = ("no_banco", "pago")
DESEMBOLSOS_PARCELAVEIS = ("reembolso", "fornecedor")
CATEGORIAS_SEM_PARCELA = (
    SpecialExpense.CATEGORY_DEVOLUCAO,
    SpecialExpense.CATEGORY_MULTA_CANCELAMENTO,
)
#: O tipo do item da parcela na Planilha de Pagamentos. O set-status precisa de ramo próprio para
#: ele ANTES do `else`, que cai no cachê (`EventRole`) de mesmo id.
TIPO_ITEM_PLANILHA = "expense_parcela"

MSG_INVALIDAS = "Não foi possível ler as parcelas. Tente novamente."
MSG_MINIMO = "Parcelado precisa de pelo menos duas parcelas."
MSG_MAXIMO = "Até 24 parcelas."
MSG_NAO_PARCELA = "Este gasto não pode ser parcelado."
MSG_DATA = "Informe a data da parcela."
MSG_VALOR = "Informe o valor da parcela."
MSG_PAGA = "Parcela paga não muda: desmarque o pagamento na Planilha de Pagamentos primeiro."
MSG_SOMA = "Gasto parcelado: o valor é a soma das parcelas."

CENTAVO = Decimal("0.01")


class ParcelaValidationError(Exception):
    """Parcela inválida; `field` é a chave de `fields` (`parcelas` ou `parcelas.N.data|valor`)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass(frozen=True)
class ItemParcela:
    """Uma parcela como veio da tela: `id` só quando já existe."""

    id: int | None
    data: date
    valor: Decimal


# ══════════════════════════════════════════════════════════════════
#  Ler e validar o que veio da tela
# ══════════════════════════════════════════════════════════════════


def ler_itens(bruto: object) -> list | None:
    """`None` quando o campo não veio; a lista (talvez vazia) quando veio. Aceita texto JSON (multipart)."""
    if bruto is None:
        return None
    if isinstance(bruto, str):
        if not bruto.strip():
            return None
        try:
            bruto = json.loads(bruto)
        except ValueError:
            raise ParcelaValidationError("parcelas", MSG_INVALIDAS) from None
    if not isinstance(bruto, list):
        raise ParcelaValidationError("parcelas", MSG_INVALIDAS)
    return bruto


def _data(valor: object) -> date | None:
    try:
        return date.fromisoformat(str(valor)[:10]) if valor else None
    except ValueError:
        return None


def _valor(valor: object) -> Decimal | None:
    try:
        numero = Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None
    return numero if numero > 0 else None


def _id(valor: object) -> int | None:
    try:
        return int(valor) if valor not in (None, "") else None
    except (TypeError, ValueError):
        return None


def validar_itens(itens: list) -> list[ItemParcela]:
    """Confere quantidade, data e valor de cada parcela; o erro aponta o índice dela."""
    if len(itens) < MIN_PARCELAS:
        raise ParcelaValidationError("parcelas", MSG_MINIMO)
    if len(itens) > MAX_PARCELAS:
        raise ParcelaValidationError("parcelas", MSG_MAXIMO)
    validados: list[ItemParcela] = []
    for indice, item in enumerate(itens):
        item = item if isinstance(item, dict) else {}
        data = _data(item.get("data"))
        if data is None:
            raise ParcelaValidationError(f"parcelas.{indice}.data", MSG_DATA)
        valor = _valor(item.get("valor"))
        if valor is None:
            raise ParcelaValidationError(f"parcelas.{indice}.valor", MSG_VALOR)
        validados.append(ItemParcela(_id(item.get("id")), data, valor))
    return validados


def soma(itens: list[ItemParcela] | list[GastoParcela]) -> Decimal:
    """O valor do gasto parcelado."""
    return sum((Decimal(item.valor) for item in itens), Decimal("0")).quantize(CENTAVO)


def exigir_parcelavel(
    disbursement_type: str | None, categoria: str, paid_at_creation: bool, gasto_id: int | None
) -> None:
    """Recusa parcelar o que não tem pagamento a fazer ou cujo valor outro módulo reescreve."""
    recusa = (
        disbursement_type not in DESEMBOLSOS_PARCELAVEIS
        or categoria in CATEGORIAS_SEM_PARCELA
        or paid_at_creation
        or (
            gasto_id is not None
            and MarketingAdSpendBatch.query.filter_by(special_expense_id=gasto_id).first()
        )
    )
    if recusa:
        raise ParcelaValidationError("parcelas", MSG_NAO_PARCELA)


# ══════════════════════════════════════════════════════════════════
#  Gravar
# ══════════════════════════════════════════════════════════════════


def situacao_derivada(parcelas: list[GastoParcela]) -> str:
    """`pago` se todas pagas; `no_banco` se nenhuma falta e alguma está no banco; senão `nao_pago`."""
    situacoes = [p.payment_status for p in parcelas]
    if situacoes and all(s == "pago" for s in situacoes):
        return "pago"
    if situacoes and "nao_pago" not in situacoes:
        return "no_banco"
    return "nao_pago"


def _exigir_travadas_intactas(
    existentes: dict[int, GastoParcela], itens: list[ItemParcela]
) -> None:
    por_id = {item.id: (indice, item) for indice, item in enumerate(itens) if item.id is not None}
    for parcela in existentes.values():
        if parcela.payment_status not in STATUS_TRAVADOS:
            continue
        achado = por_id.get(parcela.id)
        if achado is None:
            raise ParcelaValidationError("parcelas", MSG_PAGA)
        indice, item = achado
        if item.data != parcela.data:
            raise ParcelaValidationError(f"parcelas.{indice}.data", MSG_PAGA)
        if item.valor != Decimal(parcela.valor):
            raise ParcelaValidationError(f"parcelas.{indice}.valor", MSG_PAGA)


def _casar(
    existentes: dict[int, GastoParcela], itens: list[ItemParcela]
) -> list[tuple[ItemParcela, GastoParcela]]:
    """Cada item com a parcela que ele atualiza (mesmo id) ou uma nova, a pagar."""
    usados: set[int] = set()
    pares = []
    for item in itens:
        parcela = existentes.get(item.id) if item.id not in usados else None
        if parcela is None:
            parcela = GastoParcela(data=item.data, valor=item.valor, payment_status="nao_pago")
        else:
            usados.add(parcela.id)
            if parcela.payment_status not in STATUS_TRAVADOS:
                parcela.data, parcela.valor = item.data, item.valor
        pares.append((item, parcela))
    return pares


def gravar_parcelas(expense: SpecialExpense, itens: list[ItemParcela]) -> None:
    """Faz das parcelas do gasto exatamente `itens` (já validados), sem tocar na paga.

    As não pagas que não vieram saem; as que vieram com `id` mudam no lugar; as sem `id` nascem a
    pagar. Renumera por data em duas passadas (números provisórios negativos e flush): trocar 1↔2
    de uma vez esbarraria no `UNIQUE(special_expense_id, numero)`, que o Postgres confere linha a
    linha. Não faz commit.
    """
    existentes = {p.id: p for p in expense.parcelas}
    _exigir_travadas_intactas(existentes, itens)
    pares = _casar(existentes, itens)
    # Por data; na mesma data, na ordem em que vieram.
    ordem = sorted(range(len(pares)), key=lambda indice: (pares[indice][0].data, indice))
    ordenadas = [pares[indice][1] for indice in ordem]
    for provisorio, parcela in enumerate(ordenadas, start=1):
        parcela.numero = -provisorio
    expense.parcelas = ordenadas
    db.session.flush()
    for numero, parcela in enumerate(ordenadas, start=1):
        parcela.numero = numero
    expense.amount = soma(ordenadas)
    expense.payment_status = situacao_derivada(ordenadas)


def desligar_parcelas(expense: SpecialExpense) -> None:
    """Volta o gasto a um pagamento só — recusado se alguma parcela já saiu."""
    if any(p.payment_status in STATUS_TRAVADOS for p in expense.parcelas):
        raise ParcelaValidationError("parcelas", MSG_PAGA)
    expense.parcelas = []
    expense.payment_status = "nao_pago"


# ══════════════════════════════════════════════════════════════════
#  Planilha de Pagamentos
# ══════════════════════════════════════════════════════════════════


def parcelas_da_planilha_entre(desde: date, ate: date) -> Query:
    """Parcelas com data em [desde, ate) de gasto aprovado, com desembolso e não pago no cadastro —
    o mesmo corte de `_pagamentos_gastos_entre` (`app/financeiro/routes.py`), pela data da parcela."""
    return (
        GastoParcela.query.join(
            SpecialExpense, GastoParcela.special_expense_id == SpecialExpense.id
        )
        .filter(
            SpecialExpense.status == "aprovado",
            SpecialExpense.disbursement_type.isnot(None),
            SpecialExpense.paid_at_creation.is_(False),
            GastoParcela.data >= desde,
            GastoParcela.data < ate,
        )
        .order_by(GastoParcela.data.asc(), GastoParcela.id.asc())
    )


def itens_da_planilha(parcelas: list[GastoParcela], hoje: date) -> list[dict]:
    """Um item por parcela, no formato de `_build_payment_items` (o serializador da API é o mesmo)."""
    itens = []
    for parcela in parcelas:
        gasto = parcela.gasto
        total = len(gasto.parcelas)
        descricao = gasto.description or "Gasto"
        itens.append(
            {
                "type": TIPO_ITEM_PLANILHA,
                "id": parcela.id,
                "date": parcela.data,
                "event_title": f"Gasto: {gasto.category}",
                "event_id": None,
                "copy_label": f"{parcela.data.strftime('%d/%m/%Y')} - {descricao} (parcela {parcela.numero} de {total})",
                "sublabel": f"{descricao} · Parcela {parcela.numero} de {total}",
                "person_name": gasto.payee_name,
                "amount": parcela.valor,
                "pix_key": gasto.payee_pix,
                "pix_key_type": "",
                "status": parcela.payment_status or "nao_pago",
                "is_future": parcela.data > hoje,
            }
        )
    return itens


def marcar_situacao(parcela: GastoParcela, status: str) -> str:
    """Marca a parcela na Planilha e rederiva a situação do gasto. Devolve a situação anterior.

    Não faz commit nem auditoria (a view registra quem marcou).
    """
    anterior = parcela.payment_status
    parcela.payment_status = status
    parcela.updated_at = datetime.utcnow()
    gasto = parcela.gasto
    gasto.payment_status = situacao_derivada(gasto.parcelas)
    return anterior
