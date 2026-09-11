"""Endpoints de LEITURA do lado staff/admin de Formulários (migração 177, US7).

Não confundir com `app/api/formularios_write.py` (fluxo público `/f/*`, intocado nesta
feature). Reusa, sem duplicar, o núcleo já extraído em `app/formularios/formularios_ops.py`.

RBAC (função no início de cada view — constituição XIII; tabela em `docs/01` §4.3):
  * `_require_vendas` (COMERCIAL, FINANCEIRO, SUPERADMIN, pelo papel REAL — o "Ver como" não se
    aplica aqui, dívida 3.5): lista, busca e detalhe.
  * `_pode_criar_evento` (COMERCIAL, SUPERADMIN — o `_CAN_CREATE` da agenda): a flag do detalhe
    e os dados do formulário para o cadastro de evento (feature 298).
  * `_require_superadmin`: editor de estrutura.
"""

from datetime import datetime
from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import FORM_CLOSE_REASON_LABELS, RoleName
from app.formularios import destino_ops, formularios_ops
from app.models import Client, FormResponse
from app.notificacoes import notificacoes_ops


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_vendas() -> Any:
    if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _require_superadmin() -> Any:
    if not _has_role(RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _pode_criar_evento() -> bool:
    """Criar evento é da agenda (`_CAN_CREATE`); a lista de papéis não se repete aqui (298)."""
    from app.calendar.routes import _CAN_CREATE

    return _has_role(*_CAN_CREATE)


def _response_summary(r: FormResponse, corte: datetime) -> dict:
    """Resumo de uma resposta. ``corte`` vem calculado UMA vez por requisição (sem N+1)."""
    return {
        "id": r.id,
        "form_type": r.form_type,
        "form_type_label": r.form_type_label,
        "contact_name": r.contact_name,
        "contact_phone_display": r.contact_phone_display or "",
        "event_date": r.event_date.isoformat() if r.event_date else None,
        "client_id": r.client_id,
        # Nome do cliente já na listagem: a coluna "Situação" mostra o badge "Cliente: <nome>"
        # sem exigir que a tela abra o detalhe de cada resposta (`list_responses` faz joinedload).
        "client_name": r.client.name if r.client else None,
        # 'auto_phone' = deduzido pelo telefone no envio (feature 266); a tela sinaliza para a
        # comercial conferir, porque telefone compartilhado dá match único e errado.
        "client_link_source": r.client_link_source,
        "event_id": r.event_id,
        "event_link_source": r.event_link_source,
        "event_link_ambiguous": r.event_link_ambiguous,
        "event_link_locked": r.event_link_locked,
        "created_at": formularios_ops.iso_utc(r.created_at),
        # Feature 298: o destino (mesma regra das contagens, calculada no núcleo) e o encerramento.
        "destino": formularios_ops.destino_de(r, corte),
        "tipo_rotulo": formularios_ops.tipo_rotulo(r.form_type),
        "closed_reason": r.closed_reason,
        "closed_reason_label": FORM_CLOSE_REASON_LABELS.get(r.closed_reason or ""),
        "closed_note": r.closed_note,
        "closed_by_name": r.closed_by.name if r.closed_by else None,
        "closed_at": formularios_ops.iso_utc(r.closed_at),
    }


def _response_detail(r: FormResponse, corte: datetime) -> dict:
    return {
        **_response_summary(r, corte),
        "data_sections": r.data_sections,
        "event_title": r.event.title if r.event else None,
    }


@api_bp.route("/formularios/respostas")
@api_login_required
def api_formularios_respostas_list() -> Any:
    """Lista as respostas mais recentes + contadores por destino (cartões da tela).

    ``?filtro=`` aceita as partições de `formularios_ops.STATUS_FILTERS` (feature 298); valor
    desconhecido ou ausente lista tudo. Os contadores vêm sempre no payload — a tela pinta os
    cartões sem uma segunda chamada — e ``truncado`` avisa quando o filtro passa de 200.
    """
    denied = _require_vendas()
    if denied:
        return denied
    filtro = (request.args.get("filtro") or "").strip()
    corte = formularios_ops.corte_de_chegada()
    responses, truncado = formularios_ops.list_responses(filtro=filtro, corte=corte)
    return jsonify({
        "responses": [_response_summary(r, corte) for r in responses],
        "counts": formularios_ops.count_status(corte),
        "truncado": truncado,
    })


@api_bp.route("/formularios/respostas/search")
@api_login_required
def api_formularios_respostas_search() -> Any:
    """Busca respostas por nome/telefone (sem acentos)."""
    denied = _require_vendas()
    if denied:
        return denied
    results = formularios_ops.search_responses(request.args.get("q") or "")
    corte = formularios_ops.corte_de_chegada()
    return jsonify({"responses": [_response_summary(r, corte) for r in results]})


@api_bp.route("/formularios/respostas/<int:response_id>")
@api_login_required
def api_formularios_resposta_detail(response_id: int) -> Any:
    """Detalhe completo da resposta + sugestão de cliente por telefone."""
    denied = _require_vendas()
    if denied:
        return denied
    response = FormResponse.query.get(response_id)
    if response is None:
        return json_error("Resposta não encontrada", 404)
    # Um GET que escreve, de propósito (feature 272, decisão 12): o lead é aberto por três caminhos
    # (sino, card da Home, lista de /formularios) — marcar lida só pelo sino deixaria o badge
    # dizendo "3" para quem já tratou os três pela lista. Só as notificações DESTE usuário.
    if notificacoes_ops.marcar_lidas_por_objeto(current_user.id, "form_response", response.id):
        db.session.commit()
    suggested = None
    if response.client_id is None and response.contact_phone:
        suggested = Client.query.filter_by(phone=response.contact_phone).first()
    corte = formularios_ops.corte_de_chegada()
    destino = formularios_ops.destino_de(response, corte)
    return jsonify({
        "response": _response_detail(response, corte),
        "suggested_client": (
            {"id": suggested.id, "name": suggested.name} if suggested else None
        ),
        "can_edit_structure": _has_role(RoleName.SUPERADMIN),
        # Feature 298: os motivos vêm do servidor (a tela não tem cópia) e as flags dizem o que a
        # tela oferece — o servidor recusa o resto do mesmo jeito.
        "motivos_encerramento": destino_ops.motivos_encerramento(),
        "sugestao": destino_ops.sugestao_para(response) if destino == "sem_destino" else None,
        # Recalculada a cada leitura (FR-015): some sozinha quando alguém acerta a cliente.
        "divergencia_cliente": formularios_ops.divergencia_de_cliente(response),
        "flags": {
            "pode_encerrar": destino == "sem_destino",
            "pode_reabrir": destino == "encerrados",
            "pode_criar_evento": _pode_criar_evento(),
        },
    })


@api_bp.route("/formularios/respostas/<int:response_id>/para-evento")
@api_login_required
def api_formularios_para_evento(response_id: int) -> Any:
    """O formulário traduzido para o cadastro de evento (feature 298) — só leitura.

    Gate de quem cria evento, não de quem vê formulário: FINANCEIRO vê a lista, mas não cria
    evento. Não marca o aviso como lido — abrir o cadastro ainda não dá destino ao formulário.
    """
    if not _pode_criar_evento():
        return json_error("Sem permissão", 403)
    response = FormResponse.query.get(response_id)
    if response is None:
        return json_error("Resposta não encontrada", 404)
    if response.event_id is not None:
        return json_error(
            formularios_ops.FormularioJaTemDestino.MENSAGEM, 409, event_id=response.event_id
        )
    from app.formularios import pre_evento_ops

    return jsonify({
        "form_response": {
            "id": response.id,
            "form_type": response.form_type,
            "form_type_label": response.form_type_label,
            "contact_name": response.contact_name,
        },
        **pre_evento_ops.extrair_para_evento(response),
    })


@api_bp.route("/formularios/editor/<form_type>")
@api_login_required
def api_formularios_editor_get(form_type: str) -> Any:
    """Definição de campos de um formulário, agrupada por seção (SUPERADMIN)."""
    denied = _require_superadmin()
    if denied:
        return denied
    if form_type not in ("comum", "corporativo"):
        return json_error("Tipo de formulário inválido", 404)
    fields = formularios_ops.list_field_definitions(form_type)
    return jsonify({
        "fields": [
            {
                "id": f.id,
                "section_name": f.section_name,
                "field_key": f.field_key,
                "field_type": f.field_type,
                "label": f.label,
                "help_text": f.help_text,
                "placeholder": f.placeholder,
                "required": f.required,
                "options": f.options,
                "order": f.order,
                "is_system": f.is_system,
            }
            for f in fields
        ]
    })
