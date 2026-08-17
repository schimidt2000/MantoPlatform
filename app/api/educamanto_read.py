"""Endpoints de LEITURA/cálculo do EducaManto por responsabilidades (feature 235).

Só orquestra e serializa — a regra de negócio mora em `app/educamanto/pricing_ops.py` e
`quote_ops.py`. Regra de visibilidade (FR-028): papéis que não são SUPERADMIN recebem apenas
os valores finais — o corte do breakdown acontece AQUI, no servidor, nunca só na tela.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.educamanto import pdf_textos, quote_ops
from app.models import EducaMantoMusical, EducaMantoQuote

_CAN_USE = {
    RoleName.COMERCIAL,
    RoleName.SUPERADMIN,
    RoleName.ENSAIO,
    RoleName.REVENDEDOR_EDUCAMANTO,
}
_CAN_VER_GESTAO = {RoleName.COMERCIAL, RoleName.SUPERADMIN}


def _require_use() -> Any:
    if not {r.name.upper() for r in current_user.roles} & _CAN_USE:
        return json_error("Sem permissão", 403)
    return None


def _is_superadmin() -> bool:
    return bool({r.name.upper() for r in current_user.roles} & {RoleName.SUPERADMIN})


def _cortar_breakdown(resultado: dict) -> dict:
    """Remove custos/breakdown para papéis não-superadmin (FR-028, SC-005).

    Fica só a allowlist: valores finais (sem/com NF, à vista), cenário, equipe, transporte de
    viagem (repasse, sem o custo do caminhão) e os campos do próprio acréscimo (necessários
    ao aviso de teto).
    """
    resultado.pop("breakdown", None)
    transporte = resultado.get("transporte")
    if isinstance(transporte, dict):
        transporte.pop("caminhao", None)
    return resultado


@api_bp.route("/educamanto/historico")
@api_login_required
def api_educamanto_historico() -> Any:
    """Histórico de orçamentos gerados — filtros de sempre; "Gerado por" só superadmin."""
    denied = _require_use()
    if denied:
        return denied

    is_superadmin = _is_superadmin()
    entries, users = quote_ops.search_history(
        query=request.args.get("q", "").strip(),
        date_from=request.args.get("date_from", "").strip(),
        date_to=request.args.get("date_to", "").strip(),
        user_id_filter=request.args.get("user_id", "").strip(),
        is_superadmin=is_superadmin,
    )
    entries_json = [
        {
            "id": e.id,
            "created_at": e.created_at.isoformat(),
            "client_name": e.client_name,
            "packages_label": e.packages_label,
            **({"user_name": e.user.name} if is_superadmin else {}),
        }
        for e in entries
    ]
    return jsonify(
        {
            "entries": entries_json,
            **({"users": [{"id": u.id, "name": u.name} for u in users]} if is_superadmin else {}),
        }
    )


@api_bp.route("/educamanto/historico/<int:quote_id>")
@api_login_required
def api_educamanto_historico_detail(quote_id: int) -> Any:
    """Snapshot congelado (v1 ou v2) — alimenta "Ver" e "Recalcular".

    Snapshots nascem sem breakdown, mas o v2 congela `transporte.caminhao` (custo interno do
    caminhão dentro de SP) — o mesmo campo que `_cortar_breakdown` esconde no cálculo. Para
    não-superadmin ele sai também aqui (FR-028): senão o histórico seria a porta dos fundos.
    """
    denied = _require_use()
    if denied:
        return denied
    quote = EducaMantoQuote.query.get(quote_id)
    if quote is None:
        return json_error("Orçamento não encontrado.", 404)
    snapshot = quote_ops.load_quote_snapshot(quote)
    if not _is_superadmin():
        for config in snapshot.get("configs") or []:
            resultado = config.get("resultado")
            if isinstance(resultado, dict):
                _cortar_breakdown(resultado)
    return jsonify(snapshot)


@api_bp.route("/educamanto/musicals")
@api_login_required
def api_educamanto_musicals() -> Any:
    """Lista de musicais.

    Sem parâmetro: payload básico (sem custos) para o seletor da calculadora — todos os
    papéis com acesso. Com ``?gestao=1``: tela de musicais (Comercial + Superadmin); custos e
    margens só entram na resposta do SUPERADMIN (FR-028).
    """
    denied = _require_use()
    if denied:
        return denied

    gestao = request.args.get("gestao") == "1"
    if gestao and not (
        {r.name.upper() for r in current_user.roles} & _CAN_VER_GESTAO
    ):
        return json_error("Sem permissão", 403)

    musicals = EducaMantoMusical.query.order_by(EducaMantoMusical.id).all()
    completo = gestao and _is_superadmin()
    return jsonify({
        "musicals": [
            m.to_dict() if completo else m.to_dict_basico() for m in musicals
        ],
        "pode_gerir": _is_superadmin(),
    })


@api_bp.route("/educamanto/musicals/<int:musical_id>")
@api_login_required
def api_educamanto_musical_detail(musical_id: int) -> Any:
    """Musical completo (custos/margens/itens) — SÓ superadmin (form de edição)."""
    if not _is_superadmin():
        return json_error("Sem permissão", 403)
    musical = EducaMantoMusical.query.get(musical_id)
    if musical is None:
        return json_error("Musical não encontrado.", 404)
    return jsonify(musical.to_dict())


@api_bp.route("/educamanto/textos")
@api_login_required
def api_educamanto_textos() -> Any:
    """Rótulos e tooltips das responsabilidades — fonte única (`pdf_textos.py`)."""
    denied = _require_use()
    if denied:
        return denied
    return jsonify({
        "ordem": list(pdf_textos.RESPONSABILIDADES_ORDEM),
        "responsabilidades": {
            chave: {"label": t["label"], "tooltip": t["tooltip"]}
            for chave, t in pdf_textos.RESPONSABILIDADES.items()
        },
    })


@api_bp.route("/educamanto/distancia")
@api_login_required
def api_educamanto_distancia() -> Any:
    """Distância até o endereço do evento — mesmo cálculo da calculadora de eventos."""
    denied = _require_use()
    if denied:
        return denied
    from app.maps import distance_km_ida

    km_ida, error, status = distance_km_ida(request.args.get("endereco", ""))
    if error:
        return json_error(error, status)
    return jsonify({"km_ida": km_ida})


@api_bp.route("/educamanto/personagens-no-dia")
@api_login_required
def api_educamanto_personagens_no_dia() -> Any:
    """Personagens já escalados na data da apresentação — evita vender o mesmo em dobro."""
    denied = _require_use()
    if denied:
        return denied
    from datetime import date

    from app.orcamento.quote_ops import personagens_no_dia

    raw = (request.args.get("date") or "").strip()
    try:
        dia = date.fromisoformat(raw)
    except ValueError:
        return jsonify({"date": None, "personagens": []})
    return jsonify({"date": raw, "personagens": personagens_no_dia(dia)})


@api_bp.route("/educamanto/calcular", methods=["POST"])
@api_login_required
def api_educamanto_calcular() -> Any:
    """Calcula UMA configuração (uma página) — nada é persistido.

    A resposta completa (com breakdown) sai só para superadmin; os demais papéis recebem a
    versão cortada por `_cortar_breakdown` (FR-028).
    """
    denied = _require_use()
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    try:
        entrada = quote_ops.parse_config_input(data)
        _, resultado, _ = quote_ops.calcular_config(entrada)
    except quote_ops.QuoteValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message} if exc.field else None)

    resposta = resultado.to_dict()
    if not _is_superadmin():
        resposta = _cortar_breakdown(resposta)
    return jsonify(resposta)
