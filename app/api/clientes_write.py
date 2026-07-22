"""Endpoints de ESCRITA do CRM de Clientes (feature 165, US6 — Cauda Administrativa).

Reusa, sem duplicar, o núcleo já extraído em `app/clientes/client_ops.py` (feature 165). Gate
base: `require_vendas` (COMERCIAL/FINANCEIRO/SUPERADMIN); exclusão exige SUPERADMIN/FINANCEIRO,
mesma paridade de `app/clientes/routes.py::delete`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.clientes import client_ops
from app.constants import RoleName


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_vendas() -> Any:
    if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _client_summary(client) -> dict:
    return {
        "id": client.id,
        "name": client.name,
        "phone": client.phone,
        "phone_display": client.phone_display or client.phone,
        "email": client.email or "",
        "company": client.company or "",
    }


@api_bp.route("/clientes/quick-create", methods=["POST"])
@api_login_required
def api_clientes_quick_create() -> Any:
    """Cria um cliente ou reaproveita o existente por telefone (feature 165)."""
    denied = _require_vendas()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    try:
        client, reused = client_ops.quick_create_client(
            body.get("name") or "",
            body.get("phone") or "",
            phone_display=body.get("phone_display") or body.get("phone"),
            email=body.get("email"),
            company=body.get("company"),
        )
    except client_ops.ClientValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({**_client_summary(client), "reused": reused})


@api_bp.route("/clientes/<int:client_id>", methods=["PATCH"])
@api_login_required
def api_clientes_update(client_id: int) -> Any:
    """Atualiza CPF/CNPJ/endereço do cliente (feature 119, migrada na 165)."""
    denied = _require_vendas()
    if denied:
        return denied
    client, _events, _rel, _total = client_ops.get_client_detail(client_id)
    if client is None:
        return json_error("Cliente não encontrado", 404)
    body = request.get_json(silent=True) or {}
    client_ops.update_client_fields(
        client,
        cpf=body.get("cpf"),
        cnpj=body.get("cnpj"),
        address=body.get("address"),
    )
    return jsonify(
        {
            **_client_summary(client),
            "cpf": client.cpf or "",
            "cnpj": client.cnpj or "",
            "address": client.address or "",
        }
    )


@api_bp.route("/clientes/<int:client_id>", methods=["DELETE"])
@api_login_required
def api_clientes_delete(client_id: int) -> Any:
    """Exclui um cliente, desvinculando eventos associados (feature 165)."""
    if not _has_role(RoleName.SUPERADMIN, RoleName.FINANCEIRO):
        return json_error("Sem permissão", 403)
    client, _events, _rel, _total = client_ops.get_client_detail(client_id)
    if client is None:
        return json_error("Cliente não encontrado", 404)
    client_ops.delete_client(client)
    return "", 204
