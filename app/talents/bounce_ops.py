"""Núcleo da fila de emails devolvidos (feature 219).

Interpreta os avisos do Mail Delivery Subsystem lidos por `app/integracoes/imap_client.py`,
classifica o motivo e transforma em fila de contato para o casting.

Por que existe: o talento se cadastra com `hotmail.con` (ou com a caixa lotada) e a falha não
aparece em lugar nenhum do sistema — só como um email de devolução na caixa de quem enviou. Sem
isso, o problema só é descoberto quando alguém tenta convidar a pessoa para um evento.

O módulo é puro no sentido do CLAUDE.md (nada de `request`/`render_template`); a rede fica no
cliente IMAP e a decisão de quando varrer fica no app factory.
"""

from __future__ import annotations

import email
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import Message
from email.utils import parsedate_to_datetime

from app import db
from app.models import EmailBounce, Talent, User

log = logging.getLogger(__name__)

# Chave em `import_state` que serializa a varredura entre os workers.
_SWEEP_KEY = "email_bounces"

# Rótulos em pt-BR do motivo — a ação do casting muda com ele.
KIND_LABELS: dict[str, str] = {
    "caixa_cheia": "Caixa de entrada cheia",
    "endereco_invalido": "Endereço não existe",
    "dominio_invalido": "Domínio não existe (erro de digitação)",
    "bloqueado": "Servidor de destino bloqueou",
    "outro": "Falha na entrega",
}

# O que o casting deve fazer em cada caso — vai junto na fila para não virar adivinhação.
KIND_ACTIONS: dict[str, str] = {
    "caixa_cheia": "Avisar por WhatsApp para liberar espaço na caixa de entrada.",
    "endereco_invalido": "Confirmar o email correto e atualizar o cadastro.",
    "dominio_invalido": "Provável erro de digitação no domínio. Confirmar e corrigir o cadastro.",
    "bloqueado": "Verificar com a pessoa se o email cai em spam ou está bloqueado.",
    "outro": "Confirmar o email com a pessoa.",
}

_RE_RECIPIENT = re.compile(r"^Final-Recipient:\s*rfc822;\s*(\S+)", re.I | re.M)
_RE_ACTION = re.compile(r"^Action:\s*(\S+)", re.I | re.M)
_RE_STATUS = re.compile(r"^Status:\s*(\d\.\d+\.\d+)", re.I | re.M)
_RE_DIAGNOSTIC = re.compile(r"^Diagnostic-Code:\s*(.+)$", re.I | re.M)


def classify(status_code: str | None) -> str:
    """Traduz o código estendido do DSN (RFC 3463) no motivo que o casting entende.

    Os códigos vistos em produção: ``4.2.2``/``5.2.2`` caixa cheia · ``5.1.1`` usuário inexistente ·
    ``5.1.2`` domínio inexistente (o caso ``hotmail.con``) · ``5.7.x`` bloqueio por política.
    """
    if not status_code:
        return "outro"
    parts = status_code.split(".")
    if len(parts) != 3:
        return "outro"
    _class, subject, detail = parts
    if subject == "2" and detail == "2":
        return "caixa_cheia"
    if subject == "1" and detail == "1":
        return "endereco_invalido"
    if subject == "1" and detail == "2":
        return "dominio_invalido"
    if subject == "7":
        return "bloqueado"
    return "outro"


@dataclass
class ParsedBounce:
    """Uma devolução já interpretada, antes de casar com talento/usuário."""

    message_id: str
    email: str
    kind: str
    is_permanent: bool
    status_code: str | None
    diagnostic: str | None
    original_subject: str | None
    occurred_at: datetime


def _original_subject(msg: Message) -> str | None:
    """Assunto da mensagem que voltou (vem embutida no relatório como `message/rfc822`)."""
    for part in msg.walk():
        if part.get_content_type() in ("message/rfc822", "text/rfc822-headers"):
            payload = part.get_payload()
            inner = payload[0] if isinstance(payload, list) and payload else None
            if inner is None and isinstance(payload, str):
                inner = email.message_from_string(payload)
            if inner is not None and inner.get("Subject"):
                return str(inner.get("Subject"))[:300]
    return None


