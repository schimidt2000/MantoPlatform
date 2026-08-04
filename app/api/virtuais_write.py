"""Endpoints de ESCRITA da Loja de Interações Virtuais (feature 205).

CRUD de campanha (multipart — a capa é upload), publicação, acervo liberado e estoque de horários.
Reusa, sem duplicar, ``app.marketing.virtuais_ops``. Gate: ``COMERCIAL`` ou ``SUPERADMIN``.

As rotas não fazem regra de negócio (Princípio III): validam permissão, chamam o núcleo e traduzem
``VirtuaisValidationError`` no envelope de erro com o campo culpado, que é o que permite ao React
destacar o campo exato (Princípio V).
"""

from typing import Any

from flask import current_app, jsonify, request
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api.virtuais_read import require_producao_access, require_virtuais_access
from app.api_utils import api_login_required, json_error
from app.constants import VIRTUAL_REFUND_STATUS_CONCLUIDA, now_sp
from app.marketing import virtuais_ops as ops
from app.models import (
    VirtualCampaign,
    VirtualCampaignSlot,
    VirtualMediaDelivery,
    VirtualOrder,
    VirtualRefundRequest,
)
from app.storage import save_file
from app.utils import audit

CAMPAIGN_COVER_SUBFOLDER = "virtual_covers"
COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _payload() -> dict[str, Any]:
    """Campos da requisição, aceitando JSON e multipart (a capa vem em multipart)."""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def _cover_url() -> str | None:
    """Salva a capa enviada e devolve a URL, ou ``None`` se não veio arquivo."""
    cover = request.files.get("cover")
    if not cover or not cover.filename:
        return None
    import os

    ext = os.path.splitext(cover.filename)[1].lower()
    if ext not in COVER_EXTENSIONS:
        raise ops.VirtuaisValidationError(
            "cover", f"Formato de capa não suportado (use JPG, PNG ou WEBP): {cover.filename}"
        )
    return save_file(cover, CAMPAIGN_COVER_SUBFOLDER)


@api_bp.route("/virtuais/campanhas", methods=["POST"])
@api_login_required
def api_virtuais_campanha_create() -> Any:
    """Cria uma campanha virtual (nasce em rascunho, FR-001)."""
    denied = require_virtuais_access()
    if denied:
        return denied
    data = _payload()
    try:
        campaign = ops.criar_campanha(
            catalog_character_id=data.get("catalog_character_id"),
            title=data.get("title", ""),
            price_live=data.get("price_live"),
            price_recorded=data.get("price_recorded"),
            price_gift=data.get("price_gift", 0),
            recorded_capacity=data.get("recorded_capacity", 0),
            recorded_delivery_days=data.get("recorded_delivery_days", 7),
            intro_html=data.get("intro_html"),
            tolerance_terms=data.get("tolerance_terms"),
            faq=data.get("faq"),
            cover_url=_cover_url(),
            whatsapp_phone=data.get("whatsapp_phone"),
            talent_id=data.get("talent_id"),
            figurino_sheet_id=data.get("figurino_sheet_id"),
        )
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_campaign_admin(campaign)), 201


@api_bp.route("/virtuais/campanhas/<int:campaign_id>", methods=["PATCH"])
@api_login_required
def api_virtuais_campanha_update(campaign_id: int) -> Any:
    """Edita textos, preços, capacidade, prazo e limites de uma campanha."""
    denied = require_virtuais_access()
    if denied:
        return denied
    campaign = VirtualCampaign.query.get(campaign_id)
    if campaign is None:
        return json_error("Campanha não encontrada", 404)

    data = _payload()
    try:
        cover = _cover_url()
        if cover:
            data["cover_url"] = cover
        ops.atualizar_campanha(campaign, **data)
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_campaign_admin(campaign))


