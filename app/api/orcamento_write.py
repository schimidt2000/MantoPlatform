"""Endpoints de ESCRITA da Calculadora de Orçamento, Config. de Preços e Histórico (migração
177, US2/US4/US5).

Reusa, sem duplicar, o núcleo já extraído em `app/orcamento/quote_ops.py` e os módulos puros
`app/orcamento/settings.py` — os endpoints aqui só validam RBAC, parseiam o corpo JSON e
serializam.
"""

from typing import Any

from flask import Response, jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api.orcamento_read import (
    _get_entry_or_none,
    _has_role,
    _require_superadmin,
    _require_vendas,
)
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.money import parse_brl
from app.orcamento import quote_ops
from app.orcamento import settings as _cfg


@api_bp.route("/orcamento/calcular", methods=["POST"])
@api_login_required
def api_orcamento_calcular() -> Any:
    """Calcula um orçamento a partir do elenco/horas/transporte/show — não persiste."""
    denied = _require_vendas()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    try:
        result = quote_ops.calculate_quote(payload)
    except quote_ops.QuoteValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(result)


@api_bp.route("/orcamento/salvar", methods=["POST"])
@api_login_required
def api_orcamento_salvar() -> Any:
    """Persiste um orçamento já calculado (quote + snapshot) no histórico."""
    denied = _require_vendas()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    quote = body.get("quote")
    snapshot = body.get("snapshot")
    if not quote or not snapshot:
        return json_error("Orçamento inválido — recalcule antes de salvar.", 400)
    entry = quote_ops.save_quote_history(current_user, quote, snapshot)
    return jsonify({"id": entry.id}), 201


@api_bp.route("/orcamento/historico/<int:entry_id>/pdf")
@api_login_required
def api_orcamento_historico_pdf(entry_id: int) -> Any:
    """Baixa o PDF de um orçamento do histórico (a partir do snapshot congelado)."""
    denied = _require_vendas()
    if denied:
        return denied
    entry = _get_entry_or_none(entry_id, _has_role(RoleName.SUPERADMIN))
    if entry is None:
        return json_error("Orçamento não encontrado", 404)
    from app.orcamento.pdf import gerar_orcamento_pdf

    quote = quote_ops.quote_for_entry(entry)
    pdf_bytes = gerar_orcamento_pdf(quote)
    client = (quote.get("client_name") or "orcamento").replace(" ", "_")
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Orcamento_Manto_{client}.pdf"'},
    )


@api_bp.route("/orcamento/historico/<int:entry_id>/enviar-email", methods=["POST"])
@api_login_required
def api_orcamento_historico_enviar_email(entry_id: int) -> Any:
    """Envia o PDF de um orçamento do histórico por e-mail."""
    denied = _require_vendas()
    if denied:
        return denied
    entry = _get_entry_or_none(entry_id, _has_role(RoleName.SUPERADMIN))
    if entry is None:
        return json_error("Orçamento não encontrado", 404)

    body = request.get_json(silent=True) or {}
    recipient = (body.get("to") or "").strip().lower()
    if not recipient or "@" not in recipient:
        return json_error("E-mail inválido.", 400, fields={"to": "E-mail inválido."})

    from app.email_service import send_quote_email
    from app.orcamento.pdf import gerar_orcamento_pdf

    quote = quote_ops.quote_for_entry(entry)
    pdf_bytes = gerar_orcamento_pdf(quote)
    ok = send_quote_email(to=recipient, client_name=quote.get("client_name") or "", pdf_bytes=pdf_bytes)
    if not ok:
        return json_error("Falha ao enviar e-mail. Verifique as configurações de e-mail do sistema.", 502)
    return jsonify({"sent": True})


@api_bp.route("/orcamento/historico/<int:entry_id>", methods=["DELETE"])
@api_login_required
def api_orcamento_historico_delete(entry_id: int) -> Any:
    """Exclui um orçamento do histórico (dono ou SUPERADMIN)."""
    denied = _require_vendas()
    if denied:
        return denied
    entry = _get_entry_or_none(entry_id, _has_role(RoleName.SUPERADMIN))
    if entry is None:
        return json_error("Orçamento não encontrado", 404)
    from app import db

    db.session.delete(entry)
    db.session.commit()
    return "", 204


# ══════════════════════════════════════════════════════════════════
#  Configuração de Preços (SUPERADMIN)
# ══════════════════════════════════════════════════════════════════


