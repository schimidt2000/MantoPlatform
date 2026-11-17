"""Telefone do WhatsApp × ficha do cliente: o nono dígito brasileiro (feature 325, research R11).

A Meta manda o celular brasileiro de conta antiga SEM o nono dígito (12 dígitos), e a ficha guarda
o que ``normalize_phone`` gravou (em geral com o 9). A regra de "mesmo número com e sem o 9" já
existe numa fonte só, ``contratos_ops.chave_telefone`` (DDD + últimos 8 dígitos): daqui só saem as
formas completas que essa chave representa, para a busca usar o índice único de ``Client.phone``.
"""

from __future__ import annotations

import re

from app.contratos.contratos_ops import chave_telefone

DDI_BRASIL = "55"
# Celular brasileiro: o primeiro dos 8 dígitos finais é 6–9 (fixo começa com 2–5 e não ganha o 9).
PRIMEIROS_DE_CELULAR = set("6789")


def so_digitos(valor: str | None) -> str:
    """Só os dígitos de ``valor`` (vazio para ``None``)."""
    return re.sub(r"\D", "", valor or "")


def variantes_de_telefone(valor: str | None) -> list[str]:
    """As formas com DDI em que ``Client.phone`` pode ter gravado este número.

    ``5511970570577`` e ``551170570577`` → ``["5511970570577", "551170570577"]``. Número fora do
    Brasil (ou ilegível) volta só como veio, em dígitos.
    """
    digitos = so_digitos(valor)
    chave = chave_telefone(digitos)
    if not digitos or chave is None or not digitos.startswith(DDI_BRASIL):
        return [digitos] if digitos else []
    ddd, oito = chave[:2], chave[2:]
    formas = [f"{DDI_BRASIL}{ddd}9{oito}", f"{DDI_BRASIL}{ddd}{oito}"]
    if oito[0] not in PRIMEIROS_DE_CELULAR:
        formas = [f"{DDI_BRASIL}{ddd}{oito}"]
    return formas


def telefone_com_nono(valor: str | None) -> str | None:
    """A forma canônica guardada em ``Conversa.telefone``: com DDI e, se for celular, com o 9."""
    formas = variantes_de_telefone(valor)
    return formas[0] if formas else None
