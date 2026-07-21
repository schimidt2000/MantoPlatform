"""Operações de casting como fonte única de lógica (feature 146).

O núcleo de cada ação de casting mora aqui, com parâmetros explícitos (sem `request.form`,
`flash` ou `current_user`), para ser reusado por DOIS adaptadores finos: o handler Jinja
(`app/calendar/routes.py`, que lê o form e dá `flash`) e o endpoint JSON (`app/api/agenda_write.py`,
que lê o JSON e devolve o evento serializado). UMA implementação da regra (teto de cachê,
transições de convite, e-mails), zero divergência (Princípio I).

Ações: `assign_role` (escalar/atualizar/desescalar — US1/146), `add_role`/`delete_role`
(adicionar/remover cargo — US2/147), `send_invite`/`set_figurino_done`/`dismiss_role`/
`restore_role` (convite/figurino/dispensar/restaurar — US3/148).
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


def add_role(
    event: Any,
    *,
    character_name: str,
    talent_id: Any,
    cache_value: Any,
    role_type: str,
    actor_name: str,
    tz: ZoneInfo,
) -> Any:
    """Adiciona um cargo ao evento (com ou sem talento). Núcleo de `_handle_add_role`.

    Cachê via `parse_brl` (Princípio VII — harmoniza com `assign_role`; o handler antigo usava
    `int()`, agora aceita decimais pt-BR). Se tem talento: `invite_status=pending` + convite.

    Returns:
        O `EventRole` criado.
    """
    from app.models import EventRole

    role = EventRole(event_id=event.id, character_name=character_name, role_type=role_type or "character")
    if talent_id:
        role.talent_id = int(talent_id)
        role.assigned_at = datetime.now(tz=tz)
        role.invite_status = "pending"
    role.cache_value = parse_brl(cache_value)
    db.session.add(role)
    db.session.flush()
    talent_name = role.talent.full_name if role.talent else None
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Casting",
        message=(
            f"Adicionou {talent_name} como {role.character_name} "
            f"com um cachê de {role.cache_value or 0} reais"
            if talent_name
            else f"Adicionou função: {role.character_name}"
        ),
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()
    if role.talent_id:
        send_async(send_invite_email, role)
    return role


def delete_role(
    event: Any, role: Any, *, is_superadmin: bool, actor_name: str, tz: ZoneInfo
) -> bool:
    """Remove um cargo. Núcleo de `_handle_delete_role`. Cargo com convite aceito só sai por
    superadmin (retorna False sem remover, nesse caso).

    Returns:
        True se removeu; False se bloqueado (convite aceito e não-superadmin).
    """
    if role.invite_status == "accepted" and not is_superadmin:
        return False
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Casting",
        message=f"Removeu vaga: {role.character_name}",
        created_at=datetime.now(tz=tz),
    ))
    db.session.delete(role)
    db.session.commit()
    return True


def send_invite(event: Any, role: Any, *, actor_name: str, tz: ZoneInfo) -> bool:
    """Reenvia o convite de um cargo com talento. Núcleo de `_handle_send_invite` (US3, feat. 148).

    Marca `invite_status=pending`, registra em `EventLog` e envia o convite de forma **síncrona**
    (`send_invite_email`, como o Jinja de hoje — não `send_async`), para o comportamento
    observável não mudar. Cargo sem talento é no-op (retorna False), igual ao handler atual.

    Returns:
        True se o e-mail foi enviado; False se não havia talento (no-op) ou o envio falhou.
    """
    if not role.talent_id:
        return False
    role.invite_status = "pending"
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Casting",
        message=f"Enviou convite para {role.talent.full_name} ({role.character_name})",
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()
    return send_invite_email(role)


def set_figurino_done(event: Any, role: Any, *, actor_name: str, tz: ZoneInfo) -> None:
    """Marca o figurino de um cargo como separado. Núcleo de `_handle_figurino_done` (feat. 148).

    Ação de Figurino (não de casting): a RBAC (Figurino/superadmin) é aplicada nos adaptadores.
    """
    role.figurino_done_at = datetime.now(tz=tz)
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Figurino",
        message=f"Separou figurino de {role.character_name}",
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()


def dismiss_role(role: Any, *, actor_name: str, dismissed_by: int) -> bool:
    """Dispensa um cargo sem talento sem excluí-lo (feature 108). Núcleo de `dismiss_role`.

    O cargo continua existindo (o sync do Google nunca o recria) mas para de contar como tarefa
    pendente. Só cargos **sem talento** podem ser dispensados. Usa `datetime.utcnow()` (naive) e
    `dismissed_by` como o fluxo Jinja atual. Idempotente: já dispensado retorna True sem duplicar.

    Returns:
        True se o cargo foi (ou já estava) dispensado; False se tem talento (bloqueado).
    """
    if role.talent_id is not None:
        return False
    if role.dismissed_at is None:
        role.dismissed_at = datetime.utcnow()
        role.dismissed_by = dismissed_by
        db.session.add(EventLog(
            event_id=role.event_id,
            actor_name=actor_name,
            actor_role="Casting",
            message=f"Dispensou tarefa de casting: {role.character_name}",
            created_at=datetime.utcnow(),
        ))
        db.session.commit()
    return True


def restore_role(role: Any, *, actor_name: str) -> None:
    """Reverte a dispensa de um cargo, voltando a contá-lo como pendente. Núcleo de `restore_role`.

    Idempotente: cargo não dispensado é no-op.
    """
    if role.dismissed_at is not None:
        role.dismissed_at = None
        role.dismissed_by = None
        db.session.add(EventLog(
            event_id=role.event_id,
            actor_name=actor_name,
            actor_role="Casting",
            message=f"Restaurou tarefa de casting: {role.character_name}",
            created_at=datetime.utcnow(),
        ))
        db.session.commit()
