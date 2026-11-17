"""O código do site (feature 348) — superfície PÚBLICA, sem login.

RBAC: nenhum papel. O site público pede o código quando a visita chega com marcador de campanha
(``gclid``, ``utm_*``…); o limite por endereço do Flask-Limiter segura robô. O núcleo e a explicação do
fluxo estão em ``app/conversas/codigo_ops.py``. Nada de dado pessoal entra: só os marcadores da URL, o
caminho da página e o host de quem mandou a visita.
"""

from __future__ import annotations

from typing import Any

from flask import jsonify, request

from app import limiter
from app.api import api_bp
from app.api_utils import json_error
from app.conversas import codigo_ops
from app.conversas import constantes as K


@api_bp.route("/origem/codigo", methods=["POST"])
@limiter.limit("20 per hour")
def api_origem_criar_codigo() -> Any:
    """Cria o código curto de um clique de campanha. 400 sem marcador.

    201 ``{codigo, linha, validade_dias}``: a ``linha`` é o texto que vai na mensagem pronta — o servidor é a
    fonte só dele (o formulário público usa a mesma, por ``codigo_ops.anexar_a_mensagem``).
    """
    corpo = request.get_json(silent=True)
    try:
        registro = codigo_ops.criar_codigo(corpo if isinstance(corpo, dict) else {})
    except codigo_ops.SemMarcador as exc:
        return json_error(str(exc), 400)
    return jsonify(
        {
            "codigo": registro.codigo,
            "linha": codigo_ops.linha_do_codigo(registro.codigo),
            "validade_dias": K.VALIDADE_DO_CODIGO.days,
        }
    ), 201
