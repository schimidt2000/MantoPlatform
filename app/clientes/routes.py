"""Rotas do módulo de Clientes (CRM) — lista, ficha, busca e criação rápida (feature 094).

Restrito aos papéis comerciais (COMERCIAL/FINANCEIRO/SUPERADMIN), coerente com a área de vendas.
Núcleo de negócio em `app/clientes/client_ops.py` (feature 165), reusado também pela API JSON.
"""

from __future__ import annotations

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

from app.clientes import client_ops
from app.constants import RoleName

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


def _client_to_json(client) -> dict:
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
    q = request.args.get("q") or ""
    results = client_ops.search_clients(q)
    return jsonify([_client_to_json(c) for c in results])


# ── Criação rápida (inline no evento) ───────────────────────────────


@clientes_bp.route("/quick-create", methods=["POST"])
@require_vendas
def quick_create():
    """Cria um cliente (nome + telefone) ou reaproveita o existente por telefone. Retorna JSON."""
    try:
        client, reused = client_ops.quick_create_client(
            request.form.get("name") or "",
            request.form.get("phone") or "",
            phone_display=request.form.get("phone"),
            email=request.form.get("email"),
            company=request.form.get("company"),
        )
    except client_ops.ClientValidationError as exc:
        return jsonify({"error": exc.message}), 400
    return jsonify({**_client_to_json(client), "reused": reused})


# ── Lista de clientes ───────────────────────────────────────────────


@clientes_bp.route("/")
@require_vendas
def index():
    """Lista pesquisável de clientes com o número de eventos associados."""
    q = (request.args.get("q") or "").strip()
    clients, counts, total_clients = client_ops.list_clients(q)
    return render_template(
        "clientes/list.html",
        clients=clients,
        counts=counts,
        q=q,
        total_clients=total_clients,
        showing=len(clients),
    )


# ── Avaliações recebidas das clientes (feature 131) ─────────────────


@clientes_bp.route("/avaliacoes")
@require_vendas
def avaliacoes():
    """Resumo do feedback das clientes (feature 130) — filtros de período, nota, card e cliente."""
    period = request.args.get("period", "all").strip().lower()
    from_raw = request.args.get("from", "").strip()
    to_raw = request.args.get("to", "").strip()
    score_raw = request.args.get("score", "").strip()
    score = int(score_raw) if score_raw.isdigit() and 1 <= int(score_raw) <= 5 else None
    tag = request.args.get("tag", "").strip()
    client_id_raw = request.args.get("client_id", "").strip()
    client_id = int(client_id_raw) if client_id_raw.isdigit() else None

    summary = client_ops.summarize_feedback(
        period=period,
        from_raw=from_raw,
        to_raw=to_raw,
        score=score,
        tag=tag,
        client_id=client_id,
    )
    has_filters = bool(period != "all" or score or tag or client_id)

    return render_template(
        "clientes/avaliacoes.html",
        feedbacks=summary.feedbacks,
        total=summary.total,
        avg_overall=summary.avg_overall,
        clients_rated=summary.clients_rated,
        dist=summary.dist,
        dist_max=summary.dist_max,
        attention=summary.attention,
        clients_with_feedback=summary.clients_with_feedback,
        selected_client=summary.selected_client,
        client_id=client_id,
        period=period,
        from_raw=from_raw,
        to_raw=to_raw,
        score=score,
        tag=tag,
        all_tags=client_ops.ALL_FEEDBACK_TAGS,
        has_filters=has_filters,
    )


# ── Ficha do cliente ────────────────────────────────────────────────


@clientes_bp.route("/<int:client_id>")
@require_vendas
def detail(client_id: int):
    """Ficha do cliente: contato, metadados de marketing, eventos associados e totais."""
    client, events, rel_by_event, total_sales = client_ops.get_client_detail(client_id)
    if client is None:
        abort(404)
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
    client, _events, _rel, _total = client_ops.get_client_detail(client_id)
    if client is None:
        abort(404)
    client_ops.update_client_fields(
        client,
        cpf=request.form.get("cpf"),
        cnpj=request.form.get("cnpj"),
        address=request.form.get("address"),
    )
    flash("Dados do cliente atualizados.", "success")
    return redirect(url_for("clientes.detail", client_id=client.id))


# ── Excluir cliente (desvincula eventos com segurança) ──────────────


@clientes_bp.route("/<int:client_id>/delete", methods=["POST"])
@require_vendas
def delete(client_id: int):
    """Exclui um cliente, desvinculando antes os eventos associados (sem referências órfãs)."""
    if not _has_role(RoleName.SUPERADMIN, RoleName.FINANCEIRO):
        abort(403)
    client, _events, _rel, _total = client_ops.get_client_detail(client_id)
    if client is None:
        abort(404)
    client_ops.delete_client(client)
    flash("Cliente excluído. Os eventos associados foram desvinculados.", "success")
    return redirect(url_for("clientes.index"))
