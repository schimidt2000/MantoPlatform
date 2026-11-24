"""Endpoints de LEITURA da conferência de personagens do catálogo (feature 360).

RBAC: SUPERADMIN em todas as rotas — o mesmo gate da gestão do catálogo, chamado no início de cada
view. A conferência é delegada à Superadmin; os demais papéis recebem 403.

Só valida o papel, chama `app.admin.catalog_conferencia_ops` e devolve o que o núcleo serializou.
"""

from typing import Any

from flask import jsonify, request

from app.admin import catalog_conferencia_ops as ops
from app.api import api_bp
from app.api.admin_catalogo_read import _require_superadmin
from app.api_utils import api_login_required, json_error


@api_bp.route("/admin/catalogo/conferencia")
@api_login_required
def api_catalogo_conferencia_fila() -> Any:
    """Fila da conferência: contadores da fila inteira e os itens do filtro (`tipo`, `situacao`, `q`)."""
    denied = _require_superadmin()
    if denied:
        return denied
    return jsonify(
        ops.listar_fila(
            tipo=request.args.get("tipo"),
            situacao=request.args.get("situacao"),
            busca=request.args.get("q"),
        )
    )


@api_bp.route("/admin/catalogo/conferencia/<int:item_id>")
@api_login_required
def api_catalogo_conferencia_item(item_id: int) -> Any:
    """Um item da conferência: fotos, proposta da leitura, decisões e os vizinhos a conferir."""
    denied = _require_superadmin()
    if denied:
        return denied
    try:
        detalhe = ops.detalhe_do_item(
            item_id, tipo=request.args.get("tipo"), busca=request.args.get("q")
        )
    except ops.ConferenciaNaoEncontrada as exc:
        return json_error(exc.message, 404)
    return jsonify(detalhe)
