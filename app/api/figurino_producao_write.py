"""Endpoints de ESCRITA da Produção de Figurinos (feature 225).

Camada fina: RBAC como função chamada no início da view, delegação para
`app.figurino.producao_ops`, serialização. Uploads chegam em `multipart/form-data`; o resto é
JSON.

Os avisos do Google Agenda voltam no campo `warning` do payload — nunca como erro: o pedido foi
salvo, e o que falhou foi a integração (mesma política de `event_ops.update_event_core`).
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.email_service import (
    send_async,
    send_figurino_pedido_setor_email,
    send_figurino_producao_email,
)
from app.figurino import producao_ops as ops
from app.models import FigurinoProducao, FigurinoProducaoAnexo, SpecialExpense


def _require_create() -> Any | None:
    if not ops.pode_abrir(current_user):
        return json_error("Sem permissão", 403)
    return None


def _require_execute() -> Any | None:
    if not ops.pode_executar(current_user):
        return json_error("Sem permissão", 403)
    return None


def _get_producao(producao_id: int) -> FigurinoProducao | None:
    return FigurinoProducao.query.get(producao_id)


def _payload() -> dict[str, Any]:
    """Campos do corpo, aceitando JSON e multipart pela mesma porta."""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def _resposta(producao: FigurinoProducao, aviso: str | None, status: int = 200) -> Any:
    corpo: dict[str, Any] = {"producao": ops.serialize_producao(producao, detalhado=True)}
    if aviso:
        corpo["warning"] = aviso
    return jsonify(corpo), status


def _avisar_responsavel(producao: FigurinoProducao, anterior_id: int | None) -> None:
    """Manda o e-mail quando alguém NOVO virou responsável.

    Só depois do commit: `send_async` empacota o objeto ORM por chave primária e o recarrega numa
    sessão limpa dentro da thread — sem PK, o e-mail sai vazio ou explode onde ninguém vê.
    """
    if producao.responsible_id and producao.responsible_id != anterior_id:
        send_async(send_figurino_producao_email, producao, producao.responsible)


# ── Pedido ───────────────────────────────────────────────────────────────────


@api_bp.route("/figurino/producoes", methods=["POST"])
@api_login_required
def api_figurino_producao_create() -> Any:
    """Abre um pedido de produção (qualquer papel interno — FR-012)."""
    denied = _require_create()
    if denied:
        return denied

    dados = _payload()
    try:
        producao, aviso = ops.create_producao(
            title=dados.get("title", ""),
            actor=current_user,
            description=dados.get("description"),
            kind=dados.get("kind") or "producao",
            severity=dados.get("severity"),
            event_id=dados.get("event_id"),
            figurino_sheet_id=dados.get("figurino_sheet_id"),
            responsible_id=dados.get("responsible_id"),
            due_date=dados.get("due_date"),
            estimated_cost=dados.get("estimated_cost"),
            quantity=dados.get("quantity", 1),
        )
    except ops.ProducaoValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})

    _avisar_responsavel(producao, None)
    # Aviso ao SETOR: o pedido pode ter nascido sem dono (é a regra na manutenção), e nesse caso
    # ninguém receberia o e-mail individual. Só depois do commit — `send_async` recarrega por PK.
    if producao.responsible_id is None:
        send_async(send_figurino_pedido_setor_email, producao, ops.equipe_figurino())
    return _resposta(producao, aviso, status=201)


@api_bp.route("/figurino/producoes/<int:producao_id>", methods=["PATCH"])
@api_login_required
def api_figurino_producao_update(producao_id: int) -> Any:
    """Edita o pedido. Quem abriu pode editar enquanto ninguém assumiu; depois é da oficina."""
    producao = _get_producao(producao_id)
    if not producao:
        return json_error("Pedido não encontrado.", 404)

    dono_do_pedido = producao.requested_by_id == current_user.id and producao.responsible_id is None
    if not ops.pode_executar(current_user) and not dono_do_pedido:
        return json_error("Sem permissão", 403)

    anterior = producao.responsible_id
    dados = _payload()
    # Só a oficina designa responsável — quem pede não escolhe quem faz.
    if "responsible_id" in dados and not ops.pode_executar(current_user):
        dados.pop("responsible_id")

    try:
        producao, aviso = ops.update_producao(producao, actor=current_user, **dados)
    except ops.ProducaoValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})

    _avisar_responsavel(producao, anterior)
    return _resposta(producao, aviso)


@api_bp.route("/figurino/producoes/<int:producao_id>/status", methods=["POST"])
@api_login_required
def api_figurino_producao_status(producao_id: int) -> Any:
    """Move o pedido de situação. Aprovar é só de super admin (FR-011)."""
    producao = _get_producao(producao_id)
    if not producao:
        return json_error("Pedido não encontrado.", 404)

    dados = _payload()
    try:
        producao, aviso = ops.mudar_status(
            producao,
            (dados.get("status") or "").strip(),
            actor=current_user,
            motivo=dados.get("motivo"),
            observacao=dados.get("observacao"),
        )
    except ops.ProducaoValidationError as exc:
        # Falta de permissão vem do núcleo como erro de validação do campo `status`; traduzir
        # para 403 aqui mantém o contrato da API (permissão não é erro de formulário).
        status = 403 if "permiss" in exc.message.lower() or "super admin" in exc.message.lower() else 400
        if status == 403:
            return json_error(exc.message, 403)
        return json_error(exc.message, 400, fields={exc.field: exc.message})

    return _resposta(producao, aviso)


@api_bp.route("/figurino/producoes/<int:producao_id>", methods=["DELETE"])
@api_login_required
def api_figurino_producao_delete(producao_id: int) -> Any:
    """Apaga o pedido. Gastos vinculados sobrevivem (o dinheiro saiu de verdade)."""
    denied = _require_execute()
    if denied:
        return denied

    producao = _get_producao(producao_id)
    if not producao:
        return json_error("Pedido não encontrado.", 404)

    ops.delete_producao(producao, actor=current_user)
    return jsonify({"ok": True})


# ── Histórico ────────────────────────────────────────────────────────────────


@api_bp.route("/figurino/producoes/<int:producao_id>/comentarios", methods=["POST"])
@api_login_required
def api_figurino_producao_comentar(producao_id: int) -> Any:
    """Acrescenta uma nota ao histórico de evolução do pedido."""
    denied = _require_create()
    if denied:
        return denied

    producao = _get_producao(producao_id)
    if not producao:
        return json_error("Pedido não encontrado.", 404)

    mensagem = (_payload().get("message") or "").strip()
    if not mensagem:
        return json_error("Escreva alguma coisa.", 400, fields={"message": "Obrigatório"})

    from app import db

    ops.registrar_log(producao, mensagem, actor=current_user)
    db.session.commit()
    return _resposta(producao, None, status=201)


# ── Anexos ───────────────────────────────────────────────────────────────────


@api_bp.route("/figurino/producoes/<int:producao_id>/anexos", methods=["POST"])
@api_login_required
def api_figurino_producao_anexo_create(producao_id: int) -> Any:
    """Anexa foto de evolução ou orçamento de fornecedor (multipart: `file`)."""
    denied = _require_execute()
    if denied:
        return denied

    producao = _get_producao(producao_id)
    if not producao:
        return json_error("Pedido não encontrado.", 404)

    try:
        ops.add_anexo(
            producao,
            request.files.get("file"),
            kind=(request.form.get("kind") or "foto").strip(),
            actor=current_user,
            caption=request.form.get("caption"),
            supplier_name=request.form.get("supplier_name"),
            amount=request.form.get("amount"),
        )
    except ops.ProducaoValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})

    return _resposta(producao, None, status=201)


@api_bp.route(
    "/figurino/producoes/<int:producao_id>/anexos/<int:anexo_id>", methods=["DELETE"]
)
@api_login_required
def api_figurino_producao_anexo_delete(producao_id: int, anexo_id: int) -> Any:
    """Remove um anexo do pedido."""
    denied = _require_execute()
    if denied:
        return denied

    anexo = FigurinoProducaoAnexo.query.get(anexo_id)
    if not anexo or anexo.producao_id != producao_id:
        return json_error("Anexo não encontrado.", 404)

    producao = anexo.producao
    ops.remove_anexo(anexo, actor=current_user)
    return _resposta(producao, None)


# ── Gastos ───────────────────────────────────────────────────────────────────


@api_bp.route("/figurino/producoes/<int:producao_id>/gastos", methods=["POST"])
@api_login_required
def api_figurino_producao_vincular_gasto(producao_id: int) -> Any:
    """Vincula um gasto extra existente ao pedido (FR-032)."""
    denied = _require_execute()
    if denied:
        return denied

    producao = _get_producao(producao_id)
    if not producao:
        return json_error("Pedido não encontrado.", 404)

    gasto_id = _payload().get("gasto_id")
    gasto = SpecialExpense.query.get(int(gasto_id)) if str(gasto_id or "").isdigit() else None
    if not gasto:
        return json_error("Gasto não encontrado.", 404)

    ops.vincular_gasto(producao, gasto, actor=current_user)
    return _resposta(producao, None)


@api_bp.route(
    "/figurino/producoes/<int:producao_id>/gastos/<int:gasto_id>", methods=["DELETE"]
)
@api_login_required
def api_figurino_producao_desvincular_gasto(producao_id: int, gasto_id: int) -> Any:
    """Desfaz o vínculo entre um gasto e o pedido."""
    denied = _require_execute()
    if denied:
        return denied

    gasto = SpecialExpense.query.get(gasto_id)
    if not gasto or gasto.figurino_producao_id != producao_id:
        return json_error("Gasto não encontrado neste pedido.", 404)

    producao = gasto.figurino_producao
    ops.desvincular_gasto(gasto, actor=current_user)
    return _resposta(producao, None)
