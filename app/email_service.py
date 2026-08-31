"""Serviço de email da Plataforma Manto.

Usa Flask-Mail com Gmail Workspace (SMTP).
Configure as variáveis MAIL_PASSWORD (App Password) e PORTAL_URL no .env.
"""
from __future__ import annotations

import logging
import threading
from zoneinfo import ZoneInfo

from flask import current_app
from flask_mail import Mail, Message

log = logging.getLogger(__name__)
mail = Mail()

_TZ = ZoneInfo("America/Sao_Paulo")


def send_async(fn, *args) -> None:
    """Dispara fn(*args) em background thread com app context. Não bloqueia o request.

    Objetos SQLAlchemy são convertidos em (classe, pk) antes da thread iniciar e
    recarregados com sessão limpa dentro da thread, evitando acesso concorrente
    à sessão da thread principal (erro InvalidRequestError em gthread workers).
    """
    from sqlalchemy import inspect as sa_inspect

    from app import db

    app = current_app._get_current_object()

    def _pack(arg):
        if isinstance(arg, db.Model):
            identity = sa_inspect(arg).identity  # tuple de PKs — não expira após commit
            return ("orm", type(arg), identity)
        if isinstance(arg, list):
            return ("list", [_pack(item) for item in arg])
        return ("val", arg)

    def _unpack(packed):
        if packed[0] == "orm":
            _, cls, pk = packed
            return cls.query.get(pk[0] if len(pk) == 1 else pk)
        if packed[0] == "list":
            return [_unpack(item) for item in packed[1]]
        return packed[1]  # "val"

    packed = [_pack(a) for a in args]

    def _run():
        with app.app_context():
            try:
                fn(*[_unpack(p) for p in packed])
            except Exception:
                log.exception("Erro ao enviar email em background: %s", fn.__name__)

    threading.Thread(target=_run, daemon=True).start()


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
        event.start_at.strftime("%d/%m/%Y às %H:%M")
        if event.start_at else "a confirmar"
    )
    portal_url = _portal_url()

    rows = _info_row("Evento", event.title)
    rows += _info_row("Personagem", role.character_name)
    rows += _info_row("Data", start_str)
    if event.location:
        rows += _info_row("Local", event.location)
    # Logística (só inclui o que estiver definido — sem linhas vazias)
    if event.departure_time:
        saida = f"{event.departure_time} — {event.departure_location or 'Manto Produções'}"
        rows += _info_row("Saída", saida)
    if event.makeup_time:
        maq = event.makeup_time
        if event.makeup_location:
            maq += f" — {event.makeup_location}"
        rows += _info_row("Maquiagem", maq)
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


# ── Email de lembrete de confirmação ──────────────────────────────────────────