def parse_bounce(raw: bytes) -> list[ParsedBounce]:
    """Extrai as falhas de um aviso de devolução. Uma mensagem pode reportar vários destinatários.

    Devolve lista vazia quando a mensagem não é um relatório de entrega interpretável — vale para
    respostas automáticas de férias e afins, que também vêm de `postmaster` em alguns servidores.
    """
    try:
        msg = email.message_from_bytes(raw)
    except (ValueError, TypeError):
        return []

    base_message_id = (msg.get("Message-Id") or "").strip()
    if not base_message_id:
        return []

    try:
        occurred_at = parsedate_to_datetime(msg.get("Date") or "")
        occurred_at = occurred_at.replace(tzinfo=None) if occurred_at else datetime.utcnow()
    except (TypeError, ValueError):
        occurred_at = datetime.utcnow()

    subject = _original_subject(msg)
    results: list[ParsedBounce] = []

    for part in msg.walk():
        if part.get_content_type() != "message/delivery-status":
            continue
        block = part.as_string()
        recipients = _RE_RECIPIENT.findall(block)
        if not recipients:
            continue
        action_match = _RE_ACTION.search(block)
        status_match = _RE_STATUS.search(block)
        diagnostic_match = _RE_DIAGNOSTIC.search(block)

        action = (action_match.group(1) if action_match else "").lower()
        status_code = status_match.group(1) if status_match else None
        # "delayed" = o servidor ainda vai retentar (é o aviso de 46h da caixa cheia); só
        # "failed" e código 5.x.x são definitivos.
        is_permanent = action == "failed" or bool(status_code and status_code.startswith("5"))

        for index, recipient in enumerate(recipients):
            address = recipient.strip().strip("<>").lower()
            if "@" not in address:
                continue
            results.append(
                ParsedBounce(
                    # Uma mensagem pode reportar N destinatários: o índice mantém o
                    # `message_id` único por falha sem perder a trava de idempotência.
                    message_id=f"{base_message_id}#{index}" if index else base_message_id,
                    email=address,
                    kind=classify(status_code),
                    is_permanent=is_permanent,
                    status_code=status_code,
                    diagnostic=(diagnostic_match.group(1).strip()[:500]
                                if diagnostic_match else None),
                    original_subject=subject,
                    occurred_at=occurred_at,
                )
            )
    return results


def _known_owners(addresses: set[str]) -> dict[str, tuple[int | None, int | None]]:
    """Casa endereços com talento/usuário. Chave: email minúsculo → ``(talent_id, user_id)``."""
    if not addresses:
        return {}
    wanted = list(addresses)
    owners: dict[str, tuple[int | None, int | None]] = {}
    for talent in Talent.query.filter(db.func.lower(Talent.email_contact).in_(wanted)).all():
        owners[(talent.email_contact or "").lower()] = (talent.id, None)
    for user in User.query.filter(db.func.lower(User.email).in_(wanted)).all():
        key = (user.email or "").lower()
        talent_id = owners.get(key, (None, None))[0]
        owners[key] = (talent_id, user.id)
    return owners


def ingest(raw_messages: list[bytes]) -> dict:
    """Grava as devoluções novas cujo destinatário é gente da plataforma.

    **Devolução de endereço desconhecido é descartada de propósito**: a caixa é a pessoal de quem
    opera a conta, e guardar contato alheio no banco seria coleta de dado que ninguém pediu. O
    total ignorado volta no resultado para a decisão não ficar invisível.

    Returns:
        ``{"lidas", "novas", "ignoradas_desconhecidas", "ja_conhecidas"}``.
    """
    parsed: list[ParsedBounce] = []
    for raw in raw_messages:
        parsed.extend(parse_bounce(raw))

    if not parsed:
        return {"lidas": len(raw_messages), "novas": 0,
                "ignoradas_desconhecidas": 0, "ja_conhecidas": 0}

    owners = _known_owners({item.email for item in parsed})
    known_ids = {
        row[0]
        for row in db.session.query(EmailBounce.message_id).filter(
            EmailBounce.message_id.in_([item.message_id for item in parsed])
        )
    }

    novas = ignoradas = ja_conhecidas = 0
    for item in parsed:
        if item.message_id in known_ids:
            ja_conhecidas += 1
            continue
        if item.email not in owners:
            ignoradas += 1
            continue
        talent_id, user_id = owners[item.email]
        db.session.add(
            EmailBounce(
                message_id=item.message_id,
                email=item.email,
                talent_id=talent_id,
                user_id=user_id,
                kind=item.kind,
                is_permanent=item.is_permanent,
                status_code=item.status_code,
                diagnostic=item.diagnostic,
                original_subject=item.original_subject,
                occurred_at=item.occurred_at,
            )
        )
        known_ids.add(item.message_id)  # a mesma varredura pode trazer a mensagem duplicada
        novas += 1

    if novas:
        db.session.commit()
    return {
        "lidas": len(raw_messages),
        "novas": novas,
        "ignoradas_desconhecidas": ignoradas,
        "ja_conhecidas": ja_conhecidas,
    }


def sweep(username: str, password: str, lookback_days: int = 90, limit: int = 300) -> dict:
    """Lê a caixa e ingere as devoluções novas. Ponto de entrada da thread de varredura.

    Recebe credencial e janela por argumento (em vez de ler `current_app`) para o núcleo continuar
    independente do Flask — quem sabe de config é o app factory.
    """
    from app.integracoes.imap_client import fetch_bounce_messages

    raw_messages = fetch_bounce_messages(username, password, lookback_days, limit)
    return ingest(raw_messages)


