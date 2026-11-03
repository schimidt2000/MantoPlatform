"""Webhook do WhatsApp (Cloud API da Meta) — feature 325, Conversas.

RBAC: público, sem sessão. O GET (desafio de verificação) exige o ``WHATSAPP_VERIFY_TOKEN``; o POST
exige ``X-Hub-Signature-256: sha256=<hex>`` = HMAC-SHA256 do corpo BRUTO com o ``WHATSAPP_APP_SECRET``,
conferido com ``compare_digest``. Módulo desligado, token ou assinatura inválidos → **404** sem
efeito (não confirma existência). Molde: ``clicksign_webhook.py`` (corpo com teto, HMAC) e o aviso
da InfinitePay da 310 (grava cru, responde 200, processa numa thread).

O corpo válido é gravado ANTES de qualquer processamento e a resposta é 200 mesmo que o
processamento falhe: a Meta reenviaria por 7 dias o que não teve 200, e o que falhou volta à fila
da varredura (``app/conversas/varredura.py``). A URL é contrato gravado na Meta: não renomear.
"""

from __future__ import annotations

import hashlib
import hmac
import threading
from typing import Any

from flask import Response, current_app, jsonify, request

from app import db, limiter
from app.api import api_bp
from app.conversas import aviso_ops
from app.conversas.configuracao import cfg_whatsapp
from app.conversas.constantes import AVISO_CORPO_MAXIMO


def _nao_encontrado() -> tuple[Any, int]:
    return jsonify({"error": {"message": "Não encontrado"}}), 404


def assinatura_valida(corpo: bytes, cabecalho: str | None, segredo: str) -> bool:
    """Confere o ``X-Hub-Signature-256`` do corpo bruto, em tempo constante."""
    if not segredo or not cabecalho or not cabecalho.startswith("sha256="):
        return False
    recebido = cabecalho.split("=", 1)[1].strip().lower()
    esperado = hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, recebido)


def _processar_em_segundo_plano(app: Any, aviso_id: int) -> None:
    with app.app_context():
        try:
            aviso_ops.processar_aviso(aviso_id, cfg_whatsapp())
        except Exception:  # noqa: BLE001 — a varredura refaz o aviso
            db.session.rollback()
            app.logger.exception("[whatsapp] processamento do aviso %s falhou", aviso_id)
        finally:
            db.session.remove()


@api_bp.route("/webhooks/whatsapp", methods=["GET"])
@limiter.limit("60 per minute")
def api_webhook_whatsapp_verificar() -> Any:
    """Desafio de verificação da Meta: devolve o ``hub.challenge`` se o token conferir."""
    cfg = cfg_whatsapp()
    token = request.args.get("hub.verify_token") or ""
    if (
        not cfg.ligado
        or request.args.get("hub.mode") != "subscribe"
        or not hmac.compare_digest(token, cfg.verify_token)
    ):
        return _nao_encontrado()
    return Response(request.args.get("hub.challenge") or "", status=200, mimetype="text/plain")


@api_bp.route("/webhooks/whatsapp", methods=["POST"])
@limiter.limit("300 per minute")
def api_webhook_whatsapp() -> Any:
    """Recebe o aviso, confere a assinatura, grava cru e responde 200 (processa fora)."""
    cfg = cfg_whatsapp()
    if not cfg.ligado:
        return _nao_encontrado()
    # Lê com teto também o corpo sem `Content-Length` (chunked), como o C-12 da ClickSign.
    grande = (request.content_length or 0) > AVISO_CORPO_MAXIMO
    corpo = b"" if grande else request.stream.read(AVISO_CORPO_MAXIMO + 1)
    if grande or len(corpo) > AVISO_CORPO_MAXIMO:
        # A Meta reenvia o que leva 413: o log é o único sinal de que avisos estão sendo perdidos.
        current_app.logger.warning(
            "[whatsapp] aviso acima de %s bytes recusado", AVISO_CORPO_MAXIMO
        )
        return jsonify({"error": {"message": "Corpo grande demais"}}), 413
    if not assinatura_valida(corpo, request.headers.get("X-Hub-Signature-256"), cfg.app_secret):
        return _nao_encontrado()

    aviso_id = aviso_ops.gravar_aviso(corpo)
    if current_app.config.get("WHATSAPP_AVISO_SINCRONO"):
        aviso_ops.processar_aviso(aviso_id, cfg)
    else:
        app = current_app._get_current_object()  # noqa: SLF001 — a thread precisa do app real
        threading.Thread(
            target=_processar_em_segundo_plano, args=(app, aviso_id), daemon=True
        ).start()
    return jsonify({"ok": True})


# Públicos para o webhook do Instagram (feature 330), que segue o mesmo contrato.
nao_encontrado = _nao_encontrado
processar_em_segundo_plano = _processar_em_segundo_plano
