import json as _json
from datetime import datetime
from flask_login import current_user
from app import db
from app.models import AuditLog


def json_for_script(value) -> str:
    """Serializa ``value`` em JSON seguro para injetar dentro de ``<script>`` (feature 074).

    Escapa ``<``, ``>`` e ``&`` (que poderiam fechar o contexto via ``</script>``). Como
    ``json.dumps`` usa ``ensure_ascii=True``, os separadores de linha U+2028/U+2029 já saem como
    ``\\uXXXX``. O resultado continua sendo JSON válido (os escapes voltam ao original no parse).
    Use no lugar de ``json.dumps(...) | safe`` para evitar XSS armazenado.
    """
    return (
        _json.dumps(value)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def audit(
    action: str,
    entity_type: str = None,
    entity_id: int = None,
    entity_name: str = None,
    detail: str = None,
) -> None:
    """Registra uma ação no AuditLog da sessão atual.

    Adiciona um registro de AuditLog à sessão do SQLAlchemy. O commit
    deve ser feito pelo chamador (esta função não persiste sozinha).

    Args:
        action: Verbo que descreve a ação (ex: "criou", "editou", "deletou").
        entity_type: Tipo do objeto afetado (ex: "Talent", "CalendarEvent").
        entity_id: ID primário do objeto afetado, para rastreabilidade.
        entity_name: Nome legível do objeto afetado (ex: nome do talento).
        detail: Informação extra livre (ex: campos alterados, motivo).

    Note:
        O ator é inferido de ``current_user`` (Flask-Login). Fora de contexto
        de requisição autenticada, o ator será registrado como "Sistema".
    """
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
