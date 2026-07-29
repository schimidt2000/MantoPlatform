"""Núcleo de negócio das Impressões e do Acervo 3D (feature 200).

Funções puras (sem `request`/`render_template`/`flash`), fonte única reusada pelos endpoints
JSON de `app/api/impressoes3d_read.py` e `app/api/impressoes3d_write.py` — e, no caso de
`serialize_gift`, também por `app/api/agenda_read.py`, que embute os presentes 3D no detalhe do
evento (Princípio I: um mesmo payload não pode ter duas montagens).
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.constants import (
    EVENT_TYPE_SHOW,
    GIFT_3D_STATUS_ENTREGUE,
    GIFT_3D_STATUS_PENDENTE,
    GIFT_3D_STATUSES,
)
from app.models import (
    Acervo3DFile,
    Acervo3DItem,
    CalendarEvent,
    Event3DDismissal,
    Event3DGift,
    EventRole,
    FormResponse,
)
from app.storage import delete_file, save_file
from app.utils import audit

# Uploads do Acervo: a foto de preview é o que permite a busca visual (Princípio X.2) e os
# arquivos brutos são o que o Artista 3D manda para a impressora (N por peça — o modelo costuma
# vir fatiado em partes).
ACERVO_3D_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ACERVO_3D_MODEL_EXTENSIONS = {".zip", ".stl", ".3mf"}
ACERVO_3D_PHOTO_SUBFOLDER = "acervo_3d_photos"
ACERVO_3D_MODEL_SUBFOLDER = "acervo_3d_files"

MAX_GIFT_QUANTITY = 999


class Impressao3DValidationError(Exception):
    """Erro de validação de negócio do módulo 3D, com o campo culpado.

    O endpoint traduz em `json_error(msg, 400, fields={campo: msg})`, para o React destacar o
    campo exato do formulário (Princípio V — falha de validação sempre tem feedback no campo).
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


# ── Validações de upload ─────────────────────────────────────────────────────


def _validate_extension(file_obj: Any, field: str, allowed: set[str], label: str) -> None:
    """Rejeita arquivo com extensão fora de `allowed` (comparação em minúsculas)."""
    if not file_obj or not getattr(file_obj, "filename", ""):
        return
    ext = os.path.splitext(file_obj.filename)[1].lower()
    if ext not in allowed:
        raise Impressao3DValidationError(
            field, f"Arquivo não suportado (use {label}): {file_obj.filename}"
        )


def _has_upload(file_obj: Any) -> bool:
    """True quando o campo multipart veio com um arquivo de verdade (não vazio)."""
    return bool(file_obj and getattr(file_obj, "filename", ""))


# ── Acervo 3D ────────────────────────────────────────────────────────────────


def list_acervo(*, include_inactive: bool = True) -> list[tuple[Acervo3DItem, int]]:
    """Lista o acervo com a contagem de usos de cada peça em eventos.

    Args:
        include_inactive: Quando False, devolve apenas peças ativas.

    Returns:
        Lista de `(item, quantidade_de_vinculos)` ordenada por nome — a contagem é o número de
        linhas de `Event3DGift` que apontam para a peça (quantas vezes o modelo já foi usado em
        eventos), não a soma das quantidades impressas.
    """
    usage = (
        db.session.query(Event3DGift.item_id, func.count(Event3DGift.id))
        .group_by(Event3DGift.item_id)
        .all()
    )
    usage_by_item = dict(usage)

    query = Acervo3DItem.query
    if not include_inactive:
        query = query.filter(Acervo3DItem.is_active.is_(True))
    items = query.order_by(Acervo3DItem.name.asc()).all()
    return [(item, usage_by_item.get(item.id, 0)) for item in items]


def _attach_model_files(item: Acervo3DItem, model_files: list[Any], start_position: int) -> None:
    """Salva no storage e vincula à peça cada arquivo 3D informado, em ordem."""
    for offset, model_file in enumerate(model_files):
        db.session.add(
            Acervo3DFile(
                item=item,
                file_path=save_file(model_file, ACERVO_3D_MODEL_SUBFOLDER),
                original_name=(model_file.filename or "")[:255] or None,
                position=start_position + offset,
            )
        )


