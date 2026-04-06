"""Serviço de email da Plataforma Manto.

Usa Flask-Mail com Gmail Workspace (SMTP).
Configure as variáveis MAIL_PASSWORD (App Password) e PORTAL_URL no .env.
"""
from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from flask import current_app
from flask_mail import Mail, Message

log = logging.getLogger(__name__)
mail = Mail()

_TZ = ZoneInfo("America/Sao_Paulo")


def _sender():
    name  = current_app.config.get("MAIL_DEFAULT_SENDER_NAME", "Manto Produções")
    email = current_app.config.get("MAIL_USERNAME", "")
    return (name, email)


def _portal_url() -> str:
    return current_app.config.get("PORTAL_URL", "").rstrip("/")


# ── Email de convite ───────────────────────────────────────────────────────────

def send_invite_email(role) -> bool:
    """Envia convite por email ao talento quando o casting marcar invite_status='pending'.

    Retorna True se enviado, False se pulado (sem email) ou falhou.
    """
    talent = role.talent
    if not talent or not talent.email_contact:
        return False

    event = role.event
    start_str = (
        event.start_at.astimezone(_TZ).strftime("%d/%m/%Y às %H:%M")
        if event.start_at else "a confirmar"
    )

    portal_url = _portal_url()

    lines = [
        f"Olá, {talent.full_name.split()[0]}!",
        "",
        f"Você foi selecionado(a) para o evento \"{event.title}\" no dia {start_str}.",
        "Para ver todos os detalhes e confirmar sua participação, acesse o portal:",
        "",
        portal_url if portal_url else "Portal Manto Produções",
        "",
        "Manto Produções",
    ]

    return _send(
        to=talent.email_contact,
        subject=f"Você foi selecionado(a) — {event.title}",
        body="\n".join(lines),
    )


# ── Email de remoção de elenco ────────────────────────────────────────────────

def send_removal_email(talent, event, character_name: str) -> bool:
    """Notifica talento que foi removido de um evento."""
    if not talent or not talent.email_contact:
        return False

    start_str = (
        event.start_at.astimezone(_TZ).strftime("%d/%m/%Y")
        if event.start_at else "a confirmar"
    )

    body = "\n".join([
        f"Olá, {talent.full_name.split()[0]}!",
        "",
        f"Sua participação no evento \"{event.title}\" ({start_str}) foi removida.",
        "Em caso de dúvidas, entre em contato com a equipe da Manto.",
        "",
        "Manto Produções",
    ])

    return _send(
        to=talent.email_contact,
        subject=f"Atualização de elenco — {event.title}",
        body=body,
    )


# ── Email de alteração de evento ──────────────────────────────────────────────

def send_event_changed_email(role, changes: list[str]) -> bool:
    """Notifica talento confirmado sobre alteração no evento."""
    talent = role.talent
    if not talent or not talent.email_contact:
        return False

    event = role.event
    start_str = (
        event.start_at.astimezone(_TZ).strftime("%d/%m/%Y às %H:%M")
        if event.start_at else "a confirmar"
    )
    changes_text = "\n".join(f"  • {c}" for c in changes)
    portal_url = _portal_url()
    portal_line = (
        f"Verifique os detalhes no portal: {portal_url}"
        if portal_url else
        "Verifique os detalhes no portal da Manto."
    )

    body = "\n".join([
        f"Olá, {talent.full_name.split()[0]}!",
        "",
        f"Houve uma atualização no evento \"{event.title}\" ({start_str}):",
        changes_text,
        "",
        portal_line,
        "",
        "Manto Produções",
    ])

    return _send(
        to=talent.email_contact,
        subject=f"Atualização no evento: {event.title}",
        body=body,
    )


# ── Email de alerta para equipe de ENSAIO ────────────────────────────────────

