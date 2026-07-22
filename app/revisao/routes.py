"""Espaço de revisão de mídia estilo Vimeo Review (feature 088).

Equipe de marketing cria espaços, sobe materiais (vídeo/áudio/imagem/PDF) e escolhe revisores.
Revisores comentam ancorando no time code (vídeo/áudio), na página (PDF) ou num ponto (imagem).
Núcleo de negócio em `app/revisao/review_ops.py` (feature 170), reusado também pela API JSON.
"""

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.models import ReviewAsset, ReviewAssetVersion, ReviewComment, ReviewSpace, User
from app.revisao import review_ops

revisao_bp = Blueprint("revisao", __name__, url_prefix="/revisao")


def _wants_json() -> bool:
    """True quando o request veio do upload com progresso (feature 105)."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


# ── Lista ─────────────────────────────────────────────────────────────────────


@revisao_bp.route("/")
@login_required
def index():
    """Lista os espaços que o usuário pode ver (criados por ele, onde é revisor, ou tudo se admin)."""
    if review_ops.is_superadmin(current_user):
        spaces = ReviewSpace.query.order_by(ReviewSpace.created_at.desc()).all()
    else:
        from app.models import ReviewReviewer

        reviewer_space_ids = [
            r.space_id for r in ReviewReviewer.query.filter_by(user_id=current_user.id).all()
        ]
        spaces = (
            ReviewSpace.query.filter(
                db.or_(
                    ReviewSpace.created_by == current_user.id,
                    ReviewSpace.id.in_(reviewer_space_ids) if reviewer_space_ids else False,
                )
            )
            .order_by(ReviewSpace.created_at.desc())
            .all()
        )
    return render_template(
        "revisao/list.html", spaces=spaces, can_create=review_ops.can_create(current_user)
    )


# ── Criar ─────────────────────────────────────────────────────────────────────


@revisao_bp.route("/novo", methods=["GET", "POST"])
@login_required
def new_space():
    if not review_ops.can_create(current_user):
        abort(403)
    users = User.query.filter_by(is_active=True, has_access=True).order_by(User.name.asc()).all()

    if request.method == "GET":
        return render_template("revisao/new.html", users=users)

    reviewer_ids = []
    for uid in request.form.getlist("reviewers"):
        try:
            reviewer_ids.append(int(uid))
        except (ValueError, TypeError):
            continue

    try:
        space, saved, errors = review_ops.create_space(
            title=request.form.get("title", ""),
            description=request.form.get("description", ""),
            creator_id=current_user.id,
            reviewer_ids=reviewer_ids,
            files=request.files.getlist("files"),
        )
    except review_ops.ReviewValidationError as exc:
        if _wants_json():
            return jsonify({"error": exc.message}), 400
        flash(exc.message, "error")
        return render_template("revisao/new.html", users=users)

    for e in errors:
        flash(e, "warning")
    flash(f"Espaço criado com {saved} material(is).", "success")
    # ?novo=1 destaca o convite aos revisores na tela do espaço (feature 105)
    target = url_for("revisao.space_detail", space_id=space.id, novo=1)
    if _wants_json():
        return jsonify({"redirect": target})
    return redirect(target)


# ── Detalhe do espaço ─────────────────────────────────────────────────────────


@revisao_bp.route("/<int:space_id>")
@login_required
def space_detail(space_id: int):
    space = ReviewSpace.query.get_or_404(space_id)
    if not review_ops.can_view(space, current_user):
        abort(403)
    users = []
    can_manage = review_ops.can_manage(space, current_user)
    if can_manage:
        users = (
            User.query.filter_by(is_active=True, has_access=True).order_by(User.name.asc()).all()
        )
    return render_template(
        "revisao/space.html",
        space=space,
        can_manage=can_manage,
        users=users,
        just_created=request.args.get("novo") == "1",
        invite_text=review_ops.invite_text(
            space, url_for("revisao.space_detail", space_id=space.id, _external=True)
        ),
    )


@revisao_bp.route("/<int:space_id>/upload", methods=["POST"])
@login_required
def upload_assets(space_id: int):
    space = ReviewSpace.query.get_or_404(space_id)
    if not review_ops.can_manage(space, current_user):
        abort(403)
    saved, errors = review_ops.save_assets(space, request.files.getlist("files"), current_user.id)
    db.session.commit()
    for e in errors:
        flash(e, "warning")
    flash(f"{saved} material(is) adicionado(s).", "success")
    target = url_for("revisao.space_detail", space_id=space.id)
    if _wants_json():
        return jsonify({"redirect": target})
    return redirect(target)


@revisao_bp.route("/<int:space_id>/reviewers", methods=["POST"])
@login_required
def update_reviewers(space_id: int):
    space = ReviewSpace.query.get_or_404(space_id)
    if not review_ops.can_manage(space, current_user):
        abort(403)
    reviewer_ids = []
    for uid in request.form.getlist("reviewers"):
        try:
            reviewer_ids.append(int(uid))
        except (ValueError, TypeError):
            continue
    review_ops.update_reviewers(space, reviewer_ids)
    flash("Revisores atualizados.", "success")
    return redirect(url_for("revisao.space_detail", space_id=space.id))


@revisao_bp.route("/<int:space_id>/delete", methods=["POST"])
@login_required
def delete_space(space_id: int):
    space = ReviewSpace.query.get_or_404(space_id)
    if not review_ops.can_manage(space, current_user):
        abort(403)
    review_ops.delete_space(space)
    flash("Espaço excluído.", "success")
    return redirect(url_for("revisao.index"))


# ── Material (visualizador) ───────────────────────────────────────────────────


@revisao_bp.route("/<int:space_id>/asset/<int:asset_id>")
@login_required
def asset_view(space_id: int, asset_id: int):
    """Visualizador do material. ``?v=N`` abre uma versão antiga em modo somente leitura."""
    space = ReviewSpace.query.get_or_404(space_id)
    if not review_ops.can_view(space, current_user):
        abort(403)
    asset = ReviewAsset.query.filter_by(id=asset_id, space_id=space.id).first_or_404()

    current_version = asset.version or 1
    requested = request.args.get("v", type=int)
    viewing_version = None
    version_file = None
    if requested is not None and requested != current_version:
        version_file = ReviewAssetVersion.query.filter_by(
            asset_id=asset.id, version_number=requested
        ).first_or_404()
        viewing_version = requested

    return render_template(
        "revisao/asset.html",
        space=space,
        asset=asset,
        can_manage=review_ops.can_manage(space, current_user),
        viewing_version=viewing_version,
        version_file=version_file,
        history=asset.history,
    )


@revisao_bp.route("/asset/<int:asset_id>/delete", methods=["POST"])
@login_required
def delete_asset(asset_id: int):
    asset = ReviewAsset.query.get_or_404(asset_id)
    space = asset.space
    if not review_ops.can_manage(space, current_user):
        abort(403)
    review_ops.delete_asset(asset)
    flash("Material excluído.", "success")
    return redirect(url_for("revisao.space_detail", space_id=space.id))


@revisao_bp.route("/asset/<int:asset_id>/replace", methods=["POST"])
@login_required
def replace_asset(asset_id: int):
    """Substitui o arquivo por uma nova versão, preservando a anterior no histórico (feature 104)."""
    asset = ReviewAsset.query.get_or_404(asset_id)
    space = asset.space
    if not review_ops.can_manage(space, current_user):
        abort(403)

    try:
        review_ops.replace_asset(asset, request.files.get("file"), current_user.id)
    except review_ops.ReviewValidationError as exc:
        if _wants_json():
            return jsonify({"error": exc.message}), 400
        flash(exc.message, "error")
        return redirect(url_for("revisao.asset_view", space_id=space.id, asset_id=asset.id))

    flash(
        f"Nova versão enviada (v{asset.version}). Prazo reiniciado para {review_ops.EXPIRY_DAYS} dias.",
        "success",
    )
    target = url_for("revisao.asset_view", space_id=space.id, asset_id=asset.id)
    if _wants_json():
        return jsonify({"redirect": target})
    return redirect(target)


@revisao_bp.route("/asset/<int:asset_id>/finalize", methods=["POST"])
@login_required
def finalize_asset(asset_id: int):
    """Finaliza um material aprovado: remove os arquivos do armazenamento."""
    asset = ReviewAsset.query.get_or_404(asset_id)
    space = asset.space
    if not review_ops.can_manage(space, current_user):
        abort(403)
    review_ops.finalize_asset(asset)
    flash("Material finalizado. Arquivos removidos do armazenamento.", "success")
    return redirect(url_for("revisao.space_detail", space_id=space.id))


# ── Comentários (JSON) ────────────────────────────────────────────────────────


@revisao_bp.route("/asset/<int:asset_id>/comments")
@login_required
def list_comments(asset_id: int):
    """Lista os comentários de UMA versão do material (``?v=``; padrão: versão atual)."""
    asset = ReviewAsset.query.get_or_404(asset_id)
    if not review_ops.can_view(asset.space, current_user):
        abort(403)
    version = request.args.get("v", type=int) or asset.version or 1
    comments = review_ops.list_comments_for_version(asset, version)
    return jsonify([review_ops.comment_to_dict(c, current_user) for c in comments])


@revisao_bp.route("/asset/<int:asset_id>/comment", methods=["POST"])
@login_required
def add_comment(asset_id: int):
    """Cria um comentário na versão ATUAL do material (versões antigas são só leitura)."""
    asset = ReviewAsset.query.get_or_404(asset_id)
    if not review_ops.can_view(asset.space, current_user):
        abort(403)
    data = request.get_json(silent=True) or request.form

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

    requested_version = data.get("version")
    try:
        comment = review_ops.add_comment(
            asset,
            user_id=current_user.id,
            body=data.get("body") or "",
            timecode=_to_float(data.get("timecode")),
            page=_to_int(data.get("page")),
            pos_x=_to_float(data.get("pos_x")),
            pos_y=_to_float(data.get("pos_y")),
            requested_version=_to_int(requested_version),
        )
    except review_ops.ReviewValidationError as exc:
        return jsonify({"error": exc.message}), 400
    except review_ops.ReviewCommentVersionError as exc:
        return jsonify({"error": exc.message}), 409
    return jsonify(review_ops.comment_to_dict(comment, current_user)), 201


@revisao_bp.route("/comment/<int:comment_id>/resolve", methods=["POST"])
@login_required
def resolve_comment(comment_id: int):
    """Conclui ou reabre um comentário, registrando quem concluiu e quando (feature 104)."""
    comment = ReviewComment.query.get_or_404(comment_id)
    if not review_ops.can_view(comment.asset.space, current_user):
        abort(403)
    if not review_ops.can_resolve(comment, current_user):
        return jsonify({"error": "Você não pode concluir este comentário."}), 403
    review_ops.toggle_resolve_comment(comment, current_user.id)
    return jsonify(review_ops.comment_to_dict(comment, current_user))


@revisao_bp.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id: int):
    comment = ReviewComment.query.get_or_404(comment_id)
    if not review_ops.can_delete_comment(comment, current_user):
        abort(403)
    review_ops.delete_comment_row(comment)
    return jsonify({"ok": True})
