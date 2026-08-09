"""Núcleo de negócio de Avaliações do Portal do Artista (feature 191).

Extraído de `app/talent_portal/routes.py` para virar fonte única (Princípio I) reusada pela view
Jinja legada e pelos endpoints `app/api/portal_ratings.py`. Mantém a semântica já em produção:

* janela de **7 dias** para avaliar um evento terminado (contada do mais recente entre o término
  do evento e a inclusão do talento — feature 085);
* janela de **30 dias** para editar uma avaliação já enviada;
* nota abaixo de 4 exige comentário;
* versionamento da avaliação anterior a cada sessão de edição que muda conteúdo (feature 181).

Funções puras: não importam `flask.request`/`render_template`/`flash`/`session`. O baseline de
versionamento é passado como argumento pela camada de rota (Jinja guarda na sessão; a API manda
o snapshot no corpo do PUT).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_

from app import db
from app.models import (
    CalendarEvent,
    EventRating,
    EventRatingVersion,
    EventRole,
    EventSubRating,
    Talent,
)
from app.talent_portal.portal_ops import now_sp, portal_photo_url

#: Prazo para avaliar um evento depois que ele termina.
RATING_WINDOW = timedelta(days=7)

#: Prazo para editar uma avaliação já enviada.
RATING_EDIT_WINDOW = timedelta(days=30)

#: Nota mínima que dispensa comentário obrigatório.
COMMENT_REQUIRED_BELOW = 4

#: Palavras no título que caracterizam um evento de show (habilita sub-notas de som e texto).
SHOW_KEYWORDS = ("SHOW", "APRESENTAÇÃO", "APRESENTACAO", "ESPETÁCULO", "ESPETACULO")

#: Categorias de sub-avaliação sem pessoa associada, comuns a qualquer evento.
GENERAL_CATEGORIES = ("figurino",)

#: Categorias de sub-avaliação sem pessoa associada, exclusivas de eventos de show.
SHOW_CATEGORIES = ("som", "texto")

#: Categorias de sub-avaliação dirigidas a uma pessoa do elenco/equipe.
PERSON_CATEGORIES = ("artista", "coordenacao", "maquiagem")


class PortalRatingError(Exception):
    """Erro de validação de avaliação (nota fora da faixa, comentário faltando, fora da janela)."""

    def __init__(self, message: str, field: str | None = None, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.status = status


def _not_rejected():
    """Cláusula: escalação cujo convite NÃO foi recusado (aceito, pendente ou sem status)."""
    return or_(EventRole.invite_status.is_(None), EventRole.invite_status != "rejected")


def _event_end_column():
    """Coluna do término efetivo do evento (`end_at`, caindo para `start_at` quando nulo)."""
    return func.coalesce(CalendarEvent.end_at, CalendarEvent.start_at)


def event_ended(event: CalendarEvent | None) -> bool:
    """True se o evento já terminou, no fuso de Brasília."""
    if event is None:
        return False
    event_end = event.end_at or event.start_at
    return bool(event_end and event_end < now_sp())


def is_show_event(event: CalendarEvent) -> bool:
    """True se o título do evento indica um show (habilita as sub-notas de som e texto)."""
    title_upper = (event.title or "").upper()
    return any(keyword in title_upper for keyword in SHOW_KEYWORDS)


def rated_event_ids(talent: Talent) -> set[int]:
    """IDs de eventos que o talento já avaliou, independentemente de janela de tempo."""
    return {r.event_id for r in EventRating.query.filter_by(talent_id=talent.id).all()}


def _event_ids_in_window(talent: Talent, window: timedelta, only: set[int] | None = None) -> set[int]:
    """IDs de eventos terminados em que o talento está escalado, dentro de uma janela.

    A janela conta do mais recente entre o término do evento e a inclusão do talento
    (`assigned_at`), para que quem entra tarde na escalação ganhe o prazo cheio (feature 085).

    Args:
        talent: Talento autenticado.
        window: Duração da janela a partir de agora, para trás.
        only: Se informado, restringe a busca a esses IDs de evento.
    """
    if only is not None and not only:
        return set()

    now = now_sp()
    floor = now - window
    event_end = _event_end_column()

    query = (
        EventRole.query.filter(EventRole.talent_id == talent.id, _not_rejected())
        .join(CalendarEvent)
        .filter(event_end < now, or_(event_end >= floor, EventRole.assigned_at >= floor))
    )
    if only is not None:
        query = query.filter(CalendarEvent.id.in_(only))

    return {r.event_id for r in query.all() if r.event_id}


def rateable_event_ids(talent: Talent) -> set[int]:
    """IDs de eventos que o talento pode avaliar agora e ainda não avaliou."""
    rated = rated_event_ids(talent)
    return {eid for eid in _event_ids_in_window(talent, RATING_WINDOW) if eid not in rated}


def editable_rating_event_ids(talent: Talent) -> set[int]:
    """IDs de eventos já avaliados pelo talento que ainda estão na janela de edição."""
    return _event_ids_in_window(talent, RATING_EDIT_WINDOW, only=rated_event_ids(talent))


def owned_role(talent: Talent, event_id: int) -> EventRole | None:
    """Escalação do talento nesse evento cujo convite não foi recusado, ou `None`."""
    return EventRole.query.filter(
        EventRole.event_id == event_id,
        EventRole.talent_id == talent.id,
        _not_rejected(),
    ).first()


def build_rating_context(talent: Talent, event: CalendarEvent) -> dict[str, Any]:
    """Listas de pessoas avaliáveis do evento, agrupadas por categoria.

    Args:
        talent: Talento que está avaliando (excluído das listas — ninguém se auto-avalia).
        event: Evento avaliado.

    Returns:
        Dict com `artists`, `coordinators`, `makeup` (listas de `EventRole`) e `is_show`.
    """
    artists: list[EventRole] = []
    coordinators: list[EventRole] = []
    makeup: list[EventRole] = []

    for role in event.roles:
        if not role.talent_id or role.talent_id == talent.id or not role.talent:
            continue
        if role.role_type == "character":
            artists.append(role)
        elif role.role_type == "extra":
            name_lower = (role.character_name or "").lower()
            if "coordenador" in name_lower or "coord" in name_lower:
                coordinators.append(role)
            elif "maquiador" in name_lower or "maquiagem" in name_lower or "make" in name_lower:
                makeup.append(role)

    return {
        "artists": artists,
        "coordinators": coordinators,
        "makeup": makeup,
        "is_show": is_show_event(event),
    }


def snapshot_rating(rating: EventRating) -> dict[str, Any]:
    """Fotografia comparável do estado de uma avaliação (nota, comentário e sub-avaliações)."""
    return {
        "score": rating.score,
        "comment": rating.comment,
        "subs": sorted(
            [
                {
                    "category": s.category,
                    "subject_talent_id": s.subject_talent_id,
                    "score": s.score,
                    "comment": s.comment,
                }
                for s in rating.sub_ratings
            ],
            key=lambda d: (d["category"], d["subject_talent_id"] or 0),
        ),
    }


def record_version_if_changed(rating: EventRating, baseline: dict[str, Any] | None) -> bool:
    """Registra o estado anterior de uma avaliação, se ele mudou. Não faz commit.

    Args:
        rating: Avaliação já com o novo conteúdo aplicado (e `flush`ada, se subs mudaram).
        baseline: Snapshot pré-edição, ou `None` quando não é uma edição (primeira avaliação).

    Returns:
        True se uma versão foi registrada.
    """
    if baseline is None or snapshot_rating(rating) == baseline:
        return False

    db.session.add(
        EventRatingVersion(
            rating_id=rating.id,
            snapshot=json.dumps(baseline, ensure_ascii=False),
            replaced_at=datetime.utcnow(),
        )
    )
    rating.edit_count = (rating.edit_count or 0) + 1
    rating.edited_at = datetime.utcnow()
    return True


def _require_open_event(talent: Talent, event_id: int) -> EventRole:
    """Escalação do talento num evento já terminado, pronta para avaliação.

    Raises:
        PortalRatingError: Talento não escalado (404) ou evento ainda não terminou (400).
    """
    role = owned_role(talent, event_id)
    if role is None:
        raise PortalRatingError("Você não está escalado neste evento.", status=404)
    if not event_ended(role.event):
        raise PortalRatingError("A avaliação abre depois que o evento terminar.", status=400)
    return role


def get_rating(talent: Talent, event_id: int) -> EventRating | None:
    """Avaliação já enviada pelo talento para esse evento, ou `None`."""
    return EventRating.query.filter_by(event_id=event_id, talent_id=talent.id).first()


def submit_rating(
    talent: Talent,
    event_id: int,
    score: int,
    comment: str | None,
    baseline: dict[str, Any] | None = None,
) -> EventRating:
    """Cria ou atualiza a nota geral de um evento.

    Args:
        talent: Talento autenticado.
        event_id: Evento avaliado.
        score: Nota de 1 a 5.
        comment: Comentário livre — obrigatório para notas abaixo de 4.
        baseline: Snapshot pré-edição, para versionamento (`None` na primeira avaliação).

    Returns:
        A avaliação persistida.

    Raises:
        PortalRatingError: Nota fora de 1–5, comentário faltando, evento não terminado ou
            talento não escalado.
    """
    _require_open_event(talent, event_id)

    if not isinstance(score, int) or not (1 <= score <= 5):
        raise PortalRatingError("Selecione uma nota de 1 a 5 estrelas.", field="score")

    comment = (comment or "").strip() or None
    if score < COMMENT_REQUIRED_BELOW and not comment:
        raise PortalRatingError(
            "Para notas abaixo de 4 estrelas, deixe um comentário explicando o que aconteceu.",
            field="comment",
        )

    rating = get_rating(talent, event_id)
    if rating is None:
        rating = EventRating(event_id=event_id, talent_id=talent.id, score=score, comment=comment)
        db.session.add(rating)
    else:
        rating.score = score
        rating.comment = comment
        record_version_if_changed(rating, baseline)

    db.session.commit()
    return rating


def _valid_score(raw: Any) -> int | None:
    """Converte uma nota recebida do cliente em `int` 1–5, ou `None` se inválida/ausente."""
    if raw is None or raw == "":
        return None
    try:
        score = int(raw)
    except (TypeError, ValueError):
        return None
    return score if 1 <= score <= 5 else None


def submit_rating_detail(
    talent: Talent,
    event_id: int,
    general: dict[str, Any],
    people: list[dict[str, Any]],
    baseline: dict[str, Any] | None = None,
) -> EventRating:
    """Substitui as sub-avaliações de um evento pela lista enviada.

    Sub-avaliações são reescritas por completo (delete + insert) para que remover uma nota no
    cliente realmente a remova — mesmo comportamento da tela Jinja legada.

    Args:
        talent: Talento autenticado.
        event_id: Evento avaliado.
        general: Notas por categoria geral, ex.: `{"figurino": {"score": 5, "comment": None}}`.
            Categorias fora das permitidas para o tipo de evento são ignoradas.
        people: Notas por pessoa, ex.: `[{"category": "artista", "subject_talent_id": 12,
            "score": 4, "comment": None}]`.
        baseline: Snapshot pré-edição, para versionamento.

    Returns:
        A avaliação com as sub-avaliações atualizadas.

    Raises:
        PortalRatingError: Avaliação geral ainda não enviada, evento não terminado ou talento
            não escalado.
    """
    role = _require_open_event(talent, event_id)
    rating = get_rating(talent, event_id)
    if rating is None:
        raise PortalRatingError("Envie a nota geral do evento antes do detalhamento.", status=400)

    context = build_rating_context(talent, role.event)
    allowed_general = set(GENERAL_CATEGORIES) | (set(SHOW_CATEGORIES) if context["is_show"] else set())
    allowed_people = {
        "artista": {r.talent_id for r in context["artists"]},
        "coordenacao": {r.talent_id for r in context["coordinators"]},
        "maquiagem": {r.talent_id for r in context["makeup"]},
    }

    EventSubRating.query.filter_by(rating_id=rating.id).delete()

    for category, payload in (general or {}).items():
        if category not in allowed_general:
            continue
        score = _valid_score((payload or {}).get("score"))
        if score is None:
            continue
        db.session.add(
            EventSubRating(
                rating_id=rating.id,
                category=category,
                score=score,
                comment=((payload or {}).get("comment") or "").strip() or None,
            )
        )

    for entry in people or []:
        category = (entry or {}).get("category")
        subject_id = (entry or {}).get("subject_talent_id")
        if category not in allowed_people or subject_id not in allowed_people.get(category, set()):
            continue
        score = _valid_score(entry.get("score"))
        if score is None:
            continue
        db.session.add(
            EventSubRating(
                rating_id=rating.id,
                category=category,
                subject_talent_id=subject_id,
                score=score,
                comment=(entry.get("comment") or "").strip() or None,
            )
        )

    rating.detail_submitted_at = datetime.utcnow()
    db.session.flush()
    db.session.refresh(rating)
    record_version_if_changed(rating, baseline)
    db.session.commit()
    return rating


def _person_entry(role: EventRole) -> dict[str, Any]:
    """Serializa uma pessoa avaliável (talento escalado) para o cliente."""
    return {
        "talent_id": role.talent_id,
        "name": role.talent.artistic_name or role.talent.full_name,
        "character_name": role.character_name,
        "photo_face_url": portal_photo_url(role.talent.photo_face_path),
    }


def serialize_rating_form(talent: Talent, event_id: int) -> dict[str, Any]:
    """Monta tudo que a tela de avaliação precisa: evento, nota existente e pessoas avaliáveis.

    Args:
        talent: Talento autenticado.
        event_id: Evento avaliado.

    Returns:
        Dict serializável com `event`, `rating` (ou `None`), `is_show`, `general_categories`,
        `people` e `can_edit`.

    Raises:
        PortalRatingError: Talento não escalado ou evento ainda não terminou.
    """
    role = _require_open_event(talent, event_id)
    event = role.event
    context = build_rating_context(talent, event)
    rating = get_rating(talent, event_id)

    people = [
        {**_person_entry(r), "category": category}
        for category, roles in (
            ("artista", context["artists"]),
            ("coordenacao", context["coordinators"]),
            ("maquiagem", context["makeup"]),
        )
        for r in roles
    ]

    general_categories = list(GENERAL_CATEGORIES) + (
        list(SHOW_CATEGORIES) if context["is_show"] else []
    )

    return {
        "event": {
            "id": event.id,
            "title": event.title,
            "start_at": event.start_at.isoformat() if event.start_at else None,
            "end_at": event.end_at.isoformat() if event.end_at else None,
            "location": event.location,
        },
        "is_show": context["is_show"],
        "general_categories": general_categories,
        "people": people,
        "can_edit": event_id in editable_rating_event_ids(talent) or rating is None,
        "rating": None
        if rating is None
        else {
            "score": rating.score,
            "comment": rating.comment,
            "submitted_at": rating.submitted_at.isoformat() if rating.submitted_at else None,
            "detail_submitted_at": (
                rating.detail_submitted_at.isoformat() if rating.detail_submitted_at else None
            ),
            "subs": snapshot_rating(rating)["subs"],
        },
    }
