"""Endpoints de LEITURA da base autorizada (feature 350).

RBAC:
- ``GET /clientes/aniversarios`` e o pós-evento (lista e prévia): Comercial e Superadmin — o dado
  da criança não vai a quem não atende a cliente (LGPD, minimização);
- ``GET /parceiros``: Comercial, Financeiro e Superadmin (o Financeiro vê a comissão declarada);
  ``flags.pode_editar`` diz à tela se mostra os botões.

Gate por função no início da view (constituição XIII); tabela em `docs/01` §4.3.
"""

from __future__ import annotations

from typing import Any

from flask import current_app, jsonify, request
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.clientes import aniversario_ops, parceiro_ops, pos_evento_ops
from app.constants import ANIVERSARIOS_DIAS_MAXIMO, ANIVERSARIOS_DIAS_PADRAO, RoleName, now_sp
from app.conversas.configuracao import cfg_whatsapp
from app.models import CalendarEvent

_EQUIPE_COMERCIAL = {RoleName.COMERCIAL, RoleName.SUPERADMIN}
_LEITORES_DE_PARCEIRO = {RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN}


def _papeis() -> set[str]:
    return {r.name.upper() for r in current_user.roles}


def _negado(permitidos: set[str]) -> Any:
    return None if _papeis() & permitidos else json_error("Sem permissão", 403)


@api_bp.route("/clientes/aniversarios")
@api_login_required
def api_clientes_aniversarios() -> Any:
    """Crianças com aniversário nos próximos ``dias`` (padrão 60), com os dois aceites."""
    negado = _negado(_EQUIPE_COMERCIAL)
    if negado:
        return negado
    dias = request.args.get("dias", type=int) or ANIVERSARIOS_DIAS_PADRAO
    dias = max(1, min(dias, ANIVERSARIOS_DIAS_MAXIMO))
    return jsonify({"items": aniversario_ops.listar(now_sp().date(), dias), "dias": dias})


@api_bp.route("/parceiros")
@api_login_required
def api_parceiros_listar() -> Any:
    """Parceiros (ativos; ``inativos=1`` traz todos), com quantas fichas cada um trouxe."""
    negado = _negado(_LEITORES_DE_PARCEIRO)
    if negado:
        return negado
    incluir = request.args.get("inativos") == "1"
    return jsonify(
        {
            "items": [
                parceiro_ops.serializar(p, n)
                for p, n in parceiro_ops.listar(incluir_inativos=incluir)
            ],
            "tipos": parceiro_ops.tipos(),
            "flags": {"pode_editar": bool(_papeis() & _EQUIPE_COMERCIAL)},
        }
    )


@api_bp.route("/pos-evento")
@api_login_required
def api_pos_evento_lista() -> Any:
    """Eventos dos últimos 7 dias até agora, com a situação do pós-evento e da avaliação."""
    negado = _negado(_EQUIPE_COMERCIAL)
    if negado:
        return negado
    return jsonify({"items": pos_evento_ops.listar_recentes()})


@api_bp.route("/events/<int:event_id>/pos-evento")
@api_login_required
def api_pos_evento_detalhe(event_id: int) -> Any:
    """A prévia do pós-evento (``fotos_url`` opcional na query). Gera o token de avaliação na
    primeira leitura — idempotente, e o mesmo do "Pedir feedback" da 130."""
    negado = _negado(_EQUIPE_COMERCIAL)
    if negado:
        return negado
    event = db.session.get(CalendarEvent, event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    try:
        corpo = pos_evento_ops.detalhe(
            event,
            base_publica=current_app.config.get("PUBLIC_BASE_URL") or "",
            fotos_url=request.args.get("fotos_url"),
            cfg=cfg_whatsapp(),
        )
    except pos_evento_ops.PosEventoErro as exc:
        db.session.rollback()
        campos = {exc.campo: exc.mensagem} if exc.campo else None
        extras = {"codigo": exc.codigo} if exc.codigo else {}
        return json_error(exc.mensagem, exc.status, fields=campos, **extras)
    db.session.commit()  # o token de avaliação, se nasceu agora
    return jsonify(corpo)
