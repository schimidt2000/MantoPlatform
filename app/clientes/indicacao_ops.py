"""Quem indicou a cliente e por qual parceiro ela chegou (feature 350).

Núcleo puro, sem commit. Erros de validação reusam `client_ops.ClientValidationError` (campo +
mensagem), o mesmo contrato que a ficha já devolve no 400.
"""

from __future__ import annotations

from typing import Any

from app import db
from app.clientes.client_ops import ClientValidationError
from app.constants import PARCEIRO_TIPOS
from app.models import Client, Parceiro


def _id_ou_nulo(valor: Any, campo: str) -> int | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool) or not str(valor).isdigit():
        raise ClientValidationError(campo, "Selecione uma opção da lista.")
    return int(valor)


def _definir_indicado_por(client: Client, valor: Any) -> None:
    indicado_por_id = _id_ou_nulo(valor, "indicado_por_id")
    if indicado_por_id is None:
        client.indicado_por_id = None
        return
    if indicado_por_id == client.id:
        raise ClientValidationError("indicado_por_id", "A cliente não pode indicar a si mesma.")
    if db.session.get(Client, indicado_por_id) is None:
        raise ClientValidationError("indicado_por_id", "Cliente não encontrada.")
    client.indicado_por_id = indicado_por_id


def _definir_parceiro(client: Client, valor: Any) -> None:
    parceiro_id = _id_ou_nulo(valor, "parceiro_id")
    if parceiro_id is None:
        client.parceiro_id = None
        return
    parceiro = db.session.get(Parceiro, parceiro_id)
    if parceiro is None:
        raise ClientValidationError("parceiro_id", "Parceiro não encontrado.")
    # O inativo não entra em ficha nova; a ficha que já estava ligada a ele continua.
    if not parceiro.ativo and client.parceiro_id != parceiro_id:
        raise ClientValidationError("parceiro_id", "Este parceiro está inativo.")
    client.parceiro_id = parceiro_id


def definir(client: Client, dados: dict[str, Any]) -> None:
    """Muda só as chaves presentes no corpo (``indicado_por_id`` e/ou ``parceiro_id``)."""
    if "indicado_por_id" in dados:
        _definir_indicado_por(client, dados.get("indicado_por_id"))
    if "parceiro_id" in dados:
        _definir_parceiro(client, dados.get("parceiro_id"))


def _resumo_do_parceiro(parceiro: Parceiro | None) -> dict[str, Any] | None:
    if parceiro is None:
        return None
    return {
        "id": parceiro.id,
        "nome": parceiro.nome,
        "tipo": parceiro.tipo,
        "tipo_label": PARCEIRO_TIPOS.get(parceiro.tipo, parceiro.tipo),
        "ativo": bool(parceiro.ativo),
    }


def serializar(client: Client) -> dict[str, Any]:
    """``indicado_por``, ``indicacoes`` (quem ela indicou) e ``parceiro`` para a ficha."""
    indicadas = Client.query.filter(Client.indicado_por_id == client.id).order_by(Client.name).all()
    origem = client.indicado_por
    return {
        "indicado_por": {"id": origem.id, "name": origem.name} if origem else None,
        "indicacoes": [{"id": c.id, "name": c.name} for c in indicadas],
        "parceiro": _resumo_do_parceiro(client.parceiro),
    }
