"""Operações de nível-evento como fonte única de lógica (feature 149).

Segue o mesmo padrão de `casting_ops.py` (features 146/147/148): o núcleo de cada ação mora
aqui, com parâmetros explícitos (sem `request.form`, `flash` ou `current_user`), para ser
reusado por DOIS adaptadores finos — o handler Jinja (`app/calendar/routes.py`) e o endpoint
JSON (`app/api/agenda_write.py`). UMA implementação da regra, zero divergência (Princípio I).

Ações: `toggle_confirmed` (confirmar/desconfirmar o evento — feature 116) e `save_logistics`
(logística de maquiagem/saída + "precisa ensaio", com as notificações por e-mail). Os dois
notificadores de logística (`notify_accepted_roles`, `notify_ensaio_team`) vivem aqui — foram
movidos de `routes.py` (que os reimporta com alias) para manter a dependência unidirecional
`routes → event_ops` (este módulo só importa `models`/`constants`/`email_service`, nunca
`routes` — sem ciclo de import).
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.constants import RoleName
from app.email_service import send_async, send_ensaio_alert_email, send_event_changed_email
from app.models import EventLog, Role, User, db


def notify_accepted_roles(event: Any, changes: list[str]) -> None:
    """Marca roles aceitos como alterados e envia e-mails (movido de `routes.py`).

    O e-mail só é enviado uma vez por rodada de mudanças — enquanto o talento não clicar
    'Estou ciente' (que zera `event_changed_at`), notificações adicionais atualizam a descrição
    silenciosamente, sem novo e-mail.
    """
    now = datetime.now(tz=ZoneInfo("America/Sao_Paulo"))
    description = "\n".join(changes)
    for role in event.roles:
        if role.invite_status == "accepted":
            already_pending = role.event_changed_at is not None
            role.event_changed_at = now
            role.change_description = description
            if not already_pending:
                send_async(send_event_changed_email, role, changes)


def notify_ensaio_team(event: Any) -> None:
    """Envia alerta à equipe ENSAIO quando o evento precisa de ensaio (movido de `routes.py`)."""
    ensaio_users = User.query.join(User.roles).filter(Role.name == RoleName.ENSAIO).all()
    send_async(send_ensaio_alert_email, event, ensaio_users)


def resolve_makeup_location(selection: Any, custom: Any) -> str | None:
    """Resolve o local de maquiagem: se a seleção é "outro", usa o campo custom (como o Jinja).

    Compartilhado entre o adaptador Jinja e o da API para não duplicar a regra.
    """
    loc = (selection or "").strip()
    if loc == "outro":
        loc = (custom or "").strip()
    return loc or None


def toggle_confirmed(event: Any, *, actor_name: str, actor_id: int, tz: ZoneInfo) -> bool:
    """Liga/desliga a confirmação do evento (feature 116). Núcleo de `_handle_toggle_confirmado`.

    Registra autor (`confirmed_by_id`) e data/hora (`confirmed_at`), grava `EventLog` e devolve
    o novo estado. É o registro persistido de que o evento foi confirmado — independente do botão
    que só copia a mensagem de WhatsApp. A RBAC (Comercial/Superadmin) fica nos adaptadores.

    Returns:
        True se o evento ficou confirmado; False se a confirmação foi desfeita.
    """
    if event.confirmed_at is None:
        event.confirmed_at = datetime.now(tz=tz)
        event.confirmed_by_id = actor_id
        message = "Marcou o evento como confirmado"
    else:
        event.confirmed_at = None
        event.confirmed_by_id = None
        message = "Desfez a confirmação do evento"
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Comercial",
        message=message,
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()
    return event.confirmed_at is not None


def save_logistics(
    event: Any,
    *,
    makeup_time: Any,
    makeup_location: str | None,
    departure_time: Any,
    departure_location: Any,
    needs_rehearsal: bool,
    actor_name: str,
    tz: ZoneInfo,
) -> None:
    """Salva a logística do evento (maquiagem, saída, "precisa ensaio"). Núcleo de
    `_handle_save_logistics`.

    Recebe valores já resolvidos (`makeup_location` já passou por `resolve_makeup_location`).
    Detecta as mesmas quatro mudanças de hoje e dispara as mesmas notificações: aviso aos cargos
    aceitos quando a logística muda (`notify_accepted_roles`) e alerta à equipe de ENSAIO **só**
    na transição de `needs_rehearsal` desligado→ligado (`notify_ensaio_team`).

    Args:
        makeup_time: Horário de maquiagem (string "HH:MM" ou vazio → None).
        makeup_location: Local de maquiagem já resolvido (valor final ou None).
        departure_time: Horário de saída (string ou vazio → None).
        departure_location: Local de saída (string ou vazio → None).
        needs_rehearsal: Flag "precisa ensaio".
        actor_name: Nome de quem executa (mantido para simetria; o log fica nas notificações).
        tz: Fuso para timestamps (São Paulo).
    """
    old_needs_rehearsal = event.needs_rehearsal
    old_departure = event.departure_time
    old_departure_loc = event.departure_location
    old_makeup_time = event.makeup_time
    old_makeup_location = event.makeup_location

    event.makeup_time = (makeup_time or "").strip() or None
    event.makeup_location = makeup_location or None
    event.departure_time = (departure_time or "").strip() or None
    event.departure_location = (departure_location or "").strip() or None
    event.needs_rehearsal = bool(needs_rehearsal)

    logistics_changes: list[str] = []
    if event.departure_time != old_departure and old_departure is not None:
        logistics_changes.append(
            f"Horário de saída: {old_departure} → {event.departure_time or 'não definido'}"
        )
    if event.departure_location != old_departure_loc and old_departure_loc is not None:
        logistics_changes.append(
            f"Local de saída: {old_departure_loc} → {event.departure_location or 'Manto Produções'}"
        )
    if event.makeup_time != old_makeup_time and old_makeup_time is not None:
        logistics_changes.append(
            f"Horário de maquiagem: {old_makeup_time} → {event.makeup_time or 'não definido'}"
        )
    if event.makeup_location != old_makeup_location and old_makeup_location is not None:
        logistics_changes.append(
            f"Local de maquiagem: {old_makeup_location} → {event.makeup_location or 'não definido'}"
        )
    if logistics_changes:
        notify_accepted_roles(event, logistics_changes)

    db.session.commit()

    if event.needs_rehearsal and not old_needs_rehearsal:
        notify_ensaio_team(event)
