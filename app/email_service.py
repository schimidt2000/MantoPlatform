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


# ── HTML email base ────────────────────────────────────────────────────────────

def _html_wrap(content_html: str, preheader: str = "") -> str:
    """Envolve o conteúdo em um template HTML de email responsivo."""
    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Manto Produções</title>
  <!--[if mso]><style>* {{font-family: Arial, sans-serif !important;}}</style><![endif]-->
</head>
<body style="margin:0;padding:0;background:#f0eff6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  {f'<div style="display:none;max-height:0;overflow:hidden;color:#f0eff6;">{preheader}</div>' if preheader else ''}
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0eff6;padding:32px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:540px;">

        <!-- HEADER -->
        <tr>
          <td style="background:#2d1f6e;border-radius:12px 12px 0 0;padding:28px 32px;text-align:center;">
            <div style="font-size:28px;font-weight:900;color:#ffffff;letter-spacing:-1px;line-height:1;">Manto</div>
            <div style="font-size:11px;font-weight:600;color:rgba(255,255,255,0.55);letter-spacing:.15em;text-transform:uppercase;margin-top:4px;">Produções</div>
          </td>
        </tr>

        <!-- BODY -->
        <tr>
          <td style="background:#ffffff;padding:32px;border-radius:0 0 12px 12px;">
            {content_html}
            <div style="margin-top:28px;padding-top:20px;border-top:1px solid #eeecf8;font-size:12px;color:#aaa;text-align:center;line-height:1.6;">
              Este email foi enviado automaticamente pela plataforma Manto Produções.<br>
              Em caso de dúvidas, fale com nossa equipe.
            </div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _info_row(label: str, value: str) -> str:
    return (
        f'<tr>'
        f'<td style="padding:5px 0;font-size:13px;color:#888;white-space:nowrap;padding-right:12px;">{label}</td>'
        f'<td style="padding:5px 0;font-size:13px;color:#1a1a2e;font-weight:600;">{value}</td>'
        f'</tr>'
    )


def _btn(text: str, url: str) -> str:
    return (
        f'<div style="text-align:center;margin:24px 0 8px;">'
        f'<a href="{url}" style="display:inline-block;background:#2d1f6e;color:#ffffff;'
        f'text-decoration:none;padding:13px 32px;border-radius:8px;font-weight:700;'
        f'font-size:14px;letter-spacing:.02em;">{text}</a>'
        f'</div>'
    )


def _greeting(first_name: str) -> str:
    return f'<p style="font-size:18px;font-weight:700;color:#1a1a2e;margin:0 0 12px;">Olá, {first_name}!</p>'


def _paragraph(text: str) -> str:
    return f'<p style="font-size:14px;color:#555;line-height:1.7;margin:0 0 16px;">{text}</p>'


def _info_box(rows_html: str) -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" style="width:100%;background:#f7f6fb;'
        f'border-left:3px solid #2d1f6e;border-radius:0 8px 8px 0;padding:14px 16px;margin:16px 0;">'
        f'{rows_html}</table>'
    )


def _alert_box(content_html: str, color: str = "#fffbea", border: str = "#f0d060", text: str = "#7a5800") -> str:
    return (
        f'<div style="background:{color};border:1px solid {border};border-radius:8px;'
        f'padding:14px 16px;margin:16px 0;font-size:13px;color:{text};line-height:1.6;">'
        f'{content_html}</div>'
    )


# ── Email de convite ───────────────────────────────────────────────────────────

def send_invite_email(role) -> bool:
    talent = role.talent
    if not talent or not talent.email_contact:
        return False

    event = role.event
    first_name = (talent.artistic_name or talent.full_name or "").split()[0]
    start_str = (
        event.start_at.astimezone(_TZ).strftime("%d/%m/%Y às %H:%M")
        if event.start_at else "a confirmar"
    )
    portal_url = _portal_url()

    rows = _info_row("Evento", event.title)
    rows += _info_row("Personagem", role.character_name)
    rows += _info_row("Data", start_str)
    if event.location:
        rows += _info_row("Local", event.location)
    if role.cache_value:
        cache_str = f"R$ {role.cache_value:,.0f}"
        if role.travel_cache:
            cache_str += f" + R$ {role.travel_cache:,.0f} transporte"
        rows += _info_row("Cachê", cache_str)

    content = (
        _greeting(first_name)
        + _paragraph("Você foi selecionado(a) para um novo evento! Acesse o portal para ver todos os detalhes e confirmar sua participação.")
        + _info_box(rows)
        + _btn("Acessar portal e confirmar →", f"{portal_url}/")
        + _paragraph(f'Se o botão não funcionar, copie e cole: <a href="{portal_url}/" style="color:#2d1f6e;">{portal_url}</a>')
    )

    return _send(
        to=talent.email_contact,
        subject=f"🎭 Novo convite: {event.title}",
        html=_html_wrap(content, preheader=f"Você foi selecionado(a) para {event.title} — acesse o portal para confirmar."),
    )


