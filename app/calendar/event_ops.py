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

Desde a feature 267 importa também `formularios_ops` **no topo**, e isso é seguro: aquele módulo é
folha (importa só `app`, `app.clientes.importer`, `app.models` e `app.utils` — nenhum deles toca
`app.calendar`). O ciclo real continua sendo `routes → event_ops`, e é por ele que as funções
daqui importam `routes` dentro do corpo, nunca no topo.
"""

import logging
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.constants import EVENT_TYPE_SHOW, RoleName, now_sp
from app.email_service import send_async, send_ensaio_alert_email, send_event_changed_email
from app.formularios.formularios_ops import apply_event_link, clear_event_link
from app.models import (
    EventClient,
    EventLog,
    EventRole,
    FigurinoSheet,
    FormResponse,
    Role,
    Talent,
    User,
    db,
)

logger = logging.getLogger(__name__)


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
    na transição de `needs_rehearsal` desligado→ligado (`notify_ensaio_team`). Essa mesma transição
    também entra na lista de mudanças enviada aos cargos aceitos (`send_event_changed_email`) —
    o talento precisa saber que o evento passou a exigir ensaio, não só a equipe interna.

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
    rehearsal_just_activated = event.needs_rehearsal and not old_needs_rehearsal
    if rehearsal_just_activated:
        logistics_changes.append("Definição de ensaio: este evento agora precisa de ensaio")
    if logistics_changes:
        notify_accepted_roles(event, logistics_changes)

    db.session.commit()

    if rehearsal_just_activated:
        notify_ensaio_team(event)


class EventCoreUpdateBlocked(Exception):
    """Levantado quando a edição em bloco não pode prosseguir sem apagar estado protegido —
    hoje só o caso de remover um personagem com convite já aceito por um não-superadmin
    (feature 184, paridade com a trava de `casting_ops.delete_role`). Nada é gravado quando esta
    exceção é levantada — a checagem roda antes de qualquer `db.session.add`/`delete`.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EventTypeChangeBlocked(Exception):
    """Levantado quando a troca de tipo do evento não pôde ser aplicada porque o título novo não
    chegou ao Google Agenda (feature 239).

    A automação da troca de tipo (criar/remover vagas de som, cancelar ensaios) só é segura
    depois que a Agenda recebeu o prefixo "(TIPO)" novo — é ele que o `sync_events` lê de volta.
    Quando esta exceção sobe, o tipo e o título JÁ VOLTARAM ao que estavam e nada da automação
    rodou; os demais campos do salvamento (data, local, descrição, valores) continuam gravados,
    como no comportamento best-effort de sempre.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _reconcile_characters(
    event: Any,
    characters: list[dict],
    *,
    coordinator_talent_id: int | None,
    is_superadmin: bool,
    start: datetime,
    end: datetime,
) -> tuple[list[str], list[tuple[int, str]]]:
    """Reconcilia o elenco (`role_type="character"`) por `role_id` em vez de substituir tudo
    (feature 184, research.md §4): atualiza linhas existentes, insere linhas novas, remove linhas
    que saíram do conjunto enviado — recusando a remoção (levanta `EventCoreUpdateBlocked`) se
    alguma tiver convite aceito e quem edita não for superadmin. O coordenador (`role_type="extra"`,
    `character_name="Coordenador"`) é tratado à parte, mesma vaga sentinela de
    `routes._ensure_coordinator`. Devolve avisos não-bloqueantes de conflito de agenda (mesma
    lógica de `_check_talent_conflicts`).
    """
    from app.calendar.routes import _talent_time_conflict

    existing = {
        r.id: r
        for r in EventRole.query.filter_by(event_id=event.id, role_type="character").all()
    }
    submitted_ids = {c.get("role_id") for c in characters if c.get("role_id")}
    to_remove = [r for rid, r in existing.items() if rid not in submitted_ids]

    for role in to_remove:
        if role.invite_status == "accepted" and not is_superadmin:
            raise EventCoreUpdateBlocked(
                f'Não é possível remover "{role.character_name}": o talento já aceitou o convite.'
            )

    figurino_by_name = {s.character_name.lower(): s.id for s in FigurinoSheet.query.all()}
    valid_talent_ids = {t.id for t in Talent.query.filter_by(status="active").all()}
    used_talent_ids: set[int] = set()
    assigned_now: list[tuple[int, str]] = []

    for char_data in characters:
        name = (char_data.get("name") or "").strip()
        if not name:
            continue
        role_id = char_data.get("role_id")
        sheet_id = char_data.get("figurino_sheet_id") or figurino_by_name.get(name.lower())
        talent_id = char_data.get("talent_id")
        pre_tid = (
            talent_id
            if talent_id is not None and talent_id in valid_talent_ids and talent_id not in used_talent_ids
            else None
        )

        if role_id and role_id in existing:
            role = existing[role_id]
            role.character_name = name
            role.figurino_sheet_id = sheet_id
            role.cache_value = char_data.get("cache_value")
            role.needs_makeup = bool(char_data.get("needs_makeup")) or None
            role.is_singer = bool(char_data.get("is_singer")) or None
            if pre_tid and role.talent_id != pre_tid:
                role.talent_id = pre_tid
                role.assigned_at = datetime.now(tz=start.tzinfo)
                used_talent_ids.add(pre_tid)
                assigned_now.append((pre_tid, name))
        else:
            db.session.add(EventRole(
                event_id=event.id,
                character_name=name,
                role_type="character",
                figurino_sheet_id=sheet_id,
                cache_value=char_data.get("cache_value"),
                needs_makeup=bool(char_data.get("needs_makeup")) or None,
                is_singer=bool(char_data.get("is_singer")) or None,
                talent_id=pre_tid,
                assigned_at=datetime.now(tz=start.tzinfo) if pre_tid else None,
            ))
            if pre_tid:
                used_talent_ids.add(pre_tid)
                assigned_now.append((pre_tid, name))

    for role in to_remove:
        db.session.delete(role)

    coordinator = EventRole.query.filter_by(
        event_id=event.id, character_name="Coordenador", role_type="extra"
    ).first()
    if (
        coordinator_talent_id is not None
        and coordinator_talent_id in valid_talent_ids
        and coordinator_talent_id not in used_talent_ids
    ):
        if coordinator:
            if coordinator.talent_id != coordinator_talent_id:
                coordinator.talent_id = coordinator_talent_id
                coordinator.assigned_at = datetime.now(tz=start.tzinfo)
                assigned_now.append((coordinator_talent_id, "Coordenador"))
        else:
            db.session.add(EventRole(
                event_id=event.id,
                character_name="Coordenador",
                role_type="extra",
                talent_id=coordinator_talent_id,
                assigned_at=datetime.now(tz=start.tzinfo),
            ))
            assigned_now.append((coordinator_talent_id, "Coordenador"))

    warnings: list[str] = []
    for tid, char_name in assigned_now:
        other = _talent_time_conflict(tid, start, end, exclude_event_id=event.id)
        if other:
            talent = Talent.query.get(tid)
            tname = (talent.artistic_name or talent.full_name) if talent else f"Talento {tid}"
            warnings.append(f'{tname} ({char_name}) — já em "{other.title}"')
    # `assigned_now` sai junto (feature 233): quem acabou de ser escalado precisa receber convite,
    # e esta é a única lista que sabe QUEM é novo — o cargo já existia antes com outra pessoa, ou
    # nem existia.
    return warnings, assigned_now


# ── Troca de tipo do evento (SHOW ⇄ não-SHOW) — feature 239 ──────────────────────────────────
# Fonte única da reação à mudança de `event_type`. Os dois caminhos de edição (o cabeçalho da
# aba Resumo e o formulário em bloco) passam por aqui; a criação mantém a mesma regra em
# `_create_event_row`/`_apply_default_roles`. Sem isto, o evento que deixava de ser SHOW seguia
# cobrando ensaio e técnico de som para sempre — e o sync do Google ainda ressuscitava tudo pelo
# prefixo do título, por isso `build_gc_title` anda junto.


def build_gc_title(title: str | None, event_type: str | None) -> str | None:
    """Reescreve o prefixo "(TIPO)" do título do evento, preservando o resto intacto.

    Extraído da criação (`app/api/agenda_write.py`), onde era a única normalização existente.
    Só o par de parênteses inicial é trocado: a parte dos personagens ("HOMEM ARANHA + MARIO")
    fica idêntica, porque é dela que `parse_characters` reconstrói o elenco no sync do Google.

    Args:
        title: Título como veio do formulário (com ou sem prefixo de tipo).
        event_type: Tipo do evento ("SHOW", "CORP", ...). Vazio/None devolve o título como veio.

    Returns:
        O título prefixado com o tipo atual, ou o título original quando não há tipo.
    """
    if not title or not event_type:
        return title
    clean = re.sub(r"^\s*\([^)]*\)\s*", "", title).strip()
    return f"({event_type}) {clean}"


def _descrever_vaga_de_som(role: Any) -> str:
    """Resume uma vaga automática de som para o `EventLog` (quem estava, quanto e em que status).

    O log é o único rastro do que existia antes da remoção automática — sem ele ninguém consegue
    reconstruir a vaga (nem saber que havia dinheiro combinado nela).
    """
    if role.talent_id:
        talent = Talent.query.get(role.talent_id)
        quem = (talent.artistic_name or talent.full_name) if talent else f"talento {role.talent_id}"
    else:
        quem = "sem talento"
    cache = f"cachê {role.cache_value}" if role.cache_value is not None else "sem cachê"
    return (
        f"{role.character_name} [{quem}; {cache}; convite {role.invite_status or '—'}; "
        f"pagamento {role.payment_status}]"
    )


def _entrar_em_show(event: Any, tipo_antigo: str, *, actor_name: str, tz: ZoneInfo) -> list[str]:
    """Aplica o que a criação de um SHOW aplica: vagas de som e "precisa ensaio" ligado."""
    from app.calendar.routes import _ensure_sound_technician

    _ensure_sound_technician(event.id)
    event.needs_rehearsal = True
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Comercial",
        message=(
            f"Tipo do evento: {tipo_antigo or '—'} → {EVENT_TYPE_SHOW}. "
            "Vagas de Técnico de Som criadas e 'precisa ensaio' ligado (regra do SHOW)."
        ),
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()
    return [
        "O evento virou SHOW: vagas de Técnico de Som criadas e ensaio marcado como necessário.",
    ]


def _sair_de_show(event: Any, tipo_novo: str, *, actor_name: str, tz: ZoneInfo) -> list[str]:
    """Desmonta TUDO que só existia por causa do SHOW (decisão 7 da rodada 239).

    Remoção automática e incondicional: ensaios já agendados são cancelados (no Google Agenda
    também, pelo mesmo `delete_ensaio` do botão de cancelar), as duas vagas automáticas de som
    saem mesmo preenchidas, e `needs_rehearsal` é desligado. Tudo vai para o `EventLog` com os
    valores que existiam, e volta como aviso não-bloqueante para a tela.
    """
    from app.calendar.routes import PRESENCE_CHARACTER, SOUND_TECH_CHARACTER

    avisos: list[str] = []
    removidos: list[str] = []

    for ensaio in list(event.ensaios or []):
        quando = ensaio.start_at.strftime("%d/%m/%Y %H:%M") if ensaio.start_at else "sem data"
        removidos.append(f"ensaio de {quando}")
        aviso_google = delete_ensaio(ensaio)
        avisos.append(f"Ensaio de {quando} cancelado — o evento deixou de ser SHOW.")
        if aviso_google:
            avisos.append(aviso_google)

    vagas = (
        EventRole.query
        .filter(
            EventRole.event_id == event.id,
            EventRole.role_type == "extra",
            EventRole.character_name.in_((SOUND_TECH_CHARACTER, PRESENCE_CHARACTER)),
        )
        .all()
    )
    for role in vagas:
        removidos.append(_descrever_vaga_de_som(role))
        preenchida = role.talent_id is not None or role.cache_value is not None
        if preenchida:
            avisos.append(
                f"A vaga '{role.character_name}' já estava preenchida e foi removida — "
                "o evento deixou de ser SHOW."
            )
        else:
            avisos.append(f"Vaga '{role.character_name}' removida — o evento deixou de ser SHOW.")
        db.session.delete(role)

    if event.needs_rehearsal:
        removidos.append("'precisa ensaio' desligado")
        event.needs_rehearsal = False

    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Comercial",
        message=(
            f"Tipo do evento: {EVENT_TYPE_SHOW} → {tipo_novo or '—'}. Removido automaticamente: "
            + ("; ".join(removidos) if removidos else "nada (não havia ensaio nem vaga de som)")
        ),
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()
    return avisos


def aplicar_troca_de_tipo(
    event: Any,
    tipo_antigo: str | None,
    tipo_novo: str | None,
    *,
    actor_name: str,
    tz: ZoneInfo,
) -> list[str]:
    """Reage à mudança de tipo de um evento já existente — fonte única (feature 239).

    Chamada por `update_event_basics` e por `update_event_core`, sempre com o tipo ANTIGO lido
    antes da atribuição. Nada acontece quando o tipo não muda ou quando a troca não envolve
    SHOW (CORP → R&I, por exemplo, não tem regra automática nenhuma).

    Args:
        event: O `CalendarEvent` já com o tipo novo atribuído e gravado.
        tipo_antigo: Tipo que o evento tinha antes da edição.
        tipo_novo: Tipo que o evento passou a ter.
        actor_name: Nome de quem editou, para o `EventLog`.
        tz: Fuso usado no carimbo dos logs.

    Returns:
        Avisos não-bloqueantes descrevendo o que foi criado ou removido automaticamente —
        entram na mesma lista de `warnings` que os endpoints já devolvem.
    """
    antigo = (tipo_antigo or "").strip().upper()
    novo = (tipo_novo or "").strip().upper()
    if antigo == novo:
        return []
    if novo == EVENT_TYPE_SHOW:
        return _entrar_em_show(event, antigo, actor_name=actor_name, tz=tz)
    if antigo == EVENT_TYPE_SHOW:
        return _sair_de_show(event, novo, actor_name=actor_name, tz=tz)
    return []


def _push_cabecalho_ao_google(event: Any) -> None:
    """Empurra título/data/local/descrição do evento para o Google Agenda.

    Sem tratamento de erro de propósito: quem chama decide o que fazer com a falha (ver
    `_sincronizar_e_trocar_tipo`).
    """
    from app.calendar.routes import CALENDAR_ID
    from app.calendar.service import update_event as google_update_event

    google_update_event(
        CALENDAR_ID,
        event.google_event_id,
        event.title,
        event.start_at,
        event.end_at,
        description=event.description or "",
        location=event.location or "",
    )


def _desfazer_troca_de_tipo(
    event: Any,
    *,
    old_title: str | None,
    old_event_type: str | None,
    actor_name: str,
    tz: ZoneInfo,
) -> None:
    """Devolve tipo e prefixo do título ao estado anterior, registrando o motivo no `EventLog`.

    Chamado quando o Google recusou o título novo: o prefixo que ficou na Agenda ainda é o
    antigo, então manter o tipo novo no banco só faria o `sync_events` desfazê-lo sozinho
    minutos depois. A renomeação feita no mesmo salvamento é preservada — só o prefixo
    "(TIPO)" volta.
    """
    tipo_novo = event.event_type
    event.event_type = old_event_type
    if old_event_type:
        event.title = build_gc_title(event.title, old_event_type)
    else:
        # `build_gc_title` devolve o título intacto quando o tipo é vazio; aqui o prefixo TEM
        # que sair, senão o sync leria o tipo novo de volta a partir do próprio título.
        sem_prefixo = re.sub(r"^\s*\([^)]*\)\s*", "", event.title or "").strip()
        event.title = sem_prefixo or old_title
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Comercial",
        message=(
            f"Troca de tipo {old_event_type or '—'} → {tipo_novo or '—'} NÃO aplicada: "
            "o Google Agenda recusou o título novo. Nenhum ensaio, vaga de som ou "
            "'precisa ensaio' foi alterado."
        ),
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()


def _sincronizar_e_trocar_tipo(
    event: Any,
    *,
    old_title: str | None,
    old_event_type: str | None,
    changed_core: bool,
    actor_name: str,
    tz: ZoneInfo,
) -> list[str]:
    """Empurra o cabeçalho ao Google e SÓ ENTÃO aplica a automação da troca de tipo (239).

    A ordem é obrigatória e não pode ser invertida: sair de SHOW é IRREVERSÍVEL — `delete_ensaio`
    apaga o ensaio do Google Calendar de verdade e as duas vagas de som somem mesmo preenchidas.
    Se isso rodasse antes do push e o push falhasse, a Agenda continuaria com "(SHOW) ..." e o
    `sync_events` seguinte reimporia SHOW + `needs_rehearsal` + vagas num evento cujos ensaios
    já não existem mais — sem nenhuma tela mostrando que existiram.

    Por isso, quando o push falha numa troca que envolve SHOW (nos dois sentidos: as duas têm
    automação), a troca é DESFEITA e `EventTypeChangeBlocked` sobe para o endpoint devolver erro.
    Edição sem troca de tipo — ou troca sem automação, como CORP → R&I — segue best-effort de
    sempre: a falha do Google vira só um aviso.

    Args:
        event: Evento já gravado com tipo e título novos.
        old_title: Título anterior (o que a Agenda ainda tem, quando o push falha).
        old_event_type: Tipo anterior — é o que `aplicar_troca_de_tipo` compara.
        changed_core: Se algum campo sincronizável mudou (título/data/horário/local/descrição).
        actor_name: Quem editou, para o `EventLog`.
        tz: Fuso usado no carimbo dos logs.

    Returns:
        Avisos não-bloqueantes: o que a troca de tipo criou/removeu, mais a falha de
        sincronização quando ela não impede a troca.

    Raises:
        EventTypeChangeBlocked: o Google recusou o cabeçalho novo e a troca envolvia SHOW —
            nada da automação rodou e o tipo voltou ao anterior.
    """
    google_ok = True
    if changed_core and event.google_event_id:
        try:
            _push_cabecalho_ao_google(event)
        except Exception as exc:  # noqa: BLE001 — Google fora do ar não bloqueia a edição
            logger.warning("falha ao sincronizar evento %s com o Google Agenda: %s", event.id, exc)
            google_ok = False

    antigo = (old_event_type or "").strip().upper()
    novo = (event.event_type or "").strip().upper()
    troca_com_automacao = antigo != novo and EVENT_TYPE_SHOW in (antigo, novo)

    if not google_ok and troca_com_automacao:
        _desfazer_troca_de_tipo(
            event,
            old_title=old_title,
            old_event_type=old_event_type,
            actor_name=actor_name,
            tz=tz,
        )
        raise EventTypeChangeBlocked(
            "Não foi possível sincronizar com o Google Agenda — a troca de tipo não foi aplicada."
        )

    avisos = aplicar_troca_de_tipo(
        event, old_event_type, event.event_type, actor_name=actor_name, tz=tz
    )
    if not google_ok:
        avisos.append("Não foi possível sincronizar a mudança com o Google Agenda.")
    return avisos


def reclassificar_fora_de_sp(event: Any, *, local_mudou: bool) -> None:
    """Refaz a classificação dentro/fora de SP e a estimativa de trajeto (hotfix 239b).

    Até aqui só a criação e o sync do Google classificavam; as duas edições React
    (`update_event_core`, `update_event_dados`) trocavam o endereço e deixavam `is_outside_sp`
    como estava. Regra: endereço que mudou reclassifica; endereço igual só reclassifica se a
    classificação era desconhecida (cura sem custo — o Geocoding só roda quando há o que
    descobrir). A estimativa de trajeto nasce junto quando o evento é fora de SP e ainda não tem
    distância — é ela que dá base à parcela do veículo no teto do carrinho.
    """
    from app.calendar.routes import _fetch_travel_data, _lookup_sp_status
    from app.models import SiteSetting

    if not local_mudou and event.is_outside_sp is not None:
        return
    event.is_outside_sp = _lookup_sp_status(event.location or "")
    if event.is_outside_sp and (local_mudou or not event.travel_distance_km):
        _fetch_travel_data(event, SiteSetting.query.get(1))


def resolver_data_da_venda(
    informada: date | None, venda: Any, venda_anterior: Any, data_atual: date | None
) -> date | None:
    """Data da venda que vai para o banco (hotfix 267b).

    A data da venda é o **ciclo da comissão** (`coalesce(payable_from, sale_date)` na Planilha de
    Pagamentos): venda sem data é comissão que nunca aparece para ser paga. O formulário Jinja
    prefilhava o campo com "hoje"; o React, interface primária desde 04/08/2026, nascia vazio — e
    38 vendas de agosto ficaram sem ciclo, R$ 5.162,26 de comissão invisíveis na planilha. A regra
    sai do formulário e vem para o servidor, onde vale para qualquer tela:

    - data informada → vale a informada;
    - sem venda (ou cortesia/permuta) → sem data;
    - venda que já tinha data → mantém (editar a aba Comercial não apaga a data);
    - venda registrada **agora** (não havia venda antes), sem data → hoje, relógio de São Paulo;
    - venda antiga que já estava sem data → continua sem: o servidor não inventa uma data velha;
      o legado é do backfill em `specs/267b-hotfix-data-da-venda/backfill_data_da_venda.py`.

    Args:
        informada: `sale_date` que veio no corpo, ou ``None``.
        venda: `sale_value` que está sendo gravado agora (já zerado quando é cortesia).
        venda_anterior: `sale_value` que o evento tinha antes desta gravação (``None`` na criação).
        data_atual: `sale_date` que o evento tinha antes desta gravação (``None`` na criação).
    """
    if informada is not None:
        return informada
    if not venda:
        return None
    if data_atual is not None:
        return data_atual
    if not venda_anterior:
        return now_sp().date()
    return None


def update_event_core(
    event: Any,
    data: dict,
    *,
    is_superadmin: bool,
    actor_name: str,
    tz: ZoneInfo,
    sincronizar_comissao: Any = None,
) -> list[str]:
    """Atualiza em bloco os campos centrais de um evento existente (feature 184) — título, tipo,
    data/horário, local, descrição, ensaio, valores, pagamento, vendedor, elenco (reconciliado),
    clientes (substituídos) e pré-contrato vinculado. Núcleo de `PATCH /api/events/<id>`.

    `data` segue o mesmo shape de `_build_create_event_data` (routes.py/agenda_write.py), sem os
    campos exclusivos de criação (`orcamento_history_id`, `duracao`, `orc_caches`, `acrescimos`,
    reembolso, observações — esses não fazem parte da edição em bloco).

    Sincroniza título/data/horário/local/descrição com o Google Agenda quando mudam
    (best-effort — ver research.md §10): uma falha do Google não impede salvar no Manto, só vira
    um aviso na lista devolvida. A ÚNICA exceção é a troca de tipo com automação (entrar/sair de
    SHOW): sem o título novo na Agenda ela é desfeita e vira erro (`EventTypeChangeBlocked`),
    porque a saída de SHOW apaga ensaios e vagas para sempre — ver `_sincronizar_e_trocar_tipo`.

    Raises:
        EventCoreUpdateBlocked: se a reconciliação de elenco tentar remover um personagem com
            convite aceito e quem edita não for superadmin — nada é gravado nesse caso.
        EventTypeChangeBlocked: se o título novo não chegou ao Google numa troca de tipo com
            automação (entrar/sair de SHOW) — a troca é desfeita, o resto do salvamento fica.

    Returns:
        Lista de avisos não-bloqueantes (conflito de agenda de talento pré-escalado, falha de
        sincronização com o Google).
    """
    from app.calendar.routes import _build_start_end, _create_client_links

    d = date.fromisoformat(data["date_str"])
    st, et = _build_start_end(d, data["start_str"], data["end_str"])

    old_title, old_start, old_end = event.title, event.start_at, event.end_at
    old_location, old_description = event.location, event.description
    # Tipo ANTES da atribuição: é o que `aplicar_troca_de_tipo` compara no fim (feature 239).
    old_event_type = event.event_type

    # Reconciliação do elenco ANTES de qualquer outra escrita — se bloquear (convite aceito),
    # nada mais deste método deve ter efeito colateral.
    warnings, recem_escalados = _reconcile_characters(
        event,
        data.get("characters") or [],
        coordinator_talent_id=data.get("coordinator_talent_id"),
        is_superadmin=is_superadmin,
        start=st,
        end=et,
    )

    event.event_type = data["event_type"] or None
    # O prefixo "(TIPO)" do título é reescrito junto com o tipo (feature 239): é ele que o sync
    # do Google lê de volta — título antigo = tipo antigo ressuscitado na próxima rodada.
    event.title = build_gc_title(data["title"], event.event_type)
    event.start_at = st
    event.end_at = et
    event.location = data["location"] or None
    event.description = data["description"] or None
    reclassificar_fora_de_sp(
        event, local_mudou=(event.location or "").strip() != (old_location or "").strip()
    )
    event.needs_rehearsal = bool(data.get("needs_rehearsal"))

    is_cortesia = bool(data.get("is_cortesia_permuta"))
    venda_anterior, data_anterior = event.sale_value, event.sale_date
    event.is_cortesia_permuta = is_cortesia
    event.sale_value = 0 if is_cortesia else data.get("sale_value")
    event.sale_value_gross = 0 if is_cortesia else data.get("sale_value_gross")
    event.transport_value = data.get("transport_value")
    event.acrescimo_value = data.get("acrescimo_value")
    event.with_invoice = bool(data.get("with_invoice"))
    event.seller_id = data.get("seller_id")
    event.sale_date = resolver_data_da_venda(
        data.get("sale_date"), event.sale_value, venda_anterior, data_anterior
    )
    event.payment_method = data.get("payment_method")
    event.payment_installments = data.get("payment_installments")
    event.payment_due_date = data.get("payment_due_date")

    EventClient.query.filter_by(event_id=event.id).delete()
    _create_client_links(event, data.get("client_pairs") or [])

    form_response_id = data.get("form_response_id")
    if form_response_id is not None:
        fr = FormResponse.query.get(form_response_id)
        if fr and fr.event_id is None:
            apply_event_link(fr, event)

    if sincronizar_comissao is not None:
        # INCONDICIONAL, como o gêmeo `update_event_comercial`. Guardar por "campo mudou"
        # reintroduziria metade do defeito: a venda que nunca gerou linha nenhuma precisa de
        # sync mesmo quando nada mudou nesta gravação — e é exatamente esse buraco que o
        # `_resync_pending_commissions` não cobre (ele só percorre linhas já existentes).
        #
        # O flush é obrigatório: `_reconcile_characters` (acima) adiciona/remove `EventRole`
        # sem flush, e a comissão EducaManto incide sobre o LUCRO, que lê `event.roles`. Sem
        # ele a coleção volta do cache sem os cachês novos e a comissão sai errada.
        db.session.flush()
        sincronizar_comissao(event)

    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Comercial",
        message="Editou os dados do evento",
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()

    # Quem acabou de ser pré-escalado recebe o convite agora (feature 233): antes o cargo nascia
    # com pessoa e SEM convite, e nenhuma tela pedia para alguém clicar em "Convidar".
    from app.calendar.casting_ops import convidar_recem_escalados

    convidar_recem_escalados(event, recem_escalados, actor_name=actor_name, tz=tz)

    changed_core = (
        event.title != old_title
        or st != old_start
        or et != old_end
        or event.location != old_location
        or event.description != old_description
    )
    # Google PRIMEIRO, automação do tipo DEPOIS (feature 239): a saída de SHOW apaga ensaio no
    # Google Calendar e vagas de som para sempre, e só é segura com o título novo já na Agenda.
    # A regra do tipo continua sendo a última palavra sobre `needs_rehearsal` — o formulário
    # chega com a caixinha marcada mesmo quando o evento acabou de deixar de ser SHOW.
    warnings += _sincronizar_e_trocar_tipo(
        event,
        old_title=old_title,
        old_event_type=old_event_type,
        changed_core=changed_core,
        actor_name=actor_name,
        tz=tz,
    )

    return warnings


# ── Edição pontual na própria tela de detalhe — feature 215 ──────────────────
# A tela de abas edita cada bloco onde ele é exibido, sem desviar para o formulário grande
# (`PATCH /api/events/<id>`, que reescreve elenco e clientes em bloco). Cada função abaixo
# toca SÓ o seu conjunto de campos — nada de efeito colateral em elenco/cliente/pré-contrato.


def update_event_basics(
    event: Any,
    data: dict,
    *,
    actor_name: str,
    tz: ZoneInfo,
) -> list[str]:
    """Grava título, tipo, data/horário, local e descrição de um evento existente (feature 215).

    Recorte deliberado de `update_event_core`: os mesmos campos "de cabeçalho", a mesma
    sincronização best-effort com o Google Agenda e a mesma ordem "Google antes da automação do
    tipo" (feature 239), SEM tocar em elenco, clientes, valores ou pré-contrato — é a edição
    inline do cabeçalho da aba Resumo.

    Args:
        event: O `CalendarEvent` a atualizar.
        data: `title`, `event_type`, `date_str`, `start_str`, `end_str`, `location`,
            `description` — mesmo shape (parcial) de `_build_update_event_data`.
        actor_name: Nome de quem editou, para o `EventLog`.
        tz: Fuso usado no carimbo do log.

    Returns:
        Avisos não-bloqueantes (falha de sincronização com o Google, e o que a troca de tipo
        criou ou removeu automaticamente).

    Raises:
        EventTypeChangeBlocked: se o título novo não chegou ao Google numa troca de tipo com
            automação (entrar/sair de SHOW) — a troca é desfeita, o resto do salvamento fica.
    """
    from app.calendar.routes import _build_start_end

    d = date.fromisoformat(data["date_str"])
    st, et = _build_start_end(d, data["start_str"], data["end_str"])

    old_title, old_start, old_end = event.title, event.start_at, event.end_at
    old_location, old_description = event.location, event.description
    # Tipo ANTES da atribuição: é o que `aplicar_troca_de_tipo` compara logo abaixo (239).
    old_event_type = event.event_type

    event.event_type = data["event_type"] or None
    # O prefixo "(TIPO)" acompanha o tipo (feature 239) — é ele que o sync do Google lê de
    # volta, e `changed_core` empurra o título novo para a Agenda logo adiante.
    event.title = build_gc_title(data["title"], event.event_type)
    event.start_at = st
    event.end_at = et
    event.location = data["location"] or None
    event.description = data["description"] or None
    reclassificar_fora_de_sp(
        event, local_mudou=(event.location or "").strip() != (old_location or "").strip()
    )

    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Comercial",
        message="Editou os dados do evento",
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()

    changed_core = (
        event.title != old_title
        or st != old_start
        or et != old_end
        or event.location != old_location
        or event.description != old_description
    )
    # Mesma ordem obrigatória de `update_event_core` (feature 239): o título novo vai ao Google
    # ANTES da automação da troca de tipo, que é irreversível na saída de SHOW.
    return _sincronizar_e_trocar_tipo(
        event,
        old_title=old_title,
        old_event_type=old_event_type,
        changed_core=changed_core,
        actor_name=actor_name,
        tz=tz,
    )


def update_event_comercial(
    event: Any,
    data: dict,
    *,
    actor_name: str,
    tz: ZoneInfo,
    sincronizar_comissao: Any = None,
) -> None:
    """Grava os valores comerciais do evento na própria aba Comercial (feature 215).

    Mesmos campos e mesma regra de cortesia/permuta de `update_event_core` (venda zerada
    quando é cortesia), sem tocar em elenco, clientes ou pré-contrato.

    Args:
        event: O `CalendarEvent` a atualizar.
        data: Valores já convertidos (`sale_value`, `sale_value_gross`, `transport_value`,
            `with_invoice`, `is_cortesia_permuta`, `seller_id`, `sale_date`, `commission_rate`,
            `payment_method`, `payment_installments`, `payment_due_date`).
        actor_name: Nome de quem editou, para o `EventLog`.
        tz: Fuso usado no carimbo do log.
        sincronizar_comissao: Chamada com o evento depois de gravar, para criar ou atualizar a
            linha de comissão. Esta função escreve `sale_value`, `seller_id` e `commission_rate`
            — os três insumos da comissão — e até aqui não mexia nela: o gêmeo Jinja
            (`_handle_update_comercial`) sincronizava e esta não, então a mesma edição dava
            resultados diferentes conforme a tela usada.

            O estrago era pequeno porque `_resync_pending_commissions()` recalcula toda linha *a
            pagar* quando alguém abre a tela de comissões ou de pagamentos. Mas ele só percorre
            linhas que JÁ existem: uma venda que nunca gerou linha nenhuma nunca ganhava uma.

            Injetada, e não importada, para o domínio da agenda não puxar a régua de comissão de
            9 ramos do financeiro — mesmo arranjo de `calendar/group_ops.py`.
    """
    is_cortesia = bool(data.get("is_cortesia_permuta"))
    venda_anterior, data_anterior = event.sale_value, event.sale_date
    event.is_cortesia_permuta = is_cortesia
    event.sale_value = 0 if is_cortesia else data.get("sale_value")
    event.sale_value_gross = 0 if is_cortesia else data.get("sale_value_gross")
    event.transport_value = data.get("transport_value")
    event.with_invoice = bool(data.get("with_invoice"))
    event.seller_id = data.get("seller_id")
    event.sale_date = resolver_data_da_venda(
        data.get("sale_date"), event.sale_value, venda_anterior, data_anterior
    )
    event.commission_rate = data.get("commission_rate")
    event.payment_method = data.get("payment_method")
    event.payment_installments = data.get("payment_installments")
    event.payment_due_date = data.get("payment_due_date")

    # Antes do commit: `_sync_commission_payment` não commita, então as duas escritas saem juntas.
    if sincronizar_comissao is not None:
        sincronizar_comissao(event)

    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Comercial",
        message="Editou os valores comerciais",
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()


def set_event_clients(event: Any, client_pairs: list[tuple[int, str]]) -> None:
    """Substitui os clientes vinculados ao evento (feature 215).

    Mesmo par (id, relação) e mesma eleição de cliente principal de `update_event_core` —
    a lista recebida passa a ser a verdade, então mandar `[]` desvincula todo mundo.

    Args:
        event: O `CalendarEvent` dono dos vínculos.
        client_pairs: Pares `(client_id, relationship_type)` na ordem de exibição.
    """
    from app.calendar.routes import _create_client_links

    EventClient.query.filter_by(event_id=event.id).delete()
    event.client_id = None
    _create_client_links(event, client_pairs)
    db.session.commit()


def set_event_form_response(event: Any, form_response_id: int | None) -> bool:
    """Vincula (ou desvincula) o pré-contrato exibido na aba Comercial (feature 215).

    Uma resposta já vinculada a OUTRO evento não é roubada — mesma guarda de
    `_link_form_response`. Desvincular só solta a resposta que é deste evento.

    Args:
        event: O `CalendarEvent` alvo.
        form_response_id: Id da `FormResponse` a vincular, ou `None` para desvincular.

    Returns:
        `True` se o vínculo mudou; `False` quando o id não existe ou é de outro evento.
    """
    if form_response_id is None:
        changed = False
        for fr in FormResponse.query.filter_by(event_id=event.id).all():
            clear_event_link(fr)
            changed = True
        # Um commit depois do laço, não um por resposta — por isso o núcleo não commita.
        db.session.commit()
        return changed

    fr = FormResponse.query.get(form_response_id)
    if fr is None or (fr.event_id is not None and fr.event_id != event.id):
        return False
    apply_event_link(fr, event)
    db.session.commit()
    return True


def assignable_talents_for_event(event: Any) -> list[dict[str, Any]]:
    """Talentos ativos para a busca de casting, com foto e agenda do dia (feature 215).

    A busca de talento da tela de detalhe precisa das mesmas duas informações que o card já
    mostra depois de escalar: o rosto (`photo_face_path`) e o aviso de agenda. Reusa
    `talent_availability` — uma consulta só para todos os talentos, não uma por opção.

    Args:
        event: O `CalendarEvent` aberto (define a janela avaliada).

    Returns:
        Lista ordenada por nome com `id`, `name`, `artistic_name`, `photo_url` e
        `availability` (`{"status", "info"}`; `status="free"` quando não há choque).
    """
    talents = Talent.query.filter_by(status="active").order_by(Talent.full_name.asc()).all()
    availability = talent_availability(event, [t.id for t in talents])
    return [
        {
            "id": t.id,
            "name": t.full_name,
            "artistic_name": t.artistic_name,
            "photo_url": t.photo_face_path,
            "availability": availability.get(t.id) or {"status": "free", "info": ""},
        }
        for t in talents
    ]


# ── Detalhe do evento — feature 190 (refatoração da tela /events/:id) ─────────
# Núcleo das ações e cálculos que a tela de detalhe expõe e que até aqui só existiam
# inline na view Jinja (`app/calendar/routes.py::event_detail`). Extraídos para cá para
# que a API JSON os reúse sem duplicar regra (Princípio I).

_VALID_PAYMENT_STATUS = ("nao_pago", "pago", "no_banco", "fora_do_banco")

# Margem padrão de antecedência (min) quando `SiteSetting.departure_margin_minutes` é nulo.
DEFAULT_DEPARTURE_MARGIN_MINUTES = 60


def _naive(value: datetime | None) -> datetime | None:
    """Remove o fuso de um datetime para comparações seguras entre naive e aware."""
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _conflict_label(other_event: Any, start: datetime, end: datetime, overlaps: bool) -> str:
    """Texto do indicador de agenda de um talento ("Conflito: ..." ou o evento do mesmo dia)."""
    janela = f"{start.strftime('%d/%m/%Y %H:%M')} - {end.strftime('%d/%m/%Y %H:%M')}"
    prefixo = "Conflito: " if overlaps else ""
    return f"{prefixo}{other_event.title} ({janela})"


def talent_availability(event: Any, talent_ids: list[int]) -> dict[int, dict[str, str]]:
    """Disponibilidade de cada talento na janela do evento (mesma regra da view Jinja).

    Para cada talento devolve ``{"status": "free"|"same_day"|"conflict", "info": str}``:
    ``same_day`` quando ele tem outro evento no mesmo dia e ``conflict`` quando os horários
    se sobrepõem. Eventos anteriores ao mês corrente são ignorados — evita "fantasmas" de
    eventos já apagados no Google Agenda que continuam no banco.

    Args:
        event: O `CalendarEvent` aberto.
        talent_ids: Ids dos talentos a avaliar (tipicamente os escalados no evento).

    Returns:
        Mapa ``talent_id`` → estado da agenda. Vazio se o evento não tem `start_at`.
    """
    from app.models import CalendarEvent

    if not event.start_at or not talent_ids:
        return {}

    event_start = _naive(event.start_at)
    event_end = _naive(event.end_at) or (event_start + timedelta(hours=2))
    today = date.today()
    cutoff = datetime(today.year, today.month, 1)

    others = (
        EventRole.query.join(CalendarEvent)
        .filter(
            EventRole.talent_id.in_(talent_ids),
            CalendarEvent.id != event.id,
            # Evento cancelado (feature 224) não ocupa a agenda de ninguém — acusá-lo como
            # conflito impediria escalar o talento para um evento que ele está livre para fazer.
            CalendarEvent.cancelled_at.is_(None),
            CalendarEvent.start_at >= cutoff,
        )
        .all()
    )
    by_talent: dict[int, list[Any]] = {}
    for role in others:
        by_talent.setdefault(role.talent_id, []).append(role)

    availability: dict[int, dict[str, str]] = {}
    for talent_id in talent_ids:
        status, info = "free", ""
        for role in by_talent.get(talent_id, []):
            if not role.event or not role.event.start_at:
                continue
            other_start = _naive(role.event.start_at)
            other_end = _naive(role.event.end_at) or (other_start + timedelta(hours=2))
            if other_start.date() != event_start.date():
                continue
            overlaps = max(event_start, other_start) < min(event_end, other_end)
            status = "conflict" if overlaps else "same_day"
            info = _conflict_label(role.event, other_start, other_end, overlaps)
            if overlaps:
                break
        availability[talent_id] = {"status": status, "info": info}
    return availability


def set_payment_status(event: Any, role: Any, *, status: str) -> bool:
    """Grava o status de pagamento do cachê de um cargo. Núcleo de `_handle_set_payment_status`.

    Args:
        event: Evento dono do cargo (usado só para validar o vínculo).
        role: O `EventRole` a atualizar.
        status: Um de ``nao_pago``/``pago``/``no_banco``/``fora_do_banco``.

    Returns:
        True se gravou; False se o status é inválido ou o cargo não é do evento.
    """
    if status not in _VALID_PAYMENT_STATUS or role.event_id != event.id:
        return False
    role.payment_status = status
    db.session.commit()
    return True


def link_figurino_sheet(
    event: Any, role: Any, *, sheet_id: int | None, actor_name: str, tz: ZoneInfo
) -> bool:
    """Vincula (ou desvincula, com ``sheet_id=None``) uma ficha de figurino a um cargo.

    Núcleo de `_handle_link_figurino`, com o mesmo `EventLog` dos dois caminhos.

    Returns:
        True se gravou; False se o cargo não pertence ao evento ou a ficha não existe.
    """
    if role.event_id != event.id:
        return False
    if sheet_id is not None:
        sheet = FigurinoSheet.query.get(sheet_id)
        if sheet is None:
            return False
        role.figurino_sheet_id = sheet.id
        message = f"Vinculou ficha '{sheet.character_name}' ao personagem {role.character_name}"
    else:
        role.figurino_sheet_id = None
        message = f"Removeu ficha de figurino do personagem {role.character_name}"
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Figurino",
        message=message,
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()
    return True


def clear_figurino_done(event: Any, role: Any, *, actor_name: str, tz: ZoneInfo) -> None:
    """Desmarca o figurino separado de um cargo (contraparte de `casting_ops.set_figurino_done`).

    A tela nova trata "Separado" como caixa de seleção, então precisa do caminho de volta —
    o fluxo Jinja só tinha o de ida (botão "Marcar figurino"). Idempotente.
    """
    if role.figurino_done_at is None:
        return
    role.figurino_done_at = None
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Figurino",
        message=f"Desmarcou o figurino separado de {role.character_name}",
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()


def ensure_feedback_token(event: Any) -> str:
    """Devolve o token público de avaliação da cliente, gerando-o na primeira chamada.

    Token aleatório, nunca o id sequencial, para o link não ser adivinhável — a API
    reusa esta função para não ter uma segunda geração de token.
    """
    import secrets

    if not event.feedback_token:
        event.feedback_token = secrets.token_urlsafe(32)
        db.session.commit()
    return event.feedback_token


def suggested_departure_time(event: Any, settings: Any) -> str | None:
    """Horário de saída sugerido: início − (margem + tempo de viagem em cache).

    Returns:
        "HH:MM" ou None se falta o início do evento ou a estimativa de viagem.
    """
    if not event.start_at or event.travel_time_minutes is None:
        return None
    margin = DEFAULT_DEPARTURE_MARGIN_MINUTES
    if settings is not None and settings.departure_margin_minutes is not None:
        margin = settings.departure_margin_minutes
    return (event.start_at - timedelta(minutes=margin + event.travel_time_minutes)).strftime("%H:%M")


MAX_MATERIAL_MB = 20


def add_ensaio_file(
    event: Any, *, file_storage: Any, label: str, user_id: int | None
) -> Any | None:
    """Anexa um arquivo de ensaio ao evento, respeitando o limite de 20 MB.

    Usa `app.storage.save_file` (abstração local/S3) em vez do `file.save()` direto do fluxo
    Jinja — em produção os uploads não vão para o disco da aplicação.

    Returns:
        O `EnsaioMaterial` criado, ou None se não veio arquivo, se ele excede o limite ou se a
        extensão está fora de `ALLOWED_MATERIAL_EXTENSIONS` — o arquivo é servido por
        `/uploads`, no mesmo origin das SPAs, e extensão livre ali vira XSS armazenado.
    """
    from app.models import EnsaioMaterial
    from app.storage import ALLOWED_MATERIAL_EXTENSIONS, is_allowed_extension, save_file

    if not file_storage or not file_storage.filename:
        return None
    if not is_allowed_extension(file_storage.filename, ALLOWED_MATERIAL_EXTENSIONS):
        return None
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > MAX_MATERIAL_MB * 1024 * 1024:
        return None

    stored_path = save_file(file_storage, "ensaio_materials")
    material = EnsaioMaterial(
        event_id=event.id,
        user_id=user_id,
        material_type="file",
        label=label or file_storage.filename,
        file_path=stored_path,
    )
    db.session.add(material)
    db.session.commit()
    return material


def add_ensaio_link(event: Any, *, url: str, label: str, user_id: int | None) -> Any | None:
    """Anexa um link de referência (Drive, YouTube…) ao evento.

    Returns:
        O `EnsaioMaterial` criado, ou None se a URL veio vazia.
    """
    from app.models import EnsaioMaterial

    if not url:
        return None
    material = EnsaioMaterial(
        event_id=event.id,
        user_id=user_id,
        material_type="link",
        label=label or url[:60],
        url=url,
    )
    db.session.add(material)
    db.session.commit()
    return material


def delete_ensaio_material(material: Any) -> None:
    """Remove um material de ensaio e o arquivo correspondente (quando houver)."""
    from app.storage import delete_file

    if material.file_path:
        delete_file(material.file_path)
    db.session.delete(material)
    db.session.commit()


# ── Busca textual de eventos (agenda) ──────────────────────────────────────────

# Mesmo espírito de `client_ops._SEARCH_MIN_CHARS`: menos de 2 caracteres não busca.
SEARCH_MIN_CHARS = 2
SEARCH_LIMIT = 30


def search_events(q: str, limit: int = SEARCH_LIMIT) -> list[Any]:
    """Busca eventos por título, nome da cliente ou telefone (fonte única da agenda).

    Estratégia de match (paridade com `client_ops._name_search_conditions`):
    - título e nome da cliente sem acento, via `unaccent_lower_sql` (app/utils.py);
    - telefone por só-dígitos com `LIKE %digits%` — `Client.phone` já guarda DDI+DDD+número
      normalizado, então "(11) 98765-4321" digitado casa por substring.

    O vínculo evento↔cliente tem DUAS origens (feature 100): `event_clients` (fonte de
    verdade, inclui assessora/mãe) e `CalendarEvent.client_id` (denormalizado, cobre eventos
    antigos sem linha em `event_clients`). As duas entram em OR via EXISTS — sem duplicar
    linhas quando o cliente está nos dois caminhos.

    Args:
        q: Termo digitado (mínimo `SEARCH_MIN_CHARS` após strip).
        limit: Máximo de eventos devolvidos, mais recentes primeiro.

    Returns:
        Eventos ordenados por `start_at` decrescente, com `event_clients→client` e `client`
        pré-carregados (a serialização do resultado não faz N+1).
    """
    from sqlalchemy import nullslast, or_
    from sqlalchemy.orm import selectinload

    from app.models import CalendarEvent, Client
    from app.utils import strip_accents_lower, unaccent_lower_sql

    q = (q or "").strip()
    if len(q) < SEARCH_MIN_CHARS:
        return []

    # Curingas do LIKE escapados: sem isto, digitar "%%" ou "__" casa TODOS os eventos.
    term = (
        strip_accents_lower(q).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    like = f"%{term}%"
    digits = "".join(c for c in q if c.isdigit())

    client_conditions = [unaccent_lower_sql(Client.name).like(like, escape="\\")]
    if digits:
        client_conditions.append(Client.phone.ilike(f"%{digits}%"))
    client_match = or_(*client_conditions)

    return (
        CalendarEvent.query.filter(
            or_(
                unaccent_lower_sql(CalendarEvent.title).like(like, escape="\\"),
                CalendarEvent.event_clients.any(EventClient.client.has(client_match)),
                CalendarEvent.client.has(client_match),
            )
        )
        .options(
            selectinload(CalendarEvent.event_clients).selectinload(EventClient.client),
            selectinload(CalendarEvent.client),
        )
        .order_by(nullslast(CalendarEvent.start_at.desc()))
        .limit(limit)
        .all()
    )


# ── Ensaios: agendamento e presença (paridade com as rotas Jinja, pós-206) ─────
#
# Núcleo extraído de `create_ensaio`/`edit_ensaio`/`delete_ensaio`/`link_ensaio_parent` e
# `_handle_assign_tech_presence` de `app/calendar/routes.py`, para os endpoints JSON de
# `app/api/agenda_write.py` — a equipe de ensaio perdeu essas ações na aposentadoria das
# páginas Jinja. Algumas dependências (CALENDAR_ID, `_clear_event_side_tables`,
# PRESENCE_CHARACTER) são importadas EM RUNTIME de `routes` — só dentro das funções, nunca
# no topo, para não criar ciclo de import no boot (routes → event_ops).

ENSAIO_TITLE_PREFIX = "🟧 ENSAIO — "


class EnsaioValidationError(ValueError):
    """Erro de validação de agendamento de ensaio, com o campo apontado."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def _parse_hhmm(raw: str, field: str) -> Any:
    """`"HH:MM"` → `datetime.time`; formato inválido vira `EnsaioValidationError`."""
    from datetime import time as _time

    parts = (raw or "").strip().split(":")
    try:
        hour, minute = int(parts[0]), int(parts[1])
        return _time(hour, minute)
    except (IndexError, ValueError) as exc:
        raise EnsaioValidationError(field, "Horário inválido (use HH:MM).") from exc


