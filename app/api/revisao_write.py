"""Endpoints de ESCRITA da Revisão de Mídia (feature 170, US6 — fatia final da migração 144).

Reusa, sem duplicar, `app.revisao.review_ops`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.models import ReviewAsset, ReviewComment, ReviewSpace
from app.revisao import review_ops


def _int_list(values: list[str]) -> list[int]:
    result = []
    for v in values:
        try:
            result.append(int(v))
        except (ValueError, TypeError):
            continue
    return result


def _space_summary(space: ReviewSpace) -> dict:
    return {
        "id": space.id,
        "title": space.title,
        "description": space.description or "",
        "created_at": space.created_at.isoformat(),
        "creator_name": space.creator.name if space.creator else "",
        "asset_count": len(space.assets),
    }


@api_bp.route("/revisao", methods=["POST"])
@api_login_required
def api_revisao_create() -> Any:
    """Cria um espaço de revisão com materiais e revisores opcionais (feature 170)."""
    if not review_ops.can_create(current_user):
        return json_error("Sem permissão", 403)
    reviewer_ids = _int_list(request.form.getlist("reviewer_ids[]"))
    try:
        space, saved, errors = review_ops.create_space(
            title=request.form.get("title", ""),
            description=request.form.get("description", ""),
            creator_id=current_user.id,
            reviewer_ids=reviewer_ids,
            files=request.files.getlist("files"),
        )
    except review_ops.ReviewValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({**_space_summary(space), "saved": saved, "errors": errors}), 201


@api_bp.route("/revisao/<int:space_id>/upload", methods=["POST"])
@api_login_required
def api_revisao_upload(space_id: int) -> Any:
    """Adiciona materiais a um espaço existente (feature 170)."""
    space = ReviewSpace.query.get(space_id)
    if space is None:
        return json_error("Espaço não encontrado", 404)
    if not review_ops.can_manage(space, current_user):
        return json_error("Sem permissão", 403)
    saved, errors = review_ops.save_assets(space, request.files.getlist("files"), current_user.id)
    from app import db

    db.session.commit()
    return jsonify({"saved": saved, "errors": errors})


@api_bp.route("/revisao/<int:space_id>/reviewers", methods=["PATCH"])
@api_login_required
def api_revisao_update_reviewers(space_id: int) -> Any:
    """Substitui a lista de revisores de um espaço (feature 170)."""
    space = ReviewSpace.query.get(space_id)
    if space is None:
        return json_error("Espaço não encontrado", 404)
    if not review_ops.can_manage(space, current_user):
        return json_error("Sem permissão", 403)
    body = request.get_json(silent=True) or {}
    review_ops.update_reviewers(space, body.get("reviewer_ids") or [])
    return jsonify({"reviewer_ids": sorted(space.reviewer_ids)})


@api_bp.route("/revisao/<int:space_id>", methods=["DELETE"])
@api_login_required
def api_revisao_delete_space(space_id: int) -> Any:
    """Exclui um espaço e os arquivos de todos os seus materiais (feature 170)."""
    space = ReviewSpace.query.get(space_id)
    if space is None:
        return json_error("Espaço não encontrado", 404)
    if not review_ops.can_manage(space, current_user):
        return json_error("Sem permissão", 403)
    review_ops.delete_space(space)
    return "", 204


@api_bp.route("/revisao/asset/<int:asset_id>", methods=["DELETE"])
@api_login_required
def api_revisao_delete_asset(asset_id: int) -> Any:
    """Exclui um material e seus arquivos (feature 170)."""
    asset = ReviewAsset.query.get(asset_id)
    if asset is None:
        return json_error("Material não encontrado", 404)
    if not review_ops.can_manage(asset.space, current_user):
        return json_error("Sem permissão", 403)
    review_ops.delete_asset(asset)
    return "", 204


@api_bp.route("/revisao/asset/<int:asset_id>/replace", methods=["POST"])
@api_login_required
def api_revisao_replace_asset(asset_id: int) -> Any:
    """Substitui o arquivo de um material, preservando a versão anterior (feature 170)."""
    asset = ReviewAsset.query.get(asset_id)
    if asset is None:
        return json_error("Material não encontrado", 404)
    if not review_ops.can_manage(asset.space, current_user):
        return json_error("Sem permissão", 403)
    try:
        review_ops.replace_asset(asset, request.files.get("file"), current_user.id)
    except review_ops.ReviewValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"version": asset.version})


@api_bp.route("/revisao/asset/<int:asset_id>/finalize", methods=["POST"])
@api_login_required
def api_revisao_finalize_asset(asset_id: int) -> Any:
    """Finaliza um material, removendo seus arquivos do armazenamento (feature 170)."""
    asset = ReviewAsset.query.get(asset_id)
    if asset is None:
        return json_error("Material não encontrado", 404)
    if not review_ops.can_manage(asset.space, current_user):
        return json_error("Sem permissão", 403)
    review_ops.finalize_asset(asset)
    return jsonify({"finalized_at": asset.finalized_at.isoformat()})


@api_bp.route("/revisao/asset/<int:asset_id>/status", methods=["PATCH"])
@api_login_required
def api_revisao_set_status(asset_id: int) -> Any:
    """Altera o status de aprovação de um material (feature 182)."""
    asset = ReviewAsset.query.get(asset_id)
    if asset is None:
        return json_error("Material não encontrado", 404)
    if not review_ops.can_manage(asset.space, current_user):
        return json_error("Sem permissão", 403)
    body = request.get_json(silent=True) or {}
    try:
        review_ops.set_asset_status(asset, body.get("status") or "")
    except review_ops.ReviewValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"status": asset.status})


@api_bp.route("/revisao/asset/<int:asset_id>/comment", methods=["POST"])
@api_login_required
def api_revisao_add_comment(asset_id: int) -> Any:
    """Cria um comentário na versão atual do material (feature 170)."""
    asset = ReviewAsset.query.get(asset_id)
    if asset is None:
        return json_error("Material não encontrado", 404)
    if not review_ops.can_view(asset.space, current_user):
        return json_error("Sem permissão", 403)
    body = request.get_json(silent=True) or {}

    def _to_float(v):
        try:
            return float(v) if v not in (None, "") else None
        except (ValueError, TypeError):
            return None

    def _to_int(v):
        try:
            return int(v) if v not in (None, "") else None
        except (ValueError, TypeError):
            return None

    try:
        comment = review_ops.add_comment(
            asset,
            user_id=current_user.id,
            body=body.get("body") or "",
            timecode=_to_float(body.get("timecode")),
            page=_to_int(body.get("page")),
            pos_x=_to_float(body.get("pos_x")),
            pos_y=_to_float(body.get("pos_y")),
            requested_version=_to_int(body.get("version")),
        )
    except review_ops.ReviewValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    except review_ops.ReviewCommentVersionError as exc:
        return json_error(exc.message, 409)
    return jsonify(review_ops.comment_to_dict(comment, current_user)), 201


@api_bp.route("/revisao/comment/<int:comment_id>/resolve", methods=["POST"])
@api_login_required
def api_revisao_resolve_comment(comment_id: int) -> Any:
    """Conclui ou reabre um comentário (feature 170)."""
    comment = ReviewComment.query.get(comment_id)
    if comment is None:
        return json_error("Comentário não encontrado", 404)
    if not review_ops.can_view(comment.asset.space, current_user):
        return json_error("Sem permissão", 403)
    if not review_ops.can_resolve(comment, current_user):
        return json_error("Você não pode concluir este comentário.", 403)
    review_ops.toggle_resolve_comment(comment, current_user.id)
    return jsonify(review_ops.comment_to_dict(comment, current_user))


@api_bp.route("/revisao/comment/<int:comment_id>", methods=["DELETE"])
@api_login_required
def api_revisao_delete_comment(comment_id: int) -> Any:
    """Exclui um comentário (feature 170)."""
    comment = ReviewComment.query.get(comment_id)
    if comment is None:
        return json_error("Comentário não encontrado", 404)
    if not review_ops.can_delete_comment(comment, current_user):
        return json_error("Sem permissão", 403)
    review_ops.delete_comment_row(comment)
    return "", 204