# ── Email de remoção de elenco ────────────────────────────────────────────────

def send_removal_email(talent, event, character_name: str) -> bool:
    if not talent or not talent.email_contact:
        return False

    first_name = (talent.artistic_name or talent.full_name or "").split()[0]
    start_str = (
        event.start_at.astimezone(_TZ).strftime("%d/%m/%Y")
        if event.start_at else "a confirmar"
    )

    rows = _info_row("Evento", event.title)
    rows += _info_row("Personagem", character_name)
    rows += _info_row("Data", start_str)

    content = (
        _greeting(first_name)
        + _alert_box(
            f"<strong>Sua participação neste evento foi cancelada.</strong><br>"
            f"Se isso for inesperado, entre em contato com a equipe da Manto.",
            color="#fff5f5", border="#fca5a5", text="#7f1d1d",
        )
        + _info_box(rows)
        + _paragraph("Em caso de dúvidas, fale diretamente com nossa equipe de casting.")
    )

    return _send(
        to=talent.email_contact,
        subject=f"Atualização de elenco — {event.title}",
        html=_html_wrap(content, preheader=f"Sua participação em {event.title} foi cancelada."),
    )


# ── Email de alteração de evento ──────────────────────────────────────────────

def send_event_changed_email(role, changes: list[str]) -> bool:
    talent = role.talent
    if not talent or not talent.email_contact:
        return False

    event = role.event
    first_name = (talent.artistic_name or talent.full_name or "").split()[0]
    start_str = (
        event.start_at.astimezone(_TZ).strftime("%d/%m/%Y às %H:%M")
        if event.start_at else "a confirmar"
    )
    portal_url = _portal_url()

    changes_html = "".join(f'<div style="margin-bottom:4px;">• {c}</div>' for c in changes)

    content = (
        _greeting(first_name)
        + _paragraph(f'O evento <strong>{event.title}</strong> ({start_str}) teve alterações importantes:')
        + _alert_box(changes_html)
        + _paragraph("Acesse o portal para ver todas as informações atualizadas e clique em <strong>Ciente</strong> para confirmar que você viu as mudanças.")
        + _btn("Ver detalhes no portal →", f"{portal_url}/")
    )

    return _send(
        to=talent.email_contact,
        subject=f"⚠️ Alteração no evento: {event.title}",
        html=_html_wrap(content, preheader=f"O evento {event.title} foi atualizado — verifique as mudanças."),
    )


# ── Email de anúncio do portal (envio em massa) ───────────────────────────────

def send_portal_announcement_email(talent) -> bool:
    """Anuncia o portal para um talento. Retorna True se enviado."""
    if not talent or not talent.email_contact:
        return False

    portal_url = _portal_url()
    login_url  = f"{portal_url}/" if portal_url else "#"
    first_name = (talent.artistic_name or talent.full_name or "").split()[0]

    bullets = "".join([
        '<div style="display:flex;gap:10px;margin-bottom:10px;align-items:flex-start;">'
        f'<span style="font-size:18px;line-height:1.3;">{icon}</span>'
        f'<div><div style="font-weight:700;font-size:14px;color:#1a1a2e;">{title}</div>'
        f'<div style="font-size:13px;color:#666;margin-top:2px;">{desc}</div></div></div>'
        for icon, title, desc in [
            ("📅", "Seus próximos eventos", "Veja datas, horários, locais e instruções de cada evento em que você estará."),
            ("💰", "Cachê e pagamentos", "Acompanhe o valor do seu cachê e se o pagamento já foi processado."),
            ("✅", "Confirme sua presença", "Receba convites e confirme ou recuse diretamente pelo portal."),
            ("📋", "Histórico completo", "Consulte todos os eventos que você já realizou com a Manto."),
        ]
    ])

    content = (
        _greeting(first_name)
        + _paragraph(
            "A <strong>Manto Produções</strong> lançou o seu portal exclusivo — um espaço pensado para você "
            "acompanhar tudo sobre o seu trabalho conosco de qualquer lugar, pelo celular, computador ou tablet."
        )
        + f'<div style="margin:20px 0;">{bullets}</div>'
        + _paragraph(
            f'O acesso é feito com o seu <strong>CPF</strong> e uma senha que você mesmo cria no '
            f'primeiro acesso. É rápido e seguro.'
        )
        + _btn("Acessar o portal agora →", login_url)
        + _paragraph(
            f'Ou copie o endereço: <a href="{login_url}" style="color:#2d1f6e;">'
            f'portal.mantoproducoes.com.br</a>'
        )
        + _alert_box(
            "Em caso de dúvidas para acessar, responda este email ou fale com nossa equipe — vamos te ajudar.",
            color="#f0f9ff", border="#bae6fd", text="#0c4a6e",
        )
    )

    return _send(
        to=talent.email_contact,
        subject="Conheça o seu portal exclusivo — Manto Produções",
        html=_html_wrap(
            content,
            preheader="Acompanhe eventos, cachês e pagamentos de qualquer lugar com internet.",
        ),
    )


