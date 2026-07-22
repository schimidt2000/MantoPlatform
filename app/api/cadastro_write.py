"""Endpoints do cadastro público de talentos em React (feature 162, 2ª fatia da US5).

Reaproveita 100% da regra de negócio já em `app/cadastro/cadastro_ops.py` (feature 086,
extraída na 162) — este módulo só traduz o resultado em JSON. Público (sem `@login_required`/
RBAC), mesma acessibilidade do blueprint `cadastro_bp` hoje. A rota Jinja `/cadastro/*` continua
no ar em paralelo (ver `specs/162-cadastro-publico-react/plan.md`).
"""

from typing import Any

from flask import jsonify, request

from app import db, limiter
from app.api import api_bp
from app.api_utils import json_error
from app.cadastro.cadastro_ops import check_cpf_exists, process_submission


@api_bp.route("/cadastro/check-cpf")
@limiter.limit("60 per hour")
def api_cadastro_check_cpf() -> Any:
    """Checagem de CPF em tempo real (paridade com `cadastro_bp.check_cpf`)."""
    exists, valid = check_cpf_exists(request.args.get("cpf") or "")
    return jsonify({"exists": exists, "valid": valid})


@api_bp.route("/cadastro", methods=["POST"])
@limiter.limit("10 per hour")
def api_cadastro_submit() -> Any:
    """Recebe o cadastro público (multipart) e cria um talento pendente.

    Honeypot preenchido responde 201 com `id: None` (mesmo comportamento silencioso do
    redirect do Jinja) — não revela ao remetente automatizado que foi bloqueado.
    """
    outcome = process_submission(request.form, request.files)

    if outcome.honeypot:
        return jsonify({"id": None}), 201

    if outcome.error:
        fields = {outcome.field: outcome.error} if outcome.field else None
        return json_error(outcome.error, 400, fields=fields)

    db.session.add(outcome.talent)
    db.session.commit()
    return jsonify({"id": outcome.talent.id}), 201
