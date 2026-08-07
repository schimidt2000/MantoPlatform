"""Superfície PÚBLICA da Loja de Interações Virtuais (feature 205) — sem autenticação.

Landing, estoque de horários, reserva, página do pedido e autocomplete de endereço.

Três regras que valem para tudo neste módulo:

* **campanha em rascunho não existe para o público** (404) e pausada responde 410 — a família
  precisa saber a diferença entre "endereço errado" e "acabou por ora" (FR-007);
* **nenhum dado sensível trafega sem validação dupla.** A página do pedido devolve só situação,
  horário e valor; nome da criança, endereço e sala exigem também o telefone (FR-044a, US5);
* **as rotas não fazem regra de negócio** — validam entrada, chamam ``virtuais_ops`` e serializam
  (Princípio III).
"""

import os
from datetime import datetime, timedelta
from typing import Any

from flask import jsonify, request, send_file, session

from app import limiter
from app.api import api_bp
from app.api_utils import json_error
from app.constants import (
    VIRTUAL_ACCESS_SESSION_MINUTES,
    VIRTUAL_CAMPAIGN_STATUS_PUBLICADA,
    VIRTUAL_CAMPAIGN_STATUS_RASCUNHO,
    now_sp,
)
from app.marketing import virtuais_ops as ops
from app.models import VirtualCampaign, VirtualOrder


def _campanha_publicada_ou_erro(slug: str) -> tuple[Any, Any]:
    """Devolve ``(campanha, None)`` ou ``(None, resposta_de_erro)``.

    404 para inexistente ou rascunho (do ponto de vista do público, é a mesma coisa: não existe);
    410 para pausada/despublicada, que já existiu e pode voltar.
    """
    campaign = VirtualCampaign.query.filter_by(slug=slug).first()
    if campaign is None or campaign.status == VIRTUAL_CAMPAIGN_STATUS_RASCUNHO:
        return None, json_error("Campanha não encontrada", 404)
    if campaign.status != VIRTUAL_CAMPAIGN_STATUS_PUBLICADA:
        return None, json_error("Esta campanha não está disponível no momento.", 410)
    return campaign, None


@api_bp.route("/virtuais/vitrine", methods=["GET"])
def api_virtuais_vitrine() -> Any:
    """Campanhas publicadas — a home da loja (feature 224e).

    O caminho é `/vitrine`, e não `/campanhas`, porque `GET /api/virtuais/campanhas` já é a
    listagem **interna** (gated) e `/campanhas/publicadas` colidiria com o `<slug>` da landing.
    """
    return jsonify({"campanhas": ops.listar_vitrine()})


@api_bp.route("/virtuais/campanhas/<slug>", methods=["GET"])
def api_virtuais_campanha_publica(slug: str) -> Any:
    """Landing pública da campanha (FR-011)."""
    campaign, erro = _campanha_publicada_ou_erro(slug)
    if erro:
        return erro
    return jsonify(ops.serialize_campaign(campaign))


@api_bp.route("/virtuais/campanhas/<slug>/horarios", methods=["GET"])
def api_virtuais_horarios_publicos(slug: str) -> Any:
    """Horários disponíveis da campanha.

    Só entram os livres — ou travados com o lock já vencido, que é o que faz a expiração valer
    mesmo antes de a varredura rodar. Horário no passado nunca aparece. O payload não revela quem
    reservou.
    """
    campaign, erro = _campanha_publicada_ou_erro(slug)
    if erro:
        return erro
    slots = ops.listar_slots_disponiveis(campaign, day=request.args.get("date"))
    return jsonify(
        {"slots": [{"id": s.id, "start_at": s.start_at.isoformat()} for s in slots]}
    )