@api_bp.route("/virtuais/campanhas/<int:campaign_id>/publicar", methods=["POST"])
@api_login_required
def api_virtuais_campanha_status(campaign_id: int) -> Any:
    """Publica, pausa ou devolve a campanha para rascunho (FR-007)."""
    denied = require_virtuais_access()
    if denied:
        return denied
    campaign = VirtualCampaign.query.get(campaign_id)
    if campaign is None:
        return json_error("Campanha não encontrada", 404)

    data = request.get_json(silent=True) or {}
    try:
        ops.alterar_status(campaign, data.get("status", ""))
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_campaign_admin(campaign))


@api_bp.route("/virtuais/campanhas/<int:campaign_id>/acervo", methods=["PUT"])
@api_login_required
def api_virtuais_campanha_acervo(campaign_id: int) -> Any:
    """Define as peças do Acervo 3D liberadas para a campanha (FR-006)."""
    denied = require_virtuais_access()
    if denied:
        return denied
    campaign = VirtualCampaign.query.get(campaign_id)
    if campaign is None:
        return json_error("Campanha não encontrada", 404)

    data = request.get_json(silent=True) or {}
    try:
        ops.definir_acervo_liberado(campaign, data.get("item_ids", []))
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_campaign_admin(campaign))


@api_bp.route("/virtuais/campanhas/<int:campaign_id>/horarios", methods=["POST"])
@api_login_required
def api_virtuais_gerar_horarios(campaign_id: int) -> Any:
    """Gera o estoque de horários de 10 minutos de uma janela (FR-004).

    Idempotente: reexecutar a mesma janela devolve tudo em ``skipped``.
    """
    denied = require_virtuais_access()
    if denied:
        return denied
    campaign = VirtualCampaign.query.get(campaign_id)
    if campaign is None:
        return json_error("Campanha não encontrada", 404)

    data = request.get_json(silent=True) or {}
    try:
        result = ops.gerar_slots(
            campaign, day=data.get("date"), start=data.get("start"), end=data.get("end")
        )
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(result), 201


@api_bp.route("/virtuais/producao/<int:delivery_id>", methods=["PATCH"])
@api_login_required
def api_virtuais_producao_status(delivery_id: int) -> Any:
    """Move a entrega pelo fluxo `pendente` → `gravando` → `finalizado` (FR-047, FR-048a)."""
    denied = require_producao_access()
    if denied:
        return denied
    delivery = VirtualMediaDelivery.query.get(delivery_id)
    if delivery is None:
        return json_error("Entrega não encontrada", 404)
    data = request.get_json(silent=True) or {}
    try:
        ops.atualizar_status_entrega(delivery, data.get("status", ""), user_id=current_user.id)
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_delivery(delivery))


@api_bp.route("/virtuais/producao/<int:delivery_id>/video", methods=["POST"])
@api_login_required
def api_virtuais_producao_video(delivery_id: int) -> Any:
    """Recebe o vídeo gravado, finaliza a entrega e avisa a família (FR-038a/b, FR-039).

    Falha ao guardar → a entrega **não** finaliza e a família **não** é avisada (FR-038c).
    """
    denied = require_producao_access()
    if denied:
        return denied
    delivery = VirtualMediaDelivery.query.get(delivery_id)
    if delivery is None:
        return json_error("Entrega não encontrada", 404)
    try:
        ops.salvar_video_entrega(delivery, request.files.get("video"))
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_delivery(delivery))


