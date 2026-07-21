"""Operações de casting como fonte única de lógica (feature 146).

O núcleo de cada ação de casting mora aqui, com parâmetros explícitos (sem `request.form`,
`flash` ou `current_user`), para ser reusado por DOIS adaptadores finos: o handler Jinja
(`app/calendar/routes.py`, que lê o form e dá `flash`) e o endpoint JSON (`app/api/agenda_write.py`,
que lê o JSON e devolve o evento serializado). UMA implementação da regra (teto de cachê,
transições de convite, e-mails), zero divergência (Princípio I).

Nesta fatia (US1): `assign_role` (escalar/atualizar/desescalar talento num cargo).
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.email_service import (
    send_async,
    send_event_changed_email,
    send_invite_email,
    send_removal_email,
)
from app.models import EventLog, Talent, db
from app.money import parse_brl


def assign_role(
    event: Any,
    role: Any,
    *,
    talent_id: Any,
    cache_value: Any,
    travel_cache: Any,
    actor_name: str,
    is_superadmin: bool,
    tz: ZoneInfo,
) -> str:
    """Escala/atualiza/desescala o talento de um cargo. Núcleo extraído de `_handle_assign_casting`.

    Aplica o teto de cachê (`cache_cap`) para não-superadmin, reseta figurino/convite ao trocar
    de talento, registra em `EventLog` e dispara os mesmos e-mails do fluxo Jinja (via
    `send_async`, isolável em teste). Retorna a mensagem de sucesso (o adaptador Jinja dá
    `flash`; o adaptador da API a ignora e devolve o evento serializado).

    Args:
        event: O `CalendarEvent` dono do cargo.
        role: O `EventRole` a atualizar (já carregado e pertencente ao evento).
        talent_id: Id do talento (str/int) ou vazio/None para desescalar.
        cache_value: Cachê cru (string pt-BR ou número); parseado aqui via `parse_brl`.
        travel_cache: Adicional de transporte cru; parseado aqui.
        actor_name: Nome de quem executa (para o log).
        is_superadmin: Se pode ultrapassar o teto de cachê.
        tz: Fuso para timestamps (São Paulo).

    Returns:
        Mensagem de sucesso descrevendo o efeito.
    """
    old_talent_id = role.talent_id
    old_cache_value = role.cache_value
    old_travel_cache = role.travel_cache
    old_invite_status = role.invite_status

    role.talent_id = int(talent_id) if talent_id else None

    new_cache = parse_brl(cache_value)
    # Teto de cachê: casting não ultrapassa o cap do orçamento; superadmin pode (fica no log).
    if new_cache is not None and role.cache_cap is not None and new_cache > role.cache_cap:
        if not is_superadmin:
            new_cache = role.cache_cap

    role.cache_value = new_cache
    new_travel = parse_brl(travel_cache)
    role.travel_cache = new_travel
    role.assigned_at = datetime.now(tz=tz) if role.talent_id else None
    if role.talent_id != old_talent_id:
        role.figurino_done_at = None
        role.invite_status = None
    if role.talent_id:
        role.payment_status = "nao_pago"
    # Remoção: avisa o talento trocado, salvo se ele havia recusado voluntariamente.
    if old_talent_id and old_talent_id != role.talent_id and old_invite_status != "rejected":
        old_talent = Talent.query.get(old_talent_id)
        if old_talent:
            send_async(send_removal_email, old_talent, event, role.character_name)
    db.session.commit()

    if role.talent_id and role.talent_id != old_talent_id:
        role.invite_status = "pending"
        cap_note = ""
        if role.cache_cap and role.cache_value and role.cache_value > role.cache_cap:
            cap_note = f" (acima do cap de {role.cache_cap}R$ — autorizado pelo admin)"
        message = (
            f"Adicionou {role.talent.full_name} como {role.character_name} "
            f"com cachê de {role.cache_value or 0}R${cap_note}"
        )
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=actor_name,
            actor_role="Casting",
            message=message,
            created_at=datetime.now(tz=tz),
        ))
        db.session.commit()
        send_async(send_invite_email, role)
        return message

    if role.talent_id:
        cap_note = ""
        if role.cache_cap and role.cache_value and role.cache_value > role.cache_cap:
            cap_note = f" (acima do cap de {role.cache_cap}R$ — autorizado pelo admin)"
        message = (
            f"Atualizou cachê de {role.talent.full_name} como {role.character_name} "
            f"para {role.cache_value or 0}R${cap_note}"
        )
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=actor_name,
            actor_role="Casting",
            message=message,
            created_at=datetime.now(tz=tz),
        ))
        db.session.commit()
        # Notifica talento já confirmado se o cachê/transporte mudou.
        if old_invite_status == "accepted":
            changes = _cache_changes(old_cache_value, new_cache, old_travel_cache, new_travel)
            if changes:
                role.event_changed_at = datetime.now(tz=tz)
                role.change_description = "\n".join(changes)
                db.session.commit()
                send_async(send_event_changed_email, role, changes)
        return message

    # Sem talento (desescalado): confirma que a vaga foi salva (feature 138).
    return f"Vaga de {role.character_name} atualizada."


def _cache_changes(
    old_cache: Any | None, new_cache: Any | None,
    old_travel: Any | None, new_travel: Any | None,
) -> list[str]:
    """Descreve mudanças de cachê/transporte para notificar talento confirmado (como no Jinja)."""
    changes: list[str] = []
    if new_cache != old_cache:
        old_fmt = f"R$ {old_cache:,.0f}" if old_cache else "não definido"
        new_fmt = f"R$ {new_cache:,.0f}" if new_cache else "não definido"
        changes.append(f"Cachê: {old_fmt} → {new_fmt}")
    if new_travel != old_travel:
        old_fmt = f"R$ {old_travel:,.0f}" if old_travel else "não definido"
        new_fmt = f"R$ {new_travel:,.0f}" if new_travel else "não definido"
        changes.append(f"Adicional de transporte: {old_fmt} → {new_fmt}")
    return changes
