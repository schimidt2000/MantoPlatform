"""Endpoints de ESCRITA das Conversas (feature 325 — WhatsApp na Plataforma).

RBAC: COMERCIAL e SUPERADMIN (``conversas.acesso.pode_conversas``, no início de cada view —
Princípio XIII). Toda escrita que fala com a Meta passa pela trava do ambiente local
(``WHATSAPP_SUPPRESS_SEND``, Princípio XIV) dentro do núcleo (``app/conversas/envio_ops.py``).

Recusas do núcleo saem no envelope de ``json_error`` com ``codigo`` (o que a tela compara, nunca a
mensagem): 409 ``janela_fechada`` / ``envio_travado``, 503 ``nao_configurado``, 422 ``invalido``
com ``fields``, 404 ``nao_encontrada``.
"""

from __future__ import annotations

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.conversas import envio_ops, leitura_ops
from app.conversas.acesso import pode_conversas
from app.conversas.configuracao import cfg_whatsapp
from app.conversas.constantes import MIDIA_TETO_BYTES
from app.conversas.recusa import Recusa


def _negado() -> Any:
    if not pode_conversas(current_user):
        return json_error("Sem permissão", 403)
    return None


def _recusa(exc: Recusa) -> Any:
    return json_error(exc.mensagem, exc.status, fields=exc.fields or None, codigo=exc.codigo)


def _resposta(envio: envio_ops.Envio) -> Any:
    return jsonify({"mensagem": leitura_ops.serializar_mensagem(envio.mensagem)}), (
        201 if envio.nova else 200
    )


def _envio_de_arquivo(conversa_id: int) -> envio_ops.Envio:
    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        raise envio_ops.EnvioRecusado(
            "invalido", "Insira o arquivo.", 422, {"arquivo": "Insira o arquivo."}
        )
    dados = arquivo.stream.read(MIDIA_TETO_BYTES + 1)
    return envio_ops.enviar_arquivo(
        conversa_id,
        dados,
        arquivo.filename,
        arquivo.mimetype,
        request.form.get("legenda"),
        request.form.get("chave_envio"),
        current_user.id,
        cfg_whatsapp(),
    )


@api_bp.route("/conversas/<int:conversa_id>/mensagens", methods=["POST"])
@api_login_required
def api_conversas_enviar(conversa_id: int) -> Any:
    """Envia texto (JSON) ou arquivo (multipart) na conversa."""
    negado = _negado()
    if negado:
        return negado
    try:
        if request.mimetype == "multipart/form-data":
            envio = _envio_de_arquivo(conversa_id)
        else:
            corpo = request.get_json(silent=True) or {}
            envio = envio_ops.enviar_texto(
                conversa_id,
                corpo.get("texto"),
                corpo.get("chave_envio"),
                current_user.id,
                cfg_whatsapp(),
            )
    except Recusa as exc:
        return _recusa(exc)
    return _resposta(envio)


@api_bp.route("/conversas/<int:conversa_id>/modelo", methods=["POST"])
@api_login_required
def api_conversas_enviar_modelo(conversa_id: int) -> Any:
    """Envia um modelo aprovado com as variáveis (vale com a janela fechada)."""
    negado = _negado()
    if negado:
        return negado
    corpo = request.get_json(silent=True) or {}
    variaveis = corpo.get("variaveis")
    try:
        envio = envio_ops.enviar_modelo(
            conversa_id,
            corpo.get("nome"),
            corpo.get("idioma"),
            variaveis if isinstance(variaveis, list) else [],
            corpo.get("chave_envio"),
            current_user.id,
            cfg_whatsapp(),
        )
    except Recusa as exc:
        return _recusa(exc)
    return _resposta(envio)


@api_bp.route("/conversas/<int:conversa_id>/lida", methods=["POST"])
@api_login_required
def api_conversas_lida(conversa_id: int) -> Any:
    """Zera as não lidas da equipe e marca a última recebida como lida na Meta (melhor esforço)."""
    negado = _negado()
    if negado:
        return negado
    try:
        envio_ops.marcar_lida(conversa_id, cfg_whatsapp())
    except Recusa as exc:
        return _recusa(exc)
    return "", 204