@api_bp.route("/virtuais/campanhas/<slug>/reservar", methods=["POST"])
@limiter.limit("20 per minute")
def api_virtuais_reservar(slug: str) -> Any:
    """Cria o pedido, aplica o soft lock de 15 minutos e devolve o link de pagamento.

    Os códigos de erro carregam significados distintos de propósito:

    * **400** — campo inválido, com ``fields`` apontando qual (o React destaca e leva o foco);
    * **409** — o horário (ou a última vaga de vídeo) acabou de ser tomado; vem com a lista
      atualizada, para a família escolher outro sem recarregar;
    * **429** — teto anti-abuso; quando o motivo é "você já tem uma reserva", vem o token dela;
    * **502** — a operadora falhou ao abrir o pagamento; a reserva já foi desfeita e o horário
      devolvido ao estoque.
    """
    campaign, erro = _campanha_publicada_ou_erro(slug)
    if erro:
        return erro

    data = request.get_json(silent=True) or {}
    try:
        order = ops.reservar(
            campaign,
            modality=data.get("modality", ""),
            slot_id=data.get("slot_id"),
            gift_item_id=data.get("gift_item_id"),
            client_token=data.get("client_token"),
            origin_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            origin_user_agent=request.headers.get("User-Agent"),
            child_name=data.get("child_name"),
            child_age=data.get("child_age"),
            behavior_notes=data.get("behavior_notes"),
            contact_phone=data.get("contact_phone"),
            contact_email=data.get("contact_email"),
            delivery_address=data.get("delivery_address"),
        )
    except ops.VirtuaisValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    except ops.VirtuaisConflitoError as exc:
        slots = ops.listar_slots_disponiveis(campaign)
        body = json_error(str(exc), 409)[0].get_json()
        body["slots"] = [{"id": s.id, "start_at": s.start_at.isoformat()} for s in slots]
        return jsonify(body), 409
    except ops.VirtuaisLimiteError as exc:
        body = json_error(exc.message, 429)[0].get_json()
        if exc.existing_order_token:
            body["error"]["existing_order_token"] = exc.existing_order_token
        return jsonify(body), 429
    except ops.VirtuaisOperadoraError as exc:
        return json_error(str(exc), 502)

    return (
        jsonify(
            {
                "public_token": order.public_token,
                "order_nsu": order.order_nsu,
                "locked_until": order.locked_until.isoformat() if order.locked_until else None,
                "total_value": ops._money(order.total_value),
                "payment_url": order.payment_url,
            }
        ),
        201,
    )


@api_bp.route("/virtuais/pedidos/<public_token>", methods=["GET"])
def api_virtuais_pedido_publico(public_token: str) -> Any:
    """Resumo do pedido — o destino do retorno do checkout (FR-035a, FR-044).

    Sem validação de telefone, devolve apenas situação, horário e valor. Os dados da criança e o
    acesso à interação ficam atrás da validação dupla (FR-044a), implementada na US5.
    """
    order = VirtualOrder.query.filter_by(public_token=public_token).first()
    if order is None:
        return json_error("Pedido não encontrado", 404)
    return jsonify(ops.serialize_order_summary(order))


def _sessao_valida(order: VirtualOrder) -> bool:
    """True se esta sessão do navegador já validou o telefone deste pedido e não expirou.

    A sessão vive no cookie do Flask e guarda só o instante da validação. Expira por inatividade
    (FR-044c): um celular emprestado ou um computador compartilhado não pode deixar os dados da
    criança abertos indefinidamente.
    """
    dados = session.get("virtuais_acesso") or {}
    marca = dados.get(order.public_token)
    if not marca:
        return False
    try:
        quando = datetime.fromisoformat(marca)
    except (TypeError, ValueError):
        return False
    if now_sp() - quando > timedelta(minutes=VIRTUAL_ACCESS_SESSION_MINUTES):
        return False
    # Renova a janela a cada acesso — o que expira é a inatividade, não a sessão em uso.
    dados[order.public_token] = now_sp().isoformat()
    session["virtuais_acesso"] = dados
    return True


