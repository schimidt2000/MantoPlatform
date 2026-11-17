"""Endpoints de ESCRITA da base autorizada (feature 350).

RBAC: Comercial e Superadmin — quem atende a cliente — em tudo deste módulo: aceite e retirada de
novidades, aniversário da criança, indicação e parceiro da ficha, cadastro de parceiro e pós-evento.
O Financeiro lê a ficha (`clientes_read`) e a lista de parceiros (`clientes_base_read`), mas não
escreve aqui. Gate por função no início da view (constituição XIII); a tabela fica em `docs/01` §4.3.

Os núcleos não comitam: cada view comita depois de o núcleo aceitar.
"""

from __future__ import annotations

from typing import Any

from flask import current_app, jsonify, request
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.clientes import (
    consentimento_ops,
    indicacao_ops,
    parceiro_ops,
    pos_evento_ops,
)
from app.clientes.client_ops import ClientValidationError
from app.constants import POS_EVENTO_CANAL_CONVERSA, POS_EVENTO_CANAL_COPIADO, RoleName
from app.conversas.configuracao import cfg_whatsapp
from app.conversas.envio_ops import EnvioRecusado
from app.models import CalendarEvent, Client, Parceiro, PosEvento


def _negado() -> Any:
    papeis = {r.name.upper() for r in current_user.roles}
    if papeis & {RoleName.COMERCIAL, RoleName.SUPERADMIN}:
        return None
    return json_error("Sem permissão", 403)


def _ficha_ou_404(client_id: int) -> Client | None:
    return db.session.get(Client, client_id)


def _erro_de_consentimento(exc: consentimento_ops.ConsentimentoErro) -> Any:
    db.session.rollback()
    campos = {exc.campo: exc.mensagem} if exc.campo else None
    extras = {"codigo": exc.codigo} if exc.codigo else {}
    return json_error(exc.mensagem, exc.status, fields=campos, **extras)


def _erro_de_validacao(exc: ClientValidationError) -> Any:
    db.session.rollback()
    return json_error(exc.message, 400, fields={exc.field: exc.message})


def _consentimentos(client: Client) -> dict[str, Any]:
    return {
        "consentimentos": consentimento_ops.serializar(client, com_criancas=True),
        "pode_prospectar": consentimento_ops.pode_prospectar(client),
    }


# ── Consentimentos ───────────────────────────────────────────────────────────────────────────────


@api_bp.route("/clientes/<int:client_id>/consentimentos/novidades", methods=["POST", "DELETE"])
@api_login_required
def api_clientes_consentimento_novidades(client_id: int) -> Any:
    """Registra (POST) ou retira (DELETE) o aceite de novidades, com a origem da lista fechada."""
    negado = _negado()
    if negado:
        return negado
    client = _ficha_ou_404(client_id)
    if client is None:
        return json_error("Cliente não encontrada", 404)
    corpo = request.get_json(silent=True) or {}
    try:
        origem = consentimento_ops.validar_origem_da_equipe(corpo.get("origem"))
        acao = (
            consentimento_ops.registrar_aceite_novidades
            if request.method == "POST"
            else consentimento_ops.retirar_aceite_novidades
        )
        acao(client, origem=origem, referencia=corpo.get("referencia"), user_id=current_user.id)
    except consentimento_ops.ConsentimentoErro as exc:
        return _erro_de_consentimento(exc)
    db.session.commit()
    return jsonify(_consentimentos(client))


@api_bp.route("/clientes/<int:client_id>/criancas", methods=["POST"])
@api_login_required
def api_clientes_criancas_inserir(client_id: int) -> Any:
    """Guarda o aniversário de uma criança, com o aceite explícito da responsável."""
    negado = _negado()
    if negado:
        return negado
    client = _ficha_ou_404(client_id)
    if client is None:
        return json_error("Cliente não encontrada", 404)
    corpo = request.get_json(silent=True) or {}
    try:
        origem = consentimento_ops.validar_origem_da_equipe(corpo.get("origem"))
        consentimento_ops.inserir_crianca(
            client,
            primeiro_nome=corpo.get("primeiro_nome"),
            nascimento=corpo.get("nascimento"),
            aceite=corpo.get("aceite"),
            origem=origem,
            user_id=current_user.id,
        )
    except consentimento_ops.ConsentimentoErro as exc:
        return _erro_de_consentimento(exc)
    db.session.commit()
    return jsonify(_consentimentos(client)), 201


@api_bp.route("/clientes/<int:client_id>/criancas/<int:crianca_id>", methods=["DELETE"])
@api_login_required
def api_clientes_criancas_remover(client_id: int, crianca_id: int) -> Any:
    """Apaga o nome e a data da criança (o histórico guarda só a retirada)."""
    negado = _negado()
    if negado:
        return negado
    client = _ficha_ou_404(client_id)
    if client is None:
        return json_error("Cliente não encontrada", 404)
    try:
        consentimento_ops.remover_crianca(client, crianca_id, user_id=current_user.id)
    except consentimento_ops.ConsentimentoErro as exc:
        return _erro_de_consentimento(exc)
    db.session.commit()
    return jsonify(_consentimentos(client))