def claim_sweep(interval_seconds: int) -> bool:
    """Reivindica o ciclo de varredura de forma atômica entre os workers do gunicorn.

    Mesmo padrão de `app/calendar/sync.py::_claim_auto_sync`: um ``UPDATE`` condicional em
    `import_state` — só um processo ganha o ciclo, então N workers não abrem N conexões IMAP.
    """
    from sqlalchemy import text

    from app.models import ImportState

    now = datetime.utcnow()
    threshold = now - timedelta(seconds=interval_seconds)
    if not ImportState.query.filter_by(key=_SWEEP_KEY).first():
        db.session.add(ImportState(key=_SWEEP_KEY, last_row=0))
        db.session.commit()

    result = db.session.execute(
        text(
            "UPDATE import_state SET last_checked_at = :now "
            "WHERE key = :key AND (last_checked_at IS NULL OR last_checked_at < :threshold)"
        ),
        {"now": now, "threshold": threshold, "key": _SWEEP_KEY},
    )
    db.session.commit()
    return result.rowcount == 1


def pending_queue(include_resolved: bool = False) -> list[dict]:
    """Fila de contato, **agrupada por endereço** — não por mensagem.

    Uma caixa cheia gera um aviso por tentativa; o casting precisa de uma linha por pessoa, com
    quantas vezes falhou. Ordena por definitivo primeiro (endereço errado é mais urgente que caixa
    cheia) e depois pela falha mais recente.
    """
    query = EmailBounce.query
    if not include_resolved:
        query = query.filter(EmailBounce.resolved_at.is_(None))

    grouped: dict[str, dict] = {}
    for bounce in query.order_by(EmailBounce.occurred_at.desc()).all():
        entry = grouped.get(bounce.email)
        if entry is None:
            talent = bounce.talent
            grouped[bounce.email] = {
                "email": bounce.email,
                "kind": bounce.kind,
                "kind_label": KIND_LABELS.get(bounce.kind, KIND_LABELS["outro"]),
                "action_hint": KIND_ACTIONS.get(bounce.kind, KIND_ACTIONS["outro"]),
                "is_permanent": bounce.is_permanent,
                "status_code": bounce.status_code,
                "occurrences": 1,
                "last_seen_at": bounce.occurred_at.isoformat(),
                "original_subject": bounce.original_subject,
                "talent_id": bounce.talent_id,
                "talent_name": (talent.artistic_name or talent.full_name) if talent else None,
                "talent_phone": talent.phone if talent else None,
                "talent_status": talent.status if talent else None,
                "user_id": bounce.user_id,
                "user_name": bounce.user.name if bounce.user else None,
                "resolved_at": bounce.resolved_at.isoformat() if bounce.resolved_at else None,
            }
            continue
        entry["occurrences"] += 1
        # A lista vem da mais recente para a mais antiga: a primeira já é a mais nova, mas uma
        # falha definitiva mais antiga vale mais que um "delayed" recente — endereço errado não
        # deixa de estar errado porque a última tentativa foi só um atraso.
        if bounce.is_permanent and not entry["is_permanent"]:
            entry.update(
                kind=bounce.kind,
                kind_label=KIND_LABELS.get(bounce.kind, KIND_LABELS["outro"]),
                action_hint=KIND_ACTIONS.get(bounce.kind, KIND_ACTIONS["outro"]),
                is_permanent=True,
                status_code=bounce.status_code,
            )

    # Duas ordenações em vez de uma chave composta: as direções são opostas (definitivo primeiro,
    # mais recente primeiro) e o `sort` do Python é estável, então a segunda preserva a primeira.
    by_recency = sorted(grouped.values(), key=lambda item: item["last_seen_at"], reverse=True)
    return sorted(by_recency, key=lambda item: not item["is_permanent"])


def pending_count() -> int:
    """Quantos endereços distintos estão aguardando contato — o número do contador da aba."""
    return (
        db.session.query(EmailBounce.email)
        .filter(EmailBounce.resolved_at.is_(None))
        .distinct()
        .count()
    )


def resolve_email(
    address: str, actor_id: int | None, note: str | None = None, *, commit: bool = True
) -> int:
    """Marca como resolvidas **todas** as devoluções de um endereço.

    A resolução é por pessoa, não por mensagem: quando o casting fala com alguém e corrige (ou
    confirma) o email, as dez tentativas falhas daquele endereço saem da fila juntas.

    Args:
        commit: ``False`` quando a chamada acontece no meio de outra transação (a edição da ficha
            do talento), para não gravar um estado parcial antes de o chamador terminar.

    Returns:
        Quantas linhas saíram da fila.
    """
    updated = (
        EmailBounce.query.filter(
            db.func.lower(EmailBounce.email) == (address or "").lower(),
            EmailBounce.resolved_at.is_(None),
        ).update(
            {
                "resolved_at": datetime.utcnow(),
                "resolved_by_id": actor_id,
                "resolution_note": (note or "").strip() or None,
            },
            synchronize_session=False,
        )
    )
    if commit:
        db.session.commit()
    return updated


def clear_for_email(address: str) -> int:
    """Tira da fila as devoluções de um endereço que deixou de ser usado.

    Chamada quando o email do talento é corrigido: as falhas do endereço antigo não são mais
    pendência de ninguém, e mantê-las na fila só produziria contato repetido. Não commita — quem
    edita a ficha é que fecha a transação.
    """
    if not address:
        return 0
    return resolve_email(
        address, actor_id=None, note="Email do cadastro foi alterado.", commit=False
    )
