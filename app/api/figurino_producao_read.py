"""Endpoints de LEITURA da Produção de Figurinos (feature 225).

Camada fina: valida sessão, chama `app.figurino.producao_ops` e serializa. Nenhuma regra de
negócio mora aqui.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import (
    FIGURINO_KIND_LABELS,
    FIGURINO_KINDS,
    FIGURINO_PROD_ABERTOS,
    FIGURINO_PROD_LABELS,
    FIGURINO_PROD_STATUSES,
    FIGURINO_SEV_LABELS,
    RoleName,
)
from app.figurino import producao_ops as ops
from app.models import FigurinoProducao, User


def require_producao_access() -> Any | None:
    """Leitura é aberta à equipe interna: quem abre pedido precisa acompanhar o próprio pedido."""
    if not ops.pode_abrir(current_user):
        return json_error("Sem permissão", 403)
    return None


def _flags() -> dict[str, bool]:
    """Permissões que a tela usa para decidir o que desenhar."""
    return {
        "can_execute": ops.pode_executar(current_user),
        "can_approve": ops.pode_aprovar(current_user),
        "can_create": ops.pode_abrir(current_user),
    }


@api_bp.route("/figurino/producoes", methods=["GET"])
@api_login_required
def api_figurino_producoes_list() -> Any:
    """Fila da oficina. Filtros: `status`, `abertos`, `responsavel`, `evento`, `busca`."""
    denied = require_producao_access()
    if denied:
        return denied

    status = (request.args.get("status") or "").strip() or None
    if status and status not in FIGURINO_PROD_STATUSES:
        return json_error("Situação desconhecida.", 400, fields={"status": "Valor inválido"})

    kind = (request.args.get("tipo") or "").strip() or None
    if kind and kind not in FIGURINO_KINDS:
        return json_error("Tipo desconhecido.", 400, fields={"tipo": "Valor inválido"})

    responsavel = request.args.get("responsavel")
    evento = request.args.get("evento")
    ficha = request.args.get("ficha")
    itens = ops.list_producoes(
        status=status,
        kind=kind,
        somente_abertos=request.args.get("abertos", "").lower() in ("1", "true"),
        responsible_id=int(responsavel) if responsavel and responsavel.isdigit() else None,
        event_id=int(evento) if evento and evento.isdigit() else None,
        figurino_sheet_id=int(ficha) if ficha and ficha.isdigit() else None,
        busca=request.args.get("busca") or None,
    )
    return jsonify({
        "items": [ops.serialize_producao(p) for p in itens],
        "status_labels": FIGURINO_PROD_LABELS,
        "status_abertos": FIGURINO_PROD_ABERTOS,
        "kind_labels": FIGURINO_KIND_LABELS,
        "severity_labels": FIGURINO_SEV_LABELS,
        "flags": _flags(),
    })


@api_bp.route("/figurino/producoes/<int:producao_id>", methods=["GET"])
@api_login_required
def api_figurino_producao_detail(producao_id: int) -> Any:
    """Detalhe do pedido, com anexos, histórico e gastos vinculados."""
    denied = require_producao_access()
    if denied:
        return denied

    producao = FigurinoProducao.query.get(producao_id)
    if not producao:
        return json_error("Pedido não encontrado.", 404)

    return jsonify({
        "producao": ops.serialize_producao(producao, detalhado=True),
        "flags": _flags(),
        # O servidor manda para onde o pedido pode ir: as transições dependem do TIPO
        # (manutenção não passa por aprovação) e a tela não pode reimplementar essa regra.
        "transicoes": sorted(ops.transicoes_de(producao)),
        "status_labels": FIGURINO_PROD_LABELS,
        "severity_labels": FIGURINO_SEV_LABELS,
    })


@api_bp.route("/figurino/producoes/<int:producao_id>/gastos-vinculaveis", methods=["GET"])
@api_login_required
def api_figurino_producao_gastos_vinculaveis(producao_id: int) -> Any:
    """Gastos extras que fazem sentido oferecer para vincular a este pedido (FR-032)."""
    denied = require_producao_access()
    if denied:
        return denied

    producao = FigurinoProducao.query.get(producao_id)
    if not producao:
        return json_error("Pedido não encontrado.", 404)

    return jsonify({
        "items": [
            {
                "id": g.id,
                "description": g.description,
                "amount": float(g.amount or 0),
                "status": g.status,
                "expense_date": g.expense_date.isoformat() if g.expense_date else None,
                "event_title": g.event.title if g.event else None,
                "ja_vinculado": g.figurino_producao_id == producao.id,
            }
            for g in ops.gastos_vinculaveis(producao)
        ]
    })


@api_bp.route("/figurino/producoes/responsaveis", methods=["GET"])
@api_login_required
def api_figurino_producao_responsaveis() -> Any:
    """Quem pode ser designado responsável: equipe de figurino e super admins."""
    denied = require_producao_access()
    if denied:
        return denied

    usuarios = (
        User.query.filter(User.is_active.is_(True))
        .order_by(User.name.asc())
        .all()
    )
    elegiveis = [
        u for u in usuarios
        if any(r.name in (RoleName.FIGURINO, RoleName.SUPERADMIN) for r in u.roles)
    ]
    return jsonify({
        "items": [
            {"id": u.id, "name": u.name, "email": u.email, "tem_email": bool(u.email)}
            for u in elegiveis
        ]
    })
