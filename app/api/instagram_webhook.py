"""Webhook do Instagram Direct (mensageria do Instagram pela Página) — feature 330, Conversas.

RBAC: público, sem sessão. O app da Meta é o MESMO do WhatsApp: o GET (desafio) exige o
``WHATSAPP_VERIFY_TOKEN``, e o POST exige ``X-Hub-Signature-256`` = HMAC-SHA256 do corpo BRUTO com o
``WHATSAPP_APP_SECRET`` (a mesma ``assinatura_valida``). Canal desligado, token ou assinatura
inválidos → **404** sem efeito.

O corpo válido entra na MESMA fila do WhatsApp (``whatsapp_avisos``) e no mesmo processamento: o
``aviso_ops.processar_aviso`` despacha pelo ``object`` (``instagram``) e a varredura refaz o que
falhou. A resposta é 200 mesmo que o processamento falhe. A URL é contrato gravado na Meta.
"""

from __future__ import annotations

import hmac
import threading
from typing import Any

from flask import Response, current_app, jsonify, request

from app import limiter
from app.api import api_bp
from app.api.whatsapp_webhook import (
    _nao_encontrado,
    _processar_em_segundo_plano,
    assinatura_valida,
)
from app.conversas import aviso_ops
from app.conversas.configuracao import cfg_instagram, cfg_whatsapp
from app.conversas.constantes import AVISO_CORPO_MAXIMO


@api_bp.route("/webhooks/instagram", methods=["GET"])
@limiter.limit("60 per minute")
def api_webhook_instagram_verificar() -> Any:
    """Desafio de verificação da Meta: devolve o ``hub.challenge`` se o token conferir."""
    cfg = cfg_instagram()
    token = request.args.get("hub.verify_token") or ""
    if (
        not cfg.ligado
        or request.args.get("hub.mode") != "subscribe"
        or not hmac.compare_digest(token, cfg.verify_token)
    ):
        return _nao_encontrado()
    return Response(request.args.get("hub.challenge") or "", status=200, mimetype="text/plain")


@api_bp.route("/webhooks/instagram", methods=["POST"])
@limiter.limit("300 per minute")
def api_webhook_instagram() -> Any:
    """Recebe o aviso, confere a assinatura, grava cru e responde 200 (processa fora)."""
    cfg = cfg_instagram()
    if not cfg.ligado:
        return _nao_encontrado()
    grande = (request.content_length or 0) > AVISO_CORPO_MAXIMO
    corpo = b"" if grande else request.stream.read(AVISO_CORPO_MAXIMO + 1)
    if grande or len(corpo) > AVISO_CORPO_MAXIMO:
        current_app.logger.warning(
            "[instagram] aviso acima de %s bytes recusado", AVISO_CORPO_MAXIMO
        )
        return jsonify({"error": {"message": "Corpo grande demais"}}), 413
    if not assinatura_valida(corpo, request.headers.get("X-Hub-Signature-256"), cfg.app_secret):
        return _nao_encontrado()
    aviso_id = aviso_ops.gravar_aviso(corpo)
    if current_app.config.get("WHATSAPP_AVISO_SINCRONO"):
        aviso_ops.processar_aviso(aviso_id, cfg_whatsapp())
    else:
        app = current_app._get_current_object()  # noqa: SLF001 — a thread precisa do app real
        threading.Thread(
            target=_processar_em_segundo_plano, args=(app, aviso_id), daemon=True
        ).start()
    return jsonify({"ok": True})
