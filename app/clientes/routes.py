"""Rotas do módulo de Clientes (CRM) — lista, ficha, busca e criação rápida (feature 094).

Restrito aos papéis comerciais (COMERCIAL/FINANCEIRO/SUPERADMIN), coerente com a área de vendas.
"""

from __future__ import annotations

from decimal import Decimal
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, nullslast, or_

from app import db
from app.clientes.importer import normalize_phone
from app.constants import RoleName
from app.feedback.routes import ATTENTION_TAGS, POSITIVE_TAGS
from app.models import CalendarEvent, Client, ClientFeedback, EventClient
from app.talents.routes import _parse_period

clientes_bp = Blueprint("clientes", __name__, url_prefix="/clientes")


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def require_vendas(fn):
    """Restringe o acesso aos papéis comerciais (COMERCIAL/FINANCEIRO/SUPERADMIN)."""

    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


def _client_to_json(client: Client) -> dict:
    """Serializa um cliente para o autocomplete do evento."""
    return {
        "id": client.id,
        "name": client.name,
        "phone": client.phone,
        "phone_display": client.phone_display or client.phone,
        "company": client.company or "",
    }


# ── Busca (autocomplete usado na página do evento) ──────────────────


@clientes_bp.route("/search")
@require_vendas
def search():
    """Busca clientes por nome ou telefone (JSON), para o seletor no evento."""
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    # Busca sem acentos (feature 114): normaliza o termo e a coluna dos dois lados.
    from app.utils import strip_accents_lower, unaccent_lower_sql
    like = f"%{strip_accents_lower(q)}%"
    digits = "".join(c for c in q if c.isdigit())
    conditions = [unaccent_lower_sql(Client.name).like(like)]
    if digits:
        conditions.append(Client.phone.ilike(f"%{digits}%"))
    results = Client.query.filter(or_(*conditions)).order_by(Client.name.asc()).limit(10).all()
    return jsonify([_client_to_json(c) for c in results])


# ── Criação rápida (inline no evento) ───────────────────────────────


@clientes_bp.route("/quick-create", methods=["POST"])
@require_vendas
def quick_create():
    """Cria um cliente (nome + telefone) ou reaproveita o existente por telefone. Retorna JSON."""
    name = (request.form.get("name") or "").strip()
    phone = normalize_phone(request.form.get("phone"))
    if not name:
        return jsonify({"error": "Informe o nome do cliente."}), 400
    if not phone:
        return jsonify({"error": "Telefone inválido. Inclua DDD (e DDI se houver)."}), 400

    existing = Client.query.filter_by(phone=phone).first()
    if existing:
        # Reaproveita: telefone é a chave única (FR-008).
        return jsonify({**_client_to_json(existing), "reused": True})

    client = Client(
        name=name[:200],
        phone=phone,
        source="manual",
        phone_display=(request.form.get("phone") or "").strip()[:30] or None,
        email=(request.form.get("email") or "").strip()[:200] or None,
        company=(request.form.get("company") or "").strip()[:200] or None,
    )
    db.session.add(client)
    db.session.commit()
    return jsonify({**_client_to_json(client), "reused": False})


# ── Lista de clientes ───────────────────────────────────────────────


@clientes_bp.route("/")
@require_vendas
def index():
    """Lista pesquisável de clientes com o número de eventos associados."""
    q = (request.args.get("q") or "").strip()
    # nº de eventos por cliente via a associação (feature 100), distinto por evento.
    counts = dict(
        db.session.query(EventClient.client_id, func.count(func.distinct(EventClient.event_id)))
        .group_by(EventClient.client_id)
        .all()
    )
    query = Client.query
    if q:
        # Busca sem acentos (feature 114) — mesma regra do autocomplete do evento.
        from app.utils import strip_accents_lower, unaccent_lower_sql
        like = f"%{strip_accents_lower(q)}%"
        digits = "".join(c for c in q if c.isdigit())
        conditions = [unaccent_lower_sql(Client.name).like(like)]
        if digits:
            conditions.append(Client.phone.ilike(f"%{digits}%"))
        query = query.filter(or_(*conditions))
    # ordena por nº de eventos (desc) e depois nome
    clients = query.order_by(Client.name.asc()).limit(300).all()
    clients.sort(key=lambda c: (-counts.get(c.id, 0), c.name.lower()))
    total_clients = Client.query.count()
    return render_template(
        "clientes/list.html",
        clients=clients,
        counts=counts,
        q=q,
        total_clients=total_clients,
        showing=len(clients),
    )


# ── Avaliações recebidas das clientes (feature 131) ─────────────────


ALL_FEEDBACK_TAGS = POSITIVE_TAGS + ATTENTION_TAGS


