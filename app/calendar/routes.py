from datetime import datetime, timezone, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
import calendar as cal
import json
import os
import re
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

from flask import Blueprint, redirect, request, session, url_for, render_template, current_app, abort, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from .service import (
    get_authorization_url,
    build_flow,
    save_token,
    fetch_events_for_month,
    fetch_single_event,
    parse_event_datetime,
    insert_event,
    update_event,
    delete_event,
)
from .. import db
from app.constants import RoleName, event_requires_client, ACRESCIMO_TIPO_BV, CLIENT_RELATION_TIPOS
from app.orcamento.settings import acrescimo_tipos_list
from app.money import format_brl, parse_brl, parse_brl_int
from app.models import CalendarEvent, EventRole, EventLog, Talent, EventContract, EventPayment, EventInstallment, EventInvoice, SiteSetting, User, Role, FigurinoSheet, EnsaioMaterial, EventObservation, OrcamentoHistory, EventRating, AuditLog, CommissionPayment, SpecialExpense, ClientFeedback, EventReimbursement, EventAcrescimo
from app.email_service import send_removal_email
from app.storage import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_INVOICE_EXTENSIONS,
    ALLOWED_MATERIAL_EXTENSIONS,
    is_allowed_extension,
)
# Notificadores de logística movidos para event_ops (feature 149); reimportados com alias para os
# call sites existentes (sync inclusive) seguirem inalterados. Dependência unidirecional routes→event_ops.
from app.calendar.event_ops import (
    notify_accepted_roles as _notify_accepted_roles,
    notify_ensaio_team as _notify_ensaio_team,
)

calendar_bp = Blueprint("calendar", __name__)

CALENDAR_ID = "eventos@mantoproducoes.com.br"
TZ = ZoneInfo("America/Sao_Paulo")
_CAN_ENSAIO      = {RoleName.ENSAIO, RoleName.CASTING, RoleName.SUPERADMIN}
_CAN_CREATE      = {RoleName.COMERCIAL, RoleName.SUPERADMIN}
_CAN_EDIT_EVENT  = {RoleName.CASTING, RoleName.FIGURINO, RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN}
_CAN_DELETE      = {RoleName.SUPERADMIN, RoleName.COMERCIAL}

# Técnico de Som padrão para eventos SHOW (Nivaldo de Andrade — recebe o PIX)
SOUND_TECH_TALENT_ID: int = 42

# Vaga "presença" definida pela equipe de ensaio (quem vai ao evento). É tarefa do ensaio,
# não do casting.
PRESENCE_CHARACTER: str = "Técnico de Som (Presença)"


def _build_start_end(d: date, start_str: str, end_str: str) -> tuple[datetime, datetime]:
    """Combina data + horários de início/fim em datetimes.

    Se o horário de fim for **menor** que o de início, o evento cruza a meia-noite: o fim é
    interpretado como sendo no **dia seguinte** (feature 071). Fim igual ao início mantém a mesma
    data (duração zero — o chamador valida e rejeita).

    Args:
        d: Data de início do evento.
        start_str: Horário de início no formato ``HH:MM``.
        end_str: Horário de fim no formato ``HH:MM``.

    Returns:
        Tupla ``(start, end)`` de ``datetime``.

    Raises:
        ValueError: Se algum horário não estiver em ``HH:MM``.
    """
    st = datetime.combine(d, datetime.strptime(start_str, "%H:%M").time())
    et = datetime.combine(d, datetime.strptime(end_str, "%H:%M").time())
    if et < st:
        et += timedelta(days=1)
    return st, et


def _mark_month_synced(ym: str) -> None:
    settings = SiteSetting.query.get(1)
    if not settings:
        return
    cache = json.loads(settings.calendar_sync_cache) if settings.calendar_sync_cache else {}
    cache[ym] = datetime.utcnow().isoformat()
    if len(cache) > 24:
        for k in sorted(cache.keys())[:-24]:
            del cache[k]
    settings.calendar_sync_cache = json.dumps(cache)
    db.session.commit()


def _month_sync_age_minutes(ym: str) -> int | None:
    """Minutos desde a última sincronização do mês, ou None se nunca sincronizado.

    Lê a mesma fonte de `_mark_month_synced` (SiteSetting.calendar_sync_cache).
    """
    settings = SiteSetting.query.get(1)
    if not settings or not settings.calendar_sync_cache:
        return None
    cache = json.loads(settings.calendar_sync_cache)
    ts_str = cache.get(ym)
    if not ts_str:
        return None
    age_seconds = (datetime.utcnow() - datetime.fromisoformat(ts_str)).total_seconds()
    return int(age_seconds // 60)


def _query_month_events(year: int, month: int) -> list["CalendarEvent"]:
    """Eventos que aparecem no mês (fonte única da agenda — reusada pela view e pela API 145).

    Inclui eventos que começam no mês e os que atravessam o mês (fim >= início do mês). Ordena
    por início. Não chama o Google — lê só do banco.
    """
    month_start_dt = datetime(year, month, 1)
    if month == 12:
        month_end_dt = datetime(year + 1, 1, 1)
    else:
        month_end_dt = datetime(year, month + 1, 1)
    return (
        CalendarEvent.query
        .filter(
            CalendarEvent.start_at < month_end_dt,
            db.or_(
                CalendarEvent.end_at >= month_start_dt,
                db.and_(CalendarEvent.end_at.is_(None), CalendarEvent.start_at >= month_start_dt),
            ),
        )
        .order_by(CalendarEvent.start_at)
        .all()
    )


def _build_events_from_db(
    year: int, month: int, month_start: date, month_end: date
) -> tuple[dict, dict, list]:
    """Constrói event_map, events_by_day e list_items a partir do banco (sem chamar Google)."""
    db_events = _query_month_events(year, month)

    event_map = {ev.google_event_id: ev.id for ev in db_events}
    events_by_day: dict[int, list] = {}

    for ev in db_events:
        if not ev.start_at:
            continue
        ev_start = ev.start_at.date()
        ev_end = ev.end_at.date() if ev.end_at else ev_start
        is_ensaio = ev.event_type == "ENSAIO" or "ensaio" in ev.title.lower()
        cur = max(ev_start, month_start)
        stop = min(ev_end, month_end)
        while cur <= stop:
            is_start_day = (cur == ev_start)
            if is_start_day:
                when = ev.start_at.strftime("%H:%M") if (ev.start_at.hour or ev.start_at.minute) else ""
                if ev.end_at and (ev.end_at.hour or ev.end_at.minute) and ev_end > ev_start:
                    when += f"–{ev.end_at.strftime('%d/%m %H:%M')}"
                elif ev.end_at and ev.end_at.strftime("%H:%M") != "00:00":
                    when += f"–{ev.end_at.strftime('%H:%M')}"
            else:
                when = "↪"
            events_by_day.setdefault(cur.day, []).append({
                "title": ev.title,
                "when": when,
                "event_id": ev.id,
                "is_ensaio": is_ensaio,
            })
            cur += timedelta(days=1)

    list_items = [
        {
            "id": ev.google_event_id,
            "summary": ev.title,
            "start": {"dateTime": ev.start_at.strftime("%Y-%m-%dT%H:%M:%S")} if ev.start_at else {},
            "location": ev.location or "",
        }
        for ev in db_events
    ]
    return event_map, events_by_day, list_items


def _clear_event_side_tables(event_id: int) -> None:
    """Remove os registros de um evento (ou ensaio) sem cascade automático (feature 122).

    ``EventLog``, ``EventContract``, ``EventPayment``, ``EventRating``, ``ClientFeedback``
    e ``EventReimbursement`` não têm ``cascade="all, delete-orphan"`` no relacionamento de
    ``CalendarEvent`` — sem esta limpeza, ``db.session.delete(event)`` falha com violação
    de chave estrangeira sempre que existir algum desses registros (ex.: histórico de
    ações do evento).
    """
    EventLog.query.filter_by(event_id=event_id).delete()
    EventContract.query.filter_by(event_id=event_id).delete()
    EventPayment.query.filter_by(event_id=event_id).delete()
    EventRating.query.filter_by(event_id=event_id).delete()
    ClientFeedback.query.filter_by(event_id=event_id).delete()
    EventReimbursement.query.filter_by(event_id=event_id).delete()


def _delete_event(event: CalendarEvent, also_from_google: bool = False) -> None:
    """Deleta um evento do banco removendo manualmente as tabelas sem cascade.

    Cascades automáticos: EventRole, EventObservation, ensaios, EnsaioMaterial.
    Sem cascade (deletados manualmente via ``_clear_event_side_tables``): EventLog,
    EventContract, EventPayment, EventRating, ClientFeedback, EventReimbursement.
    """
    _clear_event_side_tables(event.id)

    # Comissões: se pendente, cancela; se paga, cria estorno
    for cp in list(CommissionPayment.query.filter_by(event_id=event.id).all()):
        if cp.status == "a_pagar":
            cp.status = "cancelado"
            cp.event_id = None  # desvincula antes do delete do evento
        elif cp.status == "pago":
            # cria estorno para descontar no próximo ciclo
            db.session.add(CommissionPayment(
                event_id=None,
                event_title=cp.event_title,
                seller_id=cp.seller_id,
                sale_date=cp.sale_date,
                payable_from=cp.payable_from,
                amount=-cp.amount,
                status="a_pagar",
                original_id=cp.id,
                notes=f"Estorno automático: evento cancelado",
            ))
            cp.event_id = None

    if also_from_google and event.google_event_id:
        try:
            delete_event(CALENDAR_ID, event.google_event_id)
        except Exception as exc:  # noqa: BLE001 — qualquer falha do Google não pode travar a exclusão local
            current_app.logger.exception(
                "Falha ao remover evento %s do Google Agenda", event.id)
            flash(f"Salvo no banco, mas erro ao remover do Google Calendar: {exc}", "warning")
    db.session.delete(event)


def _cleanup_stale_events(items: list[dict], year: int, month: int) -> list[str]:
    """Remove do banco eventos do mês que foram deletados do Google Calendar.

    Atua sobre qualquer evento com google_event_id, independente do source.
    Seguro: só é chamado quando fetch_events_for_month() respondeu com sucesso.
    Retorna lista de títulos dos eventos removidos.
    """
    live_ids = {item.get("id") for item in items if item.get("id")}
    month_start_dt = datetime(year, month, 1)
    month_end_dt = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

    stale = (
        CalendarEvent.query
        .filter(
            # Qualquer evento com google_event_id que não existe mais no GCal é removido,
            # independente do source (google_calendar, platform ou NULL).
            # Seguro porque _cleanup_stale_events só é chamado quando o GCal respondeu
            # com sucesso (fetch não lançou RuntimeError).
            CalendarEvent.google_event_id.isnot(None),
            CalendarEvent.start_at >= month_start_dt,
            CalendarEvent.start_at < month_end_dt,
        )
        .all()
    )

    removed_titles: list[str] = []
    for ev in stale:
        if ev.google_event_id not in live_ids:
            # Venda virtual **nunca** é apagada por sumiço no Google (FR-029b). Apagar aqui
            # destruiria em cascata um pedido já pago — evento, escala e presente 3D — porque
            # alguém removeu uma linha do calendário. A equipe é sinalizada e decide.
            if _is_virtual_event(ev):
                _log_sync(
                    "virtual_divergente", ev,
                    details=f"Evento de venda virtual sumiu do Google Calendar "
                            f"({year}-{month:02d}) — NÃO removido do sistema, pedido segue válido.",
                )
                continue
            _log_sync("auto_deleted", ev, details=f"Não encontrado no Google Calendar ({year}-{month:02d})")
            removed_titles.append(ev.title)
            _delete_event(ev)

    if removed_titles:
        db.session.commit()

    return removed_titles


def _log_sync(
    action: str,
    event: CalendarEvent | None = None,
    details: str | None = None,
    actor: str | None = None,
    actor_role: str | None = None,
) -> None:
    """Registra ação da agenda no AuditLog. Não faz commit — inclua no commit do caller."""
    detail_parts = []
    if event and event.google_event_id:
        detail_parts.append(f"gcal:{event.google_event_id}")
    if details:
        detail_parts.append(details)
    db.session.add(AuditLog(
        actor_name=actor or "Sistema",
        actor_role=actor_role,
        entity_type="agenda",
        entity_id=event.id if event else None,
        entity_name=event.title if event else None,
        action=action,
        detail=" | ".join(detail_parts) if detail_parts else None,
    ))


def _oauth_redirect_uri() -> str:
    """Retorna o redirect_uri do OAuth — usa env var em produção para garantir HTTPS correto."""
    override = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")
    if override:
        return override
    return url_for("calendar.google_callback", _external=True)


@calendar_bp.route("/google/connect")
@login_required
def google_connect():
    redirect_uri = _oauth_redirect_uri()
    auth_url, state = get_authorization_url(redirect_uri)
    session["google_oauth_state"] = state
    return redirect(auth_url)


@calendar_bp.route("/google/callback")
@login_required
def google_callback():
    state = session.get("google_oauth_state")
    redirect_uri = _oauth_redirect_uri()

    flow = build_flow(redirect_uri)
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    save_token(creds)

    return redirect(url_for("calendar.agenda"))


@calendar_bp.route("/agenda")
@login_required
def agenda():
    ym = request.args.get("ym", "").strip()
    view = request.args.get("view", "calendar").strip()
    force_sync = request.args.get("force_sync") == "1"
    now = datetime.now()

    if ym:
        year, month = ym.split("-")
        year = int(year)
        month = int(month)
    else:
        year = now.year
        month = now.month
        ym = f"{year:04d}-{month:02d}"

    first_weekday, days_in_month = cal.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end   = date(year, month, days_in_month)

    if force_sync:
        # Sincronização ao vivo SÓ quando o usuário pede explicitamente ("Atualizar agora").
        try:
            items = fetch_events_for_month(CALENDAR_ID, year, month)
            sync_events(items)
            _cleanup_stale_events(items, year, month)
            _mark_month_synced(ym)
            flash("Agenda atualizada.", "success")
        except RuntimeError:
            flash("Google Calendar não conectado. Use o botão 'Google' acima para conectar.", "warning")
        # Redireciona para a URL sem force_sync: evita re-sincronizar em F5 e
        # renderiza pelo caminho rápido (banco) já fresco.
        return redirect(url_for("calendar.agenda", ym=ym, view=view))

    # Caminho padrão: SEMPRE serve do banco — abertura instantânea, sem chamada de rede.
    # O frescor é mantido pelo cron externo (sync_worker.py) + botão "Atualizar agora".
    event_map, events_by_day, items = _build_events_from_db(year, month, month_start, month_end)

    first_weekday = (first_weekday + 1) % 7
    weeks = []
    week = []
    for _ in range(first_weekday):
        week.append(None)
    for d in range(1, days_in_month + 1):
        week.append(d)
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        while len(week) < 7:
            week.append(None)
        weeks.append(week)

    if month == 1:
        prev_ym = f"{year-1:04d}-12"
    else:
        prev_ym = f"{year:04d}-{month-1:02d}"

    if month == 12:
        next_ym = f"{year+1:04d}-01"
    else:
        next_ym = f"{year:04d}-{month+1:02d}"

    # Na view de lista, no mês atual, mostra apenas eventos de hoje em diante
    is_current_month = (year == now.year and month == now.month)
    if view == "list" and is_current_month:
        today_str = now.date().isoformat()  # "YYYY-MM-DD"
        def _event_date(item) -> str:
            start = item.get("start", {})
            return (start.get("dateTime") or start.get("date") or "")[:10]
        list_events = [i for i in items if _event_date(i) >= today_str]
    else:
        list_events = items

    sync_age_min = _month_sync_age_minutes(ym)

    return render_template(
        "calendar_list.html",
        ym=ym,
        prev_ym=prev_ym,
        next_ym=next_ym,
        events=list_events,
        event_map=event_map,
        view=view,
        month_weeks=weeks,
        events_by_day=events_by_day,
        today=now.date(),
        sync_age_min=sync_age_min,
    )


@calendar_bp.route("/agenda/day/<date_str>")
@login_required
def agenda_day(date_str: str):
    try:
        day_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for("calendar.agenda"))

    day_start = datetime(day_date.year, day_date.month, day_date.day)
    day_end   = day_start + timedelta(days=1)

    events = (
        CalendarEvent.query
        .filter(CalendarEvent.start_at >= day_start, CalendarEvent.start_at < day_end)
        .order_by(CalendarEvent.start_at)
        .all()
    )

    prev_day = (day_date - timedelta(days=1)).isoformat()
    next_day = (day_date + timedelta(days=1)).isoformat()
    ym       = day_date.strftime("%Y-%m")

    return render_template(
        "calendar_day.html",
        day=day_date,
        events=events,
        ym=ym,
        prev_day=prev_day,
        next_day=next_day,
    )


# ─── Event Detail — action handlers ──────────────────────────────────────────

