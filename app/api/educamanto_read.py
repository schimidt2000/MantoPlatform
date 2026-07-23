"""Endpoints de LEITURA/cálculo da calculadora EducaManto (feature 171).

Só orquestra e serializa — a regra de negócio (precificação do pacote + transporte com
multiplicador de dias) mora em `app/educamanto/pricing_ops.py`, sem duplicar a fórmula aqui.
Gate `_require_use` reimplementado como função, paridade com `app/educamanto/routes.py::_CAN_USE`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.educamanto import pricing_ops, quote_ops
from app.models import EducaMantoPackage

_CAN_USE = {
    RoleName.COMERCIAL,
    RoleName.SUPERADMIN,
    RoleName.ENSAIO,
    RoleName.REVENDEDOR_EDUCAMANTO,
}


def _require_use() -> Any:
    if not {r.name.upper() for r in current_user.roles} & _CAN_USE:
        return json_error("Sem permissão", 403)
    return None


def _is_superadmin() -> bool:
    return bool({r.name.upper() for r in current_user.roles} & {RoleName.SUPERADMIN})


@api_bp.route("/educamanto/historico")
@api_login_required
def api_educamanto_historico() -> Any:
    """Histórico de orçamentos gerados — mesmos filtros da tela Jinja legada (`historico()`)."""
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


@api_bp.route("/educamanto/packages")
@api_login_required
def api_educamanto_packages() -> Any:
    """Lista os pacotes para o seletor da calculadora (mesmo dado do `packages_json` do Jinja)."""
    denied = _require_use()
    if denied:
        return denied
    packages = EducaMantoPackage.query.order_by(EducaMantoPackage.id).all()
    return jsonify({"packages": [p.to_dict() for p in packages]})


@api_bp.route("/educamanto/distancia")
@api_login_required
def api_educamanto_distancia() -> Any:
    """Distância até o endereço do evento — mesmo cálculo de `GET /educamanto/api/distancia`."""
    denied = _require_use()
    if denied:
        return denied
    from app.maps import distance_km_ida

    km_ida, error, status = distance_km_ida(request.args.get("endereco", ""))
    if error:
        return json_error(error, status)
    return jsonify({"km_ida": km_ida})


def _int_arg(data: dict, key: str, default: int = 0) -> int:
    try:
        return max(int(data.get(key) or default), 0)
    except (TypeError, ValueError):
        return default


def _float_arg(data: dict, key: str, default: float = 0.0) -> float:
    try:
        return max(float(data.get(key) or default), 0.0)
    except (TypeError, ValueError):
        return default


@api_bp.route("/educamanto/calcular", methods=["POST"])
@api_login_required
def api_educamanto_calcular() -> Any:
    """Calcula o pacote (itens/desconto) + transporte já com o multiplicador de dias (feature 171).

    Endpoint de cálculo (não persiste nada) — usa POST pelo corpo aninhado (`transporte`), mesma
    convenção já aceita no projeto para ações de cálculo (ex.: `/educamanto/orcamento/gerar`).
    """
    denied = _require_use()
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    package = EducaMantoPackage.query.get(data.get("package_id"))
    if package is None:
        return json_error("Pacote inválido.", 400)

    d1 = _int_arg(data, "d1")
    d2 = _int_arg(data, "d2")
    if d1 + d2 <= 0:
        return json_error("Preencha os dias (1 e/ou 2 sessões) antes de calcular.", 400)

    ensemble = _int_arg(data, "ensemble")
    acrescimo = _float_arg(data, "acrescimo")

    transporte_in = data.get("transporte") or {}
    km_ida = _float_arg(transporte_in, "km_ida")
    transporte = None
    if km_ida > 0:
        pessoas = pricing_ops.pessoas_transporte(package, ensemble)
        transporte = pricing_ops.calcular_transporte(
            km_ida=km_ida,
            pessoas=pessoas,
            dias_total=d1 + d2,
        )

    resultado = pricing_ops.calcular_pacote(package, d1, d2, ensemble, acrescimo, transporte)
    return jsonify(resultado.to_dict())
