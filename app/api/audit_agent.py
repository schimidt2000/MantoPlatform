"""Endpoints do agente auditor financeiro (feature 221).

O auditor roda FORA do Railway (máquina local, via Claude Code) e precisa de duas coisas que
só existem em produção: os bytes dos comprovantes (volume `instance/uploads/`) e o remetente
de e-mail configurado. Estes endpoints entregam exatamente isso — nada além:

* ``GET  /api/audit-agent/<token>/file/<path>``  — download read-only de um comprovante.
* ``POST /api/audit-agent/<token>/report``       — envia o relatório semanal por e-mail.
* ``GET  /api/audit-agent/<token>/orphan-attachments`` — arquivos do volume sem linha no
  banco (hotfix 257), para recuperar os anexos que o bug de commit deixou órfãos.

Autenticação por token de ambiente (``AUDIT_AGENT_TOKEN``), no molde do webhook da
InfinitePay: token errado ou ausente responde **404** (403 confirmaria que o endereço
existe), e sem token configurado nenhum pedido é aceito.

O agente é somente leitura sobre o ERP: nenhum endpoint aqui escreve no banco.
"""

import logging
import os
import re
from datetime import datetime, timedelta
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


# ── Anexos órfãos (hotfix 257) ────────────────────────────────────────────────
#
# O bug de commit (feature 153 → hotfix 257) salvava o arquivo no volume e perdia a linha do
# banco. Este endpoint lista o que ficou órfão para a recuperação manual — somente leitura:
# nada é apagado nem re-vinculado por aqui.

# Pasta física → colunas que apontam para ela.
ORPHAN_SOURCES: dict[str, tuple[tuple[str, str], ...]] = {
    "payments": (
        ("event_payments", "file_path"),
        ("event_reimbursements", "invoice_file_path"),
        ("event_reimbursements", "receipt_file_path"),
        # Adiantamento de salário grava no MESMO volume (`adv_<sp>_<id>_arquivo`) por outro
        # caminho (`financeiro`), e sem esta linha todo adiantamento apareceria como órfão.
        ("salary_advances", "proof"),
    ),
    "contracts": (("event_contracts", "file_path"),),
    "invoices": (("event_invoices", "file"), ("calendar_events", "invoice_file")),
}
# Carimbo que `_save_bounded_upload` põe no nome: 20260821124233_668f58_nome.pdf
_PREFIXO_CARIMBO = re.compile(r"^(\d{14})_[0-9a-f]{6}_")
CANDIDATOS_MAX = 5
JANELA_EDICAO_DIAS = 1
JANELA_EVENTO_DIAS = 45


def _uploaded_at(nome: str) -> str | None:
    """Data/hora do envio, lida do carimbo no nome do arquivo (quando houver)."""
    achado = _PREFIXO_CARIMBO.match(nome)
    if not achado:
        return None
    try:
        return datetime.strptime(achado.group(1), "%Y%m%d%H%M%S").isoformat()
    except ValueError:
        return None


def _caminhos_no_banco(subpasta: str) -> set[str]:
    """Todos os caminhos já referenciados por alguma linha, para a pasta pedida."""
    from app import db

    usados: set[str] = set()
    for tabela, coluna in ORPHAN_SOURCES[subpasta]:
        # Nomes de tabela/coluna vêm do dicionário fixo acima, nunca do request.
        linhas = db.session.execute(
            db.text(f"SELECT {coluna} AS caminho FROM {tabela} WHERE {coluna} IS NOT NULL")  # noqa: S608
        ).scalars()
        # Compara pelo NOME do arquivo: colunas antigas guardam só o nome, outras o caminho
        # público inteiro — casar string crua marcaria arquivo em uso como órfão.
        usados.update(str(v).strip().replace("\\", "/").rsplit("/", 1)[-1] for v in linhas if v)
    return usados


def _evento_resumo(linha: Any, *, com_saldo: bool = False) -> dict[str, Any]:
    resumo = {
        "event_id": linha["id"],
        "title": linha["title"],
        "start_at": linha["dia"],
        "sale_value": str(linha["sale_value"]) if linha["sale_value"] is not None else None,
    }
    if com_saldo:
        resumo["received"] = str(linha["recebido"])
    return resumo


