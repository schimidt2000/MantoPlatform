"""Espaço de revisão de mídia estilo Vimeo Review (feature 088).

Equipe de marketing cria espaços, sobe materiais (vídeo/áudio/imagem/PDF) e escolhe revisores.
Revisores comentam ancorando no time code (vídeo/áudio), na página (PDF) ou num ponto (imagem).
"""
import os
from datetime import datetime, timedelta

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
from werkzeug.datastructures import FileStorage

from app import db
from app.constants import RoleName
from app.models import ReviewAsset, ReviewComment, ReviewReviewer, ReviewSpace, User
from app.storage import delete_file, save_file

revisao_bp = Blueprint("revisao", __name__, url_prefix="/revisao")

_EXPIRY_DAYS = 7  # arquivos de revisão são temporários (feature 090)

# Extensões permitidas por tipo de mídia.
_MEDIA_EXTS = {
    "video": {".mp4", ".mov", ".webm", ".m4v", ".ogv"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".aac"},
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
    "pdf": {".pdf"},
}
_MAX_FILE = 512 * 1024 * 1024  # 512 MB por arquivo


def _has_role(*names) -> bool:
    return any(r.name.upper() in {n.upper() for n in names} for r in current_user.roles)


def _is_superadmin() -> bool:
    return _has_role(RoleName.SUPERADMIN)


def _can_create() -> bool:
    """Marketing e super admin podem criar espaços."""
    return _has_role(RoleName.MARKETING, RoleName.SUPERADMIN)


def _can_view(space: ReviewSpace) -> bool:
    """Criador, revisores selecionados e super admin podem ver/comentar."""
    return (
        _is_superadmin()
        or space.created_by == current_user.id
        or current_user.id in space.reviewer_ids
    )


def _can_manage(space: ReviewSpace) -> bool:
    """Só o criador (ou super admin) gerencia o espaço."""
    return _is_superadmin() or space.created_by == current_user.id


def _detect_media_type(filename: str) -> str | None:
    ext = os.path.splitext(filename or "")[1].lower()
    for media_type, exts in _MEDIA_EXTS.items():
        if ext in exts:
            return media_type
    return None


def _file_size(file: FileStorage) -> int:
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size


def _save_assets(space: ReviewSpace, files: list[FileStorage]) -> tuple[int, list[str]]:
    """Salva os arquivos válidos como materiais do espaço. Retorna (qtd_salva, erros)."""
    errors: list[str] = []
    start = len(space.assets)
    saved = 0
    for file in files:
        if not file or not file.filename:
            continue
        media_type = _detect_media_type(file.filename)
        if not media_type:
            errors.append(f"{file.filename}: tipo não suportado.")
            continue
        if _file_size(file) > _MAX_FILE:
            errors.append(f"{file.filename}: arquivo acima de 512 MB.")
            continue
        url = save_file(file, "review")
        db.session.add(ReviewAsset(
            space_id=space.id,
            file_path=url,
            original_name=file.filename,
            media_type=media_type,
            position=start + saved,
            expires_at=datetime.utcnow() + timedelta(days=_EXPIRY_DAYS),
        ))
        saved += 1
    return saved, errors


# ── Lista ─────────────────────────────────────────────────────────────────────

@revisao_bp.route("/")
@login_required
def index():
    """Lista os espaços que o usuário pode ver (criados por ele, onde é revisor, ou tudo se admin)."""
    if _is_superadmin():
        spaces = ReviewSpace.query.order_by(ReviewSpace.created_at.desc()).all()
    else:
        reviewer_space_ids = [
            r.space_id for r in ReviewReviewer.query.filter_by(user_id=current_user.id).all()
        ]
        spaces = (
            ReviewSpace.query
            .filter(
                db.or_(
                    ReviewSpace.created_by == current_user.id,
                    ReviewSpace.id.in_(reviewer_space_ids) if reviewer_space_ids else False,
                )
            )
            .order_by(ReviewSpace.created_at.desc())
            .all()
        )
    return render_template("revisao/list.html", spaces=spaces, can_create=_can_create())


# ── Criar ─────────────────────────────────────────────────────────────────────

