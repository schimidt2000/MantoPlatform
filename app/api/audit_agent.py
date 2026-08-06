"""Endpoints do agente auditor financeiro (feature 221).

O auditor roda FORA do Railway (máquina local, via Claude Code) e precisa de duas coisas que
só existem em produção: os bytes dos comprovantes (volume `instance/uploads/`) e o remetente
de e-mail configurado. Estes endpoints entregam exatamente isso — nada além:

* ``GET  /api/audit-agent/<token>/file/<path>``  — download read-only de um comprovante.
* ``POST /api/audit-agent/<token>/report``       — envia o relatório semanal por e-mail.

Autenticação por token de ambiente (``AUDIT_AGENT_TOKEN``), no molde do webhook da
InfinitePay: token errado ou ausente responde **404** (403 confirmaria que o endereço
existe), e sem token configurado nenhum pedido é aceito.

O agente é somente leitura sobre o ERP: nenhum endpoint aqui escreve no banco.
"""

import logging
import os
from typing import Any

from flask import current_app, jsonify, request, send_from_directory

from app.api import api_bp
from app.api_utils import json_error
from app.storage import ALLOWED_DOCUMENT_EXTENSIONS, is_allowed_extension

logger = logging.getLogger(__name__)

# Subpastas de `instance/uploads/` que contêm documentos financeiros auditáveis. Qualquer
# outra (fotos de figurino, observações de evento...) fica fora do alcance do token.
AUDIT_FILE_SUBFOLDERS: frozenset[str] = frozenset(
    {"payments", "expenses", "invoices", "contracts"}
)

# Extensões aceitas: documento (imagem/PDF) + XML de nota fiscal.
AUDIT_FILE_EXTENSIONS: frozenset[str] = ALLOWED_DOCUMENT_EXTENSIONS | {".xml"}


def _token_valido(token: str) -> bool:
    """True se o token do path bate com ``AUDIT_AGENT_TOKEN`` do ambiente.

    Sem token configurado, nenhum pedido é aceito — um endpoint aberto de download de
    comprovantes seria vazamento de documento financeiro.
    """
    esperado = current_app.config.get("AUDIT_AGENT_TOKEN") or ""
    if not esperado:
        return False
    return token == esperado


@api_bp.route("/audit-agent/<token>/file/<path:rel_path>", methods=["GET"])
def api_audit_agent_file(token: str, rel_path: str) -> Any:
    """Serve um comprovante de `instance/uploads/` para o agente auditor.

    ``rel_path`` é o caminho relativo à raiz de uploads (ex.: ``payments/2026..._x.pdf``),
    o mesmo que os models guardam depois de remover o prefixo ``/uploads/``.
    """
    if not _token_valido(token):
        return jsonify({"error": {"message": "Não encontrado"}}), 404

    rel_norm = rel_path.replace("\\", "/").lstrip("/")
    first_segment = rel_norm.split("/", 1)[0]
    if first_segment not in AUDIT_FILE_SUBFOLDERS:
        return json_error("Subpasta fora do escopo de auditoria", 403)
    if not is_allowed_extension(rel_norm, AUDIT_FILE_EXTENSIONS):
        return json_error("Extensão fora do escopo de auditoria", 403)

    upload_root = current_app.config["UPLOAD_FOLDER"]
    if not os.path.isfile(os.path.join(upload_root, *rel_norm.split("/"))):
        # `arquivo_ausente` é um ACHADO de auditoria (delete não remove o arquivo e
        # vice-versa) — o agente registra e segue, por isso a mensagem é estável.
        return json_error("arquivo_ausente", 404)

    # `send_from_directory` usa `safe_join` por baixo: caminho com `..` vira 404.
    return send_from_directory(upload_root, rel_norm, as_attachment=True)


@api_bp.route("/audit-agent/<token>/report", methods=["POST"])
def api_audit_agent_report(token: str) -> Any:
    """Recebe o HTML do relatório semanal e o envia por e-mail aos destinatários.

    Os destinatários vêm no corpo, mas só são aceitos e-mails que pertençam a usuários
    internos ativos — se o token vazar, o endpoint não vira um disparador de e-mail
    arbitrário.
    """
    from app.email_service import send_audit_report_email
    from app.models import User

    if not _token_valido(token):
        return jsonify({"error": {"message": "Não encontrado"}}), 404

    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    html = (data.get("html") or "").strip()
    to = data.get("to") or []
    if not subject or not html or not isinstance(to, list) or not to:
        return json_error("Campos obrigatórios: subject, html, to[]", 400)

    from sqlalchemy import func

    users = User.query.filter(
        func.lower(User.email).in_([e.strip().lower() for e in to if isinstance(e, str)]),
        User.is_active.is_(True),
        User.has_access.is_(True),
    ).all()
    recusados = sorted(
        set(e.strip().lower() for e in to if isinstance(e, str))
        - set((u.email or "").lower() for u in users)
    )
    if recusados:
        logger.warning("[auditor] destinatários fora do quadro interno: %s", recusados)

    sent = send_audit_report_email(subject, html, users)
    return jsonify({"sent": sent, "rejected": recusados}), 200