def _to_money(raw: Any, default: float) -> float:
    """Converte um preço em R$ vindo do corpo JSON (aceita string BR ou número); cai no default."""
    if raw is None:
        return float(default)
    if isinstance(raw, (int, float)):
        return float(raw)
    parsed = parse_brl(str(raw))
    return float(parsed) if parsed is not None else float(default)


@api_bp.route("/orcamento/settings", methods=["POST"])
@api_login_required
def api_orcamento_settings_save() -> Any:
    """Salva a configuração de preços — corpo é o dict completo (mesmo shape do GET)."""
    denied = _require_superadmin()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    s = _cfg.load()

    for modelo in ("receptivo", "show"):
        incoming = body.get("markup", {}).get(modelo)
        if incoming:
            s["markup"][modelo] = [float(v) for v in incoming]

    for group in ("ator", "cantor", "coordenador"):
        incoming_group = body.get(group) or {}
        for key in s[group]:
            if key in incoming_group:
                s[group][key] = [
                    _to_money(v, s[group][key][i]) for i, v in enumerate(incoming_group[key])
                ]

    if "tecnico_som" in body:
        s["tecnico_som"] = [_to_money(v, s["tecnico_som"][i]) for i, v in enumerate(body["tecnico_som"])]

    incoming_especiais = body.get("especiais") or {}
    for nome, val in s["especiais"].items():
        if nome not in incoming_especiais:
            continue
        incoming_val = incoming_especiais[nome]
        if isinstance(val, dict):
            for show_key in val:
                if show_key in incoming_val:
                    val[show_key] = [
                        _to_money(v, val[show_key][i]) for i, v in enumerate(incoming_val[show_key])
                    ]
        else:
            s["especiais"][nome] = [_to_money(v, val[i]) for i, v in enumerate(incoming_val)]

    if "brinde_show" in body:
        s["brinde_show"] = _to_money(body.get("brinde_show"), s.get("brinde_show", 100))

    incoming_maquiador = body.get("maquiador") or {}
    for key in s["maquiador"]:
        if key in incoming_maquiador:
            s["maquiador"][key] = _to_money(incoming_maquiador[key], s["maquiador"][key])

    incoming_transporte = body.get("transporte") or {}
    for key in s["transporte"]:
        if key in incoming_transporte:
            s["transporte"][key] = float(incoming_transporte[key])

    # Tabela única de som/iluminação do EducaManto (feature 235): custo por dia de evento de
    # cada combinação. Sem este bloco a tela salvava no vazio e o valor voltava ao default.
    incoming_som_luz = body.get("educamanto_som_luz") or {}
    for key in s["educamanto_som_luz"]:
        if key in incoming_som_luz:
            s["educamanto_som_luz"][key] = _to_money(
                incoming_som_luz[key], s["educamanto_som_luz"][key]
            )

    if "acrescimo_tipos" in body:
        novos = []
        for t in body["acrescimo_tipos"]:
            t = (t or "").strip()
            if t and t not in ("BV", "Outro") and t not in novos:
                novos.append(t)
        s["acrescimo_tipos"] = novos

    _cfg.save(s)
    return jsonify({"settings": s})


@api_bp.route("/orcamento/settings/especiais", methods=["POST"])
@api_login_required
def api_orcamento_add_especial() -> Any:
    """Adiciona um item especial novo à tabela de preços."""
    denied = _require_superadmin()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    nome = (body.get("nome") or "").strip()
    prices = body.get("prices")
    if not nome or prices is None:
        return json_error("Dados inválidos", 400)
    s = _cfg.load()
    if nome in s["especiais"]:
        return json_error(f"'{nome}' já existe", 400, fields={"nome": "já existe"})
    s["especiais"][nome] = prices
    excluidos = s.setdefault("especiais_excluidos", [])
    if nome in excluidos:
        excluidos.remove(nome)
    _cfg.save(s)
    return jsonify({"settings": s}), 201


@api_bp.route("/orcamento/settings/especiais/<nome>", methods=["DELETE"])
@api_login_required
def api_orcamento_delete_especial(nome: str) -> Any:
    """Remove um item especial da tabela de preços."""
    denied = _require_superadmin()
    if denied:
        return denied
    s = _cfg.load()
    if nome in s["especiais"]:
        del s["especiais"][nome]
    excluidos = s.setdefault("especiais_excluidos", [])
    if nome not in excluidos:
        excluidos.append(nome)
    _cfg.save(s)
    return "", 204