@revisao_bp.route("/novo", methods=["GET", "POST"])
@login_required
def new_space():
    if not _can_create():
        abort(403)
    users = User.query.filter_by(is_active=True, has_access=True).order_by(User.name.asc()).all()

    if request.method == "GET":
        return render_template("revisao/new.html", users=users)

    title = (request.form.get("title") or "").strip()
    if not title:
        flash("Informe um título para o espaço.", "error")
        return render_template("revisao/new.html", users=users)

    space = ReviewSpace(
        title=title,
        description=(request.form.get("description") or "").strip() or None,
        created_by=current_user.id,
    )
    db.session.add(space)
    db.session.flush()

    # Revisores selecionados
    for uid in request.form.getlist("reviewers"):
        try:
            db.session.add(ReviewReviewer(space_id=space.id, user_id=int(uid)))
        except (ValueError, TypeError):
            continue

    saved, errors = _save_assets(space, request.files.getlist("files"))
    db.session.commit()

    for e in errors:
        flash(e, "warning")
    flash(f"Espaço criado com {saved} material(is).", "success")
    return redirect(url_for("revisao.space_detail", space_id=space.id))


# ── Detalhe do espaço ─────────────────────────────────────────────────────────

@revisao_bp.route("/<int:space_id>")
@login_required
def space_detail(space_id: int):
    space = ReviewSpace.query.get_or_404(space_id)
    if not _can_view(space):
        abort(403)
    users = []
    if _can_manage(space):
        users = User.query.filter_by(is_active=True, has_access=True).order_by(User.name.asc()).all()
    return render_template(
        "revisao/space.html",
        space=space,
        can_manage=_can_manage(space),
        users=users,
    )


@revisao_bp.route("/<int:space_id>/upload", methods=["POST"])
@login_required
def upload_assets(space_id: int):
    space = ReviewSpace.query.get_or_404(space_id)
    if not _can_manage(space):
        abort(403)
    saved, errors = _save_assets(space, request.files.getlist("files"))
    db.session.commit()
    for e in errors:
        flash(e, "warning")
    flash(f"{saved} material(is) adicionado(s).", "success")
    return redirect(url_for("revisao.space_detail", space_id=space.id))


@revisao_bp.route("/<int:space_id>/reviewers", methods=["POST"])
@login_required
def update_reviewers(space_id: int):
    space = ReviewSpace.query.get_or_404(space_id)
    if not _can_manage(space):
        abort(403)
    ReviewReviewer.query.filter_by(space_id=space.id).delete()
    for uid in request.form.getlist("reviewers"):
        try:
            db.session.add(ReviewReviewer(space_id=space.id, user_id=int(uid)))
        except (ValueError, TypeError):
            continue
    db.session.commit()
    flash("Revisores atualizados.", "success")
    return redirect(url_for("revisao.space_detail", space_id=space.id))


@revisao_bp.route("/<int:space_id>/delete", methods=["POST"])
@login_required
def delete_space(space_id: int):
    space = ReviewSpace.query.get_or_404(space_id)
    if not _can_manage(space):
        abort(403)
    for asset in space.assets:
        delete_file(asset.file_path)
    db.session.delete(space)
    db.session.commit()
    flash("Espaço excluído.", "success")
    return redirect(url_for("revisao.index"))


# ── Material (visualizador) ───────────────────────────────────────────────────

@revisao_bp.route("/<int:space_id>/asset/<int:asset_id>")
@login_required
def asset_view(space_id: int, asset_id: int):
    space = ReviewSpace.query.get_or_404(space_id)
    if not _can_view(space):
        abort(403)
    asset = ReviewAsset.query.filter_by(id=asset_id, space_id=space.id).first_or_404()
    return render_template(
        "revisao/asset.html",
        space=space,
        asset=asset,
        can_manage=_can_manage(space),
    )


@revisao_bp.route("/asset/<int:asset_id>/delete", methods=["POST"])
@login_required
def delete_asset(asset_id: int):
    asset = ReviewAsset.query.get_or_404(asset_id)
    space = asset.space
    if not _can_manage(space):
        abort(403)
    delete_file(asset.file_path)
    db.session.delete(asset)
    db.session.commit()
    flash("Material excluído.", "success")
    return redirect(url_for("revisao.space_detail", space_id=space.id))


