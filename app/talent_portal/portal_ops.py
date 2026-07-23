"""Núcleo de negócio do Portal do Artista (feature 176).

Funções puras (sem `flask.request`/`render_template`/`flash`/`session`), extraídas de
`app/talent_portal/routes.py` — reusadas tanto pela view Jinja legada quanto pelos endpoints de
API (`app/api/portal_*.py`), fonte única (Princípio I). Recebem sempre um `Talent` já resolvido
pela camada que chama (Jinja lê da `session`, API lê da mesma `session` por outro caminho).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_
from werkzeug.datastructures import FileStorage

from app import db
from app.cadastro.cadastro_ops import DOC_EXTS, DOC_MAX, PHOTO_EXTS, PHOTO_MAX, validate_upload
from app.models import CalendarEvent, EventRole, FigurinoSheet, Talent
from app.storage import save_file


class PortalUploadError(Exception):
    """Erro de validação de upload (extensão/tamanho) — nunca vazamento de exceção do storage."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def now_sp() -> datetime:
    """Agora em horário de Brasília, naïve — mesma convenção dos horários de evento no banco."""
    return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)


def find_talent_by_login(value: str) -> Talent | None:
    """Acha um talento por CPF (dígitos) ou e-mail (feature 092).

    Talentos estrangeiros não têm CPF e acessam o portal pelo e-mail. Se o valor tiver ``@``,
    busca por ``email_contact`` (case-insensitive); caso contrário, trata como CPF (dígitos).
    """
    value = (value or "").strip()
    if not value:
        return None
    if "@" in value:
        return Talent.query.filter(func.lower(Talent.email_contact) == value.lower()).first()
    digits = "".join(c for c in value if c.isdigit())
    if not digits:
        return None
    return Talent.query.filter_by(cpf=digits).first()


def needs_classic_portal_flow(talent: Talent) -> bool:
    """True se o login deve ser direcionado à versão clássica (troca de senha/termos pendentes)."""
    return bool(talent.must_change_password or not talent.terms_accepted_at)


def _not_rejected():
    """Cláusula: escalação cujo convite NÃO foi recusado (aceito, pendente ou sem status)."""
    return or_(EventRole.invite_status.is_(None), EventRole.invite_status != "rejected")


def _role_summary(role: EventRole) -> dict:
    event = role.event
    return {
        "role_id": role.id,
        "event_id": event.id,
        "title": event.title,
        "start_at": event.start_at.isoformat() if event.start_at else None,
        "end_at": event.end_at.isoformat() if event.end_at else None,
        "location": event.location,
        "character_name": role.character_name,
        "has_unacknowledged_change": bool(role.event_changed_at),
        "change_description": role.change_description,
    }


def get_agenda(talent: Talent) -> dict:
    """Monta a Agenda do talento: convites pendentes, eventos futuros e histórico com cachê.

    Nota: `home()`/`historico()` (Jinja legado) mantêm suas próprias consultas em vez de chamar
    esta função — elas misturam a mesma listagem com o fluxo de avaliação de eventos (fora do
    escopo desta fatia, feature 176), e essa função devolve dicts serializados (para a API), não
    os objetos ORM que o template Jinja precisa. Duplicação reconhecida e aceita deliberadamente
    aqui: refatorar `home()` tocaria a lógica de avaliação sem necessidade, mais arriscado que o
    ganho de reuso neste caso pontual.

    Args:
        talent: Talento autenticado.

    Returns:
        Dict com `pending_invites`, `upcoming` e `history` (histórico inclui `cache_total` e
        `payment_status` por item).
    """
    now = now_sp()

    pending_invites = (
        EventRole.query.filter_by(talent_id=talent.id, invite_status="pending")
        .join(CalendarEvent)
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )

    upcoming = (
        EventRole.query.filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.start_at >= now)
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )

    past = (
        EventRole.query.filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.start_at < now)
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    history = []
    for role in past:
        item = _role_summary(role)
        item["cache_total"] = float((role.cache_value or 0) + (role.travel_cache or 0))
        item["payment_status"] = role.payment_status
        history.append(item)

    return {
        "pending_invites": [_role_summary(r) for r in pending_invites],
        "upcoming": [_role_summary(r) for r in upcoming],
        "history": history,
    }


