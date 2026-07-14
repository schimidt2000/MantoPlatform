"""Feedback da cliente sobre a experiência com a equipe da Manto (feature 130).

Distinto de ``EventRating`` (avaliação do artista sobre o evento, via portal do talento,
com login): aqui quem avalia é a cliente, sem login, através de um link público específico
do evento. O link usa ``CalendarEvent.feedback_token`` (aleatório, gerado sob demanda pela
comercial na página do evento) em vez do id sequencial, para não ser adivinhável.
"""

from __future__ import annotations

import json
import secrets

from flask import Blueprint, abort, current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from app import db, limiter
from app.constants import RoleName
from app.models import CalendarEvent, ClientFeedback

feedback_bp = Blueprint("feedback", __name__)

POSITIVE_TAGS = [
    "🎭 Atuação Impecável",
    "👗 Figurino Perfeito",
    "🤝 Interação com Convidados",
    "⏰ Pontualidade",
    "✨ Pura Magia",
]

ATTENTION_TAGS = [
    "⏰ Atraso",
    "👗 Figurino",
    "🎭 Atuação / Energia",
    "🗣️ Comunicação",
]

MAX_COMMENT_LENGTH = 2000


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def require_comercial(fn):
    """Restringe o acesso a quem já vê hoje as demais ferramentas comerciais do evento."""
    from functools import wraps

    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not _has_role(RoleName.COMERCIAL, RoleName.SUPERADMIN):
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


def _tags_for_score(score: int) -> list[str]:
    return POSITIVE_TAGS if score == 5 else ATTENTION_TAGS


@feedback_bp.route("/events/<int:event_id>/gerar-link-feedback", methods=["POST"])
@require_comercial
def gerar_link(event_id: int):
    """Gera (se ainda não existir) e devolve a URL pública de avaliação do evento."""
    event = CalendarEvent.query.get_or_404(event_id)
    if not event.feedback_token:
        event.feedback_token = secrets.token_urlsafe(32)
        db.session.commit()
    url = request.url_root.rstrip("/") + f"/avaliar/{event.feedback_token}"
    return jsonify({"url": url})


@feedback_bp.route("/avaliar/<token>", methods=["GET"])
def avaliar(token: str):
    event = CalendarEvent.query.filter_by(feedback_token=token).first()
    if not event:
        return render_template("feedback/invalid.html"), 404
    return render_template(
        "feedback/public.html",
        event=event,
        positive_tags=POSITIVE_TAGS,
        attention_tags=ATTENTION_TAGS,
        submitted=False,
    )


@feedback_bp.route("/avaliar/<token>", methods=["POST"])
@limiter.limit("10 per hour")
def avaliar_submit(token: str):
    event = CalendarEvent.query.filter_by(feedback_token=token).first()
    if not event:
        return render_template("feedback/invalid.html"), 404

    raw_score = (request.form.get("score") or "").strip()
    try:
        score = int(raw_score)
    except ValueError:
        score = 0
    if score < 1 or score > 5:
        return render_template(
            "feedback/public.html",
            event=event,
            positive_tags=POSITIVE_TAGS,
            attention_tags=ATTENTION_TAGS,
            submitted=False,
            error="Selecione uma nota de 1 a 5 estrelas.",
        )

    allowed_tags = set(_tags_for_score(score))
    selected_tags = [t for t in request.form.getlist("tags") if t in allowed_tags]
    comment = (request.form.get("comment") or "").strip()[:MAX_COMMENT_LENGTH]

    try:
        feedback = ClientFeedback(
            event_id=event.id,
            score=score,
            tags=json.dumps(selected_tags) if selected_tags else None,
            comment=comment or None,
        )
        db.session.add(feedback)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Falha ao salvar feedback da cliente (event_id=%s)", event.id
        )
        return render_template(
            "feedback/public.html",
            event=event,
            positive_tags=POSITIVE_TAGS,
            attention_tags=ATTENTION_TAGS,
            submitted=False,
            error="Não foi possível enviar agora. Tente novamente em instantes.",
        )

    return render_template(
        "feedback/public.html",
        event=event,
        positive_tags=POSITIVE_TAGS,
        attention_tags=ATTENTION_TAGS,
        submitted=True,
    )
