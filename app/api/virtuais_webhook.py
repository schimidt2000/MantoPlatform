"""Recepção do aviso de pagamento da InfinitePay (feature 205; resposta rápida na 310).

**A rota não decide nada.** Ela valida o segredo do endereço, grava o aviso e responde; quem decide
é o núcleo (``app/marketing/virtuais_ops.py``) — Princípio III.

Regras que parecem estranhas até você saber o porquê:

1. **Segredo inválido responde 404, não 403.** 403 confirmaria que o endereço existe (FR-027a).
2. **Todo o resto responde 200**, inclusive duplicata, pedido inexistente e conflito de horário.
   A InfinitePay reenvia com 400, e reenviar não conserta nenhum desses casos.
3. **Feature 310 — responder antes de processar.** A InfinitePay pede resposta em menos de 1 s;
   o processamento (reconsulta, decisão, Google, e-mail) leva segundos e seguraria a trava do
   horário durante HTTP. A rota grava o aviso como ``pendente``, dispara o processamento numa
   thread curta e responde. Se a thread morrer (deploy), a varredura reprocessa a linha.
4. **Feature 310 — o segredo nunca vai para o log**: a URL inteira não é registrada aqui, e o log
   de acesso do servidor passa pela máscara de ``api_utils.mascarar_url_webhook``.
"""

import logging
import threading
from typing import Any

from flask import current_app, jsonify, request

from app import limiter
from app.api import api_bp

logger = logging.getLogger(__name__)

#: Corpo máximo aceito. O aviso real tem centenas de bytes; 64 KB sobra, e impede que alguém
#: sem o segredo faça o servidor desserializar megabytes.
_CORPO_MAXIMO = 64 * 1024


def _processar_em_segundo_plano(app, registro_id: int) -> None:
    from app import db
    from app.marketing import virtuais_ops as ops

    with app.app_context():
        try:
            desfecho = ops.processar_aviso(registro_id)
            logger.info("[virtuais] aviso %s decidido: %s", registro_id, desfecho)
        except Exception:  # noqa: BLE001 — a varredura reprocessa; aqui só registra
            db.session.rollback()
            logger.exception("[virtuais] processamento do aviso %s falhou", registro_id)
        finally:
            db.session.remove()


@api_bp.route("/webhooks/infinitepay/<token>", methods=["POST"])
@limiter.limit("60 per minute")
def api_virtuais_webhook(token: str) -> Any:
    """Recebe o aviso de pagamento da InfinitePay (FR-027; 310 R2)."""
    from app.marketing import virtuais_ops as ops

    if (request.content_length or 0) > _CORPO_MAXIMO:
        return jsonify({"success": False, "message": "Payload too large"}), 413
    payload = request.get_json(silent=True) or {}

    if not ops.token_do_aviso_valido(token):
        try:
            ops.registrar_aviso_invalido(payload)
        except Exception as exc:  # noqa: BLE001 — registro é best-effort
            logger.warning("[virtuais] falha ao registrar aviso recusado: %s", exc)
        return jsonify({"success": False, "message": "Not found"}), 404

    try:
        registro_id = ops.registrar_aviso(payload)
    except Exception as exc:  # noqa: BLE001 — nunca devolver 500 à operadora
        logger.exception("[virtuais] erro ao registrar aviso: %s", exc)
        return jsonify({"success": True, "message": None}), 200

    if registro_id is not None:
        if current_app.config.get("VIRTUAIS_AVISO_SINCRONO"):
            # Costura de verificação: processa na própria requisição.
            ops.processar_aviso(registro_id)
        else:
            threading.Thread(
                target=_processar_em_segundo_plano,
                args=(current_app._get_current_object(), registro_id),
                daemon=True,
            ).start()

    return jsonify({"success": True, "message": None}), 200
