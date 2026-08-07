import json
import logging
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

TZ = ZoneInfo("America/Sao_Paulo")

def _instance_path(filename: str) -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "instance", filename)

def get_client_secrets_path() -> str:
    return _instance_path("google_oauth_client.json")

def get_token_path() -> str:
    return _instance_path("google_token.json")

def build_flow(redirect_uri: str) -> Flow:
    secrets_path = get_client_secrets_path()
    if os.path.exists(secrets_path):
        return Flow.from_client_secrets_file(secrets_path, scopes=SCOPES, redirect_uri=redirect_uri)

    # Fallback: variáveis de ambiente (produção / Railway)
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError(
            "Credenciais Google OAuth não encontradas. "
            "Defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no ambiente."
        )
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)

def get_authorization_url(redirect_uri: str) -> tuple[str, str]:
    flow = build_flow(redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    return auth_url, state

def save_token(creds: Credentials) -> None:
    """Persiste o token OAuth no banco de dados (e no arquivo local como fallback)."""
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
    }
    token_json = json.dumps(data, ensure_ascii=False)

    # Salva no banco (sobrevive a redeploys no Railway)
    try:
        from flask import current_app
        with current_app.app_context():
            from app.models import SiteSetting
            from app import db
            settings = SiteSetting.query.get(1)
            if settings:
                settings.google_token = token_json
                db.session.commit()
    except RuntimeError:
        pass  # fora de contexto Flask (ex: script standalone)

    # Salva no arquivo como fallback local
    try:
        with open(get_token_path(), "w", encoding="utf-8") as f:
            f.write(token_json)
    except OSError:
        pass


def load_credentials() -> Credentials | None:
    """Carrega credenciais OAuth — banco primeiro, arquivo como fallback."""
    data = None

    # 1. Tenta banco de dados (produção / Railway)
    try:
        from flask import current_app
        with current_app.app_context():
            from app.models import SiteSetting
            settings = SiteSetting.query.get(1)
            if settings and settings.google_token:
                data = json.loads(settings.google_token)
    except RuntimeError:
        pass  # fora de contexto Flask

    # 2. Fallback: arquivo local (desenvolvimento)
    if data is None:
        token_path = get_token_path()
        if os.path.exists(token_path):
            with open(token_path, "r", encoding="utf-8") as f:
                data = json.load(f)

    if data is None:
        return None

    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )

    # Refresh automático se expirado
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_token(creds)

    return creds

def fetch_events_for_month(calendar_id: str, year: int, month: int) -> list[dict]:
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Google não conectado. Acesse /google/connect primeiro.")

    service = build("calendar", "v3", credentials=creds)

    start = datetime(year, month, 1, 0, 0, 0, tzinfo=TZ)
    # primeiro dia do mês seguinte
    if month == 12:
        end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=TZ)
    else:
        end = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=TZ)

    resp = service.events().list(
        calendarId=calendar_id,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        showDeleted=False,
        maxResults=2500,
    ).execute()  # parâmetros são os oficiais para listar ordenado por início :contentReference[oaicite:8]{index=8}

    return resp.get("items", [])


def fetch_events_for_range(calendar_id: str, start: datetime, end: datetime) -> list[dict]:
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Google nao conectado. Acesse /google/connect primeiro.")

    service = build("calendar", "v3", credentials=creds)

    resp = service.events().list(
        calendarId=calendar_id,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        showDeleted=False,
        maxResults=2500,
    ).execute()

    return resp.get("items", [])


def fetch_single_event(calendar_id: str, google_event_id: str) -> dict | None:
    """Busca um único evento pelo ID no Google Calendar."""
    creds = load_credentials()
    if not creds:
        return None
    service = build("calendar", "v3", credentials=creds)
    try:
        return service.events().get(calendarId=calendar_id, eventId=google_event_id).execute()
    except Exception as exc:  # noqa: BLE001 — evento pode ter sido removido do Google
        logger.warning("[gcal] falha ao buscar evento %s: %s", google_event_id, exc)
        return None


def parse_event_datetime(item: dict) -> tuple[datetime | None, datetime | None]:
    start = item.get("start", {})
    end = item.get("end", {})
    start_dt = start.get("dateTime") or start.get("date")
    end_dt = end.get("dateTime") or end.get("date")

    def _parse(value: str | None) -> datetime | None:
        if not value:
            return None
        # date only => naive midnight
        if len(value) == 10:
            return datetime.fromisoformat(value)
        dt = datetime.fromisoformat(value)
        # Convert timezone-aware to naive São Paulo time for consistent DB storage.
        # PostgreSQL (TIMESTAMP WITHOUT TIME ZONE) converts aware datetimes to UTC,
        # but templates display naive datetimes as-is — so we must store naive SP.
        if dt.tzinfo is not None:
            dt = dt.astimezone(TZ).replace(tzinfo=None)
        return dt

    return _parse(start_dt), _parse(end_dt)


