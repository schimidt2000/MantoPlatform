"""Endpoints do agente auditor de marketing (feature 256).

O agente roda FORA do Railway (máquina do dono, via Claude Code) e fala com o ERP só por aqui:

* ``GET  /api/marketing-agent/<token>/context`` — contexto somente leitura da rodada;
* ``POST /api/marketing-agent/<token>/run``     — ingestão idempotente do histórico + reembolso;
* ``POST /api/marketing-agent/<token>/report``  — envia o relatório semanal por e-mail.

Autenticação por token de ambiente (``MARKETING_AGENT_TOKEN``), no molde de ``audit_agent.py``:
token errado ou ausente responde **404**; sem token configurado nenhum pedido é aceito.

Diferente do auditor financeiro, este agente ESCREVE — e só o que ``desempenho_ops`` permite:
histórico de métricas, rodadas/arquivos e o Gasto Extra de Marketing para reembolso.
"""

import logging
import os
from datetime import UTC, date, datetime
from typing import Any

from flask import current_app, jsonify, request
from sqlalchemy import func

from app import db
from app.api import api_bp
from app.api_utils import json_error
from app.marketing import comando_ops, marketing_ops
from app.marketing import desempenho_ops as ops
from app.models import MarketingAgentRun, MarketingPost, User

logger = logging.getLogger(__name__)


def _token_valido(token: str) -> bool:
    """True se o token do path bate com ``MARKETING_AGENT_TOKEN``; sem env, nunca."""
    esperado = current_app.config.get("MARKETING_AGENT_TOKEN") or ""
    return bool(esperado) and token == esperado


def _nao_encontrado() -> Any:
    return jsonify({"error": {"message": "Não encontrado"}}), 404


def _em_desenvolvimento() -> bool:
    """`mode=local` (rodada de teste) só é aceito com o Flask em desenvolvimento."""
    return os.getenv("FLASK_ENV", "") == "development" or bool(current_app.config.get("TESTING"))