def send_ensaio_alert_email(event, users: list) -> int:
    """Notifica usuários ENSAIO sobre evento que precisa de ensaio.

    Retorna quantidade de emails enviados com sucesso.
    """
    if not users:
        return 0

    start_str = (
        event.start_at.astimezone(_TZ).strftime("%d/%m/%Y às %H:%M")
        if event.start_at else "a confirmar"
    )
    portal_url = _portal_url()
    platform_line = f"Acesse a plataforma: {portal_url}" if portal_url else "Acesse a plataforma."

    sent = 0
    for user in users:
        if not user.email:
            continue
        lines = [
            f"Olá, {user.name.split()[0]}!",
            "",
            "Um evento marcado como PRECISA DE ENSAIO entrou na agenda:",
            "",
            f"Evento: {event.title}",
            f"Data:   {start_str}",
        ]
        if event.location:
            lines.append(f"Local:  {event.location}")
        lines += [
            "",
            "Você é responsável por agendar o ensaio.",
            "Abra o evento na plataforma e clique em 'Criar ensaio'.",
            "",
            platform_line,
            "",
            "Atenciosamente,",
            "Manto Produções",
        ]
        if _send(to=user.email, subject=f"[Ensaio necessário] {event.title}", body="\n".join(lines)):
            sent += 1
    return sent


# ── Email de reset de senha ────────────────────────────────────────────────────

def send_password_reset_email(talent, reset_url: str) -> bool:
    """Envia link de redefinição de senha para o talento."""
    if not talent.email_contact:
        return False

    body = "\n".join([
        f"Olá, {talent.full_name.split()[0]}!",
        "",
        "Recebemos uma solicitação para redefinir sua senha no portal da Manto Produções.",
        "",
        "Clique no link abaixo para criar uma nova senha (válido por 1 hora):",
        "",
        reset_url,
        "",
        "Se você não solicitou isso, ignore este email — sua senha não será alterada.",
        "",
        "Atenciosamente,",
        "Manto Produções",
    ])

    return _send(
        to=talent.email_contact,
        subject="Redefinição de senha — Portal Manto",
        body=body,
    )


# ── Email de boas-vindas com senha temporária ──────────────────────────────────

def send_welcome_email(talent, temp_password: str) -> bool:
    """Envia email de boas-vindas com a senha temporária ao talento.

    Chamado quando o admin cria ou reseta a senha de um talento.
    Retorna True se enviado com sucesso.
    """
    if not talent or not talent.email_contact:
        return False

    portal_url = _portal_url()
    first_name = (talent.artistic_name or talent.full_name or "").split()[0]

    body = "\n".join([
        f"Olá, {first_name}!",
        "",
        "Você foi cadastrado(a) no portal da Manto Produções.",
        "",
        f"Acesse: {portal_url}/portal" if portal_url else "Acesse o portal da Manto.",
        f"Usuário: {talent.cpf}",
        f"Senha: {temp_password}",
        "",
        "Troque a senha no primeiro acesso.",
        "",
        "Manto Produções",
    ])

    return _send(
        to=talent.email_contact,
        subject="Bem-vindo(a) ao Portal Manto!",
        body=body,
    )


# ── Helper interno ─────────────────────────────────────────────────────────────

def _emails_enabled() -> bool:
    """Retorna True se notificações por email estão ativadas nas configurações do admin."""
    try:
        from app.models import SiteSetting
        settings = SiteSetting.query.first()
        return bool(settings and settings.email_notifications_enabled)
    except Exception:
        return False


def _send(to: str, subject: str, body: str) -> bool:
    if not _emails_enabled():
        log.info("Email desativado nas configurações — pulando envio para %s: %s", to, subject)
        return False
    try:
        msg = Message(subject=subject, sender=_sender(), recipients=[to], body=body)
        mail.send(msg)
        log.info("Email enviado para %s: %s", to, subject)
        return True
    except Exception as exc:
        log.error("Falha ao enviar email para %s (%s): %s", to, subject, exc)
        return False
