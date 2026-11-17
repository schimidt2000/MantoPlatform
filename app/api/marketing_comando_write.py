"""Endpoints de ESCRITA do painel de comando de marketing (feature 345).

Gates (função no início da view, Princípio XIII):

* tetos, meta e verba do mês e responsáveis (`PATCH /api/marketing/frentes`) e o calendário do ano
  (`PATCH /api/marketing/calendario`, feature 351) — só `SUPERADMIN` real;
* frente da campanha, licença dos temas e diário — `MARKETING` ou `SUPERADMIN`; liberar um tema
  licenciado é só `SUPERADMIN` (regra no `comando_ops.marcar_licenca`, 403 `so_superadmin`);
* decidir proposta — só `SUPERADMIN` (decisão do dono, 16/11/2026), 403 para os outros.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api.marketing_comando_read import eh_superadmin
from app.api.marketing_read import require_marketing_access
from app.api_utils import api_login_required, json_error
from app.marketing import comando_ops as ops
from app.models import CatalogItem


def _erro(exc: ops.ComandoError) -> Any:
    db.session.rollback()
    extra = {"codigo": exc.codigo} if exc.codigo else {}
    fields = {exc.field: exc.message} if exc.field else None
    return json_error(exc.message, exc.status, fields=fields, **extra)


def _corpo() -> dict[str, Any]:
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


@api_bp.route("/marketing/frentes", methods=["PATCH"])
@api_login_required
def api_marketing_frentes_salvar() -> Any:
    """Tetos (`null` volta ao padrão), meta e verba do mês e responsáveis por foto/vídeo — só Superadmin."""
    if not eh_superadmin(current_user):
        return json_error("Só o Superadmin altera tetos, metas, verbas e responsáveis.", 403)
    corpo = _corpo()
    try:
        ops.salvar_frentes(
            current_user.id,
            tetos_novos=corpo.get("tetos"),
            metas=corpo.get("metas"),
            verbas=corpo.get("verbas"),
            resp_foto_id=corpo["resp_foto_id"] if "resp_foto_id" in corpo else ...,
            resp_video_id=corpo["resp_video_id"] if "resp_video_id" in corpo else ...,
        )
    except ops.ComandoError as exc:
        return _erro(exc)
    return jsonify(ops.frentes_config(eh_superadmin=True))


@api_bp.route("/marketing/campanhas/frente", methods=["PATCH"])
@api_login_required
def api_marketing_campanha_frente() -> Any:
    """Corrige (ou desfaz, com `frente: null`) a frente de uma campanha."""
    denied = require_marketing_access()
    if denied:
        return denied
    corpo = _corpo()
    try:
        ops.corrigir_frente_campanha(
            str(corpo.get("platform") or ""),
            str(corpo.get("campaign_id") or ""),
            corpo.get("frente"),
            current_user.id,
        )
    except ops.ComandoError as exc:
        return _erro(exc)
    return jsonify({"ok": True})


@api_bp.route("/marketing/temas-licenca/confirmar", methods=["POST"])
@api_login_required
def api_marketing_temas_confirmar() -> Any:
    """Aplica a sugestão da rotina nos temas escolhidos (autoral sai liberado; licenciado não)."""
    denied = require_marketing_access()
    if denied:
        return denied
    try:
        n = ops.confirmar_sugestoes(_corpo().get("ids"), user_id=current_user.id)
    except (ops.ComandoError, ValueError, TypeError) as exc:
        return _erro(
            exc
            if isinstance(exc, ops.ComandoError)
            else ops.ComandoError("Lista inválida.", field="ids")
        )
    return jsonify({"confirmados": n})


@api_bp.route("/marketing/temas-licenca/<int:item_id>", methods=["PATCH"])
@api_login_required
def api_marketing_tema_licenca(item_id: int) -> Any:
    """Muda a origem e/ou o liberado de um tema; liberar licenciado só Superadmin (403)."""
    denied = require_marketing_access()
    if denied:
        return denied
    item = CatalogItem.query.get(item_id)
    if item is None:
        return json_error("Tema não encontrado.", 404)
    corpo = _corpo()
    try:
        ops.marcar_licenca(
            item,
            user_id=current_user.id,
            eh_superadmin=eh_superadmin(current_user),
            origem=corpo["licenca_origem"] if "licenca_origem" in corpo else ...,
            liberado=corpo["liberado_anuncio"] if "liberado_anuncio" in corpo else ...,
        )
    except ops.ComandoError as exc:
        return _erro(exc)
    return jsonify(ops.serialize_tema_licenca(item))


@api_bp.route("/marketing/propostas/<int:proposta_id>/decidir", methods=["POST"])
@api_login_required
def api_marketing_proposta_decidir(proposta_id: int) -> Any:
    """Aprova ou recusa uma proposta — só Superadmin; segunda decisão 409 `ja_decidida`."""
    if not eh_superadmin(current_user):
        return json_error("Só o Superadmin aprova ou recusa propostas.", 403)
    corpo = _corpo()
    try:
        proposta = ops.decidir(
            proposta_id, user_id=current_user.id, decisao=corpo.get("decisao"), obs=corpo.get("obs")
        )
    except ops.ComandoError as exc:
        return _erro(exc)
    return jsonify(ops.serialize_proposta(proposta))


@api_bp.route("/marketing/diario", methods=["POST"])
@api_login_required
def api_marketing_diario_criar() -> Any:
    """Entrada escrita à mão no diário de decisões."""
    denied = require_marketing_access()
    if denied:
        return denied
    try:
        entrada = ops.criar_entrada(_corpo(), autor_id=current_user.id)
    except ops.ComandoError as exc:
        return _erro(exc)
    return jsonify(ops.serialize_diario(entrada)), 201


@api_bp.route("/marketing/calendario", methods=["PATCH"])
@api_login_required
def api_marketing_calendario_salvar() -> Any:
    """Meta, verba e foco dos meses enviados de uma frente (feature 351) — só Superadmin real."""
    if not eh_superadmin(current_user):
        return json_error("Só o Superadmin altera o calendário do ano.", 403)
    corpo = _corpo()
    try:
        ops.salvar_calendario(corpo.get("frente"), corpo.get("meses"), user_id=current_user.id)
    except ops.ComandoError as exc:
        return _erro(exc)
    return jsonify(ops.calendario(eh_superadmin=True))