def create_acervo_item(
    *, name: str, photo_file: Any, model_files: list[Any] | None = None
) -> Acervo3DItem:
    """Cadastra uma peça nova no Acervo 3D.

    Args:
        name: Nome da peça (obrigatório).
        photo_file: Foto de preview JPG/PNG (obrigatória — a seleção da peça é visual).
        model_files: Arquivos 3D `.stl`/`.3mf`/`.zip` — **pelo menos um**. Um mesmo presente
            costuma vir fatiado em várias partes (corpo, argola, base).

    Raises:
        Impressao3DValidationError: Nome vazio, foto/arquivo ausente ou extensão não suportada.
    """
    clean_name = (name or "").strip()
    if not clean_name:
        raise Impressao3DValidationError("name", "Nome da peça é obrigatório.")
    if not _has_upload(photo_file):
        raise Impressao3DValidationError("photo", "A foto de preview (JPG/PNG) é obrigatória.")
    valid_models = [f for f in (model_files or []) if _has_upload(f)]
    if not valid_models:
        raise Impressao3DValidationError(
            "files", "Envie pelo menos um arquivo 3D (.stl, .3mf ou .zip)."
        )
    _validate_extension(photo_file, "photo", ACERVO_3D_PHOTO_EXTENSIONS, "JPG ou PNG")
    for model_file in valid_models:
        _validate_extension(model_file, "files", ACERVO_3D_MODEL_EXTENSIONS, "STL, 3MF ou ZIP")

    item = Acervo3DItem(
        name=clean_name,
        photo_url=save_file(photo_file, ACERVO_3D_PHOTO_SUBFOLDER),
    )
    db.session.add(item)
    _attach_model_files(item, valid_models, 0)
    db.session.flush()
    audit(
        "create", "Acervo3DItem", item.id, clean_name,
        f"Peça do Acervo 3D criada com {len(valid_models)} arquivo(s)",
    )
    db.session.commit()
    return item


def update_acervo_item(
    item: Acervo3DItem,
    *,
    name: str | None = None,
    is_active: bool | None = None,
    photo_file: Any = None,
    model_files: list[Any] | None = None,
    remove_file_ids: set[int] | None = None,
) -> Acervo3DItem:
    """Edita uma peça do Acervo. Só aplica os campos explicitamente informados.

    A foto nova substitui a anterior e remove a antiga do storage (`photo_url` é NOT NULL, então
    "não enviar nada" significa manter a atual). Os arquivos 3D são **acumulativos**:
    `model_files` acrescenta, `remove_file_ids` remove — e a peça nunca pode ficar com zero
    arquivos, senão deixaria de ser imprimível.
    """
    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise Impressao3DValidationError("name", "Nome da peça é obrigatório.")
        item.name = clean_name
    if is_active is not None:
        item.is_active = is_active

    _validate_extension(photo_file, "photo", ACERVO_3D_PHOTO_EXTENSIONS, "JPG ou PNG")
    if _has_upload(photo_file):
        delete_file(item.photo_url)
        item.photo_url = save_file(photo_file, ACERVO_3D_PHOTO_SUBFOLDER)

    _apply_file_changes(item, model_files or [], remove_file_ids or set())

    audit("edit", "Acervo3DItem", item.id, item.name, "Peça do Acervo 3D editada")
    db.session.commit()
    return item


def _apply_file_changes(
    item: Acervo3DItem, model_files: list[Any], remove_file_ids: set[int]
) -> None:
    """Acrescenta e/ou remove arquivos 3D da peça, garantindo que sobre ao menos um."""
    valid_models = [f for f in model_files if _has_upload(f)]
    for model_file in valid_models:
        _validate_extension(model_file, "files", ACERVO_3D_MODEL_EXTENSIONS, "STL, 3MF ou ZIP")

    to_remove = [f for f in item.files if f.id in remove_file_ids]
    if len(item.files) - len(to_remove) + len(valid_models) < 1:
        raise Impressao3DValidationError(
            "files", "A peça precisa manter pelo menos um arquivo 3D."
        )

    for stale in to_remove:
        delete_file(stale.file_path)
        item.files.remove(stale)

    next_position = max((f.position for f in item.files), default=-1) + 1
    _attach_model_files(item, valid_models, next_position)


