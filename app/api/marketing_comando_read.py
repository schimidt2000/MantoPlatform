"""Endpoints de LEITURA do painel de comando de marketing (feature 345).

`/api/marketing/frentes` (tetos e responsáveis), `/api/marketing/temas-licenca` (origem e
"liberado para anúncio" dos temas), `/api/marketing/propostas` e `/api/marketing/diario`. O núcleo é
`app.marketing.comando_ops`; aqui só RBAC (função no início da view) e serialização.

Feature 351: `/api/marketing/atribuicao` (vendas atribuídas e funil com custo, núcleo em
`app.marketing.atribuicao_ops`) e `/api/marketing/calendario` (meta, verba e foco por frente e mês).

RBAC: `MARKETING` ou `SUPERADMIN` (o mesmo `require_marketing_access` do módulo). As flags
`pode_editar`/`pode_decidir`/`pode_liberar_licenciado`/`pode_ver_valor` dizem à tela o que mostrar — quem
decide de verdade é o endpoint de escrita. O valor de cada venda atribuída só sai para o Superadmin real.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api.marketing_read import require_marketing_access
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.conversas.recusa import Recusa
from app.marketing import atribuicao_ops
from app.marketing import comando_ops as ops


def eh_superadmin(user: Any) -> bool:
    """True se o usuário é Superadmin de verdade (o "Ver como" não conta: decisão de dinheiro)."""
    return any(role.name.upper() == RoleName.SUPERADMIN for role in user.roles)


@api_bp.route("/marketing/frentes")
@api_login_required
def api_marketing_frentes() -> Any:
    """Tetos de custo por venda de cada frente e responsáveis por criativo."""
    denied = require_marketing_access()
    if denied:
        return denied
    return jsonify(ops.frentes_config(eh_superadmin=eh_superadmin(current_user)))


@api_bp.route("/marketing/temas-licenca")
@api_login_required
def api_marketing_temas_licenca() -> Any:
    """Temas ativos com origem e liberado (`?q&origem&liberado&sugestao=1`)."""
    denied = require_marketing_access()
    if denied:
        return denied
    dados = ops.listar_temas_licenca(
        q=(request.args.get("q") or "").strip() or None,
        origem=request.args.get("origem") or None,
        liberado=request.args.get("liberado") or None,
        so_sugestao=request.args.get("sugestao") == "1",
        pagina=request.args.get("pagina", 1, type=int) or 1,
    )
    return jsonify({**dados, "pode_liberar_licenciado": eh_superadmin(current_user)})


@api_bp.route("/marketing/propostas")
@api_login_required
def api_marketing_propostas() -> Any:
    """Propostas da rotina (pendentes primeiro) e se quem vê pode decidir."""
    denied = require_marketing_access()
    if denied:
        return denied
    propostas = ops.listar_propostas((request.args.get("situacao") or "").strip() or None)
    contexto = ops.contexto_das_propostas()
    itens = [ops.serialize_proposta(p, contexto) for p in propostas]
    return jsonify(
        {
            "items": itens,
            "pendentes": sum(1 for p in itens if p["situacao"] == "pendente"),
            "pode_decidir": eh_superadmin(current_user),
            "impacto_aprovado_mes": ops.impacto_aprovado_mes(),
        }
    )


@api_bp.route("/marketing/diario")
@api_login_required
def api_marketing_diario() -> Any:
    """Diário de decisões, com as entradas que já passaram da data de reavaliar."""
    denied = require_marketing_access()
    if denied:
        return denied
    itens = [ops.serialize_diario(e) for e in ops.listar_diario()]
    return jsonify({"items": itens, "a_reavaliar": sum(1 for e in itens if e["a_reavaliar"])})


@api_bp.route("/marketing/atribuicao")
@api_login_required
def api_marketing_atribuicao() -> Any:
    """Vendas atribuídas do período e o funil com custo (`?weeks|start&end&dividir`), feature 351."""
    denied = require_marketing_access()
    if denied:
        return denied
    dividir = request.args.get("dividir") or "frente"
    try:
        inicio, fim = atribuicao_ops.periodo_do_painel(
            request.args.get("start"), request.args.get("end"), request.args.get("weeks")
        )
    except ops.ComandoError as exc:
        return json_error(exc.message, exc.status, fields={exc.field: exc.message} if exc.field else None)
    try:
        funil = atribuicao_ops.funil_com_custo(inicio, fim, dividir)
    except Recusa as exc:
        # O funil das conversas vai até um ano; a venda atribuída não tem esse limite e continua na resposta.
        funil = {"dividir": dividir, "total": 0, "grupos": [], "aviso": exc.mensagem}
    pode_ver_valor = eh_superadmin(current_user)
    return jsonify(
        {
            "periodo": {"start": inicio.isoformat(), "end": fim.isoformat()},
            "regra": atribuicao_ops.regra(inicio),
            **atribuicao_ops.lista_vendas(inicio, fim, com_valor=pode_ver_valor),
            "funil": funil,
            "pode_ver_valor": pode_ver_valor,
        }
    )


@api_bp.route("/marketing/calendario")
@api_login_required
def api_marketing_calendario() -> Any:
    """Calendário do ano: meta, verba e foco por frente e mês (feature 351)."""
    denied = require_marketing_access()
    if denied:
        return denied
    return jsonify(ops.calendario(eh_superadmin=eh_superadmin(current_user)))
