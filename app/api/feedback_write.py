"""Endpoints do feedback público por token em React (feature 164, 4ª e última fatia da US5).

Reaproveita por import direto as constantes/regra de filtro de etiqueta já existentes em
`app/feedback/routes.py` (feature 130). Público (sem `@login_required`/RBAC), mesma
acessibilidade da rota `/avaliar/<token>` hoje. A rota Jinja segue no ar em paralelo; a geração
do link (`gerar_link`, autenticada) não é tocada (ver
`specs/164-feedback-publico-react/plan.md`).
"""

import json
from typing import Any

from flask import jsonify, request

from app import db, limiter
from app.api import api_bp
from app.api_utils import json_error
from app.feedback.routes import ATTENTION_TAGS, POSITIVE_TAGS, _tags_for_score
from app.models import CalendarEvent, ClientFeedback, SiteSetting

# Fallback do link de review no Google quando `SiteSetting.google_review_url` está vazio.
DEFAULT_GOOGLE_REVIEW_URL = "https://g.page/r/CUZ_o_N-Ywq8EAE/review"


def _event_by_token(token: str) -> CalendarEvent | None:
    return CalendarEvent.query.filter_by(feedback_token=token).first()


def google_review_url() -> str:
    """Link de avaliação no Google mostrado após um feedback 5 estrelas.

    Configurável em `SiteSetting.google_review_url` (Admin → Configurações); vazio cai no
    default. Compartilhado com a rota Jinja legada (`app/feedback/routes.py`).
    """
    settings = SiteSetting.query.get(1)
    configured = (settings.google_review_url or "").strip() if settings else ""
    # Cinto-e-suspensório da validação de gravação (config_ops): o valor vira href em página
    # pública — só http(s) sai daqui.
    if configured.lower().startswith(("http://", "https://")):
        return configured
    return DEFAULT_GOOGLE_REVIEW_URL


@api_bp.route("/avaliar/<token>")
def api_feedback_event(token: str) -> Any:
    """Dados do evento associado ao token (paridade com `feedback_bp.avaliar`)."""
    event = _event_by_token(token)
    if not event:
        return json_error("Link não encontrado", 404)

    return jsonify(
        {
            "event_title": event.title,
            "event_date": event.start_at.strftime("%d/%m/%Y") if event.start_at else None,
            "positive_tags": POSITIVE_TAGS,
            "attention_tags": ATTENTION_TAGS,
            # CTA pós-envio: a tela de agradecimento mostra este link quando score == 5.
            "google_review_url": google_review_url(),
        }
    )


@api_bp.route("/avaliar/<token>", methods=["POST"])
@limiter.limit("10 per hour")
def api_feedback_submit(token: str) -> Any:
    """Recebe a avaliação da cliente (paridade com `feedback_bp.avaliar_submit`)."""
    event = _event_by_token(token)
    if not event:
        return json_error("Link não encontrado", 404)

    body = request.get_json(silent=True) or {}
    client_name = (body.get("client_name") or "").strip()[:200]
    if not client_name:
        return json_error(
            "Informe seu nome antes de enviar a avaliação.", 400, fields={"client_name": "Obrigatório"}
        )

    raw_score = body.get("score")
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        score = 0
    if score < 1 or score > 5:
        return json_error(
            "Selecione uma nota de 1 a 5 estrelas.", 400, fields={"score": "Escolha de 1 a 5"}
        )

    allowed_tags = set(_tags_for_score(score))
    raw_tags = body.get("tags") or []
    selected_tags = [t for t in raw_tags if t in allowed_tags]
    comment = (body.get("comment") or "").strip()[:2000]

    feedback = ClientFeedback(
        event_id=event.id,
        score=score,
        tags=json.dumps(selected_tags) if selected_tags else None,
        comment=comment or None,
        client_name=client_name,
    )
    db.session.add(feedback)
    db.session.commit()
    return jsonify({"ok": True}), 201