def delete_acervo_item(item: Acervo3DItem) -> None:
    """Exclui uma peça do Acervo e seus arquivos do storage.

    Raises:
        Impressao3DValidationError: A peça ainda está vinculada a algum evento — nesse caso o
            caminho correto é inativá-la (`is_active=False`), preservando o histórico.
    """
    linked = Event3DGift.query.filter_by(item_id=item.id).count()
    if linked:
        raise Impressao3DValidationError(
            "id",
            f"Esta peça está vinculada a {linked} evento(s). Inative-a em vez de excluir.",
        )
    name, item_id = item.name, item.id
    delete_file(item.photo_url)
    for model_file in item.files:
        delete_file(model_file.file_path)
    db.session.delete(item)
    audit("delete", "Acervo3DItem", item_id, name, "Peça do Acervo 3D excluída")
    db.session.commit()


# ── Presentes 3D de um evento ────────────────────────────────────────────────


def _parse_quantity(raw: Any) -> int:
    """Converte a quantidade recebida em inteiro ≥ 1."""
    try:
        quantity = int(raw)
    except (TypeError, ValueError):
        raise Impressao3DValidationError("quantity", "Quantidade inválida.") from None
    if quantity < 1 or quantity > MAX_GIFT_QUANTITY:
        raise Impressao3DValidationError(
            "quantity", f"Quantidade deve ficar entre 1 e {MAX_GIFT_QUANTITY}."
        )
    return quantity


def _parse_deadline(raw: Any) -> date | None:
    """Converte `YYYY-MM-DD` (ou vazio) em `date`."""
    if raw in (None, ""):
        return None
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        raise Impressao3DValidationError("deadline_date", "Prazo inválido (use AAAA-MM-DD).") from None


def _validate_status(raw: str) -> str:
    """Garante que o status informado é um dos quatro do ciclo de vida."""
    status = (raw or "").strip().lower()
    if status not in GIFT_3D_STATUSES:
        raise Impressao3DValidationError(
            "status", f"Status inválido (use: {', '.join(GIFT_3D_STATUSES)})."
        )
    return status


def add_event_gift(
    event: CalendarEvent,
    *,
    item_id: Any,
    quantity: Any = 1,
    deadline_date: Any = None,
    notes: str | None = None,
    status: str | None = None,
) -> Event3DGift:
    """Vincula uma peça do Acervo a um evento como Presente 3D.

    Raises:
        Impressao3DValidationError: Peça inexistente/inativa, quantidade ou prazo inválidos.
    """
    item = Acervo3DItem.query.get(item_id) if item_id else None
    if item is None:
        raise Impressao3DValidationError("item_id", "Selecione uma peça do Acervo 3D.")
    if not item.is_active:
        raise Impressao3DValidationError("item_id", "Esta peça está inativa no Acervo.")

    gift = Event3DGift(
        event_id=event.id,
        item_id=item.id,
        quantity=_parse_quantity(quantity),
        deadline_date=_parse_deadline(deadline_date),
        notes=(notes or "").strip() or None,
        status=_validate_status(status) if status else GIFT_3D_STATUS_PENDENTE,
    )
    db.session.add(gift)
    # O evento passou a levar presente: uma dispensa anterior ("este não leva") deixou de valer.
    if event.dispensa_3d is not None:
        db.session.delete(event.dispensa_3d)
    db.session.flush()
    audit(
        "create", "Event3DGift", gift.id, item.name,
        f"Presente 3D '{item.name}' vinculado ao evento #{event.id}",
    )
    db.session.commit()
    return gift


