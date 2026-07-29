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

import logging
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.constants import RoleName
from app.email_service import send_async, send_ensaio_alert_email, send_event_changed_email
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


def _reconcile_characters(
    event: Any,
    characters: list[dict],
    *,
    coordinator_talent_id: int | None,
    is_superadmin: bool,
    start: datetime,
    end: datetime,
) -> list[str]:
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
    return warnings


def update_event_core(
    event: Any,
    data: dict,
    *,
    is_superadmin: bool,
    actor_name: str,
    tz: ZoneInfo,
) -> list[str]:
    """Atualiza em bloco os campos centrais de um evento existente (feature 184) — título, tipo,
    data/horário, local, descrição, ensaio, valores, pagamento, vendedor, elenco (reconciliado),
    clientes (substituídos) e pré-contrato vinculado. Núcleo de `PATCH /api/events/<id>`.

    `data` segue o mesmo shape de `_build_create_event_data` (routes.py/agenda_write.py), sem os
    campos exclusivos de criação (`orcamento_history_id`, `duracao`, `orc_caches`, `acrescimos`,
    reembolso, observações — esses não fazem parte da edição em bloco).

    Sincroniza título/data/horário/local/descrição com o Google Agenda quando mudam
    (best-effort — ver research.md §10): uma falha do Google não impede salvar no Manto, só vira
    um aviso na lista devolvida.

    Raises:
        EventCoreUpdateBlocked: se a reconciliação de elenco tentar remover um personagem com
            convite aceito e quem edita não for superadmin — nada é gravado nesse caso.

    Returns:
        Lista de avisos não-bloqueantes (conflito de agenda de talento pré-escalado, falha de
        sincronização com o Google).
    """
    from app.calendar.routes import CALENDAR_ID, _build_start_end, _create_client_links
    from app.calendar.service import update_event as google_update_event

    d = date.fromisoformat(data["date_str"])
    st, et = _build_start_end(d, data["start_str"], data["end_str"])

    old_title, old_start, old_end = event.title, event.start_at, event.end_at
    old_location, old_description = event.location, event.description

    # Reconciliação do elenco ANTES de qualquer outra escrita — se bloquear (convite aceito),
    # nada mais deste método deve ter efeito colateral.
    warnings = _reconcile_characters(
        event,
        data.get("characters") or [],
        coordinator_talent_id=data.get("coordinator_talent_id"),
        is_superadmin=is_superadmin,
        start=st,
        end=et,
    )

    event.title = data["title"]
    event.event_type = data["event_type"] or None
    event.start_at = st
    event.end_at = et
    event.location = data["location"] or None
    event.description = data["description"] or None
    event.needs_rehearsal = bool(data.get("needs_rehearsal"))

    is_cortesia = bool(data.get("is_cortesia_permuta"))
    event.is_cortesia_permuta = is_cortesia
    event.sale_value = 0 if is_cortesia else data.get("sale_value")
    event.sale_value_gross = 0 if is_cortesia else data.get("sale_value_gross")
    event.transport_value = data.get("transport_value")
    event.acrescimo_value = data.get("acrescimo_value")
    event.with_invoice = bool(data.get("with_invoice"))
    event.seller_id = data.get("seller_id")
    event.sale_date = data.get("sale_date")
    event.payment_method = data.get("payment_method")
    event.payment_installments = data.get("payment_installments")
    event.payment_due_date = data.get("payment_due_date")

    EventClient.query.filter_by(event_id=event.id).delete()
    _create_client_links(event, data.get("client_pairs") or [])

    form_response_id = data.get("form_response_id")
    if form_response_id is not None:
        fr = FormResponse.query.get(form_response_id)
        if fr and fr.event_id is None:
            fr.event_id = event.id

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
    if changed_core and event.google_event_id:
        try:
            google_update_event(
                CALENDAR_ID,
                event.google_event_id,
                event.title,
                st,
                et,
                description=event.description or "",
                location=event.location or "",
            )
        except Exception as exc:  # noqa: BLE001 — Google fora do ar não pode bloquear a edição
            logger.warning("falha ao sincronizar evento %s com o Google Agenda: %s", event.id, exc)
            warnings.append("Não foi possível sincronizar a mudança com o Google Agenda.")

    return warnings


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

    Mesma regra de `app/feedback/routes.py::gerar_link` (token aleatório, nunca o id) — a API
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
        O `EnsaioMaterial` criado, ou None se não veio arquivo ou ele excede o limite.
    """
    from app.models import EnsaioMaterial
    from app.storage import save_file

    if not file_storage or not file_storage.filename:
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