def build_ensaio_times(date_str: str, start_str: str, end_str: str) -> tuple[datetime, datetime]:
    """Combina data + HH:MM em início/fim, com a regra da meia-noite da `_build_start_end`.

    Fim menor que o início = evento cruza a meia-noite (fim no dia seguinte, feature 071);
    fim IGUAL ao início é rejeitado.
    """
    try:
        d = date.fromisoformat((date_str or "").strip())
    except ValueError:
        raise EnsaioValidationError("date", "Data inválida.")

    start = datetime.combine(d, _parse_hhmm(start_str, "start"))
    end = datetime.combine(d, _parse_hhmm(end_str, "end"))
    if end < start:
        end += timedelta(days=1)
    if end == start:
        raise EnsaioValidationError("end", "Horário de fim deve ser diferente do início.")
    return start, end


def resolve_ensaio_location(location_type: str, custom_location: str) -> str:
    """Local do ensaio: "outro" com endereço preenchido, senão o endereço da Manto."""
    from app.models import SiteSetting

    custom = (custom_location or "").strip()
    if (location_type or "").strip() == "outro" and custom:
        return custom
    settings = SiteSetting.query.get(1)
    return (settings.manto_address or "") if settings else ""


def create_ensaio(
    parent: Any,
    *,
    date_str: str,
    start_str: str,
    end_str: str,
    description: str,
    location: str,
) -> Any:
    """Cria um ensaio vinculado ao show `parent` (Google Calendar + banco).

    Raises:
        EnsaioValidationError: data/horário inválidos.
        RuntimeError: falha na criação no Google Calendar (nada é gravado no banco).
    """
    from app.calendar.routes import CALENDAR_ID
    from app.calendar.service import insert_event
    from app.models import CalendarEvent

    start, end = build_ensaio_times(date_str, start_str, end_str)
    title = f"{ENSAIO_TITLE_PREFIX}{parent.title}"
    desc = (description or "").strip()

    created = insert_event(CALENDAR_ID, title, start, end, description=desc, location=location)
    ensaio = CalendarEvent(
        google_event_id=created["id"],
        title=title,
        description=desc or None,
        location=location or None,
        start_at=start,
        end_at=end,
        event_type="ENSAIO",
        parent_event_id=parent.id,
    )
    db.session.add(ensaio)
    db.session.commit()
    return ensaio