def _parse_iso(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(valor)
    except ValueError:
        return None
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


@api_bp.route("/marketing-agent/<token>/context", methods=["GET"])
def api_marketing_agent_context(token: str) -> Any:
    """Contexto do ERP para a rodada (posts, metas, clientes novos, gastos, atribuição)."""
    if not _token_valido(token):
        return _nao_encontrado()
    inicio = _parse_iso(request.args.get("window_start"))
    fim = _parse_iso(request.args.get("window_end"))
    if inicio is None or fim is None or inicio >= fim:
        return json_error("Janela inválida: window_start e window_end em ISO, início antes do fim", 400)
    try:
        contexto = ops.agent_context(inicio, fim, request.args.get("card_holder_email"))
    except PermissionError as exc:
        return json_error(str(exc), 403)
    return jsonify(contexto)


@api_bp.route("/marketing-agent/<token>/run", methods=["POST"])
def api_marketing_agent_run(token: str) -> Any:
    """Ingestão idempotente de uma rodada; mesma `run_id` devolve o resultado guardado."""
    if not _token_valido(token):
        return _nao_encontrado()
    payload = request.get_json(silent=True)
    try:
        resultado = ops.ingest_run(payload if isinstance(payload, dict) else {}, development=_em_desenvolvimento())
    except ops.IngestValidationError as exc:
        db.session.rollback()
        return json_error(exc.message, 400, fields=exc.fields or None)
    except PermissionError as exc:
        db.session.rollback()
        return json_error(str(exc), 403)
    return jsonify(resultado)


# ── Feature 345: o painel de comando ─────────────────────────────────────────
#
# A rotina semanal (skill `marketing-auditor`, conectores Meta/Google) lê o ERP por `GET /comando`,
# grava desempenho por anúncio, sugere licenças, abre pedidos de criativo, registra propostas,
# marca o que executou e escreve o resultado do diário. Nunca decide proposta: isso é do Superadmin.


def _comando_erro(exc: comando_ops.ComandoError) -> Any:
    db.session.rollback()
    extra = {"codigo": exc.codigo} if exc.codigo else {}
    return json_error(exc.message, exc.status, fields={exc.field: exc.message} if exc.field else None, **extra)


def _corpo() -> dict[str, Any]:
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


@api_bp.route("/marketing-agent/<token>/comando", methods=["GET"])
def api_marketing_agent_comando(token: str) -> Any:
    """Contexto da rodada: frentes, temas liberados, cards prontos, propostas e diário a reavaliar."""
    if not _token_valido(token):
        return _nao_encontrado()
    try:
        inicio = date.fromisoformat(request.args.get("start") or "")
        fim = date.fromisoformat(request.args.get("end") or "")
    except ValueError:
        return json_error("Informe start e end em AAAA-MM-DD.", 400)
    if inicio > fim:
        return json_error("start depois de end.", 400)
    return jsonify(comando_ops.contexto_comando(inicio, fim))


@api_bp.route("/marketing-agent/<token>/anuncios", methods=["POST"])
def api_marketing_agent_anuncios(token: str) -> Any:
    """Desempenho por anúncio e dia (upsert idempotente)."""
    if not _token_valido(token):
        return _nao_encontrado()
    try:
        n = comando_ops.ingest_ad_metrics(_corpo().get("items"))
    except comando_ops.ComandoError as exc:
        return _comando_erro(exc)
    return jsonify({"upserted": n})


@api_bp.route("/marketing-agent/<token>/licencas/sugestoes", methods=["POST"])
def api_marketing_agent_sugestoes(token: str) -> Any:
    """Sugestões de origem dos temas — uma pessoa confirma depois."""
    if not _token_valido(token):
        return _nao_encontrado()
    try:
        return jsonify(comando_ops.gravar_sugestoes(_corpo().get("items")))
    except comando_ops.ComandoError as exc:
        return _comando_erro(exc)


@api_bp.route("/marketing-agent/<token>/pedidos", methods=["POST"])
def api_marketing_agent_pedidos(token: str) -> Any:
    """Abre pedidos de criativo no Kanban (tema não liberado é recusado, item a item)."""
    if not _token_valido(token):
        return _nao_encontrado()
    try:
        return jsonify(comando_ops.criar_pedidos(_corpo().get("items")))
    except comando_ops.ComandoError as exc:
        return _comando_erro(exc)


@api_bp.route("/marketing-agent/<token>/posts/<int:post_id>/anuncios", methods=["POST"])
def api_marketing_agent_vincular(token: str, post_id: int) -> Any:
    """Liga ao card o anúncio montado (pausado) a partir dele."""
    if not _token_valido(token):
        return _nao_encontrado()
    post = MarketingPost.query.get(post_id)
    if post is None:
        return json_error("Card não encontrado.", 404)
    corpo = _corpo()
    try:
        comando_ops.vincular_anuncio(post, corpo.get("platform"), corpo.get("ad_id"))
    except comando_ops.ComandoError as exc:
        return _comando_erro(exc)
    except marketing_ops.MarketingValidationError as exc:
        db.session.rollback()
        return json_error(exc.message, exc.status, fields={exc.field: exc.message}, codigo=exc.codigo)
    return jsonify({"ok": True})


@api_bp.route("/marketing-agent/<token>/propostas", methods=["POST"])
def api_marketing_agent_proposta(token: str) -> Any:
    """Registra uma proposta de mudança (sempre pendente, até o Superadmin decidir)."""
    if not _token_valido(token):
        return _nao_encontrado()
    try:
        proposta = comando_ops.criar_proposta(_corpo())
    except comando_ops.ComandoError as exc:
        return _comando_erro(exc)
    return jsonify({"id": proposta.id}), 201


@api_bp.route("/marketing-agent/<token>/propostas/<int:proposta_id>/execucao", methods=["POST"])
def api_marketing_agent_execucao(token: str, proposta_id: int) -> Any:
    """Marca a proposta aprovada como executada (ou falhou); nasce a entrada do diário."""
    if not _token_valido(token):
        return _nao_encontrado()
    corpo = _corpo()
    try:
        entrada = comando_ops.marcar_execucao(proposta_id, resultado=corpo.get("resultado"),
                                              detalhe=corpo.get("detalhe"))
    except comando_ops.ComandoError as exc:
        return _comando_erro(exc)
    return jsonify({"ok": True, "diario_id": entrada.id})


@api_bp.route("/marketing-agent/<token>/diario/<int:entrada_id>/resultado", methods=["POST"])
def api_marketing_agent_diario(token: str, entrada_id: int) -> Any:
    """Grava o resultado observado de uma decisão que chegou na data de reavaliar."""
    if not _token_valido(token):
        return _nao_encontrado()
    corpo = _corpo()
    try:
        comando_ops.gravar_resultado(entrada_id, texto=corpo.get("resultado_observado"),
                                     veredito=corpo.get("veredito"))
    except comando_ops.ComandoError as exc:
        return _comando_erro(exc)
    return jsonify({"ok": True})


@api_bp.route("/marketing-agent/<token>/report", methods=["POST"])
def api_marketing_agent_report(token: str) -> Any:
    """Envia o HTML do relatório aos destinatários (só usuários internos ativos) e marca a rodada."""
    from app.email_service import send_audit_report_email

    if not _token_valido(token):
        return _nao_encontrado()
    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    html = (data.get("html") or "").strip()
    to = data.get("to") or []
    if not subject or not html or not isinstance(to, list) or not to:
        return json_error("Campos obrigatórios: subject, html, to[]", 400)

    pedidos = {e.strip().lower() for e in to if isinstance(e, str)}
    users = User.query.filter(func.lower(User.email).in_(pedidos),
                              User.is_active.is_(True), User.has_access.is_(True)).all()
    recusados = sorted(pedidos - {(u.email or "").lower() for u in users})
    if recusados:
        logger.warning("[marketing] destinatários fora do quadro interno: %s", recusados)

    sent = send_audit_report_email(subject, html, users, preheader="Relatório semanal do auditor de marketing.")
    run = MarketingAgentRun.query.filter_by(run_id=str(data.get("run_id") or "")[:40]).first()
    if run is not None and sent:
        run.report_sent = True
        db.session.commit()
    return jsonify({"sent": sent, "rejected": recusados}), 200
