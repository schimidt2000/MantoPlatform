"""Endpoints de ESCRITA do EducaManto (feature 175): CRUD de pacote + geração de orçamento.

Só orquestra e serializa — a regra de negócio mora em `app/educamanto/package_ops.py` e
`app/educamanto/quote_ops.py`, sem duplicar lógica com a view Jinja legada. Gates reimplementados
como função, paridade com `app/educamanto/routes.py` (`_CAN_MANAGE`/`_CAN_USE`).
"""

from typing import Any

from flask import Response, jsonify, make_response, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.educamanto import package_ops, quote_ops
from app.educamanto.pdf import gerar_orcamento_pdf
from app.models import EducaMantoPackage, EducaMantoQuote

_CAN_USE = {
    RoleName.COMERCIAL,
    RoleName.SUPERADMIN,
    RoleName.ENSAIO,
    RoleName.REVENDEDOR_EDUCAMANTO,
}
_CAN_MANAGE = {RoleName.SUPERADMIN}


def _require_use() -> Any:
    if not {r.name.upper() for r in current_user.roles} & _CAN_USE:
        return json_error("Sem permissão", 403)
    return None


def _require_manage() -> Any:
    if not {r.name.upper() for r in current_user.roles} & _CAN_MANAGE:
        return json_error("Sem permissão", 403)
    return None


def _pdf_response(snapshot: dict, quote_id: int, *, inline: bool) -> Response:
    pdf_bytes = gerar_orcamento_pdf(snapshot)
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    disp = "inline" if inline else "attachment"
    resp.headers["Content-Disposition"] = (
        f'{disp}; filename="orcamento-educamanto-{quote_id}.pdf"'
    )
    return resp


@api_bp.route("/educamanto/packages", methods=["POST"])
@api_login_required
def api_create_package() -> Any:
    denied = _require_manage()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        pkg = package_ops.create_package(data)
    except package_ops.PackageValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(pkg.to_dict()), 201


@api_bp.route("/educamanto/packages/<int:pkg_id>", methods=["PATCH"])
@api_login_required
def api_update_package(pkg_id: int) -> Any:
    denied = _require_manage()
    if denied:
        return denied
    pkg = EducaMantoPackage.query.get(pkg_id)
    if pkg is None:
        return json_error("Pacote não encontrado.", 404)
    data = request.get_json(silent=True) or {}
    try:
        package_ops.update_package(pkg, data)
    except package_ops.PackageValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(pkg.to_dict())


@api_bp.route("/educamanto/packages/<int:pkg_id>/duplicate", methods=["POST"])
@api_login_required
def api_duplicate_package(pkg_id: int) -> Any:
    denied = _require_manage()
    if denied:
        return denied
    original = EducaMantoPackage.query.get(pkg_id)
    if original is None:
        return json_error("Pacote não encontrado.", 404)
    copy = package_ops.duplicate_package(original)
    return jsonify(copy.to_dict()), 201


@api_bp.route("/educamanto/packages/<int:pkg_id>", methods=["DELETE"])
@api_login_required
def api_delete_package(pkg_id: int) -> Any:
    denied = _require_manage()
    if denied:
        return denied
    pkg = EducaMantoPackage.query.get(pkg_id)
    if pkg is None:
        return json_error("Pacote não encontrado.", 404)
    package_ops.delete_package(pkg)
    return "", 204


@api_bp.route("/educamanto/orcamento/gerar", methods=["POST"])
@api_login_required
def api_gerar_orcamento() -> Any:
    denied = _require_use()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        quote, snapshot = quote_ops.generate_quote(current_user.id, data)
    except quote_ops.QuoteValidationError as exc:
        return json_error(exc.message, 400)
    return _pdf_response(snapshot, quote.id, inline=False)


@api_bp.route("/educamanto/orcamento/<int:quote_id>/pdf")
@api_login_required
def api_orcamento_pdf(quote_id: int) -> Any:
    denied = _require_use()
    if denied:
        return denied
    quote = EducaMantoQuote.query.get(quote_id)
    if quote is None:
        return json_error("Orçamento não encontrado.", 404)
    snapshot = quote_ops.load_quote_snapshot(quote)
    return _pdf_response(snapshot, quote.id, inline=True)