def update_event_gift(
    gift: Event3DGift,
    *,
    status: str | None = None,
    quantity: Any = None,
    deadline_date: Any = ...,
    notes: str | None = None,
    item_id: Any = None,
) -> Event3DGift:
    """Edita um Presente 3D (status, quantidade, prazo, observações ou a peça vinculada).

    `deadline_date` usa `...` (Ellipsis) como sentinela de "não alterar", porque `None` é um
    valor válido (limpar o prazo).
    """
    if status is not None:
        gift.status = _validate_status(status)
    if quantity is not None:
        gift.quantity = _parse_quantity(quantity)
    if deadline_date is not ...:
        gift.deadline_date = _parse_deadline(deadline_date)
    if notes is not None:
        gift.notes = notes.strip() or None
    if item_id is not None:
        item = Acervo3DItem.query.get(item_id)
        if item is None:
            raise Impressao3DValidationError("item_id", "Peça do Acervo não encontrada.")
        gift.item_id = item.id

    audit("edit", "Event3DGift", gift.id, gift.item.name if gift.item else "", "Presente 3D editado")
    db.session.commit()
    return gift


def delete_event_gift(gift: Event3DGift) -> None:
    """Remove o vínculo de um Presente 3D com o evento (a peça do Acervo continua existindo)."""
    gift_id = gift.id
    name = gift.item.name if gift.item else ""
    db.session.delete(gift)
    audit("delete", "Event3DGift", gift_id, name, "Presente 3D removido do evento")
    db.session.commit()


def list_print_queue() -> list[Event3DGift]:
    """Fila de Impressão: presentes ainda não entregues de eventos do tipo SHOW.

    Ordenada por prazo mais apertado primeiro; presentes sem prazo caem para o fim da lista
    (ordenados pela data do evento), porque o painel é operacional e existe para responder "o que
    imprimir primeiro".
    """
    gifts = (
        Event3DGift.query.join(CalendarEvent, Event3DGift.event_id == CalendarEvent.id)
        .options(
            joinedload(Event3DGift.item),
            joinedload(Event3DGift.event)
            .joinedload(CalendarEvent.roles)
            .joinedload(EventRole.talent),
        )
        .filter(
            Event3DGift.status != GIFT_3D_STATUS_ENTREGUE,
            CalendarEvent.event_type == EVENT_TYPE_SHOW,
        )
        .all()
    )
    far_future = date.max
    return sorted(
        gifts,
        key=lambda g: (
            g.deadline_date or far_future,
            g.event.start_at or datetime.max,
            g.id,
        ),
    )


# ── Pendências: SHOW futuro sem presente vinculado (feature 202) ─────────────


def list_pending_events(*, include_dismissed: bool = False) -> list[CalendarEvent]:
    """Eventos SHOW futuros que ainda não têm nenhum presente 3D vinculado.

    É o evento que gera o trabalho: um SHOW novo entrando na agenda vira automaticamente uma
    tarefa de "vincular presente" para o Artista 3D, sem depender de alguém lembrar de cadastrar.

    Só olha para frente (`start_at >= hoje`): show que já aconteceu não tem mais o que imprimir, e
    varrer o histórico inteiro afogaria a fila em centenas de linhas mortas.

    Args:
        include_dismissed: Quando True, inclui também os eventos já marcados como "não leva
            presente" — usado pelo toggle "Mostrar dispensados" da tela.

    Returns:
        Eventos ordenados por data (o mais próximo primeiro).
    """
    today_start = datetime.combine(date.today(), datetime.min.time())
    query = (
        CalendarEvent.query.outerjoin(Event3DGift, Event3DGift.event_id == CalendarEvent.id)
        .outerjoin(Event3DDismissal, Event3DDismissal.event_id == CalendarEvent.id)
        .filter(
            CalendarEvent.event_type == EVENT_TYPE_SHOW,
            CalendarEvent.start_at >= today_start,
            Event3DGift.id.is_(None),
        )
    )
    if not include_dismissed:
        query = query.filter(Event3DDismissal.id.is_(None))
    return query.order_by(CalendarEvent.start_at.asc()).all()


def dismiss_event(event: CalendarEvent, *, dismissed_by: int | None) -> Event3DDismissal:
    """Marca um evento SHOW como "não leva presente 3D", tirando-o da lista de pendências.

    Idempotente: dispensar duas vezes devolve a dispensa existente em vez de duplicar.
    """
    if event.dispensa_3d is not None:
        return event.dispensa_3d
    dismissal = Event3DDismissal(event_id=event.id, dismissed_by=dismissed_by)
    db.session.add(dismissal)
    audit(
        "edit", "CalendarEvent", event.id, event.title,
        "Evento marcado como 'não leva presente 3D'",
    )
    db.session.commit()
    return dismissal


