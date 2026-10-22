"""Endpoint de leitura dos contratos da ClickSign a conferir (feature 317).

RBAC (constituição XIII; `docs/01` §4.3): COMERCIAL, FINANCEIRO e SUPERADMIN leem — o mesmo
`show_comercial` do bloco do contrato no evento. A situação de cada venda sai no detalhe do evento e
no `/api/dashboard`; aqui só a lista completa de "A conferir" (a Home mostra as 6 primeiras).
"""

from typing import Any

from flask import jsonify
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.contratos import situacao_ops
from app.contratos.sincronizar_ops import integracao_ligada

_PAPEIS_QUE_VEEM = {RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN}


@api_bp.route("/contratos/a-conferir")
@api_login_required
def api_contratos_a_conferir() -> Any:
    """Todos os documentos a conferir, com o motivo e as vendas sugeridas."""
    if not any(r.name.upper() in _PAPEIS_QUE_VEEM for r in current_user.roles):
        return json_error("Sem permissão", 403)
    if not integracao_ligada():
        return jsonify({"integracao_ligada": False, "itens": []})
    return jsonify(
        {
            "integracao_ligada": True,
            "itens": [
                situacao_ops.linha_a_conferir(d) for d in situacao_ops.documentos_a_conferir()
            ],
        }
    )
