"""Endpoints de LEITURA das Conversas (feature 325 — WhatsApp na Plataforma).

RBAC: COMERCIAL e SUPERADMIN (``conversas.acesso.pode_conversas``, função chamada no início de cada
view — Princípio XIII). A mídia de quem não tem o papel responde **404**, não 403, para não
confirmar que o arquivo existe. Os endpoints só validam, chamam o núcleo (``app/conversas/``) e
serializam.
"""

from __future__ import annotations

from typing import Any

from flask import jsonify, request, send_file
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.conversas import envio_ops, leitura_ops, midia_ops
from app.conversas.acesso import pode_conversas
from app.conversas.configuracao import cfg_whatsapp
from app.integracoes import whatsapp_client as wc
from app.models import Conversa, ConversaMidia


def _negado() -> Any:
    if not pode_conversas(current_user):
        return json_error("Sem permissão", 403)
    return None


@api_bp.route("/conversas")
@api_login_required
def api_conversas_lista() -> Any:
    """Lista de conversas, da última mensagem para trás, com busca e cursor."""
    negado = _negado()
    if negado:
        return negado
    cfg = cfg_whatsapp()
    conversas, proximo = leitura_ops.listar_conversas(
        request.args.get("busca"), request.args.get("antes")
    )
    return jsonify(
        {
            "configurado": cfg.ligado,
            "envio_travado": cfg.travado,
            "poll_segundos": cfg.poll_segundos,
            "conversas": [leitura_ops.serializar_conversa(c) for c in conversas],
            "proximo": proximo,
        }
    )


@api_bp.route("/conversas/<int:conversa_id>")
@api_login_required
def api_conversas_detalhe(conversa_id: int) -> Any:
    """A conversa aberta: cabeçalho e as últimas mensagens (``antes=<id>`` pagina para trás)."""
    negado = _negado()
    if negado:
        return negado
    conversa = db.session.get(Conversa, conversa_id)
    if conversa is None:
        return json_error("Conversa não encontrada.", 404)
    antes = request.args.get("antes", type=int)
    mensagens, tem_mais = leitura_ops.mensagens_da_conversa(conversa.id, antes)
    return jsonify(
        {
            "conversa": leitura_ops.serializar_conversa(conversa),
            "mensagens": [leitura_ops.serializar_mensagem(m) for m in mensagens],
            "tem_mais": tem_mais,
        }
    )


@api_bp.route("/conversas/midia/<int:midia_id>")
@api_login_required
def api_conversas_midia(midia_id: int) -> Any:
    """O arquivo de uma mensagem. Sem papel, inexistente ou não guardado → 404."""
    if not pode_conversas(current_user):
        return json_error("Não encontrado", 404)
    midia = db.session.get(ConversaMidia, midia_id)
    caminho = midia_ops.caminho_absoluto(midia, cfg_whatsapp()) if midia is not None else None
    if caminho is None:
        return json_error("Não encontrado", 404)
    return send_file(
        caminho,
        mimetype=midia.mime or "application/octet-stream",
        download_name=midia.nome_original or None,
        as_attachment=False,
        conditional=True,
    )


@api_bp.route("/conversas/modelos")
@api_login_required
def api_conversas_modelos() -> Any:
    """Modelos aprovados da conta, para o "Enviar modelo" (cache de 5 min no núcleo)."""
    negado = _negado()
    if negado:
        return negado
    try:
        modelos = envio_ops.modelos_aprovados(cfg_whatsapp())
    except (wc.WhatsappErro, envio_ops.EnvioRecusado):
        return json_error("Não foi possível carregar os modelos. Tente novamente.", 503)
    return jsonify({"modelos": modelos})
