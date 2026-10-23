"""Cliente da InfinitePay — criação de link de pagamento e reconsulta de cobrança (feature 205).

**Este é o único arquivo do sistema que sabe que centavos existem.** A InfinitePay trabalha com
inteiros em centavos; o resto da Plataforma opera em ``Decimal`` de reais (Princípio IX). A
conversão acontece aqui, nas duas direções, e não vaza para nenhuma outra camada.

A outra responsabilidade — igualmente crítica — é **distinguir "não pago" de "não sei"**:

* ``consultar_pagamento`` devolvendo ``paid=False`` é uma decisão de negócio: a cobrança existe e
  não foi paga.
* Uma indisponibilidade (timeout, 5xx, resposta ilegível) **não** é "não pago". Ela levanta
  ``InfinitePayIndisponivel``, e quem chama retém o pedido para nova tentativa (FR-027d).

Confundir os dois é o que faria uma queda da operadora liberar produto de graça ou cancelar uma
venda já paga. Por isso nenhuma exceção é engolida em silêncio aqui.

O módulo não importa Flask: é testável sem HTTP e sem contexto de aplicação (Princípio III).

Contrato da operadora (ver `specs/205-loja-interacoes-virtuais/research.md` R1):
    POST https://api.checkout.infinitepay.io/links
    POST https://api.checkout.infinitepay.io/payment_check
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.checkout.infinitepay.io"
LINKS_ENDPOINT = f"{API_BASE_URL}/links"
PAYMENT_CHECK_ENDPOINT = f"{API_BASE_URL}/payment_check"

# (conexão, leitura) em segundos. Estourou qualquer um dos dois, a chamada é INDISPONÍVEL —
# nunca "não pago" (decisão registrada em plan.md, "Timeout das chamadas à operadora").
TIMEOUT_SECONDS = (10, 30)

CENTS_PER_REAL = 100


class InfinitePayError(Exception):
    """Falha ao falar com a InfinitePay. Base das exceções deste módulo."""


class InfinitePayIndisponivel(InfinitePayError):
    """A operadora não respondeu a tempo, ou respondeu de forma inutilizável.

    Significa **"não sei"**, jamais "não pago". Quem chama deve reter o pedido para nova tentativa
    (FR-027d), nunca efetivar nem cancelar com base nisto.
    """


class InfinitePayRecusou(InfinitePayError):
    """A operadora respondeu, mas recusou a requisição (4xx com corpo compreensível).

    Feature 310: carrega o ``code`` da operadora (``body.error``, ex.:
    ``external_checkout_not_enabled``) e o status HTTP. Antes só a ``message`` sobrevivia, e o
    motivo real de toda reserva cair em 502 ficava num warning do log.
    """

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class InfinitePayTravada(InfinitePayIndisponivel):
    """Este processo está proibido de falar com a operadora (feature 310, constituição XIV).

    É subclasse de "não sei" de propósito: travado, nada é efetivado nem cancelado — o pedido só
    fica retido, como numa queda da operadora.
    """


#: Resultado da reconsulta (feature 310, research R4). ``nao_sei`` não é valor: é a exceção
#: ``InfinitePayIndisponivel``.
RESULTADO_PAGO = "pago"
RESULTADO_NAO_PAGO = "nao_pago"
#: `200 {"success": false}` ou 404 "Not found": a operadora não achou cobrança paga com esses dados.
#: Provado em produção (teste 0, 20/10/2026) para pedido não pago consultado só por handle+order_nsu.
RESULTADO_NAO_ENCONTRADO = "nao_encontrado"


def reais_para_centavos(valor: Decimal) -> int:
    """Converte reais em centavos inteiros, arredondando para o centavo mais próximo.

    Args:
        valor: Quantia em reais (``Decimal``). ``float`` é recusado de propósito — dinheiro em
            ponto flutuante é como o centavo some.

    Returns:
        A quantia em centavos.

    Raises:
        TypeError: ``valor`` não é ``Decimal`` nem ``int``.
    """
    if isinstance(valor, float):
        raise TypeError("Dinheiro nunca em float — use Decimal (Princípio IX).")
    if not isinstance(valor, (Decimal, int)):
        raise TypeError(f"Valor monetário inválido: {type(valor).__name__}")
    quantia = Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(quantia * CENTS_PER_REAL)


def centavos_para_reais(centavos: Any) -> Decimal:
    """Converte centavos inteiros vindos da operadora em reais (``Decimal``).

    Args:
        centavos: Inteiro (ou string numérica) como a InfinitePay devolve.

    Returns:
        A quantia em reais, com duas casas.

    Raises:
        InfinitePayIndisponivel: O valor veio ausente ou ilegível — resposta inutilizável não pode
            ser interpretada como zero.
    """
    if centavos is None:
        raise InfinitePayIndisponivel("Resposta da operadora sem valor.")
    try:
        return (Decimal(int(centavos)) / CENTS_PER_REAL).quantize(Decimal("0.01"))
    except (TypeError, ValueError) as exc:
        raise InfinitePayIndisponivel(f"Valor ilegível na resposta: {centavos!r}") from exc


def _post(url: str, payload: dict, *, travada: bool = True, api_key: str | None = None) -> dict:
    """Faz o POST e devolve o JSON, traduzindo toda falha de transporte em exceção deste módulo.

    ``travada`` vem da configuração do processo (``INFINITEPAY_SUPPRESS_CALLS``), lida pela camada
    ``_ops`` a cada chamada e passada aqui — este módulo não importa Flask (Princípio III). O
    default é travado: quem esquecer de passar não cobra ninguém por engano.
    """
    if travada:
        raise InfinitePayTravada("Pagamento travado neste ambiente (cópia de teste).")
    headers = {"X-Api-Key": api_key} if api_key else None
    try:
        response = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS, headers=headers)
    except requests.Timeout as exc:
        logger.warning("[infinitepay] timeout em %s: %s", url, exc)
        raise InfinitePayIndisponivel("A operadora não respondeu a tempo.") from exc
    except requests.RequestException as exc:
        logger.warning("[infinitepay] erro de rede em %s: %s", url, exc)
        raise InfinitePayIndisponivel("Falha de rede ao falar com a operadora.") from exc

    if response.status_code >= 500:
        logger.warning("[infinitepay] %s devolveu %s", url, response.status_code)
        raise InfinitePayIndisponivel(f"Operadora indisponível (HTTP {response.status_code}).")

    try:
        body = response.json()
    except ValueError as exc:
        logger.warning("[infinitepay] resposta não-JSON de %s", url)
        raise InfinitePayIndisponivel("Resposta ilegível da operadora.") from exc

    if response.status_code >= 400:
        message = body.get("message") if isinstance(body, dict) else None
        code = body.get("error") if isinstance(body, dict) else None
        raise InfinitePayRecusou(
            message or code or f"Operadora recusou (HTTP {response.status_code}).",
            code=code, status=response.status_code,
        )

    if not isinstance(body, dict):
        raise InfinitePayIndisponivel("Formato inesperado na resposta da operadora.")
    return body


def criar_link_pagamento(
    *,
    handle: str,
    order_nsu: str,
    total: Decimal,
    description: str,
    redirect_url: str,
    webhook_url: str,
    customer: dict | None = None,
    travada: bool = True,
    api_key: str | None = None,
    valid_until: str | None = None,
) -> dict:
    """Cria o link de pagamento de um pedido e devolve para onde mandar a família.

    Feature 310: com ``api_key`` (API nova da InfinitePay), o link leva ``options.valid_until`` (o
    fim da reserva, ISO com fuso) e ``single_payment`` — vence junto com a reserva e aceita um
    pagamento só. Sem chave, exatamente o pacote provado em produção no teste A.

    Args:
        handle: A "InfiniteTag" da conta (``SiteSetting.infinitepay_handle``).
        order_nsu: Nosso identificador do pedido — volta em todo aviso e em toda reconsulta.
        total: Valor total **em reais**; a conversão para centavos acontece aqui.
        description: Texto do item que a família vê no checkout.
        redirect_url: Para onde a operadora devolve a família (a página do pedido).
        webhook_url: Endereço secreto que recebe o aviso de pagamento.
        customer: ``{"email", "phone_number"}`` — nunca o nome da criança (feature 310, R-15).
        travada: Trava do processo (ver ``_post``).
        api_key: ``INFINITEPAY_API_KEY``, quando configurada.
        valid_until: Fim da reserva em ISO 8601 com fuso; só usado com ``api_key``.

    Returns:
        ``{"payment_url": str}``.

    Raises:
        InfinitePayIndisponivel: Operadora fora do ar ou resposta ilegível.
        InfinitePayRecusou: Operadora recusou a criação do link.
    """
    payload: dict[str, Any] = {
        "handle": handle,
        "order_nsu": order_nsu,
        "redirect_url": redirect_url,
        "webhook_url": webhook_url,
        "items": [
            {
                "quantity": 1,
                "price": reais_para_centavos(total),
                "description": description,
            }
        ],
    }
    if customer:
        payload["customer"] = customer
    if api_key:
        opcoes: dict[str, Any] = {"single_payment": True}
        if valid_until:
            opcoes["valid_until"] = valid_until
        payload["options"] = opcoes

    body = _post(LINKS_ENDPOINT, payload, travada=travada, api_key=api_key)
    url = body.get("url")
    if not url:
        raise InfinitePayIndisponivel("A operadora não devolveu o link de pagamento.")
    return {"payment_url": url}


def consultar_pagamento(
    *,
    handle: str,
    order_nsu: str,
    transaction_nsu: str | None = None,
    slug: str | None = None,
    travada: bool = True,
    api_key: str | None = None,
) -> dict:
    """Reconsulta uma cobrança na operadora. **É a fonte de verdade sobre pagamento.**

    Nenhuma venda é efetivada a partir do aviso recebido: o aviso é gatilho, esta consulta é a
    prova (FR-027b). O valor volta convertido em reais, pronto para comparar com o total congelado
    do pedido.

    Args:
        handle: A "InfiniteTag" da conta.
        order_nsu: Nosso identificador do pedido.
        transaction_nsu: Identificador da transação, quando conhecido.
        slug: Identificador da fatura (``invoice_slug``), quando conhecido.

    Returns:
        ``{"resultado": "pago" | "nao_pago" | "nao_encontrado", "paid": bool,
        "amount": Decimal | None, "paid_amount": Decimal | None, "capture_method": str | None,
        "raw": dict}``. ``nao_encontrado`` é a resposta ``{"success": false}`` (ou 404 "Not
        found") — sem os identificadores do aviso/retorno, a operadora não distingue "não pago" de
        "não achei" (teste 0 em produção, feature 310).

    Raises:
        InfinitePayIndisponivel: Operadora fora do ar, lenta ou com resposta ilegível — significa
            "não sei", e o pedido deve ser retido para nova tentativa, nunca efetivado nem
            cancelado.
        InfinitePayRecusou: A operadora recusou a consulta.
    """
    payload = {"handle": handle, "order_nsu": order_nsu}
    if transaction_nsu:
        payload["transaction_nsu"] = transaction_nsu
    if slug:
        payload["slug"] = slug

    try:
        body = _post(PAYMENT_CHECK_ENDPOINT, payload, travada=travada, api_key=api_key)
    except InfinitePayRecusou as exc:
        if exc.status == 404:
            return {"resultado": RESULTADO_NAO_ENCONTRADO, "paid": False, "amount": None,
                    "paid_amount": None, "capture_method": None, "raw": {"status": 404}}
        raise

    if body.get("success") is False and "paid" not in body:
        return {"resultado": RESULTADO_NAO_ENCONTRADO, "paid": False, "amount": None,
                "paid_amount": None, "capture_method": None, "raw": body}

    if "paid" not in body:
        # Sem o campo que decide tudo, a resposta não serve para liberar nem para negar produto.
        raise InfinitePayIndisponivel("Resposta da operadora sem o campo 'paid'.")

    paid = bool(body.get("paid"))
    return {
        "resultado": RESULTADO_PAGO if paid else RESULTADO_NAO_PAGO,
        "paid": paid,
        "amount": centavos_para_reais(body["amount"]) if body.get("amount") is not None else None,
        "paid_amount": (
            centavos_para_reais(body["paid_amount"])
            if body.get("paid_amount") is not None
            else None
        ),
        "capture_method": body.get("capture_method"),
        "raw": body,
    }
