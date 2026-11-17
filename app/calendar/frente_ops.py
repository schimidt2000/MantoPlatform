"""A frente de negócio do evento (feature 348): a única leitura, em Python e em SQL.

Até a 348 a frente da venda era adivinhada pelo título (dívida 215): social sem "15 anos" ou "casamento"
caía em festas. Agora ela é campo do evento (``calendar_events.frente``, FK ``marketing_frentes``),
escolhido na aba Comercial, e a regra de 16/11 (`docs/03` 345) vira **sugestão**:

- **certa**: ``(EDU`` no título ou tipo ``EDUCAMANTO`` → educamanto; tipo ``CORP`` → corporativo; "15 anos",
  "debut", "casamento", "noiv" ou "bodas" no título → social; tipo ``VM``/``VIRTUAL`` → loja;
- **por exclusão**: o resto → festas. Esta não é gravada sozinha: quem registra a venda escolhe.

Quem lê usa ``frente_do_evento`` (Python) ou ``frente_sql`` (SQL): a gravada, e na falta dela a sugestão. O
evento antigo sem frente continua com o número de 16/11 (SC-006). Consumidores: o painel da 345
(``comando_ops.frente_venda_sql``) e a venda atribuída da 351.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import case, func, or_

from app import db
from app.constants import MARKETING_FRENTES
from app.models import CalendarEvent

SOCIAL_REGEX = "(15 anos|debut|casamento|noiv|bodas)"
_SOCIAL = re.compile(SOCIAL_REGEX, re.IGNORECASE)
FRENTE_PADRAO = "festas"
TEXTO_FRENTE_INVALIDA = "Selecione uma frente da lista."
TEXTO_FRENTE_OBRIGATORIA = "Selecione a frente da venda."


class FrenteInvalida(ValueError):
    """A frente pedida não é uma das frentes."""


def opcoes() -> list[dict[str, str]]:
    """As frentes na ordem do painel (345), para o seletor da aba Comercial."""
    return [{"slug": slug, "rotulo": rotulo} for slug, rotulo in MARKETING_FRENTES.items()]


def sugestao(titulo: str | None, event_type: str | None) -> tuple[str, bool]:
    """A frente pela regra de 16/11 e se ela é certa (``False`` = caiu em festas por exclusão)."""
    titulo = titulo or ""
    tipo = event_type or ""
    if titulo.lower().startswith("(edu") or tipo == "EDUCAMANTO":
        return "educamanto", True
    if tipo == "CORP":
        return "corporativo", True
    if _SOCIAL.search(titulo):
        return "social", True
    if tipo in ("VM", "VIRTUAL"):
        return "loja", True
    return FRENTE_PADRAO, False


def _regra_sql() -> Any:
    """A regra de 16/11 em SQL — a mesma de ``sugestao`` (o verify compara as duas em todo evento)."""
    titulo = func.coalesce(CalendarEvent.title, "")
    tipo = func.coalesce(CalendarEvent.event_type, "")
    return case(
        (or_(titulo.ilike("(EDU%"), tipo == "EDUCAMANTO"), "educamanto"),
        (tipo == "CORP", "corporativo"),
        (titulo.op("~*")(SOCIAL_REGEX), "social"),
        (tipo.in_(("VM", "VIRTUAL")), "loja"),
        else_=FRENTE_PADRAO,
    )


def frente_sql() -> Any:
    """Expressão SQL da frente do evento: a gravada ou, na falta dela, a sugestão.

    Não resolve o satélite (lê as colunas da própria linha): filtre ``group_leader_id IS NULL``, como a
    venda da 345 já faz.
    """
    return func.coalesce(CalendarEvent.frente, _regra_sql())


def frente_do_evento(event: Any) -> dict[str, Any]:
    """A frente do evento para a tela e para a 351.

    Returns:
        ``frente`` (slug), ``rotulo``, ``definida`` (alguém escolheu), ``sugestao`` e ``sugestao_certa`` (a
        regra pelo título) e ``opcoes``. O satélite responde com o principal.
    """
    alvo = event
    if getattr(event, "group_leader_id", None):
        alvo = event.group_leader or db.session.get(CalendarEvent, event.group_leader_id) or event
    sugerida, certa = sugestao(alvo.title, alvo.event_type)
    frente = alvo.frente or sugerida
    return {
        "frente": frente,
        "rotulo": MARKETING_FRENTES.get(frente, frente),
        "definida": alvo.frente is not None,
        "sugestao": sugerida,
        "sugestao_certa": certa,
        "opcoes": opcoes(),
    }


def validar(valor: Any) -> str | None:
    """A frente do corpo: um slug das frentes, ou ``None`` (vazio).

    Raises:
        FrenteInvalida: texto fora da lista, ou valor que não é texto.
    """
    if valor is None or valor == "":
        return None
    if not isinstance(valor, str) or valor not in MARKETING_FRENTES:
        raise FrenteInvalida(TEXTO_FRENTE_INVALIDA)
    return valor


def falta_na_venda(frente: str | None, venda: Any, cortesia: bool) -> bool:
    """Venda de verdade (valor > 0, sem cortesia) sem frente nenhuma? Então a aba Comercial recusa."""
    if frente or cortesia:
        return False
    try:
        return Decimal(str(venda)) > 0
    except (InvalidOperation, ValueError):
        return False


def gravar_na_criacao(event: Any, frente: str | None) -> None:
    """Na criação do evento: a frente escolhida; sem ela, só a sugestão certa (FR-021). Não comita.

    A sugestão por exclusão ("festas") fica sem gravar: é ela que punha o social sem a palavra certa em
    festas. A aba Comercial pede a escolha.
    """
    if frente:
        event.frente = frente
        return
    sugerida, certa = sugestao(event.title, event.event_type)
    if certa:
        event.frente = sugerida