@clientes_bp.route("/avaliacoes")
@require_vendas
def avaliacoes():
    """Resumo do feedback das clientes (feature 130) — filtros de período, nota, card e cliente.

    Mesmo padrão de filtros de ``talents.avaliacoes`` (chips de período reaproveitando
    ``_parse_period``), adaptado ao que ``ClientFeedback`` de fato tem: sem categorias
    com nota própria (usa cards/tags) e sem múltiplos avaliadores por evento com função.
    """
    period = request.args.get("period", "all").strip().lower()
    if period not in ("30d", "90d", "365d", "custom", "all"):
        period = "all"
    from_raw = request.args.get("from", "").strip()
    to_raw = request.args.get("to", "").strip()
    period_start, period_end = _parse_period(period, from_raw, to_raw)

    score_raw = request.args.get("score", "").strip()
    score = int(score_raw) if score_raw.isdigit() and 1 <= int(score_raw) <= 5 else None

    tag = request.args.get("tag", "").strip()
    if tag not in ALL_FEEDBACK_TAGS:
        tag = ""

    client_id_raw = request.args.get("client_id", "").strip()
    client_id = int(client_id_raw) if client_id_raw.isdigit() else None
    selected_client = Client.query.get(client_id) if client_id else None

    fb_query = ClientFeedback.query.join(CalendarEvent, ClientFeedback.event_id == CalendarEvent.id)
    if period_start:
        fb_query = fb_query.filter(ClientFeedback.submitted_at >= period_start)
    if period_end:
        fb_query = fb_query.filter(ClientFeedback.submitted_at < period_end)
    if score:
        fb_query = fb_query.filter(ClientFeedback.score == score)
    if tag:
        fb_query = fb_query.filter(ClientFeedback.tags.ilike(f'%"{tag}"%'))
    if client_id:
        fb_query = fb_query.filter(CalendarEvent.client_id == client_id)
    feedbacks = fb_query.order_by(ClientFeedback.submitted_at.desc()).all()

    total = len(feedbacks)
    avg_overall = round(sum(f.score for f in feedbacks) / total, 1) if total else 0.0
    clients_rated = len({f.event.client_id for f in feedbacks if f.event and f.event.client_id})

    dist = {s: 0 for s in range(1, 6)}
    for f in feedbacks:
        if 1 <= f.score <= 5:
            dist[f.score] += 1
    dist_max = max(dist.values()) if dist else 0

    attention = [f for f in feedbacks if f.score <= 2][:10]

    clients_with_feedback = (
        db.session.query(Client.id, Client.name)
        .join(CalendarEvent, CalendarEvent.client_id == Client.id)
        .join(ClientFeedback, ClientFeedback.event_id == CalendarEvent.id)
        .distinct()
        .order_by(Client.name.asc())
        .all()
    )

    has_filters = bool(period != "all" or score or tag or client_id)

    return render_template(
        "clientes/avaliacoes.html",
        feedbacks=feedbacks,
        total=total,
        avg_overall=avg_overall,
        clients_rated=clients_rated,
        dist=dist,
        dist_max=dist_max,
        attention=attention,
        clients_with_feedback=clients_with_feedback,
        selected_client=selected_client,
        client_id=client_id,
        period=period,
        from_raw=from_raw,
        to_raw=to_raw,
        score=score,
        tag=tag,
        all_tags=ALL_FEEDBACK_TAGS,
        has_filters=has_filters,
    )


# ── Ficha do cliente ────────────────────────────────────────────────


@clientes_bp.route("/<int:client_id>")
@require_vendas
def detail(client_id: int):
    """Ficha do cliente: contato, metadados de marketing, eventos associados e totais."""
    client = Client.query.get_or_404(client_id)
    # Eventos do cliente via a associação (feature 100); guarda a relação do cliente em cada evento.
    assocs = (
        EventClient.query.filter_by(client_id=client.id)
        .join(CalendarEvent)
        .order_by(nullslast(CalendarEvent.start_at.desc()))
        .all()
    )
    seen: set[int] = set()
    events = []
    rel_by_event: dict[int, str] = {}
    for a in assocs:
        if a.event_id in seen or not a.event:
            continue
        seen.add(a.event_id)
        events.append(a.event)
        rel_by_event[a.event_id] = a.relationship_type
    total_sales = sum((Decimal(e.sale_value) for e in events if e.sale_value), Decimal("0"))
    return render_template(
        "clientes/detail.html",
        client=client,
        events=events,
        rel_by_event=rel_by_event,
        event_count=len(events),
        total_sales=total_sales,
    )


# ── Editar dados (CPF/CNPJ/endereço) ────────────────────────────────


@clientes_bp.route("/<int:client_id>/update", methods=["POST"])
@require_vendas
def update(client_id: int):
    """Atualiza CPF/CNPJ e endereço do cliente (edição manual, feature 119)."""
    client = Client.query.get_or_404(client_id)
    client.cpf = (request.form.get("cpf") or "").strip()[:20] or None
    client.cnpj = (request.form.get("cnpj") or "").strip()[:20] or None
    client.address = (request.form.get("address") or "").strip() or None
    db.session.commit()
    flash("Dados do cliente atualizados.", "success")
    return redirect(url_for("clientes.detail", client_id=client.id))


# ── Excluir cliente (desvincula eventos com segurança) ──────────────


@clientes_bp.route("/<int:client_id>/delete", methods=["POST"])
@require_vendas
def delete(client_id: int):
    """Exclui um cliente, desvinculando antes os eventos associados (sem referências órfãs)."""
    if not _has_role(RoleName.SUPERADMIN, RoleName.FINANCEIRO):
        abort(403)
    client = Client.query.get_or_404(client_id)
    # Remove as associações (feature 100) e limpa o client_id denormalizado que apontava p/ este cliente.
    EventClient.query.filter_by(client_id=client.id).delete()
    CalendarEvent.query.filter_by(client_id=client.id).update({"client_id": None})
    db.session.delete(client)
    db.session.commit()
    flash("Cliente excluído. Os eventos associados foram desvinculados.", "success")
    return redirect(url_for("clientes.index"))