def send_invite_reminder_email(talent, roles) -> bool:
    """Cobra a confirmação de convites que o talento recebeu e não respondeu (feature 231).

    **Um e-mail por pessoa**, listando todos os eventos dela sem resposta — nunca um e-mail por
    evento. Quem tem três convites pendentes recebe uma mensagem com os três; a regra que decide
    quem entra e quando mora em `app/calendar/invite_reminders.py`.

    Args:
        talent: Talento que vai receber (precisa ter `email_contact`).
        roles: Cargos dele sem confirmação, já filtrados pela regra e ordenados por data.

    Returns:
        `True` se o e-mail saiu.
    """
    if not talent or not talent.email_contact or not roles:
        return False

    first_name = (talent.artistic_name or talent.full_name or "").split()[0]
    portal_url = _portal_url()
    um_evento = len(roles) == 1

    linhas = ""
    for role in roles:
        event = role.event
        quando = event.start_at.strftime("%d/%m às %H:%M") if event and event.start_at else "data a confirmar"
        titulo = event.title if event else "—"
        linhas += _info_row(quando, f"{titulo} — {role.character_name or 'sem personagem'}")

    chamada = (
        "Falta a sua confirmação neste evento:"
        if um_evento
        else f"Faltam as suas confirmações nestes {len(roles)} eventos:"
    )
    content = (
        _greeting(first_name)
        + _paragraph(chamada)
        + _info_box(linhas)
        + _paragraph(
            "Confirmar leva um toque: entre no portal, abra <strong>Convites</strong> e responda "
            "<strong>Aceitar</strong> ou <strong>Recusar</strong>. Se não puder ir, recusar também "
            "ajuda — é assim que a produção consegue chamar outra pessoa a tempo."
        )
        + _btn("Confirmar no portal →", f"{portal_url}/")
        + _paragraph(
            f'Se o botão não funcionar, copie e cole: <a href="{portal_url}/" style="color:#2d1f6e;">{portal_url}</a>'
        )
    )

    # Título de evento aqui chega com 140 caracteres ("TURMA DO PETER RABBIT - GORRO VERDE +
    # TURMA DO PETER RABBIT - BLUSA AZUL + ..."), e o cliente de e-mail corta o assunto por volta
    # de 60 — sem o corte, o que sobra na caixa de entrada é o nome do personagem no meio da
    # frase, e não o pedido.
    if um_evento and roles[0].event:
        titulo = roles[0].event.title or ""
        curto = titulo if len(titulo) <= 42 else titulo[:41].rstrip() + "…"
        assunto = f"Confirme sua presença: {curto}"
    else:
        assunto = f"Confirme sua presença em {len(roles)} eventos"
    return _send(
        to=talent.email_contact,
        subject=f"🙋 {assunto}",
        html=_html_wrap(
            content,
            preheader="Sua confirmação ainda não chegou — responda pelo portal.",
        ),
    )


# ── Email de remoção de elenco ────────────────────────────────────────────────

