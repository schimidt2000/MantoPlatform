"""De qual conversa e de qual contato veio cada venda (feature 348).

A conversa é uma por telefone (``uq_conversas_canal_contato``). Por isso a venda (orçamento e evento) guarda
duas coisas, congeladas no momento em que é ligada à conversa:

- ``conversa_id``: a conversa;
- ``origem_contato_id``: o contato de origem daquele momento — o contato por anúncio, publicação ou site mais
  recente da conversa nos 90 dias anteriores (research R7). Sem contato na janela, a venda é orgânica.

Congelar é o que impede a segunda festa da cliente recorrente de herdar o anúncio da primeira. E a venda
**nunca** liga à conversa pela ficha (FR-015): só pelo orçamento enviado pela conversa (333) ou pela criação
do evento com a conversa (contrato da 349).

Quem lê: a aba Comercial (``origem_da_venda``) e a venda atribuída da 351 (as colunas). Nada aqui comita.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import update

from app import db
from app.conversas import constantes as K
from app.conversas.acesso import pode_conversas
from app.conversas.leitura_ops import nome_da_conversa
from app.conversas.relogio import agora_utc
from app.models import AnuncioMeta, Conversa, ConversaAnuncio, OrcamentoHistory, OrigemCodigo

TEXTO_CONVERSA_NAO_ENCONTRADA = "Conversa não encontrada."


class ConversaNaoEncontrada(ValueError):
    """A conversa informada para a venda não existe."""


def conversa_ou_erro(conversa_id: Any) -> Conversa:
    """A conversa pelo id inteiro.

    Raises:
        ConversaNaoEncontrada: id que não é inteiro ou conversa inexistente.
    """
    valido = isinstance(conversa_id, int) and not isinstance(conversa_id, bool)
    conversa = db.session.get(Conversa, conversa_id) if valido else None
    if conversa is None:
        raise ConversaNaoEncontrada(TEXTO_CONVERSA_NAO_ENCONTRADA)
    return conversa


def contato_de_origem(conversa_id: int, momento: datetime | None = None) -> ConversaAnuncio | None:
    """O contato que dá origem a uma venda ligada em ``momento`` (UTC; padrão: agora).

    O mais recente da conversa entre ``momento - 90 dias`` e ``momento``, dos tipos anúncio, publicação e
    site; empate pelo maior id. ``None`` = venda orgânica.
    """
    referencia = momento or agora_utc()
    return (
        ConversaAnuncio.query.filter(
            ConversaAnuncio.conversa_id == conversa_id,
            ConversaAnuncio.tipo.in_(K.CONTATOS_DE_ORIGEM),
            ConversaAnuncio.momento <= referencia,
            ConversaAnuncio.momento >= referencia - K.JANELA_DA_ORIGEM,
        )
        .order_by(ConversaAnuncio.momento.desc(), ConversaAnuncio.id.desc())
        .first()
    )


def ligar_orcamento(entry: OrcamentoHistory, conversa: Conversa) -> bool:
    """A conversa e o contato de origem no orçamento ainda sem conversa (FR-011). Não comita.

    UPDATE condicional: o primeiro envio vence, e dois primeiros envios ao mesmo tempo não se sobrescrevem
    (mesma regra da ficha do orçamento, 333). Devolve se ligou.
    """
    contato = contato_de_origem(conversa.id)
    resultado = db.session.execute(
        update(OrcamentoHistory)
        .where(OrcamentoHistory.id == entry.id, OrcamentoHistory.conversa_id.is_(None))
        .values(conversa_id=conversa.id, origem_contato_id=contato.id if contato else None)
        .execution_options(synchronize_session="fetch")
    )
    return bool(resultado.rowcount)


def ligar_evento(event: Any, conversa_id: Any) -> None:
    """O evento nasce (ou passa a ser) da conversa: grava a conversa e congela o contato. Não comita.

    É o ponto de entrada da 349 ("Criar evento" na conversa) e da criação com ``conversa_id``.

    Raises:
        ConversaNaoEncontrada: a conversa não existe.
    """
    conversa = conversa_ou_erro(conversa_id)
    contato = contato_de_origem(conversa.id)
    event.conversa_id = conversa.id
    event.origem_contato_id = contato.id if contato else None


def acompanhar_orcamento(
    event: Any, antigo: OrcamentoHistory | None, novo: OrcamentoHistory | None
) -> None:
    """O evento acompanha a conversa do orçamento ligado, trocado ou desligado (FR-013). Não comita.

    Vale quando o evento não tem conversa, ou quando a conversa e o contato dele são exatamente os do
    orçamento antigo (vieram dele). A ligação feita por outro caminho (a criação pela conversa) fica.
    """
    veio_do_antigo = antigo is not None and (event.conversa_id, event.origem_contato_id) == (
        antigo.conversa_id,
        antigo.origem_contato_id,
    )
    if event.conversa_id is None or veio_do_antigo:
        event.conversa_id = novo.conversa_id if novo is not None else None
        event.origem_contato_id = novo.origem_contato_id if novo is not None else None


def ao_criar_evento(event: Any, conversa_id: Any = None) -> None:
    """Na criação: a conversa informada (349) vence; sem ela, herda do orçamento. Não comita.

    Raises:
        ConversaNaoEncontrada: ``conversa_id`` informado e inexistente (a API recusa antes do Google).
    """
    if conversa_id is not None:
        ligar_evento(event, conversa_id)
        return
    if event.orcamento_history_id:
        acompanhar_orcamento(
            event, None, db.session.get(OrcamentoHistory, event.orcamento_history_id)
        )


# ── Leitura ──────────────────────────────────────────────────────────────────────────────────────


def _iso(momento: datetime | None) -> str | None:
    return momento.replace(tzinfo=UTC).isoformat() if momento is not None else None


def _contato(contato: ConversaAnuncio | None) -> dict[str, Any] | None:
    if contato is None:
        return None
    anuncio = db.session.get(AnuncioMeta, contato.anuncio_id) if contato.anuncio_id else None
    codigo = db.session.get(OrigemCodigo, contato.codigo_id) if contato.codigo_id else None
    return {
        "tipo": contato.tipo,
        "titulo": contato.titulo,
        "anuncio_id": contato.anuncio_id,
        "campanha": (anuncio.campanha_nome if anuncio else None)
        or (codigo.utm_campaign if codigo else None),
        "campanha_id": (anuncio.campanha_id if anuncio else None)
        or (codigo.campanha_id if codigo else None),
        "conjunto": anuncio.conjunto_nome if anuncio else None,
        "codigo": codigo.codigo if codigo else None,
        "quando": _iso(contato.momento),
    }


def origem_da_venda(event: Any, user: Any = None) -> dict[str, Any] | None:
    """A conversa e o contato de origem da venda, para a aba Comercial e a 351 (FR-016).

    O satélite responde com o principal (a venda mora nele). ``None`` = venda sem conversa. ``pode_abrir``
    diz se ``user`` usa as Conversas (o Financeiro vê o bloco comercial, mas não as conversas).
    """
    alvo = event.group_leader if getattr(event, "group_leader_id", None) else event
    if alvo is None or alvo.conversa_id is None:
        return None
    conversa = db.session.get(Conversa, alvo.conversa_id)
    if conversa is None:
        return None
    contato = (
        db.session.get(ConversaAnuncio, alvo.origem_contato_id) if alvo.origem_contato_id else None
    )
    return {
        "conversa_id": conversa.id,
        "conversa_nome": nome_da_conversa(conversa),
        "canal": conversa.canal,
        "pode_abrir": bool(user is not None and pode_conversas(user)),
        "contato": _contato(contato),
    }
