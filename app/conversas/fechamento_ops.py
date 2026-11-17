"""Da conversa ao evento (feature 349, FR-017 e FR-018).

``o_que_levar`` diz o que a criação de evento recebe pronto da conversa: o último orçamento enviado nela, a ficha e
o vendedor — quem atende a conversa; sem responsável da equipe, quem mandou o último orçamento.

``ligar_evento_a_conversa`` é o **ponto único** em que o evento criado pela conversa se liga a ela. Hoje o vínculo
passa pela ficha (a ficha da conversa entre as clientes do evento — é por ela que o funil e a linha do tempo acham o
evento) e a perda da conversa é apagada, porque a venda fechou. A coluna ``calendar_events.conversa_id`` é da
feature 348: ela se grava aqui, sem a agenda precisar mudar de novo.

Puro: sem ``flask.request``. Não comita — quem chama (a criação de evento) comita.
"""

from __future__ import annotations

from typing import Any

from app import db
from app.constants import CLIENT_RELATION_TIPOS
from app.conversas import constantes as K
from app.conversas.acesso import e_da_equipe, responsavel_ativo
from app.conversas.recusa import campo
from app.models import CalendarEvent, Conversa, EventClient, OrcamentoEnvio

_CONTRATANTE = CLIENT_RELATION_TIPOS[0]
_OUTROS = CLIENT_RELATION_TIPOS[-1]


def _pessoa(user: Any) -> dict[str, Any] | None:
    return {"id": user.id, "nome": user.name} if user is not None else None


def o_que_levar(conversa: Conversa) -> dict[str, Any]:
    """O orçamento, a ficha e o vendedor para pré-preencher o evento (contrato ``Venda.fechamento``)."""
    envio = (
        OrcamentoEnvio.query.filter_by(conversa_id=conversa.id)
        .order_by(OrcamentoEnvio.created_at.desc(), OrcamentoEnvio.id.desc())
        .first()
    )
    if responsavel_ativo(conversa):
        vendedor = conversa.responsavel
    elif envio is not None and envio.autor is not None and e_da_equipe(envio.autor):
        vendedor = envio.autor
    else:
        vendedor = None
    cliente = conversa.cliente
    return {
        "orcamento_id": envio.orcamento_id if envio is not None else None,
        "cliente": {"id": cliente.id, "nome": cliente.name} if cliente is not None else None,
        "vendedor": _pessoa(vendedor),
    }


def conversa_para_evento(valor: Any) -> Conversa | None:
    """A conversa de origem do ``POST /api/events`` (``conversa_id`` opcional).

    Raises:
        Recusa: 422 em ``conversa_id`` — valor que não é inteiro ou conversa que não existe.
    """
    if valor is None:
        return None
    valido = isinstance(valor, int) and not isinstance(valor, bool)
    conversa = db.session.get(Conversa, valor) if valido else None
    if conversa is None:
        raise campo("conversa_id", K.TEXTO_CONVERSA_PARA_EVENTO)
    return conversa


def ligar_evento_a_conversa(evento: CalendarEvent, conversa: Conversa) -> None:
    """O ponto único evento↔conversa (FR-018). Não comita.

    A ficha da conversa entra entre as clientes do evento (Contratante se o evento ainda não tem nenhuma; senão
    "Outros", para não criar dois contratantes) e a perda da conversa some. A 348 grava ``evento.conversa_id`` aqui.
    """
    if conversa.client_id is not None:
        ja_tem = EventClient.query.filter_by(event_id=evento.id).all()
        if not any(ec.client_id == conversa.client_id for ec in ja_tem):
            relacao = _OUTROS if ja_tem else _CONTRATANTE
            db.session.add(
                EventClient(
                    event_id=evento.id, client_id=conversa.client_id, relationship_type=relacao
                )
            )
            if evento.client_id is None:
                evento.client_id = conversa.client_id
    conversa.perdida_em = None
    conversa.perdida_motivo = None
    conversa.perdida_nota = None
    conversa.perdida_por_id = None