def undismiss_event(event: CalendarEvent) -> None:
    """Desfaz a dispensa, devolvendo o evento à lista de pendências. Idempotente."""
    if event.dispensa_3d is None:
        return
    db.session.delete(event.dispensa_3d)
    audit(
        "edit", "CalendarEvent", event.id, event.title,
        "Dispensa de presente 3D desfeita",
    )
    db.session.commit()


# ── Serialização (fonte única dos payloads JSON do módulo) ───────────────────


def serialize_model_files(item: Acervo3DItem) -> list[dict[str, Any]]:
    """Arquivos 3D da peça em JSON, na ordem de upload."""
    return [
        {
            "id": model_file.id,
            "file_path": model_file.file_path,
            "original_name": model_file.original_name,
            "position": model_file.position,
        }
        for model_file in sorted(item.files, key=lambda f: (f.position, f.id))
    ]


def serialize_acervo_item(item: Acervo3DItem, usage_count: int = 0) -> dict[str, Any]:
    """Peça do Acervo em JSON, com os arquivos 3D e a contagem de usos em eventos."""
    return {
        "id": item.id,
        "name": item.name,
        "photo_url": item.photo_url,
        "files": serialize_model_files(item),
        "is_active": bool(item.is_active),
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "usage_count": usage_count,
    }


def serialize_gift(gift: Event3DGift) -> dict[str, Any]:
    """Presente 3D em JSON, com a peça do Acervo aninhada (nome + foto para a miniatura)."""
    item = gift.item
    return {
        "id": gift.id,
        "event_id": gift.event_id,
        "item_id": gift.item_id,
        "status": gift.status,
        "deadline_date": gift.deadline_date.isoformat() if gift.deadline_date else None,
        "quantity": gift.quantity,
        "notes": gift.notes,
        "item": (
            {
                "id": item.id,
                "name": item.name,
                "photo_url": item.photo_url,
                # Os arquivos vêm junto: da Fila o Artista 3D baixa direto, sem passar pelo Acervo.
                "files": serialize_model_files(item),
                "is_active": bool(item.is_active),
            }
            if item
            else None
        ),
    }


def serialize_form_response(response: FormResponse | None) -> dict[str, Any] | None:
    """Extrato do formulário de pré-contrato para a tela do Artista 3D.

    Normaliza as duas formas históricas de `FormResponse.data` (campos `[chave, rótulo, valor]`
    da feature 123 e os antigos `[rótulo, valor]`) num formato único, e devolve só os campos
    preenchidos — é neles que estão a idade e a quantidade de aniversariantes que definem o que
    imprimir. Campos vazios só poluiriam o painel.
    """
    if response is None:
        return None
    sections: list[dict[str, Any]] = []
    for raw_section in response.data_sections:
        campos = [_normalize_field(campo) for campo in raw_section.get("campos", [])]
        preenchidos = [c for c in campos if c["valor"]]
        if preenchidos:
            sections.append({"secao": raw_section.get("secao") or "", "campos": preenchidos})
    return {
        "id": response.id,
        "form_type": response.form_type,
        "form_type_label": response.form_type_label,
        "contact_name": response.contact_name,
        "contact_phone_display": response.contact_phone_display,
        "event_date": response.event_date.isoformat() if response.event_date else None,
        "created_at": response.created_at.isoformat() if response.created_at else None,
        "sections": sections,
    }


def _normalize_field(campo: Any) -> dict[str, str]:
    """Converte um campo do JSON do formulário em `{chave, rotulo, valor}`."""
    if not isinstance(campo, (list, tuple)):
        return {"chave": "", "rotulo": "", "valor": ""}
    if len(campo) == 3:
        chave, rotulo, valor = campo
    elif len(campo) == 2:
        chave = ""
        rotulo, valor = campo
    else:
        return {"chave": "", "rotulo": "", "valor": ""}
    return {
        "chave": str(chave or ""),
        "rotulo": str(rotulo or ""),
        "valor": str(valor or "").strip(),
    }
