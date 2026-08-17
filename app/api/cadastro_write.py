"""Endpoints do cadastro público de talentos em React (feature 162, 2ª fatia da US5).

Reaproveita 100% da regra de negócio já em `app/cadastro/cadastro_ops.py` (feature 086,
extraída na 162) — este módulo só traduz o resultado em JSON. Público (sem `@login_required`/
RBAC). São os ÚNICOS endpoints do cadastro: o formulário Jinja que rodava em paralelo foi
aposentado, e `/cadastro` passou a ser o endereço da SPA (ver `frontend/server.js`).

Feature 219 acrescentou a confirmação de email — sempre **depois** da gravação do `Talent`, nunca
como condição para ela: o formulário tem três fotos e um documento, e perder isso porque a pessoa
digitou o domínio errado seria trocar um problema por outro pior.
"""

from typing import Any

from flask import current_app, jsonify, request

from app import db, limiter
from app.api import api_bp
from app.api_utils import json_error
from app.cadastro import verify_ops
from app.cadastro.cadastro_ops import check_cpf_exists, process_submission


def _confirm_url(token: str) -> str:
    """Link de confirmação na SPA pública, na URL curta `/cadastro`.

    Os e-mails emitidos antes disso apontam para `/catalogo/cadastro/confirmar/<token>`, e o
    token não expira: aquele endereço continua servido pelo mesmo bundle (ver
    ``frontend/server.js`` e ``apps/public/src/App.tsx``) e não pode ser desativado.
    """
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    return f"{base}/cadastro/confirmar/{token}"


def _send_confirmation(talent) -> None:
    """Dispara o email de confirmação em background (não segura a resposta do formulário)."""
    from app.email_service import send_async, send_cadastro_confirmation_email

    send_async(send_cadastro_confirmation_email, talent, _confirm_url(talent.email_verify_token))


@api_bp.route("/cadastro/check-cpf")
@limiter.limit("60 per hour")
def api_cadastro_check_cpf() -> Any:
    """Checagem de CPF em tempo real, enquanto a pessoa digita os 11 dígitos."""
    exists, valid = check_cpf_exists(request.args.get("cpf") or "")
    return jsonify({"exists": exists, "valid": valid})


@api_bp.route("/cadastro", methods=["POST"])
@limiter.limit("10 per hour")
def api_cadastro_submit() -> Any:
    """Recebe o cadastro público (multipart) e cria um talento pendente.

    Honeypot preenchido responde 201 com `id: None` (mesmo comportamento silencioso do
    redirect do Jinja) — não revela ao remetente automatizado que foi bloqueado.

    Devolve também `email` e `verify_token` (feature 219): a tela de sucesso usa os dois para
    mostrar o endereço, permitir a correção e reenviar, sem tocar em nada do que já foi enviado.
    """
    outcome = process_submission(request.form, request.files)

    if outcome.honeypot:
        return jsonify({"id": None}), 201

    if outcome.error:
        fields = {outcome.field: outcome.error} if outcome.field else None
        return json_error(outcome.error, 400, fields=fields)

    verify_ops.issue_token(outcome.talent)
    db.session.add(outcome.talent)
    db.session.commit()
    _send_confirmation(outcome.talent)
    return jsonify(
        {
            "id": outcome.talent.id,
            "email": outcome.talent.email_contact,
            "verify_token": outcome.talent.email_verify_token,
        }
    ), 201


@api_bp.route("/cadastro/confirmar", methods=["POST"])
@limiter.limit("30 per hour")
def api_cadastro_confirmar() -> Any:
    """Confirma o email pelo token do link (feature 219).

    Token desconhecido responde 404 sem distinguir "nunca existiu" de "já foi usado" — a tela
    trata os dois do mesmo jeito, e um link já confirmado não é erro do ponto de vista de quem
    clicou duas vezes.
    """
    body = request.get_json(silent=True) or {}
    talent = verify_ops.confirm(body.get("token") or "")
    if talent is None:
        return json_error("Link inválido ou já utilizado", 404)
    return jsonify({"ok": True, "email": talent.email_contact, "name": talent.full_name})


@api_bp.route("/cadastro/reenviar", methods=["POST"])
@limiter.limit("10 per hour")
def api_cadastro_reenviar() -> Any:
    """Corrige o email do cadastro e/ou reenvia a confirmação (feature 219).

    Autenticado pelo par `id` + `verify_token` devolvido no envio: é o que a tela de sucesso tem
    em mãos, e some assim que o email é confirmado. Corrigir aqui **só toca o campo de email** —
    fotos, documento e o resto do formulário não são reenviados nem revalidados.
    """
    body = request.get_json(silent=True) or {}
    try:
        talent_id = int(body.get("id") or 0)
    except (TypeError, ValueError):
        return json_error("Cadastro não encontrado", 404)

    talent = verify_ops.find_by_token(talent_id, body.get("token") or "")
    if talent is None:
        return json_error("Cadastro não encontrado ou já confirmado", 404)

    novo_email = (body.get("email") or "").strip()
    if novo_email:
        ok, erro = verify_ops.change_email(talent, novo_email)
        if not ok:
            return json_error(erro or "E-mail inválido", 400, fields={"email": erro})
    else:
        verify_ops.issue_token(talent)

    db.session.commit()
    _send_confirmation(talent)
    return jsonify(
        {
            "ok": True,
            "email": talent.email_contact,
            # O token muda a cada emissão: a tela precisa do novo para uma eventual 2ª correção.
            "verify_token": talent.email_verify_token,
        }
    )
