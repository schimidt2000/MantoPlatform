from datetime import datetime
from flask_login import current_user
from app import db
from app.models import AuditLog


def audit(
    action: str,
    entity_type: str = None,
    entity_id: int = None,
    entity_name: str = None,
    detail: str = None,
):
    """Registra uma ação no AuditLog."""
    actor_name = current_user.name if current_user and current_user.is_authenticated else "Sistema"
    actor_role = (
        ", ".join(r.name for r in current_user.roles)
        if current_user and current_user.is_authenticated
        else None
    )
    db.session.add(AuditLog(
        actor_name=actor_name,
        actor_role=actor_role,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        action=action,
        detail=detail,
        created_at=datetime.utcnow(),
    ))
