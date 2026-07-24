"""Endpoints de LEITURA da Revisão de Mídia (feature 170, US6 — fatia final da migração 144).

Reusa, sem duplicar, `app.revisao.review_ops`. Gates reimplementados como funções, paridade
com `app/revisao/routes.py`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.models import ReviewAsset, ReviewAssetVersion, ReviewReviewer, ReviewSpace, User
from app.revisao import review_ops


def _space_summary(space: ReviewSpace) -> dict:
    return {
        "id": space.id,
        "title": space.title,
        "description": space.description or "",
        "created_at": space.created_at.isoformat(),
        "creator_name": space.creator.name if space.creator else "",
        "asset_count": len(space.assets),
    }


def _asset_summary(asset: ReviewAsset) -> dict:
    return {
        "id": asset.id,
        "media_type": asset.media_type,
        "original_name": asset.original_name or "",
        "position": asset.position,
        "version": asset.version or 1,
        "is_available": asset.is_available,
        "days_left": asset.days_left,
        "finalized_at": asset.finalized_at.isoformat() if asset.finalized_at else None,
        "file_url": asset.file_path if asset.is_available else None,
        "status": asset.status,
    }


@api_bp.route("/revisao")
@api_login_required
def api_revisao_list() -> Any:
    """Espaços de revisão que o usuário pode ver (feature 170)."""
    if review_ops.is_superadmin(current_user):
        spaces = ReviewSpace.query.order_by(ReviewSpace.created_at.desc()).all()
    else:
        reviewer_space_ids = [
            r.space_id for r in ReviewReviewer.query.filter_by(user_id=current_user.id).all()
        ]
        query = ReviewSpace.query.filter(
            (ReviewSpace.created_by == current_user.id)
            | (ReviewSpace.id.in_(reviewer_space_ids) if reviewer_space_ids else False)
        )
        spaces = query.order_by(ReviewSpace.created_at.desc()).all()
    return jsonify(
        {
            "items": [_space_summary(s) for s in spaces],
            "can_create": review_ops.can_create(current_user),
        }
    )


@api_bp.route("/revisao/reviewer-options")
@api_login_required
def api_revisao_reviewer_options() -> Any:
    """Usuários elegíveis para serem selecionados como revisores (feature 170)."""
    if not review_ops.can_create(current_user):
        return json_error("Sem permissão", 403)
    users = (
        User.query.filter_by(is_active=True, has_access=True).order_by(User.name.asc()).all()
    )
    return jsonify({"items": [{"id": u.id, "name": u.name} for u in users]})


@api_bp.route("/revisao/<int:space_id>")
@api_login_required
def api_revisao_detail(space_id: int) -> Any:
    """Detalhe de um espaço: materiais e revisores (feature 170)."""
    space = ReviewSpace.query.get(space_id)
    if space is None:
        return json_error("Espaço não encontrado", 404)
    if not review_ops.can_view(space, current_user):
        return json_error("Sem permissão", 403)
    can_manage = review_ops.can_manage(space, current_user)
    return jsonify(
        {
            **_space_summary(space),
            "can_manage": can_manage,
            "assets": [_asset_summary(a) for a in space.assets],
            "reviewer_ids": sorted(space.reviewer_ids),
        }
    )


@api_bp.route("/revisao/<int:space_id>/asset/<int:asset_id>")
@api_login_required
def api_revisao_asset_detail(space_id: int, asset_id: int) -> Any:
    """Material do espaço (feature 170). ``?v=N`` abre uma versão antiga (só leitura)."""
    space = ReviewSpace.query.get(space_id)
    if space is None:
        return json_error("Espaço não encontrado", 404)
    if not review_ops.can_view(space, current_user):
        return json_error("Sem permissão", 403)
    asset = ReviewAsset.query.filter_by(id=asset_id, space_id=space.id).first()
    if asset is None:
        return json_error("Material não encontrado", 404)

    current_version = asset.version or 1
    requested = request.args.get("v", type=int)
    viewing_version = None
    version_payload = None
    if requested is not None and requested != current_version:
        version_file = ReviewAssetVersion.query.filter_by(
            asset_id=asset.id, version_number=requested
        ).first()
        if version_file is None:
            return json_error("Versão não encontrada", 404)
        viewing_version = requested
        version_payload = {
            "version_number": version_file.version_number,
            "file_url": version_file.file_path if version_file.is_available else None,
            "original_name": version_file.original_name or "",
            "is_available": version_file.is_available,
        }

    return jsonify(
        {
            "space_id": space.id,
            "space_title": space.title,
            "can_manage": review_ops.can_manage(space, current_user),
            "asset": _asset_summary(asset),
            "viewing_version": viewing_version,
            "version_file": version_payload,
            "history": [
                {
                    "version_number": v.version_number,
                    "file_url": v.file_path if v.is_available else None,
                    "original_name": v.original_name or "",
                    "is_available": v.is_available,
                    "created_at": v.created_at.isoformat(),
                }
                for v in asset.history
            ],
        }
    )


@api_bp.route("/revisao/asset/<int:asset_id>/comments")
@api_login_required
def api_revisao_comments(asset_id: int) -> Any:
    """Comentários de UMA versão do material (feature 170)."""
    asset = ReviewAsset.query.get(asset_id)
    if asset is None:
        return json_error("Material não encontrado", 404)
    if not review_ops.can_view(asset.space, current_user):
        return json_error("Sem permissão", 403)
    version = request.args.get("v", type=int) or asset.version or 1
    comments = review_ops.list_comments_for_version(asset, version)
    return jsonify([review_ops.comment_to_dict(c, current_user) for c in comments])