def _handle_assign_casting(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    # Adaptador fino: a regra vive em casting_ops.assign_role (fonte única, feature 146),
    # reusada pelo endpoint JSON POST /api/roles/<id>/assign. Aqui só lemos o form e damos flash.
    role_id_raw = request.form.get("role_id", "")
    if not role_id_raw.isdigit():
        return
    role = EventRole.query.filter_by(id=int(role_id_raw), event_id=event.id).first()
    if not role:
        return
    from app.calendar.casting_ops import assign_role
    message = assign_role(
        event,
        role,
        talent_id=request.form.get("talent_id"),
        cache_value=request.form.get("cache_value"),
        travel_cache=request.form.get("travel_cache"),
        actor_name=current_user.name,
        is_superadmin=any(r.name == RoleName.SUPERADMIN for r in current_user.roles),
        tz=tz_sp,
    )
    if message:
        flash(message, "success")


def _handle_add_role(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    # Adaptador fino — a regra vive em casting_ops.add_role (feature 147).
    character_name = request.form.get("character_name", "").strip()
    if not character_name:
        return
    from app.calendar.casting_ops import add_role
    add_role(
        event,
        character_name=character_name,
        talent_id=request.form.get("talent_id"),
        cache_value=request.form.get("cache_value"),
        role_type=request.form.get("role_type", "character"),
        actor_name=current_user.name,
        tz=tz_sp,
    )


def _handle_delete_role(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    # Adaptador fino — regra em casting_ops.delete_role. Gate CASTING/SUPERADMIN.
    can_casting = any(r.name.upper() in (RoleName.CASTING, RoleName.SUPERADMIN) for r in current_user.roles)
    if not can_casting:
        return
    role_id_raw = request.form.get("role_id", "")
    # int() explícito: filter_by(id=string) quebra em manto_local (psycopg3). Ver memória.
    if not str(role_id_raw).isdigit():
        return
    role = EventRole.query.filter_by(id=int(role_id_raw), event_id=event.id).first()
    if not role:
        return
    from app.calendar.casting_ops import delete_role
    delete_role(
        event,
        role,
        is_superadmin=any(r.name.upper() == RoleName.SUPERADMIN for r in current_user.roles),
        actor_name=current_user.name,
        tz=tz_sp,
    )


def _handle_figurino_done(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    # Adaptador fino — regra em casting_ops.set_figurino_done (feature 148).
    role_id_raw = request.form.get("role_id", "")
    # int() explícito: filter_by(id=string) quebra em manto_local (psycopg3). Ver memória.
    if not str(role_id_raw).isdigit():
        return
    role = EventRole.query.filter_by(id=int(role_id_raw), event_id=event.id).first()
    if not role:
        return
    from app.calendar.casting_ops import set_figurino_done
    set_figurino_done(event, role, actor_name=current_user.name, tz=tz_sp)


def _handle_add_contract(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    file = request.files.get("contract_file")
    if not file or not file.filename:
        flash("Selecione o arquivo do contrato para enviar.", "error")
        return
    fpath = _save_bounded_upload(
        file, current_app.config["UPLOAD_CONTRACTS"], "contracts", max_mb=10
    )
    if not fpath:
        flash("Contrato não enviado: use PDF ou imagem de até 10 MB.", "error")
        return
    db.session.add(EventContract(
        event_id=event.id,
        file_path=fpath,
        amount=None,
    ))
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message="Adicionou contrato assinado",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()
    flash("Contrato enviado.", "success")


def _save_bounded_upload(
    file_storage,
    upload_dir: str,
    subpath: str,
    *,
    max_mb: int = 10,
    allowed: frozenset[str] = ALLOWED_DOCUMENT_EXTENSIONS,
) -> str | None:
    """Salva um arquivo enviado por form, respeitando limite de tamanho e allowlist de extensão.

    Fonte única para "checar tamanho + secure_filename + salvar", reaproveitada por nota
    fiscal, contrato, comprovante de pagamento e comprovante de reembolso (feature 153) — antes
    duplicada inline em cada handler.

    A allowlist é obrigatória: sem ela um `.html` sobe e é servido inline por `/uploads`, no
    mesmo origin das SPAs — XSS armazenado com a sessão de quem abrir o link.

    Args:
        file_storage: o ``FileStorage`` recebido do form (ou None).
        upload_dir: diretório absoluto onde salvar (ex.: ``current_app.config["UPLOAD_PAYMENTS"]``).
        subpath: segmento usado no caminho público (``/uploads/<subpath>/<nome>``).
        max_mb: limite de tamanho em megabytes.
        allowed: allowlist de extensões (padrão: documento — imagem ou PDF).

    Returns:
        O caminho público do arquivo ou None se não houve upload válido (sem arquivo, acima do
        limite ou extensão fora da allowlist).
    """
    if not file_storage or not file_storage.filename:
        return None
    if not is_allowed_extension(file_storage.filename, allowed):
        return None
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_mb * 1024 * 1024:
        return None
    fname = secure_filename(file_storage.filename)
    # Prefixo único obrigatório: `secure_filename` puro fazia uploads homônimos ("comprovante.pdf")
    # sobrescreverem o binário anterior em silêncio — dois EventPayment apontando para o mesmo
    # arquivo e o original do primeiro perdido, sem rastro para auditoria.
    unique = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_{fname}"
    file_storage.save(os.path.join(upload_dir, unique))
    return f"/uploads/{subpath}/{unique}"


def _save_nf_file(file_storage) -> str | None:
    """Salva o arquivo de uma nota fiscal em UPLOAD_INVOICES.

    Args:
        file_storage: o ``FileStorage`` recebido do form (ou None).

    Returns:
        O caminho público do arquivo (``/uploads/invoices/<nome>``) ou None se não houve
        upload válido (sem arquivo ou acima de 10 MB).
    """
    return _save_bounded_upload(
        file_storage,
        current_app.config["UPLOAD_INVOICES"],
        "invoices",
        max_mb=10,
        allowed=ALLOWED_INVOICE_EXTENSIONS,
    )


def _add_invoice_record(
    event: CalendarEvent,
    *,
    amount: Decimal | None,
    issue_date: date | None,
    file_storage,
) -> EventInvoice | None:
    """Adiciona UMA nota fiscal ao evento (feature 153 — ação isolada, não mexe nas existentes).

    Mesma regra de "nova nota" já usada na reconciliação do formulário de venda: rejeita só se
    valor, data e arquivo vierem todos vazios. Não altera `event.with_invoice` nem qualquer
    outra nota já cadastrada — a edição completa da lista continua só no formulário de venda
    (Jinja).

    Args:
        event: evento ao qual a nota pertence.
        amount: valor da nota, ou None.
        issue_date: data de emissão, ou None.
        file_storage: arquivo da nota (``FileStorage``) ou None.

    Returns:
        A ``EventInvoice`` criada, ou None se os três campos vierem vazios.
    """
    if amount is None and issue_date is None and not (file_storage and file_storage.filename):
        return None
    file_path = _save_nf_file(file_storage)
    invoice = EventInvoice(
        event_id=event.id,
        amount=amount,
        issue_date=issue_date,
        file=file_path,
        status="emitida" if file_path else "a_emitir",
        issued_at=datetime.now(tz=ZoneInfo("America/Sao_Paulo")) if file_path else None,
    )
    db.session.add(invoice)
    return invoice


def _parse_client_pairs() -> list[tuple[int, str]]:
    """Lê client_id[]/client_relation[] do form e devolve pares (client_id, relação) válidos.

    Compartilhado entre o save da venda (features 094/100) e a criação de evento (feature
    114): dedup por cliente, ignora ids inexistentes, relação fora da lista vira "Outros".
    """
    from app.models import Client

    _cli_ids  = request.form.getlist("client_id[]")
    _cli_rels = request.form.getlist("client_relation[]")
    _pairs: list[tuple[int, str]] = []
    _seen_cli: set[int] = set()
    for _i, _cid in enumerate(_cli_ids):
        _cid = (_cid or "").strip()
        if not _cid.isdigit():
            continue
        _cid_int = int(_cid)
        if _cid_int in _seen_cli or Client.query.get(_cid_int) is None:
            continue
        _rel = (_cli_rels[_i].strip() if _i < len(_cli_rels) else "") or "Contratante"
        if _rel not in CLIENT_RELATION_TIPOS:
            _rel = "Outros"
        _seen_cli.add(_cid_int)
        _pairs.append((_cid_int, _rel))
    return _pairs


def _primary_client_id(pairs: list[tuple[int, str]]) -> int | None:
    """client_id denormalizado: o Contratante, ou o primeiro da lista (compat de telas)."""
    primary = next((c for c, r in pairs if r == "Contratante"), None)
    if primary is None and pairs:
        primary = pairs[0][0]
    return primary


def _handle_update_comercial(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    can_vendas = any(r.name.upper() in (RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN) for r in current_user.roles)
    if not can_vendas:
        return

    # ── Clientes associados (features 094/100) ──────────────────────────────
    # Múltiplos clientes por evento, cada um com uma relação. Lê client_id[]/client_relation[], valida,
    # e recria as associações. Eventos elegíveis exigem ≥1 cliente. Bloqueia ANTES de qualquer alteração.
    from app.models import EventClient

    _pairs = _parse_client_pairs()

    # Só considera a seção de clientes se o editor foi enviado (marcador oculto), mesmo com zero clientes.
    _clients_submitted = request.form.get("clients_editor") == "1"

    if _clients_submitted and event_requires_client(event) and not _pairs:
        flash(
            "Associe ao menos um cliente ao evento para salvar os dados de venda. "
            "Busque na base ou cadastre um novo cliente.",
            "error",
        )
        return

    if _clients_submitted:
        EventClient.query.filter_by(event_id=event.id).delete()
        for _cid_int, _rel in _pairs:
            db.session.add(EventClient(event_id=event.id, client_id=_cid_int, relationship_type=_rel))
        # client_id denormalizado = contratante (ou o primeiro), p/ compat de telas que mostram "o cliente".
        event.client_id = _primary_client_id(_pairs)

    event.sale_value       = parse_brl(request.form.get("sale_value", ""))
    event.sale_value_gross = parse_brl(request.form.get("sale_value_gross", ""))
    event.transport_value  = parse_brl(request.form.get("transport_value", ""))
    event.acrescimo_value = parse_brl(request.form.get("acrescimo_value", ""))
    event.with_invoice    = request.form.get("with_invoice") == "1"
    event.is_cortesia_permuta = request.form.get("is_cortesia_permuta") == "1"
    if event.is_cortesia_permuta:
        # Permuta/cortesia: a venda é tratada como 0 (cachê dos talentos vira marketing).
        event.sale_value = 0
    sale_date_raw = request.form.get("sale_date", "").strip()
    try:
        event.sale_date = date.fromisoformat(sale_date_raw) if sale_date_raw else event.sale_date
    except ValueError:
        pass

    # ── Acréscimos tipados (feature 099) ─────────────────────────────────────
    # Recria a coleção a partir das linhas do form; congela o valor efetivo em R$ (amount_brl):
    # R$ direto, ou % sobre o valor de venda. O tipo BV guarda recebedor/PIX para a planilha de pagamentos.
    from app.models import EventAcrescimo as _EventAcrescimo

    _acr_tipos      = request.form.getlist("acrescimo_tipo[]")
    _acr_descricoes = request.form.getlist("acrescimo_descricao[]")
    _acr_valores    = request.form.getlist("acrescimo_value[]")
    _acr_percents   = request.form.getlist("acrescimo_is_percent[]")
    _acr_bv_recip   = request.form.getlist("acrescimo_bv_recipient[]")
    _acr_bv_pix     = request.form.getlist("acrescimo_bv_pix[]")

    if _acr_tipos:  # só mexe nos acréscimos se o editor foi enviado (evita apagar em POSTs de outras seções)
        # preserva o status de pagamento de BVs já existentes (por recebedor+pix), para não "despagar"
        _prev_bv_status = {
            (a.bv_recipient or "", a.bv_pix or ""): a.bv_payment_status
            for a in event.acrescimos if a.is_bv
        }
        _EventAcrescimo.query.filter_by(event_id=event.id).delete()
        _sale = Decimal(event.sale_value or 0)
        for _i, _tipo in enumerate(_acr_tipos):
            _tipo = (_tipo or "").strip()
            if not _tipo:
                continue
            _val = parse_brl(_acr_valores[_i]) if _i < len(_acr_valores) else None
            if _val is None or _val == 0:
                continue
            _is_pct = (_acr_percents[_i] == "1") if _i < len(_acr_percents) else False
            _amount = (
                (_sale * Decimal(_val) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if _is_pct else Decimal(_val)
            )
            _is_bv = _tipo == ACRESCIMO_TIPO_BV
            _recip = (_acr_bv_recip[_i].strip() if _i < len(_acr_bv_recip) else "") or None
            _pix = (_acr_bv_pix[_i].strip() if _i < len(_acr_bv_pix) else "") or None
            _status = _prev_bv_status.get((_recip or "", _pix or ""), "nao_pago") if _is_bv else "nao_pago"
            db.session.add(_EventAcrescimo(
                event_id=event.id,
                tipo=_tipo,
                descricao=(_acr_descricoes[_i].strip() if _i < len(_acr_descricoes) else "") or None,
                is_percent=_is_pct,
                value=Decimal(_val),
                amount_brl=_amount,
                is_bv=_is_bv,
                bv_recipient=_recip if _is_bv else None,
                bv_pix=_pix if _is_bv else None,
                bv_payment_status=_status,
            ))

    # ── Notas fiscais (feature 069): coleção de notas por evento (valor + data + arquivo) ──
    # Linhas do form: nf_key[] ("id_<n>" p/ existente, "new_*" p/ nova), nf_amount[], nf_date[];
    # arquivo opcional por linha em nf_file__<key>. Linha com arquivo → nota "emitida".
    if not event.with_invoice:
        # venda deixou de ser "com nota": remove as notas
        EventInvoice.query.filter_by(event_id=event.id).delete()
    else:
        _existing = {inv.id: inv for inv in event.invoices}
        _keys = request.form.getlist("nf_key[]")
        _amounts = request.form.getlist("nf_amount[]")
        _dates = request.form.getlist("nf_date[]")
        _seen_ids: set[int] = set()
        for _i, _key in enumerate(_keys):
            _key = (_key or "").strip()
            if not _key:
                continue
            _amt = parse_brl(_amounts[_i]) if _i < len(_amounts) else None
            _draw = (_dates[_i] if _i < len(_dates) else "").strip()
            try:
                _dval = date.fromisoformat(_draw) if _draw else None
            except ValueError:
                _dval = None
            _upload = _save_nf_file(request.files.get(f"nf_file__{_key}"))
            if _key.startswith("id_") and _key[3:].isdigit():
                _inv = _existing.get(int(_key[3:]))
                if not _inv:
                    continue
                _seen_ids.add(_inv.id)
                _inv.amount = _amt
                _inv.issue_date = _dval
                if _upload:
                    _inv.file = _upload
                    if _inv.status != "emitida":
                        _inv.status = "emitida"
                        _inv.issued_at = datetime.now(tz=tz_sp)
            else:  # nova nota
                if _amt is None and not _dval and not _upload:
                    continue
                db.session.add(EventInvoice(
                    event_id=event.id, amount=_amt, issue_date=_dval, file=_upload,
                    status="emitida" if _upload else "a_emitir",
                    issued_at=datetime.now(tz=tz_sp) if _upload else None,
                ))
        # remove notas existentes que não vieram no form (removidas pelo usuário)
        for _id, _inv in _existing.items():
            if _id not in _seen_ids:
                db.session.delete(_inv)
        # sinaliza divergência soma != total (sem bloquear)
        _sum = sum((parse_brl(x) or Decimal("0") for x in _amounts), Decimal("0"))
        if event.sale_value and _sum and _sum != Decimal(event.sale_value):
            flash(
                f"Atenção: a soma das notas (R$ {_sum:.2f}) é diferente do valor da venda "
                f"(R$ {Decimal(event.sale_value):.2f}).",
                "warning",
            )

    _VALID_METHODS = {"avista", "pix_parcelado", "faturado", "cartao", "futuro", "parcelado_datas"}
    pay_method = request.form.get("payment_method", "").strip()
    event.payment_method = pay_method if pay_method in _VALID_METHODS else None
    if pay_method == "pix_parcelado":
        _inst_raw = request.form.get("payment_installments", "").strip()
        event.payment_installments = int(_inst_raw) if _inst_raw.isdigit() else None
    if pay_method in ("faturado", "futuro"):
        due_raw = request.form.get("payment_due_date", "").strip()
        try:
            event.payment_due_date = date.fromisoformat(due_raw) if due_raw else None
        except ValueError:
            event.payment_due_date = None
        if pay_method == "futuro" and not event.payment_due_date:
            flash("Pagamento futuro: informe a data combinada de pagamento.", "error")

    # Cronograma de parcelas com data + valor (feature 065): recria as parcelas do evento.
    if pay_method == "parcelado_datas":
        EventInstallment.query.filter_by(event_id=event.id).delete()
        _dates = request.form.getlist("parcela_date[]")
        _amounts = request.form.getlist("parcela_amount[]")
        for _i, _draw in enumerate(_dates):
            _draw = (_draw or "").strip()
            _amt = parse_brl(_amounts[_i]) if _i < len(_amounts) else None
            if not _draw or _amt is None:
                continue
            try:
                _d = date.fromisoformat(_draw)
            except ValueError:
                continue
            db.session.add(EventInstallment(event_id=event.id, due_date=_d, amount=_amt))

    if any(r.name.upper() == RoleName.COMERCIAL for r in current_user.roles):
        if not event.seller_id:
            event.seller_id = current_user.id
    if any(r.name.upper() in (RoleName.FINANCEIRO, RoleName.SUPERADMIN) for r in current_user.roles):
        seller_raw = request.form.get("seller_id", "").strip()
        event.seller_id = int(seller_raw) if seller_raw else None
    # Taxa de comissão por evento: só o super admin altera (travada para os demais).
    if any(r.name.upper() == RoleName.SUPERADMIN for r in current_user.roles):
        rate_raw = request.form.get("commission_rate", "").strip()
        try:
            event.commission_rate = float(Decimal(rate_raw)) if rate_raw else None
        except ValueError:
            event.commission_rate = None

    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message=f"Atualizou dados comerciais: venda R$ {event.sale_value or 0}{'  (com NF)' if event.with_invoice else ''}",
        created_at=datetime.now(tz=tz_sp),
    ))
    from app.financeiro.routes import _sync_commission_payment
    _sync_commission_payment(event)
    db.session.commit()


def _handle_link_figurino(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    role_id  = request.form.get("role_id")
    sheet_id = request.form.get("figurino_sheet_id")
    role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
    if not role:
        return
    role.figurino_sheet_id = int(sheet_id) if sheet_id else None
    if role.figurino_sheet_id:
        sheet = FigurinoSheet.query.get(role.figurino_sheet_id)
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=current_user.name,
            actor_role="Figurino",
            message=f"Vinculou ficha '{sheet.character_name if sheet else sheet_id}' ao personagem {role.character_name}",
            created_at=datetime.now(tz=tz_sp),
        ))
    else:
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=current_user.name,
            actor_role="Figurino",
            message=f"Removeu ficha de figurino do personagem {role.character_name}",
            created_at=datetime.now(tz=tz_sp),
        ))
    db.session.commit()


def _handle_set_payment_status(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    role_id = request.form.get("role_id")
    status  = request.form.get("payment_status")
    _VALID  = {"nao_pago", "pago", "no_banco", "fora_do_banco"}
    role = EventRole.query.filter_by(id=role_id, event_id=event.id).first()
    if role and status in _VALID:
        role.payment_status = status
        db.session.commit()


def _handle_add_payment(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    amount = parse_brl(request.form.get("payment_amount"))
    if not amount or amount <= 0:
        flash("Informe o valor recebido para adicionar o pagamento.", "error")
        return
    file = request.files.get("payment_file")
    if not file or not file.filename:
        flash("Anexe o comprovante para adicionar o pagamento.", "error")
        return
    fpath = _save_bounded_upload(
        file, current_app.config["UPLOAD_PAYMENTS"], "payments", max_mb=10
    )
    if not fpath:
        flash("Comprovante não enviado: use PDF ou imagem de até 10 MB.", "error")
        return
    db.session.add(EventPayment(
        event_id=event.id,
        file_path=fpath,
        amount=amount,
    ))
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message=f"Adicionou pagamento recebido de R$ {amount}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()
    flash("Pagamento registrado.", "success")


def _is_superadmin() -> bool:
    return any(r.name.upper() == RoleName.SUPERADMIN for r in current_user.roles)


def _handle_edit_payment(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    if not _is_superadmin():
        flash("Apenas o super admin pode editar comprovantes.", "error")
        return
    payment = EventPayment.query.filter_by(
        id=request.form.get("payment_id"), event_id=event.id
    ).first()
    if not payment:
        return
    amount = parse_brl(request.form.get("payment_amount"))
    if not amount or amount <= 0:
        flash("Informe um valor válido para o comprovante.", "error")
        return
    old_amount = payment.amount or 0
    payment.amount = amount
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message=f"Corrigiu valor de comprovante: R$ {old_amount} → R$ {amount}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()
    flash("Valor do comprovante atualizado.", "success")


def _handle_delete_payment(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    if not _is_superadmin():
        flash("Apenas o super admin pode excluir comprovantes.", "error")
        return
    payment = EventPayment.query.filter_by(
        id=request.form.get("payment_id"), event_id=event.id
    ).first()
    if not payment:
        return
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message=f"Excluiu comprovante de R$ {payment.amount or 0}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.delete(payment)
    db.session.commit()
    flash("Comprovante excluído.", "success")


def _add_payment_record(
    event: CalendarEvent, *, amount: Decimal | None, file_storage
) -> EventPayment | None:
    """Adiciona um comprovante de pagamento ao evento (feature 153).

    Paridade com `_handle_add_payment`: exige valor E arquivo.

    Args:
        event: evento ao qual o pagamento pertence.
        amount: valor recebido.
        file_storage: arquivo do comprovante (``FileStorage``).

    Returns:
        O ``EventPayment`` criado, ou None se faltar valor válido ou arquivo (ausente/> 10 MB).
    """
    if not amount or amount <= 0:
        return None
    file_path = _save_bounded_upload(
        file_storage, current_app.config["UPLOAD_PAYMENTS"], "payments", max_mb=10
    )
    if not file_path:
        return None
    payment = EventPayment(event_id=event.id, file_path=file_path, amount=amount)
    db.session.add(payment)
    return payment


def _edit_payment_amount(payment: EventPayment, *, amount: Decimal | None) -> bool:
    """Corrige o valor de um comprovante já lançado. Paridade com `_handle_edit_payment`."""
    if not amount or amount <= 0:
        return False
    payment.amount = amount
    return True


def _delete_payment_record(payment: EventPayment) -> None:
    """Exclui um comprovante de pagamento. Paridade com `_handle_delete_payment`."""
    db.session.delete(payment)


def _handle_add_reembolso(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    """Registra um novo reembolso a cobrar da cliente (feature 136)."""
    description = (request.form.get("reembolso_description") or "").strip()
    amount = parse_brl(request.form.get("reembolso_amount"))
    if not description:
        flash("Informe a descrição do reembolso.", "error")
        return
    if not amount or amount <= 0:
        flash("Informe o valor do reembolso.", "error")
        return
    invoice_path = _save_nf_file(request.files.get("reembolso_invoice_file"))
    db.session.add(EventReimbursement(
        event_id=event.id,
        description=description[:200],
        amount=amount,
        invoice_file_path=invoice_path,
        created_by_id=current_user.id,
    ))
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message=f"Registrou reembolso a cobrar: {description[:200]} — R$ {amount}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()
    flash("Reembolso registrado.", "success")


def _handle_collect_reembolso(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    """Marca um reembolso como cobrado, com comprovante e valor recebido (feature 136)."""
    reembolso_id_raw = request.form.get("reembolso_id", "")
    if not reembolso_id_raw.isdigit():
        return
    reembolso = EventReimbursement.query.filter_by(
        id=int(reembolso_id_raw), event_id=event.id
    ).first()
    if not reembolso:
        return
    if reembolso.is_collected:
        flash("Esse reembolso já foi marcado como cobrado.", "error")
        return
    amount = parse_brl(request.form.get("reembolso_collected_amount"))
    if not amount or amount <= 0:
        flash("Informe o valor recebido do reembolso.", "error")
        return
    file = request.files.get("reembolso_receipt_file")
    if not file or not file.filename:
        flash("Anexe o comprovante para marcar o reembolso como cobrado.", "error")
        return
    fpath = _save_bounded_upload(
        file, current_app.config["UPLOAD_PAYMENTS"], "payments", max_mb=10
    )
    if not fpath:
        flash("Comprovante não enviado: use PDF ou imagem de até 10 MB.", "error")
        return
    reembolso.collected_at = datetime.now(tz=tz_sp)
    reembolso.collected_amount = amount
    reembolso.receipt_file_path = fpath
    reembolso.collected_by_id = current_user.id
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message=f"Marcou reembolso como cobrado: {reembolso.description} — R$ {amount}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()
    flash("Reembolso marcado como cobrado.", "success")


def _handle_delete_reembolso(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    if not _is_superadmin():
        flash("Apenas o super admin pode excluir reembolsos.", "error")
        return
    reembolso_id_raw = request.form.get("reembolso_id", "")
    if not reembolso_id_raw.isdigit():
        return
    reembolso = EventReimbursement.query.filter_by(
        id=int(reembolso_id_raw), event_id=event.id
    ).first()
    if not reembolso:
        return
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message=f"Excluiu reembolso: {reembolso.description} — R$ {reembolso.amount or 0}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.delete(reembolso)
    db.session.commit()
    flash("Reembolso excluído.", "success")


def _add_reimbursement_record(
    event: CalendarEvent,
    *,
    description: str,
    amount: Decimal | None,
    file_storage,
    created_by_id: int,
) -> EventReimbursement | None:
    """Registra um reembolso a cobrar da cliente (feature 153). Paridade com
    `_handle_add_reembolso` — comprovante do gasto original é opcional.

    Args:
        event: evento ao qual o reembolso pertence.
        description: descrição do gasto (obrigatória).
        amount: valor a cobrar (obrigatório).
        file_storage: comprovante do gasto original (``FileStorage``) ou None.
        created_by_id: id do usuário que registrou o reembolso.

    Returns:
        O ``EventReimbursement`` criado, ou None se faltar descrição ou valor válido.
    """
    description = (description or "").strip()
    if not description or not amount or amount <= 0:
        return None
    reimbursement = EventReimbursement(
        event_id=event.id,
        description=description[:200],
        amount=amount,
        invoice_file_path=_save_nf_file(file_storage),
        created_by_id=created_by_id,
    )
    db.session.add(reimbursement)
    return reimbursement


def _collect_reimbursement_record(
    reimbursement: EventReimbursement,
    *,
    collected_amount: Decimal | None,
    file_storage,
    collected_by_id: int,
) -> bool:
    """Marca um reembolso como cobrado (feature 153). Paridade com `_handle_collect_reembolso`
    — exige valor recebido E comprovante de recebimento; recusa se já cobrado.

    Returns:
        True se marcado com sucesso, False se já cobrado ou faltar valor/arquivo válido.
    """
    if reimbursement.is_collected:
        return False
    if not collected_amount or collected_amount <= 0:
        return False
    file_path = _save_bounded_upload(
        file_storage, current_app.config["UPLOAD_PAYMENTS"], "payments", max_mb=10
    )
    if not file_path:
        return False
    reimbursement.collected_at = datetime.now(tz=ZoneInfo("America/Sao_Paulo"))
    reimbursement.collected_amount = collected_amount
    reimbursement.receipt_file_path = file_path
    reimbursement.collected_by_id = collected_by_id
    return True


def _delete_reimbursement_record(reimbursement: EventReimbursement) -> None:
    """Exclui um reembolso. Paridade com `_handle_delete_reembolso`."""
    db.session.delete(reimbursement)


def _handle_delete_contract(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    if not _is_superadmin():
        flash("Apenas o super admin pode excluir contratos.", "error")
        return
    contract = EventContract.query.filter_by(
        id=request.form.get("contract_id"), event_id=event.id
    ).first()
    if not contract:
        return
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message="Excluiu contrato enviado",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.delete(contract)
    db.session.commit()
    flash("Contrato excluído.", "success")


def _handle_toggle_contract_signed(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    if not _is_superadmin():
        flash("Apenas o super admin pode alterar o status do contrato.", "error")
        return
    contract = EventContract.query.filter_by(
        id=request.form.get("contract_id"), event_id=event.id
    ).first()
    if not contract:
        return
    contract.is_signed = not contract.is_signed
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=current_user.name,
        actor_role="Comercial",
        message=f"Marcou contrato como {'assinado' if contract.is_signed else 'pendente'}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()
    flash("Status do contrato atualizado.", "success")


def _add_contract_record(
    event: CalendarEvent, *, file_storage, is_signed: bool = False
) -> EventContract | None:
    """Adiciona um contrato ao evento (feature 153). Paridade com `_handle_add_contract`.

    Args:
        event: evento ao qual o contrato pertence.
        file_storage: arquivo do contrato (``FileStorage``).
        is_signed: se o contrato já vem assinado no momento do envio (feature 184) — paridade
            com o checkbox "Contrato já assinado" do formulário de evento. Não usa o mesmo
            caminho de `_toggle_contract_signed` (restrito a superadmin): aqui é só o estado
            inicial do registro, informado por quem está subindo o arquivo.

    Returns:
        O ``EventContract`` criado, ou None se não houver arquivo válido (ausente ou > 10 MB).
    """
    file_path = _save_bounded_upload(
        file_storage, current_app.config["UPLOAD_CONTRACTS"], "contracts", max_mb=10
    )
    if not file_path:
        return None
    contract = EventContract(
        event_id=event.id, file_path=file_path, amount=None, is_signed=is_signed
    )
    db.session.add(contract)
    return contract


def _delete_contract_record(contract: EventContract) -> None:
    """Exclui um contrato. Paridade com `_handle_delete_contract`."""
    db.session.delete(contract)


def _toggle_contract_signed(contract: EventContract) -> None:
    """Alterna `is_signed`. Paridade com `_handle_toggle_contract_signed`."""
    contract.is_signed = not contract.is_signed


def _handle_toggle_confirmado(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    """Adaptador fino — regra em event_ops.toggle_confirmed (feature 149). RBAC Comercial/SA.

    Independente do botão "Confirmar dados do evento" (que só copia uma mensagem de WhatsApp):
    este é o registro persistido de que o evento foi de fato confirmado.
    """
    if not any(r.name.upper() in (RoleName.COMERCIAL, RoleName.SUPERADMIN) for r in current_user.roles):
        flash("Apenas comercial/super admin podem confirmar o evento.", "error")
        return
    from app.calendar.event_ops import toggle_confirmed
    confirmed = toggle_confirmed(
        event, actor_name=current_user.name, actor_id=current_user.id, tz=tz_sp
    )
    flash(
        "Evento marcado como confirmado." if confirmed else "Confirmação do evento desfeita.",
        "success",
    )


def _handle_send_invite(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    # Adaptador fino — regra em casting_ops.send_invite (feature 148). Aqui só form + flash.
    role_id_raw = request.form.get("role_id", "")
    # int() explícito: filter_by(id=string) quebra em manto_local (psycopg3). Ver memória.
    if not str(role_id_raw).isdigit():
        return
    role = EventRole.query.filter_by(id=int(role_id_raw), event_id=event.id).first()
    if not role or not role.talent_id:
        return
    from app.calendar.casting_ops import send_invite
    email_sent = send_invite(event, role, actor_name=current_user.name, tz=tz_sp)
    msg = f"Convite marcado como enviado para {role.talent.full_name}."
    if email_sent:
        msg += " Email enviado."
    elif role.talent.email_contact:
        msg += " (falha no envio do email)"
    flash(msg, "success")


def _handle_save_logistics(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    """Adaptador fino — regra em event_ops.save_logistics (feature 149)."""
    from app.calendar.event_ops import resolve_makeup_location, save_logistics
    save_logistics(
        event,
        makeup_time=request.form.get("makeup_time", ""),
        makeup_location=resolve_makeup_location(
            request.form.get("makeup_location"), request.form.get("makeup_location_custom")
        ),
        departure_time=request.form.get("departure_time", ""),
        departure_location=request.form.get("departure_location", ""),
        needs_rehearsal=bool(request.form.get("needs_rehearsal")),
        actor_name=current_user.name,
        tz=tz_sp,
    )
    flash("Logística salva.", "success")


def _handle_assign_tech_presence(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    """Permite à equipe de ensaio designar quem vai presencialmente como técnico de som.

    Só atualiza o talent_id da role 'Técnico de Som (Presença)'. Não altera cache nem figurino.
    """
    talent_id = request.form.get("talent_id")
    role = EventRole.query.filter_by(
        event_id=event.id,
        character_name=PRESENCE_CHARACTER,
        role_type="extra",
    ).first()
    if not role:
        return
    role.talent_id = int(talent_id) if talent_id else None
    role.assigned_at = datetime.now(tz=tz_sp) if role.talent_id else None
    db.session.commit()


# Campos comerciais zerados quando um evento se torna satélite (FR-005).
_SATELLITE_FIELDS_CLEARED = (
    "sale_value", "sale_value_gross", "sale_date", "with_invoice",
    "is_cortesia_permuta", "seller_id", "commission_rate",
    "payment_method", "payment_installments", "payment_due_date",
    "transport_value", "acrescimo_value", "invoice_file", "orcamento_history_id",
)


def _has_financial_data(event: CalendarEvent) -> bool:
    """True se o evento já tem valor de venda preenchido (gatilho de confirmação na FR-005)."""
    return bool(event.sale_value)


def _group_events(event: CalendarEvent) -> list[CalendarEvent]:
    """Retorna todos os eventos do mesmo grupo comercial que `event`, o principal primeiro.

    Se `event` não pertence a nenhum grupo, retorna ``[event]`` — mesmo comportamento de
    um evento avulso, sem agregação (feature 137).
    """
    if event.is_satellite:
        leader = event.group_leader
        return [leader, *leader.satellites]
    if event.is_group_leader:
        return [event, *event.satellites]
    return [event]


def _apply_satellite(event: CalendarEvent) -> None:
    """Zera os campos comerciais de um evento ao vinculá-lo como satélite de um grupo (FR-005)."""
    for field in _SATELLITE_FIELDS_CLEARED:
        setattr(event, field, False if field == "with_invoice" else None)
    event.is_cortesia_permuta = False


def _can_group_events() -> bool:
    return any(
        r.name.upper() in (RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN)
        for r in current_user.roles
    )


def _resolve_group_selection(
    event: CalendarEvent,
) -> tuple[CalendarEvent | None, list[CalendarEvent], str | None]:
    """Lê o formulário de agrupamento e resolve principal + satélites.

    Returns:
        (leader, satellites, error) — em caso de erro, `error` traz a mensagem amigável
        e os demais vêm vazios; do contrário `error` é None.
    """
    target_ids = [t for t in request.form.getlist("target_event_ids") if t.strip().isdigit()]
    if not target_ids:
        return None, [], "Selecione ao menos um evento para agrupar."

    targets = CalendarEvent.query.filter(CalendarEvent.id.in_([int(t) for t in target_ids])).all()
    if len(targets) != len(set(target_ids)):
        return None, [], "Selecione eventos válidos para agrupar."
    if any(t.id == event.id for t in targets):
        return None, [], "Não é possível agrupar um evento a ele mesmo."  # FR-004

    participants = {event.id: event, **{t.id: t for t in targets}}
    leader_raw = request.form.get("leader_event_id", "").strip()
    if leader_raw not in {str(pid) for pid in participants}:
        return None, [], "Selecione qual evento é o principal do grupo."  # FR-004

    leader = participants.pop(int(leader_raw))
    satellites = list(participants.values())
    return leader, satellites, None


def _validate_group_satellites(leader: CalendarEvent, satellites: list[CalendarEvent]) -> str | None:
    """Aplica as regras de integridade da feature 053 a cada participante. Retorna erro ou None."""
    if leader.is_satellite:
        return f'"{leader.title}" já é satélite de outro grupo e não pode ser principal.'
    # Um principal que já lidera um grupo pode receber novos satélites (mesma regra da 053).
    if leader.event_type == "ENSAIO":  # FR-003
        return "Eventos do tipo ENSAIO não podem ser agrupados por este mecanismo."
    for sat in satellites:
        if sat.event_type == "ENSAIO":  # FR-003
            return "Eventos do tipo ENSAIO não podem ser agrupados por este mecanismo."
        if sat.is_satellite:  # FR-002
            return f'"{sat.title}" já pertence a outro grupo — desagrupe antes de continuar.'
        if sat.is_group_leader:
            return f'"{sat.title}" já é principal de outro grupo — desagrupe os satélites dele antes.'
    return None


def _handle_group_events(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    """Vincula `event` e os eventos selecionados sob um único grupo comercial (FR-001/FR-003)."""
    if not _can_group_events():
        flash("Apenas Comercial, Financeiro ou Super Admin podem agrupar eventos.", "error")
        return

    leader, satellites, error = _resolve_group_selection(event)
    if error:
        flash(error, "error")
        return

    error = _validate_group_satellites(leader, satellites)
    if error:
        flash(error, "error")
        return

    if request.form.get("confirm_clear_financials") != "1":
        com_venda = [s for s in satellites if _has_financial_data(s)]
        if com_venda:
            nomes = ", ".join(f'"{s.title}"' for s in com_venda)
            flash(
                f"{nomes} já tem valor de venda preenchido. Marque a confirmação para "
                "substituí-lo pelos dados do evento principal e tente novamente.",
                "error",
            )
            return

    group_name = request.form.get("group_name", "").strip()
    if group_name:
        leader.group_name = group_name

    now = datetime.now(tz=tz_sp)
    for sat in satellites:
        _apply_satellite(sat)
        sat.group_leader_id = leader.id
        db.session.add(EventLog(
            event_id=leader.id, actor_name=current_user.name, actor_role="Comercial",
            message=f'Agrupou o evento "{sat.title}" como satélite deste contrato',
            created_at=now,
        ))
        db.session.add(EventLog(
            event_id=sat.id, actor_name=current_user.name, actor_role="Comercial",
            message=f'Vinculado ao grupo do evento "{leader.title}" — dados comerciais agora seguem o principal',
            created_at=now,
        ))
    db.session.commit()
    flash(
        f'Eventos agrupados: "{leader.title}" é o evento principal '
        f"({len(satellites)} satélite{'s' if len(satellites) != 1 else ''}).",
        "success",
    )


def _handle_ungroup_event(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    """Desfaz o vínculo de um evento satélite, devolvendo-o ao estado independente (FR-008)."""
    if not _can_group_events():
        flash("Apenas Comercial, Financeiro ou Super Admin podem desagrupar eventos.", "error")
        return
    if not event.is_satellite:
        flash("Este evento não pertence a um grupo.", "error")
        return

    leader = event.group_leader
    event.group_leader_id = None
    db.session.add(EventLog(
        event_id=event.id, actor_name=current_user.name, actor_role="Comercial",
        message=f'Desfez o agrupamento com "{leader.title if leader else "?"}" '
                "— campos comerciais voltam a ser próprios e editáveis",
        created_at=datetime.now(tz=tz_sp),
    ))
    if leader:
        db.session.add(EventLog(
            event_id=leader.id, actor_name=current_user.name, actor_role="Comercial",
            message=f'O evento "{event.title}" deixou de ser satélite deste contrato',
            created_at=datetime.now(tz=tz_sp),
        ))
    db.session.commit()
    flash("Agrupamento desfeito.", "success")


def _handle_rename_group(event: CalendarEvent, tz_sp: ZoneInfo) -> None:
    """Define/edita/limpa o nome do grupo, sempre no evento principal (feature 055)."""
    if not _can_group_events():
        flash("Apenas Comercial, Financeiro ou Super Admin podem renomear grupos.", "error")
        return
    if not event.is_group_leader:
        flash("Apenas o evento principal de um grupo pode ser renomeado.", "error")
        return

    novo_nome = request.form.get("group_name", "").strip() or None
    event.group_name = novo_nome
    rotulo = f'"{novo_nome}"' if novo_nome else "o título do evento (sem nome)"
    db.session.add(EventLog(
        event_id=event.id, actor_name=current_user.name, actor_role="Comercial",
        message=f"Nome do grupo definido para {rotulo}",
        created_at=datetime.now(tz=tz_sp),
    ))
    db.session.commit()
    flash("Nome do grupo atualizado.", "success")


_EVENT_ACTIONS = {
    "assign_casting":       _handle_assign_casting,
    "assign_tech_presence": _handle_assign_tech_presence,
    "add_role":             _handle_add_role,
    "delete_role":          _handle_delete_role,
    "figurino_done":        _handle_figurino_done,
    "add_contract":         _handle_add_contract,
    "update_comercial":     _handle_update_comercial,
    "update_sale":          _handle_update_comercial,
    "link_figurino":        _handle_link_figurino,
    "set_payment_status":   _handle_set_payment_status,
    "add_payment":          _handle_add_payment,
    "edit_payment":         _handle_edit_payment,
    "delete_payment":       _handle_delete_payment,
    "add_reembolso":        _handle_add_reembolso,
    "collect_reembolso":    _handle_collect_reembolso,
    "delete_reembolso":     _handle_delete_reembolso,
    "delete_contract":      _handle_delete_contract,
    "toggle_contract_signed": _handle_toggle_contract_signed,
    "toggle_confirmado":    _handle_toggle_confirmado,
    "send_invite":          _handle_send_invite,
    "save_logistics":       _handle_save_logistics,
    "group_events":         _handle_group_events,
    "ungroup_event":        _handle_ungroup_event,
    "rename_group":         _handle_rename_group,
}


@calendar_bp.route("/events/<int:event_id>", methods=["GET", "POST"])
@login_required
def event_detail(event_id: int):
    event = CalendarEvent.query.get_or_404(event_id)
    tz_sp = ZoneInfo("America/Sao_Paulo")
    raw_logs = EventLog.query.filter_by(event_id=event.id).order_by(EventLog.created_at.desc()).all()
    logs = []
    for log in raw_logs:
        dt = log.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(tz_sp)
        logs.append(
            {
                "ts": dt.strftime("%d%m%Y_%H:%M:%S"),
                "actor_name": log.actor_name,
                "actor_role": log.actor_role,
                "message": log.message,
            }
        )

    if request.method == "POST":
        action = request.form.get("action")
        _can_edit = any(r.name.upper() in _CAN_EDIT_EVENT for r in current_user.roles)
        # Equipe de ensaio pode apenas designar o técnico de presença
        _can_tech = (
            action == "assign_tech_presence"
            and any(r.name.upper() in _CAN_ENSAIO for r in current_user.roles)
        )
        if not _can_edit and not _can_tech:
            abort(403)
        handler = _EVENT_ACTIONS.get(action)
        eid = event.id  # capture before commit+thread expire the ORM object
        if handler:
            handler(event, tz_sp)
        return redirect(url_for("calendar.event_detail", event_id=eid))

    # Ensaio: página simplificada dedicada (feature 062) — não carrega os painéis de show.
    if event.event_type == "ENSAIO":
        can_manage_ensaio = current_user.is_authenticated and any(
            r.name.upper() in _CAN_ENSAIO for r in current_user.roles
        )
        candidate_shows = []
        if can_manage_ensaio:
            candidate_shows = (
                CalendarEvent.query
                .filter(~CalendarEvent.title.like("🟧 ENSAIO%"), CalendarEvent.id != event.id)
                .order_by(CalendarEvent.start_at.desc())
                .all()
            )
        return render_template(
            "ensaio_detail.html",
            event=event,
            parent=event.parent,
            logs=logs,
            show_ensaio=can_manage_ensaio,
            candidate_shows=candidate_shows,
            settings=SiteSetting.query.get(1),
        )

    talents = Talent.query.filter_by(status="active").order_by(Talent.full_name.asc()).all()
    contracts = EventContract.query.filter_by(event_id=event.id).order_by(EventContract.created_at.desc()).all()
    payments = EventPayment.query.filter_by(event_id=event.id).order_by(EventPayment.created_at.desc()).all()
    reembolsos = EventReimbursement.query.filter_by(event_id=event.id).order_by(EventReimbursement.created_at.desc()).all()
    reembolsos_pendentes_total = sum((r.amount or 0 for r in reembolsos if not r.is_collected), Decimal("0"))

    # Figurino: fichas disponíveis + sugestão automática por nome do personagem
    from app.figurino.drive_service import normalize_name as _norm_name
    figurino_sheets = FigurinoSheet.query.order_by(FigurinoSheet.character_name.asc()).all()
    sheet_by_norm = {s.character_name_norm: s for s in figurino_sheets if s.character_name_norm}
    suggested_sheets = {
        r.id: sheet_by_norm.get(_norm_name(r.character_name))
        for r in event.roles
        if not r.figurino_sheet_id
    }

    # disponibilidade por talento (mesmo dia / conflito de horario)
    def _naive(dt):
        """Remove timezone info para comparações seguras."""
        if dt is None:
            return None
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    availability = {}
    if event.start_at:
        event_start = _naive(event.start_at)
        event_end = _naive(event.end_at or (event.start_at + timedelta(hours=2)))
        # Ignora conflitos com eventos de meses anteriores ao atual — evita "fantasmas"
        # de eventos já deletados do Google Calendar que ainda existem no banco.
        _today = date.today()
        _conflict_cutoff = datetime(_today.year, _today.month, 1)
        for t in talents:
            conflicts = (
                EventRole.query.join(CalendarEvent)
                .filter(
                    EventRole.talent_id == t.id,
                    CalendarEvent.id != event.id,
                    CalendarEvent.start_at >= _conflict_cutoff,
                )
                .all()
            )
            # Já alocado em outro personagem NESTE MESMO evento?
            same_event = EventRole.query.filter(
                EventRole.talent_id == t.id,
                EventRole.event_id == event.id,
            ).first()
            if same_event:
                availability[t.id] = {
                    "status": "conflict",
                    "info": f"{same_event.character_name} · {_naive(event.start_at).strftime('%Hh') if event.start_at else '?'} > {_naive(event.end_at).strftime('%Hh') if event.end_at else '?'}",
                }
                continue

            status = "free"
            info = ""
            for r in conflicts:
                if not r.event or not r.event.start_at:
                    continue
                other_start = _naive(r.event.start_at)
                other_end = _naive(r.event.end_at or (r.event.start_at + timedelta(hours=2)))
                if other_start.date() == event_start.date():
                    status = "same_day"
                    info = f"{r.event.title} ({other_start.strftime('%d/%m/%Y %H:%M')} - {other_end.strftime('%d/%m/%Y %H:%M')})"
                    if max(event_start, other_start) < min(event_end, other_end):
                        status = "conflict"
                        info = f"Conflito: {r.event.title} ({other_start.strftime('%d/%m/%Y %H:%M')} - {other_end.strftime('%d/%m/%Y %H:%M')})"
                        break
            availability[t.id] = {"status": status, "info": info}

    _is_real_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)
    _impersonate = session.get("impersonate_role") if _is_real_superadmin else None

    def has_role(name: str) -> bool:
        if _impersonate:
            return _impersonate.upper() == name.upper()
        return any(r.name.upper() == name.upper() for r in current_user.roles)

    settings = SiteSetting.query.get(1)
    default_commission = Decimal(str(
        settings.default_commission_rate if settings and settings.default_commission_rate is not None else 2
    ))
    # Painel financeiro agregado por grupo comercial (feature 137): um evento agrupado
    # (principal ou satélite) mostra custo/gastos/lucro do CONTRATO inteiro, não só do
    # evento aberto — venda/comissão vêm sempre do principal (`kpi_event`), que é quem
    # mantém esses campos preenchidos (satélites os têm zerados ao entrar no grupo).
    group_events = _group_events(event)
    kpi_event = group_events[0]
    event_group_size = len(group_events)
    event_rate = (
        Decimal(str(kpi_event.commission_rate))
        if kpi_event.commission_rate is not None else default_commission
    )
    event_cost = sum(
        (r.cache_value or 0 for ge in group_events for r in ge.roles if r.talent_id), 0
    )
    # Gastos extras aprovados vinculados a qualquer evento do grupo (entram como custo:
    # lucro = venda − cachês − gastos).
    event_expenses = (
        SpecialExpense.query
        .filter(
            SpecialExpense.event_id.in_([ge.id for ge in group_events]),
            SpecialExpense.status == "aprovado",
        )
        .order_by(SpecialExpense.expense_date.desc(), SpecialExpense.id.desc())
        .all()
    )
    event_expenses_total = sum((e.amount for e in event_expenses), Decimal("0"))
    # BV (feature 099): repasse a terceiros — sai da base de comissão e desconta do lucro.
    event_bv_total = sum(
        (
            Decimal(a.amount_brl)
            for ge in group_events for a in ge.acrescimos if a.is_bv and a.amount_brl
        ),
        Decimal("0"),
    )
    _commission_base = Decimal(kpi_event.sale_value or 0) - event_bv_total
    if _commission_base < 0:
        _commission_base = Decimal("0")
    event_commission = (
        _commission_base * event_rate / Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sellers = User.query.join(User.roles).filter(Role.name == RoleName.COMERCIAL).order_by(User.name.asc()).all()

    show_comercial = has_role(RoleName.COMERCIAL) or has_role(RoleName.FINANCEIRO) or has_role(RoleName.SUPERADMIN)
    show_financeiro = has_role(RoleName.FINANCEIRO) or has_role(RoleName.SUPERADMIN)
    show_ensaio = has_role(RoleName.ENSAIO) or has_role(RoleName.CASTING) or has_role(RoleName.SUPERADMIN)

    has_makeup_role = any(
        r.character_name and "maquiador" in r.character_name.lower()
        for r in event.roles
    )

    event_ratings = (
        EventRating.query
        .filter_by(event_id=event.id)
        .order_by(EventRating.submitted_at.desc())
        .all()
    )

    client_feedbacks = (
        ClientFeedback.query
        .filter_by(event_id=event.id)
        .order_by(ClientFeedback.submitted_at.desc())
        .all()
    )

    # Candidatos a agrupar: todos os eventos não-ENSAIO exceto o próprio (sem janela de data,
    # feature 054). A busca/filtragem é feita no cliente; eventos já agrupados aparecem
    # desabilitados na UI (não some, para o usuário entender o porquê).
    groupable_events = []
    if show_comercial and not event.is_satellite:
        groupable_events = (
            CalendarEvent.query
            .filter(
                CalendarEvent.id != event.id,
                CalendarEvent.event_type != "ENSAIO",
            )
            .order_by(CalendarEvent.start_at.desc())
            .all()
        )

    # ── Mensagens de confirmação/cobrança (feature 083) ─────────────────────
    # Dados fixos da mensagem (a saudação por horário é montada no cliente, no clique).
    confirm_characters = " + ".join(parse_characters(event.title))
    confirm_date_line = _format_event_date_ptbr(event.start_at, event.end_at)
    confirm_location = event.location or ""

    # Valor em aberto + data limite para o botão de cobrança.
    # Política padrão: o saldo vence "2 dias antes do evento" (dia inteiro). Quando não há data limite
    # explícita (faturado/futuro) nem parcelas com data, cai nessa política baseada na DATA do evento —
    # assim o botão libera a partir das 00:00 do dia 2 dias antes, e não exatamente 48h antes.
    _today = date.today()
    _policy_due = (
        event.start_at.date() - timedelta(days=2) if event.start_at else None
    )
    unreceived = [i for i in event.installments if not i.received]
    if event.installments:
        cobranca_outstanding = sum((i.amount or 0 for i in unreceived), Decimal("0"))
        _due_dates = [i.due_date for i in unreceived if i.due_date]
        cobranca_due = min(_due_dates) if _due_dates else _policy_due
    else:
        _received = sum((p.amount or 0 for p in payments), Decimal("0"))
        cobranca_outstanding = Decimal(event.sale_value or 0) - _received
        cobranca_due = event.payment_due_date or _policy_due
    cobranca_enabled = (
        cobranca_due is not None
        and cobranca_due <= _today
        and cobranca_outstanding > 0
    )
    cobranca_amount = format_brl(cobranca_outstanding, prefix=True)
    cobranca_due_line = (
        f"{cobranca_due.day:02d}/{cobranca_due.month:02d}/{cobranca_due.year}"
        if cobranca_due else ""
    )
    reembolsos_pendentes_lines = [
        f"{r.description} — {format_brl(r.amount or 0, prefix=True)}"
        for r in reembolsos if not r.is_collected
    ]

    return render_template(
        "event_detail.html",
        event=event,
        event_type=parse_event_type(event.title),
        confirm_characters=confirm_characters,
        confirm_date_line=confirm_date_line,
        confirm_location=confirm_location,
        cobranca_enabled=cobranca_enabled,
        cobranca_amount=cobranca_amount,
        cobranca_due_line=cobranca_due_line,
        talents=talents,
        logs=logs,
        contracts=contracts,
        payments=payments,
        received_total=sum(p.amount or 0 for p in payments),
        reembolsos=reembolsos,
        reembolsos_pendentes_total=reembolsos_pendentes_total,
        reembolsos_pendentes_lines=reembolsos_pendentes_lines,
        availability=availability,
        show_casting=has_role(RoleName.CASTING) or has_role(RoleName.SUPERADMIN),
        show_figurino=has_role(RoleName.FIGURINO) or has_role(RoleName.SUPERADMIN),
        show_comercial=show_comercial,
        show_vendas=show_comercial,
        show_financeiro=show_financeiro,
        show_ensaio=show_ensaio,
        is_superadmin=has_role(RoleName.SUPERADMIN),
        sellers=sellers,
        event_cost=event_cost,
        event_expenses=event_expenses,
        event_expenses_total=event_expenses_total,
        event_commission=event_commission,
        event_bv_total=event_bv_total,
        kpi_event=kpi_event,
        event_group_size=event_group_size,
        acrescimo_tipos=acrescimo_tipos_list(),
        acrescimo_tipo_bv=ACRESCIMO_TIPO_BV,
        client_relation_tipos=CLIENT_RELATION_TIPOS,
        event_rate=event_rate,
        default_commission=default_commission,
        figurino_sheets=figurino_sheets,
        suggested_sheets=suggested_sheets,
        settings=settings,
        has_makeup_role=has_makeup_role,
        event_ratings=event_ratings,
        client_feedbacks=client_feedbacks,
        groupable_events=groupable_events,
        client_required=event_requires_client(event),
    )


def strip_role_prefix(name: str) -> str:
    """Remove prefixo (TIPO) do início do nome do personagem. Ex: '(R&I) HOMEM ARANHA' → 'HOMEM ARANHA'."""
    return re.sub(r'^\s*\([^)]*\)\s*', '', name).strip()


def parse_event_type(title: str) -> str:
    """Extrai o tipo do evento do prefixo entre parênteses. Ex: '(R&I) HOMEM ARANHA + MARIO' → 'R&I'."""
    if not title:
        return ""
    m = re.match(r'^\s*\(([^)]*)\)', title)
    return m.group(1).strip() if m else ""


def parse_characters(title: str) -> list[str]:
    if not title:
        return []
    parts = [p.strip() for p in re.split(r"\s*\+\s*", title) if p.strip()]
    # Remove prefixo (TIPO) de cada personagem
    cleaned = [strip_role_prefix(p) for p in parts]
    return [p for p in cleaned if p]


_PTBR_WEEKDAYS = [
    "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
    "Sexta-feira", "Sábado", "Domingo",
]
_PTBR_MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _format_event_date_ptbr(start_at, end_at) -> str:
    """Formata a data/horário do evento em português para a mensagem de confirmação.

    Ex.: "Sexta-feira, 19 de junho · 19:00 – 20:00". Se não houver término, mostra só o
    horário de início. Retorna string vazia se ``start_at`` for ``None``.

    Args:
        start_at: Início do evento (datetime naïve, horário local).
        end_at: Término do evento (datetime) ou ``None``.

    Returns:
        Linha de data formatada em pt-BR, ou "" se não houver início.
    """
    if start_at is None:
        return ""
    weekday = _PTBR_WEEKDAYS[start_at.weekday()]
    month = _PTBR_MONTHS[start_at.month - 1]
    date_part = f"{weekday}, {start_at.day} de {month}"
    time_part = start_at.strftime("%H:%M")
    if end_at is not None:
        time_part = f"{time_part} – {end_at.strftime('%H:%M')}"
    return f"{date_part} · {time_part}"


def _dt_naive(dt):
    """Remove timezone para comparação segura."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _talent_time_conflict(talent_id: int, start, end, exclude_event_id: int | None = None):
    """Retorna o primeiro evento que sobrepõe o horário [start, end] para o talento (ou None).

    Reaproveita a regra de conflito usada na página do evento: considera apenas eventos do mês atual em
    diante (evita "fantasmas" de eventos já removidos) e detecta sobreposição real de horário.

    Args:
        talent_id: Talento a checar.
        start: Início do evento sendo criado (naïve, Brasília).
        end: Fim do evento sendo criado.
        exclude_event_id: Evento a ignorar na busca (o próprio).

    Returns:
        O ``CalendarEvent`` conflitante mais próximo, ou ``None`` se não houver conflito.
    """
    if not start:
        return None
    end = end or (start + timedelta(hours=2))
    _today = date.today()
    cutoff = datetime(_today.year, _today.month, 1)
    rows = (
        EventRole.query.join(CalendarEvent)
        .filter(
            EventRole.talent_id == talent_id,
            CalendarEvent.id != exclude_event_id,
            CalendarEvent.start_at >= cutoff,
        )
        .all()
    )
    for r in rows:
        ev = r.event
        if not ev or not ev.start_at:
            continue
        o_start = ev.start_at.replace(tzinfo=None) if ev.start_at.tzinfo else ev.start_at
        o_end = ev.end_at or (ev.start_at + timedelta(hours=2))
        o_end = o_end.replace(tzinfo=None) if o_end.tzinfo else o_end
        if max(start, o_start) < min(end, o_end):
            return ev
    return None


def _ensure_coordinator(event_id: int) -> None:
    """Garante que o evento tenha ao menos 1 role de Coordenador sem talento."""
    exists = EventRole.query.filter_by(
        event_id=event_id,
        character_name="Coordenador",
        role_type="extra",
    ).first()
    if not exists:
        db.session.add(EventRole(
            event_id=event_id,
            character_name="Coordenador",
            role_type="extra",
        ))


def _ensure_sound_technician(event_id: int) -> None:
    """Para eventos SHOW: garante role de PIX (Nivaldo) e role de presença (a designar pela equipe de ensaio).

    - 'Técnico de Som': pré-atribuído ao Nivaldo (SOUND_TECH_TALENT_ID). Casting define o cache/valor.
    - 'Técnico de Som (Presença)': vaga aberta. Equipe de ensaio designa quem vai ao evento de fato.
      É essa pessoa que aparece no exportar elenco.
    """
    pix_exists = EventRole.query.filter_by(
        event_id=event_id,
        character_name="Técnico de Som",
        role_type="extra",
    ).first()
    if not pix_exists:
        db.session.add(EventRole(
            event_id=event_id,
            character_name="Técnico de Som",
            role_type="extra",
            talent_id=SOUND_TECH_TALENT_ID,
        ))

    presence_exists = EventRole.query.filter_by(
        event_id=event_id,
        character_name=PRESENCE_CHARACTER,
        role_type="extra",
    ).first()
    if not presence_exists:
        db.session.add(EventRole(
            event_id=event_id,
            character_name=PRESENCE_CHARACTER,
            role_type="extra",
        ))


def _detect_changes(event: CalendarEvent, new_start, new_end, new_location) -> list[str]:
    """Retorna lista de strings descrevendo o que mudou (data/hora/local)."""
    changes = []
    tz_sp = ZoneInfo("America/Sao_Paulo")

    old_start = _dt_naive(event.start_at)
    chk_start = _dt_naive(new_start)
    if old_start != chk_start and old_start is not None:
        old_str = event.start_at.strftime("%d/%m/%Y %H:%M") if event.start_at else "—"
        new_str = new_start.strftime("%d/%m/%Y %H:%M") if new_start else "—"
        changes.append(f"Data/hora: {old_str} → {new_str}")

    old_end = _dt_naive(event.end_at)
    chk_end = _dt_naive(new_end)
    if old_end != chk_end and old_end is not None and chk_start == old_start:
        # só reporta fim se o início não mudou (evita duplicar)
        old_str = event.end_at.strftime("%H:%M") if event.end_at else "—"
        new_str = new_end.strftime("%H:%M") if new_end else "—"
        changes.append(f"Horário de término: {old_str} → {new_str}")

    old_loc = (event.location or "").strip()
    new_loc = (new_location or "").strip()
    if old_loc != new_loc and old_loc:
        changes.append(f"Local: {old_loc or '—'} → {new_loc or '—'}")

    return changes


# _notify_accepted_roles / _notify_ensaio_team → movidos para app/calendar/event_ops.py (feature 149),
# reimportados com alias no topo deste módulo (dependência unidirecional routes → event_ops).


def _sinalizar_divergencia_virtual(event, item: dict) -> None:
    """Registra que um evento de venda virtual foi mexido direto no Google (FR-029b).

    Só sinaliza — nada é propagado para o pedido. Um pedido pago não pode ser desfeito porque
    alguém arrastou o evento no calendário; o que a equipe precisa é **saber** que aconteceu.

    Idempotente na prática: só registra quando há divergência real de título ou horário, para a
    sincronização (que roda a cada 10 min) não encher os logs.
    """
    titulo_google = item.get("summary") or ""
    inicio_google, _ = parse_event_datetime(item)

    mudou_titulo = titulo_google and titulo_google != event.title
    mudou_horario = inicio_google is not None and inicio_google != event.start_at
    if not (mudou_titulo or mudou_horario):
        return

    detalhes = []
    if mudou_titulo:
        detalhes.append(f"título no Google: {titulo_google!r} (sistema: {event.title!r})")
    if mudou_horario:
        detalhes.append(f"horário no Google: {inicio_google} (sistema: {event.start_at})")

    _log_sync(
        "virtual_divergente", event,
        details="Evento de venda virtual alterado no Google — mudança NÃO aplicada. "
                + "; ".join(detalhes),
    )


def _is_virtual_event(event) -> bool:
    """True se o evento nasceu de uma venda da Loja de Interações Virtuais (feature 205).

    Esses eventos são criados pela plataforma **e** vivem no Google (é de lá que sai a sala do
    Meet), então a sincronização os encontra e trataria como qualquer outro. Não pode: a venda é a
    fonte de verdade deles. Deixar a sincronização reescrevê-los corromperia horário, título ou
    vínculo de um evento **já pago** (FR-029a).
    """
    from app.constants import EVENT_TYPE_VIRTUAL

    return event is not None and event.event_type == EVENT_TYPE_VIRTUAL


def sync_events(items: list[dict]) -> None:
    for item in items:
        google_id = item.get("id")
        if not google_id:
            continue

        # Evento de venda virtual: a sincronização não encosta nele em nenhum caminho —
        # nem para criar, nem para atualizar (FR-029a). Edição feita direto no Google é
        # sinalizada, nunca propagada para o pedido (FR-029b).
        existente = CalendarEvent.query.filter_by(google_event_id=google_id).first()
        if _is_virtual_event(existente):
            _sinalizar_divergencia_virtual(existente, item)
            continue

        title = item.get("summary") or "Sem título"
        description = item.get("description")
        location = item.get("location")
        start_at, end_at = parse_event_datetime(item)

        event_type = parse_event_type(title)
        if title.startswith("🟧 ENSAIO"):
            event_type = "ENSAIO"

        # needs_rehearsal: automático para SHOW, ou via tag na descrição
        desc_lower = (description or "").lower()
        is_show = event_type == "SHOW"
        gc_needs_rehearsal = is_show or "#ensaio" in desc_lower or "precisa de ensaio" in desc_lower

        event = CalendarEvent.query.filter_by(google_event_id=google_id).first()
        if not event:
            event = CalendarEvent(
                google_event_id=google_id,
                google_html_link=item.get("htmlLink"),
                title=title,
                description=description,
                location=location,
                start_at=start_at,
                end_at=end_at,
                event_type=event_type,
                needs_rehearsal=gc_needs_rehearsal,
            )
            db.session.add(event)
            db.session.flush()
            db.session.add(
                EventLog(
                    event_id=event.id,
                    actor_name="Sistema",
                    actor_role="Sistema",
                    message="Evento criado",
                    created_at=datetime.now(tz=ZoneInfo("America/Sao_Paulo")),
                )
            )
            _log_sync("google_created", event)
            if not title.startswith("🟧 ENSAIO"):
                _ensure_coordinator(event.id)
                if event_type == "SHOW":
                    _ensure_sound_technician(event.id)
            if gc_needs_rehearsal:
                _notify_ensaio_team(event)
            # Determina se é fora de SP via CEP (ViaCEP) ou string
            event.is_outside_sp = _lookup_sp_status(location)
            # Auto-estima distância via Google Maps se fora de SP
            if event.is_outside_sp:
                settings = SiteSetting.query.get(1)
                _fetch_travel_data(event, settings)
        else:
            # Detecta mudanças relevantes (data, hora, local) antes de sobrescrever
            _changes = _detect_changes(event, start_at, end_at, location)
            old_needs_rehearsal = event.needs_rehearsal
            old_location = event.location

            event.title = title
            event.description = description
            event.location = location
            event.start_at = start_at
            event.end_at = end_at
            event.event_type = event_type
            event.google_html_link = item.get("htmlLink") or event.google_html_link
            # parent_event_id NÃO é sobrescrito — gerenciado pela plataforma
            if gc_needs_rehearsal and not old_needs_rehearsal:
                event.needs_rehearsal = True
                _notify_ensaio_team(event)

            # Reavalia se é fora de SP quando o endereço mudou
            location_changed = (location or "").strip() != (old_location or "").strip()
            if location_changed or event.is_outside_sp is None:
                event.is_outside_sp = _lookup_sp_status(location)

            if event.is_outside_sp and (location_changed or not event.travel_distance_km):
                settings = SiteSetting.query.get(1)
                _fetch_travel_data(event, settings)
            elif not event.is_outside_sp:
                event.travel_distance_km = None

            # Notifica talentos confirmados sobre mudanças
            if _changes:
                _notify_accepted_roles(event, _changes)
                _log_sync("google_updated", event, details="; ".join(_changes))

            # Garante técnico de som para eventos SHOW existentes (idempotente)
            if event_type == "SHOW":
                _ensure_sound_technician(event.id)

        # Eventos criados pela plataforma: atualiza metadados mas preserva roles
        if event.source == "platform":
            db.session.commit()
            continue

        if title.startswith("🟧 ENSAIO"):
            for role in list(event.roles):
                db.session.delete(role)
            db.session.commit()
            continue

        characters = parse_characters(title)
        # Only sync character roles — never touch extra roles (Coordenador, Maquiador, etc.)
        existing = {r.character_name: r for r in event.roles if r.role_type != "extra"}

        # Mapa normalizado: nome sem prefixo → (nome_atual, role)
        # Permite renomear roles antigos que ainda têm o prefixo, preservando casting/figurino
        existing_norm: dict[str, tuple[str, object]] = {}
        for name, role in existing.items():
            norm = strip_role_prefix(name)
            existing_norm[norm] = (name, role)

        # Apaga roles que não existem mais (mesmo após normalização)
        for name, role in list(existing.items()):
            if strip_role_prefix(name) not in characters:
                if role.talent_id and role.talent:
                    send_removal_email(role.talent, event, role.character_name)
                db.session.delete(role)

        # Cria novos ou renomeia roles com prefixo antigo
        for char in characters:
            if char in existing:
                # já existe com o nome correto, nada a fazer
                pass
            elif char in existing_norm:
                # existe mas com prefixo antigo → renomeia preservando assignment
                _, role = existing_norm[char]
                role.character_name = char
            else:
                db.session.add(EventRole(event_id=event.id, character_name=char))

    db.session.commit()
    _mark_talents_worked()


def _mark_talents_worked() -> None:
    """Liga "já trabalhou com a Manto" para talentos que realizaram um evento (feature 115).

    "Realizou" = teve talento atribuído a um cargo, em evento que não é Ensaio, com convite
    não recusado, e cuja data já passou. Roda a cada sincronização da agenda (mesma função
    usada pelo botão "Sincronizar agora", pela thread automática e pelo sync de um evento).
    Só LIGA o campo — nunca desliga uma marcação existente (FR-002).
    """
    now = datetime.utcnow()
    worked_talent_ids = (
        db.session.query(EventRole.talent_id)
        .join(CalendarEvent, EventRole.event_id == CalendarEvent.id)
        .filter(
            EventRole.talent_id.isnot(None),
            db.or_(EventRole.invite_status.is_(None), EventRole.invite_status != "rejected"),
            CalendarEvent.event_type != "ENSAIO",
            db.func.coalesce(CalendarEvent.end_at, CalendarEvent.start_at) < now,
        )
        .distinct()
    )
    Talent.query.filter(
        Talent.id.in_(worked_talent_ids),
        Talent.worked_before.isnot(True),
    ).update({"worked_before": True}, synchronize_session=False)
    db.session.commit()


# ─── LOGÍSTICA / ESTIMATIVA DE VIAGEM ────────────────────────────────────────

_SP_CITY_TERMS = ("sao paulo", "são paulo")

_CEP_RE = re.compile(r'\b(\d{5})-?(\d{3})\b')


def _lookup_sp_status(location: str) -> bool | None:
    """Determina se o endereço é fora da cidade de São Paulo.

    Tenta lookup via ViaCEP se encontrar um CEP no endereço.
    Fallback: checagem por string.
    Retorna True=fora de SP | False=dentro de SP | None=desconhecido.
    """
    if not location:
        return None

    m = _CEP_RE.search(location)
    if m:
        cep = m.group(1) + m.group(2)
        import json as _json
        try:
            url = f"https://viacep.com.br/ws/{cep}/json/"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = _json.loads(resp.read())
            if "erro" not in data:
                city = data.get("localidade", "").strip().lower()
                uf   = data.get("uf", "").strip().upper()
                is_sp = city in ("são paulo", "sao paulo") and uf == "SP"
                return not is_sp
        except Exception as exc:  # noqa: BLE001 — resposta externa inesperada; cai no fallback de string
            current_app.logger.warning("[transporte] geocode fora de SP falhou, usando fallback: %s", exc)

    # Fallback: se "São Paulo" está explicitamente no endereço, é dentro da cidade
    loc_lower = location.lower()
    if any(term in loc_lower for term in _SP_CITY_TERMS):
        return False
    # Sem CEP e sem "São Paulo" no endereço: desconhecido
    return None


def _is_outside_sp(location: str) -> bool:
    """Retorna True se o endereço não pertence à cidade de São Paulo (checagem rápida por string).

    Usado internamente quando só precisamos de bool (ex: decidir se chama Google Maps).
    Para persistir em banco, use _lookup_sp_status.
    """
    if not location:
        return False
    loc = location.lower()
    return not any(term in loc for term in _SP_CITY_TERMS)


def _fetch_travel_data(event: CalendarEvent, settings) -> dict:
    """Chama o Google Maps Distance Matrix e salva travel_time_minutes + travel_distance_km no evento.

    Retorna o dict com os dados ou {} em caso de falha/sem API key.
    """
    import urllib.request
    import json as _json

    if not event.location:
        return {}

    origin = (settings.manto_address if settings and settings.manto_address
              else "R. Olga Camelini, 147 - São João Climaco, São Paulo - SP")
    import os
    api_key = (settings.google_maps_api_key if settings else None) or os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {}

    url = (
        "https://maps.googleapis.com/maps/api/distancematrix/json"
        f"?origins={urllib.parse.quote(origin)}"
        f"&destinations={urllib.parse.quote(event.location)}"
        f"&language=pt-BR&key={api_key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = _json.loads(resp.read())
        element = data["rows"][0]["elements"][0]
        if element["status"] != "OK":
            return {}

        duration_min = element["duration"]["value"] // 60
        distance_km  = element["distance"]["value"] / 1000.0

        event.travel_time_minutes = duration_min
        event.travel_distance_km  = distance_km
        return {
            "duration_text":  element["duration"]["text"],
            "distance_text":  element["distance"]["text"],
            "duration_minutes": duration_min,
            "distance_km":    distance_km,
        }
    except Exception as exc:  # noqa: BLE001 — cálculo de rota é opcional; segue sem estimativa
        current_app.logger.warning("[transporte] cálculo de rota falhou: %s", exc)
        return {}


def travel_estimate(event_id: int):
    """Retorna estimativa de tempo de viagem via Google Maps Distance Matrix API."""
    from flask import jsonify

    event = CalendarEvent.query.get_or_404(event_id)
    settings = SiteSetting.query.get(1)

    if not event.location:
        return {"error": "Evento sem endereço de destino."}, 400

    origin = (settings.manto_address if settings and settings.manto_address
              else "R. Olga Camelini, 147 - São João Climaco, São Paulo - SP")
    import os
    api_key = (settings.google_maps_api_key if settings else None) or os.getenv("GOOGLE_MAPS_API_KEY")

    if not api_key:
        maps_url = (
            "https://www.google.com/maps/dir/"
            + urllib.parse.quote(origin) + "/"
            + urllib.parse.quote(event.location)
        )
        return {"maps_url": maps_url, "no_key": True}

    result = _fetch_travel_data(event, settings)
    if not result:
        return {"error": "Endereço não encontrado pelo Google Maps."}, 400

    db.session.commit()

    suggested = None
    margin = (settings.departure_margin_minutes if settings and settings.departure_margin_minutes is not None else 60)
    if event.start_at:
        depart_dt = event.start_at - timedelta(minutes=margin + result["duration_minutes"])
        suggested = depart_dt.strftime("%H:%M")

    maps_url = (
        "https://www.google.com/maps/dir/"
        + urllib.parse.quote(origin) + "/"
        + urllib.parse.quote(event.location)
    )
    return {
        "duration_text":    result["duration_text"],
        "distance_text":    result["distance_text"],
        "duration_minutes": result["duration_minutes"],
        "suggested_departure": suggested,
        "maps_url": maps_url,
    }


# ─── ENSAIOS ──────────────────────────────────────────────────────────────────

@calendar_bp.route("/events/<int:event_id>/create-ensaio", methods=["POST"])
@login_required
def create_ensaio(event_id: int):
    event = CalendarEvent.query.get_or_404(event_id)

    if not any(r.name.upper() in _CAN_ENSAIO for r in current_user.roles):
        abort(403)

    date_str      = request.form.get("ensaio_date", "").strip()
    start_str     = request.form.get("ensaio_start", "").strip()
    end_str       = request.form.get("ensaio_end", "").strip()
    desc          = request.form.get("ensaio_desc", "").strip()
    location_type = request.form.get("ensaio_location_type", "manto")
    custom_loc    = request.form.get("ensaio_location", "").strip()
    redirect_to   = request.form.get("redirect_to", "event")

    # Destino pós-ação (sucesso ou erro): home (quando veio da home) ou página do show.
    back = url_for("home") if redirect_to == "home" else url_for("calendar.event_detail", event_id=event_id)

    if location_type == "outro" and custom_loc:
        ensaio_loc = custom_loc
    else:
        _s = SiteSetting.query.get(1)
        ensaio_loc = (_s.manto_address or "") if _s else ""

    errors = []
    d = None
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        errors.append("Data inválida.")

    st = et = None
    if d:
        try:
            st, et = _build_start_end(d, start_str, end_str)
        except ValueError:
            errors.append("Horário inválido (use HH:MM).")

    if st and et and et == st:
        errors.append("Horário de fim deve ser diferente do início.")

    if errors:
        flash(" ".join(errors), "error")
        return redirect(back)

    title = f"🟧 ENSAIO — {event.title}"
    try:
        created = insert_event(CALENDAR_ID, title, st, et, description=desc, location=ensaio_loc)
        ensaio_ev = CalendarEvent(
            google_event_id=created["id"],
            title=title,
            description=desc or None,
            location=ensaio_loc or None,
            start_at=st,
            end_at=et,
            event_type="ENSAIO",
            parent_event_id=event.id,
        )
        db.session.add(ensaio_ev)
        db.session.commit()
        flash(f'Ensaio criado com sucesso para {d.strftime("%d/%m/%Y")}!', "success")
    except RuntimeError as exc:
        flash(str(exc), "error")

    return redirect(back)


@calendar_bp.route("/events/<int:ensaio_id>/edit-ensaio", methods=["POST"])
@login_required
def edit_ensaio(ensaio_id: int):
    """Edita data/hora/descrição de um evento de ensaio já criado."""
    ensaio = CalendarEvent.query.get_or_404(ensaio_id)

    if not any(r.name.upper() in _CAN_ENSAIO for r in current_user.roles):
        abort(403)

    if ensaio.event_type != "ENSAIO":
        abort(400)

    date_str    = request.form.get("ensaio_date", "").strip()
    start_str   = request.form.get("ensaio_start", "").strip()
    end_str     = request.form.get("ensaio_end", "").strip()
    desc        = request.form.get("ensaio_desc", "").strip()
    new_loc     = request.form.get("ensaio_location", "").strip()
    redirect_to = request.form.get("redirect_to", "home")

    errors = []
    d = None
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        errors.append("Data inválida.")

    st = et = None
    if d:
        try:
            st, et = _build_start_end(d, start_str, end_str)
        except ValueError:
            errors.append("Horário inválido (use HH:MM).")

    if st and et and et == st:
        errors.append("Horário de fim deve ser diferente do início.")

    if errors:
        flash(" ".join(errors), "error")
    else:
        ensaio.start_at    = st
        ensaio.end_at      = et
        ensaio.description = desc or None
        if new_loc:
            ensaio.location = new_loc
        db.session.commit()

        if ensaio.google_event_id:
            try:
                update_event(
                    CALENDAR_ID,
                    ensaio.google_event_id,
                    ensaio.title,
                    st,
                    et,
                    description=desc,
                    location=ensaio.location or "",
                )
            except RuntimeError as exc:
                flash(f"Salvo no banco, mas erro ao atualizar Google Calendar: {exc}", "warning")

        flash("Ensaio atualizado com sucesso!", "success")

    if redirect_to == "ensaio":
        return redirect(url_for("calendar.event_detail", event_id=ensaio.id))
    if redirect_to == "event" and ensaio.parent_event_id:
        return redirect(url_for("calendar.event_detail", event_id=ensaio.parent_event_id))
    return redirect(url_for("home"))


@calendar_bp.route("/events/<int:ensaio_id>/delete-ensaio", methods=["POST"])
@login_required
def delete_ensaio(ensaio_id: int):
    """Cancela (exclui) um ensaio sem afetar o evento pai."""
    ensaio = CalendarEvent.query.get_or_404(ensaio_id)

    if ensaio.event_type != "ENSAIO":
        abort(400)

    if not any(r.name.upper() in _CAN_ENSAIO for r in current_user.roles):
        abort(403)

    parent_id = ensaio.parent_event_id

    if ensaio.google_event_id:
        try:
            delete_event(CALENDAR_ID, ensaio.google_event_id)
        except Exception as exc:  # noqa: BLE001 — qualquer falha do Google não pode travar a exclusão local
            current_app.logger.exception(
                "Falha ao remover ensaio %s do Google Agenda", ensaio.id)
            flash(f"Salvo no banco, mas erro ao remover do Google Calendar: {exc}", "warning")

    # Feature 122: EventLog/EventContract/EventPayment/EventRating não têm cascade
    # automático — sem esta limpeza, o delete abaixo falha por violação de chave
    # estrangeira sempre que o ensaio tiver histórico de ações registrado.
    _clear_event_side_tables(ensaio.id)
    db.session.delete(ensaio)
    db.session.commit()

    flash("Ensaio cancelado com sucesso.", "success")
    if parent_id:
        return redirect(url_for("calendar.event_detail", event_id=parent_id))
    return redirect(url_for("home"))


@calendar_bp.route("/events/<int:ensaio_id>/link-parent", methods=["POST"])
@login_required
def link_ensaio_parent(ensaio_id: int):
    """Vincula um ensaio existente a um evento pai (show) — feature 063."""
    ensaio = CalendarEvent.query.get_or_404(ensaio_id)

    if ensaio.event_type != "ENSAIO":
        abort(400)
    if not any(r.name.upper() in _CAN_ENSAIO for r in current_user.roles):
        abort(403)

    raw = request.form.get("parent_event_id", "").strip()
    if not raw.isdigit():
        flash("Selecione um show para vincular o ensaio.", "error")
        return redirect(url_for("calendar.event_detail", event_id=ensaio.id))

    parent = CalendarEvent.query.get(int(raw))
    if parent is None or parent.event_type == "ENSAIO" or parent.id == ensaio.id:
        flash("Show inválido para vínculo.", "error")
        return redirect(url_for("calendar.event_detail", event_id=ensaio.id))

    ensaio.parent_event_id = parent.id
    db.session.add(EventLog(
        event_id=ensaio.id,
        actor_name=current_user.name,
        actor_role="Ensaio",
        message=f"Vinculou o ensaio ao show: {parent.title}",
    ))
    db.session.commit()
    flash(f'Ensaio vinculado a "{parent.title}".', "success")
    return redirect(url_for("calendar.event_detail", event_id=ensaio.id))


# ─── CRIAR EVENTO (COMERCIAL) ─────────────────────────────────────────────────

def _compute_performer_caches(snapshot: dict) -> list[dict]:
    """Retorna lista de {label, cache_1h, cache_2h, cache_4h, needs_makeup, is_singer}
    para cada performer + coordenadores + técnico + maquiador do snapshot.

    Inclui o acréscimo de "show customizado" (+R$50/artista) nos cachês de personagem quando
    aplicável — antes só entrava no total do orçamento, não no cachê individual (feature 172).
    """
    from app.orcamento.pricing import (
        get_ator_prices, get_cantor_prices, get_especial_prices,
        get_coordenador_prices, get_tecnico_prices, calcular_maquiador,
        compute_show_pricing,
    )
    from app.orcamento import settings as _orc_cfg

    performers     = snapshot.get("performers", [])
    coordenador_qty = int(snapshot.get("coordenador_qty", 1) or 1)
    has_show, sosia_custom_add_per_artist = compute_show_pricing(
        performers, snapshot.get("show_sosia_tipo", "predefinido")
    )

    # Adicional noturno (+R$50 por performer/coord se horário >= 19h)
    event_time_str = (snapshot.get("event_time") or "").strip()
    noturno_add = 0
    try:
        if event_time_str and int(event_time_str.split(":")[0]) >= 19:
            noturno_add = 50
    except (ValueError, IndexError):
        pass

    # Adicional fora SP (parcela afsp = km×2 ÷ divisor, por pessoa)
    transport_add: float = 0.0
    if snapshot.get("fora_sp"):
        km_ida = float(snapshot.get("km_ida") or 0)
        if km_ida > 0:
            afsp_divisor = float(_orc_cfg.load().get("transporte", {}).get("afsp_divisor", 3.0))
            transport_add = round(km_ida * 2 / afsp_divisor, 2)

    result = []
    num_makes_regular  = 0
    num_makes_especial = 0

    for p in performers:
        ptype      = p.get("type", "")
        show       = bool(p.get("show", False))
        makeup     = bool(p.get("makeup", False))
        makeup_tipo = p.get("makeup_tipo", "comum")
        cantor_flag = bool(p.get("cantor", False))
        nome       = p.get("nome", "").strip()
        is_singer  = False

        if ptype == "ator":
            subtipo = p.get("subtipo", "cara_limpa")
            if subtipo == "cantor":
                prices = get_cantor_prices(show, makeup)
                label  = nome or "Cantor"
                is_singer = True
            else:
                prices = get_ator_prices(subtipo, show, makeup)
                label  = nome or ("Boneco" if subtipo == "boneco" else "Ator")
        elif ptype == "cantor":
            prices = get_cantor_prices(show=True, makeup=makeup)
            label  = nome or "Cantor"
            is_singer = True
        elif ptype == "especial":
            personagem = p.get("personagem", "")
            prices = get_especial_prices(personagem, show, cantor_flag)
            label  = nome or personagem
            if cantor_flag:
                is_singer = True
        else:
            prices = (0, 0, 0, 0)
            label  = nome or "Profissional"

        if makeup:
            if makeup_tipo == "especial":
                num_makes_especial += 1
            else:
                num_makes_regular += 1

        result.append({
            "label":       label,
            "cache_1h":    round(int(prices[0]) + noturno_add + transport_add + sosia_custom_add_per_artist),
            "cache_2h":    round(int(prices[1]) + noturno_add + transport_add + sosia_custom_add_per_artist),
            "cache_3h":    round(int(prices[2]) + noturno_add + transport_add + sosia_custom_add_per_artist),
            "cache_4h":    round(int(prices[3]) + noturno_add + transport_add + sosia_custom_add_per_artist),
            "needs_makeup": makeup,
            "is_singer":    is_singer,
            "role_type":   "character",
        })

    # Coordenadores
    coord_prices = get_coordenador_prices(has_show, coordenador_qty)
    per_coord    = [coord_prices[i] // max(coordenador_qty, 1) for i in range(4)]
    for _ in range(coordenador_qty):
        result.append({
            "label":       "Coordenador",
            "cache_1h":    round(int(per_coord[0]) + noturno_add + transport_add),
            "cache_2h":    round(int(per_coord[1]) + noturno_add + transport_add),
            "cache_3h":    round(int(per_coord[2]) + noturno_add + transport_add),
            "cache_4h":    round(int(per_coord[3]) + noturno_add + transport_add),
            "needs_makeup": False,
            "is_singer":    False,
            "role_type":   "extra",
        })

    # Técnico de som (se houver show) — apenas regra do >500km afeta o técnico, não os adicionais por pessoa
    if has_show:
        tp = get_tecnico_prices()
        result.append({
            "label":       "Técnico de Som",
            "cache_1h":    int(tp[0]),
            "cache_2h":    int(tp[1]),
            "cache_3h":    int(tp[2]),
            "cache_4h":    int(tp[3]),
            "needs_makeup": False,
            "is_singer":    False,
            "role_type":   "extra",
        })

    # Maquiador (se necessário)
    if num_makes_regular > 0 or num_makes_especial > 0:
        mq_cost = calcular_maquiador(num_makes_regular, num_makes_especial)
        result.append({
            "label":       "Maquiador",
            "cache_1h":    int(mq_cost),
            "cache_2h":    int(mq_cost),
            "cache_3h":    int(mq_cost),
            "cache_4h":    int(mq_cost),
            "needs_makeup": False,
            "is_singer":    False,
            "role_type":   "extra",
        })

    return result


def _save_file_upload(
    file,
    upload_dir: str,
    subpath: str,
    *,
    allowed: frozenset[str] = ALLOWED_DOCUMENT_EXTENSIONS,
) -> str | None:
    """Salva um arquivo e retorna o path relativo a /uploads/, ou None.

    Args:
        file: o ``FileStorage`` recebido (ou None).
        upload_dir: diretório absoluto de destino.
        subpath: segmento do caminho público (``/uploads/<subpath>/<nome>``).
        allowed: allowlist de extensões. O padrão (documento) cobre contrato e comprovante;
            observação de evento passa `ALLOWED_IMAGE_EXTENSIONS`, porque o endpoint que a
            recebe não tem gate de papel — qualquer usuário logado sobe arquivo por ele.

    Returns:
        O caminho público, ou None se não houve arquivo, se ele excede 20 MB ou se a extensão
        está fora da allowlist (o arquivo é servido no mesmo origin das SPAs: extensão livre
        aqui é XSS armazenado).
    """
    if not file or not file.filename:
        return None
    if not is_allowed_extension(file.filename, allowed):
        return None
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > 20 * 1024 * 1024:
        return None
    name = secure_filename(file.filename)
    file.save(os.path.join(upload_dir, name))
    return f"/uploads/{subpath}/{name}"


# ─── CRIAÇÃO DE EVENTO — núcleo compartilhado (feature 152) ──────────────────────
# Funções de módulo puras (sem `request`/`flash`/`current_user`), reusadas pelo wrapper Jinja
# (`create_event`, abaixo) e pelos endpoints JSON (`app/api/agenda_write.py`,
# `app/api/agenda_read.py`). Ficam em `routes.py` (não em módulo `ops` dedicado) porque reusam
# helpers já existentes aqui (`_build_start_end`, `_ensure_coordinator`,
# `_ensure_sound_technician`, `_lookup_sp_status`, `_fetch_travel_data`, `_talent_time_conflict`,
# `_compute_performer_caches`, `_parse_client_pairs`, `_primary_client_id`) que são usados por
# outras rotas — mover para um módulo novo exigiria tocar esses call sites fora de escopo (ver
# Complexity Tracking em specs/152-criar-evento-react/plan.md). Upload de arquivo (nota fiscal,
# contrato, comprovantes de pagamento, comprovante de reembolso, imagem de observação) fica FORA
# do núcleo — só o wrapper Jinja lida com isso.


def _build_event_create_options() -> dict:
    """Opções do formulário de criação de evento: fichas, vendedores, talentos, tipos de relação.

    Fonte única reusada pelo GET do wrapper Jinja e por `GET /api/events/new/options` (152).
    """
    figurino_sheets = FigurinoSheet.query.order_by(FigurinoSheet.character_name.asc()).all()
    sellers = (
        User.query.join(User.roles)
        .filter(Role.name == RoleName.COMERCIAL)
        .order_by(User.name.asc())
        .all()
    )
    # `photo_face_path` (feature 195): o avatar do talento aparece na busca de pré-escala e de
    # coordenador do formulário de evento. O Jinja legado simplesmente ignora a chave extra.
    assignable_talents = [
        {
            "id": t.id,
            "name": t.artistic_name or t.full_name,
            "photo_face_path": t.photo_face_path,
        }
        for t in Talent.query.filter_by(status="active").order_by(Talent.full_name.asc()).all()
    ]
    return {
        "figurino_sheets": [
            {"id": s.id, "character_name": s.character_name, "photo_url": s.photo_url}
            for s in figurino_sheets
        ],
        "sellers": [{"id": u.id, "name": u.name} for u in sellers],
        "assignable_talents": assignable_talents,
        "client_relation_tipos": CLIENT_RELATION_TIPOS,
    }


def _build_orcamento_prefill(orcamento_id: int | None) -> dict:
    """Pré-preenchimento a partir de um orçamento salvo (`OrcamentoHistory`), feature 152.

    Mesmo cálculo do GET de `create_event`: transporte fora-SP, acréscimo legado (snapshots
    antigos) e cachês por personagem para as 4 durações. `{}` se `orcamento_id` for `None` ou
    não existir — nunca levanta erro (paridade com o `if entry:` silencioso de hoje).
    """
    if orcamento_id is None:
        return {}
    entry = OrcamentoHistory.query.get(orcamento_id)
    if entry is None:
        return {}

    snap = json.loads(entry.form_snapshot or "{}")
    transport_val = 0
    if snap.get("fora_sp"):
        from app.orcamento.transport import calcular_carro, calcular_van

        km = float(snap.get("km_ida", 0) or 0)
        if snap.get("transporte_tipo", "van") == "van":
            tb = calcular_van(
                int(snap.get("num_colaboradores", 1) or 1),
                km,
                bool(snap.get("carretinha", False)),
                entry.has_show,
            )
        else:
            tb = calcular_carro(
                int(snap.get("num_carros", 1) or 1),
                int(snap.get("num_colaboradores", 1) or 1),
                km,
                entry.has_show,
            )
        transport_val = int(tb["total"])

    acrescimo = float(snap.get("acrescimo_valor", 0) or 0)
    acrescimo_val = int(acrescimo) if snap.get("acrescimo_tipo", "valor") == "valor" else 0

    caches = _compute_performer_caches(snap)

    duracao_custom = int(snap.get("duracao_custom", 0) or 0)
    total_4h_val = float(entry.total_4h or 0)
    total_custom = (
        round(total_4h_val / 4 * duracao_custom, 2)
        if duracao_custom > 0 and duracao_custom not in (1, 2, 3, 4)
        else None
    )

    return {
        "orcamento_id": entry.id,
        "date": snap.get("event_date", ""),
        "start_time": snap.get("event_time", ""),
        "location": entry.event_location or "",
        "client_name": entry.client_name or "",
        "total_1h": float(entry.total_1h or 0),
        "total_2h": float(entry.total_2h or 0),
        "total_3h": float(entry.total_3h or 0),
        "total_4h": float(entry.total_4h or 0),
        "total_custom": total_custom,
        "duracao_custom": duracao_custom if total_custom else None,
        "has_show": entry.has_show,
        "transport_value": transport_val,
        "acrescimo_value": acrescimo_val,
        "acrescimos": snap.get("acrescimos", []),
        "with_invoice": bool(snap.get("nota_fiscal", False)),
        "caches": caches,
    }


def _validate_event_core(data: dict) -> dict[str, str]:
    """Valida os campos essenciais/financeiros da criação de evento (feature 152).

    Espera valores já normalizados pelo adaptador (money/ids já convertidos para número —
    Princípio VII; datas/horários continuam string ISO/"HH:MM" cru, mesmo formato nos dois
    adaptadores). Devolve um mapa campo→mensagem (vazio = válido); o wrapper Jinja converte os
    valores em lista para manter o flash de hoje.
    """
    errors: dict[str, str] = {}
    title = (data.get("title") or "").strip()
    if not title:
        errors["title"] = "Título obrigatório."

    date_str = (data.get("date_str") or "").strip()
    start_str = (data.get("start_str") or "").strip()
    end_str = (data.get("end_str") or "").strip()
    d = st = et = None
    if date_str:
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            errors["event_date"] = "Data inválida."
    else:
        errors["event_date"] = "Data obrigatória."

    if not start_str or not end_str:
        errors["event_time"] = "Informe o horário de início e de fim."
    elif d:
        try:
            st, et = _build_start_end(d, start_str, end_str)
        except ValueError:
            errors["event_time"] = "Horário inválido (use HH:MM)."

    if st and et and et == st:
        errors["event_time"] = "Horário de fim deve ser diferente do início."

    if not data.get("is_cortesia_permuta"):
        if (data.get("sale_value_gross") or 0) <= 0:
            errors["sale_value_gross"] = "Informe o valor antes do desconto."
        if (data.get("sale_value") or 0) <= 0:
            errors["sale_value"] = "Informe o valor de venda."

    if not data.get("seller_id"):
        errors["seller_id"] = "Selecione o vendedor responsável."

    installments = data.get("payment_installments")
    if data.get("payment_method") == "pix_parcelado" and not (
        isinstance(installments, int) and 2 <= installments <= 12
    ):
        errors["payment_installments"] = "Informe o número de parcelas (2 a 12)."

    return errors


def _create_event_row(data: dict, *, google_event_id: str, gc_title: str) -> CalendarEvent:
    """Grava o `CalendarEvent` essencial + financeiro + acréscimos tipados + nota fiscal (sem
    arquivo) + detecção fora-de-SP (feature 152). Chamado depois que `insert_event` (Google) já
    rodou com sucesso — recebe o id/título já prontos, não sabe nada de Google.
    """
    d = date.fromisoformat(data["date_str"])
    st, et = _build_start_end(d, data["start_str"], data["end_str"])
    is_cortesia = bool(data.get("is_cortesia_permuta"))

    event = CalendarEvent(
        google_event_id=google_event_id,
        title=gc_title,
        description=(data.get("description") or "").strip() or None,
        location=(data.get("location") or "").strip() or None,
        start_at=st,
        end_at=et,
        event_type=data.get("event_type") or None,
        needs_rehearsal=bool(data.get("needs_rehearsal")),
        source="platform",
        is_cortesia_permuta=is_cortesia,
        sale_value=0 if is_cortesia else data.get("sale_value"),
        sale_value_gross=None if is_cortesia else data.get("sale_value_gross"),
        sale_date=data.get("sale_date"),
        transport_value=data.get("transport_value"),
        acrescimo_value=data.get("acrescimo_value"),
        with_invoice=bool(data.get("with_invoice")),
        invoice_file=data.get("invoice_filename"),
        seller_id=data.get("seller_id"),
        payment_method=data.get("payment_method"),
        payment_installments=data.get("payment_installments"),
        payment_due_date=data.get("payment_due_date"),
        orcamento_history_id=data.get("orcamento_history_id"),
    )
    db.session.add(event)
    db.session.flush()

    acr_list = data.get("acrescimos") or []
    if acr_list:
        sale_ev = Decimal(event.sale_value or 0)
        for a in acr_list:
            tipo = (a.get("tipo") or "").strip()
            val = a.get("value")
            if not tipo or not val:
                continue
            is_pct = bool(a.get("is_percent"))
            val_d = Decimal(str(val))
            amount = (
                (sale_ev * val_d / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if is_pct else val_d
            )
            db.session.add(EventAcrescimo(
                event_id=event.id,
                tipo=tipo,
                descricao=(a.get("descricao") or "").strip() or None,
                is_percent=is_pct,
                value=val_d,
                amount_brl=amount,
                is_bv=bool(a.get("is_bv")) or tipo == ACRESCIMO_TIPO_BV,
            ))

    if event.with_invoice:
        invoice_filename = data.get("invoice_filename")
        db.session.add(EventInvoice(
            event_id=event.id,
            amount=event.sale_value,
            issue_date=None,
            file=(f"/uploads/invoices/{invoice_filename}" if invoice_filename else None),
            status="emitida" if invoice_filename else "a_emitir",
            issued_at=datetime.now(tz=TZ) if invoice_filename else None,
        ))

    event.is_outside_sp = _lookup_sp_status(event.location or "")
    if event.is_outside_sp:
        settings = SiteSetting.query.get(1)
        _fetch_travel_data(event, settings)

    return event


def _create_roles_from_input(
    event: CalendarEvent,
    characters: list[dict],
    *,
    orc_caches: list[dict],
    dur_idx: int,
    figurino_by_name: dict[str, int],
    valid_talent_ids: set[int],
) -> list[tuple[int, str]]:
    """Grava `EventRole` por personagem informado na criação (feature 152).

    Auto-detecta a ficha de figurino pelo nome quando não selecionada manualmente; pré-escala um
    talento por vaga sem duplicar o mesmo talento no mesmo formulário. Devolve `(talent_id,
    character_name)` de cada pré-escala feita, para o aviso de conflito pós-commit.
    """
    used_talent_ids: set[int] = set()
    assigned_now: list[tuple[int, str]] = []
    cache_keys = ["cache_1h", "cache_2h", "cache_3h", "cache_4h"]

    for i, char_data in enumerate(characters):
        name = (char_data.get("name") or "").strip()
        if not name:
            continue

        sheet_id = char_data.get("figurino_sheet_id") or figurino_by_name.get(name.lower())
        cache_val = char_data.get("cache_value")
        if cache_val is None and i < len(orc_caches):
            cache_val = orc_caches[i].get(cache_keys[dur_idx])
        role_type = orc_caches[i].get("role_type", "character") if i < len(orc_caches) else "character"

        talent_id = char_data.get("talent_id")
        pre_tid = None
        if talent_id is not None and talent_id in valid_talent_ids and talent_id not in used_talent_ids:
            pre_tid = talent_id
            used_talent_ids.add(pre_tid)
            assigned_now.append((pre_tid, name))

        from_orc = bool(orc_caches) and cache_val is not None
        db.session.add(EventRole(
            event_id=event.id,
            character_name=name,
            figurino_sheet_id=sheet_id,
            cache_value=cache_val,
            cache_cap=cache_val if from_orc else None,
            role_type=role_type,
            needs_makeup=bool(char_data.get("needs_makeup")) or None,
            is_singer=bool(char_data.get("is_singer")) or None,
            talent_id=pre_tid,
            assigned_at=datetime.now(tz=TZ) if pre_tid else None,
        ))

    return assigned_now


def _apply_default_roles(
    event: CalendarEvent,
    *,
    event_type: str | None,
    came_from_orcamento: bool,
    coordinator_talent_id: int | None,
    valid_talent_ids: set[int],
    used_talent_ids: set[int],
) -> tuple[int, str] | None:
    """Garante coordenador + (SHOW) técnico de som quando a criação não veio de um orçamento
    (feature 152) — mesma regra condicional de `_ensure_coordinator`/`_ensure_sound_technician`.

    Devolve a pré-escala do coordenador (para o aviso de conflito), se houver.
    """
    assigned: tuple[int, str] | None = None
    if not came_from_orcamento:
        if (
            coordinator_talent_id is not None
            and coordinator_talent_id in valid_talent_ids
            and coordinator_talent_id not in used_talent_ids
        ):
            db.session.add(EventRole(
                event_id=event.id,
                character_name="Coordenador",
                role_type="extra",
                talent_id=coordinator_talent_id,
                assigned_at=datetime.now(tz=TZ),
            ))
            assigned = (coordinator_talent_id, "Coordenador")
        else:
            _ensure_coordinator(event.id)

    if event_type == "SHOW":
        _ensure_sound_technician(event.id)

    return assigned


def _check_talent_conflicts(
    assigned_now: list[tuple[int, str]],
    start: datetime,
    end: datetime,
    event_id: int,
    talents: list[dict],
) -> list[str]:
    """Aviso não-bloqueante de conflito de agenda para talentos pré-escalados (feature 152)."""
    conflicts = []
    for tid, char_name in assigned_now:
        other = _talent_time_conflict(tid, start, end, exclude_event_id=event_id)
        if other:
            tname = next((t["name"] for t in talents if t["id"] == tid), f"Talento {tid}")
            conflicts.append(f"{tname} ({char_name}) — já em “{other.title}”")
    return conflicts


def _create_client_links(event: CalendarEvent, client_pairs: list[tuple[int, str]]) -> None:
    """Associa clientes ao evento na criação (feature 114/152)."""
    if not client_pairs:
        return
    from app.models import EventClient

    for cid, rel in client_pairs:
        db.session.add(EventClient(event_id=event.id, client_id=cid, relationship_type=rel))
    event.client_id = _primary_client_id(client_pairs)


def _link_form_response(form_response_id: int | None, event_id: int) -> None:
    """Vincula uma resposta de pré-contrato já recebida ao evento novo (feature 118/152).

    Marca o vínculo como decisão humana (``manual`` + ``locked``): o evento foi criado a
    partir desta resposta, então a automação nunca deve religá-la em outro lugar.
    """
    if form_response_id is None:
        return
    from app.models import FormResponse

    fr = FormResponse.query.get(form_response_id)
    if fr and fr.event_id is None:
        fr.event_id = event_id
        fr.event_link_source = "manual"
        fr.event_link_ambiguous = False
        fr.event_link_locked = True


def _create_reembolso_entry(
    event: CalendarEvent,
    *,
    description: str | None,
    amount: float | None,
    created_by_id: int,
    invoice_file_path: str | None = None,
) -> None:
    """Reembolso a cobrar da cliente na criação, sem comprovante nesta fatia (feature 136/152)."""
    desc = (description or "").strip()
    if not desc or not amount or amount <= 0:
        return
    db.session.add(EventReimbursement(
        event_id=event.id,
        description=desc[:200],
        amount=amount,
        invoice_file_path=invoice_file_path,
        created_by_id=created_by_id,
    ))


def _create_observations_from_input(event: CalendarEvent, observations: list[dict]) -> None:
    """Observações de texto/link/imagem na criação (feature 150/152).

    Cada item já vem com `file_path` resolvido pelo wrapper Jinja quando `obs_type == "image"`
    (upload continua fora do núcleo). A API não envia imagem nesta fatia — um item de imagem sem
    `file_path` é descartado, mesmo padrão da feature 150.
    """
    for obs in observations:
        otype = obs.get("obs_type")
        content = (obs.get("content") or "").strip()
        label = (obs.get("label") or "").strip()
        file_path = obs.get("file_path")
        if otype == "image":
            if not file_path:
                continue
        elif otype in ("text", "link"):
            if not content:
                continue
        else:
            continue
        db.session.add(EventObservation(
            event_id=event.id,
            obs_type=otype,
            content=content or None,
            file_path=file_path,
            label=label or None,
        ))


def _create_event_core(
    data: dict,
    *,
    google_event_id: str,
    gc_title: str,
    actor_name: str,
    actor_id: int,
    actor_role: str,
) -> tuple[CalendarEvent, list[str]]:
    """Orquestra a criação completa do evento (feature 152) — único ponto chamado pelo wrapper
    Jinja e pela API, depois que `insert_event` (Google) já rodou com sucesso (mesmo padrão de
    `_delete_event_flow`/`_sync_single_event_flow`, 151). Devolve o evento criado e os avisos de
    conflito de agenda (pré-escala de talento), não-bloqueantes.
    """
    event = _create_event_row(data, google_event_id=google_event_id, gc_title=gc_title)

    _create_client_links(event, data.get("client_pairs") or [])
    _link_form_response(data.get("form_response_id"), event.id)

    figurino_by_name = {
        s.character_name.lower(): s.id for s in FigurinoSheet.query.all()
    }
    assignable_talents = [
        {"id": t.id, "name": t.artistic_name or t.full_name}
        for t in Talent.query.filter_by(status="active").all()
    ]
    valid_talent_ids = {t["id"] for t in assignable_talents}
    orc_caches = data.get("orc_caches") or []
    dur_idx = {"1": 0, "2": 1, "3": 2, "4": 3}.get(str(data.get("duracao", "1")), 0)

    assigned_now = _create_roles_from_input(
        event,
        data.get("characters") or [],
        orc_caches=orc_caches,
        dur_idx=dur_idx,
        figurino_by_name=figurino_by_name,
        valid_talent_ids=valid_talent_ids,
    )
    coord = _apply_default_roles(
        event,
        event_type=data.get("event_type"),
        came_from_orcamento=bool(orc_caches),
        coordinator_talent_id=data.get("coordinator_talent_id"),
        valid_talent_ids=valid_talent_ids,
        used_talent_ids={tid for tid, _ in assigned_now},
    )
    if coord:
        assigned_now.append(coord)

    if data.get("has_reembolso"):
        _create_reembolso_entry(
            event,
            description=data.get("reembolso_description"),
            amount=data.get("reembolso_amount"),
            invoice_file_path=data.get("reembolso_invoice_file_path"),
            created_by_id=actor_id,
        )
    _create_observations_from_input(event, data.get("observations") or [])

    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="COMERCIAL",
        message="Evento criado pela plataforma",
        created_at=datetime.now(tz=TZ),
    ))
    _log_sync("platform_created", event, actor=actor_name, actor_role=actor_role)
    from app.financeiro.routes import _sync_commission_payment
    _sync_commission_payment(event)
    db.session.commit()

    if event.needs_rehearsal:
        _notify_ensaio_team(event)

    conflicts = _check_talent_conflicts(
        assigned_now, event.start_at, event.end_at, event.id, assignable_talents
    )
    return event, conflicts


def _parse_create_event_form() -> dict:
    """Lê `request.form`/`request.files` e devolve o `data` normalizado para o núcleo (feature
    152) — money/ids já convertidos, campos de arquivo resolvidos em caminho. Só usado pelo
    wrapper Jinja (a API constrói seu próprio `data` a partir do corpo JSON).
    """
    def _int_or_none(raw: str) -> int | None:
        raw = (raw or "").strip()
        return int(raw) if raw.isdigit() else None

    sale_date_raw = request.form.get("sale_date", "").strip()
    try:
        sale_date_val = date.fromisoformat(sale_date_raw) if sale_date_raw else None
    except ValueError:
        sale_date_val = None

    payment_due_raw = request.form.get("payment_due_date", "").strip()

    char_names = request.form.getlist("character_names[]")
    sheet_ids = request.form.getlist("figurino_sheet_ids[]")
    char_makeups = request.form.getlist("char_needs_makeup[]")
    char_singers = request.form.getlist("char_is_singer[]")
    char_caches = request.form.getlist("char_cache[]")
    char_talent_ids = request.form.getlist("char_talent_id[]")
    characters = []
    for i, (char, sheet_id_raw) in enumerate(zip(char_names, sheet_ids, strict=False)):
        char = char.strip()
        if not char:
            continue
        characters.append({
            "name": char,
            "figurino_sheet_id": _int_or_none(sheet_id_raw),
            "cache_value": parse_brl(char_caches[i]) if i < len(char_caches) else None,
            "needs_makeup": (char_makeups[i] == "1") if i < len(char_makeups) else False,
            "is_singer": (char_singers[i] == "1") if i < len(char_singers) else False,
            "talent_id": _int_or_none(char_talent_ids[i]) if i < len(char_talent_ids) else None,
        })

    acr_json = request.form.get("acrescimos_json", "").strip()
    try:
        acrescimos = json.loads(acr_json) if acr_json else []
    except json.JSONDecodeError:
        acrescimos = []

    orc_caches_json = request.form.get("orc_caches_json", "")
    try:
        orc_caches = json.loads(orc_caches_json) if orc_caches_json else []
    except json.JSONDecodeError:
        orc_caches = []

    # Nota fiscal (arquivo opcional) — fora do núcleo, resolvido aqui em caminho salvo.
    invoice_filename = None
    invoice_file = request.files.get("invoice_file")
    # "Não veio arquivo" e "formato recusado" são casos diferentes: juntar os dois num único `if`
    # fazia o evento ser criado em silêncio, sem a nota que a pessoa acabou de anexar.
    if invoice_file and invoice_file.filename:
        if not is_allowed_extension(invoice_file.filename, ALLOWED_INVOICE_EXTENSIONS):
            flash("Nota fiscal não anexada: envie PDF, XML ou imagem.", "error")
            invoice_file = None
    else:
        invoice_file = None

    if invoice_file:
        inv_size = invoice_file.stream.seek(0, 2)
        invoice_file.stream.seek(0)
        if inv_size <= 20 * 1024 * 1024:
            invoice_filename = secure_filename(invoice_file.filename)
            invoice_file.save(os.path.join(current_app.config["UPLOAD_INVOICES"], invoice_filename))

    # Observações texto/link/imagem — imagem resolvida em caminho aqui (fora do núcleo).
    obs_types = request.form.getlist("obs_type[]")
    obs_contents = request.form.getlist("obs_content[]")
    obs_labels = request.form.getlist("obs_label[]")
    obs_images = request.files.getlist("obs_image[]")
    observations = []
    img_idx = 0
    for j, otype in enumerate(obs_types):
        file_path = None
        if otype == "image":
            if img_idx < len(obs_images):
                file_path = _save_file_upload(
                    obs_images[img_idx],
                    current_app.config["UPLOAD_EVENT_OBS"],
                    "event_obs",
                    allowed=ALLOWED_IMAGE_EXTENSIONS,
                )
                img_idx += 1
        observations.append({
            "obs_type": otype,
            "content": obs_contents[j].strip() if j < len(obs_contents) else "",
            "label": obs_labels[j].strip() if j < len(obs_labels) else "",
            "file_path": file_path,
        })

    event_type = request.form.get("event_type", "").strip()
    return {
        "title": request.form.get("title", "").strip(),
        "event_type": event_type,
        "date_str": request.form.get("event_date", "").strip(),
        "start_str": request.form.get("event_start", "").strip(),
        "end_str": request.form.get("event_end", "").strip(),
        "location": request.form.get("location", "").strip(),
        "description": request.form.get("description", "").strip(),
        "needs_rehearsal": (event_type == "SHOW") or bool(request.form.get("needs_rehearsal")),
        "sale_value": parse_brl(request.form.get("sale_value", "")),
        "sale_value_gross": parse_brl(request.form.get("sale_value_gross", "")),
        "transport_value": parse_brl(request.form.get("transport_value", "")),
        "acrescimo_value": parse_brl(request.form.get("acrescimo_value", "")),
        "with_invoice": bool(request.form.get("with_invoice")),
        "invoice_filename": invoice_filename,
        "is_cortesia_permuta": bool(request.form.get("is_cortesia_permuta")),
        "seller_id": _int_or_none(request.form.get("seller_id", "")),
        "sale_date": sale_date_val,
        "payment_method": request.form.get("payment_method", "").strip() or None,
        "payment_installments": _int_or_none(request.form.get("payment_installments", "")),
        "payment_due_date": date.fromisoformat(payment_due_raw) if payment_due_raw else None,
        "orcamento_history_id": _int_or_none(request.form.get("orcamento_history_id", "")),
        "duracao": request.form.get("duracao", "1").strip(),
        "characters": characters,
        "orc_caches": orc_caches,
        "acrescimos": acrescimos,
        "coordinator_talent_id": _int_or_none(request.form.get("coordinator_talent_id", "")),
        "client_pairs": _parse_client_pairs(),
        "form_response_id": _int_or_none(request.form.get("form_response_id", "")),
        "has_reembolso": bool(request.form.get("has_reembolso")),
        "reembolso_description": request.form.get("reembolso_description", "").strip(),
        "reembolso_amount": parse_brl(request.form.get("reembolso_amount", "")),
        "reembolso_invoice_file_path": _save_nf_file(request.files.get("reembolso_invoice_file")),
        "observations": observations,
    }


@calendar_bp.route("/events/new", methods=["GET", "POST"])
@login_required
def create_event():
    if not any(r.name.upper() in _CAN_CREATE for r in current_user.roles):
        abort(403)

    options = _build_event_create_options()

    # ── GET — pré-fill a partir do orçamento ────────────────────────────────
    if request.method == "GET":
        orc_id = request.args.get("orcamento_id", "").strip()
        prefill = _build_orcamento_prefill(int(orc_id) if orc_id.isdigit() else None)
        return render_template(
            "event_create.html",
            figurino_sheets=options["figurino_sheets"],
            sellers=options["sellers"],
            assignable_talents=options["assignable_talents"],
            errors=[],
            prefill=prefill,
            today_str=date.today().isoformat(),
            old={},
            old_chars=[],
            old_clients=[],
            old_form_response=None,
            client_relation_tipos=CLIENT_RELATION_TIPOS,
        )

    # ── POST ────────────────────────────────────────────────────────────────
    data = _parse_create_event_form()

    # Personagens enviados, p/ repopular o form se o servidor re-renderizar por erro
    # (apenas dados alinhados por linha: nome + figurino; anexos não são restauráveis).
    old_chars = [
        {"label": c["name"], "sheet_id": c["figurino_sheet_id"] or ""} for c in data["characters"]
    ]

    old_form_response = None
    if data["form_response_id"] is not None:
        from app.models import FormResponse as _FormResponse
        _fr_obj = _FormResponse.query.get(data["form_response_id"])
        if _fr_obj:
            old_form_response = {
                "id": _fr_obj.id,
                "name": _fr_obj.contact_name,
                "form_type": _fr_obj.form_type_label,
            }

    from app.models import Client as _Client
    old_clients = []
    for _cid, _rel in data["client_pairs"]:
        _cli = _Client.query.get(_cid)
        if _cli:
            old_clients.append({
                "id": _cli.id,
                "name": _cli.name,
                "phone": _cli.phone_display or _cli.phone or "",
                "relation": _rel,
            })

    def _render_error(errors: list[str]):
        return render_template(
            "event_create.html", figurino_sheets=options["figurino_sheets"],
            sellers=options["sellers"], assignable_talents=options["assignable_talents"],
            errors=errors, prefill={}, today_str=date.today().isoformat(),
            old=request.form, old_chars=old_chars, old_clients=old_clients,
            old_form_response=old_form_response, client_relation_tipos=CLIENT_RELATION_TIPOS,
        )

    validation_errors = _validate_event_core(data)
    if validation_errors:
        return _render_error(list(validation_errors.values()))

    # Remove prefixo (TIPO) que o JS já inseriu no título para não duplicar
    title = data["title"]
    event_type = data["event_type"]
    clean_title = re.sub(r'^\s*\([^)]*\)\s*', '', title).strip() if title else title
    gc_title = f"({event_type}) {clean_title}" if event_type else title
    d = date.fromisoformat(data["date_str"])
    st, et = _build_start_end(d, data["start_str"], data["end_str"])
    try:
        created = insert_event(
            CALENDAR_ID, gc_title, st, et,
            description=data["description"], location=data["location"],
        )
    except Exception as exc:
        # Qualquer falha do Google Agenda (desconectado, indisponível, erro da API) vira
        # um aviso amigável — nunca uma tela de erro técnica. Registra o erro real no log.
        current_app.logger.exception("Falha ao criar evento no Google Agenda")
        if "não conectado" in str(exc).lower() or "google não" in str(exc).lower():
            friendly = ("A Agenda do Google está desconectada. Reconecte em /google/connect e "
                        "tente novamente. Se precisar, avise o suporte.")
        else:
            friendly = ("Não foi possível criar o evento na Agenda do Google agora. "
                        "Verifique a conexão e tente novamente. Se persistir, avise o suporte.")
        return _render_error([friendly])

    event, conflicts = _create_event_core(
        data,
        google_event_id=created["id"],
        gc_title=gc_title,
        actor_name=current_user.name,
        actor_id=current_user.id,
        actor_role=", ".join(r.name for r in current_user.roles),
    )

    # ── Comprovantes de pagamento e contrato (dependem de arquivo — fora do núcleo) ──────────
    payment_files = request.files.getlist("payment_files[]")
    payment_amounts = request.form.getlist("payment_amounts[]")
    for pf, pa_raw in zip(payment_files, payment_amounts, strict=False):
        fpath = _save_file_upload(pf, current_app.config["UPLOAD_PAYMENTS"], "payments")
        if fpath:
            db.session.add(EventPayment(event_id=event.id, file_path=fpath, amount=parse_brl(pa_raw)))

    contract_file = request.files.get("contract_file")
    contract_amount = request.form.get("contract_amount", "").strip()
    is_signed = bool(request.form.get("contract_signed"))
    fpath = _save_file_upload(contract_file, current_app.config["UPLOAD_CONTRACTS"], "contracts")
    if fpath:
        db.session.add(EventContract(
            event_id=event.id, file_path=fpath,
            amount=parse_brl_int(contract_amount), is_signed=is_signed,
        ))
    if payment_files or fpath:
        db.session.commit()

    if conflicts:
        flash("Atenção: conflito de agenda na pré-escala — " + "; ".join(conflicts), "warning")

    flash("Evento criado com sucesso!", "success")
    return redirect(url_for("calendar.event_detail", event_id=event.id))

# ─── MATERIAIS DE ENSAIO ──────────────────────────────────────────────────────

_CAN_ENSAIO_MATERIAL = {RoleName.ENSAIO, RoleName.CASTING, RoleName.SUPERADMIN}

def _can_ensaio(user) -> bool:
    return any(r.name.upper() in _CAN_ENSAIO_MATERIAL for r in user.roles)


@calendar_bp.route("/events/<int:event_id>/ensaio/upload", methods=["POST"])
@login_required
def ensaio_upload_material(event_id: int):
    if not _can_ensaio(current_user):
        abort(403)
    event = CalendarEvent.query.get_or_404(event_id)

    file = request.files.get("material_file")
    label = request.form.get("label", "").strip()

    if not file or not file.filename:
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    # Allowlist antes do disco: o material é servido por `/uploads`, no mesmo origin das SPAs.
    if not is_allowed_extension(file.filename, ALLOWED_MATERIAL_EXTENSIONS):
        flash("Formato de arquivo não permitido para material de ensaio.", "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > 20 * 1024 * 1024:
        flash("Arquivo muito grande (máx 20 MB).", "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    filename = secure_filename(file.filename)
    save_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "ensaio_materials")
    os.makedirs(save_dir, exist_ok=True)
    # prefixo com event_id para evitar colisões
    unique_name = f"{event_id}_{int(datetime.utcnow().timestamp())}_{filename}"
    file.save(os.path.join(save_dir, unique_name))

    db.session.add(EnsaioMaterial(
        event_id=event_id,
        user_id=current_user.id,
        material_type="file",
        label=label or filename,
        file_path=f"ensaio_materials/{unique_name}",
    ))
    db.session.commit()
    flash("Arquivo adicionado.", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))


@calendar_bp.route("/events/<int:event_id>/ensaio/link", methods=["POST"])
@login_required
def ensaio_add_link(event_id: int):
    if not _can_ensaio(current_user):
        abort(403)
    event = CalendarEvent.query.get_or_404(event_id)

    url   = request.form.get("link_url", "").strip()
    label = request.form.get("link_label", "").strip()

    if not url:
        flash("URL não pode ser vazio.", "error")
        return redirect(url_for("calendar.event_detail", event_id=event_id))

    db.session.add(EnsaioMaterial(
        event_id=event_id,
        user_id=current_user.id,
        material_type="link",
        label=label or url[:60],
        url=url,
    ))
    db.session.commit()
    flash("Link adicionado.", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))


@calendar_bp.route("/events/<int:event_id>/ensaio/material/<int:material_id>/delete", methods=["POST"])
@login_required
def ensaio_delete_material(event_id: int, material_id: int):
    if not _can_ensaio(current_user):
        abort(403)
    material = EnsaioMaterial.query.get_or_404(material_id)
    if material.event_id != event_id:
        abort(404)
    # remove arquivo físico se existir
    if material.file_path:
        full = os.path.join(current_app.config["UPLOAD_FOLDER"], material.file_path)
        if os.path.exists(full):
            os.remove(full)
    db.session.delete(material)
    db.session.commit()
    flash("Material removido.", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))


def _sync_single_event_flow(event: CalendarEvent) -> str:
    """Núcleo da sincronização de um evento com o Google (feature 151), fonte única.

    Reusado pelo wrapper Jinja e pelo endpoint JSON. Sem `flash`/`request` — o adaptador é quem
    traduz o status em mensagem/resposta.

    Returns:
        `"no_google_id"` se o evento não tem `google_event_id`; `"not_found"` se o Google não
        devolve o evento; `"ok"` quando sincroniza e commita.
    """
    if not event.google_event_id:
        return "no_google_id"
    item = fetch_single_event(CALENDAR_ID, event.google_event_id)
    if not item:
        return "not_found"
    sync_events([item])
    db.session.commit()
    return "ok"


def _delete_event_flow(event: CalendarEvent, *, actor_name: str, actor_role: str) -> bool:
    """Núcleo da exclusão de um evento (feature 151), fonte única.

    Reusado pelo wrapper Jinja e pelo endpoint JSON. Recusa a exclusão de um evento líder de grupo
    (é preciso desagrupar os satélites antes). Registra o log `manual_deleted`, remove do banco e do
    Google via `_delete_event` e commita.

    Returns:
        `False` se o evento é líder de grupo (não excluído); `True` quando excluído.
    """
    if event.is_group_leader:  # FR-004: desagrupar antes
        return False
    _log_sync(
        "manual_deleted", event,
        details="Removido do banco e do Google Calendar",
        actor=actor_name,
        actor_role=actor_role,
    )
    _delete_event(event, also_from_google=True)
    db.session.commit()
    return True


@calendar_bp.route("/events/<int:event_id>/sync", methods=["POST"])
@login_required
def sync_single_event(event_id: int):
    """Sincroniza um único evento com o Google Calendar (wrapper fino sobre
    `_sync_single_event_flow`, feature 151)."""
    event = CalendarEvent.query.get_or_404(event_id)
    status = _sync_single_event_flow(event)
    if status == "no_google_id":
        flash("Evento sem ID do Google Calendar — não é possível sincronizar.", "error")
    elif status == "not_found":
        flash("Não foi possível buscar o evento no Google Calendar.", "error")
    else:
        flash("Evento sincronizado com sucesso.", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))


@calendar_bp.route("/events/<int:event_id>/observations/add", methods=["POST"])
@login_required
def add_observation(event_id: int):
    """Adiciona observações a um evento existente.

    Adaptador fino: a regra de "o que conta como observação válida" vive em
    `observation_ops.add_observation` (fonte única, feature 150). Este handler mantém o parsing dos
    arrays do form e o upload de imagem; o núcleo cria (ou ignora) cada item.
    """
    from app.calendar.observation_ops import add_observation as _add_observation

    event = CalendarEvent.query.get_or_404(event_id)

    obs_types    = request.form.getlist("obs_type[]")
    obs_contents = request.form.getlist("obs_content[]")
    obs_labels   = request.form.getlist("obs_label[]")
    obs_images   = request.files.getlist("obs_image[]")
    img_idx = 0
    added = 0
    for j, otype in enumerate(obs_types):
        content   = obs_contents[j] if j < len(obs_contents) else ""
        label     = obs_labels[j]   if j < len(obs_labels)   else ""
        file_path = None
        if otype == "image" and img_idx < len(obs_images):
            file_path = _save_file_upload(
                obs_images[img_idx],
                current_app.config["UPLOAD_EVENT_OBS"],
                "event_obs",
                allowed=ALLOWED_IMAGE_EXTENSIONS,
            )
            img_idx += 1
        if _add_observation(
            event, obs_type=otype, content=content, label=label, file_path=file_path
        ):
            added += 1

    if added:
        db.session.commit()
        flash(f"{added} observação(ões) adicionada(s).", "success")
    return redirect(url_for("calendar.event_detail", event_id=event_id))


@calendar_bp.route("/events/<int:event_id>/observations/<int:obs_id>/delete", methods=["POST"])
@login_required
def delete_observation(event_id: int, obs_id: int):
    """Remove uma observação de um evento.

    Adaptador fino sobre `observation_ops.delete_observation` (feature 150): 404 se a observação
    não pertence ao evento, exatamente como o `first_or_404` de antes.
    """
    from app.calendar.observation_ops import delete_observation as _delete_observation

    event = CalendarEvent.query.get_or_404(event_id)
    if not _delete_observation(event, obs_id):
        abort(404)
    return redirect(url_for("calendar.event_detail", event_id=event_id))


@calendar_bp.route("/agenda/log")
@login_required
def agenda_log():
    """Redireciona para a página unificada de Sincronização da Agenda (compatibilidade de links antigos)."""
    return redirect(url_for("admin.sync_status"))


@calendar_bp.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_calendar_event(event_id: int):
    """Exclui permanentemente um evento do banco e do Google Calendar (wrapper fino sobre
    `_delete_event_flow`, feature 151)."""
    if not any(r.name.upper() in _CAN_DELETE for r in current_user.roles):
        abort(403)
    event = CalendarEvent.query.get_or_404(event_id)
    title = event.title  # capturado antes da exclusão
    if not _delete_event_flow(
        event,
        actor_name=current_user.name,
        actor_role=", ".join(r.name for r in current_user.roles),
    ):
        flash(
            f'Não é possível excluir "{title}": desagrupe os eventos satélites antes de excluir.',
            "error",
        )
        return redirect(url_for("calendar.event_detail", event_id=event_id))
    flash(f'Evento "{title}" excluído com sucesso.', "success")
    return redirect(url_for("calendar.agenda"))


def _redirect_back():
    """Volta para a página de onde veio o form (ex.: home); cai na home se não houver referrer."""
    return redirect(request.referrer or url_for("home"))


@calendar_bp.route("/roles/<int:role_id>/dismiss", methods=["POST"])
@login_required
def dismiss_role(role_id: int):
    """Dispensa um cargo de casting pendente sem excluí-lo (feature 108).

    Diferente de excluir, o cargo continua existindo — por isso a sincronização com o Google
    Agenda nunca o recria — mas para de contar como tarefa pendente de casting. Restrito ao
    super admin (mais restrito que a exclusão de cargo, que também aceita o papel Casting).
    """
    # Adaptador fino — regra em casting_ops.dismiss_role (feature 148).
    if not _is_superadmin():
        abort(403)
    role = EventRole.query.get_or_404(role_id)
    from app.calendar.casting_ops import dismiss_role as _dismiss_role
    ok = _dismiss_role(role, actor_name=current_user.name, dismissed_by=current_user.id)
    if not ok:
        flash("Só é possível dispensar cargos sem talento atribuído.", "error")
    else:
        flash("Tarefa dispensada.", "success")
    return _redirect_back()


@calendar_bp.route("/roles/<int:role_id>/restore", methods=["POST"])
@login_required
def restore_role(role_id: int):
    """Reverte a dispensa de um cargo de casting, voltando a contá-lo como pendente (feature 108)."""
    # Adaptador fino — regra em casting_ops.restore_role (feature 148).
    if not _is_superadmin():
        abort(403)
    role = EventRole.query.get_or_404(role_id)
    was_dismissed = role.dismissed_at is not None
    from app.calendar.casting_ops import restore_role as _restore_role
    _restore_role(role, actor_name=current_user.name)
    if was_dismissed:
        flash("Tarefa restaurada.", "success")
    return _redirect_back()
