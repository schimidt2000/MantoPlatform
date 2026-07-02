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
from app.models import (
    ReviewAsset,
    ReviewAssetVersion,
    ReviewComment,
    ReviewReviewer,
    ReviewSpace,
    User,
)
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


def _can_resolve(comment: ReviewComment) -> bool:
    """Criador do espaço, super admin ou autor do comentário podem concluir/reabrir (FR-010)."""
    return (
        _is_superadmin()
        or comment.asset.space.created_by == current_user.id
        or comment.user_id == current_user.id
    )


def _can_delete_comment(comment: ReviewComment) -> bool:
    """Só o autor do comentário ou super admin podem excluir (FR-011).

    Excluir fica fora do fluxo normal de revisão — quem atende um comentário o CONCLUI.
    """
    return _is_superadmin() or comment.user_id == current_user.id


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
            uploaded_by=current_user.id,
        ))
        saved += 1
    return saved, errors


def _snapshot_current_version(asset: ReviewAsset) -> None:
    """Preserva a versão atual do material como entrada de histórico (feature 104).

    Chamado ANTES de sobrescrever o asset em uma substituição: guarda arquivo, autor e prazos
    da versão vigente. O arquivo NÃO é apagado — segue vivo até o ``expires_at`` herdado.
    """
    uploaded_at = (
        asset.expires_at - timedelta(days=_EXPIRY_DAYS)
        if asset.expires_at else asset.created_at
    )
    db.session.add(ReviewAssetVersion(
        asset_id=asset.id,
        version_number=asset.version or 1,
        file_path=asset.file_path,
        original_name=asset.original_name,
        uploaded_by=asset.uploaded_by,
        created_at=uploaded_at,
        expires_at=asset.expires_at,
        file_removed=asset.file_removed,
    ))


def _delete_version_files(asset: ReviewAsset) -> None:
    """Remove do armazenamento os arquivos de snapshots ainda disponíveis do material."""
    for version in asset.versions:
        if not version.file_removed and version.file_path:
            delete_file(version.file_path)
            version.file_removed = True


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
        _delete_version_files(asset)
    db.session.delete(space)
    db.session.commit()
    flash("Espaço excluído.", "success")
    return redirect(url_for("revisao.index"))


# ── Material (visualizador) ───────────────────────────────────────────────────

@revisao_bp.route("/<int:space_id>/asset/<int:asset_id>")
@login_required
def asset_view(space_id: int, asset_id: int):
    """Visualizador do material. ``?v=N`` abre uma versão antiga em modo somente leitura."""
    space = ReviewSpace.query.get_or_404(space_id)
    if not _can_view(space):
        abort(403)
    asset = ReviewAsset.query.filter_by(id=asset_id, space_id=space.id).first_or_404()

    current_version = asset.version or 1
    requested = request.args.get("v", type=int)
    viewing_version = None   # None = versão atual
    version_file = None      # snapshot exibido quando é versão antiga
    if requested is not None and requested != current_version:
        version_file = ReviewAssetVersion.query.filter_by(
            asset_id=asset.id, version_number=requested,
        ).first_or_404()
        viewing_version = requested

    return render_template(
        "revisao/asset.html",
        space=space,
        asset=asset,
        can_manage=_can_manage(space),
        viewing_version=viewing_version,
        version_file=version_file,
        history=asset.history,
    )


@revisao_bp.route("/asset/<int:asset_id>/delete", methods=["POST"])
@login_required
def delete_asset(asset_id: int):
    asset = ReviewAsset.query.get_or_404(asset_id)
    space = asset.space
    if not _can_manage(space):
        abort(403)
    delete_file(asset.file_path)
    _delete_version_files(asset)
    db.session.delete(asset)
    db.session.commit()
    flash("Material excluído.", "success")
    return redirect(url_for("revisao.space_detail", space_id=space.id))


