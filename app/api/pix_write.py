"""Endpoints de ESCRITA do PIX recebido por e-mail (feature 318): as respostas ao "É esta?",
o "Desfazer" e a configuração da leitura.

RBAC (função no início de cada view — constituição XIII; tabela em `docs/01` §4.3), sempre pelo
papel REAL (escrita):
  * confirmar / descartar / não é de venda: COMERCIAL, FINANCEIRO, SUPERADMIN (decisão do dono);
    no repasse da InfinitePay, só FINANCEIRO e SUPERADMIN.
  * desfazer: FINANCEIRO, SUPERADMIN (escrita financeira).
  * configuração: SUPERADMIN.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user
from sqlalchemy.exc import DBAPIError

from app import db
from app.api import api_bp
from app.api.pix_read import (
    _require_financeiro,
    _require_superadmin,
    _require_vendas,
    config_json,
    ve_repasse,
)
from app.api_utils import api_login_required, json_error, json_recusa_do_cancelado
from app.calendar.cancel_ops import CancelValidationError
from app.constants import PIX_SUGESTAO_REPASSE, now_sp
from app.financeiro import pix_ops
from app.models import ContaRecebimento, PixRecebido, SiteSetting


def _recusa(exc: pix_ops.PixErro) -> Any:
    db.session.rollback()
    if exc.codigo:
        return json_error(exc.mensagem, exc.status, codigo=exc.codigo)
    return json_error(exc.mensagem, exc.status)


def _ids(valores: Any) -> list[int] | None:
    """Ids inteiros de uma lista vinda do corpo; `None` se algum não for número."""
    try:
        return [int(v) for v in (valores or [])]
    except (TypeError, ValueError):
        return None


def _gate_resposta(pix_id: int) -> Any:
    """Quem responde o "É esta?": vendas; o repasse da InfinitePay, só Financeiro/Superadmin."""
    negado = _require_vendas()
    if negado:
        return negado
    pix = db.session.get(PixRecebido, pix_id)
    if pix is not None and pix.tipo_sugestao == PIX_SUGESTAO_REPASSE and not ve_repasse():
        return json_error("Sem permissão", 403)
    return None


def _executar(acao) -> Any:
    try:
        pix = acao()
        db.session.commit()
    except pix_ops.PixErro as exc:
        return _recusa(exc)
    except CancelValidationError as exc:
        db.session.rollback()
        return json_recusa_do_cancelado(exc)
    except DBAPIError:
        db.session.rollback()
        return json_error("Outra pessoa mexeu neste pagamento agora. Tente de novo.", 409)
    return jsonify({"pix": pix_ops.para_api(pix)})


@api_bp.route("/pix/<int:pix_id>/confirmar", methods=["POST"])
@api_login_required
def api_pix_confirmar(pix_id: int) -> Any:
    negado = _gate_resposta(pix_id)
    if negado:
        return negado
    corpo = request.get_json(silent=True) or {}
    ids = _ids(corpo.get("event_ids") or ([corpo["event_id"]] if corpo.get("event_id") else []))
    if not ids:
        return json_error("Escolha a venda deste PIX.", 400, fields={"event_id": "Obrigatório"})
    novo = bool(corpo.get("novo"))
    return _executar(lambda: pix_ops.confirmar(pix_id, ids, current_user, novo=novo))


@api_bp.route("/pix/<int:pix_id>/descartar", methods=["POST"])
@api_login_required
def api_pix_descartar(pix_id: int) -> Any:
    negado = _gate_resposta(pix_id)
    if negado:
        return negado
    corpo = request.get_json(silent=True) or {}
    ids = _ids([corpo.get("event_id")]) if corpo.get("event_id") else None
    if not ids:
        return json_error("Informe a venda.", 400, fields={"event_id": "Obrigatório"})
    return _executar(lambda: pix_ops.descartar(pix_id, ids[0], current_user))


@api_bp.route("/pix/<int:pix_id>/nao-e-venda", methods=["POST"])
@api_login_required
def api_pix_nao_e_venda(pix_id: int) -> Any:
    negado = _gate_resposta(pix_id)
    if negado:
        return negado
    return _executar(lambda: pix_ops.nao_e_venda(pix_id, current_user))


@api_bp.route("/pix/<int:pix_id>/desfazer", methods=["POST"])
@api_login_required
def api_pix_desfazer(pix_id: int) -> Any:
    negado = _require_financeiro()
    if negado:
        return negado
    return _executar(lambda: pix_ops.desfazer(pix_id, current_user))


@api_bp.route("/pix/config", methods=["PATCH"])
@api_login_required
def api_pix_config_salvar() -> Any:
    negado = _require_superadmin()
    if negado:
        return negado
    corpo = request.get_json(silent=True) or {}
    s = db.session.get(SiteSetting, 1)
    if "ativo" in corpo:
        ativo = bool(corpo["ativo"])
        if ativo and not s.pix_email_ativo:
            # Só entra na fila o que chegar daqui em diante: o passado é do ensaio.
            s.pix_email_ativo_desde = now_sp()
        s.pix_email_ativo = ativo
    if "pagadores_proprios" in corpo:
        nomes = [str(n).strip() for n in corpo.get("pagadores_proprios") or [] if str(n).strip()]
        s.pix_pagadores_proprios = "\n".join(dict.fromkeys(nomes)) or None
    for item in corpo.get("contas") or []:
        conta_ids = _ids([item.get("id") or 0])
        conta = db.session.get(ContaRecebimento, conta_ids[0]) if conta_ids else None
        if conta is None:
            db.session.rollback()
            return json_error("Conta não encontrada.", 404)
        if "numero_conta" in item:
            numero = "".join(ch for ch in str(item["numero_conta"] or "") if ch.isdigit())
            outra = ContaRecebimento.query.filter(
                ContaRecebimento.numero_conta == numero, ContaRecebimento.id != conta.id
            ).first()
            if numero and outra is not None:
                db.session.rollback()
                return json_error(
                    "Esse número já está em outra conta.", 400, fields={"numero_conta": "Repetido"}
                )
            conta.numero_conta = numero or None
        if "ativa" in item:
            conta.ativa = bool(item["ativa"])
    db.session.commit()
    return jsonify(config_json())
