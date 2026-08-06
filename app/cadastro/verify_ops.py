"""Confirmação do email do cadastro público (feature 219).

Desenho central: a confirmação acontece **depois** do envio, com o `Talent` já gravado como
`pending`. O formulário é longo (dados, medidas, PIX, três fotos e documento) — bloquear o envio
numa confirmação por email significaria arriscar tudo isso numa caixa que talvez nem exista. Assim
nada do que a pessoa preencheu depende do email funcionar.

O `email_verify_token` faz dois papéis de propósito: é o link que confirma **e** a credencial da
tela de sucesso para corrigir o endereço e reenviar. Confirmar zera o token, fechando os dois.
"""

from __future__ import annotations

import re
import secrets
from datetime import datetime

from app import db
from app.models import Talent

# Validação deliberadamente frouxa: barrar formato exótico rejeitaria email válido de gente real.
# Quem separa o certo do errado é a confirmação — e, quando ela falha, a fila de devoluções.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$")

# Domínios digitados errado que aparecem no cadastro real (`hotmail.con` é caso verídico).
# Não bloqueiam nada: viram um aviso "você quis dizer…?" antes do envio.
DOMAIN_TYPOS: dict[str, str] = {
    "gmail.con": "gmail.com",
    "gmail.co": "gmail.com",
    "gmial.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gamil.com": "gmail.com",
    "gmail.cm": "gmail.com",
    "hotmail.con": "hotmail.com",
    "hotmail.co": "hotmail.com",
    "hotmial.com": "hotmail.com",
    "hotmail.cm": "hotmail.com",
    "outlook.con": "outlook.com",
    "outlok.com": "outlook.com",
    "yahoo.con": "yahoo.com",
    "yaho.com": "yahoo.com",
    "icloud.con": "icloud.com",
    "iclod.com": "icloud.com",
    "bol.com": "bol.com.br",
    "uol.com": "uol.com.br",
}


def is_valid_email(address: str) -> bool:
    """Formato mínimo de email — sem tentar validar existência (isso é papel da confirmação)."""
    return bool(_EMAIL_RE.match((address or "").strip()))


def suggest_correction(address: str) -> str | None:
    """Sugere o endereço certo quando o domínio é um erro de digitação conhecido.

    Returns:
        O email corrigido, ou ``None`` quando o domínio não está na lista de enganos.
    """
    clean = (address or "").strip().lower()
    if "@" not in clean:
        return None
    local, _, domain = clean.rpartition("@")
    fixed = DOMAIN_TYPOS.get(domain)
    return f"{local}@{fixed}" if fixed else None


def issue_token(talent: Talent) -> str:
    """Gera (ou regenera) o token de confirmação do talento. Não commita."""
    talent.email_verify_token = secrets.token_urlsafe(32)
    talent.email_verify_sent_at = datetime.utcnow()
    talent.email_verified_at = None
    return talent.email_verify_token


def confirm(token: str) -> Talent | None:
    """Confirma o email pelo token do link. Idempotente por consequência: o token é zerado.

    Returns:
        O talento confirmado, ou ``None`` se o token não existe (link velho ou já usado).
    """
    clean = (token or "").strip()
    if not clean:
        return None
    talent = Talent.query.filter_by(email_verify_token=clean).first()
    if talent is None:
        return None
    talent.email_verified_at = datetime.utcnow()
    talent.email_verify_token = None
    db.session.commit()
    return talent


def find_by_token(talent_id: int, token: str) -> Talent | None:
    """Talento cujo token bate — a credencial da tela de sucesso para corrigir o email."""
    clean = (token or "").strip()
    if not clean:
        return None
    return Talent.query.filter_by(id=talent_id, email_verify_token=clean).first()


def change_email(talent: Talent, new_email: str) -> tuple[bool, str | None]:
    """Troca o email do cadastro e emite um token novo. Não commita.

    Returns:
        ``(ok, erro)``. O token antigo deixa de valer — o link do email errado morre junto.
    """
    clean = (new_email or "").strip()
    if not is_valid_email(clean):
        return False, "Informe um e-mail válido."
    if clean.lower() == (talent.email_contact or "").lower():
        return True, None  # mesmo endereço: só reenviar, sem invalidar nada à toa

    from app.talents import bounce_ops

    antigo = talent.email_contact
    talent.email_contact = clean
    if antigo:
        # O endereço antigo saiu de cena: as devoluções dele não são pendência de ninguém.
        bounce_ops.clear_for_email(antigo)
    issue_token(talent)
    return True, None
