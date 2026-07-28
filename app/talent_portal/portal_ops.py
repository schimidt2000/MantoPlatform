"""Núcleo de negócio do Portal do Artista (feature 176).

Funções puras (sem `flask.request`/`render_template`/`flash`/`session`), extraídas de
`app/talent_portal/routes.py` — reusadas tanto pela view Jinja legada quanto pelos endpoints de
API (`app/api/portal_*.py`), fonte única (Princípio I). Recebem sempre um `Talent` já resolvido
pela camada que chama (Jinja lê da `session`, API lê da mesma `session` por outro caminho).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_
from werkzeug.datastructures import FileStorage

from app import db
from app.cadastro.cadastro_ops import DOC_EXTS, DOC_MAX, PHOTO_EXTS, PHOTO_MAX, validate_upload
from app.models import CalendarEvent, EventRole, FigurinoSheet, Talent, TalentMedia
from app.storage import save_file

#: Máximo de fotos de atuação que um talento pode manter no portfólio.
MAX_PORTFOLIO_PHOTOS = 3

#: Campos de texto livre do perfil que o próprio talento pode editar pelo portal.
EDITABLE_TEXT_FIELDS = (
    "full_name",
    "artistic_name",
    "phone",
    "email_contact",
    "gender",
    "race",
    "languages",
    "skills",
    "pix_key",
    "pix_key_type",
    "pix_key_secondary",
    "rg",
    "passport_visa_text",
    "car_brand",
    "car_model",
    "car_year",
    "car_plate",
    "clothing_size_top",
    "clothing_size_bottom",
    "shoe_size",
)

#: Campos de data do perfil editáveis pelo talento (ISO `YYYY-MM-DD`).
EDITABLE_DATE_FIELDS = ("birth_date", "cnh_expiration")


class PortalUploadError(Exception):
    """Erro de validação de upload (extensão/tamanho) — nunca vazamento de exceção do storage."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PortalProfileError(Exception):
    """Erro de validação de um campo do perfil (valor fora do formato esperado)."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


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


# ── Perfil e portfólio (feature 191) ───────────────────────────────────────────


def _media_to_dict(item: TalentMedia) -> dict[str, Any]:
    """Serializa um item de portfólio (foto de atuação ou link)."""
    return {
        "id": item.id,
        "media_type": item.media_type,
        "label": item.label,
        "file_url": item.file_path,
        "url": item.url,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def get_profile(talent: Talent) -> dict[str, Any]:
    """Perfil completo do talento para a tela de edição do portal.

    Returns:
        Dict com dados pessoais, medidas corporais, dados de pagamento, arquivos e o portfólio
        (`media`), já serializado para JSON.
    """
    return {
        "id": talent.id,
        "cpf": talent.cpf,
        "full_name": talent.full_name,
        "artistic_name": talent.artistic_name,
        "phone": talent.phone,
        "email_contact": talent.email_contact,
        "gender": talent.gender,
        "race": talent.race,
        "languages": talent.languages,
        "skills": talent.skills,
        "birth_date": talent.birth_date.isoformat() if talent.birth_date else None,
        # Medidas corporais — o bloco mais usado do perfil (figurino depende dele).
        "height_cm": talent.height_cm,
        "clothing_size_top": talent.clothing_size_top,
        "clothing_size_bottom": talent.clothing_size_bottom,
        "shoe_size": talent.shoe_size,
        # Pagamento
        "pix_key": talent.pix_key,
        "pix_key_type": talent.pix_key_type,
        "pix_key_secondary": talent.pix_key_secondary,
        # Documentos e veículo
        "rg": talent.rg,
        "has_visa": bool(talent.has_visa),
        "passport_visa_text": talent.passport_visa_text,
        "cnh_expiration": talent.cnh_expiration.isoformat() if talent.cnh_expiration else None,
        "cnh_file_url": talent.cnh_file_path,
        "car_brand": talent.car_brand,
        "car_model": talent.car_model,
        "car_year": talent.car_year,
        "car_plate": talent.car_plate,
        # Fotos oficiais
        "photo_face_url": talent.photo_face_path,
        "photo_full_url": talent.photo_full_path,
        # Portfólio
        "media": [_media_to_dict(m) for m in talent.media_items],
        "max_photos": MAX_PORTFOLIO_PHOTOS,
    }


def _parse_optional_date(raw: Any, field: str):
    """Converte uma data ISO opcional vinda do cliente, ou `None`.

    Raises:
        PortalProfileError: Valor presente mas fora do formato `YYYY-MM-DD`.
    """
    value = (raw or "").strip() if isinstance(raw, str) else raw
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise PortalProfileError("Data inválida. Use o formato AAAA-MM-DD.", field=field) from exc


def _parse_optional_height(raw: Any):
    """Converte a altura em centímetros, ou `None`.

    Raises:
        PortalProfileError: Valor não numérico ou fora de uma faixa humana plausível.
    """
    value = (raw or "").strip() if isinstance(raw, str) else raw
    if value in (None, ""):
        return None
    try:
        height = int(value)
    except (TypeError, ValueError) as exc:
        raise PortalProfileError("Altura deve ser um número em centímetros.", field="height_cm") from exc
    if not (50 <= height <= 260):
        raise PortalProfileError("Altura deve estar entre 50 e 260 cm.", field="height_cm")
    return height


def update_profile(talent: Talent, data: dict[str, Any]) -> Talent:
    """Aplica ao talento apenas os campos de perfil que ele mesmo pode editar.

    Só as chaves presentes em `data` são tocadas (semântica de PATCH) — assim a tela pode enviar
    um bloco isolado (ex.: só as medidas) sem apagar o resto. `full_name` nunca é apagado: valor
    vazio mantém o nome atual, como já fazia a tela Jinja.

    Args:
        talent: Talento autenticado.
        data: Corpo JSON enviado pelo cliente.

    Returns:
        O talento atualizado.

    Raises:
        PortalProfileError: Altura ou data em formato inválido.
    """
    for field in EDITABLE_TEXT_FIELDS:
        if field not in data:
            continue
        value = (data.get(field) or "").strip() or None
        if field == "full_name" and not value:
            continue  # nome é obrigatório — vazio mantém o atual
        setattr(talent, field, value)

    for field in EDITABLE_DATE_FIELDS:
        if field in data:
            setattr(talent, field, _parse_optional_date(data.get(field), field))

    if "height_cm" in data:
        talent.height_cm = _parse_optional_height(data.get("height_cm"))

    if "has_visa" in data:
        talent.has_visa = bool(data.get("has_visa"))

    db.session.commit()
    return talent


def add_portfolio_photo(talent: Talent, file: FileStorage, label: str | None = None) -> TalentMedia:
    """Adiciona uma foto de atuação ao portfólio do talento.

    Args:
        talent: Talento autenticado.
        file: Imagem enviada.
        label: Legenda opcional.

    Returns:
        O item de portfólio criado.

    Raises:
        PortalUploadError: Limite de fotos atingido, formato não aceito ou acima do tamanho.
    """
    photo_count = TalentMedia.query.filter_by(talent_id=talent.id, media_type="photo").count()
    if photo_count >= MAX_PORTFOLIO_PHOTOS:
        raise PortalUploadError(f"Limite de {MAX_PORTFOLIO_PHOTOS} fotos de atuação atingido.")

    validated, error = validate_upload(file, PHOTO_EXTS, PHOTO_MAX, required=True, label="Foto")
    if error:
        raise PortalUploadError(error)

    ext = os.path.splitext(validated.filename or "")[1].lower()
    filename = f"media_{talent.id}_{uuid.uuid4().hex[:8]}{ext}"
    item = TalentMedia(
        talent_id=talent.id,
        media_type="photo",
        label=(label or "").strip() or None,
        file_path=save_file(validated, "talent_photos", filename),
    )
    db.session.add(item)
    db.session.commit()
    return item


def add_portfolio_link(talent: Talent, url: str, label: str | None = None) -> TalentMedia:
    """Adiciona um link de portfólio (Vimeo, YouTube…) ao talento.

    Args:
        talent: Talento autenticado.
        url: Endereço do vídeo/portfólio — precisa começar com `http://` ou `https://`.
        label: Rótulo opcional; sem ele, usa o começo da própria URL.

    Returns:
        O item de portfólio criado.

    Raises:
        PortalProfileError: URL vazia ou sem esquema http(s).
    """
    url_value = (url or "").strip()
    if not url_value:
        raise PortalProfileError("Informe o endereço do link.", field="url")
    if not url_value.lower().startswith(("http://", "https://")):
        raise PortalProfileError("O link deve começar com http:// ou https://", field="url")

    item = TalentMedia(
        talent_id=talent.id,
        media_type="link",
        label=(label or "").strip() or url_value[:60],
        url=url_value,
    )
    db.session.add(item)
    db.session.commit()
    return item


def delete_portfolio_item(talent: Talent, media_id: int) -> bool:
    """Remove um item do portfólio do talento (e o arquivo físico, se houver).

    Filtra por `talent_id` junto com o `id` — um talento nunca apaga a mídia de outro.

    Returns:
        True se removeu; False se o item não existe ou não é do talento.
    """
    item = TalentMedia.query.filter_by(id=media_id, talent_id=talent.id).first()
    if item is None:
        return False

    if item.file_path:
        _delete_local_upload(item.file_path)

    db.session.delete(item)
    db.session.commit()
    return True


def _delete_local_upload(file_path: str) -> None:
    """Apaga o arquivo local de um upload, ignorando silenciosamente o que não existe.

    Só age sobre caminhos locais (`/uploads/...`); em produção com S3/R2 o `file_path` é uma URL
    absoluta e nada é removido aqui — a limpeza do bucket é responsabilidade de `app.storage`.
    """
    import logging

    from flask import current_app

    if file_path.lower().startswith(("http://", "https://")):
        return

    relative = file_path.removeprefix("/uploads/").removeprefix("uploads/")
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], relative)
    try:
        if os.path.exists(full_path):
            os.remove(full_path)
    except OSError as exc:
        logging.getLogger(__name__).warning("Falha ao remover upload %s: %s", full_path, exc)


# ── Histórico de apresentações (feature 191) ───────────────────────────────────


def get_historico(talent: Talent) -> dict[str, Any]:
    """Histórico completo de eventos passados do talento, com somatórios de cachê.

    Diferente de `get_agenda`, que devolve só os últimos eventos junto com convites e futuros,
    aqui vem a lista completa mais os totais pago/pendente que a tela exibe no topo.

    Args:
        talent: Talento autenticado.

    Returns:
        Dict com `items` (mais recente primeiro) e `totals` (`paid`, `pending`, `overall`,
        `count`). Valores monetários em `float`, formatados no cliente por `@manto/money`.
    """
    past = (
        EventRole.query.filter_by(talent_id=talent.id, invite_status="accepted")
        .join(CalendarEvent)
        .filter(CalendarEvent.start_at < now_sp())
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    items = []
    total_paid = 0.0
    total_pending = 0.0
    for role in past:
        cache_total = float((role.cache_value or 0) + (role.travel_cache or 0))
        if role.payment_status == "pago":
            total_paid += cache_total
        else:
            total_pending += cache_total

        item = _role_summary(role)
        item["cache_value"] = float(role.cache_value or 0)
        item["travel_cache"] = float(role.travel_cache or 0)
        item["cache_total"] = cache_total
        item["payment_status"] = role.payment_status
        items.append(item)

    return {
        "items": items,
        "totals": {
            "paid": total_paid,
            "pending": total_pending,
            "overall": total_paid + total_pending,
            "count": len(items),
        },
    }