def send_removal_email(talent, event, character_name: str) -> bool:
    if not talent or not talent.email_contact:
        return False

    first_name = (talent.artistic_name or talent.full_name or "").split()[0]
    start_str = (
        event.start_at.strftime("%d/%m/%Y")
        if event.start_at else "a confirmar"
    )

    rows = _info_row("Evento", event.title)
    rows += _info_row("Personagem", character_name)
    rows += _info_row("Data", start_str)

    content = (
        _greeting(first_name)
        + _alert_box(
            "<strong>Sua participação neste evento foi cancelada.</strong><br>"
            "Se isso for inesperado, entre em contato com a equipe da Manto.",
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
        event.start_at.strftime("%d/%m/%Y às %H:%M")
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
            'O acesso é feito com o seu <strong>CPF</strong> e uma senha que você mesmo cria no '
            'primeiro acesso. É rápido e seguro.'
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
    """Notifica usuários ENSAIO sobre evento que precisa de ensaio (email interno)."""
    if not users:
        return 0

    start_str = (
        event.start_at.strftime("%d/%m/%Y às %H:%M")
        if event.start_at else "a confirmar"
    )
    portal_url = _portal_url()

    rows = _info_row("Evento", event.title)
    rows += _info_row("Data", start_str)
    if event.location:
        rows += _info_row("Local", event.location)

    sent = 0
    for user in users:
        if not user.email:
            continue
        first_name = user.name.split()[0]
        content = (
            _greeting(first_name)
            + _paragraph("Um evento marcado como <strong>PRECISA DE ENSAIO</strong> entrou na agenda:")
            + _info_box(rows)
            + _alert_box(
                "Você é responsável por agendar o ensaio. Abra o evento na plataforma e clique em "
                "<strong>Criar ensaio</strong>.",
                color="#f0f9ff", border="#bae6fd", text="#0c4a6e",
            )
            + (_btn("Acessar a plataforma →", portal_url) if portal_url else "")
        )
        html = _html_wrap(content, preheader=f"{event.title} precisa de ensaio — agende pela plataforma.")
        if _send(to=user.email, subject=f"[Ensaio necessário] {event.title}", html=html):
            sent += 1
    return sent


# ── Email de resposta nova de formulário (feature 266) ─────────────────────────

def send_form_response_email(response, users: list) -> int:
    """Avisa o comercial que uma resposta de formulário público chegou (feature 266).

    Até a 266 o único "aviso" era o link de WhatsApp que a **própria cliente** disparava depois
    de enviar: se ela fechasse a página antes do redirect, o lead ficava salvo e invisível até
    alguém abrir `/formularios` por iniciativa própria.

    Vai só para quem pode agir no lead (COMERCIAL/SUPERADMIN, resolvido por quem chama).
    Mandar para CASTING e FIGURINO transformaria o aviso em ruído e o time aprenderia a
    ignorá-lo — e um aviso ignorado não avisa nada.

    Args:
        response: a ``FormResponse`` recém-salva.
        users: usuários internos destinatários (já filtrados por papel e por ativos).

    Returns:
        Quantos e-mails saíram.
    """
    if not users:
        return 0

    base_url = current_app.config.get("PUBLIC_BASE_URL", "").rstrip("/")
    link = f"{base_url}/formularios?resposta={response.id}" if base_url else ""
    data_festa = response.event_date.strftime("%d/%m/%Y") if response.event_date else "não informada"

    rows = _info_row("Contratante", response.contact_name or "não informado")
    rows += _info_row("Telefone", response.contact_phone_display or "não informado")
    rows += _info_row("Data da festa", data_festa)
    rows += _info_row("Formulário", response.form_type_label)

    content = (
        _paragraph("Uma nova resposta de formulário acabou de chegar:")
        + _info_box(rows)
        + (_btn("Abrir a resposta →", link) if link else "")
    )
    html = _html_wrap(
        content,
        preheader=f"{response.contact_name or 'Novo lead'} — festa em {data_festa}.",
    )
    assunto = f"[Formulário] {response.contact_name or 'Nova resposta'} — festa em {data_festa}"

    sent = 0
    for user in users:
        if not user.email:
            continue
        if _send(to=user.email, subject=assunto, html=html):
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


# ── Confirmação do email do cadastro público ──────────────────────────────────

def send_cadastro_confirmation_email(talent, confirm_url: str) -> bool:
    """Pede ao talento recém-cadastrado que confirme o próprio email (feature 219).

    É a primeira mensagem que sai para quem se cadastra — antes disso, o primeiro contato só
    acontecia no convite de um evento, semanas depois, quando o email errado já tinha custado uma
    escalação. Quando esta mensagem volta, a devolução alimenta a fila de contato do casting.
    """
    if not talent or not talent.email_contact:
        return False

    first_name = (talent.artistic_name or talent.full_name or "").split()[0]

    content = (
        _greeting(first_name)
        + _paragraph(
            "Recebemos seu cadastro no <strong>banco de talentos da Manto Produções</strong> — "
            "está tudo salvo, você não precisa preencher nada de novo."
        )
        + _paragraph(
            "Falta só confirmar que este é mesmo o seu email. É por ele que enviamos os convites "
            "de trabalho, então um endereço errado significa perder oportunidade."
        )
        + _btn("Confirmar meu email →", confirm_url)
        + _paragraph(
            f'Se o botão não funcionar, copie e cole: '
            f'<a href="{confirm_url}" style="color:#2d1f6e;">{confirm_url}</a>'
        )
        + _alert_box(
            "Não se cadastrou na Manto? Pode ignorar esta mensagem — sem a confirmação, nada "
            "acontece.",
            color="#f0f9ff", border="#bae6fd", text="#0c4a6e",
        )
    )

    return _send(
        to=talent.email_contact,
        subject="✅ Confirme seu email — Cadastro Manto Produções",
        html=_html_wrap(
            content, preheader="Um clique para confirmar seu email e receber nossos convites."
        ),
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


# ── Email de orçamento para cliente ───────────────────────────────────────────

def send_quote_email(to: str, client_name: str, pdf_bytes: bytes) -> bool:
    """Envia orçamento em PDF para o email do cliente.

    Args:
        to:          Email do destinatário (cliente).
        client_name: Nome do cliente (para personalizar a saudação).
        pdf_bytes:   PDF gerado como bytes — será anexado ao email.

    Returns:
        True se enviado com sucesso, False caso contrário.
    """
    first_name = client_name.split()[0] if client_name else "prezado(a)"

    content = (
        _greeting(first_name)
        + _paragraph(
            "É um prazer apresentar nossa proposta para o seu evento! "
            "Segue em anexo o orçamento preparado com carinho pela equipe da "
            "<strong>Manto Produções</strong>."
        )
        + _paragraph(
            "Caso tenha alguma dúvida ou queira ajustar algum detalhe, fique à vontade para responder "
            "este email ou entrar em contato pelo WhatsApp — estamos aqui para tornar o seu evento especial."
        )
        + _alert_box(
            "Proposta válida por <strong>7 dias</strong> a contar desta data.",
            color="#f0f9ff", border="#bae6fd", text="#0c4a6e",
        )
        + _paragraph(
            '<strong>Manto Produções</strong><br>'
            '📞 +55 (11) 97057-0577<br>'
            '✉️ contato@mantoproducoes.com.br'
        )
    )

    html = _html_wrap(content, preheader="Seu orçamento Manto Produções está pronto — confira em anexo.")

    try:
        from flask_mail import Message as _Message
        plain = _strip_html(html)
        msg = _Message(
            subject="Proposta Comercial — Manto Produções",
            sender=_sender(),
            recipients=[to],
            body=plain,
            html=html,
        )
        msg.attach(
            filename="Orcamento_Manto_Producoes.pdf",
            content_type="application/pdf",
            data=pdf_bytes,
        )
        if not _emails_enabled():
            log.info("Email desativado nas configurações — pulando envio de orçamento para %s", to)
            return False
        mail.send(msg)
        log.info("Orçamento enviado para %s", to)
        return True
    except Exception as exc:
        log.error("Falha ao enviar orçamento para %s: %s", to, exc)
        return False


# ── Email de alerta de gasto extra para Financeiro/Superadmin ────────────────

def send_new_expense_alert_email(expense, users: list) -> int:
    """Notifica FINANCEIRO/SUPERADMIN sobre um novo gasto extra pendente de aprovação."""
    if not users:
        return 0

    event_title = expense.event.title if expense.event else None
    amount_str = f"R$ {expense.amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    rows = _info_row("Descrição", expense.description)
    rows += _info_row("Categoria", expense.category)
    rows += _info_row("Valor", amount_str)
    if event_title:
        rows += _info_row("Evento", event_title)

    subject_target = f"no evento {event_title}" if event_title else "sem evento vinculado"
    content_paragraph = (
        f"Um novo gasto extra foi cadastrado {subject_target} e está aguardando aprovação."
    )

    sent = 0
    for user in users:
        if not user.email:
            continue
        content = (
            _greeting(user.name.split()[0])
            + _paragraph(content_paragraph)
            + _info_box(rows)
            + _alert_box(
                "Acesse o sistema para revisar e aprovar o gasto.",
                color="#fffbea", border="#f0d060", text="#7a5800",
            )
        )
        html = _html_wrap(content, preheader="Novo gasto extra cadastrado — verifique no sistema para aprovação.")
        if _send(to=user.email, subject="Novo gasto extra cadastrado — aprovação pendente", html=html):
            sent += 1
    return sent


# ── Email de pedido de figurino designado (feature 225) ──────────────────────

def send_figurino_producao_email(producao, user) -> bool:
    """Avisa a pessoa que ela ficou responsável por produzir uma peça de figurino.

    O convite do Google Agenda cobre o prazo; este e-mail cobre o *conteúdo* — o que é, para qual
    evento, quanto está previsto gastar. Os dois são independentes de propósito: o convite pode
    falhar (conta sem permissão, pessoa sem e-mail no Google) sem que o aviso se perca.

    Args:
        producao: O ``FigurinoProducao`` já commitado.
        user: A pessoa responsável.

    Returns:
        True se o e-mail saiu.
    """
    if not user or not user.email:
        return False

    from app.constants import FIGURINO_KIND_COMPRA

    # Feature 225c: o mesmo e-mail serve à compra, e um pedido de compra que chega dizendo
    # "você ficou responsável por produzir" manda a pessoa fazer a coisa errada.
    e_compra = producao.kind == FIGURINO_KIND_COMPRA
    verbo = "comprar" if e_compra else "produzir"
    assunto = (
        f"Compra para fazer: {producao.title}" if e_compra
        else f"Figurino para produzir: {producao.title}"
    )

    prazo = producao.prazo_efetivo
    rows = _info_row("O que comprar" if e_compra else "Peça", producao.title)
    if producao.quantity and producao.quantity > 1:
        rows += _info_row("Quantidade", str(producao.quantity))
    if producao.figurino_sheet:
        rows += _info_row("Figurino", producao.figurino_sheet.character_name)
    if producao.event:
        rows += _info_row("Evento", producao.event.title)
        if producao.event.start_at:
            rows += _info_row("Data do evento", producao.event.start_at.strftime("%d/%m/%Y"))
    if prazo:
        rows += _info_row("Prazo", prazo.strftime("%d/%m/%Y"))
    if producao.estimated_cost is not None:
        valor = f"R$ {producao.estimated_cost:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        rows += _info_row("Custo previsto", valor)

    corpo = _paragraph(
        f"Você ficou responsável por {verbo} <strong>{producao.title}</strong>."
    )
    if producao.description:
        corpo += _paragraph(producao.description)

    aviso = (
        "O prazo também foi para a sua agenda — você deve ter recebido o convite."
        if prazo
        else f"Ainda não há prazo definido para {'esta compra' if e_compra else 'esta peça'}."
    )

    content = (
        _greeting(user.name.split()[0] if user.name else "Olá")
        + corpo
        + _info_box(rows)
        + _alert_box(aviso, color="#fffbea", border="#f0d060", text="#7a5800")
    )
    html = _html_wrap(
        content, preheader=f"Você é responsável por {verbo}: {producao.title}"
    )
    return _send(to=user.email, subject=assunto, html=html)


def send_figurino_pedido_setor_email(producao, users: list) -> int:
    """Avisa o setor de figurino que entrou um pedido novo (feature 225b).

    Existe por causa da manutenção: quem relata "tem uma peça solta dentro do boneco" é quem
    recebeu o feedback do evento, não quem vai consertar — o pedido nasce sem dono. Sem este
    aviso, ele ficaria esperando alguém lembrar de abrir a fila.

    Args:
        producao: O ``FigurinoProducao`` já commitado.
        users: Equipe de figurino + super admins (já filtrados por e-mail).

    Returns:
        Quantidade de e-mails efetivamente enviados.
    """
    if not users:
        return 0

    from app.constants import (
        FIGURINO_KIND_COMPRA,
        FIGURINO_KIND_LABELS,
        FIGURINO_KIND_MANUTENCAO,
        FIGURINO_SEV_IMPEDE,
        FIGURINO_SEV_LABELS,
    )

    e_manutencao = producao.kind == FIGURINO_KIND_MANUTENCAO
    e_compra = producao.kind == FIGURINO_KIND_COMPRA
    rotulo = FIGURINO_KIND_LABELS.get(producao.kind, producao.kind)
    # Compra não é "de figurino" — pode ser tinta de cenário ou material de escritório. O
    # assunto do e-mail é o que a pessoa lê antes de abrir; chamar tudo de figurino faria o
    # Superadmin arquivar como assunto da oficina.
    contexto = "" if e_compra else " de figurino"
    prazo = producao.prazo_efetivo

    rows = _info_row("Tipo", rotulo)
    rows += _info_row("O que", producao.title)
    if producao.figurino_sheet:
        rows += _info_row("Figurino", producao.figurino_sheet.character_name)
    if producao.severity:
        rows += _info_row("Situação da peça", FIGURINO_SEV_LABELS.get(producao.severity, "—"))
    if producao.event:
        rows += _info_row("Evento", producao.event.title)
    if prazo:
        rows += _info_row("Prazo", prazo.strftime("%d/%m/%Y"))
    rows += _info_row("Aberto por", producao.requested_by.name if producao.requested_by else "—")

    corpo = _paragraph(
        f"Entrou um pedido de <strong>{rotulo.lower()}</strong>{contexto} e "
        "ainda não tem ninguém responsável."
    )
    if producao.description:
        corpo += _paragraph(producao.description)

    if e_manutencao and producao.severity == FIGURINO_SEV_IMPEDE:
        aviso = (
            "Esta peça está marcada como <strong>não pode ir para evento</strong> até o conserto. "
            "O aviso aparece na ficha e no elenco de quem escalar este personagem."
        )
        cores = {"color": "#fdecec", "border": "#e45858", "text": "#8a1f1f"}
    elif e_compra:
        aviso = "Abra os pedidos de compra para aprovar e dizer quem vai comprar."
        cores = {"color": "#fffbea", "border": "#f0d060", "text": "#7a5800"}
    else:
        aviso = "Abra a fila da oficina para assumir o pedido e definir o prazo."
        cores = {"color": "#fffbea", "border": "#f0d060", "text": "#7a5800"}

    assunto = f"{rotulo}{contexto}: {producao.title}"
    sent = 0
    for user in users:
        if not user.email:
            continue
        content = (
            _greeting(user.name.split()[0] if user.name else "Olá")
            + corpo
            + _info_box(rows)
            + _alert_box(aviso, **cores)
        )
        html = _html_wrap(content, preheader=assunto)
        if _send(to=user.email, subject=assunto, html=html):
            sent += 1
    return sent


# ── Helper interno ─────────────────────────────────────────────────────────────

def send_audit_report_email(subject: str, content_html: str, users: list) -> int:
    """Envia o relatório semanal do agente auditor financeiro (feature 221).

    O corpo já chega montado pelo auditor (tabelas de achados, sumário); aqui ele só ganha a
    moldura padrão dos e-mails da plataforma.

    Args:
        subject: Assunto do e-mail.
        content_html: HTML interno do relatório (vai dentro de ``_html_wrap``).
        users: Usuários internos destinatários (já validados pelo endpoint).

    Returns:
        Quantidade de e-mails efetivamente enviados.
    """
    sent = 0
    for user in users:
        if not user.email:
            continue
        html = _html_wrap(content_html, preheader="Relatório semanal da auditoria financeira.")
        if _send(to=user.email, subject=subject, html=html):
            sent += 1
    return sent


def _emails_enabled() -> bool:
    # Trava de ambiente vem ANTES da configuração do banco: `email_notifications_enabled` mora no
    # próprio banco, então a cópia local herda o valor da produção (ligado) e um processo de
    # desenvolvimento acaba com permissão de escrever para artista e cliente de verdade.
    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        log.info("Envio de e-mail suprimido neste ambiente (MAIL_SUPPRESS_SEND).")
        return False
    try:
        from app.models import SiteSetting
        settings = SiteSetting.query.first()
        return bool(settings and settings.email_notifications_enabled)
    except Exception as exc:  # noqa: BLE001 — sem acesso à config: assume desabilitado
        log.warning("falha ao ler configuração de notificações: %s", exc)
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


# ── Loja de Interações Virtuais (feature 205) ────────────────────────────────
#
# Os avisos da loja falam com a **família compradora**, não com o time. Por isso o tom é direto e
# sem jargão, e nenhum deles carrega dado da criança além do primeiro nome: o e-mail leva à página
# do pedido, onde o acesso exige o telefone da compra (FR-044a).
#
# A trava de "no máximo um por pedido e tipo" **não** está aqui: é a restrição
# `UNIQUE(order_id, kind)` de `virtual_order_notifications`, aplicada em
# `virtuais_ops._enviar_aviso` antes do disparo (FR-028a/FR-028b).


def _virtuais_order_url(order) -> str:
    """Endereço público de acompanhamento do pedido."""
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    return f"{base}/catalogo/v/pedido/{order.public_token}"


def _virtuais_valor(order) -> str:
    """Valor total no padrão brasileiro (Princípio IX)."""
    valor = order.total_value or 0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def send_virtual_order_confirmed_email(order) -> bool:
    """Confirma a compra de uma interação virtual (FR-035)."""
    if not order.contact_email:
        return False

    campanha = order.campaign
    quando = (
        order.slot.start_at.strftime("%d/%m/%Y às %H:%M")
        if order.slot and order.slot.start_at
        else f"em até {campanha.recorded_delivery_days} dias"
    )
    modalidade = (
        "Chamada de vídeo ao vivo (10 minutos)"
        if order.modality == "ao_vivo"
        else "Vídeo gravado"
    )

    rows = _info_row("Interação", modalidade)
    rows += _info_row("Para", order.child_name)
    rows += _info_row("Quando", quando)
    rows += _info_row("Valor", _virtuais_valor(order))

    url = _virtuais_order_url(order)
    content = (
        _greeting(order.child_name.split()[0] if order.child_name else "Olá")
        + _paragraph(
            "Recebemos seu pagamento e a interação está garantida! Guarde este e-mail: "
            "é por ele que você chega à página do pedido."
        )
        + _info_box(rows)
        + _btn("Ver meu pedido →", url)
        + _paragraph(
            "Na página do pedido você confirma o telefone da compra e vê o acesso à interação. "
            "Pedimos o telefone justamente para os dados da sua criança não ficarem abertos a "
            "quem só tiver o link."
        )
    )

    return _send(
        to=order.contact_email,
        subject=f"✨ Tudo certo! Sua interação com {campanha.title}",
        html=_html_wrap(content, preheader=f"Pagamento confirmado — {quando}."),
    )


def send_virtual_order_cancelled_email(order) -> bool:
    """Avisa o cancelamento por horário indisponível e a devolução em andamento (FR-043a).

    **Não promete prazo** de devolução: quem executa é uma pessoa no painel da operadora, e o
    sistema não controla esse tempo. Prometer o que não se controla é como a confiança se perde.
    """
    if not order.contact_email:
        return False

    campanha = order.campaign
    content = (
        _greeting(order.child_name.split()[0] if order.child_name else "Olá")
        + _paragraph(
            "Precisamos te dar uma notícia chata: o horário que você escolheu acabou sendo "
            "confirmado para outra família antes do seu pagamento chegar até nós."
        )
        + _paragraph(
            f"Seu pedido foi cancelado e a devolução de {_virtuais_valor(order)} já está em "
            "andamento. Assim que ela for concluída, o valor volta pelo mesmo meio de pagamento."
        )
        + _alert_box(
            "Se quiser tentar outro horário, é só voltar à página da campanha — e qualquer "
            "dúvida, fale com a gente pelo WhatsApp."
        )
        + _btn("Ver outros horários →", f"{(current_app.config.get('PUBLIC_BASE_URL') or '').rstrip('/')}/catalogo/v/{campanha.slug}")
    )

    return _send(
        to=order.contact_email,
        subject="Sobre o seu pedido — precisamos remarcar",
        html=_html_wrap(content, preheader="O horário foi confirmado para outra família; a devolução está em andamento."),
    )


def send_virtual_video_ready_email(order) -> bool:
    """Avisa que o vídeo gravado está disponível na página do pedido (FR-039).

    O vídeo **não** vai anexo nem por link direto: o e-mail leva à página do pedido, que exige o
    telefone da compra. Um vídeo em que o nome da criança é dito em voz alta não pode depender de
    o link não vazar (FR-038e).
    """
    if not order.contact_email:
        return False

    url = _virtuais_order_url(order)
    content = (
        _greeting(order.child_name.split()[0] if order.child_name else "Olá")
        + _paragraph("O vídeo ficou pronto! É só abrir a página do seu pedido para assistir.")
        + _btn("Assistir agora →", url)
        + _paragraph(
            "Vamos pedir o telefone da compra antes de mostrar o vídeo — é assim que garantimos "
            "que só você tem acesso."
        )
    )

    return _send(
        to=order.contact_email,
        subject="🎬 Seu vídeo está pronto!",
        html=_html_wrap(content, preheader="O vídeo da sua criança já está disponível."),
    )
