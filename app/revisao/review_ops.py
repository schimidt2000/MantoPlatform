"""Núcleo de negócio da Revisão de Mídia (feature 170, US6 — Cauda Administrativa, fatia final).

Funções puras (sem `request`/`render_template`/`flash`), reusadas tanto pelas views Jinja de
`app/revisao/routes.py` quanto pelos endpoints de API (`app/api/revisao_read.py`,
`app/api/revisao_write.py`) — fonte única, sem duplicar regra de negócio (Princípio I).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

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

EXPIRY_DAYS = 7

_MEDIA_EXTS = {
    "video": {".mp4", ".mov", ".webm", ".m4v", ".ogv"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".aac"},
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
    "pdf": {".pdf"},
}
_MAX_FILE = 512 * 1024 * 1024


class ReviewValidationError(Exception):
    """Erro de validação de negócio (arquivo inválido, tipo incompatível, corpo vazio)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class ReviewCommentVersionError(Exception):
    """Comentário tentado numa versão que não é a atual do material (409)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _has_role(user: User, *names: str) -> bool:
    upper = {n.upper() for n in names}
    return any(r.name.upper() in upper for r in user.roles)


def is_superadmin(user: User) -> bool:
    return _has_role(user, RoleName.SUPERADMIN)


def can_create(user: User) -> bool:
    """Marketing e super admin podem criar espaços."""
    return _has_role(user, RoleName.MARKETING, RoleName.SUPERADMIN)


def can_view(space: ReviewSpace, user: User) -> bool:
    """Criador, revisores selecionados e super admin podem ver/comentar."""
    return is_superadmin(user) or space.created_by == user.id or user.id in space.reviewer_ids


def can_manage(space: ReviewSpace, user: User) -> bool:
    """Só o criador (ou super admin) gerencia o espaço."""
    return is_superadmin(user) or space.created_by == user.id


def can_resolve(comment: ReviewComment, user: User) -> bool:
    """Criador do espaço, super admin ou autor do comentário podem concluir/reabrir."""
    return (
        is_superadmin(user)
        or comment.asset.space.created_by == user.id
        or comment.user_id == user.id
    )


def can_delete_comment(comment: ReviewComment, user: User) -> bool:
    """Só o autor do comentário ou super admin podem excluir."""
    return is_superadmin(user) or comment.user_id == user.id


def detect_media_type(filename: str) -> str | None:
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


def save_assets(
    space: ReviewSpace, files: list[FileStorage], uploader_id: int
) -> tuple[int, list[str]]:
    """Salva os arquivos válidos como materiais do espaço. Retorna (qtd_salva, erros)."""
    errors: list[str] = []
    start = len(space.assets)
    saved = 0
    for file in files:
        if not file or not file.filename:
            continue
        media_type = detect_media_type(file.filename)
        if not media_type:
            errors.append(f"{file.filename}: tipo não suportado.")
            continue
        if _file_size(file) > _MAX_FILE:
            errors.append(f"{file.filename}: arquivo acima de 512 MB.")
            continue
        url = save_file(file, "review")
        db.session.add(
            ReviewAsset(
                space_id=space.id,
                file_path=url,
                original_name=file.filename,
                media_type=media_type,
                position=start + saved,
                expires_at=datetime.utcnow() + timedelta(days=EXPIRY_DAYS),
                uploaded_by=uploader_id,
            )
        )
        saved += 1
    return saved, errors


def create_space(
    *,
    title: str,
    description: str | None,
    creator_id: int,
    reviewer_ids: list[int],
    files: list[FileStorage],
) -> tuple[ReviewSpace, int, list[str]]:
    """Cria um espaço de revisão com materiais e revisores opcionais."""
    clean_title = (title or "").strip()
    if not clean_title:
        raise ReviewValidationError("title", "Informe um título para o espaço.")

    space = ReviewSpace(
        title=clean_title, description=(description or "").strip() or None, created_by=creator_id
    )
    db.session.add(space)
    db.session.flush()

    for uid in reviewer_ids:
        db.session.add(ReviewReviewer(space_id=space.id, user_id=uid))

    saved, errors = save_assets(space, files, creator_id)
    db.session.commit()
    return space, saved, errors


def update_reviewers(space: ReviewSpace, reviewer_ids: list[int]) -> None:
    """Substitui a lista de revisores de um espaço."""
    ReviewReviewer.query.filter_by(space_id=space.id).delete()
    for uid in reviewer_ids:
        db.session.add(ReviewReviewer(space_id=space.id, user_id=uid))
    db.session.commit()


def delete_version_files(asset: ReviewAsset) -> None:
    """Remove do armazenamento os arquivos de snapshots ainda disponíveis do material."""
    for version in asset.versions:
        if not version.file_removed and version.file_path:
            delete_file(version.file_path)
            version.file_removed = True


def delete_space(space: ReviewSpace) -> None:
    """Exclui um espaço e os arquivos (atual e versões) de todos os seus materiais."""
    for asset in space.assets:
        delete_file(asset.file_path)
        delete_version_files(asset)
    db.session.delete(space)
    db.session.commit()


def delete_asset(asset: ReviewAsset) -> None:
    """Exclui um material e seus arquivos (atual e versões)."""
    delete_file(asset.file_path)
    delete_version_files(asset)
    db.session.delete(asset)
    db.session.commit()


def snapshot_current_version(asset: ReviewAsset) -> None:
    """Preserva a versão atual do material como entrada de histórico, antes de sobrescrever."""
    uploaded_at = (
        asset.expires_at - timedelta(days=EXPIRY_DAYS) if asset.expires_at else asset.created_at
    )
    db.session.add(
        ReviewAssetVersion(
            asset_id=asset.id,
            version_number=asset.version or 1,
            file_path=asset.file_path,
            original_name=asset.original_name,
            uploaded_by=asset.uploaded_by,
            created_at=uploaded_at,
            expires_at=asset.expires_at,
            file_removed=asset.file_removed,
        )
    )


def replace_asset(asset: ReviewAsset, file: FileStorage, uploader_id: int) -> ReviewAsset:
    """Substitui o arquivo por uma nova versão, preservando a anterior no histórico."""
    if not file or not file.filename:
        raise ReviewValidationError("file", "Selecione um arquivo para substituir.")
    media_type = detect_media_type(file.filename)
    if media_type != asset.media_type:
        raise ReviewValidationError(
            "file", f"A nova versão precisa ser do mesmo tipo ({asset.media_type})."
        )
    if _file_size(file) > _MAX_FILE:
        raise ReviewValidationError("file", "Arquivo acima de 512 MB.")

    snapshot_current_version(asset)
    asset.file_path = save_file(file, "review")
    asset.original_name = file.filename
    asset.version = (asset.version or 1) + 1
    asset.expires_at = datetime.utcnow() + timedelta(days=EXPIRY_DAYS)
    asset.file_removed = False
    asset.finalized_at = None
    asset.uploaded_by = uploader_id
    db.session.commit()
    return asset


def finalize_asset(asset: ReviewAsset) -> ReviewAsset:
    """Finaliza um material: remove os arquivos (atual e de versões) do armazenamento."""
    if not asset.file_removed and asset.file_path:
        delete_file(asset.file_path)
    delete_version_files(asset)
    asset.file_removed = True
    asset.finalized_at = datetime.utcnow()
    db.session.commit()
    return asset


def comment_to_dict(comment: ReviewComment, user: User) -> dict:
    return {
        "id": comment.id,
        "body": comment.body,
        "author": comment.user.name if comment.user else "—",
        "author_id": comment.user_id,
        "timecode": comment.timecode,
        "page": comment.page,
        "pos_x": comment.pos_x,
        "pos_y": comment.pos_y,
        "version_number": comment.version_number or 1,
        "resolved": comment.resolved,
        "resolved_by_name": comment.resolver.name if comment.resolver else None,
        "resolved_at": comment.resolved_at.strftime("%d/%m/%Y %H:%M")
        if comment.resolved_at
        else None,
        "created_at": comment.created_at.strftime("%d/%m/%Y %H:%M"),
        "can_resolve": can_resolve(comment, user),
        "can_delete": can_delete_comment(comment, user),
    }


def list_comments_for_version(asset: ReviewAsset, version: int) -> list[ReviewComment]:
    return sorted(
        (c for c in asset.comments if (c.version_number or 1) == version),
        key=lambda c: (c.timecode if c.timecode is not None else 1e9, c.page or 0, c.created_at),
    )


def add_comment(
    asset: ReviewAsset,
    *,
    user_id: int,
    body: str,
    timecode: float | None,
    page: int | None,
    pos_x: float | None,
    pos_y: float | None,
    requested_version: int | None,
) -> ReviewComment:
    """Cria um comentário na versão ATUAL do material (versões antigas são só leitura)."""
    clean_body = (body or "").strip()
    if not clean_body:
        raise ReviewValidationError("body", "Comentário vazio.")
    current_version = asset.version or 1
    if requested_version is not None and requested_version != current_version:
        raise ReviewCommentVersionError("Comentários só podem ser feitos na versão atual.")

    comment = ReviewComment(
        asset_id=asset.id,
        user_id=user_id,
        body=clean_body,
        timecode=timecode,
        page=page,
        pos_x=pos_x,
        pos_y=pos_y,
        version_number=current_version,
    )
    db.session.add(comment)
    db.session.commit()
    return comment


def toggle_resolve_comment(comment: ReviewComment, user_id: int) -> ReviewComment:
    """Conclui ou reabre um comentário, registrando quem concluiu e quando."""
    if comment.resolved:
        comment.resolved = False
        comment.resolved_by = None
        comment.resolved_at = None
    else:
        comment.resolved = True
        comment.resolved_by = user_id
        comment.resolved_at = datetime.utcnow()
    db.session.commit()
    return comment


def delete_comment_row(comment: ReviewComment) -> None:
    db.session.delete(comment)
    db.session.commit()


def invite_text(space: ReviewSpace, space_url: str) -> str:
    """Mensagem pronta para a editoria colar no WhatsApp dos revisores."""
    return (
        f'Olá! 👋 Você foi adicionado(a) como revisor(a) de "{space.title}" na Plataforma Manto.\n'
        f"Acesse aqui: {space_url}\n"
        "(entre com seu login de sempre)"
    )