@revisao_bp.route("/asset/<int:asset_id>/replace", methods=["POST"])
@login_required
def replace_asset(asset_id: int):
    """Substitui o arquivo por uma nova versão, preservando a anterior no histórico (feature 104).

    A versão vigente vira um snapshot (``ReviewAssetVersion``) com o arquivo intacto até o prazo
    herdado. A nova versão incrementa o número, reinicia o prazo de 7 dias e mantém os
    comentários antigos associados à versão em que foram feitos.
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

    _snapshot_current_version(asset)
    asset.file_path = save_file(file, "review")
    asset.original_name = file.filename
    asset.version = (asset.version or 1) + 1
    asset.expires_at = datetime.utcnow() + timedelta(days=_EXPIRY_DAYS)
    asset.file_removed = False
    asset.finalized_at = None
    asset.uploaded_by = current_user.id
    db.session.commit()
    flash(f"Nova versão enviada (v{asset.version}). Prazo reiniciado para {_EXPIRY_DAYS} dias.", "success")
    return redirect(url_for("revisao.asset_view", space_id=space.id, asset_id=asset.id))


@revisao_bp.route("/asset/<int:asset_id>/finalize", methods=["POST"])
@login_required
def finalize_asset(asset_id: int):
    """Finaliza um material aprovado: remove os arquivos (atual e de versões antigas) do armazenamento.

    Registros, histórico de versões e comentários permanecem.
    """
    asset = ReviewAsset.query.get_or_404(asset_id)
    space = asset.space
    if not _can_manage(space):
        abort(403)
    if not asset.file_removed and asset.file_path:
        delete_file(asset.file_path)
    _delete_version_files(asset)
    asset.file_removed = True
    asset.finalized_at = datetime.utcnow()
    db.session.commit()
    flash("Material finalizado. Arquivos removidos do armazenamento.", "success")
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
        "version_number": c.version_number or 1,
        "resolved": c.resolved,
        "resolved_by_name": c.resolver.name if c.resolver else None,
        "resolved_at": c.resolved_at.strftime("%d/%m/%Y %H:%M") if c.resolved_at else None,
        "created_at": c.created_at.strftime("%d/%m/%Y %H:%M"),
        "can_resolve": _can_resolve(c),
        "can_delete": _can_delete_comment(c),
    }


@revisao_bp.route("/asset/<int:asset_id>/comments")
@login_required
def list_comments(asset_id: int):
    """Lista os comentários de UMA versão do material (``?v=``; padrão: versão atual)."""
    asset = ReviewAsset.query.get_or_404(asset_id)
    if not _can_view(asset.space):
        abort(403)
    version = request.args.get("v", type=int) or asset.version or 1
    comments = sorted(
        (c for c in asset.comments if (c.version_number or 1) == version),
        key=lambda c: (c.timecode if c.timecode is not None else 1e9, c.page or 0, c.created_at),
    )
    return jsonify([_comment_json(c) for c in comments])


@revisao_bp.route("/asset/<int:asset_id>/comment", methods=["POST"])
@login_required
def add_comment(asset_id: int):
    """Cria um comentário na versão ATUAL do material (versões antigas são só leitura)."""
    asset = ReviewAsset.query.get_or_404(asset_id)
    if not _can_view(asset.space):
        abort(403)
    data = request.get_json(silent=True) or request.form
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Comentário vazio."}), 400
    requested_version = data.get("version")
    if requested_version not in (None, "") and int(requested_version) != (asset.version or 1):
        return jsonify({"error": "Comentários só podem ser feitos na versão atual."}), 409

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
        version_number=asset.version or 1,
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify(_comment_json(comment)), 201


@revisao_bp.route("/comment/<int:comment_id>/resolve", methods=["POST"])
@login_required
def resolve_comment(comment_id: int):
    """Conclui ou reabre um comentário, registrando quem concluiu e quando (feature 104)."""
    comment = ReviewComment.query.get_or_404(comment_id)
    if not _can_view(comment.asset.space):
        abort(403)
    if not _can_resolve(comment):
        return jsonify({"error": "Você não pode concluir este comentário."}), 403
    if comment.resolved:
        comment.resolved = False
        comment.resolved_by = None
        comment.resolved_at = None
    else:
        comment.resolved = True
        comment.resolved_by = current_user.id
        comment.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_comment_json(comment))


@revisao_bp.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id: int):
    comment = ReviewComment.query.get_or_404(comment_id)
    if not _can_delete_comment(comment):
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"ok": True})
