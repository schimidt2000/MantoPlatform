"""Aviso da ClickSign (webhook da conta) — feature 317.

O aviso NÃO é interpretado: ele só diz "algo mudou na conta". Validado o HMAC, a rota responde 200
na hora e dispara uma sincronização incremental, que reconsulta a ClickSign (a fonte da verdade).
Assim, um segredo vazado (o `site_settings` vai para o backup e para o espelho) não consegue marcar
contrato como assinado nem parar uma cobrança: no máximo dispara uma consulta (research R-01/R-06).

Sem sessão. `Content-Hmac: sha256=<hex>` = HMAC-SHA256(segredo, corpo BRUTO) — conferido contra o
segredo atual e o anterior (24 h) com `compare_digest`. Inválido ou sem segredo → 404 sem efeito.
Molde de corpo e thread: o aviso da InfinitePay da 310 (não o da `main`, que compara com `==` e
processa dentro da requisição). A ClickSign trata 301 como falha: a rota não redireciona.
"""

import hashlib
import hmac
import threading
from typing import Any

from flask import current_app, jsonify, request

from app import db, limiter
from app.api import api_bp
from app.constants import CLICKSIGN_AVISO_CORPO_MAXIMO, now_sp
from app.models import SiteSetting


def _segredos_validos() -> list[str]:
    """O segredo atual e, por 24 h depois de recadastrar, o anterior."""
    s = db.session.get(SiteSetting, 1)
    if s is None:
        return []
    segredos = [s.clicksign_webhook_secret] if s.clicksign_webhook_secret else []
    if (
        s.clicksign_webhook_secret_anterior
        and s.clicksign_webhook_secret_anterior_ate
        and s.clicksign_webhook_secret_anterior_ate > now_sp()
    ):
        segredos.append(s.clicksign_webhook_secret_anterior)
    return segredos


def aviso_valido(corpo: bytes, cabecalho: str | None) -> bool:
    """Confere o `Content-Hmac` do corpo bruto contra os segredos válidos, em tempo constante."""
    if not cabecalho or not cabecalho.startswith("sha256="):
        return False
    recebido = cabecalho.split("=", 1)[1].strip().lower()
    for segredo in _segredos_validos():
        esperado = hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()
        if hmac.compare_digest(esperado, recebido):
            return True
    return False


def _sincronizar_em_segundo_plano(app: Any) -> None:
    from app.contratos import sincronizar_ops

    with app.app_context():
        try:
            sincronizar_ops.sincronizar(motivo="aviso")
        except Exception:  # noqa: BLE001 — a conferência periódica cobre
            db.session.rollback()
            app.logger.exception("[clicksign] sincronização do aviso falhou")
        finally:
            db.session.remove()


@api_bp.route("/webhooks/clicksign", methods=["POST"])
@limiter.limit("60 per minute")
def api_webhook_clicksign() -> Any:
    """Recebe o aviso, confere o HMAC e dispara a sincronização (o corpo não decide nada)."""
    if (request.content_length or 0) > CLICKSIGN_AVISO_CORPO_MAXIMO:
        return jsonify({"error": {"message": "Corpo grande demais"}}), 413
    corpo = request.get_data(cache=True)
    if len(corpo) > CLICKSIGN_AVISO_CORPO_MAXIMO:
        return jsonify({"error": {"message": "Corpo grande demais"}}), 413
    if not aviso_valido(corpo, request.headers.get("Content-Hmac")):
        return jsonify({"error": {"message": "Não encontrado"}}), 404

    from app.contratos import sincronizar_ops

    if current_app.config.get("CLICKSIGN_AVISO_SINCRONO"):
        sincronizar_ops.sincronizar(motivo="aviso")
    else:
        app = current_app._get_current_object()  # noqa: SLF001 — a thread precisa do app real
        threading.Thread(target=_sincronizar_em_segundo_plano, args=(app,), daemon=True).start()
    return jsonify({"success": True})
