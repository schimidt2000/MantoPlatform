"""Endpoints de LEITURA do PIX recebido por e-mail (feature 318).

Núcleo em `app/financeiro/pix_ops.py` e `app/financeiro/pix_email_ops.py`; aqui só RBAC e
serialização.

RBAC (função no início de cada view — constituição XIII; tabela em `docs/01` §4.3):
  * `_require_vendas` (COMERCIAL, FINANCEIRO, SUPERADMIN, papel REAL): a fila "PIX para conferir",
    os ligados dos últimos 30 dias e a saúde da leitura. O repasse da InfinitePay só aparece para
    FINANCEIRO/SUPERADMIN (decisão do dono: a comercial não é acionada).
  * `_require_financeiro` (FINANCEIRO, SUPERADMIN): o resumo recebido por conta × mês.
  * `_require_superadmin`: a configuração da leitura.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app import db
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.financeiro import pix_email_ops, pix_ops
from app.models import ContaRecebimento, SiteSetting


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_vendas() -> Any:
    if not _has_role(RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _require_financeiro() -> Any:
    if not _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _require_superadmin() -> Any:
    if not _has_role(RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def ve_repasse() -> bool:
    """O repasse da InfinitePay é só de quem cuida do dinheiro."""
    return _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN)


def config_json() -> dict:
    s = db.session.get(SiteSetting, 1)
    proprios = [
        linha.strip()
        for linha in ((s.pix_pagadores_proprios if s else None) or "").splitlines()
        if linha.strip()
    ]
    return {
        "ativo": bool(s and s.pix_email_ativo),
        "ativo_desde": s.pix_email_ativo_desde.isoformat(timespec="seconds")
        if s and s.pix_email_ativo_desde
        else None,
        "pagadores_proprios": proprios,
        "contas": [
            {"id": c.id, "apelido": c.apelido, "numero_conta": c.numero_conta, "ativa": c.ativa}
            for c in ContaRecebimento.query.order_by(ContaRecebimento.id).all()
        ],
    }


@api_bp.route("/pix", methods=["GET"])
@api_login_required
def api_pix_listar() -> Any:
    negado = _require_vendas()
    if negado:
        return negado
    aba = request.args.get("aba", "conferir")
    repasse = ve_repasse()
    itens = pix_ops.listar("ligados" if aba == "ligados" else "conferir", ver_repasse=repasse)
    return jsonify(
        {
            "itens": [pix_ops.para_api(p) for p in itens],
            "contagem_conferir": pix_ops.contagem_para_conferir(ver_repasse=repasse),
            "flags": {
                "pode_desfazer": repasse,
                "pode_repasse": repasse,
                "pode_resumo": repasse,
                "pode_configurar": _has_role(RoleName.SUPERADMIN),
            },
        }
    )


@api_bp.route("/pix/sem-comprovante", methods=["GET"])
@api_login_required
def api_pix_sem_comprovante() -> Any:
    """A tarefa: pagamentos registrados por PIX esperando o comprovante do banco (decisão de 23/10)."""
    negado = _require_vendas()
    if negado:
        return negado
    return jsonify({"itens": pix_ops.sem_comprovante()})


@api_bp.route("/pix/saude", methods=["GET"])
@api_login_required
def api_pix_saude() -> Any:
    negado = _require_vendas()
    if negado:
        return negado
    return jsonify(pix_email_ops.saude())


@api_bp.route("/pix/resumo-por-conta", methods=["GET"])
@api_login_required
def api_pix_resumo_por_conta() -> Any:
    negado = _require_financeiro()
    if negado:
        return negado
    try:
        meses = int(request.args.get("meses", 6))
    except ValueError:
        meses = 6
    return jsonify(pix_ops.resumo_por_conta(meses))


@api_bp.route("/pix/config", methods=["GET"])
@api_login_required
def api_pix_config() -> Any:
    negado = _require_superadmin()
    if negado:
        return negado
    return jsonify(config_json())
