"""Endpoints de escrita dos contratos da ClickSign (feature 317).

RBAC (função no início de cada view — constituição XIII; tabela em `docs/01` §4.3):
  * `_require_cobrar` (COMERCIAL, SUPERADMIN): cobrar, ligar, desligar e descartar. O FINANCEIRO
    vê a situação mas não age — decisão do dono no planejamento (22/10/2026).
A trava do cancelado (312) é aplicada no núcleo (`sincronizar_ops.ligar`), não pelo prefixo: as rotas
`/api/contratos/` ficam fora de `PREFIXOS_DA_TELA` do `verify_312` de propósito.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.contratos import sincronizar_ops
from app.models import ClicksignDocumento

_PAPEIS_QUE_COBRAM = {RoleName.COMERCIAL, RoleName.SUPERADMIN}


def _require_cobrar() -> Any:
    """403 para quem não é COMERCIAL nem SUPERADMIN."""
    if any(r.name.upper() in _PAPEIS_QUE_COBRAM for r in current_user.roles):
        return None
    return json_error("Sem permissão", 403)


def _recusa(exc: sincronizar_ops.ContratoIndisponivel) -> Any:
    db.session.rollback()
    return json_error(exc.motivo, 409, codigo=exc.codigo)


def _bloco_do_evento(event_id: int | None) -> Any:
    """O bloco `contrato` atualizado do evento, para a tela trocar sem recarregar tudo."""
    from app.constants import now_sp
    from app.contratos import situacao_ops
    from app.models import CalendarEvent

    if event_id is None:
        return None
    evento = db.session.get(CalendarEvent, event_id)
    if evento is None:
        return None
    return situacao_ops.bloco_do_evento(
        evento, pode_cobrar_papel=True, pode_conferir_papel=True, hoje=now_sp().date()
    )


@api_bp.route("/contratos/<int:documento_id>/cobranca", methods=["POST"])
@api_login_required
def api_contratos_cobrar(documento_id: int) -> Any:
    """Registra o "Cobrar contrato" (a mensagem é copiada na tela). FR-011."""
    denied = _require_cobrar()
    if denied:
        return denied
    if db.session.get(ClicksignDocumento, documento_id) is None:
        return json_error("Contrato não encontrado", 404)
    try:
        cobranca = sincronizar_ops.registrar_cobranca(documento_id, current_user)
    except sincronizar_ops.ContratoIndisponivel as exc:
        return _recusa(exc)
    db.session.commit()
    return jsonify(
        {"ultima_cobranca": {"por": cobranca.usuario_nome, "em": cobranca.em.isoformat()}}
    ), 201


@api_bp.route("/contratos/<int:documento_id>/ligar", methods=["POST"])
@api_login_required
def api_contratos_ligar(documento_id: int) -> Any:
    """ "É esse mesmo": liga o documento à venda do evento informado. FR-006."""
    denied = _require_cobrar()
    if denied:
        return denied
    corpo = request.get_json(silent=True) or {}
    try:
        event_id = int(corpo.get("event_id"))
    except (TypeError, ValueError):
        return json_error("Informe o evento.", 400, fields={"event_id": "Informe o evento."})
    try:
        documento = sincronizar_ops.ligar(documento_id, event_id, current_user)
    except LookupError as exc:
        db.session.rollback()
        alvo = "Contrato" if str(exc) == "documento" else "Evento"
        return json_error(f"{alvo} não encontrado", 404)
    except sincronizar_ops.ContratoIndisponivel as exc:
        return _recusa(exc)
    db.session.commit()
    return jsonify({"contrato": _bloco_do_evento(documento.event_id)})


@api_bp.route("/contratos/<int:documento_id>/desligar", methods=["POST"])
@api_login_required
def api_contratos_desligar(documento_id: int) -> Any:
    """Desliga o documento da venda; a sincronização não religa sozinha nessa venda. FR-005."""
    denied = _require_cobrar()
    if denied:
        return denied
    documento = db.session.get(ClicksignDocumento, documento_id)
    if documento is None:
        return json_error("Contrato não encontrado", 404)
    event_id = documento.event_id
    try:
        sincronizar_ops.desligar(documento_id, current_user)
    except sincronizar_ops.ContratoIndisponivel as exc:
        return _recusa(exc)
    db.session.commit()
    return jsonify({"contrato": _bloco_do_evento(event_id)})


@api_bp.route("/contratos/<int:documento_id>/descartar", methods=["POST"])
@api_login_required
def api_contratos_descartar(documento_id: int) -> Any:
    """ "Não é de nenhuma venda": sai da conferência para sempre."""
    denied = _require_cobrar()
    if denied:
        return denied
    if db.session.get(ClicksignDocumento, documento_id) is None:
        return json_error("Contrato não encontrado", 404)
    try:
        sincronizar_ops.descartar(documento_id, current_user)
    except sincronizar_ops.ContratoIndisponivel as exc:
        return _recusa(exc)
    db.session.commit()
    return jsonify({"ok": True})