# ── Indicação e parceiro da ficha ────────────────────────────────────────────────────────────────


@api_bp.route("/clientes/<int:client_id>/indicacao", methods=["PATCH"])
@api_login_required
def api_clientes_indicacao(client_id: int) -> Any:
    """Define "Indicado por" e/ou o parceiro da ficha (só as chaves presentes no corpo)."""
    negado = _negado()
    if negado:
        return negado
    client = _ficha_ou_404(client_id)
    if client is None:
        return json_error("Cliente não encontrada", 404)
    try:
        indicacao_ops.definir(client, request.get_json(silent=True) or {})
    except ClientValidationError as exc:
        return _erro_de_validacao(exc)
    db.session.commit()
    return jsonify(indicacao_ops.serializar(client))


# ── Parceiros ────────────────────────────────────────────────────────────────────────────────────


@api_bp.route("/parceiros", methods=["POST"])
@api_login_required
def api_parceiros_criar() -> Any:
    """Cadastra um parceiro (buffet, assessoria, agência ou outro) com a comissão declarada."""
    negado = _negado()
    if negado:
        return negado
    try:
        parceiro = parceiro_ops.criar(request.get_json(silent=True) or {})
    except ClientValidationError as exc:
        return _erro_de_validacao(exc)
    db.session.commit()
    return jsonify(parceiro_ops.serializar(parceiro, 0)), 201


@api_bp.route("/parceiros/<int:parceiro_id>", methods=["PATCH"])
@api_login_required
def api_parceiros_atualizar(parceiro_id: int) -> Any:
    """Edita, desativa ou reativa o parceiro (só as chaves presentes no corpo)."""
    negado = _negado()
    if negado:
        return negado
    parceiro = db.session.get(Parceiro, parceiro_id)
    if parceiro is None:
        return json_error("Parceiro não encontrado", 404)
    try:
        parceiro_ops.atualizar(parceiro, request.get_json(silent=True) or {})
    except ClientValidationError as exc:
        return _erro_de_validacao(exc)
    db.session.commit()
    clientes = Client.query.filter_by(parceiro_id=parceiro.id).count()
    return jsonify(parceiro_ops.serializar(parceiro, clientes))


# ── Pós-evento ───────────────────────────────────────────────────────────────────────────────────


def _base_publica() -> str:
    # PUBLIC_BASE_URL, nunca request.url_root: atrás do proxy o Host é o do backend (hotfix 269b).
    return current_app.config.get("PUBLIC_BASE_URL") or ""


def _erro_do_pos_evento(exc: pos_evento_ops.PosEventoErro) -> Any:
    db.session.rollback()
    campos = {exc.campo: exc.mensagem} if exc.campo else None
    extras = {"codigo": exc.codigo} if exc.codigo else {}
    return json_error(exc.mensagem, exc.status, fields=campos, **extras)


def _registrar_pos_evento(event: CalendarEvent, corpo: dict[str, Any]) -> PosEvento:
    canal = corpo.get("canal")
    if canal not in pos_evento_ops.CANAIS:
        raise pos_evento_ops.PosEventoErro("canal", "Selecione copiar ou enviar pela conversa.")
    pos_evento_ops.exigir_vivo(event)
    fotos = pos_evento_ops.validar_fotos(corpo.get("fotos_url"))
    if canal == POS_EVENTO_CANAL_CONVERSA:
        return pos_evento_ops.enviar_pela_conversa(
            event,
            base_publica=_base_publica(),
            fotos_url=fotos,
            user_id=current_user.id,
            cfg=cfg_whatsapp(),
        )
    return pos_evento_ops.registrar(event, POS_EVENTO_CANAL_COPIADO, fotos, current_user.id)


@api_bp.route("/events/<int:event_id>/pos-evento", methods=["POST"])
@api_login_required
def api_pos_evento_registrar(event_id: int) -> Any:
    """Registra a cópia (``copiado``) ou envia pela conversa (``conversa``) o pós-evento."""
    negado = _negado()
    if negado:
        return negado
    event = db.session.get(CalendarEvent, event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    try:
        resultado = _registrar_pos_evento(event, request.get_json(silent=True) or {})
    except pos_evento_ops.PosEventoErro as exc:
        return _erro_do_pos_evento(exc)
    except EnvioRecusado as exc:
        db.session.rollback()
        return json_error(exc.mensagem, exc.status, fields=exc.fields or None, codigo=exc.codigo)
    db.session.commit()
    return jsonify(
        {
            "situacao": resultado.canal,
            "registrado_em": resultado.registrado_em.isoformat(),
            "fotos_url": resultado.fotos_url,
        }
    )
