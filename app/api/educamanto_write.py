"""Endpoints de ESCRITA do EducaManto (feature 235): CRUD de musicais + geração de orçamento.

Só orquestra e serializa — a regra de negócio mora em `app/educamanto/musical_ops.py` e
`quote_ops.py`. A geração RECALCULA tudo no servidor (FR-026): o corpo traz apenas as
entradas de cada configuração, nunca valores prontos.
"""

from typing import Any

from flask import Response, jsonify, make_response, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.educamanto import musical_ops, quote_ops
from app.educamanto.pdf import gerar_orcamento_pdf
from app.models import EducaMantoMusical, EducaMantoQuote

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


@api_bp.route("/educamanto/musicals", methods=["POST"])
@api_login_required
def api_create_musical() -> Any:
    denied = _require_manage()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        musical = musical_ops.create_musical(data)
    except musical_ops.MusicalValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(musical.to_dict()), 201


@api_bp.route("/educamanto/musicals/<int:musical_id>", methods=["PATCH"])
@api_login_required
def api_update_musical(musical_id: int) -> Any:
    denied = _require_manage()
    if denied:
        return denied
    musical = EducaMantoMusical.query.get(musical_id)
    if musical is None:
        return json_error("Musical não encontrado.", 404)
    data = request.get_json(silent=True) or {}
    try:
        musical_ops.update_musical(musical, data)
    except musical_ops.MusicalValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(musical.to_dict())


@api_bp.route("/educamanto/musicals/<int:musical_id>/duplicate", methods=["POST"])
@api_login_required
def api_duplicate_musical(musical_id: int) -> Any:
    denied = _require_manage()
    if denied:
        return denied
    original = EducaMantoMusical.query.get(musical_id)
    if original is None:
        return json_error("Musical não encontrado.", 404)
    copia = musical_ops.duplicate_musical(original)
    return jsonify(copia.to_dict()), 201


@api_bp.route("/educamanto/musicals/<int:musical_id>", methods=["DELETE"])
@api_login_required
def api_delete_musical(musical_id: int) -> Any:
    denied = _require_manage()
    if denied:
        return denied
    musical = EducaMantoMusical.query.get(musical_id)
    if musical is None:
        return json_error("Musical não encontrado.", 404)
    musical_ops.delete_musical(musical)
    return "", 204


@api_bp.route("/educamanto/orcamento/gerar", methods=["POST"])
@api_login_required
def api_gerar_orcamento() -> Any:
    """Gera o orçamento multi-configuração: RECALCULA no servidor, congela o snapshot v2 e
    devolve o PDF (uma página A4 por configuração)."""
    denied = _require_use()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        quote, snapshot = quote_ops.generate_quote(current_user.id, data)
    except quote_ops.QuoteValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message} if exc.field else None)
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