def _owned_role(talent: Talent, role_id: int) -> EventRole | None:
    return EventRole.query.filter_by(id=role_id, talent_id=talent.id).first()


def accept_invite(talent: Talent, role_id: int) -> EventRole | None:
    """Aceita um convite pendente — idempotente (repetir não muda nada nem gera erro)."""
    role = _owned_role(talent, role_id)
    if role is None:
        return None
    role.invite_status = "accepted"
    db.session.commit()
    return role


def reject_invite(talent: Talent, role_id: int) -> EventRole | None:
    """Recusa um convite — idempotente. Mantém `talent_id` (o casting precisa saber quem recusou)."""
    role = _owned_role(talent, role_id)
    if role is None:
        return None
    role.invite_status = "rejected"
    db.session.commit()
    return role


def ack_event_change(talent: Talent, role_id: int) -> EventRole | None:
    """Marca como reconhecida a alteração de um evento já aceito pelo talento."""
    role = _owned_role(talent, role_id)
    if role is None:
        return None
    role.event_changed_at = None
    role.change_description = None
    db.session.commit()
    return role


def get_figurino(talent: Talent, event_id: int) -> list[tuple[FigurinoSheet, str | None]] | None:
    """Fichas de figurino dos personagens do talento num evento.

    Args:
        talent: Talento autenticado.
        event_id: Evento consultado.

    Returns:
        Lista de `(sheet, photo_url)` (pode ser vazia — evento escalado sem ficha ainda), ou
        `None` se o talento não está escalado nesse evento (nem pendente, nem aceito).
    """
    from app.figurino.drive_service import normalize_name

    role = EventRole.query.filter(
        EventRole.event_id == event_id,
        EventRole.talent_id == talent.id,
        EventRole.invite_status.in_(["accepted", "pending"]),
    ).first()
    if role is None:
        return None

    event = role.event
    seen_ids: set[int] = set()
    sheet_items: list[tuple[FigurinoSheet, str | None]] = []

    for r in [r for r in event.roles if r.talent_id == talent.id]:
        sheet = r.figurino_sheet
        if not sheet:
            norm = normalize_name(r.character_name)
            sheet = FigurinoSheet.query.filter_by(character_name_norm=norm).first()

        if not sheet or sheet.id in seen_ids:
            continue
        seen_ids.add(sheet.id)

        photo_url = None
        if sheet.photo_filename:
            if sheet.photo_filename.startswith("/uploads/"):
                photo_url = "/portal/photo/" + sheet.photo_filename[9:]
            else:
                photo_url = sheet.photo_filename

        sheet_items.append((sheet, photo_url))

    return sheet_items


def update_photo(talent: Talent, kind: str, file: FileStorage) -> Talent:
    """Substitui a foto de rosto ou corpo inteiro do talento.

    Args:
        talent: Talento autenticado.
        kind: `"face"` ou `"full"`.
        file: Arquivo enviado.

    Raises:
        PortalUploadError: Formato não aceito ou acima do limite.
    """
    validated, error = validate_upload(file, PHOTO_EXTS, PHOTO_MAX, required=True, label="Foto")
    if error:
        raise PortalUploadError(error)
    url = save_file(validated, "talent_photos")
    if kind == "full":
        talent.photo_full_path = url
    else:
        talent.photo_face_path = url
    db.session.commit()
    return talent


def update_document(talent: Talent, file: FileStorage) -> Talent:
    """Substitui o arquivo da CNH do talento.

    Raises:
        PortalUploadError: Formato não aceito ou acima do limite.
    """
    validated, error = validate_upload(file, DOC_EXTS, DOC_MAX, required=True, label="Arquivo da CNH")
    if error:
        raise PortalUploadError(error)
    talent.cnh_file_path = save_file(validated, "talent_docs")
    db.session.commit()
    return talent
