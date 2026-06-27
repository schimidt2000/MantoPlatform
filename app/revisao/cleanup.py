"""Limpeza de arquivos temporários da Revisão (feature 090).

Materiais de revisão expiram em 7 dias. Esta rotina remove o **arquivo** do armazenamento dos materiais
vencidos e não finalizados, mantendo o registro e os comentários (o histórico da revisão não se perde).
É idempotente e segura para rodar várias vezes.
"""
from datetime import datetime


def cleanup_expired_review_files() -> int:
    """Remove o arquivo dos materiais vencidos e não finalizados. Retorna quantos foram removidos.

    Requer um ``app_context`` ativo. Marca ``file_removed=True`` (não apaga o registro).
    """
    from app import db
    from app.models import ReviewAsset
    from app.storage import delete_file

    now = datetime.utcnow()
    expired = ReviewAsset.query.filter(
        ReviewAsset.file_removed.is_(False),
        ReviewAsset.finalized_at.is_(None),
        ReviewAsset.expires_at.isnot(None),
        ReviewAsset.expires_at < now,
    ).all()

    removed = 0
    for asset in expired:
        try:
            delete_file(asset.file_path)
        except Exception:  # noqa: BLE001 — falha ao apagar 1 arquivo não pode travar a limpeza
            pass
        asset.file_removed = True
        removed += 1
    if removed:
        db.session.commit()
    return removed