def insert_event(
    calendar_id: str,
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    description: str = "",
    location: str = "",
    conference_request_id: str | None = None,
) -> dict:
    """Cria um evento no Google Calendar. Retorna o dict do evento criado (inclui 'id').

    Args:
        conference_request_id: Quando informado, pede ao Google que gere uma **sala do Meet**
            para o evento (feature 205). Precisa ser único por requisição — o Google usa esse id
            para não criar duas salas se a mesma chamada for repetida.

    A criação da sala é assíncrona do lado do Google: a resposta pode voltar com
    ``conferenceData.createRequest.status.statusCode == "pending"`` e **sem** ``hangoutLink``.
    Quem chama precisa tratar esse caso (ver `virtuais_ops.extrair_meet_url`), não assumir que o
    link veio.
    """
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Google não conectado. Acesse /google/connect primeiro.")
    service = build("calendar", "v3", credentials=creds)
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Sao_Paulo"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "America/Sao_Paulo"},
    }
    if location:
        body["location"] = location

    # `conferenceDataVersion=1` é obrigatório para o Google aceitar `conferenceData` — sem ele a
    # API ignora o pedido em silêncio e devolve um evento sem sala.
    kwargs: dict = {}
    if conference_request_id:
        body["conferenceData"] = {
            "createRequest": {
                "requestId": conference_request_id,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }
        kwargs["conferenceDataVersion"] = 1

    return service.events().insert(calendarId=calendar_id, body=body, **kwargs).execute()


def update_event(
    calendar_id: str,
    google_event_id: str,
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    description: str = "",
    location: str = "",
) -> dict:
    """Atualiza um evento existente no Google Calendar via patch."""
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Google não conectado. Acesse /google/connect primeiro.")
    service = build("calendar", "v3", credentials=creds)
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Sao_Paulo"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "America/Sao_Paulo"},
    }
    if location:
        body["location"] = location
    return service.events().patch(calendarId=calendar_id, eventId=google_event_id, body=body).execute()


def upsert_task_event(
    calendar_id: str,
    title: str,
    day: "date",
    *,
    google_event_id: str | None = None,
    description: str = "",
    attendee_emails: list[str] | None = None,
    extended_private: dict[str, str] | None = None,
) -> dict:
    """Cria ou atualiza um compromisso de **dia inteiro** com convidados (feature 225).

    Separado de `insert_event`/`update_event` de propósito: aquele par serve aos eventos de show,
    que são a fonte de verdade da agenda e passam pelo sincronizador. Este serve a prazos internos
    de trabalho — dia inteiro, com a pessoa responsável convidada — e **nunca** deve virar um
    `CalendarEvent` na plataforma. É `extended_private` que garante isso: `sync_events` pula todo
    item que carregue `extendedProperties.private.manto_kind`.

    Args:
        day: Dia do prazo. Vira um evento de dia inteiro (`start.date`), porque prazo não tem
            hora — e evento de dia inteiro aparece na faixa do topo da agenda, onde se lê de
            relance, em vez de sumir no meio dos horários do dia.
        google_event_id: Quando informado, atualiza esse compromisso em vez de criar outro.
        attendee_emails: Convidados. O Google manda o convite por e-mail e o compromisso entra
            na agenda pessoal de cada um (`sendUpdates="all"`).

    Returns:
        O dict do evento criado/atualizado (inclui ``id``).

    Raises:
        RuntimeError: Google não conectado. Quem chama trata como aviso, nunca como falha da
            operação de negócio.
    """
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Google não conectado. Acesse /google/connect primeiro.")
    service = build("calendar", "v3", credentials=creds)

    # `end.date` é EXCLUSIVO na API do Google: um evento de um dia só termina no dia seguinte.
    body: dict = {
        "summary": title,
        "description": description,
        "start": {"date": day.isoformat()},
        "end": {"date": (day + timedelta(days=1)).isoformat()},
        "transparency": "transparent",  # prazo não ocupa a pessoa: ela segue livre para eventos
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 12 * 60}],  # véspera, meio-dia
        },
    }
    if attendee_emails is not None:
        body["attendees"] = [{"email": e} for e in attendee_emails if e]
    if extended_private:
        body["extendedProperties"] = {"private": dict(extended_private)}

    if google_event_id:
        return (
            service.events()
            .patch(
                calendarId=calendar_id, eventId=google_event_id,
                body=body, sendUpdates="all",
            )
            .execute()
        )
    return (
        service.events()
        .insert(calendarId=calendar_id, body=body, sendUpdates="all")
        .execute()
    )


def delete_event(calendar_id: str, google_event_id: str) -> None:
    """Remove um evento do Google Calendar."""
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Google não conectado. Acesse /google/connect primeiro.")
    service = build("calendar", "v3", credentials=creds)
    service.events().delete(calendarId=calendar_id, eventId=google_event_id).execute()