@api_bp.route("/virtuais/pedidos/<public_token>/verificar", methods=["POST"])
@limiter.limit("10 per minute")
def api_virtuais_verificar_pedido(public_token: str) -> Any:
    """Valida o telefone da compra e libera os dados do pedido (FR-044a–044c).

    É a segunda metade da validação dupla: o endereço do pedido sozinho não mostra nada da criança.
    """
    order = VirtualOrder.query.filter_by(public_token=public_token).first()
    if order is None:
        return json_error("Pedido não encontrado", 404)

    data = request.get_json(silent=True) or {}
    try:
        confere = ops.verificar_telefone(order, data.get("phone", ""))
    except ops.VirtuaisLimiteError as exc:
        body = json_error(exc.message, 429)[0].get_json()
        body["error"]["blocked_until"] = (
            order.access_blocked_until.isoformat() if order.access_blocked_until else None
        )
        return jsonify(body), 429

    if not confere:
        body = json_error("Telefone não confere com o da compra.", 401)[0].get_json()
        body["error"]["attempts_left"] = ops.tentativas_restantes(order)
        return jsonify(body), 401

    dados = session.get("virtuais_acesso") or {}
    dados[order.public_token] = now_sp().isoformat()
    session["virtuais_acesso"] = dados
    return jsonify(ops.serialize_order_full(order))


@api_bp.route("/virtuais/pedidos/<public_token>/completo", methods=["GET"])
def api_virtuais_pedido_completo(public_token: str) -> Any:
    """Dados completos do pedido — só com a sessão de acesso aberta (FR-044a)."""
    order = VirtualOrder.query.filter_by(public_token=public_token).first()
    if order is None:
        return json_error("Pedido não encontrado", 404)
    if not _sessao_valida(order):
        return json_error("Confirme o telefone da compra para ver estes dados.", 401)
    return jsonify(ops.serialize_order_full(order))


@api_bp.route("/virtuais/pedidos/<public_token>/video", methods=["GET"])
def api_virtuais_video(public_token: str) -> Any:
    """Serve o vídeo gravado **sob validação a cada requisição** (FR-038e).

    O arquivo mora fora de qualquer pasta servida estaticamente e a URL do disco nunca sai em
    payload nenhum: este endpoint é o único caminho até ele. `conditional=True` dá suporte a
    `Range`, que é o que permite ao player buscar no meio do vídeo sem baixar tudo.
    """
    order = VirtualOrder.query.filter_by(public_token=public_token).first()
    if order is None:
        return json_error("Pedido não encontrado", 404)
    if not _sessao_valida(order):
        return json_error("Confirme o telefone da compra para assistir.", 401)

    entrega = order.media_delivery
    caminho = ops.caminho_video(entrega) if entrega else None
    if not caminho or not os.path.exists(caminho):
        return json_error("O vídeo ainda não está disponível.", 404)

    return send_file(
        caminho,
        mimetype=entrega.video_mime or "video/mp4",
        conditional=True,
        download_name=f"{order.child_name}.mp4",
    )


@api_bp.route("/virtuais/enderecos/autocomplete", methods=["GET"])
@limiter.limit("30 per minute")
def api_virtuais_endereco_autocomplete() -> Any:
    """Sugestões de endereço para o checkout público (FR-015).

    Variante sem login de ``/api/maps/address-autocomplete``, que é restrito a usuários
    autenticados — o checkout é anônimo por natureza. A chave do Google continua **só no servidor**
    (Princípio XII.4) e o teto por origem protege a cota (XII.5).

    Reusa ``app.maps.address_autocomplete`` — a mesma função do endpoint interno, não uma segunda
    implementação (Princípio I). O que muda aqui é só o gate: sem login, com teto por origem.

    Devolve o mesmo formato do endpoint interno (``{"items": [...]}``), para o
    ``GoogleAddressInput`` promovido ao ``@manto/ui`` funcionar nos dois lugares sem ramificação.
    """
    from app.maps import address_autocomplete

    sugestoes, error, status = address_autocomplete(
        request.args.get("q", ""),
        session_token=(request.args.get("session_token") or None),
    )
    if error:
        return json_error(error, status)
    return jsonify({"items": sugestoes})
