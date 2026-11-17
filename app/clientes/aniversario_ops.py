"""Aniversários dos próximos dias, só de quem autorizou (feature 350).

Só leitura: nada aqui envia mensagem (o lembrete automático é outra feature). Entra na lista a
criança com aceite de aniversário (a linha só existe com ele) **e** cuja responsável tem aceite de
novidades — sem os dois, a equipe não pode usar o dado para contato.
"""

from __future__ import annotations

from calendar import isleap
from datetime import date
from typing import Any

from app.models import Client, ClienteCrianca

FEVEREIRO = 2
DIA_BISSEXTO = 29


def _no_ano(nascimento: date, ano: int) -> date:
    """O aniversário no ano pedido; 29/02 em ano comum cai em 28/02."""
    if (nascimento.month, nascimento.day) == (FEVEREIRO, DIA_BISSEXTO) and not isleap(ano):
        return date(ano, FEVEREIRO, DIA_BISSEXTO - 1)
    return nascimento.replace(year=ano)


def proximo_aniversario(nascimento: date, hoje: date) -> date:
    """O próximo aniversário a partir de hoje (hoje conta)."""
    neste_ano = _no_ano(nascimento, hoje.year)
    return neste_ano if neste_ano >= hoje else _no_ano(nascimento, hoje.year + 1)


def listar(hoje: date, dias: int) -> list[dict[str, Any]]:
    """As crianças com aniversário de hoje até ``hoje + dias``, em ordem de data."""
    linhas = (
        ClienteCrianca.query.join(Client, Client.id == ClienteCrianca.client_id)
        .filter(Client.marketing_opt_in_at.isnot(None))
        .all()
    )
    itens = []
    for crianca in linhas:
        data = proximo_aniversario(crianca.nascimento, hoje)
        faltam = (data - hoje).days
        if faltam <= dias:
            itens.append(_item(crianca, data, faltam))
    return sorted(itens, key=lambda item: (item["data"], item["primeiro_nome"]))


def _item(crianca: ClienteCrianca, data: date, faltam: int) -> dict[str, Any]:
    cliente = crianca.cliente
    return {
        "crianca_id": crianca.id,
        "primeiro_nome": crianca.primeiro_nome,
        "data": data.isoformat(),
        "dias": faltam,
        "idade": data.year - crianca.nascimento.year,
        "cliente": {
            "id": cliente.id,
            "name": cliente.name,
            "phone_display": cliente.phone_display or cliente.phone,
        },
    }