# ── Email de alerta para equipe de ENSAIO ────────────────────────────────────

def send_ensaio_alert_email(event, users: list) -> int:
    """Notifica usuários ENSAIO sobre evento que precisa de ensaio (email interno — plain text)."""
    if not users:
        return 0

    start_str = (
        event.start_at.astimezone(_TZ).strftime("%d/%m/%Y às %H:%M")
        if event.start_at else "a confirmar"
    )
    portal_url = _portal_url()

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
            f"Acesse: {portal_url}" if portal_url else "Acesse a plataforma.",
            "",
            "Manto Produções",
        ]
        if _send(to=user.email, subject=f"[Ensaio necessário] {event.title}", body="\n".join(lines)):
            sent += 1
    return sent


# ── Email de reset de senha ────────────────────────────────────────────────────

def send_password_reset_email(talent, reset_url: str) -> bool:
    if not talent.email_contact:
        return False

    first_name = (talent.artistic_name or talent.full_name or "").split()[0]

    content = (
        _greeting(first_name)
        + _paragraph("Recebemos uma solicitação para redefinir sua senha no portal da Manto Produções.")
        + _btn("Criar nova senha →", reset_url)
        + _paragraph(f'Se o botão não funcionar, copie e cole: <a href="{reset_url}" style="color:#2d1f6e;">{reset_url}</a>')
        + _alert_box(
            "Este link é válido por <strong>1 hora</strong>. Se você não solicitou a redefinição, ignore este email — sua senha não será alterada.",
            color="#f0f9ff", border="#bae6fd", text="#0c4a6e",
        )
    )

    return _send(
        to=talent.email_contact,
        subject="🔐 Redefinição de senha — Portal Manto",
        html=_html_wrap(content, preheader="Clique para criar uma nova senha no portal Manto."),
    )


# ── Email de boas-vindas com senha temporária ──────────────────────────────────

def send_welcome_email(talent, temp_password: str) -> bool:
    if not talent or not talent.email_contact:
        return False

    portal_url = _portal_url()
    first_name = (talent.artistic_name or talent.full_name or "").split()[0]
    login_url = f"{portal_url}/" if portal_url else "#"

    rows = _info_row("Usuário (CPF)", talent.cpf or "—")
    rows += _info_row("Senha temporária", temp_password)

    content = (
        _greeting(first_name)
        + _paragraph("Seja bem-vindo(a) ao <strong>Portal Manto Produções</strong>! Seus dados de acesso estão prontos.")
        + _info_box(rows)
        + _alert_box(
            "Você será solicitado(a) a <strong>criar uma nova senha</strong> no primeiro acesso.",
            color="#f0f9ff", border="#bae6fd", text="#0c4a6e",
        )
        + _btn("Acessar o portal →", login_url)
    )

    return _send(
        to=talent.email_contact,
        subject="🎉 Bem-vindo(a) ao Portal Manto!",
        html=_html_wrap(content, preheader="Seus dados de acesso ao portal Manto Produções estão prontos."),
    )


# ── Helper interno ─────────────────────────────────────────────────────────────

def _emails_enabled() -> bool:
    try:
        from app.models import SiteSetting
        settings = SiteSetting.query.first()
        return bool(settings and settings.email_notifications_enabled)
    except Exception:
        return False


def _send(to: str, subject: str, body: str = "", html: str = "") -> bool:
    if not _emails_enabled():
        log.info("Email desativado nas configurações — pulando envio para %s: %s", to, subject)
        return False
    try:
        plain = body or _strip_html(html)
        msg = Message(
            subject=subject,
            sender=_sender(),
            recipients=[to],
            body=plain,
            html=html or None,
        )
        mail.send(msg)
        log.info("Email enviado para %s: %s", to, subject)
        return True
    except Exception as exc:
        log.error("Falha ao enviar email para %s (%s): %s", to, subject, exc)
        return False


def _strip_html(html: str) -> str:
    """Remove tags HTML para gerar fallback plain text."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