def _candidatos(enviado_em: str | None) -> dict[str, Any]:
    """Eventos que podem ser o dono do arquivo: mexidos na hora do envio, ou com saldo em aberto."""
    from app import db

    vazio: dict[str, Any] = {"editados_perto": [], "com_saldo_aberto": []}
    if not enviado_em:
        return vazio
    quando = datetime.fromisoformat(enviado_em)
    editados = db.session.execute(
        db.text(
            "SELECT id, title, to_char(start_at, 'YYYY-MM-DD') AS dia, sale_value "
            "FROM calendar_events WHERE updated_at BETWEEN :ini AND :fim "
            "ORDER BY abs(EXTRACT(EPOCH FROM (updated_at - :quando))) LIMIT :lim"
        ),
        {
            "ini": quando - timedelta(days=JANELA_EDICAO_DIAS),
            "fim": quando + timedelta(days=JANELA_EDICAO_DIAS),
            "quando": quando,
            "lim": CANDIDATOS_MAX,
        },
    ).mappings().all()
    com_saldo = db.session.execute(
        db.text(
            "SELECT e.id, e.title, to_char(e.start_at, 'YYYY-MM-DD') AS dia, e.sale_value, "
            "COALESCE((SELECT SUM(p.amount) FROM event_payments p WHERE p.event_id = e.id), 0) AS recebido "
            "FROM calendar_events e "
            "WHERE e.sale_value > 0 AND e.cancelled_at IS NULL "
            "AND e.start_at BETWEEN :ini AND :fim "
            "AND COALESCE((SELECT SUM(p.amount) FROM event_payments p WHERE p.event_id = e.id), 0) < e.sale_value "
            "ORDER BY abs(EXTRACT(EPOCH FROM (e.start_at - :quando))) LIMIT :lim"
        ),
        {
            "ini": quando - timedelta(days=JANELA_EVENTO_DIAS),
            "fim": quando + timedelta(days=JANELA_EVENTO_DIAS),
            "quando": quando,
            "lim": CANDIDATOS_MAX,
        },
    ).mappings().all()
    return {
        "editados_perto": [_evento_resumo(linha) for linha in editados],
        "com_saldo_aberto": [_evento_resumo(linha, com_saldo=True) for linha in com_saldo],
    }


def _orfaos_da_pasta(subpasta: str, upload_root: str, *, com_candidatos: bool) -> dict[str, Any]:
    """Arquivos da pasta que nenhuma linha do banco referencia."""
    pasta = os.path.join(upload_root, subpasta)
    if not os.path.isdir(pasta):
        return {"files_total": 0, "orphans": [], "note": "pasta inexistente"}
    usados = _caminhos_no_banco(subpasta)
    arquivos = sorted(os.listdir(pasta))
    orfaos: list[dict[str, Any]] = []
    for nome in arquivos:
        caminho_absoluto = os.path.join(pasta, nome)
        if not os.path.isfile(caminho_absoluto):
            continue
        publico = f"/uploads/{subpasta}/{nome}"
        if nome in usados:
            continue
        enviado_em = _uploaded_at(nome)
        item: dict[str, Any] = {
            "file": publico,
            "filename": nome,
            "size_bytes": os.path.getsize(caminho_absoluto),
            "uploaded_at": enviado_em,
            "modified_at": datetime.utcfromtimestamp(os.path.getmtime(caminho_absoluto)).isoformat(),
        }
        if com_candidatos:
            item["candidates"] = _candidatos(enviado_em)
        orfaos.append(item)
    orfaos.sort(key=lambda o: o["uploaded_at"] or o["modified_at"], reverse=True)
    return {"files_total": len(arquivos), "orphans": orfaos}


@api_bp.route("/audit-agent/<token>/orphan-attachments", methods=["GET"])
def api_audit_agent_orphan_attachments(token: str) -> Any:
    """Lista arquivos das pastas de anexo que não têm linha correspondente no banco.

    Existe por causa do hotfix 257: o upload era salvo no volume e o registro se perdia, então
    os bytes continuam lá, órfãos. Somente leitura — enumera o volume, cruza com as colunas que
    guardam caminho e devolve cada órfão com data de envio, tamanho e eventos candidatos. Não
    apaga nem re-vincula: a decisão é humana.
    """
    if not _token_valido(token):
        return jsonify({"error": {"message": "Não encontrado"}}), 404

    com_candidatos = request.args.get("candidatos", "1") != "0"
    upload_root = current_app.config["UPLOAD_FOLDER"]
    subfolders = {
        nome: _orfaos_da_pasta(nome, upload_root, com_candidatos=com_candidatos)
        for nome in ORPHAN_SOURCES
    }
    return jsonify({
        "generated_at": datetime.utcnow().isoformat(),
        "subfolders": subfolders,
        "orphans_total": sum(len(bloco["orphans"]) for bloco in subfolders.values()),
    })