@api_bp.route("/virtuais/pedidos/<int:order_id>/sala", methods=["POST"])
@api_login_required
def api_virtuais_regerar_sala(order_id: int) -> Any:
    """Tenta obter a sala de um pedido cuja criação ficou pendente no Google (FR-037).

    Gate da **Fila de Produção**, não o de campanhas: a ação aparece na fila, e quem trabalha nela
    é `CASTING`. Com o gate estreito, o botão apareceria e devolveria 403 — botão morto ao clique é
    exatamente o que o Princípio V proíbe. Não é alargamento de permissão: `CASTING` já finaliza
    entrega e envia vídeo por este mesmo gate.
    """
    denied = require_producao_access()
    if denied:
        return denied
    order = VirtualOrder.query.get(order_id)
    if order is None:
        return json_error("Pedido não encontrado", 404)
    try:
        ops.regerar_sala(order)
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    except Exception as exc:  # noqa: BLE001 — Google fora não pode virar 500 na cara da equipe
        current_app.logger.warning(
            "[virtuais] regeração manual da sala do pedido %s falhou: %s", order.order_nsu, exc
        )
        return json_error(
            "O Google não respondeu agora. A varredura continua tentando em segundo plano.", 502
        )
    return jsonify({
        "meet_url": order.meet_url,
        "meet_pending": order.meet_pending,
        "meet_attempts": order.meet_attempts or 0,
        "meet_retry_esgotado": bool(
            order.meet_pending and ops.retry_esgotou(order.meet_attempts or 0)
        ),
    })


@api_bp.route("/virtuais/pedidos/<int:order_id>/avisos/<kind>/reenviar", methods=["POST"])
@api_login_required
def api_virtuais_reenviar_aviso(order_id: int, kind: str) -> Any:
    """Reenvia, por ação da equipe, um aviso automático que falhou (FR-039c).

    Deliberadamente **não** cria aviso novo: só reentrega o que já foi registrado e falhou. Um
    endpoint que criasse a linha seria um caminho paralelo ao fluxo automático, e a trava
    `UNIQUE(order_id, kind)` deixaria de significar "a família recebe este aviso uma vez".

    Gate da Fila de Produção pelo mesmo motivo do endpoint de sala: é lá que o banner de falha
    aparece, e `CASTING` já dispara e-mail para a família ao finalizar uma entrega de vídeo.
    """
    denied = require_producao_access()
    if denied:
        return denied
    order = VirtualOrder.query.get(order_id)
    if order is None:
        return json_error("Pedido não encontrado", 404)
    try:
        registro = ops.reenviar_aviso(order, kind)
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})

    if not registro.sent_ok:
        return json_error(
            registro.error_message or "O aviso falhou de novo.",
            502,
            fields={"kind": "Não foi possível entregar agora — use o WhatsApp para o reforço."},
        )
    return jsonify({"kind": registro.kind, "sent_ok": True, "attempts": registro.attempts or 0})


@api_bp.route("/virtuais/devolucoes/<int:refund_id>", methods=["PATCH"])
@api_login_required
def api_virtuais_concluir_devolucao(refund_id: int) -> Any:
    """Marca uma devolução como concluída depois de executada no painel da operadora (FR-043)."""
    denied = require_virtuais_access()
    if denied:
        return denied
    refund = VirtualRefundRequest.query.get(refund_id)
    if refund is None:
        return json_error("Devolução não encontrada", 404)

    data = request.get_json(silent=True) or {}
    if data.get("status") != VIRTUAL_REFUND_STATUS_CONCLUIDA:
        return json_error(
            "Status inválido para uma devolução.", 400,
            fields={"status": "Use 'concluida'."},
        )

    refund.status = VIRTUAL_REFUND_STATUS_CONCLUIDA
    refund.resolved_by_id = current_user.id
    refund.resolved_at = now_sp()
    audit(
        "edit", "VirtualRefundRequest", refund.id, refund.order.order_nsu if refund.order else "",
        "Devolução marcada como concluída",
    )
    db.session.commit()
    return jsonify(ops.serialize_refund(refund))


@api_bp.route("/virtuais/horarios/<int:slot_id>", methods=["DELETE"])
@api_login_required
def api_virtuais_remover_horario(slot_id: int) -> Any:
    """Remove um horário livre do estoque; recusa reservado ou vendido (FR-008)."""
    denied = require_virtuais_access()
    if denied:
        return denied
    slot = VirtualCampaignSlot.query.get(slot_id)
    if slot is None:
        return json_error("Horário não encontrado", 404)
    try:
        ops.remover_slot(slot)
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 409, fields={exc.field: exc.message})
    return jsonify({"deleted": True})
