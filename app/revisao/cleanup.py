"""Limpeza de arquivos temporários da Revisão (features 090/104).

Materiais de revisão expiram em 7 dias. Esta rotina remove o **arquivo** do armazenamento dos materiais
vencidos e não finalizados — e também dos snapshots de versões antigas (feature 104) — mantendo os
registros e os comentários (o histórico da revisão não se perde).
É idempotente e segura para rodar várias vezes.
"""
from datetime import datetime


def cleanup_expired_review_files() -> int:
    """Remove os arquivos vencidos (materiais atuais e versões antigas). Retorna o total removido.

    Requer um ``app_context`` ativo. Marca ``file_removed=True`` (não apaga registros).
    """
    from app import db
    from app.models import ReviewAsset, ReviewAssetVersion
    from app.storage import delete_file

    now = datetime.utcnow()
    expired = ReviewAsset.query.filter(
        ReviewAsset.file_removed.is_(False),
        ReviewAsset.finalized_at.is_(None),
        ReviewAsset.expires_at.isnot(None),
        ReviewAsset.expires_at < now,
    ).all()
    expired_versions = ReviewAssetVersion.query.filter(
        ReviewAssetVersion.file_removed.is_(False),
        ReviewAssetVersion.expires_at.isnot(None),
        ReviewAssetVersion.expires_at < now,
    ).all()

    removed = 0
    for record in expired + expired_versions:
        try:
            delete_file(record.file_path)
        except Exception:  # noqa: BLE001 — falha ao apagar 1 arquivo não pode travar a limpeza
            pass
        record.file_removed = True
        removed += 1
    if removed:
        db.session.commit()
    return removed
