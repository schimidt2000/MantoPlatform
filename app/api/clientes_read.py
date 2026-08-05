"""Endpoints de LEITURA do CRM de Clientes (feature 165, US6 — Cauda Administrativa).

Reusa, sem duplicar, o núcleo já extraído em `app/clientes/client_ops.py` (feature 165) — os
endpoints aqui só validam RBAC e serializam. Gate `require_vendas` reimplementado como função,
paridade com `app/clientes/routes.py::_has_role`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.clientes import client_ops
from app.constants import RoleName


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_vendas() -> Any:
    if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _client_summary(client) -> dict:
    return {
        "id": client.id,
        "name": client.name,
        "phone": client.phone,
        "phone_display": client.phone_display or client.phone,
        "email": client.email or "",
        "company": client.company or "",
    }


@api_bp.route("/clientes/search")
@api_login_required
def api_clientes_search() -> Any:
    """Busca clientes por nome/telefone (sem acentos), para o seletor de cliente do evento."""
    denied = _require_vendas()
    if denied:
        return denied
    results = client_ops.search_clients(request.args.get("q") or "")
    return jsonify([_client_summary(c) for c in results])


@api_bp.route("/clientes/")
@api_login_required
def api_clientes_list() -> Any:
    """Lista de clientes com contagem de eventos associados (feature 165)."""
    denied = _require_vendas()
    if denied:
        return denied
    clients, counts, total_clients = client_ops.list_clients(request.args.get("q") or "")
    items = [{**_client_summary(c), "event_count": counts.get(c.id, 0)} for c in clients]
    return jsonify({"items": items, "total_clients": total_clients})


@api_bp.route("/clientes/<int:client_id>")
@api_login_required
def api_clientes_detail(client_id: int) -> Any:
    """Ficha do cliente: contato, CPF/CNPJ, endereço, eventos associados e total vendido."""
    denied = _require_vendas()
    if denied:
        return denied
    client, events, rel_by_event, total_sales = client_ops.get_client_detail(client_id)
    if client is None:
        return json_error("Cliente não encontrado", 404)
    return jsonify(
        {
            **_client_summary(client),
            "cpf": client.cpf or "",
            "cnpj": client.cnpj or "",
            "address": client.address or "",
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "start_at": e.start_at.isoformat() if e.start_at else None,
                    "relation": rel_by_event.get(e.id, ""),
                }
                for e in events
            ],
            "event_count": len(events),
            "total_sales": float(total_sales),
        }
    )


def _feedback_item(feedback) -> dict:
    """Serializa uma avaliação com o evento e a cliente aninhados (feature 197).

    O relacionamento vem pré-carregado por `client_ops.summarize_feedback` (joinedload), então
    aqui não há consulta extra. `client.full_name` cai para `ClientFeedback.client_name` — o
    nome digitado por quem respondeu (feature 132) — quando o evento não tem cliente vinculada.

    Args:
        feedback: Linha de `ClientFeedback` já carregada.

    Returns:
        Dicionário pronto para `jsonify`, com `event` e `client` aninhados (nulos quando o
        evento foi apagado ou não tem cliente/nome de quem respondeu).
    """
    event = feedback.event
    client = event.client if event else None
    full_name = (client.name if client else "") or (feedback.client_name or "")
    return {
        "id": feedback.id,
        "score": feedback.score,
        "comment": feedback.comment or "",
        "tags": feedback.tags_list,
        "submitted_at": feedback.submitted_at.isoformat() if feedback.submitted_at else None,
        "event": (
            {
                "id": event.id,
                "title": event.title,
                "event_date": event.start_at.isoformat() if event.start_at else None,
            }
            if event
            else None
        ),
        "client": {"id": client.id if client else None, "full_name": full_name} if full_name else None,
    }


@api_bp.route("/clientes/avaliacoes")
@api_login_required
def api_clientes_avaliacoes() -> Any:
    """Resumo do feedback das clientes (feature 130/131), com filtros de período/nota/tag/cliente."""
    denied = _require_vendas()
    if denied:
        return denied

    score_raw = (request.args.get("score") or "").strip()
    score = int(score_raw) if score_raw.isdigit() and 1 <= int(score_raw) <= 5 else None
    client_id_raw = (request.args.get("client_id") or "").strip()
    client_id = int(client_id_raw) if client_id_raw.isdigit() else None
    period = (request.args.get("period") or "all").strip().lower()
    from_raw = (request.args.get("from") or "").strip()
    to_raw = (request.args.get("to") or "").strip()
    tag = (request.args.get("tag") or "").strip()

    summary = client_ops.summarize_feedback(
        period=period,
        from_raw=from_raw,
        to_raw=to_raw,
        score=score,
        tag=tag,
        client_id=client_id,
    )

    return jsonify(
        {
            # Capacidade da UI: só SUPERADMIN exclui avaliações (o servidor decide, o
            # cliente apenas espelha — mesmo padrão de can_edit_structure dos formulários).
            "can_delete": _has_role(RoleName.SUPERADMIN),
            "feedbacks": [_feedback_item(f) for f in summary.feedbacks],
            "kpis": {
                "media_geral": summary.avg_overall,
                "total_avaliacoes": summary.total,
                "percentual_5_estrelas": summary.pct_five,
            },
            "total": summary.total,
            "avg_overall": summary.avg_overall,
            "clients_rated": summary.clients_rated,
            "dist": summary.dist,
            "dist_max": summary.dist_max,
            "attention": [_feedback_item(f) for f in summary.attention],
            "clients_with_feedback": [
                {"id": cid, "name": name} for cid, name in summary.clients_with_feedback
            ],
            "all_tags": client_ops.ALL_FEEDBACK_TAGS,
            "filters": {
                "period": period,
                "from": from_raw,
                "to": to_raw,
                "score": score,
                "tag": tag,
                "client_id": client_id,
            },
        }
    )
