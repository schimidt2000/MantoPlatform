"""Recepção do aviso de pagamento da InfinitePay (feature 205).

**A rota não decide nada.** Ela valida o segredo do endereço, desserializa e delega ao núcleo
(``app/marketing/virtuais_ops.py``) — Princípio III e diretriz arquitetural da feature.

Duas regras que parecem estranhas até você saber o porquê:

1. **Segredo inválido responde 404, não 403.** 403 confirmaria que o endereço existe; 404 não
   entrega nada a quem está sondando (FR-027a).
2. **Todo o resto responde 200**, inclusive duplicata, pedido inexistente e conflito de horário.
   A InfinitePay reenvia o aviso quando recebe 400 — e reenviar não conserta nenhum desses casos,
   só cria loop. O que precisa de atenção humana é sinalizado pelo registro em
   ``VirtualPaymentNotification``, não pelo status HTTP.

O processamento propriamente dito (reconsulta na operadora, efetivação, devolução) entra na US3.
"""

import logging
from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.models import SiteSetting

logger = logging.getLogger(__name__)


def _token_valido(token: str) -> bool:
    """True se o token do path bate com o segredo configurado.

    Sem segredo configurado, nenhum token é aceito — um endereço de webhook aberto seria um botão
    público de "libere produto de graça".
    """
    settings = SiteSetting.query.get(1)
    esperado = (settings.infinitepay_webhook_token or "") if settings else ""
    if not esperado:
        return False
    return token == esperado


@api_bp.route("/webhooks/infinitepay/<token>", methods=["POST"])
def api_virtuais_webhook(token: str) -> Any:
    """Recebe o aviso de pagamento da InfinitePay.

    O corpo do aviso identifica o pedido, mas **não** autoriza nada: a liberação depende da
    reconsulta da cobrança na operadora (FR-027a/FR-027b).
    """
    from app.marketing.virtuais_ops import processar_notificacao_pagamento

    payload = request.get_json(silent=True) or {}

    if not _token_valido(token):
        # A tentativa é registrada (com `secret_ok=False`) para a equipe perceber sondagem, e a
        # resposta é 404 — 403 confirmaria que o endereço existe.
        try:
            processar_notificacao_pagamento(payload, secret_ok=False)
        except Exception as exc:  # noqa: BLE001 — registro é best-effort
            logger.warning("[virtuais] falha ao registrar webhook recusado: %s", exc)
        return jsonify({"success": False, "message": "Not found"}), 404

    try:
        resultado = processar_notificacao_pagamento(payload, secret_ok=True)
        logger.info("[virtuais] webhook processado: %s", resultado)
    except Exception as exc:  # noqa: BLE001 — nunca devolver 400/500 à operadora
        # Responder erro faria a InfinitePay reenviar em loop, e reenviar não conserta um bug
        # nosso. O aviso fica registrado; a falha vai para o log e para a equipe.
        logger.exception("[virtuais] erro inesperado ao processar webhook: %s", exc)

    return jsonify({"success": True, "message": None}), 200
