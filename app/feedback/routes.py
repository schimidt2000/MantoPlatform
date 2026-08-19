"""Feedback da cliente sobre a experiência com a equipe da Manto (feature 130).

Distinto de ``EventRating`` (avaliação do artista sobre o evento, via portal do talento,
com login): aqui quem avalia é a cliente, sem login, através de um link público específico
do evento. O link usa ``CalendarEvent.feedback_token`` (aleatório, gerado sob demanda pela
comercial na página do evento) em vez do id sequencial, para não ser adivinhável.
"""

from __future__ import annotations

import json
import secrets

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request
from flask_login import current_user, login_required

from app import db, limiter
from app.constants import RoleName
from app.models import CalendarEvent, ClientFeedback

feedback_bp = Blueprint("feedback", __name__)

# As etiquetas e a regra por nota vivem em `feedback_ops` — é de lá que a API React e o CRM de
# clientes importam. Aqui ficam só como referência para o POST Jinja remanescente, que sai junto
# com este blueprint na fase 5.
from app.feedback.feedback_ops import (  # noqa: E402  — depois do bp por clareza de leitura
    ATTENTION_TAGS,
    MAX_COMMENT_LENGTH,
    POSITIVE_TAGS,
    tags_for_score as _tags_for_score,
)


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


@feedback_bp.route("/events/<int:event_id>/gerar-link-feedback", methods=["POST"])
@require_comercial
def gerar_link(event_id: int):
    """Gera (se ainda não existir) e devolve a URL pública de avaliação do evento."""
    event = CalendarEvent.query.get_or_404(event_id)
    if not event.feedback_token:
        event.feedback_token = secrets.token_urlsafe(32)
        db.session.commit()
    # PUBLIC_BASE_URL, não url_root: atrás do proxy (206) o Host aqui é o do backend.
    base = (current_app.config.get("PUBLIC_BASE_URL") or request.url_root).rstrip("/")
    url = f"{base}/catalogo/avaliar/{event.feedback_token}"
    return jsonify({"url": url})


@feedback_bp.route("/avaliar/<token>", methods=["GET"])
def avaliar(token: str):
    """Manda a cliente para a página React de avaliação, preservando o token.

    Esta rota **não some nunca**. `/avaliar/<token>` é o endereço que a comercial copia e cola no
    WhatsApp desde a feature 130, o token não expira, e não há como recolher um link já enviado —
    então todo link em circulação continua entrando por aqui. O que mudou é o destino: em vez de
    renderizar o Jinja, ela devolve 302 para a página React equivalente (feature 164), que tem
    paridade completa (grava `ClientFeedback`, CTA do Google Review em nota 5 pela mesma função,
    mesmo limite de 10/h).

    Redirect **relativo** de propósito: sai pelo mesmo host público, o browser reentra em
    `frontend/server.js` e `/catalogo/*` cai no bundle da vitrine — que roda com
    `basename="/catalogo"` (`apps/public/src/App.tsx`), daí o caminho ter esse prefixo. Uma URL
    absoluta montada aqui pegaria o Host do serviço backend (o proxy usa `changeOrigin`).

    302 e não 301: o navegador não memoriza, então o destino continua sendo nosso para mudar.
    """
    return redirect(f"/catalogo/avaliar/{token}", code=302)


@feedback_bp.route("/avaliar/<token>", methods=["POST"])
@limiter.limit("10 per hour")
def avaliar_submit(token: str):
    event = CalendarEvent.query.filter_by(feedback_token=token).first()
    if not event:
        return render_template("feedback/invalid.html"), 404

    client_name = (request.form.get("client_name") or "").strip()[:200]
    if not client_name:
        return render_template(
            "feedback/public.html",
            event=event,
            positive_tags=POSITIVE_TAGS,
            attention_tags=ATTENTION_TAGS,
            submitted=False,
            client_name=client_name,
            error="Informe seu nome antes de enviar a avaliação.",
        )

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
            client_name=client_name,
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
            client_name=client_name,
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
            client_name=client_name,
            error="Não foi possível enviar agora. Tente novamente em instantes.",
        )

    # CTA do Google Review em nota 5 — mesma fonte única da API React
    # (app/api/feedback_write.py::google_review_url).
    from app.api.feedback_write import google_review_url

    return render_template(
        "feedback/public.html",
        event=event,
        positive_tags=POSITIVE_TAGS,
        attention_tags=ATTENTION_TAGS,
        submitted=True,
        google_review_url=google_review_url() if score == 5 else None,
    )