@revisao_bp.route("/asset/<int:asset_id>/replace", methods=["POST"])
@login_required
def replace_asset(asset_id: int):
    """Substitui o arquivo de um material por uma nova versão (feature 090).

    Remove o arquivo antigo, salva o novo (mesmo tipo de mídia), incrementa a versão e reinicia o
    prazo de 7 dias. Os comentários são mantidos.
    """
    asset = ReviewAsset.query.get_or_404(asset_id)
    space = asset.space
    if not _can_manage(space):
        abort(403)

    file = request.files.get("file")
    if not file or not file.filename:
        flash("Selecione um arquivo para substituir.", "error")
        return redirect(url_for("revisao.asset_view", space_id=space.id, asset_id=asset.id))
    media_type = _detect_media_type(file.filename)
    if media_type != asset.media_type:
        flash(f"A nova versão precisa ser do mesmo tipo ({asset.media_type}).", "error")
        return redirect(url_for("revisao.asset_view", space_id=space.id, asset_id=asset.id))
    if _file_size(file) > _MAX_FILE:
        flash("Arquivo acima de 512 MB.", "error")
        return redirect(url_for("revisao.asset_view", space_id=space.id, asset_id=asset.id))

    if asset.file_path and not asset.file_removed:
        delete_file(asset.file_path)
    asset.file_path = save_file(file, "review")
    asset.original_name = file.filename
    asset.version = (asset.version or 1) + 1
    asset.expires_at = datetime.utcnow() + timedelta(days=_EXPIRY_DAYS)
    asset.file_removed = False
    asset.finalized_at = None
    db.session.commit()
    flash(f"Arquivo substituído (versão {asset.version}). Prazo reiniciado para {_EXPIRY_DAYS} dias.", "success")
    return redirect(url_for("revisao.asset_view", space_id=space.id, asset_id=asset.id))


@revisao_bp.route("/asset/<int:asset_id>/finalize", methods=["POST"])
@login_required
def finalize_asset(asset_id: int):
    """Finaliza um material aprovado: remove o arquivo do armazenamento (registro + comentários ficam)."""
    asset = ReviewAsset.query.get_or_404(asset_id)
    space = asset.space
    if not _can_manage(space):
        abort(403)
    if not asset.file_removed and asset.file_path:
        delete_file(asset.file_path)
    asset.file_removed = True
    asset.finalized_at = datetime.utcnow()
    db.session.commit()
    flash("Material finalizado. Arquivo removido do armazenamento.", "success")
    return redirect(url_for("revisao.space_detail", space_id=space.id))


# ── Comentários (JSON) ────────────────────────────────────────────────────────

def _comment_json(c: ReviewComment) -> dict:
    return {
        "id": c.id,
        "body": c.body,
        "author": c.user.name if c.user else "—",
        "author_id": c.user_id,
        "timecode": c.timecode,
        "page": c.page,
        "pos_x": c.pos_x,
        "pos_y": c.pos_y,
        "resolved": c.resolved,
        "created_at": c.created_at.strftime("%d/%m/%Y %H:%M"),
        "can_delete": _is_superadmin() or c.user_id == current_user.id or c.asset.space.created_by == current_user.id,
    }


@revisao_bp.route("/asset/<int:asset_id>/comments")
@login_required
def list_comments(asset_id: int):
    asset = ReviewAsset.query.get_or_404(asset_id)
    if not _can_view(asset.space):
        abort(403)
    comments = sorted(
        asset.comments,
        key=lambda c: (c.timecode if c.timecode is not None else 1e9, c.page or 0, c.created_at),
    )
    return jsonify([_comment_json(c) for c in comments])


@revisao_bp.route("/asset/<int:asset_id>/comment", methods=["POST"])
@login_required
def add_comment(asset_id: int):
    asset = ReviewAsset.query.get_or_404(asset_id)
    if not _can_view(asset.space):
        abort(403)
    data = request.get_json(silent=True) or request.form
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Comentário vazio."}), 400

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

    comment = ReviewComment(
        asset_id=asset.id,
        user_id=current_user.id,
        body=body,
        timecode=_to_float(data.get("timecode")),
        page=_to_int(data.get("page")),
        pos_x=_to_float(data.get("pos_x")),
        pos_y=_to_float(data.get("pos_y")),
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify(_comment_json(comment)), 201


@revisao_bp.route("/comment/<int:comment_id>/resolve", methods=["POST"])
@login_required
def resolve_comment(comment_id: int):
    comment = ReviewComment.query.get_or_404(comment_id)
    if not _can_view(comment.asset.space):
        abort(403)
    comment.resolved = not comment.resolved
    db.session.commit()
    return jsonify(_comment_json(comment))


@revisao_bp.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id: int):
    comment = ReviewComment.query.get_or_404(comment_id)
    space = comment.asset.space
    if not (_is_superadmin() or comment.user_id == current_user.id or space.created_by == current_user.id):
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"ok": True})
