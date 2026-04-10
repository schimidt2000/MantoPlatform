import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

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
    except Exception:
        return None


def parse_event_datetime(item: dict) -> tuple[datetime | None, datetime | None]:
    start = item.get("start", {})
    end = item.get("end", {})
    start_dt = start.get("dateTime") or start.get("date")
    end_dt = end.get("dateTime") or end.get("date")

    def _parse(value: str | None) -> datetime | None:
        if not value:
            return None
        # date only => midnight in local TZ
        if len(value) == 10:
            return datetime.fromisoformat(value).replace(tzinfo=TZ)
        return datetime.fromisoformat(value)

    return _parse(start_dt), _parse(end_dt)


def insert_event(
    calendar_id: str,
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    description: str = "",
) -> dict:
    """Cria um evento no Google Calendar. Retorna o dict do evento criado (inclui 'id')."""
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
    return service.events().insert(calendarId=calendar_id, body=body).execute()