def update_ensaio(
    ensaio: Any,
    *,
    date_str: str,
    start_str: str,
    end_str: str,
    description: str,
    location: str,
) -> str | None:
    """Edita data/hora/descrição/local de um ensaio. Retorna aviso se o Google falhar."""
    from app.calendar.routes import CALENDAR_ID
    from app.calendar.service import update_event

    start, end = build_ensaio_times(date_str, start_str, end_str)
    desc = (description or "").strip()
    ensaio.start_at = start
    ensaio.end_at = end
    ensaio.description = desc or None
    new_location = (location or "").strip()
    if new_location:
        ensaio.location = new_location
    db.session.commit()

    if ensaio.google_event_id:
        try:
            update_event(
                CALENDAR_ID, ensaio.google_event_id, ensaio.title, start, end,
                description=desc, location=ensaio.location or "",
            )
        except RuntimeError as exc:
            return f"Salvo no banco, mas erro ao atualizar o Google Calendar: {exc}"
    return None


def delete_ensaio(ensaio: Any) -> str | None:
    """Cancela um ensaio (Google + banco). Retorna aviso se o Google falhar.

    A limpeza de tabelas satélite (`_clear_event_side_tables`) é a mesma da rota Jinja —
    sem ela o DELETE viola FK quando o ensaio tem histórico.
    """
    from app.calendar.routes import CALENDAR_ID, _clear_event_side_tables
    from app.calendar.service import delete_event

    warning = None
    if ensaio.google_event_id:
        try:
            delete_event(CALENDAR_ID, ensaio.google_event_id)
        except Exception as exc:  # noqa: BLE001 — falha do Google não trava a exclusão local
            logger.exception("Falha ao remover ensaio %s do Google Agenda", ensaio.id)
            warning = f"Removido do banco, mas erro ao remover do Google Calendar: {exc}"

    _clear_event_side_tables(ensaio.id)
    db.session.delete(ensaio)
    db.session.commit()
    return warning


def link_ensaio_to_show(ensaio: Any, parent: Any, actor_name: str) -> None:
    """Vincula um ensaio órfão a um show (feature 063), com registro no log do ensaio."""
    ensaio.parent_event_id = parent.id
    db.session.add(EventLog(
        event_id=ensaio.id,
        actor_name=actor_name,
        actor_role="Ensaio",
        message=f"Vinculou o ensaio ao show: {parent.title}",
    ))
    db.session.commit()


def assign_tech_presence(event: Any, talent_id: int | None, tz: ZoneInfo) -> bool:
    """Define (ou limpa) o talento da vaga 'Técnico de Som (Presença)' — tarefa do ensaio.

    Só toca o `talent_id` da role de presença; cachê e figurino ficam intactos (paridade
    com `_handle_assign_tech_presence`). Retorna False se o evento não tem a vaga.
    """
    from app.calendar.routes import PRESENCE_CHARACTER

    role = EventRole.query.filter_by(
        event_id=event.id, character_name=PRESENCE_CHARACTER, role_type="extra"
    ).first()
    if not role:
        return False
    role.talent_id = talent_id
    role.assigned_at = datetime.now(tz=tz) if talent_id else None
    db.session.commit()
    return True
